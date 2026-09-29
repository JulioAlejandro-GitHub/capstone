"""Shared evidence primitives; reuse the fingerprints validated in RESET.1B/3."""
import hashlib
import json
import os
import re
from pathlib import Path


class MaintenanceError(RuntimeError):
    """A public error code, never a driver/credential-bearing exception message."""


def require(value, code):
    if not value:
        raise MaintenanceError(code)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w') as stream:
        os.chmod(temporary, 0o600)
        json.dump(value, stream, indent=2, default=str)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def normalized_catalog(cat):
    """The exact narrow restore normalizations validated by RESET.3."""
    result = {}
    for key, rows in cat.items():
        cleaned = []
        for original in rows:
            row = {k: v for k, v in original.items() if k != 'oid'}
            if key == 'triggers' and row['tgisinternal']:
                row['definition'] = row['definition'].replace(row['tgname'], 'RI_INTERNAL_GENERATED_NAME')
                row['tgname'] = 'RI_INTERNAL_GENERATED_NAME'
            if key == 'constraints':
                definition = re.sub(r"\(ARRAY\[((?:'[^']*'::character varying)(?:, '[^']*'::character varying)*)\]\)::text\[\]", r"ARRAY[\1]", row['definition'])
                row['definition'] = re.sub(r"\('([^']*)'::character varying\)::text", r"'\1'::character varying", definition)
            cleaned.append(json.dumps(row, sort_keys=True))
        result[key] = sorted(cleaned)
    return result


def filesystem_fingerprint(root):
    """Includes symlink identities without traversing them."""
    root = Path(root)
    rows = []
    if root.is_file():
        return {'entries':1,'sha256':digest(root),'bytes':root.stat().st_size}
    if not root.exists():
        return {'entries': 0, 'sha256': hashlib.sha256(b'[]').hexdigest()}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in list(dirs):
            path = Path(directory) / name
            if path.is_symlink():
                rows.append([str(path.relative_to(root)), 'link', os.readlink(path)])
                dirs.remove(name)
        for name in files:
            path = Path(directory) / name
            if path.is_symlink():
                rows.append([str(path.relative_to(root)), 'link', os.readlink(path)])
            else:
                before = path.stat()
                hashed = digest(path)
                after = path.stat()
                require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'PROTECTED_FILE_CHANGED_DURING_READ')
                rows.append([str(path.relative_to(root)), before.st_size, hashed])
    rows.sort()
    return {'entries': len(rows), 'sha256': hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()}


def protected_link_targets(roots):
    """A scientific symlink protects its referent as well as its own entry."""
    targets = set()
    for root in map(Path, roots):
        if root.is_symlink():
            targets.add(str(root.resolve()))
        for directory, dirs, files in os.walk(root, followlinks=False):
            for name in dirs + files:
                path = Path(directory) / name
                if path.is_symlink():
                    targets.add(str(path.resolve()))
    return sorted(targets)
