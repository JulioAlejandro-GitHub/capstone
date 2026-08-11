"""Database construction without scientific-data bootstrap side effects."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine


def create_postgresql_engine(database_url: str, **kwargs: object) -> Engine:
    """Create an engine and reject non-PostgreSQL persistence targets."""
    engine = create_engine(database_url, **kwargs)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        raise ValueError("The dataset split persistence layer requires PostgreSQL")
    return engine
