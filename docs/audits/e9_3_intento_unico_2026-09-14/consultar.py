import json,os,datetime,re,shutil
from pathlib import Path
from sqlalchemy import text
from src.malaria_dl.execution.controlled import ControlledRepository
from src.malaria_dl.execution.global_gate import process_table,managed_execution,resources,descendants
repo=ControlledRepository();request='7d4cacb1-3d85-53f6-9828-8a7b1e0164c5';cid='3acf89b7-dc42-4b7a-8e2a-ca6ea024c344'
out={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'request_id':request,'resources':resources()}
with repo.transaction(readonly=True) as c:
 q=c.execute(text('SELECT * FROM campaign_controlled_requests WHERE id=CAST(:id AS uuid)'),{'id':request}).mappings().one_or_none();out['request']=dict(q) if q else None
 out['campaign_state']=c.execute(text('SELECT state FROM experimental_campaigns WHERE id=CAST(:id AS uuid)'),{'id':cid}).scalar_one()
 out['member_counts']={r[0]:r[1] for r in c.execute(text('SELECT state,count(*) FROM campaign_members WHERE campaign_id=CAST(:id AS uuid) GROUP BY state'),{'id':cid})}
 out['attempt_count']=c.execute(text('SELECT count(*) FROM campaign_attempts a JOIN campaign_members m ON m.id=a.member_id WHERE m.campaign_id=CAST(:id AS uuid)'),{'id':cid}).scalar_one()
 out['gate'] = dict(c.execute(text('SELECT * FROM experiment_execution_gate')).mappings().one())
 out['events']=[dict(r) for r in c.execute(text('SELECT event,payload,created_at FROM experiment_execution_events ORDER BY id DESC LIMIT 12')).mappings()]
 if q:
  run=str(q['run_id']);out['session']=dict(c.execute(text('SELECT * FROM train_execution_sessions WHERE run_id=CAST(:id AS uuid)'),{'id':run}).mappings().one());out['records']=[dict(r) for r in c.execute(text('SELECT kind,count(*),max(created_at) AS last_at FROM train_execution_records WHERE run_id=CAST(:id AS uuid) GROUP BY kind'),{'id':run}).mappings()]
  out['artifacts']=[dict(r) for r in c.execute(text("SELECT payload FROM train_execution_records WHERE run_id=CAST(:id AS uuid) AND kind IN ('artifact','selection') ORDER BY created_at"),{'id':run}).mappings()]
t=process_table();managed=[]
for pid,r in t.items():
 try:args=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
 except (FileNotFoundError,PermissionError):continue
 if managed_execution(args) and Path(args[0].decode(errors='replace')).name not in ('sh','bash'):
  managed.append(pid)
pids=set(managed)
for pid in managed:pids.update(descendants(t,pid))
out['processes']=[]
for pid in sorted(pids):
 try:
  f=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split(); out['processes'].append({**t[pid],'cpu_ticks':int(f[11])+int(f[12]),'rss_bytes':int(f[21])*os.sysconf('SC_PAGE_SIZE'),'managed':pid in managed})
 except (FileNotFoundError,KeyError):pass
out['clock_ticks_per_second']=os.sysconf('SC_CLK_TCK')
for name in ('cpu.stat','memory.swap.current','memory.swap.max','memory.events'):
 f=Path('/sys/fs/cgroup')/name
 if f.exists():out[name]=f.read_text().strip()
log=Path('/app/var/artifacts/controlled_'+request+'.log')
if log.exists():
 with log.open('rb') as f:
  f.seek(max(0,log.stat().st_size-8192));tail=f.read().decode(errors='replace')
 out['log_bytes']=log.stat().st_size;out['epoch_markers']=re.findall(r'Epoch \d+/\d+',tail);out['batch_markers']=re.findall(r'\b\d+/\d+\b',tail)[-4:];out['cli_exit']=re.findall(r'CONTROLLED_CLI_EXIT=(-?\d+)',tail)
 out['sanitized_error_markers']=[line for line in tail.splitlines() if re.fullmatch(r'[A-Za-z0-9_.]+: [A-Z][A-Z0-9_]+',line)]
print(json.dumps(out,indent=2,default=str))
