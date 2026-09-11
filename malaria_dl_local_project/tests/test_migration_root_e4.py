"""Actual file/stdin entry paths, without DB access (--help exits before app)."""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ("verify_alembic_adoption.py", "validate_alembic_transactionally.py")


@pytest.mark.parametrize("name", SCRIPTS)
@pytest.mark.parametrize(
    "mode", ["file", "stdin_root", "stdin_missing", "stdin_invalid", "stdin_empty"]
)
def test_script_root_modes(name, mode, tmp_path):
    env = dict(os.environ)
    env.pop("CAPSTONE_ROOT", None)
    script = ROOT / "scripts/db" / name
    args = [sys.executable, "-B", str(script), "--help"]
    source = None
    if mode != "file":
        args = [sys.executable, "-B", "-", "--help"]
        source = script.read_text()
    if mode == "stdin_root":
        env["CAPSTONE_ROOT"] = str(ROOT)
    if mode == "stdin_invalid":
        env["CAPSTONE_ROOT"] = str(tmp_path)
    if mode == "stdin_empty":
        env["CAPSTONE_ROOT"] = ""
    result = subprocess.run(
        args,
        input=source,
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        check=False,
    )
    if mode in ("file", "stdin_root"):
        assert result.returncode == 0, result.stderr
        assert "usage:" in result.stdout
    else:
        assert result.returncode != 0
        assert (
            "CAPSTONE_ROOT_REQUIRED_FOR_STDIN"
            if mode == "stdin_missing"
            else "CAPSTONE_ROOT_INVALID"
        ) in result.stderr
        assert "IndexError" not in result.stderr


def test_defined_root_never_evaluates_file_fallback(monkeypatch):
    monkeypatch.setenv("CAPSTONE_ROOT", str(ROOT))
    for name in SCRIPTS:
        spec = importlib.util.spec_from_file_location(
            "root_case", ROOT / "scripts/db" / name
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert (
            module.resolve_capstone_root({"CAPSTONE_ROOT": str(ROOT)}, "/app/<stdin>")
            == ROOT
        )


def test_precheck_accepts_known_parent_revisions(monkeypatch, tmp_path):
    monkeypatch.setenv("CAPSTONE_ROOT", str(ROOT))
    monkeypatch.chdir(tmp_path)
    spec = importlib.util.spec_from_file_location(
        "precheck", ROOT / "scripts/db/verify_alembic_adoption.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module._linear_head() == "20260911_02"
    assert {"20260901_01", "20260911_01", "20260911_02"} <= {
        r.revision for r in module._scripts().walk_revisions()
    }


def test_forward_correction_renders_offline():
    from io import StringIO

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    spec = importlib.util.spec_from_file_location(
        "correction", ROOT / "alembic/versions/20260911_02_campaign_integrity.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    )
    with Operations.context(context):
        module.upgrade()
    rendered = output.getvalue()
    assert module.down_revision == "20260911_01"
    assert "ck_campaign_frozen_required_v2" in rendered
    assert "CREATE OR REPLACE FUNCTION campaign_attempt_guard" in rendered
    assert "TRAIN_RELATIONAL_MODEL_CONFLICT" in rendered
    assert "IS NOT DISTINCT FROM encode(sha256" in rendered
    assert "SET search_path = public, pg_catalog" in rendered


@pytest.mark.parametrize(
    "revision", ["20260911_01_experimental_campaigns", "20260911_02_campaign_integrity"]
)
def test_migration_ddl_has_no_accidental_bind_parameters(revision):
    from sqlalchemy import text
    from sqlalchemy.dialects.postgresql import psycopg

    spec = importlib.util.spec_from_file_location(
        revision, ROOT / "alembic/versions" / (revision + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("DDL", "ATTEMPT_GUARD"):
        if hasattr(module, name):
            compiled = text(getattr(module, name)).compile(dialect=psycopg.dialect())
            # Mirrors the execution-time step that failed before reaching PostgreSQL.
            assert compiled.construct_params({}) == {}


def test_synthetic_sql_literals_have_only_explicit_parameters():
    import ast

    from sqlalchemy import text
    from sqlalchemy.dialects.postgresql import psycopg

    tree = ast.parse(
        (ROOT / "malaria_dl_local_project/tests/test_campaigns_postgres.py").read_text()
    )
    checked = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id not in ("sql", "rejected") or len(node.args) < 2:
            continue
        literal = node.args[1]
        if not isinstance(literal, ast.Constant) or not isinstance(literal.value, str):
            continue
        compiled = text(literal.value).compile(dialect=psycopg.dialect())
        parameters = {kw.arg: None for kw in node.keywords if kw.arg is not None}
        assert set(compiled.construct_params(parameters)) <= set(parameters)
        checked += 1
    assert checked > 20


def test_fresh_process_guard_allows_driver_metadata_and_blocks_configs(monkeypatch):
    import ast

    tree = ast.parse(
        (ROOT / "malaria_dl_local_project/tests/test_campaigns_postgres.py").read_text()
    )
    fn = next(
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef)
        and n.name == "test_concurrent_active_attempt_two_connections"
    )
    code = next(
        n.value.value
        for n in ast.walk(fn)
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "code" for t in n.targets)
    )
    # Run the real child initialization in a new interpreter, without opening a DB connection.
    prefix = code.split("try:\n    result=", 1)[0]
    suffix = """
try:
    Path('configs/forbidden.yaml').read_text()
except AssertionError:
    print('config_guard_ok')
else:
    raise AssertionError('guard missing')
engine.dispose()
"""
    env = dict(
        os.environ, DATABASE_URL="postgresql+psycopg://synthetic:synthetic@db/synthetic"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            prefix + suffix,
            "capstone_test_e4_synthetic",
            "synthetic",
        ],
        cwd=ROOT / "malaria_dl_local_project",
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, "fresh process initialization failed"
    assert result.stdout.strip() == "config_guard_ok"
