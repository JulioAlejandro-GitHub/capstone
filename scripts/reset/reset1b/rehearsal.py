"""Full rollback + committed reset + E10 migration, exclusively in a fresh clone."""
import hashlib,json,re,time,uuid
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path
from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError
from common import require,qi,sha,fingerprint,catalog,assert_clone,orphan_checks
from files import classify,DisposableFiles
HERE=Path(__file__).resolve().parent
cfg=json.loads((HERE/'target.json').read_text());m=json.loads((HERE/'manifest.json').read_text())

def make_engine():
 require(cfg['container'].startswith('capstone-reset1b-') and cfg['database']=='reset1b_rehearsal','PRODUCTION_FORBIDDEN')
 return create_engine(URL.create('postgresql+psycopg',username=cfg['user'],password=cfg['password'],host=cfg['container'],database=cfg['database']),connect_args={'options':'-c search_path='+cfg['schema']+',pg_catalog'})
engine=make_engine();S=qi(cfg['schema']);report={'task':'RESET.1B','target':{k:v for k,v in cfg.items() if k!='password'},'production_execution_authorized':False}

def function_ddl(c, definition):
 # No DBAPI parameters: preserve literal percent signs in approved PL/pgSQL.
 with c.connection.driver_connection.cursor() as cursor:
  cursor.execute(definition)

def checkpoint(stage):
 report['stage']=stage;(HERE/'progress.json').write_text(json.dumps(report,default=str,indent=2))
 print(stage,flush=True,file=__import__('sys').stderr)

def protected(c):
 out=fingerprint(c,cfg['schema'],m['protected_tables'])
 pred=m['tables']['audit_events']['predicate']
 rows=c.execute(text(f'SELECT to_jsonb(t)::text FROM audit_events t WHERE NOT ({pred}) ORDER BY to_jsonb(t)::text')).scalars().all()
 out['audit_events_preserved']={'count':len(rows),'sha256':sha(rows)}
 return out

def normal_probes(c):
 result=[]
 tables=sorted({t['relname'] for t in m['schema_catalog']['triggers'] if 'BEFORE' in t['definition'] and 'DELETE' in t['definition'] and t['relname'] not in m['protected_tables'] and m['tables'][t['relname']]['current']})
 for table in tables:
  cols=m['tables'][table]['pk'];key=dict(c.execute(text('SELECT '+','.join(qi(k) for k in cols)+' FROM '+qi(table)+' LIMIT 1')).mappings().one())
  where=' AND '.join(qi(k)+'=:p'+str(i) for i,k in enumerate(cols));params={'p'+str(i):key[k] for i,k in enumerate(cols)}
  tx=c.begin_nested()
  try:
   c.execute(text('DELETE FROM '+qi(table)+' WHERE '+where),params);c.execute(text('SET CONSTRAINTS ALL IMMEDIATE'))
   raise RuntimeError('NORMAL_GUARD_UNEXPECTEDLY_ALLOWED:'+table)
  except DBAPIError as e:result.append({'table':table,'sqlstate':e.orig.sqlstate,'message':str(e.orig).split('\n')[0]})
  finally:tx.rollback()
 return result

class DeferredCache:
 def __init__(self):self.pending=set()
 def invalidate_model_version(self,value):self.pending.add(str(value))


