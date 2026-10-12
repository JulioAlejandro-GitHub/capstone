"""Real SQL to the TRAIN launch boundary; no training/evaluation/explanation process."""
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4
from datetime import datetime, timezone
from dataclasses import replace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.engine import Connection, Engine

from src.malaria_dl.campaigns.contracts import CampaignError, member_configuration
from src.malaria_dl.data.governed_dataset import GovernedDatasetError
from src.malaria_dl.execution.campaign import execute_campaign
from src.malaria_dl.execution.global_gate import GlobalGate
from src.malaria_dl.execution.repository import ExecutionRepository


class BeforeTrain(BaseException):
    """Test-only stop; never interpreted as a successful child or an execution failure."""


def forbidden_launch(session: dict, repository: ExecutionRepository) -> int:
    raise BeforeTrain('Unexpected launch boundary in a rejection test')


@pytest.mark.parametrize('resume', [False, True])
def test_persisted_campaign_reaches_train_without_alembic(case: SimpleNamespace, statements: list[str], resume: bool) -> None:
    seen: list[dict] = []

    def stop(session: dict, repository: ExecutionRepository) -> int:
        seen.append(session)
        raise BeforeTrain()

    with GlobalGate('db02c-test') as gate:
        with pytest.raises(BeforeTrain):
            execute_campaign(case.repo, case.cid, case.artifacts, launch=stop, resume=resume)
        assert len(seen) == 1
        session = seen[0]
        first = case.row['members'][0]
        config = member_configuration(case.contract['matrix']['configurations'][first['configuration_hash']]['configuration'], first['seed'])
        assert session['configuration'] == config
        assert session['dataset'] == case.snapshot.metadata()
        assert session['environment'] == case.contract['environment']
        assert session['child_pid'] is None
        with case.engine.connect() as c:
            run = c.execute(text('SELECT * FROM runs WHERE id=:id'), {'id': session['run_id']}).mappings().one()
            projected = c.execute(text('SELECT * FROM run_configurations WHERE run_id=:id'), {'id': session['run_id']}).mappings().one()
            attempt = c.execute(text('SELECT * FROM campaign_attempts WHERE id=:id'), {'id': session['attempt_id']}).mappings().one()
            assert attempt['member_id'] == first['id'] and attempt['ordinal'] == 1
            assert attempt['training_run_id'] == run['id'] == session['run_id']
            assert str(run['campaign_id']) == case.cid
            assert str(run['dataset_version_id']) == str(case.snapshot.dataset_version_id)
            assert run['random_seed'] == config['resolved']['execution']['seed'] == 11
            assert projected['provenance_snapshot'] == config
            assert run['execution_parameters']['runtime_environment']['execution_mode'] == 'docker'
            assert run['execution_parameters']['runtime_environment']['python']
            for table in ('train_execution_records', 'artifacts', 'evaluations'):
                assert c.execute(text(f'SELECT count(*) FROM {table} WHERE run_id=:id'), {'id': run['id']}).scalar_one() == 0
        assert case.repo.get(case.cid)['members'][1]['state'] == 'pending'
        assert any('INSERT INTO run_configurations' in q for q in statements)
        try:
            assert_result_persistence(case, session, gate)
        finally:
            case.repo.finish(session['run_id'], session['owner'], 'interrupted', cause='DB02C_TEST_STOP_BEFORE_TRAIN')


def test_missing_campaign_is_rejected(engine: Engine, tmp_path: Path, statements: list[str]) -> None:
    with pytest.raises(CampaignError, match='CAMPAIGN_NOT_FOUND'):
        execute_campaign(ExecutionRepository(), str(uuid4()), tmp_path, launch=forbidden_launch)


def test_unreachable_database_is_reported(tmp_path: Path) -> None:
    engine = create_engine('postgresql+psycopg://postgres@127.0.0.1:1/db02c_test', connect_args={'connect_timeout': 1})

    @contextmanager
    def scope(readonly: bool = False) -> Iterator[Connection]:
        with engine.begin() as c:
            yield c

    try:
        with pytest.raises(OperationalError):
            execute_campaign(ExecutionRepository(scope), str(uuid4()), tmp_path, launch=forbidden_launch)
    finally:
        engine.dispose()


