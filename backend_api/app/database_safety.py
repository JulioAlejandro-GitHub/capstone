from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from app.config import Settings

TEMPORARY_SCHEMA_RE = re.compile(r"^capstone_test_[a-z0-9_]{6,48}$")
SYSTEM_SCHEMAS = {"public", "information_schema", "pg_catalog", "pg_toast"}


def validate_database_url(url: str | None) -> str:
    if url is None or not url.strip():
        raise ValueError("DATABASE_URL es obligatoria y no puede estar vacía")

    normalized = url.strip()
    if normalized.startswith("postgresql://"):
        normalized = normalized.replace(
            "postgresql://", "postgresql+psycopg://", 1
        )
    elif not normalized.startswith("postgresql+psycopg://"):
        raise ValueError(
            "DATABASE_URL debe usar postgresql:// o postgresql+psycopg://"
        )

    try:
        parsed = urlparse(
            normalized.replace("postgresql+psycopg://", "postgresql://", 1)
        )
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError("DATABASE_URL PostgreSQL inválida") from exc

    if not hostname:
        raise ValueError("DATABASE_URL debe incluir el hostname db")
    if hostname != "db":
        raise ValueError("DATABASE_URL solo permite el hostname db")
    if port is not None and port != 5432:
        raise ValueError("DATABASE_URL solo permite el puerto PostgreSQL 5432")
    if not parsed.path.strip("/"):
        raise ValueError("DATABASE_URL debe incluir el nombre de la base")
    return normalized


def database_target(url: str) -> tuple[str, int, str]:
    normalized = validate_database_url(url)
    parsed = urlparse(
        normalized.replace("postgresql+psycopg://", "postgresql://", 1)
    )
    return parsed.hostname, parsed.port or 5432, parsed.path.strip("/")


def redacted_database_target(url: str) -> str:
    host, port, name = database_target(url)
    return f"{host}:{port}/{name}"


def assert_capstone_database(settings: Settings, actual_database: str | None = None) -> str:
    _, _, expected = database_target(settings.database_url)
    if expected in {"postgres", "template0", "template1"}:
        raise RuntimeError("La base de mantenimiento no puede ser la base Capstone")
    if actual_database is not None and actual_database != expected:
        raise RuntimeError("La conexión no corresponde a la base Capstone configurada")
    return expected


def assert_database_drop_forbidden() -> None:
    raise RuntimeError("DROP DATABASE está permanentemente prohibido")


def assert_public_schema_drop_forbidden(schema: str) -> None:
    if schema.lower() == "public":
        raise RuntimeError("DROP SCHEMA public está permanentemente prohibido")


def assert_safe_temporary_schema(settings: Settings, schema: str) -> str:
    if not settings.test_execution or not settings.allow_temporary_test_schema:
        raise RuntimeError("Schema temporal rechazado fuera de una ejecución de pruebas autorizada")
    if schema.lower() in SYSTEM_SCHEMAS or not TEMPORARY_SCHEMA_RE.fullmatch(schema):
        raise RuntimeError("Nombre de schema temporal inseguro")
    return schema


def assert_test_transaction_required(settings: Settings) -> None:
    if not settings.test_execution or settings.test_isolation_mode != "transaction":
        raise RuntimeError("Las pruebas PostgreSQL de escritura requieren transacción con rollback")
