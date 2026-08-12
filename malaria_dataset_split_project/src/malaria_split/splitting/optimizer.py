"""Bounded deterministic multi-start optimization for SPLIT 3A.2 dry-runs."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Mapping
from uuid import UUID

from .candidate import CandidateEvaluation, candidate_sort_key, evaluate_candidate
from .objective import SPLITS
from .patient_group_stratified_v1 import build_seeded_greedy_baseline
from .patient_group_stratified_v1 import randomized_patient_sequence
from .patient_profiles import PatientProfile


INITIAL_CANDIDATES = 16
LOCALLY_OPTIMIZED_STARTS = 4
LOCAL_SEARCH_ITERATION_LIMIT = 30
NEIGHBOR_PROPOSALS_PER_ITERATION = 20


@dataclass(frozen=True, slots=True)
class OptimizedCandidate:
    candidate_id: str
    assignments: Mapping[UUID, str]
    evaluation: CandidateEvaluation


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    seed: int
    winner: OptimizedCandidate
    baseline: OptimizedCandidate
    initial_candidates: int
    candidates_evaluated: int
    local_search_iterations: int


def _derived_seed(seed: int, start: int) -> int:
    return seed * 1_000_003 + start * 10_007


def _valid_candidate(
    profiles: tuple[PatientProfile, ...], assignments: Mapping[UUID, str]
) -> OptimizedCandidate | None:
    evaluation = evaluate_candidate(profiles, assignments)
    if not evaluation.valid:
        return None
    return OptimizedCandidate(
        candidate_id=f"candidate-{evaluation.canonical_assignment_digest[:16]}",
        assignments=dict(assignments),
        evaluation=evaluation,
    )


def _proposal(
    assignments: Mapping[UUID, str], identities: tuple[UUID, ...], rng: random.Random,
    operation: int,
) -> dict[UUID, str]:
    candidate = dict(assignments)
    if operation % 4 == 0:
        identity = identities[rng.randrange(len(identities))]
        alternatives = tuple(split for split in SPLITS if split != candidate[identity])
        candidate[identity] = alternatives[rng.randrange(len(alternatives))]
    else:
        first = identities[rng.randrange(len(identities))]
        other_splits = tuple(split for split in SPLITS if split != candidate[first])
        target_split = other_splits[rng.randrange(len(other_splits))]
        partners = tuple(identity for identity in identities if candidate[identity] == target_split)
        if partners:
            second = partners[rng.randrange(len(partners))]
            candidate[first], candidate[second] = candidate[second], candidate[first]
    return candidate


def _target_count_candidate(
    profiles: tuple[PatientProfile, ...], seed: int
) -> dict[UUID, str]:
    """Seeded initial point near soft patient targets; counts remain non-hard."""
    sequence = randomized_patient_sequence(profiles, seed)
    train_count = round(len(sequence) * 0.80)
    val_count = round(len(sequence) * 0.10)
    assignments = {}
    for index, profile in enumerate(sequence):
        split = "train" if index < train_count else "val" if index < train_count + val_count else "test"
        assignments[profile.clinical_identity_id] = split
    return assignments


def _local_search(
    profiles: tuple[PatientProfile, ...], start: OptimizedCandidate, seed: int,
) -> tuple[OptimizedCandidate, int, int]:
    current = start
    identities = tuple(sorted(current.assignments, key=str))
    rng = random.Random(seed)
    evaluated = 0
    iterations = 0
    for iteration in range(LOCAL_SEARCH_ITERATION_LIMIT):
        iterations += 1
        neighbors = []
        for operation in range(NEIGHBOR_PROPOSALS_PER_ITERATION):
            proposal = _proposal(current.assignments, identities, rng, operation)
            evaluated += 1
            candidate = _valid_candidate(profiles, proposal)
            if candidate is not None:
                neighbors.append(candidate)
        if not neighbors:
            break
        best_neighbor = min(neighbors, key=lambda item: candidate_sort_key(item.evaluation))
        if candidate_sort_key(best_neighbor.evaluation) < candidate_sort_key(current.evaluation):
            current = best_neighbor
        else:
            break
    return current, evaluated, iterations


def optimize_patient_split(
    profiles: tuple[PatientProfile, ...], seed: int = 42
) -> OptimizationResult:
    """Rebuild and optimize a winner; no persistence or global random state."""
    baseline_assignments = build_seeded_greedy_baseline(profiles, seed)
    baseline = _valid_candidate(profiles, baseline_assignments)
    if baseline is None:
        raise ValueError("The approved baseline violates hard constraints")
    initial = [baseline]
    evaluated = 1
    for start in range(1, INITIAL_CANDIDATES):
        assignments = _target_count_candidate(profiles, _derived_seed(seed, start))
        evaluated += 1
        candidate = _valid_candidate(profiles, assignments)
        if candidate is not None:
            initial.append(candidate)
    ranked = sorted(initial, key=lambda item: candidate_sort_key(item.evaluation))
    optimized = list(initial)
    total_iterations = 0
    for rank, start in enumerate(ranked[:LOCALLY_OPTIMIZED_STARTS]):
        improved, neighbor_count, iterations = _local_search(
            profiles, start, _derived_seed(seed, 10_000 + rank)
        )
        evaluated += neighbor_count
        total_iterations += iterations
        optimized.append(improved)
    winner = min(optimized, key=lambda item: candidate_sort_key(item.evaluation))
    return OptimizationResult(
        seed=seed, winner=winner, baseline=baseline,
        initial_candidates=INITIAL_CANDIDATES,
        candidates_evaluated=evaluated,
        local_search_iterations=total_iterations,
    )
