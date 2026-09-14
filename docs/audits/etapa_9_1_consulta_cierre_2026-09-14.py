import json,datetime,socket
from pathlib import Path
from sqlalchemy import text
from src.malaria_dl.data.governed_dataset import dataset_read_connection
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
out={'process_utc':now(),'host':socket.gethostname(),'processes':[]}
for pid in (3475,3483):
 p=Path('/proc')/str(pid);info={'pid':pid,'exists':p.exists()}
 if p.exists():
  stat=(p/'stat').read_text().rsplit(')',1)[1].split();cmd=(p/'cmdline').read_bytes().split(b'\0')
  info.update(state=stat[0],utime=stat[11],stime=stat[12],start_ticks=stat[19],campaign_id_in_cmdline=b'3acf89b7-dc42-4b7a-8e2a-ca6ea024c344' in cmd,run_id_in_cmdline=b'a5f36df1-3341-43fd-94b9-ee1cedb834c5' in cmd)
 out['processes'].append(info)
with dataset_read_connection() as c:
 def rows(q,**p):return [dict(x) for x in c.execute(text(q),p).mappings()]
 out['publication_utc']=str(c.execute(text('SELECT transaction_timestamp()')).scalar_one())
 out['publications']=rows("SELECT p.id,p.datasource,p.scope,p.training_run_id,p.evaluation_run_id,p.model_version_id,p.checkpoint_artifact_id,p.status,p.is_active FROM stage2_model_publications p WHERE p.is_active")
 out['deployments']=rows("SELECT d.id,d.model_version_id,d.status,d.environment,d.alias,m.training_run_id,m.checkpoint_artifact_id FROM deployed_model_versions d JOIN model_versions m ON m.id=d.model_version_id WHERE d.status='active'")
print(json.dumps(out,default=str,indent=2))
