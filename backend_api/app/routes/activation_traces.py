"""Authenticated catalog of saved activation traces of one TRAIN."""
from typing import Annotated, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from app.schemas.activation_traces import ActivationTrace, ActivationTraceCandidate, ActivationTraceCatalog, ActivationTraceRequest
from app.security import Permission, require_permission
from app.services.activation_traces import ActivationTraceService, get_activation_trace_service

router = APIRouter(prefix='/runs/{run_id}/activation-traces', tags=['activation-traces'],
                   dependencies=[Depends(require_permission(Permission.RUNS_READ))])
Service = Annotated[ActivationTraceService, Depends(get_activation_trace_service)]
Writer = Depends(require_permission(Permission.SCIENTIFIC_CELL_CLASSIFICATION_EXPLAIN))


@router.get('', response_model=ActivationTraceCatalog)
def catalog(run_id: UUID, service: Service, datasource: str | None = Query(None)) -> dict[str, Any]:
    return service.catalog(run_id, datasource)


@router.get('/candidates', response_model=list[ActivationTraceCandidate])
def candidates(run_id: UUID, service: Service, category: str = Query('false_negative'), limit: int = Query(8, ge=1, le=50),
               datasource: str | None = Query(None), explained: bool = Query(False)) -> list[dict[str, Any]]:
    return service.candidates(run_id, category, limit, datasource, explained)


@router.get('/{sample_id}', response_model=ActivationTrace)
def read(run_id: UUID, sample_id: UUID, service: Service) -> dict[str, Any]:
    return service.read(run_id, sample_id)


@router.post('', response_model=ActivationTrace, status_code=201, dependencies=[Writer])
def create(run_id: UUID, body: ActivationTraceRequest, service: Service, datasource: str | None = Query(None)) -> dict[str, Any]:
    return service.create(run_id, body.sample_id, datasource)


@router.delete('/{sample_id}', dependencies=[Writer])
def delete(run_id: UUID, sample_id: UUID, service: Service) -> dict[str, bool]:
    service.delete(run_id, sample_id)
    return {'deleted': True}
