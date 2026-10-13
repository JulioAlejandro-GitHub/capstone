"""Inherit opaque patient keys; source-specific identity rules stay in adapters."""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping


class SameSplitConflict(ValueError):
    """Fail closed before persistence, or reject divergent existing content."""


def inherit_patient_assignments(
    patient_keys: Mapping[str, str], reference: Iterable[tuple[str, str]],
) -> dict[str, str]:
    if len(set(patient_keys.values())) != len(patient_keys):
        raise SameSplitConflict("STOP: canonical collision")
    splits: dict[str, set[str]] = defaultdict(set)
    for key, split in reference:
        if split not in {"train", "val", "test"}:
            raise SameSplitConflict("STOP: invalid reference split")
        splits[key].add(split)
    if any(len(values) != 1 for values in splits.values()):
        raise SameSplitConflict("STOP: ambiguous Cell assignment")
    missing = set(patient_keys.values()) - splits.keys()
    if missing:
        raise SameSplitConflict(f"STOP: NO_ASSIGNMENT: {sorted(missing)}")
    return {patient: next(iter(splits[key])) for patient, key in sorted(patient_keys.items())}


def check_audited_distribution(assignments: Mapping[str, str], polygon: set[str]) -> None:
    """S1.2 acceptance gates, never used to choose or rebalance assignments."""
    if len(assignments) != 193 or Counter(assignments.values()) != {"train": 154, "val": 19, "test": 20}:
        raise SameSplitConflict("STOP: protected Full Smear distribution mismatch")
    if not polygon <= assignments.keys() or Counter(assignments[p] for p in polygon) != {"train": 28, "val": 2, "test": 3}:
        raise SameSplitConflict("STOP: protected Polygon distribution mismatch")
