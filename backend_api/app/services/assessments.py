"""Assessment consultation never picks a preferred or latest execution."""
from typing import Any
from uuid import UUID
from app.repositories.assessments import AssessmentReadRepository


class AssessmentReadService:
    def __init__(self, repository: AssessmentReadRepository) -> None:
        self.repository = repository

    def list(self, training: UUID | None, campaign: UUID | None, limit: int, offset: int) -> dict[str, Any]:
        return {"items": self.repository.list(training,campaign,limit,offset), "contract":"assessment_identity_v1"}

    def detail(self, attempt: UUID) -> dict[str, Any] | None:
        return self.repository.detail(attempt)

    def payloads(self, attempt: UUID, kind: str, limit: int, offset: int) -> dict[str, Any]:
        return {"items":self.repository.payloads(attempt,kind,limit,offset)}
