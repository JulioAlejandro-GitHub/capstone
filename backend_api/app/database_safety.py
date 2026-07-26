from __future__ import annotations

from urllib.parse import urlparse

from app.config import Settings


PERSONAL_DATABASES = {"malaria_experiments", "bacteria_experiments", "anemia_experiments", "postgres"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres", "capstone-test-postgres"}


def database_target(url: str) -> tuple[str, int, str]:
    parsed = urlparse(url.replace("postgresql+psycopg://", "postgresql://", 1))
    if parsed.scheme != "postgresql" or not parsed.hostname or not parsed.path.strip("/"):
        raise ValueError("URL PostgreSQL inválida")
    return parsed.hostname, parsed.port or 5432, parsed.path.strip("/")


def redacted_database_target(url: str) -> str:
    host, port, name = database_target(url)
    return f"{host}:{port}/{name}"


def assert_safe_test_database(settings: Settings, *, confirmation: bool) -> str:
    if settings.app_env != "test":
        raise RuntimeError("Operación destructiva rechazada: APP_ENV debe ser test")
    if not settings.test_database_allow_reset:
        raise RuntimeError("Operación destructiva rechazada: TEST_DATABASE_ALLOW_RESET no está habilitado")
    if settings.test_database_require_ephemeral and not confirmation:
        raise RuntimeError("Operación destructiva rechazada: falta confirmación programática de base efímera")
    url = settings.test_database_url or settings.database_url
    host, _, name = database_target(url)
    if name in PERSONAL_DATABASES or "test" not in name.lower():
        raise RuntimeError(f"Base rechazada: {host}/<redacted>; el nombre debe identificar inequívocamente test")
    if host not in LOCAL_HOSTS:
        raise RuntimeError("Host de test no autorizado")
    if settings.database_url != url:
        db_target = database_target(settings.database_url)
        if db_target == database_target(url) and db_target[2] != settings.test_database_name:
            raise RuntimeError("DATABASE_URL y TEST_DATABASE_URL apuntan al mismo destino no autorizado")
    return url
