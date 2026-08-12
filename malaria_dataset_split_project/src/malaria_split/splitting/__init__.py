"""Patient-level split design primitives."""

from .candidate import CandidateEvaluation, evaluate_candidate
from .patient_group_stratified_v1 import (
    DEFAULT_SEED,
    build_seeded_greedy_baseline,
    randomized_patient_sequence,
)
from .patient_profiles import PatientProfile, load_patient_profiles
from .optimizer import OptimizationResult, optimize_patient_split

__all__ = [
    "CandidateEvaluation",
    "DEFAULT_SEED",
    "PatientProfile",
    "OptimizationResult",
    "build_seeded_greedy_baseline",
    "evaluate_candidate",
    "load_patient_profiles",
    "optimize_patient_split",
    "randomized_patient_sequence",
]
