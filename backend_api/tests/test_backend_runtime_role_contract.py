"""SWV2.1: the backend connects to PostgreSQL v2 only as capstone_v2_runtime."""
from __future__ import annotations

from test_scientific_storage_docker_contract import (
    BASE_COMPOSE,
    OVERRIDE_COMPOSE,
    ROOT,
    _service_block,
    _service_child_block,
)


def _environment(source: str, service: str) -> dict[str, str]:
    block = _service_child_block(_service_block(source, service), "environment")
    pairs = (line.strip().split(":", 1) for line in block.splitlines()
             if line.strip() and not line.strip().startswith("#"))
    return {key.strip(): value.strip() for key, value in pairs}


def test_backend_database_url_uses_only_the_runtime_role():
    environment = _environment(BASE_COMPOSE.read_text(encoding="utf-8"), "backend")
    url = environment["DATABASE_URL"]
    assert url.startswith("postgresql+psycopg://capstone_v2_runtime:${CAPSTONE_V2_RUNTIME_PASSWORD:?")
    assert url.endswith("@db:5432/${POSTGRES_DB:?POSTGRES_DB is required}")
    for forbidden in ("POSTGRES_USER", "POSTGRES_PASSWORD", "capstone_v2_migrator", "julio"):
        assert forbidden not in url


def test_backend_container_does_not_carry_the_admin_login():
    environment = _environment(BASE_COMPOSE.read_text(encoding="utf-8"), "backend")
    assert environment["POSTGRES_USER"] == '""'
    assert environment["POSTGRES_PASSWORD"] == '""'
    override = OVERRIDE_COMPOSE.read_text(encoding="utf-8")
    backend_override = _service_block(override, "backend")
    for name in ("DATABASE_URL", "POSTGRES_USER", "POSTGRES_PASSWORD", "capstone_v2_migrator"):
        assert name not in backend_override


def test_env_example_declares_runtime_credential_without_value():
    lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    assert "CAPSTONE_V2_RUNTIME_PASSWORD=" in lines
