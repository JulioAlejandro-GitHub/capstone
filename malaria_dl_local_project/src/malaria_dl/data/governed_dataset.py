"""Governed dataset selection and immutable run lineage snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text

from src.malaria_dl.common.paths import PROJECT_ROOT
from src.malaria_dl.persistence.database import get_engine

REQUIRED_CHECKS = (
    "identity_coverage", "identity_conflicts", "patient_train_val_overlap",
    "patient_train_test_overlap", "patient_val_test_overlap",
    "duplicate_cross_split_overlap", "assignment_count", "source_record_count",
    "split_completeness", "class_presence_train", "class_presence_val",
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


def _trainable_rows(connection) -> list[dict]:
    rows = connection.execute(text("""
        SELECT dv.id,dv.frozen_at,dv.methodology_json,
               dm.id AS materialization_id,dm.relative_root,dm.manifest_metadata
        FROM dataset_versions dv
        JOIN LATERAL (
          SELECT * FROM dataset_materializations
          WHERE dataset_version_id=dv.id AND status='READY'
            AND reconciliation_status='PASS'
          ORDER BY attempt_number DESC,completed_at DESC NULLS LAST,id DESC LIMIT 1
        ) dm ON true
        WHERE dv.status='FROZEN'
          AND NOT EXISTS (
            SELECT 1 FROM unnest(CAST(:checks AS text[])) required(name)
            WHERE NOT EXISTS (
              SELECT 1 FROM dataset_split_validation_checks c
              WHERE c.dataset_version_id=dv.id AND c.check_name=required.name
                AND c.blocking_for_validation AND c.status='PASS'
                AND NOT EXISTS (
                  SELECT 1 FROM dataset_split_validation_checks newer
                  WHERE newer.dataset_version_id=c.dataset_version_id
                    AND newer.check_name=c.check_name
                    AND (newer.executed_at,newer.id)>(c.executed_at,c.id)
                )
            )
          )
        ORDER BY dv.frozen_at DESC NULLS LAST,dv.id DESC
    """), {"checks": list(REQUIRED_CHECKS)}).mappings().all()
    return [dict(row) for row in rows]


def list_trainable_dataset_versions() -> list[UUID]:
    engine = get_engine()
    try:
        with engine.connect() as connection:
            return [row["id"] for row in _trainable_rows(connection)]
    finally:
        engine.dispose()


def resolve_governed_dataset(dataset_version_id: str | UUID | None = None) -> GovernedDatasetSnapshot:
    requested = None
    if dataset_version_id is not None:
        try:
            requested = UUID(str(dataset_version_id))
        except ValueError as exc:
            raise GovernedDatasetError("INVALID_DATASET_VERSION_ID") from exc
    engine = get_engine()
    try:
        with engine.connect() as connection:
            rows = _trainable_rows(connection)
            if requested is None:
                if not rows:
                    raise GovernedDatasetError("NO_TRAINABLE_DATASET_VERSION")
                row = rows[0]
            else:
                row = next((item for item in rows if item["id"] == requested), None)
                if row is None:
                    raise GovernedDatasetError("DATASET_VERSION_NOT_TRAINABLE")
    finally:
        engine.dispose()
    contract = (row["methodology_json"] or {}).get("freeze_contract")
    if not contract or contract.get("version") != "malaria_patient_split_freeze_v1":
        raise GovernedDatasetError("FINAL_LINEAGE_NOT_SEALED")
    fingerprints = contract.get("fingerprints") or {}
    required_fingerprints = (
        "patient_assignment_sha256", "record_assignment_sha256",
        "source_population_sha256", "clinical_identity_sha256",
    )
    if any(not fingerprints.get(name) for name in required_fingerprints):
        raise GovernedDatasetError("FINAL_LINEAGE_FINGERPRINT_MISSING")
    if str(row["materialization_id"]) != contract.get("dataset_materialization_id"):
        raise GovernedDatasetError("MATERIALIZATION_FREEZE_CONTRACT_MISMATCH")
    root = PROJECT_ROOT / "data" / Path(row["relative_root"])
    if not root.is_dir():
        raise GovernedDatasetError("MATERIALIZED_DATASET_ROOT_MISSING")
    reconciliation = (row["manifest_metadata"] or {}).get("reconciliation") or {}
    return GovernedDatasetSnapshot(
        row["id"], row["materialization_id"], root,
        fingerprints["patient_assignment_sha256"],
        fingerprints["record_assignment_sha256"],
        fingerprints["source_population_sha256"],
        fingerprints["clinical_identity_sha256"],
        reconciliation.get("split_counts") or {},
    )


def assert_run_dataset_snapshot_unchanged(requested: GovernedDatasetSnapshot,
                                          persisted: GovernedDatasetSnapshot) -> None:
    if requested != persisted:
        raise GovernedDatasetError("RUN_DATASET_SNAPSHOT_IMMUTABLE")


def resolve_training_run_dataset(training_run_id: str | UUID) -> GovernedDatasetSnapshot | None:
    """Inherit a governed dataset; None explicitly denotes a historical run."""
    try:
        run_id = UUID(str(training_run_id))
    except ValueError as exc:
        raise GovernedDatasetError("INVALID_TRAINING_RUN_ID") from exc
    engine = get_engine()
    try:
        with engine.connect() as connection:
            version_id = connection.execute(text("""
                SELECT dataset_version_id FROM runs
                WHERE id=:id AND run_type='training'
            """), {"id": run_id}).scalar_one()
    finally:
        engine.dispose()
    if version_id is None:
        return None
    return resolve_governed_dataset(version_id)
