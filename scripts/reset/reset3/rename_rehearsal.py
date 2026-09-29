"""Exercise transactional database renames only on disposable empty clone DBs."""
import json
from pathlib import Path
from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL
from common import require
cfg=json.loads((Path(__file__).parent/'target.json').read_text());require(cfg['container'].startswith('capstone-reset3-'),'CLONE_REQUIRED')
e=create_engine(URL.create('postgresql+psycopg',username=cfg['user'],password=cfg['password'],host=cfg['container'],database='postgres'))
with e.connect().execution_options(isolation_level='AUTOCOMMIT') as c:
 require(c.execute(text('SELECT system_identifier::text FROM pg_control_system()')).scalar_one()==cfg['system_identifier']!='7668020338728398886','CLONE_IDENTITY')
 c.exec_driver_sql('CREATE DATABASE reset3_swap_a');c.exec_driver_sql('CREATE DATABASE reset3_swap_b')
with e.connect() as c:
 def names():return dict(c.execute(text("SELECT datname,oid FROM pg_database WHERE datname LIKE 'reset3_swap_%' ORDER BY datname")).all())
 before=names();c.rollback()
 t=c.begin();c.exec_driver_sql('ALTER DATABASE reset3_swap_a ALLOW_CONNECTIONS false');c.exec_driver_sql('ALTER DATABASE reset3_swap_a RENAME TO reset3_swap_old');c.exec_driver_sql('ALTER DATABASE reset3_swap_b RENAME TO reset3_swap_a');t.rollback()
 require(names()==before,'RENAME_ROLLBACK_FAILED');c.rollback()
 with c.begin():
  c.exec_driver_sql('ALTER DATABASE reset3_swap_a ALLOW_CONNECTIONS false');c.exec_driver_sql('ALTER DATABASE reset3_swap_a RENAME TO reset3_swap_old');c.exec_driver_sql('ALTER DATABASE reset3_swap_b RENAME TO reset3_swap_a')
 actual=names();require(actual=={'reset3_swap_a':before['reset3_swap_b'],'reset3_swap_old':before['reset3_swap_a']},'RENAME_COMMIT_FAILED')
print(json.dumps({'result':'PASS_TRANSACTIONAL_RENAME_REHEARSAL','rollback_exact':True,'commit_oid_mapping_exact':True,'cluster':cfg['system_identifier']}))
with e.connect().execution_options(isolation_level='AUTOCOMMIT') as c:
 c.exec_driver_sql('DROP DATABASE reset3_swap_a');c.exec_driver_sql('DROP DATABASE reset3_swap_old')
