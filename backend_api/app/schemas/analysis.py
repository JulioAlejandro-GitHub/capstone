from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AnalysisRunCreate(BaseModel):
    ingestion_batch_id: UUID


class QualityDecisionCreate(BaseModel):
    decision: Literal["approve_with_warnings", "reject"]
    comment: str = Field(min_length=1, max_length=2000)


class QualityQueueCreate(BaseModel):
    analysis_run_id: UUID
    priority: Literal[1, 50, 100] = 50


class QualityQueueRetry(BaseModel):
    priority: Literal[1, 50, 100] = 50
