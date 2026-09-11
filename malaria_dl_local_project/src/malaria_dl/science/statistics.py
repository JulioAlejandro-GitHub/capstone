"""Descriptive binary metrics; patient sampling and seed variability stay separate."""

from itertools import combinations

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)

from .protocol import require

METRICS = (
    "sensitivity",
    "specificity",
    "precision",
    "f1",
    "f2",
    "balanced_accuracy",
    "roc_auc",
    "average_precision",
)


def validate_rows(rows):
    require(bool(rows), "PREDICTIONS_REQUIRED")
    require(len({r["sample_id"] for r in rows}) == len(rows), "DUPLICATE_SAMPLE")
    require(
        all(
            type(r["label"]) is int
            and r["label"] in (0, 1)
            and type(r["raw_score"]) in (int, float)
            and np.isfinite(r["raw_score"])
            and 0 <= r["raw_score"] <= 1
            and type(r["predicted"]) is int
            and r["predicted"] in (0, 1)
            for r in rows
        ),
        "PREDICTION_INVALID",
    )


def metrics(rows):
    validate_rows(rows)
    y = np.array([r["label"] for r in rows])
    pred = np.array([r["predicted"] for r in rows])
    score = np.array([r["raw_score"] for r in rows])
    tp = int(np.sum((y == 1) & (pred == 1)))
    tn = int(np.sum((y == 0) & (pred == 0)))
    fp = int(np.sum((y == 0) & (pred == 1)))
    fn = int(np.sum((y == 1) & (pred == 0)))
    missing = {}

    def ratio(name, n, d, reason):
        if not d:
            missing[name] = reason
            return None
        return float(n / d)

    sensitivity = ratio("sensitivity", tp, tp + fn, "NO_POSITIVES")
    specificity = ratio("specificity", tn, tn + fp, "NO_NEGATIVES")
    result = {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "confusion": [[tn, fp], [fn, tp]],
        "support": {"uninfected": tn + fp, "parasitized": tp + fn},
        "prevalence": float(np.mean(y)),
        "sensitivity": sensitivity,
        "specificity": specificity,
        "precision": ratio("precision", tp, tp + fp, "NO_PREDICTED_POSITIVES"),
        "f1": ratio("f1", 2 * tp, 2 * tp + fp + fn, "NO_TRUE_OR_PREDICTED_POSITIVES"),
        "f2": ratio(
            "f2", 5 * tp, 5 * tp + 4 * fn + fp, "NO_TRUE_OR_PREDICTED_POSITIVES"
        ),
    }
    if sensitivity is None or specificity is None:
        result.update(balanced_accuracy=None, roc_auc=None, average_precision=None)
        missing.update(
            {
                name: "BOTH_CLASSES_REQUIRED"
                for name in ("balanced_accuracy", "roc_auc", "average_precision")
            }
        )
    else:
        result.update(
            balanced_accuracy=(sensitivity + specificity) / 2,
            roc_auc=float(roc_auc_score(y, score)),
            average_precision=float(average_precision_score(y, score)),
        )
    result["undefined"] = missing
    return result


def curves(rows):
    validate_rows(rows)
    if len({r["label"] for r in rows}) != 2:
        return {
            "roc": None,
            "precision_recall": None,
            "reason": "BOTH_CLASSES_REQUIRED",
        }
    y = [r["label"] for r in rows]
    s = [r["raw_score"] for r in rows]
    fpr, tpr, t = roc_curve(y, s)
    precision, recall, pt = precision_recall_curve(y, s)
    return {
        "roc": {
            "fpr": fpr.tolist(),
            "tpr": tpr.tolist(),
            "thresholds": [float(v) if np.isfinite(v) else None for v in t],
        },
        "precision_recall": {
            "precision": precision.tolist(),
            "recall": recall.tolist(),
            "thresholds": pt.tolist(),
        },
        "pr_auc_definition": "average_precision_non_interpolated",
    }


def threshold_selection(rows, *, split):
    require(split == "val", "THRESHOLD_SELECTION_VAL_ONLY")
    validate_rows(rows)
    if len({r["label"] for r in rows}) != 2:
        return {
            "threshold": None,
            "objective_met": False,
            "reason": "BOTH_CLASSES_REQUIRED",
        }
    # Compute only counts for the threshold grid, avoiding O(n^2) scans and AUC calls.
    ordered = sorted(rows, key=lambda r: r["raw_score"], reverse=True)
    candidates = sorted({0.0, 1.0, *(r["raw_score"] for r in rows)}, reverse=True)
    positives = sum(r["label"] for r in rows)
    negatives = len(rows) - positives
    tp = fp = i = 0
    choices = []
    for t in candidates:
        while i < len(ordered) and ordered[i]["raw_score"] >= t:
            tp += ordered[i]["label"]
            fp += 1 - ordered[i]["label"]
            i += 1
        fn = positives - tp
        choices.append(
            {
                "threshold": t,
                "sensitivity": tp / positives,
                "specificity": 1 - fp / negatives,
                "f2": 5 * tp / (5 * tp + 4 * fn + fp) if 5 * tp + 4 * fn + fp else None,
            }
        )
    feasible = [c for c in choices if c["sensitivity"] > 0.98]
    key = lambda c: (
        c["specificity"],
        c["f2"] if c["f2"] is not None else -1,
        c["threshold"],
    )
    best = (
        max(feasible, key=key)
        if feasible
        else max(choices, key=lambda c: (c["sensitivity"], *key(c)))
    )
    return {
        **best,
        "objective_met": bool(feasible),
        "reason": None if feasible else "OBJECTIVE_NOT_REACHED",
    }


