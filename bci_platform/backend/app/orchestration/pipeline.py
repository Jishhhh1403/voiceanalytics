from __future__ import annotations

import traceback
from typing import Any

from ..config import Settings
from ..db.database import Database
from .run_context import RunContext
from ..intelligence.ingestion import module_a_ingestion
from ..intelligence.extraction import module_b_extraction
from ..intelligence.direct_gap import module_c_vectorize, module_d_clustering, module_e_canonical, module_f_backlog, module_g_validator
from ..intelligence.whitespace import graph_analyzer, spatial_analyzer, combinatorial_analyzer, triangulator
from ..intelligence import unified_merger


MODULES = [
    ("module_a_ingestion", module_a_ingestion.run),
    ("module_b_extraction", module_b_extraction.run),
    ("module_c_vectorize", module_c_vectorize.run),
    ("module_d_clustering", module_d_clustering.run),
    ("module_e_canonical", module_e_canonical.run),
    ("module_f_jira_ingestion", module_f_backlog.run),
    ("module_g_validator", module_g_validator.run),
    ("module_h1_graph", graph_analyzer.run),
    ("module_h2_spatial", spatial_analyzer.run),
    ("module_h3_combinatorial", combinatorial_analyzer.run),
    ("module_h4_triangulation", triangulator.run),
    ("unified_merger", unified_merger.run),
]


def execute_run(settings: Settings, db: Database, feedback_file: str | None = None, jira_file: str | None = None) -> dict[str, Any]:
    feedback_file = feedback_file or str(settings.feedback_source_path)
    jira_file = jira_file or str(settings.jira_source_path)
    ctx = RunContext.create(settings, db, feedback_file, jira_file)
    ctx.set_run_status("RUNNING", current_module=MODULES[0][0])
    results = {}
    try:
        for name, fn in MODULES:
            ctx.set_run_status("RUNNING", current_module=name)
            try:
                res = fn(ctx)
                results[name] = res
            except Exception as e:
                err = f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=5)}"
                ctx.module_fail(name, err)
                ctx.set_run_status("FAILED", current_module=name, error=str(e))
                return {"run_id": ctx.run_id, "status": "FAILED", "failed_module": name, "error": str(e), "results": results}
        ctx.set_run_status("COMPLETED", current_module=None)
        return {"run_id": ctx.run_id, "status": "COMPLETED", "results": results}
    except Exception as e:
        ctx.set_run_status("FAILED", error=str(e))
        return {"run_id": ctx.run_id, "status": "FAILED", "error": str(e), "results": results}
