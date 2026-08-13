import os
import hashlib
import json
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from malaria_split.persistence.database import create_postgresql_engine
from malaria_split.persistence.split_generation import (
    DigestMismatch,
    V1_ID,
    _bulk_insert,
    audit_persisted_assignments,
    prepare_split_generation,
)


@pytest.fixture(scope="module")
def engine():
    value = create_postgresql_engine(os.environ["DATABASE_URL"])
    yield value
    value.dispose()


def _official_snapshot(engine):
    with engine.connect() as connection:
        version = connection.execute(text("""
            SELECT status,generated_at,methodology_json FROM dataset_versions WHERE id=:id
        """), {"id": V1_ID}).mappings().one()
        audit = audit_persisted_assignments(connection, V1_ID)
    return {
        "status": version["status"], "generated_at": version["generated_at"],
        "assignment_count": audit["total_assignments"],
        "patient_digest": audit["patient_digest"], "record_digest": audit["record_digest"],
        "methodology_hash": hashlib.sha256(json.dumps(
            version["methodology_json"], sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest(),
    }


@pytest.fixture
def draft_fixture(engine):
    official_before = _official_snapshot(engine)
    connection = engine.connect()
    transaction = connection.begin()
    version_id = uuid4()
    connection.execute(text("""
        INSERT INTO dataset_versions(
          id,name,semantic_version,status,grouping_strategy,grouping_field,
          stratification_strategy,split_algorithm,split_algorithm_version,random_seed,
          target_train_ratio,target_val_ratio,target_test_ratio,positive_class,class_mapping,
          source_record_count,methodology_json
        )
        SELECT :fixture_id,:name,:semver,'DRAFT',grouping_strategy,grouping_field,
          stratification_strategy,split_algorithm,split_algorithm_version,random_seed,
          target_train_ratio,target_val_ratio,target_test_ratio,positive_class,class_mapping,
          source_record_count,methodology_json
        FROM dataset_versions WHERE id=:official_id
    """), {
        "fixture_id": version_id, "official_id": V1_ID,
        "name": f"3c1 transactional fixture {version_id}", "semver": f"0.0.{version_id}",
    })
    connection.execute(text("""
        INSERT INTO dataset_version_sources(dataset_version_id,dataset_id,role)
        SELECT :fixture_id,dataset_id,role FROM dataset_version_sources
        WHERE dataset_version_id=:official_id
    """), {"fixture_id": version_id, "official_id": V1_ID})
    yield connection, version_id
    if transaction.is_active:
        transaction.rollback()
    connection.close()
    with engine.connect() as verification:
        assert verification.execute(text(
            "SELECT count(*) FROM dataset_versions WHERE id=:id"
        ), {"id": version_id}).scalar_one() == 0
        assert verification.execute(text(
            "SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=:id"
        ), {"id": version_id}).scalar_one() == 0
    assert _official_snapshot(engine) == official_before


def _state(engine):
    with engine.connect() as connection:
        return connection.execute(text("""
            SELECT status,(SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=dv.id)
            FROM dataset_versions dv WHERE id=:id
        """), {"id": V1_ID}).one()


def test_failure_after_partial_real_bulk_insert_is_atomic(draft_fixture):
    connection, version_id = draft_fixture
    prepared = prepare_split_generation(connection, dataset_version_id=version_id)
    savepoint = connection.begin_nested()
    with pytest.raises(RuntimeError, match="simulated failure"):
        connection.execute(text("SELECT id FROM dataset_versions WHERE id=:id FOR UPDATE NOWAIT"),
                           {"id": version_id})
        _bulk_insert(connection, prepared.assignment_rows[:1000])
        assert connection.execute(text(
            "SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=:id"
        ), {"id": version_id}).scalar_one() == 1000
        raise RuntimeError("simulated failure after partial real bulk insert")
    savepoint.rollback()
    assert connection.execute(text(
        "SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=:id"
    ), {"id": version_id}).scalar_one() == 0
    assert connection.execute(text(
        "SELECT status FROM dataset_versions WHERE id=:id"
    ), {"id": version_id}).scalar_one() == "DRAFT"


def test_digest_mismatch_aborts_before_writes(draft_fixture):
    connection, version_id = draft_fixture
    with pytest.raises(DigestMismatch):
        prepare_split_generation(
            connection, dataset_version_id=version_id, expected_digest="0" * 64
        )
    assert connection.execute(text(
        "SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=:id"
    ), {"id": version_id}).scalar_one() == 0
    assert connection.execute(text(
        "SELECT status FROM dataset_versions WHERE id=:id"
    ), {"id": version_id}).scalar_one() == "DRAFT"


def test_dataset_version_nowait_lock_blocks_concurrent_generator(engine):
    state_before = _state(engine)
    first = engine.connect()
    second = engine.connect()
    transaction = first.begin()
    try:
        first.execute(text("SELECT id FROM dataset_versions WHERE id=:id FOR UPDATE"), {"id": V1_ID})
        with pytest.raises(DBAPIError):
            second.execute(text("SELECT id FROM dataset_versions WHERE id=:id FOR UPDATE NOWAIT"), {"id": V1_ID})
        second.rollback()
    finally:
        transaction.rollback()
        first.close()
        second.close()
    assert _state(engine) == state_before


def test_assignment_invariant_triggers_remain_enabled(draft_fixture):
    connection, version_id = draft_fixture
    with connection.begin_nested():
        triggers = connection.execute(text("""
            SELECT tgname,tgenabled FROM pg_trigger
            WHERE tgrelid='dataset_split_assignments'::regclass AND NOT tgisinternal
        """)).all()
        assert triggers
        assert all(enabled == "O" for _, enabled in triggers)
        source = connection.execute(text("""
            SELECT r.id,r.clinical_identity_id,r.class_index,r.class_name,
                   (SELECT id FROM clinical_identities WHERE id<>r.clinical_identity_id LIMIT 1) wrong_identity
            FROM dataset_source_records r LIMIT 1
        """)).mappings().one()
        savepoint = connection.begin_nested()
        with pytest.raises(IntegrityError):
            connection.execute(text("""
                INSERT INTO dataset_split_assignments(
                  dataset_version_id,source_record_id,clinical_identity_id,split_name,class_index,class_name
                ) VALUES (:version,:record,:wrong,'train',:class_index,:class_name)
            """), {"version": version_id, "record": source["id"], "wrong": source["wrong_identity"],
                    "class_index": source["class_index"], "class_name": source["class_name"]})
        savepoint.rollback()
    assert connection.execute(text(
        "SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=:id"
    ), {"id": version_id}).scalar_one() == 0
