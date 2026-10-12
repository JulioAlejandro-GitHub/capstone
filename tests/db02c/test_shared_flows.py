"""Shared callers and local process boundary remain independent of schema diagnostics."""
import ast
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.malaria_dl.execution import campaign, global_gate
from src.malaria_dl.execution.repository import ExecutionRepository
from test_execution import BeforeTrain

ROOT = Path(__file__).resolve().parents[2]


def test_no_operational_import_or_structural_preflight() -> None:
    roots = (ROOT / 'malaria_dl_local_project/src', ROOT / 'backend_api/app')
    diagnostics = {'execution/schema.py', 'persistence/schema_contract.py'}
    forbidden = ('require_e10_schema', 'preflight_e10_schema', 'require_v2_capabilities',
                 'SUPPORTED_REVISIONS', 'E10SchemaNotReady', 'alembic_version',
                 'to_regclass', 'pg_get_functiondef', 'pg_get_triggerdef')
    for root in roots:
        for path in root.rglob('*.py'):
            if any(path.as_posix().endswith(name) for name in diagnostics):
                continue
            source = path.read_text()
            ast.parse(source)
            assert not any(name in source for name in forbidden), path


def test_local_child_uses_active_python_without_launch(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple] = []
    gate = SimpleNamespace(owner=str(uuid4()), require_healthy=lambda: None)
    token = global_gate.CURRENT.set(gate)

    def stop(argv: list[str], **kwargs: object) -> None:
        calls.append((argv, kwargs))
        raise BeforeTrain()

    monkeypatch.setattr(campaign.subprocess, 'Popen', stop)
    try:
        session = dict(run_id=uuid4(), owner=uuid4())
        with pytest.raises(BeforeTrain):
            campaign.run_child(session, ExecutionRepository())
    finally:
        global_gate.CURRENT.reset(token)
    argv, kwargs = calls[0]
    assert argv == [sys.executable, '-B', '-m', 'src.malaria_dl.execution.worker',
                    '--run-id', str(session['run_id']), '--owner', str(session['owner'])]
    assert kwargs['env']['CAPSTONE_EXECUTION_TOKEN'] == gate.owner
    assert kwargs['start_new_session'] is True


def test_ready_checks_real_connectivity_without_migrations(engine: Engine, statements: list[str],
                                                           monkeypatch: pytest.MonkeyPatch) -> None:
    from app.routes import health
    monkeypatch.setattr(health, 'get_primary_engine', lambda: engine)
    result = health.ready()
    assert result['status'] == 'ready'
    assert result['components'] == {'database': 'ready', 'storage': 'ready'}


def test_ready_rejects_unreachable_database(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.routes import health
    engine = create_engine('postgresql+psycopg://postgres@127.0.0.1:1/db02c_test', connect_args={'connect_timeout': 1})
    monkeypatch.setattr(health, 'get_primary_engine', lambda: engine)
    try:
        result = health.ready()
        assert result.status_code == 503
        assert json.loads(result.body)['components']['database'] == 'not_ready'
    finally:
        engine.dispose()


def test_scientific_results_missing_run_without_alembic(engine: Engine, statements: list[str]) -> None:
    from app.services.scientific_results import read_scientific_results
    with engine.connect() as c:
        assert read_scientific_results(c, uuid4()) is None


def test_live_local_preparation_rejects_missing_campaign(engine: Engine, statements: list[str]) -> None:
    from src.malaria_dl.campaigns.contracts import CampaignError
    from src.malaria_dl.execution.controlled import ControlledRepository
    from src.malaria_dl.local_execution.backend import LocalBackend
    backend = LocalBackend(ControlledRepository(), {})
    with pytest.raises(CampaignError, match='CAMPAIGN_NOT_FOUND'):
        backend.prepare(dict(campaign_id=str(uuid4()), dataset_id=str(uuid4())))
