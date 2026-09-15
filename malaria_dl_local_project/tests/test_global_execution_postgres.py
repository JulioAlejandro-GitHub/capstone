"""Global gate and queue tests in disposable PostgreSQL schemas only."""
import os
import sys
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import event, text
from alembic.migration import MigrationContext
from alembic.operations import Operations
from src.malaria_dl.persistence.database import get_engine
from src.malaria_dl.campaigns.contracts import CampaignError
from src.malaria_dl.execution.global_gate import GlobalGate, process_absent, process_identity
from src.malaria_dl.execution.controlled import ControlledRepository
from src.malaria_dl.execution.campaign import execute_campaign
from test_controlled_train_postgres import control
from test_campaigns_postgres import isolated, migration
from test_campaign_executor_postgres import synthetic_train

pytestmark = pytest.mark.skipif(os.getenv('RUN_STAGE93_GLOBAL_POSTGRES_TESTS') != '1', reason='Compose opt-in required')


@pytest.fixture
def global_fixture(control):
    x = control
    x.other = x.s.freeze()
    for name in ('20260912_02_assessments', '20260914_02_global_execution'):
        mod = migration(name)
        mod.op = Operations(MigrationContext.configure(x.s.c))
        mod.upgrade()
    scope = x.s.make_visible()
    x.repo = ControlledRepository(scope)
    def factory():
        engine = get_engine()
        def search_path(dbapi, record):
            with dbapi.cursor() as cursor:
                cursor.execute(f'SET search_path TO {x.s.schema}, pg_catalog')
            dbapi.commit()
        event.listen(engine, 'connect', search_path)
        return engine
    x.factory = factory
    return x


def test_two_coordinators_global_lock(global_fixture):
    x = global_fixture
    with GlobalGate('synthetic-first-campaign', engine_factory=x.factory):
        def second():
            with pytest.raises(CampaignError, match='GLOBAL_EXPERIMENT_BUSY'):
                with GlobalGate('synthetic-other-campaign', engine_factory=x.factory):
                    pytest.fail('second coordinator acquired')
        with ThreadPoolExecutor(1) as pool:
            pool.submit(second).result(timeout=10)
    # Clean DB release is insufficient while the previous coordinator PID lives.
    with pytest.raises(CampaignError, match='PROCESS_STILL_ALIVE'):
        with GlobalGate('synthetic-repeat', engine_factory=x.factory):
            pass


def test_reservations_require_global_owner(global_fixture):
    x = global_fixture
    with pytest.raises(CampaignError):
        x.repo.reserve(**x.args)
    with GlobalGate('synthetic-control', engine_factory=x.factory):
        first, created = x.repo.reserve(**x.args)
        assert created
        again, created = x.repo.reserve(**x.args)
        assert not created and again['run_id'] == first['run_id']
        # A different campaign cannot reserve while a controlled TRAIN is active.
        assert x.repo.get(x.other['id'])['state'] == 'frozen'
        with pytest.raises(CampaignError):
            x.repo.claim(x.other['id'], str(uuid4()), 'synthetic', 1, x.args['root'])
        x.repo.finish(first['run_id'], first['owner'], 'failed', cause='SYNTHETIC_END')


def test_new_oom_and_consecutive_failure_circuit(global_fixture, monkeypatch):
    x = global_fixture
    readings = {'available_bytes': 2*1024**3, 'cgroup_current_bytes': 1, 'cgroup_max': 'max', 'oom_kill': 5}
    monkeypatch.setattr('src.malaria_dl.execution.global_gate.resources', lambda: dict(readings))
    with GlobalGate('synthetic-oom', engine_factory=x.factory) as gate:
        readings['oom_kill'] = 6
        gate.after_wait(999999, -9, 'synthetic')
        with pytest.raises(CampaignError, match='NEW_CONTAINER_OOM_PAUSE'):
            gate.require_healthy()
        with x.repo.transaction(readonly=True) as c:
            assert c.execute(text('SELECT blocked_reason FROM experiment_execution_gate')).scalar_one() == 'NEW_CONTAINER_OOM_PAUSE'


def test_two_failures_pause_without_consuming_matrix(global_fixture, monkeypatch):
    x = global_fixture
    # Tests below use synthetic worker outcomes, no process/model or dataset access.
    monkeypatch.setattr('src.malaria_dl.execution.global_gate.resources', lambda: {'available_bytes':2*1024**3,'cgroup_current_bytes':1,'cgroup_max':'max','oom_kill':0})
    with GlobalGate('synthetic-queue', engine_factory=x.factory):
        code, result = execute_campaign(x.repo, x.args['campaign'], x.args['root'], resume=True,
            dataset=x.args['dataset'], check=lambda *a: None, launch=lambda *a: 2, loader=lambda *a: None)
        assert code == 3 and result['state'] == 'paused'
        assert len(x.repo.get(x.args['campaign'])['attempts']) == 3  # original + only two failures


