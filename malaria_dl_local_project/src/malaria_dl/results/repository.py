"""Atomic application port; no concrete storage implementation."""
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager

from ..execution.contracts import ExecutionContext, RunEvent
from .models import AcceptanceState
from .training import TrainingResultsV1


class EventAcceptanceScope(ABC):
    """Bound to exactly one context/event; valid only inside acceptance_scope."""

    @property
    @abstractmethod
    def state(self) -> AcceptanceState:
        """Return the authorized, protected acceptance snapshot."""
        raise NotImplementedError

    @abstractmethod
    def append(self) -> None:
        """Stage the bound event unchanged, once; confirmation occurs on scope exit."""
        raise NotImplementedError

    def project_training_result(self, result: TrainingResultsV1) -> None:
        """Stage the unique final result atomically with the bound new event.

        Preserve unrelated output. A preexisting final result is a conflict,
        including identical science under another event identity. Legacy ports
        remain usable for other events; unsupported projection fails closed.
        """
        from .errors import ResultPersistenceError
        raise ResultPersistenceError()


class ResultRepository(ABC):
    @abstractmethod
    def acceptance_scope(
        self, context: ExecutionContext, event: RunEvent,
    ) -> AbstractContextManager[EventAcceptanceScope]:
        """Authorize and serialize an entire acceptance decision atomically.

        Before yielding: validate current writer/owner, active state, run/attempt
        and authoritative context identity, or raise WriterNotAuthorized. This
        applies even to retries. Keep authorization protected until exit.

        Hold event_id uniqueness across runs and per-run sequence protection
        from snapshot reads through append and commit. No separate unprotected
        checks, stale snapshots or external uncommitted transaction may suffice.

        A normal exit confirms commit (or a read-only duplicate). Any body/write/
        commit failure must propagate; roll back uncommitted work and never
        suppress errors. Translate storage failures to ResultPersistenceError.
        An uncertain commit may already be durable: retry the same event.

        Preserve the complete event, canonical numeric distinctions, global
        event_id identity, append-only evidence and sequence high-water mark.
        Adapters must not assign/replace identity, sequence or timestamps.
        """
        raise NotImplementedError
