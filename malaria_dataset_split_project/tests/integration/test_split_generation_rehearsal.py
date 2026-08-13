import os

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from malaria_split.persistence.database import create_postgresql_engine
from malaria_split.persistence.split_generation import (
    DigestMismatch,
    V1_ID,
    _bulk_insert,
    prepare_split_generation,
)


@pytest.fixture(scope="module")
def engine():
    value = create_postgresql_engine(os.environ["DATABASE_URL"])
    yield value
    value.dispose()


@pytest.fixture(scope="module")
def prepared(engine):
    with engine.connect() as connection:
        return prepare_split_generation(connection)


def _state(engine):
    with engine.connect() as connection:
        return connection.execute(text("""
            SELECT status,(SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=dv.id)
            FROM dataset_versions dv WHERE id=:id
        """), {"id": V1_ID}).one()


def test_failure_after_partial_real_bulk_insert_is_atomic(engine, prepared):
    with pytest.raises(RuntimeError, match="simulated failure"):
        connection = engine.connect()
        transaction = connection.begin()
        try:
            connection.execute(text("SELECT id FROM dataset_versions WHERE id=:id FOR UPDATE NOWAIT"),
                               {"id": V1_ID})
            _bulk_insert(connection, prepared.assignment_rows[:1000])
            assert connection.execute(text(
                "SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=:id"
            ), {"id": V1_ID}).scalar_one() == 1000
            raise RuntimeError("simulated failure after partial real bulk insert")
        except Exception:
            transaction.rollback()
            raise
        finally:
            connection.close()
    assert _state(engine) == ("DRAFT", 0)


def test_digest_mismatch_aborts_before_writes(engine):
    with engine.connect() as connection:
        with pytest.raises(DigestMismatch):
            prepare_split_generation(connection, expected_digest="0" * 64)
    assert _state(engine) == ("DRAFT", 0)


def test_dataset_version_nowait_lock_blocks_concurrent_generator(engine):
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
    assert _state(engine) == ("DRAFT", 0)


def test_assignment_invariant_triggers_remain_enabled(engine):
    with engine.connect() as connection, connection.begin():
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
            """), {"version": V1_ID, "record": source["id"], "wrong": source["wrong_identity"],
                    "class_index": source["class_index"], "class_name": source["class_name"]})
        savepoint.rollback()
        connection.rollback()
    assert _state(engine) == ("DRAFT", 0)
