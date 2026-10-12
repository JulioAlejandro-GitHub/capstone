"""E6 evaluations retain their attempt identity, independently of public.runs."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, JsonValue


class AssessmentEvaluationChild(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_kind: Literal["assessment_e6"] = "assessment_e6"
    attempt_id: UUID
    identity_id: UUID
    training_run_id: UUID
    state: Literal["active", "verified", "failed", "interrupted"]
    ordinal: int
    split: Literal["train", "val", "test"]
    purpose: Literal["development", "final"]
    started_at: datetime
    finished_at: datetime | None
    verification: dict[str, JsonValue] | None
