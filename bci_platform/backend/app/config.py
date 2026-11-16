from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Banking Customer Intelligence (A-H)"
    environment: str = "local"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    tenant_id: str = "demo-bank"
    code_version: str = "0.1.0"
    schema_version: str = "1.0.0"

    data_dir: Path = REPO_ROOT / "data"
    database_path: Path | None = None
    object_store: str = "local"
    local_object_root: Path | None = None

    feedback_source_path: Path = REPO_ROOT / "data" / "raw" / "feedback" / "synthetic_banking_app_feedback_15000.csv"
    jira_source_path: Path = REPO_ROOT / "data" / "raw" / "jira" / "sample_backlog_upload.csv"
    taxonomy_path: Path = REPO_ROOT / "taxonomy" / "banking_taxonomy_v1.yaml"
    artifacts_dir: Path = REPO_ROOT / "artifacts"

    random_seed: int = 42
    batch_size: int = 32

    # Ingestion
    duplicate_similarity_threshold: float = 0.90
    duplicate_window_hours: int = 24
    customer_id_salt: str = "bci-local-salt"

    # Extraction
    taxonomy_confidence_threshold: float = 0.55
    enable_workaround_tagger: bool = True
    extraction_provider: str = "rules"  # rules|bert|llm
    extraction_model_version: str = "rules-v1"

    # Clustering
    svd_components: int = 100
    min_cluster_size: int = 15
    min_samples: int = 5
    mega_cluster_fraction: float = 0.08
    open_set_effort_threshold: float = 4.0
    open_set_min_count: int = 5

    # Direct gap / backlog
    covered_threshold: float = 0.75
    gray_zone_lower: float = 0.60
    backlog_top_k: int = 5

    # Whitespace
    triangulation_min_lenses: int = 2
    feedback_jaccard_threshold: float = 0.30
    graph_followed_by_days: int = 7
    graph_addressed_by_threshold: float = 0.60
    motif_min_support: int = 5
    n_components_nmf: int = 12
    spatial_grid_size: int = 100
    void_backlog_factor: float = 0.85

    # Providers / LLM
    embedding_provider: str = "local"  # local|sentence_transformer|gemini
    sentence_transformer_model: str = "BAAI/bge-large-en-v1.5"
    generation_provider: str = "gemini"  # gemini|none
    allow_cloud_calls: bool = True
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    llm_timeout_seconds: int = 60

    # Runtime
    cors_origins: str = "http://localhost:5173,http://localhost:8080,http://localhost:3000"

    @property
    def db_path(self) -> Path:
        return self.database_path or (self.data_dir / "local" / "bci.db")

    @property
    def object_root(self) -> Path:
        return self.local_object_root or (self.data_dir / "local" / "objects")

    @property
    def cors_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    def ensure_dirs(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.object_root.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "processed").mkdir(parents=True, exist_ok=True)

    def snapshot(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        # do not leak secrets in artifacts
        for k in list(data.keys()):
            if "key" in k.lower() or "secret" in k.lower() or "token" in k.lower():
                data[k] = "***" if data[k] else ""
        return data

    def config_hash(self) -> str:
        return hashlib.sha256(json.dumps(self.snapshot(), sort_keys=True).encode()).hexdigest()[:16]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
