import hashlib
import json
import os

from sqlalchemy import text

from malaria_split.persistence.bootstrap import audit_scientific_bootstrap
from malaria_split.persistence.database import create_postgresql_engine
from malaria_split.persistence.split_generation import V1_ID, audit_persisted_assignments


def _v1_snapshot(engine):
    with engine.connect() as connection:
        version = connection.execute(text("""
            SELECT status,generated_at,methodology_json FROM dataset_versions WHERE id=:id
        """), {"id": V1_ID}).mappings().one()
        assignments = audit_persisted_assignments(connection, V1_ID)
    return {
        "status": version["status"], "generated_at": version["generated_at"],
        "assignments": assignments["total_assignments"],
        "patient_digest": assignments["patient_digest"],
        "record_digest": assignments["record_digest"],
        "methodology_hash": hashlib.sha256(json.dumps(
            version["methodology_json"], sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest(),
    }


def test_real_scientific_bootstrap_contract():
    engine = create_postgresql_engine(os.environ["DATABASE_URL"])
    try:
        audit = audit_scientific_bootstrap(engine)
    finally:
        engine.dispose()
    assert audit["status"] == "PASS"
    assert audit["dataset_version_status"] in ("DRAFT", "GENERATED")
    assert audit["v1_assignment_count"] in (0, 27558)
    assert audit["v1_materialization_count"] == 0


def test_generated_bootstrap_audit_is_read_only():
    engine = create_postgresql_engine(os.environ["DATABASE_URL"])
    try:
        before = _v1_snapshot(engine)
        audit = audit_scientific_bootstrap(engine)
        after = _v1_snapshot(engine)
    finally:
        engine.dispose()
    assert audit["dataset_version_status"] == "GENERATED"
    assert audit["v1_assignment_count"] == 27558
    assert before == after
