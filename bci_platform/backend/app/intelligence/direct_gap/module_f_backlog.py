from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from ...db.database import jdump
from ...orchestration.run_context import RunContext
from ..extraction.taxonomy import Taxonomy


def run(ctx: RunContext) -> dict[str, Any]:
    ctx.module_start("module_f_jira_ingestion")
    src = Path(ctx.settings.jira_source_path)
    if not src.exists():
        ctx.warn(f"Jira/backlog source not found: {src}; continuing with empty backlog")
        ctx.module_done("module_f_jira_ingestion", 0, 0, "no backlog source")
        return {"items": 0}
    df = pd.read_csv(src, dtype=str, keep_default_na=False)
    tax = Taxonomy.load(ctx.settings.taxonomy_path)
    # mapping from synthetic backlog format
    rows = []
    for idx, r in df.iterrows():
        bid = str(r.get("backlog_id") or r.get("issue_key") or r.get("key") or f"BL-{idx+1}").strip()
        title = str(r.get("title") or r.get("summary") or "").strip()
        desc = str(r.get("description") or "").strip()
        status = str(r.get("status") or "Unknown").strip()
        issue_type = str(r.get("issue_type") or r.get("type") or "Story").strip()
        priority = str(r.get("priority") or "").strip() or None
        product_area = str(r.get("product_area") or "").strip()
        ac = str(r.get("acceptance_criteria") or "").strip()
        searchable = " ".join([title, desc, ac, product_area]).strip()
        content_hash = hashlib.sha256(searchable.encode("utf-8")).hexdigest()
        journey_node_id, jconf, is_open, _ = tax.map_text(searchable, threshold=0.45)
        # simple intent/aspect profiling
        intents = []
        for k in ["fix","improve","add","show","reduce","enable","support"]:
            if k in searchable.lower(): intents.append(k)
        rows.append((
            bid, ctx.run_id, "jira-synthetic", bid, title, desc, str(r.to_dict()),
            searchable, status, status.lower(), issue_type, priority,
            jdump([]), jdump([product_area] if product_area else []), None, jdump([]),
            journey_node_id, jdump(intents[:5]), jdump([product_area] if product_area else []), jdump({"journey": jconf}),
            "local-hash-embed-v1", content_hash, src.name, None, None,
            jdump({"product_area": product_area, "acceptance_criteria": ac, "source": "synthetic_backlog"}),
        ))
    ctx.db.executemany(
        """INSERT OR REPLACE INTO backlog_items
        (backlog_id,run_id,upload_batch_id,issue_key,title,description,raw_text,searchable_text,status,status_normalized,issue_type,priority,
         labels_json,components_json,parent_id,dependencies_json,journey_node_id,profiled_intents_json,profiled_aspects_json,profile_confidence_json,
         embedding_model_version,content_hash,source_export_id,created_at_source,updated_at_source,metadata_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    report = {"items": len(rows), "source": str(src), "note": "Synthetic backlog treated as Jira export baseline; no status implies delivery."}
    c = ctx.artifacts.write_json("direct/backlog_ingestion_report.json", report)
    ctx.record_artifact("module_f_jira_ingestion", "report", "direct/backlog_ingestion_report.json", c)
    ctx.module_done("module_f_jira_ingestion", input_count=len(df), output_count=len(rows), message=f"backlog items={len(rows)}")
    return report
