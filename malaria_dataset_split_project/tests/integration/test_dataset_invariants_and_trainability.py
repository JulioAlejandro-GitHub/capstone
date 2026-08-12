"""SPLIT 2C transactional tests; every fixture is rolled back."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from malaria_split.governance.dataset_lifecycle import transition_dataset_version
from malaria_split.governance.trainability import (
    REQUIRED_LOGICAL_VALIDATION_CHECKS,
    get_dataset_version_trainability,
    list_trainable_dataset_versions,
    resolve_default_trainable_dataset_version,
    resolve_trainable_materialization,
)
from malaria_split.persistence.database import create_postgresql_engine


@pytest.fixture(scope="module")
def engine():
    value = create_postgresql_engine(os.environ["DATABASE_URL"])
    yield value
    value.dispose()


@pytest.fixture
def db(engine):
    connection = engine.connect()
    transaction = connection.begin()
    yield connection
    transaction.rollback()
    connection.close()


def _version(db, *, frozen=False, suffix=None, frozen_at=None):
    version_id = uuid4()
    suffix = suffix or str(version_id)
    db.execute(text("""
        INSERT INTO dataset_versions (
          id,name,semantic_version,status,grouping_strategy,grouping_field,
          stratification_strategy,split_algorithm,split_algorithm_version,random_seed,
          target_train_ratio,target_val_ratio,target_test_ratio,positive_class,
          source_record_count
        ) VALUES (
          :id,:name,:semver,'DRAFT','patient_group','patient_id','fixture',
          'fixture','1.0.0',42,0.8,0.1,0.1,'parasitized',0
        )
    """), {"id": version_id, "name": f"2c fixture {suffix}", "semver": f"0.0.{suffix}"})
    if frozen:
        for status in ("GENERATED", "VALIDATED", "FROZEN"):
            transition_dataset_version(db, version_id, status)
        if frozen_at:
            db.execute(text("UPDATE dataset_versions SET frozen_at=:at WHERE id=:id"),
                       {"at": frozen_at, "id": version_id})
    return version_id


def _source_fixture(db, patient_id, class_name="parasitized", count=1):
    dataset_id = db.execute(text("SELECT id FROM datasets ORDER BY id LIMIT 1")).scalar_one()
    identity_id = uuid4()
    db.execute(text("""
        INSERT INTO clinical_identities(id,dataset_id,identity_type,source_identifier,status)
        VALUES (:id,:dataset,'PATIENT',:identifier,'VERIFIED')
    """), {"id": identity_id, "dataset": dataset_id, "identifier": f"2c-{patient_id}-{identity_id}"})
    records = []
    class_index = 1 if class_name == "parasitized" else 0
    for _ in range(count):
        record_id = uuid4()
        db.execute(text("""
            INSERT INTO dataset_source_records(
              id,dataset_id,clinical_identity_id,source_record_key,class_index,class_name,
              identity_status
            ) VALUES (:id,:dataset,:identity,:key,:class_index,:class_name,'VERIFIED')
        """), {"id": record_id, "dataset": dataset_id, "identity": identity_id,
                "key": f"2c:{record_id}", "class_index": class_index, "class_name": class_name})
        records.append(record_id)
    return dataset_id, identity_id, records


def _assignment(db, version_id, record_id, identity_id, split="train", class_name="parasitized"):
    assignment_id = uuid4()
    db.execute(text("""
        INSERT INTO dataset_split_assignments(
          id,dataset_version_id,source_record_id,clinical_identity_id,split_name,
          class_index,class_name
        ) VALUES (:id,:version,:record,:identity,:split,:class_index,:class_name)
    """), {"id": assignment_id, "version": version_id, "record": record_id,
            "identity": identity_id, "split": split,
            "class_index": 1 if class_name == "parasitized" else 0,
            "class_name": class_name})
    return assignment_id


def _rejected(db, statement, parameters):
    savepoint = db.begin_nested()
    with pytest.raises(IntegrityError):
        db.execute(text(statement), parameters)
    savepoint.rollback()


def _validation_pass(db, version_id, *, fail_name=None, omit_name=None):
    for name in REQUIRED_LOGICAL_VALIDATION_CHECKS:
        if name == omit_name:
            continue
        db.execute(text("""
            INSERT INTO dataset_split_validation_checks(
              dataset_version_id,check_name,status,blocking_for_validation,blocking_for_freeze
            ) VALUES (:version,:name,:status,true,true)
        """), {"version": version_id, "name": name,
                "status": "FAIL" if name == fail_name else "PASS"})


def _materialization(db, version_id, attempt, status="READY", reconciliation="PASS"):
    materialization_id = uuid4()
    db.execute(text("""
        INSERT INTO dataset_materializations(
          id,dataset_version_id,attempt_number,status,reconciliation_status,relative_root,
          completed_at
        ) VALUES (:id,:version,:attempt,:status,:reconciliation,:root,now())
    """), {"id": materialization_id, "version": version_id, "attempt": attempt,
            "status": status, "reconciliation": reconciliation,
            "root": f"fixtures/{materialization_id}"})
    return materialization_id


def test_patient_disjoint_and_source_record_unique(db):
    version = _version(db)
    _, identity, records = _source_fixture(db, "PAT-A", count=4)
    assignments = [_assignment(db, version, record, identity) for record in records[:3]]
    _rejected(db, """
        INSERT INTO dataset_split_assignments(
          dataset_version_id,source_record_id,clinical_identity_id,split_name,class_index,class_name
        ) VALUES (:v,:r,:i,'test',1,'parasitized')
    """, {"v": version, "r": records[3], "i": identity})
    _rejected(db, "UPDATE dataset_split_assignments SET split_name='val' WHERE id=:id",
              {"id": assignments[0]})
    _rejected(db, """
        INSERT INTO dataset_split_assignments(
          dataset_version_id,source_record_id,clinical_identity_id,split_name,class_index,class_name
        ) VALUES (:v,:r,:i,'train',1,'parasitized')
    """, {"v": version, "r": records[0], "i": identity})
    _, identity_b, records_b = _source_fixture(db, "PAT-B")
    _assignment(db, version, records_b[0], identity_b, "test")


def test_assignment_identity_and_class_consistency(db):
    version = _version(db)
    _, identity_a, records = _source_fixture(db, "PAT-A")
    _, identity_b, _ = _source_fixture(db, "PAT-B")
    _rejected(db, """
        INSERT INTO dataset_split_assignments(
          dataset_version_id,source_record_id,clinical_identity_id,split_name,class_index,class_name
        ) VALUES (:v,:r,:i,'train',1,'parasitized')
    """, {"v": version, "r": records[0], "i": identity_b})
    _rejected(db, """
        INSERT INTO dataset_split_assignments(
          dataset_version_id,source_record_id,clinical_identity_id,split_name,class_index,class_name
        ) VALUES (:v,:r,:i,'train',0,'uninfected')
    """, {"v": version, "r": records[0], "i": identity_a})


def test_lifecycle_forward_archive_and_reverse_rejected(db):
    version = _version(db)
    generated = transition_dataset_version(db, version, "GENERATED")
    assert generated["generated_at"] is not None
    validated = transition_dataset_version(db, version, "VALIDATED")
    assert validated["validated_at"] is not None
    frozen = transition_dataset_version(db, version, "FROZEN")
    assert frozen["frozen_at"] is not None
    archived = transition_dataset_version(db, version, "ARCHIVED")
    assert archived["archived_at"] is not None
    _rejected(db, "UPDATE dataset_versions SET status='DRAFT' WHERE id=:id", {"id": version})
    for initial in ("DRAFT", "GENERATED", "VALIDATED"):
        other = _version(db)
        if initial in ("GENERATED", "VALIDATED"):
            transition_dataset_version(db, other, "GENERATED")
        if initial == "VALIDATED":
            transition_dataset_version(db, other, "VALIDATED")
        transition_dataset_version(db, other, "ARCHIVED")


def test_frozen_scientific_fields_are_immutable(db):
    for field, expression, extra in (
        ("random_seed", "99", {}), ("grouping_field", "'other'", {}),
        ("target_train_ratio", "0.7", {}),
        ("class_mapping", "CAST(:value AS jsonb)", {"value": json.dumps({"x": 1})}),
        ("methodology_json", "CAST(:value AS jsonb)", {"value": json.dumps({"changed": True})}),
    ):
        version = _version(db, frozen=True)
        _rejected(db, f"UPDATE dataset_versions SET {field}={expression} WHERE id=:id",
                  {"id": version, **extra})


def test_frozen_assignments_insert_update_delete_rejected(db):
    version = _version(db)
    _, identity, records = _source_fixture(db, "PAT-A", count=2)
    assignment = _assignment(db, version, records[0], identity)
    for status in ("GENERATED", "VALIDATED", "FROZEN"):
        transition_dataset_version(db, version, status)
    _rejected(db, """
        INSERT INTO dataset_split_assignments(
          dataset_version_id,source_record_id,clinical_identity_id,split_name,class_index,class_name
        ) VALUES (:v,:r,:i,'train',1,'parasitized')
    """, {"v": version, "r": records[1], "i": identity})
    _rejected(db, "UPDATE dataset_split_assignments SET metadata=CAST(:value AS jsonb) WHERE id=:id",
              {"id": assignment, "value": json.dumps({"x": 1})})
    mutable_version = _version(db)
    _rejected(db, "UPDATE dataset_split_assignments SET dataset_version_id=:version WHERE id=:id",
              {"id": assignment, "version": mutable_version})
    _rejected(db, "DELETE FROM dataset_split_assignments WHERE id=:id", {"id": assignment})


def test_frozen_source_composition_insert_update_delete_rejected(db):
    version = _version(db)
    datasets = db.execute(text("SELECT id FROM datasets ORDER BY id LIMIT 2")).scalars().all()
    db.execute(text("""
        INSERT INTO dataset_version_sources(dataset_version_id,dataset_id,role)
        VALUES (:v,:d,'PRIMARY')
    """), {"v": version, "d": datasets[0]})
    for status in ("GENERATED", "VALIDATED", "FROZEN"):
        transition_dataset_version(db, version, status)
    _rejected(db, """
        INSERT INTO dataset_version_sources(dataset_version_id,dataset_id,role)
        VALUES (:v,:d,'AUXILIARY')
    """, {"v": version, "d": datasets[1]})
    _rejected(db, "UPDATE dataset_version_sources SET role='AUXILIARY' WHERE dataset_version_id=:v",
              {"v": version})
    _rejected(db, "DELETE FROM dataset_version_sources WHERE dataset_version_id=:v",
              {"v": version})


def test_single_current_activation_and_history(db):
    v1, v2 = _version(db), _version(db)
    m1, m2 = _materialization(db, v1, 1), _materialization(db, v2, 1)
    a1 = uuid4()
    db.execute(text("""
        INSERT INTO dataset_materialization_activations(
          id,dataset_version_id,materialization_id,dataset_family
        ) VALUES (:id,:v,:m,'2c-malaria')
    """), {"id": a1, "v": v1, "m": m1})
    _rejected(db, """
        INSERT INTO dataset_materialization_activations(
          dataset_version_id,materialization_id,dataset_family
        ) VALUES (:v,:m,'2c-malaria')
    """, {"v": v2, "m": m2})
    db.execute(text("UPDATE dataset_materialization_activations SET deactivated_at=now() WHERE id=:id"),
               {"id": a1})
    db.execute(text("""
        INSERT INTO dataset_materialization_activations(
          dataset_version_id,materialization_id,dataset_family
        ) VALUES (:v,:m,'2c-malaria')
    """), {"v": v2, "m": m2})


@pytest.mark.parametrize("check_failure,material_status,reconciliation,expected", [
    (None, "READY", "PASS", True),
    ("identity_coverage", "READY", "PASS", False),
    (None, "FAILED", "PASS", False),
    (None, "READY", "FAIL", False),
])
def test_trainable_matrix(db, check_failure, material_status, reconciliation, expected):
    version = _version(db)
    _validation_pass(db, version, fail_name=check_failure)
    _materialization(db, version, 1, material_status, reconciliation)
    for status in ("GENERATED", "VALIDATED", "FROZEN"):
        transition_dataset_version(db, version, status)
    assert get_dataset_version_trainability(db, version).trainable is expected


def test_draft_and_missing_required_validation_are_not_trainable(db):
    draft = _version(db)
    assert set(get_dataset_version_trainability(db, draft).reasons) == {
        "DATASET_NOT_FROZEN", "VALIDATION_NOT_PASS",
        "NO_READY_RECONCILED_MATERIALIZATION",
    }
    frozen = _version(db)
    _validation_pass(db, frozen, omit_name="class_presence_test")
    _materialization(db, frozen, 1)
    for status in ("GENERATED", "VALIDATED", "FROZEN"):
        transition_dataset_version(db, frozen, status)
    assert get_dataset_version_trainability(db, frozen).reasons == ("VALIDATION_NOT_PASS",)


def test_trainable_without_activation_and_materialization_resolution(db):
    version = _version(db)
    _validation_pass(db, version)
    _materialization(db, version, 1, "FAILED", "PASS")
    attempt2 = _materialization(db, version, 2)
    for status in ("GENERATED", "VALIDATED", "FROZEN"):
        transition_dataset_version(db, version, status)
    state = get_dataset_version_trainability(db, version)
    assert state.trainable and state.resolved_materialization_id == attempt2
    db.execute(text("""
        INSERT INTO dataset_materialization_activations(
          dataset_version_id,materialization_id,dataset_family
        ) VALUES (:version,:materialization,:family)
    """), {"version": version, "materialization": attempt2,
            "family": f"2c-trainable-{version}"})
    assert get_dataset_version_trainability(db, version).trainable
    attempt3 = _materialization(db, version, 3)
    assert resolve_trainable_materialization(db, version)["id"] == attempt3


def test_trainable_list_and_default_are_deterministic(db):
    now = datetime.now(timezone.utc)
    versions = []
    for index in range(3):
        version = _version(db, suffix=f"list-{index}")
        if index:
            _validation_pass(db, version)
            _materialization(db, version, 1)
        for status in ("GENERATED", "VALIDATED", "FROZEN"):
            transition_dataset_version(db, version, status)
        db.execute(text("UPDATE dataset_versions SET frozen_at=:at WHERE id=:id"),
                   {"at": now + timedelta(seconds=index), "id": version})
        versions.append(version)
    candidates = list_trainable_dataset_versions(db)
    ids = [item["dataset_version_id"] for item in candidates if item["dataset_version_id"] in versions]
    assert ids == [versions[2], versions[1]]
    assert resolve_default_trainable_dataset_version(db)["dataset_version_id"] == versions[2]


def test_default_with_zero_and_one_candidates(db):
    assert resolve_default_trainable_dataset_version(db) is None
    version = _version(db)
    _validation_pass(db, version)
    _materialization(db, version, 1)
    for status in ("GENERATED", "VALIDATED", "FROZEN"):
        transition_dataset_version(db, version, status)
    assert resolve_default_trainable_dataset_version(db)["dataset_version_id"] == version
