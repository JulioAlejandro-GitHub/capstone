"""Local Python execution (Mac agent) tests: real PostgreSQL, disposable E4 schema only.

Covers section 12 of the local-execution fix: local-vs-Docker exclusivity, two local
agents racing, idempotency/ownership, heartbeat expiry, reconnection, paused-campaign
gating, single-attempt (no chaining), a sequential two-member run, subprocess failure,
persistence failure, invalid paths/hashes, and a genuine minimal calculation through
API -> agent -> subprocess TRAIN -> checkpoint -> API -> PostgreSQL.
"""
import json
import os
import socket
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text

from src.malaria_dl.campaigns.contracts import CampaignError, canonical, digest
from src.malaria_dl.execution.controlled import ControlledRepository
from src.malaria_dl.execution.global_gate import GlobalGate
from src.malaria_dl.local_execution import storage
from src.malaria_dl.local_execution.backend import LocalBackend

from test_campaigns_postgres import isolated, migration  # noqa: F401
from test_controlled_train_postgres import control  # noqa: F401
from test_global_execution_postgres import global_fixture  # noqa: F401
from test_campaigns_e4 import request as matrix_request, protocol

pytestmark = pytest.mark.skipif(os.getenv('RUN_LOCAL_EXECUTION_POSTGRES_TESTS') != '1', reason='Compose opt-in required')

ROOT = Path(__file__).resolve().parents[1]

LOCAL_ENVIRONMENT = {
    'execution_mode': 'local_python', 'platform': 'Darwin', 'machine': 'arm64',
    'device': 'CPU', 'precision': 'float32',
    'packages': {'tensorflow': '2.17.1', 'numpy': '1.26.4'},
    'determinism_environment': {'PYTHONHASHSEED': '42'},
    'source_sha256': 'd' * 64, 'python': '3.12.13', 'tensorflow': '2.17.1',
}


def synthetic_images(root, counts):
    from PIL import Image
    import numpy as np
    for split in ('train', 'val'):
        for i in range(counts[split]):
            label, colour = ('uninfected', 0) if i % 2 == 0 else ('parasitized', 255)
            folder = root / split / label
            folder.mkdir(parents=True, exist_ok=True)
            Image.fromarray(np.full((16, 16, 3), colour, dtype='uint8')).save(folder / (str(uuid4()) + '.png'))


def simulate_prior_failure(x, campaign_id, root):
    """One failed classic-mode attempt + pause, satisfying 20260914_02_global_execution's
    ownership guard WITHOUT going through GlobalGate: GlobalGate's exit releases its
    identity only once its own OS process has actually terminated, which never happens
    for the long-lived pytest process itself -- reusing it here would permanently poison
    this schema's gate for every later check in the same test (see
    test_two_coordinators_global_lock). A manually held session-scoped advisory lock,
    released and cleared explicitly, avoids that without bypassing the guard's intent."""
    token = str(uuid4())
    raw = x.s.c.engine.connect()
    try:
        raw.execute(text('SELECT pg_advisory_lock(120994,1)'))
        raw.execute(text(f'SET search_path TO {x.s.schema}, pg_catalog'))
        db_pid = raw.execute(text('SELECT pg_backend_pid()')).scalar_one()
        raw.execute(text("UPDATE experiment_execution_gate SET owner=CAST(:o AS uuid),db_pid=:p,"
                          "process_evidence='{}',blocked_reason=NULL,updated_at=clock_timestamp()"),
                    {'o': token, 'p': db_pid})
        raw.commit()

        @contextmanager
        def reentrant_scope(readonly=False):
            with raw.begin():
                raw.execute(text("SELECT set_config('capstone.execution_token',:t,true)"), {'t': token})
                yield raw

        fixture_repo = ControlledRepository(reentrant_scope)
        first = fixture_repo.claim(str(campaign_id), str(uuid4()), 'synthetic', 1, root)
        fixture_repo.finish(first['run_id'], first['owner'], 'failed', cause='SYNTHETIC_FAILURE')
        fixture_repo.pause(str(campaign_id), 'SYNTHETIC_PAUSE')
        return first
    finally:
        raw.execute(text("UPDATE experiment_execution_gate SET owner=NULL,db_pid=NULL,"
                          "process_evidence='{}',blocked_reason=NULL,updated_at=clock_timestamp()"))
        raw.commit()
        raw.execute(text('SELECT pg_advisory_unlock(120994,1)'))
        raw.commit()
        raw.close()


