"""Strict scientific projections. No defaults lookup, image I/O or artifact generation."""

import json
from copy import deepcopy
from decimal import Decimal, localcontext

from .core import number, path_get, require, sha, stable_id

RATES = {
    "recall": "recall_parasitized",
    "sensitivity": "sensitivity_parasitized",
    "specificity": "specificity",
    "precision": "precision_parasitized",
    "f1": "f1_parasitized",
    "f2": "f2_parasitized",
    "balanced_accuracy": "balanced_accuracy",
    "accuracy": "accuracy",
    "roc_auc": "roc_auc_parasitized",
    "pr_auc": "pr_auc_parasitized",
}
RESERVED = set(RATES) | set(RATES.values()) | {"tp", "fp", "fn", "tn"}


def configuration(run, binding, evidence):
    cfg = path_get(
        run, ["execution_parameters", "model_configuration_e2", "configuration"]
    )
    raw, original_hash = (
        evidence.get(binding["canonical"]),
        evidence.get(binding["sha256"]),
    )
    require(
        type(raw) is str and sha(raw) == original_hash, "CONFIGURATION_HASH_MISMATCH"
    )
    require(json.loads(raw) == cfg["resolved"], "CONFIGURATION_CANONICAL_MISMATCH")
    r = cfg["resolved"]
    ex = r["execution"]
    model = r["model"]
    opt = r["optimizer"]
    sel = r["selection"]
    result = {
        "run_id": run["id"],
        "architecture": cfg["model_id"],
        "adapter_version": cfg["adapter_version"],
        "optimizer": opt["name"],
        "learning_rate": opt["parameters"]["learning_rate"],
        "fine_tune_learning_rate": opt["fine_tune_learning_rate"],
        "random_seed": ex["seed"],
        "checkpoint_monitor": sel["monitor"],
        "checkpoint_mode": sel["mode"],
        "early_stopping_monitor": sel["early_stopping_monitor"],
        "early_stopping_mode": sel["early_stopping_mode"],
        "normalization": model["preprocessing"],
        "internal_preprocessing": r["input_contract"]["internal"]["mode"],
        "input_height": model["input_shape"][0],
        "input_width": model["input_shape"][1],
        "input_channels": model["input_shape"][2],
        "loss_function": r["recipe"]["loss"],
        "calibration_enabled": ex["calibrate_threshold"],
        "default_threshold": sel["threshold"],
        "clinical_target_recall": ex["target_recall"],
        "configuration_hash": original_hash,
        "canonical_configuration": raw,
        "optimizer_extensions": {
            k: v for k, v in opt["parameters"].items() if k != "learning_rate"
        },
        "extension_configuration": deepcopy(r),
        "provenance_snapshot": deepcopy(cfg),
        "created_at": run["created_at"],
    }
    for k in (
        "batch_size",
        "max_epochs",
        "fine_tune_epochs",
        "early_stopping",
        "early_stopping_patience",
        "early_stopping_min_delta",
        "restore_best_weights",
    ):
        result[k] = ex[k]
    for k in ("dropout", "l2", "weights", "fine_tune_layers"):
        result[k] = model[k]
    require(
        run["run_type"] == "training" and result["random_seed"] == run["random_seed"],
        "CONFIGURATION_TRAIN_SEED_MISMATCH",
    )
    require(
        result["architecture"] in ("custom_cnn", "vgg16", "densenet121")
        and result["optimizer"] in ("adam", "adamw", "sgd", "adadelta"),
        "UNSUPPORTED_CONFIGURATION",
    )
    for k in ("early_stopping", "restore_best_weights", "calibration_enabled"):
        require(type(result[k]) is bool, "BOOLEAN_REQUIRED", k)
    for k in (
        "input_height",
        "input_width",
        "input_channels",
        "batch_size",
        "max_epochs",
        "fine_tune_epochs",
        "random_seed",
        "early_stopping_patience",
        "fine_tune_layers",
    ):
        require(
            type(result[k]) is int and result[k] >= 0,
            "CONFIGURATION_INTEGER_INVALID",
            k,
        )
    require(
        result["input_height"] >= 32
        and result["input_width"] == result["input_height"]
        and result["input_channels"] == 3
        and result["batch_size"] > 0
        and result["max_epochs"] > 0,
        "CONFIGURATION_SHAPE_INVALID",
    )
    for k in ("learning_rate", "fine_tune_learning_rate"):
        require(number(result[k], k) > 0, "CONFIGURATION_RATE_INVALID", k)
    require(
        number(result["clinical_target_recall"], "target") == Decimal(".98")
        and number(result["default_threshold"], "threshold") == Decimal(".5"),
        "CLINICAL_CONFIGURATION_CONFLICT",
    )
    modes = {
        "custom_cnn": ("rescale_0_1", None),
        "vgg16": ("vgg16_imagenet", None),
        "densenet121": ("rescale_0_1", "densenet_imagenet_channel_mean_std"),
    }
    require(
        (result["normalization"], result["internal_preprocessing"])
        == modes[result["architecture"]],
        "PREPROCESSING_CONFLICT",
    )
    return result


