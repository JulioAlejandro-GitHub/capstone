from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/storage/reset_smear_analysis.py"
SPEC = importlib.util.spec_from_file_location("reset_smear_analysis", SCRIPT)
reset = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = reset
SPEC.loader.exec_module(reset)


@pytest.mark.parametrize("key", ["/absolute.png", "../escape.png", "microscopy-images/../x"])
def test_rejects_unsafe_storage_keys(key):
    with pytest.raises(reset.ResetRefused):
        reset.namespace_for(key)


def test_rejects_preserved_and_unknown_namespaces():
    for key in ("model-explanations/model/overlay.png", "artifacts/file.bin"):
        with pytest.raises(reset.ResetRefused):
            reset.namespace_for(key)


def test_manifest_entry_is_deterministic_and_complete(tmp_path):
    root = tmp_path / "storage"
    path = root / "cell-crops" / "run" / "crop.png"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"clinical crop")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    item = reset.inspect_file(root, key="cell-crops/run/crop.png", table="cell_crops",
                              row_id="row", expected_size=13, expected_sha256=digest)
    assert item.namespace == "cell-crops"
    assert item.sha256 == digest
    assert item.inode and item.device and item.mtime_ns


def test_manifest_rejects_symlink(tmp_path):
    root = tmp_path / "storage"
    root.mkdir()
    target = tmp_path / "target"
    target.write_bytes(b"x")
    (root / "microscopy-images").symlink_to(target)
    with pytest.raises(reset.ResetRefused, match="symlink"):
        reset.inspect_file(root, key="microscopy-images", table="microscopy_images",
                           row_id="1", expected_size=1,
                           expected_sha256=hashlib.sha256(b"x").hexdigest())


def test_dry_run_is_default_and_execution_needs_exact_confirmation():
    args = reset.parse_args([])
    assert args.execute is False
    assert args.confirmation is None
    assert reset.CONFIRMATION == "RESET MALARIA SMEAR ANALYSIS"

def test_audit_classification_is_exact_and_fail_closed():
    clinical = {"run-1", "image-1"}; keys = {"cell-crops/run-1/crop.png"}
    def event(**changes):
        row = {"id":"e", "resource_type":"run", "resource_id":None, "request_path":None,
               "action":"train", "before_state":None, "after_state":None, "metadata":None}
        row.update(changes); return row
    assert reset.classify_audit_event(event(resource_type="microscopy_analysis_run", resource_id="run-1"), clinical, keys).category == "DELETE_CLINICAL_AUDIT"
    assert reset.classify_audit_event(event(request_path="/api/v1/analysis/runs/x", resource_id="run-1"), clinical, keys).category == "DELETE_CLINICAL_AUDIT"
    assert reset.classify_audit_event(event(metadata={"analysis_run_id":"run-1"}), clinical, keys).category == "DELETE_CLINICAL_AUDIT"
    assert reset.classify_audit_event(event(metadata={"storage_key":"cell-crops/run-1/crop.png"}), clinical, keys).category == "DELETE_CLINICAL_AUDIT"
    assert reset.classify_audit_event(event(action="login", resource_type="authentication"), clinical, keys).category == "PRESERVE_SECURITY_AUDIT"
    assert reset.classify_audit_event(event(resource_type="model_version"), clinical, keys).category == "PRESERVE_EXPERIMENTAL_AUDIT"
    assert reset.classify_audit_event(event(resource_type="unrelated", request_path="/api/v1/analysisx/run-1"), clinical, keys).category == "PRESERVE_UNRELATED_AUDIT"
    assert reset.classify_audit_event(event(resource_type="microscopy_analysis_run", resource_id="other"), clinical, keys).category == "AMBIGUOUS_AUDIT"