def register_local_revision(x, row):
    proposal = {
        'original_environment': row['environment'], 'environment': deepcopy(LOCAL_ENVIRONMENT),
        'contract_hash': row['contract_hash'], 'reason': 'local_python synthetic fixture',
        'files': {'malaria_dl_local_project/src/malaria_dl/local_execution/backend.py': 'a' * 64},
        'tests': ['synthetic'], 'authorization': 'synthetic fixture only',
    }
    revision_id = str(uuid4())
    x.repo.register_revision(row['id'], revision_id, proposal)
    return revision_id, proposal['environment']


@pytest.fixture
def local_ready(global_fixture, tmp_path):
    """A paused, single-member campaign with a real populated dataset root and a
    registered local_python technical revision, ready for LocalBackend.claim()."""
    x = global_fixture
    # global_fixture's make_visible() already committed the outer transaction, which
    # discards the fixture's original SET LOCAL search_path; restore it (non-LOCAL, so it
    # survives the savepoints x.s.service/x.s.c use below) before touching x.s.* directly.
    x.s.c.execute(text(f'SET search_path TO {x.s.schema}, pg_catalog'))
    mod = migration('20260915_01_local_execution')
    mod.op = Operations(MigrationContext.configure(x.s.c))
    mod.upgrade()
    dataset_root = tmp_path / 'dataset'
    synthetic_images(dataset_root, {'train': 2, 'val': 2})
    base = x.s.service.verifier(x.s.dataset['dataset_version_id'])
    eid = str(uuid4())
    snapshot = replace(base, dataset_root=dataset_root, evidence_id=eid)
    x.s.c.execute(text(
        "INSERT INTO audit_events(id,event_type,action,resource_type,resource_id,request_method,request_path,"
        "correlation_id,after_state,metadata,success) VALUES(CAST(:id AS uuid),'ml.dataset_verification','verify',"
        "'dataset_version',:dataset,'TEST','synthetic',CAST(:id AS text),CAST(:payload AS jsonb),'{}',true)"),
        {'id': eid, 'dataset': x.s.dataset['dataset_version_id'],
         'payload': canonical({'dataset_version_id': x.s.dataset['dataset_version_id'],
                                'snapshot': snapshot.metadata(), 'integrity_status': 'verified'})})
    x.s.service.verifier = lambda *a, **kw: snapshot
    req = matrix_request()
    req['models'] = ['custom_cnn']
    req['optimizers'] = ['adam']
    row = x.s.service.create(name='Local execution fixture', purpose='synthetic local_python test',
                              dataset_version_id=x.s.dataset['dataset_version_id'], request=req,
                              protocol=protocol(), actor='synthetic')
    row = x.s.service.freeze(str(row['id']))
    x.s.c.commit()  # visible to x.repo's own (fresh-connection) writes below
    first = simulate_prior_failure(x, row['id'], tmp_path / 'old')
    row = x.repo.get(row['id'])
    member = row['members'][0]
    revision_id, env = register_local_revision(x, row)
    artifacts_root = tmp_path / 'artifacts'
    artifacts_root.mkdir(parents=True)  # pre-provisioned storage, per the roots contract
    roots = {'dataset': dataset_root, 'artifacts': artifacts_root}
    backend = LocalBackend(x.repo, roots, check=lambda *a: None, loader=lambda *a: None)
    data = dict(campaign_id=str(row['id']), dataset_id=str(row['dataset_version_id']),
                member_id=str(member['id']), previous_attempt_id=str(first['attempt_id']),
                revision_id=revision_id, request_id=str(uuid4()), reason='local synthetic test',
                dataset_root_id='dataset', artifact_root_id='artifacts', mode='controlled',
                environment=env, agent_id=str(uuid4()))
    return SimpleNamespace(x=x, backend=backend, roots=roots, row=row, member=member,
                            first=first, revision_id=revision_id, env=env, data=data,
                            dataset_root=dataset_root, tmp_path=tmp_path)


def envelope(job):
    return {k: job[k] for k in ('job_id', 'agent_id', 'owner')}