def test_sequential_revision_and_verified_before_next(global_fixture, monkeypatch):
    x = global_fixture
    monkeypatch.setattr('src.malaria_dl.execution.global_gate.resources', lambda: {'available_bytes':2*1024**3,'cgroup_current_bytes':1,'cgroup_max':'max','oom_kill':0})
    previous = []
    def launch(session, repo):
        if previous:
            assert repo.session(previous[-1])['state'] == 'verified'
        previous.append(session['run_id'])
        assert session['environment'] == x.proposal['environment']
        return synthetic_train(repo, session)
    with GlobalGate('synthetic-queue', engine_factory=x.factory):
        code, result = execute_campaign(x.repo, x.args['campaign'], x.args['root'], resume=True,
            dataset=x.args['dataset'], revision_id=x.args['revision_id'], check=lambda *a:None,
            launch=launch, loader=lambda *a:None)
        assert code == 0 and result['matrix_complete']
        assert len(previous) == 12  # original failed seed retried only after pending members
        with x.repo.transaction(readonly=True) as c:
            assert c.execute(text('SELECT count(*) FROM train_execution_revisions')).scalar_one() == 12


def test_escaped_descendant_blocks_next_work(global_fixture):
    x = global_fixture
    with GlobalGate('synthetic-process-tree', engine_factory=x.factory) as gate:
        # Owned fixture child forks, creates a new session, and outlives its parent.
        p = subprocess.Popen([sys.executable, '-c',
            'import os,time; p=os.fork(); '
            'os._exit(0) if p else None; os.setsid(); time.sleep(0.8)'], start_new_session=True)
        gate.child_started(p.pid)
        code = p.wait(timeout=5)
        try:
            assert not gate.after_wait(p.pid, code, 'synthetic')
            with pytest.raises(CampaignError, match='DESCENDANTS_NOT_RELEASED'):
                gate.require_healthy()
        finally:
            time.sleep(1)
            while True:
                try:
                    if os.waitpid(-1, os.WNOHANG)[0] == 0: break
                except ChildProcessError: break


def test_successful_child_reaped_and_identity_checked(global_fixture):
    x = global_fixture
    with GlobalGate('synthetic-process', engine_factory=x.factory) as gate:
        p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(.1)'], start_new_session=True)
        gate.child_started(p.pid)
        identity = process_identity(p.pid)
        assert not process_absent(identity)
        assert p.wait(timeout=5) == 0
        assert process_absent(identity)
        assert gate.after_wait(p.pid, 0, 'synthetic')
        gate.require_healthy()


def test_insufficient_resources_fail_before_reservation(global_fixture, monkeypatch):
    x = global_fixture
    monkeypatch.setattr('src.malaria_dl.execution.global_gate.resources', lambda: {'available_bytes':1,'cgroup_current_bytes':1,'cgroup_max':'max','oom_kill':5})
    with pytest.raises(CampaignError, match='INSUFFICIENT_MEMORY_HEADROOM'):
        with GlobalGate('synthetic-low-memory', engine_factory=x.factory):
            pytest.fail('insufficient resources admitted')
    assert len(x.repo.get(x.args['campaign'])['attempts']) == 1


def test_pause_after_work_prevents_next_claim(global_fixture, monkeypatch):
    x = global_fixture
    monkeypatch.setattr('src.malaria_dl.execution.global_gate.resources', lambda: {'available_bytes':2*1024**3,'cgroup_current_bytes':1,'cgroup_max':'max','oom_kill':5})
    def launch(session, repo):
        code = synthetic_train(repo, session)
        repo.pause(x.args['campaign'], 'SYNTHETIC_PAUSE_BETWEEN_WORK')
        return code
    with GlobalGate('synthetic-pause', engine_factory=x.factory):
        _, result = execute_campaign(x.repo, x.args['campaign'], x.args['root'], resume=True,
            dataset=x.args['dataset'], check=lambda *a:None, launch=launch, loader=lambda *a:None)
        assert result['state'] == 'paused'
        row = x.repo.get(x.args['campaign'])
        assert len(row['attempts']) == 2
        assert sum(a['state']=='verified' for a in row['attempts']) == 1


