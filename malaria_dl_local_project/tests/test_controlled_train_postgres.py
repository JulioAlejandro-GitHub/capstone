"""Only synthetic E4 schema; no operational campaign reservations."""
import os
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from src.malaria_dl.campaigns.contracts import CampaignError
from src.malaria_dl.execution.repository import ExecutionRepository
from src.malaria_dl.execution.controlled import ControlledRepository, execute_one
from test_campaigns_postgres import isolated, migration

pytestmark=pytest.mark.skipif(os.getenv('RUN_STAGE93_CONTROLLED_POSTGRES_TESTS')!='1',reason='Compose opt-in required')

@pytest.fixture
def control(isolated,tmp_path):
    for name in ['20260912_01_train_execution','20260914_01_controlled_train']:
        mod=migration(name);mod.op=Operations(MigrationContext.configure(isolated.c));mod.upgrade()
    row=isolated.freeze();repo=ControlledRepository(isolated.repo.scope)
    first=repo.claim(str(row['id']),str(uuid4()),'synthetic',1,tmp_path/'old')
    repo.finish(first['run_id'],first['owner'],'failed',cause='SYNTHETIC_FAILURE')
    repo.pause(row['id'],'SYNTHETIC_PAUSE')
    row=repo.get(row['id']);m=next(m for m in row['members'] if m['state']=='failed')
    env=deepcopy(row['environment']);env['source_sha256']='f'*64
    proposal={'original_environment':row['environment'],'environment':env,'contract_hash':row['contract_hash'],'reason':'synthetic technical fixture','files':{'src/example.py':'a'*64},'tests':['synthetic pass'],'authorization':'synthetic fixture only'}
    rid=str(uuid4());repo.register_revision(row['id'],rid,proposal)
    args=dict(campaign=str(row['id']),member=str(m['id']),previous=str(first['attempt_id']),dataset=str(row['dataset_version_id']),revision_id=rid,request_id=str(uuid4()),reason='fixture',root=tmp_path/'new',current=env)
    return SimpleNamespace(s=isolated,repo=repo,row=row,first=first,proposal=proposal,args=args)


def test_paused_atomic_idempotent_identity(control):
    x=control;s,new=x.repo.reserve(**x.args);assert new
    s2,new=x.repo.reserve(**x.args);assert not new and s2['run_id']==s['run_id']
    assert x.repo.get(x.row['id'])['state']=='paused'
    assert x.repo.session(x.first['run_id'])['state']=='failed'
    assert s['environment']==x.proposal['environment']
    x.s.c.execute(text('SET CONSTRAINTS ALL IMMEDIATE'))
    cid=x.s.c.execute(text('SELECT campaign_id FROM runs WHERE id=:id'),{'id':s['run_id']}).scalar_one()
    assert str(cid)==x.args['campaign']
    with pytest.raises(CampaignError):x.repo.claim(x.row['id'],str(uuid4()),'synthetic',1,x.args['root'])

@pytest.mark.parametrize('field,value',[('dataset',str(uuid4())),('member',str(uuid4())),('revision_id',str(uuid4()))])
def test_wrong_identity_rejected(control,field,value):
    args=dict(control.args);args[field]=value
    with pytest.raises(CampaignError):control.repo.reserve(**args)
    assert len(control.repo.get(control.row['id'])['attempts'])==1

@pytest.mark.parametrize('mutation',['contract','source','packages','files'])
def test_invalid_revision_rejected(control,mutation):
    x=control;p=deepcopy(x.proposal)
    if mutation=='contract':p['contract_hash']='a'*64
    if mutation=='source':p['environment']['source_sha256']='bad'
    if mutation=='packages':p['environment']['packages']={}
    if mutation=='files':p['files']={'x':'bad'}
    with pytest.raises(CampaignError):x.repo.register_revision(x.row['id'],str(uuid4()),p)


def test_runtime_hash_and_active_rejected(control):
    x=control;args=dict(x.args);args['current']={**args['current'],'source_sha256':'1'*64}
    with pytest.raises(CampaignError):x.repo.reserve(**args)
    x.repo.reserve(**x.args)
    args=dict(x.args);args['request_id']=str(uuid4())
    with pytest.raises(CampaignError):x.repo.reserve(**args)


def test_dry_run_no_writes(control):
    x=control
    before=x.repo.get(x.row['id'])
    result=x.repo.dry_run(x.args['campaign'],x.args['member'],x.args['previous'],x.args['dataset'],x.args['revision_id'],current=x.args['current'])
    assert result['writes']==0 and not result['execution_ready']
    assert result['global_execution']['reason']=='GLOBAL_EXECUTION_MIGRATION_REQUIRED'
    assert x.repo.get(x.row['id'])==before
    assert x.s.c.execute(text('SELECT count(*) FROM campaign_controlled_requests')).scalar_one()==0


def test_concurrent_idempotence(control):
    x=control;repo=ControlledRepository(x.s.make_visible());barrier=Barrier(2)
    def reserve():
        barrier.wait(timeout=5)
        return repo.reserve(**x.args)
    with ThreadPoolExecutor(2) as pool:
        a=pool.submit(reserve);b=pool.submit(reserve);results=[a.result(timeout=15),b.result(timeout=15)]
    assert len({str(s['run_id']) for s,_ in results})==1
    assert sorted(new for _,new in results)==[False,True]
    assert repo.get(x.row['id'])['state']=='paused'


