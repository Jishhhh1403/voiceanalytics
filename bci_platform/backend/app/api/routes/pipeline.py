from __future__ import annotations

import threading

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from ...config import Settings, get_settings
from ...db.database import Database
from ...orchestration.pipeline import execute_run

router = APIRouter(tags=["pipeline"])

_db: Database | None = None


def get_db(settings: Settings = Depends(get_settings)) -> Database:
    global _db
    if _db is None:
        _db = Database(settings.db_path)
    return _db


class PipelineRunRequest(BaseModel):
    feedback_file: Optional[str] = None
    jira_file: Optional[str] = None
    provider_mode: str = "local"
    configuration_profile: str = "baseline"


@router.post("/pipeline/run")
def start_pipeline(req: PipelineRunRequest, settings: Settings = Depends(get_settings), db: Database = Depends(get_db)):
    from ...orchestration.run_context import RunContext
    feedback_file = req.feedback_file or str(settings.feedback_source_path)
    jira_file = req.jira_file or str(settings.jira_source_path)
    ctx = RunContext.create(settings, db, feedback_file, jira_file)

    def worker(run_id: str):
        wdb = Database(settings.db_path)
        # execute modules for existing run
        from ...orchestration.pipeline import MODULES
        from ...orchestration.artifact_manager import ArtifactManager
        wctx = RunContext(settings=settings, db=wdb, run_id=run_id, artifacts=ArtifactManager(settings, run_id))
        try:
            existing = wdb.query_one("SELECT warnings_json FROM pipeline_runs WHERE run_id=?", (run_id,))
            import json as _json
            wctx.warnings = _json.loads((existing or {}).get("warnings_json") or "[]")
        except Exception:
            wctx.warnings = []
        wctx.set_run_status("RUNNING", current_module=MODULES[0][0])
        try:
            for name, fn in MODULES:
                wctx.set_run_status("RUNNING", current_module=name)
                fn(wctx)
            wctx.set_run_status("COMPLETED", current_module=None)
        except Exception as e:
            import traceback
            err = f"{type(e).__name__}: {e}"
            try:
                cur = wdb.query_one("SELECT current_module FROM pipeline_runs WHERE run_id=?", (run_id,))
                mod = (cur or {}).get("current_module") or "unknown"
                wctx.module_fail(mod, err + "\n" + traceback.format_exc(limit=8))
            except Exception:
                pass
            wctx.set_run_status("FAILED", error=err)

    t = threading.Thread(target=worker, args=(ctx.run_id,), daemon=True)
    t.start()
    return {"run_id": ctx.run_id, "status": "PENDING"}
