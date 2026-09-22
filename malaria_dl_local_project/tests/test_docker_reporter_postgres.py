"""Real composition against E10.3's approved disposable PostgreSQL fixture."""
from contextlib import contextmanager
from dataclasses import replace
import os
from uuid import uuid4

import pytest
from sqlalchemy import event as sa_event, text
from sqlalchemy.exc import OperationalError

from src.malaria_dl.campaigns.contracts import digest
from src.malaria_dl.execution.artifacts import verify_session
from src.malaria_dl.execution.composition import build_docker_run_reporter
from src.malaria_dl.execution.contracts import RunEventType
from src.malaria_dl.execution.repository import ExecutionRepository
from src.malaria_dl.results.errors import (
    EventIdConflict, SequenceConflict, SequenceGap, WriterNotAuthorized, ResultPersistenceError,
)
from test_campaigns_postgres import isolated  # noqa: F401
from test_result_repository_postgres import pg, item  # noqa: F401

pytestmark = [pytest.mark.requires_docker_postgres, pytest.mark.skipif(
    os.getenv('RUN_E10_DOCKER_REPORTER_POSTGRES_TESTS') != '1', reason='Explicit disposable-schema opt-in required')]


def reporter(pg, context=None, factory=None):
    return build_docker_run_reporter(context or pg.ctx, execution_token=pg.token,
                                    engine_factory=factory or pg.factory)


def legacy_repository(pg):
    @contextmanager
    def scope(readonly=False):
        with pg.sql() as c:
            if readonly:
                c.execute(text('SET TRANSACTION READ ONLY'))
            yield c
    return ExecutionRepository(scope)


def snapshot(pg):
    with pg.sql() as c:
        return {
            table: c.execute(text(f'SELECT to_jsonb(t) FROM {table} t ORDER BY {key}')).scalars().all()
            for table, key in [('runs','id'), ('campaign_attempts','id'),
                               ('campaign_members','id'), ('train_execution_sessions','run_id')]
        }


@pytest.mark.parametrize('kind', [
    RunEventType.EPOCH_COMPLETED, RunEventType.ARTIFACT_PREPARED, RunEventType.ARTIFACT_CREATED,
    RunEventType.SELECTION_COMPLETED, RunEventType.CALIBRATION_COMPLETED,
    RunEventType.EVALUATION_COMPLETED, RunEventType.TRAINING_COMPLETED,
])
def test_real_composition_durable_retry_and_no_state_side_effects(pg, kind):
    before = snapshot(pg)
    first = item(pg.ctx, event_type=kind)
    second = item(pg.ctx, event_type=kind, sequence=2)
    chain = reporter(pg)
    assert chain.report(first) is None
    assert chain.report(second) is None
    rows = pg.records()
    assert len(rows) == 3 and [row['event_sequence'] for row in rows] == [None, 1, 2]
    assert chain.report(first) is None
    assert reporter(pg).report(first) is None  # entirely new reporter/service/repository
    assert pg.records() == rows
    assert snapshot(pg) == before  # includes every runs.parameters and all states


@pytest.mark.parametrize('case,error', [('id',EventIdConflict), ('sequence',SequenceConflict), ('gap',SequenceGap)])
def test_conflicts_propagate_without_extra_rows(pg, case, error):
    first = item(pg.ctx)
    chain = reporter(pg)
    chain.report(first)
    changed = {'id': replace(first, payload={'different': True}),
               'sequence': replace(first, event_id=uuid4()),
               'gap': replace(first, event_id=uuid4(), sequence=3)}[case]
    with pytest.raises(error):
        chain.report(changed)
    assert len(pg.records()) == 2


def test_wrong_owner_and_inactive_session_propagate(pg):
    event = item(pg.ctx)
    with pytest.raises(WriterNotAuthorized):
        reporter(pg, replace(pg.ctx, owner=uuid4())).report(event)
    assert len(pg.records()) == 1
    reporter(pg).report(event)
    legacy_repository(pg).finish(pg.ctx.run_id, pg.ctx.owner, 'failed', cause='SYNTHETIC_END')
    with pytest.raises(WriterNotAuthorized):
        reporter(pg).report(event)
    assert len(pg.records()) == 2


def test_commit_failure_is_not_success_and_retry_is_durable(pg):
    def failing_factory():
        engine = pg.factory()
        def fail(connection):
            raise OperationalError('controlled pre-commit', {}, RuntimeError('synthetic'))
        sa_event.listen(engine, 'commit', fail)
        return engine
    event = item(pg.ctx)
    with pytest.raises(ResultPersistenceError):
        reporter(pg, factory=failing_factory).report(event)
    assert len(pg.records()) == 1
    assert reporter(pg).report(event) is None
    assert len(pg.records()) == 2


def test_pure_readers_coexist_with_stable_legacy_records_hash(pg, tmp_path):
    from test_campaign_executor_e5 import evidence
    session, evidence_rows = evidence(tmp_path)
    session['run_id'] = str(pg.ctx.run_id)
    repo = legacy_repository(pg)
    for row in evidence_rows:
        if row['kind'] == 'runtime':
            continue  # fixture already has the identical legacy key
        if row['kind'] == 'artifact':
            row['payload']['run_id'] = str(pg.ctx.run_id)
        repo.put(pg.ctx.run_id, pg.ctx.owner, row['kind'], row['phase'], row['record_key'], row['payload'])
    legacy = repo.records(pg.ctx.run_id)
    session['completion']['records_hash'] = digest(legacy)
    assert verify_session(repo, session, lambda *_: None)['status'] == 'verified'
    before = snapshot(pg)
    reporter(pg).report(item(pg.ctx, event_type=RunEventType.TRAINING_COMPLETED))
    stored = pg.records()
    assert repo.records(pg.ctx.run_id) == repo.legacy_records(pg.ctx.run_id) == legacy
    assert all(set(row) == {'kind','phase','record_key','payload'} for row in legacy)
    assert len(repo.result_events(pg.ctx.run_id)) == 1
    assert digest(legacy) == session['completion']['records_hash']
    assert verify_session(repo, session, lambda *_: None)['records_hash'] == digest(legacy)
    with pg.sql() as c:
        c.execute(text('SET TRANSACTION READ ONLY'))
        calibration = c.execute(text("""SELECT payload FROM train_execution_records
            WHERE run_id=:run AND kind='calibration' AND phase='val' AND record_key='selected'"""),
            {'run': pg.ctx.run_id}).scalar_one()
    assert calibration == next(row['payload'] for row in legacy if row['kind'] == 'calibration')
    assert snapshot(pg) == before and pg.records() == stored