def depublication(c):
 from src.malaria_dl.governance.services.stage2_publication_service import Stage2PublicationService
 from src.malaria_dl.governance.services.stage2_availability_service import Stage2ModelAvailabilityService
 @contextmanager
 def shared():yield c
 deferred=DeferredCache();pub=Stage2PublicationService(shared);availability=Stage2ModelAvailabilityService(shared,cache=deferred)
 before_pub=c.execute(text('SELECT id::text FROM stage2_model_publications WHERE is_active')).scalars().all()
 before_dep=c.execute(text("SELECT id::text FROM deployed_model_versions WHERE status='active'")).scalars().all()
 for pid in before_pub:pub.deactivate(pid,actor='RESET.1B rehearsal',reason='Isolated history reset',correlation_id=cfg['operation'])
 for did in before_dep:availability.deactivate(did,actor='RESET.1B rehearsal',reason='Isolated history reset')
 deferred.pending.update(row['id'] for row in m['tables']['model_versions']['ids'])
 require(c.execute(text("SELECT count(*) FROM stage2_model_publications WHERE is_active")).scalar_one()==0,'PUBLICATION_ACTIVE')
 require(c.execute(text("SELECT count(*) FROM deployed_model_versions WHERE status='active'")).scalar_one()==0,'DEPLOYMENT_ACTIVE')
 return deferred,{'publications_deactivated':before_pub,'deployments_deactivated':before_dep,'shared_backend_pid':c.execute(text('SELECT pg_backend_pid()')).scalar_one(),'transaction_id':str(c.execute(text('SELECT pg_current_xact_id()')).scalar_one()),'cache_invalidation_deferred_until_commit':True}


def install(c):
 assert_clone(c,cfg)
 require(c.execute(text("SELECT owner IS NULL AND db_pid IS NULL AND blocked_reason IS NULL AND process_evidence='{}'::jsonb FROM experiment_execution_gate")).scalar_one(),'GLOBAL_GATE_NOT_FREE')
 c.execute(text("SELECT set_config('reset1b.operation',:op,true)"),{'op':cfg['operation']})
 template=(HERE/'maintenance.sql').read_text()
 for k,v in {'SCHEMA':S,'SCHEMA_NAME':cfg['schema'],'ROLE':cfg['user'],'OPERATION':cfg['operation'],'CLUSTER':cfg['system_identifier']}.items():template=template.replace('@@'+k+'@@',v)
 c.exec_driver_sql(template)
 allowed={};initial_audit_ids=c.execute(text('SELECT id::text FROM audit_events')).scalars().all()
 for t,desc in m['tables'].items():
  if desc['action']=='PRESERVE':continue
  pred=desc['predicate'];keys=','.join("'"+k+"',t."+qi(k) for k in desc['pk'])
  # The only extra initial row is the publication service event generated in this transaction.
  if t=='stage2_model_publication_events':
   delta=c.execute(text(f'SELECT to_jsonb(t) FROM {qi(t)} t WHERE NOT ({pred})')).scalars().all()
   for r in delta:
    require(r['event_type']=='MODEL_STAGE2_DEACTIVATED' and r['correlation_id']==cfg['operation'] and r['publication_id'] in {p['id'] for p in m['publications_and_deployments']['stage2_model_publications']},'UNAPPROVED_NEW_PUBLICATION_EVENT')
   extra=[r['id'] for r in delta];report.setdefault('publication_events_generated',[]).append(extra)
   if extra:pred+=' OR t.id IN ('+','.join("'"+v+"'::uuid" for v in extra)+')'
  n=c.execute(text(f"INSERT INTO pg_temp.reset1b_allowed SELECT '{cfg['schema']}.{t}'::regclass,sha256(convert_to(to_jsonb(t)::text,'UTF8')),jsonb_build_object({keys}) FROM {S}.{qi(t)} t WHERE {pred}")).rowcount
  require(n==desc['delete']+(len(extra) if t=='stage2_model_publication_events' else 0),'CANDIDATE_DRIFT:'+t)
  allowed[t]=n
 # Keep every FK trigger enabled. Add a temporary operation gate, including protected tables.
 for t in m['tables']:
  c.exec_driver_sql(f'CREATE TRIGGER a_reset1b_delete_scope BEFORE DELETE ON {S}.{qi(t)} FOR EACH ROW EXECUTE FUNCTION {S}._reset1b_delete_scope()')
 functions=[dict(r) for r in c.execute(text("""SELECT DISTINCT p.oid,pg_get_functiondef(p.oid) AS definition,p.proname,p.prosrc FROM pg_trigger t JOIN pg_class r ON r.oid=t.tgrelid JOIN pg_namespace n ON n.oid=r.relnamespace JOIN pg_proc p ON p.oid=t.tgfoid WHERE n.nspname=:s AND NOT t.tgisinternal AND (t.tgtype & 8)>0 AND (t.tgtype & 2)>0 AND t.tgname<>'a_reset1b_delete_scope' AND r.relname=ANY(:tables) ORDER BY p.oid"""),{'s':cfg['schema'],'tables':m['delete_order']}).mappings()]
 for f in functions:
  original=f['definition'];body=f['prosrc']
  modified,n=re.subn(r'\bBEGIN\b',lambda match:match[0]+f"\n IF TG_OP='DELETE' AND {S}._reset1b_allowed(TG_RELID,to_jsonb(OLD)) THEN RETURN OLD; END IF;\n",body,count=1,flags=re.I)
  require(n==1 and body in original,'UNSUPPORTED_GUARD_BODY:'+f['proname']);function_ddl(c,original.replace(body,modified,1))
 report['guard_functions_patched']=[f['proname'] for f in functions]
 return functions,allowed,initial_audit_ids


