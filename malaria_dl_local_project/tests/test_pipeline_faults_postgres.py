"""Persistence fault contrasts: real PostgreSQL, disposable E4 schema only."""
import os
import signal
import subprocess
import sys
from pathlib import Path
from uuid import uuid4
import pytest
from sqlalchemy import text, event
from src.malaria_dl.campaigns.contracts import CampaignError
from src.malaria_dl.execution.global_gate import GlobalGate
from src.malaria_dl.execution.artifacts import verify_session
from test_campaigns_postgres import isolated
from test_controlled_train_postgres import control
from test_global_execution_postgres import global_fixture
from test_campaign_executor_postgres import synthetic_train

pytestmark=pytest.mark.skipif(os.getenv('RUN_PIPELINE_MOCK_POSTGRES_TESTS')!='1',reason='Compose synthetic opt-in')

@pytest.mark.parametrize('stage',['epoch','artifact','final'])
def test_calculation_success_database_rejects_without_false_success(global_fixture,stage):
    x=global_fixture
    with GlobalGate('mock-persistence-failure',engine_factory=x.factory):
        s,_=x.repo.reserve(**x.args)
        table='runs' if stage=='final' else 'train_execution_records'
        when="NEW.status='completed'" if stage=='final' else f"NEW.kind='{stage}'"
        operation='UPDATE' if stage=='final' else 'INSERT'
        with x.repo.transaction() as c:
            c.execute(text(f"CREATE FUNCTION mock_failure() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF {when} THEN RAISE EXCEPTION 'MOCK_PERSISTENCE_FAILURE' USING ERRCODE='23514'; END IF; RETURN NEW; END $$"))
            c.execute(text(f'CREATE TRIGGER mock_failure BEFORE {operation} ON {table} FOR EACH ROW EXECUTE FUNCTION mock_failure()'))
        diagnostics=[]
        def error(ctx):diagnostics.append(getattr(ctx.original_exception,'sqlstate',None))
        event.listen(x.s.c.engine,'handle_error',error)
        try:
            with pytest.raises(CampaignError):synthetic_train(x.repo,s)
        finally:event.remove(x.s.c.engine,'handle_error',error)
        # Repositories use new connections after make_visible: these are committed reads.
        current=x.repo.session(s['run_id'])
        assert current['state']=='active' and current['completion'] is None
        with x.repo.transaction(readonly=True) as c:
            assert c.execute(text('SELECT status FROM runs WHERE id=:id'),{'id':s['run_id']}).scalar_one()!='completed'
        assert Path(s['artifact_root'],'1.keras').exists()
        x.repo.finish(s['run_id'],s['owner'],'failed',cause='MOCK_PERSISTENCE_FAILURE_'+stage)
        assert x.repo.session(s['run_id'])['state']=='failed'
        print({'contrast':'calculation-success/persistence-failure','stage':stage,'sqlstate':diagnostics,'false_success':False})


def test_commit_visible_lost_client_ack_and_repeat_finalize(global_fixture):
    x=global_fixture
    with GlobalGate('mock-lost-ack',engine_factory=x.factory):
        s,_=x.repo.reserve(**x.args)
        synthetic_train(x.repo,s)
        # Client discards acknowledgement after actual commit; do not mock commit.
        try:raise ConnectionError('MOCK_ACK_LOST_AFTER_RETURNED_COMMIT')
        except ConnectionError:pass
        fresh=x.repo.session(s['run_id']);assert fresh['state']=='completed'
        proof=verify_session(x.repo,fresh,lambda *a:None)
        x.repo.finish(s['run_id'],s['owner'],'verified',proof)
        before=x.repo.records(s['run_id'])
        with pytest.raises(CampaignError):x.repo.finish(s['run_id'],s['owner'],'verified',proof)
        assert x.repo.records(s['run_id'])==before and x.repo.session(s['run_id'])['state']=='verified'
        repeated,created=x.repo.reserve(**x.args)
        assert not created and repeated['run_id']==s['run_id']
        print('committed readback; repeated finalization rejected without duplicate; request idempotent')


