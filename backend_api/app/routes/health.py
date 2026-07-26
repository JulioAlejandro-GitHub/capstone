from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.db import check_connection, get_primary_engine, list_datasources


router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    settings = get_settings()
    return {"status": "ok", "version": settings.app_version, "environment": settings.app_env}


@router.get("/ready")
def ready():
    settings = get_settings()
    components = {"database": "ready", "migrations": "ready", "storage": "ready"}
    try:
        with get_primary_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
            if revision is None:
                components["migrations"] = "not_ready"
    except Exception:
        components["database"] = "not_ready"
        components["migrations"] = "not_ready"
    try:
        for root in (settings.storage_root, settings.artifacts_root):
            Path(root).mkdir(parents=True, exist_ok=True)
            if not Path(root).is_dir():
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
