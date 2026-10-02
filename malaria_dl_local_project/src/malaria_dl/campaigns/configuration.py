"""SWV2.2 operator configuration -> canonical E4 request/protocol. No TRAIN; the model
catalog (ids and labels) is read from public.models through models.registry.

The operator edits a campaign on one page; this module is the single translation from that
document into the existing E4 contract (``expand_matrix`` request + frozen protocol). It never
introduces parameters: every model parameter is a field of model_config_v1 whose domain and
editability follow ``models.configuration.resolve_config`` and the model descriptor; defaults are
the versioned batch profile; protocol decisions come from the approved scientific protocol.

Contract facts this module must respect (see campaigns.contracts / campaign_guard):
- seeds, optimizers and the protocol (EarlyStopping, checkpoint, clinical target) are
  campaign-level; per-model values travel as ``variants[].by_model`` overrides;
- total experiments = ``expand_matrix(...)["expected_count"]`` (configurations x seeds).
"""

from copy import deepcopy
from functools import lru_cache
import math

from .contracts import CampaignError, digest, expand_matrix

CONFIGURATION_VERSION = "campaign_configuration_v1"
SEED_MAX = 2147483647
NAME_MAX = 200

OPTIMIZER_LABELS = {"adam": "Adam", "adamw": "AdamW", "sgd": "SGD", "adadelta": "Adadelta"}

# model_config_v1 fields an operator may see. Editability/domain is decided per descriptor below,
# with exactly the rules resolve_config enforces (it remains the final authority).
PARAMETERS = (
    ("input_size", ("model", "input_shape"), "integer", "architecture", "Tamaño de entrada (px, cuadrado RGB)"),
    ("weights", ("model", "weights"), "enum", "architecture", "Pesos iniciales"),
    ("preprocessing", ("model", "preprocessing"), "enum", "architecture", "Preprocesamiento"),
    ("dropout", ("model", "dropout"), "number", "architecture", "Dropout"),
    ("l2", ("model", "l2"), "number", "architecture", "Regularización L2"),
    ("head_units", ("model", "head_units"), "integer", "architecture", "Unidades de la cabeza"),
    ("batch_normalization", ("model", "batch_normalization"), "enum", "architecture", "Batch normalization"),
    ("fine_tune_layers", ("model", "fine_tune_layers"), "integer", "fine_tuning", "Capas descongeladas en fine-tuning"),
    ("max_epochs", ("execution", "max_epochs"), "integer", "training", "Épocas (fase base)"),
    ("fine_tune_epochs", ("execution", "fine_tune_epochs"), "integer", "fine_tuning", "Épocas de fine-tuning"),
    ("batch_size", ("execution", "batch_size"), "integer", "training", "Batch size"),
    ("deterministic_ops", ("execution", "deterministic_ops"), "boolean", "training", "Operaciones deterministas"),
    ("no_augment", ("execution", "no_augment"), "boolean", "training", "Desactivar data augmentation"),
    ("reject_prediction_collapse", ("execution", "reject_prediction_collapse"), "boolean", "selection",
     "Rechazar colapso de predicción"),
    ("min_class_fraction", ("execution", "min_class_fraction"), "number", "selection",
     "Fracción mínima por clase (colapso)"),
)
PROTOCOL_PARAMETERS = (
    ("early_stopping.enabled", "boolean", "EarlyStopping activo", {}),
    ("early_stopping.patience", "integer", "Paciencia (épocas)", {"minimum": 0}),
    ("early_stopping.min_delta", "number", "Mejora mínima (min_delta)", {"minimum": 0}),
    ("early_stopping.restore_best_weights", "boolean", "Restaurar mejores pesos", {}),
    ("budget.max_attempts_per_member", "integer", "Intentos máximos por experimento", {"minimum": 1}),
)
CONFIGURATION_KEYS = {"version", "models", "optimizers", "seeds", "variants", "protocol"}


