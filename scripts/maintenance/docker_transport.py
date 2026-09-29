"""Canonical Compose transport. SQL and application dependencies stay in Docker."""
import json
import os
import re
import select
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit, unquote

from scripts.maintenance.verification import require, write_json, digest, filesystem_fingerprint, protected_link_targets
from scripts.maintenance.protected_resources import PROTECTED_PATHS
from scripts.reset.reset3.artifact_plan import ROOTS


def reject_workers(commands):
    pattern = re.compile(r'(malaria_dl\.(train|campaign|campaign_cli|cli|local_execution\.agent)|scripts/(train|run_campaign|run_local_agent)\.py|run_campaign\.py|local_execution_agent|train\.py)(\s|$)')
    require(not any(pattern.search(c) for c in commands), 'ACTIVE_TRAIN_PROCESS')


class DockerTransport:
    def __init__(self, project, report):
        self.project, self.report = Path(project), Path(report)
        self.lease = None
        self.stopped = []
        self.secret = None
        self.helper = 'capstone-maintenance-' + report.name.lower().replace('_', '-')
        self.file_roots = []
        self.volume_roots = []
        self.extra_mounts = []
        self.internal_roots = []
        self.protected = [str(self.project / p) for p in PROTECTED_PATHS]

    def command(self, args, *, data=None, output=None, input_file=None):
        result = subprocess.run(args, cwd=self.project, input=data,
                                stdin=input_file, stdout=output or subprocess.PIPE,
                                stderr=subprocess.PIPE)
        require(result.returncode == 0, 'DOCKER_COMMAND_FAILED:' + args[1])
        return result.stdout

    def json_command(self, args):
        return json.loads(self.command(args))

    def inspect_container(self, name):
        return self.json_command(['docker', 'inspect', name])[0]

    def discover(self):
        config = self.json_command(['docker', 'compose', 'config', '--format', 'json'])
        def service(name):
            ids = self.command(['docker', 'compose', 'ps', '-aq', name]).decode().split()
            require(len(ids) == 1, 'CANONICAL_CONTAINER_REQUIRED:' + name)
            return self.inspect_container(ids[0])
        self.db, self.backend, self.frontend = (service(s) for s in ('db','backend','frontend'))
        require(self.db['State']['Running'], 'POSTGRES_NOT_RUNNING')
        env = dict(item.split('=',1) for item in self.backend['Config']['Env'])
        configured = config['services']['backend']['environment']['DATABASE_URL']
        require(env['DATABASE_URL'] == configured, 'STALE_CANONICAL_CONFIGURATION')
        parsed = urlsplit(configured.replace('postgresql+psycopg://','postgresql://',1))
        self.database, self.user = unquote(parsed.path[1:]), unquote(parsed.username or '')
        require(parsed.hostname == 'db' and parsed.port == 5432 and not parsed.query, 'NONCANONICAL_POSTGRES')
        require(all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', v) for v in (self.database,self.user)), 'INVALID_SQL_IDENTITY')
        dbenv = dict(item.split('=',1) for item in self.db['Config']['Env'])
        require(dbenv['POSTGRES_DB'] == self.database and dbenv['POSTGRES_USER'] == self.user, 'POSTGRES_CONFIGURATION_MISMATCH')
        raw = self.command(['docker','exec',self.db['Id'],'psql','-X','-U',self.user,'-d',self.database,'-Atc',
            "SELECT json_build_object('database',current_database(),'user',session_user,'cluster',(SELECT system_identifier::text FROM pg_control_system()))"])
        self.identity = json.loads(raw)
        write_json(self.report/'identity.json', self.identity)
        networks = set(self.backend['NetworkSettings']['Networks']) & set(self.db['NetworkSettings']['Networks'])
        require(len(networks) == 1, 'AMBIGUOUS_DOCKER_NETWORK')
        self.network = networks.pop()
        reject_workers(self.command(['ps','-axo','command=']).decode().splitlines())
        ids = self.command(['docker','ps','-q']).decode().split()
        for identifier in ids:
            c = self.inspect_container(identifier)
            if c['Id'] in (self.backend['Id'],self.frontend['Id'],self.db['Id']):
                continue
            reject_workers([' '.join(c['Config'].get('Cmd') or [])])
            require(self.network not in c['NetworkSettings']['Networks'], 'UNMANAGED_NETWORK_WRITER')
        self.protected += protected_link_targets([self.project/'malaria_dl_local_project/data',self.project/'malaria_dataset_split_project'])
        self.map_storage()
        env['PYTHONPATH'] = '/maintenance_code:/app/malaria_dataset_split_project/src:/app/malaria_dl_local_project:/app'
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        env['SQL_LOGGING'] = 'false'
        fd, name = tempfile.mkstemp(prefix='capstone-maintenance-', suffix='.env')
        self.secret = Path(name)
        with os.fdopen(fd, 'w') as stream:
            for key,value in env.items():
                require('\n' not in value and '\r' not in value, 'MULTILINE_ENV_UNSUPPORTED')
                stream.write(key+'='+value+'\n')
        args = ['docker','run','--rm','-i','--name',self.helper,'--network',self.network,'--user','root',
                '--env-file',name,'--volumes-from',self.backend['Id']+':ro',
                '--mount',f'type=bind,src={self.project},dst=/maintenance_code,readonly',
                '--mount',f'type=bind,src={self.report},dst=/maintenance_report',*self.extra_mounts,
                '--entrypoint','python',self.backend['Image'],'-m','scripts.maintenance.runtime','lease']
        self.lease = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        ready,_,_ = select.select([self.lease.stdout],[],[],45)
        require(ready and json.loads(self.lease.stdout.readline()).get('status') == 'LEASE_READY', 'DATABASE_LEASE_UNAVAILABLE')
        self.secret.unlink()
        self.secret = None

    def map_storage(self):
        mounts = sorted(self.backend['Mounts'], key=lambda m:len(m['Destination']), reverse=True)
        pg_sources = {m['Source'] for m in self.db['Mounts']}
        pg_names = {m.get('Name') for m in self.db['Mounts'] if m.get('Name')}
        seen_volumes = set()
        for path,category in ROOTS:
            if category == 'staging':  # original uploads; never an experimental deletion root
                continue
            mount = next((m for m in mounts if Path(path).is_relative_to(m['Destination'])),None)
            if mount is None:
                self.internal_roots.append(path)
                continue
            require(mount['Source'] not in pg_sources and mount.get('Name') not in pg_names, 'POSTGRES_VOLUME_PROTECTED')
            relative = Path(path).relative_to(mount['Destination'])
            if mount['Type'] == 'bind':
                physical = Path(mount['Source'])/relative
                require(physical.resolve().is_relative_to(self.project), 'EXTERNAL_BIND_REQUIRES_POLICY')
                self.file_roots.append(dict(path=str(physical),category=category,physical_root='bind:'+str(physical.resolve()), alias=path))
            elif mount['Type'] == 'volume':
                name = mount['Name']
                require(name.endswith('_scientific_storage'), 'UNREVIEWED_VOLUME')
                destination = '/maintenance_volumes/'+name
                if name not in seen_volumes:
                    self.extra_mounts += ['--mount',f'type=volume,src={name},dst={destination}']
                    seen_volumes.add(name)
                self.volume_roots.append(dict(path=str(Path(destination)/relative),category=category,physical_root='volume:'+name+'/'+str(relative),alias=path))
            else:
                require(False,'UNSUPPORTED_MOUNT')
        # Host roots can exist without being exposed in the backend container.
        for relative,category in (('var/artifacts','artifacts'),('backend_api/var/artifacts','artifacts'),
                                  ('malaria_dl_local_project/outputs','ml_outputs'),
                                  ('malaria_dl_local_project/local_execution_artifacts','local_execution')):
            self.file_roots.append(dict(path=str(self.project/relative),category=category,physical_root='bind:'+str(self.project/relative)))

    def rpc(self, action, payload=None):
        require(self.lease is not None and self.lease.poll() is None, 'DATABASE_LEASE_LOST')
        response = subprocess.run(['docker','exec','-i',self.helper,'python','-m','scripts.maintenance.runtime',action],input=json.dumps(payload or {}).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        result = json.loads(response.stdout)
        require(response.returncode == 0, result.get('error','RUNTIME_ERROR'))
        require(result.get('status') != 'ERROR', result.get('error','RUNTIME_ERROR'))
        return result

    def stop_writers(self):
        for c in (self.frontend,self.backend):
            if c['State']['Running']:
                self.command(['docker','stop','--time','30',c['Id']])
                self.stopped.append(c['Id'])
        reject_workers(self.command(['ps','-axo','command=']).decode().splitlines())
        # No clients may remain once the official writers are stopped.
        peers = self.command(['docker','exec',self.db['Id'],'psql','-X','-U',self.user,'-d','postgres','-Atc',
            "SELECT count(*) FROM pg_stat_activity WHERE datname='"+self.database+"' AND backend_type='client backend'"]).decode().strip()
        require(peers == '0','EXTERNAL_DATABASE_CONNECTIONS')

    def inspect(self, artifact_only=False):
        return self.rpc('inspect',{'artifact_only':artifact_only})

    def filesystem_state(self):
        roots = [self.project/p for p in PROTECTED_PATHS if p not in ('var/maintenance','backups','.git')]
        roots += [Path(p) for p in protected_link_targets(roots) if not any(Path(p).is_relative_to(r) for r in roots)]
        host = {str(p):filesystem_fingerprint(p) for p in roots}
        volume = self.rpc('protected_files',{'roots':[str(Path(r['path']).parent/'microscopy-images') for r in self.volume_roots]})
        return {'host':host,'volume':volume}

    def scan(self, source):
        from scripts.maintenance.clean_experiment_artifacts import scan_roots
        owners = set(source['owned_paths'])
        for owner in list(owners):
            if owner.startswith(('outputs/','releases/','local_execution_artifacts/')):
                owners.add('/app/malaria_dl_local_project/'+owner)
            elif owner.startswith('var/'):
                owners.add('/app/'+owner)
        for root in self.file_roots+self.volume_roots:
            for owner in list(owners):
                alias = root.get('alias')
                if alias and Path(owner).is_relative_to(alias):
                    owners.add(str(Path(root['path'])/Path(owner).relative_to(alias)))
        host = scan_roots(self.file_roots,self.protected,owners,source['models'])
        volume = self.rpc('files',dict(operation='scan',roots=self.volume_roots,protected=list({str(Path(r['path']).parent/'microscopy-images') for r in self.volume_roots}),owned_paths=sorted(owners),models=source['models']))
        # A stopped container layer is inspected as a tar stream, never extracted
        # onto the host or silently discarded when the backend is recreated.
        import tarfile
        for root in self.internal_roots:
            proc = subprocess.Popen(['docker','cp',self.backend['Id']+':'+root,'-'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
            try:
                with tarfile.open(fileobj=proc.stdout,mode='r|') as archive:
                    for entry in archive:
                        if entry.isdir() or Path(entry.name).name == '.gitkeep':
                            continue
                        stream = archive.extractfile(entry) if entry.isfile() else None
                        if stream and entry.size == 20 and stream.read() == b'synthetic checkpoint':
                            host['excluded'].append({'path':root+'/'+entry.name,'reason':'VALIDATED_SYNTHETIC_CHECKPOINT'})
                        else:
                            host['issues'].append({'path':root+'/'+entry.name,'reason':'UNMOUNTED_CONTAINER_LAYER_REQUIRES_REVIEW'})
            except tarfile.ReadError:
                # docker cp of an absent directory returns no archive; inspect
                # container changes to distinguish absence from inaccessible data.
                changed = self.command(['docker','diff',self.backend['Id']]).decode().splitlines()
                require(not any(root in line for line in changed),'UNREADABLE_CONTAINER_LAYER')
            finally:
                proc.stdout.close()
                proc.wait()
        return {'host':host,'volume':volume}

    def cleanup_db(self, source):
        import uuid
        token = uuid.uuid4().hex[:12]
        names = dict(restore='capstone_m3_'+token+'_restore',candidate='capstone_m3_'+token+'_new',recovery='capstone_m3_'+token+'_old')
        directory = self.project/'backups'/'maintenance'/self.report.name
        directory.mkdir(parents=True,mode=0o700)
        backup = directory/'source.dump'
        with backup.open('wb') as output:
            os.chmod(backup,0o600)
            self.command(['docker','exec',self.db['Id'],'pg_dump','-U',self.user,'-d',self.database,'--format=custom'],output=output)
            output.flush(); os.fsync(output.fileno())
        require(backup.stat().st_size>0,'EMPTY_BACKUP')
        self.rpc('create_restore',names)
        with backup.open('rb') as stream:
            self.command(['docker','exec','-i',self.db['Id'],'pg_restore','-U',self.user,'-d',names['restore'],'--exit-on-error','--single-transaction'],input_file=stream)
        write_json(self.report/'backup.json',dict(path=str(backup),sha256=digest(backup),bytes=backup.stat().st_size,**names))
        result = self.rpc('rebuild',names)
        result['backup'] = json.loads((self.report/'backup.json').read_text())
        result['backup']['restore_verified'] = True
        return result

    def delete_files(self, manifest):
        from scripts.maintenance.clean_experiment_artifacts import delete_manifest
        # Revalidate frozen paths against today's canonical mapping, including
        # after a PARTIAL restart. A saved manifest cannot expand deletion scope.
        for name,roots in (('host',self.file_roots),('volume',self.volume_roots)):
            approved = {str(Path(r['path']).resolve()) for r in roots}
            for row in manifest[name]['files']:
                require(row['root'] in approved,'MANIFEST_ROOT_NOT_APPROVED')
                if name == 'host':
                    require(not any(Path(row['path']).resolve().is_relative_to(p) for p in self.protected),'PROTECTED_PATH')
        host = delete_manifest(manifest['host'],self.report/'host_journal.jsonl')
        volume = self.rpc('files',dict(operation='delete',manifest=manifest['volume']))
        return {'status':'COMPLETED' if host['deleted_files']+volume['deleted_files'] else 'NO_ARTIFACTS_FOUND','host':host,'volume':volume}

    def restart(self):
        for identifier in reversed(self.stopped):
            self.command(['docker','start',identifier])
        # Verify HTTP without authentication/login writes.
        if self.backend['Id'] in self.stopped:
            code = "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready',timeout=5).read()"
            for attempt in range(30):
                r = subprocess.run(['docker','exec',self.backend['Id'],'python','-c',code],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                if r.returncode == 0:
                    break
                time.sleep(1)
            else:
                require(False,'BACKEND_HEALTH_FAILED')
        if self.frontend['Id'] in self.stopped:
            for attempt in range(45):
                try:
                    self.rpc('frontend_ready')
                    break
                except Exception:
                    time.sleep(1)
            else:
                require(False,'FRONTEND_HEALTH_FAILED')
        self.stopped.clear()

    def close(self):
        if self.secret:
            self.secret.unlink(missing_ok=True)
        if self.lease:
            self.lease.stdin.close()
            try:
                self.lease.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.command(['docker','stop','--time','5',self.helper])
