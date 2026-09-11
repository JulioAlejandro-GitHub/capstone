"""E8 probability ensembles over exact E6 predictions; no model loading or TEST."""

import math
from copy import deepcopy
from uuid import UUID, uuid5

from ..assessment.contracts import verify_rows
from ..campaigns.contracts import digest
from ..campaigns.repository import identifier
from ..data.input_contract import MAPPING, validate_input_contract
from .comparison import classify
from .protocol import configuration_key, load_protocol, matrix, require
from .statistics import cluster_interval, curves, metrics, threshold_selection

VERSION = "probability_ensemble_e8_v1"
TOLERANCE = 1e-12
ARCHITECTURES = ("custom_cnn", "densenet121", "vgg16")
NAMESPACE = UUID("f92e90ca-980a-4a75-b247-5702c8fa8cd3")


def experimental_matrix():
    protocol = load_protocol()
    rows = matrix(protocol)
    for r in rows:
        r["entity_type"] = "individual"
    for strategy in ("uniform", "weighted"):
        for optimizer in ("adam", "adamw", "sgd", "adadelta"):
            for seed in protocol["seeds"]:
                rows.append(
                    {
                        "entity_type": "ensemble",
                        "condition": "three_architectures_" + strategy,
                        "strategy": strategy,
                        "architectures": list(ARCHITECTURES),
                        "optimizer": optimizer,
                        "seed": seed,
                        "state": "planned",
                        "reason": "EXACT_MEMBER_EVALUATIONS_REQUIRED",
                        "member_run_ids": None,
                        "weights": None if strategy == "weighted" else [1 / 3] * 3,
                        "protocol_hash": digest(protocol),
                        "extension": VERSION,
                    }
                )
    return rows


def weights_for(strategy, members):
    require(len(members) >= 2, "AT_LEAST_TWO_MEMBERS_REQUIRED")
    require(strategy in ("uniform", "weighted"), "ENSEMBLE_STRATEGY_INVALID")
    if strategy == "uniform":
        require(
            all("weight" not in m for m in members), "UNIFORM_WEIGHTS_MUST_BE_IMPLICIT"
        )
        return [1 / len(members)] * len(members)
    values = [m.get("weight") for m in members]
    require(
        all(type(w) in (int, float) and math.isfinite(w) and w >= 0 for w in values),
        "ENSEMBLE_WEIGHTS_INVALID",
    )
    require(
        abs(math.fsum(values) - 1) <= TOLERANCE and sum(w > 0 for w in values) >= 2,
        "ENSEMBLE_WEIGHTS_SUM_OR_SUPPORT_INVALID",
    )
    return values


def align(evidences):
    require(len(evidences) == 3, "THREE_ARCHITECTURES_REQUIRED")
    protocol = load_protocol()
    indexed = []
    sample_contract = None
    dataset = None
    architectures = []
    hashes = []
    seeds = []
    optimizers = []
    environments = []
    for e in evidences:
        v = e["identity"]
        c = e["configuration"]
        rs = e["rows"]
        require(
            v["kind"] == "evaluate"
            and v["split"] == "val"
            and v["purpose"] == "development",
            "ENSEMBLE_VAL_ONLY",
        )
        require(c is not None, "ENSEMBLE_TRAIN_CONFIGURATION_REQUIRED")
        contract = validate_input_contract(v["model"]["input_contract"])
        require(
            contract["label_mapping"] == MAPPING
            and contract == c["resolved"]["input_contract"],
            "ENSEMBLE_INPUT_MAPPING_CONFLICT",
        )
        require(
            v["decision"]["calibrator"] is None
            and v["decision"]["score_domain"] == "raw"
            and all(r.get("calibrated_score") is None for r in rs),
            "ENSEMBLE_CALIBRATOR_UNSUPPORTED",
        )
        require(verify_rows(v, rs) == e["proof"], "ENSEMBLE_PREDICTION_PROOF_CONFLICT")
        require(
            configuration_key(c) in protocol["configurations"],
            "ENSEMBLE_CONFIGURATION_OUTSIDE_E7",
        )
        samples = sorted(v["samples"], key=lambda s: s["sample_id"])
        if sample_contract is None:
            sample_contract = samples
            dataset = v["dataset"]
        require(samples == sample_contract, "ENSEMBLE_SAMPLE_PATIENT_LABEL_CONFLICT")
        require(v["dataset"] == dataset, "ENSEMBLE_DATASET_CONFLICT")
        architectures.append(c["model_id"])
        hashes.append(v["model"]["sha256"])
        seeds.append(c["resolved"]["execution"]["seed"])
        optimizers.append(c["resolved"]["optimizer"]["name"])
        assessed = classify(e, protocol, dataset, "val")
        require(assessed["method_compatible"], "ENSEMBLE_MEMBER_NOT_E7_COMPARABLE")
        environments.append(assessed["environment_hash"])
        indexed.append({r["sample_id"]: r for r in rs})
    require(
        sorted(architectures) == list(ARCHITECTURES),
        "ENSEMBLE_ARCHITECTURE_GROUP_INVALID",
    )
    require(len(set(hashes)) == 3, "DUPLICATE_CHECKPOINT")
    require(
        len(set(seeds)) == 1 and seeds[0] in protocol["seeds"],
        "ENSEMBLE_SEED_GROUP_CONFLICT",
    )
    require(
        len(set(optimizers)) == 1 and len(set(environments)) == 1,
        "ENSEMBLE_BUDGET_ENVIRONMENT_CONFLICT",
    )
    return sorted(indexed[0]), indexed


