"""Atomic final lineage seal and freeze for Malaria Patient Split v1."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Iterable, Callable, Sequence

if TYPE_CHECKING:
    from malaria_split.sources.thin_blood_smears_pf import SmearSourceInspection
from uuid import UUID

from sqlalchemy import Connection, Engine, text

from malaria_split.governance.dataset_lifecycle import transition_dataset_version
from malaria_split.governance.trainability import (
    REQUIRED_LOGICAL_VALIDATION_CHECKS,
    get_dataset_version_trainability,
    logical_validation_passes,
    resolve_trainable_materialization,
)
from malaria_split.persistence.split_generation import (
    APPROVED_ASSIGNMENT_DIGEST,
    APPROVED_RECORD_ASSIGNMENT_DIGEST,
    V1_ID,
    audit_persisted_assignments,
)

FREEZE_CONTRACT_VERSION = "malaria_patient_split_freeze_v1"


class FreezeError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class FinalFingerprints:
    source_population: str
    clinical_identity: str
    patient_assignment: str
    record_assignment: str


@dataclass(frozen=True, slots=True)
class FreezeOutcome:
    result: str
    dataset_version_id: UUID
    materialization_id: UUID | None
    fingerprints: FinalFingerprints
    frozen_at: Any
    trainable: bool
    trainability_reasons: tuple[str, ...]


def _canonical_digest(rows: Iterable[Iterable[Any]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update("|".join("" if value is None else str(value) for value in row).encode())
        digest.update(b"\n")
    return digest.hexdigest()


def compute_source_population_fingerprint(
    connection: Connection, dataset_version_id: UUID
) -> str:
    rows = connection.execute(text("""
        SELECT r.id,r.clinical_identity_id,r.class_name,
               r.source_file_sha256,r.decoded_pixel_sha256
        FROM dataset_source_records r
        JOIN dataset_version_sources vs ON vs.dataset_id=r.dataset_id
        WHERE vs.dataset_version_id=:id
        ORDER BY r.id
    """), {"id": dataset_version_id})
    return _canonical_digest(rows)


def compute_clinical_identity_fingerprint(
    connection: Connection, dataset_version_id: UUID
) -> str:
    rows = connection.execute(text("""
        SELECT i.id,i.source_identifier,i.status
        FROM clinical_identities i
        JOIN dataset_version_sources vs ON vs.dataset_id=i.dataset_id
        WHERE vs.dataset_version_id=:id
        ORDER BY i.id
    """), {"id": dataset_version_id})
    return _canonical_digest(rows)


def compute_final_fingerprints(
    connection: Connection, dataset_version_id: UUID = V1_ID
) -> FinalFingerprints:
    assignments = audit_persisted_assignments(connection, dataset_version_id)
    return FinalFingerprints(
        source_population=compute_source_population_fingerprint(connection, dataset_version_id),
        clinical_identity=compute_clinical_identity_fingerprint(connection, dataset_version_id),
        patient_assignment=assignments["patient_digest"],
        record_assignment=assignments["record_digest"],
    )


def _preflight(connection: Connection, dataset_version_id: UUID) -> tuple[dict, dict]:
    version = dict(connection.execute(text(
        "SELECT * FROM dataset_versions WHERE id=:id FOR UPDATE"
    ), {"id": dataset_version_id}).mappings().one())
    if version["status"] not in {"VALIDATED", "FROZEN"}:
        raise FreezeError(f"FREEZE_REQUIRES_VALIDATED:{version['status']}")
    if not logical_validation_passes(connection, dataset_version_id):
        raise FreezeError("FORMAL_VALIDATION_NOT_PASS")
    materialization = resolve_trainable_materialization(connection, dataset_version_id)
    if materialization is None:
        raise FreezeError("NO_READY_RECONCILED_MATERIALIZATION")
    if materialization.get("record_count") != 27_558:
        raise FreezeError("MATERIALIZATION_RECORD_COUNT_MISMATCH")
    return version, materialization


def _freeze_contract(
    connection: Connection,
    version: dict,
    materialization: dict,
    fingerprints: FinalFingerprints,
) -> dict[str, Any]:
    assignment_count = connection.execute(text("""
        SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=:id
    """), {"id": version["id"]}).scalar_one()
    identity_count = connection.execute(text("""
        SELECT count(*) FROM clinical_identities i
        JOIN dataset_version_sources vs ON vs.dataset_id=i.dataset_id
        WHERE vs.dataset_version_id=:id
    """), {"id": version["id"]}).scalar_one()
    return {
        "version": FREEZE_CONTRACT_VERSION,
        "dataset_version_id": str(version["id"]),
        "dataset_materialization_id": str(materialization["id"]),
        "materialization_attempt_number": materialization["attempt_number"],
        "materialization_status": materialization["status"],
        "reconciliation_status": materialization["reconciliation_status"],
        "split_algorithm": version["split_algorithm"],
        "split_algorithm_version": version["split_algorithm_version"],
        "random_seed": version["random_seed"],
        "source_record_count": version["source_record_count"],
        "assignment_count": assignment_count,
        "clinical_identity_count": identity_count,
        "required_validation_checks": list(REQUIRED_LOGICAL_VALIDATION_CHECKS),
        "required_validation_check_count": len(REQUIRED_LOGICAL_VALIDATION_CHECKS),
        "fingerprints": {
            "source_population_sha256": fingerprints.source_population,
            "clinical_identity_sha256": fingerprints.clinical_identity,
            "patient_assignment_sha256": fingerprints.patient_assignment,
            "record_assignment_sha256": fingerprints.record_assignment,
        },
    }


def _freeze_materialized_cell_dataset_version(engine: Engine, dataset_version_id: UUID) -> FreezeOutcome:
    with engine.begin() as connection:
        version, materialization = _preflight(connection, dataset_version_id)
        run_a = compute_final_fingerprints(connection, dataset_version_id)
        run_b = compute_final_fingerprints(connection, dataset_version_id)
        if run_a != run_b:
            raise FreezeError("FINAL_FINGERPRINT_REPRODUCIBILITY_FAIL")
        if run_a.patient_assignment != APPROVED_ASSIGNMENT_DIGEST:
            raise FreezeError("PATIENT_ASSIGNMENT_DIGEST_MISMATCH")
        if run_a.record_assignment != APPROVED_RECORD_ASSIGNMENT_DIGEST:
            raise FreezeError("RECORD_ASSIGNMENT_DIGEST_MISMATCH")
        contract = _freeze_contract(connection, version, materialization, run_a)
        methodology = dict(version["methodology_json"] or {})
        existing = methodology.get("freeze_contract")
        if version["status"] == "FROZEN":
            if existing != contract:
                raise FreezeError("FROZEN_STATE_CONFLICT")
            result = "ALREADY_FROZEN_MATCH_NO_OP"
        else:
            if existing is not None and existing != contract:
                raise FreezeError("PREEXISTING_FREEZE_CONTRACT_CONFLICT")
            methodology["freeze_contract"] = contract
            connection.execute(text("""
                UPDATE dataset_versions SET methodology_json=CAST(:methodology AS jsonb)
                WHERE id=:id
            """), {"id": dataset_version_id,
                     "methodology": json.dumps(methodology, sort_keys=True)})
            transition_dataset_version(connection, dataset_version_id, "FROZEN")
            result = "FROZEN_COMMIT"
        frozen_at = connection.execute(text(
            "SELECT frozen_at FROM dataset_versions WHERE id=:id"
        ), {"id": dataset_version_id}).scalar_one()
    with engine.connect() as connection:
        state = get_dataset_version_trainability(connection, dataset_version_id)
    return FreezeOutcome(result, dataset_version_id, materialization["id"], run_a,
                         frozen_at, state.trainable, state.reasons)


def freeze_dataset_version(
    engine: Engine, dataset_version_id: UUID = V1_ID, *,
    source_inspections: Sequence[SmearSourceInspection] | None = None,
    expected_assignments: dict[str, str] | None = None,
    integrity_guard: Callable[[Connection], None] | None = None,
) -> FreezeOutcome:
    """Freeze through the family contract; a source seal does not imply TRAINABLE.

    Cell retains its historical READY materialization and approved digest gates.
    Smear validates the existing source population before S4 changes representation.
    """
    with engine.begin() as connection:
        version = connection.execute(text(
            "SELECT * FROM dataset_versions WHERE id=:id FOR UPDATE NOWAIT"
        ), {"id": dataset_version_id}).mappings().one()
        if version['methodology_json'].get('dataset_family') == 'smear_segmentation':
            if source_inspections is None or expected_assignments is None or integrity_guard is None:
                raise FreezeError('SOURCE_FREEZE_REQUIRES_INSPECTIONS_S2_EVIDENCE_AND_INTEGRITY_GUARD')
            return _freeze_governed_source(connection, dict(version), source_inspections,
                                           expected_assignments, integrity_guard)
    return _freeze_materialized_cell_dataset_version(engine, dataset_version_id)


def _freeze_governed_source(
    connection: Connection, version: dict[str, Any],
    inspections: Sequence[SmearSourceInspection], expected_assignments: dict[str, str],
    integrity_guard: Callable[[Connection], None],
) -> FreezeOutcome:
    # Lazy imports avoid the existing S2 -> freeze fingerprint dependency cycle.
    from malaria_split.persistence.formal_validation import persist_formal_validation
    from malaria_split.persistence.smear_validation import prepare_smear_validation

    dataset_version_id = version['id']
    connection.execute(text('SELECT pg_advisory_xact_lock(2026100302)'))
    connection.execute(text('SELECT id FROM dataset_versions WHERE id=:id FOR SHARE'), {'id': V1_ID})
    prepared = prepare_smear_validation(connection, inspections, expected_assignments, dataset_version_id)
    persist_formal_validation(connection, prepared.formal)
    if not logical_validation_passes(connection, dataset_version_id):
        raise FreezeError('FORMAL_VALIDATION_NOT_PASS')
    repeated = prepare_smear_validation(connection, inspections, expected_assignments, dataset_version_id)
    if prepared != repeated:
        raise FreezeError('FINAL_FINGERPRINT_REPRODUCIBILITY_FAIL')
    contract = {
        'version': 'governed_source_freeze_v1', 'scope': 'source_population_and_assignments',
        'dataset_version_id': str(dataset_version_id), 'dataset_family': 'smear_segmentation',
        'reference_dataset_version_id': str(V1_ID),
        'split_algorithm': version['split_algorithm'],
        'identity_rule': version['methodology_json']['identity_rule'],
        'source_record_count': prepared.formal.statistics['total_source_records'],
        'assignment_count': prepared.formal.statistics['total_assignments'],
        'clinical_identity_count': prepared.formal.statistics['total_patients'],
        'required_validation_checks': sorted(prepared.formal.checks),
        'required_validation_check_count': len(prepared.formal.checks),
        'fingerprints': prepared.fingerprints,
        'manifest_contract': prepared.manifest['contract'],
        'manifest_sha256': prepared.manifest_fingerprint,
        'source_provenance': prepared.manifest['sources'],
        's4_consumption': 'explicit dataset_version_id; Polygon only; inherit every assignment',
        'scientific_limitations': prepared.formal.statistics['scientific_limitations'],
    }
    methodology = dict(version['methodology_json'])
    existing = methodology.get('freeze_contract')
    if version['status'] == 'FROZEN':
        if existing != contract:
            raise FreezeError('FROZEN_STATE_CONFLICT')
        result = 'ALREADY_FROZEN_MATCH_NO_OP'
    else:
        if existing is not None:
            raise FreezeError('PREEXISTING_FREEZE_CONTRACT_CONFLICT')
        # RAW/Cell inventories and protected rows are checked inside the transaction.
        # Any failure rolls back validation rows and lifecycle as well as the seal.
        integrity_guard(connection)
        methodology['freeze_contract'] = contract
        connection.execute(text('UPDATE dataset_versions SET methodology_json=CAST(:metadata AS jsonb) WHERE id=:id'),
                           {'id': dataset_version_id, 'metadata': json.dumps(methodology, sort_keys=True)})
        transition_dataset_version(connection, dataset_version_id, 'FROZEN')
        result = 'FROZEN_COMMIT'
    if version['status'] == 'FROZEN':
        integrity_guard(connection)
    fingerprints = compute_final_fingerprints(connection, dataset_version_id)
    if ({key + '_sha256': value for key, value in asdict(fingerprints).items()} != prepared.fingerprints
            or fingerprints != compute_final_fingerprints(connection, dataset_version_id)):
        raise FreezeError('FINAL_FINGERPRINT_REPRODUCIBILITY_FAIL')
    frozen_at = connection.execute(text('SELECT frozen_at FROM dataset_versions WHERE id=:id'), {'id': dataset_version_id}).scalar_one()
    state = get_dataset_version_trainability(connection, dataset_version_id)
    return FreezeOutcome(result, dataset_version_id, None, fingerprints, frozen_at, state.trainable, state.reasons)
