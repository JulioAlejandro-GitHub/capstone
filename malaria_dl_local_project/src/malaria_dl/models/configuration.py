"""Pure resolution: versioned defaults < selected JSON < explicit CLI overrides."""

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from .registry import resolve_descriptor
from .optimizers import optimizer_config, BATCH_LEARNING_RATES


def merge_strict(base, override, path=""):
    if not isinstance(override, dict):
        raise ValueError("EXPECTED_OBJECT:" + path)
    for key, value in override.items():
        if key not in base:
            raise ValueError("UNKNOWN_CONFIG_FIELD:" + path + key)
        if isinstance(base[key], dict) and path + key != "optimizer.parameters":
            merge_strict(base[key], value, path + key + ".")
        else:
            base[key] = deepcopy(value)
    return base


def _finite_tree(value, path=""):
    if isinstance(value, dict):
        for k, v in value.items():
            _finite_tree(v, path + k + ".")
    elif isinstance(value, list):
        for v in value:
            _finite_tree(v, path)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("NON_FINITE_CONFIG:" + path)


def resolve_config(model_name, selected=None, overrides=None, *, batch=False):
    descriptor = resolve_descriptor(model_name)
    raw = Path(descriptor.config_path).read_bytes()
    defaults = json.loads(raw)
    config = deepcopy(defaults)
    if batch:
        config["execution"].update(config["batch"])
    selected = deepcopy(selected or {})
    overrides = deepcopy(overrides or {})
    merge_strict(config, selected)
    merge_strict(config, overrides)
    _finite_tree(config)
    if config["recipe"] != defaults["recipe"]:
        raise ValueError("UNSUPPORTED_RECIPE_CHANGE")
    if "batch" in selected:
        if batch:
            for key, value in selected["batch"].items():
                if key not in selected.get(
                    "execution", {}
                ) and key not in overrides.get("execution", {}):
                    config["execution"][key] = value
        elif selected["batch"] != defaults["batch"]:
            raise ValueError("IGNORED_BATCH_PROFILE")
    if config["schema_version"] != "model_config_v1":
        raise ValueError("UNKNOWN_CONFIG_SCHEMA")
    m, e, o = config["model"], config["execution"], config["optimizer"]
    if (
        not isinstance(m["input_shape"], list)
        or len(m["input_shape"]) != 3
        or any(type(v) is not int for v in m["input_shape"])
        or m["input_shape"][0] < 32
        or m["input_shape"][0] != m["input_shape"][1]
        or m["input_shape"][2] != 3
    ):
        raise ValueError("INVALID_INPUT_SHAPE")
    for key in ("dropout", "l2"):
        if type(m[key]) not in (int, float) or not 0 <= m[key] < 1:
            raise ValueError("INVALID_MODEL_PARAMETER:" + key)
    if (
        type(m["fine_tune_layers"]) is not int
        or not 0 <= m["fine_tune_layers"] <= defaults["model"]["fine_tune_layers"]
    ):
        raise ValueError("INVALID_FINE_TUNE_LAYERS")
    # Architecture-specific supported knobs are declared by its versioned defaults.
    for key in ("head_units", "batch_normalization"):
        if m[key] != defaults["model"][key] or type(m[key]) is not type(
            defaults["model"][key]
        ):
            raise ValueError("UNSUPPORTED_MODEL_PARAMETER:" + key)
    if m["weights"] not in ("none", "imagenet") or (
        "fine_tuning" not in descriptor.strategies and m["weights"] != "none"
    ):
        raise ValueError("INCOMPATIBLE_WEIGHTS")
    allowed_preprocessing = descriptor.preprocessing_modes
    if m["preprocessing"] == "auto":
        m["preprocessing"] = descriptor.default_preprocessing
    if m["preprocessing"] not in allowed_preprocessing:
        raise ValueError("INCOMPATIBLE_PREPROCESSING")
    if defaults["model"]["l2"] == 0 and m["l2"] != 0:
        raise ValueError("UNSUPPORTED_MODEL_PARAMETER:l2")
    for key in (
        "max_epochs",
        "fine_tune_epochs",
        "batch_size",
        "seed",
        "early_stopping_patience",
    ):
        if type(e[key]) is not int or e[key] < (
            1 if key in ("max_epochs", "batch_size") else 0
        ):
            raise ValueError("INVALID_EXECUTION_PARAMETER:" + key)
    for key, default in defaults["execution"].items():
        if isinstance(default, bool) and type(e[key]) is not bool:
            raise ValueError("INVALID_EXECUTION_PARAMETER:" + key)
    for key in ("min_recall", "target_recall", "min_class_fraction", "min_specificity"):
        v = e[key]
        if v is None and key == "min_specificity":
            continue
        if type(v) not in (int, float) or not 0 <= v <= (
            0.5 if key == "min_class_fraction" else 1
        ):
            raise ValueError("INVALID_EXECUTION_PARAMETER:" + key)
    if (
        type(e["early_stopping_min_delta"]) not in (int, float)
        or e["early_stopping_min_delta"] < 0
    ):
        raise ValueError("INVALID_EARLY_STOPPING_DELTA")
    if type(e["beta"]) not in (int, float) or e["beta"] != 2:
        raise ValueError("F2_REQUIRES_BETA_2")
    if e["checkpoint_policy"] not in (
        "f2",
        "auc_with_min_recall",
        "val_auc",
        "balanced_accuracy",
    ):
        raise ValueError("INVALID_CHECKPOINT_POLICY")
    for key in ("checkpoint_mode", "early_stopping_mode"):
        if e[key] not in ("auto", "min", "max"):
            raise ValueError("INVALID_MONITOR_MODE")
    from ..training.cli_constants import CHECKPOINT_METRIC_CHOICES

    for key in ("checkpoint_monitor", "early_stopping_monitor"):
        if e[key] is not None and e[key] not in CHECKPOINT_METRIC_CHOICES:
            raise ValueError("INVALID_MONITOR")
    if e["fine_tune_epochs"] and (
        "fine_tuning" not in descriptor.strategies or m["fine_tune_layers"] == 0
    ):
        raise ValueError("INCOMPATIBLE_FINE_TUNING")
    if "fine_tuning" not in descriptor.strategies and m["fine_tune_layers"] != 0:
        raise ValueError("IGNORED_FINE_TUNE_LAYERS")
    if not isinstance(o["parameters"], dict):
        raise ValueError("EXPECTED_OPTIMIZER_PARAMETERS_OBJECT")
    if o["name"] not in descriptor.optimizers:
        raise ValueError("INCOMPATIBLE_OPTIMIZER")
    if batch and "learning_rate" not in o["parameters"]:
        o["parameters"]["learning_rate"] = BATCH_LEARNING_RATES[o["name"]][0]
        if not any(
            "fine_tune_learning_rate" in x.get("optimizer", {})
            for x in (selected, overrides)
        ):
            o["fine_tune_learning_rate"] = BATCH_LEARNING_RATES[o["name"]][1]
    o["parameters"] = optimizer_config(o["name"], o["parameters"])
    if (
        type(o["fine_tune_learning_rate"]) not in (int, float)
        or o["fine_tune_learning_rate"] <= 0
    ):
        raise ValueError("INVALID_FINE_TUNE_LEARNING_RATE")
    from ..data.input_contract import make_input_contract
    input_contract = make_input_contract(descriptor.id, descriptor.version, m['input_shape'], m['preprocessing'], descriptor.internal_preprocessing)
    return dict(
        schema_version=config["schema_version"],
        model_id=descriptor.id,
        adapter_version=descriptor.version,
        requested=dict(
            model_name=model_name, selected=selected, overrides=overrides, batch=batch
        ),
        provenance=dict(
            defaults_sha256=hashlib.sha256(raw).hexdigest(),
            precedence=["versioned_defaults", "selected", "explicit_overrides"],
        ),
        resolved={
            **{k: config[k] for k in ("model", "optimizer", "execution", "recipe")},
            "selection": selection_semantics(e),
            "input_contract": input_contract,
        },
    )