def negative_scope_probes(c):
 results=[]
 candidate="DELETE FROM train_execution_records WHERE (run_id,kind,phase,record_key) IN (SELECT run_id,kind,phase,record_key FROM train_execution_records LIMIT 1)"
 checks=[('protected_source',None,'DELETE FROM dataset_split_assignments WHERE id IN (SELECT id FROM dataset_split_assignments LIMIT 1)'),('preserved_audit',None,'DELETE FROM audit_events t WHERE NOT ('+m['tables']['audit_events']['predicate']+')'),('wrong_role','SET LOCAL ROLE julio',candidate),('wrong_operation',"SELECT set_config('reset1b.operation','wrong',true)",candidate),('wrong_transaction',"UPDATE pg_temp.reset1b_context SET xid='0'::xid8",candidate),('unchanged_update_rules',None,'UPDATE train_execution_records SET payload=payload')]
 # Resolve the real protected-table PK rather than assume a column.
 pk=m['tables']['dataset_split_assignments']['pk'][0]
 checks[0]=('protected_source',None,f'DELETE FROM dataset_split_assignments WHERE {qi(pk)} IN (SELECT {qi(pk)} FROM dataset_split_assignments LIMIT 1)')
 for name,setup,sql in checks:
  save=c.begin_nested()
  try:
   if setup:c.exec_driver_sql(setup)
   c.exec_driver_sql(sql);raise RuntimeError('NEGATIVE_PROBE_ALLOWED:'+name)
  except DBAPIError as e:
   require(e.orig.sqlstate in ('P0001','55000'),'UNEXPECTED_NEGATIVE_ERROR:'+str(e.orig));results.append({'check':name,'message':str(e.orig).split('\n')[0],'sqlstate':e.orig.sqlstate})
  finally:save.rollback()
 changed=c.execute(text(f"SELECT {S}._reset1b_allowed('train_execution_records'::regclass,to_jsonb(t)||CAST(:change AS jsonb)) FROM train_execution_records t LIMIT 1"),{'change':json.dumps({'payload':{'changed':True}})}).scalar_one()
 require(changed is False,'ALTERED_ROW_AUTHORIZED');results.append({'check':'changed_row_hash','accepted':False})
 return results


def remove_maintenance(c,functions):
 for f in functions:function_ddl(c,f['definition'])
 for t in m['tables']:c.exec_driver_sql(f'DROP TRIGGER a_reset1b_delete_scope ON {S}.{qi(t)}')
 c.exec_driver_sql(f'DROP FUNCTION {S}._reset1b_delete_scope()')
 c.exec_driver_sql(f'DROP FUNCTION {S}._reset1b_allowed(oid,jsonb)')
 # Only session-local operation state is removed, never application tables.
 c.exec_driver_sql('DROP TABLE pg_temp.reset1b_allowed');c.exec_driver_sql('DROP TABLE pg_temp.reset1b_context')
 c.execute(text("SELECT set_config('reset1b.operation','',true)"))


