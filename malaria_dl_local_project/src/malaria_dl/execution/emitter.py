"""One in-memory scientific event stream per run; no runtime integration."""
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from uuid import UUID, uuid4

from .contracts import RUN_EVENT_SCHEMA_VERSION, RunEvent, RunEventType, RunReporter


class PendingEventExists(RuntimeError):
    pass


class NoPendingEvent(RuntimeError):
    pass


class EventStreamClosed(RuntimeError):
    pass


class EventEmissionInProgress(RuntimeError):
    pass


class OperationalHeartbeatExcluded(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class _State:
    next_sequence: int = 1
    pending: RunEvent | None = None
    closed: bool = False


class RunEventEmitter:
    """Own identity, sequence and pending for a NEW, single-producer run stream.

    State lives only in this object. Construction is NOT recovery of an existing
    stream. There is no durable journal or remote watermark inference here.
    Overlapping/reentrant deliveries fail rather than sending the same slot twice.
    """
    def __init__(self, reporter: RunReporter, *, run_id: UUID, attempt_id: UUID | None = None):
        if not isinstance(run_id, UUID) or (attempt_id is not None and not isinstance(attempt_id, UUID)):
            raise TypeError('run_id and optional attempt_id must be UUID')
        self._reporter = reporter
        self._run_id = run_id
        self._attempt_id = attempt_id
        self._state = _State()
        self._delivery = Lock()

    @property
    def next_sequence(self) -> int:
        return self._state.next_sequence

    @property
    def pending(self) -> RunEvent | None:
        return self._state.pending

    @property
    def closed(self) -> bool:
        return self._state.closed

    def emit(self, event_type: RunEventType, payload) -> RunEvent:
        if not self._delivery.acquire(blocking=False):
            raise EventEmissionInProgress('EVENT_EMISSION_IN_PROGRESS')
        try:
            if self.closed:
                raise EventStreamClosed('EVENT_STREAM_CLOSED')
            if self.pending is not None:
                raise PendingEventExists('PENDING_EVENT_EXISTS')
            if event_type is RunEventType.HEARTBEAT:
                raise OperationalHeartbeatExcluded('OPERATIONAL_HEARTBEAT_EXCLUDED')
            event = RunEvent(event_id=uuid4(), run_id=self._run_id, attempt_id=self._attempt_id,
                sequence=self.next_sequence, occurred_at=datetime.now(timezone.utc),
                schema_version=RUN_EVENT_SCHEMA_VERSION, event_type=event_type, payload=payload)
            self._state = _State(next_sequence=event.sequence, pending=event)
            return self._report_pending()
        finally:
            self._delivery.release()

    def retry_pending(self) -> RunEvent:
        if not self._delivery.acquire(blocking=False):
            raise EventEmissionInProgress('EVENT_EMISSION_IN_PROGRESS')
        try:
            if self.closed:
                raise EventStreamClosed('EVENT_STREAM_CLOSED')
            if self.pending is None:
                raise NoPendingEvent('NO_PENDING_EVENT')
            return self._report_pending()
        finally:
            self._delivery.release()

    def _report_pending(self) -> RunEvent:
        event = self._state.pending
        self._reporter.report(event)
        # Only a normal return acknowledges. Every exception, including an
        # interruption or lost ACK after commit, leaves the SAME immutable event.
        # Replace the entire state at once: no intermediate clear-before-advance.
        self._state = _State(next_sequence=event.sequence + 1, closed=event.event_type in (
            RunEventType.TRAINING_COMPLETED, RunEventType.TRAINING_FAILED))
        return event