def process_proof(pid=4242):
    return {'pid': pid, 'created_at': 123.0, 'host': 'synthetic-host', 'platform': 'Darwin'}


def exit_proof(job, code, remaining=None):
    proof = process_proof()
    return {'parent': proof, 'children': [], 'exit_code': code,
            'remaining': remaining or [], 'absence_proven': True, 'scope': 'synthetic'}


# ---------------------------------------------------------------------------
# Reservation: idempotency and ownership
# ---------------------------------------------------------------------------

def test_claim_is_idempotent_by_request_id(local_ready):
    r = local_ready
    job = r.backend.claim(r.data, 'admin-1')
    again = r.backend.claim(r.data, 'admin-1')
    assert again == job
    with r.x.repo.transaction(readonly=True) as c:
        count = c.execute(text('SELECT count(*) FROM local_execution_jobs')).scalar_one()
    assert count == 1


def test_claim_rejects_mismatched_repeat(local_ready):
    r = local_ready
    r.backend.claim(r.data, 'admin-1')
    mutated = dict(r.data, reason='different reason text')
    with pytest.raises(CampaignError, match='LOCAL_REQUEST_CONFLICT'):
        r.backend.claim(mutated, 'admin-1')
    with pytest.raises(CampaignError, match='LOCAL_REQUEST_CONFLICT'):
        r.backend.claim(r.data, 'admin-2')


def test_owner_and_agent_fencing(local_ready):
    r = local_ready
    job = r.backend.claim(r.data, 'admin-1')
    good = envelope(job)
    with pytest.raises(CampaignError, match='LOCAL_OWNER_FENCED'):
        r.backend.operation('heartbeat', {**good, 'owner': str(uuid4())}, 'admin-1')
    with pytest.raises(CampaignError, match='LOCAL_OWNER_FENCED'):
        r.backend.operation('heartbeat', {**good, 'agent_id': str(uuid4())}, 'admin-1')
    with pytest.raises(CampaignError, match='LOCAL_OWNER_FENCED'):
        r.backend.operation('heartbeat', good, 'admin-2')
    assert r.backend.operation('heartbeat', {**good, 'process': process_proof()}, 'admin-1')['accepted']


# ---------------------------------------------------------------------------
# Local vs Docker exclusivity, both directions
# ---------------------------------------------------------------------------

def test_local_job_blocks_docker_gate_while_held(local_ready):
    r = local_ready
    r.backend.claim(r.data, 'admin-1')
    with pytest.raises(CampaignError, match='PROCESS_TREE_RELEASE_UNPROVEN'):
        with GlobalGate('docker-coordinator', engine_factory=r.x.factory):
            pytest.fail('docker coordinator acquired the gate during an active local job')


def test_docker_gate_blocks_local_claim(local_ready):
    r = local_ready
    with GlobalGate('docker-coordinator', engine_factory=r.x.factory):
        # Docker holds the session-scoped advisory lock for its whole run, so the local
        # claim's own pg_try_advisory_xact_lock fails immediately (GLOBAL_EXPERIMENT_BUSY);
        # GLOBAL_EXECUTION_BLOCKED is the narrower case where the lock is free but a gate
        # owner is still recorded.
        with pytest.raises(CampaignError, match='GLOBAL_EXPERIMENT_BUSY'):
            r.backend.claim(r.data, 'admin-1')


def test_two_local_agents_race_claim(local_ready):
    r = local_ready
    backend2 = LocalBackend(ControlledRepository(r.x.repo.scope), r.roots, check=lambda *a: None)
    barrier = Barrier(2)

    def attempt(backend, request_id):
        data = dict(r.data, request_id=request_id, agent_id=str(uuid4()))
        barrier.wait(timeout=5)
        try:
            return backend.claim(data, 'admin-1')
        except CampaignError:
            return None

    with ThreadPoolExecutor(2) as pool:
        a = pool.submit(attempt, r.backend, str(uuid4()))
        b = pool.submit(attempt, backend2, str(uuid4()))
        results = [a.result(timeout=15), b.result(timeout=15)]
    assert sum(x is not None for x in results) == 1
    assert len(r.x.repo.get(r.row['id'])['attempts']) == 2  # original failure + one new active


