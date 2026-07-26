from dataclasses import replace

import pytest

from app.config import Settings
from app.database_safety import assert_safe_test_database, redacted_database_target
from app.observability import sanitize, valid_correlation_id
from app.security import Permission, ROLE_PERMISSIONS, hash_password, verify_password


def test_local_configuration_has_no_personal_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("APP_ENV", "local")
    settings = Settings.from_env()
    assert "malaria_experiments" not in settings.database_url


def test_demo_rejects_example_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "demo")
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:y@postgres/demo")
    monkeypatch.setenv("JWT_SECRET", "change-me")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_disabled_auth_rejected_outside_local(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:y@localhost/capstone_test")
    monkeypatch.setenv("AUTH_MODE", "disabled")
    monkeypatch.setenv("ALLOW_INSECURE_LOCAL_AUTH", "true")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_database_guard_accepts_ephemeral_and_redacts_password(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:super-secret@localhost:55433/capstone_test")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://u:super-secret@localhost:55433/capstone_test")
    monkeypatch.setenv("TEST_DATABASE_ALLOW_RESET", "true")
    monkeypatch.setenv("JWT_SECRET", "test-secret-with-at-least-thirty-two-characters")
    settings = Settings.from_env()
    assert assert_safe_test_database(settings, confirmation=True).endswith("/capstone_test")
    assert "super-secret" not in redacted_database_target(settings.database_url)


def test_database_guard_rejects_personal_database(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/malaria_experiments")
    monkeypatch.setenv("TEST_DATABASE_ALLOW_RESET", "true")
    monkeypatch.setenv("JWT_SECRET", "test-secret-with-at-least-thirty-two-characters")
    with pytest.raises(RuntimeError):
        assert_safe_test_database(Settings.from_env(), confirmation=True)


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