@pytest.mark.parametrize("url", [
    "postgresql+psycopg://user:secret@localhost:5432/db",
    "postgresql+psycopg://user:secret@db:5433/db",
    "sqlite:///tmp/test.db",
])
def test_rejects_noncanonical_database_address(url):
    with pytest.raises(reset.ResetRefused):
        reset.validate_url(url)


def test_backup_requires_custom_format_and_read_only_parent(tmp_path, monkeypatch):
    backup = tmp_path / "backup.dump"
    backup.write_bytes(b"not-a-dump" * 200)
    with pytest.raises(reset.ResetRefused, match="custom-format"):
        reset.validate_backup(backup)
    backup.write_bytes(b"PGDMP" + b"x" * 2048)
    monkeypatch.setattr(os, "statvfs", lambda _: type("FS", (), {"f_flag": os.ST_RDONLY})())
    original_access = os.access
    monkeypatch.setattr(os, "access", lambda path, mode: False if mode == os.W_OK else original_access(path, mode))
    monkeypatch.setattr(reset.shutil, "which", lambda _: "/usr/bin/pg_restore")
    monkeypatch.setattr(reset.subprocess, "run", lambda *a, **kw: type("Result", (), {
        "returncode": 0,
        "stdout": "".join(f" TABLE DATA public {table} x\n" for table in ("alembic_version", "users", "runs", "model_versions")),
    })())
    reset.validate_backup(backup)


def test_delete_order_keeps_experimental_predictions_out():
    assert "cell_predictions" in reset.DELETE_ORDER
    assert "predictions" not in reset.DELETE_ORDER
    assert "model_versions" not in reset.DELETE_ORDER
    assert reset.DELETE_ORDER.index("cell_predictions") < reset.DELETE_ORDER.index("cell_classification_runs")
    assert reset.DELETE_ORDER.index("microscopy_images") < reset.DELETE_ORDER.index("smear_slides")


def test_exact_post_commit_file_deletion_and_idempotence(tmp_path):
    root = tmp_path / "storage"
    path = root / "microscopy-images" / "one.jpg"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"image")
    digest = hashlib.sha256(b"image").hexdigest()
    item = reset.inspect_file(root, key="microscopy-images/one.jpg", table="microscopy_images",
                              row_id="1", expected_size=5, expected_sha256=digest)
    assert reset.delete_manifest_files(root, [item]) == (1, [])
    assert not path.exists()
    assert reset.delete_manifest_files(root, []) == (0, [])


def test_dml_failure_rolls_back_and_never_touches_storage(tmp_path, monkeypatch):
    class Tx:
        is_active = True
        committed = False
        rolled_back = False
        def commit(self): self.committed = True; self.is_active = False
        def rollback(self): self.rolled_back = True; self.is_active = False
    class Connection:
        def __init__(self): self.tx = Tx()
        def begin(self): return self.tx
        def execute(self, statement, params=None):
            if str(statement).startswith("DELETE FROM"):
                raise RuntimeError("injected DML failure")
            return type("Result", (), {"rowcount": 0})()
    class Context:
        def __init__(self): self.connection = Connection()
        def __enter__(self): return self.connection
        def __exit__(self, *args): pass
    class Engine:
        def __init__(self): self.context = Context()
        def connect(self): return self.context
    engine = Engine()
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:secret@db:5432/capstone")
    monkeypatch.setattr(reset, "backup_identity", lambda _: {})
    monkeypatch.setattr(reset, "database_snapshot", lambda *args: {})
    monkeypatch.setattr(reset, "validate_identity", lambda *args: None)
    monkeypatch.setattr(reset, "plan", lambda *args: ({}, [], {"users": "same"}, {"ids": [], "counts": {}}, {"productive_train_id": "x", "fingerprint": "x"}))
    monkeypatch.setattr(reset, "admin_fingerprint", lambda *args: "same")
    monkeypatch.setattr(reset, "release_fingerprint", lambda *args: {"productive_train_id": "x", "fingerprint": "x"})
    monkeypatch.setattr(reset, "write_operation_manifest", lambda *args: tmp_path / "manifest.json")
    touched = []
    monkeypatch.setattr(reset, "delete_manifest_files", lambda *args: touched.append(True))
    with pytest.raises(RuntimeError, match="injected"):
        reset.execute_reset(engine, tmp_path, tmp_path / "backup.dump")
    assert engine.context.connection.tx.rolled_back
    assert not engine.context.connection.tx.committed
    assert touched == []