# ---------------------------------------------------------------------------
# Heartbeat expiry, reconnection, duplicate reports
# ---------------------------------------------------------------------------

def test_heartbeat_expiry_reports_uncertain_without_releasing(local_ready):
    r = local_ready
    job = r.backend.claim(r.data, 'admin-1')
    good = envelope(job)
    r.backend.operation('heartbeat', {**good, 'process': process_proof()}, 'admin-1')
    with r.x.repo.transaction() as c:
        c.execute(text("UPDATE local_execution_jobs SET heartbeat_at=clock_timestamp()-interval '90 seconds' "
                        "WHERE id=CAST(:id AS uuid)"), {'id': good['job_id']})
    status = r.backend.operation('status', good, 'admin-1')
    assert status['communication'] == 'uncertain' and status['state'] == 'held' and not status['released']


def test_reconnect_and_duplicate_reports_are_idempotent(local_ready):
    r = local_ready
    job = r.backend.claim(r.data, 'admin-1')
    good = envelope(job)
    proof = process_proof()
    first = r.backend.operation('heartbeat', {**good, 'process': proof}, 'admin-1')
    second = r.backend.operation('heartbeat', {**good, 'process': proof}, 'admin-1')
    assert first == second == {'accepted': True, 'may_launch': True}
    payload = {'path': {'root_id': job['artifact_root_id'], 'relative_path': job['run_id'] + '/1.keras'}}
    Path(r.roots['artifacts'], job['run_id']).mkdir(parents=True)
    artifact_path = Path(r.roots['artifacts'], job['run_id'], '1.keras')
    artifact_path.write_bytes(b'synthetic checkpoint content')
    identity = storage.identity(artifact_path)
    record = {'kind': 'artifact', 'phase': 'base', 'key': '1', 'payload': {**payload, **identity}, **good}
    r.backend.operation('record', record, 'admin-1')
    r.backend.operation('record', record, 'admin-1')  # duplicate report, same payload
    assert len(r.backend.operation('records', good, 'admin-1')['records']) == 1
    # Explicit reconnection status query never mutates state.
    status = r.backend.operation('status', good, 'admin-1')
    assert status['state'] == 'held'


# ---------------------------------------------------------------------------
# Paused-campaign gating and single-attempt (no chaining)
# ---------------------------------------------------------------------------

def test_controlled_mode_requires_paused_campaign(local_ready):
    r = local_ready
    r.x.repo.resume(r.row['id'])
    with pytest.raises(CampaignError, match='CAMPAIGN_PAUSE_CONFLICT'):
        r.backend.claim(r.data, 'admin-1')


def test_sequential_mode_rejects_paused_and_accepts_active(local_ready):
    r = local_ready
    sequential = dict(r.data, mode='sequential', request_id=str(uuid4()))
    with pytest.raises(CampaignError, match='CAMPAIGN_PAUSE_CONFLICT'):
        r.backend.claim(sequential, 'admin-1')
    r.x.repo.resume(r.row['id'])
    job = r.backend.claim(sequential, 'admin-1')
    assert job['mode'] == 'sequential'


def test_single_controlled_attempt_does_not_chain(local_ready):
    r = local_ready
    job = r.backend.claim(r.data, 'admin-1')
    finish_job(r.backend, job, exit_code=0)
    # No new job auto-appears, and reusing the same eligibility args is now rejected
    # because the member is no longer failed/interrupted -- proving no auto-chaining.
    with r.x.repo.transaction(readonly=True) as c:
        held = c.execute(text("SELECT count(*) FROM local_execution_jobs WHERE state IN ('held','calculation_reported')")).scalar_one()
    assert held == 0
    with pytest.raises(CampaignError):
        r.backend.claim(dict(r.data, request_id=str(uuid4()), agent_id=str(uuid4())), 'admin-1')


