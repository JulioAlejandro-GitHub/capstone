"""Authenticated HTTP catalog for governed, single-cell EXPLAIN."""
from typing import Annotated, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from app.audit import audited_permission
from app.repositories.explain_generation import ExplainRepository
import os
from app.repositories.explain_queue import ExplainQueueRepository
from app.schemas.explain_generation import ExplainExecutor, ExplainRequest, ExplainState, ExplainSubmission, ExplainPreparation
from app.services.explain_host import HostQueueLauncher, executor_status
from app.security import Permission, Principal, require_permission
from app.services.explain_generation import ExplainService
from app.services.explain_launcher import ExplainLauncher
from src.malaria_dl.campaigns.contracts import CampaignError

router = APIRouter(prefix='/explain-generations', tags=['explain-generations'], dependencies=[
    Depends(require_permission(Permission.RUNS_READ)), Depends(require_permission(Permission.DATASETS_READ)),
    Depends(require_permission(Permission.ARTIFACTS_READ))])


def get_service(repository: Annotated[ExplainRepository, Depends()]) -> ExplainService:
    return ExplainService(repository)


Service = Annotated[ExplainService, Depends(get_service)]


def docker_cpu() -> bool:
    # Explicit environment choice only; without it EXPLAIN never falls back silently to the container CPU.
    return os.getenv('EXPLAIN_EXECUTOR', 'host_gpu') == 'docker_cpu'


def get_launcher() -> ExplainLauncher | HostQueueLauncher:
    return ExplainLauncher() if docker_cpu() else HostQueueLauncher(ExplainQueueRepository())
Reader = Annotated[Principal, Depends(require_permission(Permission.RUNS_READ))]
Writer = Annotated[Principal, Depends(audited_permission(Permission.SCIENTIFIC_CELL_CLASSIFICATION_EXPLAIN, 'scientific.explain.request'))]


@router.get('/executor', response_model=ExplainExecutor)
def executor(principal: Reader) -> dict[str, Any]:
    if docker_cpu():
        return {'executor': 'docker_cpu', 'available': True}
    return executor_status(ExplainQueueRepository())


@router.get('', response_model=ExplainState)
def state(source_attempt_id: UUID, sample_id: UUID, service: Service, principal: Reader,
          class_id: int = Query(1, ge=0, le=1), num_samples: int = Query(1000, ge=1000, le=5000),
          background_sample_id: UUID | None = None) -> dict[str, Any]:
    try:
        return service.state(ExplainRequest(source_attempt_id=source_attempt_id, sample_id=sample_id,
                                 class_id=class_id, num_samples=num_samples, background_sample_id=background_sample_id),
                             Permission.SCIENTIFIC_CELL_CLASSIFICATION_EXPLAIN in principal.permissions)
    except CampaignError as exc:
        raise HTTPException(409, str(exc)) from None


@router.post('/prepare', response_model=ExplainPreparation)
def prepare(request: ExplainRequest, service: Service, principal: Writer) -> dict[str, Any]:
    try:
        return service.preview(request)
    except CampaignError as exc:
        raise HTTPException(409, str(exc)) from None


@router.post('', response_model=ExplainSubmission, status_code=202)
def generate(request: ExplainRequest, service: Service, principal: Writer,
             launcher: Annotated[ExplainLauncher | HostQueueLauncher, Depends(get_launcher)]) -> dict[str, Any]:
    try:
        return service.submit(request, launcher, principal.user_id)
    except CampaignError as exc:
        raise HTTPException(409, str(exc)) from None
