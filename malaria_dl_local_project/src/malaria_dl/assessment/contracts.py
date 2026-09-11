"""Pure, versioned inference identity and reconstructible binary metrics."""

import math
from copy import deepcopy

from ..campaigns.contracts import CampaignError, canonical, digest
from ..campaigns.repository import identifier
from ..data.input_contract import validate_input_contract


class AssessmentError(CampaignError):
    pass


def require(condition, code):
    if not condition:
        raise AssessmentError(code)


def probability(value):
    require(
        type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1,
        "SCORE_OR_THRESHOLD_INVALID",
    )
    return float(value)


def threshold(requested, protocol, calibration=None):
    if requested == "clinical":
        require(
            isinstance(calibration, dict)
            and calibration.get("result", {}).get("enabled") is not False,
            "CLINICAL_THRESHOLD_EVIDENCE_REQUIRED",
        )
        result = calibration["result"]
        require(
            result.get("schema_version") == 1
            and result.get("calibration_split") == "val"
            and result.get("positive_class_index") == 1
            and result.get("threshold_source") == "validation_calibration"
            and result.get("threshold_selected") == result.get("threshold_used"),
            "CLINICAL_THRESHOLD_EVIDENCE_REQUIRED",
        )
        value = probability(result.get("threshold_selected"))
        source = {"version": "e5_val_threshold_v1", "sha256": digest(calibration)}
    else:
        try:
            value = probability(float(requested))
        except (ValueError, TypeError):
            raise AssessmentError("THRESHOLD_EXPLICIT_REQUIRED") from None
        require(
            value in protocol.get("allowed_numeric_thresholds", []),
            "THRESHOLD_NOT_ALLOWED_BY_PROTOCOL",
        )
        source = {"version": "protocol_numeric_v1", "sha256": digest(protocol)}
    return {
        "requested": str(requested),
        "effective": value,
        "source": source,
        "calibrator": None,
        "score_domain": "raw",
        "positive_class": 1,
        "comparison": ">=",
    }


def identity(
    binding,
    dataset,
    samples,
    *,
    split,
    purpose,
    protocol,
    decision,
    code,
    seed,
    batch_size,
    explanation=None,
    evaluation=None,
):
    require(
        split in ("train", "val", "test") and purpose in ("development", "final"),
        "PROTOCOL_REQUIRED",
    )
    require(
        isinstance(protocol, dict)
        and protocol.get("version")
        and split in protocol.get("splits", [])
        and purpose in protocol.get("purposes", []),
        "PROTOCOL_CONFLICT",
    )
    require(
        (purpose == "final" and split == "test")
        or (purpose == "development" and split != "test"),
        "TEST_FINAL_LOCK_REQUIRED",
    )
    require(
        type(seed) is int and type(batch_size) is int and batch_size > 0,
        "INFERENCE_OPTIONS_INVALID",
    )
    validate_input_contract(binding["input_contract"])
    ordered = sorted(deepcopy(samples), key=lambda s: s["sample_id"])
    require(
        ordered and len({s["sample_id"] for s in ordered}) == len(ordered),
        "SAMPLE_SET_INVALID",
    )
    for s in ordered:
        identifier(s["sample_id"])
        identifier(s["patient_id"])
        require(
            type(s["label"]) is int
            and s["label"] in (0, 1)
            and s["split"] == split
            and len(s["sha256"]) == 64,
            "SAMPLE_IDENTITY_INVALID",
        )
    result = {
        "schema": "assessment_identity_v1",
        "kind": "explain" if explanation else "evaluate",
        "model": deepcopy(binding),
        "dataset": deepcopy(dataset),
        "samples": ordered,
        "split": split,
        "purpose": purpose,
        "protocol": deepcopy(protocol),
        "decision": deepcopy(decision),
        "code": code,
        "seed": seed,
        "batch_size": batch_size,
        "metrics_definition": "binary_counts_rates_v1",
        "explanation": explanation,
        "evaluation": evaluation,
    }
    # File location remains evidence, not a reason to reuse a different binary/sample population.
    canonical(result)  # rejects non-finite JSON
    return result


def prediction(sample, raw_score, decision):
    score = probability(raw_score)
    require(
        decision["calibrator"] is None and decision["score_domain"] == "raw",
        "CALIBRATOR_UNSUPPORTED",
    )
    return {
        "sample_id": sample["sample_id"],
        "patient_id": sample["patient_id"],
        "label": sample["label"],
        "raw_score": score,
        "calibrated_score": None,
        "threshold": decision["effective"],
        "predicted": int(score >= decision["effective"]),
    }


def metrics(rows):
    counts = {"tn": 0, "fp": 0, "fn": 0, "tp": 0}
    for row in rows:
        counts[("tn", "fp", "fn", "tp")[2 * row["label"] + row["predicted"]]] += 1
    tn, fp, fn, tp = (counts[k] for k in ("tn", "fp", "fn", "tp"))

    def ratio(a, b):
        return a / b if b else None

    return {
        "definition": "binary_counts_rates_v1",
        "count": len(rows),
        **counts,
        "confusion_matrix": [[tn, fp], [fn, tp]],
        "accuracy": ratio(tp + tn, len(rows)),
        "precision": ratio(tp, tp + fp),
        "recall": ratio(tp, tp + fn),
        "specificity": ratio(tn, tn + fp),
        "f2": ratio(5 * tp, 5 * tp + 4 * fn + fp),
    }


def verify_rows(value, rows):
    expected = {s["sample_id"]: s for s in value["samples"]}
    require(
        len(rows) == len(expected) and {r["sample_id"] for r in rows} == set(expected),
        "PREDICTIONS_INCOMPLETE",
    )
    for r in rows:
        require(
            r
            == prediction(expected[r["sample_id"]], r["raw_score"], value["decision"]),
            "PREDICTION_CONFLICT",
        )
    ordered = sorted(rows, key=lambda r: r["sample_id"])
    return {"count": len(rows), "sha256": digest(ordered), "metrics": metrics(ordered)}