def _registry():
    """(Python descriptor, public.models row) for every model in the catalog."""
    from ..models.registry import model_catalog, resolve_descriptor

    return [(resolve_descriptor(m["name"]), m) for m in model_catalog()]


def _get(tree, path):
    for key in path:
        tree = tree[key]
    return tree


def _set(tree, path, value):
    for key in path[:-1]:
        tree = tree.setdefault(key, {})
    tree[path[-1]] = value


def _defaults(descriptor):
    """Versioned batch defaults exactly as resolve_config produces them for this model."""
    import json
    from pathlib import Path
    from ..models.configuration import resolve_config

    raw = json.loads(Path(descriptor.config_path).read_text())
    resolved = resolve_config(descriptor.id, None, {"optimizer": {"name": descriptor.optimizers[0]}}, batch=True)
    return raw, resolved


def _parameter(descriptor, raw, resolved, key, path, kind, section, label):
    fine = "fine_tuning" in descriptor.strategies
    value = _get(resolved["resolved"], path)
    spec = dict(key=key, label=label, section=section, type=kind, path=".".join(path), editable=True,
                source=f"configs/models/{descriptor.id}.json (perfil batch)")
    if key == "input_size":
        value = value[0]
        spec.update(minimum=32, note="Se aplica como [n, n, 3].")
    elif key in ("dropout", "l2"):
        spec.update(minimum=0, maximum=1, exclusive_maximum=True)
        if key == "l2" and raw["model"]["l2"] == 0:
            spec.update(editable=False, note="La arquitectura no admite L2 distinto de 0.")
    elif key == "weights":
        spec["choices"] = ["none", "imagenet"] if fine else ["none"]
        spec["editable"] = len(spec["choices"]) > 1
    elif key == "preprocessing":
        spec["choices"] = list(descriptor.preprocessing_modes)
        spec["editable"] = len(spec["choices"]) > 1
    elif key in ("head_units", "batch_normalization"):
        spec.update(editable=False, note="Parámetro fijo validado de la arquitectura versionada.")
    elif key == "fine_tune_layers":
        spec.update(minimum=0, maximum=raw["model"]["fine_tune_layers"])
        spec["editable"] = fine and raw["model"]["fine_tune_layers"] > 0
    elif key in ("max_epochs", "batch_size"):
        spec["minimum"] = 1
    elif key == "fine_tune_epochs":
        spec.update(minimum=0, editable=fine)
    elif key == "min_class_fraction":
        spec.update(minimum=0, maximum=0.5)
    if kind == "enum" and "choices" not in spec:
        spec["choices"] = [value]
    spec["default"] = value
    return spec


@lru_cache(maxsize=1)
def protocol_template():
    """Approved scientific protocol (configs/science/e7_v1.json) as an E4 campaign plan."""
    from ..science.protocol import campaign_plan, load_protocol

    plan = campaign_plan(load_protocol())
    return deepcopy(plan["request"]), deepcopy(plan["campaign_protocol"])


def _catalog_models():
    models = []
    for d, row in _registry():
        raw, resolved = _defaults(d)
        models.append(dict(
            # Label is public.models.architecture; a row without one is shown by its name.
            id=d.id, label=row["architecture"] or d.id, adapter_version=d.version, strategies=list(d.strategies),
            optimizers=list(d.optimizers), input_contract=d.input_contract, output_contract=d.output_contract,
            parameters=[_parameter(d, raw, resolved, *p) for p in PARAMETERS],
        ))
    return models


def _optimizers():
    from ..models.optimizers import BATCH_LEARNING_RATES, OPTIMIZER_DEFAULTS, optimizer_config

    names = [n for n in OPTIMIZER_DEFAULTS if any(n in d.optimizers for d, _ in _registry())]
    return [dict(id=n, label=OPTIMIZER_LABELS.get(n, n), learning_rate=BATCH_LEARNING_RATES[n][0],
                 fine_tune_learning_rate=BATCH_LEARNING_RATES[n][1],
                 parameters=optimizer_config(n, {"learning_rate": BATCH_LEARNING_RATES[n][0]}),
                 source="src/malaria_dl/models/optimizers.py (OPTIMIZER_DEFAULTS, BATCH_LEARNING_RATES)")
            for n in names]