import copy
import json
import socket
import uuid


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://unused:unused@db:5432/unit_test')
    def forbidden(*args, **kwargs):
        raise AssertionError('Network/real engine forbidden in unit suite')
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(reset, 'create_engine', forbidden)


@pytest.fixture
def recovery(tmp_path, monkeypatch):
    root = tmp_path / 'storage'; root.mkdir()
    files = []
    for name in ('a', 'b'):
        path = root / 'cell-crops' / 'run' / name
        path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(name.encode())
        files.append(reset.inspect_file(root, key=f'cell-crops/run/{name}', table='cell_crops',
                                        row_id=name, expected_size=1,
                                        expected_sha256=hashlib.sha256(name.encode()).hexdigest()))
    preserved = root / 'model-explanations' / 'keep'; preserved.parent.mkdir(); preserved.write_bytes(b'keep')
    before = {'database_identity': reset.database_identity(reset.validate_url(os.environ['DATABASE_URL'])),
              'alembic_revision': reset.EXPECTED_HEAD,
              'target_tables': {t: [] for t in reset.DELETE_ORDER},
              'audit_events': [], 'preserved_tables': {t: 'a'*32 for t in reset.PRESERVED_TABLES},
              'admin_fingerprint': 'b'*32,
              'release_fingerprint': {'productive_train_id': str(uuid.uuid4()), 'fingerprint': 'c'*64}}
    before['target_tables']['cell_crops'] = [{'id': x, 'sha256': hashlib.sha256(x.encode()).hexdigest()} for x in ('a', 'b')]
    eid = str(uuid.uuid4()); keep = str(uuid.uuid4())
    before['audit_events'] = sorted([{'id': eid, 'sha256': 'd'*64}, {'id': keep, 'sha256': 'e'*64}], key=lambda r: r['id'])
    audit = {'ids': [eid], 'fingerprints': {eid: 'f'*64}}
    backup = {'path': str(tmp_path / 'backup.dump'), 'size': 2048, 'sha256': '0'*64}
    path = reset.write_operation_manifest(root, files, audit, before, backup)
    payload = reset.read_manifest(path)
    after = copy.deepcopy(before); after['target_tables'] = {t: [] for t in reset.DELETE_ORDER}
    after['audit_events'] = [r for r in before['audit_events'] if r['id'] != eid]
    class Engine:
        statements = []
        state = after
        def connect(self): return self
        def begin(self): return self
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, statement):
            sql = str(statement); self.statements.append(sql)
            assert sql.startswith(('SET ', 'SELECT ', 'LOCK TABLE '))
    engine = Engine()
    monkeypatch.setattr(reset, 'database_snapshot', lambda *a: copy.deepcopy(engine.state))
    monkeypatch.setattr(reset, 'validate_schema', lambda *a: None)
    monkeypatch.setattr(reset, 'detect_active_work', lambda *a: None)
    monkeypatch.setattr(reset, 'validate_preserved_storage_references', lambda *a: None)
    monkeypatch.setattr(reset, 'backup_identity', lambda _: backup)
    def resume(): return reset.resume_cleanup(engine, root, Path(backup['path']), payload['operation_id'])
    return root, path, payload, engine, before, after, resume


def test_manifest_is_atomic_private_and_prepared(recovery):
    _, path, payload, *_ = recovery
    assert reset.validate_manifest(payload) == payload
    assert payload['state'] == 'prepared'
    assert path.stat().st_mode & 0o777 == 0o600
    assert not any(secret in json.dumps(payload) for secret in ('password', 'unused:unused', 'token', 'PGDMP'))