def synthetic_local_train(backend, job):
    """Mirrors test_campaign_executor_postgres.synthetic_train, but through the
    LocalBackend record/calculation-ended operations instead of repo.put directly."""
    good = envelope(job)
    run_dir = Path(backend.roots[job['artifact_root_id']], job['run_id'])
    run_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = run_dir / '1.keras'
    checkpoint.write_bytes(b'synthetic checkpoint')
    identity = storage.identity(checkpoint)
    selection = {'selected_epoch': 1}
    payloads = {
        ('runtime', 'configuration'): {'synthetic': True},
        ('epoch', '1'): {'epoch': 1},
        ('artifact_prepared', '1'): {'epoch': 1},
        ('artifact', '1'): {'path': {'root_id': job['artifact_root_id'], 'relative_path': job['run_id'] + '/1.keras'},
                             'epoch': 1, 'run_id': job['run_id'], **identity},
        ('predictions', '1'): {'samples': [{'sample': 'val/a'}, {'sample': 'val/b'}]},
        ('selection', '1'): selection,
        ('phase', 'completed'): {'epochs': 1},
    }
    for (kind, key), payload in payloads.items():
        backend.operation('record', {'kind': kind, 'phase': 'base', 'key': key, 'payload': payload, **good}, 'admin-1')
    backend.operation('record', {'kind': 'calibration', 'phase': 'val', 'key': 'selected',
                                  'payload': {'synthetic': True}, **good}, 'admin-1')
    records = backend.operation('records', good, 'admin-1')['records']
    evidence = {'epochs': 1, 'selection': selection, 'records_hash': digest(records)}
    backend.operation('calculation-ended', {**good, 'evidence': evidence}, 'admin-1')


def finish_job(backend, job, exit_code, remaining=None):
    good = envelope(job)
    proof = process_proof()
    backend.operation('heartbeat', {**good, 'process': proof}, 'admin-1')
    if exit_code == 0:
        synthetic_local_train(backend, job)
    proof_full = {'parent': proof, 'children': [], 'exit_code': exit_code,
                  'remaining': remaining or [], 'absence_proven': True, 'scope': 'synthetic'}
    return backend.operation('exit', {**good, 'proof': proof_full}, 'admin-1')


# ---------------------------------------------------------------------------
# Sequential two-member mock sequence
# ---------------------------------------------------------------------------

@pytest.fixture
def local_sequential(global_fixture, tmp_path):
    x = global_fixture
    # global_fixture's make_visible() already committed the outer transaction, which
    # discards the fixture's original SET LOCAL search_path; restore it (non-LOCAL, so it
    # survives the savepoints x.s.service/x.s.c use below) before touching x.s.* directly.
    x.s.c.execute(text(f'SET search_path TO {x.s.schema}, pg_catalog'))
    mod = migration('20260915_01_local_execution')
    mod.op = Operations(MigrationContext.configure(x.s.c))
    mod.upgrade()
    dataset_root = tmp_path / 'dataset'
    synthetic_images(dataset_root, {'train': 2, 'val': 2})
    base = x.s.service.verifier(x.s.dataset['dataset_version_id'])
    eid = str(uuid4())
    snapshot = replace(base, dataset_root=dataset_root, evidence_id=eid)
    x.s.c.execute(text(
        "INSERT INTO audit_events(id,event_type,action,resource_type,resource_id,request_method,request_path,"
        "correlation_id,after_state,metadata,success) VALUES(CAST(:id AS uuid),'ml.dataset_verification','verify',"
        "'dataset_version',:dataset,'TEST','synthetic',CAST(:id AS text),CAST(:payload AS jsonb),'{}',true)"),
        {'id': eid, 'dataset': x.s.dataset['dataset_version_id'],
         'payload': canonical({'dataset_version_id': x.s.dataset['dataset_version_id'],
                                'snapshot': snapshot.metadata(), 'integrity_status': 'verified'})})
    x.s.service.verifier = lambda *a, **kw: snapshot
    req = matrix_request(seeds=[11, 12])
    req['models'] = ['custom_cnn']
    req['optimizers'] = ['adam']
    row = x.s.service.create(name='Local sequential fixture', purpose='synthetic local_python test',
                              dataset_version_id=x.s.dataset['dataset_version_id'], request=req,
                              protocol=protocol(), actor='synthetic')
    row = x.s.service.freeze(str(row['id']))
    x.s.c.commit()  # visible to x.repo's own (fresh-connection) writes below
    # register_revision() always requires a paused campaign (the E9.3 controlled-attempt
    # convention); a sequential-mode revision still needs to be prepared that way, then
    # the campaign resumes to frozen/active for sequential claim() to accept it.
    x.repo.pause(row['id'], 'SYNTHETIC_PAUSE_FOR_REVISION')
    revision_id, env = register_local_revision(x, row)
    x.repo.resume(row['id'])
    artifacts_root = tmp_path / 'artifacts'
    artifacts_root.mkdir(parents=True)  # pre-provisioned storage, per the roots contract
    roots = {'dataset': dataset_root, 'artifacts': artifacts_root}
    backend = LocalBackend(x.repo, roots, check=lambda *a: None, loader=lambda *a: None)
    return SimpleNamespace(x=x, backend=backend, roots=roots, row=x.repo.get(row['id']),
                            revision_id=revision_id, env=env)