def test_disposable_process_sigkill_before_finalization(global_fixture):
    x=global_fixture
    with GlobalGate('mock-killed-calculation',engine_factory=x.factory) as gate:
        s,_=x.repo.reserve(**x.args);gate.active_run=str(s['run_id'])
        child=subprocess.Popen([sys.executable,'-c','import time; print("CALCULATION_STARTED",flush=True); time.sleep(60)'],stdout=subprocess.PIPE,start_new_session=True)
        gate.child_started(child.pid)
        assert child.stdout.readline().strip()==b'CALCULATION_STARTED'
        child.send_signal(signal.SIGKILL);assert child.wait(timeout=5)==-9
        assert gate.after_wait(child.pid,-9,'MOCK_CALCULATION')
        x.repo.finish(s['run_id'],s['owner'],'failed',cause='MOCK_SIGKILL_NOT_OOM')
        assert not x.repo.records(s['run_id']) and x.repo.session(s['run_id'])['completion'] is None
        print('process killed during synthetic calculation; no completion; SIGKILL does not prove OOM')


def test_invalid_foreign_key_and_lost_test_connection(global_fixture):
    x=global_fixture
    with x.repo.transaction(readonly=True) as c:before=c.execute(text('SELECT count(*) FROM train_execution_revisions')).scalar_one()
    with pytest.raises(CampaignError):
        with x.repo.transaction() as c:
            c.execute(text('INSERT INTO train_execution_revisions VALUES(:a,:c,:r,DEFAULT)'),{'a':uuid4(),'c':uuid4(),'r':uuid4()})
    with x.repo.transaction(readonly=True) as c:assert c.execute(text('SELECT count(*) FROM train_execution_revisions')).scalar_one()==before
    # Invalidate this disposable client connection only, never terminate server sessions.
    with pytest.raises(CampaignError):
        with x.repo.transaction() as c:
            c.invalidate()
            c.execute(text('SELECT 1'))
    with x.repo.transaction(readonly=True) as c:assert c.execute(text('SELECT 1')).scalar_one()==1

from test_campaign_executor_postgres import execution

def test_minimal_real_train_serialization_and_committed_readback(execution,tmp_path):
    """Real engine, tiny adapter, synthetic directory; no operational dataset."""
    from dataclasses import replace
    from types import SimpleNamespace
    from PIL import Image
    import numpy as np
    import tensorflow as tf
    from test_campaigns_e4 import request,protocol
    from src.malaria_dl.execution.repository import ExecutionRepository
    from src.malaria_dl.execution.train import train
    from src.malaria_dl.execution.artifacts import keras_loader
    from src.malaria_dl.models.adapters import BaseAdapter
    s=execution.s
    root=tmp_path/'images'
    patients=[]
    for split in ('train','val','test'):
        for label,colour in [('uninfected',0),('parasitized',255)]:
            folder=root/split/label;folder.mkdir(parents=True)
            patient=str(uuid4());patients.append(patient)
            Image.fromarray(np.full((16,16,3),colour,dtype=np.uint8)).save(folder/(patient+'.png'))
    assert len(set(patients))==6
    snapshot=replace(s.service.verifier(s.dataset['dataset_version_id']),dataset_root=root)
    from src.malaria_dl.campaigns.contracts import canonical
    eid=str(uuid4());snapshot=replace(snapshot,evidence_id=eid)
    s.c.execute(text("INSERT INTO audit_events(id,event_type,action,resource_type,resource_id,request_method,request_path,correlation_id,after_state,metadata,success) VALUES(CAST(:id AS uuid),'ml.dataset_verification','verify','dataset_version',:dataset,'TEST','synthetic',CAST(:id AS text),CAST(:payload AS jsonb),'{}',true)"),{'id':eid,'dataset':s.dataset['dataset_version_id'],'payload':canonical({'dataset_version_id':s.dataset['dataset_version_id'],'snapshot':snapshot.metadata(),'integrity_status':'verified'})})
    s.service.verifier=lambda *a,**kw:snapshot
    req=request();req['models']=['custom_cnn'];req['optimizers']=['adam'];req['variants'][0]['selected']={'execution':{'max_epochs':1,'batch_size':2,'no_augment':True}}
    row=s.service.create(name='Tiny synthetic actual calculation',purpose='mock integration only',dataset_version_id=s.dataset['dataset_version_id'],request=req,protocol=protocol(),actor='synthetic')
    row=s.service.freeze(row['id']);repo=ExecutionRepository(s.make_visible())
    session=repo.claim(row['id'],str(uuid4()),'synthetic',os.getpid(),tmp_path/'artifacts')
    class Tiny(BaseAdapter):
        def build(self,config):
            model=tf.keras.Sequential([tf.keras.Input(tuple(config['model']['input_shape'])),tf.keras.layers.GlobalAveragePooling2D(),tf.keras.layers.Dense(1,activation='sigmoid')])
            return self.result(model,None,config)
    train(repo,session,SimpleNamespace(create_adapter=Tiny))
    finished=repo.session(session['run_id']);assert finished['state']=='completed'
    proof=verify_session(repo,finished,keras_loader);repo.finish(session['run_id'],session['owner'],'verified',proof)
    assert repo.session(session['run_id'])['state']=='verified'
    print('REAL tiny fit -> internal VAL -> serialized checkpoint -> committed completion -> safe load -> verified; TEST directory not used by TRAIN')

