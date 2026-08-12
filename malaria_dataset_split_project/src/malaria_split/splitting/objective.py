"""Auditable, normalized objective components and lexicographic priority."""

from __future__ import annotations

from dataclasses import dataclass


SPLITS = ("train", "val", "test")
TARGET_RATIOS = {"train": 0.80, "val": 0.10, "test": 0.10}


@dataclass(frozen=True, slots=True)
class SplitMetrics:
    patients: int
    records: int
    parasitized_records: int
    uninfected_records: int
    both_classes_patients: int
    uninfected_only_patients: int
    parasitized_only_patients: int
    mean_patient_size: float
    mean_both_classes_parasitized_ratio: float

    @property
    def parasitized_ratio(self) -> float:
        return self.parasitized_records / self.records if self.records else 0.0


@dataclass(frozen=True, slots=True)
class ObjectiveComponents:
    patient_profile_deviation: float
    patient_size_deviation: float
    within_patient_parasitized_ratio_deviation: float
    representativeness_deviation: float
    class_balance_deviation: float
    record_ratio_deviation: float
    patient_ratio_deviation: float

    @property
    def objective_tuple(self) -> tuple[float, ...]:
        """Lower is better; digest is the separate final tie-break."""
        return (
            self.representativeness_deviation,
            self.class_balance_deviation,
            self.record_ratio_deviation,
            self.patient_ratio_deviation,
        )