def test_sequential_two_experiments_in_a_row(local_sequential):
    r = local_sequential
    seen = set()
    for _ in range(2):
        data = dict(campaign_id=str(r.row['id']), dataset_id=str(r.row['dataset_version_id']),
                    member_id='', previous_attempt_id='', revision_id=r.revision_id,
                    request_id=str(uuid4()), reason='sequential synthetic', dataset_root_id='dataset',
                    artifact_root_id='artifacts', mode='sequential', environment=r.env, agent_id=str(uuid4()))
        job = r.backend.claim(data, 'admin-1')
        assert job['run_id'] not in seen
        seen.add(job['run_id'])
        result = finish_job(r.backend, job, exit_code=0)
        assert result['state'] == 'verified' and result['released']
    assert len(seen) == 2


# ---------------------------------------------------------------------------
# Subprocess failure and process-absence proof
# ---------------------------------------------------------------------------

def test_subprocess_failure_marks_failed_and_pauses_campaign(local_ready):
    r = local_ready
    job = r.backend.claim(r.data, 'admin-1')
    result = finish_job(r.backend, job, exit_code=137)
    assert result['state'] == 'failed' and result['released']
    assert r.x.repo.get(r.row['id'])['state'] == 'paused'


def test_exit_requires_proven_absence_of_remaining_processes(local_ready):
    r = local_ready
    job = r.backend.claim(r.data, 'admin-1')
    good = envelope(job)
    proof = process_proof()
    r.backend.operation('heartbeat', {**good, 'process': proof}, 'admin-1')
    stray = {'parent': proof, 'children': [], 'exit_code': 0, 'remaining': [proof], 'absence_proven': False}
    with pytest.raises(CampaignError, match='LOCAL_PROCESS_ABSENCE_UNPROVEN'):
        r.backend.operation('exit', {**good, 'proof': stray}, 'admin-1')


# ---------------------------------------------------------------------------
# Persistence / communication failure
# ---------------------------------------------------------------------------

def test_persistence_rejection_leaves_no_false_record(local_ready):
    r = local_ready
    job = r.backend.claim(r.data, 'admin-1')
    good = envelope(job)
    with r.x.repo.transaction() as c:
        c.execute(text("CREATE FUNCTION mock_local_failure() RETURNS trigger LANGUAGE plpgsql AS $$ "
                        "BEGIN RAISE EXCEPTION 'MOCK_LOCAL_PERSISTENCE_FAILURE' USING ERRCODE='23514'; END $$"))
        c.execute(text('CREATE TRIGGER mock_local_failure BEFORE INSERT ON train_execution_records '
                        "FOR EACH ROW WHEN (NEW.kind='epoch') EXECUTE FUNCTION mock_local_failure()"))
    record = {'kind': 'epoch', 'phase': 'base', 'key': '1', 'payload': {'epoch': 1}, **good}
    with pytest.raises(Exception):
        r.backend.operation('record', record, 'admin-1')
    assert r.backend.operation('records', good, 'admin-1')['records'] == []


# ---------------------------------------------------------------------------
# Invalid paths and hashes (storage.py)
# ---------------------------------------------------------------------------

def test_resolve_rejects_escape_and_symlink(tmp_path):
    root = tmp_path / 'root'
    root.mkdir()
    (root / 'inside').write_bytes(b'x')
    with pytest.raises(ValueError, match='INVALID_RELATIVE_PATH'):
        storage.resolve(root, '../outside')
    with pytest.raises(ValueError, match='INVALID_RELATIVE_PATH'):
        storage.resolve(root, '/absolute')
    outside = tmp_path / 'outside'
    outside.write_bytes(b'y')
    (root / 'link').symlink_to(outside)
    with pytest.raises(ValueError, match='SYMLINK_FORBIDDEN'):
        storage.resolve(root, 'link')


