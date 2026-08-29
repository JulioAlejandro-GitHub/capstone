from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_docker_postgres_contract.py"
SPEC = importlib.util.spec_from_file_location("docker_postgres_guard", SCRIPT)
assert SPEC and SPEC.loader
guard = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = guard
SPEC.loader.exec_module(guard)


@pytest.mark.parametrize(
    ("text", "rule"),
    [
        ("postgresql://user:secret@localhost:5432/app", "PG_DSN_HOST"),
        ("postgresql://user:secret@127.0.0.1:5432/app", "PG_DSN_HOST"),
        ("postgresql://user:secret@[::1]:5432/app", "PG_DSN_HOST"),
        ("postgresql://user:secret@host.docker.internal:5432/app", "PG_DSN_HOST"),
        ("DB_HOST=localhost", "PG_HOST_ENV"),
        ("requires_local_postgres", "RETIRED_IDENTIFIER"),
        ("brew services start postgresql", "HOST_ADMIN_COMMAND"),
        ("createdb -h localhost app", "HOST_ADMIN_COMMAND"),
        ("psql postgresql://user:secret@localhost/app", "HOST_POSTGRES_BINARY"),
    ],
)
def test_forbidden_patterns_fail(text, rule):
    violations, _ = guard.scan_text("notes.md", text)
    assert rule in {item.rule for item in violations}


@pytest.mark.parametrize(
    "text",
    [
        "docker compose exec -T db pg_dump --format=custom",
        "postgresql://unused:unused@db:5432/capstone",
        "http://localhost:5173",
        "http://localhost:8000",
        "malaria_dl_local_project",
    ],
)
def test_allowed_patterns_pass(text):
    violations, _ = guard.scan_text("notes.md", text)
    assert violations == []


def test_contract_file_allowlist_is_exact():
    text = "postgresql://user:secret@localhost:5432/app"
    violations, exceptions = guard.scan_text(
        "backend_api/tests/test_database_url_contract.py", text
    )
    assert violations == []
    assert exceptions == 1
    violations, exceptions = guard.scan_text("backend_api/tests/other.py", text)
    assert violations and exceptions == 0


def test_violation_output_never_contains_credentials(capsys, monkeypatch):
    violation = guard.Violation("PG_DSN_HOST", "unsafe.md", 7, "DSN rechazada")
    monkeypatch.setattr(guard, "scan_repository", lambda: ([violation], 1, 0))
    assert guard.main() == 1
    output = capsys.readouterr().err
    assert "PG_DSN_HOST unsafe.md:7" in output
    assert "secret" not in output
    assert "postgresql://" not in output


def test_unstaged_new_files_are_scanned_and_generated_paths_are_excluded(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "tracked.md").write_text("Docker-only\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.md"], cwd=tmp_path, check=True)
    (tmp_path / "new.md").write_text("DB_HOST=localhost\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "ignored.md").write_text(
        "DB_HOST=localhost\n", encoding="utf-8"
    )
    (tmp_path / "binary.py").write_bytes(b"DB_HOST=localhost\0ignored")

    files = guard.repository_files(tmp_path)
    assert "new.md" in files
    violations, reviewed, _ = guard.scan_repository(tmp_path)
    assert {(item.path, item.rule) for item in violations} == {
        ("new.md", "PG_HOST_ENV")
    }
    assert reviewed == 2


def test_binary_files_are_not_processed(tmp_path):
    binary = tmp_path / "payload.py"
    binary.write_bytes(b"DB_HOST=localhost\0ignored")
    assert guard.read_text(binary) is None
