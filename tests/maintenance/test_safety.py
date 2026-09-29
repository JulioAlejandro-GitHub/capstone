import copy
import json
from pathlib import Path

import pytest
from scripts.maintenance.clean_experiment_artifacts import scan_roots, delete_manifest
from scripts.maintenance.docker_transport import DockerTransport, reject_workers
from scripts.maintenance.orchestrator import execute
from scripts.maintenance.protected_resources import HISTORY_TABLES, PROTECTED_TABLES, EXPECTED_TABLES
from scripts.maintenance.verification import MaintenanceError, write_json


def fixture_files(tmp_path):
    root=tmp_path/'outputs'
    directory=root/'custom_cnn'
    directory.mkdir(parents=True)
    (directory/'best_model.keras').write_bytes(b'test artifact')
    return root,[dict(path=str(root),category='ml_outputs',physical_root='test')]


def test_files_and_idempotence(tmp_path):
    root,specs=fixture_files(tmp_path)
    protected=tmp_path/'dataset'
    protected.mkdir()
    (protected/'image.npy').write_bytes(b'original scientific data')
    manifest=scan_roots(specs,[str(protected)],[],['custom_cnn'])
    assert not manifest['issues'] and len(manifest['files'])==1
    result=delete_manifest(manifest,tmp_path/'journal.jsonl')
    assert result['deleted_files']==1 and result['deleted_bytes']==13
    assert delete_manifest(manifest,tmp_path/'journal.jsonl')['already_missing']==1
    assert not scan_roots(specs,[],[],['custom_cnn'])['files']
    assert (protected/'image.npy').read_bytes()==b'original scientific data'


def test_extension_does_not_authorize_and_symlinks(tmp_path):
    root,specs=fixture_files(tmp_path)
    (root/'unowned.npy').write_bytes(b'dataset?')
    (root/'custom_cnn'/'link.keras').symlink_to(root/'unowned.npy')
    value=scan_roots(specs,[],[],['custom_cnn'])
    assert {i['reason'] for i in value['issues']}=={'UNATTRIBUTED_FILE','SYMLINK_EXCLUDED'}


def test_changed_file_prevents_all_deletion(tmp_path):
    root,specs=fixture_files(tmp_path)
    manifest=scan_roots(specs,[],[],['custom_cnn'])
    file=root/'custom_cnn'/'best_model.keras'
    file.write_bytes(b'changed')
    with pytest.raises(MaintenanceError):
        delete_manifest(manifest,tmp_path/'journal')
    assert file.exists()


def test_dataset_cannot_be_a_cleanup_root(tmp_path):
    root,specs=fixture_files(tmp_path)
    value=scan_roots(specs,[str(root)],[],['custom_cnn'])
    assert not value['files'] and value['issues'][0]['reason']=='PROTECTED_ROOT'


def test_postgres_volume_rejected(tmp_path):
    t=DockerTransport(tmp_path,tmp_path/'report')
    mount={'Type':'volume','Source':'/pg','Name':'pg','Destination':'/app/malaria_dl_local_project'}
    t.backend={'Mounts':[mount]};t.db={'Mounts':[mount]}
    with pytest.raises(MaintenanceError,match='POSTGRES_VOLUME_PROTECTED'):
        t.map_storage()


def test_train_process_rejected():
    with pytest.raises(MaintenanceError,match='ACTIVE_TRAIN_PROCESS'):
        reject_workers(['python -m malaria_dl.train --config experiment.yml'])
    reject_workers(['python -m scripts.maintenance.clean_all_experiments'])


class FakeTransport:
    """Explicit orchestration double. SQL behavior is separately integration-tested."""
    def __init__(self, report, history=True, db_error=False, file_error=False):
        self.report=report;self.db_error=db_error;self.file_error=file_error
        self.deletions=0;self.rebuilds=0;self.restarts=0
        self.source={'identity':{'database':'fixture','cluster':'isolated'},'snapshot':{'schemas':{'public':{t:{'count':int(history),'sha256':'test'} for t in HISTORY_TABLES}}}}
    def discover(self): pass
    def inspect(self,**kwargs): return copy.deepcopy(self.source)
    def stop_writers(self): pass
    def filesystem_state(self): return {'protected':'unchanged'}
    def scan(self,source): return {k:{'files':[],'issues':[],'excluded':[]} for k in ('host','volume')}
    def cleanup_db(self,source):
        self.rebuilds+=1
        if self.db_error: raise MaintenanceError('INJECTED_SQL_ERROR')
        for value in self.source['snapshot']['schemas']['public'].values(): value['count']=0
        return {'status':'COMPLETED','deleted_records':77}
    def rpc(self,action): return {'protected_tables_equal':list(PROTECTED_TABLES)}
    def delete_files(self,manifest):
        self.deletions+=1
        if self.file_error: raise MaintenanceError('INJECTED_UNLINK_ERROR')
        return {'status':'NO_ARTIFACTS_FOUND'}
    def restart(self): self.restarts+=1
    def close(self): pass


