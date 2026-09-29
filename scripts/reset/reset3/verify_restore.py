"""Verify the complete new archive restore against the read-only origin snapshot."""
import json,re
from pathlib import Path
from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL
from common import fingerprint,catalog,require,sha
p=Path(__file__).parent;c=json.loads((p/'target.json').read_text())
require(c['container'].startswith('capstone-reset3-') and c.get('restore_database','reset3_full_restore').startswith('reset3_'),'ISOLATED_TARGET_REQUIRED')
e=create_engine(URL.create('postgresql+psycopg',username=c['user'],password=c['password'],host=c['container'],database=c.get('restore_database','reset3_full_restore')))
with e.connect().execution_options(postgresql_readonly=True,isolation_level='REPEATABLE READ') as db,db.begin():
 require(db.execute(text('SELECT system_identifier::text FROM pg_control_system()')).scalar_one()==c['system_identifier']!='7668020338728398886','IDENTITY')
 schemas=db.execute(text("SELECT nspname FROM pg_namespace WHERE nspname='public' OR nspname LIKE 'capstone_test_%' ORDER BY nspname")).scalars().all()
 snapshot={'schemas':{s:fingerprint(db,s) for s in schemas},'catalog':catalog(db,'public')}
 expected=json.loads((p/'source_before.json').read_text())
 require(snapshot['schemas']==expected['schemas'],'RESTORE_DATA_MISMATCH')
 # Object OIDs change on restore. Compare full definitions/owners/ACL, not OIDs.
 def norm(cat):
  result={}
  for k,rows in cat.items():
   cleaned=[]
   for row in rows:
    row={a:b for a,b in row.items() if a!='oid'}
    if k=='triggers' and row['tgisinternal']:
     row['definition']=row['definition'].replace(row['tgname'],'RI_INTERNAL_GENERATED_NAME')
     row['tgname']='RI_INTERNAL_GENERATED_NAME'
    if k=='constraints':
     # pg_restore reparses varchar[]::text[] as per-element text casts.
     # Restrict normalization to literal varchar/text arrays only.
     d=row['definition']
     d=re.sub(r"\(ARRAY\[((?:'[^']*'::character varying)(?:, '[^']*'::character varying)*)\]\)::text\[\]",r"ARRAY[\1]",d)
     d=re.sub(r"\('([^']*)'::character varying\)::text",r"'\1'::character varying",d)
     row['definition']=d
    cleaned.append(json.dumps(row,sort_keys=True))
   result[k]=sorted(cleaned)
  return result
 (p/'restore_catalog.json').write_text(json.dumps(snapshot['catalog'],default=str))
 require(norm(snapshot['catalog'])==norm(expected['catalog']),'RESTORE_CATALOG_MISMATCH')
 print(json.dumps({'result':'PASS_FULL_BACKUP_RESTORE','schemas':snapshot['schemas'],'public_catalog_equivalent':True,'normalizations':['generated internal RI trigger names/OIDs','literal varchar array to text array casts'],'source_snapshot_sha256':sha(expected),'revision':db.execute(text('SELECT version_num FROM alembic_version')).scalar_one()}))
