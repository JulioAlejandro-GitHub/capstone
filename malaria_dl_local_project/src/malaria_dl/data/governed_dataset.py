"""Governed dataset selection and immutable run lineage snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from contextlib import contextmanager
import argparse
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text

from src.malaria_dl.common.paths import PROJECT_ROOT
from src.malaria_dl.persistence.database import get_engine

REQUIRED_CHECKS = (
    "identity_coverage",
    "identity_conflicts",
    "patient_train_val_overlap",
    "patient_train_test_overlap",
    "patient_val_test_overlap",
    "duplicate_cross_split_overlap",
    "assignment_count",
    "source_record_count",
    "split_completeness",
    "class_presence_train",
    "class_presence_val",
    "class_presence_test",
)


class GovernedDatasetError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class GovernedDatasetSnapshot:
    dataset_version_id: UUID
    dataset_materialization_id: UUID
    dataset_root: Path
    patient_assignment_fingerprint: str
    record_assignment_fingerprint: str
    source_population_fingerprint: str
    clinical_identity_fingerprint: str
    counts: dict[str, Any]
    evidence_id: str | None = field(default=None, compare=False)

    def metadata(self) -> dict[str, Any]:
        return {
            "dataset_version_id": str(self.dataset_version_id),
            "dataset_materialization_id": str(self.dataset_materialization_id),
            "dataset_root": str(self.dataset_root),
            "patient_assignment_fingerprint": self.patient_assignment_fingerprint,
            "record_assignment_fingerprint": self.record_assignment_fingerprint,
            "source_population_fingerprint": self.source_population_fingerprint,
            "clinical_identity_fingerprint": self.clinical_identity_fingerprint,
            "counts": self.counts,
            "selection_unit": "dataset_version_id",
        }


def normalize_dataset_version_id(value) -> str:
    if value is None or not str(value).strip():
        raise GovernedDatasetError("DATASET_VERSION_ID_REQUIRED")
    try:
        return str(UUID(str(value).strip()))
    except (ValueError, TypeError, AttributeError) as exc:
        raise GovernedDatasetError("INVALID_DATASET_VERSION_ID") from exc


def dataset_uuid_arg(value):
    try:
        return normalize_dataset_version_id(value)
    except GovernedDatasetError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


@contextmanager
def dataset_read_connection():
    engine = get_engine()
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                )
                yield connection
    finally:
        engine.dispose()


def _resolve(connection, requested):
    row = (
        connection.execute(
            text(
                "SELECT id,status,methodology_json FROM dataset_versions WHERE id=:id"
            ),
            {"id": requested},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise GovernedDatasetError("DATASET_VERSION_NOT_FOUND")
    if row["status"] != "FROZEN":
        raise GovernedDatasetError("DATASET_VERSION_NOT_TRAINABLE")
    contract = (row["methodology_json"] or {}).get("freeze_contract") or {}
    if contract.get("version") != "malaria_patient_split_freeze_v1":
        raise GovernedDatasetError("FINAL_LINEAGE_NOT_SEALED")
    if normalize_dataset_version_id(contract.get("dataset_version_id")) != requested:
        raise GovernedDatasetError("DATASET_FREEZE_CONTRACT_MISMATCH")
    fingerprints = contract.get("fingerprints") or {}
    names = (
        "patient_assignment_sha256",
        "record_assignment_sha256",
        "source_population_sha256",
        "clinical_identity_sha256",
    )
    if any(
        not isinstance(fingerprints.get(k), str) or len(fingerprints[k]) != 64
        for k in names
    ):
        raise GovernedDatasetError("FINAL_LINEAGE_FINGERPRINT_MISSING")
    materialization_id = normalize_dataset_version_id(
        contract.get("dataset_materialization_id")
    )
    materialization = (
        connection.execute(
            text("""
        SELECT id,dataset_version_id,status,reconciliation_status,relative_root
        FROM dataset_materializations WHERE id=:id
    """),
            {"id": materialization_id},
        )
        .mappings()
        .one_or_none()
    )
    if (
        not materialization
        or str(materialization["dataset_version_id"]) != requested
        or str(materialization["id"]) != materialization_id
    ):
        raise GovernedDatasetError("MATERIALIZATION_FREEZE_CONTRACT_MISMATCH")
    if (
        materialization["status"] != "READY"
        or materialization["reconciliation_status"] != "PASS"
    ):
        raise GovernedDatasetError("SEALED_MATERIALIZATION_NOT_READY_PASS")
    checks = (
        connection.execute(
            text("""
        SELECT DISTINCT ON (check_name) check_name,status,blocking_for_validation
        FROM dataset_split_validation_checks WHERE dataset_version_id=:id
        ORDER BY check_name,executed_at DESC,id DESC
    """),
            {"id": requested},
        )
        .mappings()
        .all()
    )
    passed = {
        r["check_name"]
        for r in checks
        if r["status"] == "PASS" and r["blocking_for_validation"]
    }
    if not set(REQUIRED_CHECKS).issubset(passed) or any(
        r["blocking_for_validation"] and r["status"] == "FAIL" for r in checks
    ):
        raise GovernedDatasetError("DATASET_REQUIRED_CHECKS_NOT_PASS")
    relative = Path(materialization["relative_root"] or "")
    data_root = (PROJECT_ROOT / "data").resolve()
    root = (data_root / relative).resolve()
    if (
        relative.is_absolute()
        or not root.is_relative_to(data_root)
        or root == data_root
    ):
        raise GovernedDatasetError("MATERIALIZED_DATASET_ROOT_INVALID")
    if not root.is_dir():
        raise GovernedDatasetError("MATERIALIZED_DATASET_ROOT_MISSING")
    from .dataset_integrity import verify_integrity

    try:
        counts = verify_integrity(connection, requested, root, contract)
    except GovernedDatasetError as exc:
        exc.evidence = {
            "dataset_materialization_id": materialization_id,
            "dataset_root": str(root),
            "expected_fingerprints": fingerprints,
        }
        raise
    return GovernedDatasetSnapshot(
        UUID(requested),
        UUID(materialization_id),
        root,
        *(fingerprints[k] for k in names),
        counts,
    )


def resolve_governed_dataset(dataset_version_id=None) -> GovernedDatasetSnapshot:
    """Read-only verification. No implicit version and no writes or split commands."""
    requested = normalize_dataset_version_id(dataset_version_id)
    with dataset_read_connection() as connection:
        return _resolve(connection, requested)


def assert_run_dataset_snapshot_unchanged(requested, persisted) -> None:
    # Compare identity plus accredited physical location; never accept a relocated alias.
    keys = (
        "dataset_version_id",
        "dataset_materialization_id",
        "patient_assignment_fingerprint",
        "record_assignment_fingerprint",
        "source_population_fingerprint",
        "clinical_identity_fingerprint",
    )
    left = (
        requested.metadata()
        if isinstance(requested, GovernedDatasetSnapshot)
        else requested
    )
    right = (
        persisted.metadata()
        if isinstance(persisted, GovernedDatasetSnapshot)
        else persisted
    )
    if any(not right.get(k) or left.get(k) != right.get(k) for k in keys):
        raise GovernedDatasetError("RUN_DATASET_SNAPSHOT_IMMUTABLE")
    if (
        right.get("dataset_root")
        and Path(left["dataset_root"]).resolve()
        != Path(right["dataset_root"]).resolve()
    ):
        raise GovernedDatasetError("RUN_DATASET_ROOT_IMMUTABLE")
    if right.get("counts") is not None and left.get("counts") != right["counts"]:
        raise GovernedDatasetError("RUN_DATASET_COUNTS_IMMUTABLE")


def training_dataset_metadata(training_run_id):
    try:
        run_id = str(UUID(str(training_run_id)))
    except (ValueError, TypeError) as exc:
        raise GovernedDatasetError("INVALID_TRAINING_RUN_ID") from exc
    with dataset_read_connection() as connection:
        row = (
            connection.execute(
                text("""
            SELECT dataset_version_id,execution_parameters,parameters,metadata FROM runs
            WHERE id=:id AND run_type='training'
        """),
                {"id": run_id},
            )
            .mappings()
            .one_or_none()
        )
    if not row or not row["dataset_version_id"]:
        raise GovernedDatasetError("TRAIN_DATASET_NOT_ACCREDITED")
    version = normalize_dataset_version_id(row["dataset_version_id"])
    candidates = [row.get("execution_parameters") or {}, row.get("parameters") or {}]
    # Existing runs already store the snapshot in these JSONB columns. Never backfill.
    complete = [c for c in candidates if c.get("dataset_materialization_id")]
    if not complete:
        raise GovernedDatasetError("TRAIN_DATASET_SNAPSHOT_MISSING")
    snapshot = dict(complete[0])
    snapshot["dataset_version_id"] = normalize_dataset_version_id(
        snapshot.get("dataset_version_id")
    )
    snapshot["dataset_materialization_id"] = normalize_dataset_version_id(
        snapshot.get("dataset_materialization_id")
    )
    if snapshot["dataset_version_id"] != version:
        raise GovernedDatasetError("TRAIN_DATASET_SNAPSHOT_CONFLICT")
    for candidate in complete:
        normalized = dict(candidate)
        for key in ("dataset_version_id", "dataset_materialization_id"):
            normalized[key] = normalize_dataset_version_id(normalized.get(key))
        assert_run_dataset_snapshot_unchanged(snapshot, normalized)
    return snapshot


def resolve_training_run_dataset(training_run_id):
    persisted = training_dataset_metadata(training_run_id)
    resolved = resolve_governed_dataset(persisted["dataset_version_id"])
    assert_run_dataset_snapshot_unchanged(resolved, persisted)
    return resolved


def validate_dataset_location(snapshot, dataset_dir=None, data_source="physical"):
    if data_source not in (None, "physical"):
        raise GovernedDatasetError("GOVERNED_DATASET_REQUIRES_PHYSICAL")
    if dataset_dir is not None:
        path = Path(dataset_dir).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if path.resolve() != snapshot.dataset_root.resolve():
            raise GovernedDatasetError("DATASET_DIR_CONFLICT")
