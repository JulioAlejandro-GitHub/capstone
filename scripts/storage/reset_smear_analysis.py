#!/usr/bin/env python3
"""Reset narrowly-scoped smear-analysis data. Safe plan mode is the default."""
from __future__ import annotations

import argparse
import errno
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.exc import SQLAlchemyError

CONFIRMATION = "RESET MALARIA SMEAR ANALYSIS"
EXPECTED_HEAD = "20260901_01"
ALLOWED_SCHEMA = "public"
ALLOWED_NAMESPACES = frozenset({
    "microscopy-images", "cell-crops", "cell-explanations",
    ".staging/uploads", ".staging/cell-detection", ".staging/cell-explanations",
})
PRESERVED_NAMESPACES = frozenset({"model-explanations"})
CLINICAL_AUDIT_RESOURCE_TYPES = frozenset({
    "microscopy_analysis_run", "image_ingestion_batch", "microscopy_image",
    "image_quality_assessment", "cell_detection_run", "cell_detection", "cell_crop",
    "cell_classification_run", "cell_prediction", "cell_explanation", "smear_analysis_summary",
})
CLINICAL_API_PREFIXES = (
    "/api/v1/analysis", "/api/v1/scientific/workflows", "/api/v1/scientific/images",
    "/api/v1/cell-analysis", "/api/v1/cell-classification",
)
SECURITY_AUDIT_ACTIONS = frozenset({"login", "logout", "password-change", "user-create", "user-update", "role-grant", "role-revoke"})

# Children precede parents. This is deliberately static and reviewable.
DELETE_ORDER = (
    "cell_explanations", "cell_classification_reviews", "cell_classification_events",
    "smear_analysis_summaries", "cell_predictions", "cell_classification_inputs",
    "cell_classification_runs", "scientific_reviews", "cell_crops",
    "cell_detection_events", "cell_detections", "image_connected_components",
    "cell_detection_runs", "quality_gate_decisions", "quality_assessment_queue_items",
    "microscopy_analysis_events", "image_quality_assessments",
    "microscopy_analysis_run_images", "microscopy_analysis_runs", "microscopy_images",
    "image_ingestion_batches", "smear_slides", "blood_samples", "scientific_cases",
    "research_subjects",
)
TARGET_TABLES = frozenset(DELETE_ORDER)
PRESERVED_TABLES = (
    "users", "roles", "user_roles", "runs", "run_lineage", "model_versions",
    "stage2_model_publications", "deployed_model_versions", "datasets",
    "dataset_versions", "artifacts", "predictions", "image_analysis_jobs",
    "scientific_validation_sessions", "scientific_validation_images",
    "scientific_validation_detection_runs", "scientific_validation_classification_runs",
    "scientific_validation_annotations", "scientific_validation_annotation_events",
)
ACTIVE_RUN_STATES = frozenset({"created", "pending", "queued", "running", "processing", "quality_pending", "quality_processing", "annotation_in_progress"})
STORAGE_COLUMNS = (
    ("microscopy_images", "id", "storage_key", "file_size_bytes", "sha256"),
    ("cell_crops", "id", "relative_storage_key", "file_size_bytes", "sha256"),
    ("cell_explanations", "id", "heatmap_storage_key", "heatmap_file_size_bytes", "heatmap_sha256"),
    ("cell_explanations", "id", "overlay_storage_key", "overlay_file_size_bytes", "overlay_sha256"),
)

class ResetRefused(RuntimeError):
    pass

class StorageRefused(ResetRefused):
    def __init__(self, classification: str):
        self.classification = classification
        super().__init__(classification)

@dataclass(frozen=True)
class ManifestEntry:
    storage_key: str
    namespace: str
    table: str
    row_id: str
    size: int
    sha256: str
    uid: int
    gid: int
    mode: int
    inode: int
    device: int
    mtime_ns: int
    column: str = ""
    classification: str = "canonical_present"

@dataclass(frozen=True)
class MissingReference:
    table: str
    row_id: str
    column: str
    storage_key: str
    expected_size: int | None
    expected_sha256: str | None
    classification: str = "missing_before_reset"
    reason: str = "absent_from_canonical_storage"

@dataclass(frozen=True)
class StoragePlan:
    files: list[ManifestEntry]
    missing: list[MissingReference]

    @property
    def keys(self) -> set[str]:
        return {x.storage_key for x in [*self.files, *self.missing]}

@dataclass(frozen=True)
class AuditClassification:
    category: str
    event_id: str
    fingerprint: str