def measurement(source, context, identity):
    result = deepcopy(source) if "run_clinical_metric_id" in source else {}
    counts = source.get("confusion_matrix", source)
    if not isinstance(counts, dict):
        counts = source
    for k in ("tn", "fp", "fn", "tp"):
        require(k in counts, "BINARY_COUNTS_REQUIRED", k)
        n = number(counts[k], k, integer=True)
        require(0 <= n <= 2**63 - 1, "BINARY_COUNT_RANGE", k)
        result[k] = int(n)
    tn, fp, fn, tp = (Decimal(result[k]) for k in ("tn", "fp", "fn", "tp"))
    require(tn + fp + fn + tp > 0, "EMPTY_EVALUATION_POPULATION")
    if "n_samples" in source:
        require(
            number(source["n_samples"], "n_samples", True) == tn + fp + fn + tp,
            "SAMPLE_COUNT_MISMATCH",
        )
    ratio = lambda n, d: n / d if d else None
    with localcontext() as ctx:
        ctx.prec = 40
        derived = {
            "recall_parasitized": ratio(tp, tp + fn),
            "sensitivity_parasitized": ratio(tp, tp + fn),
            "specificity": ratio(tn, tn + fp),
            "precision_parasitized": ratio(tp, tp + fp),
            "f1_parasitized": ratio(2 * tp, 2 * tp + fp + fn),
            "f2_parasitized": ratio(5 * tp, 5 * tp + fp + 4 * fn),
            "accuracy": (tn + tp) / (tn + fp + fn + tp),
        }
        derived["balanced_accuracy"] = (
            (derived["recall_parasitized"] + derived["specificity"]) / 2
            if tp + fn and tn + fp
            else None
        )
    supplied = source.get("metrics", source)
    for alias, dest in RATES.items():
        if dest not in derived:
            continue
        for key in {alias, dest} & set(supplied):
            old = supplied[key]
            new = derived[dest]
            if new is None:
                require(
                    old is None or number(old, key) == 0,
                    "UNDEFINED_LEGACY_METRIC_CONFLICT",
                    key,
                )
            elif old is not None:
                require(
                    abs(number(old, key) - new) <= Decimal("1e-12"),
                    "METRIC_COUNTS_CONFLICT",
                    key,
                )
    result.update(derived)
    for short, k in [
        ("roc_auc", "roc_auc_parasitized"),
        ("pr_auc", "pr_auc_parasitized"),
    ]:
        require(short in supplied or k in supplied, "AUC_EVIDENCE_REQUIRED", k)
        value = supplied.get(short, supplied.get(k))
        if short in supplied and k in supplied:
            require(supplied[short] == supplied[k], "AUC_ALIAS_CONFLICT")
        require(value is None or 0 <= number(value, k) <= 1, "AUC_RANGE", k)
        require((tp + fn and tn + fp) or value is None, "SINGLE_CLASS_AUC")
        result[k] = value
    reason = context.get("auc_unavailability_reason")
    null_auc = any(
        result[k] is None for k in ("roc_auc_parasitized", "pr_auc_parasitized")
    )
    require(
        (reason in ("single_class", "scores_unavailable", "not_computed"))
        if null_auc
        else reason is None,
        "AUC_REASON_REQUIRED",
    )
    if reason == "single_class":
        require(not (tp + fn and tn + fp), "AUC_REASON_CONFLICT")
    result.update(
        run_clinical_metric_id=source.get(
            "run_clinical_metric_id", stable_id("measurement", identity)
        ),
        evaluation_id=context["id"],
        run_id=context["run_id"],
        split_name=context["split"],
        threshold_used=context["threshold_used"],
        threshold_source=context["threshold_source"],
        confusion_matrix=[[int(tn), int(fp)], [int(fn), int(tp)]],
        auc_unavailability_reason=reason,
        created_at=source.get("created_at", context["created_at"]),
    )
    for key, expected in [
        ("run_id", context["run_id"]),
        ("split_name", context["split"]),
        ("threshold_used", context["threshold_used"]),
        ("threshold_source", context["threshold_source"]),
    ]:
        if key in source and source[key] is not None:
            require(source[key] == expected, "MEASUREMENT_CONTEXT_CONFLICT", key)
    if "threshold" in source:
        require(
            source["threshold"]
            == {
                "value": context["threshold_used"],
                "source": context["threshold_source"],
            },
            "THRESHOLD_CONFLICT",
        )
    return result


