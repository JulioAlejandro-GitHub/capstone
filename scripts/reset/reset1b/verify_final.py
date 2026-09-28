"""Read-only final catalogue and retained indirect-reference checks in the clone."""
import json
from pathlib import Path
from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL
from common import require,assert_clone
HERE=Path(__file__).resolve().parent
cfg=json.loads((HERE/'target.json').read_text());m=json.loads((HERE/'manifest.json').read_text())
require(cfg['container'].startswith('capstone-reset1b-') and cfg['database']=='reset1b_rehearsal','CLONE_REQUIRED')
engine=create_engine(URL.create('postgresql+psycopg',username=cfg['user'],password=cfg['password'],host=cfg['container'],database=cfg['database']),connect_args={'options':'-c search_path='+cfg['schema']+',pg_catalog'})
ids={str(row['id']) for table in ('runs','model_versions','experimental_campaigns','campaign_members','campaign_attempts','microscopy_analysis_runs','cell_detection_runs','cell_classification_runs') for row in m['tables'][table].get('ids',[])}
def walk(value,path=''):
 if isinstance(value,dict):
  for key,v in value.items():yield from walk(v,path+'.'+key)
 elif isinstance(value,list):
  for i,v in enumerate(value):yield from walk(v,path+'['+str(i)+']')
 elif isinstance(value,str) and value in ids:yield {'field':path,'historical_id':value}
with engine.connect().execution_options(postgresql_readonly=True) as c:
 with c.begin():
  assert_clone(c,cfg)
  out={'revision':c.execute(text('SELECT version_num FROM alembic_version')).scalar_one(),'maintenance_functions_remaining':c.execute(text("SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname=:s AND p.proname LIKE '\\_reset1b\\_%'"),{'s':cfg['schema']}).scalar_one(),'disabled_triggers_including_fk':c.execute(text("SELECT count(*) FROM pg_trigger t JOIN pg_class r ON r.oid=t.tgrelid JOIN pg_namespace n ON n.oid=r.relnamespace WHERE n.nspname=:s AND t.tgenabled<>'O'"),{'s':cfg['schema']}).scalar_one(),'unvalidated_constraints':c.execute(text('SELECT count(*) FROM pg_constraint WHERE connamespace=CAST(:s AS regnamespace) AND NOT convalidated'),{'s':cfg['schema']}).scalar_one(),'public_tables_in_clone':c.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='public'")).scalar_one(),'retained_indirect_references':[]}
  for table in [*m['protected_tables'],'audit_events']:
   if m['tables'][table]['current']>10000:continue
   for row in c.execute(text('SELECT to_jsonb(t) FROM "'+table+'" t')).scalars():
    refs=list(walk(row))
    if refs:out['retained_indirect_references'].append({'table':table,'pk':{k:row[k] for k in m['tables'][table]['pk']},'references':refs})
  require(out['maintenance_functions_remaining']==out['disabled_triggers_including_fk']==out['unvalidated_constraints']==out['public_tables_in_clone']==0,'FINAL_CATALOG_INVALID')
print(json.dumps(out,default=str))
