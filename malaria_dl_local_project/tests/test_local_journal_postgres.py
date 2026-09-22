"""HTTP + real PostgreSQL + real host SQLite/process death, disposable schemas only."""
from contextlib import contextmanager
from dataclasses import fields
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text
from src.malaria_dl.campaigns.contracts import digest
from src.malaria_dl.execution.contracts import RunEventType as E
from src.malaria_dl.execution.emitter import RunEventEmitter
from src.malaria_dl.local_execution.event_journal import SQLiteEventJournal, StreamIdentity
from src.malaria_dl.local_execution.event_runtime import stream_identity
from src.malaria_dl.local_execution.transport import Api
from test_campaigns_postgres import isolated  # noqa: F401
from test_result_repository_postgres import pg, apply, REVISION  # noqa: F401
from test_http_reporter_postgres import remote, serve  # noqa: F401
from test_docker_reporter_postgres import legacy_repository
from test_controlled_train_postgres import control  # noqa: F401
from test_global_execution_postgres import global_fixture  # noqa: F401
from test_local_execution_postgres import local_ready  # noqa: F401

pytestmark=pytest.mark.skipif(os.getenv('RUN_E10_LOCAL_JOURNAL_POSTGRES_TESTS')!='1',reason='Explicit temporary-schema opt-in')


@pytest.mark.parametrize('point',['A','B','C','D'])
def test_crash_http_commit_and_exact_retry(pg,remote,tmp_path,point):
    identity=StreamIdentity(remote.identity.job_id,remote.identity.agent_id,pg.ctx.run_id,pg.ctx.attempt_id)
    path=tmp_path/'journal'
    script='''
import json,os,sys
from uuid import UUID
from src.malaria_dl.local_execution.event_journal import SQLiteEventJournal,StreamIdentity
from src.malaria_dl.local_execution.event_client import build_http_run_reporter
from src.malaria_dl.local_execution.event_transport import RemoteExecutionIdentity
from src.malaria_dl.local_execution import transport
from src.malaria_dl.execution.emitter import RunEventEmitter
from src.malaria_dl.execution.contracts import RunEventType as E
identity=StreamIdentity(*(UUID(v) for v in json.loads(sys.argv[2])))
reporter=build_http_run_reporter(sys.argv[3],os.environ['SYNTHETIC_EVENT_BEARER'],RemoteExecutionIdentity(job_id=identity.job_id,agent_id=identity.agent_id))
point=sys.argv[4]
if point=='B':
 real_open=transport.urlopen
 def lost(*args,**kwargs):
  with real_open(*args,**kwargs) as response: assert json.load(response)['status']=='accepted'
  os._exit(72)
 transport.urlopen=lost
with SQLiteEventJournal(sys.argv[1],identity,create=True) as journal:
 if point=='C':
  original=journal.transition
  def transition(before,after):
   if after.pending is None:os._exit(73)
   original(before,after)
  journal.transition=transition
 if point=='A':reporter.report=lambda event:os._exit(71)
 writer=RunEventEmitter(reporter,run_id=identity.run_id,attempt_id=identity.attempt_id,journal=journal)
 writer.emit(E.EPOCH_COMPLETED,{'values':[1,1.0,-0.0,True],'text':'á'})
 os._exit(74)
'''
    child=subprocess.run([sys.executable,'-B','-c',script,str(path),json.dumps(list(identity.wire().values())),remote.url,point],
                         env={**os.environ,'SYNTHETIC_EVENT_BEARER':remote.token()},capture_output=True,timeout=30)
    assert child.returncode=={'A':71,'B':72,'C':73,'D':74}[point],child.stderr.decode()
    repo=legacy_repository(pg);events=repo.result_events(pg.ctx.run_id)
    assert len(events)==(0 if point=='A' else 1)
    with SQLiteEventJournal(path,identity) as journal:
        writer=RunEventEmitter(remote.reporter(),run_id=identity.run_id,attempt_id=identity.attempt_id,journal=journal)
        if point!='D':
            pending=writer.pending
            if events:assert pending.to_dict()==events[0].to_dict()
            assert writer.retry_pending() is pending
        assert writer.next_sequence==2
        writer.emit(E.TRAINING_COMPLETED,{})
    events=repo.result_events(pg.ctx.run_id)
    assert [e.sequence for e in events]==[1,2]
    with SQLiteEventJournal(path,identity) as journal:assert journal.load(identity.run_id,identity.attempt_id).closed


def test_readonly_state_authorized_no_internal_owner(pg,remote):
    api=Api(remote.url,remote.token());identity={'job_id':str(remote.identity.job_id),'agent_id':str(remote.identity.agent_id)}
    with pg.sql() as c:
        before=c.execute(text('SELECT to_jsonb(j) FROM local_execution_jobs j')).scalar_one()
    state=api.call('event-state',identity)
    assert state==dict(run_id=str(pg.ctx.run_id),attempt_id=str(pg.ctx.attempt_id),last_sequence=0,last_event_id=None,terminal_type=None,legacy_exists=True)
    with pytest.raises(RuntimeError,match='API_REJECTED_403'):
        Api(remote.url,remote.token(remote.other)).call('event-state',identity)
    with pytest.raises(RuntimeError,match='API_REJECTED_422'):
        api.call('event-state',{**identity,'owner':str(pg.ctx.owner)})
    with pg.sql() as c:assert c.execute(text('SELECT to_jsonb(j) FROM local_execution_jobs j')).scalar_one()==before


