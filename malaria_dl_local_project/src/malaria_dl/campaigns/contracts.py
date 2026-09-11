"""Versioned scientific identity and pure planning using the E2 resolver."""

import hashlib
import json
import math
from copy import deepcopy
from dataclasses import asdict


class CampaignError(ValueError):
    pass


def canonical(value):
    """JSON v1: string keys sorted, list order significant, integral floats -> int.

    UTF-8 strings are exact (no Unicode normalization). No accidental IDs or times
    are stripped implicitly: scientific_configuration explicitly removes seed.
    """

    def normalize(v):
        if v is None or type(v) in (str, bool, int):
            return v
        if type(v) is float and math.isfinite(v):
            return int(v) if v.is_integer() else v
        if type(v) is list:
            return [normalize(x) for x in v]
        if type(v) is dict and all(type(k) is str for k in v):
            return {k: normalize(x) for k, x in v.items()}
        raise CampaignError("NON_CANONICAL_JSON")

    return json.dumps(
        normalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def scientific_configuration(config):
    result = {
        k: deepcopy(config[k])
        for k in ("schema_version", "model_id", "adapter_version", "resolved")
    }
    result["resolved"]["execution"].pop("seed", None)
    return result


def member_configuration(config, seed):
    result = deepcopy(config)
    result["resolved"]["execution"]["seed"] = seed
    return result


def required_object(value, keys, name):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise CampaignError("INVALID_FIELDS:" + name)


def validate_protocol(protocol, *, frozen=False, dataset=None):
    canonical(protocol)
    if not isinstance(protocol, dict):
        raise CampaignError("PROTOCOL_OBJECT_REQUIRED")
    allowed = {
        "version",
        "objective",
        "metrics",
        "sensitivity_target",
        "specificity_minimum",
        "roles",
        "ranking",
        "checkpoint",
        "early_stopping",
        "calibration",
        "budget",
        "missing",
        "retries",
        "fallback",
        "test_access",
        "aggregation",
        "uncertainty",
        "limitations",
        "pending",
    }
    if set(protocol) - allowed:
        raise CampaignError("UNKNOWN_PROTOCOL_FIELD")
    roles = protocol.get("roles", {})
    if not isinstance(roles, dict) or set(roles) - {
        "train",
        "selection",
        "calibration",
        "final_test",
    }:
        raise CampaignError("INVALID_DATA_ROLES")
    for role, split in roles.items():
        expected = {
            "train": "train",
            "selection": "val",
            "calibration": "val",
            "final_test": "test",
        }[role]
        if split != expected:
            raise CampaignError("UNSUPPORTED_OR_TEST_SELECTION_ROLE")
    # This dataset contract accredits physical train/val/test only, not new partitions.
    if protocol.get("test_access") not in (None, "final_only_after_candidate_lock"):
        raise CampaignError("TEST_ACCESS_CONFLICT")
    for key in ("sensitivity_target", "specificity_minimum"):
        if protocol.get(key) is not None and (
            type(protocol[key]) not in (int, float) or not 0 <= protocol[key] <= 1
        ):
            raise CampaignError("INVALID_CLINICAL_TARGET")
    for field, key in (("ranking", "partition"), ("calibration", "population")):
        if field in protocol:
            value = protocol[field]
            if not isinstance(value, dict) or (key in value and value[key] != "val"):
                raise CampaignError("TEST_OR_UNSUPPORTED_ROLE")
    if "limitations" in protocol and not isinstance(protocol["limitations"], dict):
        raise CampaignError("INVALID_LIMITATIONS")
    if protocol.get("limitations", {}).get("independent_calibration") is True:
        raise CampaignError("FALSE_CALIBRATION_INDEPENDENCE")
    if not frozen:
        return deepcopy(protocol)
    if (
        set(protocol) != allowed
        or protocol["pending"] != []
        or any(protocol[k] is None for k in allowed)
    ):
        raise CampaignError("SCIENTIFIC_DECISIONS_PENDING")
    if not isinstance(protocol["version"], str) or not protocol["version"].strip():
        raise CampaignError("PROTOCOL_VERSION_REQUIRED")
    if not isinstance(protocol["objective"], str) or not protocol["objective"].strip():
        raise CampaignError("OBJECTIVE_REQUIRED")
    if roles != {
        "train": "train",
        "selection": "val",
        "calibration": "val",
        "final_test": "test",
    }:
        raise CampaignError("DATA_ROLES_REQUIRED")
    counts = (dataset or {}).get("counts", {})
    if not all(
        type(counts.get(s)) is int and counts[s] > 0 for s in ("train", "val", "test")
    ):
        raise CampaignError("DATA_ROLES_NOT_ACCREDITED")
    required_object(
        protocol["limitations"],
        ("shared_val", "independent_calibration", "test_exposure"),
        "limitations",
    )
    if (
        not isinstance(protocol["limitations"]["shared_val"], str)
        or not protocol["limitations"]["shared_val"].strip()
        or protocol["limitations"]["independent_calibration"] is not False
        or protocol["limitations"]["test_exposure"]
        not in ("previously_accessed", "unknown", "accredited_unexposed")
    ):
        raise CampaignError("FALSE_INDEPENDENCE_OR_UNDECLARED_OVERLAP")
    # No independent exposure attestation is available from E1's seal.
    if protocol["limitations"]["test_exposure"] == "accredited_unexposed":
        raise CampaignError("TEST_INDEPENDENCE_NOT_ACCREDITED")
    required_object(
        protocol["metrics"],
        ("primary", "secondary", "definitions_version", "compliance"),
        "metrics",
    )
    if (
        not isinstance(protocol["metrics"]["primary"], list)
        or not protocol["metrics"]["primary"]
        or not isinstance(protocol["metrics"]["secondary"], list)
        or protocol["metrics"]["compliance"]
        not in ("point_estimate", "confidence_bound")
    ):
        raise CampaignError("METRICS_REQUIRED")
    required_object(
        protocol["ranking"], ("partition", "criteria", "tie_breaks"), "ranking"
    )
    if (
        protocol["ranking"]["partition"] != "val"
        or not protocol["ranking"]["criteria"]
        or not protocol["ranking"]["tie_breaks"]
    ):
        raise CampaignError("RANKING_NOT_FIXED_ON_VAL")
    required_object(
        protocol["checkpoint"], ("policy", "monitor", "mode", "threshold"), "checkpoint"
    )
    if protocol["checkpoint"]["threshold"] != 0.5:
        raise CampaignError("E2_SELECTION_THRESHOLD_IS_0_5")
    required_object(
        protocol["early_stopping"],
        ("enabled", "monitor", "mode", "patience", "min_delta", "restore_best_weights"),
        "early_stopping",
    )
    required_object(
        protocol["calibration"], ("algorithm", "population", "version"), "calibration"
    )
    if (
        protocol["calibration"]["algorithm"] not in ("none", "threshold_grid")
        or protocol["calibration"]["population"] != "val"
    ):
        raise CampaignError("CALIBRATION_NOT_SUPPORTED_OR_TEST")
    required_object(
        protocol["budget"], ("max_members", "max_attempts_per_member"), "budget"
    )
    if any(type(v) is not int or v < 1 for v in protocol["budget"].values()):
        raise CampaignError("INVALID_BUDGET")
    if (
        protocol["retries"] != "first_verified_attempt"
        or protocol["missing"] != "report_all_members"
        or protocol["fallback"] != "diagnostic_only"
    ):
        raise CampaignError("UNSUPPORTED_ATTEMPT_OR_MISSING_POLICY")
    for field in ("aggregation", "uncertainty"):
        required_object(protocol[field], ("version", "specification"), field)

    # Non-empty versioned scientific definitions; numbers never filled by historic defaults.
    def nonempty(v):
        if isinstance(v, str):
            return bool(v.strip())
        if isinstance(v, list):
            return all(nonempty(x) for x in v)
        if isinstance(v, dict):
            return all(nonempty(x) for x in v.values())
        return v is not None

    if not nonempty(protocol):
        raise CampaignError("EMPTY_PROTOCOL_DEFINITION")
    return deepcopy(protocol)


def expand_matrix(request, protocol=None, *, frozen=False, dataset=None):
    from ..models.configuration import resolve_config
    from ..models.registry import enabled_models, resolve_descriptor

    required_object(
        request, ("models", "optimizers", "seeds", "variants", "exclusions"), "matrix"
    )
    canonical(request)
    seeds = request["seeds"]
    if (
        not isinstance(seeds, list)
        or not seeds
        or any(type(s) is not int or not 0 <= s <= 2147483647 for s in seeds)
    ):
        raise CampaignError("INVALID_TRAINING_SEEDS")
    seeds = sorted(set(seeds))
    names = (
        request["models"] if request["models"] is not None else list(enabled_models())
    )
    if not isinstance(names, list) or not names:
        raise CampaignError("NO_MODELS")
    models = sorted({resolve_descriptor(n).id for n in names})
    variants = request["variants"]
    if not isinstance(variants, list) or not variants:
        raise CampaignError("NO_VARIANTS")
    variant_names = []
    for v in variants:
        required_object(v, ("name", "selected", "by_model"), "variant")
        if (
            not isinstance(v["name"], str)
            or not v["name"]
            or v["name"] in variant_names
        ):
            raise CampaignError("INVALID_VARIANT_NAME")
        variant_names.append(v["name"])
        if not isinstance(v["by_model"], dict) or set(v["by_model"]) - set(models):
            raise CampaignError("UNKNOWN_VARIANT_MODEL")
        for selected in (v["selected"], *v["by_model"].values()):
            if not isinstance(selected, dict) or "seed" in selected.get(
                "execution", {}
            ):
                raise CampaignError("SEED_BELONGS_TO_MEMBER")
    if not isinstance(request["exclusions"], list):
        raise CampaignError("EXCLUSIONS_LIST_REQUIRED")
    exclusions = {}
    for e in request["exclusions"]:
        required_object(e, ("model", "optimizer", "variant", "reason"), "exclusion")
        key = (e["model"], e["optimizer"], e["variant"])
        if (
            key in exclusions
            or not isinstance(e["reason"], str)
            or not e["reason"].strip()
        ):
            raise CampaignError("INVALID_EXCLUSION")
        exclusions[key] = e["reason"]
    if protocol is not None:
        validate_protocol(protocol, frozen=frozen, dataset=dataset)
    configs, members, registry = {}, [], []
    consumed = set()
    for model in models:
        d = resolve_descriptor(model)
        descriptor = asdict(d)
        descriptor.pop("config_path")
        registry.append(descriptor)
        opts = (
            request["optimizers"]
            if request["optimizers"] is not None
            else list(d.optimizers)
        )
        if (
            not isinstance(opts, list)
            or not opts
            or any(o not in d.optimizers for o in opts)
        ):
            raise CampaignError("INCOMPATIBLE_OPTIMIZER_MATRIX")
        for optimizer in sorted(set(opts)):
            for variant in sorted(variants, key=lambda x: x["name"]):
                overrides = deepcopy(variant["by_model"].get(model, {}))
                overrides.setdefault("optimizer", {})["name"] = optimizer
                if frozen:
                    p = protocol
                    cp = p["checkpoint"]
                    es = p["early_stopping"]
                    policy = {
                        "checkpoint_policy": cp["policy"],
                        "checkpoint_monitor": cp["monitor"],
                        "checkpoint_mode": cp["mode"],
                        "min_recall": p["sensitivity_target"],
                        "target_recall": p["sensitivity_target"],
                        "min_specificity": p["specificity_minimum"],
                        "calibrate_threshold": p["calibration"]["algorithm"] != "none",
                        "evaluate_best_on_test": False,
                        "early_stopping": es["enabled"],
                        "early_stopping_monitor": es["monitor"],
                        "early_stopping_mode": es["mode"],
                        "early_stopping_patience": es["patience"],
                        "early_stopping_min_delta": es["min_delta"],
                        "restore_best_weights": es["restore_best_weights"],
                    }
                    for supplied in (
                        variant["selected"].get("execution", {}),
                        overrides.get("execution", {}),
                    ):
                        if any(
                            k in supplied and supplied[k] != v
                            for k, v in policy.items()
                        ):
                            raise CampaignError("VARIANT_PROTOCOL_CONFLICT")
                    overrides.setdefault("execution", {}).update(policy)
                config = resolve_config(
                    model, variant["selected"], overrides, batch=True
                )
                identity = scientific_configuration(config)
                h = digest(identity)
                configs.setdefault(h, {"configuration": identity, "requests": []})[
                    "requests"
                ].append(
                    {
                        "variant": variant["name"],
                        "requested": config["requested"],
                        "provenance": config["provenance"],
                    }
                )
                key = (model, optimizer, variant["name"])
                reason = exclusions.get(key)
                if reason:
                    consumed.add(key)
                for seed in seeds:
                    if any(
                        m["configuration_hash"] == h and m["seed"] == seed
                        for m in members
                    ):
                        raise CampaignError("EQUIVALENT_VARIANTS_DUPLICATE_MEMBER")
                    members.append(
                        {
                            "configuration_hash": h,
                            "seed": seed,
                            "position": len(members),
                            "exclusion_reason": reason,
                        }
                    )
    if consumed != set(exclusions):
        raise CampaignError("UNUSED_EXCLUSION")
    if frozen and (
        len(members) > protocol["budget"]["max_members"]
        or all(m["exclusion_reason"] for m in members)
    ):
        raise CampaignError("BUDGET_OR_EMPTY_EXECUTABLE_MATRIX")
    # dataclass tuples become JSON arrays in the persisted registry snapshot.
    registry = json.loads(json.dumps(registry))
    return {
        "canonical_version": "campaign_json_v1",
        "registry": registry,
        "registry_hash": digest(registry),
        "configurations": configs,
        "members": members,
        "expected_count": len(members),
        "seeds": seeds,
    }


def validate_frozen_contract(contract):
    """Read persisted content without re-resolving from current configuration files."""
    required_object(
        contract,
        (
            "version",
            "name",
            "purpose",
            "experiment_id",
            "dataset",
            "dataset_evidence_id",
            "requested",
            "protocol",
            "environment",
            "matrix",
        ),
        "frozen_contract",
    )
    canonical(contract)
    if contract["version"] != "campaign_contract_v1":
        raise CampaignError("UNKNOWN_CAMPAIGN_CONTRACT")
    validate_protocol(contract["protocol"], frozen=True, dataset=contract["dataset"])
    environment = contract["environment"]
    if (
        not isinstance(environment, dict)
        or not isinstance(environment.get("source_sha256"), str)
        or len(environment["source_sha256"]) != 64
        or not environment.get("python")
        or not environment.get("tensorflow")
        or not environment.get("packages")
        or not isinstance(environment.get("determinism_environment"), dict)
    ):
        raise CampaignError("CODE_ENVIRONMENT_IDENTITY_REQUIRED")
    matrix = contract["matrix"]
    required_object(
        matrix,
        (
            "canonical_version",
            "registry",
            "registry_hash",
            "configurations",
            "members",
            "expected_count",
            "seeds",
        ),
        "frozen_matrix",
    )
    if (
        matrix["canonical_version"] != "campaign_json_v1"
        or digest(matrix["registry"]) != matrix["registry_hash"]
    ):
        raise CampaignError("REGISTRY_SNAPSHOT_CONFLICT")
    if matrix["expected_count"] != len(matrix["members"]) or not matrix["members"]:
        raise CampaignError("INCOMPLETE_MATRIX")
    from ..data.input_contract import validate_input_contract

    for h, item in matrix["configurations"].items():
        required_object(item, ("configuration", "requests"), "configuration_snapshot")
        c = item["configuration"]
        required_object(
            c,
            ("schema_version", "model_id", "adapter_version", "resolved"),
            "configuration_identity",
        )
        required_object(
            c["resolved"],
            (
                "model",
                "optimizer",
                "execution",
                "recipe",
                "selection",
                "input_contract",
            ),
            "resolved_configuration",
        )
        inp = validate_input_contract(c["resolved"]["input_contract"])
        if (
            inp["architecture"] != c["model_id"]
            or inp["adapter_version"] != c["adapter_version"]
            or digest(c) != h
        ):
            raise CampaignError("CONFIGURATION_SNAPSHOT_CONFLICT")
        if (
            c["resolved"]["execution"].get("evaluate_best_on_test") is not False
            or "seed" in c["resolved"]["execution"]
        ):
            raise CampaignError("CONFIGURATION_MEMBER_OR_TEST_CONFLICT")
    for item in matrix["configurations"].values():
        c = item["configuration"]
        e = c["resolved"]["execution"]
        p = contract["protocol"]
        expected = {
            "min_recall": p["sensitivity_target"],
            "target_recall": p["sensitivity_target"],
            "min_specificity": p["specificity_minimum"],
            "checkpoint_policy": p["checkpoint"]["policy"],
            "checkpoint_monitor": p["checkpoint"]["monitor"],
            "checkpoint_mode": p["checkpoint"]["mode"],
            "calibrate_threshold": p["calibration"]["algorithm"] != "none",
        }
        for k, v in p["early_stopping"].items():
            target = {
                "enabled": "early_stopping",
                "restore_best_weights": "restore_best_weights",
            }.get(k, "early_stopping_" + k)
            expected[target] = v
        if any(e.get(k) != v for k, v in expected.items()):
            raise CampaignError("FROZEN_PROTOCOL_CONFIGURATION_CONFLICT")
    seeds = matrix["seeds"]
    if (
        not isinstance(seeds, list)
        or seeds != sorted(set(seeds))
        or matrix["expected_count"] != len(matrix["configurations"]) * len(seeds)
    ):
        raise CampaignError("INCOMPLETE_CONFIGURATION_SEED_GRID")
    seen = set()
    for index, m in enumerate(matrix["members"]):
        required_object(
            m, ("configuration_hash", "seed", "position", "exclusion_reason"), "member"
        )
        identity = (m["configuration_hash"], m["seed"])
        if (
            identity in seen
            or m["configuration_hash"] not in matrix["configurations"]
            or m["position"] != index
        ):
            raise CampaignError("DUPLICATE_OR_INCOMPLETE_MEMBER")
        if type(m["seed"]) is not int or m["seed"] < 0 or m["seed"] not in seeds:
            raise CampaignError("INVALID_TRAINING_SEED")
        seen.add(identity)
    return contract