def reset(c,baseline_catalog,protected_before):
 c.execute(text("SET LOCAL lock_timeout='3s'"));c.execute(text("SET LOCAL statement_timeout='300s'"))
 for t in sorted(m['tables']):c.exec_driver_sql(f'LOCK TABLE {S}.{qi(t)} IN SHARE ROW EXCLUSIVE MODE')
 deferred,pub=depublication(c);functions,allowed,audit_before=install(c)
 negatives=negative_scope_probes(c)
 c.exec_driver_sql('SET CONSTRAINTS ALL DEFERRED');deleted={};new_audit=[]
 for table in m['delete_order']:
  if table=='audit_events':
   delta=c.execute(text('SELECT to_jsonb(t) FROM audit_events t WHERE NOT (id::text=ANY(:ids))'),{'ids':audit_before}).scalars().all()
   for r in delta:
    require(r['action']=='delete' and r['resource_type'] in ('campaign_members','campaign_configurations') and r['event_type']=='ml.campaign.'+r['resource_type'],'UNEXPECTED_MAINTENANCE_AUDIT')
    valid=c.execute(text(f"SELECT {S}._reset1b_allowed(CAST(:relation AS regclass),CAST(:value AS jsonb))"),{'relation':cfg['schema']+'.'+r['resource_type'],'value':json.dumps(r['before_state'])}).scalar_one()
    require(valid,'AUDIT_NOT_FROM_APPROVED_ROW');new_audit.append(r['id'])
   if new_audit:
    c.execute(text(f"INSERT INTO pg_temp.reset1b_allowed SELECT 'audit_events'::regclass,sha256(convert_to(to_jsonb(t)::text,'UTF8')),jsonb_build_object('id',t.id) FROM audit_events t WHERE id::text=ANY(:ids)"),{'ids':new_audit})
    allowed[table]+=len(new_audit)
  # The PKs come from the frozen allowlist, not from an unbounded DELETE.
  cols=m['tables'][table]['pk'];join=' AND '.join('t.'+qi(k)+"::text=a.row_key->>'"+k+"'" for k in cols)
  n=c.execute(text(f"DELETE FROM {S}.{qi(table)} t USING pg_temp.reset1b_allowed a WHERE a.relation='{cfg['schema']}.{table}'::regclass AND {join}")).rowcount
  require(n==allowed[table],'DELETE_COUNT_MISMATCH:'+table);deleted[table]=n
 c.exec_driver_sql('SET CONSTRAINTS ALL IMMEDIATE')
 orphans=orphan_checks(c,m,cfg['schema'])
 for table in m['delete_order']:
  count=c.execute(text('SELECT count(*) FROM '+qi(table))).scalar_one()
  require(count==m['tables'][table]['keep'],'HISTORY_REMAINS:'+table)
 require(protected(c)==protected_before,'PROTECTED_DATA_CHANGED')
 remove_maintenance(c,functions)
 require(catalog(c,cfg['schema'])==baseline_catalog,'ORIGINAL_GUARDS_NOT_RESTORED')
 return deferred,{'depublication':pub,'deleted':deleted,'total_deleted':sum(deleted.values()),'new_operation_audit_ids':new_audit,'negative_probes':negatives,'orphan_checks':orphans,'original_catalog_restored':True,'protected_hashes_match':True}