def combine(evidences, weights, threshold_value):
    ids, indexed = align(evidences)
    require(
        type(threshold_value) in (float, int)
        and math.isfinite(threshold_value)
        and 0 <= threshold_value <= 1,
        "ENSEMBLE_THRESHOLD_INVALID",
    )
    require(len(weights) == len(evidences), "ENSEMBLE_WEIGHT_MEMBER_CONFLICT")
    weights_for("weighted", [{"weight": w} for w in weights])
    output = []
    for sid in ids:
        contributions = [
            {
                "evaluation_id": e["evaluation_id"],
                "training_run_id": e["identity"]["model"]["training_run_id"],
                "checkpoint_sha256": e["identity"]["model"]["sha256"],
                "raw_score": index[sid]["raw_score"],
                "weight": w,
                "weighted_score": w * index[sid]["raw_score"],
            }
            for e, index, w in zip(evidences, indexed, weights)
        ]
        score = math.fsum(x["weighted_score"] for x in contributions)
        # A within-tolerance weight sum still must yield a genuine probability.
        require(
            -TOLERANCE <= score <= 1 + TOLERANCE,
            "ENSEMBLE_COMBINED_PROBABILITY_OUT_OF_RANGE",
        )
        combination_sum = score
        score = min(1.0, max(0.0, score))
        r = indexed[0][sid]
        output.append(
            {
                "sample_id": sid,
                "patient_id": r["patient_id"],
                "label": r["label"],
                "raw_score": score,
                "calibrated_score": None,
                "threshold": threshold_value,
                "predicted": int(score >= threshold_value),
                "contributions": contributions,
                "combination_sum": combination_sum,
            }
        )
    return output


