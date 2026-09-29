"""Stage D isolated rehearsal. Never mutates the operational source."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
E = ROOT / 'docs/audits/e10_10_5d_evidence'
DOCKER = ['docker', '--host', 'unix:///Users/julio/.docker/run/docker.sock']
os.environ['DOCKER_HOST'] = DOCKER[2]

def save(name, value):
    (E / name).write_text(json.dumps(value, indent=2, default=str) + '\n')

def run(args, data=None, output=None, sensitive=False):
    p = subprocess.run(args, input=data, stdout=output or subprocess.PIPE, stderr=subprocess.PIPE)
    rec = {'argv':args,'returncode':p.returncode,'stdin_sha256':hashlib.sha256(data).hexdigest() if data else None}
    if not sensitive:
        rec['stderr'] = p.stderr.decode()
        if output is None:
            rec['stdout'] = p.stdout.decode()
    with (E/'commands.jsonl').open('a') as f:
        f.write(json.dumps(rec)+'\n')
    if p.returncode:
        raise RuntimeError('COMMAND_FAILED: '+str(p.returncode))
    return p.stdout

def main():
    if (E / "target.json").exists() or (E / "source_backup.json").exists():
        raise SystemExit("Existing evidence: refuse to overwrite or restart blocked D")
    from adoption_v2.core import digest
    from adoption_v2.execute import capture, private_write, apply
    from adoption_v2.preflight import preflight, schema_signature
    from alembic_v2.safety import inspect_isolation
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.string import TextLoader
    private=Path(tempfile.mkdtemp(prefix='e10_10_5d_',dir='/private/tmp'))
    os.chmod(private,0o700)
    save('private_location.json',{'directory':str(private),'sensitive_files':'excluded from repository'})
    origin=json.loads(run(DOCKER+['inspect','capstone_db','--format','{{json .Id}}']))
    backup=private/'source.dump'
    with backup.open('xb') as f:
        os.chmod(backup,0o600)
        run(DOCKER+['exec',origin,'sh','-c','PGOPTIONS="-c default_transaction_read_only=on" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --lock-wait-timeout=5s'],output=f)
    save('source_backup.json',{'container_id':origin,'database':'malaria_experiments','system_identifier':'7668020338728398886','revision_observed_before_dump':'20260922_01','version':'17.9','sha256':hashlib.sha256(backup.read_bytes()).hexdigest(),'bytes':backup.stat().st_size,'path':str(backup),'consistency':'pg_dump single consistent snapshot; no source writes'})
    nonce=str(uuid.uuid4()); name='capstone_v2_isolated_'+nonce.replace('-','')[:12]
    t={'authorized_stage':'E10.10.5D','gate_c_approved':True,'copy_only':True,'writers_fenced':True,'isolation_id':nonce,'container_name':name,'volume':name,'database':name,'host_port':55479,'origin_system_identifier':'7668020338728398886','migration_role':'capstone_v2_migrator','runtime_role':'capstone_v2_runtime'}
    secret=secrets.token_hex(24); envfile=private/'container.env'
    envfile.write_text('POSTGRES_PASSWORD='+secret+'\nPGDATA=/var/lib/postgresql/data\n');os.chmod(envfile,0o600)
    label='org.capstone.pgv2.isolation='+nonce
    run(DOCKER+['image','inspect','postgres:17.9','--format','{{.Id}}'])
    run(DOCKER+['volume','create','--label',label,name])
    t['container_id']=run(DOCKER+['run','-d','--name',name,'--label',label,'--env-file',str(envfile),'-p','127.0.0.1:55479:5432','-v',name+':/var/lib/postgresql/data','postgres:17.9']).decode().strip()
    save('target.json',t)
    for _ in range(40):
        r=subprocess.run(DOCKER+['exec',t['container_id'],'pg_isready','-U','postgres'],capture_output=True)
        if r.returncode==0:break
        time.sleep(1)
    inspect_isolation(t)
    def sql(statement, db='postgres', sensitive=False):
        return run(DOCKER+['exec','-i',t['container_id'],'psql','-X','-U','postgres','-d',db,'-v','ON_ERROR_STOP=1','-At'],statement.encode(),sensitive=sensitive)
    ident=json.loads(sql("SELECT json_build_object('system_identifier',system_identifier::text,'version',current_setting('server_version_num')) FROM pg_control_system();"))
    assert ident['version']=='170009' and ident['system_identifier']!=t['origin_system_identifier']
    save('identity_before_provision.json',ident)
    sql("CREATE ROLE capstone_v2_migrator LOGIN PASSWORD '"+secret+"'; CREATE ROLE capstone_v2_runtime LOGIN PASSWORD '"+secrets.token_hex(24)+"'; CREATE DATABASE "+name+" OWNER capstone_v2_migrator;",sensitive=True)
    # Destination owns extensions and restored objects; source owners/ACL are not imported.
    sql('SET ROLE capstone_v2_migrator; CREATE EXTENSION pgcrypto;',name)
    t['postgres_system_identifier']=ident['system_identifier']
    t['database_oid']=int(sql('SELECT oid FROM pg_database WHERE datname=current_database();',name))
    save('target.json',t)
    with backup.open('rb') as f:
        run(DOCKER+['exec','-i',t['container_id'],'pg_restore','-U','postgres','-d',name,'--role=capstone_v2_migrator','--no-owner','--no-acl','--exit-on-error','--single-transaction'],data=f.read(),sensitive=True)
    isolated=private/'isolated.dump'
    with isolated.open('xb') as f:
        os.chmod(isolated,0o600)
        run(DOCKER+['exec',t['container_id'],'pg_dump','-U','postgres','-d',name,'-Fc'],output=f)
    t['backup_sha256']=hashlib.sha256(isolated.read_bytes()).hexdigest()
    with psycopg.connect(host='127.0.0.1',port=t['host_port'],user=t['migration_role'],password=secret,dbname=name,row_factory=dict_row) as c:
        c.adapters.register_loader('uuid',TextLoader)
        source=capture(c)
        inventory=preflight(source)
        save('reference_inventory.json',inventory)
        private_write(private/'captured_source.json',source)
        t['source_inventory_sha256']=digest(inventory)
        t['legacy_schema_sha256']=digest(schema_signature(source['catalog']))
    bindings={'documents':{},'configurations':{},'evaluations':[],'calibrations':{},'consolidations':[],'xai':[],'xai_excluded':{}}
    t['mapping_sha256']=digest(bindings)
    save('target.json',t)
    archive=private/'apply';archive.mkdir(mode=0o700)
    url=f"postgresql+psycopg://{t['migration_role']}:{secret}@127.0.0.1:{t['host_port']}/{name}"
    result=apply(t,url,bindings,archive,backup_path=isolated)
    save('apply_result.json',result)

if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        # Structural codes only: driver errors may contain row values.
        save('blocker.json',{'type':type(exc).__name__,'code':getattr(exc,'code',None),'location':getattr(exc,'location',None),'sqlstate':getattr(exc,'sqlstate',None),'message':str(exc) if type(exc).__module__ in ('adoption_v2.core','alembic_v2.safety') else 'See private diagnostic; not certified'})
        if (E/'private_location.json').exists():
            loc=json.loads((E/'private_location.json').read_text())['directory']
            path=Path(loc)/'failure.txt';path.write_text(str(exc));os.chmod(path,0o600)
        print('BLOCKED; see public blocker.json and private diagnostic')
        sys.exit(1)
