"""Real runtime E10 service projection probe; synthetic fixtures, no training claim."""
import json, os, sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'docs/audits/e10_10_5e2_evidence/route_a'
sys.path[:0]=[str(ROOT),str(ROOT/'malaria_dl_local_project')]
os.environ['PGV2_EVIDENCE_DIR']=str(E)
os.environ['PGPASSFILE']=json.loads((E/'private_paths.json').read_text())['pgpass']
from verify_v2_route_a import guard, connect, RUNTIME
from test_v2_route_a_server import fixture, insert
from sqlalchemy import create_engine, text, event as sql_event
from src.malaria_dl.execution.contracts import ExecutionContext,ExecutionMode,RunEvent,RunEventType
from src.malaria_dl.persistence.result_repository import PostgresResultRepository
from src.malaria_dl.results import ResultService
from src.malaria_dl.results.errors import ResultPersistenceError,WriterNotAuthorized,SequenceGap,SequenceConflict,EventIdConflict
from src.malaria_dl.evaluation.validation import evaluate_validation_predictions
from src.malaria_dl.results.training import ThresholdResult
from src.malaria_dl.results.identity import canonical_event
import hashlib

def main():
 t=guard(); token=uuid4(); owner=uuid4(); out={}
 # Retain the real advisory lock on a real runtime connection for this probe.
 with connect(t,role=RUNTIME) as lock:
  lock.execute('SELECT pg_advisory_lock(120994,1)')
  lock.execute('UPDATE experiment_execution_gate SET owner=%s,db_pid=pg_backend_pid()',(token,))
  lock.execute("SELECT set_config('capstone.execution_token',%s,false)",(str(token),))
  for stale in lock.execute("SELECT run_id,owner FROM train_execution_sessions WHERE host='E2-synthetic' AND state='active'").fetchall():
   with lock.transaction():
    lock.execute("SELECT set_config('capstone.train_owner',%s,true)",(str(stale['owner']),))
    lock.execute("UPDATE train_execution_sessions SET state='interrupted' WHERE run_id=%s",(stale['run_id'],))
  with lock.transaction():
   lock.execute("SELECT set_config('capstone.execution_token',%s,true)",(str(token),))
   ids=fixture(lock)
   lock.execute('UPDATE experiment_execution_gate SET owner=%s,db_pid=pg_backend_pid()',(token,))
   lock.execute("UPDATE runs SET status='running' WHERE id=%s",(ids['train'],))
   cfg=lock.execute('SELECT execution_parameters FROM runs WHERE id=%s',(ids['train'],)).fetchone()['execution_parameters']['model_configuration_e2']['configuration']
   insert(lock,'train_execution_sessions',dict(run_id=ids['train'],owner=owner,host='E2-synthetic',parent_pid=os.getpid(),configuration=cfg,dataset={'dataset_version_id':str(ids['version'])},environment={'synthetic':True},artifact_root='synthetic://E1/'+str(ids['train'])))
  url=f"postgresql+psycopg://{RUNTIME}@127.0.0.1:{t['host_port']}/{t['database']}"
  errors=[]; statements=[]; fail_metrics=[False]
  def factory():
   engine=create_engine(url)
   @sql_event.listens_for(engine,'before_cursor_execute',retval=True)
   def capture(connection,cursor,statement,parameters,context,many):
    statements.append(statement)
    if fail_metrics[0] and statement.startswith('INSERT INTO run_clinical_metrics'):
     return 'SELECT 1/0', ()
    return statement,parameters
   @sql_event.listens_for(engine,'handle_error')
   def error(ctx):
    errors.append({'sqlstate':getattr(ctx.original_exception,'sqlstate',None),'message':str(ctx.original_exception)})
   return engine
  ctx=ExecutionContext(run_id=ids['train'],owner=owner,execution_mode=ExecutionMode.LOCAL_PYTHON,dataset_version_id=ids['version'],model_id='custom_cnn',adapter_version='fixture-v1')
  svc=ResultService(PostgresResultRepository(execution_token=token,engine_factory=factory))
  epoch=RunEvent(event_id=uuid4(),run_id=ctx.run_id,attempt_id=None,sequence=1,event_type=RunEventType.EPOCH_COMPLETED,occurred_at=datetime.now(timezone.utc),payload={'epoch':0,'loss':.5})
  out['epoch']=svc.accept_event(ctx,epoch).status.value
  out['duplicate']=svc.accept_event(ctx,epoch).status.value
  try: svc.accept_event(replace(ctx,owner=uuid4()),replace(epoch,event_id=uuid4(),sequence=2))
  except WriterNotAuthorized: out['fencing']=True
  else: raise AssertionError('fencing failed')
  result=evaluate_validation_predictions([0,0,1,1],[.1,.8,.6,.9],ThresholdResult(.5,'default'))
  ev=replace(epoch,event_id=uuid4(),sequence=2,event_type=RunEventType.EVALUATION_COMPLETED,payload=result.to_dict())
  try: svc.accept_event(ctx,ev)
  except ResultPersistenceError: out['missing_provenance_rejected']=True
  else: raise AssertionError('missing provenance accepted')
  assert lock.execute('SELECT count(*) AS n FROM train_execution_records WHERE run_id=%s',(ctx.run_id,)).fetchone()['n']==1
  out['missing_provenance_ledger_rollback']=True
  # Explicit synthetic context only exercises the consumer; it does NOT certify a producer.
  protocol={'fixture':'E2 explicit synthetic provenance, not TRAIN output'}
  context={k:hashlib.sha256(k.encode()).hexdigest() for k in ['protocol_hash','population_hash','input_contract_hash','comparison_contract_hash']}
  context.update(checkpoint_artifact_id=str(ids['artifact']),protocol_version='E2-synthetic',protocol_snapshot=protocol)
  from psycopg.types.json import Jsonb
  lock.execute("UPDATE runs SET execution_parameters=execution_parameters || jsonb_build_object('e10_v2_evaluation_context_v1',%s::jsonb) WHERE id=%s",(Jsonb(context),ctx.run_id))
  # Fault after the ledger and evaluation INSERT, at the typed metrics INSERT.
  fail_metrics[0]=True
  try: svc.accept_event(ctx,ev)
  except ResultPersistenceError: out['typed_sql_failure_rejected']=True
  else: raise AssertionError('fault accepted')
  fail_metrics[0]=False
  counts=lock.execute("SELECT (SELECT count(*) FROM train_execution_records WHERE run_id=%s) AS ledger, (SELECT count(*) FROM evaluations WHERE run_id=%s) AS evaluations, (SELECT count(*) FROM run_clinical_metrics WHERE run_id=%s) AS metrics",(ctx.run_id,)*3).fetchone()
  assert counts==dict(ledger=1,evaluations=0,metrics=0)
  assert errors[-1]['sqlstate']=='22012'
  out['typed_sql_failure_rollback']=counts
  out['evaluation']=svc.accept_event(ctx,ev).status.value
  out['evaluation_duplicate']=svc.accept_event(ctx,ev).status.value
  row=lock.execute('SELECT tn,fp,fn,tp,precision_parasitized FROM run_clinical_metrics WHERE run_id=%s',(ctx.run_id,)).fetchone()
  assert [row[k] for k in ('tn','fp','fn','tp')]==[1,1,0,2]
  assert not lock.execute("SELECT parameters ? 'training_results' AS yes FROM runs WHERE id=%s",(ctx.run_id,)).fetchone()['yes']
  assert not any('UPDATE runs' in q and 'training_results' in q for q in statements)
  out['service_never_updates_legacy_results']=True
  stored=lock.execute('SELECT payload FROM train_execution_records WHERE event_id=%s',(ev.event_id,)).fetchone()['payload']['canonical_event']
  assert stored==canonical_event(ev)
  out['ledger_canonical_event_and_typed_atomic']=True
  out['historical_event_bytes_preserved']=True
  out['ids']={k:str(v) for k,v in ids.items()}
  out['sql_errors']=errors
  # No duplicate projection after lost ACK (fresh service/engine recovery).
  recovered=ResultService(PostgresResultRepository(execution_token=token,engine_factory=factory))
  assert recovered.accept_event(ctx,ev).status.value=='duplicate_accepted'
  assert lock.execute('SELECT count(*) AS n FROM evaluations WHERE run_id=%s',(ctx.run_id,)).fetchone()['n']==1
  assert lock.execute('SELECT count(*) AS n FROM run_clinical_metrics WHERE run_id=%s',(ctx.run_id,)).fetchone()['n']==1
  out['fresh_service_replay_after_discarded_ack']=True
  for name,item,error in [
    ('gap',replace(epoch,event_id=uuid4(),sequence=4),SequenceGap),
    ('sequence_conflict',replace(epoch,event_id=uuid4()),SequenceConflict),
    ('event_id_conflict',replace(epoch,payload={'epoch':99}),EventIdConflict)]:
   try: svc.accept_event(ctx,item)
   except error: out[name]=True
   else: raise AssertionError(name)
  import psycopg
  out['check_rejections']=[]
  for statement,params in [
   ("UPDATE runs SET parameters=jsonb_build_object('training_results','{}'::jsonb) WHERE id=%s",(ctx.run_id,)),
   ("INSERT INTO runs(id,run_type,status,parameters) VALUES (%s,'evaluation','running',jsonb_build_object('training_results','{}'::jsonb))",(uuid4(),))]:
   try:
    with lock.transaction(): lock.execute(statement,params)
   except psycopg.Error as error:
    assert error.sqlstate=='23514' and error.diag.constraint_name=='ck_v2_no_result_json'
    out['check_rejections'].append({'sqlstate':error.sqlstate,'constraint':error.diag.constraint_name})
   else: raise AssertionError('scientific JSONB accepted')
  # E-03: reproduce both prohibited E10 calibration roles with otherwise valid
  # columns copied from the accepted synthetic evaluation. No source relabeling.
  out['calibration_architectural_block']=[]
  base=lock.execute('SELECT * FROM evaluations WHERE run_id=%s',(ctx.run_id,)).fetchone()
  for role in ('calibration_default','calibration_selected'):
   candidate=dict(base,id=uuid4(),evaluation_role=role,source_record_key=role)
   try:
    with lock.transaction(): insert(lock,'evaluations',candidate)
   except psycopg.Error as error:
    assert error.sqlstate=='23514' and error.diag.constraint_name=='v2_evaluations_check_6a2239d39784'
    out['calibration_architectural_block'].append({'role':role,'source_kind':'e10','sqlstate':error.sqlstate,'constraint':error.diag.constraint_name})
   else: raise AssertionError('unexpected calibration role acceptance')
  lock.execute("SELECT set_config('capstone.train_owner',%s,false)",(str(owner),))
  lock.execute("UPDATE train_execution_sessions SET state='interrupted' WHERE run_id=%s",(ctx.run_id,))
  lock.execute('UPDATE experiment_execution_gate SET owner=NULL,db_pid=NULL')
  out['scope']='Consumer/service integration only. Synthetic provenance injected explicitly; no TRAIN or producer certification.'
 (E/'e10_projection.json').write_text(json.dumps(out,indent=2,default=str)+'\n')
 print(json.dumps(out,indent=2,default=str))
if __name__=='__main__': raise SystemExit(main())
