"""Explicit result-chain composition at the Docker boundary."""
from collections.abc import Callable
from uuid import UUID

from sqlalchemy.engine import Engine

from ..persistence.database import get_engine
from ..persistence.result_repository import PostgresResultRepository
from ..results import ResultService
from .contracts import ExecutionContext
from .reporters.docker import DockerRunReporter


def build_docker_run_reporter(
    context: ExecutionContext, *, execution_token: UUID,
    engine_factory: Callable[[], Engine] = get_engine,
) -> DockerRunReporter:
    """Build without IO; trusted context and global token come from the caller.

    The engine factory is not called until report(). The repository owns each
    engine/connection/transaction; no connection or ambient transaction is passed.
    """
    repository = PostgresResultRepository(
        execution_token=execution_token, engine_factory=engine_factory,
    )
    return DockerRunReporter(context, ResultService(repository))
