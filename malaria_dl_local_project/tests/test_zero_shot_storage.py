"""Offline storage contracts; never writes to PostgreSQL or scientific roots."""
import hashlib
from pathlib import Path
import pytest
from src.malaria_dl.pretrained.registration import verified_file, resolve_dependencies, register_external_model


def evidence(path, role='model_config'):
    return dict(role=role, path=str(path), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def test_registered_location_overrides_stale_cache_path(tmp_path):
    path = tmp_path / 'config.json'
    path.write_bytes(b'{}')
    item = evidence(path)
    frozen = {**item, 'path': '/missing/old/cache/config.json'}
    artifact = {**item, 'artifact_id': 'artifact-id', 'status': 'available'}
    result = resolve_dependencies({'dependencies': [frozen]}, [artifact], Path)
    assert result['dependencies'][0]['path'] == str(path)
    assert result['dependencies'][0]['artifact_id'] == 'artifact-id'
    assert frozen['path'] == '/missing/old/cache/config.json'


@pytest.mark.parametrize('problem', ['missing', 'duplicate', 'checksum', 'unavailable', 'changed', 'identity'])
def test_dependency_conflicts_fail_closed(tmp_path, problem):
    path = tmp_path / 'config.json'
    path.write_bytes(b'{}')
    item = evidence(path)
    records = [{**item, 'artifact_id': 'one', 'status': 'available'}]
    if problem == 'missing': records = []
    if problem == 'duplicate': records *= 2
    if problem == 'checksum': records[0]['sha256'] = '0' * 64
    if problem == 'unavailable': records[0]['status'] = 'archived'
    if problem == 'changed': path.write_bytes(b'changed')
    if problem == 'identity': item['artifact_id'] = 'other'
    with pytest.raises(ValueError):
        resolve_dependencies({'dependencies': [item]}, records, Path)


def test_symlink_is_not_a_registered_binary(tmp_path):
    path = tmp_path / 'actual'
    path.write_bytes(b'x')
    link = tmp_path / 'link'
    link.symlink_to(path)
    with pytest.raises(ValueError, match='Symlink'):
        verified_file(evidence(link))


def test_missing_binary_fails(tmp_path):
    with pytest.raises(FileNotFoundError):
        verified_file(dict(path=str(tmp_path / 'missing'), sha256='0'*64, bytes=1))


def test_duplicate_roles_rejected_before_database(tmp_path):
    path = tmp_path / 'checkpoint'
    path.write_bytes(b'weights')
    item = evidence(path)
    with pytest.raises(ValueError, match='Duplicate'):
        register_external_model(dict(metadata={'training_mode':'logical',
            'scientific_origin':{'kind':'pretrained_external'}},
            files=[{**item, 'role':'checkpoint'}, item, item]))


def test_incorporation_uses_shared_tree_and_preserves_sources(tmp_path, monkeypatch):
    from uuid import uuid4
    from src.malaria_dl.execution import storage_paths
    monkeypatch.setattr(storage_paths, 'PROJECT_ROOT', tmp_path / 'project')
    source = tmp_path / 'external'
    (source / 'text').mkdir(parents=True)
    (source / 'weights.bin').write_bytes(b'weights')
    (source / 'text' / 'config.json').write_bytes(b'{}')
    files = [evidence(source / 'weights.bin', 'checkpoint'), evidence(source / 'text' / 'config.json')]
    run_id = str(uuid4())
    copied = storage_paths.incorporate_training_files(run_id, files)
    root = tmp_path / 'project' / 'outputs' / 'train_runs' / run_id
    assert [Path(item['path']).relative_to(root).as_posix() for item in copied] == ['weights.bin', 'text/config.json']
    assert [item['sha256'] for item in files] == [item['sha256'] for item in copied]
    assert all(Path(item['path']).exists() for item in files)
    with pytest.raises(FileExistsError):
        storage_paths.incorporate_training_files(run_id, files)


def test_repeat_registration_reuses_identity_and_copied_artifacts(tmp_path, monkeypatch):
    """Exercise the writer twice through mocked repositories, without a database."""
    from contextlib import contextmanager
    from types import SimpleNamespace
    from uuid import uuid4
    from src.malaria_dl.pretrained import registration as module
    from src.malaria_dl.execution import storage_paths
    monkeypatch.setattr(storage_paths, 'PROJECT_ROOT', tmp_path / 'project')
    path = tmp_path / 'weights.bin'
    path.write_bytes(b'weights')
    spec = dict(name='generic_external', model_type='zero_shot', framework='keras', architecture='generic',
                metadata={'training_mode':'logical','scientific_origin':{'kind':'pretrained_external','repo_id':'example/model'}},
                files=[evidence(path, 'checkpoint')], preprocessing={'mode':'rescale_0_1'},
                input_signature={'shape':[None,8,8,3]}, output_signature={'shape':[None,1]},
                class_mapping={'0':'uninfected','1':'parasitized'})
    state = {'artifacts': [], 'version': None, 'starts': 0}
    class Result:
        def __init__(self, value): self.value = value
        def mappings(self): return self
        def one(self): return self.value
        def all(self): return self.value
        def first(self): return self.value
        def scalar_one(self): return self.value
    class Connection:
        def execute(self, statement, params):
            sql = str(statement)
            if 'SELECT * FROM models' in sql: return Result(spec)
            if 'SELECT mv.*' in sql: return Result([state['version']] if state['version'] else [])
            if 'SELECT id FROM runs' in sql: return Result(None)
            if 'MAX(version_number)' in sql: return Result(1)
            if 'SELECT artifact_type' in sql: return Result(state['artifacts'])
            assert 'pg_advisory_xact_lock' in sql
            return Result(None)
    @contextmanager
    def connection(): yield Connection()
    monkeypatch.setattr(module, 'get_connection', connection)
    monkeypatch.setattr(module.runs, 'get_or_create_model', lambda **kw: 'model-id')
    def start(**kwargs):
        assert kwargs['run_type'] == 'training' and kwargs['total_epochs'] == 0
        assert kwargs['metadata']['training_performed'] is False
        state['starts'] += 1
        return str(uuid4())
    monkeypatch.setattr(module.runs, 'start_run', start)
    def artifact(run, kind, path, **kwargs):
        assert '/outputs/train_runs/' in path
        state['artifacts'].append(dict(artifact_type=kind, path=path, checksum=kwargs['checksum'],
            file_size_bytes=kwargs['file_size_bytes'], artifact_status='available', metadata=kwargs['metadata']))
        return 'artifact-id'
    monkeypatch.setattr(module.runs, 'log_artifact', artifact)
    def version(**kwargs):
        state['version'] = dict(kwargs, id='version-id', run_status='completed')
        return SimpleNamespace(id='version-id')
    monkeypatch.setattr(module, 'create_model_version', version)
    monkeypatch.setattr(module.runs, 'finish_run', lambda *a, **kw: True)
    first = module.register_external_model(spec)
    second = module.register_external_model(spec)
    assert second == {**first, 'idempotent': True}
    assert state['starts'] == 1 and len(state['artifacts']) == 1
    spec['class_mapping'] = {'0':'parasitized','1':'uninfected'}
    with pytest.raises(ValueError, match='conflicts'):
        module.register_external_model(spec)

    spec['class_mapping'] = {'0':'uninfected','1':'parasitized'}
    Path(state['artifacts'][0]['path']).write_bytes(b'corrupted')
    with pytest.raises(ValueError, match='identity mismatch'):
        module.register_external_model(spec)