def evaluation(context, key):
    require(isinstance(context, dict), "INCOMPLETE_OR_INCOMPATIBLE_EVIDENCE")
    e = deepcopy(context)
    e.pop("auc_unavailability_reason", None)
    e.setdefault("id", stable_id("evaluation", key))
    e["metric_definition"] = "binary_nullable_v2"
    required = (
        "run_id",
        "training_run_id",
        "dataset_version_id",
        "split",
        "evaluation_role",
        "purpose",
        "subject_kind",
        "protocol_version",
        "protocol_hash",
        "population_hash",
        "input_contract_hash",
        "comparison_contract_hash",
        "protocol_snapshot",
        "source_kind",
        "source_record_key",
        "source_record_phase",
        "threshold_used",
        "threshold_source",
        "created_at",
    )
    require(
        all(e.get(k) is not None for k in required), "EVALUATION_CONTEXT_INCOMPLETE"
    )
    for k in (
        "protocol_hash",
        "population_hash",
        "input_contract_hash",
        "comparison_contract_hash",
    ):
        import re

        require(
            isinstance(e[k], str) and re.fullmatch("[0-9a-f]{64}", e[k]),
            "EVALUATION_HASH_INVALID",
            k,
        )
    scope = (e["split"], e["purpose"], e["evaluation_role"])
    legal = (
        scope == ("external", "complementary", "external_complementary")
        or scope == ("test", "final", "final_test")
        or (
            e["split"] in ("train", "val")
            and e["purpose"] == "development"
            and e["evaluation_role"]
            in (
                "training_validation_final",
                "development",
                "calibration_default",
                "calibration_selected",
            )
        )
    )
    require(legal, "EVALUATION_SCOPE_INVALID")
    if e["evaluation_role"] in (
        "training_validation_final",
        "calibration_default",
        "calibration_selected",
    ):
        require(e["split"] == "val", "VAL_ROLE_REQUIRED")
    require(e["subject_kind"] in ("single", "ensemble"), "SUBJECT_KIND_INVALID")
    require(
        e["subject_kind"] == "ensemble" or e.get("checkpoint_artifact_id") is not None,
        "CHECKPOINT_REQUIRED",
    )
    if e["split"] == "external":
        require(
            e["source_kind"] in ("legacy", "external_record"), "EXTERNAL_SOURCE_INVALID"
        )
        require(
            all(
                e.get(k)
                for k in (
                    "dataset_origin_id",
                    "dataset_origin_role",
                    "population_manifest_uri",
                    "population_manifest_sha256",
                    "dataset_provenance_uri",
                    "dataset_provenance_sha256",
                )
            ),
            "EXTERNAL_PROVENANCE_MISSING",
        )
        for k in ("population_manifest_sha256", "dataset_provenance_sha256"):
            require(
                re.fullmatch("[0-9a-f]{64}", e[k]) is not None,
                "EXTERNAL_HASH_INVALID",
                k,
            )
    require(
        e["source_kind"] in ("legacy", "e10", "assessment", "external_record"),
        "SOURCE_KIND_INVALID",
    )
    if e["source_kind"] == "external_record":
        require(e["split"] == "external", "EXTERNAL_SOURCE_INVALID")
    if e["split"] == "test":
        require(e["source_kind"] == "assessment", "TEST_ASSESSMENT_REQUIRED")
    if e["source_kind"] == "e10":
        require(
            e["evaluation_role"] in {"training_validation_final", "calibration_default", "calibration_selected"}
            and e["run_id"] == e["training_run_id"],
            "E10_ROLE_INVALID",
        )
        if e['evaluation_role'] == 'calibration_default':
            require(e['threshold_source'] == 'default' and e.get('calibration_id') is None,
                    'E04_DEFAULT_SOURCE')
        if e['evaluation_role'] == 'calibration_selected':
            require(e['threshold_source'] == 'validation_calibration' and e.get('calibration_id') is not None,
                    'E04_SELECTED_SOURCE')
        require(
            e.get("event_kind") == "e10_event"
            and e.get("event_phase") == "run_event_v1"
            and e.get("source_event_id")
            and e.get("event_key") == str(e["source_event_id"]),
            "E10_REFERENCE_INVALID",
        )
    value = number(e["threshold_used"], "threshold")
    require(0 <= value <= 1, "THRESHOLD_RANGE")
    require(
        (
            e["threshold_source"] == "default"
            and value == Decimal(".5")
            and e.get("calibration_id") is None
        )
        or (
            e["threshold_source"] == "validation_calibration"
            and e.get("calibration_id") is not None
        )
        or (
            e["threshold_source"] == "protocol_numeric"
            and e.get("calibration_id") is None
        ),
        "THRESHOLD_LINEAGE_INVALID",
    )
    return e


