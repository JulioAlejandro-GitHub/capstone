import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError


from src.malaria_dl.common.paths import PROJECT_ROOT
DEFAULT_DATABASE_URL = "postgresql+psycopg://capstone_local:local-only@localhost:55432/capstone_local"


def load_environment():
    load_dotenv(PROJECT_ROOT / ".env")


def normalize_database_url(database_url):
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def get_database_url():
    load_environment()

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return normalize_database_url(database_url)

    if os.getenv("APP_ENV", "local") != "local":
        raise RuntimeError("DATABASE_URL es obligatoria fuera del entorno local")
    host = os.getenv("DATABASE_HOST", os.getenv("DB_HOST", "localhost"))
    port = os.getenv("DATABASE_PORT", os.getenv("DB_PORT", "55432"))
    name = os.getenv("DATABASE_NAME", os.getenv("DB_NAME", "capstone_local"))
    user = os.getenv("DATABASE_USER", os.getenv("DB_USER", "capstone_local"))
    password = os.getenv("DATABASE_PASSWORD", os.getenv("DB_PASSWORD", "local-only"))
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
            "No se pudo conectar al PostgreSQL configurado. Verifica DATABASE_URL "
            "y usa el entorno efímero documentado para pruebas. "
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
