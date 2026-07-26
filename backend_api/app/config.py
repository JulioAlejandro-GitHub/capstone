from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


TRUE_VALUES = {"1", "true", "yes", "on"}


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in TRUE_VALUES


def _int(name: str, default: int, minimum: int = 0) -> int:
    value = int(os.getenv(name, str(default)))
    if value < minimum:
        raise ValueError(f"{name} debe ser >= {minimum}")
    return value


def _origins(value: str) -> tuple[str, ...]:
    origins = tuple(item.strip().rstrip("/") for item in value.split(",") if item.strip())
    if any(item == "*" or urlparse(item).scheme not in {"http", "https"} for item in origins):
        raise ValueError("CORS_ORIGINS debe contener orígenes HTTP(S) explícitos")
    return origins


@dataclass(frozen=True)
class Settings:
    app_env: str
    app_name: str
    app_version: str
    debug: bool
    log_level: str
    log_format: str
    api_prefix: str
    frontend_origin: str
    cors_origins: tuple[str, ...]
    database_url: str
    database_pool_min_size: int
    database_pool_max_size: int
    database_connect_timeout: int
    test_database_url: str | None
    test_database_name: str
    test_database_allow_reset: bool
    test_database_require_ephemeral: bool
    auth_mode: str
    jwt_secret: str | None
    jwt_algorithm: str
    jwt_access_token_expire_minutes: int
    password_hash_scheme: str
    allow_insecure_local_auth: bool
    storage_provider: str
    storage_root: Path
    artifacts_root: Path
    max_upload_size_bytes: int
    correlation_id_header: str
    include_stacktrace: bool
    sql_logging: bool
    request_logging: bool

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.getenv("APP_ENV", "local").strip().lower()
        if env not in {"local", "test", "demo"}:
            raise ValueError("APP_ENV debe ser local, test o demo")
        auth_mode = os.getenv("AUTH_MODE", "local_jwt").strip().lower()
        insecure = _bool("ALLOW_INSECURE_LOCAL_AUTH")
        if auth_mode not in {"local_jwt", "disabled"}:
            raise ValueError("AUTH_MODE debe ser local_jwt o disabled")
        if auth_mode == "disabled" and (env != "local" or not insecure):
            raise ValueError("AUTH_MODE=disabled sólo se permite en local con autorización explícita")
        secret = os.getenv("JWT_SECRET")
        if env == "demo" and (
            auth_mode == "disabled"
            or not secret
            or secret.lower() in {"change-me", "changeme", "secret", "example"}
            or len(secret) < 32
        ):
            raise ValueError("demo requiere autenticación y JWT_SECRET seguro (>=32 caracteres)")
        if auth_mode == "local_jwt" and not secret:
            if env != "local":
                raise ValueError("JWT_SECRET es obligatorio fuera de local")
            secret = "local-only-insecure-secret-change-before-demo"
        database_url = os.getenv("DATABASE_URL", "").strip()
        if not database_url and env == "local":
            database_url = "postgresql://capstone_local:local-only@localhost:55432/capstone_local"
        if not database_url:
            raise ValueError("DATABASE_URL es obligatorio fuera de local; no existe una base personal por defecto")
        pool_min = _int("DATABASE_POOL_MIN_SIZE", 1, 1)
        pool_max = _int("DATABASE_POOL_MAX_SIZE", 5, 1)
        if pool_min > pool_max:
            raise ValueError("DATABASE_POOL_MIN_SIZE no puede superar DATABASE_POOL_MAX_SIZE")
        storage_root = Path(os.getenv("STORAGE_ROOT", "./var/storage")).expanduser()
        artifacts_root = Path(os.getenv("ARTIFACTS_ROOT", "./var/artifacts")).expanduser()
        if env == "demo" and (not storage_root.is_absolute() or not artifacts_root.is_absolute()):
            raise ValueError("demo requiere STORAGE_ROOT y ARTIFACTS_ROOT absolutos")
        return cls(
            app_env=env,
            app_name=os.getenv("APP_NAME", "Capstone Experiments API"),
            app_version=os.getenv("APP_VERSION", "0.3.0"),
            debug=_bool("DEBUG"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            log_format=os.getenv("LOG_FORMAT", "json" if env != "local" else "text"),
            api_prefix=os.getenv("API_PREFIX", "/api/v1").rstrip("/"),
            frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").rstrip("/"),
            cors_origins=_origins(os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")),
            database_url=database_url,
            database_pool_min_size=pool_min,
            database_pool_max_size=pool_max,
            database_connect_timeout=_int("DATABASE_CONNECT_TIMEOUT", 5, 1),
            test_database_url=os.getenv("TEST_DATABASE_URL"),
            test_database_name=os.getenv("TEST_DATABASE_NAME", "capstone_test"),
            test_database_allow_reset=_bool("TEST_DATABASE_ALLOW_RESET"),
            test_database_require_ephemeral=_bool("TEST_DATABASE_REQUIRE_EPHEMERAL", True),
            auth_mode=auth_mode,
            jwt_secret=secret,
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            jwt_access_token_expire_minutes=_int("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30, 1),
            password_hash_scheme=os.getenv("PASSWORD_HASH_SCHEME", "argon2"),
            allow_insecure_local_auth=insecure,
            storage_provider=os.getenv("STORAGE_PROVIDER", "local"),
            storage_root=storage_root,
            artifacts_root=artifacts_root,
            max_upload_size_bytes=_int("MAX_UPLOAD_SIZE_BYTES", 20_971_520, 1),
            correlation_id_header=os.getenv("CORRELATION_ID_HEADER", "X-Correlation-ID"),
            include_stacktrace=_bool("INCLUDE_STACKTRACE"),
            sql_logging=_bool("SQL_LOGGING"),
            request_logging=_bool("REQUEST_LOGGING", True),
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def reset_settings_cache() -> None:
    global _settings
    _settings = None
