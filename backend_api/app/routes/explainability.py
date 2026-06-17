from fastapi import APIRouter, Query

from app.db import fetch_all
from app.services.serialization import rows_to_list


router = APIRouter(tags=["explainability"])


@router.get("/explainability")
def explainability(
    datasource: str | None = Query(default="malaria"),
    limit: int = Query(default=100, ge=1, le=500),
):
    rows = fetch_all(
        datasource,
        """
        SELECT
            er.*,
            r.run_name,
            r.run_type,
            m.name AS model_name
        FROM explainability_results er
        LEFT JOIN runs r ON r.id = er.run_id
        LEFT JOIN models m ON m.id = r.model_id
        ORDER BY er.created_at DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )
    summary = fetch_all(
        datasource,
        """
        SELECT
            s.*,
            r.run_name,
            m.name AS model_name
        FROM vw_explainability_summary s
        LEFT JOIN runs r ON r.id = s.run_id
        LEFT JOIN models m ON m.id = r.model_id
        ORDER BY total_explanations DESC, method
        """,
    )
    return {"summary": rows_to_list(summary), "items": rows_to_list(rows)}

