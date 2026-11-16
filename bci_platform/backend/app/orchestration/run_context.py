from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..config import Settings
from ..db.database import Database, jdump
from .artifact_manager import ArtifactManager


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RunContext:
    settings: Settings
    db: Database
    run_id: str
    artifacts: ArtifactManager
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def create(cls, settings: Settings, db: Database, feedback_file: str, jira_file: str) -> "RunContext":
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        artifacts = ArtifactManager(settings, run_id)
        db.execute(
            """
            INSERT INTO pipeline_runs(run_id,status,current_module,feedback_file,jira_file,config_json,config_hash,
              schema_version,code_version,warnings_json,started_at,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))
            """,
            (
                run_id,
                "PENDING",
                None,
                feedback_file,
                jira_file,
                jdump(settings.snapshot()),
                settings.config_hash(),
                settings.schema_version,
                settings.code_version,
                jdump([]),
                utcnow(),
            ),
        )
        artifacts.write_json("config_snapshot.json", settings.snapshot())
        artifacts.write_json("manifest.json", {"run_id": run_id, "artifacts": []})
        return cls(settings=settings, db=db, run_id=run_id, artifacts=artifacts)

    def set_run_status(self, status: str, current_module: str | None = None, error: str | None = None) -> None:
        fields = {"status": status, "current_module": current_module, "error": error, "updated_at": utcnow()}
        if status in {"COMPLETED", "FAILED", "CANCELLED"}:
            fields["completed_at"] = utcnow()
        if self.warnings:
            fields["warnings_json"] = jdump(self.warnings)
        sets = ", ".join(f"{k}=?" for k in fields)
        self.db.execute(f"UPDATE pipeline_runs SET {sets} WHERE run_id=?", (*fields.values(), self.run_id))

    def update_counts(self, **counts: int) -> None:
        if not counts:
            return
        sets = ", ".join(f"{k}=?" for k in counts)
        self.db.execute(f"UPDATE pipeline_runs SET {sets}, updated_at=datetime('now') WHERE run_id=?", (*counts.values(), self.run_id))

    def module_start(self, module: str) -> None:
        self.db.execute(
            """INSERT INTO pipeline_module_runs(run_id,module,status,started_at)
                 VALUES(?,?, 'RUNNING', ?)
                 ON CONFLICT(run_id,module) DO UPDATE SET status='RUNNING', started_at=excluded.started_at, error=NULL""",
            (self.run_id, module, utcnow()),
        )

    def module_done(self, module: str, input_count: int | None = None, output_count: int | None = None, message: str | None = None, artifacts: Any = None) -> None:
        self.db.execute(
            """UPDATE pipeline_module_runs SET status='COMPLETED', input_count=?, output_count=?, message=?, artifact_json=?, completed_at=?
                 WHERE run_id=? AND module=?""",
            (input_count, output_count, message, jdump(artifacts), utcnow(), self.run_id, module),
        )

    def module_fail(self, module: str, error: str) -> None:
        self.db.execute(
            """UPDATE pipeline_module_runs SET status='FAILED', error=?, completed_at=? WHERE run_id=? AND module=?""",
            (error, utcnow(), self.run_id, module),
        )

    def record_artifact(self, module: str, artifact_type: str, path: str, checksum: str, metadata: Any = None) -> None:
        self.db.execute(
            "INSERT INTO artifact_manifest(run_id,module,artifact_type,path,checksum,metadata_json) VALUES(?,?,?,?,?,?)",
            (self.run_id, module, artifact_type, path, checksum, jdump(metadata)),
        )
        try:
            manifest = self.artifacts.load_json("manifest.json")
        except Exception:
            manifest = {"run_id": self.run_id, "artifacts": []}
        manifest.setdefault("artifacts", []).append({"module": module, "type": artifact_type, "path": path, "checksum": checksum})
        self.artifacts.write_json("manifest.json", manifest)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        self.db.execute("UPDATE pipeline_runs SET warnings_json=?, updated_at=datetime('now') WHERE run_id=?", (jdump(self.warnings), self.run_id))
