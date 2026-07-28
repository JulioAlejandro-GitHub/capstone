from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CellDetectionRunCreate(BaseModel):
    analysis_run_id: UUID


class ScientificReviewCreate(BaseModel):
    decision: Literal["accepted", "rejected", "needs_attention", "comment_only"]
    comment: str | None = Field(default=None, max_length=4000)

