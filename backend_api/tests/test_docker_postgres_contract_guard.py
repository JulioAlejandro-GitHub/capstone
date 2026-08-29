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

FORBIDDEN_DSN = "postgresql://user:secret@localhost:5432/app"
FORBIDDEN_HOST_ENV = "DB_HOST=localhost"
RETIRED_ENV = "TEST_DATABASE_URL"
RETIRED_RULE = "RETIRED_DATABASE_URL"


@pytest.mark.parametrize(
    ("text", "rule"),
    [
        (FORBIDDEN_DSN, "PG_DSN_HOST"),
        ("postgresql://user:secret@127.0.0.1:5432/app", "PG_DSN_HOST"),
        ("postgresql://user:secret@[::1]:5432/app", "PG_DSN_HOST"),
        ("postgresql://user:secret@host.docker.internal:5432/app", "PG_DSN_HOST"),
        (FORBIDDEN_HOST_ENV, "PG_HOST_ENV"),
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
    text = FORBIDDEN_DSN
    violations, exceptions = guard.scan_text(
        "backend_api/tests/test_database_url_contract.py", text
    )
    assert violations == []
    assert exceptions == 1
    violations, exceptions = guard.scan_text("backend_api/tests/other.py", text)
    assert violations and exceptions == 0


def test_runtime_config_is_not_allowlisted_and_explicit_rejection_is_accepted():
    path = "backend_api/app/config.py"
    assert path not in guard.ALLOWLIST
    source = (ROOT / path).read_text(encoding="utf-8")
    violations, _ = guard.scan_text(path, source)
    assert RETIRED_RULE not in {item.rule for item in violations}


def test_operational_retired_database_url_use_fails():
    source = f'database_url = os.getenv("{RETIRED_ENV}")\n'
    violations, _ = guard.scan_text("runtime.py", source)
    assert RETIRED_RULE in {item.rule for item in violations}


def test_explicit_rejection_followed_by_operational_use_fails():
    source = f'''
if os.getenv("{RETIRED_ENV}"):
    raise ValueError("{RETIRED_ENV} is forbidden")
database_url = os.getenv("{RETIRED_ENV}")
'''
    violations, _ = guard.scan_text("runtime.py", source)
    assert [item.rule for item in violations] == [RETIRED_RULE]


def test_check_without_unconditional_raise_fails():
    source = f'''
if os.getenv("{RETIRED_ENV}"):
    logger.warning("{RETIRED_ENV} is configured")
'''
    violations, _ = guard.scan_text("runtime.py", source)
    assert len([item for item in violations if item.rule == RETIRED_RULE]) == 2


def test_retired_database_url_fallback_fails():
    source = f'database_url = os.getenv("{RETIRED_ENV}") or os.getenv("DATABASE_URL")\n'
    violations, _ = guard.scan_text("runtime.py", source)
    assert RETIRED_RULE in {item.rule for item in violations}


def test_allowlist_entry_with_zero_expected_matches_is_stale(tmp_path):
    path = tmp_path / "tests" / "contract.py"
    path.parent.mkdir()
    path.write_text("safe = True\n", encoding="utf-8")
    allowlist = {"tests/contract.py": {"PG_DSN_HOST": 0}}
    violations = guard.validate_allowlist(tmp_path, allowlist)
    assert {item.rule for item in violations} == {"STALE_ALLOWLIST_ENTRY"}


def test_missing_allowlisted_path_is_stale(tmp_path):
    allowlist = {"tests/missing.py": {"PG_DSN_HOST": 1}}
    violations = guard.validate_allowlist(tmp_path, allowlist)
    assert {item.rule for item in violations} == {"STALE_ALLOWLIST_ENTRY"}


def test_allowlist_match_count_drift_is_stale(tmp_path):
    path = tmp_path / "tests" / "contract.py"
    path.parent.mkdir()
    path.write_text(FORBIDDEN_HOST_ENV + "\n", encoding="utf-8")
    allowlist = {"tests/contract.py": {"PG_HOST_ENV": 2}}
    violations = guard.validate_allowlist(tmp_path, allowlist)
    assert {item.rule for item in violations} == {"STALE_ALLOWLIST_ENTRY"}


@pytest.mark.parametrize(
    "path",
    [
        "backend_api/app/config.py",
        "docker-compose.yml",
        ".github/workflows/ci.yml",
        "docs/contract.py",
        "Makefile",
    ],
)
def test_allowlist_rejects_non_test_targets(tmp_path, path):
    allowlist = {path: {RETIRED_RULE: 1}}
    violations = guard.validate_allowlist(tmp_path, allowlist)
    assert {item.rule for item in violations} == {"INVALID_ALLOWLIST_TARGET"}


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
    (tmp_path / "new.md").write_text(FORBIDDEN_HOST_ENV + "\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "ignored.md").write_text(
        FORBIDDEN_HOST_ENV + "\n", encoding="utf-8"
    )
    (tmp_path / "binary.py").write_bytes(
        FORBIDDEN_HOST_ENV.encode() + b"\0ignored"
    )

    files = guard.repository_files(tmp_path)
    assert "new.md" in files
    violations, reviewed, _ = guard.scan_repository(tmp_path, {})
    assert {(item.path, item.rule) for item in violations} == {
        ("new.md", "PG_HOST_ENV")
    }
    assert reviewed == 2


def test_binary_files_are_not_processed(tmp_path):
    binary = tmp_path / "payload.py"
    binary.write_bytes(FORBIDDEN_HOST_ENV.encode() + b"\0ignored")
    assert guard.read_text(binary) is None
