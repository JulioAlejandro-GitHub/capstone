"""Public reading contracts; architecture names remain open strings."""
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ComparisonConfiguration(BaseModel):
    scc_max_comparison_runs: int = Field(ge=1)


class EligibilityReason(BaseModel):
    stage: str
    code: str
    message: str


class ComparisonEligibility(BaseModel):
    run_id: UUID
    eligible: bool
    train: bool | None
    evaluate: bool | None
    explain: bool | None
    reasons: list[EligibilityReason]
    evidence: dict[str, list[dict[str, str]]]


class TrainingReference(BaseModel):
    eligibility: ComparisonEligibility | None = None
    training_run_id: UUID
    status: str
    run_name: str | None = None
    dataset_version_id: UUID | None = None
    started_at: str | None = None


class RegisteredModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    model_id: UUID
    model_name: str
    model_type: str
    architecture: str | None = None
    training_runs: list[TrainingReference]
    has_training_runs: bool
    has_completed_training: bool


class ModelCatalog(BaseModel):
    items: list[RegisteredModel]
    comparison: ComparisonConfiguration


class ScientificRead(BaseModel):
    contract_version: Literal["scc_core_1"] = "scc_core_1"
    training_run_id: UUID
    model: dict[str, Any] | None
    training: dict[str, Any]
    evidence: dict[str, Any]
    assessments: list[dict[str, Any]]
    evidence_status: dict[str, str]
    references: dict[str, str]
