from fastapi import APIRouter, Query

from app.db import fetch_all
from app.services.serialization import rows_to_list


router = APIRouter(tags=["observability"])


@router.get("/errors")
def errors(
    datasource: str | None = Query(default="malaria"),
    limit: int = Query(default=100, ge=1, le=500),
):
    rows = fetch_all(
        datasource,
        """
        SELECT
            e.*,
            r.run_name,
            r.run_type,
            m.name AS model_name
        FROM errors e
        LEFT JOIN runs r ON r.id = e.run_id
        LEFT JOIN models m ON m.id = r.model_id
        ORDER BY e.created_at DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )
    return {"items": rows_to_list(rows)}


@router.get("/logs")
def logs(
    datasource: str | None = Query(default="malaria"),
    limit: int = Query(default=100, ge=1, le=500),
):
    rows = fetch_all(
        datasource,
        """
        SELECT
            l.*,
            r.run_name,
            r.run_type,
            m.name AS model_name
        FROM execution_logs l
        LEFT JOIN runs r ON r.id = l.run_id
        LEFT JOIN models m ON m.id = r.model_id
        ORDER BY l.created_at DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )
    return {"items": rows_to_list(rows)}