@pytest.mark.parametrize('mutation', [
    lambda p: p.update(manifest_version=3), lambda p: p.update(manifest_version=True),
    lambda p: p.update(operation_id='bad'), lambda p: p.update(state='unknown'),
    lambda p: p.pop('backup'), lambda p: p.update(updated_at='bad'),
    lambda p: p.update(created_at='2026-01-01T00:00:00'),
    lambda p: p['storage_files'][0].update(storage_key='../escape'),
    lambda p: p['storage_files'][0].update(storage_key='/escape'),
    lambda p: p['storage_files'][0].update(namespace='model-explanations'),
    lambda p: p['storage_files'].append(dict(p['storage_files'][0], size=99)),
    lambda p: p['database_before']['database_identity'].update(password='secret'),
    lambda p: p['database_before']['target_tables'].pop('cell_crops'),
    lambda p: p['database_before'].update(alembic_revision='other'),
    lambda p: p['storage_files'][0].update(uid=True),
])
def test_strict_schema(recovery, mutation):
    payload = copy.deepcopy(recovery[2]); mutation(payload)
    with pytest.raises((reset.ResetRefused, ValueError)): reset.validate_manifest(payload)


def test_before_aborts_without_cleanup(recovery):
    root, path, p, engine, before, _, resume = recovery
    engine.state = before; inventory = reset.storage_inventory(root)
    assert resume()['status'] == 'RESET_NOT_COMMITTED_NO_STORAGE_CLEANUP'
    assert reset.read_manifest(path)['state'] == 'aborted_before_commit'
    assert reset.storage_inventory(root) == inventory
    with pytest.raises(reset.ResetRefused): resume()


@pytest.mark.parametrize('field', ['target_tables', 'audit_events', 'preserved_tables', 'admin_fingerprint', 'release_fingerprint', 'alembic_revision', 'database_identity'])
def test_mixed_blocks_without_deletion(recovery, field):
    root, path, p, engine, before, after, resume = recovery
    if field == 'target_tables': engine.state[field]['cell_crops'] = before[field]['cell_crops'][:1]
    elif field == 'audit_events': engine.state[field] = []
    elif field == 'preserved_tables': engine.state[field]['users'] = '0'*32
    elif field == 'release_fingerprint': engine.state[field]['fingerprint'] = '0'*64
    elif field == 'database_identity': engine.state[field]['database'] = 'different'
    else: engine.state[field] = 'different'
    inventory = reset.storage_inventory(root)
    with pytest.raises(reset.ResetRefused, match='DATABASE_STATE_MIXED'): resume()
    assert reset.read_manifest(path)['state'] == 'blocked'
    assert reset.storage_inventory(root) == inventory


def test_after_completes_and_preserves_roots(recovery):
    root, path, p, engine, *_, resume = recovery
    assert resume()['storage_files_deleted'] == 2
    assert not path.exists() and not path.parent.exists()
    assert (root / '.staging').is_dir()
    assert (root / '.staging/smear-reset').is_dir()
    assert (root / 'cell-crops').is_dir()
    assert not (root / 'cell-crops/run').exists()
    assert (root / 'model-explanations/keep').read_bytes() == b'keep'
    with pytest.raises(FileNotFoundError): resume()


def test_partial_cleanup_retries_absent_files_and_preserves_additional(recovery):
    root, path, p, engine, *_, resume = recovery
    modified = root / 'cell-crops/run/b'; original = modified.read_bytes(); info = modified.stat()
    modified.write_bytes(b'changed')
    extra = root / 'cell-crops/run/extra'; extra.write_bytes(b'extra')
    result = resume()
    assert result['storage_files_deleted'] == 1
    assert result['conflicts'] == ['cell-crops/run/b: STORAGE_FILE_CHANGED']
    assert reset.read_manifest(path)['state'] == 'cleanup_pending'
    assert resume()['storage_files_deleted'] == 0
    modified.write_bytes(original); os.utime(modified, ns=(info.st_atime_ns, info.st_mtime_ns))
    result = resume()
    assert result['storage_files_deleted'] == 1
    assert result['additional_files'] == ['cell-crops/run/extra']
    assert extra.read_bytes() == b'extra'


