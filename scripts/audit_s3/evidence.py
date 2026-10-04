"""Read-only S3 evidence using existing canonical hashing and file inventory rules."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, text
from malaria_split.governance.freeze import _canonical_digest
from malaria_split.persistence.same_split import VERSION_ID, V1_ID
from malaria_split.sources.thin_blood_smears_pf import file_sha256

TABLES = ('datasets', 'dataset_version_sources', 'clinical_identities', 'dataset_source_records',
          'identity_evidence', 'dataset_split_assignments', 'dataset_materializations')


def inventory(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): file_sha256(p) for p in sorted(root.rglob('*')) if p.is_file()}


def protected_state(snapshot: dict[str, Any]) -> dict[str, Any]:
    versions = {str(V1_ID), str(VERSION_ID)}
    links = [r for r in snapshot['dataset_version_sources'] if str(r['dataset_version_id']) in versions]
    sources = {str(r['dataset_id']) for r in links}
    records = [r for r in snapshot['dataset_source_records'] if str(r['dataset_id']) in sources]
    record_ids = {str(r['id']) for r in records}
    groups = dict(
        cell_version=[snapshot['version']], sources=links, records=records,
        datasets=[r for r in snapshot['datasets'] if str(r['id']) in sources],
        identities=[r for r in snapshot['clinical_identities'] if str(r['dataset_id']) in sources],
        evidence=[r for r in snapshot['identity_evidence'] if str(r['source_record_id']) in record_ids],
        assignments=[r for r in snapshot['dataset_split_assignments'] if str(r['dataset_version_id']) in versions],
        materializations=[r for r in snapshot['dataset_materializations'] if str(r['dataset_version_id']) in versions])
    return {name: dict(count=len(rows), sha256=_canonical_digest([(line,) for line in sorted(
        json.dumps(r, sort_keys=True, default=str, separators=(',', ':')) for r in rows)])) for name, rows in groups.items()}


def snapshot_database(connection: Connection) -> dict[str, Any]:
    result = {t: [dict(r) for r in connection.execute(text('SELECT * FROM ' + t)).mappings()] for t in TABLES}
    result['version'] = dict(connection.execute(text('SELECT * FROM dataset_versions WHERE id=:id'), {'id': V1_ID}).mappings().one())
    # Match the S2 JSON snapshot's serialization of UUID, Decimal and timestamps.
    return json.loads(json.dumps(result, default=str))


def version_core(version: dict[str, Any]) -> dict[str, Any]:
    result = {k: v for k, v in version.items() if k not in ('status', 'validated_at', 'frozen_at')}
    result['methodology_json'] = {k: v for k, v in result['methodology_json'].items() if k != 'freeze_contract'}
    return json.loads(json.dumps(result, default=str))
