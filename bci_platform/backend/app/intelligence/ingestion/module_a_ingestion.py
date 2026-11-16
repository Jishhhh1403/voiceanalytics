from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from ...config import Settings
from ...db.database import jdump
from ...orchestration.run_context import RunContext


PII_PATTERNS = [
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("PHONE", re.compile(r"\b(?:\+?\d[\d\s-]{8,}\d)\b")),
    ("CARD", re.compile(r"\b(?:\d[ -]*?){13,16}\b")),
    ("UPI", re.compile(r"\b[\w.\-]{2,}@[a-zA-Z]{2,}\b")),
    ("ACCOUNT", re.compile(r"\b\d{9,18}\b")),
]


def _norm_text(text: str) -> str:
    if text is None:
        return ""
    t = str(text).replace("\u200b", " ").replace("\xa0", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _clean_text(text: str) -> str:
    t = _norm_text(text)
    # preserve meaning/negation/numbers; only light normalization
    return t


def _hash_customer(customer_id: str | None, salt: str) -> str | None:
    if customer_id is None or str(customer_id).strip() == "" or str(customer_id).lower() == "nan":
        return None
    raw = f"{salt}::{str(customer_id).strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_ts(val: Any) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        # handle Z
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        try:
            dt = pd.to_datetime(s, utc=True)
            return dt.to_pydatetime().isoformat()
        except Exception:
            return None


def _redact(text: str) -> tuple[str, list[str], bool]:
    redacted = text
    types: list[str] = []
    for label, pat in PII_PATTERNS:
        if pat.search(redacted):
            types.append(label)
            redacted = pat.sub(f"[{label}]", redacted)
    return redacted, sorted(set(types)), bool(types)


def _shingles(text: str, k: int = 3) -> set[str]:
    toks = re.findall(r"[a-z0-9]+", text.lower())
    if len(toks) < k:
        return set([" ".join(toks)]) if toks else set()
    return {" ".join(toks[i : i + k]) for i in range(len(toks) - k + 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def run(ctx: RunContext) -> dict[str, Any]:
    ctx.module_start("module_a_ingestion")
    settings = ctx.settings
    src = Path(settings.feedback_source_path)
    if not src.exists():
        ctx.module_fail("module_a_ingestion", f"Feedback source not found: {src}")
        raise FileNotFoundError(src)

    df = pd.read_csv(src, dtype=str, keep_default_na=False)
    total = len(df)
    # source-to-canonical mapping (voice-analytics style dataset)
    colmap = {
        "feedback_id": "feedback_id",
        "synthetic_customer_ref": "customer_id",
        "submitted_at": "timestamp",
        "source_channel": "channel",
        "platform": "platform",
        "rating_1_to_5": "rating",
        "language": "language",
        "feedback_text": "raw_text",
        "customer_tier": "customer_tier",
    }
    # normalize columns presence
    for src_col in colmap:
        if src_col not in df.columns and colmap[src_col] not in df.columns:
            # allow missing optional
            pass

    accepted = 0
    rejected = 0
    rows = []
    rejects = []
    seen_ids: set[str] = set()
    for idx, r in df.iterrows():
        fid = str(r.get("feedback_id") or f"FB-ROW-{idx+1}").strip()
        if fid in seen_ids:
            # deterministic suffix to preserve
            fid = f"{fid}-DUPROW-{idx+1}"
        seen_ids.add(fid)
        raw = _norm_text(r.get("feedback_text") or r.get("raw_text") or "")
        cust = r.get("synthetic_customer_ref") or r.get("customer_id") or r.get("customer_ref")
        ts = _parse_ts(r.get("submitted_at") or r.get("timestamp"))
        channel = _norm_text(r.get("source_channel") or r.get("channel") or "")
        tier = _norm_text(r.get("customer_tier") or "") or None
        platform = _norm_text(r.get("platform") or "") or None
        lang = _norm_text(r.get("language") or "") or None
        rating_s = str(r.get("rating_1_to_5") or r.get("rating") or "").strip()
        try:
            rating = int(float(rating_s)) if rating_s else None
        except Exception:
            rating = None

        reason = None
        if not raw:
            reason = "empty_raw_text"
        elif len(raw) < 3:
            reason = "too_short"
        if reason:
            rejected += 1
            rejects.append({"source_row": int(idx) + 2, "feedback_id": fid, "reason": reason, "raw_text": raw})
            ctx.db.execute(
                "INSERT OR REPLACE INTO feedback_records(run_id,feedback_id,source_row,raw_text,cleaned_text,ingestion_status,reject_reason,source_file,is_duplicate_representative) VALUES(?,?,?,?,?,?,?, ?,0)",
                (ctx.run_id, fid, int(idx) + 2, raw, "", "rejected", reason, str(src)),
            )
            continue

        cleaned = _clean_text(raw)
        red_clean, pii_types, pii_flag = _redact(cleaned)
        row = {
            "run_id": ctx.run_id,
            "feedback_id": fid,
            "source_row": int(idx) + 2,
            "customer_id_hash": _hash_customer(cust, settings.customer_id_salt),
            "timestamp": ts,
            "channel": channel or None,
            "customer_tier": tier,
            "platform": platform,
            "rating": rating,
            "language": lang,
            "raw_text": raw,
            "cleaned_text": red_clean,
            "duplicate_group_id": None,
            "is_duplicate_representative": 1,
            "pii_redacted": 1 if pii_flag else 0,
            "pii_types_json": jdump(pii_types),
            "ingestion_status": "accepted",
            "reject_reason": None,
            "source_file": str(src),
        }
        rows.append(row)
        accepted += 1

    # near-duplicate grouping per customer within window
    groups: dict[str, list[int]] = defaultdict(list)
    texts = [r["cleaned_text"] for r in rows]
    shingle_sets = [_shingles(t) for t in texts]
    by_cust: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        key = r["customer_id_hash"] or "__none__"
        by_cust[key].append(i)

    def within_window(a: str | None, b: str | None) -> bool:
        if not a or not b:
            return True  # if missing ts, allow comparison by policy-conservative; flagged in report
        try:
            da = datetime.fromisoformat(a)
            dbb = datetime.fromisoformat(b)
            return abs((da - dbb).total_seconds()) <= settings.duplicate_window_hours * 3600
        except Exception:
            return True

    gid_counter = 0
    assigned = [-1] * len(rows)
    for cust, idxs in by_cust.items():
        n = len(idxs)
        if n < 2:
            continue
        parent = list(range(n))
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        def union(a,b):
            ra, rb = find(a), find(b)
            if ra!=rb: parent[rb]=ra
        for a in range(n):
            ia = idxs[a]
            for b in range(a+1, n):
                ib = idxs[b]
                if not within_window(rows[ia]["timestamp"], rows[ib]["timestamp"]):
                    continue
                sim = _jaccard(shingle_sets[ia], shingle_sets[ib])
                if sim >= settings.duplicate_similarity_threshold:
                    union(a,b)
        comps: dict[int, list[int]] = defaultdict(list)
        for a in range(n):
            comps[find(a)].append(idxs[a])
        for comp in comps.values():
            if len(comp) < 2:
                continue
            gid_counter += 1
            gid = f"DUP-{ctx.run_id[-8:]}-{gid_counter:05d}"
            # representative: earliest timestamp else first source_row
            comp_sorted = sorted(comp, key=lambda i: (rows[i]["timestamp"] or "9999", rows[i]["source_row"]))
            rep = comp_sorted[0]
            for i in comp:
                rows[i]["duplicate_group_id"] = gid
                rows[i]["is_duplicate_representative"] = 1 if i == rep else 0

    # persist
    ins_sql = """
    INSERT OR REPLACE INTO feedback_records
    (run_id,feedback_id,source_row,customer_id_hash,timestamp,channel,customer_tier,platform,rating,language,
     raw_text,cleaned_text,duplicate_group_id,is_duplicate_representative,pii_redacted,pii_types_json,
     ingestion_status,reject_reason,source_file)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """
    params = [(
        r["run_id"], r["feedback_id"], r["source_row"], r["customer_id_hash"], r["timestamp"], r["channel"], r["customer_tier"],
        r["platform"], r["rating"], r["language"], r["raw_text"], r["cleaned_text"], r["duplicate_group_id"],
        r["is_duplicate_representative"], r["pii_redacted"], r["pii_types_json"], r["ingestion_status"], r["reject_reason"], r["source_file"]
    ) for r in rows]
    ctx.db.executemany(ins_sql, params)

    dup_members = sum(1 for r in rows if r["duplicate_group_id"])
    report = {
        "source_file": str(src),
        "total_rows": total,
        "accepted": accepted,
        "rejected": rejected,
        "duplicate_groups": gid_counter,
        "duplicate_members": dup_members,
        "representatives": sum(1 for r in rows if r["is_duplicate_representative"]),
        "pii_redacted_rows": sum(1 for r in rows if r["pii_redacted"]),
        "missing_timestamp": sum(1 for r in rows if not r["timestamp"]),
        "missing_customer": sum(1 for r in rows if not r["customer_id_hash"]),
        "channels": pd.Series([r["channel"] or "unknown" for r in rows]).value_counts().to_dict() if rows else {},
        "tiers": pd.Series([r["customer_tier"] or "unknown" for r in rows]).value_counts().to_dict() if rows else {},
    }
    rep_rows = rejects
    import csv as _csv
    rej_path = ctx.artifacts.path("ingestion", "rejected_rows.csv")
    with rej_path.open("w", newline="", encoding="utf-8") as f:
        w = _csv.DictWriter(f, fieldnames=["source_row","feedback_id","reason","raw_text"])
        w.writeheader()
        for rr in rejects:
            w.writerow(rr)
    c1 = ctx.artifacts.write_json("ingestion/ingestion_quality_report.json", report)
    ctx.record_artifact("module_a_ingestion", "report", "ingestion/ingestion_quality_report.json", c1, {"rows": accepted})
    ctx.record_artifact("module_a_ingestion", "rejected_rows", "ingestion/rejected_rows.csv", ArtifactManager_checksum(rej_path), {"rows": rejected})

    ctx.update_counts(feedback_count=accepted)
    ctx.module_done("module_a_ingestion", input_count=total, output_count=accepted, message=f"accepted={accepted} rejected={rejected}", artifacts={"report": "ingestion/ingestion_quality_report.json"})
    return report


def ArtifactManager_checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()
