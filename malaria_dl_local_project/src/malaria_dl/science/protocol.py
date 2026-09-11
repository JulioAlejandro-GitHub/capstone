"""Frozen scientific protocol and explicit planned matrix, independent of current defaults."""

import json
from copy import deepcopy
from pathlib import Path

from ..campaigns.contracts import digest, scientific_configuration
from ..data.input_contract import MAPPING, validate_input_contract

PATH = Path(__file__).resolve().parents[3] / "configs/science/e7_v1.json"


class ScienceError(ValueError):
    pass


def require(value, code):
    if not value:
        raise ScienceError(code)


def load_protocol(path=PATH):
    p = json.loads(Path(path).read_text())
    require(
        digest(p) == "7db076d71c2143934f0b3bae47ff253f18d3f65c5c3f8efb2634586acbadbdf2",
        "FROZEN_PROTOCOL_HASH_CONFLICT",
    )
    require(p["version"] == "capstone_science_e7_v1", "PROTOCOL_VERSION_UNSUPPORTED")
    require(
        p["positive_class"] == MAPPING
        and p["objective"] == {"metric": "sensitivity", "operator": ">", "value": 0.98},
        "SCIENTIFIC_OBJECTIVE_CONFLICT",
    )
    require(
        len(p["seeds"]) >= 3
        and len(set(p["seeds"])) == len(p["seeds"])
        and all(type(s) is int for s in p["seeds"]),
        "SHARED_SEEDS_REQUIRED",
    )
    require(
        set(p["architectures"]) == {"custom_cnn", "vgg16", "densenet121"},
        "ARCHITECTURES_REQUIRED",
    )
    for key, config in p["configurations"].items():
        require(
            digest(config) == key and "seed" not in config["resolved"]["execution"],
            "CONFIGURATION_HASH_CONFLICT",
        )
        validate_input_contract(config["resolved"]["input_contract"])
        require(
            config["resolved"]["execution"]["evaluate_best_on_test"] is False,
            "TEST_FORBIDDEN",
        )
    return p


def matrix(protocol, dataset=None):
    rows = []
    for config_hash, config in sorted(protocol["configurations"].items()):
        for condition in protocol["conditions"]:
            for seed in protocol["seeds"]:
                available = condition == "original"
                rows.append(
                    {
                        "architecture": config["model_id"],
                        "configuration_hash": config_hash,
                        "configuration": deepcopy(config),
                        "initialization": config["resolved"]["model"]["weights"],
                        "preprocessing": config["resolved"]["input_contract"],
                        "augmentation": config["resolved"]["recipe"]["augmentation"],
                        "condition": condition,
                        "synthetic": deepcopy(protocol["conditions"][condition]),
                        "seed": seed,
                        "dataset": deepcopy(dataset),
                        "dataset_snapshot_hash": digest(dataset) if dataset else None,
                        "protocol_version": protocol["version"],
                        "protocol_hash": digest(protocol),
                        "budget": protocol["budget"],
                        "threshold_strategy": protocol["threshold"],
                        "state": "pending" if available and dataset else "planned",
                        "reason": None
                        if available and dataset
                        else (
                            "DATASET_NOT_ACCREDITED"
                            if available
                            else "SYNTHETIC_GENERATOR_NOT_AVAILABLE"
                        ),
                    }
                )
    return rows


def configuration_key(config):
    return digest(scientific_configuration(config))


def e6_protocol(protocol, selected_threshold):
    require(
        type(selected_threshold) in (float, int) and 0 <= selected_threshold <= 1,
        "THRESHOLD_INVALID",
    )
    return {
        "version": protocol["version"],
        "scientific_protocol_hash": digest(protocol),
        "splits": ["val", "test"],
        "purposes": ["development", "final"],
        "allowed_numeric_thresholds": [selected_threshold],
        "threshold_rule": protocol["threshold"]["rule"],
        "calibration": "none_raw_probability",
    }