def test_identity_rejects_partial_and_verify_samples_rejects_test_split(tmp_path):
    partial = tmp_path / 'a.partial'
    partial.write_bytes(b'x')
    with pytest.raises(ValueError, match='ARTIFACT_NOT_FINAL'):
        storage.identity(partial)
    root = tmp_path / 'dataset'
    (root / 'test' / 'uninfected').mkdir(parents=True)
    sample_path = root / 'test' / 'uninfected' / 'p.png'
    sample_path.write_bytes(b'img')
    identity = storage.identity(sample_path)
    with pytest.raises(ValueError, match='TEST_FORBIDDEN'):
        storage.verify_samples(root, [{'split': 'test', 'relative_path': 'test/uninfected/p.png', **identity}])
    with pytest.raises(ValueError):
        storage.verify_samples(root, [{'split': 'train', 'relative_path': 'test/uninfected/p.png', **identity}])


def test_artifact_hash_conflict_and_owner_conflict(local_ready):
    r = local_ready
    job = r.backend.claim(r.data, 'admin-1')
    good = envelope(job)
    run_dir = Path(r.roots['artifacts'], job['run_id'])
    run_dir.mkdir(parents=True)
    artifact_path = run_dir / '1.keras'
    artifact_path.write_bytes(b'real content')
    bad_payload = {'path': {'root_id': job['artifact_root_id'], 'relative_path': job['run_id'] + '/1.keras'},
                   'sha256': 'f' * 64, 'bytes': 7}
    with pytest.raises(CampaignError, match='LOCAL_ARTIFACT_HASH_CONFLICT'):
        r.backend.operation('record', {'kind': 'artifact', 'phase': 'base', 'key': '1', 'payload': bad_payload, **good}, 'admin-1')
    foreign_payload = {'path': {'root_id': job['artifact_root_id'], 'relative_path': str(uuid4()) + '/1.keras'},
                        **storage.identity(artifact_path)}
    with pytest.raises(CampaignError, match='LOCAL_ARTIFACT_OWNER_CONFLICT'):
        r.backend.operation('record', {'kind': 'artifact', 'phase': 'base', 'key': '1', 'payload': foreign_payload, **good}, 'admin-1')


# ---------------------------------------------------------------------------
# Exclusivity released only when appropriate
# ---------------------------------------------------------------------------

def test_gate_owner_persists_until_exit(local_ready):
    r = local_ready
    job = r.backend.claim(r.data, 'admin-1')
    good = envelope(job)
    with r.x.repo.transaction(readonly=True) as c:
        owner = c.execute(text('SELECT owner FROM experiment_execution_gate')).scalar_one()
    assert str(owner) == job['owner']
    r.backend.operation('heartbeat', {**good, 'process': process_proof()}, 'admin-1')
    r.backend.operation('calculation-ended', {**good, 'evidence': {'epochs': 0}}, 'admin-1')
    with r.x.repo.transaction(readonly=True) as c:
        owner = c.execute(text('SELECT owner FROM experiment_execution_gate')).scalar_one()
    assert owner is not None  # still held after calculation-ended, before exit
    finish_job(r.backend, job, exit_code=137)
    with r.x.repo.transaction(readonly=True) as c:
        owner = c.execute(text('SELECT owner FROM experiment_execution_gate')).scalar_one()
    assert owner is None


# ---------------------------------------------------------------------------
# Route-level dispatch and authorization (direct handler call, per test_governance_api.py pattern)
# ---------------------------------------------------------------------------

def test_route_dispatch_and_error_mapping(local_ready, monkeypatch):
    sys.path.insert(0, str(ROOT.parent / 'backend_api'))
    try:
        from app.routes import local_execution as route_module
        from app.security import Permission, Principal
    finally:
        sys.path.remove(str(ROOT.parent / 'backend_api'))
    r = local_ready
    principal = Principal('admin-1', 'admin', ('administrator',), frozenset({Permission.SYSTEM_ADMIN}))
    value = route_module.local_operation('dry-run', r.data, principal, r.backend)
    assert 'execution_ready' in value
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as excinfo:
        route_module.local_operation('bogus-operation', r.data, principal, r.backend)
    assert excinfo.value.status_code == 404
    r.backend.claim(r.data, 'admin-1')
    mutated = dict(r.data, reason='a different reason than the original claim')
    with pytest.raises(HTTPException) as excinfo:
        route_module.local_operation('claim', mutated, principal, r.backend)
    assert excinfo.value.status_code == 409


