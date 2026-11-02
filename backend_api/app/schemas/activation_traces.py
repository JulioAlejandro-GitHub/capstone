"""Activation trace contract: one cell's forward pass through a TRAIN checkpoint."""
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel


class ActivationTraceRequest(BaseModel):
    sample_id: UUID


class ActivationTraceSummary(BaseModel):
    sample_id: UUID
    created_at: str
    label: int | None
    predicted: int | None
    score: float
    persisted_score: float | None
    consistent: bool
    split: str
    bytes: int


class ActivationTraceCatalog(BaseModel):
    available: bool
    reason: str | None
    split: str | None
    items: list[ActivationTraceSummary]
    used_bytes: int
    max_bytes: int


class ActivationTraceCandidate(BaseModel):
    sample_id: UUID
    label: int
    predicted: int
    score: float
    threshold: float


class ActivationTraceStep(BaseModel):
    layer: str
    block: str
    kind: Literal['spatial', 'vector', 'output']
    shape: list[int]
    stats: dict[str, float]
    maps: list[dict[str, Any]] = []
    top: list[dict[str, Any]] = []


class ActivationTrace(ActivationTraceSummary):
    version: str
    training_run_id: UUID
    attempt_id: UUID
    checkpoint_sha256: str
    threshold: float | None
    logit: float
    selection: str
    input_image: str
    steps: list[ActivationTraceStep]
