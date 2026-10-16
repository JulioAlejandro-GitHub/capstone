"""Authenticated query endpoint; POST only transports explicit scientific identities."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from app.db import resolve_datasource
from app.observability import correlation_id_context
from app.schemas.scientific_preflight import PreflightRequest, PreflightResponse
from app.schemas.scientific_report import (
    ScientificReportRequest,
    ScientificReportResponse,
)
from app.security import Permission, Principal, require_permission
from app.services.scientific_preflight import ScientificPreflightService
from app.services.scientific_report import ScientificReportService

router = APIRouter(tags=['models'])


def preflight_principal(
    principal: Annotated[Principal, Depends(require_permission(Permission.RUNS_READ))],
) -> Principal:
    # RBAC is global in this project. Apply every consulted domain before reads.
    # An anonymous auth_mode=disabled principal cannot satisfy this endpoint.
    if principal.insecure_local:
        raise HTTPException(401, 'Autenticación obligatoria para Preflight.')
    required = {Permission.MODELS_READ, Permission.DATASETS_READ,
                Permission.PREDICTIONS_READ, Permission.ARTIFACTS_READ}
    if not required.issubset(principal.permissions):
        raise HTTPException(403, 'Permiso insuficiente para los recursos del Preflight.')
    return principal


@router.post('/models/comparison/preflight', response_model=PreflightResponse)
def scientific_preflight(
    body: PreflightRequest, response: Response,
    principal: Annotated[Principal, Depends(preflight_principal)], datasource: str | None = None,
):
    response.headers['Cache-Control'] = 'private, no-store'
    return ScientificPreflightService().read(
        body, resolve_datasource(datasource), correlation_id_context.get() or 'preflight')


@router.post('/models/comparison/report', response_model=ScientificReportResponse)
def scientific_report(
    body: ScientificReportRequest, response: Response,
    principal: Annotated[Principal, Depends(preflight_principal)], datasource: str | None = None,
):
    response.headers['Cache-Control'] = 'private, no-store'
    return ScientificReportService().read(body, resolve_datasource(datasource))
