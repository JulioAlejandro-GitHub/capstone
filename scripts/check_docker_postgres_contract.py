#!/usr/bin/env python3
"""Reject tracked or unignored PostgreSQL host-local configuration."""

from __future__ import annotations

import ast
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

# Exceptions are exact test-file/rule pairs with an asserted current match count.
ALLOWLIST: dict[str, dict[str, int]] = {
    "backend_api/tests/test_database_url_contract.py": {"PG_DSN_HOST": 4},
    "malaria_dl_local_project/tests/test_database_url_contract.py": {"PG_DSN_HOST": 4},
    "backend_api/tests/test_foundation_config.py": {"RETIRED_DATABASE_URL": 1},
    "backend_api/tests/test_docker_postgres_tooling.py": {
        "HOST_ADMIN_COMMAND": 2,
        "RETIRED_IDENTIFIER": 1,
    },
    "backend_api/tests/test_docker_postgres_contract_guard.py": {
        "HOST_ADMIN_COMMAND": 2,
        "PG_DSN_HOST": 5,
        "PG_HOST_ENV": 1,
        "RETIRED_DATABASE_URL": 1,
        "RETIRED_IDENTIFIER": 1,
    },
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


def _retired_name_from_test(node: ast.expr) -> str | None:
    candidate = node
    if (
        isinstance(candidate, ast.Compare)
        and len(candidate.ops) == 1
        and isinstance(candidate.ops[0], (ast.IsNot, ast.In))
    ):
        if isinstance(candidate.ops[0], ast.IsNot):
            if not (
                len(candidate.comparators) == 1
                and isinstance(candidate.comparators[0], ast.Constant)
                and candidate.comparators[0].value is None
            ):
                return None
            candidate = candidate.left
        else:
            if not (
                isinstance(candidate.left, ast.Constant)
                and isinstance(candidate.left.value, str)
                and len(candidate.comparators) == 1
                and isinstance(candidate.comparators[0], ast.Attribute)
                and isinstance(candidate.comparators[0].value, ast.Name)
                and candidate.comparators[0].value.id == "os"
                and candidate.comparators[0].attr == "environ"
            ):
                return None
            return candidate.left.value
    if not (
        isinstance(candidate, ast.Call)
        and len(candidate.args) == 1
        and not candidate.keywords
        and isinstance(candidate.func, ast.Attribute)
        and isinstance(candidate.func.value, ast.Name)
        and candidate.func.value.id == "os"
        and candidate.func.attr == "getenv"
        and isinstance(candidate.args[0], ast.Constant)
        and isinstance(candidate.args[0].value, str)
    ):
        return None
    return candidate.args[0].value


def explicit_rejection_lines(path: str, text: str) -> set[int]:
    if Path(path).suffix != ".py":
        return set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    retired_names = {
        "MALARIA_DATABASE_URL",
        "MODEL_GOVERNANCE_TEST_DATABASE_URL",
        "TEST_DATABASE_URL",
    }
    accepted: set[int] = set()
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.If)
            and len(node.body) == 1
            and isinstance(node.body[0], ast.Raise)
            and not node.orelse
        ):
            continue
        name = _retired_name_from_test(node.test)
        if name not in retired_names:
            continue
        unsafe_raise_access = any(
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Attribute)
            and isinstance(child.func.value, ast.Name)
            and child.func.value.id == "os"
            and child.func.attr == "getenv"
            for child in ast.walk(node.body[0])
        )
        if unsafe_raise_access:
            continue
        accepted.update(range(node.lineno, node.body[0].end_lineno + 1))
    return accepted


def _eligible_rule_matches(path: str, text: str, rule: Rule) -> list[int]:
    explicit_lines = explicit_rejection_lines(path, text)
    matches: list[int] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not rule.pattern.search(line):
            continue
        if rule.identifier == "HOST_POSTGRES_BINARY" and _docker_governed_native_command(text, line):
            continue
        if rule.identifier == "RETIRED_DATABASE_URL" and line_number in explicit_lines:
            continue
        matches.append(line_number)
    return matches


def validate_allowlist(
    root: Path = ROOT,
    allowlist: dict[str, dict[str, int]] | None = None,
) -> list[Violation]:
    entries = ALLOWLIST if allowlist is None else allowlist
    known_rules = {rule.identifier: rule for rule in RULES}
    violations: list[Violation] = []
    for path, expected_rules in entries.items():
        candidate = Path(path)
        parts = candidate.parts
        is_test_root = (
            bool(parts)
            and (
                parts[0] == "tests"
                or parts[:2] == ("backend_api", "tests")
                or parts[:2] == ("malaria_dl_local_project", "tests")
            )
        )
        is_exact_test = (
            not any(character in path for character in "*?[]")
            and candidate.suffix == ".py"
            and is_test_root
        )
        if not is_exact_test:
            violations.append(Violation("INVALID_ALLOWLIST_TARGET", path, 0, "allowlist solo admite archivos de prueba exactos"))
            continue
        text = read_text(root / path)
        if text is None:
            violations.append(Violation("STALE_ALLOWLIST_ENTRY", path, 0, "ruta allowlisted inexistente o no legible"))
            continue
        for identifier, expected_count in expected_rules.items():
            rule = known_rules.get(identifier)
            if rule is None or expected_count < 1:
                violations.append(Violation("STALE_ALLOWLIST_ENTRY", path, 0, "regla allowlisted inválida o sin coincidencias esperadas"))
                continue
            actual_count = len(_eligible_rule_matches(path, text, rule))
            if actual_count != expected_count:
                violations.append(Violation("STALE_ALLOWLIST_ENTRY", path, 0, "cantidad allowlisted distinta de la esperada"))
    return violations


def scan_text(
    path: str,
    text: str,
    allowlist: dict[str, dict[str, int]] | None = None,
) -> tuple[list[Violation], int]:
    violations: list[Violation] = []
    exceptions = 0
    entries = ALLOWLIST if allowlist is None else allowlist
    allowed_rules = entries.get(path, {})
    explicit_lines = explicit_rejection_lines(path, text)
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule in RULES:
            if not rule.pattern.search(line):
                continue
            if (
                rule.identifier == "HOST_POSTGRES_BINARY"
                and _docker_governed_native_command(text, line)
            ):
                continue
            if (
                rule.identifier == "RETIRED_DATABASE_URL"
                and line_number in explicit_lines
            ):
                continue
            if rule.identifier in allowed_rules:
                exceptions += 1
                continue
            violations.append(
                Violation(rule.identifier, path, line_number, rule.description)
            )
    return violations, exceptions


def scan_repository(
    root: Path = ROOT,
    allowlist: dict[str, dict[str, int]] | None = None,
) -> tuple[list[Violation], int, int]:
    entries = ALLOWLIST if allowlist is None else allowlist
    violations = validate_allowlist(root, entries)
    exceptions = 0
    reviewed = 0
    for relative_path in repository_files(root):
        if not is_candidate(relative_path):
            continue
        text = read_text(root / relative_path)
        if text is None:
            continue
        reviewed += 1
        found, applied = scan_text(relative_path, text, entries)
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