@pytest.mark.parametrize('damage', ['hash', 'missing_val'])
def test_invalid_dataset_rejected_before_attempt(case: SimpleNamespace, statements: list[str], damage: str) -> None:
    path = next((case.root / 'val').rglob('*.png'))
    if damage == 'hash':
        path.write_bytes(b'changed synthetic file')
    else:
        path.unlink()
    with pytest.raises(GovernedDatasetError, match='DATASET_CONTENT_(HASH|SET)_MISMATCH'):
        execute_campaign(case.repo, case.cid, case.artifacts, launch=forbidden_launch)
    row = case.repo.get(case.cid)
    assert row['state'] == 'frozen' and row['attempts'] == []


@pytest.mark.parametrize('statement,state', [
    ('SELECT * FROM db02c_missing_table', '42P01'),
    ('SELECT db02c_missing_column FROM experimental_campaigns', '42703'),
])
def test_actual_sql_error_is_preserved(engine: Engine, statement: str, state: str) -> None:
    with pytest.raises(ProgrammingError) as error:
        with ExecutionRepository().transaction(readonly=True) as c:
            c.execute(text(statement))
    assert error.value.orig.sqlstate == state


def test_restart_guard_preserves_sql_errors(engine: Engine, statements: list[str]) -> None:
    # Missing table in a transaction-local schema: no fallback to public.
    with engine.connect() as c, c.begin():
        c.execute(text('CREATE SCHEMA db02c_missing_stream'))
        c.execute(text('SET LOCAL search_path TO db02c_missing_stream'))

        @contextmanager
        def scope(readonly: bool = False) -> Iterator[Connection]:
            with c.begin_nested():
                yield c

        with pytest.raises(ProgrammingError) as error:
            ExecutionRepository(scope).preflight_result_events(uuid4())
        assert error.value.orig.sqlstate == '42P01'
        c.rollback()


def assert_result_persistence(case: SimpleNamespace, session: dict, gate: GlobalGate) -> None:
    """Synthetic heartbeat only; verify the shared durable writer and its fencing."""
    from src.malaria_dl.execution.contracts import RunEvent, RunEventType
    from src.malaria_dl.execution.worker import docker_context
    from src.malaria_dl.persistence.result_repository import PostgresResultRepository
    from src.malaria_dl.results import ResultService
    from src.malaria_dl.results.errors import WriterNotAuthorized
    from app.services.scientific_results import read_scientific_results

    row = case.repo.get(case.cid)
    attempt = next(a for a in row['attempts'] if a['id'] == session['attempt_id'])
    member = next(m for m in row['members'] if m['id'] == attempt['member_id'])
    ctx = docker_context(session, row, attempt, member)
    service = ResultService(PostgresResultRepository(execution_token=UUID(gate.owner)))
    event = RunEvent(event_id=uuid4(), run_id=ctx.run_id, attempt_id=ctx.attempt_id,
                     sequence=1, event_type=RunEventType.HEARTBEAT,
                     occurred_at=datetime.now(timezone.utc), payload={'source': 'db02c-test'})
    case.repo.preflight_result_events(ctx.run_id)
    assert service.accept_event(ctx, event).status.value == 'accepted'
    service.accept_event(ctx, event)
    assert case.repo.result_events(ctx.run_id) == [event]
    with pytest.raises(WriterNotAuthorized):
        service.accept_event(replace(ctx, owner=uuid4()), replace(event, event_id=uuid4(), sequence=2))
    with pytest.raises(CampaignError, match='E10_ACTIVE_STREAM_RECOVERY_UNSUPPORTED'):
        case.repo.preflight_result_events(ctx.run_id)
    with case.engine.connect() as c:
        results = read_scientific_results(c, ctx.run_id)
    assert results['contract_version'] == 'scientific_results_v2'
    assert len(results['run_configurations']) == 1
    assert results['evaluations'] == results['training_history'] == []


def test_dry_run_is_readonly_and_reports_eligible_member(case: SimpleNamespace, statements: list[str]) -> None:
    from src.malaria_dl.execution.campaign import dry_run
    before = case.repo.get(case.cid)
    report = dry_run(case.repo, case.cid, case.artifacts)
    assert report['writes'] == 0 and report['execution_ready']
    assert report['eligible_members'] == 2 and report['next_member']['seed'] == 11
    assert case.repo.get(case.cid) == before
    assert not any(q.lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'ALTER', 'CREATE')) for q in statements)
