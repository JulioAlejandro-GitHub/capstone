"""Explicit technical revision and a single paused TRAIN; no queue resume."""
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
import argparse
import json
import os
import socket

from ..campaigns.contracts import CampaignError, canonical, digest, member_configuration
from ..campaigns.repository import execute, identifier
from ..campaigns.service import planning_environment
from .repository import ExecutionRepository


def validate_revision(row, payload):
    required = {'original_environment', 'environment', 'contract_hash', 'reason', 'files', 'tests', 'authorization'}
    if set(payload) != required:
        raise CampaignError('TECHNICAL_REVISION_FIELDS_INVALID')
    if payload['original_environment'] != row['environment'] or payload['contract_hash'] != row['contract_hash']:
        raise CampaignError('TECHNICAL_SCIENTIFIC_CONTRACT_CONFLICT')
    for k in ('reason', 'authorization'):
        if not isinstance(payload[k], str) or not payload[k].strip():
            raise CampaignError('TECHNICAL_PROVENANCE_REQUIRED')
    if not isinstance(payload['files'], dict) or not payload['files'] or not isinstance(payload['tests'], list) or not payload['tests']:
        raise CampaignError('TECHNICAL_EVIDENCE_REQUIRED')
    import re
    if not all(isinstance(p,str) and isinstance(h,str) and re.fullmatch('[a-f0-9]{64}',h) for p,h in payload['files'].items()):
        raise CampaignError('TECHNICAL_FILE_HASH_INVALID')
    env = payload['environment']
    if not isinstance(env,dict) or not re.fullmatch('[a-f0-9]{64}',str(env.get('source_sha256',''))):
        raise CampaignError('TECHNICAL_SOURCE_INVALID')
    from ..local_execution.revision import valid_environment
    if not valid_environment(env) and {k:v for k,v in env.items() if k not in ('source_sha256','git_commit')} != {k:v for k,v in row['environment'].items() if k not in ('source_sha256','git_commit')}:
        raise CampaignError('TECHNICAL_ENVIRONMENT_CONFLICT')
    return payload


