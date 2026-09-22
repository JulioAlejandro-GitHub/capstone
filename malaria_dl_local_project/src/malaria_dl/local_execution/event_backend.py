"""Backend composition and atomic revalidation of authenticated Local identity."""
from ..persistence.database import get_engine
from ..persistence.result_repository import PostgresResultRepository
from ..results import ResultService
from ..results.errors import WriterNotAuthorized
from .event_context import LocalExecutionContextResolver


class _LocalResultRepository(PostgresResultRepository):
    """Extend authorization only; all acceptance/storage stays in E10.3.

    Revalidation is inside the SAME root transaction, before even a duplicate
    can succeed. No outer transaction or savepoint pretends to confirm commit.
    """
    def __init__(self, resolver, identity, principal, resolved):
        super().__init__(execution_token=resolved.execution_token,
                         engine_factory=resolver.engine_factory)
        self._resolver = resolver
        self._identity = identity
        self._principal = principal
        self._resolved = resolved

    def _authorize(self, connection, context, event):
        super()._authorize(connection, context, event)
        current = self._resolver.resolve_on_connection(
            connection, self._identity, self._principal, lock_job=True)
        if current != self._resolved or current.context != context:
            raise WriterNotAuthorized()


class LocalEventBackend:
    def __init__(self, resolver):
        self.resolver = resolver

    def accept(self, request, principal):
        resolved = self.resolver.resolve(request.identity, principal)
        repository = _LocalResultRepository(self.resolver, request.identity, principal, resolved)
        return ResultService(repository).accept_event(resolved.context, request.event)

    def stream_state(self, identity, principal):
        """Authenticated observation only; never allocates a sequence or writer."""
        from sqlalchemy import text
        from sqlalchemy.exc import SQLAlchemyError
        from ..persistence.execution_record_readers import read_result_events
        from ..results.errors import ResultPersistenceError
        engine = self.resolver.engine_factory()
        try:
            with engine.connect().execution_options(isolation_level='REPEATABLE READ') as c, c.begin():
                c.execute(text('SET TRANSACTION READ ONLY'))
                resolved = self.resolver.resolve_on_connection(c, identity, principal)
                # Also fail before scientific work when E10.3 is not installed.
                c.execute(text('SELECT event_id,event_sequence FROM train_execution_records LIMIT 0'))
                events = read_result_events(c, resolved.context.run_id)
                terminals = [e for e in events if e.event_type.value in ('training_completed','training_failed')]
                if (any(e.sequence != i for i,e in enumerate(events,1))
                        or len(terminals)>1 or (terminals and terminals[-1] != events[-1])):
                    raise ResultPersistenceError()
                legacy = c.execute(text('SELECT EXISTS(SELECT 1 FROM train_execution_records WHERE run_id=:run AND event_id IS NULL)'),
                                   {'run':resolved.context.run_id}).scalar_one()
                return {'run_id':str(resolved.context.run_id),
                        'attempt_id':str(resolved.context.attempt_id) if resolved.context.attempt_id else None,
                        'last_sequence':events[-1].sequence if events else 0,
                        'last_event_id':str(events[-1].event_id) if events else None,
                        'terminal_type':terminals[-1].event_type.value if terminals else None,
                        'legacy_exists':legacy}
        except SQLAlchemyError:
            raise ResultPersistenceError() from None
        finally:
            engine.dispose()


def build_local_event_backend(*, engine_factory=get_engine):
    return LocalEventBackend(LocalExecutionContextResolver(engine_factory))
