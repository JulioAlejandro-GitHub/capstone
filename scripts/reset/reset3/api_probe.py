"""Read-only HTTP authentication/smoke check; never invokes password login."""
import json,os,urllib.request,urllib.error
from sqlalchemy import text
from app.db import get_primary_engine
from app.security import create_access_token,ROLE_PERMISSIONS,Permission
from app.config import get_settings
settings=get_settings()
expected=os.environ.get('RESET3_EXPECT_DATABASE','reset3_candidate')
assert expected in ('reset3_candidate','malaria_experiments')
assert settings.auth_mode=='local_jwt' and settings.database_url.endswith('/'+expected)
with get_primary_engine().connect().execution_options(postgresql_readonly=True) as c:
 user=c.execute(text("SELECT id,username,status FROM users WHERE username='admin'")).mappings().one()
 roles=c.execute(text('SELECT r.name FROM roles r JOIN user_roles ur ON ur.role_id=r.id WHERE ur.user_id=:id ORDER BY r.name'),{'id':user['id']}).scalars().all()
 assert user['status']=='active' and 'administrator' in roles
 token=create_access_token(user['id'],user['username'],roles)
def get(path,authenticated=False):
 req=urllib.request.Request('http://127.0.0.1:8000'+path,headers={'Authorization':'Bearer '+token} if authenticated else {})
 try:
  with urllib.request.urlopen(req,timeout=30) as r:return r.status,json.load(r)
 except urllib.error.HTTPError as e:return e.code,None
r={'mode':'official JWT generated in memory; password login NOT exercised','credentials_modified':False,'roles':roles}
for path in ['/health','/ready']:
 status,body=get(path);assert status==200,(path,status);r[path]=body
status,me=get('/api/v1/auth/me',True);assert status==200 and me['id']==str(user['id']) and me['username']==user['username'] and sorted(me['roles'])==sorted(roles) and not me['insecure_local'];r['authenticated_me']={'status':status,'identity_equal':True,'roles_equal':True,'permissions_count':len(me['permissions'])}
status,_=get('/api/v1/auth/me');assert status==401;r['unauthenticated_status']=status
status,spec=get('/openapi.json');assert status==200
r['available_read_routes']=[p for p,v in spec['paths'].items() if 'get' in v and any(k in p for k in ['dataset','experiment','campaign','publication','deployment'])]
r['read_endpoints']={}
for path in ['/api/datasets','/api/datasets/d8c0cab5-09dd-597f-9de7-7ca01aee2ec2','/api/dataset/summary','/api/dataset/split','/api/deployments']:
 status,body=get(path,True)
 r['read_endpoints'][path]={'status':status,'body':body}
 assert status==200,(path,status)
r['result']='PASS_AUTHENTICATED_READ_ONLY_API' 
print(json.dumps(r,indent=2,default=str))