def seed_summary(items):
    """No pooling predictions. Require distinct seeds and expose missing repetitions."""
    require(len({i["seed"] for i in items}) == len(items), "AMBIGUOUS_SEED_REPETITION")
    out = {}
    for name in METRICS:
        values = [i["metrics"][name] for i in items if i["metrics"][name] is not None]
        out[name] = {
            "n": len(values),
            "mean": float(np.mean(values)) if values else None,
            "sd": float(np.std(values, ddof=1)) if len(values) > 1 else None,
            "sd_reason": None if len(values) > 1 else "AT_LEAST_TWO_SEEDS_REQUIRED",
        }
    return out


def cluster_interval(rows, specification, paired=None):
    """Pointwise percentile CI, whole patients with multiplicity, never seed pooling."""
    validate_rows(rows)
    rows = sorted(rows, key=lambda r: r["sample_id"])
    if paired is not None:
        validate_rows(paired)
        paired = sorted(paired, key=lambda r: r["sample_id"])
        require(
            [(r["sample_id"], r.get("patient_id"), r["label"]) for r in rows]
            == [(r["sample_id"], r.get("patient_id"), r["label"]) for r in paired],
            "PAIRED_POPULATION_CONFLICT",
        )
    base = {
        "method": specification["method"],
        "confidence": specification["confidence"],
        "replicates": specification["replicates"],
        "seed": specification["seed"],
        "paired_difference": "left_minus_right" if paired is not None else None,
    }
    if any(not r.get("patient_id") for r in rows):
        return {**base, "intervals": None, "reason": "PATIENT_GROUPING_UNAVAILABLE"}
    groups = {}
    for i, r in enumerate(rows):
        groups.setdefault(r["patient_id"], []).append(i)
    patients = sorted(groups)
    base["patients"] = len(patients)
    if len(patients) < specification["minimum_patients"]:
        return {**base, "intervals": None, "reason": "INSUFFICIENT_PATIENT_CLUSTERS"}
    names = specification["paired_metrics"] if paired is not None else METRICS
    values = {n: [] for n in names}
    rng = np.random.default_rng(specification["seed"])
    for _ in range(specification["replicates"]):
        indices = [
            i
            for patient in rng.choice(patients, len(patients), replace=True)
            for i in groups[patient]
        ]
        # A repeated patient is a repeated cluster, not an accidental duplicate sample.
        a = metrics([{**rows[i], "sample_id": str(j)} for j, i in enumerate(indices)])
        b = (
            metrics([{**paired[i], "sample_id": str(j)} for j, i in enumerate(indices)])
            if paired is not None
            else None
        )
        for n in names:
            if a[n] is not None and (b is None or b[n] is not None):
                values[n].append(a[n] - (b[n] if b else 0))
    alpha = (1 - specification["confidence"]) / 2
    intervals = {}
    for n, v in values.items():
        valid = (
            len(v)
            >= specification["replicates"] * specification["minimum_valid_fraction"]
        )
        intervals[n] = {
            "low": float(np.quantile(v, alpha)) if valid else None,
            "high": float(np.quantile(v, 1 - alpha)) if valid else None,
            "valid_replicates": len(v),
            "reason": None if valid else "INSUFFICIENT_VALID_REPLICATES",
        }
    return {**base, "intervals": intervals, "reason": None}


def paired_contrasts(items, protocol):
    output = []
    for left, right in combinations(items, 2):
        if left["architecture"] == right["architecture"]:
            continue
        if any(
            left[k] != right[k]
            for k in (
                "optimizer",
                "condition",
                "seed",
                "dataset_hash",
                "sample_hash",
                "decision_rule",
                "environment_hash",
            )
        ):
            continue
        if (left["architecture"], right["architecture"]) not in [
            tuple(x) for x in protocol["contrasts"]
        ]:
            left, right = right, left
        a, b = left["metrics"], right["metrics"]
        output.append(
            {
                "left": left["evaluation_id"],
                "right": right["evaluation_id"],
                "seed": left["seed"],
                "difference": {
                    n: a[n] - b[n] if a[n] is not None and b[n] is not None else None
                    for n in protocol["uncertainty"]["paired_metrics"]
                },
                "uncertainty": cluster_interval(
                    left["rows"], protocol["uncertainty"], right["rows"]
                ),
            }
        )
    return output
