import os
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.config import get_settings
from app.database_safety import assert_capstone_database
from app.db import get_primary_engine, list_datasources


router = APIRouter(tags=["health"])


@router.get("/health")
def health(datasource: str | None = Query("malaria")):
    settings = get_settings()
    return {"status": "ok", "version": settings.app_version, "environment": settings.app_env}


@router.get("/ready")
def ready():
    settings = get_settings()
    expected_revision = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
    components = {"database": "ready", "migrations": "ready", "storage": "ready"}
    try:
        with get_primary_engine().connect() as connection:
            actual_database = connection.execute(text("SELECT current_database()")).scalar_one()
            assert_capstone_database(settings, actual_database)
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
            if revision != expected_revision:
                components["migrations"] = "not_ready"
    except Exception:
        components["database"] = "not_ready"
        components["migrations"] = "not_ready"
    try:
        for root in (settings.storage_root, settings.artifacts_root):
            path = Path(root)
            if not path.is_dir() or not os.access(path, os.R_OK | os.W_OK | os.X_OK):
                raise OSError()
    except OSError:
        components["storage"] = "not_ready"
    is_ready = all(value == "ready" for value in components.values())
    body = {"status": "ready" if is_ready else "not_ready", "components": components,
            "version": settings.app_version, "environment": settings.app_env}
    return body if is_ready else JSONResponse(body, status_code=503)


@router.get("/datasources")
def datasources():
    return {"items": list_datasources()}
