"""S3 source validation/lifecycle tests; every write rolls back on a cloned version."""
from __future__ import annotations

import contextlib
import json
import os
from dataclasses import replace
from pathlib import Path
from uuid import uuid4
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from malaria_split.governance.freeze import FreezeError, freeze_dataset_version, compute_final_fingerprints
from malaria_split.governance.trainability import logical_validation_passes, get_dataset_version_trainability
from malaria_split.persistence.database import create_postgresql_engine
from malaria_split.persistence.formal_validation import FormalValidationError, persist_formal_validation
from malaria_split.persistence.same_split import VERSION_ID, V1_ID
from malaria_split.persistence import smear_validation
from malaria_split.persistence.smear_validation import prepare_smear_validation
from malaria_split.persistence.split_generation import audit_persisted_assignments, _bulk_insert
from malaria_split.sources.thin_blood_smears_pf import inspect_thin_blood_smears_pf


@pytest.fixture(scope='module')
def inspections():
    root = Path('/app/malaria_dl_local_project/data/NIH-NLM-ThinBloodSmearsPf')
    return [inspect_thin_blood_smears_pf(root, annotation_set=s) for s in ('Polygon Set', 'Point Set')]


@pytest.fixture(scope='module')
def engine():
    value = create_postgresql_engine(os.environ['DATABASE_URL'])
    yield value
    value.dispose()


@pytest.fixture
def generated(engine, monkeypatch):
    with engine.connect() as connection:
        tx = connection.begin()
        version_id = uuid4()
        connection.execute(text('''
            INSERT INTO dataset_versions(id,name,semantic_version,status,grouping_strategy,grouping_field,
              stratification_strategy,split_algorithm,split_algorithm_version,random_seed,target_train_ratio,
              target_val_ratio,target_test_ratio,positive_class,class_mapping,source_record_count,methodology_json)
            SELECT :id,:name,semantic_version,'GENERATED',grouping_strategy,grouping_field,
              stratification_strategy,split_algorithm,split_algorithm_version,random_seed,target_train_ratio,
              target_val_ratio,target_test_ratio,positive_class,class_mapping,source_record_count,
              methodology_json - 'freeze_contract' FROM dataset_versions WHERE id=:source
        '''), {'id':version_id,'source':VERSION_ID,'name':f'S3 rollback {version_id}'})
        original_definition = smear_validation._definition
        def fixture_definition(inspections, plan):
            return {**original_definition(inspections, plan), 'name':f'S3 rollback {version_id}'}
        monkeypatch.setattr(smear_validation, '_definition', fixture_definition)
        connection.execute(text('INSERT INTO dataset_version_sources(dataset_version_id,dataset_id,role) SELECT :id,dataset_id,role FROM dataset_version_sources WHERE dataset_version_id=:source'), {'id':version_id,'source':VERSION_ID})
        connection.execute(text('''INSERT INTO dataset_split_assignments(dataset_version_id,source_record_id,clinical_identity_id,split_name,class_index,class_name,metadata)
            SELECT :id,source_record_id,clinical_identity_id,split_name,class_index,class_name,metadata
            FROM dataset_split_assignments WHERE dataset_version_id=:source'''), {'id':version_id,'source':VERSION_ID})
        audit = audit_persisted_assignments(connection, VERSION_ID)
        expected = {key:audit[key] for key in ('patient_digest','record_digest')}
        yield connection,version_id,expected
        tx.rollback()


class BoundEngine:
    def __init__(self, connection):
        self.connection = connection

    @contextlib.contextmanager
    def connect(self):
        yield self.connection

    @contextlib.contextmanager
    def begin(self):
        with self.connection.begin_nested():
            yield self.connection


