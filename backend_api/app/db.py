from contextlib import contextmanager
from functools import lru_cache

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import get_settings
from app.database_safety import validate_database_url


DEFAULT_DATASOURCE = "malaria"
READ_ONLY_STATEMENT_TIMEOUT_MS = 10_000
READ_ONLY_LOCK_TIMEOUT_MS = 2_000


def normalize_sqlalchemy_url(url: str) -> str:
    return validate_database_url(url)


def _datasources() -> dict:
    settings = get_settings()
    return {
        "malaria": {"label": "Malaria", "domain": "Parasitos", "database_url": settings.database_url, "enabled": True},
    }


DATASOURCE_CONFIG = _datasources()


def list_datasources():
    return [{"key": key, "label": value["label"], "domain": value["domain"], "enabled": value["enabled"],
             "database": value["database_url"].rsplit("/", 1)[-1].split("?", 1)[0]}
            for key, value in _datasources().items()]


def resolve_datasource(datasource: str | None) -> str:
    key = datasource or DEFAULT_DATASOURCE
    if key not in _datasources():
        raise HTTPException(404, f"Datasource no soportado: {key}")
    return key


@lru_cache
def get_engine(datasource: str) -> Engine:
    settings = get_settings()
    config = _datasources()[datasource]
    return create_engine(config["database_url"], pool_pre_ping=True,
                         pool_size=settings.database_pool_max_size,
                         connect_args={"connect_timeout": settings.database_connect_timeout},
                         echo=settings.sql_logging, future=True)


def get_primary_engine() -> Engine:
    return get_engine(DEFAULT_DATASOURCE)


def fetch_all(datasource: str | None, sql: str, params: dict | None = None):
    with get_engine(resolve_datasource(datasource)).connect() as connection:
        return connection.execute(text(sql), params or {}).mappings().all()


def fetch_one(datasource: str | None, sql: str, params: dict | None = None):
    with get_engine(resolve_datasource(datasource)).connect() as connection:
        return connection.execute(text(sql), params or {}).mappings().first()


@contextmanager
def read_only_transaction(datasource: str | None):
    """Yield one bounded PostgreSQL transaction that cannot write."""
    key = resolve_datasource(datasource)
    with get_engine(key).connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            connection.execute(
                text(
                    "SET LOCAL statement_timeout = "
                    f"'{READ_ONLY_STATEMENT_TIMEOUT_MS}ms'"
                )
            )
            connection.execute(
                text(
                    "SET LOCAL lock_timeout = "
                    f"'{READ_ONLY_LOCK_TIMEOUT_MS}ms'"
                )
            )
            yield connection
        finally:
            if transaction.is_active:
                transaction.rollback()


def check_connection(datasource: str | None = None) -> dict:
    key = resolve_datasource(datasource)
    with get_engine(key).connect() as connection:
        row = connection.execute(text("SELECT current_database() database, current_user AS user")).mappings().one()
    return {"datasource": key, **dict(row)}
