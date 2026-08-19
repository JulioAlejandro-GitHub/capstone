"""Read-only adapter from scientific dataset governance to the Dataset UI."""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text

from app.db import get_engine, resolve_datasource


CAPSTONE_ROOT = Path(__file__).resolve().parents[3]
SPLIT_SOURCE = CAPSTONE_ROOT / "malaria_dataset_split_project" / "src"
if str(SPLIT_SOURCE) not in sys.path:
    sys.path.insert(0, str(SPLIT_SOURCE))

from malaria_split.governance.trainability import (  # noqa: E402
    REQUIRED_LOGICAL_VALIDATION_CHECKS,
    get_dataset_version_trainability,
    resolve_trainable_materialization,
)


def _details(value) -> dict:
    return value if isinstance(value, dict) else {}


def _latest_checks(connection, version_id: UUID) -> list[dict]:
    rows = connection.execute(text("""
        SELECT DISTINCT ON (check_name) check_name,status,observed_value,
               expected_value,details_json,blocking_for_validation,
               blocking_for_freeze,executed_at
        FROM dataset_split_validation_checks
        WHERE dataset_version_id=:id
        ORDER BY check_name,executed_at DESC,id DESC
    """), {"id": version_id}).mappings().all()
    return [dict(row) for row in rows]


def _statistics(connection, version_id: UUID) -> dict:
    row = connection.execute(text("""
        SELECT details_json FROM dataset_split_statistics
        WHERE dataset_version_id=:id
        ORDER BY computed_at DESC,id DESC LIMIT 1
    """), {"id": version_id}).mappings().one_or_none()
    return _details(row["details_json"]) if row else {}


def _summary(connection, version: dict) -> dict:
    version_id = version["id"]
    statistics = _statistics(connection, version_id)
    records = _details(statistics.get("records"))
    patients = _details(statistics.get("patients"))
    checks = _latest_checks(connection, version_id)
    required = [item for item in checks if item["check_name"] in REQUIRED_LOGICAL_VALIDATION_CHECKS]
    materialization = resolve_trainable_materialization(connection, version_id)
    trainability = get_dataset_version_trainability(connection, version_id)
    return {
        "dataset_version_id": version_id,
        "name": version["name"],
        "semantic_version": version["semantic_version"],
        "status": version["status"],
        "trainable": trainability.trainable,
        "trainability_reasons": list(trainability.reasons),
        "source_record_count": int(version["source_record_count"] or 0),
        "patient_count": int(statistics.get("total_patients") or sum(int(v) for v in patients.values())),
        "train_records": int(records.get("train") or 0),
        "val_records": int(records.get("val") or 0),
        "test_records": int(records.get("test") or 0),
        "train_patients": int(patients.get("train") or 0),
        "val_patients": int(patients.get("val") or 0),
        "test_patients": int(patients.get("test") or 0),
        "validation_pass_count": sum(item["status"] == "PASS" for item in required),
        "validation_required_count": len(REQUIRED_LOGICAL_VALIDATION_CHECKS),
        "materialization_status": materialization["status"] if materialization else None,
        "reconciliation_status": materialization["reconciliation_status"] if materialization else None,
        "created_at": version["created_at"],
        "generated_at": version["generated_at"],
        "validated_at": version["validated_at"],
        "frozen_at": version["frozen_at"],
    }


def list_governed_dataset_versions(datasource: str | None) -> dict:
    key = resolve_datasource(datasource)
    with get_engine(key).connect() as connection:
        versions = connection.execute(text("""
            SELECT * FROM dataset_versions
            ORDER BY created_at DESC,id DESC
        """)).mappings().all()
        return {"items": [_summary(connection, dict(version)) for version in versions]}