class ControlledRepository(ExecutionRepository):
    def installed(self):
        with self.transaction(readonly=True) as c:
            return bool(execute(c,"SELECT to_regclass('campaign_technical_revisions') IS NOT NULL").scalar_one())

    def register_revision(self, campaign, revision_id, payload):
        """Explicit write, never called by dry-run or reservation implicitly."""
        with self.transaction() as c:
            row=self._campaign(c,campaign,True)
            validate_revision(row,payload)
            if row['state']!='paused':raise CampaignError('PAUSED_CAMPAIGN_REQUIRED')
            old=execute(c,'SELECT payload FROM campaign_technical_revisions WHERE id=CAST(:id AS uuid)',id=identifier(revision_id)).scalar_one_or_none()
            if old is not None:
                if old!=payload:raise CampaignError('REVISION_IDEMPOTENCY_CONFLICT')
                return
            execute(c,'INSERT INTO campaign_technical_revisions(id,campaign_id,payload,canonical_payload,payload_hash) VALUES(CAST(:id AS uuid),CAST(:cid AS uuid),CAST(:payload AS jsonb),:canonical,:hash)',id=identifier(revision_id),cid=identifier(campaign),payload=canonical(payload),canonical=canonical(payload),hash=digest(payload))

    def revision(self,c, campaign, revision_id):
        r=execute(c,'SELECT * FROM campaign_technical_revisions WHERE id=CAST(:id AS uuid) AND campaign_id=CAST(:cid AS uuid)',id=identifier(revision_id),cid=identifier(campaign)).mappings().one_or_none()
        if r is None:raise CampaignError('UNKNOWN_TECHNICAL_REVISION')
        if digest(r['payload'])!=r['payload_hash']:raise CampaignError('TECHNICAL_HASH_CONFLICT')
        return r['payload']

    def eligibility(self,c,row,member_id,previous_id,dataset_id,payload,current):
        if str(row['dataset_version_id'])!=identifier(dataset_id):raise CampaignError('DATASET_ID_CONFLICT')
        if row['state']!='paused':raise CampaignError('PAUSED_CAMPAIGN_REQUIRED')
        validate_revision(row,payload)
        if any(current.get(k)!=payload['environment'].get(k) for k in ('source_sha256','python','tensorflow','packages','determinism_environment')):
            raise CampaignError('TECHNICAL_RUNTIME_HASH_CONFLICT')
        member=execute(c,'SELECT * FROM campaign_members WHERE id=CAST(:id AS uuid) AND campaign_id=CAST(:cid AS uuid)',id=identifier(member_id),cid=str(row['id'])).mappings().one_or_none()
        previous=execute(c,'SELECT * FROM campaign_attempts WHERE id=CAST(:id AS uuid)',id=identifier(previous_id)).mappings().one_or_none()
        if member is None or previous is None or previous['member_id']!=member['id'] or previous['state'] not in ('failed','interrupted') or member['state'] not in ('failed','interrupted'):
            raise CampaignError('CONTROLLED_MEMBER_INELIGIBLE')
        if execute(c,"SELECT count(*) FROM campaign_attempts a JOIN campaign_members m ON m.id=a.member_id WHERE m.campaign_id=CAST(:id AS uuid) AND a.state IN ('active','completed')",id=str(row['id'])).scalar_one():
            raise CampaignError('ACTIVE_ATTEMPT_BLOCKS_CONTROLLED')
        ordinal=execute(c,'SELECT coalesce(max(ordinal),0)+1 FROM campaign_attempts WHERE member_id=CAST(:id AS uuid)',id=identifier(member_id)).scalar_one()
        if ordinal>row['protocol']['budget']['max_attempts_per_member']:raise CampaignError('ATTEMPT_BUDGET_EXHAUSTED')
        return member,ordinal

    def dry_run(self,campaign,member,previous,dataset,revision_id=None,proposal=None,current=None):
        row=self.get(campaign,dataset)
        installed=self.installed()
        if not installed and proposal is None:
            raise CampaignError('TECHNICAL_REVISION_MIGRATION_REQUIRED')
        with self.transaction(readonly=True) as c:
            payload=proposal if proposal is not None else self.revision(c,campaign,revision_id)
            m,n=self.eligibility(c,row,member,previous,dataset,payload,current or planning_environment())
        from .global_gate import status
        global_status = status(self)
        return {'campaign_id':str(row['id']),'dataset_version_id':identifier(dataset),'member_id':str(m['id']),'previous_attempt_id':identifier(previous),'next_ordinal':n,'state':'paused','eligible_without_reservation':True,'installed':installed,'revision_registered':proposal is None,'execution_ready':installed and proposal is None and global_status['available'],'global_execution':global_status,'memory_optimization_required':False,'revision_hash':digest(payload),'writes':0}

    def reserve(self,campaign,member,previous,dataset,revision_id,request_id,reason,root,current=None):
        current=current or planning_environment()
        with self.transaction() as c:
            row=self._campaign(c,campaign,True)
            old=execute(c,'SELECT * FROM campaign_controlled_requests WHERE id=CAST(:id AS uuid)',id=identifier(request_id)).mappings().one_or_none()
            if old:
                if any(str(old[k])!=identifier(v) for k,v in [('campaign_id',campaign),('member_id',member),('previous_attempt_id',previous),('revision_id',revision_id)]) or old['reason']!=reason or str(row['dataset_version_id'])!=identifier(dataset):
                    raise CampaignError('CONTROLLED_IDEMPOTENCY_CONFLICT')
                run=str(old['run_id']); created=False
            else:
                payload=self.revision(c,campaign,revision_id)
                m,n=self.eligibility(c,row,member,previous,dataset,payload,current)
                if not isinstance(reason,str) or not reason.strip():raise CampaignError('CONTROLLED_REASON_REQUIRED')
                attempt,run,owner=map(str,(uuid4(),uuid4(),uuid4()))
                execute(c,'INSERT INTO campaign_controlled_requests(id,campaign_id,member_id,revision_id,previous_attempt_id,attempt_id,run_id,reason) VALUES(CAST(:id AS uuid),CAST(:cid AS uuid),CAST(:member AS uuid),CAST(:revision AS uuid),CAST(:previous AS uuid),CAST(:attempt AS uuid),CAST(:run AS uuid),:reason)',id=identifier(request_id),cid=identifier(campaign),member=identifier(member),revision=identifier(revision_id),previous=identifier(previous),attempt=attempt,run=run,reason=reason)
                execute(c,"INSERT INTO campaign_attempts(id,member_id,ordinal,state) VALUES(CAST(:id AS uuid),CAST(:member AS uuid),:n,'active')",id=attempt,member=identifier(member),n=n)
                cfg=execute(c,'SELECT configuration FROM campaign_configurations WHERE campaign_id=CAST(:cid AS uuid) AND configuration_hash=:hash',cid=identifier(campaign),hash=m['configuration_hash']).scalar_one()
                config=member_configuration(cfg,m['seed'])
                self._create_run(c,run,config,row['dataset_snapshot'],payload['environment'],row['experiment_id'],evidence_id=str(row['dataset_evidence_id']),campaign_id=campaign)
                execute(c,'UPDATE campaign_attempts SET training_run_id=CAST(:run AS uuid) WHERE id=CAST(:id AS uuid)',run=run,id=attempt)
                execute(c,'INSERT INTO train_execution_sessions(run_id,attempt_id,owner,host,parent_pid,configuration,dataset,environment,artifact_root) VALUES(CAST(:run AS uuid),CAST(:attempt AS uuid),CAST(:owner AS uuid),:host,:pid,CAST(:config AS jsonb),CAST(:dataset AS jsonb),CAST(:env AS jsonb),:root)',run=run,attempt=attempt,owner=owner,host=socket.gethostname(),pid=os.getpid(),config=canonical(config),dataset=canonical(row['dataset_snapshot']),env=canonical(payload['environment']),root=str(Path(root).resolve()/run))
                created=True
        return self.session(run),created

    def existing_request(self, request_id):
        with self.transaction(readonly=True) as c:
            q=execute(c,'SELECT * FROM campaign_controlled_requests WHERE id=CAST(:id AS uuid)',id=identifier(request_id)).mappings().one_or_none()
            return dict(q) if q else None

    def recover(self, campaign, request_id):
        """Reconcile the same consumed reservation; never launch or reserve again."""
        from .campaign import dead_local
        from .artifacts import verify_session, keras_loader
        q=self.existing_request(request_id)
        if q is None or str(q['campaign_id'])!=identifier(campaign):
            raise CampaignError('CONTROLLED_REQUEST_NOT_FOUND')
        s=self.session(q['run_id'])
        if self.get(campaign)['state']!='paused':raise CampaignError('PAUSED_CAMPAIGN_REQUIRED')
        if s['state'] in ('active','completed'):
            if not dead_local(s):raise CampaignError('ACTIVE_OWNER_NOT_PROVEN_DEAD')
            if s['state']=='active':
                self.finish(s['run_id'],s['owner'],'interrupted',cause='CONTROLLED_OWNER_AND_CHILD_ABSENT')
            else:
                from .campaign import preflight
                preflight(self,effective_row(self,self.get(campaign),s),Path(s['artifact_root']).parent)
                self.finish(s['run_id'],s['owner'],'verified',verify_session(self,s,keras_loader))
        return {'run_id':str(s['run_id']),'state':self.session(s['run_id'])['state'],'launched':False}