@pytest.mark.parametrize('where', ['file', 'parent', 'manifest', 'staging'])
def test_symlinks_block(recovery, where, tmp_path):
    root, path, p, engine, *_, resume = recovery
    if where == 'file':
        victim = root / 'cell-crops/run/a'; victim.unlink(); victim.symlink_to(root / 'model-explanations/keep')
    elif where == 'parent':
        victim = root / 'cell-crops/run'; victim.rename(root / 'moved'); victim.symlink_to(root / 'moved', target_is_directory=True)
    elif where == 'manifest':
        saved = tmp_path / 'saved'; path.rename(saved); path.symlink_to(saved)
    else:
        victim = root / '.staging'; victim.rename(root / 'saved'); victim.symlink_to(root / 'saved', target_is_directory=True)
    with pytest.raises((OSError, reset.ResetRefused)): resume()
    assert (root / 'model-explanations/keep').read_bytes() == b'keep'


@pytest.mark.parametrize('target_state', ['database_committed', 'cleanup_pending', 'cleanup_completed'])
def test_crash_after_durable_transition(recovery, monkeypatch, target_state):
    root, path, p, engine, *_, resume = recovery
    original = reset.transition
    def crash(path, payload, state):
        result = original(path, payload, state)
        if state == target_state: raise RuntimeError('crash')
        return result
    monkeypatch.setattr(reset, 'transition', crash)
    with pytest.raises(RuntimeError, match='crash'): resume()
    assert reset.read_manifest(path)['state'] == target_state
    monkeypatch.setattr(reset, 'transition', original)
    assert resume()['status'] == 'CLEANUP_COMPLETE'


def test_crash_after_unlink_before_fsync(recovery, monkeypatch):
    root, path, p, engine, *_, resume = recovery
    original = os.unlink
    def crash(name, *args, **kw):
        original(name, *args, **kw)
        if name == 'a': raise RuntimeError('crash')
    monkeypatch.setattr(os, 'unlink', crash)
    with pytest.raises(RuntimeError): resume()
    monkeypatch.setattr(os, 'unlink', original)
    assert resume()['storage_files_deleted'] == 1


def test_fsync_and_atomic_write_failure_preserves_old_manifest(recovery, monkeypatch):
    _, path, p, *_ = recovery
    seen = []; original = os.fsync
    monkeypatch.setattr(os, 'fsync', lambda fd: (seen.append(fd), original(fd))[-1])
    updated = reset.transition(path, p, 'database_committed')
    assert len(seen) >= 2
    monkeypatch.setattr(os, 'replace', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('crash')))
    with pytest.raises(RuntimeError): reset.transition(path, updated, 'cleanup_pending')
    assert reset.read_manifest(path) == updated


@pytest.mark.parametrize('state', sorted(reset.STATES))
def test_transition_matrix(recovery, state):
    _, path, p, *_ = recovery
    p = dict(p, state=state); reset._atomic_manifest(path, p)
    for target in reset.STATES - reset.TRANSITIONS[state]:
        with pytest.raises(reset.ResetRefused): reset.transition(path, p, target)


def test_legacy_rejected_without_conversion(recovery):
    root, path, p, engine, *_, resume = recovery
    legacy = root / '.smear-reset-cleanup-pending.json'; legacy.write_text('[]')
    inventory = reset.storage_inventory(root)
    with pytest.raises(reset.ResetRefused, match='no soportado'): resume()
    assert legacy.read_text() == '[]'
    assert reset.storage_inventory(root) == inventory
    assert reset.read_manifest(path) == p
    assert '.smear-reset-cleanup-pending.json' not in SCRIPT.read_text()