def governed_dataset_version_detail(datasource: str | None, dataset_version_id: UUID) -> dict:
    key = resolve_datasource(datasource)
    with get_engine(key).connect() as connection:
        version_row = connection.execute(text(
            "SELECT * FROM dataset_versions WHERE id=:id"
        ), {"id": dataset_version_id}).mappings().one_or_none()
        if version_row is None:
            raise HTTPException(404, "Dataset Version no encontrada.")
        version = dict(version_row)
        summary = _summary(connection, version)
        statistics = _statistics(connection, dataset_version_id)
        checks = _latest_checks(connection, dataset_version_id)
        materialization = resolve_trainable_materialization(connection, dataset_version_id)
        methodology = _details(version.get("methodology_json"))
        freeze_contract = _details(methodology.get("freeze_contract"))
        fingerprints = _details(freeze_contract.get("fingerprints"))
        reconciliation = _details(
            _details(materialization.get("manifest_metadata") if materialization else {}).get("reconciliation")
        )
        overlaps = _details(reconciliation.get("patient_overlaps"))
        run_rows = connection.execute(text("""
            SELECT r.id AS run_id,r.run_name,r.run_type,r.status,r.started_at,
                   COALESCE(m.name,r.execution_parameters->>'model_name',
                            r.parameters->>'model_name') AS model_name
            FROM runs r LEFT JOIN models m ON m.id=r.model_id
            WHERE r.dataset_version_id=:id
            ORDER BY r.started_at DESC NULLS LAST,r.id DESC
        """), {"id": dataset_version_id}).mappings().all()
    return {
        "dataset": {
            **summary,
            "grouping_strategy": version["grouping_strategy"],
            "grouping_field": version["grouping_field"],
            "split_algorithm": version["split_algorithm"],
            "split_algorithm_version": version["split_algorithm_version"],
            "random_seed": version["random_seed"],
            "positive_class": version["positive_class"],
            "class_mapping": version["class_mapping"],
        },
        "distribution": {
            "records": _details(statistics.get("records")),
            "patients": _details(statistics.get("patients")),
            "class_counts": _details(statistics.get("class_counts")),
            "total_patients": int(statistics.get("total_patients") or 0),
            "total_records": int(statistics.get("total_source_records") or version["source_record_count"] or 0),
        },
        "integrity": {
            "patient_disjoint": all(int(overlaps.get(name) or 0) == 0 for name in ("train_val", "train_test", "val_test")),
            "patient_train_val_overlap": int(overlaps.get("train_val") or 0),
            "patient_train_test_overlap": int(overlaps.get("train_test") or 0),
            "patient_val_test_overlap": int(overlaps.get("val_test") or 0),
            "duplicate_cross_split_overlap": next((int(item["observed_value"]) for item in checks if item["check_name"] == "duplicate_cross_split_overlap"), 0),
        },
        "validation": {
            "required_count": len(REQUIRED_LOGICAL_VALIDATION_CHECKS),
            "pass_count": sum(item["status"] == "PASS" and item["check_name"] in REQUIRED_LOGICAL_VALIDATION_CHECKS for item in checks),
            "fail_count": sum(item["status"] == "FAIL" and item["check_name"] in REQUIRED_LOGICAL_VALIDATION_CHECKS for item in checks),
            "checks": checks,
        },
        "materialization": None if materialization is None else {
            "dataset_materialization_id": materialization["id"],
            "status": materialization["status"],
            "reconciliation_status": materialization["reconciliation_status"],
            "record_count": int(materialization["record_count"] or 0),
            "sha_files_checked": int(reconciliation.get("sha_files_checked") or 0),
            "sha_match": int(reconciliation.get("sha_match") or 0),
            "sha_mismatch": int(reconciliation.get("sha_mismatch") or 0),
            "attempt_number": materialization["attempt_number"],
            "relative_root": materialization["relative_root"],
            "started_at": materialization["started_at"],
            "completed_at": materialization["completed_at"],
        },
        "lineage": {
            "contract_version": freeze_contract.get("version"),
            "source_population_fingerprint": fingerprints.get("source_population_sha256"),
            "clinical_identity_fingerprint": fingerprints.get("clinical_identity_sha256"),
            "patient_assignment_fingerprint": fingerprints.get("patient_assignment_sha256"),
            "record_assignment_fingerprint": fingerprints.get("record_assignment_sha256"),
        },
        "lifecycle": ["DRAFT", "GENERATED", "VALIDATED", "FROZEN"],
        "runs": {"items": [dict(row) for row in run_rows], "count": len(run_rows)},
    }
