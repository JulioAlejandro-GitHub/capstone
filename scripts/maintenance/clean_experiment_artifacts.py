"""STORAGE.CLEAN.1: canonical, attributable manifests and exact per-file unlink."""
import json
import os
import re
import stat
from pathlib import Path

from scripts.maintenance.protected_resources import MARKERS, GENERATED_NAMES, RELEASE_NAMES
from scripts.maintenance.verification import digest, require

MODEL_EXTENSIONS = frozenset(('.keras', '.h5', '.hdf5', '.ckpt', '.pt', '.pth', '.npy', '.npz', '.pkl', '.parquet'))
UUID = re.compile(r'^[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}$')


def attributable(path, root, category, owners, models):
    relative = path.relative_to(root)
    if path.suffix in {'.py', '.sh', '.sql', '.dump', '.env', '.ini', '.yaml', '.yml', '.toml'}:
        return None
    if str(path) in owners:
        return 'REGISTERED_HISTORICAL_ARTIFACT'
    # A session artifact_root is itself a registered owner, not merely an extension.
    if any(str(p) in owners for p in path.parents if p != root and p.is_relative_to(root)):
        return 'REGISTERED_HISTORICAL_SESSION_DIRECTORY'
    if category == 'ml_outputs':
        if relative.parts[0] in set(models) | {'ensemble', 'cnn_features_svm'} and path.name in GENERATED_NAMES:
            return 'TRAINER_GENERATED_OUTPUT_CONTRACT'
        if relative.parts[0] == 'explainability' and path.suffix in {'.png', '.json', '.csv'}:
            return 'HISTORICAL_EXPLANATION_NAMESPACE'
    if category == 'releases' and path.name in RELEASE_NAMES:
        manifest = path.parent / 'manifest.json'
        if manifest.is_file() and not manifest.is_symlink():
            try:
                value = json.loads(manifest.read_text())
                if (UUID.fullmatch(path.parent.name) and str(value.get('model_version_id')) == path.parent.name
                        and UUID.fullmatch(str(value.get('training_run_id', '')))
                        and re.fullmatch(r'[a-f0-9]{64}', str(value.get('sha256', '')))):
                    return 'HISTORICAL_RELEASE_MANIFEST'
            except (ValueError, OSError):
                pass
    if category in ('local_execution', 'artifacts'):
        if any(UUID.fullmatch(p) for p in relative.parts[:-1]) and re.fullmatch(r'epoch_\d+\.(keras|h5|hdf5|ckpt|pt|pth)', path.name):
            return 'PER_RUN_CHECKPOINT_CONTRACT'
    if category in ('cell_crops', 'cell_explanations', 'model_explanations'):
        if any(UUID.fullmatch(p) for p in relative.parts[:-1]) and path.suffix in {'.png', '.json'}:
            return 'DERIVED_IMAGE_NAMESPACE'
    return None


def scan_roots(roots, protected, owned_paths, models):
    files, issues, excluded = [], [], []
    seen = set()
    protected = [Path(p).resolve() for p in protected]
    owners = set(owned_paths)
    for specification in roots:
        root = Path(specification['path'])
        if not root.exists():
            continue
        if any(root.resolve().is_relative_to(p) for p in protected):
            issues.append({'path': str(root), 'reason': 'PROTECTED_ROOT'})
            continue
        for directory, dirs, names in os.walk(root, followlinks=False):
            for name in list(dirs):
                p = Path(directory) / name
                if p.is_symlink():
                    issues.append({'path': str(p), 'reason': 'SYMLINK_EXCLUDED'})
                    dirs.remove(name)
            for name in names:
                path = Path(directory) / name
                if name in MARKERS:
                    excluded.append({'path': str(path), 'reason': 'TECHNICAL_MARKER'})
                    continue
                if path.is_symlink() or any(p.is_symlink() for p in path.parents):
                    issues.append({'path': str(path), 'reason': 'SYMLINK_EXCLUDED'})
                    continue
                if any(path.resolve().is_relative_to(p) for p in protected):
                    issues.append({'path': str(path), 'reason': 'PROTECTED_PATH'})
                    continue
                s = path.stat()
                if not stat.S_ISREG(s.st_mode) or s.st_nlink != 1:
                    issues.append({'path': str(path), 'reason': 'SHARED_OR_SPECIAL_FILE'})
                    continue
                key = (s.st_dev, s.st_ino)
                if key in seen:
                    continue
                seen.add(key)
                reason = attributable(path, root, specification['category'], owners, models)
                if reason is None:
                    issues.append({'path': str(path), 'reason': 'UNATTRIBUTED_FILE'})
                    continue
                hashed = digest(path)
                after = path.stat()
                require((s.st_size, s.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'FILE_CHANGED_DURING_INVENTORY')
                files.append({'path': str(path.resolve()), 'root': str(root.resolve()), 'category': specification['category'],
                              'physical_root': specification['physical_root'], 'bytes': s.st_size,
                              'allocated_bytes': s.st_blocks * 512, 'device': s.st_dev, 'inode': s.st_ino,
                              'mtime_ns': s.st_mtime_ns, 'sha256': hashed, 'ownership': reason})
    return {'files': files, 'issues': issues, 'excluded': excluded}


def delete_manifest(manifest, journal_path):
    def check(row, contents):
        p = Path(row['path'])
        require(p.is_relative_to(Path(row['root'])), 'OUTSIDE_FROZEN_ROOT')
        require(not p.is_symlink() and not any(parent.is_symlink() for parent in p.parents), 'SYMLINK_CHANGED')
        if not p.exists():
            return None
        s = p.stat()
        require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'SHARED_FILE_CHANGED')
        require((s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns) == (row['device'], row['inode'], row['bytes'], row['mtime_ns']), 'FILE_IDENTITY_CHANGED')
        if contents:
            require(digest(p) == row['sha256'], 'FILE_HASH_CHANGED')
        return p
    # No deletion until every remaining member is verified. Absent entries on a
    # retry are recorded separately and never counted as recovered bytes.
    for row in manifest['files']:
        check(row, True)
    roots = {row['physical_root']: Path(row['root']) for row in manifest['files']}
    before = {key: os.statvfs(root) for key, root in roots.items()}
    deleted, missing, size, allocated = 0, 0, 0, 0
    with Path(journal_path).open('a') as journal:
        for row in manifest['files']:
            path = check(row, False)
            if path is None:
                missing += 1
                continue
            path.unlink()
            deleted += 1
            size += row['bytes']
            allocated += row['allocated_bytes']
            journal.write(json.dumps({'path': row['path'], 'sha256': row['sha256'], 'bytes': row['bytes'], 'allocated_bytes':row['allocated_bytes'], 'action': 'UNLINK_CONFIRMED'}) + '\n')
            journal.flush()
            os.fsync(journal.fileno())
    after = {key: os.statvfs(root) for key, root in roots.items()}
    require(all(not Path(row['path']).exists() for row in manifest['files']), 'ARTIFACT_RESIDUE')
    return {'deleted_files': deleted, 'deleted_bytes': size, 'allocated_bytes_unlinked':allocated, 'already_missing': missing,
            'observed_available_delta_by_root': {key: after[key].f_bavail * after[key].f_frsize - before[key].f_bavail * before[key].f_frsize for key in roots}}


def main():
    from scripts.maintenance.orchestrator import main as run
    return run('artifacts')


if __name__ == '__main__':
    raise SystemExit(main())
