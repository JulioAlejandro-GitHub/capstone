from fastapi import APIRouter, Query

from app.db import fetch_all
from app.services.serialization import rows_to_list


router = APIRouter(tags=["catalog"])


@router.get("/models")
def models(datasource: str | None = Query(default="malaria")):
    rows = fetch_all(
        datasource,
        """
        SELECT
            s.*,
            m.framework,
            m.architecture,
            m.input_shape,
            m.output_shape,
            m.pretrained,
            m.pretrained_source,
            m.created_at,
            m.metadata
        FROM vw_model_run_summary s
        LEFT JOIN models m ON m.id = s.model_id
        ORDER BY s.total_runs DESC, s.model_name
        """,
    )
    return {"items": rows_to_list(rows)}


@router.get("/models/comparison")
@router.get("/api/models/comparison")
def model_comparison(
    datasource: str | None = Query(default="malaria"),
    limit: int = Query(default=100, ge=1, le=500),
):
    rows = fetch_all(
        datasource,
        """
        SELECT *
        FROM vw_clinical_run_summary
        ORDER BY started_at DESC NULLS LAST
        LIMIT :limit
        """,
        {"limit": limit},
    )
    return {"items": rows_to_list(rows)}


@router.get("/datasets")
def datasets(datasource: str | None = Query(default="malaria")):
    rows = fetch_all(
        datasource,
        """
        SELECT *
        FROM datasets
        ORDER BY created_at DESC
        """,
    )
    return {"items": rows_to_list(rows)}