def prepare(request, reader, *, code):
    request = deepcopy(request)
    request.setdefault("strategy", "uniform")
    if request["strategy"] == "uniform":
        request.setdefault("weight_provenance", {"kind": "uniform_no_fit"})
    require(
        set(request) == {"ensemble_id", "strategy", "members", "weight_provenance"},
        "ENSEMBLE_REQUEST_FIELDS_INVALID",
    )
    identifier(request["ensemble_id"])
    members = request["members"]
    require(
        isinstance(members, list) and len(members) == 3, "THREE_ARCHITECTURES_REQUIRED"
    )
    require(
        all(
            set(m) <= {"evaluation_id", "weight"} and "evaluation_id" in m
            for m in members
        ),
        "ENSEMBLE_MEMBER_FIELDS_INVALID",
    )
    require(
        len({identifier(m["evaluation_id"]) for m in members}) == 3,
        "DUPLICATE_MEMBER_REFERENCE",
    )
    ws = weights_for(request["strategy"], members)
    provenance = request["weight_provenance"]
    if request["strategy"] == "weighted":
        require(
            isinstance(provenance, dict)
            and set(provenance) == {"kind", "reference"}
            and provenance["kind"] == "predeclared"
            and isinstance(provenance["reference"], str)
            and bool(provenance["reference"].strip()),
            "PREDECLARED_WEIGHT_PROVENANCE_REQUIRED",
        )
    else:
        require(provenance == {"kind": "uniform_no_fit"}, "UNIFORM_PROVENANCE_REQUIRED")
    # A missing or failed member aborts the entire configuration; no subset fallback.
    loaded = [(reader(identifier(m["evaluation_id"])), w) for m, w in zip(members, ws)]
    require(
        all(
            e["evaluation_id"] == identifier(m["evaluation_id"])
            for (e, _w), m in zip(loaded, members)
        ),
        "ENSEMBLE_EXPLICIT_REFERENCE_CONFLICT",
    )
    loaded.sort(
        key=lambda pair: (
            pair[0]["configuration"]["model_id"] if pair[0]["configuration"] else ""
        )
    )
    es = [x[0] for x in loaded]
    ws = [x[1] for x in loaded]
    rows = combine(es, ws, 0.5)
    decision = threshold_selection(rows, split="val")
    require(decision["threshold"] is not None, "ENSEMBLE_THRESHOLD_NOT_ESTIMABLE")
    body = {
        "schema": VERSION,
        "extension_hash": digest(extension_contract()),
        "ensemble_id": identifier(request["ensemble_id"]),
        "strategy": request["strategy"],
        "weight_tolerance": TOLERANCE,
        "weight_provenance": deepcopy(provenance),
        "members": [
            {
                "architecture": e["configuration"]["model_id"],
                "weight": w,
                "model": deepcopy(e["identity"]["model"]),
                "configuration_hash": configuration_key(e["configuration"]),
                "calibrator": None,
            }
            for e, w in loaded
        ],
        "dataset": deepcopy(es[0]["identity"]["dataset"]),
        "split": "val",
        "repetition": {
            "kind": "between_architectures",
            "seed": es[0]["configuration"]["resolved"]["execution"]["seed"],
            "optimizer": es[0]["configuration"]["resolved"]["optimizer"]["name"],
        },
        "validation_references": [
            {
                "evaluation_id": e["evaluation_id"],
                "identity_hash": digest(e["identity"]),
                "prediction_hash": e["proof"]["sha256"],
            }
            for e in es
        ],
        "sample_hash": digest(es[0]["identity"]["samples"]),
        "post_calibrator": None,
        "transform_order": [
            "raw_member",
            "member_calibrator_none",
            "weighted_sum",
            "post_calibrator_none",
            "threshold",
        ],
        "decision": {
            "effective": decision["threshold"],
            "source": {
                "kind": "e7_val_threshold",
                "rule": load_protocol()["threshold"]["rule"],
                "score_hash": digest(
                    [
                        {
                            k: r[k]
                            for k in ("sample_id", "patient_id", "label", "raw_score")
                        }
                        for r in rows
                    ]
                ),
                "selection": decision,
            },
        },
        "protocol": {
            "version": load_protocol()["version"],
            "sha256": digest(load_protocol()),
        },
        "code": deepcopy(code),
        "limitations": [
            "shared_VAL_member_and_threshold_selection_optimism",
            "mixture_not_accredited_as_calibrated",
            "TEST_requires_future_explicit_frozen_authorization",
        ],
    }
    result = {"configuration": body, "revision": digest(body)}
    validate_configuration(result)
    return result


