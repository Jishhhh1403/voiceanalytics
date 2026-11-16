from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db.database import Database
from .api.routes import pipeline, runs


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # init db
    Database(settings.db_path)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    prefix = settings.api_prefix
    app.include_router(pipeline.router, prefix=prefix)
    app.include_router(runs.router, prefix=prefix)

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok", "app": settings.app_name, "schema_version": settings.schema_version}

    @app.get("/api/v1/meta/source")
    def meta():
        return {
            "feedback_source": str(settings.feedback_source_path),
            "jira_source": str(settings.jira_source_path),
            "taxonomy": str(settings.taxonomy_path),
            "synthetic_warning": True,
            "note": "Bundled feedback is synthetic (15k). Jira/backlog source is synthetic sample treated as backlog export. H3 traffic residual unavailable (no real channel/journey denominators).",
        }

    return app


app = create_app()
