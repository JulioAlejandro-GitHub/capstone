from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from app.database_safety import validate_database_url


TRUE_VALUES = {"1", "true", "yes", "on"}


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in TRUE_VALUES


def _int(name: str, default: int, minimum: int = 0) -> int:
    value = int(os.getenv(name, str(default)))
    if value < minimum:
        raise ValueError(f"{name} debe ser >= {minimum}")
    return value


def _float(
    name: str,
    default: float,
    minimum: float = 0.0,
    maximum: float | None = None,
) -> float:
    value = float(os.getenv(name, str(default)))
    if (
        not math.isfinite(value)
        or value < minimum
        or (maximum is not None and value > maximum)
    ):
        upper = f" y <= {maximum}" if maximum is not None else ""
        raise ValueError(f"{name} debe ser >= {minimum}{upper}")
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
    test_execution: bool
    test_isolation_mode: str
    test_schema_prefix: str
    allow_temporary_test_schema: bool
    allow_database_drop: bool
    allow_public_schema_drop: bool
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
    max_image_pixels: int
    upload_chunk_size_bytes: int
    staging_retention_hours: int
    allowed_microscopy_formats: tuple[str, ...]
    quality_analysis_max_dimension: int
    cell_detection_page_max: int
    cell_classification_batch_size: int
    cell_classification_review_margin: float
    cell_classification_page_max: int
    correlation_id_header: str
    include_stacktrace: bool
    sql_logging: bool
    request_logging: bool

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.getenv("APP_ENV", "development").strip().lower()
        if env != "development":
            raise ValueError("APP_ENV solo admite development")
        auth_mode = os.getenv("AUTH_MODE", "local_jwt").strip().lower()
        insecure = _bool("ALLOW_INSECURE_LOCAL_AUTH")
        if auth_mode not in {"local_jwt", "disabled"}:
            raise ValueError("AUTH_MODE debe ser local_jwt o disabled")
        if auth_mode == "disabled" and not insecure:
            raise ValueError("AUTH_MODE=disabled requiere autorización explícita")
        secret = os.getenv("JWT_SECRET")
        if auth_mode == "local_jwt" and not secret:
            raise ValueError("JWT_SECRET es obligatorio; no existe un secreto por defecto")
        database_url = validate_database_url(os.getenv("DATABASE_URL"))
        if os.getenv("TEST_DATABASE_URL"):
            raise ValueError("TEST_DATABASE_URL está prohibida: las pruebas usan la base Capstone")
        pool_min = _int("DATABASE_POOL_MIN_SIZE", 1, 1)
        pool_max = _int("DATABASE_POOL_MAX_SIZE", 5, 1)
        if pool_min > pool_max:
            raise ValueError("DATABASE_POOL_MIN_SIZE no puede superar DATABASE_POOL_MAX_SIZE")
        project_root = Path(__file__).resolve().parents[2]
        storage_root = Path(os.getenv("STORAGE_ROOT", "./var/storage")).expanduser()
        if not storage_root.is_absolute():
            storage_root = project_root / storage_root
        artifacts_root = Path(os.getenv("ARTIFACTS_ROOT", "./var/artifacts")).expanduser()
        isolation_mode = os.getenv("TEST_ISOLATION_MODE", "transaction").strip().lower()
        if isolation_mode not in {"transaction", "temporary_schema"}:
            raise ValueError("TEST_ISOLATION_MODE debe ser transaction o temporary_schema")
        return cls(
            app_env=env,
            app_name=os.getenv("APP_NAME", "Capstone Experiments API"),
            app_version=os.getenv("APP_VERSION", "0.3.0"),
            debug=_bool("DEBUG"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            log_format=os.getenv("LOG_FORMAT", "text"),
            api_prefix=os.getenv("API_PREFIX", "/api/v1").rstrip("/"),
            frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").rstrip("/"),
            cors_origins=_origins(os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")),
            database_url=database_url,
            database_pool_min_size=pool_min,
            database_pool_max_size=pool_max,
            database_connect_timeout=_int("DATABASE_CONNECT_TIMEOUT", 5, 1),
            test_execution=_bool("TEST_EXECUTION"),
            test_isolation_mode=isolation_mode,
            test_schema_prefix=os.getenv("TEST_SCHEMA_PREFIX", "capstone_test_"),
            allow_temporary_test_schema=_bool("ALLOW_TEMPORARY_TEST_SCHEMA", True),
            allow_database_drop=False,
            allow_public_schema_drop=False,
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
            max_image_pixels=_int("MAX_IMAGE_PIXELS", 100_000_000, 1),
            upload_chunk_size_bytes=_int("UPLOAD_CHUNK_SIZE_BYTES", 1_048_576, 1),
            staging_retention_hours=_int("STAGING_RETENTION_HOURS", 24, 1),
            allowed_microscopy_formats=tuple(
                item.strip().upper() for item in
                os.getenv("ALLOWED_MICROSCOPY_FORMATS", "JPEG,PNG,TIFF").split(",")
                if item.strip()
            ),
            quality_analysis_max_dimension=_int("QUALITY_ANALYSIS_MAX_DIMENSION", 2048, 64),
            cell_detection_page_max=_int("CELL_DETECTION_PAGE_MAX", 500, 500),
            cell_classification_batch_size=_int(
                "CELL_CLASSIFICATION_BATCH_SIZE", 32, 1
            ),
            cell_classification_review_margin=_float(
                "CELL_CLASSIFICATION_REVIEW_MARGIN", 0.05, 0.0, 1.0
            ),
            cell_classification_page_max=_int(
                "CELL_CLASSIFICATION_PAGE_MAX", 500, 100
            ),
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