# ---------------------------------------------------------------------------
# Closing minimal real calculation: API -> agent -> subprocess TRAIN -> checkpoint -> API -> PostgreSQL
# ---------------------------------------------------------------------------

def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def test_minimal_real_calculation_through_http_agent_and_subprocess(local_ready, monkeypatch):
    """Real uvicorn (native process), real agent/worker subprocesses, real fit,
    real checkpoint hash, committed PostgreSQL readback from a fresh connection.
    No Docker, no operational campaign/dataset -- only this fixture's disposable schema.

    LocalBackend.claim() always runs inside the Linux Docker backend in production and
    cross-checks /proc for a live Docker-mode coordinator (see backend.py); that scan is
    structurally Linux-only and is already exercised for real on Linux by
    test_local_job_blocks_docker_gate_while_held / test_docker_gate_blocks_local_claim
    above. Running the throwaway HTTP server natively here (the only way to also prove
    real TensorFlow fit + checkpoint serialization on actual macOS/arm64, which is this
    test's point) has no /proc to scan, so that one sub-check is stubbed for this test only."""
    import uvicorn
    from fastapi import FastAPI
    from src.malaria_dl.local_execution import backend as backend_module
    monkeypatch.setattr(backend_module, 'process_table', lambda: {})

    backend_dir = ROOT.parent / 'backend_api'
    sys.path.insert(0, str(backend_dir))
    try:
        from app.routes import local_execution as route_module
        from app.security import Permission, Principal, current_principal
    finally:
        sys.path.remove(str(backend_dir))

    r = local_ready
    data = dict(r.data, request_id=str(uuid4()))  # controlled mode, matching local_ready's paused campaign
    # local_ready's own backend uses a no-op loader (for the mock-style tests above); this
    # closing test needs the REAL default loader, so its checkpoint verification is genuine.
    real_backend = LocalBackend(ControlledRepository(r.x.repo.scope), r.roots, check=lambda *a: None)
    app = FastAPI()
    app.include_router(route_module.router)
    app.dependency_overrides[current_principal] = lambda: Principal(
        'agent-test', 'agent', ('administrator',), frozenset({Permission.SYSTEM_ADMIN}))
    app.dependency_overrides[route_module.service] = lambda: real_backend

    port = free_port()
    config = uvicorn.Config(app, host='127.0.0.1', port=port, log_level='warning')
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.time() + 15
        while not server.started and time.time() < deadline:
            time.sleep(0.1)
        assert server.started

        config_path = r.tmp_path / 'agent_config.json'
        config_path.write_text(json.dumps({
            'url': f'http://127.0.0.1:{port}',
            'request': data,
            'roots': {k: str(v) for k, v in r.roots.items()},
        }))
        state_path = r.tmp_path / 'agent_state.json'
        env = {**os.environ, 'CAPSTONE_AGENT_BEARER': 'synthetic-token'}
        import subprocess
        result = subprocess.run(
            [sys.executable, '-B', '-m', 'src.malaria_dl.local_execution.agent', 'start',
             '--config', str(config_path), '--state', str(state_path)],
            cwd=str(ROOT), env=env, capture_output=True, timeout=300,
        )
        assert result.returncode == 0, result.stdout.decode() + result.stderr.decode()
        output = json.loads(result.stdout.decode().strip().splitlines()[-1])
        run_id = output['run_id']
        assert output['result']['state'] == 'verified' and output['result']['released']
    finally:
        server.should_exit = True
        thread.join(timeout=15)

    # Fresh connection, independent of the agent's own reporting round trip.
    with r.x.repo.transaction(readonly=True) as c:
        state = c.execute(text('SELECT state FROM train_execution_sessions WHERE run_id=CAST(:id AS uuid)'),
                           {'id': run_id}).scalar_one()
    assert state == 'verified'