def test_readiness_does_not_require_memory_optimization(global_fixture, monkeypatch):
    x = global_fixture
    monkeypatch.setattr('src.malaria_dl.execution.global_gate.resources', lambda: {'available_bytes':2*1024**3,'cgroup_current_bytes':1,'cgroup_max':'max','oom_kill':5})
    value = x.repo.dry_run(x.args['campaign'],x.args['member'],x.args['previous'],x.args['dataset'],x.args['revision_id'],current=x.args['current'])
    assert value['execution_ready'] and value['global_execution']['available']
    assert value['memory_optimization_required'] is False


def test_lost_db_lock_fences_owner(global_fixture):
    x = global_fixture
    with GlobalGate('synthetic-lost-lock', engine_factory=x.factory) as gate:
        gate.sql('SELECT pg_advisory_unlock(120994,1)')
        with pytest.raises(Exception):
            gate.require_healthy()
        # Failed SQL invalidates this transaction; rollback before cleanup.
        gate.connection.rollback()
        with pytest.raises(CampaignError):
            x.repo.reserve(**x.args)


def test_migration_rejects_multiple_legacy_active_sessions(control):
    x = control
    x.repo.resume(x.args['campaign'])
    x.repo.claim(x.args['campaign'],str(uuid4()),'synthetic',1,x.args['root']/'one')
    x.repo.claim(x.args['campaign'],str(uuid4()),'synthetic',1,x.args['root']/'two')
    mod=migration('20260912_02_assessments');mod.op=Operations(MigrationContext.configure(x.s.c));mod.upgrade()
    mod=migration('20260914_02_global_execution');mod.op=Operations(MigrationContext.configure(x.s.c))
    with pytest.raises(Exception):
        with x.s.c.begin_nested():
            mod.upgrade()


def test_checkpoint_loader_owned_process_handshake(global_fixture, monkeypatch, tmp_path):
    import json
    from src.malaria_dl.execution.process_verification import isolated_keras_loader
    x = global_fixture
    monkeypatch.setenv('PGOPTIONS', f'-c search_path={x.s.schema},pg_catalog')
    contract = x.first['configuration']['resolved']['input_contract']
    path = tmp_path / 'synthetic.keras'
    with GlobalGate('synthetic-checkpoint', engine_factory=x.factory) as gate:
        gate.active_run = str(x.first['run_id'])
        read_fd, write_fd = os.pipe()
        process = None
        try:
            code = ('import sys,json; from src.malaria_dl.execution.global_gate import attach_worker; '
                    'attach_worker(); import tensorflow as tf; '
                    'shape=json.loads(sys.argv[2]); '
                    'm=tf.keras.Sequential([tf.keras.Input(shape=shape),tf.keras.layers.GlobalAveragePooling2D(),'
                    'tf.keras.layers.Dense(1,activation="sigmoid")]); m.save(sys.argv[1])')
            process = subprocess.Popen([sys.executable,'-B','-c',code,str(path),json.dumps(contract['shape'][1:])],
                start_new_session=True,pass_fds=(read_fd,),
                env={**os.environ,'CAPSTONE_EXECUTION_TOKEN':gate.owner,'CAPSTONE_START_FD':str(read_fd)})
            gate.child_started(process.pid)
            os.write(write_fd,b'1')
            assert process.wait(timeout=40) == 0
            assert gate.after_wait(process.pid,0,'SYNTHETIC_CHECKPOINT_CREATION')
        finally:
            os.close(read_fd);os.close(write_fd)
            if process is not None and process.poll() is None:
                process.terminate();process.wait(timeout=5)  # Own fixture only.
        isolated_keras_loader(path,contract)
        with x.repo.transaction(readonly=True) as c:
            proof=c.execute(text("SELECT payload FROM experiment_execution_events WHERE event='process_exit' ORDER BY id DESC LIMIT 1")).scalar_one()
        assert proof['phase']=='CHECKPOINT_LOAD' and proof['exit_code']==0 and proof['remaining_pids']==[]
        assert proof['run_id']==str(x.first['run_id'])


from test_assessment_postgres import assessment