def validate_configuration(value):
    require(
        set(value) == {"configuration", "revision"},
        "ENSEMBLE_CONFIGURATION_FIELDS_INVALID",
    )
    b = value["configuration"]
    require(
        set(b)
        == {
            "schema",
            "extension_hash",
            "ensemble_id",
            "strategy",
            "weight_tolerance",
            "weight_provenance",
            "members",
            "dataset",
            "split",
            "repetition",
            "validation_references",
            "sample_hash",
            "post_calibrator",
            "transform_order",
            "decision",
            "protocol",
            "code",
            "limitations",
        },
        "ENSEMBLE_CONFIGURATION_FIELDS_INVALID",
    )
    require(value["revision"] == digest(b), "ENSEMBLE_REVISION_CONFLICT")
    require(
        b["schema"] == VERSION
        and b["split"] == "val"
        and b["protocol"]
        == {"version": load_protocol()["version"], "sha256": digest(load_protocol())},
        "ENSEMBLE_PROTOCOL_CONFLICT",
    )
    require(
        b["extension_hash"] == digest(extension_contract()),
        "ENSEMBLE_EXTENSION_CONFLICT",
    )
    require(
        b["transform_order"]
        == [
            "raw_member",
            "member_calibrator_none",
            "weighted_sum",
            "post_calibrator_none",
            "threshold",
        ],
        "ENSEMBLE_TRANSFORM_ORDER_CONFLICT",
    )
    require(
        isinstance(b["code"], dict) and bool(b["code"]),
        "ENSEMBLE_CODE_EVIDENCE_REQUIRED",
    )
    identifier(b["ensemble_id"])
    require(b["weight_tolerance"] == TOLERANCE, "ENSEMBLE_TOLERANCE_CONFLICT")
    refs = b["validation_references"]
    require(
        len(refs) == 3 and len({identifier(r["evaluation_id"]) for r in refs}) == 3,
        "ENSEMBLE_VALIDATION_REFERENCES_INVALID",
    )
    ms = b["members"]
    require(
        [m["architecture"] for m in ms] == list(ARCHITECTURES),
        "ENSEMBLE_MEMBER_ORDER_CONFLICT",
    )
    require(len({m["model"]["sha256"] for m in ms}) == 3, "DUPLICATE_CHECKPOINT")
    for m in ms:
        require(
            set(m)
            == {"architecture", "weight", "model", "configuration_hash", "calibrator"},
            "ENSEMBLE_MEMBER_FIELDS_INVALID",
        )
        for key in ("training_run_id", "model_version_id", "checkpoint_artifact_id"):
            identifier(m["model"][key])
        require(
            validate_input_contract(m["model"]["input_contract"])["architecture"]
            == m["architecture"],
            "ENSEMBLE_INPUT_ARCHITECTURE_CONFLICT",
        )
        require(
            m["configuration_hash"] in load_protocol()["configurations"],
            "ENSEMBLE_CONFIGURATION_OUTSIDE_E7",
        )
        require(m["calibrator"] is None, "ENSEMBLE_CALIBRATOR_UNSUPPORTED")
    require(b["post_calibrator"] is None, "ENSEMBLE_CALIBRATOR_UNSUPPORTED")
    weights_for("weighted", ms)
    require(
        all(
            load_protocol()["configurations"][m["configuration_hash"]]["model_id"]
            == m["architecture"]
            and load_protocol()["configurations"][m["configuration_hash"]]["resolved"][
                "input_contract"
            ]
            == m["model"]["input_contract"]
            for m in ms
        ),
        "ENSEMBLE_MEMBER_CONFIGURATION_CONFLICT",
    )
    expected_provenance = {"kind": "uniform_no_fit"}
    if b["strategy"] == "uniform":
        require(
            b["weight_provenance"] == expected_provenance, "UNIFORM_PROVENANCE_REQUIRED"
        )
    else:
        prov = b["weight_provenance"]
        require(
            isinstance(prov, dict)
            and set(prov) == {"kind", "reference"}
            and prov["kind"] == "predeclared"
            and isinstance(prov["reference"], str)
            and bool(prov["reference"].strip()),
            "PREDECLARED_WEIGHT_PROVENANCE_REQUIRED",
        )
    require(b["strategy"] in ("uniform", "weighted"), "ENSEMBLE_STRATEGY_INVALID")
    if b["strategy"] == "uniform":
        require(all(m["weight"] == 1 / 3 for m in ms), "UNIFORM_WEIGHT_CONFLICT")
    require(
        type(b["decision"]["effective"]) in (int, float)
        and 0 <= b["decision"]["effective"] <= 1
        and b["decision"]["source"]["kind"] == "e7_val_threshold",
        "ENSEMBLE_THRESHOLD_PROVENANCE_CONFLICT",
    )
    require(
        b["decision"]["source"]["selection"]["threshold"] == b["decision"]["effective"],
        "ENSEMBLE_THRESHOLD_PROVENANCE_CONFLICT",
    )
    require(
        b["repetition"]["kind"] == "between_architectures"
        and b["repetition"]["seed"] in load_protocol()["seeds"],
        "ENSEMBLE_SEED_GROUP_CONFLICT",
    )
    return value