def test_backup_and_database_mismatch_before_connect(recovery, monkeypatch):
    root, path, p, engine, *_, resume = recovery
    monkeypatch.setattr(reset, 'backup_identity', lambda _: dict(p['backup'], sha256='1'*64))
    with pytest.raises(reset.ResetRefused, match='backup diferente'): resume()
    assert engine.statements == []
    monkeypatch.setenv('DATABASE_URL', 'postgresql://unused:unused@db:5432/other')
    with pytest.raises(reset.ResetRefused, match='otra base'): resume()
    assert engine.statements == []


@pytest.mark.parametrize('args', [
    ['--resume-cleanup', '--execute'], ['--resume-cleanup', '--dry-run'],
    ['--manifest', '/tmp/arbitrary'],
])
def test_cli_exclusion_and_no_arbitrary_path(args):
    with pytest.raises(SystemExit): reset.parse_args(args)


@pytest.mark.parametrize('optin,confirmation,operation', [
    ('1', reset.CONFIRMATION, None), ('0', reset.CONFIRMATION, 'valid'),
    ('1', 'wrong', 'valid'),
])
def test_cli_authorization(recovery, monkeypatch, optin, confirmation, operation):
    root, path, p, engine, *_ = recovery
    monkeypatch.setenv('STORAGE_ROOT', str(root)); monkeypatch.setenv('SMEAR_RESET_ALLOW_EXECUTION', optin)
    monkeypatch.setattr(reset, 'create_engine', lambda *a, **k: engine)
    args = ['--resume-cleanup', '--confirmation', confirmation]
    if operation: args += ['--operation-id', p['operation_id']]
    assert reset.main(args) == 2
    assert engine.statements == []


def test_scientific_json_scalars_and_sample_id_guard(monkeypatch):
    assert reset._json_scalars({'nested': [{'sample_id': 'sample'}]}) == {'sample'}
    class Result:
        def mappings(self): return self
        def all(self): return [{'column_name': 'sample_id', 'data_type': 'uuid'}]
        def first(self): return (1,)
    class Connection:
        def execute(self, *a, **k): return Result()
    with pytest.raises(reset.ResetRefused, match='references clinical'):
        reset.validate_scientific_validation(Connection(), {'sample'}, set())

@pytest.mark.parametrize('source,target', [(a, b) for a, bs in reset.TRANSITIONS.items() for b in bs])
def test_every_allowed_transition(recovery, source, target):
    _, path, p, *_ = recovery
    p = dict(p, state=source); reset._atomic_manifest(path, p)
    changed = reset.transition(path, p, target)
    assert changed['state'] == target
    assert {k: v for k, v in p.items() if k not in ('state', 'updated_at')} == {
        k: v for k, v in changed.items() if k not in ('state', 'updated_at')}


@pytest.mark.parametrize('point', ['file_fsync', 'rename', 'directory_fsync', 'reread'])
def test_atomic_crash_points_recover_old_or_new_document(recovery, monkeypatch, point):
    _, path, p, *_ = recovery
    original_fsync = os.fsync; original_replace = os.replace; original_read = reset.read_manifest
    count = 0
    def sync(fd):
        nonlocal count
        count += 1
        if (point == 'file_fsync' and count == 1) or (point == 'directory_fsync' and count == 2):
            raise RuntimeError('crash')
        original_fsync(fd)
    def replace(*a, **k):
        if point == 'rename': raise RuntimeError('crash')
        original_replace(*a, **k)
    def read(path):
        if point == 'reread': raise RuntimeError('crash')
        return original_read(path)
    monkeypatch.setattr(os, 'fsync', sync); monkeypatch.setattr(os, 'replace', replace)
    monkeypatch.setattr(reset, 'read_manifest', read)
    with pytest.raises(RuntimeError): reset._atomic_manifest(path, dict(p, state='database_committed'))
    persisted = original_read(path)
    assert persisted['state'] in ('prepared', 'database_committed')
    assert persisted['storage_files'] == p['storage_files']


