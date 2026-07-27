import json
import os
from uuid import uuid4

import pytest
from fastapi import Request
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.audit import record_event
from app.config import Settings
from app.database_safety import assert_capstone_database, assert_safe_temporary_schema
from app.db import normalize_sqlalchemy_url
from app.observability import correlation_id_context
from app.security import Principal


pytestmark = pytest.mark.requires_local_postgres


@pytest.fixture(autouse=True)
def require_local_gate():
    if os.getenv("TEST_EXECUTION", "").lower() != "true":
        pytest.skip("requiere gate PostgreSQL local explícito")


@pytest.fixture
def transaction():
    settings = Settings.from_env()
    engine = create_engine(normalize_sqlalchemy_url(settings.database_url))
    with engine.connect() as connection:
        assert_capstone_database(
            settings, connection.execute(text("SELECT current_database()")).scalar_one()
        )
        tx = connection.begin_nested() if connection.in_transaction() else connection.begin()
        try:
            yield connection
        finally:
            tx.rollback()
    engine.dispose()


def _audit_row(connection, event_id):
    connection.execute(text("""
        INSERT INTO audit_events(
          id,event_type,action,resource_type,request_method,request_path,
          correlation_id,metadata,success
        ) VALUES(
          :id,'TEST_ROLLBACK','isolation-test','test','POST','/test',
          :correlation_id,CAST(:metadata AS jsonb),true
        )
    """), {"id": event_id, "correlation_id": f"test-{event_id}",
           "metadata": json.dumps({"is_test_fixture": True})})


def test_row_visible_inside_transaction(transaction):
    event_id = uuid4()
    _audit_row(transaction, event_id)
    assert transaction.execute(
        text("SELECT count(*) FROM audit_events WHERE id=:id"), {"id": event_id}
    ).scalar_one() == 1


def test_rollback_after_success_leaves_no_row():
    settings = Settings.from_env()
    engine = create_engine(normalize_sqlalchemy_url(settings.database_url))
    event_id = uuid4()
    with engine.connect() as connection:
        tx = connection.begin()
        _audit_row(connection, event_id)
        tx.rollback()
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM audit_events WHERE id=:id"), {"id": event_id}
        ).scalar_one() == 0
    engine.dispose()


def test_rollback_after_exception_leaves_no_row():
    settings = Settings.from_env()
    engine = create_engine(normalize_sqlalchemy_url(settings.database_url))
    event_id = uuid4()
    with pytest.raises(RuntimeError):
        with engine.connect() as connection:
            tx = connection.begin()
            try:
                _audit_row(connection, event_id)
                raise RuntimeError("simulated test failure")
            finally:
                tx.rollback()
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM audit_events WHERE id=:id"), {"id": event_id}
        ).scalar_one() == 0
    engine.dispose()


def test_consecutive_transactions_do_not_contaminate(transaction):
    event_id = uuid4()
    assert transaction.execute(
        text("SELECT count(*) FROM audit_events WHERE id=:id"), {"id": event_id}
    ).scalar_one() == 0
    _audit_row(transaction, event_id)


def test_temporary_schema_is_created_and_removed():
    settings = Settings.from_env()
    schema = assert_safe_temporary_schema(settings, f"capstone_test_run_{uuid4().hex[:12]}")
    engine = create_engine(normalize_sqlalchemy_url(settings.database_url))
    quoted = engine.dialect.identifier_preparer.quote(schema)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(f"CREATE SCHEMA {quoted}")
            connection.exec_driver_sql(f"SET LOCAL search_path TO {quoted}")
            connection.exec_driver_sql("CREATE TABLE isolated_object(id integer)")
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(f"DROP SCHEMA IF EXISTS {quoted} CASCADE")
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM pg_namespace WHERE nspname=:schema"), {"schema": schema}
        ).scalar_one() == 0
    engine.dispose()


def test_no_temporary_schema_residue():
    settings = Settings.from_env()
    engine = create_engine(normalize_sqlalchemy_url(settings.database_url))
    with engine.connect() as connection:
        residues = connection.execute(text("""
            SELECT nspname FROM pg_namespace
            WHERE nspname ~ '^capstone_test_[a-z0-9_]{6,48}$'
        """)).scalars().all()
    engine.dispose()
    assert residues == []


FAMILIES = (
    "stage2_publish", "stage2_deactivate_reactivate", "deployment_create_update",
    "stage2_default", "deployment_rollback", "persistent_inference",
)


def _request(family):
    return Request({
        "type": "http", "method": "POST", "path": f"/test/{family}",
        "headers": [], "query_string": b"", "server": ("test", 80),
        "client": ("test", 1), "scheme": "http",
    })


@pytest.mark.parametrize("family", FAMILIES)
def test_real_audit_constraint_failure_rolls_back_shared_mutation(family):
    settings = Settings.from_env()
    engine = create_engine(normalize_sqlalchemy_url(settings.database_url))
    run_id = uuid4()
    connection = engine.connect()
    tx = connection.begin()
    try:
        connection.execute(text("""
            INSERT INTO runs(id,run_name,run_type,status,metadata)
            VALUES(:id,:name,'inference','running',CAST(:metadata AS jsonb))
        """), {"id": run_id, "name": f"capstone_test_{family}",
               "metadata": json.dumps({"is_test_fixture": True, "family": family})})
        with pytest.raises(IntegrityError):
            record_event(
                event_type="TEST_ATOMICITY", action=family,
                principal=Principal(str(uuid4()), "capstone_test_actor", ("read_only",), frozenset()),
                request=_request(family), success=True, connection=connection,
                metadata={"is_test_fixture": True},
                before_state={"status": "absent"}, after_state={"status": "running"},
                # PostgreSQL rejects this real FK; no table/schema alteration is used.
                # A synthetic Principal would expose no secret, but direct invalid FK is clearer.
            )
    finally:
        tx.rollback()
        connection.close()
    with engine.connect() as verify:
        assert verify.execute(
            text("SELECT count(*) FROM runs WHERE id=:id"), {"id": run_id}
        ).scalar_one() == 0
    engine.dispose()
