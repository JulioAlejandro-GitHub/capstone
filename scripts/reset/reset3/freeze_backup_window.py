"""PROPOSED backup-only freeze. NOT executed or approved by automatic review.

Requires explicit review of the complete disruption scope before use. It must
never be repurposed as a cutover lock: a watchdog reopens the original service.
"""
raise SystemExit("RESET3_FREEZE_BLOCKED_PENDING_EXPLICIT_REVIEW")

import json,os,signal,time
from pathlib import Path
from sqlalchemy import text
from src.malaria_dl.persistence.database import get_engine
from common import require,qi
HERE=Path(__file__).parent
state={'purpose':'backup only','processes':[]};stopped=[]
require(HERE.name.startswith('reset3_') and HERE.parent==Path('/tmp'),'PRIVATE_WORK_REQUIRED')
def save(): (HERE/'freeze_state.json').write_text(json.dumps(state,default=str))
try:
 with get_engine().connect() as c:
  tx=c.begin()
  try:
   require(tuple(c.execute(text('SELECT current_database(),(SELECT system_identifier::text FROM pg_control_system())')).one())==('malaria_experiments','7668020338728398886'),'IDENTITY_MISMATCH')
   require(c.execute(text("SELECT owner IS NULL AND db_pid IS NULL AND blocked_reason IS NULL AND process_evidence='{}'::jsonb FROM experiment_execution_gate")).scalar_one(),'GATE_NOT_FREE')
   require(c.execute(text('SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() AND xact_start IS NOT NULL')).scalar_one()==0,'ACTIVE_TRANSACTION')
   checks={'runs':"status NOT IN ('completed','failed','interrupted')",'experimental_campaigns':"state<>'paused'",'campaign_attempts':"state NOT IN ('failed','interrupted','verified')",'train_execution_sessions':"state NOT IN ('failed','interrupted','verified')",'local_execution_jobs':"state<>'released'",'assessment_attempts':'TRUE','cell_detection_runs':"status NOT IN ('completed','failed')",'cell_classification_runs':"status NOT IN ('completed','failed')",'microscopy_analysis_runs':"run_status NOT IN ('ready_for_analysis','review_required','blocked')",'quality_assessment_queue_items':"status NOT IN ('completed','failed')",'image_analysis_jobs':"status NOT IN ('completed','failed')"}
   for t,pred in checks.items():require(c.execute(text('SELECT count(*) FROM '+qi(t)+' WHERE '+pred)).scalar_one()==0,'ACTIVE_WORK:'+t)
   parents={}
   for p in Path('/proc').iterdir():
    if p.name.isdigit():
     try:parents[int(p.name)]=int((p/'status').read_text().split('PPid:')[1].splitlines()[0])
     except (FileNotFoundError,ProcessLookupError):pass
   pids={1}
   while True:
    expanded=pids|{p for p,parent in parents.items() if parent in pids}
    if expanded==pids:break
    pids=expanded
   require(os.getpid() not in pids and 'python' in Path('/proc/1/comm').read_text(),'APPLICATION_PROCESS_IDENTITY')
   for pid in sorted(pids):os.kill(pid,signal.SIGSTOP);stopped.append(pid)
   c.exec_driver_sql("SET LOCAL lock_timeout='5s'")
   tables=c.execute(text("SELECT schemaname,tablename FROM pg_tables WHERE schemaname='public' OR schemaname LIKE 'capstone_test_%' ORDER BY schemaname,tablename")).all()
   for s,t in tables:c.exec_driver_sql(f'LOCK TABLE {qi(s)}.{qi(t)} IN SHARE MODE')
   state.update(state='FROZEN',processes=stopped,tables_locked=len(tables),started_at=str(c.execute(text('SELECT clock_timestamp()')).scalar_one()),backend_pid=c.execute(text('SELECT pg_backend_pid()')).scalar_one());save();print('FROZEN',flush=True)
   deadline=time.monotonic()+900
   while not (HERE/'unfreeze').exists() and time.monotonic()<deadline:time.sleep(.5)
   state['release_reason']='requested' if (HERE/'unfreeze').exists() else 'watchdog_expired'
  finally:tx.rollback()
finally:
 for pid in reversed(stopped):
  try:os.kill(pid,signal.SIGCONT)
  except ProcessLookupError:pass
 state['state']='RELEASED';save();print('RELEASED',flush=True)
