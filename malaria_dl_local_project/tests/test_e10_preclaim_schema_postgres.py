"""OP1: real PostgreSQL catalogs and reservations, no TRAIN or public writes."""
import os
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from src.malaria_dl.execution.campaign import execute_campaign
from src.malaria_dl.execution.controlled import ControlledRepository, execute_one
from src.malaria_dl.execution.schema import E10SchemaNotReady
from src.malaria_dl.local_execution.backend import LocalBackend
from test_campaigns_postgres import isolated  # noqa: F401
from test_result_repository_postgres import apply, REVISION

pytestmark = [pytest.mark.requires_docker_postgres, pytest.mark.skipif(
    os.getenv('RUN_E10_POSTGRES_TESTS') != '1', reason='Disposable-schema opt-in required')]
TABLES = ('campaign_attempts', 'campaign_members', 'runs', 'train_execution_sessions',
          'local_execution_jobs', 'experimental_campaigns', 'experiment_execution_gate',
          'campaign_controlled_requests', 'train_execution_revisions')


def snapshot(c):
    return {table: c.execute(text(f'SELECT to_jsonb(t)::text FROM {table} t ORDER BY to_jsonb(t)::text')).scalars().all()
            for table in TABLES}


@pytest.fixture
def old(isolated):
    for name in ('20260912_01_train_execution', '20260912_02_assessments',
                 '20260914_01_controlled_train', '20260914_02_global_execution',
                 '20260915_01_local_execution'):
        apply(isolated.c, name)
    isolated.c.execute(text('CREATE TABLE alembic_version (version_num varchar(32) PRIMARY KEY)'))
    isolated.c.execute(text("INSERT INTO alembic_version VALUES ('20260915_01')"))
    row = isolated.freeze()
    return SimpleNamespace(s=isolated, repo=ControlledRepository(isolated.repo.scope), row=row)


def upgrade(x):
    apply(x.s.c, REVISION)
    x.s.c.execute(text("UPDATE alembic_version SET version_num='20260922_01'"))


def forbidden(*a, **kw):
    pytest.fail('No TRAIN, dataset preflight, reconciliation or loader may run here')


@pytest.mark.parametrize('entry', ['claim', 'reserve', 'campaign', 'resume', 'controlled',
                                   'local_prepare', 'local_claim_controlled', 'local_claim_sequential'])
def test_old_schema_rejects_before_any_mutation_or_budget_consumption(old, tmp_path, entry):
    x = old
    before = snapshot(x.s.c)
    assert not any(before[t] for t in ('campaign_attempts','runs','train_execution_sessions','local_execution_jobs'))
    args = dict(campaign=str(x.row['id']), member=str(x.row['members'][0]['id']),
                previous=str(uuid4()), dataset=str(x.row['dataset_version_id']), revision_id=str(uuid4()),
                request_id=str(uuid4()), reason='synthetic', root=tmp_path)
    data = dict(request_id=str(uuid4()), mode='controlled' if entry.endswith('controlled') else 'sequential')
    backend = LocalBackend(x.repo, {}, check=forbidden, loader=forbidden)
    mutations = []
    def capture(c, cursor, sql, params, ctx, many):
        if sql.lstrip().split()[0].upper() in ('INSERT','UPDATE','DELETE','CREATE','ALTER','DROP'):
            mutations.append(sql)
    event.listen(x.s.c, 'before_cursor_execute', capture)
    try:
        for _ in range(2):  # repeated failures cannot advance ordinal/budget
            with pytest.raises(E10SchemaNotReady, match='E10_SCHEMA_NOT_READY') as exc:
                if entry == 'claim': x.repo.claim(x.row['id'], uuid4(), 'synthetic', 1, tmp_path)
                elif entry == 'reserve': x.repo.reserve(**args, current=x.row['environment'])
                elif entry in ('campaign','resume'):
                    execute_campaign(x.repo, x.row['id'], tmp_path, resume=entry=='resume', check=forbidden, launch=forbidden, loader=forbidden)
                elif entry == 'controlled': execute_one(x.repo, **args, check=forbidden, launch=forbidden, loader=forbidden)
                elif entry == 'local_prepare': backend.prepare(data)
                else: backend.claim(data, 'synthetic')
            assert 'alembic_revision_20260922_01' in exc.value.missing
            assert snapshot(x.s.c) == before
        assert mutations == []
    finally:
        event.remove(x.s.c, 'before_cursor_execute', capture)


