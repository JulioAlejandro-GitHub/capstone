from dataclasses import replace

import pytest

from app.config import Settings
from app.database_safety import (
    assert_capstone_database,
    assert_database_drop_forbidden,
    assert_safe_temporary_schema,
    assert_test_transaction_required,
    redacted_database_target,
)
from app.observability import sanitize, valid_correlation_id
from app.security import Permission, ROLE_PERMISSIONS, hash_password, verify_password


def _development(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:secret@127.0.0.1:5432/malaria_experiments")
    monkeypatch.setenv("JWT_SECRET", "test-secret-with-at-least-thirty-two-characters")


def test_development_is_the_only_environment(monkeypatch):
    _development(monkeypatch)
    assert Settings.from_env().app_env == "development"
    for invalid in ("local", "test", "demo"):
        monkeypatch.setenv("APP_ENV", invalid)
        with pytest.raises(ValueError):
            Settings.from_env()


def test_database_and_secret_are_required(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(ValueError):
        Settings.from_env()


def test_second_database_url_is_rejected(monkeypatch):
    _development(monkeypatch)
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://u:p@localhost/other")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_capstone_identity_and_redaction(monkeypatch):
    _development(monkeypatch)
    settings = Settings.from_env()
    assert assert_capstone_database(settings, "malaria_experiments") == "malaria_experiments"
    with pytest.raises(RuntimeError):
        assert_capstone_database(settings, "postgres")
    assert "secret" not in redacted_database_target(settings.database_url)


def test_database_drop_is_always_forbidden():
    with pytest.raises(RuntimeError):
        assert_database_drop_forbidden()


@pytest.mark.parametrize("name", [
    "public", "information_schema", "pg_catalog", "pg_toast",
    "capstone_test_bad-name", "capstone_test_x", 'capstone_test_bad"name',
])
def test_temporary_schema_guard_rejects_unsafe_names(monkeypatch, name):
    _development(monkeypatch)
    monkeypatch.setenv("TEST_EXECUTION", "true")
    with pytest.raises(RuntimeError):
        assert_safe_temporary_schema(Settings.from_env(), name)


def test_test_isolation_guards(monkeypatch):
    _development(monkeypatch)
    monkeypatch.setenv("TEST_EXECUTION", "true")
    settings = Settings.from_env()
    assert_safe_temporary_schema(settings, "capstone_test_run_123456")
    assert_test_transaction_required(settings)
    with pytest.raises(RuntimeError):
        assert_test_transaction_required(replace(settings, test_execution=False))


def test_password_is_one_way_and_permissions_are_central():
    encoded = hash_password("correct horse battery staple")
    assert "correct horse battery staple" not in encoded
    assert verify_password("correct horse battery staple", encoded)
    assert Permission.USERS_MANAGE in ROLE_PERMISSIONS["administrator"]
    assert Permission.USERS_MANAGE not in ROLE_PERMISSIONS["read_only"]


def test_logging_sanitization_and_correlation_id():
    cleaned = sanitize({"password": "hidden", "nested": {"Authorization": "Bearer abc"}})
    assert cleaned == {"password": "<redacted>", "nested": {"Authorization": "<redacted>"}}
    assert valid_correlation_id("x") != "x"


def test_cell_detection_page_limit_supports_at_least_five_hundred(monkeypatch):
    _development(monkeypatch)
    monkeypatch.setenv("CELL_DETECTION_PAGE_MAX", "499")
    with pytest.raises(ValueError):
        Settings.from_env()
    monkeypatch.setenv("CELL_DETECTION_PAGE_MAX", "500")
    assert Settings.from_env().cell_detection_page_max == 500