def test_combined_db_error_never_deletes(tmp_path):
    t=FakeTransport(tmp_path,db_error=True)
    assert execute('all',t,tmp_path)==2
    assert t.deletions==0
    assert json.loads((tmp_path/'summary.json').read_text())['status']=='ERROR'


def test_partial_resume_skips_database(tmp_path):
    first=tmp_path/'first';first.mkdir()
    t=FakeTransport(first,file_error=True)
    assert execute('all',t,first)==2
    assert json.loads((first/'summary.json').read_text())['status']=='PARTIAL'
    second=tmp_path/'second';second.mkdir()
    t.file_error=False
    assert execute('all',t,second,first)==0
    assert t.rebuilds==1 and t.deletions==2


@pytest.mark.parametrize('mode,status',[('db','ALREADY_CLEAN'),('all','ALREADY_CLEAN'),('artifacts','NO_ARTIFACTS_FOUND')])
def test_already_clean_exit_codes(tmp_path,mode,status):
    t=FakeTransport(tmp_path,history=False)
    assert execute(mode,t,tmp_path)==0
    assert t.rebuilds==0
    assert json.loads((tmp_path/'summary.json').read_text())['status']==status


def test_policy_exhaustive_and_disjoint():
    assert len(EXPECTED_TABLES)==97
    assert not set(PROTECTED_TABLES)&set(HISTORY_TABLES)


def test_scientific_symlink_protects_referent(tmp_path):
    from scripts.maintenance.verification import protected_link_targets
    root,specs=fixture_files(tmp_path)
    dataset=tmp_path/'dataset';dataset.mkdir()
    target=root/'custom_cnn'/'best_model.keras'
    (dataset/'materialized-image').symlink_to(target)
    manifest=scan_roots(specs,protected_link_targets([dataset]),[],['custom_cnn'])
    assert not manifest['files']
    assert target.exists()


def test_resume_rejects_inventory_drift(tmp_path):
    first=tmp_path/'first';first.mkdir()
    t=FakeTransport(first,file_error=True)
    assert execute('all',t,first)==2
    t.source['snapshot']['schemas']['public']['runs']['count']=1
    second=tmp_path/'second';second.mkdir()
    assert execute('all',t,second,first)==2
    assert t.rebuilds==1 and t.deletions==1


@pytest.mark.parametrize('mode',['db','artifacts','all'])
def test_public_entry_exit_codes_without_operational_targets(tmp_path,monkeypatch,mode):
    import scripts.maintenance.orchestrator as module
    import scripts.maintenance.docker_transport as docker
    monkeypatch.setattr(module,'__file__',str(tmp_path/'scripts/maintenance/orchestrator.py'))
    monkeypatch.setattr(module.sys,'argv',['maintenance'])
    monkeypatch.setattr(docker,'DockerTransport',lambda project,report:FakeTransport(report,history=False))
    assert module.main(mode)==0
    assert module.main(mode)==0  # Immediate repeat also gets its own report.
    # Reentrant host lock is denied, without constructing a Docker transport.
    import fcntl
    with (tmp_path/'var/maintenance/.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert module.main(mode)==2


def test_official_release_contract(tmp_path):
    from scripts.maintenance.protected_resources import RELEASE_NAMES
    import hashlib
    root=tmp_path/'releases'
    identifier='12345678-1234-1234-1234-123456789abc'
    release=root/'custom_cnn'/identifier
    release.mkdir(parents=True)
    for name in RELEASE_NAMES:
        (release/name).write_bytes(b'release fixture')
    (release/'manifest.json').write_text(json.dumps({'model_version_id':identifier,
        'training_run_id':'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'sha256':hashlib.sha256(b'release fixture').hexdigest()}))
    specifications=[dict(path=str(root),category='releases',physical_root='fixture')]
    manifest=scan_roots(specifications,[],[],['custom_cnn'])
    assert not manifest['issues']
    assert len(manifest['files'])==len(RELEASE_NAMES)
    assert delete_manifest(manifest,tmp_path/'journal.jsonl')['deleted_files']==len(RELEASE_NAMES)
    assert not scan_roots(specifications,[],[],['custom_cnn'])['files']


def test_standalone_artifacts_uses_current_baseline_after_later_data(tmp_path):
    first=tmp_path/'database';first.mkdir()
    t=FakeTransport(first)
    assert execute('db',t,first)==0
    # A legitimate later event must not make an old DB report a permanent gate.
    t.source['snapshot']['schemas']['public']['audit_events']['count']=1
    second=tmp_path/'artifacts';second.mkdir()
    assert execute('artifacts',t,second,first)==0
    assert t.rebuilds==1 and t.deletions==1
    assert t.source['snapshot']['schemas']['public']['audit_events']['count']==1
