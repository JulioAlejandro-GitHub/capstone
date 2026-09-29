#!/usr/bin/env python3
"""Human-run secure login check against the LOOPBACK ISOLATED API only.

Password and access token remain in memory, never in argv, shell history or the
report. Does not reset a password or connect to operational port 8000.
"""
import getpass,json,os,sys,urllib.request,subprocess
from datetime import datetime,timezone
from pathlib import Path
BASE='http://127.0.0.1:18003'
try:
 if not sys.stdin.isatty():raise RuntimeError('INTERACTIVE_TERMINAL_REQUIRED')
 config=json.loads(Path('/private/tmp/reset3_run/api.json').read_text())
 info=json.loads(subprocess.check_output(['docker','inspect',config['container']],stderr=subprocess.DEVNULL))[0]
 assert config['container'].startswith('capstone-reset3-') and info['Config']['Labels']['capstone.task']=='RESET.3' and info['State']['Running']
 assert list(info['NetworkSettings']['Networks'])==[config['network']]
 password=getpass.getpass('Contraseña actual del administrador (no se guarda): ')
 data=json.dumps({'username':'admin','password':password}).encode()
 request=urllib.request.Request(BASE+'/api/v1/auth/login',data=data,headers={'Content-Type':'application/json'},method='POST')
 with urllib.request.urlopen(request,timeout=30) as response:token=json.load(response)['access_token']
 del password,data,request
 request=urllib.request.Request(BASE+'/api/v1/auth/me',headers={'Authorization':'Bearer '+token})
 with urllib.request.urlopen(request,timeout=30) as response:me=json.load(response)
 del token,request
 assert me['id']=='9fdddd0f-e485-4c18-b75d-df3869917f41' and me['username']=='admin' and 'administrator' in me['roles'] and me['permissions']
 evidence={'at':datetime.now(timezone.utc).isoformat(),'isolated_api':BASE,'login_status':200,'me_status':200,'user':me,'password_saved':False,'token_saved':False}
 p=Path('/private/tmp/reset3_run/login.json');fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(evidence,f,indent=2)
 print('Login real en candidato aislado validado; evidencia guardada sin contraseña ni token.')
except Exception as e:
 print('Validación no aprobada:',type(e).__name__,file=sys.stderr);raise SystemExit(2)
