import json,hashlib,re,datetime
from pathlib import Path
from sqlalchemy import text
from src.malaria_dl.execution.controlled import ControlledRepository
from src.malaria_dl.execution.global_gate import process_table,process_absent,verify_retained_processes,host_identity
r=ControlledRepository();run='79f39931-ac71-4bc1-a317-149a975d1f74';o={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'host':host_identity()}
with r.transaction(readonly=True) as c:
 s=dict(c.execute(text('SELECT * FROM train_execution_sessions WHERE run_id=CAST(:id AS uuid)'),{'id':run}).mappings().one());o['run']=dict(c.execute(text('SELECT id,status,campaign_id,dataset_version_id FROM runs WHERE id=CAST(:id AS uuid)'),{'id':run}).mappings().one());o['attempt']=dict(c.execute(text('SELECT * FROM campaign_attempts WHERE training_run_id=CAST(:id AS uuid)'),{'id':run}).mappings().one());o['epochs']=[dict(x) for x in c.execute(text("SELECT phase,record_key,payload,created_at FROM train_execution_records WHERE run_id=CAST(:id AS uuid) AND kind='epoch' ORDER BY created_at"),{'id':run}).mappings()];o['artifacts']=[]
 for x in c.execute(text("SELECT payload FROM train_execution_records WHERE run_id=CAST(:id AS uuid) AND kind='artifact' ORDER BY created_at"),{'id':run}).scalars():
  p=Path(x['path']);exists=p.is_file();h=hashlib.sha256(p.read_bytes()).hexdigest() if exists else None;o['artifacts'].append({'reference':x,'exists':exists,'size':p.stat().st_size if exists else None,'hash_matches':h==x['sha256']})
 gate=dict(c.execute(text('SELECT * FROM experiment_execution_gate')).mappings().one());verify_retained_processes(gate['process_evidence']);o['retained_processes_absent']=True;o['advisory_owners']=c.execute(text("SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND classid=120994 AND objid=1 AND objsubid=2 AND granted")).scalar_one()
log=Path('/app/var/artifacts/controlled_7d4cacb1-3d85-53f6-9828-8a7b1e0164c5.log');data=log.read_bytes();txt=data.decode(errors='replace');o['log']={'path':str(log),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'epoch_markers':re.findall(r'Epoch \d+/\d+',txt),'last_batch_markers':re.findall(r'\b\d+/\d+\b',txt)[-8:],'cli_exit':re.findall(r'CONTROLLED_CLI_EXIT=(-?\d+)',txt),'resource_exhausted_occurrences':txt.count('ResourceExhaustedError')}
p=Path('/sys/fs/cgroup/memory.peak');o['cgroup_peak_bytes']=p.read_text().strip() if p.exists() else None;o['peak_scope']='container lifetime, not isolated to this attempt'
print(json.dumps(o,indent=2,default=str))