def e10_checks(protected_before):
 from alembic import command
 from alembic.config import Config
 from src.malaria_dl.execution.schema import require_e10_schema,E10SchemaNotReady
 from src.malaria_dl.execution.controlled import ControlledRepository
 from src.malaria_dl.local_execution.backend import LocalBackend
 @contextmanager
 def scope(readonly=False):
  with engine.connect().execution_options(postgresql_readonly=readonly) as c:
   with c.begin():assert_clone(c,cfg);yield c
 class BeforeClaim(Exception):pass
 class Repository(ControlledRepository):
  def get(self,*args):raise BeforeClaim('stop before claim or reservation')
 def guards():
  repo=Repository(scope);result={}
  for name,call in [('docker',repo.preflight_e10_schema),('local',lambda:LocalBackend(repo,{}).prepare({'campaign_id':m['e9_before']['id'],'dataset_id':'unused'}))]:
   try:call();result[name]='E10_SCHEMA_READY'
   except BeforeClaim:result[name]='E10_SCHEMA_READY'
   except E10SchemaNotReady:result[name]='E10_SCHEMA_NOT_READY'
  return result
 before=guards();require(set(before.values())=={'E10_SCHEMA_NOT_READY'},'WRONG_SOURCE_GUARD')
 with scope() as c:
  c.exec_driver_sql("SET LOCAL lock_timeout='3s'");c.exec_driver_sql("SET LOCAL statement_timeout='60s'")
  config=Config('/app/alembic.ini');config.set_main_option('script_location','/app/alembic');config.attributes['connection']=c;command.upgrade(config,'head')
 after=guards();require(set(after.values())=={'E10_SCHEMA_READY'},'E10_NOT_READY')
 with scope(True) as c:
  require(c.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='20260922_01','WRONG_HEAD')
  now=protected(c);old={k:v for k,v in protected_before.items() if k!='alembic_version'}
  require({k:v for k,v in now.items() if k!='alembic_version'}==old,'SOURCE_CHANGED_BY_MIGRATION')
  require(c.execute(text('SELECT count(*) FROM train_execution_records')).scalar_one()==0,'ARTIFICIAL_BACKFILL')
  capabilities=require_e10_schema(c)
 from src.malaria_dl.results.service import ResultService
 from src.malaria_dl.persistence.result_repository import PostgresResultRepository
 from src.malaria_dl.execution.contracts import ExecutionContext,ExecutionMode,RunEvent,RunEventType
 from src.malaria_dl.results.errors import WriterNotAuthorized
 owner=uuid.uuid4();run_id=uuid.uuid4()
 context=ExecutionContext(run_id=run_id,owner=owner,execution_mode=ExecutionMode.DOCKER,dataset_version_id=uuid.UUID('d8c0cab5-09dd-597f-9de7-7ca01aee2ec2'),model_id='custom_cnn',adapter_version='1')
 event=RunEvent(event_id=uuid.uuid4(),run_id=run_id,sequence=1,event_type=next(iter(RunEventType)),occurred_at=datetime.now(timezone.utc),payload={})
 service=ResultService(PostgresResultRepository(execution_token=owner,engine_factory=make_engine))
 try:service.accept_event(context,event)
 except WriterNotAuthorized:rejected=True
 else:raise RuntimeError('UNOWNED_RESULT_ACCEPTED')
 with scope(True) as c:
  empty={t:c.execute(text('SELECT count(*) FROM '+qi(t))).scalar_one() for t in m['delete_order'] if t!='audit_events'}
  require(not any(empty.values()),'HISTORY_CREATED_DURING_E10_CHECK')
 return {'guards_before':before,'guards_after':after,'head':'20260922_01','capabilities':capabilities,'event_rows':0,'ResultService':'AVAILABLE','unowned_new_execution_rejected':rejected,'no_train_or_test_executed':True,'empty_history_counts':empty}


