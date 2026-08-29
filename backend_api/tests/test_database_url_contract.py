from __future__ import annotations

import pytest

from app.config import Settings
from app.database_safety import validate_database_url


PASSWORD = "fictional-password"


def _settings(monkeypatch, database_url: str | None):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv(
        "JWT_SECRET", "unit-test-secret-at-least-thirty-two-characters"
    )
    if database_url is None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("DATABASE_URL", database_url)
    return Settings.from_env()


@pytest.mark.parametrize("database_url", [None, "", "   "])
def test_database_url_is_required(monkeypatch, database_url):
    with pytest.raises(ValueError, match="DATABASE_URL"):
        _settings(monkeypatch, database_url)


def test_plain_postgresql_url_is_normalized(monkeypatch):
    settings = _settings(
        monkeypatch,
        f"postgresql://user:{PASSWORD}@db:5432/capstone?sslmode=require&application_name=unit",
    )
    assert settings.database_url == (
        f"postgresql+psycopg://user:{PASSWORD}@db:5432/capstone"
        "?sslmode=require&application_name=unit"
    )


def test_psycopg_url_is_accepted_unchanged(monkeypatch):
    database_url = f"postgresql+psycopg://user:{PASSWORD}@db:5432/capstone"
    assert _settings(monkeypatch, database_url).database_url == database_url


@pytest.mark.parametrize(
    "database_url",
    [
        f"postgresql://user:{PASSWORD}@localhost:5432/capstone",
        f"postgresql://user:{PASSWORD}@127.0.0.1:5432/capstone",
        f"postgresql://user:{PASSWORD}@[::1]:5432/capstone",
        f"postgresql://user:{PASSWORD}@host.docker.internal:5432/capstone",
        f"postgresql://user:{PASSWORD}@other:5432/capstone",
        "postgresql:///capstone",
        f"postgresql://user:{PASSWORD}@db:55432/capstone",
    ],
)
def test_non_docker_database_targets_are_rejected(monkeypatch, database_url):
    with pytest.raises(ValueError) as error:
        _settings(monkeypatch, database_url)
    assert PASSWORD not in str(error.value)


@pytest.mark.parametrize(
    "variables",
    [
        {
            "DB_HOST": "db",
            "DB_PORT": "5432",
            "DB_NAME": "capstone",
            "DB_USER": "user",
            "DB_PASSWORD": PASSWORD,
        },
        {
            "DATABASE_HOST": "db",
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": "capstone",
            "DATABASE_USER": "user",
            "DATABASE_PASSWORD": PASSWORD,
        },
    ],
)
def test_partial_variables_do_not_create_a_fallback(monkeypatch, variables):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    for name, value in variables.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        _settings(monkeypatch, None)


def test_validation_errors_do_not_disclose_password():
    with pytest.raises(ValueError) as error:
        validate_database_url(
            f"postgresql://user:{PASSWORD}@not-db:5432/capstone"
        )
    assert PASSWORD not in str(error.value)
