"""E10.3: real independent connections, existing disposable-schema infrastructure."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from threading import Barrier, Event
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import event as sa_event, text
from sqlalchemy.exc import DBAPIError, OperationalError

from src.malaria_dl.execution.contracts import ExecutionContext, ExecutionMode, RunEvent, RunEventType
from src.malaria_dl.execution.repository import ExecutionRepository
from src.malaria_dl.persistence.database import get_engine
from src.malaria_dl.persistence.result_repository import PostgresResultRepository
from src.malaria_dl.results import EventAcceptanceStatus as Status, ResultService
from src.malaria_dl.results.errors import EventIdConflict, ResultPersistenceError, SequenceConflict, SequenceGap, WriterNotAuthorized
from src.malaria_dl.results.identity import canonical_event
from test_campaigns_postgres import isolated, migration  # noqa: F401

pytestmark = [pytest.mark.requires_docker_postgres, pytest.mark.skipif(
    os.getenv('RUN_E10_POSTGRES_TESTS') != '1', reason='Explicit disposable-schema opt-in required')]
REVISION = '20260922_01_result_events'


def apply(c, name, operation='upgrade'):
    mod = migration(name)
    mod.op = Operations(MigrationContext.configure(c))
    getattr(mod, operation)()


def item(ctx, **changes):
    fields = dict(event_id=uuid4(), run_id=ctx.run_id, attempt_id=ctx.attempt_id,
                  sequence=1, event_type=RunEventType.EPOCH_COMPLETED,
                  occurred_at=datetime(2026, 9, 22, 13, tzinfo=timezone.utc), payload={'x': 1.0})
    return RunEvent(**(fields | changes))


@pytest.fixture
def pg(isolated, tmp_path):
    x = isolated
    for name in ('20260912_01_train_execution', '20260912_02_assessments',
                 '20260914_01_controlled_train', '20260914_02_global_execution',
                 '20260915_01_local_execution'):
        apply(x.c, name)
    row = x.freeze()
    token = uuid4()
    # A synthetic retained job satisfies the REAL global fencing function. No
    # shared advisory lock or operational job is acquired or replaced.
    x.c.execute(text("""INSERT INTO local_execution_jobs
        (id,principal,agent_id,owner,request_hash,campaign_id,state)
        VALUES(:id,'e10-fixture',:agent,:owner,:hash,:campaign,'held')"""),
        dict(id=uuid4(), agent=uuid4(), owner=token, hash='a'*64, campaign=row['id']))
    x.c.execute(text('UPDATE experiment_execution_gate SET owner=:owner'), {'owner': token})
    x.c.execute(text("SELECT set_config('capstone.execution_token',:token,true)"), {'token': str(token)})
    legacy = ExecutionRepository(x.repo.scope)
    session = legacy.claim(str(row['id']), str(uuid4()), 'synthetic', 1, tmp_path)
    legacy.put(session['run_id'], session['owner'], 'runtime', 'base', 'configuration', {'legacy': True})
    apply(x.c, REVISION)
    member = next(m for m in row['members'] if m['id'] == next(
        a['member_id'] for a in legacy.get(row['id'])['attempts'] if a['id'] == session['attempt_id']))
    ctx = ExecutionContext(run_id=session['run_id'], owner=session['owner'], attempt_id=session['attempt_id'],
        execution_mode=ExecutionMode.DOCKER, dataset_version_id=UUID(x.dataset['dataset_version_id']),
        model_id=session['configuration']['model_id'], adapter_version=session['configuration']['adapter_version'],
        campaign_id=row['id'], member_id=member['id'], configuration_hash=member['configuration_hash'], contract_hash=row['contract_hash'])
    x.make_visible()
    pids = []
    def factory():
        engine = get_engine()
        def configure(dbapi, record):
            with dbapi.cursor() as cursor:
                cursor.execute(f'SET search_path TO {x.schema},pg_catalog')
                cursor.execute("SET lock_timeout='5s'")
                cursor.execute("SET statement_timeout='15s'")
                cursor.execute('SELECT pg_backend_pid()')
                pids.append(cursor.fetchone()[0])
            dbapi.commit()
        sa_event.listen(engine, 'connect', configure)
        return engine
    @contextmanager
    def sql_scope():
        engine = factory()
        try:
            with engine.begin() as c:
                c.execute(text("SELECT set_config('capstone.execution_token',:token,true)"), {'token': str(token)})
                c.execute(text("SELECT set_config('capstone.train_owner',:owner,true)"), {'owner': str(ctx.owner)})
                yield c
        finally:
            engine.dispose()
    def repository(**kwargs):
        return PostgresResultRepository(execution_token=token, engine_factory=kwargs.get('factory', factory))
    def records():
        with sql_scope() as c:
            return c.execute(text('SELECT * FROM train_execution_records ORDER BY event_sequence NULLS FIRST')).mappings().all()
    return SimpleNamespace(ctx=ctx, factory=factory, repository=repository, sql=sql_scope,
                           records=records, pids=pids, schema=x.schema, token=token)


@pytest.mark.parametrize('kind', list(RunEventType))
def test_durable_roundtrip_all_types_without_state_mutation(pg, kind):
    event = item(pg.ctx, event_type=kind)
    with pg.sql() as c:
        before = c.execute(text('SELECT to_jsonb(r) FROM runs r WHERE id=:id'), {'id': pg.ctx.run_id}).scalar_one()
    result = ResultService(pg.repository()).accept_event(pg.ctx, event)
    assert result.status is Status.ACCEPTED
    # New repository/engine/connection: no acceptance state survives in Python.
    assert ResultService(pg.repository()).accept_event(pg.ctx, event).status is Status.DUPLICATE_ACCEPTED
    rows = pg.records()
    assert len(rows) == 2 and rows[0]['event_id'] is None
    saved = rows[1]
    assert saved['event_id'] == event.event_id and saved['event_sequence'] == 1
    assert saved['kind'] == 'e10_event' and saved['phase'] == 'run_event_v1'
    assert saved['payload'] == {'canonical_event': canonical_event(event)}
    assert RunEvent.from_dict(json.loads(saved['payload']['canonical_event'])) == event
    with pg.sql() as c:
        assert c.execute(text('SELECT to_jsonb(r) FROM runs r WHERE id=:id'), {'id': pg.ctx.run_id}).scalar_one() == before
        assert c.execute(text('SELECT state FROM train_execution_sessions WHERE run_id=:id'), {'id': pg.ctx.run_id}).scalar_one() == 'active'
    assert len(set(pg.pids)) >= 3


@pytest.mark.parametrize('left,right', [(1, 1.0), (True, 1), (0.0, -0.0), ('\x00', 'x'), ('\ud800', 'x')])
def test_canonical_text_survives_jsonb_normalization(pg, left, right):
    event = item(pg.ctx, payload={'value': left})
    service = ResultService(pg.repository())
    service.accept_event(pg.ctx, event)
    assert service.accept_event(pg.ctx, event).status is Status.DUPLICATE_ACCEPTED
    with pytest.raises(EventIdConflict):
        service.accept_event(pg.ctx, replace(event, payload={'value': right}))
    assert len(pg.records()) == 2


@pytest.mark.parametrize('field,value', [
    ('owner', uuid4()), ('attempt_id', uuid4()), ('dataset_version_id', uuid4()),
    ('model_id', 'wrong'), ('adapter_version', 'wrong'), ('campaign_id', uuid4()),
    ('member_id', uuid4()), ('configuration_hash', 'a'*64), ('contract_hash', 'a'*64),
])
def test_authoritative_fencing(pg, field, value):
    ctx = replace(pg.ctx, **{field: value})
    with pytest.raises(WriterNotAuthorized):
        ResultService(pg.repository()).accept_event(ctx, item(ctx))
    assert len(pg.records()) == 1


def test_runtime_does_not_change_authorization_and_optional_metadata(pg):
    ctx = replace(pg.ctx, execution_mode=ExecutionMode.LOCAL_PYTHON, campaign_id=None,
                  member_id=None, configuration_hash=None, contract_hash=None)
    assert ResultService(pg.repository()).accept_event(ctx, item(ctx)).status is Status.ACCEPTED


def test_gate_fencing_applies_to_duplicates(pg):
    event = item(pg.ctx)
    ResultService(pg.repository()).accept_event(pg.ctx, event)
    wrong = PostgresResultRepository(execution_token=uuid4(), engine_factory=pg.factory)
    with pytest.raises(WriterNotAuthorized):
        ResultService(wrong).accept_event(pg.ctx, event)
    with pg.sql() as c:
        c.execute(text('UPDATE experiment_execution_gate SET owner=NULL'))
    with pytest.raises(WriterNotAuthorized):
        ResultService(pg.repository()).accept_event(pg.ctx, event)
    assert len(pg.records()) == 2


def test_sequence_persists_and_legacy_does_not_count(pg):
    service = ResultService(pg.repository())
    first = item(pg.ctx)
    second = item(pg.ctx, sequence=2)
    with pytest.raises(SequenceGap):
        service.accept_event(pg.ctx, second)
    service.accept_event(pg.ctx, first)
    with pytest.raises(SequenceConflict):
        ResultService(pg.repository()).accept_event(pg.ctx, item(pg.ctx))
    service.accept_event(pg.ctx, second)
    assert ResultService(pg.repository()).accept_event(pg.ctx, first).status is Status.DUPLICATE_ACCEPTED
    assert [r['event_sequence'] for r in pg.records()] == [None, 1, 2]


@pytest.mark.parametrize('case', ['same_sequence', 'same_event', 'changed_event', 'invalid_writer'])
def test_independent_connections_race(pg, case):
    first = item(pg.ctx)
    other = first
    other_ctx = pg.ctx
    expected = Status.DUPLICATE_ACCEPTED
    if case == 'same_sequence':
        other = replace(first, event_id=uuid4()); expected = SequenceConflict
    elif case == 'changed_event':
        other = replace(first, payload={'different': 1}); expected = EventIdConflict
    elif case == 'invalid_writer':
        other_ctx = replace(pg.ctx, owner=uuid4()); expected = WriterNotAuthorized
    barrier = Barrier(2)
    def accept(pair):
        engine_factory = pg.factory
        def concurrent_factory():
            engine = engine_factory()
            # Ensure separate connections have opened before either can accept.
            def ready(dbapi, record):
                barrier.wait(timeout=10)
            sa_event.listen(engine, 'connect', ready)
            return engine
        try:
            return ResultService(pg.repository(factory=concurrent_factory)).accept_event(*pair).status
        except (EventIdConflict, SequenceConflict, WriterNotAuthorized) as exc:
            return type(exc)
    pg.pids.clear()
    with ThreadPoolExecutor(2) as pool:
        futures = [pool.submit(accept, pair) for pair in [(pg.ctx, first), (other_ctx, other)]]
        results = [future.result(timeout=20) for future in futures]
    assert results.count(Status.ACCEPTED) == 1 and results.count(expected) == 1
    assert len(set(pg.pids)) == 2
    assert len(pg.records()) == 2


def test_controlled_commit_failure_rolls_back_and_releases_locks(pg):
    def failing_factory():
        engine = pg.factory()
        def fail(connection):
            raise OperationalError('synthetic commit boundary', {}, RuntimeError('synthetic'))
        sa_event.listen(engine, 'commit', fail)
        return engine
    event = item(pg.ctx)
    with pytest.raises(ResultPersistenceError):
        ResultService(pg.repository(factory=failing_factory)).accept_event(pg.ctx, event)
    assert len(pg.records()) == 1
    assert ResultService(pg.repository()).accept_event(pg.ctx, event).status is Status.ACCEPTED


def test_body_rollback_and_waiting_writer_recovery(pg):
    event = item(pg.ctx)
    staged, release = Event(), Event()
    def rollback():
        with pytest.raises(RuntimeError):
            with pg.repository().acceptance_scope(pg.ctx, event) as scope:
                scope.append(); staged.set()
                assert release.wait(10)
                raise RuntimeError('controlled rollback')
    with ThreadPoolExecutor(2) as pool:
        aborted = pool.submit(rollback)
        assert staged.wait(10)
        retry = pool.submit(ResultService(pg.repository()).accept_event, pg.ctx, event)
        release.set()
        aborted.result(timeout=15)
        assert retry.result(timeout=15).status is Status.ACCEPTED
    assert len(pg.records()) == 2


def test_lost_ack_after_real_commit(pg):
    event = item(pg.ctx)
    def caller_loses_ack():
        ResultService(pg.repository()).accept_event(pg.ctx, event)
        raise ConnectionError('synthetic response loss after commit')
    with pytest.raises(ConnectionError):
        caller_loses_ack()
    before = pg.records()
    assert ResultService(pg.repository()).accept_event(pg.ctx, event).status is Status.DUPLICATE_ACCEPTED
    assert pg.records() == before


def test_migration_roundtrip_preserves_legacy_constraints_triggers_indexes(pg):
    with pg.sql() as c:
        def inventory():
            return (
                c.execute(text("SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='train_execution_records'::regclass ORDER BY conname")).all(),
                c.execute(text("SELECT tgname,tgenabled,pg_get_triggerdef(oid) FROM pg_trigger WHERE tgrelid='train_execution_records'::regclass ORDER BY tgname")).all(),
                c.execute(text("SELECT indexname,indexdef FROM pg_indexes WHERE schemaname=current_schema() AND tablename='train_execution_records' ORDER BY indexname")).all(),
            )
        upgraded = inventory()
        apply(c, REVISION, 'downgrade')
        old = inventory()
        assert any(row[0] == 'train_record_guard' and row[1] == 'O' for row in old[1])
        assert any(row[0] == 'train_execution_records_pkey' for row in old[0])
        assert len(old[2]) == 1
        assert c.execute(text('SELECT payload FROM train_execution_records')).scalar_one() == {'legacy': True}
        apply(c, REVISION)
        assert inventory() == upgraded
        assert c.execute(text('SELECT event_id,event_sequence FROM train_execution_records')).one() == (None, None)


def test_downgrade_refuses_to_destroy_event_identity(pg):
    ResultService(pg.repository()).accept_event(pg.ctx, item(pg.ctx))
    with pytest.raises(DBAPIError):
        with pg.sql() as c:
            apply(c, REVISION, 'downgrade')
    assert len(pg.records()) == 2


@pytest.mark.parametrize('operation', ['UPDATE train_execution_records SET payload=payload', 'DELETE FROM train_execution_records'])
def test_original_append_only_trigger_remains_active(pg, operation):
    ResultService(pg.repository()).accept_event(pg.ctx, item(pg.ctx))
    with pytest.raises(DBAPIError):
        with pg.sql() as c:
            c.execute(text(operation))
    assert len(pg.records()) == 2


def test_legacy_all_kinds_and_owner_guard_after_upgrade(pg):
    @contextmanager
    def legacy_scope(readonly=False):
        with pg.sql() as c:
            yield c
    repo = ExecutionRepository(legacy_scope)
    for kind in ('runtime','epoch','artifact_prepared','artifact','predictions','selection','phase','calibration'):
        repo.put(pg.ctx.run_id, pg.ctx.owner, kind, 'synthetic', '1', {'legacy': kind})
        repo.put(pg.ctx.run_id, pg.ctx.owner, kind, 'synthetic', '1', {'legacy': kind})
    assert len(pg.records()) == 9
    from src.malaria_dl.campaigns.contracts import CampaignError
    with pytest.raises(CampaignError):
        repo.put(pg.ctx.run_id, uuid4(), 'epoch', 'synthetic', '2', {})
    assert all(r['event_id'] is None and r['event_sequence'] is None for r in pg.records())


def test_raw_event_rejects_gap_and_wrong_envelope(pg):
    for sequence, payload in [(2, None), (1, {})]:
        event = item(pg.ctx, sequence=sequence)
        with pytest.raises(DBAPIError):
            with pg.sql() as c:
                c.execute(text("""INSERT INTO train_execution_records
                    (run_id,kind,phase,record_key,payload,event_id,event_sequence)
                    VALUES(:run,'e10_event','run_event_v1',:key,CAST(:payload AS jsonb),:id,:seq)"""),
                    dict(run=pg.ctx.run_id, key=str(event.event_id), id=event.event_id,
                         seq=sequence, payload=json.dumps(payload if payload is not None else {'canonical_event': canonical_event(event)})))
    assert len(pg.records()) == 1


def test_closed_session_rejects_retry_and_global_id_cannot_move_runs(pg, tmp_path):
    event = item(pg.ctx)
    ResultService(pg.repository()).accept_event(pg.ctx, event)
    @contextmanager
    def scope(readonly=False):
        with pg.sql() as c:
            yield c
    legacy = ExecutionRepository(scope)
    legacy.finish(pg.ctx.run_id, pg.ctx.owner, 'failed', cause='SYNTHETIC_END')
    with pytest.raises(WriterNotAuthorized):
        ResultService(pg.repository()).accept_event(pg.ctx, event)
    new = legacy.claim(pg.ctx.campaign_id, uuid4(), 'synthetic', 1, tmp_path / 'next')
    ctx = replace(pg.ctx, run_id=new['run_id'], attempt_id=new['attempt_id'], owner=new['owner'],
                  model_id=new['configuration']['model_id'], adapter_version=new['configuration']['adapter_version'],
                  member_id=None, configuration_hash=None)
    with pytest.raises(EventIdConflict):
        ResultService(pg.repository()).accept_event(ctx, replace(event, run_id=ctx.run_id, attempt_id=ctx.attempt_id))
    assert len(pg.records()) == 2
    assert ResultService(pg.repository()).accept_event(ctx, item(ctx)).status is Status.ACCEPTED


def test_controlled_reservation_and_event_after_migration(pg, tmp_path):
    from src.malaria_dl.execution.controlled import ControlledRepository
    @contextmanager
    def scope(readonly=False):
        with pg.sql() as c:
            yield c
    repo = ControlledRepository(scope)
    repo.finish(pg.ctx.run_id, pg.ctx.owner, 'failed', cause='SYNTHETIC_END')
    repo.pause(pg.ctx.campaign_id, 'SYNTHETIC_PAUSE')
    row = repo.get(pg.ctx.campaign_id)
    original = row['environment']
    current = {**original, 'source_sha256': 'f'*64}
    revision = uuid4()
    repo.register_revision(pg.ctx.campaign_id, revision, {
        'original_environment': original, 'environment': current, 'contract_hash': row['contract_hash'],
        'reason': 'synthetic', 'files': {'src/synthetic.py': 'a'*64},
        'tests': ['synthetic'], 'authorization': 'synthetic fixture only'})
    args = dict(campaign=pg.ctx.campaign_id, member=pg.ctx.member_id, previous=pg.ctx.attempt_id,
                dataset=pg.ctx.dataset_version_id, revision_id=revision, request_id=uuid4(),
                reason='synthetic', root=tmp_path / 'controlled', current=current)
    new, created = repo.reserve(**args)
    assert created
    repeated, created = repo.reserve(**args)
    assert not created and repeated['run_id'] == new['run_id']
    ctx = replace(pg.ctx, run_id=new['run_id'], attempt_id=new['attempt_id'], owner=new['owner'])
    assert ResultService(pg.repository()).accept_event(ctx, item(ctx)).status is Status.ACCEPTED
    assert repo.get(pg.ctx.campaign_id)['state'] == 'paused'


def test_postgres_snapshot_exposes_no_artificial_stale_holes(pg):
    event = item(pg.ctx)
    ResultService(pg.repository()).accept_event(pg.ctx, event)
    # On a contiguous append-only stream every stale slot remains occupied;
    # E10.2 must therefore prefer SEQUENCE_CONFLICT, not STALE_SEQUENCE.
    with pg.repository().acceptance_scope(pg.ctx, item(pg.ctx)) as scope:
        assert scope.state.last_sequence == 1
        assert scope.state.sequence_event.event_id == event.event_id


def test_raw_corrupt_canonical_is_detected_without_false_duplicate(pg):
    event = item(pg.ctx)
    with pg.sql() as c:
        c.execute(text("""INSERT INTO train_execution_records
            (run_id,kind,phase,record_key,payload,event_id,event_sequence)
            VALUES(:run,'e10_event','run_event_v1',:key,CAST(:payload AS jsonb),:id,1)"""),
            dict(run=pg.ctx.run_id, key=str(event.event_id), id=event.event_id,
                 payload=json.dumps({'canonical_event': canonical_event(replace(event, run_id=uuid4()))})))
    with pytest.raises(ResultPersistenceError):
        ResultService(pg.repository()).accept_event(pg.ctx, event)
    assert len(pg.records()) == 2


def test_session_lock_is_held_through_append_and_released_at_commit(pg):
    event = item(pg.ctx)
    with pg.repository().acceptance_scope(pg.ctx, event) as scope:
        scope.append()
        with pytest.raises(DBAPIError) as caught:
            with pg.sql() as other:
                other.execute(text('SELECT run_id FROM train_execution_sessions WHERE run_id=:run FOR UPDATE NOWAIT'), {'run': pg.ctx.run_id})
        assert caught.value.orig.sqlstate == '55P03'
    with pg.sql() as other:
        assert other.execute(text('SELECT run_id FROM train_execution_sessions WHERE run_id=:run FOR UPDATE NOWAIT'), {'run': pg.ctx.run_id}).scalar_one() == pg.ctx.run_id


def test_standalone_without_attempt_uses_same_fencing(pg, tmp_path):
    @contextmanager
    def scope(readonly=False):
        with pg.sql() as c:
            yield c
    legacy = ExecutionRepository(scope)
    original = legacy.session(pg.ctx.run_id)
    legacy.finish(pg.ctx.run_id, pg.ctx.owner, 'failed', cause='SYNTHETIC_END')
    session = legacy.standalone(original['configuration'], original['dataset'], original['environment'],
                                tmp_path / 'standalone', 'synthetic', 1, None)
    ctx = replace(pg.ctx, run_id=session['run_id'], owner=session['owner'], attempt_id=None,
                  campaign_id=None, member_id=None, configuration_hash=None, contract_hash=None)
    event = item(ctx)
    assert ResultService(pg.repository()).accept_event(ctx, event).status is Status.ACCEPTED
    assert ResultService(pg.repository()).accept_event(ctx, event).status is Status.DUPLICATE_ACCEPTED


def test_global_event_unique_index_rejects_direct_duplicate(pg):
    event = item(pg.ctx)
    ResultService(pg.repository()).accept_event(pg.ctx, event)
    with pytest.raises(DBAPIError) as caught:
        with pg.sql() as c:
            c.execute(text("""INSERT INTO train_execution_records
                (run_id,kind,phase,record_key,payload,event_id,event_sequence)
                VALUES(:run,'e10_event','run_event_v1',:key,CAST(:payload AS jsonb),:id,2)"""),
                dict(run=pg.ctx.run_id, key=str(event.event_id), id=event.event_id,
                     payload=json.dumps({'canonical_event': canonical_event(replace(event, sequence=2))})))
    assert caught.value.orig.sqlstate == '23505'
    assert len(pg.records()) == 2
