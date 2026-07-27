from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AnalysisRunCreate(BaseModel):
    ingestion_batch_id: UUID


class QualityDecisionCreate(BaseModel):
    decision: Literal["approve_with_warnings", "reject"]
    comment: str = Field(min_length=1, max_length=2000)
