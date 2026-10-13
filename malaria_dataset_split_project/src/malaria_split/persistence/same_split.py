"""S2 transaction: preflight, source verify/ingest, provisional version, assignments.

No optimizer, RNG, validation/freeze, materialization or Cell mutation is invoked.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from collections import Counter
from collections.abc import Callable, Sequence
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import Connection, Engine, text

from malaria_split.governance.dataset_lifecycle import transition_dataset_version
from malaria_split.governance.freeze import compute_final_fingerprints
from malaria_split.sources.thin_blood_smears_pf import SmearSourceInspection
from malaria_split.splitting.same_split import (
    SameSplitConflict, check_audited_distribution, inherit_patient_assignments,
)
from .repositories import DatasetVersionRepository
from .smear_source_ingest import dataset_source_id, ingest_smear_source, prepare_smear_rows
from .split_generation import ASSIGNMENT_NAMESPACE, V1_ID, _bulk_insert, audit_persisted_assignments

STRATEGY = "thin_blood_smear_same_split_v1"
VERSION_ID = uuid5(ASSIGNMENT_NAMESPACE, STRATEGY)
IDENTITY_RULE = "canonical_nlm_full_smear_patient_key:s1.2:v1"


def _reference_fingerprints(connection: Connection) -> dict[str, str]:
    return {key + "_sha256": value for key, value in asdict(compute_final_fingerprints(connection, V1_ID)).items()}


def preflight(connection: Connection, inspections: Sequence[SmearSourceInspection]) -> dict[str, Any]:
    reference_version = DatasetVersionRepository(connection).get(V1_ID)
    if reference_version is None or reference_version["status"] != "FROZEN":
        raise SameSplitConflict("STOP: protected Cell version is not FROZEN")
    fingerprints = _reference_fingerprints(connection)
    if fingerprints != reference_version["methodology_json"]["freeze_contract"]["fingerprints"]:
        raise SameSplitConflict("STOP: protected Cell fingerprints differ")
    if {s.annotation_set for s in inspections} != {"Polygon Set", "Point Set"} or len(inspections) != 2:
        raise SameSplitConflict("STOP: expected separate Polygon and Point inspections")
    if any(not s.contract_passed for s in inspections):
        raise SameSplitConflict("STOP: source inspection failed")
    records = [r for s in inspections for r in s.records]
    grouped = Counter(r.patient_id for r in records)
    if len(records) != 965 or set(grouped.values()) != {5}:
        raise SameSplitConflict("STOP: each patient must have five source records")
    if len({r.source_record_key for r in records}) != len(records):
        raise SameSplitConflict("STOP: duplicate source record")
    if len({r.image_sha256 for r in records}) != len(records):
        raise SameSplitConflict("STOP: duplicate Full Smear image")
    if any(r.annotation_set != s.annotation_set for s in inspections for r in s.records):
        raise SameSplitConflict("STOP: annotation set mismatch")
    if sum(len(s.patients) for s in inspections) != len(grouped):
        raise SameSplitConflict("STOP: patient appears in multiple source sets")
    keys = {r.patient_id: r.canonical_nlm_patient_key for r in records}
    reference = list(connection.execute(text("""
        SELECT i.source_identifier,a.split_name
        FROM dataset_split_assignments a
        JOIN clinical_identities i ON i.id=a.clinical_identity_id
        JOIN dataset_source_records r ON r.id=a.source_record_id
        JOIN dataset_version_sources vs ON vs.dataset_id=r.dataset_id
          AND vs.dataset_version_id=a.dataset_version_id
        WHERE a.dataset_version_id=:id
    """), {"id": V1_ID}).tuples())
    if Counter(split for _, split in reference) != {"train": 22180, "val": 2693, "test": 2685}:
        raise SameSplitConflict("STOP: protected Cell record counts differ")
    assignments = inherit_patient_assignments(keys, reference)
    polygon = next(s for s in inspections if s.annotation_set == "Polygon Set")
    check_audited_distribution(assignments, set(polygon.patients))
    annotation_counts = {split: Counter() for split in ("train", "val", "test")}
    for record in polygon.records:
        annotation_counts[assignments[record.patient_id]].update(record.label_counts)
    expected = {
        "train": {"Parasitized": 1057, "Uninfected": 27236, "White_Blood_Cell": 47},
        "val": {"Parasitized": 35, "Uninfected": 2026, "White_Blood_Cell": 2},
        "test": {"Parasitized": 50, "Uninfected": 3809, "White_Blood_Cell": 2},
    }
    if annotation_counts != expected:
        raise SameSplitConflict("STOP: Polygon annotation distribution mismatch")
    return {"status": "PASS", "patient_assignments": assignments, "canonical_keys": keys,
            "patients": len(keys), "canonical_ids": len(set(keys.values())),
            "cell_matches": len(keys), "cell_assignments": len(assignments),
            "no_assignment": 0, "canonical_collisions": 0,
            "reference_fingerprints": fingerprints, "polygon_annotations": annotation_counts}


def _definition(inspections: Sequence[SmearSourceInspection], plan: dict[str, Any]) -> dict[str, Any]:
    methodology = {
        "dataset_family": "smear_segmentation", "policy": "SAME_SPLIT",
        "reference_dataset_version_id": str(V1_ID), "identity_rule": IDENTITY_RULE,
        "identity_evidence": "technical naming convention; not clinical identity verification",
        "reference_fingerprints": plan["reference_fingerprints"],
        "source_fingerprints": {s.annotation_set: s.population_fingerprint for s in inspections},
        "seed_semantics": "schema requires integer; 0 unused, no RNG",
        "target_ratios_semantics": "reference nominal ratios; no optimization",
        "annotation_sets": {"Polygon Set": "polygon", "Point Set": "point; not segmentation masks"},
        "phase": "S2; provisional GENERATED; S3 validation and freeze pending",
    }
    return dict(id=VERSION_ID, name="Thin Blood Smear Patient Split", semantic_version="1.0.0",
                grouping_strategy="PATIENT", grouping_field="clinical_identity_id",
                stratification_strategy="inherit_reference_patient_assignment",
                split_algorithm=STRATEGY, split_algorithm_version="1.0.0", random_seed=0,
                target_train_ratio="0.8", target_val_ratio="0.1", target_test_ratio="0.1",
                positive_class="not_applicable_full_smear_image",
                class_mapping=json.dumps({"0": "full_smear_image"}), source_record_count=965,
                methodology_json=json.dumps(methodology, sort_keys=True))


def _assignment_rows(inspections: Sequence[SmearSourceInspection], plan: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    rows = []
    for inspection in inspections:
        prepared = prepare_smear_rows(inspection)
        patients = {r["id"]: r["source_identifier"] for r in prepared["identities"]}
        for record in prepared["records"]:
            patient = patients[record["clinical_identity_id"]]
            rows.append(dict(
                id=uuid5(ASSIGNMENT_NAMESPACE, f"{VERSION_ID}:{record['id']}"),
                dataset_version_id=VERSION_ID, source_record_id=record["id"],
                clinical_identity_id=record["clinical_identity_id"],
                split_name=plan["patient_assignments"][patient],
                class_index=record["class_index"], class_name=record["class_name"],
                metadata=json.dumps({"algorithm": STRATEGY, "canonical_patient_id": plan["canonical_keys"][patient],
                                     "reference_dataset_version_id": str(V1_ID),
                                     "annotation_set": inspection.annotation_set}, sort_keys=True)))
    return tuple(sorted(rows, key=lambda r: str(r["source_record_id"])))


def persist_same_split(
    connection: Connection, inspections: Sequence[SmearSourceInspection],
    failure_hook: Callable[[Connection], None] | None = None,
) -> dict[str, Any]:
    """Caller owns transaction; all preflight gates precede the first INSERT."""
    connection.execute(text("SELECT pg_advisory_xact_lock(2026100302)"))
    connection.execute(text("SELECT id FROM dataset_versions WHERE id=:id FOR SHARE"), {"id": V1_ID})
    plan = preflight(connection, inspections)
    definition = _definition(inspections, plan)
    rows = _assignment_rows(inspections, plan)
    repository = DatasetVersionRepository(connection)
    existing = repository.get(VERSION_ID)
    if existing:
        for key, value in definition.items():
            actual = existing[key]
            if key in ("class_mapping", "methodology_json"):
                value = json.loads(value)
            elif key.startswith("target_"):
                actual = str(actual.normalize())
            if actual != value:
                raise SameSplitConflict(f"CONFLICT: version {key}")
        if existing["status"] != "GENERATED":
            raise SameSplitConflict("CONFLICT: S2 version lifecycle no longer GENERATED")
        actual_rows = [dict(r) for r in connection.execute(text("""
            SELECT id,dataset_version_id,source_record_id,clinical_identity_id,split_name,
                   class_index,class_name,metadata FROM dataset_split_assignments
            WHERE dataset_version_id=:id ORDER BY source_record_id
        """), {"id": VERSION_ID}).mappings()]
        expected_rows = [{**r, "metadata": json.loads(r["metadata"])} for r in rows]
        if actual_rows != expected_rows:
            raise SameSplitConflict("CONFLICT: existing assignments differ")
        links = list(connection.execute(text("SELECT dataset_id,role FROM dataset_version_sources WHERE dataset_version_id=:id"), {"id": VERSION_ID}).tuples())
        if set(links) != {(dataset_source_id(s.annotation_set), "PRIMARY") for s in inspections}:
            raise SameSplitConflict("CONFLICT: version sources differ")
    ingests = [ingest_smear_source(connection, inspection) for inspection in inspections]
    if existing and any(r["result"] == "INSERTED" for r in ingests):
        raise SameSplitConflict("CONFLICT: existing version had missing source content")
    if not existing:
        repository.add_draft(definition)
        for inspection in inspections:
            connection.execute(text("""INSERT INTO dataset_version_sources(dataset_version_id,dataset_id,role)
                                     VALUES (:version,:source,'PRIMARY')"""),
                               {"version": VERSION_ID, "source": dataset_source_id(inspection.annotation_set)})
        _bulk_insert(connection, rows)
        if failure_hook:
            failure_hook(connection)
        transition_dataset_version(connection, VERSION_ID, "GENERATED")
    audit = audit_persisted_assignments(connection, VERSION_ID)
    if (audit["total_assignments"] != 965 or audit["distinct_patients"] != 193
            or audit["patient_overlap"] or audit["duplicate_cross_split_overlap"]):
        raise SameSplitConflict("STOP: persisted assignment audit failed")
    # Explicit join across every record, including Point (not just Polygon).
    persisted = connection.execute(text("""
        SELECT i.source_identifier,a.split_name FROM dataset_split_assignments a
        JOIN clinical_identities i ON i.id=a.clinical_identity_id
        WHERE a.dataset_version_id=:id
    """), {"id": VERSION_ID}).tuples()
    if any(plan["patient_assignments"].get(patient) != split for patient, split in persisted):
        raise SameSplitConflict("STOP: cross-family mismatch")
    if _reference_fingerprints(connection) != plan["reference_fingerprints"]:
        raise SameSplitConflict("STOP: protected Cell changed during transaction")
    return {"result": "ALREADY_EXISTS_MATCH" if existing else "INSERTED",
            "dataset_version_id": str(VERSION_ID), "status": "GENERATED",
            "assignments": audit["total_assignments"], "patients": audit["distinct_patients"],
            "patient_counts": audit["patient_counts"], "image_counts": audit["split_counts"],
            "patient_digest": audit["patient_digest"], "record_digest": audit["record_digest"],
            "patient_overlap": audit["patient_overlap"], "cross_family_mismatches": 0,
            "sources": ingests, "preflight": plan}


def apply_same_split(engine: Engine, inspections: Sequence[SmearSourceInspection]) -> dict[str, Any]:
    with engine.begin() as connection:
        return persist_same_split(connection, inspections)