def test_same_counts_different_rows_is_mixed(recovery):
    p = recovery[2]; current = copy.deepcopy(p['database_before'])
    current['target_tables']['cell_crops'][0]['sha256'] = '0'*64
    assert reset.database_state(p, current) == 'mixed'


def test_empty_before_after_does_not_infer_commit(recovery):
    p = copy.deepcopy(recovery[2]); before = p['database_before']
    before['target_tables'] = {t: [] for t in reset.DELETE_ORDER}
    before['audit_events'] = []; p['clinical_audit_events'] = {'ids': [], 'fingerprints': {}}
    assert reset.database_state(p, before) == 'before'
    reset.require_after(p, before)  # Explicit durable committed state can safely be empty.


def test_changed_preserved_file_blocks_without_cleanup(recovery):
    root, path, p, engine, *_, resume = recovery
    (root / 'model-explanations/keep').write_bytes(b'changed')
    with pytest.raises(reset.ResetRefused, match='STORAGE_FILE_CHANGED'): resume()
    assert (root / 'cell-crops/run/a').exists()


def test_final_revalidation_failure_keeps_manifest(recovery, monkeypatch):
    root, path, p, engine, *_, resume = recovery
    calls = 0
    def snapshot(*args):
        nonlocal calls
        calls += 1
        state = copy.deepcopy(engine.state)
        if calls > 1: state['admin_fingerprint'] = '0'*32
        return state
    monkeypatch.setattr(reset, 'database_snapshot', snapshot)
    with pytest.raises(reset.ResetRefused, match='DATABASE_STATE_MIXED'): resume()
    assert reset.read_manifest(path)['state'] == 'cleanup_pending'
    monkeypatch.setattr(reset, 'database_snapshot', lambda *a: engine.state)
    assert resume()['storage_files_deleted'] == 0


def test_crash_after_manifest_unlink_does_not_reuse_operation(recovery, monkeypatch):
    root, path, p, engine, *_, resume = recovery
    original = os.unlink
    def unlink(name, *args, **kw):
        original(name, *args, **kw)
        if name == 'manifest.json': raise RuntimeError('crash')
    monkeypatch.setattr(os, 'unlink', unlink)
    with pytest.raises(RuntimeError): resume()
    assert not path.exists()
    extra = root / 'cell-crops/new'; extra.write_bytes(b'new')
    monkeypatch.setattr(os, 'unlink', original)
    with pytest.raises(FileNotFoundError): resume()
    assert extra.read_bytes() == b'new'


def test_duplicate_json_key_rejected(recovery):
    _, path, p, *_ = recovery
    path.write_text(json.dumps(p)[:-1] + ', "state": "cleanup_completed"}')
    with pytest.raises(reset.ResetRefused, match='duplicado'): reset.read_manifest(path)


def test_missing_backup_and_operation_id_without_resume(recovery, monkeypatch):
    root, path, p, engine, *_ = recovery
    with pytest.raises(reset.ResetRefused): reset.validate_backup(None)
    monkeypatch.setenv('STORAGE_ROOT', str(root))
    assert reset.main(['--operation-id', p['operation_id']]) == 2


def test_backup_on_writable_filesystem_is_rejected(tmp_path):
    path = tmp_path / 'dump'; path.write_bytes(b'PGDMP' + b'x'*2048)
    with pytest.raises(reset.ResetRefused, match='solo lectura'): reset.validate_backup(path)


