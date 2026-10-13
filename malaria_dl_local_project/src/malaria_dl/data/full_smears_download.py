"""Prepare immutable NLM RAW files. Standard library only; never opens a database."""
from __future__ import annotations

import hashlib
import http.client
import json
import os
import shutil
import stat
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Callable

from malaria_split.source_config import SourceConfig, resolve_source_config

DATASET = 'NIH-NLM-ThinBloodSmearsPf'
MANIFEST = '.capstone_download_manifest.json'
DOCUMENTS = ('ReadMe.pdf', 'Dataset_statistics.xlsx', 'Data License Agreement.docx')
# NLM ReadMe.pdf + Dataset_statistics.xlsx, independently audited in S1.1.
EXPECTED = {'Polygon Set': (33, 165), 'Point Set': (160, 800)}


class SourceError(RuntimeError):
    """An explicit non-ready state; existing scientific files must be preserved."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json_atomic(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + '.part')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == 'a':
            self.hrefs.extend(v for k, v in attrs if k == 'href' and v is not None)


def discover_urls(index: Path, source: str) -> dict[str, str]:
    parser = Links()
    parser.feed(index.read_text(encoding='utf-8'))
    found: dict[str, str] = {}
    for href in parser.hrefs:
        url = urllib.parse.urljoin(source, href)
        parsed = urllib.parse.urlsplit(url)
        url = urllib.parse.urlunsplit(parsed._replace(path=urllib.parse.quote(parsed.path, safe='/%')))
        name = urllib.parse.unquote(PurePosixPath(parsed.path).name)
        if name in (*DOCUMENTS, DATASET + '.zip'):
            if parsed.scheme != 'https' or parsed.netloc != urllib.parse.urlsplit(source).netloc:
                raise SourceError('SOURCE_MISMATCH: cross-origin or non-HTTPS distribution link')
            if name in found and found[name] != url:
                raise SourceError('SOURCE_VERSION_CONFLICT: ambiguous distribution link')
            found[name] = url
    if set(found) != {*DOCUMENTS, DATASET + '.zip'}:
        raise SourceError('DATASET_STRUCTURE_MISMATCH: index lacks archive or official documents')
    return found


def download_file(url: str, destination: Path) -> dict:
    """Retain verified completed transfers; retry only interrupted transfers."""
    receipt_path = destination.with_name(destination.name + '.receipt.json')
    if any(p.is_symlink() for p in (destination, receipt_path, destination.with_name(destination.name + '.part'))):
        raise SourceError('SOURCE_VERSION_CONFLICT: symlink in download staging')
    if destination.exists():
        if not receipt_path.is_file():
            raise SourceError(f'SOURCE_VERSION_CONFLICT: untracked cached file {destination}')
        receipt = json.loads(receipt_path.read_text())
        if receipt['url'] != url:
            raise SourceError('SOURCE_VERSION_CONFLICT: cached URL differs')
        if destination.stat().st_size != receipt['size'] or sha256(destination) != receipt['sha256']:
            raise SourceError(f'INTEGRITY_FAIL: {destination}')
        return {**receipt, 'downloaded_files': 0, 'downloaded_bytes': 0}
    temporary = destination.with_name(destination.name + '.part')
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Capstone-S1.D/1.0', 'Accept-Encoding': 'identity'})
            with urllib.request.urlopen(request, timeout=60) as response:
                effective_url = response.geturl()
                if (response.status != 200 or urllib.parse.urlsplit(effective_url).scheme != 'https'
                        or urllib.parse.urlsplit(effective_url).netloc != urllib.parse.urlsplit(url).netloc):
                    raise SourceError('SOURCE_MISMATCH: unexpected HTTP status or redirect origin')
                length = response.headers.get('Content-Length')
                with temporary.open('wb') as stream:
                    shutil.copyfileobj(response, stream, length=1024 * 1024)
                    stream.flush()
                    os.fsync(stream.fileno())
            size = temporary.stat().st_size
            if size == 0 or (length is not None and size != int(length)):
                raise OSError('truncated HTTP response')
            receipt = {'url': url, 'effective_url': effective_url, 'retrieved_at': utc_now(),
                       'size': size, 'sha256': sha256(temporary), 'hash_strategy': 'LOCAL_BASELINE_SHA256'}
            # Receipt first: a crash before rename leaves only an incomplete .part.
            write_json_atomic(receipt_path, receipt)
            temporary.replace(destination)
            return {**receipt, 'downloaded_files': 1, 'downloaded_bytes': size}
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403, 404, 410):
                raise SourceError(f'DOWNLOAD_FAILED: STOP HTTP {exc.code} {url}') from exc
            if attempt == 2:
                raise SourceError(f'DOWNLOAD_FAILED: {url}: {exc}') from exc
        except (OSError, urllib.error.URLError, http.client.HTTPException) as exc:
            if attempt == 2:
                raise SourceError(f'DOWNLOAD_FAILED: {url}: {exc}') from exc
        time.sleep(attempt + 1)
    raise SourceError('DOWNLOAD_FAILED')


def extract_archive(archive: Path, destination: Path) -> None:
    """No paths outside staging, symlinks, duplicate names or silent overwrites."""
    with zipfile.ZipFile(archive) as source:
        seen: set[str] = set()
        for entry in source.infolist():
            path = PurePosixPath(entry.filename)
            if (path.is_absolute() or '..' in path.parts or '\\' in entry.filename
                    or not path.parts or ':' in path.parts[0]
                    or path.parts[0] in (MANIFEST, '.capstone_source_documents')
                    or stat.S_ISLNK(entry.external_attr >> 16)):
                raise SourceError('INTEGRITY_FAIL: unsafe ZIP member')
            folded = str(path).casefold()
            if folded in seen:
                raise SourceError('INTEGRITY_FAIL: duplicate ZIP member')
            seen.add(folded)
            target = destination.joinpath(*path.parts)
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            # Reading through ZipFile validates CRC; no image/annotation re-encoding.
            with source.open(entry) as incoming, target.open('xb') as outgoing:
                shutil.copyfileobj(incoming, outgoing)


def validate_structure(root: Path) -> dict:
    result: dict[str, dict] = {}
    for subset, (patients, images) in EXPECTED.items():
        folder = root / subset
        if not folder.is_dir():
            raise SourceError(f'DATASET_STRUCTURE_MISMATCH: missing {subset}')
        directories = sorted(p for p in folder.iterdir() if p.is_dir())
        count = 0
        for patient in directories:
            image_dirs = [p for p in patient.iterdir() if p.is_dir() and p.name.lower() == 'img']
            if len(image_dirs) != 1:
                raise SourceError(f'DATASET_STRUCTURE_MISMATCH: image directory {patient.name}')
            jpgs = sorted(p for p in image_dirs[0].iterdir() if p.suffix.lower() in ('.jpg', '.jpeg', '.png'))
            annotations = sorted((patient / 'GT').glob('*.txt'))
            if len(jpgs) != 5 or len(annotations) != 5 or {p.stem for p in jpgs} != {p.stem for p in annotations}:
                raise SourceError(f'DATASET_STRUCTURE_MISMATCH: image/GT association {patient.name}')
            for gt in annotations:
                with gt.open(encoding='utf-8-sig') as stream:
                    header = stream.readline().strip().split(',')
                    try:
                        valid = len(header) == 3 and all(int(v) > 0 for v in header)
                    except ValueError:
                        valid = False
                    if not valid or not stream.readline().strip():
                        raise SourceError(f'DATASET_STRUCTURE_MISMATCH: invalid GT header/body {gt}')
            if any(p.stat().st_size == 0 for p in jpgs):
                raise SourceError('DATASET_STRUCTURE_MISMATCH: empty image')
            count += len(jpgs)
        if (len(directories), count) != (patients, images):
            raise SourceError(f'DATASET_STRUCTURE_MISMATCH: {subset}: {len(directories)} IDs, {count} images')
        result[subset] = {'patients': len(directories), 'images': count, 'ground_truth_files': count}
    for name in DOCUMENTS:
        if not (root / name).is_file() or (root / name).stat().st_size == 0:
            raise SourceError(f'DATASET_STRUCTURE_MISMATCH: missing {name}')
    return result


def inventory(root: Path) -> list[dict]:
    entries = []
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise SourceError('INTEGRITY_FAIL: symlink in RAW source')
        if path.is_file() and path != root / MANIFEST:
            if path.name.endswith('.part'):
                raise SourceError('INTEGRITY_FAIL: partial file in RAW source')
            entries.append({'relative_path': path.relative_to(root).as_posix(),
                            'size': path.stat().st_size, 'sha256': sha256(path)})
    return entries


def verify_full_smear_source(config: SourceConfig) -> dict:
    root = config.smear_root
    if not (root / MANIFEST).is_file():
        raise SourceError('INTEGRITY_FAIL: missing download manifest; existing RAW is never adopted silently')
    try:
        manifest = json.loads((root / MANIFEST).read_text())
        if manifest['source'] != config.smear_source:
            raise SourceError('SOURCE_VERSION_CONFLICT: configured SOURCE differs from manifest')
        if manifest['dataset'] != DATASET or manifest['schema_version'] != 1 or manifest['files'] != inventory(root):
            raise SourceError('INTEGRITY_FAIL: manifest/file mismatch')
        structure = validate_structure(root)
    except (KeyError, ValueError, OSError) as exc:
        raise SourceError(f'INTEGRITY_FAIL: invalid manifest or files: {exc}') from exc
    return {'dataset': DATASET, 'source': config.smear_source, 'destination': str(root),
            'integrity': 'PASS', 'status': 'ALREADY_DOWNLOADED', 'downloaded_files': 0,
            'downloaded_bytes': 0, 'structure': structure, 'manifest': str(root / MANIFEST)}


def prepare_full_smear_source(
    config: SourceConfig | None = None, *, verify_only: bool = False,
    fetch: Callable[[str, Path], dict] = download_file,
) -> dict:
    config = config or resolve_source_config()
    root = config.smear_root
    if root.is_symlink():
        raise SourceError('SOURCE_VERSION_CONFLICT: RAW root is a symlink')
    if root.exists() or verify_only:
        return verify_full_smear_source(config)
    if urllib.parse.urlsplit(config.smear_source).scheme != 'https':
        raise SourceError('SOURCE_MISMATCH: SOURCE must be an HTTPS distribution index')
    started = utc_now()
    staging = root.parent / ('.' + root.name + '.download')
    if staging.is_symlink():
        raise SourceError('SOURCE_VERSION_CONFLICT: staging is a symlink')
    staging.mkdir(parents=True, exist_ok=True)
    lock = staging / 'active.lock'
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise SourceError(f'DOWNLOAD_FAILED: active/stale lock {lock}; inspect before removal') from exc
    os.close(lock_fd)
    try:
        source_marker = staging / 'source.json'
        if source_marker.exists() and json.loads(source_marker.read_text())['source'] != config.smear_source:
            raise SourceError('SOURCE_VERSION_CONFLICT: staging belongs to another SOURCE')
        write_json_atomic(source_marker, {'source': config.smear_source})
        transfers = [fetch(config.smear_source, staging / 'index.html')]
        urls = discover_urls(staging / 'index.html', config.smear_source)
        transfers.append(fetch(urls[DATASET + '.zip'], staging / 'source.zip'))
        for name in DOCUMENTS:
            transfers.append(fetch(urls[name], staging / name))
        extracted = staging / 'extracted'
        if extracted.exists():
            # Only this downloader's unpublished extraction is disposable, never ROOT.
            shutil.rmtree(extracted)
        extracted.mkdir()
        try:
            extract_archive(staging / 'source.zip', extracted)
        except (zipfile.BadZipFile, OSError) as exc:
            raise SourceError(f'INTEGRITY_FAIL: archive extraction: {exc}') from exc
        document_versions = []
        for name in DOCUMENTS:
            published = staging / name
            archived = extracted / name
            differs = archived.exists() and sha256(archived) != sha256(published)
            if differs:
                # Retain both published versions, explicitly; never replace archive evidence.
                target = extracted / '.capstone_source_documents' / name
                target.parent.mkdir(exist_ok=True)
            else:
                target = archived
            if not target.exists():
                shutil.copyfile(published, target)
            document_versions.append({'document': name, 'url': urls[name],
                                      'standalone_relative_path': target.relative_to(extracted).as_posix(),
                                      'archive_differs_from_standalone': differs,
                                      'archive_sha256': sha256(archived),
                                      'standalone_sha256': sha256(published)})
        structure = validate_structure(extracted)
        manifest = {'schema_version': 1, 'dataset': DATASET, 'dataset_family': 'smear_segmentation',
                    'source': config.smear_source, 'started_at': started, 'downloaded_at': utc_now(),
                    'hash_strategy': 'LOCAL_BASELINE_SHA256', 'official_checksum_available': False,
                    'transfers': transfers, 'document_versions': document_versions,
                    'structure': structure, 'files': inventory(extracted)}
        write_json_atomic(extracted / MANIFEST, manifest)
        if root.exists():
            raise SourceError('SOURCE_VERSION_CONFLICT: destination appeared during download')
        extracted.rename(root)
        result = verify_full_smear_source(config)
        return {**result, 'status': 'READY', 'started_at': started, 'finished_at': utc_now(),
                'downloaded_files': sum(t['downloaded_files'] for t in transfers),
                'downloaded_bytes': sum(t['downloaded_bytes'] for t in transfers)}
    finally:
        lock.unlink()
