"""Per-epoch VAL score of every cell, as recorded by one TRAIN."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel


class TrajectoryEpoch(BaseModel):
    epoch: int
    phase: str


class TrajectorySample(BaseModel):
    sample: str
    label: int
    sample_id: UUID | None


class TrainingTrajectories(BaseModel):
    training_run_id: UUID
    state: Literal['available', 'missing', 'inconsistent']
    issues: list[str]
    epochs: list[TrajectoryEpoch]
    samples: list[TrajectorySample]
    scores: list[list[float | None]]
    training_threshold: float
    evaluation_attempt_id: UUID | None
