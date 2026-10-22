"""EXPLAIN HTTP catalog, using the canonical scientific repository and SQL selectors."""
from contextlib import contextmanager
from typing import Iterator
from sqlalchemy.engine import Connection
from app.db import get_primary_engine
from app.repositories.explain_queries import ExplainQueries
from src.malaria_dl.campaigns.repository import execute


@contextmanager
def assessment_scope(readonly: bool = False) -> Iterator[Connection]:
    with get_primary_engine().begin() as connection:
        if readonly:
            execute(connection, 'SET TRANSACTION READ ONLY')
        yield connection


class ExplainRepository(ExplainQueries):
    def __init__(self) -> None:
        super().__init__(scope=assessment_scope)
