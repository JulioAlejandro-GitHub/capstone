"""Storage-independent atomic state port for the single scientific emitter."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from .contracts import RunEvent, RunEventType

TERMINALS = (RunEventType.TRAINING_COMPLETED, RunEventType.TRAINING_FAILED)


class JournalError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class EventState:
    next_sequence: int = 1
    pending: RunEvent | None = None
    closed: bool = False
    terminal_type: RunEventType | None = None

    def validate(self, run_id: UUID, attempt_id: UUID | None):
        if (type(self.next_sequence) is not int or self.next_sequence < 1
                or type(self.closed) is not bool
                or (self.closed != (self.terminal_type in TERMINALS))
                or (not self.closed and self.terminal_type is not None)
                or (self.closed and (self.pending is not None or self.next_sequence < 2))):
            raise JournalError('EVENT_JOURNAL_STATE_INVALID')
        if self.pending is not None and (
                not isinstance(self.pending, RunEvent) or self.pending.run_id != run_id
                or self.pending.attempt_id != attempt_id
                or self.pending.sequence != self.next_sequence
                or self.pending.event_type is RunEventType.HEARTBEAT):
            raise JournalError('EVENT_JOURNAL_PENDING_INVALID')


class EventJournal(ABC):
    @abstractmethod
    def load(self, run_id: UUID, attempt_id: UUID | None) -> EventState:
        """Load validated state for the exact bound stream, failing closed."""

    @abstractmethod
    def transition(self, expected: EventState, updated: EventState) -> None:
        """Atomically compare and durably replace the entire state before return.

        Failure may mean commit uncertainty. The caller must stop and reopen,
        never overwrite uncertain state from its in-memory copy.
        """