@pytest.mark.parametrize('damage,capability', [
    ("UPDATE alembic_version SET version_num='20260915_01'", 'alembic_revision_20260922_01'),
    ("UPDATE alembic_version SET version_num='20990101_01'", 'alembic_revision_20260922_01'),
    ('DROP TABLE alembic_version', 'alembic_revision_20260922_01'),
    ('ALTER TABLE train_execution_records DROP COLUMN event_id CASCADE', 'event_columns'),
    ('ALTER TABLE train_execution_records DROP COLUMN event_sequence CASCADE', 'event_columns'),
    ('ALTER TABLE train_execution_records DROP CONSTRAINT train_event_metadata', 'event_metadata_constraint'),
    ('ALTER TABLE train_execution_records DROP CONSTRAINT train_event_metadata; ALTER TABLE train_execution_records ADD CONSTRAINT train_event_metadata CHECK (true) NOT VALID', 'event_metadata_constraint'),
    ('ALTER TABLE train_execution_records DROP CONSTRAINT train_event_metadata; ALTER TABLE train_execution_records ADD CONSTRAINT train_event_metadata CHECK (true)', 'event_metadata_constraint'),
    ('CREATE OR REPLACE FUNCTION train_event_guard() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$', 'event_trigger_guard'),
    ('DROP INDEX train_event_id_unique', 'event_unique_indexes'),
    ('DROP INDEX train_event_sequence_unique', 'event_unique_indexes'),
    ('DROP INDEX train_event_sequence_unique; CREATE UNIQUE INDEX train_event_sequence_unique ON train_execution_records(run_id,event_id) WHERE event_sequence IS NOT NULL', 'event_unique_indexes'),
    ('ALTER TABLE train_execution_records DISABLE TRIGGER a_train_event_guard', 'event_trigger_guard'),
    ('DROP TRIGGER a_train_event_guard ON train_execution_records', 'event_trigger_guard'),
    ('ALTER FUNCTION train_event_guard() RESET search_path', 'event_trigger_guard'),
])
def test_stamp_alone_or_partial_installation_cannot_reserve(old, tmp_path, damage, capability):
    upgrade(old)
    assert old.repo.preflight_e10_schema()['revision'] == '20260922_01'
    old.s.c.execute(text(damage))
    before = snapshot(old.s.c)
    with pytest.raises(E10SchemaNotReady) as exc:
        old.repo.claim(old.row['id'], uuid4(), 'synthetic', 1, tmp_path)
    assert capability in exc.value.missing
    assert snapshot(old.s.c) == before


def test_ready_guard_is_readonly_and_existing_claim_rules_continue(old, tmp_path):
    upgrade(old)
    # Commit only our schema; use an independently READ ONLY connection.
    scope = old.s.make_visible()
    repo = ControlledRepository(scope)
    with scope(readonly=True) as c:
        assert c.execute(text('SHOW transaction_read_only')).scalar_one() == 'on'
        before = snapshot(c)
    assert repo.preflight_e10_schema()['event_trigger_guard']
    with scope(readonly=True) as c: assert snapshot(c) == before
    # Exercise real ownership and budget rules without invoking a worker. The
    # transaction advisory lock and gate row belong only to this synthetic test.
    with scope() as c:
        c.execute(text('SELECT pg_advisory_xact_lock(120994,1)'))
        token = uuid4()
        c.execute(text('UPDATE experiment_execution_gate SET owner=:token,db_pid=pg_backend_pid()'), {'token':token})
        c.execute(text("SELECT set_config('capstone.execution_token',:token,true)"), {'token':str(token)})
        @contextmanager
        def bound(readonly=False):
            with c.begin_nested(): yield c
        bound_repo = ControlledRepository(bound)
        s = bound_repo.claim(old.row['id'], uuid4(), 'synthetic', 1, tmp_path)
        assert s['state'] == 'active'
        after = snapshot(c)
        assert len(after['campaign_attempts']) == len(after['runs']) == len(after['train_execution_sessions']) == 1
        assert len(after['local_execution_jobs']) == 0
        assert bound_repo.get(old.row['id'])['attempts'][0]['ordinal'] == 1
        bound_repo.finish(s['run_id'], s['owner'], 'failed', cause='SYNTHETIC_NO_TRAIN')
        # Pending-first order is unchanged; failed member has retained its attempt.
        next_s = bound_repo.claim(old.row['id'], uuid4(), 'synthetic', 1, tmp_path)
        row = bound_repo.get(old.row['id'])
        assert len(row['attempts']) == 2 and next_s['attempt_id'] != s['attempt_id']
        assert len({a['member_id'] for a in row['attempts']}) == 2
        c.execute(text('UPDATE experiment_execution_gate SET owner=NULL,db_pid=NULL'))


# Existing disposable fixtures supply real revisions and historical failed attempts.
from test_controlled_train_postgres import control  # noqa: E402,F401
from test_global_execution_postgres import global_fixture  # noqa: E402,F401
from test_local_execution_postgres import local_ready  # noqa: E402,F401


