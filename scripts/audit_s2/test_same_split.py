"""S2 contracts on real read-only sources; PostgreSQL writes always roll back."""
from __future__ import annotations
import os
import json
from uuid import uuid5
from dataclasses import replace
from pathlib import Path
from collections import Counter

import pytest
from sqlalchemy import text

from malaria_split.persistence.database import create_postgresql_engine
from malaria_split.persistence import same_split
from malaria_split.persistence.same_split import persist_same_split, preflight
from malaria_split.persistence.split_generation import _bulk_insert

VERSION_ID = uuid5(same_split.VERSION_ID, "rollback-test")


@pytest.fixture(autouse=True)
def isolated_version(monkeypatch):
    monkeypatch.setattr(same_split, "VERSION_ID", VERSION_ID)
from malaria_split.sources.thin_blood_smears_pf import inspect_thin_blood_smears_pf
from malaria_split.splitting.same_split import SameSplitConflict, inherit_patient_assignments, check_audited_distribution


@pytest.mark.parametrize('split', ['train', 'val', 'test'])
def test_inheritance(split: str) -> None:
    assert inherit_patient_assignments({'smear': 'key'}, [('key', split)]) == {'smear': split}


@pytest.mark.parametrize('keys,reference,reason', [
    ({'smear': 'key'}, [], 'NO_ASSIGNMENT'),
    ({'smear': 'key'}, [('key', 'train'), ('key', 'val')], 'ambiguous'),
    ({'smear': 'key', 'other': 'key'}, [('key', 'train')], 'collision'),
    ({'smear': 'key'}, [('key', 'invalid')], 'invalid'),
])
def test_fail_closed(keys: dict, reference: list, reason: str) -> None:
    with pytest.raises(SameSplitConflict, match=reason):
        inherit_patient_assignments(keys, reference)


def test_determinism() -> None:
    keys = {'b': 'B', 'a': 'A'}
    reference = [('A', 'train'), ('B', 'test'), ('A', 'train')]
    assert inherit_patient_assignments(keys, reference) == inherit_patient_assignments(dict(reversed(list(keys.items()))), reversed(reference))


def test_distribution_stop() -> None:
    with pytest.raises(SameSplitConflict, match='distribution mismatch'):
        check_audited_distribution({'a': 'train'}, {'a'})


@pytest.fixture(scope='module')
def inspections() -> list:
    root = Path('/app/malaria_dl_local_project/data/NIH-NLM-ThinBloodSmearsPf')
    return [inspect_thin_blood_smears_pf(root, annotation_set=s) for s in ('Polygon Set', 'Point Set')]


@pytest.fixture(scope='module')
def engine():
    value = create_postgresql_engine(os.environ['DATABASE_URL'])
    yield value
    value.dispose()


@pytest.fixture
def db(engine):
    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()


def test_actual_preflight(db, inspections) -> None:
    plan = preflight(db, inspections)
    assert plan['patients'] == plan['canonical_ids'] == 193
    assert Counter(plan['patient_assignments'].values()) == {'train': 154, 'val': 19, 'test': 20}
    assert all(r.polygon_count == 0 and not r.label_counts for r in inspections[1].records)
    assert inspections[1].report()['polygons'] is None


def test_persistence_idempotency_grouping_leakage(db, inspections) -> None:
    first = persist_same_split(db, inspections)
    second = persist_same_split(db, list(reversed(inspections)))
    assert second['result'] == 'ALREADY_EXISTS_MATCH'
    assert first['patient_digest'] == second['patient_digest']
    assert first['record_digest'] == second['record_digest']
    rows = list(db.execute(text('SELECT clinical_identity_id,count(*),count(DISTINCT split_name) FROM dataset_split_assignments WHERE dataset_version_id=:id GROUP BY clinical_identity_id'), {'id': VERSION_ID}))
    assert len(rows) == 193 and all(count == 5 and splits == 1 for _, count, splits in rows)
    assert first['cross_family_mismatches'] == first['patient_overlap'] == 0
    assert db.execute(text('SELECT validated_at IS NULL AND frozen_at IS NULL FROM dataset_versions WHERE id=:id'), {'id': VERSION_ID}).scalar_one()