def test_preserved_reference_guard_uses_exact_keys(monkeypatch):
    # Exercise the real guard independently of the recovery connection double.
    class Rows:
        def mappings(self): return [{'snapshot': {'key': 'cell-crops/a'}}]
    class Connection:
        def execute(self, *a): return Rows()
    with pytest.raises(reset.ResetRefused, match='preservado'):
        reset.validate_preserved_storage_references(Connection(), {'cell-crops/a'})
    reset.validate_preserved_storage_references(Connection(), {'cell-crops/other'})


def test_dry_run_read_only_and_no_manifest(tmp_path, monkeypatch, capsys):
    class Transaction:
        def rollback(self): calls.append('rollback')
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def begin(self): return Transaction()
        def execute(self, sql): calls.append(str(sql))
        def connect(self): return self
    calls = []
    monkeypatch.setenv('STORAGE_ROOT', str(tmp_path))
    monkeypatch.setattr(reset, 'create_engine', lambda *a, **k: Connection())
    monkeypatch.setattr(reset, 'validate_identity', lambda *a: None)
    monkeypatch.setattr(reset, 'plan', lambda *a: ({}, [], {}, {'counts': {}}, {'productive_train_id': 'x'}))
    assert reset.main([]) == 0
    assert 'DRY_RUN' in capsys.readouterr().out
    assert 'READ ONLY' in calls[0] and calls[-1] == 'rollback'
    assert list(tmp_path.iterdir()) == []

@pytest.mark.parametrize('committed', [False, True])
def test_lost_commit_acknowledgement_resolves_prepared(recovery, monkeypatch, committed):
    root, path, p, original_engine, before, after, _ = recovery
    # Recreate a new operation through execute_reset, with a real durable manifest.
    path.unlink(); path.parent.rmdir()
    class Result:
        rowcount = 1
        def scalar_one(self): return 0
    class Tx:
        is_active = True
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def commit(self):
            if committed: engine.state = copy.deepcopy(after)
            self.is_active = False
            raise RuntimeError('lost commit acknowledgement')
        def rollback(self): self.is_active = False
    class Engine:
        state = copy.deepcopy(before)
        def connect(self): return self
        def begin(self): return Tx()
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, sql, params=None): return Result()
    engine = Engine()
    monkeypatch.setattr(reset, 'plan', lambda *a: (
        {}, [reset.ManifestEntry(**x) for x in p['storage_files']], before['preserved_tables'],
        p['clinical_audit_events'], before['release_fingerprint']))
    monkeypatch.setattr(reset, 'validate_identity', lambda *a: None)
    monkeypatch.setattr(reset, 'admin_fingerprint', lambda *a: before['admin_fingerprint'])
    monkeypatch.setattr(reset, 'release_fingerprint', lambda *a: before['release_fingerprint'])
    monkeypatch.setattr(reset, 'fingerprint', lambda *a: before['preserved_tables'])
    monkeypatch.setattr(reset, 'revalidate_audit_plan', lambda *a: None)
    monkeypatch.setattr(reset, 'database_snapshot', lambda *a: copy.deepcopy(engine.state))
    monkeypatch.setattr(reset, 'validate_schema', lambda *a: None)
    monkeypatch.setattr(reset, 'detect_active_work', lambda *a: None)
    with pytest.raises(RuntimeError, match='lost commit'):
        reset.execute_reset(engine, root, Path(p['backup']['path']))
    operations = list((root / '.staging/smear-reset').iterdir())
    assert len(operations) == 1
    manifest = operations[0] / 'manifest.json'
    assert reset.read_manifest(manifest)['state'] == 'prepared'
    assert (root / 'cell-crops/run/a').exists()
    result = reset.resume_cleanup(engine, root, Path(p['backup']['path']), operations[0].name)
    assert result['status'] == ('CLEANUP_COMPLETE' if committed else 'RESET_NOT_COMMITTED_NO_STORAGE_CLEANUP')
    assert (root / 'cell-crops/run/a').exists() is (not committed)