@pytest.mark.parametrize('mode', ['controlled', 'sequential'])
def test_local_old_schema_keeps_existing_budget_then_upgrade_allows_claim(local_ready, mode):
    r = local_ready
    if mode == 'sequential': r.x.repo.resume(r.row['id'])
    data = dict(r.data, mode=mode)
    with r.x.repo.transaction() as c:
        apply(c, REVISION, 'downgrade')
        c.execute(text("UPDATE alembic_version SET version_num='20260915_01'"))
        before = snapshot(c)
    for _ in range(2):
        with pytest.raises(E10SchemaNotReady): r.backend.prepare(data)
        with pytest.raises(E10SchemaNotReady): r.backend.claim(data, 'synthetic')
        with r.x.repo.transaction(readonly=True) as c: assert snapshot(c) == before
    with r.x.repo.transaction() as c:
        apply(c, REVISION)
        c.execute(text("UPDATE alembic_version SET version_num='20260922_01'"))
    result = r.backend.claim(data, 'synthetic')
    assert r.backend.claim(data, 'synthetic') == result
    with r.x.repo.transaction(readonly=True) as c:
        after = snapshot(c)
        for name in ('campaign_attempts','runs','train_execution_sessions','local_execution_jobs'):
            assert len(after[name]) == len(before[name]) + 1
    # The frozen retry budget and failed historical attempt are preserved.
    row = r.x.repo.get(r.row['id'])
    assert row['protocol']['budget'] == r.row['protocol']['budget']
    attempts = [a for a in row['attempts'] if a['member_id'] == r.member['id']]
    assert sorted(a['ordinal'] for a in attempts) == [1,2]
    assert next(a for a in attempts if a['ordinal']==1)['state'] == 'failed'


def test_controlled_existing_request_and_recover_do_not_reserve_on_old_schema(control, monkeypatch):
    x = control
    s, created = x.repo.reserve(**x.args)
    assert created
    apply(x.s.c, REVISION, 'downgrade')
    x.s.c.execute(text("UPDATE alembic_version SET version_num='20260915_01'"))
    before = x.repo.get(x.row['id'])  # control predates Local tables
    repeated, created = x.repo.reserve(**x.args)
    assert not created and repeated['run_id'] == s['run_id']
    assert x.repo.get(x.row['id']) == before
    monkeypatch.setattr('src.malaria_dl.execution.campaign.dead_local', lambda s: True)
    result = x.repo.recover(x.row['id'], x.args['request_id'])
    assert result['state'] == 'interrupted' and result['launched'] is False
    row = x.repo.get(x.row['id'])
    assert len(row['attempts']) == len(before['attempts']) == 2
    assert row['protocol']['budget'] == before['protocol']['budget']
    # A NEW request on that same historical campaign is blocked before reservation.
    with pytest.raises(E10SchemaNotReady):
        x.repo.reserve(**dict(x.args, request_id=str(uuid4())))
    assert x.repo.get(x.row['id']) == row


@pytest.mark.parametrize('entry', ['campaign', 'resume', 'controlled'])
def test_cli_rejects_old_schema_before_acquiring_global_gate(old, monkeypatch, tmp_path, entry):
    from src.malaria_dl.execution import campaign, controlled, global_gate
    monkeypatch.setattr(global_gate, 'GlobalGate', forbidden)
    cid, did = str(old.row['id']), str(old.row['dataset_version_id'])
    with pytest.raises(E10SchemaNotReady):
        if entry in ('campaign','resume'):
            monkeypatch.setattr(campaign, 'ExecutionRepository', lambda: old.repo)
            args = ['--campaign-id',cid,'--dataset-version-id',did,'--artifact-root',str(tmp_path)]
            campaign.main(args + (['--resume'] if entry=='resume' else []))
        else:
            import sys
            monkeypatch.setattr(controlled, 'ControlledRepository', lambda: old.repo)
            monkeypatch.setattr(sys, 'argv', ['controlled','execute','--campaign-id',cid,
                '--dataset-version-id',did,'--member-id',str(uuid4()),
                '--previous-attempt-id',str(uuid4()),'--revision-id',str(uuid4()),
                '--request-id',str(uuid4()),'--reason','synthetic'])
            controlled.main()


def test_local_rechecks_before_first_job_write_after_prepare(local_ready):
    r = local_ready
    with r.x.repo.transaction(readonly=True) as c: before = snapshot(c)
    def change_revision(*args):
        with r.x.repo.transaction() as c:
            c.execute(text("UPDATE alembic_version SET version_num='20260915_01'"))
    r.backend.check = change_revision
    with pytest.raises(E10SchemaNotReady): r.backend.claim(r.data, 'synthetic')
    with r.x.repo.transaction(readonly=True) as c: assert snapshot(c) == before


def test_standalone_legacy_does_not_require_e10_schema(control, tmp_path):
    x = control
    apply(x.s.c, REVISION, 'downgrade')
    x.s.c.execute(text("UPDATE alembic_version SET version_num='20260915_01'"))
    with pytest.raises(E10SchemaNotReady): x.repo.preflight_e10_schema()
    before = x.repo.get(x.row['id'])
    original = x.first
    s = x.repo.standalone(original['configuration'], original['dataset'], original['environment'],
                          tmp_path, 'synthetic', 1, str(x.row['dataset_evidence_id']))
    assert s['attempt_id'] is None and s['state'] == 'active'
    assert x.repo.get(x.row['id']) == before
