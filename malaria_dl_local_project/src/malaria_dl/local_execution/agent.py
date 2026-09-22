"""Explicit foreground local agent, no PostgreSQL imports or auto-start."""
import argparse,json,os,signal,subprocess,sys,threading,time
from pathlib import Path
from uuid import uuid4
from .transport import Api
from .processes import ProcessTracker
from .storage import verify_samples


def main():
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['dry-run','start','status','reconcile'])
    p.add_argument('--config',required=True,type=Path);p.add_argument('--state',required=True,type=Path)
    a=p.parse_args();config=json.loads(a.config.read_text());api=Api(config['url'],os.environ['CAPSTONE_AGENT_BEARER'])
    request=config['request'];state=a.state
    if a.operation=='dry-run':print(json.dumps(api.call('dry-run',request)));return
    if a.operation in ('status','reconcile'):
        stored=json.loads(state.read_text());job=stored['job'];env={k:job[k] for k in ('job_id','agent_id','owner')}
        if a.operation=='reconcile' and stored.get('exit_proof'):
            if stored.get('event_journal'):
                from .event_runtime import recover_pending
                recover_pending(api,job,stored['event_journal'],config['roots'][job['artifact_root_id']])
            print(json.dumps(api.call('exit',{**env,'proof':stored['exit_proof']})));return
        print(json.dumps(api.call('status',env)));return
    if state.exists():raise SystemExit('STATE_EXISTS_QUERY_BEFORE_EXECUTION')
    stop=threading.Event()
    def pause(*_):stop.set() # stop after this work; never signal the worker
    signal.signal(signal.SIGINT,pause);signal.signal(signal.SIGTERM,pause)
    def save(value):
        state.parent.mkdir(parents=True,exist_ok=True);tmp=state.with_suffix('.partial')
        fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as f:json.dump(value,f);f.flush();os.fsync(f.fileno())
        os.replace(tmp,state)
    while not stop.is_set():
        # Persist idempotency before submitting. A failed response never generates a new key.
        save({'request':request,'pending_claim':True})
        job=api.call('claim',request)
        from .event_runtime import journal_path, has_pending
        journal=str(journal_path(state,job))
        stored={'request':request,'job':job,'event_journal':journal};save(stored)
        roots=config['roots'];verify_samples(roots[job['session']['dataset']['dataset_root']['root_id']],job['dataset_manifest'])
        if job.get('released'):return
        child=subprocess.Popen([sys.executable,'-B','-m','src.malaria_dl.local_execution.worker'],stdin=subprocess.PIPE,start_new_session=True)
        tracker=ProcessTracker(child.pid);env={k:job[k] for k in ('job_id','agent_id','owner')}
        try:api.call('heartbeat',{**env,'process':tracker.parent})
        except BaseException:
            child.stdin.close();child.wait();raise # no job body was delivered
        lost=threading.Event();done=threading.Event()
        def heartbeat():
            while not done.wait(15):
                tracker.sample()
                try:api.call('heartbeat',{**env,'process':tracker.parent})
                except Exception:lost.set() # reservation stays held; no replacement work
        monitor=threading.Thread(target=heartbeat,daemon=True);monitor.start()
        child.stdin.write(json.dumps({'job':job,'roots':roots,'url':config['url'],'event_journal':journal}).encode());child.stdin.close()
        while child.poll() is None:tracker.sample();time.sleep(1)
        code=child.wait();done.set();monitor.join(timeout=50)
        proof=tracker.exit_proof(code);stored['exit_proof']=proof;save(stored)
        if has_pending(journal,job):
            raise RuntimeError('LOCAL_E10_PENDING_RECONCILE_REQUIRED')
        result=api.call('exit',{**env,'proof':proof});stored['result']=result;save(stored)
        print(json.dumps({'run_id':job['run_id'],'result':result}))
        if request['mode']=='controlled' or code!=0 or lost.is_set() or stop.is_set():return
        # Keep per-job state immutable; only proceed once release was confirmed.
        if not result.get('released'):return
        state=state.with_name(str(uuid4())+'.json');request={**request,'request_id':str(uuid4())}

if __name__=='__main__':main()
