"""The infrastructure adapter must remain outside the approved application port."""
import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_adapter_is_not_imported_by_service_or_contracts():
    source = ROOT / 'malaria_dl_local_project/src/malaria_dl'
    for directory in ('results', 'execution/contracts'):
        for path in (source / directory).rglob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom):
                    assert 'persistence' not in (node.module or '')
                    assert all(name.name != 'PostgresResultRepository' for name in node.names)
                if isinstance(node, ast.Import):
                    assert all('persistence' not in name.name for name in node.names)


def test_migration_has_no_accidental_sqlalchemy_parameters():
    from sqlalchemy import text
    from sqlalchemy.dialects.postgresql import psycopg
    path = ROOT / 'alembic/versions/20260922_01_result_events.py'
    spec = importlib.util.spec_from_file_location('result_event_migration', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert text(module.DDL).compile(dialect=psycopg.dialect()).construct_params({}) == {}
