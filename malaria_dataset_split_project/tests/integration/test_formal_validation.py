"""SPLIT 4 mutable tests use only rollback-scoped dataset versions."""

from __future__ import annotations

import os
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from malaria_split.governance.trainability import get_dataset_version_trainability
from malaria_split.persistence.database import create_postgresql_engine
from malaria_split.persistence.formal_validation import (
    FormalValidationError,
    persist_formal_validation,
    prepare_formal_validation,
)
from malaria_split.persistence.split_generation import V1_ID


@pytest.fixture(scope="module")
def engine():
    value = create_postgresql_engine(os.environ["DATABASE_URL"])
    yield value
    value.dispose()


@pytest.fixture
def generated_fixture(engine):
    connection = engine.connect()
    transaction = connection.begin()
    version_id = uuid4()
    connection.execute(text("""
        INSERT INTO dataset_versions(
          id,name,semantic_version,status,grouping_strategy,grouping_field,
          stratification_strategy,split_algorithm,split_algorithm_version,random_seed,
          target_train_ratio,target_val_ratio,target_test_ratio,positive_class,class_mapping,
          source_record_count,methodology_json,generated_at
        ) SELECT :id,:name,:semver,'GENERATED',grouping_strategy,grouping_field,
          stratification_strategy,split_algorithm,split_algorithm_version,random_seed,
          target_train_ratio,target_val_ratio,target_test_ratio,positive_class,class_mapping,
          source_record_count,methodology_json,now()
        FROM dataset_versions WHERE id=:v1
    """), {"id": version_id, "v1": V1_ID, "name": f"split4 fixture {version_id}",
            "semver": f"0.0.{version_id}"})
    connection.execute(text("""
        INSERT INTO dataset_version_sources(dataset_version_id,dataset_id,role)
        SELECT :id,dataset_id,role FROM dataset_version_sources WHERE dataset_version_id=:v1
    """), {"id": version_id, "v1": V1_ID})
    connection.execute(text("""
        INSERT INTO dataset_split_assignments(
          dataset_version_id,source_record_id,clinical_identity_id,split_name,
          class_index,class_name,metadata)
        SELECT :id,source_record_id,clinical_identity_id,split_name,class_index,class_name,metadata
        FROM dataset_split_assignments WHERE dataset_version_id=:v1
    """), {"id": version_id, "v1": V1_ID})
    yield connection, version_id
    transaction.rollback()
    connection.close()
    with engine.connect() as check:
        assert check.execute(text("SELECT count(*) FROM dataset_versions WHERE id=:id"),
                             {"id": version_id}).scalar_one() == 0


def test_all_required_checks_and_generated_to_validated_idempotent(generated_fixture):
    connection, version_id = generated_fixture
    prepared = prepare_formal_validation(connection, version_id)
    assert len(prepared.checks) == 12
    assert all(check["status"] == "PASS" for check in prepared.checks.values())
    first = persist_formal_validation(connection, prepared)
    assert not first.already_validated
    assert first.status == "VALIDATED"
    assert get_dataset_version_trainability(connection, version_id).reasons == (
        "DATASET_NOT_FROZEN", "NO_READY_RECONCILED_MATERIALIZATION",
    )
    second = persist_formal_validation(connection, prepare_formal_validation(connection, version_id))
    assert second.already_validated
    assert connection.execute(text(
        "SELECT count(*) FROM dataset_split_statistics WHERE dataset_version_id=:id"
    ), {"id": version_id}).scalar_one() == 1
    assert connection.execute(text(
        "SELECT count(*) FROM dataset_split_validation_checks WHERE dataset_version_id=:id"
    ), {"id": version_id}).scalar_one() == 12


def test_validation_failure_blocks_lifecycle_and_writes(generated_fixture):
    connection, version_id = generated_fixture
    prepared = prepare_formal_validation(connection, version_id)
    checks = dict(prepared.checks)
    checks["identity_conflicts"] = {**checks["identity_conflicts"], "status": "FAIL"}
    with pytest.raises(FormalValidationError, match="PREVALIDATION_FAILED"):
        persist_formal_validation(connection, replace(prepared, checks=checks))
    assert connection.execute(text("SELECT status FROM dataset_versions WHERE id=:id"),
                              {"id": version_id}).scalar_one() == "GENERATED"
    assert connection.execute(text(
        "SELECT count(*) FROM dataset_split_statistics WHERE dataset_version_id=:id"
    ), {"id": version_id}).scalar_one() == 0


def test_atomic_rollback_after_validation_rows_inserted(generated_fixture):
    connection, version_id = generated_fixture
    prepared = prepare_formal_validation(connection, version_id)
    savepoint = connection.begin_nested()
    def fail(conn):
        assert conn.execute(text(
            "SELECT count(*) FROM dataset_split_validation_checks WHERE dataset_version_id=:id"
        ), {"id": version_id}).scalar_one() == 12
        raise RuntimeError("simulated validation failure")
    with pytest.raises(RuntimeError, match="simulated validation failure"):
        persist_formal_validation(connection, prepared, failure_hook=fail)
    savepoint.rollback()
    assert connection.execute(text("SELECT status FROM dataset_versions WHERE id=:id"),
                              {"id": version_id}).scalar_one() == "GENERATED"
    assert connection.execute(text(
        "SELECT count(*) FROM dataset_split_validation_checks WHERE dataset_version_id=:id"
    ), {"id": version_id}).scalar_one() == 0