def main():
 checkpoint('restore verification')
 with engine.connect() as c:
  with c.begin():
   assert_clone(c,cfg);before=fingerprint(c,cfg['schema']);expected={k:{'count':v['current'],'sha256':v['sha256_before']} for k,v in m['tables'].items()};require(before==expected,'RESTORE_CONTENT_MISMATCH')
   baseline=catalog(c,cfg['schema']);keep=protected(c);normal=normal_probes(c)
 report.update(restored_tables=len(before),restored_rows=sum(v['count'] for v in before.values()),restore_matches_manifest=True,protected_before=keep,normal_guards_before=normal)
 classification=classify(m);report['file_classification']=classification;checkpoint('copying disposable filesystem')
 fs=DisposableFiles(m,classification);report['filesystem_before']=fs.evidence()
 checkpoint('full reset with forced SQL failure and recovery')
 with engine.connect() as c:
  tx=c.begin()
  try:
   assert_clone(c,cfg);deferred,attempt=reset(c,baseline,keep);report['rollback_full_reset']=attempt
   fs.quarantine();c.exec_driver_sql("DO $$ BEGIN RAISE EXCEPTION 'RESET1B_INJECTED_FAILURE_AFTER_FULL_DELETE'; END $$")
  except DBAPIError as e:
   require('RESET1B_INJECTED_FAILURE_AFTER_FULL_DELETE' in str(e.orig),'UNEXPECTED_RESET_FAILURE:'+str(e.orig))
  finally:tx.rollback();fs.restore()
 with engine.connect() as c:
  with c.begin():
   require(fingerprint(c,cfg['schema'])==before,'DATABASE_NOT_RESTORED_AFTER_FAILURE');require(catalog(c,cfg['schema'])==baseline,'GUARDS_NOT_RESTORED_AFTER_FAILURE')
   require(normal_probes(c)==normal,'NORMAL_GUARD_BEHAVIOR_CHANGED');report['rollback_recovery']={'all_97_tables_equal':True,'all_guards_same_errors':True,'filesystem_restored':True,'cache_invalidations_applied':0}
 checkpoint('full reset and commit exclusively in clone')
 from src.malaria_dl.inference.traceable import ModelCache
 cache=ModelCache(maxsize=100)
 for r in m['tables']['model_versions']['ids']:cache._items[(r['id'],'rehearsal')]=object()
 with engine.connect() as c:
  tx=c.begin();commit_requested=False
  try:
   assert_clone(c,cfg);deferred,success=reset(c,baseline,keep);fs.quarantine();assert_clone(c,cfg)
   commit_requested=True;tx.commit()
  except BaseException:
   if commit_requested:
    # A lost commit acknowledgement is not proof of rollback. Keep copies
    # quarantined for reconciliation against a fresh database connection.
    fs.write_journal('COMMIT_UNCERTAIN')
   else:
    tx.rollback();fs.restore()
   raise
 for mid in deferred.pending:cache.invalidate_model_version(mid)
 require(not cache._items,'STALE_MODEL_CACHE');fs.write_journal('SQL_COMMITTED')
 report['committed_reset']=success;report['cache']={'versions_invalidated':len(deferred.pending),'remaining_entries':len(cache._items),'only_disposable_cache_used':True}
 with engine.connect() as c:
  with c.begin():
   require(catalog(c,cfg['schema'])==baseline,'PERSISTENT_GUARD_EXCEPTION');require(protected(c)==keep,'PROTECTED_CHANGED_AFTER_COMMIT')
   report['protected_after_reset']=protected(c)
   @contextmanager
   def shared():yield c
   from src.malaria_dl.governance.services.stage2_publication_service import Stage2PublicationService
   from src.malaria_dl.governance.services.deployment_service import ModelDeploymentService
   from src.model_governance.errors import GovernanceConflictError
   require(Stage2PublicationService(shared).models()==[],'PUBLISHED_MODEL_REMAINS')
   try:ModelDeploymentService(shared).resolve_alias('malaria-stage2-classifier','stage2','default')
   except GovernanceConflictError:pass
   else:raise RuntimeError('STALE_DEPLOYMENT_ALIAS')
   report['availability']={'state':'SIN_MODELO_PRODUCTIVO','models':[],'available_for_inference':False,'missing_alias':'GovernanceConflictError (controlled)','no_inference_attempted':True}
   tx=c.begin_nested()
   try:c.execute(text('DELETE FROM audit_events'));raise RuntimeError('AUDIT_GUARD_DISABLED_AFTER_RESET')
   except DBAPIError as e:require('audit_events is append-only' in str(e.orig),'AUDIT_GUARD_CHANGED');report['normal_guard_after_commit']=str(e.orig).split('\n')[0]
   finally:tx.rollback()
 checkpoint('migrate empty clone and verify E10 contracts')
 report['e10']=e10_checks(keep)
 report['filesystem_after']=fs.evidence();report['operational_files']=fs.verify_originals()
 from src.malaria_dl.models.registry import enabled_models
 from src.malaria_dl.models.configuration import resolve_config
 report['registry']={model:bool(resolve_config(model)) for model in enabled_models()}
 report['protected_code_hashes']={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in m['scientific_configuration']['files']}
 require(report['protected_code_hashes']==m['scientific_configuration']['files'],'SCIENTIFIC_CODE_CHANGED')
 report['result']='RESET.1B APROBADO';checkpoint('complete');print(json.dumps(report,default=str))

if __name__=='__main__':main()
