"""Explicit E6 evidence comparison. This module never fits or predicts."""

import re
from collections import defaultdict
from copy import deepcopy

from ..assessment import lineage
from ..assessment.contracts import identity as rebuild_identity
from ..assessment.contracts import threshold
from ..assessment.service import verify
from ..campaigns.contracts import digest
from ..campaigns.repository import identifier
from ..execution.repository import ExecutionRepository
from .protocol import configuration_key, matrix, require
from .statistics import (
    cluster_interval,
    curves,
    metrics,
    paired_contrasts,
    seed_summary,
    threshold_selection,
)


def read_evaluation(repository, evaluation_id, explanation_ids=None):
    """All DB transactions read-only, including E1 inspection; no audit-writing wrapper."""
    a = repository.attempt(identifier(evaluation_id))
    require(a["state"] == "verified", "EVALUATION_NOT_VERIFIED")
    value = repository.identity(a["identity_id"])
    require(value["kind"] == "evaluate", "EVALUATE_REQUIRED")
    binding, dataset, calibration = lineage.resolve(
        repository,
        value["model"]["training_run_id"],
        value["model"]["model_version_id"],
    )
    require(
        binding == value["model"] and dataset == value["dataset"],
        "TRAIN_LINEAGE_CONFLICT",
    )
    samples = lineage.dataset_samples(
        repository, dataset, value["split"], inspection=True
    )
    require(
        sorted(samples, key=lambda s: s["sample_id"]) == value["samples"],
        "SEALED_POPULATION_CONFLICT",
    )
    require(
        threshold(value["decision"]["requested"], value["protocol"], calibration)
        == value["decision"],
        "THRESHOLD_PROVENANCE_CONFLICT",
    )
    reconstructed = rebuild_identity(
        binding,
        dataset,
        samples,
        split=value["split"],
        purpose=value["purpose"],
        protocol=value["protocol"],
        decision=value["decision"],
        code=value["code"],
        seed=value["seed"],
        batch_size=value["batch_size"],
    )
    require(reconstructed == value, "ASSESSMENT_IDENTITY_CONFLICT")
    proof = verify(repository, a, value)
    session = None
    if binding["source"]["kind"] == "e5_selected_record":
        session = ExecutionRepository(repository.scope).session(
            binding["training_run_id"]
        )
    explanations = []
    if explanation_ids is None:
        explanation_ids = repository.associated_explanations(evaluation_id)
    require(
        len(set(explanation_ids)) == len(explanation_ids),
        "AMBIGUOUS_EXPLANATION_REFERENCE",
    )
    for eid in sorted(explanation_ids):
        ea = repository.attempt(identifier(eid))
        ev = repository.identity(ea["identity_id"])
        require(
            ea["state"] == "verified"
            and ev["kind"] == "explain"
            and ev["evaluation"]
            == {
                "attempt_id": identifier(evaluation_id),
                "identity_hash": digest(value),
            },
            "EXPLAIN_PARENT_CONFLICT",
        )
        require(
            all(
                ev[k] == value[k]
                for k in (
                    "model",
                    "dataset",
                    "samples",
                    "split",
                    "purpose",
                    "protocol",
                    "decision",
                )
            ),
            "EXPLAIN_LINEAGE_CONFLICT",
        )
        explanations.append(
            {
                "attempt_id": identifier(eid),
                "identity_hash": digest(ev),
                "proof": verify(repository, ea, ev),
                "artifacts": repository.artifacts(eid),
            }
        )
    return {
        "evaluation_id": identifier(evaluation_id),
        "identity": value,
        "proof": proof,
        "rows": repository.results(evaluation_id),
        "configuration": session["configuration"] if session else None,
        "training_environment": session["environment"] if session else None,
        "explanations": explanations,
    }


def safe_reason(exc):
    # Only contract codes are surfaced, never arbitrary exception/driver text.
    value = str(exc)
    return (
        value
        if re.fullmatch(r"[A-Z][A-Z0-9_]{2,100}", value)
        else "EVIDENCE_UNVERIFIED"
    )


