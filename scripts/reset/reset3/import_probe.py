"""Import exact scientific/access allowlist into the disposable candidate only.

Operational connection is repeatable-read READ ONLY. PostgreSQL COPY preserves
original values; all destination constraints/triggers remain enabled.
"""
import hashlib,json
from pathlib import Path
from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL
from src.malaria_dl.persistence.database import get_engine
from common import require,qi,sha
HERE=Path(__file__).parent;cfg=json.loads((HERE/'target.json').read_text())
require(cfg['container'].startswith('capstone-reset3-') and cfg['database']=='reset3_candidate','ISOLATED_TARGET_REQUIRED')
engine=create_engine(URL.create('postgresql+psycopg',username=cfg['user'],password=cfg['password'],host=cfg['container'],database=cfg['database']))
V='d8c0cab5-09dd-597f-9de7-7ca01aee2ec2';M='e15dc166-1c4b-558e-b77b-727b1783430c'
root='/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/data/malaria_dataset_versions/'+V
assign=f"SELECT source_record_id FROM dataset_split_assignments WHERE dataset_version_id='{V}'"
ident=f"SELECT clinical_identity_id FROM dataset_source_records WHERE id IN ({assign}) UNION SELECT clinical_identity_id FROM identity_evidence WHERE source_record_id IN ({assign}) UNION SELECT clinical_identity_id FROM dataset_split_assignments WHERE dataset_version_id='{V}'"
# Entire protected families: no row-level filtering or authentication rewriting.
pred={t:'TRUE' for t in (
 'roles','users','user_roles','datasets','dataset_versions',
 'dataset_version_sources','clinical_identities','dataset_source_records',
 'identity_evidence','dataset_materializations','dataset_split_assignments',
 'dataset_split_images','dataset_split_statistics','dataset_split_validation_checks',
 'dataset_materialization_activations','dataset_splits')}
# Architecture definitions only; trained versions and deployments stay empty.
pred['models']="name IN ('custom_cnn','vgg16','densenet121')"

report={'target':{k:v for k,v in cfg.items() if k!='password'},'source_access':'READ ONLY','selections':{},'no_history_imported':None,'result':'IN_PROGRESS'}
manifest={'official_dataset':V,'materialization':M,'selections':{}}
def fp(c,t,where='TRUE'):
 rows=c.execute(text(f'SELECT to_jsonb(t)::text FROM {qi(t)} t WHERE {where} ORDER BY to_jsonb(t)::text')).scalars().all()
 return {'count':len(rows),'sha256':sha(rows)}
