"""Read-only functional contracts against the isolated, populated E10 candidate."""
import json,uuid
from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL
from common import require,orphan_checks
from src.malaria_dl.execution.controlled import ControlledRepository
from src.malaria_dl.local_execution.backend import LocalBackend
from src.malaria_dl.execution.schema import require_e10_schema
from src.malaria_dl.results.service import ResultService
from src.malaria_dl.persistence.result_repository import PostgresResultRepository
from src.malaria_dl.models.registry import enabled_models
from src.malaria_dl.models.configuration import resolve_config
from src.malaria_dl.governance.services.stage2_publication_service import Stage2PublicationService
from src.malaria_dl.governance.services.deployment_service import ModelDeploymentService
from src.model_governance.errors import GovernanceConflictError
HERE=Path(__file__).parent;cfg=json.loads((HERE/'target.json').read_text())
require(cfg['container'].startswith('capstone-reset3-') and cfg['database']=='reset3_candidate','TARGET_REQUIRED')
engine=create_engine(URL.create('postgresql+psycopg',username=cfg['user'],password=cfg['password'],host=cfg['container'],database=cfg['database']))
@contextmanager
def scope(readonly=False):
 with engine.connect().execution_options(postgresql_readonly=True) as c:
  with c.begin():
   require(tuple(c.execute(text('SELECT current_database(),(SELECT system_identifier::text FROM pg_control_system())')).one())==(cfg['database'],cfg['system_identifier']),'IDENTITY_MISMATCH')
   yield c
class BeforeClaim(Exception):pass
class Repo(ControlledRepository):
 def get(self,*args):raise BeforeClaim()
repo=Repo(scope);repo.preflight_e10_schema();report={'docker_op1':'E10_SCHEMA_READY'}
try:LocalBackend(repo,{}).prepare({'campaign_id':'unused','dataset_id':'unused'})
except BeforeClaim:report['local_op1']='E10_SCHEMA_READY; stopped before get/claim'
else:raise RuntimeError('LOCAL_NOT_STOPPED_BEFORE_CLAIM')
service=ResultService(PostgresResultRepository(execution_token=uuid.uuid4(),engine_factory=lambda:engine));report['ResultService']='instantiated without publishing events or reserving runs'
report['registry']={model:bool(resolve_config(model)) for model in enabled_models()}
with scope() as c:
 report['capabilities']=require_e10_schema(c)
 report['gate_free']=c.execute(text("SELECT owner IS NULL AND db_pid IS NULL AND blocked_reason IS NULL AND process_evidence='{}'::jsonb FROM experiment_execution_gate")).scalar_one();require(report['gate_free'],'GATE_NOT_FREE')
 report['disabled_triggers']=c.execute(text("SELECT count(*) FROM pg_trigger t JOIN pg_class r ON r.oid=t.tgrelid JOIN pg_namespace n ON n.oid=r.relnamespace WHERE n.nspname='public' AND t.tgenabled<>'O'")).scalar_one();require(report['disabled_triggers']==0,'TRIGGERS_DISABLED')
 report['unvalidated_constraints']=c.execute(text("SELECT count(*) FROM pg_constraint WHERE connamespace='public'::regnamespace AND NOT convalidated")).scalar_one();require(report['unvalidated_constraints']==0,'INVALID_CONSTRAINTS')
 m=json.loads((HERE/'original_manifest.json').read_text());report['foreign_keys']=orphan_checks(c,m,'public')
 @contextmanager
 def shared():yield c
 require(Stage2PublicationService(shared).models()==[],'PUBLICATIONS_PRESENT')
 try:ModelDeploymentService(shared).resolve_alias('malaria-stage2-classifier','stage2','default')
 except GovernanceConflictError:report['availability']='SIN_MODELO_PRODUCTIVO'
 else:raise RuntimeError('DEPLOYMENT_PRESENT')
 report['history']={t:c.execute(text('SELECT count(*) FROM "'+t+'"')).scalar_one() for t in ('runs','experimental_campaigns','experiments','train_execution_sessions','local_execution_jobs','train_execution_records','model_versions','microscopy_analysis_runs','cell_detection_runs','cell_classification_runs','predictions','explainability_results','stage2_model_publications','deployed_model_versions')}
 require(not any(report['history'].values()),'HISTORY_PRESENT')
report['result']='PASS_FUNCTIONAL_CONTRACTS_LOGIN_PENDING'
print(json.dumps(report,indent=2,default=str))
