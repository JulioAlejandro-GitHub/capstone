"""Recognize legacy E10 using its actual migrations in a disposable legacy schema."""
import json, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'docs/audits/e10_10_5e4_evidence/route_a'
sys.path[:0]=[str(ROOT),str(ROOT/'malaria_dl_local_project'),str(ROOT/'malaria_dl_local_project/tests')]
os.environ['PGV2_EVIDENCE_DIR']=str(E)
os.environ['PGPASSFILE']=json.loads((E/'private_paths.json').read_text())['pgpass']
from verify_v2_route_a import guard
from sqlalchemy import create_engine,text
from src.malaria_dl.execution.schema import require_e10_schema
import test_campaigns_postgres as legacy
from test_result_repository_postgres import apply
from e10_schema_fixture import install_e10

def main():
 t=guard()
 url=f"postgresql+psycopg://capstone_v2_migrator@127.0.0.1:{t['host_port']}/{t['database']}"
 legacy.get_engine=lambda:create_engine(url)
 gen=legacy.isolated.__wrapped__()
 x=next(gen)
 try:
  for name in ('20260912_01_train_execution','20260912_02_assessments','20260914_01_controlled_train','20260914_02_global_execution','20260915_01_local_execution'):
   apply(x.c,name)
  install_e10(x.c)
  x.c.execute(text(f'GRANT USAGE ON SCHEMA {x.schema} TO capstone_v2_runtime'))
  x.c.execute(text(f'GRANT SELECT ON {x.schema}.alembic_version TO capstone_v2_runtime'))
  x.make_visible()
  engine=create_engine(url.replace('capstone_v2_migrator@','capstone_v2_runtime@'))
  try:
   with engine.begin() as c:
    c.execute(text(f'SET LOCAL search_path TO {x.schema},pg_catalog'))
    result=require_e10_schema(c)
    assert result['revision']=='20260922_01'
    result['session_user']=c.execute(text('SELECT session_user')).scalar_one()
    assert result['session_user']=='capstone_v2_runtime'
    result['scope']='actual legacy migrations over disposable synthetic parent tables; not full legacy baseline certification'
    (E/'legacy_revision.json').write_text(json.dumps(result,indent=2)+'\n')
  finally: engine.dispose()
 finally:
  try: next(gen)
  except StopIteration: pass
 print('Legacy revision recognized using actual runtime login')
if __name__=='__main__': main()
