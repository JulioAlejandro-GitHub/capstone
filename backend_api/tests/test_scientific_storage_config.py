from pathlib import Path

import pytest

from app.config import Settings


def _base_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://unused:unused@db:5432/capstone"
    )
    monkeypatch.setenv(
        "JWT_SECRET", "unit-test-secret-at-least-thirty-two-characters"
    )


@pytest.mark.parametrize("value", [None, "", "   "])
def test_storage_root_is_required(monkeypatch, value):
    _base_environment(monkeypatch)
    if value is None:
        monkeypatch.delenv("STORAGE_ROOT", raising=False)
    else:
        monkeypatch.setenv("STORAGE_ROOT", value)

    with pytest.raises(ValueError, match="STORAGE_ROOT"):
        Settings.from_env()


@pytest.mark.parametrize(
    "value",
    ["var/storage", "./var/storage", "backend_api/var/storage"],
)
def test_storage_root_rejects_relative_paths_without_disclosing_value(
    monkeypatch, value
):
    _base_environment(monkeypatch)
    monkeypatch.setenv("STORAGE_ROOT", value)

    with pytest.raises(ValueError, match="STORAGE_ROOT") as error:
        Settings.from_env()

    assert value not in str(error.value)


def test_absolute_temporary_storage_root_is_accepted_without_creation(
    monkeypatch, tmp_path: Path
):
    _base_environment(monkeypatch)
    storage_root = tmp_path / "not-created-by-configuration"
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))

    settings = Settings.from_env()

    assert settings.storage_root == storage_root
    assert settings.storage_root.is_absolute()
    assert not storage_root.exists()
