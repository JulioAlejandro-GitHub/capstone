"""E10.9 atomic event + scientific projection over real independent connections."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import os
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import text
from src.malaria_dl.results import ResultService
from src.malaria_dl.results.errors import (FinalEvaluationConflict, ResultPersistenceError,
    EventIdConflict, SequenceGap, SequenceConflict, WriterNotAuthorized, InvalidScientificResult)
from src.malaria_dl.execution.contracts import RunEventType as E
from src.malaria_dl.execution.emitter import RunEventEmitter
from src.malaria_dl.local_execution.event_journal import SQLiteEventJournal, StreamIdentity
from src.malaria_dl.local_execution.event_transport import EventTransportFailure
from src.malaria_dl.campaigns.contracts import digest
from test_campaigns_postgres import isolated  # noqa: F401
from test_result_repository_postgres import pg, item  # noqa: F401
from test_http_reporter_postgres import remote, wire  # noqa: F401
from test_docker_reporter_postgres import legacy_repository
from test_training_results import payload

pytestmark=pytest.mark.skipif(os.getenv('RUN_E10_POSTGRES_TESTS')!='1',reason='Temporary schemas only; explicit opt-in')


def parameters(pg):
    with pg.sql() as c:return c.execute(text('SELECT parameters FROM runs WHERE id=:id'),{'id':pg.ctx.run_id}).scalar_one()


def scientific(pg,**changes):
    return item(pg.ctx,event_type=E.EVALUATION_COMPLETED,payload=payload(),**changes)


def test_atomic_merge_duplicate_immutable_and_hash(pg):
    with pg.sql() as c:c.execute(text("UPDATE runs SET parameters='{"+'"legacy":{"nested":[1,true]}}'+"'::jsonb WHERE id=:id"),{'id':pg.ctx.run_id})
    legacy=legacy_repository(pg);before_hash=digest(legacy.records(pg.ctx.run_id))
    service=ResultService(pg.repository());event=scientific(pg)
    assert service.accept_event(pg.ctx,event).status.value=='accepted'
    expected={'legacy':{'nested':[1,True]},'training_results':{'schema_version':'training_results_v1','validation':payload()}}
    assert parameters(pg)==expected
    assert ResultService(pg.repository()).accept_event(pg.ctx,event).status.value=='duplicate_accepted'
    with pytest.raises(FinalEvaluationConflict):service.accept_event(pg.ctx,scientific(pg,sequence=2))
    assert parameters(pg)==expected and len(legacy.result_events(pg.ctx.run_id))==1
    assert digest(legacy.records(pg.ctx.run_id))==before_hash


def test_projection_failure_rolls_back_insert(pg):
    with pg.sql() as c:
        c.execute(text("""CREATE FUNCTION reject_scientific_projection() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'SYNTHETIC_PROJECTION_FAILURE'; END $$;
        CREATE TRIGGER reject_science BEFORE UPDATE OF parameters ON runs
        FOR EACH ROW EXECUTE FUNCTION reject_scientific_projection();"""))
    with pytest.raises(ResultPersistenceError):ResultService(pg.repository()).accept_event(pg.ctx,scientific(pg))
    assert parameters(pg)=={} and len(pg.records())==1  # Only initial legacy evidence.


@pytest.mark.parametrize('case',['conflict','sequence','gap','writer','malformed'])
def test_rejections_keep_both_stores_intact(pg,case):
    service=ResultService(pg.repository());event=scientific(pg);ctx=pg.ctx
    error=InvalidScientificResult
    if case in ('conflict','sequence'):
        service.accept_event(ctx,event)
        if case=='conflict':event=replace(event,payload={});error=EventIdConflict
        else:event=replace(event,event_id=uuid4());error=SequenceConflict
    if case=='gap':event=replace(event,sequence=2);error=SequenceGap
    if case=='writer':ctx=replace(ctx,owner=uuid4());error=WriterNotAuthorized
    if case=='malformed':event=replace(event,payload={})
    before=parameters(pg);rows=pg.records()
    with pytest.raises(error):service.accept_event(ctx,event)
    assert parameters(pg)==before and pg.records()==rows


@pytest.mark.parametrize('existing',[{'training_results':None}, {'training_results':{'legacy':'unknown'}}, []])
def test_namespace_never_overwritten(pg,existing):
    with pg.sql() as c:c.execute(text('UPDATE runs SET parameters=CAST(:p AS jsonb) WHERE id=:id'),{'p':json.dumps(existing),'id':pg.ctx.run_id})
    with pytest.raises(FinalEvaluationConflict):ResultService(pg.repository()).accept_event(pg.ctx,scientific(pg))
    assert parameters(pg)==existing and len(pg.records())==1


def test_concurrent_independent_writers_one_final_evaluation(pg):
    barrier=Barrier(2);events=[scientific(pg),scientific(pg)]
    def accept(event):
        barrier.wait(timeout=10)
        try:return ResultService(pg.repository()).accept_event(pg.ctx,event)
        except (ResultPersistenceError,SequenceConflict) as exc:return exc
    with ThreadPoolExecutor(2) as pool:receipts=list(pool.map(accept,events))
    assert sum(getattr(r,'status',None) is not None for r in receipts)==1
    durable=legacy_repository(pg).result_events(pg.ctx.run_id)
    assert len(durable)==1 and parameters(pg)['training_results']['validation']==durable[0].to_dict()['payload']
    loser=next(e for e in events if e.event_id!=durable[0].event_id)
    with pytest.raises(FinalEvaluationConflict):ResultService(pg.repository()).accept_event(pg.ctx,replace(loser,sequence=2))
    assert len(set(pg.pids))>=2


def test_local_journal_lost_ack_retries_identical_projection(pg,remote,tmp_path):
    from src.malaria_dl.local_execution import transport
    from unittest.mock import patch
    identity=StreamIdentity(remote.identity.job_id,remote.identity.agent_id,pg.ctx.run_id,pg.ctx.attempt_id)
    path=tmp_path/'journal.sqlite3';before_hash=digest(legacy_repository(pg).records(pg.ctx.run_id))
    original=transport.urlopen
    def lost(*args,**kwargs):
        with original(*args,**kwargs) as response:assert json.load(response)['status']=='accepted'
        raise OSError('synthetic ACK loss after committed projection')
    with SQLiteEventJournal(path,identity,create=True) as journal:
        emitter=RunEventEmitter(remote.reporter(),run_id=pg.ctx.run_id,attempt_id=pg.ctx.attempt_id,journal=journal)
        with patch.object(transport,'urlopen',lost),pytest.raises(EventTransportFailure):emitter.emit(E.EVALUATION_COMPLETED,payload())
        event=emitter.pending;assert event is not None
    before=parameters(pg);rows=pg.records()
    with SQLiteEventJournal(path,identity) as journal:
        emitter=RunEventEmitter(remote.reporter(),run_id=pg.ctx.run_id,attempt_id=pg.ctx.attempt_id,journal=journal)
        assert emitter.pending.to_dict()==event.to_dict()
        emitter.retry_pending();assert emitter.pending is None and emitter.next_sequence==2
    status,receipt=remote.post(wire(remote,event),remote.token())
    assert status==200 and receipt['status']=='duplicate_accepted'
    assert parameters(pg)==before and pg.records()==rows
    assert digest(legacy_repository(pg).records(pg.ctx.run_id))==before_hash


@pytest.mark.parametrize('case',['malformed','writer','gap','conflict'])
def test_http_rejections_do_not_project(pg,remote,case):
    event=scientific(pg);bearer=remote.token();expected=422
    if case=='malformed':event=replace(event,payload={})
    if case=='writer':bearer=remote.token(remote.other);expected=403
    if case=='gap':event=replace(event,sequence=2);expected=409
    if case=='conflict':
        assert remote.post(wire(remote,event),bearer)[0]==200
        event=replace(event,payload={});expected=409
    before=parameters(pg);rows=pg.records()
    assert remote.post(wire(remote,event),bearer)[0]==expected
    assert parameters(pg)==before and pg.records()==rows