def history(row):
    r = deepcopy(row)
    require(
        r.get("run_id") is not None
        and type(r.get("epoch")) is int
        and r["epoch"] >= 0
        and r.get("phase") is not None,
        "HISTORY_IDENTITY_REQUIRED",
    )
    for old, new in [("loss", "train_loss"), ("accuracy", "train_accuracy")]:
        a, b = r.get(old), r.get(new)
        require(
            a is None or b is None or number(a, old) == number(b, new),
            "HISTORY_ALIAS_CONFLICT",
        )
        if b is None and a is not None:
            r[new] = a
        if a is None and b is not None:
            r[old] = b
    return r


def calibration(row, binding, evidence, evaluations):
    r = deepcopy(row)
    require(
        r.get("calibration_split") == "val"
        and number(r["target_recall"], "target") == Decimal(".98")
        and number(r["default_threshold"], "default") == Decimal(".5"),
        "CALIBRATION_VAL_ONLY",
    )
    for col in ("default_evaluation_id", "selected_evaluation_id"):
        r[col] = evidence.get(binding[col])
    by_id = {str(e["id"]): e for e in evaluations}
    require(
        all(
            str(r[k]) in by_id
            for k in ("default_evaluation_id", "selected_evaluation_id")
        ),
        "CALIBRATION_EVALUATION_MISSING",
    )
    a, b = (
        by_id[str(r[k])] for k in ("default_evaluation_id", "selected_evaluation_id")
    )
    require(
        a["id"] != b["id"]
        and a["split"] == b["split"] == "val"
        and a["evaluation_role"] == "calibration_default"
        and b["evaluation_role"] == "calibration_selected",
        "CALIBRATION_PAIR_INVALID",
    )
    require(
        all(
            a[k] == b[k]
            for k in (
                "training_run_id",
                "dataset_version_id",
                "population_hash",
                "checkpoint_artifact_id",
            )
        )
        and a["training_run_id"] == r["run_id"]
        and a["threshold_used"] == Decimal(".5")
        and number(b["threshold_used"], "threshold")
        == number(r["threshold_selected"], "selected"),
        "CALIBRATION_PAIR_LINEAGE",
    )
    return r