def _protocol_values(protocol):
    return {"early_stopping": {k: protocol["early_stopping"][k]
                               for k in ("enabled", "patience", "min_delta", "restore_best_weights")},
            "budget": {"max_attempts_per_member": protocol["budget"]["max_attempts_per_member"]}}


def _variant_parameters(models, by_model=None):
    result = {}
    for m in models:
        values = {}
        for p in m["parameters"]:
            path = tuple(p["path"].split("."))
            supplied = (by_model or {}).get(m["id"], {})
            try:
                value = _get(supplied, path)
                value = value[0] if p["key"] == "input_size" else value
            except (KeyError, TypeError):
                value = p["default"]
            if p["editable"]:
                values[p["key"]] = value
        result[m["id"]] = values
    return result


def catalog():
    """Everything the UI needs to render a campaign form, discovered from the registry."""
    models = _catalog_models()
    request, protocol = protocol_template()
    template_values = _protocol_values(protocol)
    ids = [m["id"] for m in models]
    optimizers = _optimizers()
    common = [o["id"] for o in optimizers if all(o["id"] in m["optimizers"] for m in models)]
    e7_models = [m for m in models if m["id"] in request["models"]]
    presets = [
        dict(id="system_batch_defaults", label="Valores por defecto del sistema (perfil batch versionado)",
             configuration=dict(version=CONFIGURATION_VERSION, models=ids, optimizers=common,
                                seeds=list(request["seeds"]),
                                variants=[dict(name="configuracion_1", parameters=_variant_parameters(models))],
                                protocol=deepcopy(template_values))),
        dict(id=request["variants"][0]["name"], label="Plan científico aprobado " + request["variants"][0]["name"],
             configuration=dict(version=CONFIGURATION_VERSION, models=[m["id"] for m in e7_models],
                                optimizers=list(request["optimizers"]), seeds=list(request["seeds"]),
                                variants=[dict(name=request["variants"][0]["name"],
                                               parameters=_variant_parameters(e7_models,
                                                                              request["variants"][0]["by_model"]))],
                                protocol=deepcopy(template_values))),
    ]
    fixed = {
        "early_stopping.monitor": protocol["early_stopping"]["monitor"],
        "early_stopping.mode": protocol["early_stopping"]["mode"],
        "checkpoint.policy": protocol["checkpoint"]["policy"],
        "checkpoint.monitor": protocol["checkpoint"]["monitor"],
        "checkpoint.mode": protocol["checkpoint"]["mode"],
        "checkpoint.threshold": protocol["checkpoint"]["threshold"],
        "sensitivity_target": protocol["sensitivity_target"],
        "specificity_minimum": protocol["specificity_minimum"],
        "calibration.algorithm": protocol["calibration"]["algorithm"],
        "test_access": protocol["test_access"],
    }
    return dict(
        version=CONFIGURATION_VERSION,
        models=models,
        optimizers=optimizers,
        seeds=dict(minimum=0, maximum=SEED_MAX, scope="campaign", default=list(request["seeds"]),
                   source="configs/science/e7_v1.json (seeds)"),
        protocol=dict(template_version=protocol["version"], source="configs/science/e7_v1.json → science.protocol.campaign_plan",
                      editable=[dict(key=k, type=t, label=label, default=_get(template_values, k.split(".")), **extra)
                                for k, t, label, extra in PROTOCOL_PARAMETERS],
                      fixed=fixed, objective=protocol["objective"]),
        presets=presets,
        default_preset="system_batch_defaults",
        experiment_formula="Total de Experimentos = configuraciones × semillas; configuraciones = modelos × optimizadores × variantes",
    )


# ---------------------------------------------------------------- validation and translation

def _error(errors, field, code):
    errors.append(dict(field=field, code=code))


