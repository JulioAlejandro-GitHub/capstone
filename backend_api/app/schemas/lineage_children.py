"""Typed contract for direct lineage children of one TRAIN."""

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LineageConfidence(str, Enum):
    EXPLICIT = "explicit"
    INFERRED_EXACT_CHECKPOINT = "inferred_exact_checkpoint"
    INFERRED_MODEL_VERSION = "inferred_model_version"
    INFERRED_HEURISTIC = "inferred_heuristic"
    UNKNOWN = "unknown"


class LineageChildBase(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    run_id: UUID
    status: str
    run_name: str | None
    model_name: str | None
    dataset_name: str | None
    dataset_version_id: UUID | None
    optimizer: str | None
    started_at: datetime | None
    finished_at: datetime | None
    duration_seconds: float | None
    parent_run_id: UUID
    confidence: LineageConfidence
    model_version_id: UUID | None
    checkpoint_artifact_id: UUID | None


class EvaluationLineageChild(LineageChildBase):
    run_type: Literal["evaluation"]
    relationship_type: Literal["evaluates_checkpoint_from"]
    accuracy: float | None
    precision_parasitized: float | None
    recall: float | None
    recall_parasitized: float | None
    sensitivity_parasitized: float | None
    specificity: float | None
    f2_score: float | None
    f2_parasitized: float | None
    auc: float | None
    roc_auc_parasitized: float | None
    pr_auc_parasitized: float | None
    balanced_accuracy: float | None
    threshold_used: float | None
    tn: int | None
    fp: int | None
    fn: int | None
    tp: int | None
    confusion_matrix: list[list[int | float]] | None
    prediction_collapse_detected: bool | None


class ExplainabilityLineageChild(LineageChildBase):
    run_type: Literal["explainability"]
    relationship_type: Literal["explains_checkpoint_from"]
    method: str | None
    methods: list[str]
    total_explanations: int = Field(ge=0)
    success_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)


class TrainingLineageChildren(BaseModel):
    model_config = ConfigDict(extra="forbid")

    training_run_id: UUID
    evaluation_count: int = Field(ge=0)
    explainability_count: int = Field(ge=0)
    total_count: int = Field(ge=0)
    evaluations: list[EvaluationLineageChild]
    explainabilities: list[ExplainabilityLineageChild]
    limit: int = Field(ge=1, le=500)
    truncated: bool