def classify(evidence, protocol, dataset, split):
    value = evidence["identity"]
    rows = evidence["rows"]
    config = evidence["configuration"]
    require(value["split"] == split, "SPLIT_CONFLICT")
    require(value["dataset"] == dataset, "DATASET_SNAPSHOT_CONFLICT")
    require(
        value["decision"]["source"].get("sha256")
        and value["decision"]["calibrator"] is None
        and value["decision"]["score_domain"] == "raw",
        "THRESHOLD_PROVENANCE_REQUIRED",
    )
    reasons = []
    if split == "val":
        reasons.append("SHARED_VAL_SELECTION_OPTIMISM")
    else:
        reasons.append("HISTORICAL_TEST_DESCRIPTIVE_NO_SELECTION")
    config_hash = configuration_key(config) if config else None
    seed = config["resolved"]["execution"]["seed"] if config else None
    arch = config["model_id"] if config else None
    if not config:
        reasons.append("TRAIN_CONFIGURATION_UNAVAILABLE")
    if config_hash not in protocol["configurations"]:
        reasons.append("CONFIGURATION_OUTSIDE_FROZEN_MATRIX")
    if seed not in protocol["seeds"]:
        reasons.append("TRAIN_SEED_OUTSIDE_MATRIX")
    if not evidence["training_environment"]:
        reasons.append("TRAIN_ENVIRONMENT_UNAVAILABLE")
    if seed is not None and value["seed"] != seed:
        reasons.append("INFERENCE_SEED_DIFFERS_FROM_TRAIN")
    compatible_protocol = (
        value["protocol"].get("scientific_protocol_hash") == digest(protocol)
        and value["protocol"].get("version") == protocol["version"]
        and value["protocol"].get("threshold_rule") == protocol["threshold"]["rule"]
        and value["protocol"].get("calibration") == "none_raw_probability"
    )
    if not compatible_protocol:
        reasons.append("HISTORICAL_PROTOCOL_DIFFERENT")
    proposal = threshold_selection(rows, split=split) if split == "val" else None
    if proposal is not None and proposal["threshold"] != value["decision"]["effective"]:
        reasons.append("EVALUATED_THRESHOLD_DIFFERS_FROM_VAL_RULE")
    if proposal is not None and proposal["threshold"] is None:
        reasons.append("THRESHOLD_NOT_ESTIMABLE")
    same_rule = compatible_protocol and (
        proposal is None or proposal["threshold"] == value["decision"]["effective"]
    )
    method_compatible = (
        config_hash in protocol["configurations"]
        and seed in protocol["seeds"]
        and same_rule
        and bool(evidence["training_environment"])
        and value["seed"] == seed
    )
    m = metrics(rows)
    return {
        "evaluation_id": evidence["evaluation_id"],
        "architecture": arch,
        "configuration_hash": config_hash,
        "configuration": config,
        "seed": seed,
        "optimizer": config["resolved"]["optimizer"]["name"] if config else None,
        "condition": "original" if config_hash in protocol["configurations"] else None,
        "status": "exploratory"
        if split == "val" or not method_compatible
        else "comparable",
        "method_compatible": method_compatible,
        "limitations": reasons,
        "dataset_hash": digest(dataset),
        "sample_hash": digest(value["samples"]),
        "environment_hash": digest(
            {
                "train": evidence["training_environment"],
                "inference": value["code"],
                "batch_size": value["batch_size"],
            }
        )
        if evidence["training_environment"]
        else None,
        "decision_rule": protocol["threshold"]["rule"]
        if same_rule
        else digest(value["decision"]),
        "metrics": m,
        "objective_point_estimate_met": m["sensitivity"] is not None
        and m["sensitivity"] > 0.98,
        "threshold_proposal_val_only": proposal,
        "uncertainty": cluster_interval(rows, protocol["uncertainty"]),
        "curves": curves(rows),
        "baseline_always_parasitized": metrics(
            [{**r, "predicted": 1, "raw_score": 1.0} for r in rows]
        ),
        "lineage": {
            "identity": value,
            "identity_hash": digest(value),
            "prediction_reference": {
                "table": "assessment_results",
                "attempt_id": evidence["evaluation_id"],
                "proof": evidence["proof"],
            },
            "explanations": evidence["explanations"],
        },
        "rows": rows,
    }


