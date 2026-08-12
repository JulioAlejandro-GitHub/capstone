"""Composition statistics for an optimized patient-level candidate."""

from __future__ import annotations

from statistics import fmean, median
from typing import Mapping
from uuid import UUID

from .objective import SPLITS
from .patient_profiles import PatientClassProfile, PatientProfile


def candidate_composition(
    profiles: tuple[PatientProfile, ...], assignments: Mapping[UUID, str]
) -> dict:
    result = {}
    for split in SPLITS:
        members = [item for item in profiles if assignments[item.clinical_identity_id] == split]
        sizes = [item.total_records for item in members]
        both_ratios = [
            item.parasitized_ratio for item in members
            if item.patient_class_profile == PatientClassProfile.BOTH_CLASSES
        ]
        parasitized = sum(item.parasitized_records for item in members)
        uninfected = sum(item.uninfected_records for item in members)
        records = parasitized + uninfected
        result[split] = {
            "patients": len(members), "patient_ratio": len(members) / len(profiles),
            "records": records,
            "record_ratio": records / sum(item.total_records for item in profiles),
            "parasitized": parasitized, "uninfected": uninfected,
            "parasitized_ratio": parasitized / records,
            "both_classes_patients": sum(item.patient_class_profile == PatientClassProfile.BOTH_CLASSES for item in members),
            "uninfected_only_patients": sum(item.patient_class_profile == PatientClassProfile.UNINFECTED_ONLY for item in members),
            "parasitized_only_patients": sum(item.patient_class_profile == PatientClassProfile.PARASITIZED_ONLY for item in members),
            "patient_size": {
                "min": min(sizes), "max": max(sizes), "mean": fmean(sizes),
                "median": median(sizes),
            },
            "both_classes_patient_parasitized_ratio": {
                "min": min(both_ratios), "max": max(both_ratios),
                "mean": fmean(both_ratios), "median": median(both_ratios),
            },
        }
    return result
