#!/usr/bin/env python3
"""Reject tracked or unignored PostgreSQL host-local configuration."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELF = "scripts/check_docker_postgres_contract.py"
SUPPORTED_NAMES = {"Makefile", "Dockerfile", "pytest.ini"}
SUPPORTED_SUFFIXES = {
    ".cfg", ".conf", ".env", ".example", ".ini", ".json", ".md",
    ".py", ".sh", ".toml", ".yaml", ".yml",
}
EXCLUDED_PARTS = {
    ".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv",
    "__pycache__", "build", "dist", "node_modules",
}
EXCLUDED_PREFIXES = (
    "backups/",
    "data/",
    "datasets/",
    "malaria_dl_local_project/outputs/",
    "malaria_dl_local_project/releases/",
)


@dataclass(frozen=True)
class Rule:
    identifier: str
    pattern: re.Pattern[str]
    description: str


RULES = (
    Rule(
        "PG_DSN_HOST",
        re.compile(
            r"postgresql(?:\+psycopg)?://[^\s'\"`]*@(?:localhost|127\.0\.0\.1|\[?::1\]?|host\.docker\.internal)(?=[:/\s'\"`]|$)",
            re.IGNORECASE,
        ),
        "DSN PostgreSQL dirigido al host",
    ),
    Rule(
        "PG_HOST_ENV",
        re.compile(
            r"\b(?:DB_HOST|DATABASE_HOST|PGHOST)\s*=\s*(?:localhost|127\.0\.0\.1|::1|host\.docker\.internal)\b",
            re.IGNORECASE,
        ),
        "variable PostgreSQL dirigida al host",
    ),
    Rule(
        "RETIRED_IDENTIFIER",
        re.compile(r"\b(?:requires_local_postgres|postgres_local|local_postgres|POSTGRES_LOCAL)\b", re.IGNORECASE),
        "identificador PostgreSQL local retirado",
    ),
    Rule(
        "RETIRED_DATABASE_URL",
        re.compile(r"\b(?:MALARIA_DATABASE_URL|MODEL_GOVERNANCE_TEST_DATABASE_URL|TEST_DATABASE_URL)\b"),
        "variable de conexión alternativa retirada",
    ),
    Rule(
        "RETIRED_DATABASE_NAME",
        re.compile(r"\b(?:capstone_local|malaria_experiments_test|malaria_governance_test)\b", re.IGNORECASE),
        "nombre de segunda base retirado",
    ),
    Rule(
        "HOST_ADMIN_COMMAND",
        re.compile(r"\b(?:pg_ctl|brew\s+services|createdb|dropdb)\b", re.IGNORECASE),
        "administración PostgreSQL fuera de Docker",
    ),
    Rule(
        "HOST_POSTGRES_BINARY",
        re.compile(
            r"^(?:\s*(?:[-*]\s+|[$>]\s*)?)(?:sudo\s+)?(?:psql|pg_dump|pg_restore|pg_isready)\b|[\[(]\s*['\"](?:psql|pg_dump|pg_restore|pg_isready)['\"]",
            re.IGNORECASE,
        ),
        "binario PostgreSQL invocado directamente desde el host",
    ),
    Rule(
        "HOST_ARCHITECTURE",
        re.compile(
            r"\bPostgreSQL\s+(?:Homebrew|local)\b|\bDocker\s+no\s+(?:forma\s+parte|es\s+parte)\b",
            re.IGNORECASE,
        ),
        "descripción de arquitectura PostgreSQL retirada",
    ),
)

# Exceptions are exact and rule-scoped. They enforce rejection behavior or inspect
# Docker-governed commands; none is an operational PostgreSQL host configuration.
ALLOWLIST: dict[str, frozenset[str]] = {
    # Contract tests intentionally feed forbidden hosts and retired database names.
    "backend_api/tests/test_database_url_contract.py": frozenset(
        {"PG_DSN_HOST", "PG_HOST_ENV", "RETIRED_DATABASE_NAME"}
    ),
    "malaria_dl_local_project/tests/test_database_url_contract.py": frozenset(
        {"PG_DSN_HOST", "PG_HOST_ENV", "RETIRED_DATABASE_NAME"}
    ),
    # Runtime and characterization test explicitly reject the retired test URL.
    "backend_api/app/config.py": frozenset({"RETIRED_DATABASE_URL"}),
    "backend_api/tests/test_foundation_config.py": frozenset(
        {"RETIRED_DATABASE_URL"}
    ),
    # Tooling tests assert removed terms stay absent and inspect Docker commands.
    "backend_api/tests/test_docker_postgres_tooling.py": frozenset(
        {"HOST_ADMIN_COMMAND", "HOST_POSTGRES_BINARY", "RETIRED_IDENTIFIER"}
    ),
    # The guard tests necessarily contain every forbidden fixture.
    "backend_api/tests/test_docker_postgres_contract_guard.py": frozenset(
        rule.identifier for rule in RULES
    ),
    # Healthcheck executes pg_isready inside the db container, never on the host.
    "docker-compose.yml": frozenset({"HOST_POSTGRES_BINARY"}),
}


@dataclass(frozen=True)
class Violation:
    rule: str
    path: str
    line: int
    description: str


def repository_files(root: Path = ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return sorted(item.decode("utf-8") for item in result.stdout.split(b"\0") if item)


def is_candidate(path: str) -> bool:
    candidate = Path(path)
    if path == SELF or any(part in EXCLUDED_PARTS for part in candidate.parts):
        return False
    if path.startswith(EXCLUDED_PREFIXES):
        return False
    return candidate.name in SUPPORTED_NAMES or candidate.suffix.lower() in SUPPORTED_SUFFIXES


def read_text(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) > 2_000_000 or b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _docker_governed_native_command(text: str, line: str) -> bool:
    if re.search(r"docker\s+compose\s+exec(?:\s+-T)?\s+(?:db|backend)\b", line):
        return True
    return bool(
        re.search(r"(?:^|\n)\s*(?:docker\s+)?compose\s+exec\s+-T\s+db\b", text)
        and re.search(r"\b(?:pg_dump|pg_restore|pg_isready)\b", line)
    )


def scan_text(path: str, text: str) -> tuple[list[Violation], int]:
    violations: list[Violation] = []
    exceptions = 0
    allowed_rules = ALLOWLIST.get(path, frozenset())
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule in RULES:
            if not rule.pattern.search(line):
                continue
            if (
                rule.identifier == "HOST_POSTGRES_BINARY"
                and _docker_governed_native_command(text, line)
            ):
                continue
            if rule.identifier in allowed_rules:
                exceptions += 1
                continue
            violations.append(
                Violation(rule.identifier, path, line_number, rule.description)
            )
    return violations, exceptions


def scan_repository(root: Path = ROOT) -> tuple[list[Violation], int, int]:
    violations: list[Violation] = []
    exceptions = 0
    reviewed = 0
    for relative_path in repository_files(root):
        if not is_candidate(relative_path):
            continue
        text = read_text(root / relative_path)
        if text is None:
            continue
        reviewed += 1
        found, applied = scan_text(relative_path, text)
        violations.extend(found)
        exceptions += applied
    return violations, reviewed, exceptions


def main() -> int:
    violations, reviewed, exceptions = scan_repository()
    if violations:
        for violation in violations:
            print(
                f"{violation.rule} {violation.path}:{violation.line}: "
                f"{violation.description}; contrato esperado: db:5432",
                file=sys.stderr,
            )
        print(
            f"Contrato PostgreSQL Docker: FALLÓ ({len(violations)} infracciones, "
            f"{reviewed} archivos revisados, {exceptions} excepciones contractuales).",
            file=sys.stderr,
        )
        return 1
    print(
        f"Contrato PostgreSQL Docker: OK ({reviewed} archivos revisados, "
        f"{exceptions} excepciones contractuales)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