def effective_row(repository,row,session):
    """Only a registered binding can select an alternate runtime identity."""
    if session['environment']==row['environment']:return row
    control=ControlledRepository(repository.scope)
    if not control.installed():raise CampaignError('TECHNICAL_REVISION_NOT_INSTALLED')
    with control.transaction(readonly=True) as c:
        q=execute(c,'SELECT * FROM campaign_controlled_requests WHERE run_id=CAST(:run AS uuid) AND campaign_id=CAST(:cid AS uuid)',run=str(session['run_id']),cid=str(row['id'])).mappings().one_or_none()
        if q is None:
            installed = execute(c,"SELECT to_regclass('train_execution_revisions') IS NOT NULL").scalar_one()
            if installed:
                q=execute(c,'SELECT revision_id FROM train_execution_revisions WHERE attempt_id=CAST(:attempt AS uuid) AND campaign_id=CAST(:cid AS uuid)',attempt=str(session['attempt_id']),cid=str(row['id'])).mappings().one_or_none()
        if q is None:raise CampaignError('TECHNICAL_BINDING_REQUIRED')
        payload=control.revision(c,row['id'],q['revision_id']);validate_revision(row,payload)
        if session['environment']!=payload['environment']:raise CampaignError('TECHNICAL_SESSION_CONFLICT')
    result=deepcopy(row);result['environment']=payload['environment'];return result


