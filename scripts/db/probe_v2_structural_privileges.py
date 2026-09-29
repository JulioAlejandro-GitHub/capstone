import json,sys
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
import psycopg
from psycopg.rows import dict_row
E=ROOT/'docs/audits/e10_10_5d1_evidence';O=ROOT/'docs/audits/e10_10_5d_evidence'
t=json.loads((O/'target.json').read_text());p=Path(json.loads((O/'private_location.json').read_text())['directory']);password=(p/'container.env').read_text().splitlines()[0].split('=',1)[1]
a=json.loads((E/'auxiliary_identities.json').read_text());out={}
q="""SELECT c.relname,pg_get_userbyid(c.relowner) owner,c.relacl::text,has_sequence_privilege('capstone_v2_migrator','public.experiment_execution_events_id_seq','USAGE') migrator_usage,has_sequence_privilege('capstone_v2_runtime','public.experiment_execution_events_id_seq','USAGE') runtime_usage,has_table_privilege('capstone_v2_runtime','public.experiment_execution_events','INSERT') runtime_insert FROM pg_class c WHERE c.oid IN ('public.experiment_execution_events'::regclass,'public.experiment_execution_events_id_seq'::regclass) ORDER BY c.relname"""
for k,v in a.items():
 with psycopg.connect(host='127.0.0.1',port=t['host_port'],dbname=v['database'],user='postgres',password=password,row_factory=dict_row) as c:
  c.execute('SET TRANSACTION READ ONLY');ident=c.execute("SELECT system_identifier::text id FROM pg_control_system()").fetchone();assert ident['id']==t['postgres_system_identifier'];out[k]=c.execute(q).fetchall();c.rollback()
(E/'ownership_privileges.json').write_text(json.dumps({'query':q,'observations':out},indent=2)+'\n')
print('ownership and effective privileges recorded')
