"""Real PostgreSQL/full filesystem-copy rehearsal of the FINAL RESET.1B block.

No migrations, training, operational writes or production file moves. The only
commit fault is a Python exception AFTER the actual PostgreSQL commit returns;
this is NOT a real network interruption and no SQL/filesystem double is used.
"""
import argparse,ast,hashlib,json,sys
from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
import rehearsal as r
from common import require,fingerprint,catalog,sha,qi,orphan_checks

p=argparse.ArgumentParser();p.add_argument('--case',choices=['success','lost_ack'],required=True);args=p.parse_args()
r.m=json.loads((r.HERE/'reconciled_baseline.json').read_text())
source=Path(r.__file__).read_text();tree=ast.parse(source)
main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
block=next(n for n in main.body if isinstance(n,ast.With) and any(isinstance(v,ast.Name) and v.id=='commit_requested' for v in ast.walk(n)))
block_text=ast.get_source_segment(source,block)
code=compile(ast.fix_missing_locations(ast.Module(body=[block],type_ignores=[])),str(Path(r.__file__)), 'exec')
report={'case':args.case,'final_rehearsal_sha256':hashlib.sha256(source.encode()).hexdigest(),'actual_commit_block_sha256':hashlib.sha256(block_text.encode()).hexdigest(),'real_postgresql':True,'real_disposable_files':True,'network_interruption':False,'fault_mechanism':'exception after real commit returned' if args.case=='lost_ack' else None,'code_path':'exact AST node from final rehearsal.main, real reset(), actual SQL and filesystem; migration section not invoked'}
def stage(value):print(value,file=sys.stderr,flush=True)
def fresh():
 r.engine.dispose()
 return r.engine.connect()
with r.engine.connect() as c:
 with c.begin():
  r.assert_clone(c,r.cfg);before=fingerprint(c,r.cfg['schema'])
  require(before=={t:{'count':v['current'],'sha256':v['sha256_before']} for t,v in r.m['tables'].items()},'RECONCILED_RESTORE_MISMATCH')
  baseline=catalog(c,r.cfg['schema']);keep=r.protected(c);normal=r.normal_probes(c)
classification=r.classify(r.m);stage('copying and hashing actual disposable files')
fs=r.DisposableFiles(r.m,classification);report['filesystem_before']=fs.evidence()
from src.malaria_dl.inference.traceable import ModelCache
cache=ModelCache(maxsize=100)
for row in r.m['tables']['model_versions']['ids']:cache._items[(row['id'],'rehearsal')]=object()

# A connection/transaction proxy delegates every real SQL operation. Only the
# acknowledgement seen by the caller is injected after the server commits.
class LostAcknowledgement(ConnectionError):pass
class TransactionProxy:
 def __init__(self,tx):self.tx=tx
 def commit(self):
  self.tx.commit();report['server_commit_returned_before_injection']=True
  raise LostAcknowledgement('RESET2A_SIMULATED_COMMIT_ACK_LOSS')
 def rollback(self):
  report['unexpected_rollback_after_commit_request']=True
  return self.tx.rollback()
class ConnectionProxy:
 def __init__(self,c):self.c=c
 def __getattr__(self,n):return getattr(self.c,n)
 def begin(self):return TransactionProxy(self.c.begin())
class EngineProxy:
 @contextmanager
 def connect(self):
  with r.engine.connect() as c:yield ConnectionProxy(c)

calls=[]
original_restore=fs.restore
# Instrumentation delegates to the REAL file restore; does not replace its work.
def observed_restore():calls.append('restore');return original_restore()
fs.restore=observed_restore

def scope(engine,reset):
 return {'engine':engine,'cfg':r.cfg,'assert_clone':r.assert_clone,'reset':reset,'baseline':baseline,'keep':keep,'fs':fs}
if args.case=='success':
 stage('full real SQL reset; injected SQL failure after every DELETE and file quarantine')
 def failing_reset(c,*a):
  deferred,result=r.reset(c,*a);report['rollback_reset']=result
  fs.quarantine()
  c.exec_driver_sql("DO $$ BEGIN RAISE EXCEPTION 'RESET2A_AFTER_ALL_DELETES'; END $$")
 env=scope(r.engine,failing_reset)
 try:exec(code,env)
 except DBAPIError as e:require('RESET2A_AFTER_ALL_DELETES' in str(e.orig),'UNEXPECTED_SQL_ERROR')
 else:raise RuntimeError('FAULT_NOT_RAISED')
 with fresh() as c:
  with c.begin():
   r.assert_clone(c,r.cfg)
   require(fingerprint(c,r.cfg['schema'])==before,'ROLLBACK_DATA_MISMATCH')
   require(catalog(c,r.cfg['schema'])==baseline,'ROLLBACK_CATALOG_MISMATCH')
   require(r.normal_probes(c)==normal,'ROLLBACK_GUARD_BEHAVIOR_MISMATCH')
 require(fs.snapshot()==fs.before and calls==['restore'],'FILES_NOT_RESTORED')
 require(len(cache._items)==36,'PREMATURE_CACHE_INVALIDATION')
 report['rollback_recovery']={'all_97_tables_equal':True,'catalog_exactly_equal':True,'all_normal_guard_errors_equal':True,'real_files_restored':True,'files':len(fs.entries),'cache_unchanged':True}
 calls.clear()
