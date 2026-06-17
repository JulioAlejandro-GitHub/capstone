from fastapi import APIRouter, Query

from app.db import check_connection, list_datasources


router = APIRouter(tags=["health"])


@router.get("/health")
def health(datasource: str | None = Query(default="malaria")):
    connection = check_connection(datasource)
    return {"status": "ok", **connection}


@router.get("/datasources")
def datasources():
    return {"items": list_datasources()}

