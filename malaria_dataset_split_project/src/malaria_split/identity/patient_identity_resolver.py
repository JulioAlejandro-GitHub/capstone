import csv
from pathlib import Path

from .identity_evidence import EVIDENCE_PRECEDENCE, EvidenceType, IdentityStatus, ResolvedClinicalIdentity
from .source_identity_index import decoded_pixel_key


def resolve_one(
    *,
    tfds_index: int,
    physical_path: Path,
    physical_relative_path: str,
    historical_split: str,
    class_name: str,
    label: int,
    source_index: dict,
) -> ResolvedClinicalIdentity:
    key = decoded_pixel_key(physical_path)
    candidates = [item for item in source_index.get(key, []) if item.class_name == class_name]
    if candidates:
        best_rank = min(EVIDENCE_PRECEDENCE[item.evidence_type] for item in candidates)
        candidates = [item for item in candidates if EVIDENCE_PRECEDENCE[item.evidence_type] == best_rank]
    patients = {item.patient_id for item in candidates if item.patient_id}
    if not candidates:
        status, patient_id, method = IdentityStatus.UNRESOLVED, None, "no_match"
    elif len(patients) != 1:
        status, patient_id, method = IdentityStatus.CONFLICT, None, "multiple_patient_mapping"
    elif len({item.source_record_id for item in candidates}) != 1:
        status, patient_id, method = IdentityStatus.CONFLICT, None, "multiple_source_matches"
    else:
        status, patient_id, method = IdentityStatus.VERIFIED, next(iter(patients)), "decoded_pixel_hash_to_official_metadata"
    first = candidates[0] if candidates else None
    return ResolvedClinicalIdentity(
        tfds_index=tfds_index,
        physical_relative_path=physical_relative_path,
        historical_split=historical_split,
        class_name=class_name,
        label=label,
        source_record_id=first.source_record_id if first else None,
        source_filename=first.source_filename if first else None,
        patient_id=patient_id,
        sample_id=None,
        smear_id=None,
        slide_id=None,
        identity_status=status,
        evidence_type=first.evidence_type if first else EvidenceType.NONE,
        evidence_reference=first.evidence_reference if first else None,
        mapping_method=method,
        ambiguity_count=len(candidates),
    )


def resolve_physical_manifest(manifest_path: Path, physical_root: Path, source_index: dict) -> list[ResolvedClinicalIdentity]:
    results = []
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        for tfds_index, row in enumerate(csv.DictReader(handle)):
            relative_path = row["relative_path"]
            results.append(
                resolve_one(
                    tfds_index=tfds_index,
                    physical_path=physical_root / relative_path,
                    physical_relative_path=relative_path,
                    historical_split=row["split"],
                    class_name=row["class_name"],
                    label=int(row["project_label"]),
                    source_index=source_index,
                )
            )
    return results