def _is_int(v):
    return type(v) is int


def _is_number(v):
    return type(v) in (int, float) and math.isfinite(v)


def _check_value(spec, value):
    kind = spec["type"]
    if kind == "boolean":
        return type(value) is bool
    if kind == "integer" and not _is_int(value):
        return False
    if kind == "number" and not _is_number(value):
        return False
    if kind == "enum":
        return isinstance(value, str) and value in spec["choices"]
    if "minimum" in spec and value < spec["minimum"]:
        return False
    if "maximum" in spec and (value >= spec["maximum"] if spec.get("exclusive_maximum") else value > spec["maximum"]):
        return False
    return True


def _unique_list(errors, field, value, check):
    if not isinstance(value, list) or not value:
        _error(errors, field, "REQUIRED_NON_EMPTY_LIST")
        return []
    if any(not check(v) for v in value):
        _error(errors, field, "INVALID_ITEM")
        return []
    if len(set(value)) != len(value):
        _error(errors, field, "DUPLICATE_ITEM")
        return []
    return value


def normalize(configuration):
    """Strict, field-addressed validation of the operator document. Returns (normalized, errors)."""
    errors = []
    if not isinstance(configuration, dict):
        return None, [dict(field="", code="CONFIGURATION_OBJECT_REQUIRED")]
    unknown = set(configuration) - CONFIGURATION_KEYS
    if unknown:
        for k in sorted(unknown):
            _error(errors, k, "UNKNOWN_FIELD")
    if configuration.get("version", CONFIGURATION_VERSION) != CONFIGURATION_VERSION:
        _error(errors, "version", "UNSUPPORTED_CONFIGURATION_VERSION")
    models = {m["id"]: m for m in _catalog_models()}
    selected = _unique_list(errors, "models", configuration.get("models"), lambda v: isinstance(v, str))
    for name in selected:
        if name not in models:
            _error(errors, "models", "UNKNOWN_OR_NOT_EXECUTABLE_MODEL:" + name)
    selected = [m for m in selected if m in models]
    known_optimizers = {o["id"] for o in _optimizers()}
    optimizers = _unique_list(errors, "optimizers", configuration.get("optimizers"), lambda v: isinstance(v, str))
    for o in optimizers:
        if o not in known_optimizers:
            _error(errors, "optimizers", "UNKNOWN_OPTIMIZER:" + o)
        elif any(o not in models[m]["optimizers"] for m in selected):
            _error(errors, "optimizers", "OPTIMIZER_NOT_SUPPORTED_BY_SELECTED_MODEL:" + o)
    seeds = _unique_list(errors, "seeds", configuration.get("seeds"),
                         lambda v: _is_int(v) and 0 <= v <= SEED_MAX)
    variants = configuration.get("variants")
    normalized_variants = []
    if not isinstance(variants, list) or not variants:
        _error(errors, "variants", "REQUIRED_NON_EMPTY_LIST")
        variants = []
    names = []
    for i, variant in enumerate(variants):
        field = f"variants[{i}]"
        if not isinstance(variant, dict) or set(variant) != {"name", "parameters"}:
            _error(errors, field, "INVALID_VARIANT_FIELDS")
            continue
        name = variant["name"]
        if not isinstance(name, str) or not name.strip() or len(name) > NAME_MAX or name != name.strip():
            _error(errors, field + ".name", "INVALID_VARIANT_NAME")
        elif name in names:
            _error(errors, field + ".name", "DUPLICATE_VARIANT_NAME")
        names.append(name)
        supplied = variant["parameters"]
        if not isinstance(supplied, dict):
            _error(errors, field + ".parameters", "PARAMETERS_OBJECT_REQUIRED")
            continue
        for model_id in sorted(set(supplied) - set(selected)):
            _error(errors, f"{field}.parameters.{model_id}", "PARAMETERS_FOR_UNSELECTED_MODEL")
        values = {}
        for model_id in selected:
            given = supplied.get(model_id, {})
            if not isinstance(given, dict):
                _error(errors, f"{field}.parameters.{model_id}", "PARAMETERS_OBJECT_REQUIRED")
                continue
            specs = {p["key"]: p for p in models[model_id]["parameters"]}
            out = {}
            for key in sorted(set(given) - set(specs)):
                _error(errors, f"{field}.parameters.{model_id}.{key}", "UNKNOWN_PARAMETER")
            for key, spec in specs.items():
                value = given.get(key, spec["default"])
                where = f"{field}.parameters.{model_id}.{key}"
                if not spec["editable"]:
                    # JSON may carry 0.0 as 0: compare values, but never a bool for a number.
                    if value != spec["default"] or (type(value) is bool) != (type(spec["default"]) is bool):
                        _error(errors, where, "PARAMETER_NOT_EDITABLE")
                    continue
                if not _check_value(spec, value):
                    _error(errors, where, "INVALID_PARAMETER_VALUE")
                    continue
                out[key] = value
            values[model_id] = out
        normalized_variants.append(dict(name=name, parameters=values))
    protocol = configuration.get("protocol")
    template = _protocol_values(protocol_template()[1])
    out_protocol = deepcopy(template)
    if not isinstance(protocol, dict) or set(protocol) != {"early_stopping", "budget"} \
            or not isinstance(protocol.get("early_stopping"), dict) or not isinstance(protocol.get("budget"), dict) \
            or set(protocol["early_stopping"]) != set(template["early_stopping"]) \
            or set(protocol["budget"]) != set(template["budget"]):
        _error(errors, "protocol", "INVALID_PROTOCOL_FIELDS")
    else:
        for key, kind, _label, extra in PROTOCOL_PARAMETERS:
            section, leaf = key.split(".")
            value = protocol[section][leaf]
            if not _check_value(dict(type=kind, **extra), value):
                _error(errors, "protocol." + key, "INVALID_PARAMETER_VALUE")
            else:
                out_protocol[section][leaf] = value
    normalized = dict(version=CONFIGURATION_VERSION, models=selected, optimizers=optimizers, seeds=seeds,
                      variants=normalized_variants, protocol=out_protocol)
    return normalized, errors


