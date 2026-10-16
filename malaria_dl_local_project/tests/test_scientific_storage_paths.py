"""Portable binary locations preserve identity and reject ungoverned remapping."""
from uuid import uuid4
import pytest
from src.malaria_dl.execution import storage_paths
from src.malaria_dl.execution.artifacts import file_identity


def test_historical_checkpoint_same_bytes_and_no_database_rewrite(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_paths, 'PROJECT_ROOT', tmp_path)
    suffix = f'outputs/train_runs/{uuid4()}/epoch_2.keras'
    local = tmp_path / suffix; local.parent.mkdir(parents=True); local.write_bytes(b'checkpoint')
    registered = '/absent/Mac/malaria_dl_local_project/' + suffix
    assert storage_paths.local_scientific_path(registered) == local
    assert file_identity(registered) == file_identity(local)
    assert registered.startswith('/absent/Mac/')


def test_assessment_same_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_paths, 'PROJECT_ROOT', tmp_path)
    suffix = f'artifacts/assessments/{uuid4()}/{uuid4()}.png'
    local = tmp_path / suffix; local.parent.mkdir(parents=True); local.write_bytes(b'image')
    assert file_identity('/absent/malaria_dl_local_project/' + suffix) == file_identity(local)


@pytest.mark.parametrize('suffix', ['outputs/train_runs/../secret', 'outputs/train_runs/not-a-uuid/image', 'artifacts/assessments/../secret'])
def test_invalid_scientific_locations(suffix):
    with pytest.raises(ValueError): storage_paths.local_scientific_path('/absent/malaria_dl_local_project/' + suffix)


def test_unrelated_path_not_relocated(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_paths, 'PROJECT_ROOT', tmp_path)
    source = '/absent/malaria_dl_local_project/secrets/config'
    assert str(storage_paths.local_scientific_path(source)) == source


def test_relocation_rejects_symlinked_run_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_paths, 'PROJECT_ROOT', tmp_path)
    tree=tmp_path/'outputs/train_runs';tree.mkdir(parents=True)
    foreign=tmp_path/'foreign';foreign.mkdir();(foreign/'checkpoint.keras').write_bytes(b'foreign')
    run=str(uuid4());(tree/run).symlink_to(foreign, target_is_directory=True)
    with pytest.raises(ValueError, match='SCIENTIFIC_PATH_INVALID'):
        storage_paths.local_scientific_path(f'/absent/malaria_dl_local_project/outputs/train_runs/{run}/checkpoint.keras')


def test_dead_zombie_owner_does_not_hide_live_descendants(monkeypatch):
    from src.malaria_dl.execution import global_gate as gate
    identity={'host':'h','boot_id':'b','pid':123,'start_ticks':'1'}
    monkeypatch.setattr(gate,'host_identity',lambda:{'host':'h','boot_id':'b'})
    table={123:{'pid':123,'ppid':1,'session':123,'state':'Z','start_ticks':'1'}}
    monkeypatch.setattr(gate,'process_table',lambda:table)
    evidence={'identities':[identity],'sessions':[123],'release_confirmed':False}
    gate.verify_retained_processes(evidence)
    table[124]={'pid':124,'ppid':1,'session':123,'state':'R','start_ticks':'2'}
    with pytest.raises(ValueError,match='DESCENDANTS_STILL_ALIVE'):
        gate.verify_retained_processes(evidence)
