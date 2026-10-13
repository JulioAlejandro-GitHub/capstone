"""E10.10 success transitions, privileged tampering and independent DB writers."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import json
import os
from pathlib import Path
from threading import Barrier, Event
from uuid import uuid4

import pytest
from sqlalchemy import text
from src.malaria_dl.campaigns.contracts import CampaignError, digest
from src.malaria_dl.execution.artifacts import verify_session
from src.malaria_dl.execution.completion import CompletionError, TrainingCompletionContractV1
from src.malaria_dl.execution.contracts import RunEventType as E
from src.malaria_dl.results.identity import canonical_event
from src.malaria_dl.results.errors import ResultError
from test_campaigns_postgres import isolated  # noqa: F401
from test_result_repository_postgres import pg, item  # noqa: F401
from test_docker_train_postgres import docker  # noqa: F401
from test_docker_reporter_postgres import reporter, legacy_repository
from test_event_emitter_records_postgres import valid_legacy_session

pytestmark=pytest.mark.skipif(os.getenv('RUN_E10_POSTGRES_TESTS')!='1',reason='Explicit disposable-schema opt-in')


@pytest.fixture
def prepared(docker,monkeypatch):
    x=docker; original=x.repo.finish; captured=[]
    def defer(run,owner,state,evidence=None,cause=None):
        if state=='completed':captured.append(deepcopy(evidence));return
        return original(run,owner,state,evidence,cause)
    monkeypatch.setattr(x.repo,'finish',defer)
    assert x.launch()==0
    monkeypatch.setattr(x.repo,'finish',original)
    x.completion=captured[0]
    return x


def finish(x):
    x.repo.finish(x.session['run_id'],x.session['owner'],'completed',x.completion)


def state(x):
    with x.pg.sql() as c:
        return c.execute(text('SELECT to_jsonb(s) FROM train_execution_sessions s WHERE run_id=:id'),{'id':x.session['run_id']}).scalar_one()


def mutate_event(x,index,change):
    event=x.repo.result_events(x.session['run_id'])[index]
    altered=change(event)
    with x.pg.sql() as c:
        c.execute(text('ALTER TABLE train_execution_records DISABLE TRIGGER USER'))
        c.execute(text('UPDATE train_execution_records SET payload=CAST(:payload AS jsonb) WHERE event_id=:id'),
                  {'payload':json.dumps({'canonical_event':canonical_event(altered)}),'id':event.event_id})
        c.execute(text('ALTER TABLE train_execution_records ENABLE TRIGGER USER'))


def tamper(x,case):
    rid=x.session['run_id']
    if case in ('event','evaluation_missing','terminal_missing','failed','duplicate_evaluation'):
        if case=='event':mutate_event(x,-2,lambda e:replace(e,occurred_at=e.occurred_at+timedelta(seconds=1)))
        elif case=='evaluation_missing':mutate_event(x,-2,lambda e:replace(e,event_type=E.EPOCH_COMPLETED))
        elif case=='terminal_missing':mutate_event(x,-1,lambda e:replace(e,event_type=E.PHASE_COMPLETED))
        elif case=='failed':mutate_event(x,-1,lambda e:replace(e,event_type=E.TRAINING_FAILED))
        else:
            payload=x.repo.result_events(rid)[-2].to_dict()['payload']
            mutate_event(x,0,lambda e:replace(e,event_type=E.EVALUATION_COMPLETED,payload=payload))
        return
    with x.pg.sql() as c:
        if case in ('parameters','projection','threshold','matrix'):
            params=c.execute(text('SELECT parameters FROM runs WHERE id=:id'),{'id':rid}).scalar_one()
            if case=='parameters':params.pop('training_results')
            elif case=='projection':params['training_results']['validation']['metrics']['roc_auc']=.3
            elif case=='threshold':params['training_results']['validation']['threshold']['value']=.123
            else:params['training_results']['validation']['confusion_matrix']['tp']+=1
            c.execute(text('UPDATE runs SET parameters=CAST(:p AS jsonb) WHERE id=:id'),{'p':json.dumps(params),'id':rid})
        elif case in ('artifact_hash','artifact_path'):
            c.execute(text('ALTER TABLE train_execution_records DISABLE TRIGGER USER'))
            field,value=('sha256','0'*64) if case=='artifact_hash' else ('path','/synthetic-tamper/foreign.keras')
            c.execute(text("UPDATE train_execution_records SET payload=jsonb_set(payload,ARRAY[:field],CAST(:value AS jsonb)) WHERE run_id=:id AND kind='artifact'"),{'id':rid,'field':field,'value':json.dumps(value)})
            c.execute(text('ALTER TABLE train_execution_records ENABLE TRIGGER USER'))
        elif case in ('snapshot','population','seal'):
            c.execute(text('ALTER TABLE train_execution_sessions DISABLE TRIGGER USER'))
            if case=='seal':
                c.execute(text("UPDATE train_execution_sessions SET completion=completion-'training_completion' WHERE run_id=:id"),{'id':rid})
            else:
                path='{patient_assignment_fingerprint}' if case=='snapshot' else '{counts,val}'
                value=json.dumps('0'*64 if case=='snapshot' else 999)
                c.execute(text('UPDATE train_execution_sessions SET dataset=jsonb_set(dataset,CAST(:path AS text[]),CAST(:value AS jsonb)) WHERE run_id=:id'),{'id':rid,'path':path,'value':value})
            c.execute(text('ALTER TABLE train_execution_sessions ENABLE TRIGGER USER'))
        elif case=='dataset_version':
            new=uuid4();c.execute(text('INSERT INTO dataset_versions(id) VALUES(:id)'),{'id':new})
            c.execute(text('ALTER TABLE runs DISABLE TRIGGER USER'))
            c.execute(text('UPDATE runs SET dataset_version_id=:dataset WHERE id=:id'),{'id':rid,'dataset':new})
            c.execute(text('ALTER TABLE runs ENABLE TRIGGER USER'))


def test_atomic_completion_seal_verification_and_safe_repeat(prepared):
    x=prepared; raw=deepcopy(x.completion);finish(x)
    current=x.repo.session(x.session['run_id']);seal=TrainingCompletionContractV1.from_dict(current['completion']['training_completion'])
    assert {k:v for k,v in current['completion'].items() if k!='training_completion'}==raw
    assert x.completion==raw and seal.records_hash==digest(x.repo.records(x.session['run_id']))
    before=state(x)
    with pytest.raises(CampaignError):finish(x)
    assert state(x)==before
    proof=verify_session(x.repo,current,lambda *a:None)
    assert proof['training_completion_hash']==digest(seal.to_dict())
    x.repo.finish(current['run_id'],current['owner'],'verified',proof)
    assert x.repo.session(current['run_id'])['state']=='verified'
    with x.pg.sql() as c:
        run_before = c.execute(text('SELECT to_jsonb(r) FROM runs r WHERE id=:id'),
                               {'id': current['run_id']}).scalar_one()
    proof = verify_session(x.repo, x.repo.session(current['run_id']), lambda *a: None)
    x.repo.finish(current['run_id'], current['owner'], 'verified', proof)
    with x.pg.sql() as c:
        assert c.execute(text('SELECT to_jsonb(r) FROM runs r WHERE id=:id'),
                         {'id': current['run_id']}).scalar_one() == run_before


@pytest.mark.parametrize('case',['evaluation_missing','terminal_missing','parameters','projection','failed','duplicate_evaluation','population','dataset_version','snapshot','artifact_hash'])
def test_completion_rejected_without_state_mutations(prepared,case):
    x=prepared;tamper(x,case);before=state(x)
    with pytest.raises(CompletionError):finish(x)
    assert state(x)==before and before['state']=='active'
    with x.pg.sql() as c:
        assert c.execute(text('SELECT state FROM campaign_attempts WHERE id=:id'),{'id':x.session['attempt_id']}).scalar_one()=='active'
        assert c.execute(text('SELECT status FROM runs WHERE id=:id'),{'id':x.session['run_id']}).scalar_one()=='running'


@pytest.mark.parametrize('case',['parameters','projection','threshold','matrix','event','artifact_hash','artifact_path','dataset_version','snapshot','seal'])
def test_tampering_after_completed_blocks_verification(prepared,case):
    x=prepared;finish(x);current=x.repo.session(x.session['run_id'])
    proof=verify_session(x.repo,current,lambda *a:None)
    tamper(x,case);before=state(x)
    with pytest.raises(CompletionError):verify_session(x.repo,x.repo.session(current['run_id']),lambda *a:None)
    # A proof obtained BEFORE tampering cannot bypass the protected transition.
    with pytest.raises(CompletionError):x.repo.finish(current['run_id'],current['owner'],'verified',proof)
    assert state(x)==before


def test_physical_checkpoint_change_after_loader_blocks_verified(prepared):
    x=prepared;finish(x);s=x.repo.session(x.session['run_id']);proof=verify_session(x.repo,s,lambda *a:None)
    path=Path(proof['artifact']['path']);original=path.read_bytes()
    try:
        path.write_bytes(b'changed after successful loader')
        with pytest.raises(CampaignError,match='CHECKPOINT_CONTENT_CHANGED'):x.repo.finish(s['run_id'],s['owner'],'verified',proof)
    finally:path.write_bytes(original)
    assert x.repo.session(s['run_id'])['state']=='completed'


def test_failure_during_state_update_rolls_back_seal_and_attempt(prepared):
    x=prepared
    with x.pg.sql() as c:
        c.execute(text("""CREATE FUNCTION reject_e10_finish() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN IF NEW.status='completed' THEN RAISE EXCEPTION 'SYNTHETIC_STATE_FAILURE'; END IF; RETURN NEW; END $$;
        CREATE TRIGGER reject_e10_finish BEFORE UPDATE OF status ON runs FOR EACH ROW EXECUTE FUNCTION reject_e10_finish();"""))
    before=state(x)
    with pytest.raises(CampaignError):finish(x)
    assert state(x)==before and before['completion'] is None


def test_concurrent_finish_has_one_transition(prepared):
    x=prepared;barrier=Barrier(2)
    def attempt():
        barrier.wait(timeout=10)
        try:finish(x);return 'completed'
        except CampaignError:return 'rejected'
    with ThreadPoolExecutor(2) as pool:outcomes=list(pool.map(lambda _:attempt(),range(2)))
    assert sorted(outcomes)==['completed','rejected']
    assert state(x)['completion']['training_completion']['schema_version']=='training_completion_v1'


def test_writer_cannot_change_evidence_during_completion(prepared,monkeypatch):
    from src.malaria_dl.execution.completion import TrainingCompletionValidator
    from src.malaria_dl.execution.composition import build_docker_run_reporter
    x=prepared;entered=Event();release=Event();original=TrainingCompletionValidator.validate
    def wait(self,*args,**kwargs):
        entered.set();assert release.wait(15)
        return original(self,*args,**kwargs)
    monkeypatch.setattr(TrainingCompletionValidator,'validate',wait)
    with ThreadPoolExecutor(1) as pool:
        future=pool.submit(finish,x)
        assert entered.wait(10)
        try:
            ctx=x.contexts[0];chain=build_docker_run_reporter(ctx,execution_token=x.pg.token,engine_factory=x.pg.factory)
            extra=item(ctx,sequence=len(x.repo.result_events(ctx.run_id))+1)
            with pytest.raises(ResultError):chain.report(extra)
        finally:release.set()
        future.result(timeout=15)
    assert state(x)['state']=='completed'
    assert x.repo.result_events(x.session['run_id'])[-1].event_type is E.TRAINING_COMPLETED


@pytest.mark.parametrize('terminal',['failed','interrupted'])
def test_failure_paths_need_no_final_evaluation(pg,terminal):
    repo=legacy_repository(pg);reporter(pg).report(item(pg.ctx))
    repo.finish(pg.ctx.run_id,pg.ctx.owner,terminal,cause='SYNTHETIC_FAILURE')
    assert repo.session(pg.ctx.run_id)['state']==terminal


def test_legacy_completion_and_verification_without_e10(pg):
    repo,s=valid_legacy_session(pg)
    repo.finish(pg.ctx.run_id,pg.ctx.owner,'completed',s['completion'])
    current=repo.session(pg.ctx.run_id);proof=verify_session(repo,current,lambda *a:None)
    assert 'training_completion' not in current['completion'] and 'training_completion_hash' not in proof
    repo.finish(pg.ctx.run_id,pg.ctx.owner,'verified',proof)
    assert repo.session(pg.ctx.run_id)['state']=='verified'