def test_conflict_is_explicit(db, inspections) -> None:
    persist_same_split(db, inspections)
    rows = [dict(r) for r in db.execute(text("SELECT id,dataset_version_id,source_record_id,clinical_identity_id,split_name,class_index,class_name,metadata FROM dataset_split_assignments WHERE dataset_version_id=:id AND clinical_identity_id=(SELECT clinical_identity_id FROM dataset_split_assignments WHERE dataset_version_id=:id AND split_name='val' LIMIT 1)"), {'id': VERSION_ID}).mappings()]
    db.execute(text('DELETE FROM dataset_split_assignments WHERE dataset_version_id=:id AND clinical_identity_id=:patient'), {'id': VERSION_ID, 'patient': rows[0]['clinical_identity_id']})
    _bulk_insert(db, tuple({**r, 'split_name': 'test', 'metadata': json.dumps(r['metadata'])} for r in rows))
    with pytest.raises(SameSplitConflict, match='CONFLICT: existing assignments'):
        persist_same_split(db, inspections)


def test_preflight_stops_before_writes(db, inspections) -> None:
    before = db.execute(text('SELECT count(*) FROM dataset_versions')).scalar_one()
    damaged = [replace(inspections[0], records=inspections[0].records[:-1]), inspections[1]]
    with pytest.raises(SameSplitConflict, match='five source records'):
        persist_same_split(db, damaged)
    assert db.execute(text('SELECT count(*) FROM dataset_versions')).scalar_one() == before


def test_atomicity(engine, inspections) -> None:
    # Run before committed S2. The real reference stays untouched; all inserts roll back.
    with engine.connect() as connection:
        exists = connection.execute(text('SELECT count(*) FROM dataset_versions WHERE id=:id'), {'id': VERSION_ID}).scalar_one()
        tables = ('datasets', 'clinical_identities', 'dataset_source_records', 'identity_evidence', 'dataset_versions', 'dataset_version_sources', 'dataset_split_assignments')
        before = {t: connection.execute(text(f'SELECT count(*) FROM {t}')).scalar_one() for t in tables}
    assert not exists
    def fail(connection) -> None:
        assert connection.execute(text('SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=:id'), {'id': VERSION_ID}).scalar_one() == 965
        raise RuntimeError('injected after assignments')
    with pytest.raises(RuntimeError, match='injected'):
        with engine.begin() as connection:
            persist_same_split(connection, inspections, failure_hook=fail)
    with engine.connect() as connection:
        after = {t: connection.execute(text(f'SELECT count(*) FROM {t}')).scalar_one() for t in tables}
    assert before == after


def test_canonical_collision_before_write(db, inspections) -> None:
    polygon = inspections[0]
    original, other = polygon.patients[:2]
    alias = ('999' if other[:3] != '999' else '998') + other[3:]
    records = tuple(replace(r, patient_id=alias) if r.patient_id == original else r for r in polygon.records)
    with pytest.raises(SameSplitConflict, match='collision'):
        persist_same_split(db, [replace(polygon, records=records), inspections[1]])
    assert db.execute(text('SELECT count(*) FROM dataset_versions WHERE id=:id'), {'id': VERSION_ID}).scalar_one() == 0


def test_distribution_mismatch_before_insert(db, inspections, monkeypatch) -> None:
    from sqlalchemy import event
    original = same_split.inherit_patient_assignments
    statements = []
    def changed(keys: dict, reference: list) -> dict:
        assignments = original(keys, reference)
        patient = next(p for p, s in assignments.items() if s == 'train')
        assignments[patient] = 'val'
        return assignments
    def capture(connection, cursor, statement, parameters, context, executemany) -> None:
        statements.append(statement)
    monkeypatch.setattr(same_split, 'inherit_patient_assignments', changed)
    event.listen(db, 'before_cursor_execute', capture)
    try:
        with pytest.raises(SameSplitConflict, match='distribution mismatch'):
            persist_same_split(db, inspections)
    finally:
        event.remove(db, 'before_cursor_execute', capture)
    assert not any(s.lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')) for s in statements)
