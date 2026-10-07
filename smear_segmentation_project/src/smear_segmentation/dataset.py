"""Read-only access to governed Full Smear Polygon records."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Connection, text

from malaria_split.sources.thin_blood_smears_pf import SmearSourceInspection


SMEAR_SEGMENTATION_DATASET_VERSION_ID = UUID(
    "f0c1f636-715c-54e2-8e46-ed150f9d8791"
)

POLYGON_DATASET_ID = UUID(
    "3ea11683-fddb-5ed5-8fa1-c41000a9ebd1"
)


@dataclass(frozen=True)
class SmearRecord:
    source_record_id: UUID
    clinical_identity_id: UUID
    split: str
    patient_id: str
    image_relative_path: str
    image_sha256: str
    image_width: int
    image_height: int
    annotation: dict


def load_polygon_records(
    connection: Connection,
    dataset_version_id: UUID = SMEAR_SEGMENTATION_DATASET_VERSION_ID,
) -> tuple[SmearRecord, ...]:
    """Return the governed Polygon Set records without modifying persistence."""

    rows = connection.execute(
        text(
            """
            SELECT
                a.source_record_id,
                a.clinical_identity_id,
                a.split_name,
                i.source_identifier AS patient_id,
                r.relative_source_key,
                r.source_file_sha256,
                r.image_width,
                r.image_height,
                r.metadata->'annotation' AS annotation
            FROM dataset_split_assignments a
            JOIN dataset_source_records r
              ON r.id = a.source_record_id
            JOIN clinical_identities i
              ON i.id = a.clinical_identity_id
            WHERE a.dataset_version_id = :dataset_version_id
              AND r.dataset_id = :polygon_dataset_id
            ORDER BY
                a.split_name,
                i.source_identifier,
                r.relative_source_key
            """
        ),
        {
            "dataset_version_id": dataset_version_id,
            "polygon_dataset_id": POLYGON_DATASET_ID,
        },
    ).mappings()

    return tuple(
        SmearRecord(
            source_record_id=row["source_record_id"],
            clinical_identity_id=row["clinical_identity_id"],
            split=row["split_name"],
            patient_id=row["patient_id"],
            image_relative_path=row["relative_source_key"],
            image_sha256=row["source_file_sha256"],
            image_width=row["image_width"],
            image_height=row["image_height"],
            annotation=dict(row["annotation"]),
        )
        for row in rows
    )

def validate_physical_records(
    governed_records: tuple[SmearRecord, ...],
    inspection: SmearSourceInspection,
) -> None:
    """Validate governed PostgreSQL records against the inspected physical source."""

    if not inspection.contract_passed:
        raise ValueError(
            f"Physical Polygon source contract failed with "
            f"{len(inspection.issues)} issue(s)"
        )

    physical_by_path = {
        record.image_relative_path: record
        for record in inspection.records
    }

    governed_paths = {
        record.image_relative_path
        for record in governed_records
    }

    physical_paths = set(physical_by_path)

    if governed_paths != physical_paths:
        missing = sorted(governed_paths - physical_paths)
        unexpected = sorted(physical_paths - governed_paths)
        raise ValueError(
            "Governed and physical Polygon populations differ: "
            f"missing={missing[:5]}, unexpected={unexpected[:5]}"
        )

    for governed in governed_records:
        physical = physical_by_path[governed.image_relative_path]

        annotation_path = governed.annotation.get("relative_path")
        annotation_sha256 = governed.annotation.get("sha256")

        checks = {
            "patient_id": (
                governed.patient_id,
                physical.patient_id,
            ),
            "image_sha256": (
                governed.image_sha256,
                physical.image_sha256,
            ),
            "image_width": (
                governed.image_width,
                physical.image_width,
            ),
            "image_height": (
                governed.image_height,
                physical.image_height,
            ),
            "annotation_relative_path": (
                annotation_path,
                physical.annotation_relative_path,
            ),
            "annotation_sha256": (
                annotation_sha256,
                physical.annotation_sha256,
            ),
        }

        mismatches = {
            field: (expected, actual)
            for field, (expected, actual) in checks.items()
            if expected != actual
        }

        if mismatches:
            raise ValueError(
                f"Physical record mismatch for "
                f"{governed.image_relative_path}: {mismatches}"
            )