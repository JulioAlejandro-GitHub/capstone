"""Pure candidate representation, hard-constraint gate and evaluator."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from statistics import fmean
from typing import Mapping
from uuid import UUID

from .objective import ObjectiveComponents, SPLITS, TARGET_RATIOS, SplitMetrics
from .patient_profiles import PatientClassProfile, PatientProfile


@dataclass(frozen=True, slots=True)
class CandidateEvaluation:
    valid: bool
    hard_constraint_violations: tuple[str, ...]
    split_metrics: Mapping[str, SplitMetrics]
    objective: ObjectiveComponents
    objective_tuple: tuple[float, ...]
    canonical_assignment_digest: str


def canonical_assignment_digest(assignments: Mapping[UUID, str]) -> str:
    payload = "\n".join(
        f"{identity_id}|{assignments[identity_id]}"
        for identity_id in sorted(assignments, key=str)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def candidate_sort_key(evaluation: CandidateEvaluation) -> tuple:
    return (*evaluation.objective_tuple, evaluation.canonical_assignment_digest)


def _deviation(values: list[float], references: list[float]) -> float:
    return max((abs(value - reference) for value, reference in zip(values, references)), default=0.0)


def evaluate_candidate(
    profiles: tuple[PatientProfile, ...], assignments: Mapping[UUID, str]
) -> CandidateEvaluation:
    profile_by_id = {profile.clinical_identity_id: profile for profile in profiles}
    expected = set(profile_by_id)
    assigned = set(assignments)
    violations = []
    if assigned != expected:
        if expected - assigned:
            violations.append("RECORD_COMPLETENESS_UNASSIGNED_PATIENTS")
        if assigned - expected:
            violations.append("UNKNOWN_PATIENT_ASSIGNMENTS")
    if any(split not in SPLITS for split in assignments.values()):
        violations.append("INVALID_SPLIT_NAME")

    grouped: dict[str, list[PatientProfile]] = {split: [] for split in SPLITS}
    hash_splits: dict[str, set[str]] = defaultdict(set)
    for identity_id, split in assignments.items():
        profile = profile_by_id.get(identity_id)
        if profile is None or split not in grouped:
            continue
        grouped[split].append(profile)
        for digest in profile.source_file_sha256:
            hash_splits[digest].add(split)
    if any(len(splits) > 1 for splits in hash_splits.values()):
        violations.append("DUPLICATE_CROSS_SPLIT_OVERLAP")

    metrics = {}
    for split in SPLITS:
        members = grouped[split]
        parasitized = sum(item.parasitized_records for item in members)
        uninfected = sum(item.uninfected_records for item in members)
        records = parasitized + uninfected
        if not parasitized or not uninfected:
            violations.append(f"CLASS_PRESENCE_{split.upper()}")
        both_ratios = [item.parasitized_ratio for item in members if item.patient_class_profile == PatientClassProfile.BOTH_CLASSES]
        metrics[split] = SplitMetrics(
            patients=len(members), records=records,
            parasitized_records=parasitized, uninfected_records=uninfected,
            both_classes_patients=sum(item.patient_class_profile == PatientClassProfile.BOTH_CLASSES for item in members),
            uninfected_only_patients=sum(item.patient_class_profile == PatientClassProfile.UNINFECTED_ONLY for item in members),
            parasitized_only_patients=sum(item.patient_class_profile == PatientClassProfile.PARASITIZED_ONLY for item in members),
            mean_patient_size=fmean(item.total_records for item in members) if members else 0.0,
            mean_both_classes_parasitized_ratio=fmean(both_ratios) if both_ratios else 0.0,
        )

    total_records = sum(item.total_records for item in profiles) or 1
    total_patients = len(profiles) or 1
    global_parasitized_ratio = sum(item.parasitized_records for item in profiles) / total_records
    global_mean_size = total_records / total_patients
    global_profile_ratios = {
        kind: sum(item.patient_class_profile == kind for item in profiles) / total_patients
        for kind in PatientClassProfile
    }
    global_both = [item.parasitized_ratio for item in profiles if item.patient_class_profile == PatientClassProfile.BOTH_CLASSES]
    global_both_ratio = fmean(global_both) if global_both else 0.0

    profile_deviation = max(
        abs(
            getattr(metrics[split], {
                PatientClassProfile.BOTH_CLASSES: "both_classes_patients",
                PatientClassProfile.UNINFECTED_ONLY: "uninfected_only_patients",
                PatientClassProfile.PARASITIZED_ONLY: "parasitized_only_patients",
            }[kind]) / metrics[split].patients - global_profile_ratios[kind]
        ) if metrics[split].patients else 1.0
        for split in SPLITS for kind in PatientClassProfile
    )
    size_deviation = max(
        abs(metrics[split].mean_patient_size - global_mean_size) / global_mean_size
        for split in SPLITS
    )
    within_patient_deviation = max(
        abs(metrics[split].mean_both_classes_parasitized_ratio - global_both_ratio)
        for split in SPLITS
    )
    representativeness = max(profile_deviation, size_deviation, within_patient_deviation)
    components = ObjectiveComponents(
        patient_profile_deviation=profile_deviation,
        patient_size_deviation=size_deviation,
        within_patient_parasitized_ratio_deviation=within_patient_deviation,
        representativeness_deviation=representativeness,
        class_balance_deviation=max(abs(metrics[split].parasitized_ratio - global_parasitized_ratio) for split in SPLITS),
        record_ratio_deviation=max(abs(metrics[split].records / total_records - TARGET_RATIOS[split]) for split in SPLITS),
        patient_ratio_deviation=max(abs(metrics[split].patients / total_patients - TARGET_RATIOS[split]) for split in SPLITS),
    )
    digest = canonical_assignment_digest(assignments)
    return CandidateEvaluation(
        valid=not violations,
        hard_constraint_violations=tuple(dict.fromkeys(violations)),
        split_metrics=metrics,
        objective=components,
        objective_tuple=components.objective_tuple,
        canonical_assignment_digest=digest,
    )
