"""Immutable acceptance results and the protected state needed for a decision."""
from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from ..execution.contracts import RunEvent


class EventAcceptanceStatus(str, Enum):
    ACCEPTED = "accepted"
    DUPLICATE_ACCEPTED = "duplicate_accepted"


@dataclass(frozen=True, slots=True, kw_only=True)
class EventAcceptance:
    status: EventAcceptanceStatus
    run_id: UUID
    event_id: UUID
    sequence: int

    def __post_init__(self) -> None:
        if not isinstance(self.status, EventAcceptanceStatus):
            raise TypeError("status must be EventAcceptanceStatus")
        if not isinstance(self.run_id, UUID) or not isinstance(self.event_id, UUID):
            raise TypeError("run_id and event_id must be UUID")
        if type(self.sequence) is not int or self.sequence < 1:
            raise ValueError("sequence must be an integer >= 1")


@dataclass(frozen=True, slots=True, kw_only=True)
class AcceptanceState:
    """Snapshot held stable until scope exit; empty streams have last_sequence=0.

    existing_event: lookup by event_id across the repository.
    sequence_event: lookup by (run_id, sequence) of the candidate.
    last_sequence: committed high-water mark for that run, never inferred from time.
    """

    existing_event: RunEvent | None
    sequence_event: RunEvent | None
    last_sequence: int

    def __post_init__(self) -> None:
        if type(self.last_sequence) is not int or self.last_sequence < 0:
            raise ValueError("last_sequence must be an integer >= 0")
        for value in (self.existing_event, self.sequence_event):
            if value is not None and not isinstance(value, RunEvent):
                raise TypeError("stored events must be RunEvent or None")
