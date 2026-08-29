import os
from contextlib import contextmanager
from urllib.parse import urlparse

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError


from src.malaria_dl.common.paths import PROJECT_ROOT


def load_environment():
    load_dotenv(PROJECT_ROOT / ".env")


def normalize_database_url(database_url):
    if database_url is None or not database_url.strip():
        raise RuntimeError("DATABASE_URL es obligatoria y no puede estar vacía")

    normalized = database_url.strip()
    if normalized.startswith("postgresql://"):
        normalized = normalized.replace(
            "postgresql://", "postgresql+psycopg://", 1
        )
    elif not normalized.startswith("postgresql+psycopg://"):
        raise RuntimeError(
            "DATABASE_URL debe usar postgresql:// o postgresql+psycopg://"
        )

    try:
        parsed = urlparse(
            normalized.replace("postgresql+psycopg://", "postgresql://", 1)
        )
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise RuntimeError("DATABASE_URL PostgreSQL inválida") from exc

    if not hostname:
        raise RuntimeError("DATABASE_URL debe incluir el hostname db")
    if hostname != "db":
        raise RuntimeError("DATABASE_URL solo permite el hostname db")
    if port is not None and port != 5432:
        raise RuntimeError("DATABASE_URL solo permite el puerto PostgreSQL 5432")
    if not parsed.path.strip("/"):
        raise RuntimeError("DATABASE_URL debe incluir el nombre de la base")
    return normalized


def get_database_url():
    load_environment()

    return normalize_database_url(os.getenv("DATABASE_URL"))


def get_engine(echo=False):
    return create_engine(
        get_database_url(),
        echo=echo,
        pool_pre_ping=True,
        future=True,
    )


@contextmanager
def get_connection():
    engine = get_engine()
    try:
        with engine.begin() as connection:
            yield connection
    except OperationalError as exc:
        raise RuntimeError(
            "No se pudo conectar al PostgreSQL configurado. Verifica DATABASE_URL "
            "y el servicio Docker Compose db."
        ) from exc
    except SQLAlchemyError as exc:
        raise RuntimeError("Error SQLAlchemy al acceder a PostgreSQL") from exc


def test_connection():
    with get_connection() as connection:
        result = connection.execute(
            text(
                """
                SELECT
                    current_database() AS database_name,
                    current_user AS user_name,
                    version() AS postgres_version
                """
            )
        ).mappings().one()
    return dict(result)