@pytest.fixture
def native_ready(monkeypatch,request):
    # The existing approved Local fixture, bounded to one tiny real epoch.
    import test_local_execution_postgres as legacy_tests
    original=legacy_tests.matrix_request
    def tiny_request():
        value=original()
        value['variants'][0]['selected']={'model':{'input_shape':[32,32,3]},
            'execution':{'max_epochs':1,'batch_size':2,'no_augment':True}}
        return value
    monkeypatch.setattr(legacy_tests,'matrix_request',tiny_request)
    ready=request.getfixturevalue('local_ready')
    with ready.x.repo.transaction() as c:apply(c,REVISION)
    return ready


@pytest.fixture
def native_http(native_ready,monkeypatch):
    from fastapi import FastAPI
    from app import security,config
    from app.routes import local_execution as route
    from src.malaria_dl.local_execution import backend,event_backend
    from src.malaria_dl.local_execution.backend import LocalBackend
    ready=native_ready
    monkeypatch.setattr(backend,'process_table',lambda:{})  # /proc scan is Linux-only; covered by regression.
    principal=uuid4()
    with ready.x.repo.transaction() as c:
        c.execute(text('CREATE TABLE users(id uuid PRIMARY KEY,username text,status text)'))
        c.execute(text("INSERT INTO users VALUES(:id,'native-fixture','active')"),{'id':principal})
    settings=SimpleNamespace(**{f.name:getattr(config.Settings.from_env(),f.name) for f in fields(config.Settings)})
    settings.auth_mode='local_jwt';settings.jwt_secret=uuid4().hex+uuid4().hex
    settings.jwt_algorithm='HS256';settings.jwt_access_token_expire_minutes=15
    monkeypatch.setattr(config,'get_settings',lambda:settings)
    monkeypatch.setattr(security,'get_settings',lambda:settings)
    engine=ready.x.factory();monkeypatch.setattr(security,'get_primary_engine',lambda:engine)
    monkeypatch.setenv('CAPSTONE_LOCAL_EXECUTION_ENABLED','1')
    build=event_backend.build_local_event_backend
    monkeypatch.setattr(event_backend,'build_local_event_backend',lambda:build(engine_factory=ready.x.factory))
    real=LocalBackend(ready.x.repo,ready.roots,check=lambda *a:None)
    stages=[]
    original_operation=real.operation
    def operation(name,data,principal):
        if name in ('calculation-ended','exit'):
            with ready.x.repo.transaction(readonly=True) as c:
                job=c.execute(text('SELECT * FROM local_execution_jobs WHERE id=CAST(:id AS uuid)'),{'id':data['job_id']}).mappings().one()
            events=ready.x.repo.result_events(job['run_id'])
            stages.append((name,job['state'],events[-1].event_type.value if events else None))
        return original_operation(name,data,principal)
    real.operation=operation
    app=FastAPI();app.include_router(route.router)
    app.dependency_overrides[route.service]=lambda:real
    try:
        with serve(app) as url:
            yield SimpleNamespace(ready=ready,url=url,bearer=security.create_access_token(principal,'native-fixture',['administrator']),backend=real,stages=stages)
    finally:engine.dispose()


def run_agent(http,mode,state,config_path):
    root=Path(__file__).resolve().parents[1]
    environment={**os.environ,'CAPSTONE_AGENT_BEARER':http.bearer,
                 'TF_NUM_INTEROP_THREADS':'1','TF_NUM_INTRAOP_THREADS':'1','OMP_NUM_THREADS':'1',
                 'KERAS_HOME':str(config_path.parent/'keras-cache')}
    return subprocess.run([sys.executable,'-B','-m','src.malaria_dl.local_execution.agent',mode,
                           '--config',str(config_path),'--state',str(state)],cwd=root,
                          env=environment,capture_output=True,timeout=180)


