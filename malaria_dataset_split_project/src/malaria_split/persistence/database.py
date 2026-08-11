"""Database construction without scientific-data bootstrap side effects."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine


def create_postgresql_engine(database_url: str, **kwargs: object) -> Engine:
    """Create an engine and reject non-PostgreSQL persistence targets."""
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg://", 1
        )
    engine = create_engine(database_url, **kwargs)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        raise ValueError("The dataset split persistence layer requires PostgreSQL")
    return engine
