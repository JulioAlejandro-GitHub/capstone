"""Run software tests in Docker, with no operational DB/storage destination."""
import json
import os
import secrets
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

os.umask(0o077)
PROJECT=Path(__file__).resolve().parents[2]
name='capstone-maintenance-test-'+uuid.uuid4().hex[:10]
report=PROJECT/'var'/'maintenance-tests'/name
report.mkdir(parents=True,mode=0o700)
network=name+'-net'; pg=name+'-pg'; runner=name+'-runner'

def call(args,**kwargs):
    result=subprocess.run(args,check=False,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**kwargs)
    if result.returncode:
        # Test credentials are private too; diagnostic output is written locally.
        (report/'failure.log').write_bytes(result.stderr)
        raise RuntimeError('isolated command failed: '+args[0]+' '+args[1])
    return result.stdout

password=secrets.token_hex(24)
fd,envfile=tempfile.mkstemp(prefix='capstone-maintenance-tests-',suffix='.env')
with os.fdopen(fd,'w') as stream:
    stream.write('POSTGRES_USER=julio\nPOSTGRES_PASSWORD='+password+'\nPOSTGRES_DB=maintenance_fixture\n')
    stream.write('DATABASE_URL=postgresql+psycopg://julio:'+password+'@db:5432/maintenance_fixture\n')
    stream.write('STORAGE_ROOT=/tmp/maintenance-storage\nJWT_SECRET='+secrets.token_hex(32)+'\nMAINTENANCE_ISOLATED=1\nPYTHONDONTWRITEBYTECODE=1\nPYTHONPATH=/maintenance_code:/app:/app/malaria_dl_local_project:/app/malaria_dataset_split_project/src\n')
try:
    call(['docker','network','create','--internal',network])
    call(['docker','run','-d','--name',pg,'--network',network,'--network-alias','db','--env-file',envfile,'postgres:17.9'])
    for i in range(40):
        ready=subprocess.run(['docker','exec',pg,'pg_isready','-U','julio','-d','maintenance_fixture'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if ready.returncode==0: break
        time.sleep(1)
    else: raise RuntimeError('isolated postgres not ready')
    with (PROJECT/'backups/reset3_final/capstone_20260929T001919Z.dump').open('rb') as stream:
        call(['docker','exec','-i',pg,'pg_restore','-U','julio','-d','maintenance_fixture','--exit-on-error','--single-transaction'],stdin=stream)
    image=call(['docker','inspect','--format','{{.Image}}','capstone_backend']).decode().strip()
    mounts=[]
    for src,dst in ((PROJECT,'/maintenance_code'),(PROJECT/'backend_api/app','/app/app'),(PROJECT/'alembic','/app/alembic'),(PROJECT/'alembic.ini','/app/alembic.ini'),(PROJECT/'malaria_dl_local_project','/app/malaria_dl_local_project'),(PROJECT/'malaria_dataset_split_project/src','/app/malaria_dataset_split_project/src')):
        mounts+=['--mount',f'type=bind,src={src},dst={dst},readonly']
    call(['docker','run','-d','--name',runner,'--network',network,'--user','root','--env-file',envfile,*mounts,
          '--mount',f'type=bind,src={report},dst=/maintenance_report','--entrypoint','sleep',image,'infinity'])
    call(['docker','exec',runner,'python','-m','alembic','upgrade','20260922_01'])
    # Real dump of the fixture, restored into the backup-verification destination.
    backup=report/'fixture.dump'
    with backup.open('wb') as stream:
        result=subprocess.run(['docker','exec',pg,'pg_dump','-U','julio','-d','maintenance_fixture','-Fc'],stdout=stream,stderr=subprocess.PIPE)
        assert result.returncode==0
    call(['docker','exec',pg,'createdb','-U','julio','capstone_m3_aaaaaaaaaaaa_restore'])
    with backup.open('rb') as stream:
        call(['docker','exec','-i',pg,'pg_restore','-U','julio','-d','capstone_m3_aaaaaaaaaaaa_restore','--exit-on-error','--single-transaction'],stdin=stream)
    test=subprocess.run(['docker','exec',runner,'python','-m','pytest','-q','-p','no:cacheprovider','/maintenance_code/tests/maintenance',
                         '--junitxml=/maintenance_report/junit.xml'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (report/'pytest.log').write_bytes(test.stdout)
    print(test.stdout.decode())
    print('Isolated evidence: '+str(report))
    raise SystemExit(test.returncode)
finally:
    Path(envfile).unlink(missing_ok=True)
    # Only freshly generated exact fixture names, never operational resources.
    for container in (runner,pg):
        subprocess.run(['docker','rm','-fv',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run(['docker','network','rm',network],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