@pytest.mark.parametrize('failure',['none','completion','verify'])
def test_native_agent_worker_train_journal_release(native_http,tmp_path,monkeypatch,failure):
    if platform.system()!='Darwin':pytest.skip('This evidence must run on the actual Mac host')
    h=native_http;r=h.ready
    if failure=='completion':
        original=h.backend.operation
        def fail(name,*args):
            if name=='calculation-ended':
                from src.malaria_dl.campaigns.contracts import CampaignError
                raise CampaignError('SYNTHETIC_COMPLETION_FAILURE')
            return original(name,*args)
        monkeypatch.setattr(h.backend,'operation',fail)
    elif failure=='verify':
        def fail(*args):raise ValueError('synthetic loader failure')
        monkeypatch.setattr(h.backend,'loader',fail)
    configuration=tmp_path/'agent_config.json';state=tmp_path/'agent_state.json'
    configuration.write_text(json.dumps(dict(url=h.url,request=r.data,roots={k:str(v) for k,v in r.roots.items()})))
    result=run_agent(h,'start',state,configuration)
    stored=json.loads(state.read_text());job=stored['job'];ident=stream_identity(job)
    with SQLiteEventJournal(stored['event_journal'],ident) as journal:
        js=journal.load(ident.run_id,ident.attempt_id)
        assert js.closed and js.pending is None and js.terminal_type is E.TRAINING_COMPLETED
    proof=stored['exit_proof']
    assert proof['parent']['platform']=='Darwin' and proof['parent']['pid']!=os.getpid()
    assert proof['absence_proven'] and not proof['remaining']
    current=r.x.repo.session(job['run_id']);events=r.x.repo.result_events(job['run_id'])
    expected=[E.PHASE_STARTED,E.EPOCH_COMPLETED,E.ARTIFACT_PREPARED,E.ARTIFACT_CREATED,
              E.SELECTION_COMPLETED,E.PREDICTIONS_COMPLETED,E.PHASE_COMPLETED,E.CALIBRATION_COMPLETED,E.TRAINING_COMPLETED]
    assert [e.event_type for e in events]==expected and [e.sequence for e in events]==list(range(1,10))
    assert not any(str(tmp_path) in json.dumps(e.to_dict()) for e in events)
    with r.x.repo.transaction(readonly=True) as c:
        params=c.execute(text('SELECT parameters FROM runs WHERE id=CAST(:id AS uuid)'),{'id':job['run_id']}).scalar_one()
        dbjob=c.execute(text('SELECT * FROM local_execution_jobs WHERE id=CAST(:id AS uuid)'),{'id':job['job_id']}).mappings().one()
    assert params=={}
    assert events[-1].payload['records_hash']==digest(r.x.repo.records(job['run_id']))
    if failure=='none':
        assert result.returncode==0,result.stderr.decode()
        assert current['state']=='verified' and dbjob['state']=='released'
        assert h.stages==[('calculation-ended','held','training_completed'),('exit','calculation_reported','training_completed')]
        assert current['verification']['records_hash']==events[-1].payload['records_hash']
    elif failure=='completion':
        assert current['state']=='failed' and dbjob['state']=='failed'
    else:
        assert result.returncode!=0 and current['state']=='active' and dbjob['state']=='calculation_reported'
        assert current['verification'] is None
        # Retry only verification/exit, never science; exact saved process proof.
        monkeypatch.setattr(h.backend,'loader',h.backend.load_checkpoint)
        again=run_agent(h,'reconcile',state,configuration)
        assert again.returncode==0,again.stderr.decode()
        assert r.x.repo.session(job['run_id'])['state']=='verified'
    assert r.x.repo.result_events(job['run_id'])==events


def test_native_agent_holds_pending_until_explicit_transport_reconcile(native_http,tmp_path,monkeypatch):
    if platform.system()!='Darwin':pytest.skip('Actual native Mac evidence required')
    from src.malaria_dl.local_execution.event_backend import LocalEventBackend
    from src.malaria_dl.results.errors import ResultPersistenceError
    h=native_http;r=h.ready
    original=LocalEventBackend.accept
    def lost(self,request,principal):
        original(self,request,principal)
        raise ResultPersistenceError()  # HTTP 503 after the real committed append.
    monkeypatch.setattr(LocalEventBackend,'accept',lost)
    config=tmp_path/'config.json';state=tmp_path/'agent.json'
    config.write_text(json.dumps(dict(url=h.url,request=r.data,roots={k:str(v) for k,v in r.roots.items()})))
    result=run_agent(h,'start',state,config)
    assert result.returncode!=0 and b'LOCAL_E10_PENDING_RECONCILE_REQUIRED' in result.stderr
    stored=json.loads(state.read_text());job=stored['job'];identity=stream_identity(job)
    events=r.x.repo.result_events(job['run_id'])
    assert len(events)==1 and events[0].event_type is E.PHASE_STARTED
    with SQLiteEventJournal(stored['event_journal'],identity) as journal:
        assert journal.load(identity.run_id,identity.attempt_id).pending.to_dict()==events[0].to_dict()
    with r.x.repo.transaction(readonly=True) as c:
        assert c.execute(text('SELECT state FROM local_execution_jobs WHERE id=CAST(:id AS uuid)'),{'id':job['job_id']}).scalar_one()=='held'
    assert r.x.repo.session(job['run_id'])['state']=='active' and not h.stages
    monkeypatch.setattr(LocalEventBackend,'accept',original)
    recovered=run_agent(h,'reconcile',state,config)
    assert recovered.returncode==0,recovered.stderr.decode()
    assert r.x.repo.session(job['run_id'])['state']=='failed'  # Transport ACK is not scientific success.
    assert r.x.repo.result_events(job['run_id'])==events
    with SQLiteEventJournal(stored['event_journal'],identity) as journal:
        s=journal.load(identity.run_id,identity.attempt_id)
        assert s.pending is None and s.next_sequence==2 and not s.closed
