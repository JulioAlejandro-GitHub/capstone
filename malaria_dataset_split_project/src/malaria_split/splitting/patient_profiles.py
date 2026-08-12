"""Canonical Patient Profiles constructed exclusively from PostgreSQL."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Connection, text


class PatientClassProfile(StrEnum):
    BOTH_CLASSES = "BOTH_CLASSES"
    UNINFECTED_ONLY = "UNINFECTED_ONLY"
    PARASITIZED_ONLY = "PARASITIZED_ONLY"


@dataclass(frozen=True, slots=True)
class PatientProfile:
    clinical_identity_id: UUID
    source_identifier: str
    total_records: int
    parasitized_records: int
    uninfected_records: int
    parasitized_ratio: float
    uninfected_ratio: float
    patient_class_profile: PatientClassProfile
    source_file_sha256: tuple[str, ...]


def _class_profile(parasitized: int, uninfected: int) -> PatientClassProfile:
    if parasitized and uninfected:
        return PatientClassProfile.BOTH_CLASSES
    if uninfected:
        return PatientClassProfile.UNINFECTED_ONLY
    return PatientClassProfile.PARASITIZED_ONLY


def load_patient_profiles(
    connection: Connection, dataset_version_id: UUID
) -> tuple[PatientProfile, ...]:
    """Load one canonical profile per PATIENT in the version's PRIMARY population."""
    rows = connection.execute(
        text(
            """
            SELECT ci.id clinical_identity_id, ci.source_identifier,
                   count(*) total_records,
                   count(*) FILTER (WHERE dsr.class_name='parasitized') parasitized_records,
                   count(*) FILTER (WHERE dsr.class_name='uninfected') uninfected_records,
                   array_agg(dsr.source_file_sha256 ORDER BY dsr.source_file_sha256) hashes
            FROM dataset_versions dv
            JOIN dataset_version_sources dvs ON dvs.dataset_version_id=dv.id
              AND dvs.role='PRIMARY'
            JOIN clinical_identities ci ON ci.dataset_id=dvs.dataset_id
              AND ci.identity_type='PATIENT' AND ci.status='VERIFIED'
            JOIN dataset_source_records dsr ON dsr.dataset_id=dvs.dataset_id
              AND dsr.clinical_identity_id=ci.id AND dsr.identity_status='VERIFIED'
            WHERE dv.id=:version_id
            GROUP BY ci.id,ci.source_identifier
            ORDER BY ci.source_identifier ASC,ci.id ASC
            """
        ),
        {"version_id": dataset_version_id},
    ).mappings()
    profiles = []
    for row in rows:
        total = row["total_records"]
        parasitized = row["parasitized_records"]
        uninfected = row["uninfected_records"]
        profiles.append(
            PatientProfile(
                clinical_identity_id=row["clinical_identity_id"],
                source_identifier=row["source_identifier"],
                total_records=total,
                parasitized_records=parasitized,
                uninfected_records=uninfected,
                parasitized_ratio=parasitized / total,
                uninfected_ratio=uninfected / total,
                patient_class_profile=_class_profile(parasitized, uninfected),
                source_file_sha256=tuple(row["hashes"]),
            )
        )
    return tuple(profiles)
