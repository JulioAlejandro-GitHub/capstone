"""Versioned events; producers retain identity and sequence across retries."""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import UUID

from ._json import JSONObject, JSONValue, freeze_object, thaw

RUN_EVENT_SCHEMA_VERSION = "run_event_v1"


class RunEventType(str, Enum):
    HEARTBEAT = "heartbeat"
    EPOCH_COMPLETED = "epoch_completed"
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    ARTIFACT_PREPARED = "artifact_prepared"
    ARTIFACT_CREATED = "artifact_created"
    PREDICTIONS_COMPLETED = "predictions_completed"
    SELECTION_COMPLETED = "selection_completed"
    CALIBRATION_COMPLETED = "calibration_completed"
    EVALUATION_COMPLETED = "evaluation_completed"
    TRAINING_COMPLETED = "training_completed"
    TRAINING_FAILED = "training_failed"


@dataclass(frozen=True, slots=True, kw_only=True)
class RunEvent:
    event_id: UUID
    run_id: UUID
    sequence: int
    event_type: RunEventType
    occurred_at: datetime
    payload: JSONObject
    attempt_id: UUID | None = None
    schema_version: Literal["run_event_v1"] = RUN_EVENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("event_id", "run_id"):
            if not isinstance(getattr(self, name), UUID):
                raise TypeError(f"{name} must be UUID")
        if self.attempt_id is not None and not isinstance(self.attempt_id, UUID):
            raise TypeError("attempt_id must be UUID or None")
        if type(self.sequence) is not int or self.sequence < 1:
            raise ValueError("sequence must be an integer >= 1 within a run")
        if not isinstance(self.event_type, RunEventType):
            raise TypeError("event_type must be RunEventType")
        if type(self.schema_version) is not str or self.schema_version != RUN_EVENT_SCHEMA_VERSION:
            raise ValueError("unsupported event schema_version")
        if not isinstance(self.occurred_at, datetime):
            raise TypeError("occurred_at must be datetime")
        if self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")
        object.__setattr__(self, "occurred_at", self.occurred_at.astimezone(timezone.utc))
        object.__setattr__(self, "payload", freeze_object(self.payload))

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a detached JSON-compatible envelope, with UTC ISO-8601 time."""
        return {
            "event_id": str(self.event_id), "run_id": str(self.run_id),
            "attempt_id": str(self.attempt_id) if self.attempt_id is not None else None,
            "sequence": self.sequence, "event_type": self.event_type.value,
            "schema_version": self.schema_version,
            "occurred_at": self.occurred_at.isoformat(), "payload": thaw(self.payload),
        }

    @classmethod
    def from_dict(cls, value: dict[str, JSONValue]) -> "RunEvent":
        """Parse the explicit v1 envelope; unknown/missing fields are errors."""
        fields = {"event_id", "run_id", "attempt_id", "sequence", "event_type",
                  "schema_version", "occurred_at", "payload"}
        if type(value) is not dict or value.keys() != fields:
            raise ValueError("event envelope must contain exactly the v1 fields")
        for name in ("event_id", "run_id", "event_type", "schema_version", "occurred_at"):
            if type(value[name]) is not str:
                raise TypeError(f"{name} must be a string in the envelope")
        attempt = value["attempt_id"]
        if attempt is not None and type(attempt) is not str:
            raise TypeError("attempt_id must be a UUID string or null")
        return cls(
            event_id=UUID(value["event_id"]), run_id=UUID(value["run_id"]),
            attempt_id=UUID(attempt) if attempt is not None else None,
            sequence=value["sequence"], event_type=RunEventType(value["event_type"]),
            schema_version=value["schema_version"],
            occurred_at=datetime.fromisoformat(value["occurred_at"]), payload=value["payload"],
        )
