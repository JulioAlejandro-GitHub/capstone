import json,hashlib,datetime,urllib.request,urllib.error
from pathlib import Path
from sqlalchemy import text
from alembic.config import Config
from alembic.script import ScriptDirectory
from src.malaria_dl.execution.repository import ExecutionRepository
from src.malaria_dl.execution.global_gate import status,process_table,managed_execution
from src.malaria_dl.campaigns.service import planning_environment
repo=ExecutionRepository(); out={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'environment':planning_environment()}
with repo.transaction(readonly=True) as c:
 rev=c.execute(text('SELECT version_num FROM public.alembic_version')).scalar_one();out['revision']=rev
 cfg=Config('/app/alembic.ini');cfg.set_main_option('script_location','/app/alembic');script=ScriptDirectory.from_config(cfg);out['head']=script.get_current_head();out['ancestry']=[r.revision for r in script.walk_revisions(base='base',head=rev)]
 out['legacy_integrity']={}
 for table in ('runs','run_lineage','model_versions','stage2_model_publications','deployed_model_versions','campaign_attempts'):
  out['legacy_integrity'][table]=dict(c.execute(text(f"SELECT count(*) AS count, md5(coalesce(string_agg((to_jsonb(r)-'campaign_id')::text,'' ORDER BY (to_jsonb(r)-'campaign_id')::text),'')) AS content_hash FROM public.{table} r")).mappings().one())
 out['tables']=list(c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND (tablename LIKE 'assessment_%' OR tablename LIKE '%execution%' OR tablename IN ('campaign_technical_revisions','campaign_controlled_requests')) ORDER BY tablename")).scalars())
 out['triggers']=[dict(r) for r in c.execute(text("SELECT c.relname,t.tgname,t.tgenabled FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND NOT t.tgisinternal AND (t.tgname LIKE 'assessment_%' OR t.tgname LIKE 'global_%' OR t.tgname IN ('train_execution_revision_immutable','train_record_guard','technical_revision_guard','controlled_binding_guard','train_revision_binding_guard')) ORDER BY t.tgname")).mappings()]
 out['indexes']=[dict(r) for r in c.execute(text("SELECT c.relname,i.indisvalid,i.indisunique FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid WHERE c.relname IN ('uq_global_train_active','uq_global_assessment_active')")).mappings()]
 out['campaign_column']=[dict(r) for r in c.execute(text("SELECT is_nullable FROM information_schema.columns WHERE table_schema='public' AND table_name='runs' AND column_name='campaign_id'")).mappings()]
 if out['campaign_column']:
  out['campaign_references']=dict(c.execute(text("SELECT count(*) FILTER(WHERE r.campaign_id IS NULL) AS null_campaigns,count(*) FILTER(WHERE r.campaign_id IS NOT NULL AND c.id IS NULL) AS orphans FROM runs r LEFT JOIN experimental_campaigns c ON c.id=r.campaign_id")).mappings().one())
 out['global_status']=status(repo)
try:r=urllib.request.urlopen('http://localhost:8000/ready')
except urllib.error.HTTPError as e:r=e
out['ready']={'http':r.status,'body':json.loads(r.read())}
print(json.dumps(out,indent=2,default=str))
