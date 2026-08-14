"""Formal SPLIT 4 validation calculated first and persisted atomically."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID, uuid5

from sqlalchemy import Connection, Engine, text

from malaria_split.governance.dataset_lifecycle import transition_dataset_version
from malaria_split.governance.trainability import REQUIRED_LOGICAL_VALIDATION_CHECKS
from malaria_split.persistence.split_generation import (
    APPROVED_ASSIGNMENT_DIGEST,
    APPROVED_RECORD_ASSIGNMENT_DIGEST,
    V1_ID,
    audit_persisted_assignments,
)

VALIDATION_NAMESPACE = UUID("6380038e-6a15-551e-ac67-63ff46e56df1")
STATISTIC_METRIC = "formal_scientific_validation_v1"


class FormalValidationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class FormalValidationPreparation:
    dataset_version_id: UUID
    statistics: dict[str, Any]
    checks: dict[str, dict[str, Any]]
    patient_digest: str
    record_digest: str


@dataclass(frozen=True, slots=True)
class FormalValidationResult:
    already_validated: bool
    status: str
    validated_at: Any
    statistics_count: int
    validation_check_count: int


def _check(observed: Any, expected: Any, passed: bool, **details: Any) -> dict[str, Any]:
    return {
        "status": "PASS" if passed else "FAIL",
        "observed": str(observed), "expected": str(expected), "details": details,
    }


def prepare_formal_validation(
    connection: Connection, dataset_version_id: UUID = V1_ID
) -> FormalValidationPreparation:
    version = connection.execute(text("""
        SELECT status FROM dataset_versions WHERE id=:id
    """), {"id": dataset_version_id}).scalar_one()
    if version not in ("GENERATED", "VALIDATED"):
        raise FormalValidationError(f"Validation requires GENERATED or VALIDATED, got {version}")
    audit = audit_persisted_assignments(connection, dataset_version_id)
    if audit["patient_digest"] != APPROVED_ASSIGNMENT_DIGEST:
        raise FormalValidationError("PATIENT_ASSIGNMENT_DIGEST_MISMATCH")
    if audit["record_digest"] != APPROVED_RECORD_ASSIGNMENT_DIGEST:
        raise FormalValidationError("RECORD_ASSIGNMENT_DIGEST_MISMATCH")

    source = connection.execute(text("""
        SELECT count(*) records,
          count(*) FILTER (WHERE r.clinical_identity_id IS NOT NULL
                            AND r.identity_status='VERIFIED' AND i.status='VERIFIED') identified,
          count(*) FILTER (WHERE r.identity_status='CONFLICT' OR i.status='CONFLICT') conflicts,
          count(*) FILTER (WHERE r.class_name='parasitized') parasitized,
          count(*) FILTER (WHERE r.class_name='uninfected') uninfected
        FROM dataset_version_sources vs
        JOIN dataset_source_records r ON r.dataset_id=vs.dataset_id
        LEFT JOIN clinical_identities i ON i.id=r.clinical_identity_id
        WHERE vs.dataset_version_id=:id AND vs.role='PRIMARY'
    """), {"id": dataset_version_id}).mappings().one()
    unassigned_records = connection.execute(text("""
        SELECT count(*) FROM dataset_version_sources vs
        JOIN dataset_source_records r ON r.dataset_id=vs.dataset_id
        WHERE vs.dataset_version_id=:id AND vs.role='PRIMARY'
          AND NOT EXISTS (SELECT 1 FROM dataset_split_assignments a
            WHERE a.dataset_version_id=:id AND a.source_record_id=r.id)
    """), {"id": dataset_version_id}).scalar_one()
    multi_records = connection.execute(text("""
        SELECT count(*) FROM (SELECT source_record_id FROM dataset_split_assignments
        WHERE dataset_version_id=:id GROUP BY source_record_id HAVING count(*)<>1) q
    """), {"id": dataset_version_id}).scalar_one()
    invalid_splits = connection.execute(text("""
        SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=:id
          AND split_name NOT IN ('train','val','test')
    """), {"id": dataset_version_id}).scalar_one()
    unassigned_patients = connection.execute(text("""
        SELECT count(*) FROM clinical_identities i JOIN dataset_version_sources vs
          ON vs.dataset_id=i.dataset_id AND vs.role='PRIMARY'
        WHERE vs.dataset_version_id=:id AND i.identity_type='PATIENT' AND i.status='VERIFIED'
          AND NOT EXISTS (SELECT 1 FROM dataset_split_assignments a
            WHERE a.dataset_version_id=:id AND a.clinical_identity_id=i.id)
    """), {"id": dataset_version_id}).scalar_one()

    split_counts = audit["split_counts"]
    patient_counts = audit["patient_counts"]
    class_counts = audit["class_counts"]
    profile_counts = audit["profile_counts"]
    statistics = {
        "total_source_records": source["records"], "total_patients": audit["distinct_patients"],
        "total_parasitized": source["parasitized"], "total_uninfected": source["uninfected"],
        "records": {s: split_counts.get(s, 0) for s in ("train", "val", "test")},
        "patients": {s: patient_counts.get(s, 0) for s in ("train", "val", "test")},
        "record_ratios": {s: split_counts.get(s, 0) / source["records"] for s in ("train", "val", "test")},
        "patient_ratios": {s: patient_counts.get(s, 0) / audit["distinct_patients"] for s in ("train", "val", "test")},
        "class_counts": {s: {c: class_counts.get((s, c), 0) for c in ("parasitized", "uninfected")} for s in ("train", "val", "test")},
        "patient_profiles": {s: {
            "BOTH_CLASSES": profile_counts.get((s, "BOTH_CLASSES"), 0),
            "UNINFECTED_ONLY": profile_counts.get((s, "UNINFECTED_ONLY"), 0),
            "PARASITIZED_ONLY": profile_counts.get((s, "PARASITIZED_ONLY"), 0),
        } for s in ("train", "val", "test")},
        "patient_assignment_digest": audit["patient_digest"],
        "record_assignment_digest": audit["record_digest"],
    }
    sets = {s: set(connection.execute(text("""
        SELECT DISTINCT clinical_identity_id FROM dataset_split_assignments
        WHERE dataset_version_id=:id AND split_name=:split
    """), {"id": dataset_version_id, "split": s}).scalars()) for s in ("train", "val", "test")}
    completeness = not any((unassigned_records, multi_records, unassigned_patients,
                            audit["patient_overlap"], invalid_splits))
    checks = {
        "identity_coverage": _check(source["identified"], source["records"], source["identified"] == source["records"]),
        "identity_conflicts": _check(source["conflicts"], 0, source["conflicts"] == 0),
        "patient_train_val_overlap": _check(len(sets["train"] & sets["val"]), 0, not sets["train"] & sets["val"]),
        "patient_train_test_overlap": _check(len(sets["train"] & sets["test"]), 0, not sets["train"] & sets["test"]),
        "patient_val_test_overlap": _check(len(sets["val"] & sets["test"]), 0, not sets["val"] & sets["test"]),
        "duplicate_cross_split_overlap": _check(audit["duplicate_cross_split_overlap"], 0, audit["duplicate_cross_split_overlap"] == 0),
        "assignment_count": _check(audit["total_assignments"], 27558, audit["total_assignments"] == 27558),
        "source_record_count": _check(source["records"], 27558, source["records"] == 27558),
        "split_completeness": _check("complete" if completeness else "incomplete", "complete", completeness,
            unassigned_source_records=unassigned_records, multiassigned_source_records=multi_records,
            unassigned_patients=unassigned_patients, multi_split_patients=audit["patient_overlap"], invalid_splits=invalid_splits),
    }
    for split in ("train", "val", "test"):
        present = all(class_counts.get((split, c), 0) > 0 for c in ("parasitized", "uninfected"))
        checks[f"class_presence_{split}"] = _check("both" if present else "missing", "both", present)
    if set(checks) != set(REQUIRED_LOGICAL_VALIDATION_CHECKS):
        raise FormalValidationError("REQUIRED_CHECK_SET_MISMATCH")
    return FormalValidationPreparation(dataset_version_id, statistics, checks,
                                       audit["patient_digest"], audit["record_digest"])


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def persist_formal_validation(
    connection: Connection, prepared: FormalValidationPreparation,
    failure_hook: Callable[[Connection], None] | None = None,
) -> FormalValidationResult:
    version = connection.execute(text("""
        SELECT status,validated_at FROM dataset_versions WHERE id=:id FOR UPDATE NOWAIT
    """), {"id": prepared.dataset_version_id}).mappings().one()
    stat_rows = connection.execute(text("""
        SELECT metric_name,details_json FROM dataset_split_statistics WHERE dataset_version_id=:id
    """), {"id": prepared.dataset_version_id}).mappings().all()
    check_rows = connection.execute(text("""
        SELECT check_name,status,observed_value,expected_value,details_json,
               blocking_for_validation,blocking_for_freeze
        FROM dataset_split_validation_checks WHERE dataset_version_id=:id
    """), {"id": prepared.dataset_version_id}).mappings().all()
    if version["status"] == "VALIDATED":
        if len(stat_rows) != 1 or stat_rows[0]["metric_name"] != STATISTIC_METRIC or stat_rows[0]["details_json"] != prepared.statistics:
            raise FormalValidationError("VALIDATED_STATE_CONFLICT")
        persisted = {row["check_name"]: row for row in check_rows}
        if len(persisted) != 12 or any(
            name not in persisted or persisted[name]["status"] != check["status"]
            or persisted[name]["observed_value"] != check["observed"]
            or persisted[name]["expected_value"] != check["expected"]
            or persisted[name]["details_json"] != check["details"]
            or not persisted[name]["blocking_for_validation"]
            or not persisted[name]["blocking_for_freeze"]
            for name, check in prepared.checks.items()
        ):
            raise FormalValidationError("VALIDATED_STATE_CONFLICT")
        return FormalValidationResult(True, "VALIDATED", version["validated_at"], 1, 12)
    if version["status"] != "GENERATED" or stat_rows or check_rows:
        raise FormalValidationError("VALIDATION_TRANSACTION_PRECONDITION_FAILED")
    failed = [name for name, check in prepared.checks.items() if check["status"] != "PASS"]
    if failed:
        raise FormalValidationError(f"PREVALIDATION_FAILED:{','.join(failed)}")
    connection.execute(text("""
        INSERT INTO dataset_split_statistics(id,dataset_version_id,scope,metric_name,details_json)
        VALUES (:row_id,:version_id,'dataset',:metric,CAST(:details AS jsonb))
    """), {"row_id": uuid5(VALIDATION_NAMESPACE, f"{prepared.dataset_version_id}:statistics"),
            "version_id": prepared.dataset_version_id, "metric": STATISTIC_METRIC,
            "details": _canonical_json(prepared.statistics)})
    statement = text("""
        INSERT INTO dataset_split_validation_checks(
          id,dataset_version_id,check_name,status,observed_value,expected_value,details_json,
          blocking_for_validation,blocking_for_freeze)
        VALUES (:id,:version_id,:name,:status,:observed,:expected,CAST(:details AS jsonb),true,true)
    """)
    connection.execute(statement, [{"id": uuid5(VALIDATION_NAMESPACE, f"{prepared.dataset_version_id}:{name}"),
        "version_id": prepared.dataset_version_id, "name": name, **check,
        "details": _canonical_json(check["details"])} for name, check in prepared.checks.items()])
    if failure_hook:
        failure_hook(connection)
    if connection.execute(text("""
        SELECT count(*) FROM dataset_split_validation_checks WHERE dataset_version_id=:id
          AND status='PASS' AND blocking_for_validation
    """), {"id": prepared.dataset_version_id}).scalar_one() != 12:
        raise FormalValidationError("PERSISTED_REQUIRED_CHECKS_NOT_PASS")
    transitioned = transition_dataset_version(connection, prepared.dataset_version_id, "VALIDATED")
    return FormalValidationResult(False, transitioned["status"], transitioned["validated_at"], 1, 12)


def apply_formal_validation(engine: Engine, prepared: FormalValidationPreparation) -> FormalValidationResult:
    with engine.begin() as connection:
        return persist_formal_validation(connection, prepared)