def test_launch_failure_no_chain(control,monkeypatch):
    x=control
    monkeypatch.setattr('src.malaria_dl.execution.controlled.planning_environment',lambda:x.args['current'])
    args={k:v for k,v in x.args.items() if k!='current'}
    def launch(*a):raise OSError('synthetic launch failure')
    with pytest.raises(OSError):execute_one(x.repo,**args,check=lambda *a:None,launch=launch)
    row=x.repo.get(x.row['id'])
    assert row['state']=='paused' and len(row['attempts'])==2
    assert all(a['state']=='failed' for a in row['attempts'])


def test_success_once_and_repeat_no_launch(control,monkeypatch):
    from test_campaign_executor_postgres import synthetic_train
    x=control;monkeypatch.setattr('src.malaria_dl.execution.controlled.planning_environment',lambda:x.args['current'])
    args={k:v for k,v in x.args.items() if k!='current'};calls=[]
    def launch(s,repo):calls.append(s['run_id']);return synthetic_train(repo,s)
    result=execute_one(x.repo,**args,check=lambda *a:None,launch=launch,loader=lambda *a:None)
    assert result['state']=='verified'
    again=execute_one(x.repo,**args,launch=lambda *a:pytest.fail('launched twice'))
    assert again['run_id']==result['run_id'] and not again['launched'] and len(calls)==1
    assert x.repo.get(x.row['id'])['state']=='paused'


def test_recovery_requires_absence_and_never_launches(control,monkeypatch):
    x=control;s,_=x.repo.reserve(**x.args)
    with pytest.raises(CampaignError):x.repo.recover(x.row['id'],x.args['request_id'])
    monkeypatch.setattr('src.malaria_dl.execution.campaign.dead_local',lambda s:True)
    result=x.repo.recover(x.row['id'],x.args['request_id'])
    assert result['state']=='interrupted' and not result['launched']
    assert len(x.repo.get(x.row['id'])['attempts'])==2


def test_resume_and_revision_mutation_blocked(control):
    x=control;x.repo.reserve(**x.args)
    with pytest.raises(CampaignError):x.repo.resume(x.row['id'])
    with pytest.raises(Exception):
        with x.s.c.begin_nested():
            x.s.c.execute(text("UPDATE campaign_technical_revisions SET payload_hash=:hash WHERE id=:id"),{'hash':'1'*64,'id':x.args['revision_id']})
    assert x.repo.get(x.row['id'])['state']=='paused'


def test_wrong_scientific_payload_sql_rejected(control):
    from src.malaria_dl.campaigns.contracts import canonical,digest
    x=control;p=deepcopy(x.proposal);p['contract_hash']='a'*64
    with pytest.raises(Exception):
        with x.s.c.begin_nested():
            x.s.c.execute(text('INSERT INTO campaign_technical_revisions VALUES(:id,:cid,CAST(:p AS jsonb),:cp,:h,clock_timestamp())'),{'id':str(uuid4()),'cid':x.args['campaign'],'p':canonical(p),'cp':canonical(p),'h':digest(p)})


def test_distinct_concurrent_requests_only_one_reservation(control):
    x=control;repo=ControlledRepository(x.s.make_visible());barrier=Barrier(2)
    def reserve(request):
        args=dict(x.args);args['request_id']=request
        barrier.wait(timeout=5)
        try:return repo.reserve(**args)[1]
        except CampaignError:return False
    with ThreadPoolExecutor(2) as pool:
        a=pool.submit(reserve,str(uuid4()));b=pool.submit(reserve,str(uuid4()))
        assert sorted([a.result(timeout=15),b.result(timeout=15)])==[False,True]
    assert len(repo.get(x.row['id'])['attempts'])==2


def test_technical_worker_binding(control):
    from src.malaria_dl.execution.controlled import effective_row
    x=control;s,_=x.repo.reserve(**x.args)
    row=effective_row(x.repo,x.repo.get(x.row['id']),s)
    assert row['environment']==s['environment']
    assert x.repo.get(x.row['id'])['environment']==x.proposal['original_environment']
    bad=deepcopy(s);bad['environment']['source_sha256']='a'*64
    with pytest.raises(CampaignError):effective_row(x.repo,x.repo.get(x.row['id']),bad)


def test_controlled_failure_return_code_does_not_chain(control,monkeypatch):
    x=control;monkeypatch.setattr('src.malaria_dl.execution.controlled.planning_environment',lambda:x.args['current'])
    args={k:v for k,v in x.args.items() if k!='current'}
    result=execute_one(x.repo,**args,check=lambda *a:None,launch=lambda *a:-9)
    s=x.repo.session(result['run_id'])
    assert s['state']=='failed' and s['cause']=='CONTROLLED_CHILD_EXIT_-9'
    assert x.repo.get(x.row['id'])['state']=='paused'
    assert len(x.repo.get(x.row['id'])['attempts'])==2
