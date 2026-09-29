import json
from pathlib import Path
from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL
from common import fingerprint,require
p=Path(__file__).parent;c=json.loads((p/'target.json').read_text())
require(c['container'].startswith('capstone-reset3-') and c['database']=='reset3_candidate','ISOLATED_REQUIRED')
e=create_engine(URL.create('postgresql+psycopg',username=c['user'],password=c['password'],host=c['container'],database=c['database']))
with e.connect().execution_options(postgresql_readonly=True) as db,db.begin():
 require(db.execute(text('SELECT system_identifier::text FROM pg_control_system()')).scalar_one()==c['system_identifier']!='7668020338728398886','IDENTITY')
 print(json.dumps(fingerprint(db,'public')))
