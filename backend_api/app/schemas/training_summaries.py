"""Typed response contract for the lightweight TRAIN listing."""

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TrainingReleaseStatus(str, Enum):
    NOT_AVAILABLE = "not_available"
    AVAILABLE_TO_PUBLISH = "available_to_publish"
    PRODUCTIVE_STAGE2 = "productive_stage2"


class TrainingSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    run_id: UUID
    run_type: Literal["training"]
    status: str
    release_status: TrainingReleaseStatus | None
    release_updated_at: datetime | None
    release_changed_by: str | None
    release_reason: str | None
    evaluation_count: int = Field(ge=0)
    explainability_count: int = Field(ge=0)
    run_name: str
    model_name: str | None
    dataset_name: str | None
    dataset_version_id: UUID | None
    optimizer: str | None
    command: str | None
    started_at: datetime | None
    finished_at: datetime | None
    duration_seconds: float | None
    recall: float | None
    recall_parasitized: float | None
    specificity: float | None
    f2_score: float | None
    f2_parasitized: float | None
    auc: float | None
    roc_auc_parasitized: float | None
    tn: int | None
    fp: int | None
    fn: int | None
    tp: int | None
    confusion_matrix: list[list[int | float]] | None
    prediction_collapse_detected: bool | None


class TrainingSummaryCollection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TrainingSummary]
    count: int = Field(ge=0)
    limit: int = Field(ge=1, le=500)