def _route_matches_clinical(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("/"):
        return False
    path = value.split("?", 1)[0].rstrip("/") or "/"
    return any(path == prefix or path.startswith(prefix + "/") for prefix in CLINICAL_API_PREFIXES)

def _json_scalars(value: Any, *, nested=False) -> set[str]:
    """Only exact scalar values are evidence; objects/arrays are recursively traversed."""
    if value is None: return set()
    if isinstance(value, str) and not nested:
        try: value = json.loads(value)
        except json.JSONDecodeError: raise ResetRefused("JSON de auditoría no interpretable")
    if isinstance(value, (int, float, bool)): return {str(value)}
    if isinstance(value, str): return {value}
    if isinstance(value, list):
        result: set[str] = set()
        for item in value: result |= _json_scalars(item, nested=True)
        return result
    if isinstance(value, dict):
        result: set[str] = set()
        for item in value.values(): result |= _json_scalars(item, nested=True)
        return result
    if nested: return {str(value)}
    raise ResetRefused("JSON de auditoría no interpretable")

def classify_audit_event(row: Mapping[str, Any], clinical_ids: set[str], storage_keys: set[str]) -> AuditClassification:
    """Fail closed: a clinical clue without exact deletion evidence is ambiguous."""
    event_id = str(row["id"])
    payload_scalars: set[str] = set()
    for field in ("before_state", "after_state", "metadata"):
        if field in row and row[field] is not None:
            payload_scalars |= _json_scalars(row[field])
    resource_type, resource_id = row.get("resource_type"), str(row.get("resource_id") or "")
    route = row.get("request_path")
    exact_payload = bool(payload_scalars & (clinical_ids | storage_keys))
    exact_resource = resource_type in CLINICAL_AUDIT_RESOURCE_TYPES and resource_id in clinical_ids
    exact_route = _route_matches_clinical(route) and (resource_id in clinical_ids or exact_payload)
    digest = hashlib.sha256(json.dumps(dict(row), default=str, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if exact_resource or exact_route or exact_payload:
        return AuditClassification("DELETE_CLINICAL_AUDIT", event_id, digest)
    if resource_type in CLINICAL_AUDIT_RESOURCE_TYPES or _route_matches_clinical(route):
        return AuditClassification("AMBIGUOUS_AUDIT", event_id, digest)
    action = str(row.get("action") or "")
    if action in SECURITY_AUDIT_ACTIONS or resource_type in {"user", "role", "authentication"}:
        return AuditClassification("PRESERVE_SECURITY_AUDIT", event_id, digest)
    if resource_type in {"run", "model_version", "dataset", "artifact", "deployment", "publication", "image_analysis_job", "prediction"}:
        return AuditClassification("PRESERVE_EXPERIMENTAL_AUDIT", event_id, digest)
    return AuditClassification("PRESERVE_UNRELATED_AUDIT", event_id, digest)

def namespace_for(key: str) -> str:
    safe_key(key)
    if not isinstance(key, str) or not key or "\x00" in key:
        raise ResetRefused("storage key vacío o inválido")
    path = PurePosixPath(key)
    if not path.parts or path.is_absolute() or ".." in path.parts or str(path) != key:
        raise ResetRefused("storage key inseguro")
    namespace = "/".join(path.parts[:2]) if path.parts[0] == ".staging" else path.parts[0]
    if namespace not in ALLOWED_NAMESPACES:
        raise ResetRefused("namespace clínico no autorizado")
    return namespace

def inspect_file(root: Path, *, key: str, table: str, row_id: Any,
                 expected_size: Any, expected_sha256: Any, column: str = "") -> ManifestEntry:
    namespace = namespace_for(key)
    parts = safe_key(key)
    try:
        with directory_fd(root.joinpath(*parts[:-1])) as parent:
            info = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode): raise ResetRefused(f"symlink rechazado: {key}")
            if not stat.S_ISREG(info.st_mode): raise ResetRefused(f"archivo especial rechazado: {key}")
            try: fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
            except FileNotFoundError as exc:
                raise ResetRefused('STORAGE_FILE_CHANGED: archivo desapareció durante inspección') from exc
            try: metadata = file_metadata(fd)
            finally: os.close(fd)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise ResetRefused(f"symlink o directorio inseguro: {key}") from exc
        raise
    validate_expected_metadata(expected_size, expected_sha256)
    if ((expected_size is not None and expected_size != metadata['size']) or
            (expected_sha256 is not None and expected_sha256 != metadata['sha256'])):
        raise ResetRefused(f"metadata ambigua para archivo: {key}")
    if not column and table != 'clinical_staging':
        candidates = [c for t, _, c, _, _ in STORAGE_COLUMNS if t == table]
        if len(candidates) == 1: column = candidates[0]
    return ManifestEntry(key, namespace, table, str(row_id), **metadata, column=column)

def validate_expected_metadata(size, sha256):
    if size is not None and (type(size) is not int or size < 0):
        raise ResetRefused('tamaño esperado inválido')
    if sha256 is not None: _digest(sha256)

def build_manifest(connection: Connection, root: Path) -> StoragePlan:
    entries: dict[str, ManifestEntry] = {}
    missing: list[MissingReference] = []
    seen = set()
    with directory_fd(root):
        pass  # A missing or unsafe root is not a missing clinical file.
    for table, id_col, key_col, size_col, sha_col in STORAGE_COLUMNS:
        rows = connection.execute(text(
            f'SELECT "{id_col}", "{key_col}", "{size_col}", "{sha_col}" FROM "{table}" ORDER BY "{key_col}", "{id_col}"'
        )).mappings()
        for row in rows:
            key = row[key_col]
            try:
                validate_reference(table, str(row[id_col]), key_col, key)
                validate_expected_metadata(row[size_col], row[sha_col])
                if key in seen: raise StorageRefused('ambiguous')
                seen.add(key)
                item = inspect_file(root, key=key, table=table, row_id=row[id_col],
                                    expected_size=row[size_col], expected_sha256=row[sha_col],
                                    column=key_col)
            except FileNotFoundError:
                # Confirm absence with no-follow metadata only; never infer it from
                # a vanished file descriptor or a missing/unsafe STORAGE_ROOT.
                absent = MissingReference(table, str(row[id_col]), key_col, key,
                                          row[size_col], row[sha_col])
                require_missing(root, [asdict(absent)])
                missing.append(absent)
            except StorageRefused:
                raise
            except (OSError, ResetRefused, TypeError, ValueError) as exc:
                raise StorageRefused('invalid_or_unsafe') from exc
            else:
                entries[item.storage_key] = item
    # Staging has no database row by design. Enumerate only the three exact roots;
    # never infer deletable namespaces from names or patterns.
    for namespace in sorted(x for x in ALLOWED_NAMESPACES if x.startswith(".staging/")):
        staging_root = root.joinpath(*PurePosixPath(namespace).parts)
        if not staging_root.exists() and not staging_root.is_symlink():
            continue
        with directory_fd(staging_root):
            pass
        pending = [staging_root]
        while pending:
            directory = pending.pop()
            for child in sorted(os.scandir(directory), key=lambda item: item.name):
                info = child.stat(follow_symlinks=False)
                key = Path(child.path).relative_to(root).as_posix()
                if child.is_symlink():
                    raise ResetRefused(f"symlink rechazado: {key}")
                if stat.S_ISDIR(info.st_mode):
                    pending.append(Path(child.path)); continue
                if not stat.S_ISREG(info.st_mode):
                    raise ResetRefused(f"archivo especial rechazado: {key}")
                digest = hashlib.sha256(Path(child.path).read_bytes()).hexdigest()
                item = inspect_file(root, key=key, table="clinical_staging", row_id=key,
                                    expected_size=info.st_size, expected_sha256=digest)
                if key in entries:
                    raise ResetRefused(f"storage key duplicada incompatible: {key}")
                entries[key] = item
    return StoragePlan([entries[key] for key in sorted(entries)],
                       sorted(missing, key=lambda x: (x.table, x.row_id, x.column)))

def fingerprint(connection: Connection, tables: Iterable[str] = PRESERVED_TABLES) -> dict[str, str]:
    result = {}
    for table in tables:
        result[table] = connection.execute(text(
            f"SELECT md5(COALESCE(string_agg(row_to_json(t)::text, '' ORDER BY row_to_json(t)::text), '')) FROM \"{table}\" t"
        )).scalar_one()
    return result

def admin_fingerprint(connection: Connection) -> str:
    return connection.execute(text("""
      SELECT md5(COALESCE(string_agg(row_to_json(x)::text, '' ORDER BY row_to_json(x)::text), ''))
      FROM (SELECT u.email,u.username,u.status,r.name role
            FROM users u JOIN user_roles ur ON ur.user_id=u.id JOIN roles r ON r.id=ur.role_id
            WHERE lower(u.email)='admin@capstone.local') x
    """)).scalar_one()

def release_fingerprint(connection: Connection) -> dict[str, Any]:
    rows = connection.execute(text("""
      SELECT id,run_type,release_status,release_updated_at,release_changed_by,release_reason
      FROM runs WHERE run_type='training' ORDER BY id
    """)).mappings().all()
    productive = [str(x["id"]) for x in rows if x["release_status"] == "productive_stage2"]
    if len(productive) != 1: raise ResetRefused("se requiere exactamente un TRAIN productive_stage2")
    return {"productive_train_id": productive[0], "fingerprint": hashlib.sha256(json.dumps([dict(x) for x in rows], default=str, sort_keys=True).encode()).hexdigest()}

def clinical_references(connection: Connection) -> tuple[set[str], set[str]]:
    ids: set[str] = set()
    for table in TARGET_TABLES:
        columns = connection.execute(text("""SELECT column_name FROM information_schema.columns
          WHERE table_schema='public' AND table_name=:table AND column_name='id'"""), {"table": table}).scalars().all()
        if columns:
            ids.update(str(x) for x in connection.execute(text(f'SELECT id FROM "{table}"')).scalars())
    keys = set()
    for table, _, key, _, _ in STORAGE_COLUMNS:
        keys.update(str(x) for x in connection.execute(text(f'SELECT "{key}" FROM "{table}" WHERE "{key}" IS NOT NULL')).scalars())
    return ids, keys

def audit_plan(connection: Connection, clinical_ids: set[str], storage_keys: set[str]) -> dict[str, Any]:
    rows = connection.execute(text("SELECT id,resource_type,resource_id,request_path,action,before_state,after_state,metadata FROM audit_events ORDER BY id")).mappings().all()
    classified = [classify_audit_event(row, clinical_ids, storage_keys) for row in rows]
    counts = {name: sum(x.category == name for x in classified) for name in (
        "DELETE_CLINICAL_AUDIT", "PRESERVE_SECURITY_AUDIT", "PRESERVE_EXPERIMENTAL_AUDIT", "PRESERVE_UNRELATED_AUDIT", "AMBIGUOUS_AUDIT")}
    if counts["AMBIGUOUS_AUDIT"]: raise ResetRefused("auditoría ambigua puede contener datos clínicos")
    return {"total": len(classified), "counts": counts,
            "ids": [x.event_id for x in classified if x.category == "DELETE_CLINICAL_AUDIT"],
            "fingerprints": {x.event_id: x.fingerprint for x in classified if x.category == "DELETE_CLINICAL_AUDIT"}}

def revalidate_audit_plan(connection: Connection, audit: dict[str, Any]) -> None:
    for event_id, expected in audit["fingerprints"].items():
        row = connection.execute(text("SELECT id,resource_type,resource_id,request_path,action,before_state,after_state,metadata FROM audit_events WHERE id=CAST(:id AS uuid)"), {"id":event_id}).mappings().first()
        if row is None or hashlib.sha256(json.dumps(dict(row), default=str, sort_keys=True, separators=(",", ":")).encode()).hexdigest() != expected:
            raise ResetRefused("evento de auditoría cambió concurrentemente")

def validate_scientific_validation(connection: Connection, clinical_ids: set[str], storage_keys: set[str]) -> None:
    tables = [x for x in PRESERVED_TABLES if x.startswith("scientific_validation_")]
    for table in tables:
        columns = connection.execute(text("SELECT column_name,data_type FROM information_schema.columns WHERE table_schema='public' AND table_name=:t"), {"t":table}).mappings().all()
        names = {x["column_name"] for x in columns}
        for name in {"sample_id", "analysis_run_id", "cell_detection_id", "microscopy_image_id", "detection_run_id", "classification_run_id"} & names:
            if connection.execute(text(f'SELECT 1 FROM "{table}" WHERE "{name}"::text = ANY(:ids) LIMIT 1'), {"ids":list(clinical_ids)}).first():
                raise ResetRefused("scientific validation references clinical data")
        for name in {x["column_name"] for x in columns if x["data_type"] in ("json", "jsonb")}:
            for raw in connection.execute(text(f'SELECT "{name}" FROM "{table}" WHERE "{name}" IS NOT NULL')).scalars():
                if _json_scalars(raw) & (clinical_ids | storage_keys):
                    raise ResetRefused("scientific validation references clinical data")

MANIFEST_VERSION = 2
STATES = {'prepared', 'database_committed', 'cleanup_pending', 'cleanup_completed',
          'aborted_before_commit', 'blocked'}
TRANSITIONS = {
    'prepared': {'aborted_before_commit', 'database_committed', 'blocked'},
    'database_committed': {'cleanup_pending', 'cleanup_completed'},
    'cleanup_pending': {'cleanup_pending', 'cleanup_completed'},
    'cleanup_completed': set(), 'aborted_before_commit': set(), 'blocked': set(),
}

def canonical_uuid(value):
    if type(value) is not str:
        raise ResetRefused('operation_id debe ser UUID canónico')
    try: valid = str(uuid.UUID(value)) == value
    except ValueError: valid = False
    if not valid: raise ResetRefused('operation_id debe ser UUID canónico')
    return value

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def safe_key(key):
    if (type(key) is not str or not key or '\\' in key or ':' in key or
            any(ord(c) < 32 or ord(c) == 127 for c in key)):
        raise ResetRefused('ruta relativa inválida')
    p = PurePosixPath(key)
    if p.is_absolute() or '..' in p.parts or str(p) != key or key == '.':
        raise ResetRefused('ruta relativa insegura')
    return p.parts

def validate_reference(table, row_id, column, key):
    if type(row_id) is not str or not row_id:
        raise ResetRefused('identidad de referencia inválida')
    if (table, column) not in {(t, c) for t, _, c, _, _ in STORAGE_COLUMNS}:
        raise ResetRefused('tabla o columna de referencia inválida')
    namespace = namespace_for(key)
    if key == namespace or namespace != {
        'microscopy_images': 'microscopy-images', 'cell_crops': 'cell-crops',
        'cell_explanations': 'cell-explanations',
    }[table]:
        raise ResetRefused('namespace incompatible con tabla')

def require_missing(root, references):
    """Probe exact components with no-follow stat; never open a missing target.

    Parent descriptors are pinned for confinement. There is no enumeration,
    content read, alternate root, or deletion for these references.
    """
    with directory_fd(root) as root_fd:
        for reference in references:
            parts = safe_key(reference['storage_key'])
            fd = os.dup(root_fd)
            try:
                for index, part in enumerate(parts):
                    try: info = os.stat(part, dir_fd=fd, follow_symlinks=False)
                    except FileNotFoundError: break
                    if index == len(parts) - 1:
                        raise ResetRefused('STORAGE_FILE_CHANGED: missing_before_reset apareció')
                    if not stat.S_ISDIR(info.st_mode):
                        raise ResetRefused('STORAGE_FILE_CHANGED: ancestro inseguro')
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    os.close(fd); fd = child
            finally:
                os.close(fd)

@contextmanager
def directory_fd(path, create=False):
    """Walk every ancestor using pinned descriptors; never follow a symlink."""
    if not path.is_absolute():
        raise ResetRefused('ruta raíz debe ser absoluta')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            if part in ('.', '..'): raise ResetRefused('ruta insegura')
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                    os.fsync(fd)
                except FileExistsError: pass
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = new
        yield fd
    finally:
        os.close(fd)

def reject_unsupported(root):
    with directory_fd(root) as fd:
        if any(name.endswith('-cleanup-pending.json') for name in os.listdir(fd)):
            raise ResetRefused('formato de recuperación no soportado; conservar evidencia')

def operation_path(root, operation_id):
    canonical_uuid(operation_id)
    return root / '.staging' / 'smear-reset' / operation_id / 'manifest.json'

def digest_row(row):
    return hashlib.sha256(json.dumps(dict(row), default=str, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()

def row_snapshot(connection, table):
    rows = connection.execute(text(f'SELECT * FROM "{table}"')).mappings().all()
    return sorted([{'id': str(row.get('id', digest_row(row))), 'sha256': digest_row(row)}
                   for row in rows], key=lambda x: (x['id'], x['sha256']))

def database_identity(url):
    return {'host': 'db', 'port': 5432, 'database': url.database,
            'username': url.username, 'schema': ALLOWED_SCHEMA}

def database_snapshot(connection, url):
    validate_identity(connection, url)
    return {'database_identity': database_identity(url), 'alembic_revision': EXPECTED_HEAD,
            'target_tables': {t: row_snapshot(connection, t) for t in DELETE_ORDER},
            'audit_events': row_snapshot(connection, 'audit_events'),
            'preserved_tables': fingerprint(connection),
            'admin_fingerprint': admin_fingerprint(connection),
            'release_fingerprint': release_fingerprint(connection)}

def database_state(payload, current):
    before = payload['database_before']
    after = dict(before, target_tables={t: [] for t in DELETE_ORDER},
                 audit_events=[r for r in before['audit_events']
                               if r['id'] not in payload['clinical_audit_events']['ids']])
    # An empty target set is ambiguous: never infer a commit from no evidence.
    if current == before: return 'before'
    if current == after: return 'after'
    return 'mixed'

def require_after(payload, current):
    expected = dict(payload['database_before'], target_tables={t: [] for t in DELETE_ORDER},
                    audit_events=[r for r in payload['database_before']['audit_events']
                                  if r['id'] not in payload['clinical_audit_events']['ids']])
    if current != expected: raise ResetRefused('DATABASE_STATE_MIXED')

def file_metadata(fd):
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode): raise ResetRefused('archivo no regular')
    digest = hashlib.sha256()
    while chunk := os.read(fd, 1024 * 1024): digest.update(chunk)
    after = os.fstat(fd)
    attrs = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_uid', 'st_gid', 'st_mode')
    if any(getattr(before, k) != getattr(after, k) for k in attrs):
        raise ResetRefused('archivo cambió durante lectura')
    return dict(size=after.st_size, sha256=digest.hexdigest(), uid=after.st_uid,
                gid=after.st_gid, mode=stat.S_IMODE(after.st_mode), inode=after.st_ino,
                device=after.st_dev, mtime_ns=after.st_mtime_ns)

def storage_inventory(root, missing=()):
    require_missing(root, missing)
    forbidden = {x['storage_key'] for x in missing}
    result = {}
    def walk(fd, prefix=''):
        for name in sorted(os.listdir(fd)):
            key = prefix + name
            if key == '.staging/smear-reset': continue
            if key in forbidden:
                raise ResetRefused('STORAGE_FILE_CHANGED: missing_before_reset apareció')
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try: walk(child, key + '/')
                finally: os.close(child)
            elif stat.S_ISREG(info.st_mode):
                child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
                try: result[key] = file_metadata(child)
                finally: os.close(child)
            else: raise ResetRefused('STORAGE_FILE_CHANGED: archivo especial o symlink: ' + key)
    with directory_fd(root) as fd: walk(fd)
    return result

def _fields(value, names):
    if type(value) is not dict or set(value) != set(names):
        raise ResetRefused('campos de manifiesto inválidos')

def _digest(value, length=64):
    if type(value) is not str or re.fullmatch('[0-9a-f]{%d}' % length, value) is None:
        raise ResetRefused('fingerprint inválido')

def _rows(rows):
    if type(rows) is not list: raise ResetRefused('filas inválidas')
    for row in rows:
        _fields(row, ('id', 'sha256'))
        if type(row['id']) is not str or not row['id']: raise ResetRefused('ID inválido')
        _digest(row['sha256'])
    if rows != sorted(rows, key=lambda r: (r['id'], r['sha256'])) or len({r['id'] for r in rows}) != len(rows):
        raise ResetRefused('filas duplicadas o desordenadas')

def _metadata(value):
    _fields(value, ('size', 'sha256', 'uid', 'gid', 'mode', 'inode', 'device', 'mtime_ns'))
    _digest(value['sha256'])
    for k in set(value) - {'sha256'}:
        if type(value[k]) is not int or value[k] < 0: raise ResetRefused('metadata inválida')
    if value['mode'] > 0o7777: raise ResetRefused('permisos inválidos')

def validate_manifest(p):
    _fields(p, ('manifest_version', 'operation_id', 'state', 'created_at', 'updated_at',
                'backup', 'database_before', 'clinical_audit_events', 'storage_files',
                'storage_missing', 'storage_targets_sha256', 'storage_preserved'))
    if type(p['manifest_version']) is not int or p['manifest_version'] != MANIFEST_VERSION:
        raise ResetRefused('versión no soportada')
    canonical_uuid(p['operation_id'])
    if type(p['state']) is not str or p['state'] not in STATES: raise ResetRefused('estado inválido')
    times = []
    for k in ('created_at', 'updated_at'):
        if type(p[k]) is not str: raise ResetRefused('timestamp inválido')
        dt = datetime.fromisoformat(p[k])
        if dt.tzinfo is None or dt.utcoffset() != timedelta(0): raise ResetRefused('timestamp debe ser UTC')
        times.append(dt)
    if times[1] < times[0]: raise ResetRefused('timestamps invertidos')
    b = p['backup']; _fields(b, ('path', 'size', 'sha256'))
    if type(b['path']) is not str or not Path(b['path']).is_absolute() or '..' in Path(b['path']).parts:
        raise ResetRefused('backup inválido')
    if type(b['size']) is not int or b['size'] < 1024: raise ResetRefused('backup vacío')
    _digest(b['sha256'])
    db = p['database_before']
    _fields(db, ('database_identity', 'alembic_revision', 'target_tables', 'audit_events',
                 'preserved_tables', 'admin_fingerprint', 'release_fingerprint'))
    identity = db['database_identity']; _fields(identity, ('host', 'port', 'database', 'username', 'schema'))
    if identity['host'] != 'db' or type(identity['port']) is not int or identity['port'] != 5432 or identity['schema'] != 'public':
        raise ResetRefused('identidad inválida')
    for k in ('database', 'username'):
        if type(identity[k]) is not str or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$-]{0,62}', identity[k]) is None:
            raise ResetRefused('identidad no sanitizada')
    if db['alembic_revision'] != EXPECTED_HEAD: raise ResetRefused('Alembic incompatible')
    _fields(db['target_tables'], DELETE_ORDER)
    for rows in db['target_tables'].values(): _rows(rows)
    _rows(db['audit_events'])
    _fields(db['preserved_tables'], PRESERVED_TABLES)
    for value in db['preserved_tables'].values(): _digest(value, 32)
    _digest(db['admin_fingerprint'], 32)
    _fields(db['release_fingerprint'], ('productive_train_id', 'fingerprint'))
    canonical_uuid(db['release_fingerprint']['productive_train_id']); _digest(db['release_fingerprint']['fingerprint'])
    audit = p['clinical_audit_events']; _fields(audit, ('ids', 'fingerprints'))
    if type(audit['ids']) is not list or any(type(x) is not str for x in audit['ids']) or len(set(audit['ids'])) != len(audit['ids']):
        raise ResetRefused('auditoría duplicada')
    _fields(audit['fingerprints'], audit['ids'])
    all_audit = {r['id'] for r in db['audit_events']}
    for k, v in audit['fingerprints'].items():
        canonical_uuid(k); _digest(v)
        if k not in all_audit: raise ResetRefused('auditoría fuera de targets')
    if type(p['storage_files']) is not list: raise ResetRefused('archivos inválidos')
    seen = set()
    references = set()
    for value in p['storage_files']:
        _fields(value, ManifestEntry.__dataclass_fields__)
        key = value['storage_key']; namespace = namespace_for(key)
        if key == namespace or value['namespace'] != namespace or key in seen: raise ResetRefused('archivo duplicado o namespace inválido')
        seen.add(key)
        if value['classification'] != 'canonical_present': raise ResetRefused('clasificación inválida')
        _metadata({k: value[k] for k in ('size', 'sha256', 'uid', 'gid', 'mode', 'inode', 'device', 'mtime_ns')})
        if value['table'] == 'clinical_staging':
            if not namespace.startswith('.staging/') or value['row_id'] != key or value['column'] != '': raise ResetRefused('staging inválido')
        elif type(value['table']) is not str or value['table'] not in {x[0] for x in STORAGE_COLUMNS} or value['row_id'] not in {r['id'] for r in db['target_tables'][value['table']]}:
            raise ResetRefused('archivo fuera de targets')
        elif namespace != {'microscopy_images': 'microscopy-images', 'cell_crops': 'cell-crops', 'cell_explanations': 'cell-explanations'}[value['table']]:
            raise ResetRefused('namespace incompatible con tabla')
        else:
            validate_reference(value['table'], value['row_id'], value['column'], key)
            reference = (value['table'], value['row_id'], value['column'])
            if reference in references: raise ResetRefused('referencia duplicada')
            references.add(reference)
    if type(p['storage_missing']) is not list: raise ResetRefused('referencias ausentes inválidas')
    for value in p['storage_missing']:
        _fields(value, MissingReference.__dataclass_fields__)
        validate_reference(value['table'], value['row_id'], value['column'], value['storage_key'])
        validate_expected_metadata(value['expected_size'], value['expected_sha256'])
        if value['classification'] != 'missing_before_reset' or value['reason'] != 'absent_from_canonical_storage':
            raise ResetRefused('clasificación o motivo inválido')
        reference = (value['table'], value['row_id'], value['column'])
        if value['storage_key'] in seen or reference in references:
            raise ResetRefused('referencia duplicada entre categorías')
        seen.add(value['storage_key']); references.add(reference)
        if value['row_id'] not in {r['id'] for r in db['target_tables'][value['table']]}:
            raise ResetRefused('referencia ausente fuera de targets')
    expected_references = {(t, r['id'], c) for t, _, c, _, _ in STORAGE_COLUMNS
                           for r in db['target_tables'][t]}
    if references != expected_references: raise ResetRefused('referencias incompletas o targets ampliados')
    if type(p['storage_preserved']) is not dict: raise ResetRefused('inventario inválido')
    for key, value in p['storage_preserved'].items():
        safe_key(key); _metadata(value)
        if key in seen or key.startswith('.staging/smear-reset/'): raise ResetRefused('inventario incompatible')
    _digest(p['storage_targets_sha256'])
    if p['storage_targets_sha256'] != storage_targets_digest(p):
        raise ResetRefused('targets modificados')
    return p

def storage_targets_digest(payload):
    return digest_row({k: payload[k] for k in
                       ('database_before', 'storage_files', 'storage_missing', 'storage_preserved')})

def read_manifest(path):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result: raise ResetRefused('campo JSON duplicado')
            result[k] = v
        return result
    with directory_fd(path.parent) as parent:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
        with os.fdopen(fd) as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
                raise ResetRefused('manifiesto no regular o no privado')
            p = validate_manifest(json.load(stream, object_pairs_hook=pairs))
    if p['operation_id'] != path.parent.name: raise ResetRefused('operation_id diferente')
    return p

def _atomic_manifest(path, payload):
    validate_manifest(payload)
    if path.parent.name != payload['operation_id']: raise ResetRefused('operation_id diferente')
    with directory_fd(path.parent, create=True) as parent:
        tmp = '.manifest-' + str(uuid.uuid4()) + '.tmp'
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            with os.fdopen(fd, 'w') as stream:
                os.fchmod(stream.fileno(), 0o600)
                json.dump(payload, stream, sort_keys=True)
                stream.flush(); os.fsync(stream.fileno())
            os.replace(tmp, path.name, src_dir_fd=parent, dst_dir_fd=parent)
            os.fsync(parent)
        finally:
            try: os.unlink(tmp, dir_fd=parent)
            except FileNotFoundError: pass
    if read_manifest(path) != payload: raise ResetRefused('manifiesto no verificable')

def transition(path, payload, state):
    if state not in TRANSITIONS[payload['state']]: raise ResetRefused('transición inválida')
    if read_manifest(path) != payload: raise ResetRefused('manifiesto cambió')
    updated = dict(payload, state=state, updated_at=utc_now())
    _atomic_manifest(path, updated)
    return updated

def backup_identity(path):
    validate_backup(path)
    with directory_fd(path.parent) as parent:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
        try: metadata = file_metadata(fd)
        finally: os.close(fd)
    return {'path': str(path), 'size': metadata['size'], 'sha256': metadata['sha256']}

def write_operation_manifest(root, manifest, audit, before, backup, missing=()):
    reject_unsupported(root)
    missing = [asdict(x) for x in missing]
    files = [asdict(x) for x in manifest]
    inventory = validated_inventory(root, files, missing)
    now = utc_now(); operation_id = str(uuid.uuid4())
    payload = {'manifest_version': MANIFEST_VERSION, 'operation_id': operation_id,
               'state': 'prepared', 'created_at': now, 'updated_at': now,
               'backup': backup, 'database_before': before,
               'clinical_audit_events': {k: audit[k] for k in ('ids', 'fingerprints')},
               'storage_files': files,
               'storage_missing': missing,
               'storage_preserved': {k: v for k, v in inventory.items() if k not in {x.storage_key for x in manifest}}}
    payload['storage_targets_sha256'] = storage_targets_digest(payload)
    path = operation_path(root, operation_id)
    _atomic_manifest(path, payload)
    return path

def validated_inventory(root, files, missing):
    inventory = storage_inventory(root, missing)
    for item in files:
        expected = {k: item[k] for k in inventory.get(item['storage_key'], {})}
        if inventory.get(item['storage_key']) != expected or not expected: raise ResetRefused('STORAGE_FILE_CHANGED')
    return inventory

def delete_manifest_files(root, manifest):
    deleted = 0
    for item in manifest:
        namespace_for(item.storage_key)
        parts = safe_key(item.storage_key)
        try:
            with directory_fd(root.joinpath(*parts[:-1])) as parent:
                try: fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
                except FileNotFoundError: continue
                try: current = file_metadata(fd)
                finally: os.close(fd)
                expected = {k: getattr(item, k) for k in current}
                if current != expected: return deleted, [item.storage_key + ': STORAGE_FILE_CHANGED']
                info = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
                if (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_size) != (item.device, item.inode, item.mtime_ns, item.size):
                    return deleted, [item.storage_key + ': STORAGE_FILE_CHANGED']
                os.unlink(parts[-1], dir_fd=parent); os.fsync(parent); deleted += 1
        except FileNotFoundError: continue
        except (OSError, ResetRefused): return deleted, [item.storage_key + ': STORAGE_FILE_CHANGED']
    return deleted, []

def check_preserved_storage(root, payload, baseline=None):
    current = storage_inventory(root, payload['storage_missing'])
    expected = payload['storage_preserved'] if baseline is None else baseline
    if any(current.get(k) != v for k, v in expected.items()):
        raise ResetRefused('STORAGE_FILE_CHANGED: archivo preservado')
    targets = {x['storage_key'] for x in payload['storage_files']}
    return {k: v for k, v in current.items() if k not in targets}

def remove_empty_directories(root, files):
    directories = set()
    for item in files:
        parent = PurePosixPath(item['storage_key']).parent
        while str(parent) != item['namespace']:
            directories.add(str(parent)); parent = parent.parent
    for key in sorted(directories, key=lambda k: (-k.count('/'), k)):
        parts = safe_key(key)
        try:
            with directory_fd(root.joinpath(*parts[:-1])) as fd:
                os.rmdir(parts[-1], dir_fd=fd); os.fsync(fd)
        except FileNotFoundError: pass
        except OSError as exc:
            if exc.errno not in (errno.ENOTEMPTY, errno.EEXIST): raise

def remove_completed_manifest(path, payload):
    if payload['state'] != 'cleanup_completed' or read_manifest(path) != payload:
        raise ResetRefused('manifiesto no completado')
    with directory_fd(path.parent) as fd:
        os.unlink(path.name, dir_fd=fd); os.fsync(fd)
    with directory_fd(path.parent.parent) as fd:
        try: os.rmdir(path.parent.name, dir_fd=fd); os.fsync(fd)
        except OSError as exc:
            if exc.errno not in (errno.ENOTEMPTY, errno.EEXIST): raise

def resume_cleanup(engine, root, backup, operation_id):
    reject_unsupported(root)
    path = operation_path(root, operation_id)
    payload = read_manifest(path)
    url = validate_url(os.environ['DATABASE_URL'])
    if payload['database_before']['database_identity'] != database_identity(url):
        raise ResetRefused('operación asociada a otra base')
    if backup_identity(backup) != payload['backup']: raise ResetRefused('backup diferente')
    if payload['state'] in ('blocked', 'aborted_before_commit'):
        raise ResetRefused('operación terminal: ' + payload['state'])
    with engine.connect() as connection:
        with connection.begin():
            connection.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            connection.execute(text("SET LOCAL statement_timeout='30s'; SET LOCAL lock_timeout='2s'"))
            # Cooperative lock serializes reset/recovery; table locks exclude scientific writers.
            connection.execute(text("SELECT pg_advisory_xact_lock(736321904)"))
            for table in sorted(TARGET_TABLES | set(PRESERVED_TABLES) | {'audit_events', 'alembic_version'}):
                connection.execute(text(f'LOCK TABLE "{table}" IN SHARE MODE'))
            validate_schema(connection); detect_active_work(connection)
            current = database_snapshot(connection, url)
            if payload['state'] == 'prepared':
                state = database_state(payload, current)
                if state == 'before':
                    inventory = storage_inventory(root, payload['storage_missing'])
                    expected = dict(payload['storage_preserved'])
                    for item in payload['storage_files']:
                        expected[item['storage_key']] = {k: item[k] for k in ('size', 'sha256', 'uid', 'gid', 'mode', 'inode', 'device', 'mtime_ns')}
                    if inventory != expected: raise ResetRefused('STORAGE_FILE_CHANGED')
                    transition(path, payload, 'aborted_before_commit')
                    return {'status': 'RESET_NOT_COMMITTED_NO_STORAGE_CLEANUP', 'storage_files_deleted': 0}
                if state == 'mixed':
                    transition(path, payload, 'blocked')
                    raise ResetRefused('DATABASE_STATE_MIXED')
                payload = transition(path, payload, 'database_committed')
            require_after(payload, current)
            validate_preserved_storage_references(connection, {x['storage_key'] for x in
                                                  [*payload['storage_files'], *payload['storage_missing']]})
            baseline = check_preserved_storage(root, payload)
            if payload['state'] != 'cleanup_completed' and payload['storage_files']:
                payload = transition(path, payload, 'cleanup_pending')
            if payload['state'] == 'cleanup_completed':
                if any(x['storage_key'] in storage_inventory(root, payload['storage_missing']) for x in payload['storage_files']):
                    raise ResetRefused('STORAGE_FILE_CHANGED: operación completada')
                remove_completed_manifest(path, payload)
                return {'status': 'CLEANUP_COMPLETE', 'storage_files_deleted': 0}
            if read_manifest(path) != payload: raise ResetRefused('manifiesto cambió')
            deleted, conflicts = delete_manifest_files(root, [ManifestEntry(**x) for x in payload['storage_files']])
            if conflicts:
                return {'status': 'DATABASE_RESET_STORAGE_CLEANUP_PENDING', 'operation_id': operation_id,
                        'storage_files_deleted': deleted, 'conflicts': conflicts}
            require_after(payload, database_snapshot(connection, url))
            check_preserved_storage(root, payload, baseline)
            inventory = storage_inventory(root, payload['storage_missing'])
            if any(x['storage_key'] in inventory for x in payload['storage_files']): raise ResetRefused('STORAGE_FILE_CHANGED')
            remove_empty_directories(root, payload['storage_files'])
            payload = transition(path, payload, 'cleanup_completed')
            remove_completed_manifest(path, payload)
            return {'status': 'CLEANUP_COMPLETE', 'storage_files_deleted': deleted,
                    'additional_files': sorted(set(baseline) - set(payload['storage_preserved']))}

def validate_url(database_url: str):
    url = make_url(database_url)
    if url.drivername not in {"postgresql", "postgresql+psycopg"} or url.host != "db" or (url.port or 5432) != 5432:
        raise ResetRefused("DATABASE_URL debe apuntar a PostgreSQL db:5432")
    if not url.database or not url.username:
        raise ResetRefused("identidad configurada incompleta")
    return url

def validate_identity(connection: Connection, url) -> None:
    row = connection.execute(text("SELECT current_database(), current_user, current_schema()" )).one()
    if row[0] != url.database or row[1] != url.username or row[2] != ALLOWED_SCHEMA:
        raise ResetRefused("identidad PostgreSQL no coincide con la configuración canónica")
    revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    if revision != EXPECTED_HEAD:
        raise ResetRefused("Alembic current no coincide con repository head")
    admins = connection.execute(text("""
        SELECT u.status, count(*) OVER () AS total
        FROM users u JOIN user_roles ur ON ur.user_id=u.id JOIN roles r ON r.id=ur.role_id
        WHERE lower(u.email)='admin@capstone.local' AND u.username='admin' AND r.name='administrator'
    """)).all()
    if len(admins) != 1 or admins[0].status != "active":
        raise ResetRefused("se requiere exactamente un admin@capstone.local activo con rol administrator")

def validate_schema(connection: Connection) -> None:
    tables = set(connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")).scalars())
    missing = TARGET_TABLES.union(PRESERVED_TABLES) - tables
    if missing:
        raise ResetRefused("tablas requeridas ausentes: " + ", ".join(sorted(missing)))
    unknown = connection.execute(text("""
      SELECT DISTINCT child.relname
      FROM pg_constraint c JOIN pg_class child ON child.oid=c.conrelid
      JOIN pg_namespace n ON n.oid=child.relnamespace
      WHERE c.contype='f' AND n.nspname='public'
        AND c.confrelid = ANY(ARRAY(SELECT to_regclass('public.' || x) FROM unnest(CAST(:targets AS text[])) x))
        AND NOT (child.relname = ANY(:targets))
    """), {"targets": list(TARGET_TABLES)}).scalars().all()
    allowed = {name for name in unknown if name.startswith("scientific_validation_")}
    if set(unknown) - allowed:
        raise ResetRefused("foreign key desconocida hacia dominio clínico: " + ", ".join(sorted(set(unknown)-allowed)))
    if allowed:
        linked = connection.execute(text("""
          SELECT (SELECT count(*) FROM scientific_validation_images)
               + (SELECT count(*) FROM scientific_validation_detection_runs)
               + (SELECT count(*) FROM scientific_validation_classification_runs)
               + (SELECT count(*) FROM scientific_validation_annotations
                   WHERE cell_detection_id IS NOT NULL OR analysis_run_id IS NOT NULL)
        """)).scalar_one()
        if linked:
            raise ResetRefused("la validación científica preservada referencia análisis clínicos")

def detect_active_work(connection: Connection) -> None:
    checks = (
        ("runs", "status", ("created", "pending", "queued", "running", "processing")),
        ("image_analysis_jobs", "status", ("pending", "queued", "running", "processing")),
        ("image_ingestion_batches", "status", ("pending", "incomplete")),
        ("microscopy_analysis_runs", "run_status", ("created", "quality_pending", "quality_processing")),
        ("quality_assessment_queue_items", "status", ("queued", "running")),
        ("image_quality_assessments", "assessment_status", ("pending", "processing")),
        ("cell_detection_runs", "status", ("created", "processing")),
        ("cell_classification_runs", "status", ("created", "processing")),
    )
    for table, column, states in checks:
        count = connection.execute(text(f'SELECT count(*) FROM "{table}" WHERE "{column}" = ANY(:states)'), {"states": list(states)}).scalar_one()
        if count:
            raise ResetRefused(f"trabajo activo detectado en {table}")

def validate_backup(path: Path | None) -> None:
    if path is None or not path.is_absolute() or not path.is_file() or path.is_symlink() or path.stat().st_size < 1024:
        raise ResetRefused("backup PostgreSQL durable, absoluto y no vacío requerido")
    with directory_fd(path.parent):
        pass
    with path.open("rb") as stream:
        data = stream.read(5)
    if data != b"PGDMP":
        raise ResetRefused("backup PostgreSQL custom-format inválido")
    with directory_fd(path.parent):
        pass
    if not os.access(path, os.R_OK) or not (os.statvfs(path).f_flag & os.ST_RDONLY):
        raise ResetRefused("backup debe estar en un mount durable de solo lectura")
    pg_restore = shutil.which("pg_restore")
    if not pg_restore:
        raise ResetRefused("pg_restore no está disponible en el contenedor")
    checked = subprocess.run([pg_restore, "--list", str(path)], capture_output=True,
                             text=True, timeout=30, check=False)
    if checked.returncode or any(f" TABLE DATA public {table} " not in checked.stdout for table in ("alembic_version", "users", "runs", "model_versions")):
        raise ResetRefused("backup no es restaurable o no contiene las tablas preservadas")

def validate_preserved_storage_references(connection, storage_keys):
    for table in PRESERVED_TABLES:
        for row in connection.execute(text(f'SELECT * FROM "{table}"')).mappings():
            if _json_scalars(dict(row), nested=True) & storage_keys:
                raise ResetRefused('registro preservado requiere archivo objetivo')

def plan(connection: Connection, root: Path) -> tuple[dict[str, int], StoragePlan, dict[str, str], dict[str, Any], dict[str, Any]]:
    validate_schema(connection); detect_active_work(connection)
    clinical_ids, storage_keys = clinical_references(connection)
    validate_scientific_validation(connection, clinical_ids, storage_keys)
    counts = {table: connection.execute(text(f'SELECT count(*) FROM "{table}"')).scalar_one() for table in DELETE_ORDER}
    files = build_manifest(connection, root)
    validate_preserved_storage_references(connection, files.keys)
    return counts, files, fingerprint(connection), audit_plan(connection, clinical_ids, storage_keys), release_fingerprint(connection)

def plan_summary(root, counts, storage, audit, release):
    inventory = validated_inventory(root, [asdict(x) for x in storage.files],
                                    [asdict(x) for x in storage.missing])
    present = sum(x.table != 'clinical_staging' for x in storage.files)
    return {
        'status': 'DRY_RUN', 'changed': False, 'rows_by_table': counts,
        'clinical_database_references': present + len(storage.missing),
        'canonical_present': present, 'missing_before_reset': len(storage.missing),
        'invalid_or_unsafe': 0, 'ambiguous': 0,
        'physical_delete_targets': len(storage.files),
        'database_delete_targets': sum(counts.values()) + len(audit.get('ids', [])),
        'preserved_storage_files': len(set(inventory) - {x.storage_key for x in storage.files}),
        'missing_references': [asdict(x) for x in storage.missing],
        'files': len(storage.files), 'bytes': sum(x.size for x in storage.files),
        'audit': audit['counts'], 'productive_train_id': release['productive_train_id'],
    }

def execute_reset(engine, root: Path, backup: Path) -> dict[str, Any]:
    backup_record = backup_identity(backup)
    reject_unsupported(root)
    operations = root / '.staging' / 'smear-reset'
    try:
        with directory_fd(operations) as fd:
            if os.listdir(fd): raise ResetRefused('operación anterior requiere revisión o recuperación')
    except FileNotFoundError: pass
    with engine.connect() as connection:
        tx = connection.begin()
        try:
            connection.execute(text("SET LOCAL statement_timeout='30s'; SET LOCAL lock_timeout='2s'"))
            url = validate_url(os.environ["DATABASE_URL"]); validate_identity(connection, url)
            connection.execute(text("SELECT pg_advisory_xact_lock(736321904)"))
            for table in sorted(TARGET_TABLES | set(PRESERVED_TABLES) | {'audit_events', 'alembic_version'}):
                connection.execute(text(f'LOCK TABLE "{table}" IN SHARE ROW EXCLUSIVE MODE'))
            counts, manifest, before, audit, release = plan(connection, root)
            admin_before = admin_fingerprint(connection)
            snapshot = database_snapshot(connection, url)
            operation = write_operation_manifest(root, manifest.files, audit, snapshot, backup_record,
                                                 missing=manifest.missing)
            for table in reversed(DELETE_ORDER):
                connection.execute(text(f'LOCK TABLE "{table}" IN SHARE ROW EXCLUSIVE MODE'))
            for table in DELETE_ORDER:
                connection.execute(text(f'ALTER TABLE "{table}" DISABLE TRIGGER USER'))
            if audit["ids"]:
                revalidate_audit_plan(connection, audit)
                connection.execute(text('ALTER TABLE audit_events DISABLE TRIGGER USER'))
            deleted = 0
            for table in DELETE_ORDER:
                deleted += connection.execute(text(f'DELETE FROM "{table}"')).rowcount
            if audit["ids"]:
                deleted += connection.execute(text("DELETE FROM audit_events WHERE id = ANY(:ids)"), {"ids": audit["ids"]}).rowcount
                connection.execute(text('ALTER TABLE audit_events ENABLE TRIGGER USER'))
            for table in reversed(DELETE_ORDER):
                connection.execute(text(f'ALTER TABLE "{table}" ENABLE TRIGGER USER'))
            if any(connection.execute(text(f'SELECT count(*) FROM "{t}"')).scalar_one() for t in DELETE_ORDER):
                raise ResetRefused("validación interna: dominio clínico no quedó vacío")
            if before != fingerprint(connection) or admin_before != admin_fingerprint(connection) or release != release_fingerprint(connection):
                raise ResetRefused("fingerprint preservado cambió dentro de la transacción")
            validate_identity(connection, url)
            tx.commit()
        except BaseException:
            if tx.is_active: tx.rollback()
            raise
    payload = read_manifest(operation)
    transition(operation, payload, "database_committed")
    result = resume_cleanup(engine, root, backup, operation.parent.name)
    result['database_rows_deleted'] = deleted
    return result

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirmation")
    parser.add_argument("--backup", type=Path)
    modes.add_argument("--resume-cleanup", action="store_true")
    parser.add_argument("--operation-id")
    return parser.parse_args(argv)

def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        database_url = os.environ.get("DATABASE_URL")
        root_value = os.environ.get("STORAGE_ROOT")
        if not database_url or not root_value: raise ResetRefused("DATABASE_URL y STORAGE_ROOT son obligatorios")
        url = validate_url(database_url); root = Path(root_value)
        if args.resume_cleanup:
            canonical_uuid(args.operation_id)
        elif args.operation_id is not None:
            raise ResetRefused('--operation-id requiere --resume-cleanup')
        reject_unsupported(root)
        engine = create_engine(database_url, future=True)
        if args.resume_cleanup:
            if args.execute: raise ResetRefused("--execute y --resume-cleanup son excluyentes")
            if os.environ.get("SMEAR_RESET_ALLOW_EXECUTION") != "1": raise ResetRefused("falta SMEAR_RESET_ALLOW_EXECUTION=1")
            if args.confirmation != CONFIRMATION: raise ResetRefused("confirmación textual incorrecta")
            result = resume_cleanup(engine, root, args.backup, args.operation_id)
        elif args.execute:
            if os.environ.get("SMEAR_RESET_ALLOW_EXECUTION") != "1": raise ResetRefused("falta SMEAR_RESET_ALLOW_EXECUTION=1")
            if args.confirmation != CONFIRMATION: raise ResetRefused("confirmación textual incorrecta")
            result = execute_reset(engine, root, args.backup)
        else:
            if args.confirmation or args.backup: raise ResetRefused("--confirmation/--backup sólo son válidos con --execute")
            with engine.connect() as connection:
                tx = connection.begin()
                try:
                    connection.execute(text("SET TRANSACTION READ ONLY; SET LOCAL statement_timeout='10s'; SET LOCAL lock_timeout='2s'"))
                    validate_identity(connection, url)
                    counts, manifest, _, audit, release = plan(connection, root)
                    result = plan_summary(root, counts, manifest, audit, release)
                finally:
                    tx.rollback()
        print(json.dumps(result, sort_keys=True, indent=2)); return 0
    except (KeyError, TypeError, OSError, ValueError, ResetRefused, SQLAlchemyError) as exc:
        # Exception messages may contain a DSN, SQL parameters or absolute paths.
        category = exc.classification if isinstance(exc, StorageRefused) else 'preflight_or_recovery_guard'
        print('RESET_REFUSED: ' + category, file=sys.stderr); return 2

if __name__ == "__main__":
    raise SystemExit(main())
