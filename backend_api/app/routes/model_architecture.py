"""Read-only architecture recorded by one TRAIN."""
from typing import Annotated, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from app.schemas.model_architecture import ModelArchitecture
from app.security import Permission, require_permission
from app.services.model_architecture import ModelArchitectureService, get_model_architecture_service

router = APIRouter(tags=['model-architecture'], dependencies=[Depends(require_permission(Permission.RUNS_READ))])


@router.get('/runs/{run_id}/architecture', response_model=ModelArchitecture)
def model_architecture(
    run_id: UUID,
    service: Annotated[ModelArchitectureService, Depends(get_model_architecture_service)],
    datasource: str | None = Query(None),
) -> dict[str, Any]:
    return service.read(run_id, datasource)