def technical_row(repository, row, revision_id):
    control = ControlledRepository(repository.scope)
    with control.transaction(readonly=True) as c:
        payload = control.revision(c, row['id'], revision_id)
        validate_revision(row, payload)
    result = deepcopy(row)
    result['environment'] = payload['environment']
    return result


def queue_dry_run(repository, campaign, dataset, revision_id=None, proposal=None, current=None):
    """Inspect the queue's deterministic next member; never claim or resume."""
    from .global_gate import status, POLICY
    from .campaign import IDENTITY_KEYS
    row = repository.get(campaign, dataset)
    if str(row['dataset_version_id']) != identifier(dataset):
        raise CampaignError('DATASET_ID_CONFLICT')
    if proposal is not None:
        payload = validate_revision(row, proposal)
    else:
        with repository.transaction(readonly=True) as c:
            payload = ControlledRepository(repository.scope).revision(c, campaign, revision_id)
        validate_revision(row, payload)
    actual = current or planning_environment()
    if any(actual.get(k) != payload['environment'].get(k) for k in IDENTITY_KEYS):
        raise CampaignError('TECHNICAL_RUNTIME_HASH_CONFLICT')
    budget = row['protocol']['budget']['max_attempts_per_member']
    candidates = [m for m in row['members'] if m['state'] in ('pending','failed','interrupted')
                  and sum(a['member_id'] == m['id'] for a in row['attempts']) < budget]
    candidates.sort(key=lambda m: (m['state'] != 'pending', m['position']))
    global_status = status(repository)
    return {'campaign_id': str(row['id']), 'dataset_version_id': identifier(dataset),
            'campaign_state': row['state'], 'writes': 0, 'reservations': 0,
            'next_member_id': str(candidates[0]['id']) if candidates else None,
            'next_position': candidates[0]['position'] if candidates else None,
            'revision_registered': proposal is None, 'global_execution': global_status,
            'execution_ready': bool(candidates) and proposal is None and global_status['available'],
            'memory_optimization_required': False, 'policy': POLICY,
            'dataset_integrity': 'frozen contract checked; canonical E1 preflight required before reservation'}


