"""S1 smear_segmentation ingest against PostgreSQL; every fixture is rolled back."""

import contextlib
import os
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy import text

from malaria_split.governance.freeze import compute_final_fingerprints
from malaria_split.persistence import smear_source_ingest
from malaria_split.persistence.bootstrap import audit_scientific_bootstrap
from malaria_split.persistence.database import create_postgresql_engine
from malaria_split.persistence.smear_source_ingest import (
    SmearIngestConflict,
    audit_smear_source,
    ingest_smear_source,
)
from malaria_split.persistence.split_generation import V1_ID
from malaria_split.sources.thin_blood_smears_pf import inspect_thin_blood_smears_pf
from tests.smear_fixtures import build_tree, write_smear


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


@pytest.fixture
def isolated_source(monkeypatch):
    """A unique source name keeps synthetic rows apart from a committed real ingest."""
    monkeypatch.setattr(smear_source_ingest, "SOURCE_NAME", f"S1 fixture {uuid4()}")


class _BoundEngine:
    """Lets engine-based audits read this test's uncommitted transaction."""

    def __init__(self, connection):
        self._connection = connection

    @contextlib.contextmanager
    def connect(self):
        yield self._connection


def _v1_state(db):
    fingerprints = compute_final_fingerprints(db, V1_ID)
    counts = db.execute(text("""
        SELECT
          (SELECT count(*) FROM dataset_source_records r JOIN dataset_version_sources vs
             ON vs.dataset_id=r.dataset_id WHERE vs.dataset_version_id=:id) records,
          (SELECT count(*) FROM clinical_identities i JOIN dataset_version_sources vs
             ON vs.dataset_id=i.dataset_id WHERE vs.dataset_version_id=:id) identities,
          (SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=:id) assignments,
          (SELECT status FROM dataset_versions WHERE id=:id) status,
          (SELECT md5(methodology_json::text) FROM dataset_versions WHERE id=:id) methodology
    """), {"id": V1_ID}).mappings().one()
    return fingerprints, dict(counts)


def _v1_audit_status(db):
    return audit_scientific_bootstrap(_BoundEngine(db))["status"]


def test_synthetic_ingest_is_idempotent_and_leaves_v1_untouched(db, tmp_path, isolated_source):
    v1_before = _v1_state(db)
    inspection = inspect_thin_blood_smears_pf(build_tree(tmp_path))

    first = ingest_smear_source(db, inspection)
    second = ingest_smear_source(db, inspect_thin_blood_smears_pf(tmp_path))

    assert first["result"] == "INSERTED"
    assert first["inserted"] == {
        "datasets": 1, "clinical_identities": 2, "dataset_source_records": 5,
        "identity_evidence": 5,
    }
    assert second["result"] == "ALREADY_INGESTED_MATCH_NO_OP"
    assert set(second["inserted"].values()) == {0}
    assert first["persisted"] == second["persisted"]
    assert second["persisted"] == {
        "patients": 2, "source_records": 5, "identity_evidence": 5,
        "records_without_identity": 0, "duplicate_image_sha256_groups": 0,
        "dataset_versions": 0, "split_assignments": 0,
    }
    identities = dict(db.execute(text("""
        SELECT i.source_identifier, count(DISTINCT r.clinical_identity_id)
        FROM dataset_source_records r JOIN clinical_identities i ON i.id=r.clinical_identity_id
        WHERE r.dataset_id=:dataset GROUP BY 1
    """), {"dataset": smear_source_ingest.dataset_source_id()}).all())
    assert identities == {"201C1P1ThinF": 1, "202C2NThinF": 1}
    assert _v1_state(db) == v1_before
    assert _v1_audit_status(db) == "PASS"


def test_changed_source_content_is_rejected_atomically(db, tmp_path, isolated_source):
    root = build_tree(tmp_path)
    ingest_smear_source(db, inspect_thin_blood_smears_pf(root))
    before = audit_smear_source(db)
    Image.new("RGB", (64, 48), (250, 1, 1)).save(root / "Polygon Set/201C1P1ThinF/Img/IMG_00.jpg")
    write_smear(root, "202C2NThinF", "IMG_09", seed=99)

    savepoint = db.begin_nested()
    with pytest.raises(SmearIngestConflict):
        ingest_smear_source(db, inspect_thin_blood_smears_pf(root))
    savepoint.rollback()
    assert audit_smear_source(db) == before


def test_failed_inspection_persists_nothing(db, tmp_path, isolated_source):
    root = build_tree(tmp_path)
    (root / "Polygon Set/201C1P1ThinF/GT/IMG_00.txt").unlink()
    inspection = inspect_thin_blood_smears_pf(root)
    assert not inspection.contract_passed
    with pytest.raises(SmearIngestConflict):
        ingest_smear_source(db, inspection)
    assert audit_smear_source(db)["source_records"] == 0


@pytest.mark.skipif(
    not os.environ.get("THIN_BLOOD_SMEARS_PF_ROOT"),
    reason="THIN_BLOOD_SMEARS_PF_ROOT not set; real ThinBloodSmearsPf copy unavailable",
)
def test_real_thin_blood_smears_pf_ingest_is_idempotent(db):
    root = Path(os.environ["THIN_BLOOD_SMEARS_PF_ROOT"])
    v1_before = _v1_state(db)
    first = ingest_smear_source(db, inspect_thin_blood_smears_pf(root))
    second = ingest_smear_source(db, inspect_thin_blood_smears_pf(root))
    assert second["result"] == "ALREADY_INGESTED_MATCH_NO_OP"
    assert first["persisted"] == second["persisted"]
    assert second["persisted"]["patients"] == len(inspect_thin_blood_smears_pf(root).patients)
    assert second["persisted"]["split_assignments"] == 0
    assert second["persisted"]["dataset_versions"] == 0
    assert _v1_state(db) == v1_before
    assert _v1_audit_status(db) == "PASS"