def test_real_counts_disjointness_same_split_sets_and_determinism(generated, inspections):
    c, version, expected = generated
    first = prepare_smear_validation(c, inspections, expected, version)
    second = prepare_smear_validation(c, list(reversed(inspections)), expected, version)
    assert first == second
    stats = first.formal.statistics
    assert stats['total_patients'] == 193 and stats['total_assignments'] == stats['total_source_records'] == 965
    assert stats['patients'] == {'train':154,'val':19,'test':20}
    assert stats['records'] == {'train':770,'val':95,'test':100}
    assert stats['cross_family_mismatches'] == stats['no_assignment'] == 0
    assert set(stats['patient_overlaps'].values()) == {0}
    assert stats['populations']['Polygon Set']['patients'] == 33
    assert stats['populations']['Point Set']['patients'] == 160
    assert len(first.manifest['records']) == 965
    assert first.manifest_fingerprint == second.manifest_fingerprint
    assert len(first.formal.checks) == 17


def test_missing_assignment_stops(generated, inspections):
    c, version, expected = generated
    c.execute(text('DELETE FROM dataset_split_assignments WHERE id=(SELECT id FROM dataset_split_assignments WHERE dataset_version_id=:id LIMIT 1)'), {'id':version})
    with pytest.raises(FormalValidationError, match='coverage'):
        prepare_smear_validation(c, inspections, expected, version)


def test_cross_family_mutation_stops_without_repair(generated, inspections):
    c, version, expected = generated
    rows = [dict(r) for r in c.execute(text("SELECT id,dataset_version_id,source_record_id,clinical_identity_id,split_name,class_index,class_name,metadata FROM dataset_split_assignments WHERE dataset_version_id=:id AND clinical_identity_id=(SELECT clinical_identity_id FROM dataset_split_assignments WHERE dataset_version_id=:id AND split_name='val' LIMIT 1)"), {'id':version}).mappings()]
    c.execute(text('DELETE FROM dataset_split_assignments WHERE dataset_version_id=:id AND clinical_identity_id=:patient'), {'id':version,'patient':rows[0]['clinical_identity_id']})
    _bulk_insert(c,tuple({**r,'split_name':'train','metadata':json.dumps(r['metadata'])} for r in rows))
    before = audit_persisted_assignments(c,version)['record_digest']
    with pytest.raises(FormalValidationError, match='same_split_cross_family'):
        prepare_smear_validation(c, inspections, expected, version)
    assert audit_persisted_assignments(c,version)['record_digest'] == before


def test_patient_overlap_blocked_by_existing_postgres_constraint(generated):
    c, version, _ = generated
    with pytest.raises(DBAPIError, match='already assigned'):
        with c.begin_nested():
            c.execute(text("UPDATE dataset_split_assignments SET split_name='test' WHERE id=(SELECT id FROM dataset_split_assignments WHERE dataset_version_id=:id AND split_name='train' LIMIT 1)"), {'id':version})
    assert audit_persisted_assignments(c,version)['patient_overlap'] == 0


@pytest.mark.parametrize('annotation_set', ['Polygon Set','Point Set'])
def test_changed_gt_or_source_content_rejected(generated, inspections, annotation_set):
    c, version, expected = generated
    selected = next(s for s in inspections if s.annotation_set == annotation_set)
    changed = replace(selected, records=(replace(selected.records[0],annotation_sha256='0'*64),)+selected.records[1:])
    with pytest.raises(FormalValidationError, match='definition conflict'):
        prepare_smear_validation(c,[changed if s.annotation_set == annotation_set else s for s in inspections],expected,version)


def test_s2_fingerprint_mutation_stops(generated, inspections):
    c, version, expected = generated
    with pytest.raises(FormalValidationError, match='s2_assignments_unchanged'):
        prepare_smear_validation(c, inspections, {**expected,'record_digest':'0'*64}, version)


def test_nonreproducible_fingerprint_stops(generated, inspections, monkeypatch):
    c, version, expected = generated
    original = smear_validation.compute_final_fingerprints
    calls = 0
    def unstable(connection, dataset_version_id):
        nonlocal calls
        calls += 1
        value = original(connection,dataset_version_id)
        return replace(value,source_population='0'*64) if calls == 2 else value
    monkeypatch.setattr(smear_validation,'compute_final_fingerprints',unstable)
    with pytest.raises(FormalValidationError, match='fingerprint_reproducibility'):
        prepare_smear_validation(c,inspections,expected,version)


