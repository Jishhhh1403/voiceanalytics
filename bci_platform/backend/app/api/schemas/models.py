from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class PipelineRunRequest(BaseModel):
    feedback_file: Optional[str] = None
    jira_file: Optional[str] = None
    provider_mode: str = "local"
    configuration_profile: str = "baseline"


class PipelineRunResponse(BaseModel):
    run_id: str
    status: str


class RunStatus(BaseModel):
    run_id: str
    status: str
    current_module: Optional[str] = None
    modules: list[dict[str, Any]] = []
    counts: dict[str, Any] = {}
    warnings: list[str] = []
    error: Optional[str] = None


class ExportRequest(BaseModel):
    candidate_ids: list[str] = Field(default_factory=list)
    format: str = "json"
