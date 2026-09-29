"""Read-only structural evidence from the attested isolated D copy only."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import psycopg
from psycopg.rows import dict_row
from alembic_v2.safety import inspect_isolation
E=ROOT/'docs/audits/e10_10_5d1_evidence';OLD=ROOT/'docs/audits/e10_10_5d_evidence'
t=json.loads((OLD/'target.json').read_text());inspect_isolation(t)
p=Path(json.loads((OLD/'private_location.json').read_text())['directory']);password=(p/'container.env').read_text().splitlines()[0].split('=',1)[1]
queries={
 'sequence':"SELECT s.*,pg_get_userbyid(c.relowner) owner,c.relacl FROM pg_sequence s JOIN pg_class c ON c.oid=s.seqrelid WHERE c.oid='public.experiment_execution_events_id_seq'::regclass",
 'sequence_dependencies':"SELECT classid::regclass::text class,objid, objsubid,refclassid::regclass::text refclass,refobjid,refobjsubid,deptype,pg_describe_object(classid,objid,objsubid) object,pg_describe_object(refclassid,refobjid,refobjsubid) referenced FROM pg_depend WHERE objid='public.experiment_execution_events_id_seq'::regclass OR (refobjid='public.experiment_execution_events'::regclass AND refobjsubid=1) ORDER BY classid,objid,objsubid,refobjid",
 'column':"SELECT a.attname,a.attnum,a.attidentity,a.attgenerated,a.attnotnull,format_type(a.atttypid,a.atttypmod) type,a.attacl,d.adbin::text,pg_get_expr(d.adbin,d.adrelid) expression FROM pg_attribute a LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum WHERE a.attrelid='public.experiment_execution_events'::regclass AND a.attname='id'",
 'state':"SELECT last_value,is_called FROM public.experiment_execution_events_id_seq",
 'functions':"SELECT p.oid,n.nspname,p.proname,pg_get_function_result(p.oid) result,p.prosrc,p.probin,l.lanname,p.provolatile,p.proparallel,p.proisstrict,p.prosecdef,p.proacl,pg_get_userbyid(p.proowner) owner,pg_get_functiondef(p.oid) definition FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.oid=p.prolang WHERE p.proname='gen_random_uuid' ORDER BY n.nspname",
 'defaults':"SELECT c.relname table_name,a.attname column_name,format_type(a.atttypid,a.atttypmod) type,d.oid default_oid,d.adbin::text expression_tree,pg_get_expr(d.adbin,d.adrelid) expression,coalesce((SELECT json_agg(json_build_object('deptype',x.deptype,'object',pg_describe_object(x.refclassid,x.refobjid,x.refobjsubid))) FROM pg_depend x WHERE x.classid='pg_attrdef'::regclass AND x.objid=d.oid),'[]'::json) dependencies FROM pg_attrdef d JOIN pg_class c ON c.oid=d.adrelid JOIN pg_attribute a ON a.attrelid=d.adrelid AND a.attnum=d.adnum WHERE c.relnamespace='public'::regnamespace ORDER BY c.relname,a.attnum"
}
with psycopg.connect(host='127.0.0.1',port=t['host_port'],dbname=t['database'],user=t['migration_role'],password=password,row_factory=dict_row) as c:
 c.execute('SET TRANSACTION READ ONLY')
 ident=c.execute("SELECT system_identifier::text id,current_setting('server_version_num') version FROM pg_control_system()").fetchone();assert ident=={'id':t['postgres_system_identifier'],'version':'170009'}
 result={'identity':ident,'queries':queries,'observations':{k:c.execute(v).fetchall() for k,v in queries.items()}}
 c.execute('SET LOCAL search_path=public,pg_catalog');result['public_first_defaults']=c.execute(queries['defaults']).fetchall()
 c.execute('SET LOCAL search_path=pg_catalog,public');result['catalog_first_defaults']=c.execute(queries['defaults']).fetchall()
 c.rollback()
(E/'diagnostic.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
print(json.dumps({k:result['observations'][k] for k in ['column','functions']},default=str))
