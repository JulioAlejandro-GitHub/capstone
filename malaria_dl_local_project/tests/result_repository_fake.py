"""Test-only port adapter: global lock, staged append, simulated commit failures."""
from contextlib import contextmanager
from threading import RLock
from typing import Iterator
from uuid import UUID

from src.malaria_dl.execution.contracts import ExecutionContext, RunEvent
from src.malaria_dl.results.errors import ResultPersistenceError, WriterNotAuthorized
from src.malaria_dl.results.models import AcceptanceState
from src.malaria_dl.results.repository import EventAcceptanceScope, ResultRepository


class _Scope(EventAcceptanceScope):
    def __init__(self, state: AcceptanceState, repository: "FakeResultRepository"):
        self._state = state
        self._repository = repository
        self.active = True
        self.staged = False

    @property
    def state(self) -> AcceptanceState:
        assert self.active
        self._repository.fail_at("read")
        return self._state

    def append(self) -> None:
        assert self.active and not self.staged
        self._repository.fail_at("append")
        self.staged = True


class FakeResultRepository(ResultRepository):
    def __init__(self):
        self._lock = RLock()
        self._authorized: dict[UUID, ExecutionContext] = {}
        self._events: dict[UUID, RunEvent] = {}
        self._sequences: dict[tuple[UUID, int], RunEvent] = {}
        self._last: dict[UUID, int] = {}
        self.failure: str | None = None
        self.scope_calls = 0
        self.append_count = 0

    @property
    def events(self) -> tuple[RunEvent, ...]:
        with self._lock:
            return tuple(self._events.values())

    def authorize(self, context: ExecutionContext) -> None:
        with self._lock:
            self._authorized[context.run_id] = context

    def revoke(self, run_id: UUID) -> None:
        with self._lock:
            self._authorized.pop(run_id, None)

    def seed(self, event: RunEvent) -> None:
        """Simulate preexisting committed evidence without incrementing writes."""
        with self._lock:
            self._store(event)

    def set_watermark(self, run_id: UUID, sequence: int) -> None:
        """Simulate incomplete historical state to exercise fail-closed stale logic."""
        with self._lock:
            self._last[run_id] = sequence

    def fail_at(self, point: str) -> None:
        if self.failure == point:
            raise ResultPersistenceError()

    def _store(self, event: RunEvent) -> None:
        self._events[event.event_id] = event
        self._sequences[event.run_id, event.sequence] = event
        self._last[event.run_id] = event.sequence

    @contextmanager
    def acceptance_scope(
        self, context: ExecutionContext, event: RunEvent,
    ) -> Iterator[EventAcceptanceScope]:
        with self._lock:
            self.scope_calls += 1
            self.fail_at("enter")
            if self._authorized.get(context.run_id) != context:
                raise WriterNotAuthorized()
            scope = _Scope(AcceptanceState(
                existing_event=self._events.get(event.event_id),
                sequence_event=self._sequences.get((event.run_id, event.sequence)),
                last_sequence=self._last.get(event.run_id, 0),
            ), self)
            try:
                yield scope
                self.fail_at("commit")
                if scope.staged:
                    self._store(event)
                    self.append_count += 1
                self.fail_at("ack")
            finally:
                scope.active = False