try:
 with get_engine().connect().execution_options(postgresql_readonly=True,isolation_level='REPEATABLE READ') as src,engine.connect() as dst:
  with src.begin(),dst.begin():
   require(tuple(src.execute(text("SELECT current_database(),current_schema(),(SELECT system_identifier::text FROM pg_control_system()),current_setting('transaction_read_only')")).one())==('malaria_experiments','public','7668020338728398886','on'),'SOURCE_IDENTITY')
   require(tuple(dst.execute(text('SELECT current_database(),session_user,(SELECT system_identifier::text FROM pg_control_system())')).one())==(cfg['database'],cfg['user'],cfg['system_identifier']),'TARGET_IDENTITY')
   require(dst.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='20260922_01','TARGET_REVISION')
   for t,where in pred.items():
    report['stage']=t
    expected=fp(src,t,where);report['selections'][t]={'predicate':where,'source':expected}
    cols=src.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=:t ORDER BY ordinal_position"),{'t':t}).scalars().all()
    keys=src.execute(text("SELECT a.attname FROM pg_index i JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=ANY(i.indkey) WHERE i.indrelid=CAST(:t AS regclass) AND i.indisprimary ORDER BY a.attnum"),{'t':t}).scalars().all()
    require(keys,'PK_REQUIRED:'+t)
    keypairs=','.join("'"+k+"',t."+qi(k) for k in keys)
    allow=src.execute(text(f"SELECT jsonb_build_object({keypairs}) AS pk, encode(sha256(convert_to(to_jsonb(t)::text,'UTF8')),'hex') AS preimage_sha256 FROM {qi(t)} t WHERE {where} ORDER BY to_jsonb(t)::text")).mappings().all()
    manifest['selections'][t]={'predicate':where,'source':expected,'rows':[dict(v) for v in allow]}
    if t=='roles':
     require(expected['count']==5,'ROLES_CHANGED')
     for row in src.execute(text('SELECT id,name,created_at FROM roles WHERE '+where)).mappings():
      require(dst.execute(text('UPDATE roles SET id=:id,created_at=:created_at WHERE name=:name'),dict(row)).rowcount==1,'ROLE_MISSING')
    else:
     require(dst.execute(text('SELECT count(*) FROM '+qi(t))).scalar_one()==0,'TARGET_NOT_EMPTY:'+t)
     selectcols=[("'DRAFT'::text" if t=='dataset_versions' and col=='status' else qi(col)) for col in cols]
     with src.connection.driver_connection.cursor() as reader,dst.connection.driver_connection.cursor() as writer:
      with reader.copy(f"COPY (SELECT {','.join(selectcols)} FROM {qi(t)} WHERE {where}) TO STDOUT") as stream,writer.copy(f"COPY {qi(t)} ({','.join(map(qi,cols))}) FROM STDIN") as sink:
       for block in stream:sink.write(block)
    if t != 'dataset_versions':require(fp(dst,t)==expected,'IMPORT_CONTENT_MISMATCH:'+t)
   original_status=src.execute(text('SELECT status FROM dataset_versions WHERE id=:v'),{'v':V}).scalar_one();require(original_status=='FROZEN','EXPECTED_FROZEN_SOURCE')
   for state in ('GENERATED','VALIDATED','FROZEN'):dst.execute(text('UPDATE dataset_versions SET status=:s WHERE id=:v'),{'s':state,'v':V})
   require(fp(dst,'dataset_versions')==report['selections']['dataset_versions']['source'],'VERSION_CHANGED')
   require(fp(dst,'users')==fp(src,'users'),'USERS_NOT_PRESERVED')
   report['authentication']={'all_rows_and_columns_equal':True,'password_hashes_preserved':True,'last_login_at_preserved':True}
   assignments=dict(dst.execute(text('SELECT split_name,count(*) FROM dataset_split_assignments GROUP BY split_name')).all())
   images=dict(dst.execute(text('SELECT split_name,count(*) FROM dataset_split_images WHERE dataset_dir=:root GROUP BY split_name'),{'root':root}).all())
   require(assignments==images=={'train':22180,'val':2693,'test':2685},'SPLIT_COUNTS_MISMATCH')
   require(dst.execute(text('SELECT count(*) FROM (SELECT clinical_identity_id FROM dataset_split_assignments GROUP BY clinical_identity_id HAVING count(DISTINCT split_name)>1) t')).scalar_one()==0,'PATIENT_LEAKAGE')
   dst.exec_driver_sql('SET CONSTRAINTS ALL IMMEDIATE')
   tables=dst.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")).scalars().all()
   counts={t:dst.execute(text('SELECT count(*) FROM '+qi(t))).scalar_one() for t in tables}
   allowed=set(pred)|{'alembic_version','schema_migrations','experiment_execution_gate'}
   require(not any(n for t,n in counts.items() if t not in allowed),'UNAPPROVED_DATA_IMPORTED')
   report.update(no_history_imported=True,table_counts=counts,assignments=assignments,split_images=images,patient_leakage=0,result='PASS_ISOLATED_IMPORT',version_sha256=fp(dst,'dataset_versions'),materialization_sha256=fp(dst,'dataset_materializations'))
 (HERE/'import_allowlist.json').write_text(json.dumps(manifest,indent=2,default=str))
except Exception as e:
 report['result']='STOP_IMPORT_FAILED';original=getattr(e,'orig',e);report['error_type']=type(e).__name__;report['sqlstate']=getattr(original,'sqlstate',None);report['error']=getattr(getattr(original,'diag',None),'message_primary',None) or type(original).__name__
print(json.dumps(report,indent=2,default=str))
raise SystemExit(0 if report['result']=='PASS_ISOLATED_IMPORT' else 2)
