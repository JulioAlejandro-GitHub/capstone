#!/usr/bin/env python3
"""Docker-only RESET.1B orchestrator. Only creates fresh labelled disposable targets.

python3 scripts/reset/reset1b/run.py prepare --work /private/tmp/reset1b_run
python3 scripts/reset/reset1b/run.py rehearse --work /private/tmp/reset1b_run
python3 scripts/reset/reset1b/run.py finish --work /private/tmp/reset1b_run

No operational reset/migration subcommand exists. Backup must match RESET.1 manifest.
"""
import argparse,hashlib,json,os,re,secrets,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SCRIPTS=Path(__file__).resolve().parent
MANIFEST=ROOT/'docs/engineering/e10_execution_refactor/reset_1_full_history_manifest.json'

def run(args,**kw):return subprocess.run(args,check=True,**kw)
def output(args):return subprocess.check_output(args)
def write_json(p,value):p.write_text(json.dumps(value,indent=2,default=str));p.chmod(0o600)
def check(v,msg):
 if not v:raise RuntimeError(msg)

def verify(cfg):
 check(cfg['container'].startswith('capstone-reset1b-') and cfg['database']=='reset1b_rehearsal','PRODUCTION_FORBIDDEN')
 info=json.loads(output(['docker','inspect',cfg['container']]))[0]
 check(info['Config']['Labels'].get('capstone.task')=='RESET.1B','CLONE_LABEL_REQUIRED')
 check(not info['HostConfig']['PortBindings'],'CLONE_PORTS_FORBIDDEN')
 check(all(m['Type']=='volume' for m in info['Mounts']),'CLONE_BIND_MOUNT_FORBIDDEN')
 operational=json.loads(output(['docker','inspect','capstone_db']))[0]
 check(not {m.get('Name') for m in info['Mounts']} & {m.get('Name') for m in operational['Mounts']},'SHARED_VOLUME_FORBIDDEN')
 return info

def copy_code(cfg):
 run(['docker','exec','--user','root','capstone_backend','mkdir','-p',cfg['backend_work']],stdout=subprocess.DEVNULL)
 run(['docker','cp',str(SCRIPTS)+'/.','capstone_backend:'+cfg['backend_work']],stdout=subprocess.DEVNULL)

def backend(cfg,script,destination):
 copy_code(cfg)
 with destination.open('wb') as out:
  run(['docker','exec','--user','root','-e','PYTHONPATH='+cfg['backend_work']+':/app/malaria_dl_local_project:/app','capstone_backend','python',cfg['backend_work']+'/'+script],stdout=out)
 destination.chmod(0o600)

def production_guard(cfg,work):
 result=subprocess.run(['docker','exec','-i',cfg['container'],'psql','-X','-v','ON_ERROR_STOP=1','-U',cfg['user'],'-d',cfg['database']],input=(SCRIPTS/'production_blocked.sql').read_text(),text=True,capture_output=True)
 check(result.returncode==3 and 'RESET1B_PRODUCTION_NOT_AUTHORIZED' in result.stderr,'PRODUCTION_BARRIER_FAILED')
 write_json(work/'production_guard.json',{'exit':result.returncode,'before_dml_rejection':True,'message':result.stderr.strip(),'target':'isolated clone'})

