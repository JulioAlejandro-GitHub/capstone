"""Atomic persistence shared by SPLIT 3B rehearsal and future apply."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable
from uuid import UUID, uuid5

from sqlalchemy import Connection, Engine, text

from malaria_split.governance.dataset_lifecycle import transition_dataset_version
from malaria_split.governance.trainability import get_dataset_version_trainability
from malaria_split.splitting import load_patient_profiles
from malaria_split.splitting.candidate import canonical_assignment_digest
from malaria_split.splitting.optimizer import OptimizationResult, optimize_patient_split


V1_ID = UUID("d8c0cab5-09dd-597f-9de7-7ca01aee2ec2")
APPROVED_ASSIGNMENT_DIGEST = "cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f"
APPROVED_RECORD_ASSIGNMENT_DIGEST = "9709ce48b9b41bcacca49ccfb53ec62b48c4822c2fb8e227643bf26aed196ea2"
ASSIGNMENT_NAMESPACE = UUID("ec41e4bb-4967-5dbf-b311-3c8dd44a87df")


class PersistenceMode(StrEnum):
    REHEARSE = "REHEARSE"
    APPLY = "APPLY"


class DigestMismatch(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PreparedSplitGeneration:
    dataset_version_id: UUID
    optimization: OptimizationResult
    assignment_rows: tuple[dict[str, Any], ...]
    methodology_json: dict[str, Any]


@dataclass(frozen=True, slots=True)
class PersistenceResult:
    mode: PersistenceMode
    regenerated_digest: str
    persisted_assignment_digest: str
    persisted_record_assignment_digest: str
    audit: dict[str, Any]
    rolled_back: bool
    already_applied: bool = False


def _methodology(existing: dict[str, Any], optimization: OptimizationResult) -> dict[str, Any]:
    result = dict(existing)
    winner = optimization.winner
    result["generation_contract"] = {
        "algorithm_name": "patient_group_stratified_v1",
        "algorithm_version": "1.0.0",
        "seed": 42,
        "randomization_unit": "clinical_identity_id",
        "randomization_method": "canonical_order_plus_local_seeded_prng_permutations",
        "objective": list(winner.evaluation.objective_tuple),
        "objective_function": "lexicographic_normalized_maximum_deviations",
        "objective_priority": [
            "representativeness", "class_balance", "record_ratio",
            "patient_ratio", "canonical_assignment_digest",
        ],
        "candidate_generation": {"method": "bounded_seeded_multi_start", "initial_candidates": 16},
        "local_search": {
            "method": "patient_level_move_and_swap", "iteration_limit_per_start": 30,
            "optimized_starts": 4, "neighbor_proposals_per_iteration": 20,
        },
        "tie_break": "canonical_assignment_digest_ASC",
        "approved_assignment_digest": winner.evaluation.canonical_assignment_digest,
        "record_assignment_digest": APPROVED_RECORD_ASSIGNMENT_DIGEST,
        "winning_candidate_id": winner.candidate_id,
        "patient_counts": {split: winner.evaluation.split_metrics[split].patients for split in ("train", "val", "test")},
        "record_counts": {split: winner.evaluation.split_metrics[split].records for split in ("train", "val", "test")},
        "class_counts": {
            split: {
                "parasitized": winner.evaluation.split_metrics[split].parasitized_records,
                "uninfected": winner.evaluation.split_metrics[split].uninfected_records,
            } for split in ("train", "val", "test")
        },
    }
    return result


def prepare_split_generation(
    connection: Connection,
    dataset_version_id: UUID = V1_ID,
    expected_digest: str = APPROVED_ASSIGNMENT_DIGEST,
) -> PreparedSplitGeneration:
    """Read-only regeneration and row expansion, performed before the write transaction."""
    version = connection.execute(
        text("SELECT status,methodology_json FROM dataset_versions WHERE id=:id"),
        {"id": dataset_version_id},
    ).mappings().one()
    assignment_count = connection.execute(
        text("SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=:id"),
        {"id": dataset_version_id},
    ).scalar_one()
    if version["status"] not in ("DRAFT", "GENERATED"):
        raise RuntimeError("Split generation requires DRAFT or matching GENERATED state")
    if version["status"] == "DRAFT" and assignment_count != 0:
        raise RuntimeError("DRAFT split generation requires zero assignments")
    profiles = load_patient_profiles(connection, dataset_version_id)
    optimization = optimize_patient_split(profiles, 42)
    regenerated = optimization.winner.evaluation.canonical_assignment_digest
    if regenerated != expected_digest:
        raise DigestMismatch(f"DIGEST_MISMATCH:{regenerated}:{expected_digest}")
    rows = connection.execute(text("""
        SELECT id source_record_id,clinical_identity_id,class_index,class_name
        FROM dataset_source_records ORDER BY id
    """)).mappings()
    assignments = optimization.winner.assignments
    prepared_rows = tuple({
        "id": uuid5(ASSIGNMENT_NAMESPACE, f"{dataset_version_id}:{row['source_record_id']}"),
        "dataset_version_id": dataset_version_id,
        "source_record_id": row["source_record_id"],
        "clinical_identity_id": row["clinical_identity_id"],
        "split_name": assignments[row["clinical_identity_id"]],
        "class_index": row["class_index"], "class_name": row["class_name"],
        "metadata": json.dumps({
            "algorithm": "patient_group_stratified_v1", "algorithm_version": "1.0.0",
            "approved_patient_assignment_digest": regenerated,
        }, sort_keys=True),
    } for row in rows)
    if len(prepared_rows) != 27_558:
        raise RuntimeError("Expected 27558 assignment rows")
    return PreparedSplitGeneration(
        dataset_version_id=dataset_version_id, optimization=optimization,
        assignment_rows=prepared_rows,
        methodology_json=_methodology(version["methodology_json"], optimization),
    )


def _bulk_insert(connection: Connection, rows: tuple[dict[str, Any], ...]) -> None:
    statement = text("""
        INSERT INTO dataset_split_assignments(
          id,dataset_version_id,source_record_id,clinical_identity_id,split_name,
          class_index,class_name,metadata
        ) VALUES (
          :id,:dataset_version_id,:source_record_id,:clinical_identity_id,:split_name,
          :class_index,:class_name,CAST(:metadata AS jsonb)
        )
    """)
    for offset in range(0, len(rows), 1000):
        connection.execute(statement, rows[offset:offset + 1000])


def _sha256_lines(lines: list[str]) -> str:
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def audit_persisted_assignments(
    connection: Connection, dataset_version_id: UUID
) -> dict[str, Any]:
    patient_rows = connection.execute(text("""
        SELECT clinical_identity_id,split_name,count(*) records
        FROM dataset_split_assignments WHERE dataset_version_id=:id
        GROUP BY clinical_identity_id,split_name
        ORDER BY clinical_identity_id,split_name
    """), {"id": dataset_version_id}).mappings().all()
    record_rows = connection.execute(text("""
        SELECT source_record_id,clinical_identity_id,split_name
        FROM dataset_split_assignments WHERE dataset_version_id=:id
        ORDER BY source_record_id
    """), {"id": dataset_version_id}).mappings().all()
    patient_digest = _sha256_lines([
        f"{row['clinical_identity_id']}|{row['split_name']}" for row in patient_rows
    ])
    record_digest = _sha256_lines([
        f"{row['source_record_id']}|{row['clinical_identity_id']}|{row['split_name']}"
        for row in record_rows
    ])
    split_counts = dict(connection.execute(text("""
        SELECT split_name,count(*) FROM dataset_split_assignments
        WHERE dataset_version_id=:id GROUP BY split_name
    """), {"id": dataset_version_id}).all())
    patient_counts = dict(connection.execute(text("""
        SELECT split_name,count(DISTINCT clinical_identity_id)
        FROM dataset_split_assignments WHERE dataset_version_id=:id GROUP BY split_name
    """), {"id": dataset_version_id}).all())
    class_counts = {(split, cls): count for split, cls, count in connection.execute(text("""
        SELECT split_name,class_name,count(*) FROM dataset_split_assignments
        WHERE dataset_version_id=:id GROUP BY split_name,class_name
    """), {"id": dataset_version_id}).all()}
    profile_counts = {(split, profile): count for split, profile, count in connection.execute(text("""
        SELECT split_name,
          CASE WHEN parasitized>0 AND uninfected>0 THEN 'BOTH_CLASSES'
               WHEN uninfected>0 THEN 'UNINFECTED_ONLY'
               ELSE 'PARASITIZED_ONLY' END profile,
          count(*)
        FROM (
          SELECT split_name,clinical_identity_id,
            count(*) FILTER(WHERE class_name='parasitized') parasitized,
            count(*) FILTER(WHERE class_name='uninfected') uninfected
          FROM dataset_split_assignments WHERE dataset_version_id=:id
          GROUP BY split_name,clinical_identity_id
        ) p GROUP BY split_name,profile
    """), {"id": dataset_version_id}).all()}
    overlaps = connection.execute(text("""
        SELECT count(*) FROM (
          SELECT clinical_identity_id FROM dataset_split_assignments
          WHERE dataset_version_id=:id GROUP BY clinical_identity_id
          HAVING count(DISTINCT split_name)>1
        ) q
    """), {"id": dataset_version_id}).scalar_one()
    duplicate_overlap = connection.execute(text("""
        SELECT count(*) FROM (
          SELECT r.source_file_sha256 FROM dataset_split_assignments a
          JOIN dataset_source_records r ON r.id=a.source_record_id
          WHERE a.dataset_version_id=:id GROUP BY r.source_file_sha256
          HAVING count(DISTINCT a.split_name)>1
        ) q
    """), {"id": dataset_version_id}).scalar_one()
    return {
        "total_assignments": len(record_rows), "distinct_source_records": len({r["source_record_id"] for r in record_rows}),
        "distinct_patients": len({r["clinical_identity_id"] for r in record_rows}),
        "split_counts": split_counts, "patient_counts": patient_counts,
        "class_counts": class_counts, "profile_counts": profile_counts,
        "patient_overlap": overlaps,
        "duplicate_cross_split_overlap": duplicate_overlap,
        "patient_digest": patient_digest, "record_digest": record_digest,
    }


def persist_split_generation(
    engine: Engine,
    prepared: PreparedSplitGeneration,
    mode: PersistenceMode,
    failure_hook: Callable[[Connection], None] | None = None,
) -> PersistenceResult:
    connection = engine.connect()
    transaction = connection.begin()
    rolled_back = False
    try:
        locked = connection.execute(text("""
            SELECT status FROM dataset_versions WHERE id=:id FOR UPDATE NOWAIT
        """), {"id": prepared.dataset_version_id}).scalar_one()
        count = connection.execute(text("""
            SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=:id
        """), {"id": prepared.dataset_version_id}).scalar_one()
        if locked == "GENERATED":
            audit = audit_persisted_assignments(connection, prepared.dataset_version_id)
            if (
                count != 27_558
                or audit["patient_digest"] != APPROVED_ASSIGNMENT_DIGEST
                or audit["record_digest"] != APPROVED_RECORD_ASSIGNMENT_DIGEST
            ):
                raise RuntimeError("GENERATED_STATE_CONFLICT")
            transaction.rollback()
            rolled_back = True
            return PersistenceResult(
                mode=mode, regenerated_digest=prepared.optimization.winner.evaluation.canonical_assignment_digest,
                persisted_assignment_digest=audit["patient_digest"],
                persisted_record_assignment_digest=audit["record_digest"], audit=audit,
                rolled_back=True, already_applied=True,
            )
        if locked != "DRAFT" or count != 0:
            raise RuntimeError("Transactional precondition failed")
        _bulk_insert(connection, prepared.assignment_rows)
        if failure_hook:
            failure_hook(connection)
        audit = audit_persisted_assignments(connection, prepared.dataset_version_id)
        approved = prepared.optimization.winner.evaluation.canonical_assignment_digest
        expected = {
            "total_assignments": 27558, "distinct_source_records": 27558,
            "distinct_patients": 201, "split_counts": {"train": 22180, "val": 2693, "test": 2685},
            "patient_counts": {"train": 161, "val": 20, "test": 20},
            "class_counts": {
                ("train", "parasitized"): 11137, ("train", "uninfected"): 11043,
                ("val", "parasitized"): 1325, ("val", "uninfected"): 1368,
                ("test", "parasitized"): 1317, ("test", "uninfected"): 1368,
            },
            "profile_counts": {
                ("train", "BOTH_CLASSES"): 121, ("train", "UNINFECTED_ONLY"): 40,
                ("val", "BOTH_CLASSES"): 15, ("val", "UNINFECTED_ONLY"): 5,
                ("test", "BOTH_CLASSES"): 15, ("test", "UNINFECTED_ONLY"): 5,
            },
            "patient_overlap": 0, "duplicate_cross_split_overlap": 0,
            "patient_digest": approved,
            "record_digest": APPROVED_RECORD_ASSIGNMENT_DIGEST,
        }
        for key, value in expected.items():
            if audit[key] != value:
                raise RuntimeError(f"Persistence audit mismatch {key}: {audit[key]!r} != {value!r}")
        connection.execute(text("""
            UPDATE dataset_versions SET methodology_json=CAST(:methodology AS jsonb)
            WHERE id=:id
        """), {"methodology": json.dumps(prepared.methodology_json, sort_keys=True),
                "id": prepared.dataset_version_id})
        transition_dataset_version(connection, prepared.dataset_version_id, "GENERATED")
        audit["status_inside_transaction"] = connection.execute(
            text("SELECT status FROM dataset_versions WHERE id=:id"), {"id": prepared.dataset_version_id}
        ).scalar_one()
        audit["generated_at_inside_transaction"] = connection.execute(
            text("SELECT generated_at FROM dataset_versions WHERE id=:id"),
            {"id": prepared.dataset_version_id},
        ).scalar_one()
        audit["trainable_inside_transaction"] = get_dataset_version_trainability(
            connection, prepared.dataset_version_id
        ).trainable
        if mode is PersistenceMode.REHEARSE:
            transaction.rollback()
            rolled_back = True
        else:
            transaction.commit()
        return PersistenceResult(
            mode=mode, regenerated_digest=approved,
            persisted_assignment_digest=audit["patient_digest"],
            persisted_record_assignment_digest=audit["record_digest"],
            audit=audit, rolled_back=rolled_back,
            already_applied=False,
        )
    except Exception:
        if transaction.is_active:
            transaction.rollback()
        rolled_back = True
        raise
    finally:
        connection.close()
