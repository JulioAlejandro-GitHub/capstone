"""Authenticated HTTP catalog for REPRESENT of a verified EVALUATE population."""
from typing import Annotated, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from app.audit import audited_permission
from app.repositories.explain_queue import ExplainQueueRepository
from app.repositories.representation_generation import RepresentRepository
from app.routes.explain_generation import docker_cpu
from app.schemas.representation_generation import RepresentRequest, RepresentState, RepresentSubmission
from app.security import Permission, Principal, require_permission
from app.services.explain_launcher import ExplainLauncher
from app.services.representation_generation import RepresentHostLauncher, RepresentService
from src.malaria_dl.campaigns.contracts import CampaignError

# Executor availability is the EXPLAIN one (/explain-generations/executor): same executor and queue.
router = APIRouter(prefix='/representation-generations', tags=['representation-generations'], dependencies=[
    Depends(require_permission(Permission.RUNS_READ)), Depends(require_permission(Permission.DATASETS_READ)),
    Depends(require_permission(Permission.ARTIFACTS_READ))])


def get_service(repository: Annotated[RepresentRepository, Depends()]) -> RepresentService:
    return RepresentService(repository)


Service = Annotated[RepresentService, Depends(get_service)]


def get_launcher() -> ExplainLauncher | RepresentHostLauncher:
    return ExplainLauncher('app.services.represent_worker') if docker_cpu() else RepresentHostLauncher(ExplainQueueRepository())


Reader = Annotated[Principal, Depends(require_permission(Permission.RUNS_READ))]
Writer = Annotated[Principal, Depends(audited_permission(Permission.SCIENTIFIC_CELL_CLASSIFICATION_EXPLAIN, 'scientific.represent.request'))]


@router.get('', response_model=RepresentState)
def state(source_attempt_id: UUID, service: Service, principal: Reader) -> dict[str, Any]:
    try:
        return service.state(RepresentRequest(source_attempt_id=source_attempt_id),
                             Permission.SCIENTIFIC_CELL_CLASSIFICATION_EXPLAIN in principal.permissions)
    except CampaignError as exc:
        raise HTTPException(409, str(exc)) from None


@router.post('', response_model=RepresentSubmission, status_code=202)
def generate(request: RepresentRequest, service: Service, principal: Writer,
             launcher: Annotated[ExplainLauncher | RepresentHostLauncher, Depends(get_launcher)]) -> dict[str, Any]:
    try:
        return service.submit(request, launcher, principal.user_id)
    except CampaignError as exc:
        raise HTTPException(409, str(exc)) from None
