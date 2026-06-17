from functools import lru_cache
from os import getenv

from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


load_dotenv()


DEFAULT_DATASOURCE = "malaria"

DATASOURCE_CONFIG = {
    "malaria": {
        "label": "Malaria",
        "domain": "Parasitos",
        "database_url": getenv(
            "MALARIA_DATABASE_URL",
            "postgresql://julio@localhost:5432/malaria_experiments",
        ),
        "enabled": getenv("ENABLE_MALARIA_DATASOURCE", "true").lower() == "true",
    },
    "bacteria": {
        "label": "Bacterias / Streptococcus",
        "domain": "Bacterias",
        "database_url": getenv(
            "BACTERIA_DATABASE_URL",
            "postgresql://julio@localhost:5432/bacteria_experiments",
        ),
        "enabled": getenv("ENABLE_BACTERIA_DATASOURCE", "false").lower() == "true",
    },
    "anemia": {
        "label": "Anemia",
        "domain": "Enfermedad",
        "database_url": getenv(
            "ANEMIA_DATABASE_URL",
            "postgresql://julio@localhost:5432/anemia_experiments",
        ),
        "enabled": getenv("ENABLE_ANEMIA_DATASOURCE", "false").lower() == "true",
    },
}


def normalize_sqlalchemy_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def list_datasources():
    return [
        {
            "key": key,
            "label": config["label"],
            "domain": config["domain"],
            "enabled": config["enabled"],
            "database": config["database_url"].rsplit("/", maxsplit=1)[-1],
        }
        for key, config in DATASOURCE_CONFIG.items()
    ]


def resolve_datasource(datasource: str | None) -> str:
    key = datasource or DEFAULT_DATASOURCE
    if key not in DATASOURCE_CONFIG:
        raise HTTPException(status_code=404, detail=f"Datasource no soportado: {key}")
    if not DATASOURCE_CONFIG[key]["enabled"]:
        raise HTTPException(status_code=400, detail=f"Datasource inactivo: {key}")
    return key


@lru_cache
def get_engine(datasource: str) -> Engine:
    config = DATASOURCE_CONFIG[datasource]
    return create_engine(
        normalize_sqlalchemy_url(config["database_url"]),
        pool_pre_ping=True,
        future=True,
    )


def fetch_all(datasource: str | None, sql: str, params: dict | None = None):
    key = resolve_datasource(datasource)
    with get_engine(key).connect() as connection:
        return connection.execute(text(sql), params or {}).mappings().all()


def fetch_one(datasource: str | None, sql: str, params: dict | None = None):
    key = resolve_datasource(datasource)
    with get_engine(key).connect() as connection:
        return connection.execute(text(sql), params or {}).mappings().first()


def check_connection(datasource: str | None = None) -> dict:
    key = resolve_datasource(datasource)
    with get_engine(key).connect() as connection:
        row = connection.execute(
            text("SELECT current_database() AS database, current_user AS user")
        ).mappings().one()
        return {"datasource": key, **dict(row)}