@pytest.mark.parametrize('split',['val','test'])
def test_val_persistence_failure_preserves_verified_train(global_fixture,split):
    from src.malaria_dl.assessment.repository import AssessmentRepository
    from src.malaria_dl.assessment.service import run
    from test_assessment_e6 import value,Runtime
    x=global_fixture
    with GlobalGate('mock-val-failure',engine_factory=x.factory):
        s,_=x.repo.reserve(**x.args);synthetic_train(x.repo,s)
        proof=verify_session(x.repo,x.repo.session(s['run_id']),lambda *a:None)
        x.repo.finish(s['run_id'],s['owner'],'verified',proof)
        v=value(x.args['root']);v['model']['training_run_id']=str(s['run_id']);v['dataset']=x.s.dataset
        repo=AssessmentRepository(x.repo.scope)
        if split=='test':
            from src.malaria_dl.campaigns.contracts import canonical,digest
            v['split']='test';v['purpose']='final';v['protocol'].update(splits=['test'],purposes=['final'])
            for sample in v['samples']:sample['split']='test'
            with pytest.raises(CampaignError):repo.reserve(v,x.args['root'])
            # Fixture lock for error isolation only, NOT accreditation of E7 selection.
            with repo.transaction() as c:
                c.execute(text('INSERT INTO assessment_final_locks VALUES(:id,:hash,CAST(:evidence AS jsonb),DEFAULT)'),{'id':uuid4(),'hash':digest(v),'evidence':canonical({'status':'locked','identity_hash':digest(v),'candidate':v['model'],'decision':v['decision']})})
        with repo.transaction() as c:
            c.execute(text("CREATE FUNCTION reject_mock_prediction() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'MOCK_VAL_PERSISTENCE' USING ERRCODE='23514'; END $$"))
            c.execute(text('CREATE TRIGGER reject_mock_prediction BEFORE INSERT ON assessment_results FOR EACH ROW EXECUTE FUNCTION reject_mock_prediction()'))
        with pytest.raises(CampaignError):run(repo,v,x.args['root'],Runtime)
        assert x.repo.session(s['run_id'])['state']=='verified'
        with repo.transaction(readonly=True) as c:
            assert c.execute(text("SELECT state FROM assessment_attempts")).scalar_one()=='failed'
            assert c.execute(text('SELECT count(*) FROM assessment_results')).scalar_one()==0
        print('VAL SQL rejection leaves TRAIN verified and VAL failed; zero partial predictions')


@pytest.fixture(autouse=True)
def remove_owned_artifacts(tmp_path):
    yield
    import shutil
    shutil.rmtree(tmp_path)
    assert not tmp_path.exists()