def select_candidate(items, protocol, split):
    if split != "val":
        return {"candidate": None, "reason": "TEST_SELECTION_FORBIDDEN"}
    eligible = [r for r in items if r["method_compatible"]]
    expected = {(h, s) for h in protocol["configurations"] for s in protocol["seeds"]}
    if {(r["configuration_hash"], r["seed"]) for r in eligible} != expected:
        return {"candidate": None, "reason": "COMPLETE_ORIGINAL_MATRIX_REQUIRED"}
    if (
        len({r["sample_hash"] for r in eligible}) != 1
        or len({r["environment_hash"] for r in eligible}) != 1
    ):
        return {"candidate": None, "reason": "POPULATION_OR_ENVIRONMENT_CONFLICT"}
    groups = defaultdict(list)
    for r in eligible:
        groups[r["configuration_hash"]].append(r)
    if any(len(rs) != len(protocol["seeds"]) for rs in groups.values()):
        return {"candidate": None, "reason": "AMBIGUOUS_REPETITION"}
    ranked = []
    for key, rs in groups.items():
        if any(
            r["metrics"][n] is None
            for r in rs
            for n in ("sensitivity", "specificity", "f2")
        ):
            return {"candidate": None, "reason": "SELECTION_METRICS_UNDEFINED"}
        success = all(r["metrics"]["sensitivity"] > 0.98 for r in rs)
        ranked.append(
            (
                key,
                success,
                min(r["metrics"]["sensitivity"] for r in rs),
                sum(r["metrics"]["specificity"] for r in rs) / len(rs),
                sum(r["metrics"]["f2"] for r in rs) / len(rs),
            )
        )
    feasible = [r for r in ranked if r[1]]
    chosen = (
        min(feasible, key=lambda r: (-r[3], -r[4], r[0]))
        if feasible
        else min(ranked, key=lambda r: (-r[2], -r[3], -r[4], r[0]))
    )
    representative = next(
        r
        for r in groups[chosen[0]]
        if r["seed"] == protocol["selection"]["representative_seed"]
    )
    return {
        "candidate": {
            "configuration_hash": chosen[0],
            "evaluation_id": representative["evaluation_id"],
            "representative_seed": representative["seed"],
            "model": representative["lineage"]["identity"]["model"],
            "decision": representative["lineage"]["identity"]["decision"],
            "e6_protocol": representative["lineage"]["identity"]["protocol"],
        },
        "objective_met_all_seeds": bool(feasible),
        "reason": "EXPLORATORY_VAL_CANDIDATE"
        if feasible
        else "OBJECTIVE_NOT_REACHED_EXPLORATORY_CANDIDATE",
        "production_selection": "manual_unchanged",
        "test_permission": "separate_exact_E6_final_lock_required",
    }


