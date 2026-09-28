"""SELECT-only operational checks; run inside the existing backend."""
import json
from pathlib import Path
from sqlalchemy import text
from src.malaria_dl.persistence.database import get_engine
from common import require,fingerprint
m=json.loads((Path(__file__).parent/'manifest.json').read_text())
with get_engine().connect().execution_options(postgresql_readonly=True,isolation_level='REPEATABLE READ') as c:
 with c.begin():
  identity=list(c.execute(text("SELECT current_database(),current_schema(),session_user,(SELECT system_identifier::text FROM pg_control_system()),current_setting('transaction_read_only')")).one())
  require(identity==['malaria_experiments','public','julio','7668020338728398886','on'],'IDENTITY_CHANGED')
  states={}
  for table in list(m['active_states'])+['experimental_campaigns','campaign_members']:
   columns=c.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=:t"),{'t':table}).scalars().all()
   key={'image_quality_assessments':'assessment_status','microscopy_analysis_runs':'run_status'}.get(table, 'status' if 'status' in columns else 'state')
   require(key in columns,'STATE_COLUMN_UNKNOWN')
   states[table]=dict(c.execute(text('SELECT "'+key+'",count(*) FROM "'+table+'" GROUP BY "'+key+'"')).all())
  for t,expected in m['active_states'].items():require(states[t]==expected,'STATE_DRIFT:'+t)
  require(states['experimental_campaigns']=={'paused':2},'CAMPAIGN_ACTIVE')
  gate=c.execute(text('SELECT to_jsonb(t) FROM experiment_execution_gate t')).scalars().all()
  require(len(gate)==1 and gate[0]['owner'] is None and gate[0]['db_pid'] is None and gate[0]['blocked_reason'] is None and gate[0]['process_evidence']=={},'GATE_NOT_FREE')
  activities=[dict(r) for r in c.execute(text("SELECT pid,usename,application_name,state,xact_start,wait_event_type,wait_event FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() ORDER BY pid")).mappings()]
  require(not any(r['xact_start'] is not None for r in activities),'OTHER_TRANSACTION')
  locks=[dict(r) for r in c.execute(text("SELECT locktype,mode,granted,pid,relation::regclass::text AS relation FROM pg_locks WHERE database=(SELECT oid FROM pg_database WHERE datname=current_database()) AND pid<>pg_backend_pid()")).mappings()]
  out={'identity':identity,'revision':c.execute(text('SELECT version_num FROM alembic_version')).scalar_one(),'states':states,'gate':gate,'activity':activities,'locks':locks,'at':str(c.execute(text('SELECT clock_timestamp()')).scalar_one()),'publications':c.execute(text('SELECT to_jsonb(t) FROM stage2_model_publications t ORDER BY id')).scalars().all(),'deployments':c.execute(text('SELECT to_jsonb(t) FROM deployed_model_versions t ORDER BY id')).scalars().all()}
  actual=fingerprint(c,'public')
  expected={t:{'count':v['current'],'sha256':v['sha256_before']} for t,v in m['tables'].items()}
  drift={t:{'approved':expected.get(t),'observed':actual.get(t)} for t in sorted(set(expected)|set(actual)) if expected.get(t)!=actual.get(t)}
  out.update(table_fingerprints=actual,inventory_drift=drift,result='STOP_INVENTORY_DRIFT' if drift else 'DATABASE_PRECHECK_ONLY_PASSED')
print(json.dumps(out,default=str))
raise SystemExit(2 if drift else 0)