def test_lifecycle_freeze_idempotency_and_no_training(generated, inspections):
    c, version, expected = generated
    original = compute_final_fingerprints(c,version)
    def guard(connection):
        assert compute_final_fingerprints(connection,version) == original
    first = freeze_dataset_version(BoundEngine(c),version,source_inspections=inspections,expected_assignments=expected,integrity_guard=guard)
    assert first.result == 'FROZEN_COMMIT' and first.materialization_id is None and not first.trainable
    assert logical_validation_passes(c,version)
    assert get_dataset_version_trainability(c,version).reasons == ('NO_READY_RECONCILED_MATERIALIZATION',)
    persisted = dict(c.execute(text('SELECT * FROM dataset_versions WHERE id=:id'),{'id':version}).mappings().one())
    second = freeze_dataset_version(BoundEngine(c),version,source_inspections=inspections,expected_assignments=expected,integrity_guard=guard)
    assert second.result == 'ALREADY_FROZEN_MATCH_NO_OP'
    assert dict(c.execute(text('SELECT * FROM dataset_versions WHERE id=:id'),{'id':version}).mappings().one()) == persisted
    assert persisted['validated_at'] is not None and persisted['frozen_at'] is not None
    assert compute_final_fingerprints(c,version) == original
    assert c.execute(text('SELECT count(*) FROM dataset_split_validation_checks WHERE dataset_version_id=:id'),{'id':version}).scalar_one() == 17


def test_integrity_failure_rolls_back_validation_and_freeze(generated, inspections):
    c, version, expected = generated
    def fail(connection):
        assert connection.execute(text('SELECT status FROM dataset_versions WHERE id=:id'),{'id':version}).scalar_one() == 'VALIDATED'
        raise ValueError('RAW changed')
    with pytest.raises(ValueError,match='RAW changed'):
        freeze_dataset_version(BoundEngine(c),version,source_inspections=inspections,expected_assignments=expected,integrity_guard=fail)
    assert c.execute(text('SELECT status FROM dataset_versions WHERE id=:id'),{'id':version}).scalar_one() == 'GENERATED'
    for table in ('dataset_split_statistics','dataset_split_validation_checks'):
        assert c.execute(text(f'SELECT count(*) FROM {table} WHERE dataset_version_id=:id'),{'id':version}).scalar_one() == 0


def test_missing_source_freeze_evidence_rejected(generated):
    c, version, _ = generated
    with pytest.raises(FreezeError,match='SOURCE_FREEZE_REQUIRES'):
        freeze_dataset_version(BoundEngine(c),version)


def test_validated_to_frozen(generated, inspections):
    c,version,expected = generated
    prepared = prepare_smear_validation(c,inspections,expected,version)
    persist_formal_validation(c,prepared.formal)
    result = freeze_dataset_version(BoundEngine(c),version,source_inspections=inspections,expected_assignments=expected,integrity_guard=lambda connection: None)
    assert result.result == 'FROZEN_COMMIT'


def test_existing_cell_freeze_contract_is_unchanged(engine):
    with engine.connect() as c:
        transaction = c.begin()
        before = dict(c.execute(text('SELECT * FROM dataset_versions WHERE id=:id'), {'id':V1_ID}).mappings().one())
        fingerprints = compute_final_fingerprints(c,V1_ID)
        outcome = freeze_dataset_version(BoundEngine(c),V1_ID)
        assert outcome.result == 'ALREADY_FROZEN_MATCH_NO_OP'
        assert outcome.materialization_id is not None and outcome.trainable
        assert dict(c.execute(text('SELECT * FROM dataset_versions WHERE id=:id'), {'id':V1_ID}).mappings().one()) == before
        assert compute_final_fingerprints(c,V1_ID) == fingerprints
        transaction.rollback()
