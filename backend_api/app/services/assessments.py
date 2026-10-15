"""Assessment consultation never picks a preferred or latest execution."""
from typing import Any
from fastapi import HTTPException
from app.services.scientific_public import public_evidence, assessment_projection
from uuid import UUID
from app.repositories.assessments import AssessmentReadRepository


class AssessmentReadService:
    def __init__(self, repository: AssessmentReadRepository) -> None:
        self.repository = repository

    def list(self, training: UUID | None, campaign: UUID | None, limit: int, offset: int, traceability: bool = False) -> dict[str, Any]:
        items = self.repository.list(training,campaign,limit,offset)
        return {"items": [assessment_projection(item) for item in items] if traceability else items,
                "contract":"assessment_identity_v1"}

    def detail(self, attempt: UUID, traceability: bool = False) -> dict[str, Any] | None:
        result = self.repository.detail(attempt)
        return assessment_projection(result) if traceability and result is not None else result

    def payloads(self, attempt: UUID, kind: str, limit: int, offset: int, traceability: bool = False) -> dict[str, Any]:
        detail = self.repository.detail(attempt) if traceability else None
        if traceability and detail is None:
            raise HTTPException(404, "Assessment not found")
        items = self.repository.payloads(attempt,kind,limit,offset)
        if detail is not None:
            provenance = {key: detail[key] for key in ('attempt_id', 'identity_id', 'training_run_id', 'model_id')}
            provenance['split'] = detail['identity'].get('split')
            items = [{**public_evidence(item), **provenance} for item in items]
            if kind == 'artifacts':
                items = [{**item, 'file_availability': 'not_checked'} for item in items]
        return {"items": items}
