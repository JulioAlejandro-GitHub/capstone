"""Explicit root identities; no textual prefix replacement."""
from pathlib import Path, PurePosixPath
import hashlib


def resolve(root, relative):
    if not isinstance(relative,str) or not relative or '\\' in relative:
        raise ValueError('INVALID_RELATIVE_PATH')
    p=PurePosixPath(relative)
    if p.is_absolute() or str(p)!=relative or any(x in ('..','.') for x in p.parts):
        raise ValueError('INVALID_RELATIVE_PATH')
    root=Path(root).resolve(strict=True)
    candidate=root.joinpath(*p.parts)
    current=root
    for part in p.parts:
        current=current/part
        if current.is_symlink():raise ValueError('SYMLINK_FORBIDDEN')
    if not candidate.resolve().is_relative_to(root):raise ValueError('PATH_ESCAPE')
    return candidate


def identity(path):
    p=Path(path)
    if not p.is_file() or p.is_symlink() or '.partial' in p.name:
        raise ValueError('ARTIFACT_NOT_FINAL')
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return {'sha256':h.hexdigest(),'bytes':p.stat().st_size}


def verify_samples(root,samples):
    seen=set()
    for s in samples:
        if s['split'] not in ('train','val'):raise ValueError('TEST_FORBIDDEN')
        if s['relative_path'].split('/')[0]!=s['split']:raise ValueError('SPLIT_CONFLICT')
        if s['relative_path'] in seen:raise ValueError('DUPLICATE_SAMPLE')
        seen.add(s['relative_path'])
        if identity(resolve(root,s['relative_path']))['sha256']!=s['sha256']:
            raise ValueError('DATASET_HASH_CONFLICT')
    if not samples:raise ValueError('EMPTY_DATASET_MANIFEST')