def evaluate(configuration, reader, *, configuration_id):
    from .cli import provenance

    validate_configuration(configuration)
    b = configuration["configuration"]
    es = [reader(r["evaluation_id"]) for r in b["validation_references"]]
    # Rebuild from exact evidence to reject altered config, decision, provenance or sources.
    req = {
        "ensemble_id": b["ensemble_id"],
        "strategy": b["strategy"],
        "weight_provenance": b["weight_provenance"],
        "members": [
            {
                "evaluation_id": r["evaluation_id"],
                **({"weight": m["weight"]} if b["strategy"] == "weighted" else {}),
            }
            for r, m in zip(b["validation_references"], b["members"])
        ],
    }
    rebuilt = prepare(
        req,
        lambda eid: next(e for e in es if e["evaluation_id"] == eid),
        code=b["code"],
    )
    require(rebuilt == configuration, "ENSEMBLE_CONFIGURATION_EVIDENCE_CONFLICT")
    rows = combine(es, [m["weight"] for m in b["members"]], b["decision"]["effective"])
    protocol = load_protocol()
    mm = metrics(rows)
    comparisons = []
    for e in es:
        own = metrics(e["rows"])
        by_id = {r["sample_id"]: r for r in e["rows"]}
        comparisons.append(
            {
                "evaluation_id": e["evaluation_id"],
                "architecture": e["configuration"]["model_id"],
                "metrics": own,
                "difference": {
                    n: mm[n] - own[n]
                    if mm[n] is not None and own[n] is not None
                    else None
                    for n in protocol["uncertainty"]["paired_metrics"]
                },
                "uncertainty": cluster_interval(
                    rows, protocol["uncertainty"], e["rows"]
                ),
                "corrected_sample_ids": [
                    r["sample_id"]
                    for r in rows
                    if r["predicted"] == r["label"]
                    and by_id[r["sample_id"]]["predicted"] != r["label"]
                ],
                "introduced_sample_ids": [
                    r["sample_id"]
                    for r in rows
                    if r["predicted"] != r["label"]
                    and by_id[r["sample_id"]]["predicted"] == r["label"]
                ],
                "explanations": e["explanations"],
            }
        )
    member_rows = [{r["sample_id"]: r for r in e["rows"]} for e in es]
    disagreement = []
    for r in rows:
        preds = [rmap[r["sample_id"]]["predicted"] for rmap in member_rows]
        scores = [x["raw_score"] for x in r["contributions"]]
        disagreement.append(
            {
                "sample_id": r["sample_id"],
                "member_decisions_disagree": len(set(preds)) > 1,
                "score_range": max(scores) - min(scores),
            }
        )
    reference = min(
        comparisons,
        key=lambda c: (
            -(c["metrics"]["sensitivity"] > 0.98),
            -c["metrics"]["specificity"],
            -c["metrics"]["f2"],
            c["architecture"],
        ),
    )
    return {
        "schema": "ensemble_evaluation_e8_v1",
        "execution_code": provenance(),
        "configuration_id": identifier(configuration_id),
        "configuration": configuration,
        "split": "val",
        "state": "exploratory",
        "rows": rows,
        "prediction_hash": digest(rows),
        "metrics": mm,
        "curves": curves(rows),
        "uncertainty": cluster_interval(rows, protocol["uncertainty"]),
        "baseline": metrics([{**r, "predicted": 1, "raw_score": 1.0} for r in rows]),
        "member_comparisons": comparisons,
        "disagreement": disagreement,
        "individual_reference": {
            "evaluation_id": reference["evaluation_id"],
            "selection_partition": "val",
            "rule": "sensitivity > .98 then specificity then F2 then architecture",
        },
        "objective_point_estimate_met": mm["sensitivity"] is not None
        and mm["sensitivity"] > 0.98,
        "latency": {"combination_seconds": None, "full_inference_seconds": None},
        "limitations": b["limitations"]
        + [
            "disagreement_is_not_calibrated_clinical_uncertainty",
            "member_EXPLAIN_not_a_spatial_ensemble_explanation",
        ],
    }