def compare(protocol, dataset, split, references, reader, *, provenance, campaign=None):
    require(split in ("val", "test"), "COMPARISON_SPLIT_REQUIRED")
    references = [
        {
            "evaluation_id": identifier(r["evaluation_id"]),
            **(
                {"explanation_ids": sorted(identifier(e) for e in r["explanation_ids"])}
                if "explanation_ids" in r
                else {}
            ),
        }
        for r in references
    ]
    ids = [r["evaluation_id"] for r in references]
    require(len(set(ids)) == len(ids), "EXPLICIT_UNIQUE_EVALUATIONS_REQUIRED")
    if campaign:
        require(
            campaign["dataset"] == dataset
            and campaign["protocol"]["version"]
            == protocol["version"] + ":" + digest(protocol),
            "CAMPAIGN_PROTOCOL_DATASET_CONFLICT",
        )
        require(
            set(campaign["configuration_hashes"]) == set(protocol["configurations"]),
            "CAMPAIGN_MATRIX_CONFLICT",
        )
    items = []
    excluded = []
    for ref in sorted(references, key=lambda r: r["evaluation_id"]):
        try:
            e = reader(ref["evaluation_id"], ref.get("explanation_ids"))
            require(e["evaluation_id"] == ref["evaluation_id"], "REFERENCE_CONFLICT")
            if campaign:
                matches = [
                    a
                    for a in campaign["attempts"]
                    if a["training_run_id"] == e["identity"]["model"]["training_run_id"]
                ]
                require(
                    len(matches) == 1 and matches[0]["state"] == "verified",
                    "CAMPAIGN_TRAIN_REFERENCE_CONFLICT",
                )
                prior = [
                    a
                    for a in campaign["attempts"]
                    if a["member_id"] == matches[0]["member_id"]
                    and a["state"] == "verified"
                    and a["ordinal"] < matches[0]["ordinal"]
                ]
                require(not prior, "FIRST_VERIFIED_ATTEMPT_REQUIRED")
            items.append(classify(e, protocol, dataset, split))
        except Exception as exc:  # noqa: BLE001 -- report missing evidence without driver data
            excluded.append(
                {
                    "evaluation_id": ref["evaluation_id"],
                    "status": "excluded",
                    "reason": safe_reason(exc),
                }
            )
    # Ambiguity is never resolved by order, timestamp or the best observed score.
    groups = defaultdict(list)
    for r in items:
        groups[(r["configuration_hash"], r["seed"], r["condition"])].append(r)
    duplicate_ids = {
        r["evaluation_id"]
        for rs in groups.values()
        if len(rs) > 1
        for r in rs
        if r["configuration_hash"] is not None
    }
    excluded += [
        {
            "evaluation_id": i,
            "status": "excluded",
            "reason": "AMBIGUOUS_REPETITION_SELECT_ONE_EXPLICITLY",
        }
        for i in sorted(duplicate_ids)
    ]
    items = [r for r in items if r["evaluation_id"] not in duplicate_ids]
    summaries = []
    groups = defaultdict(list)
    for r in items:
        if r["method_compatible"]:
            groups[
                (r["configuration_hash"], r["sample_hash"], r["environment_hash"])
            ].append(r)
    for (config, pop, env), rs in sorted(groups.items()):
        summaries.append(
            {
                "configuration_hash": config,
                "sample_hash": pop,
                "environment_hash": env,
                "seeds": sorted(r["seed"] for r in rs),
                "missing_seeds": sorted(
                    set(protocol["seeds"]) - {r["seed"] for r in rs}
                ),
                "metrics": seed_summary(rs),
            }
        )
    planned = matrix(protocol, dataset)
    for row in planned:
        if campaign and row["condition"] == "original":
            members = [
                m
                for m in campaign["members"]
                if m["configuration_hash"] == row["configuration_hash"]
                and m["seed"] == row["seed"]
            ]
            require(len(members) == 1, "CAMPAIGN_MEMBER_MATRIX_CONFLICT")
            row["train_state"] = members[0]["state"]
            row["train_exclusion_reason"] = members[0]["exclusion_reason"]
            row["member_id"] = members[0]["id"]
            row["train_attempts"] = [
                a for a in campaign["attempts"] if a["member_id"] == members[0]["id"]
            ]
        match = [
            r
            for r in items
            if r["method_compatible"]
            and r["configuration_hash"] == row["configuration_hash"]
            and r["seed"] == row["seed"]
            and r["condition"] == row["condition"]
        ]
        if match:
            row.update(
                state="evaluated", reason=None, evaluation_id=match[0]["evaluation_id"]
            )
    report = {
        "schema": "scientific_comparison_e7_v1",
        "protocol": deepcopy(protocol),
        "protocol_hash": digest(protocol),
        "dataset": deepcopy(dataset),
        "split": split,
        "references": sorted(deepcopy(references), key=lambda r: r["evaluation_id"]),
        "provenance": provenance,
        "campaign": campaign,
        "state": "results" if items else "preparation_missing_evidence",
        "items": items,
        "exclusions": excluded,
        "matrix": planned,
        "seed_summaries": summaries,
        "paired_contrasts": paired_contrasts(
            [r for r in items if r["method_compatible"]], protocol
        ),
        "selection": select_candidate(items, protocol, split),
        "test_exposure": {
            "selected_test_evaluations": ids if split == "test" else [],
            "prior_history": "unknown_not_accredited_as_unexposed",
        },
        "limitations": [
            "VAL reuse is exploratory; no clinical validation",
            "No seed pooling; CIs describe patient sampling conditional on a trained model",
            "No operational inference performed by this command",
        ],
    }
    # Raw predictions are already immutable in E6; preserve exact reference/hash, not a second ledger.
    for item in report["items"]:
        item.pop("rows")
    return report
