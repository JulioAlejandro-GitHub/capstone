from functools import lru_cache

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import get_settings


DEFAULT_DATASOURCE = "malaria"


def normalize_sqlalchemy_url(url: str) -> str:
    return url.replace("postgresql://", "postgresql+psycopg://", 1) if url.startswith("postgresql://") else url


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
    return create_engine(normalize_sqlalchemy_url(config["database_url"]), pool_pre_ping=True,
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


def check_connection(datasource: str | None = None) -> dict:
    key = resolve_datasource(datasource)
    with get_engine(key).connect() as connection:
        row = connection.execute(text("SELECT current_database() database, current_user AS user")).mappings().one()
    return {"datasource": key, **dict(row)}
