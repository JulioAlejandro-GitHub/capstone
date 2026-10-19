from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from app.services.catalog import CatalogService, get_catalog_service
from app.schemas.scientific_read import ModelCatalog

from app.db import fetch_all
from app.services.serialization import rows_to_list


router = APIRouter(tags=["catalog"])


@router.get("/models", response_model=ModelCatalog)
def models(
    service: Annotated[CatalogService, Depends(get_catalog_service)],
    datasource: str | None = Query(default="malaria"),
    view: Literal["existing", "traceability"] = "existing",
    comparison: bool = False,
) -> dict[str, Any]:
    return service.models(datasource, view == "traceability", comparison=comparison)


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
