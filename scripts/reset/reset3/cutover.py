"""Authorized RESET.3 DB-name swap, fail closed and reconcile commit by OID.

Host orchestration must stop frontend/backend/external clients and finish verified
backup + artifact quarantine first. No DROP/TRUNCATE or migration of old public.
"""
import json,os
from pathlib import Path
from sqlalchemy import create_engine,text
from app.db import get_primary_engine
from common import require,fingerprint
HERE=Path(__file__).parent
ORIGINAL='malaria_experiments';READY='malaria_reset3_ready_20260929';RECOVERY='malaria_pre_reset3_20260929'
evidence=json.loads((HERE/'cutover_prerequisites.json').read_text())
require(all(evidence[k] is True for k in ('writers_stopped','definitive_backup_verified','staging_verified','artifact_quarantine_verified','rename_rehearsal_passed')),'PRECHECKS_REQUIRED')
expected=json.loads((HERE/'source_before.json').read_text())
source=get_primary_engine()
with source.connect().execution_options(postgresql_readonly=True,isolation_level='REPEATABLE READ') as c,c.begin():
 require(tuple(c.execute(text('SELECT current_database(),(SELECT system_identifier::text FROM pg_control_system())')).one())==(ORIGINAL,'7668020338728398886'),'SOURCE_IDENTITY')
 actual={s:fingerprint(c,s) for s in expected['schemas']}
 require(actual==expected['schemas'],'FINAL_SOURCE_DRIFT')
source.dispose()
e=create_engine(source.url.set(database='postgres'))
def state(c):return {r.datname:{'oid':r.oid,'allow_connections':r.datallowconn} for r in c.execute(text('SELECT datname,oid,datallowconn FROM pg_database WHERE datname IN (:a,:b,:d)'),{'a':ORIGINAL,'b':READY,'d':RECOVERY})}
def record(data):
 with (HERE/'cutover.json').open('w') as f:json.dump(data,f,indent=2,default=str);f.flush();os.fsync(f.fileno())
with e.connect() as c:
 require(c.execute(text('SELECT system_identifier::text FROM pg_control_system()')).scalar_one()=='7668020338728398886','CLUSTER_IDENTITY')
 before=state(c);require(set(before)=={ORIGINAL,READY},'DATABASE_SET_MISMATCH')
 active=c.execute(text("SELECT count(*) FROM pg_stat_activity WHERE datname IN (:a,:b) AND backend_type='client backend'"),{'a':ORIGINAL,'b':READY}).scalar_one();require(active==0,'CONNECTIONS_PRESENT')
 c.rollback();report={'result':'PREPARED','before':before,'source_all_schemas_unchanged':True};record(report)
 try:
  with c.begin():
   c.exec_driver_sql("SET LOCAL lock_timeout='5s'");c.exec_driver_sql("SET LOCAL statement_timeout='15s'")
   c.exec_driver_sql('ALTER DATABASE malaria_experiments ALLOW_CONNECTIONS false')
   c.exec_driver_sql('ALTER DATABASE malaria_reset3_ready_20260929 ALLOW_CONNECTIONS false')
   c.exec_driver_sql('ALTER DATABASE malaria_experiments RENAME TO malaria_pre_reset3_20260929')
   c.exec_driver_sql('ALTER DATABASE malaria_reset3_ready_20260929 RENAME TO malaria_experiments')
   c.exec_driver_sql('ALTER DATABASE malaria_experiments ALLOW_CONNECTIONS true')
  report['commit_response_received']=True
 except Exception as exc:
  report['commit_response_received']=False;report['exception_type']=type(exc).__name__
 report['result']='COMMIT_UNCERTAIN_PENDING_RECONCILIATION';record(report)
e.dispose()
with e.connect().execution_options(postgresql_readonly=True) as fresh:
 after=state(fresh);report['after']=after
 if set(after)=={ORIGINAL,RECOVERY} and after[ORIGINAL]['oid']==before[READY]['oid'] and after[RECOVERY]['oid']==before[ORIGINAL]['oid'] and after[ORIGINAL]['allow_connections'] and not after[RECOVERY]['allow_connections']:
  report['result']='COMMIT_CONFIRMED_BY_FRESH_CONNECTION'
 elif after==before:report['result']='ROLLBACK_CONFIRMED_BY_FRESH_CONNECTION'
 else:report['result']='COMMIT_UNCERTAIN_STOP_ALL_WRITERS'
 record(report)
print(json.dumps(report,indent=2));require(report['result']=='COMMIT_CONFIRMED_BY_FRESH_CONNECTION','CUTOVER_NOT_CONFIRMED')
