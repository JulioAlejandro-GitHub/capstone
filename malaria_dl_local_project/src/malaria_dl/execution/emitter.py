"""One scientific event stream per run, with optional abstract durable state."""
from datetime import datetime, timezone
from threading import Lock
from uuid import UUID, uuid4

from .contracts import RUN_EVENT_SCHEMA_VERSION, RunEvent, RunEventType, RunReporter
from .journal import EventJournal, EventState, JournalError, TERMINALS


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


class RunEventEmitter:
    """Own identity, sequence and pending for a NEW, single-producer run stream.

    Without a journal, state lives only in this object (Docker). A supplied
    abstract journal restores exact state; there is no remote watermark inference.
    Overlapping/reentrant deliveries fail rather than sending the same slot twice.
    """
    def __init__(self, reporter: RunReporter, *, run_id: UUID, attempt_id: UUID | None = None,
                 journal: EventJournal | None = None, prepare_payload=None):
        if not isinstance(run_id, UUID) or (attempt_id is not None and not isinstance(attempt_id, UUID)):
            raise TypeError('run_id and optional attempt_id must be UUID')
        self._reporter = reporter
        self._run_id = run_id
        self._attempt_id = attempt_id
        self._journal = journal
        self._prepare_payload = prepare_payload
        self._journal_failed = False
        self._state = journal.load(run_id, attempt_id) if journal is not None else EventState()
        self._state.validate(run_id, attempt_id)
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
            if self._journal_failed:
                raise JournalError('EVENT_JOURNAL_REOPEN_REQUIRED')
            if self.closed:
                raise EventStreamClosed('EVENT_STREAM_CLOSED')
            if self.pending is not None:
                raise PendingEventExists('PENDING_EVENT_EXISTS')
            if event_type is RunEventType.HEARTBEAT:
                raise OperationalHeartbeatExcluded('OPERATIONAL_HEARTBEAT_EXCLUDED')
            if self._prepare_payload is not None:
                payload = self._prepare_payload(payload)
            event = RunEvent(event_id=uuid4(), run_id=self._run_id, attempt_id=self._attempt_id,
                sequence=self.next_sequence, occurred_at=datetime.now(timezone.utc),
                schema_version=RUN_EVENT_SCHEMA_VERSION, event_type=event_type, payload=payload)
            previous = self._state
            self._state = EventState(next_sequence=event.sequence, pending=event)
            self._persist(previous, self._state)
            return self._report_pending()
        finally:
            self._delivery.release()

    def retry_pending(self) -> RunEvent:
        if not self._delivery.acquire(blocking=False):
            raise EventEmissionInProgress('EVENT_EMISSION_IN_PROGRESS')
        try:
            if self._journal_failed:
                raise JournalError('EVENT_JOURNAL_REOPEN_REQUIRED')
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
        closed = event.event_type in TERMINALS
        updated = EventState(next_sequence=event.sequence + 1, closed=closed,
                             terminal_type=event.event_type if closed else None)
        self._persist(self._state, updated)
        self._state = updated
        return event

    def _persist(self, previous, updated):
        if self._journal is not None:
            try:
                self._journal.transition(previous, updated)
            except BaseException:
                self._journal_failed = True
                raise
