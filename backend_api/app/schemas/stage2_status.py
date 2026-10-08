"""Independent eligibility, operational readiness, publication and availability."""

from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, JsonValue


class Stage2Condition(BaseModel):
    code: str
    message: str


class Stage2Eligibility(BaseModel):
    train_completed: bool
    evaluate_completed: bool
    missing_conditions: list[str]


class DeploymentReadiness(BaseModel):
    ready: bool
    status: Literal["ready", "blocked"]
    checkpoint_accessible: bool
    checkpoint_verified: bool


class Stage2Status(BaseModel):
    training_run_id: UUID
    train_status: str
    train_started_at: datetime | None = None
    train_finished_at: datetime | None = None
    evaluation_source_kind: Literal["run", "assessment_e6"] | None = None
    evaluation_run_id: UUID | None = None
    evaluation_attempt_id: UUID | None = None
    evaluation_identity_id: UUID | None = None
    evaluation_status: str | None = None
    evaluation_started_at: datetime | None = None
    evaluation_finished_at: datetime | None = None
    evaluation_split: str | None = None
    evaluation_purpose: str | None = None
    explainability_run_ids: list[UUID] = Field(default_factory=list)
    explanations: list[dict[str, JsonValue]] = Field(default_factory=list)
    eligible: bool
    eligible_for_stage2_production: bool
    eligibility: Stage2Eligibility
    deployment_readiness: DeploymentReadiness
    model_version_id: UUID | None = None
    model_version_registered: bool
    version_number: int | None = None
    model_name: str | None = None
    architecture: str | None = None
    checkpoint_artifact_id: UUID | None = None
    checkpoint: str | None = None
    checkpoint_sha256: str | None = None
    checkpoint_bytes: int | None = None
    evidence_source: str | None = None
    publication: dict[str, JsonValue] | None = None
    published: bool
    available: bool
    is_stage2_available: bool
    is_stage2_production: bool
    available_for_inference: bool
    stage2_status: Literal["not_available", "production"]
    production_state: Literal["not_eligible", "eligible", "active"]
    next_action: Literal["view_stage2_model", "enable_for_stage2", "unavailable"]
    deployment_id: UUID | None = None
    deployment_status: str | None = None
    environment: str | None = None
    alias: str | None = None
    deployed_at: datetime | None = None
    artifact_sha256: str | None = None
    threshold: float | None = None
    threshold_source: str | None = None
    smoke_status: str | None = None
    blockers: list[Stage2Condition]
    technical_blockers: list[Stage2Condition]
    warnings: list[str]
    package: dict[str, JsonValue] | None = None
