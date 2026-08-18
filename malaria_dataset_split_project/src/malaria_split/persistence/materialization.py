"""Versioned byte-exact materialization and DB/filesystem reconciliation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import Connection, Engine, text

from malaria_split.persistence.split_generation import (
    APPROVED_ASSIGNMENT_DIGEST,
    APPROVED_RECORD_ASSIGNMENT_DIGEST,
    V1_ID,
    audit_persisted_assignments,
)

MATERIALIZATION_NAMESPACE = UUID("ac72c2d7-44f1-55fc-9cb6-b49c0ed41e84")
SPLITS = ("train", "val", "test")
CLASSES = ("parasitized", "uninfected")


class MaterializationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MaterializationEntry:
    source_record_id: UUID
    clinical_identity_id: UUID
    split_name: str
    class_name: str
    source_path: Path
    relative_path: Path
    source_sha256: str


@dataclass(frozen=True, slots=True)
class MaterializationPlan:
    dataset_version_id: UUID
    entries: tuple[MaterializationEntry, ...]
    patient_digest: str
    record_digest: str
    filename_collisions: int
    filename_strategy: str


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    expected_assignments: int
    files_found: int
    missing_files: int
    unexpected_files: int
    wrong_split_files: int
    wrong_class_files: int
    sha_files_checked: int
    sha_match: int
    sha_mismatch: int
    split_counts: dict[str, int]
    class_counts: dict[str, int]
    patient_counts: dict[str, int]
    patient_overlaps: dict[str, int]

    @property
    def passed(self) -> bool:
        return not any((self.missing_files, self.unexpected_files,
                        self.wrong_split_files, self.wrong_class_files,
                        self.sha_mismatch)) and self.files_found == self.expected_assignments


@dataclass(frozen=True, slots=True)
class MaterializationOutcome:
    materialization_id: UUID
    attempt_number: int
    already_materialized: bool
    final_root: Path
    staging_root: Path
    reconciliation: ReconciliationResult


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_materialization_plan(
    connection: Connection, source_root: Path, dataset_version_id: UUID = V1_ID
) -> MaterializationPlan:
    state = connection.execute(text("""
        SELECT status FROM dataset_versions WHERE id=:id
    """), {"id": dataset_version_id}).scalar_one()
    if state != "VALIDATED":
        raise MaterializationError(f"Materialization requires VALIDATED, got {state}")
    audit = audit_persisted_assignments(connection, dataset_version_id)
    if audit["patient_digest"] != APPROVED_ASSIGNMENT_DIGEST:
        raise MaterializationError("PATIENT_ASSIGNMENT_DIGEST_MISMATCH")
    if audit["record_digest"] != APPROVED_RECORD_ASSIGNMENT_DIGEST:
        raise MaterializationError("RECORD_ASSIGNMENT_DIGEST_MISMATCH")
    if connection.execute(text("""
        SELECT count(*) FROM dataset_split_validation_checks
        WHERE dataset_version_id=:id AND status='PASS' AND blocking_for_validation
    """), {"id": dataset_version_id}).scalar_one() != 12:
        raise MaterializationError("FORMAL_VALIDATION_NOT_PASS")
    rows = connection.execute(text("""
        SELECT a.source_record_id,a.clinical_identity_id,a.split_name,r.class_name,
               r.source_filename,r.source_file_sha256
        FROM dataset_split_assignments a JOIN dataset_source_records r ON r.id=a.source_record_id
        WHERE a.dataset_version_id=:id ORDER BY a.source_record_id
    """), {"id": dataset_version_id}).mappings().all()
    if len(rows) != 27_558:
        raise MaterializationError("EXPECTED_27558_ASSIGNMENTS")
    names = Counter((row["split_name"], row["class_name"], row["source_filename"]) for row in rows)
    collision_keys = {key for key, count in names.items() if count > 1}
    entries = []
    missing = []
    for row in rows:
        source = source_root / row["class_name"].capitalize() / row["source_filename"]
        if not source.is_file():
            missing.append(str(source))
        key = (row["split_name"], row["class_name"], row["source_filename"])
        filename = (
            f"{row['source_record_id']}__{row['source_filename']}"
            if key in collision_keys else row["source_filename"]
        )
        entries.append(MaterializationEntry(
            row["source_record_id"], row["clinical_identity_id"], row["split_name"],
            row["class_name"], source, Path(row["split_name"]) / row["class_name"] / filename,
            row["source_file_sha256"],
        ))
    if missing:
        raise MaterializationError(f"MISSING_SOURCE_FILES:{len(missing)}")
    return MaterializationPlan(dataset_version_id, tuple(entries), audit["patient_digest"],
                               audit["record_digest"], len(collision_keys),
                               "PRESERVE_SOURCE_FILENAME" if not collision_keys
                               else "SOURCE_RECORD_ID_PREFIX_ON_COLLISION")


def reconcile_materialization(plan: MaterializationPlan, root: Path) -> ReconciliationResult:
    expected = {entry.relative_path.as_posix(): entry for entry in plan.entries}
    actual = {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*") if path.is_file()
    } if root.is_dir() else {}
    missing = set(expected) - set(actual)
    unexpected = set(actual) - set(expected)
    sha_match = 0
    sha_mismatch = 0
    for relative in set(expected) & set(actual):
        if _sha256(actual[relative]) == expected[relative].source_sha256:
            sha_match += 1
        else:
            sha_mismatch += 1
    split_counts = Counter(entry.split_name for key, entry in expected.items() if key in actual)
    class_counts = Counter(f"{entry.split_name}|{entry.class_name}" for key, entry in expected.items() if key in actual)
    patient_sets = {split: {entry.clinical_identity_id for entry in plan.entries if entry.split_name == split}
                    for split in SPLITS}
    return ReconciliationResult(
        len(expected), len(actual), len(missing), len(unexpected), 0, 0,
        len(set(expected) & set(actual)), sha_match, sha_mismatch,
        dict(split_counts), dict(class_counts), {s: len(patient_sets[s]) for s in SPLITS},
        {"train_val": len(patient_sets["train"] & patient_sets["val"]),
         "train_test": len(patient_sets["train"] & patient_sets["test"]),
         "val_test": len(patient_sets["val"] & patient_sets["test"])},
    )


def _manifest(plan: MaterializationPlan, result: ReconciliationResult) -> dict[str, Any]:
    return {
        "contract": "byte_exact_assignment_materialization_v1",
        "filename_strategy": plan.filename_strategy,
        "filename_collisions": plan.filename_collisions,
        "patient_assignment_digest": plan.patient_digest,
        "record_assignment_digest": plan.record_digest,
        "reconciliation": {
            "files_found": result.files_found, "missing_files": result.missing_files,
            "unexpected_files": result.unexpected_files, "sha_files_checked": result.sha_files_checked,
            "sha_match": result.sha_match, "sha_mismatch": result.sha_mismatch,
            "split_counts": result.split_counts, "class_counts": result.class_counts,
            "patient_counts": result.patient_counts, "patient_overlaps": result.patient_overlaps,
        },
    }


def materialize_dataset_version(
    engine: Engine, plan: MaterializationPlan, versions_root: Path
) -> MaterializationOutcome:
    final_root = versions_root / str(plan.dataset_version_id)
    with engine.begin() as connection:
        connection.execute(text("SELECT id FROM dataset_versions WHERE id=:id FOR UPDATE NOWAIT"),
                           {"id": plan.dataset_version_id})
        existing = connection.execute(text("""
            SELECT * FROM dataset_materializations WHERE dataset_version_id=:id
            ORDER BY attempt_number DESC
        """), {"id": plan.dataset_version_id}).mappings().all()
        ready = [row for row in existing if row["status"] == "READY" and row["reconciliation_status"] == "PASS"]
        if ready:
            if len(ready) != 1:
                raise MaterializationError("MATERIALIZED_STATE_CONFLICT")
            result = reconcile_materialization(plan, final_root)
            if not result.passed or ready[0]["manifest_metadata"] != _manifest(plan, result):
                raise MaterializationError("MATERIALIZED_STATE_CONFLICT")
            attempt = ready[0]["attempt_number"]
            staging = versions_root / f".{plan.dataset_version_id}.attempt-{attempt}.staging"
            return MaterializationOutcome(ready[0]["id"], attempt, True, final_root, staging, result)
        if final_root.exists():
            raise MaterializationError("FINAL_ROOT_EXISTS_WITHOUT_READY_PASS")
        attempt = max((row["attempt_number"] for row in existing), default=0) + 1
        materialization_id = uuid5(MATERIALIZATION_NAMESPACE, f"{plan.dataset_version_id}:{attempt}")
        relative_root = Path("malaria_dataset_versions") / str(plan.dataset_version_id)
        connection.execute(text("""
            INSERT INTO dataset_materializations(
              id,dataset_version_id,attempt_number,status,reconciliation_status,
              relative_root,started_at,metadata)
            VALUES (:id,:version,:attempt,'MATERIALIZING','PENDING',:root,now(),CAST(:metadata AS jsonb))
        """), {"id": materialization_id, "version": plan.dataset_version_id,
                "attempt": attempt, "root": relative_root.as_posix(),
                "metadata": json.dumps({"staging_name": f".{plan.dataset_version_id}.attempt-{attempt}.staging"})})
    staging = versions_root / f".{plan.dataset_version_id}.attempt-{attempt}.staging"
    try:
        if staging.exists():
            raise MaterializationError("ATTEMPT_STAGING_ALREADY_EXISTS")
        for split in SPLITS:
            for class_name in CLASSES:
                (staging / split / class_name).mkdir(parents=True, exist_ok=False)
        for entry in plan.entries:
            shutil.copyfile(entry.source_path, staging / entry.relative_path)
        staged = reconcile_materialization(plan, staging)
        if not staged.passed:
            raise MaterializationError("STAGING_RECONCILIATION_FAILED")
        versions_root.mkdir(parents=True, exist_ok=True)
        os.replace(staging, final_root)
        final = reconcile_materialization(plan, final_root)
        if not final.passed:
            raise MaterializationError("POST_PROMOTION_RECONCILIATION_FAILED")
        with engine.begin() as connection:
            connection.execute(text("""
                UPDATE dataset_materializations SET status='READY',reconciliation_status='PASS',
                  record_count=:count,manifest_metadata=CAST(:manifest AS jsonb),completed_at=now()
                WHERE id=:id AND status='MATERIALIZING' AND reconciliation_status='PENDING'
            """), {"count": final.files_found, "manifest": json.dumps(_manifest(plan, final), sort_keys=True),
                    "id": materialization_id})
        return MaterializationOutcome(materialization_id, attempt, False, final_root, staging, final)
    except Exception as exc:
        with engine.begin() as connection:
            connection.execute(text("""
                UPDATE dataset_materializations SET status='FAILED',reconciliation_status='FAIL',
                  failure_reason=:reason,completed_at=now() WHERE id=:id AND status='MATERIALIZING'
            """), {"reason": str(exc), "id": materialization_id})
        raise
