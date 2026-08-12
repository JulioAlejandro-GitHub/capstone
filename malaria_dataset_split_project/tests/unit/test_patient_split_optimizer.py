from unittest import TestCase
from uuid import UUID

from malaria_split.splitting.candidate import candidate_sort_key, evaluate_candidate
from malaria_split.splitting.optimizer import (
    INITIAL_CANDIDATES,
    LOCAL_SEARCH_ITERATION_LIMIT,
    optimize_patient_split,
)
from malaria_split.splitting.patient_group_stratified_v1 import build_seeded_greedy_baseline
from malaria_split.splitting.patient_profiles import PatientClassProfile, PatientProfile


def _profiles():
    rows = []
    for index in range(1, 31):
        parasitized = 5 + index % 7
        uninfected = 7 + index % 5
        total = parasitized + uninfected
        rows.append(PatientProfile(
            clinical_identity_id=UUID(int=index), source_identifier=f"P-{index:03d}",
            total_records=total, parasitized_records=parasitized,
            uninfected_records=uninfected, parasitized_ratio=parasitized / total,
            uninfected_ratio=uninfected / total,
            patient_class_profile=PatientClassProfile.BOTH_CLASSES,
            source_file_sha256=(f"{index:064x}",),
        ))
    return tuple(rows)


class PatientSplitOptimizerTests(TestCase):
    def test_generation_is_bounded_and_winner_valid(self):
        result = optimize_patient_split(_profiles(), 42)
        self.assertEqual(result.initial_candidates, INITIAL_CANDIDATES)
        self.assertLessEqual(result.local_search_iterations, 4 * LOCAL_SEARCH_ITERATION_LIMIT)
        self.assertTrue(result.winner.evaluation.valid)
        self.assertEqual(len(result.winner.assignments), 30)

    def test_same_seed_rebuilds_same_winner_and_objective(self):
        first = optimize_patient_split(_profiles(), 42)
        second = optimize_patient_split(tuple(reversed(_profiles())), 42)
        self.assertEqual(
            first.winner.evaluation.canonical_assignment_digest,
            second.winner.evaluation.canonical_assignment_digest,
        )
        self.assertEqual(first.winner.evaluation.objective_tuple, second.winner.evaluation.objective_tuple)

    def test_winner_is_not_worse_than_approved_baseline(self):
        profiles = _profiles()
        result = optimize_patient_split(profiles, 42)
        baseline = evaluate_candidate(profiles, build_seeded_greedy_baseline(profiles, 42))
        self.assertLessEqual(candidate_sort_key(result.winner.evaluation), candidate_sort_key(baseline))

    def test_different_seed_controls_candidate_generation(self):
        first = optimize_patient_split(_profiles(), 42)
        second = optimize_patient_split(_profiles(), 43)
        self.assertNotEqual(
            first.winner.evaluation.canonical_assignment_digest,
            second.winner.evaluation.canonical_assignment_digest,
        )
