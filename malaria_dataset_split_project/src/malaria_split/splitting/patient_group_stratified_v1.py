"""Controlled patient randomization and non-official baseline contract."""

from __future__ import annotations

import random
from typing import Mapping
from uuid import UUID

from .objective import SPLITS, TARGET_RATIOS
from .patient_profiles import PatientProfile


DEFAULT_SEED = 42


def canonical_patient_order(profiles: tuple[PatientProfile, ...]) -> tuple[PatientProfile, ...]:
    return tuple(sorted(profiles, key=lambda item: (item.source_identifier, str(item.clinical_identity_id))))


def randomized_patient_sequence(
    profiles: tuple[PatientProfile, ...], seed: int = DEFAULT_SEED
) -> tuple[PatientProfile, ...]:
    ordered = list(canonical_patient_order(profiles))
    random.Random(seed).shuffle(ordered)
    return tuple(ordered)


def build_seeded_greedy_baseline(
    profiles: tuple[PatientProfile, ...], seed: int = DEFAULT_SEED
) -> Mapping[UUID, str]:
    """Baseline only: seeded patients greedily approach record and patient targets."""
    sequence = randomized_patient_sequence(profiles, seed)
    total_records = sum(item.total_records for item in sequence)
    total_patients = len(sequence)
    records = {split: 0 for split in SPLITS}
    patients = {split: 0 for split in SPLITS}
    assignments = {}
    for profile in sequence:
        def projected_key(split: str) -> tuple[float, float, int]:
            projected_records = {**records, split: records[split] + profile.total_records}
            projected_patients = {**patients, split: patients[split] + 1}
            record_error = max(
                abs(projected_records[item] / total_records - TARGET_RATIOS[item])
                for item in SPLITS
            )
            patient_error = max(
                abs(projected_patients[item] / total_patients - TARGET_RATIOS[item])
                for item in SPLITS
            )
            return record_error, patient_error, SPLITS.index(split)
        split = min(SPLITS, key=projected_key)
        assignments[profile.clinical_identity_id] = split
        records[split] += profile.total_records
        patients[split] += 1
    _repair_class_presence(assignments, sequence)
    return assignments


def _repair_class_presence(
    assignments: dict[UUID, str], sequence: tuple[PatientProfile, ...]
) -> None:
    """Deterministically move whole patients so every partition has both classes."""
    for target in SPLITS:
        for class_field in ("parasitized_records", "uninfected_records"):
            if any(
                assignments[profile.clinical_identity_id] == target
                and getattr(profile, class_field) > 0
                for profile in sequence
            ):
                continue
            donors = []
            for index, profile in enumerate(sequence):
                source = assignments[profile.clinical_identity_id]
                if source == target or getattr(profile, class_field) == 0:
                    continue
                source_class_patients = sum(
                    assignments[item.clinical_identity_id] == source
                    and getattr(item, class_field) > 0
                    for item in sequence
                )
                if source_class_patients > 1:
                    donors.append((profile.total_records, index, profile))
            if not donors:
                raise ValueError(f"Cannot satisfy class presence for {target}:{class_field}")
            profile = min(donors)[2]
            assignments[profile.clinical_identity_id] = target
