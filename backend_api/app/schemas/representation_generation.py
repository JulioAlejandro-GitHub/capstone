"""Closed HTTP contracts for REPRESENT generated from the report: identifiers only, never commands."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict

RepresentStateName = Literal['not_executed', 'pending', 'running', 'completed', 'failed']


class RepresentRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    # The verified EVALUATE whose model, population, split and threshold are represented.
    source_attempt_id: UUID
    # Discriminates REPRESENT rows from EXPLAIN rows in the shared host GPU queue.
    operation: Literal['represent'] = 'represent'


class RepresentState(BaseModel):
    source_attempt_id: UUID
    training_run_id: UUID
    authorized: bool
    state: RepresentStateName
    attempt_id: UUID | None = None
    operation_id: UUID | None = None
    error: str | None = None


class RepresentSubmission(BaseModel):
    state: Literal['pending', 'running', 'completed']
    attempt_id: UUID | None = None
    operation_id: UUID | None = None