def restore(cfg,work,manifest):
 dump=Path(manifest['backup']['dump'])
 digest=hashlib.sha256(dump.read_bytes()).hexdigest();check(digest==manifest['backup']['sha256'],'BACKUP_HASH_MISMATCH')
 for _ in range(30):
  if subprocess.run(['docker','exec',cfg['container'],'pg_isready','-U',cfg['user'],'-d',cfg['database']],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
  time.sleep(1)
 else:raise RuntimeError('CLONE_NOT_READY')
 run(['docker','cp',str(dump),cfg['container']+':/tmp/source.dump'])
 toc=output(['docker','exec',cfg['container'],'pg_restore','--list','/tmp/source.dump']).decode()
 (work/'archive.toc').write_text(toc)
 owners={line.rsplit(' ',1)[-1] for line in toc.splitlines() if line and not line.startswith(';')}-{'' ,'-',cfg['user']}
 check(all(re.fullmatch('[a-zA-Z_][a-zA-Z_0-9]*',x) for x in owners),'BAD_OWNER')
 setup=''.join(f'CREATE ROLE "{o}";\n' for o in sorted(owners))+f'CREATE SCHEMA "{cfg["schema"]}";\nGRANT USAGE,CREATE ON SCHEMA "{cfg["schema"]}" TO julio;\n'
 cmd=['docker','exec','-i',cfg['container'],'psql','-X','-v','ON_ERROR_STOP=1','-U',cfg['user'],'-d',cfg['database']]
 run(cmd,input=setup.encode(),stdout=subprocess.DEVNULL)
 sql=work/'restore.sql';copy_hash=hashlib.sha256();blocks=0;copying=False
 with sql.open('wb') as out:
  proc=subprocess.Popen(['docker','exec',cfg['container'],'pg_restore','--file=-','/tmp/source.dump'],stdout=subprocess.PIPE)
  for line in proc.stdout:
   if copying:
    out.write(line);copy_hash.update(line)
    if line.rstrip(b'\r\n')==b'\\.':copying=False
   else:
    line=re.sub(rb'\bpublic\b',cfg['schema'].encode(),line);out.write(line)
    if line.startswith(b'COPY ') and line.rstrip().endswith(b' FROM stdin;'):copying=True;blocks+=1
  check(proc.wait()==0 and not copying,'ARCHIVE_STREAM_FAILED')
 sql.chmod(0o600);start=time.monotonic()
 with sql.open('rb') as stream,(work/'restore.log').open('wb') as log:run(cmd+['--single-transaction'],stdin=stream,stdout=log,stderr=log)
 cfg['system_identifier']=output(cmd+['-Atc','SELECT system_identifier FROM pg_control_system()']).decode().strip()
 write_json(work/'restore.json',{'backup':str(dump),'sha256':digest,'seconds':round(time.monotonic()-start,3),'copy_blocks':blocks,'copy_sha256':copy_hash.hexdigest(),'owners':sorted(owners)})

def main():
 parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','classify','rehearse','finish']);parser.add_argument('--work',type=Path,required=True);a=parser.parse_args();work=a.work.resolve()
 check(str(work).startswith(('/private/tmp/','/tmp/')),'PRIVATE_TEMP_WORK_REQUIRED');work.mkdir(mode=0o700,parents=True,exist_ok=True)
 manifest=json.loads(MANIFEST.read_text())
 if a.stage=='prepare':
  check(not (work/'target.json').exists(),'TARGET_ALREADY_EXISTS')
  run([sys.executable,str(SCRIPTS/'protected_assets.py'),'--output',str(work/'protected_assets_before.json')])
  suffix=secrets.token_hex(6);info=json.loads(output(['docker','inspect','capstone_backend']))[0];networks=list(info['NetworkSettings']['Networks']);check(len(networks)==1,'AMBIGUOUS_NETWORK')
  cfg={'container':'capstone-reset1b-'+suffix,'database':'reset1b_rehearsal','schema':'capstone_test_reset1b_'+suffix,'user':'reset1b_maintenance','password':secrets.token_urlsafe(32),'backend_work':'/tmp/reset1b_'+suffix,'operation':secrets.token_hex(16)}
  write_json(work/'target.json',cfg)
  env=work/'target.env';env.write_text(f"POSTGRES_USER={cfg['user']}\nPOSTGRES_PASSWORD={cfg['password']}\nPOSTGRES_DB={cfg['database']}\n");env.chmod(0o600)
  run(['docker','run','-d','--name',cfg['container'],'--network',networks[0],'--env-file',str(env),'--label','capstone.task=RESET.1B','postgres:17.9'],stdout=subprocess.DEVNULL)
  verify(cfg);backend(cfg,'source_snapshot.py',work/'source_before.json');restore(cfg,work,manifest);write_json(work/'target.json',cfg)
  for hostfile,name in [(work/'target.json','target.json'),(MANIFEST,'manifest.json')]:run(['docker','cp',str(hostfile),'capstone_backend:'+cfg['backend_work']+'/'+name])
  print(json.dumps({k:v for k,v in cfg.items() if k!='password'}))
 else:
  cfg=json.loads((work/'target.json').read_text());info=verify(cfg)
  if a.stage=='classify':backend(cfg,'files.py',work/'files.json')
  elif a.stage=='rehearse':
   run([sys.executable,str(SCRIPTS/'verify_commit_boundary.py'),'--output',str(work/'commit_boundary.json')])
   backend(cfg,'rehearsal.py',work/'rehearsal.json')
   backend(cfg,'verify_final.py',work/'verify_final.json')
   production_guard(cfg,work)
  elif a.stage=='finish':
   backend(cfg,'source_snapshot.py',work/'source_after.json')
   before=json.loads((work/'source_before.json').read_text());after=json.loads((work/'source_after.json').read_text())
   check(before['schemas']==after['schemas'] and before['catalog']==after['catalog'],'OPERATIONAL_STATE_CHANGED')
   run([sys.executable,str(SCRIPTS/'protected_assets.py'),'--output',str(work/'protected_assets_after.json')])
   check(json.loads((work/'protected_assets_before.json').read_text())==json.loads((work/'protected_assets_after.json').read_text()),'PROTECTED_ASSETS_CHANGED')
   backend(cfg,'cleanup_files.py',work/'file_cleanup.json')
   volumes=[m['Name'] for m in info['Mounts']]
   run(['docker','rm','--force','--volumes',cfg['container']],stdout=subprocess.DEVNULL)
   for v in volumes:check(subprocess.run(['docker','volume','inspect',v],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0,'CLONE_VOLUME_REMAINS')
   write_json(work/'finish.json',{'public_unchanged':True,'all_synthetic_schemas_unchanged':True,'readonly':after['readonly'],'source_before':before['at'],'source_after':after['at'],'clone_removed':cfg['container'],'own_volumes_removed':len(volumes)})
  print(a.stage+' completed')
if __name__=='__main__':main()