def build_request(normalized):
    """E4 request: per-model values are explicit by_model overrides of every editable parameter."""
    models = {m["id"]: m for m in _catalog_models()}
    variants = []
    for variant in normalized["variants"]:
        by_model = {}
        for model_id, values in variant["parameters"].items():
            overrides = {}
            for spec in models[model_id]["parameters"]:
                if spec["key"] in values:
                    value = values[spec["key"]]
                    if spec["key"] == "input_size":
                        value = [value, value, 3]
                    _set(overrides, tuple(spec["path"].split(".")), value)
            by_model[model_id] = overrides
        variants.append(dict(name=variant["name"], selected={}, by_model=by_model))
    return dict(models=sorted(normalized["models"]), optimizers=sorted(normalized["optimizers"]),
                seeds=sorted(normalized["seeds"]), variants=variants, exclusions=[])


def document_from_request(request, protocol):
    """Operator document of a stored campaign: the inverse of build_request/build_protocol.

    ``request`` is the E4 request persisted in ``experimental_campaigns.requested``; per-model
    values travel as explicit ``variants[].by_model`` overrides, so each variant re-reads them
    through the current catalog parameter paths (a path the catalog no longer exposes falls back
    to its current default; a model the catalog no longer registers is dropped). Only
    operator-editable parameters are exposed, and the protocol contributes only its
    operator-editable fields — exactly the shape the configuration page and ``normalize`` accept,
    so a stored campaign prefills its own editing form and re-saves to the same contract.
    """
    models = {m["id"]: m for m in _catalog_models()}
    requested = [m for m in request.get("models", []) if m in models]
    variants = []
    for variant in request.get("variants", []):
        by_model = variant.get("by_model") or {}
        parameters = {}
        for model_id in requested:
            overrides = by_model.get(model_id)
            if not isinstance(overrides, dict):
                continue
            values = {}
            for spec in models[model_id]["parameters"]:
                if not spec["editable"]:
                    continue
                try:
                    value = _get(overrides, tuple(spec["path"].split(".")))
                    value = value[0] if spec["key"] == "input_size" else value
                except (KeyError, TypeError):
                    value = spec["default"]
                values[spec["key"]] = value
            parameters[model_id] = values
        variants.append(dict(name=str(variant["name"]), parameters=parameters))
    return dict(
        version=CONFIGURATION_VERSION,
        models=requested,
        optimizers=list(request.get("optimizers", [])),
        seeds=list(request.get("seeds", [])),
        variants=variants,
        protocol=_protocol_values(protocol),
    )