def protocol_document(protocol):
    return "\n".join(
        [
            "# Protocolo científico E7",
            "",
            f"Versión: `{protocol['version']}`.",
            f"SHA-256 canónico de la configuración: `{digest(protocol)}`.",
            "",
            protocol["question"],
            "",
            *protocol["methodology"],
            "",
            "## Configuración canónica",
            "",
            "Los parámetros completos, configuraciones por arquitectura y semillas se fijan en `malaria_dl_local_project/configs/science/e7_v1.json`.",
            "La serialización de hash usa `campaigns.contracts.canonical` (UTF-8, claves ordenadas, números finitos).",
            "",
            "## Referencias metodológicas",
            "",
            *[f"- {s}" for s in protocol["references"]],
            "",
        ]
    )


def campaign_plan(protocol):
    """Explicit E4 request + protocol. Pure preparation, not campaign creation or execution.

    Re-resolved E2 identity must exactly equal the frozen E7 snapshots before use.
    """
    from ..campaigns.contracts import expand_matrix

    configurations = list(protocol["configurations"].values())
    by_model = {}
    for arch in protocol["architectures"]:
        c = next(c for c in configurations if c["model_id"] == arch)
        by_model[arch] = {
            k: deepcopy(c["resolved"][k]) for k in ("model", "execution", "recipe")
        }
    execution = configurations[0]["resolved"]["execution"]
    request = {
        "models": protocol["architectures"],
        "optimizers": sorted(
            {c["resolved"]["optimizer"]["name"] for c in configurations}
        ),
        "seeds": protocol["seeds"],
        "variants": [
            {"name": protocol["version"], "selected": {}, "by_model": by_model}
        ],
        "exclusions": [],
    }
    cp = {k: execution["checkpoint_" + k] for k in ("policy", "monitor", "mode")}
    cp["threshold"] = 0.5
    p = {
        "version": protocol["version"] + ":" + digest(protocol),
        "objective": "Sensitivity strictly > 0.98, then specificity; exploratory VAL",
        "metrics": {
            "primary": ["sensitivity", "specificity"],
            "secondary": ["f2", "roc_auc", "average_precision"],
            "definitions_version": protocol["version"],
            "compliance": "point_estimate",
        },
        "sensitivity_target": 0.98,
        "specificity_minimum": 0,
        "roles": {
            "train": "train",
            "selection": "val",
            "calibration": "val",
            "final_test": "test",
        },
        "ranking": {
            "partition": "val",
            "criteria": [protocol["selection"]["rule"]],
            "tie_breaks": ["configuration_hash asc"],
        },
        "checkpoint": cp,
        "early_stopping": {
            "enabled": execution["early_stopping"],
            **{
                k: execution["early_stopping_" + k]
                for k in ("monitor", "mode", "patience", "min_delta")
            },
            "restore_best_weights": execution["restore_best_weights"],
        },
        "calibration": {
            "algorithm": "none",
            "population": "val",
            "version": "E7 threshold selected later from exact VAL scores; no probability calibration",
        },
        "budget": {"max_members": 36, "max_attempts_per_member": 3},
        "missing": "report_all_members",
        "retries": "first_verified_attempt",
        "fallback": "diagnostic_only",
        "test_access": "final_only_after_candidate_lock",
        "aggregation": {
            "version": protocol["version"],
            "specification": "sample mean and ddof=1 SD between shared seeds; never pool predictions",
        },
        "uncertainty": {
            "version": protocol["version"],
            "specification": "patient bootstrap, 1000 replicates, 95% pointwise intervals",
        },
        "limitations": {
            "shared_val": "checkpoint and threshold selection and exploratory comparison reuse VAL",
            "independent_calibration": False,
            "test_exposure": "unknown",
        },
        "pending": [],
    }
    # This checks a pure planning contract; counts are not an accreditation of a dataset.
    expanded = expand_matrix(
        request,
        p,
        frozen=True,
        dataset={"counts": dict.fromkeys(("train", "val", "test"), 1)},
    )
    require(
        {h: v["configuration"] for h, v in expanded["configurations"].items()}
        == protocol["configurations"],
        "E2_DEFAULT_DRIFT_FROM_FROZEN_E7_PLAN",
    )
    return {
        "kind": "preparation_not_results",
        "protocol_hash": digest(protocol),
        "request": request,
        "campaign_protocol": p,
    }
