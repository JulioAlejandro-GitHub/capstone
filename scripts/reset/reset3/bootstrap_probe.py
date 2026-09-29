"""Isolated schema-construction preflight. Never connects to the canonical DB.

Uses original legacy DDL and Alembic files; omits legacy sample-data seed 004
because it fabricates an experiment and a different split. No source data import.
"""
import hashlib,importlib.util,json
from pathlib import Path
from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL
from alembic import command
from alembic.config import Config
HERE=Path(__file__).parent
cfg=json.loads((HERE/'target.json').read_text())
assert cfg['container'].startswith('capstone-reset3-') and cfg['database']=='reset3_candidate'
engine=create_engine(URL.create('postgresql+psycopg',username=cfg['user'],password=cfg['password'],host=cfg['container'],database=cfg['database']))
report={'target':{k:v for k,v in cfg.items() if k!='password'},'legacy_files':[],'seed_004_excluded':'sample experiment and split are forbidden; source allowlist not imported in this probe','operational_database_connected':False,'target_revision':'20260922_01'}
spec=importlib.util.spec_from_file_location('legacy', '/app/malaria_dl_local_project/scripts/init_db.py');legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
try:
 with engine.connect() as c:
  with c.begin():
   identity=list(c.execute(text('SELECT current_database(),session_user,(SELECT system_identifier::text FROM pg_control_system())')).one())
   assert identity==[cfg['database'],cfg['user'],cfg['system_identifier']] and identity[2]!='7668020338728398886'
   assert c.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='public'")).scalar_one()==0
   legacy.ensure_migration_ledger(c)
   for p in legacy.SQL_FILES:
    if p.name=='004_seed.sql':continue
    report['stage']=p.name
    # No parameter binding: preserve literal PL/pgSQL percent characters.
    with c.connection.driver_connection.cursor() as cursor:cursor.execute(p.read_text())
    legacy.record_migration(c,p,legacy.migration_checksum(p),len(legacy.split_sql_statements(p.read_text())))
    report['legacy_files'].append({'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
   report['stage']='alembic upgrade 20260922_01'
   config=Config('/app/alembic.ini');config.set_main_option('script_location','/app/alembic');config.attributes['connection']=c
   command.upgrade(config,'20260922_01')
   report['revision']=c.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
   report['tables']=c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")).scalars().all()
 report['result']='PASS_SCHEMA_ONLY'
except Exception as e:
 report['result']='STOP_SCHEMA_BUILD_FAILED';report['error_type']=type(e).__name__
 original=getattr(e,'orig',e);report['sqlstate']=getattr(original,'sqlstate',None)
 report['error']=str(original)
with engine.connect() as c:
 with c.begin():
  report['tables_after']=c.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='public'")).scalar_one()
print(json.dumps(report,indent=2,default=str))
raise SystemExit(0 if report['result']=='PASS_SCHEMA_ONLY' else 2)