def test_train_assessment_cross_exclusion(assessment, monkeypatch):
    from src.malaria_dl.assessment.repository import AssessmentRepository
    from src.malaria_dl.execution.repository import ExecutionRepository
    from src.malaria_dl.assessment import repository as assessment_module
    x = assessment
    other = x.s.freeze()
    for name in ('20260914_01_controlled_train','20260914_02_global_execution'):
        mod=migration(name);mod.op=Operations(MigrationContext.configure(x.s.c));mod.upgrade()
    scope=x.s.make_visible()
    def factory():
        engine=get_engine()
        def configure(dbapi, record):
            with dbapi.cursor() as cursor:cursor.execute(f'SET search_path TO {x.s.schema}, pg_catalog')
            dbapi.commit()
        event.listen(engine,'connect',configure)
        return engine
    repo=AssessmentRepository(scope);train=ExecutionRepository(scope)
    messages=[];original=assessment_module.execute
    def observed(*args,**kwargs):
        try:return original(*args,**kwargs)
        except Exception as exc:
            messages.append(getattr(getattr(getattr(exc,'orig',None),'diag',None),'message_primary',None))
            raise
    monkeypatch.setattr(assessment_module,'execute',observed)
    with GlobalGate('synthetic-cross-kind',engine_factory=factory):
        with pytest.raises(CampaignError):repo.reserve(x.value,x.root/'assessment')
        assert 'GLOBAL_TRAIN_ALREADY_ACTIVE' in messages
        train.finish(x.train['run_id'],x.train['owner'],'failed',cause='SYNTHETIC_END')
        attempt,created=repo.reserve(x.value,x.root/'assessment')
        assert created and attempt['state']=='active'
        with pytest.raises(CampaignError):train.claim(other['id'],str(uuid4()),'synthetic',1,x.root/'another-train')
        repo.finish(attempt['id'],attempt['owner'],'failed',cause='SYNTHETIC_END')


def test_queue_launch_failure_is_recorded_and_paused(global_fixture):
    x = global_fixture
    def launch(*args):
        raise OSError('synthetic launch error')
    with GlobalGate('synthetic-launch-error', engine_factory=x.factory):
        code, result = execute_campaign(x.repo,x.args['campaign'],x.args['root'],resume=True,
            dataset=x.args['dataset'],check=lambda *a:None,launch=launch,loader=lambda *a:None)
        assert code==3 and result['state']=='paused'
        row=x.repo.get(x.args['campaign'])
        assert len(row['attempts'])==2
        assert row['attempts'][-1]['cause']=='CHILD_CONTROL_OSERROR'


def test_unverified_checkpoint_never_advances(global_fixture):
    x = global_fixture
    def bad_load(*args):
        raise CampaignError('SYNTHETIC_CHECKPOINT_INVALID')
    with GlobalGate('synthetic-verification-error', engine_factory=x.factory):
        code,result=execute_campaign(x.repo,x.args['campaign'],x.args['root'],resume=True,
            dataset=x.args['dataset'],check=lambda *a:None,
            launch=lambda session,repo:synthetic_train(repo,session),loader=bad_load)
        assert code==3 and result['state']=='paused'
        row=x.repo.get(x.args['campaign'])
        assert len(row['attempts'])==2 and row['attempts'][-1]['state']=='completed'
        assert not result['matrix_complete']


def test_unclean_disappearance_is_not_resource_release(global_fixture):
    import json
    from src.malaria_dl.execution.global_gate import host_identity
    x=global_fixture
    with x.repo.transaction() as c:
        c.execute(text('UPDATE experiment_execution_gate SET process_evidence=CAST(:e AS jsonb)'),
                  {'e':json.dumps({'identities':[{**host_identity(),'pid':99999999,'start_ticks':'1'}],
                                   'sessions':[],'release_confirmed':False})})
    with pytest.raises(CampaignError,match='PROCESS_TREE_RELEASE_UNPROVEN'):
        with GlobalGate('synthetic-crash',engine_factory=x.factory):
            pytest.fail('unclean process tree admitted')
    assert len(x.repo.get(x.args['campaign'])['attempts'])==1


def test_queue_dry_run_selects_pending_and_never_reserves(global_fixture):
    from src.malaria_dl.execution.controlled import queue_dry_run
    x=global_fixture
    before=x.repo.get(x.args['campaign'])
    value=queue_dry_run(x.repo,x.args['campaign'],x.args['dataset'],x.args['revision_id'],current=x.args['current'])
    assert value['writes']==value['reservations']==0
    assert value['next_position']==1  # Position0 has a failed historical attempt.
    assert value['execution_ready'] and not value['memory_optimization_required']
    assert x.repo.get(x.args['campaign'])==before
    with pytest.raises(CampaignError):
        queue_dry_run(x.repo,x.args['campaign'],str(uuid4()),x.args['revision_id'],current=x.args['current'])


def test_inspection_is_not_an_executing_coordinator():
    from src.malaria_dl.execution.global_gate import managed_execution
    assert managed_execution([b'python',b'run_train_all_models.py',b'--resume'])
    assert not managed_execution([b'python',b'run_train_all_models.py',b'--dry-run'])
    assert not managed_execution([b'python',b'-m',b'src.malaria_dl.execution.controlled',b'dry-run'])
    assert managed_execution([b'python',b'-m',b'src.train'])