def validate_evaluation(value):
    require(
        value["schema"] == "ensemble_evaluation_e8_v1"
        and value["split"] == "val"
        and value["state"] == "exploratory",
        "ENSEMBLE_EVALUATION_INVALID",
    )
    validate_configuration(value["configuration"])
    require(
        isinstance(value["execution_code"], dict)
        and value["execution_code"].get("source_sha256"),
        "ENSEMBLE_EXECUTION_CODE_REQUIRED",
    )
    identifier(value["configuration_id"])
    require(
        digest(value["rows"]) == value["prediction_hash"]
        and metrics(value["rows"]) == value["metrics"],
        "ENSEMBLE_RESULT_PROOF_CONFLICT",
    )
    b = value["configuration"]["configuration"]
    refs = b["validation_references"]
    for r in value["rows"]:
        for contribution, member, ref in zip(r["contributions"], b["members"], refs):
            require(
                contribution["weight"] == member["weight"]
                and contribution["training_run_id"]
                == member["model"]["training_run_id"]
                and contribution["checkpoint_sha256"] == member["model"]["sha256"],
                "ENSEMBLE_CONTRIBUTION_MEMBER_CONFLICT",
            )
            require(
                type(contribution["raw_score"]) in (int, float)
                and math.isfinite(contribution["raw_score"])
                and 0 <= contribution["raw_score"] <= 1
                and contribution["weighted_score"]
                == contribution["weight"] * contribution["raw_score"],
                "ENSEMBLE_CONTRIBUTION_SCORE_CONFLICT",
            )
        require(
            -TOLERANCE <= r["combination_sum"] <= 1 + TOLERANCE
            and r["calibrated_score"] is None,
            "ENSEMBLE_RESULT_PROBABILITY_CONFLICT",
        )
        require(
            r["threshold"] == b["decision"]["effective"]
            and r["predicted"] == int(r["raw_score"] >= r["threshold"]),
            "ENSEMBLE_RESULT_DECISION_CONFLICT",
        )
        require(
            len(r["contributions"]) == 3
            and [x["evaluation_id"] for x in r["contributions"]]
            == [x["evaluation_id"] for x in refs],
            "ENSEMBLE_CONTRIBUTION_REFERENCE_CONFLICT",
        )
        require(
            math.fsum(x["weighted_score"] for x in r["contributions"])
            == r["combination_sum"]
            and r["raw_score"] == min(1.0, max(0.0, r["combination_sum"])),
            "ENSEMBLE_CONTRIBUTION_SCORE_CONFLICT",
        )
    return value


def configuration_event_id(value):
    # Shared E7 audit namespace, schema keeps ensemble identities distinct.
    from .repository import NAMESPACE as audit_namespace

    return str(uuid5(audit_namespace, digest(value)))


def extension_contract():
    return {
        "version": VERSION,
        "parent_protocol": {
            "version": load_protocol()["version"],
            "sha256": digest(load_protocol()),
        },
        "default_strategy": "uniform",
        "strategies": ["uniform", "weighted"],
        "architectures": list(ARCHITECTURES),
        "weights": {
            "tolerance": TOLERANCE,
            "minimum_positive": 2,
            "normalization": "forbidden",
            "weighted_provenance": "predeclared",
            "search": "not_implemented",
        },
        "probability_roundoff": "retain combination_sum; clip only out-of-range sum within weight tolerance; do not normalize weights",
        "calibration": "none; reject unknown or double calibration",
        "threshold": load_protocol()["threshold"],
        "permitted_splits": ["val"],
        "test": "disabled_pending_future_frozen_authorization",
        "repetition": "one checkpoint per architecture, same TRAIN seed and optimizer; no cross-seed ensembles",
        "matrix_rows": 96,
        "optional_pairs": "not_enabled",
        "superiority": "unproven",
    }
