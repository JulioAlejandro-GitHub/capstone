"""Compare the restored golden to live SELECTs; mutate ONLY authenticated clone.

No operational credentials or complete user records are serialized to evidence.
The original manifest is never modified. The new baseline is a separate artifact.
"""
import copy,json,hashlib
from pathlib import Path
from sqlalchemy import text
import rehearsal as r
from common import require,fingerprint,sha
from src.malaria_dl.persistence.database import get_engine

with r.engine.connect() as c:
 with c.begin():
  r.assert_clone(c,r.cfg)
  golden=fingerprint(c,r.cfg['schema'])
  expected={k:{'count':v['current'],'sha256':v['sha256_before']} for k,v in r.m['tables'].items()}
  require(golden==expected,'GOLDEN_RESTORE_MISMATCH')
  old_users=c.execute(text('SELECT to_jsonb(t) FROM users t ORDER BY id')).scalars().all()
  old_audit={v['id']:v for v in c.execute(text('SELECT to_jsonb(t) FROM audit_events t')).scalars()}
with get_engine().connect().execution_options(postgresql_readonly=True,isolation_level='REPEATABLE READ') as c:
 with c.begin():
  identity=list(c.execute(text("SELECT current_database(),current_schema(),session_user,(SELECT system_identifier::text FROM pg_control_system()),current_setting('transaction_read_only')")).one())
  require(identity==['malaria_experiments','public','julio','7668020338728398886','on'],'SOURCE_IDENTITY_MISMATCH')
  actual=fingerprint(c,'public')
  new_users=c.execute(text('SELECT to_jsonb(t) FROM users t ORDER BY id')).scalars().all()
  new_audit={v['id']:v for v in c.execute(text('SELECT to_jsonb(t) FROM audit_events t')).scalars()}
  at=str(c.execute(text('SELECT clock_timestamp()')).scalar_one())
require({t for t in expected if expected[t]!=actual.get(t)}=={'users','audit_events'} and set(expected)==set(actual),'STOP_UNEXPLAINED_INVENTORY_DRIFT')
require(len(old_users)==len(new_users)==1,'STOP_USERS_COUNT')
a,b=old_users[0],new_users[0]
changed=[k for k in sorted(set(a)|set(b)) if a.get(k)!=b.get(k)]
require(changed==['last_login_at'],'STOP_UNEXPLAINED_USER_FIELDS')
require(all(new_audit.get(k)==v for k,v in old_audit.items()),'STOP_EXISTING_AUDIT_CHANGED')
added=[v for k,v in new_audit.items() if k not in old_audit]
require(len(added)==1,'STOP_UNEXPECTED_ADDED_EVENTS')
event=added[0]
require(event['id']=='7615cb3c-6fc3-44ac-bdae-5c6462105c56' and event['event_type']=='USER_LOGIN_SUCCEEDED' and event['action']=='login' and event['resource_type']=='login' and event['success'] is True and event['actor_user_id']==b['id'] and event['actor_username_snapshot']==b['username'],'STOP_UNEXPLAINED_LOGIN')
from datetime import datetime
login=datetime.fromisoformat(b['last_login_at']);evt=datetime.fromisoformat(event['created_at'])
require(0<=(evt-login).total_seconds()<1 and login>datetime.fromisoformat(a['last_login_at']),'STOP_LOGIN_TIME_MISMATCH')
# Exact event and user preimage proof, excluding secrets from evidence.
evidence={'classification':'EXPECTED_AUTHENTICATION_DRIFT','at':at,'identity':identity,'tables':actual,'original_tables':expected,'user':{'id':b['id'],'username':b['username'],'changed_columns':changed,'before':{'last_login_at':a['last_login_at']},'after':{'last_login_at':b['last_login_at']},'all_other_columns_equal':True,'all_other_columns_compared':sorted(k for k in a if k!='last_login_at')},'event':{k:event[k] for k in ('id','event_type','action','created_at','actor_user_id','actor_username_snapshot','resource_type','resource_id','request_method','request_path','success')},'event_row_sha256':sha(event),'all_old_audit_rows_exactly_equal':True,'added_audit_rows':1,'other_95_tables_equal':True}
baseline=copy.deepcopy(r.m)
baseline['task']='RESET.2A baseline v1'
baseline['reconciliation']={'version':1,'classification':evidence['classification'],'source_golden_sha256':hashlib.sha256((r.HERE/'manifest.json').read_bytes()).hexdigest(),'at':at,'event_id':event['id'],'preserve_new_login':True}
for t in ('users','audit_events'):
 baseline['tables'][t]['current']=actual[t]['count'];baseline['tables'][t]['sha256_before']=actual[t]['sha256']
baseline['tables']['audit_events']['keep']+=1
baseline['status']='RECONCILED_BASELINE_NOT_OPERATIONAL_RESET_AUTHORIZATION'
baseline['commit_authorized']=False
# Overlay only the exactly proved authentication delta into the disposable clone.
with r.engine.connect() as c:
 with c.begin():
  r.assert_clone(c,r.cfg)
  require(c.execute(text('UPDATE users SET last_login_at=:value WHERE id=:id'),{'value':b['last_login_at'],'id':b['id']}).rowcount==1,'CLONE_USER_UPDATE_FAILED')
  c.execute(text('INSERT INTO audit_events SELECT (json_populate_record(NULL::audit_events,CAST(:row AS json))).*'),{'row':json.dumps(event)})
  require(fingerprint(c,r.cfg['schema'])==actual,'CLONE_BASELINE_NOT_EXACT')
(r.HERE/'reconciled_baseline.json').write_text(json.dumps(baseline,indent=2,default=str))
print(json.dumps(evidence,indent=2,default=str))
