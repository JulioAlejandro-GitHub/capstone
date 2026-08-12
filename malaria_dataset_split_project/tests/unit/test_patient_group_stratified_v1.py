from unittest import TestCase
from uuid import UUID

from malaria_split.splitting.candidate import (
    candidate_sort_key,
    canonical_assignment_digest,
    evaluate_candidate,
)
from malaria_split.splitting.patient_group_stratified_v1 import (
    build_seeded_greedy_baseline,
    canonical_patient_order,
    randomized_patient_sequence,
)
from malaria_split.splitting.patient_profiles import PatientClassProfile, PatientProfile


def _profile(number, patient, parasitized, uninfected, hashes=()):
    total = parasitized + uninfected
    if parasitized and uninfected:
        kind = PatientClassProfile.BOTH_CLASSES
    elif uninfected:
        kind = PatientClassProfile.UNINFECTED_ONLY
    else:
        kind = PatientClassProfile.PARASITIZED_ONLY
    return PatientProfile(
        clinical_identity_id=UUID(int=number), source_identifier=patient,
        total_records=total, parasitized_records=parasitized,
        uninfected_records=uninfected, parasitized_ratio=parasitized / total,
        uninfected_ratio=uninfected / total, patient_class_profile=kind,
        source_file_sha256=tuple(hashes),
    )


class PatientGroupStratifiedV1Tests(TestCase):
    def setUp(self):
        self.profiles = tuple(
            _profile(index, f"PAT-{index:02d}", 5 + index, 8 - index % 3, (f"{index:064x}",))
            for index in range(1, 13)
        )

    def test_canonical_order_uses_source_identifier_then_uuid(self):
        shuffled = tuple(reversed(self.profiles))
        ordered = canonical_patient_order(shuffled)
        self.assertEqual([p.source_identifier for p in ordered], sorted(p.source_identifier for p in shuffled))

    def test_seeded_randomization_is_local_and_reproducible(self):
        one = randomized_patient_sequence(self.profiles, 42)
        two = randomized_patient_sequence(tuple(reversed(self.profiles)), 42)
        other = randomized_patient_sequence(self.profiles, 43)
        self.assertEqual(one, two)
        self.assertNotEqual(one, other)

    def test_baseline_is_patient_level_complete_and_reproducible(self):
        first = build_seeded_greedy_baseline(self.profiles, 42)
        second = build_seeded_greedy_baseline(tuple(reversed(self.profiles)), 42)
        self.assertEqual(first, second)
        self.assertEqual(set(first), {p.clinical_identity_id for p in self.profiles})
        self.assertEqual(set(first.values()), {"train", "val", "test"})

    def test_evaluator_accepts_complete_candidate_with_class_presence(self):
        assignments = {
            profile.clinical_identity_id: ("train" if index < 8 else "val" if index < 10 else "test")
            for index, profile in enumerate(self.profiles)
        }
        result = evaluate_candidate(self.profiles, assignments)
        self.assertTrue(result.valid)
        self.assertEqual(len(result.objective_tuple), 4)
        self.assertEqual(set(result.split_metrics), {"train", "val", "test"})

    def test_record_completeness_and_class_presence_are_hard(self):
        assignments = {p.clinical_identity_id: "train" for p in self.profiles[:-1]}
        result = evaluate_candidate(self.profiles, assignments)
        self.assertFalse(result.valid)
        self.assertIn("RECORD_COMPLETENESS_UNASSIGNED_PATIENTS", result.hard_constraint_violations)
        self.assertIn("CLASS_PRESENCE_VAL", result.hard_constraint_violations)

    def test_duplicate_hash_cross_split_is_hard(self):
        profiles = (
            _profile(101, "A", 3, 3, ("a" * 64,)),
            _profile(102, "B", 3, 3, ("a" * 64,)),
            _profile(103, "C", 3, 3, ("c" * 64,)),
        )
        result = evaluate_candidate(
            profiles,
            {profiles[0].clinical_identity_id: "train", profiles[1].clinical_identity_id: "val",
             profiles[2].clinical_identity_id: "test"},
        )
        self.assertIn("DUPLICATE_CROSS_SPLIT_OVERLAP", result.hard_constraint_violations)

    def test_digest_is_canonical_and_tie_break_is_digest_ascending(self):
        candidate = {p.clinical_identity_id: "train" for p in self.profiles}
        reversed_candidate = dict(reversed(list(candidate.items())))
        self.assertEqual(canonical_assignment_digest(candidate), canonical_assignment_digest(reversed_candidate))
        a = evaluate_candidate(self.profiles, candidate)
        changed = dict(candidate)
        changed[self.profiles[0].clinical_identity_id] = "val"
        b = evaluate_candidate(self.profiles, changed)
        expected = min((a, b), key=candidate_sort_key)
        self.assertIn(expected, (a, b))

    def test_objective_components_are_normalized_and_auditable(self):
        assignments = {
            p.clinical_identity_id: ("train" if i < 8 else "val" if i < 10 else "test")
            for i, p in enumerate(self.profiles)
        }
        objective = evaluate_candidate(self.profiles, assignments).objective
        for value in objective.objective_tuple:
            self.assertGreaterEqual(value, 0.0)
        self.assertEqual(
            objective.representativeness_deviation,
            max(objective.patient_profile_deviation, objective.patient_size_deviation,
                objective.within_patient_parasitized_ratio_deviation),
        )