def build_protocol(normalized, expected_count):
    """Approved protocol + the operator's EarlyStopping/budget values; budget sized to the matrix.

    The version keeps the approved identifier only when the result is exactly the approved
    protocol; otherwise it is a content-derived identifier, so a derived protocol never claims
    to be the approved one (E7 comparisons check that version).
    """
    template = protocol_template()[1]
    protocol = deepcopy(template)
    protocol["early_stopping"].update(normalized["protocol"]["early_stopping"])
    protocol["budget"] = dict(max_members=expected_count,
                              max_attempts_per_member=normalized["protocol"]["budget"]["max_attempts_per_member"])
    # PostgreSQL v2 run_configurations.clinical_target_recall: numeric NOT NULL, > 0 and <= 1.
    if not (_is_number(protocol["sensitivity_target"]) and 0 < protocol["sensitivity_target"] <= 1):
        raise CampaignError("SENSITIVITY_TARGET_OUTSIDE_V2_DOMAIN")
    if protocol != template:
        protocol["version"] = CONFIGURATION_VERSION + ":" + digest(
            {k: v for k, v in protocol.items() if k != "version"})
    return protocol


def resolve(configuration, dataset_counts=None):
    """Single canonical resolution used by preview, save and tests.

    Returns dict(valid, errors, normalized, request, protocol, matrix, summary). The total is
    always ``expand_matrix``'s expected_count; nothing else computes it.
    """
    normalized, errors = normalize(configuration)
    result = dict(valid=False, errors=errors, normalized=normalized, request=None, protocol=None,
                  matrix=None, summary=None)
    if errors:
        return result
    dataset = {"counts": dataset_counts} if dataset_counts is not None else {
        "counts": dict.fromkeys(("train", "val", "test"), 1)}
    try:
        request = build_request(normalized)
        provisional = build_protocol(normalized, SEED_MAX)
        count = expand_matrix(request, provisional, frozen=True, dataset=dataset)["expected_count"]
        protocol = build_protocol(normalized, count)
        matrix = expand_matrix(request, protocol, frozen=True, dataset=dataset)
    except (CampaignError, ValueError) as exc:
        errors.append(dict(field="", code=str(exc)))
        return result
    result.update(valid=True, request=request, protocol=protocol, matrix=matrix, summary=summarize(matrix, request))
    return result


def summarize(matrix, request):
    configurations = []
    for h, item in matrix["configurations"].items():
        c = item["configuration"]
        configurations.append(dict(configuration_hash=h, model_id=c["model_id"],
                                   optimizer=c["resolved"]["optimizer"]["name"],
                                   variants=sorted(r["variant"] for r in item["requests"])))
    configurations.sort(key=lambda x: (x["model_id"], x["optimizer"], x["variants"], x["configuration_hash"]))
    per_model = {}
    for c in configurations:
        per_model[c["model_id"]] = per_model.get(c["model_id"], 0) + len(matrix["seeds"])
    return dict(models=len(request["models"]), optimizers=len(request["optimizers"]),
                variants=len(request["variants"]), seeds=len(matrix["seeds"]),
                configurations=len(matrix["configurations"]), total_experiments=matrix["expected_count"],
                experiments_per_model=per_model, configuration_list=configurations)
