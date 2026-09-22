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


def build_local_event_backend(*, engine_factory=get_engine):
    return LocalEventBackend(LocalExecutionContextResolver(engine_factory))
