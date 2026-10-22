"""Immutable assessment history and evidence selected by attempt ID."""
from typing import Annotated, Any, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.repositories.assessments import AssessmentReadRepository
from app.services.assessments import AssessmentReadService

router = APIRouter(prefix="/assessments", tags=["assessments"])


class AssessmentList(BaseModel):
    items: list[dict[str, Any]]
    contract: str = "assessment_identity_v1"


class AssessmentPayloads(BaseModel):
    items: list[dict[str, Any]]


def get_service(repository: Annotated[AssessmentReadRepository, Depends()]) -> AssessmentReadService:
    return AssessmentReadService(repository)


Service = Annotated[AssessmentReadService, Depends(get_service)]


@router.get("", response_model=AssessmentList)
def list_assessments(service: Service, training_run_id: UUID | None = None,
                     campaign_id: UUID | None = None, limit: int = Query(50, ge=1, le=500),
                     offset: int = Query(0, ge=0), view: Literal['existing', 'traceability'] = 'existing') -> dict[str, Any]:
    return service.list(training_run_id,campaign_id,limit,offset, view == 'traceability')


@router.get("/{attempt_id}", response_model=dict[str, Any])
def assessment(attempt_id: UUID, service: Service, view: Literal['existing', 'traceability'] = 'existing') -> dict[str, Any]:
    result = service.detail(attempt_id, view == 'traceability')
    if result is None:
        raise HTTPException(404,"Assessment not found")
    return result


@router.get("/{attempt_id}/results", response_model=AssessmentPayloads)
def results(attempt_id: UUID, service: Service, limit: int = Query(100, ge=1, le=1000),
            offset: int = Query(0, ge=0), view: Literal['existing', 'traceability'] = 'existing') -> dict[str, Any]:
    return service.payloads(attempt_id,"results",limit,offset, view == "traceability")


@router.get("/{attempt_id}/artifacts", response_model=AssessmentPayloads)
def artifacts(attempt_id: UUID, service: Service, limit: int = Query(100, ge=1, le=1000),
              offset: int = Query(0, ge=0), view: Literal['existing', 'traceability'] = 'existing',
              sample_id: Annotated[list[UUID] | None, Query(max_length=100)] = None) -> dict[str, Any]:
    return service.payloads(attempt_id,"artifacts",limit,offset, view == "traceability", sample_id)
