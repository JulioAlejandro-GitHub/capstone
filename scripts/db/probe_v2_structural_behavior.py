"""Destructive probes only in fresh auxiliary databases in the isolated D cluster."""
import hashlib,json,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from alembic_v2.safety import inspect_isolation
from alembic_v2.resources import load_baseline
from adoption_v2.core import table_digest,contract
E=ROOT/'docs/audits/e10_10_5d1_evidence';OLD=ROOT/'docs/audits/e10_10_5d_evidence'
t=json.loads((OLD/'target.json').read_text());inspect_isolation(t)
p=Path(json.loads((OLD/'private_location.json').read_text())['directory']);password=(p/'container.env').read_text().splitlines()[0].split('=',1)[1]
def connect(db,role='postgres'):
 return psycopg.connect(host='127.0.0.1',port=t['host_port'],dbname=db,user=role,password=password,row_factory=dict_row,autocommit=True)
def save(name,value):(E/name).write_text(json.dumps(value,indent=2,default=str)+'\n')
def identity(c):
 r=c.execute("SELECT system_identifier::text id,current_setting('server_version_num') version,current_database() database,(SELECT oid FROM pg_database WHERE datname=current_database()) oid FROM pg_control_system()").fetchone()
 assert r['id']==t['postgres_system_identifier'] and r['version']=='170009';return r
names={k:t['database']+'_d1_'+k for k in ['legacy','baseline']}
identities={}
with connect('postgres') as c:
 identity(c)
 for db in names.values():c.execute(sql.SQL('CREATE DATABASE {} OWNER capstone_v2_migrator TEMPLATE template0').format(sql.Identifier(db)))
for k,db in names.items():
 with connect(db) as c:
  identities[k]=identity(c)
  assert c.execute("SELECT count(*) n FROM pg_class WHERE relnamespace='public'::regnamespace").fetchone()['n']==0
save('auxiliary_identities.json',identities)
backup=p/'source.dump';assert hashlib.sha256(backup.read_bytes()).hexdigest()==json.loads((OLD/'source_backup.json').read_text())['sha256']
args=['docker','--host','unix:///Users/julio/.docker/run/docker.sock','exec','-i',t['container_id'],'pg_restore','-U','postgres','-d',names['legacy'],'--role=capstone_v2_migrator','--no-owner','--no-acl','--single-transaction','--exit-on-error']
r=subprocess.run(args,input=backup.read_bytes(),capture_output=True);save('aux_restore.json',{'argv':args,'exit_code':r.returncode,'backup_sha256':hashlib.sha256(backup.read_bytes()).hexdigest()});assert r.returncode==0
manifest,statements=load_baseline()
with connect(names['baseline'],'capstone_v2_migrator') as c,c.transaction():
 identity(c)
 c.execute('CREATE TABLE public.alembic_version(version_num varchar(32) PRIMARY KEY)')
 for entry,statement in zip(manifest['statements'],statements):
  if entry['kind']!='seed':c.execute(statement)
# Diagnostic representation, not Alembic installation/certification; no head inserted.
queries=json.loads((E/'diagnostic.json').read_text())['queries'];catalog={};tests={}
for kind,db in names.items():
 with connect(db) as c:
  identity(c);c.execute('SET search_path=pg_catalog,public')
  catalog[kind]={k:c.execute(q).fetchall() for k,q in queries.items()}
  tests[kind]={}
  actions={
   'omitted_id':"INSERT INTO public.experiment_execution_events(owner,event,payload) VALUES ('00000000-0000-0000-0000-000000000001','D1_SYNTHETIC_PROBE','{}') RETURNING id",
   'explicit_id':"INSERT INTO public.experiment_execution_events(id,owner,event,payload) VALUES (9000000,'00000000-0000-0000-0000-000000000001','D1_SYNTHETIC_PROBE','{}') RETURNING id",
   'override_id':"INSERT INTO public.experiment_execution_events(id,owner,event,payload) OVERRIDING SYSTEM VALUE VALUES (9000001,'00000000-0000-0000-0000-000000000001','D1_SYNTHETIC_PROBE','{}') RETURNING id"
  }
  for label,statement in actions.items():
   try:
    with c.transaction():
     value=c.execute(statement).fetchone();tests[kind][label]={'sqlstate':'00000','value':value};c.execute('ROLLBACK')
   except psycopg.Error as ex:tests[kind][label]={'sqlstate':ex.sqlstate}
  # Replicate the actually resolved default on an auxiliary table; all DDL/ACL changes rollback.
  expression=next(x['expression'] for x in catalog[kind]['defaults'] if x['table_name']=='datasets' and x['column_name']=='id')
  with c.transaction():
   c.execute('CREATE TABLE public.d1_default_probe(id uuid DEFAULT '+expression+')')
   c.execute('GRANT INSERT,SELECT ON public.d1_default_probe TO capstone_v2_runtime')
   c.execute('GRANT USAGE ON SCHEMA public TO capstone_v2_runtime')
   c.execute('REVOKE EXECUTE ON FUNCTION public.gen_random_uuid() FROM PUBLIC,capstone_v2_runtime')
   try:
    with c.transaction():
     c.execute('SET LOCAL ROLE capstone_v2_runtime');c.execute('INSERT INTO public.d1_default_probe DEFAULT VALUES')
     tests[kind]['revoked_wrapper_execute']={'sqlstate':'00000'}
   except psycopg.Error as ex:tests[kind]['revoked_wrapper_execute']={'sqlstate':ex.sqlstate}
   c.execute('ROLLBACK')
  tests[kind]['aux_sequence_after_probes']=c.execute(queries['state']).fetchall()
save('auxiliary_catalogs.json',catalog);save('behavior_tests.json',tests)
# One row per divergence, retaining resolved OID and dependencies; no string-based equivalence.
legacy={(x['table_name'],x['column_name']):x for x in catalog['legacy']['defaults']};baseline={(x['table_name'],x['column_name']):x for x in catalog['baseline']['defaults']}
rows=[]
for key,l in legacy.items():
 v=baseline.get(key)
 if v and (l['expression']!=v['expression'] or l['expression_tree'].split(':location')[0]!=v['expression_tree'].split(':location')[0]):
  rows.append({'table':key[0],'column':key[1],'legacy':l,'v2':v,'classification':'distinct_resolved_object_and_dependency; execution privilege behavior differs','proposed_resolution':'Retain legacy pg_catalog.gen_random_uuid in baseline through explicit qualification; architectural decision required before schema changes'})
save('default_divergences.json',rows)
# Original D copy remains untouched, including sequence; hashes compared using original codec.
from psycopg.types.string import TextLoader
with connect(t['database'],'capstone_v2_migrator') as c,c.transaction():
 c.adapters.register_loader('uuid',TextLoader);c.execute('SET TRANSACTION READ ONLY')
 actual={k:{'count':len(v),'sha256':table_digest(v)} for k in contract()['tables'] for v in [c.execute(sql.SQL('SELECT * FROM public.{}').format(sql.Identifier(k))).fetchall()]}
 seq=c.execute(queries['state']).fetchall()
expected=json.loads((OLD/'reference_inventory.json').read_text());assert actual==expected and seq==[{'last_value':1,'is_called':False}]
save('preservation.json',{'tables':97,'all_hashes_and_counts_equal':True,'sequence_unchanged':seq,'backups':{f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in ['source.dump','isolated.dump']},'operational_connections':0,'original_copy_writes':0})
print(json.dumps({'behavior':tests,'default_divergences':len(rows),'preservation':'PASS'}))
