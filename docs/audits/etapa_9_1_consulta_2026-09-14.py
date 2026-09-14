import json,os,socket,shutil,datetime,urllib.request,time
from pathlib import Path
from contextlib import contextmanager
from collections import Counter
from sqlalchemy import text
from src.malaria_dl.data.governed_dataset import dataset_read_connection
from src.malaria_dl.execution.repository import ExecutionRepository
from src.malaria_dl.campaigns.service import planning_environment
from src.malaria_dl.campaigns.contracts import digest,member_configuration
from src.malaria_dl.execution.artifacts import verify_session

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def rows(c,q,**p):return [dict(r) for r in c.execute(text(q),p).mappings()]
def publication(c):return {'publications':rows(c,"SELECT p.id,p.datasource,p.scope,p.training_run_id,p.evaluation_run_id,p.model_version_id,p.checkpoint_artifact_id,p.status,p.is_active FROM stage2_model_publications p WHERE p.is_active"),'deployments':rows(c,"SELECT d.id,d.model_version_id,d.status,d.environment,d.alias,m.training_run_id,m.checkpoint_artifact_id FROM deployed_model_versions d JOIN model_versions m ON m.id=d.model_version_id WHERE d.status='active'")}
out={'kind':'E9.1 audit inventory, not scientific results fallback','started_utc':now(),'timezone':'UTC; America/Santiago rendering in report','hostname':socket.gethostname(),'git_available':bool(shutil.which('git'))}
with dataset_read_connection() as c:
 @contextmanager
 def scope(readonly=False):
  assert readonly
  yield c
 repo=ExecutionRepository(scope)
 out['snapshot_utc']=str(c.execute(text('SELECT transaction_timestamp()')).scalar_one())
 out['database']=rows(c,'SELECT current_database() database,current_schema() schema')
 out['revision']=rows(c,'SELECT version_num FROM alembic_version')
 out['publication_initial']=publication(c)
 out['campaigns']=[]
 for cid in ['3acf89b7-dc42-4b7a-8e2a-ca6ea024c344','ec442763-7eea-499d-a94f-9a3ddfb7c0f0']:
  row=repo.get(cid); members=[]
  for m in row['members']:
   cfg=row['contract']['matrix']['configurations'][m['configuration_hash']]['configuration']
   entry={'planned_id':m['id'],'position':m['position'],'architecture':cfg['model_id'],'condition':'original','seed':m['seed'],'configuration_hash':m['configuration_hash'],'persisted_state':m['state'],'attempts':[],'proposed_action':'wait; no new execution in E9.1'}
   for a in row['attempts']:
    if a['member_id']!=m['id']:continue
    ai={'attempt':a,'session':None}
    if a['training_run_id']:
     s=repo.session(a['training_run_id']);records=repo.records(s['run_id'])
     ai['session']={k:s[k] for k in ['run_id','attempt_id','state','owner','host','parent_pid','child_pid','artifact_root','cause','started_at','updated_at','environment','completion','verification']}
     ai['identity_matches']={'configuration':s['configuration']==member_configuration(cfg,m['seed']),'dataset':s['dataset']==row['dataset_snapshot'],'environment':s['environment']==row['environment']}
     ai['records_by_kind']=dict(Counter(r['kind'] for r in records))
     ai['last_record']=rows(c,'SELECT max(created_at) last_record,count(*) count FROM train_execution_records WHERE run_id=CAST(:id AS uuid)',id=str(s['run_id']))
     ai['artifacts']=[r['payload'] for r in records if r['kind']=='artifact']
     ai['versions']=rows(c,'SELECT id,training_run_id,checkpoint_artifact_id FROM model_versions WHERE training_run_id=CAST(:id AS uuid)',id=str(s['run_id']))
     ai['observed_verification']='not completed; no finalized checkpoint claimed'
     if s['state'] in ('completed','verified'):
      try:
       proof=verify_session(repo,s,lambda *_:None)
       ai['observed_verification']='documentary and selected checkpoint bytes verified; model loading/inference not performed'
       ai['documentary_proof']=proof
      except Exception as e:ai['observed_verification']='verification failed: '+type(e).__name__
    entry['attempts'].append(ai)
   members.append(entry)
  out['campaigns'].append({'id':cid,'state':row['state'],'contract_hash':row['contract_hash'],'contract_hash_matches':digest(row['contract'])==row['contract_hash'],'environment':row['environment'],'dataset':row['dataset_snapshot'],'protocol':row['protocol'],'matrix':row['contract']['matrix'],'purpose':row['purpose'],'members':members,'counts':dict(Counter(m['persisted_state'] for m in members)),'attempt_count':len(row['attempts']),'unmatched_attempts':[str(a['id']) for a in row['attempts'] if a['member_id'] not in {m['id'] for m in row['members']}]})
 out['assessments']=rows(c,"SELECT i.training_run_id,i.kind,i.identity->>'split' split,i.identity->>'purpose' purpose,a.id attempt_id,a.state FROM assessment_identities i LEFT JOIN assessment_attempts a ON a.identity_id=i.id")
 out['final_lock_count']=c.execute(text('SELECT count(*) FROM assessment_final_locks')).scalar_one()
 out['legacy_evaluations']=rows(c,"SELECT parameters->>'dataset_version_id' dataset_version_id,count(*) count FROM runs WHERE run_type='evaluation' GROUP BY 1")
 out['snapshot_end_utc']=now()
out['process_observations']=[]
for campaign in out['campaigns']:
 for member in campaign['members']:
  for a in member['attempts']:
   s=a['session']
   if s and s['state']=='active':
    observation={'utc':now(),'run_id':s['run_id'],'same_host':s['host']==socket.gethostname(),'processes':[]}
    for label in ['parent_pid','child_pid']:
     pid=s[label];p=Path('/proc')/str(pid)
     info={'role':label,'pid':pid,'exists':p.exists()}
     if p.exists():
      try:
       cmd=(p/'cmdline').read_bytes().split(b'\0')
       info['expected_role_in_cmdline']=any((b'run_train_all_models.py' if label=='parent_pid' else b'src.malaria_dl.execution.worker') in x for x in cmd)
       info['run_id_in_cmdline']=str(s['run_id']).encode() in cmd
       stat=(p/'stat').read_text().rsplit(')',1)[1].split()
       info.update(state=stat[0],utime=stat[11],stime=stat[12],start_ticks=stat[19])
      except OSError as e:info['error']=type(e).__name__
     observation['processes'].append(info)
    out['process_observations'].append(observation)
out['current_environment']=planning_environment()
out['resources']={'utc':now(),'cpu_count':os.cpu_count(),'memory':[x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith(('MemTotal:','MemAvailable:'))],'disk':dict(zip(('total','used','free'),shutil.disk_usage('/app/var/artifacts'))),'gpu_device_nodes':[str(p) for p in Path('/dev').glob('nvidia*')]}
try:out['ready']=json.load(urllib.request.urlopen('http://localhost:8000/ready',timeout=10))
except Exception as e:out['ready']={'error':type(e).__name__}
out['finished_utc']=now()
print(json.dumps(out,default=str,indent=2))