def execute_one(repo, *, campaign,member,previous,dataset,revision_id,request_id,reason,root,check=None,launch=None,loader=None):
    from .campaign import preflight,run_child
    from .artifacts import keras_loader,verify_session
    check=check or preflight;launch=launch or run_child;loader=loader or keras_loader
    from .global_gate import CURRENT
    gate = CURRENT.get()
    if gate is not None and loader is keras_loader:
        from .process_verification import isolated_keras_loader
        loader = isolated_keras_loader
    old=repo.existing_request(request_id)
    if old:
        if any(str(old[k])!=identifier(v) for k,v in [('campaign_id',campaign),('member_id',member),('previous_attempt_id',previous),('revision_id',revision_id)]) or old['reason']!=reason:
            raise CampaignError('CONTROLLED_IDEMPOTENCY_CONFLICT')
        row=repo.get(campaign,dataset)
        if row['state']!='paused':raise CampaignError('PAUSED_CAMPAIGN_REQUIRED')
        s=repo.session(old['run_id'])
        return {'launched':False,'run_id':str(s['run_id']),'state':s['state']}
    # All checks that can fail without reserving happen first.
    repo.dry_run(campaign,member,previous,dataset,revision_id)
    row=repo.get(campaign,dataset)
    with repo.transaction(readonly=True) as c:payload=repo.revision(c,campaign,revision_id)
    runtime=deepcopy(row);runtime['environment']=payload['environment']
    check(repo,runtime,root)
    session,created=repo.reserve(campaign,member,previous,dataset,revision_id,request_id,reason,root)
    if not created:return {'launched':False,'run_id':str(session['run_id']),'state':session['state']}
    run,owner=str(session['run_id']),str(session['owner'])
    if gate is not None:gate.active_run=run
    try:
        code=launch(session,repo)
        current=repo.session(run)
        if code!=0 or current['state']!='completed':
            if current['state']=='active':repo.finish(run,owner,'failed',cause=f'CONTROLLED_CHILD_EXIT_{code}')
            if gate is not None:gate.outcome(False)
        else:
            if gate is not None:gate.require_healthy()
            check(repo,runtime,root)
            repo.finish(run,owner,'verified',verify_session(repo,current,loader))
            if gate is not None:gate.outcome(True)
    except BaseException as exc:
        current=repo.session(run)
        if current['state']=='active':repo.finish(run,owner,'failed',cause='CONTROLLED_'+type(exc).__name__.upper())
        raise
    return {'launched':True,'run_id':run,'state':repo.session(run)['state']}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('operation',choices=['dry-run','execute','register','recover'])
    for name in ('campaign-id','dataset-version-id','member-id','previous-attempt-id'):p.add_argument('--'+name,required=True,type=identifier)
    p.add_argument('--revision-id',type=identifier)
    p.add_argument('--proposal',type=Path)
    p.add_argument('--request-id',type=identifier)
    p.add_argument('--reason')
    p.add_argument('--artifact-root',default='/app/var/artifacts/campaign_runs')
    a=p.parse_args();repo=ControlledRepository()
    proposal=json.loads(a.proposal.read_text()) if a.proposal else None
    if a.operation=='dry-run':
        result=repo.dry_run(a.campaign_id,a.member_id,a.previous_attempt_id,a.dataset_version_id,a.revision_id,proposal)
    elif a.operation=='register':
        if not a.revision_id or proposal is None:p.error('revision-id and proposal required')
        repo.dry_run(a.campaign_id,a.member_id,a.previous_attempt_id,a.dataset_version_id,proposal=proposal)
        repo.register_revision(a.campaign_id,a.revision_id,proposal);result={'registered':a.revision_id}
    elif a.operation=='recover':
        if not a.request_id:p.error('request-id required')
        repo.get(a.campaign_id,a.dataset_version_id)
        from .global_gate import GlobalGate
        with GlobalGate('controlled-recovery'):
            result=repo.recover(a.campaign_id,a.request_id)
    else:
        if not a.revision_id or not a.request_id or not a.reason:p.error('revision-id, request-id and reason required')
        from .global_gate import GlobalGate
        with GlobalGate('controlled'):
            result=execute_one(repo,campaign=a.campaign_id,member=a.member_id,previous=a.previous_attempt_id,dataset=a.dataset_version_id,revision_id=a.revision_id,request_id=a.request_id,reason=a.reason,root=a.artifact_root)
    print(json.dumps(result))

if __name__=='__main__':main()
