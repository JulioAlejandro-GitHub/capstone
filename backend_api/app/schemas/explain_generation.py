"""Closed HTTP contracts: identifiers and scientific options, never commands."""
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

Method = Literal['gradcam', 'lime', 'shap']


class ExplainRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_attempt_id: UUID
    sample_id: UUID
    methods: list[Method] = Field(default_factory=lambda: ['gradcam'], min_length=1, max_length=3)
    class_id: Literal[0, 1] = 1
    num_samples: int = Field(default=1000, ge=1000, le=5000, strict=True)
    background_sample_id: UUID | None = None

    @field_validator('class_id', mode='before')
    @classmethod
    def integer_class(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError('class_id must be 0 or 1')
        return value


class ExplainMethodState(BaseModel):
    method: Method
    state: Literal['not_executed', 'pending', 'running', 'completed', 'failed']
    attempt_id: UUID | None = None
    identity_id: UUID | None = None
    operation_id: UUID | None = None
    error: str | None = None
    detail: dict[str, Any] | None = None
    artifacts: list[dict[str, Any]] = Field(default_factory=list)


class ExplainState(BaseModel):
    training_run_id: UUID
    dataset_version_id: UUID
    sample_id: UUID
    authorized: bool
    methods: list[ExplainMethodState]


class ExplainOperation(BaseModel):
    method: Method
    state: Literal['pending', 'running', 'completed'] | None = None
    operation_id: UUID | None = None
    attempt_id: UUID | None = None
    error: str | None = None


class ExplainSubmission(BaseModel):
    operations: list[ExplainOperation]


class PreparedMethod(BaseModel):
    method: Method
    sample_ids: list[UUID]
    specification: dict[str, Any]


class ExplainPreparation(BaseModel):
    sample_id: UUID
    training_run_id: UUID
    methods: list[PreparedMethod]
