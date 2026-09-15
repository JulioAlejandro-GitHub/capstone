import json, datetime
from pathlib import Path
from sqlalchemy import text
from src.malaria_dl.execution.global_gate import process_table,managed_execution,resources
from src.malaria_dl.execution.repository import ExecutionRepository
out={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'managed_processes':[],'resources':resources()}
for pid,row in process_table().items():
    try: args=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
    except (FileNotFoundError,PermissionError):continue
    if managed_execution(args):out['managed_processes'].append({'pid':pid,**row})
with ExecutionRepository().transaction(readonly=True) as c:
    for key,query in {
      'revision':'SELECT version_num FROM alembic_version',
      'active_train':"SELECT count(*) FROM train_execution_sessions WHERE state IN ('active','completed')",
      'active_assessment':"SELECT count(*) FROM assessment_attempts WHERE state='active'",
      'gate_installed':"SELECT to_regclass('public.experiment_execution_gate') IS NOT NULL",
      'synthetic_schemas':"SELECT count(*) FROM pg_namespace WHERE nspname LIKE 'capstone_test_e4_%'",
      'wrong_dataset':"SELECT count(*) FROM runs r JOIN campaign_attempts a ON a.training_run_id=r.id JOIN campaign_members m ON m.id=a.member_id WHERE m.campaign_id='3acf89b7-dc42-4b7a-8e2a-ca6ea024c344' AND r.dataset_version_id IS DISTINCT FROM 'd8c0cab5-09dd-597f-9de7-7ca01aee2ec2'::uuid"
    }.items():out[key]=c.execute(text(query)).scalar_one()
print(json.dumps(out,indent=2,default=str))
