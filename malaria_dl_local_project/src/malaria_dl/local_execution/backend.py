"""Backend-only service. All mutations serialize against the existing global gate."""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
import json
import os
from sqlalchemy import text
from ..campaigns.contracts import CampaignError,canonical,digest
from ..execution.controlled import ControlledRepository,validate_revision
from ..execution.global_gate import verify_retained_processes,process_table,managed_execution
from ..execution.artifacts import verify_session,file_identity
from .storage import resolve,identity


class LocalBackend:
    def __init__(self,repository,roots,check=None,loader=None):
        self.repo=repository;self.roots={k:Path(v).resolve() for k,v in roots.items()}
        self.check=check or self.preflight;self.loader=loader or self.load_checkpoint

    @staticmethod
    def load_checkpoint(path,contract):
        import subprocess,sys
        result=subprocess.run([sys.executable,'-B','-c',
            'import sys,json; from src.malaria_dl.execution.artifacts import keras_loader; keras_loader(sys.argv[1],json.loads(sys.argv[2]))',str(path),json.dumps(contract)],capture_output=True,timeout=120)
        if result.returncode:raise CampaignError('LOCAL_CHECKPOINT_LOAD_FAILED')

    def preflight(self,row,payload):
        from ..persistence.dataset_evidence import verify_dataset_for_execution
        from ..data.governed_dataset import assert_run_dataset_snapshot_unchanged
        from ..campaigns.service import planning_environment
        snapshot=verify_dataset_for_execution(str(row['dataset_version_id']),expected_evidence_id=str(row['dataset_evidence_id']),consumer='local_python.claim')
        assert_run_dataset_snapshot_unchanged(snapshot,row['dataset_snapshot'])
        if planning_environment()['source_sha256']!=payload['environment']['source_sha256']:
            raise CampaignError('LOCAL_BACKEND_SOURCE_CONFLICT')

    @contextmanager
    def bound(self,c):
        @contextmanager
        def scope(readonly=False):
            with c.begin_nested():yield c
        yield ControlledRepository(scope)

    def read_job(self,c,data,principal,lock=True):
        job=c.execute(text('SELECT * FROM local_execution_jobs WHERE id=CAST(:id AS uuid)'+(' FOR UPDATE' if lock else '')),{'id':data['job_id']}).mappings().one_or_none()
        if not job or job['principal']!=principal or str(job['agent_id'])!=data['agent_id'] or str(job['owner'])!=data['owner']:
            raise CampaignError('LOCAL_OWNER_FENCED')
        return dict(job)

    def prepare(self,data):
        row=self.repo.get(data['campaign_id'],data['dataset_id'])
        with self.repo.transaction(readonly=True) as c:payload=self.repo.revision(c,data['campaign_id'],data['revision_id'])
        validate_revision(row,payload)
        if payload['environment'].get('execution_mode')!='local_python' or payload['environment']!=data['environment']:
            raise CampaignError('LOCAL_ENVIRONMENT_CONFLICT')
        if str(Path(row['dataset_snapshot']['dataset_root']).resolve())!=str(self.roots[data['dataset_root_id']]):
            raise CampaignError('DATASET_ROOT_MAPPING_CONFLICT')
        if data['artifact_root_id']==data['dataset_root_id']:raise CampaignError('DISTINCT_STORAGE_ROOTS_REQUIRED')
        if data['mode'] not in ('controlled','sequential'):raise CampaignError('LOCAL_MODE_INVALID')
        expected=('paused',) if data['mode']=='controlled' else ('frozen','active')
        if row['state'] not in expected:raise CampaignError('CAMPAIGN_PAUSE_CONFLICT')
        return row,payload

    def dry_run(self,data):
        self.prepare(data)
        from ..execution.global_gate import status
        value=status(self.repo)
        return {'execution_ready':value['available'],'global':value,'writes':0,'reservations':0,'mode':data['mode']}

    def claim(self,data,principal):
        fingerprint=digest(data)
        # Idempotent read before running a potentially expensive dataset preflight.
        with self.repo.transaction(readonly=True) as c:
            old=c.execute(text('SELECT * FROM local_execution_jobs WHERE id=CAST(:id AS uuid)'),{'id':data['request_id']}).mappings().one_or_none()
            if old:
                if old['principal']!=principal or old['request_hash']!=fingerprint:raise CampaignError('LOCAL_REQUEST_CONFLICT')
                return json.loads(canonical(old['result']))
        row,payload=self.prepare(data);self.check(row,payload)
        manifest=[]
        dataset_root=self.roots[data['dataset_root_id']]
        for split in ('train','val'):
            for path in sorted((dataset_root/split).rglob('*')):
                if path.is_file() and path.suffix.lower() in ('.png','.jpg','.jpeg','.bmp','.gif'):
                    manifest.append({'split':split,'relative_path':path.relative_to(dataset_root).as_posix(),**identity(path)})
        if any(sum(x['split']==split for x in manifest)!=row['dataset_snapshot']['counts'][split] for split in ('train','val')):raise CampaignError('LOCAL_DATASET_POPULATION_CONFLICT')
        with self.repo.transaction() as c:
            if not c.execute(text('SELECT pg_try_advisory_xact_lock(120994,1)')).scalar_one():raise CampaignError('GLOBAL_EXPERIMENT_BUSY')
            gate=dict(c.execute(text('SELECT * FROM experiment_execution_gate FOR UPDATE')).mappings().one())
            # Recheck after serialization for a response lost after commit.
            old=c.execute(text('SELECT * FROM local_execution_jobs WHERE id=CAST(:id AS uuid)'),{'id':data['request_id']}).mappings().one_or_none()
            if old:
                if old['principal']!=principal or old['request_hash']!=fingerprint:raise CampaignError('LOCAL_REQUEST_CONFLICT')
                return old['result']
            verify_retained_processes(gate['process_evidence'])
            if gate['owner'] or gate['blocked_reason']:raise CampaignError('GLOBAL_EXECUTION_BLOCKED')
            if c.execute(text("SELECT (SELECT count(*) FROM train_execution_sessions WHERE state IN ('active','completed'))+(SELECT count(*) FROM assessment_attempts WHERE state='active')")).scalar_one():raise CampaignError('GLOBAL_EXPERIMENT_BUSY')
            for pid in process_table():
                try:args=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
                except (FileNotFoundError,PermissionError):continue
                if managed_execution(args):raise CampaignError('LOCAL_DOCKER_PROCESS_ACTIVE')
            token=str(uuid4())
            c.execute(text("INSERT INTO local_execution_jobs(id,principal,agent_id,owner,request_hash,campaign_id,state) VALUES(CAST(:id AS uuid),:principal,CAST(:agent AS uuid),CAST(:owner AS uuid),:hash,CAST(:campaign AS uuid),'held')"),dict(id=data['request_id'],principal=principal,agent=data['agent_id'],owner=token,hash=fingerprint,campaign=data['campaign_id']))
            c.execute(text("UPDATE experiment_execution_gate SET owner=CAST(:owner AS uuid),db_pid=NULL,process_evidence=CAST(:proof AS jsonb),updated_at=clock_timestamp()"),{'owner':token,'proof':canonical({'release_confirmed':False,'remote_job':data['request_id']})})
            c.execute(text("SELECT set_config('capstone.execution_token',:token,true)"),{'token':token})
            with self.bound(c) as repo:
                if data['mode']=='controlled':
                    s,_=repo.reserve(campaign=data['campaign_id'],member=data['member_id'],previous=data['previous_attempt_id'],dataset=data['dataset_id'],revision_id=data['revision_id'],request_id=data['request_id'],reason=data['reason'],root=self.roots[data['artifact_root_id']],current=data['environment'])
                else:s=repo.claim(data['campaign_id'],str(uuid4()),'local_python:'+data['agent_id'],os.getpid(),self.roots[data['artifact_root_id']],revision_id=data['revision_id'])
                if s is None:raise CampaignError('NO_ELIGIBLE_MEMBER')
            # repository.session() returns raw driver types (uuid.UUID, datetime) for
            # uuid/timestamptz columns; canonical() intentionally never coerces those.
            safe=deepcopy(s)
            for key in ('run_id','attempt_id','owner','started_at','updated_at'):
                if safe.get(key) is not None:safe[key]=str(safe[key])
            public=deepcopy(safe);public['owner']=token
            public['dataset']['dataset_root']={'root_id':data['dataset_root_id'],'relative_path':None}
            public['artifact_root']={'root_id':data['artifact_root_id'],'relative_path':str(s['run_id'])}
            result={'job_id':data['request_id'],'agent_id':data['agent_id'],'owner':token,'run_id':str(s['run_id']),'artifact_root_id':data['artifact_root_id'],'session':public,'mode':data['mode'],'heartbeat_seconds':15,'expiry_seconds':60,'dataset_manifest':manifest}
            c.execute(text('UPDATE local_execution_jobs SET run_id=CAST(:run AS uuid),session=CAST(:session AS jsonb),result=CAST(:result AS jsonb) WHERE id=CAST(:id AS uuid)'),{'id':data['request_id'],'run':str(s['run_id']),'session':canonical(safe),'result':canonical(result)})
            return json.loads(canonical(result))

    def operation(self,operation,data,principal):
        readonly=operation in ('status','records')
        with self.repo.transaction(readonly=readonly) as c:
            if not readonly:c.execute(text('SELECT * FROM experiment_execution_gate FOR UPDATE')).first()
            job=self.read_job(c,data,principal,lock=not readonly)
            if operation=='status':
                age=c.execute(text('SELECT EXTRACT(EPOCH FROM clock_timestamp()-:seen)'),{'seen':job['heartbeat_at']}).scalar_one()
                return {'state':job['state'],'communication':'uncertain' if age>60 else 'connected','released':job['state'] in ('released','failed'),'result':job['result'],'exit_proof':job['exit_proof']}
            if operation=='records':
                with self.bound(c) as repo:return {'records':repo.records(job['run_id'])}
            if job['state'] in ('released','failed'):
                if operation=='exit' and job['exit_proof']==data['proof']:return job['result']
                raise CampaignError('LOCAL_OWNER_FENCED')
            c.execute(text("SELECT set_config('capstone.execution_token',:token,true)"),{'token':str(job['owner'])})
            s=job['session'];rid=str(s['run_id']);owner=str(s['owner'])
            with self.bound(c) as repo:
                if operation=='heartbeat':
                    proof=data.get('process')
                    if job['process'] and proof!=job['process']:raise CampaignError('LOCAL_PROCESS_IDENTITY_CONFLICT')
                    c.execute(text('UPDATE local_execution_jobs SET heartbeat_at=clock_timestamp(),process=coalesce(process,CAST(:process AS jsonb)) WHERE id=:id'),{'process':canonical(proof),'id':job['id']})
                    return {'accepted':True,'may_launch':proof is not None}
                if operation=='record':
                    payload=deepcopy(data['payload'])
                    if 'path' in payload:
                        ref=payload['path'];root=self.roots[ref['root_id']]
                        if ref['root_id']!=job['result']['artifact_root_id'] or not ref['relative_path'].startswith(rid+'/'):raise CampaignError('LOCAL_ARTIFACT_OWNER_CONFLICT')
                        path=resolve(root,ref['relative_path']);payload['path']=str(path)
                        if data['kind']=='artifact' and identity(path)!={k:payload[k] for k in ('sha256','bytes')}:raise CampaignError('LOCAL_ARTIFACT_HASH_CONFLICT')
                    repo.put(rid,owner,data['kind'],data['phase'],data['key'],payload);return {'accepted':True}
                if operation=='calculation-ended':
                    if job['completion'] is not None and job['completion']!=data['evidence']:raise CampaignError('LOCAL_COMPLETION_CONFLICT')
                    c.execute(text("UPDATE local_execution_jobs SET completion=CAST(:proof AS jsonb),state='calculation_reported' WHERE id=:id"),{'proof':canonical(data['evidence']),'id':job['id']});return {'calculation_reported':True,'released':False}
                if operation=='exit':
                    proof=data['proof']
                    if not job['process'] or proof['parent']!=job['process'] or proof['remaining'] or not proof['absence_proven']:raise CampaignError('LOCAL_PROCESS_ABSENCE_UNPROVEN')
                    if proof['exit_code']==0 and job['completion']:
                        repo.finish(rid,owner,'completed',job['completion'])
                        verification=verify_session(repo,repo.session(rid),self.loader)
                        repo.finish(rid,owner,'verified',verification);state='released'
                    else:
                        repo.finish(rid,owner,'failed',cause='LOCAL_CHILD_EXIT_'+str(proof['exit_code']));state='failed'
                        repo.pause(str(job['campaign_id']),'LOCAL_TRAIN_FAILURE')
                    result={'run_id':rid,'state':repo.session(rid)['state'],'released':True}
                    c.execute(text('UPDATE local_execution_jobs SET state=:state,exit_proof=CAST(:proof AS jsonb),result=CAST(:result AS jsonb) WHERE id=:id'),{'id':job['id'],'state':state,'proof':canonical(proof),'result':canonical(result)})
                    c.execute(text("UPDATE experiment_execution_gate SET owner=NULL,db_pid=NULL,process_evidence='{}',blocked_reason=:reason,updated_at=clock_timestamp()"),{'reason':'LOCAL_TRAIN_FAILURE' if state=='failed' else None})
                    return result
            raise CampaignError('LOCAL_OPERATION_INVALID')
