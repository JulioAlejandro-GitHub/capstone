import os
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/malaria_experiments"


def load_environment():
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / ".env.example")


def normalize_database_url(database_url):
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def get_database_url():
    load_environment()

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return normalize_database_url(database_url)

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "malaria_experiments")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"


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
        original_error = getattr(exc, "orig", exc)
        raise RuntimeError(
            "No se pudo conectar a PostgreSQL local. Verifica que PostgreSQL 17.9 "
            "esté ejecutándose en localhost, que la base malaria_experiments exista "
            "y que las credenciales de .env sean correctas. Para crear la base: "
            "createdb -h localhost -p 5432 -U postgres malaria_experiments. "
            f"Detalle original: {original_error}"
        ) from exc
    except SQLAlchemyError as exc:
        raise RuntimeError(f"Error SQLAlchemy al acceder a PostgreSQL: {exc}") from exc


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