def load_selected(path):
    return json.loads(Path(path).read_text()) if path else {}


def config_digest(resolved):
    return hashlib.sha256(
        json.dumps(
            resolved, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def selection_semantics(execution):
    e = execution
    policy_monitor = {
        "f2": "val_f2_parasitized",
        "balanced_accuracy": "val_balanced_accuracy",
    }.get(e["checkpoint_policy"], "val_auc")
    explicit = e["checkpoint_monitor"] is not None or e["checkpoint_mode"] == "min"
    monitor = e["checkpoint_monitor"] or policy_monitor

    def mode(name, requested):
        return (
            requested
            if requested != "auto"
            else ("min" if name.endswith("loss") else "max")
        )

    checkpoint_mode = mode(monitor, e["checkpoint_mode"])
    es_monitor = e["early_stopping_monitor"] or (
        monitor if explicit else "val_checkpoint_policy_score"
    )
    es_mode = (
        checkpoint_mode
        if e["early_stopping_monitor"] is None
        and explicit
        and e["early_stopping_mode"] == "auto"
        else mode(es_monitor, e["early_stopping_mode"])
    )
    return dict(
        monitor=monitor,
        mode=checkpoint_mode,
        explicit=explicit,
        early_stopping_monitor=es_monitor,
        early_stopping_mode=es_mode,
        threshold=0.5,
        beta=2.0,
        clinical_objective="min_recall; assessed independently of technical completion",
        fallback="retain existing policy warning and collapse status",
    )