stage('full real SQL reset and '+args.case)
def counted_reset(c,*a):
 report['transaction_backend_pid']=c.execute(text('SELECT pg_backend_pid()')).scalar_one()
 return r.reset(c,*a)
env=scope(EngineProxy() if args.case=='lost_ack' else r.engine,counted_reset)
try:exec(code,env)
except LostAcknowledgement:
 require(args.case=='lost_ack','UNEXPECTED_LOST_ACK')
 require(json.loads((fs.root/'journal.json').read_text())['state']=='COMMIT_UNCERTAIN','UNCERTAIN_NOT_RECORDED')
 require(not calls and not report.get('unexpected_rollback_after_commit_request'),'UNSAFE_AUTOMATIC_RESTORE')
 require(all(v['location']=='quarantine' for k,v in fs.snapshot().items() if any(e['key']==k and e['move'] for e in fs.entries)),'QUARANTINE_LOST')
 require(len(cache._items)==36,'UNCERTAIN_CACHE_INVALIDATION')
 report['uncertain_before_reconciliation']={'state':'COMMIT_UNCERTAIN','automatic_file_restore_calls':0,'rollback_requested':False,'cache_entries_preserved':36,'files_kept_in_quarantine':True}
else:require(args.case=='success','ACK_FAULT_NOT_INJECTED')

# Independent new physical connection; never infer rollback from an exception.
stage('reconciling complete postconditions on a fresh PostgreSQL connection')
with fresh() as c:
 with c.begin():
  r.assert_clone(c,r.cfg)
  pid=c.execute(text('SELECT pg_backend_pid()')).scalar_one();require(pid!=report['transaction_backend_pid'],'CONNECTION_NOT_NEW')
  after=fingerprint(c,r.cfg['schema']);require(catalog(c,r.cfg['schema'])==baseline,'COMMITTED_CATALOG_MISMATCH')
  require(r.protected(c)==keep,'COMMITTED_PROTECTED_MISMATCH')
  for table,desc in r.m['tables'].items():
   require(after[table]['count']==desc['keep'],'POSTCOMMIT_COUNT_MISMATCH:'+table)
   if desc['keep']==0:require(after[table]['sha256']==sha([]),'NONEMPTY_HISTORY')
  orphans=orphan_checks(c,r.m,r.cfg['schema'])
  require(c.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='20260915_01','MIGRATION_EXECUTED')
  @contextmanager
  def shared():yield c
  from src.malaria_dl.governance.services.stage2_publication_service import Stage2PublicationService
  from src.malaria_dl.governance.services.deployment_service import ModelDeploymentService
  from src.model_governance.errors import GovernanceConflictError
  require(Stage2PublicationService(shared).models()==[],'PUBLICATION_REMAINS')
  try:ModelDeploymentService(shared).resolve_alias('malaria-stage2-classifier','stage2','default')
  except GovernanceConflictError:pass
  else:raise RuntimeError('DEPLOYMENT_REMAINS')
  save=c.begin_nested()
  try:c.exec_driver_sql('DELETE FROM audit_events');raise RuntimeError('GUARD_NOT_RESTORED')
  except DBAPIError as e:require('audit_events is append-only' in str(e.orig),'GUARD_ERROR_CHANGED')
  finally:save.rollback()
  report['reconciliation']={'state':'COMMIT_CONFIRMED','new_backend_pid':pid,'full_postconditions_checked':True,'all_70_history_tables_empty':sum(v['count']==0 for t,v in after.items() if t in r.m['delete_order'])==70,'protected_rows':sum(v['count'] for v in keep.values()),'protected_hashes':keep,'catalog_restored':True,'original_append_only_guard_rejected_delete':True,'foreign_keys':orphans,'alembic_revision':'20260915_01','availability':'SIN_MODELO_PRODUCTIVO'}
for mid in env['deferred'].pending:cache.invalidate_model_version(mid)
require(not cache._items,'CACHE_STALE');fs.write_journal('SQL_COMMITTED')
report['committed_reset']=env['success'];report['cache_invalidations_after_confirmation']=len(env['deferred'].pending)
report['filesystem_after']=fs.evidence();report['original_operational_files']=fs.verify_originals()
report['file_restore_calls_after_commit_request']=calls
report['result']='PASS';print(json.dumps(report,default=str))
