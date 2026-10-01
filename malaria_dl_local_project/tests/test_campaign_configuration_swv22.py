"""SWV2.2 campaign configuration contract: pure, no database, no TRAIN."""
from copy import deepcopy
from dataclasses import replace

import pytest

from src.malaria_dl.campaigns import configuration as cc
from src.malaria_dl.campaigns.contracts import digest, expand_matrix
from src.malaria_dl.models import registry
from src.malaria_dl.models.configuration import resolve_config
from src.malaria_dl.models.optimizers import BATCH_LEARNING_RATES, OPTIMIZER_DEFAULTS
from src.malaria_dl.science.protocol import campaign_plan, load_protocol

COUNTS = {"train": 22180, "val": 2693, "test": 2685}


@pytest.fixture(scope="module")
def catalog():
    return cc.catalog()


def preset(catalog, preset_id="system_batch_defaults"):
    return deepcopy(next(p for p in catalog["presets"] if p["id"] == preset_id)["configuration"])


def small(catalog):
    c = preset(catalog)
    c["models"] = ["custom_cnn", "vgg16"]
    c["optimizers"] = ["adam", "sgd"]
    c["seeds"] = [11, 29]
    for v in c["variants"]:
        v["parameters"].pop("densenet121")
    c["variants"][0]["parameters"]["custom_cnn"]["max_epochs"] = 50
    c["variants"][0]["parameters"]["vgg16"]["max_epochs"] = 30
    c["variants"][0]["parameters"]["vgg16"]["fine_tune_epochs"] = 5
    return c


def codes(result):
    return {(e["field"], e["code"]) for e in result["errors"]}


# --- discovery -----------------------------------------------------------------------------

def test_models_are_discovered_from_the_registry(catalog):
    assert [m["id"] for m in catalog["models"]] == list(registry.enabled_models())
    for m in catalog["models"]:
        d = registry.resolve_descriptor(m["id"])
        assert m["adapter_version"] == d.version and m["optimizers"] == list(d.optimizers)


def test_defaults_come_from_the_versioned_batch_profile(catalog):
    for m in catalog["models"]:
        resolved = resolve_config(m["id"], None, {"optimizer": {"name": m["optimizers"][0]}}, batch=True)["resolved"]
        for p in m["parameters"]:
            section, key = p["path"].split(".")
            expected = resolved[section][key]
            assert p["default"] == (expected[0] if p["key"] == "input_size" else expected), (m["id"], p["key"])


def test_architecture_specific_editability_follows_the_resolver(catalog):
    by = {m["id"]: {p["key"]: p for p in m["parameters"]} for m in catalog["models"]}
    assert by["custom_cnn"]["l2"]["editable"] and not by["vgg16"]["l2"]["editable"]
    assert not by["custom_cnn"]["fine_tune_epochs"]["editable"] and by["densenet121"]["fine_tune_epochs"]["editable"]
    assert by["custom_cnn"]["weights"]["choices"] == ["none"] and by["vgg16"]["weights"]["choices"] == ["none", "imagenet"]
    assert by["vgg16"]["fine_tune_layers"]["maximum"] == 4
    for m in by.values():
        assert not m["head_units"]["editable"] and not m["batch_normalization"]["editable"]


def test_optimizers_are_the_closed_domain_of_the_factory(catalog):
    assert [o["id"] for o in catalog["optimizers"]] == list(OPTIMIZER_DEFAULTS) == ["adam", "adamw", "sgd", "adadelta"]
    for o in catalog["optimizers"]:
        assert (o["learning_rate"], o["fine_tune_learning_rate"]) == BATCH_LEARNING_RATES[o["id"]]


def test_early_stopping_contract_exposes_its_real_parameters(catalog):
    keys = [p["key"] for p in catalog["protocol"]["editable"]]
    assert keys == ["early_stopping.enabled", "early_stopping.patience", "early_stopping.min_delta",
                    "early_stopping.restore_best_weights", "budget.max_attempts_per_member"]
    _request, protocol = cc.protocol_template()
    assert catalog["protocol"]["fixed"]["early_stopping.monitor"] == protocol["early_stopping"]["monitor"]
    assert catalog["protocol"]["fixed"]["sensitivity_target"] == load_protocol()["objective"]["value"]


def test_new_registered_descriptor_needs_no_campaign_change(catalog):
    base = registry.MODEL_REGISTRY["custom_cnn"]
    registry.register(replace(base, id="swv22_probe", aliases=()))
    try:
        extended = cc.catalog()
        assert [m["id"] for m in extended["models"]][-1] == "swv22_probe"
        result = cc.resolve(preset(extended), COUNTS)
        assert result["valid"]
        assert result["summary"]["total_experiments"] == 4 * 4 * 1 * 3
    finally:
        registry.MODEL_REGISTRY.pop("swv22_probe")


# --- presets and canonical equivalence ----------------------------------------------------

def test_approved_plan_preset_reproduces_frozen_e7_configurations(catalog):
    result = cc.resolve(preset(catalog, "capstone_science_e7_v1"), COUNTS)
    assert result["valid"]
    p = load_protocol()
    assert set(result["matrix"]["configurations"]) == set(p["configurations"])
    assert result["protocol"] == campaign_plan(p)["campaign_protocol"]
    assert result["summary"]["total_experiments"] == 36


def test_system_defaults_preset_is_valid_and_explicit(catalog):
    result = cc.resolve(preset(catalog), COUNTS)
    assert result["valid"] and result["summary"]["configurations"] == 12
    for variant in result["request"]["variants"]:
        assert variant["selected"] == {} and set(variant["by_model"]) == set(result["request"]["models"])


# --- validation ----------------------------------------------------------------------------

def test_valid_parameters_are_accepted_and_preserved_per_model(catalog):
    result = cc.resolve(small(catalog), COUNTS)
    assert result["valid"], result["errors"]
    by_model = result["request"]["variants"][0]["by_model"]
    assert by_model["custom_cnn"]["execution"]["max_epochs"] == 50
    assert by_model["vgg16"]["execution"]["max_epochs"] == 30
    for item in result["matrix"]["configurations"].values():
        c = item["configuration"]
        expected = {"custom_cnn": 50, "vgg16": 30}[c["model_id"]]
        assert c["resolved"]["execution"]["max_epochs"] == expected
        if c["model_id"] == "vgg16":
            assert c["resolved"]["execution"]["fine_tune_epochs"] == 5


@pytest.mark.parametrize("mutate,expected", [
    (lambda c: c["variants"][0]["parameters"]["custom_cnn"].update(max_epochs=0),
     ("variants[0].parameters.custom_cnn.max_epochs", "INVALID_PARAMETER_VALUE")),
    (lambda c: c["variants"][0]["parameters"]["custom_cnn"].update(max_epochs=1.5),
     ("variants[0].parameters.custom_cnn.max_epochs", "INVALID_PARAMETER_VALUE")),
    (lambda c: c["variants"][0]["parameters"]["custom_cnn"].update(dropout=1),
     ("variants[0].parameters.custom_cnn.dropout", "INVALID_PARAMETER_VALUE")),
    (lambda c: c["variants"][0]["parameters"]["vgg16"].update(l2=0.01),
     ("variants[0].parameters.vgg16.l2", "PARAMETER_NOT_EDITABLE")),
    (lambda c: c["variants"][0]["parameters"]["vgg16"].update(fine_tune_layers=5),
     ("variants[0].parameters.vgg16.fine_tune_layers", "INVALID_PARAMETER_VALUE")),
    (lambda c: c["variants"][0]["parameters"]["custom_cnn"].update(learning_rate=0.1),
     ("variants[0].parameters.custom_cnn.learning_rate", "UNKNOWN_PARAMETER")),
    (lambda c: c["variants"][0]["parameters"]["custom_cnn"].update(deterministic_ops="yes"),
     ("variants[0].parameters.custom_cnn.deterministic_ops", "INVALID_PARAMETER_VALUE")),
    (lambda c: c.update(optimizers=["adam", "rmsprop"]), ("optimizers", "UNKNOWN_OPTIMIZER:rmsprop")),
    (lambda c: c.update(optimizers=[]), ("optimizers", "REQUIRED_NON_EMPTY_LIST")),
    (lambda c: c.update(models=[]), ("models", "REQUIRED_NON_EMPTY_LIST")),
    (lambda c: c.update(models=["custom_cnn", "unet_hard_attention"]),
     ("models", "UNKNOWN_OR_NOT_EXECUTABLE_MODEL:unet_hard_attention")),
    (lambda c: c.update(seeds=[11, 11]), ("seeds", "DUPLICATE_ITEM")),
    (lambda c: c.update(seeds=[-1]), ("seeds", "INVALID_ITEM")),
    (lambda c: c.update(seeds=[2147483648]), ("seeds", "INVALID_ITEM")),
    (lambda c: c.update(extra=1), ("extra", "UNKNOWN_FIELD")),
    (lambda c: c["protocol"]["early_stopping"].update(patience=-1),
     ("protocol.early_stopping.patience", "INVALID_PARAMETER_VALUE")),
    (lambda c: c["protocol"]["early_stopping"].update(enabled=1),
     ("protocol.early_stopping.enabled", "INVALID_PARAMETER_VALUE")),
    (lambda c: c["protocol"]["early_stopping"].update(min_delta=-0.1),
     ("protocol.early_stopping.min_delta", "INVALID_PARAMETER_VALUE")),
    (lambda c: c["protocol"]["early_stopping"].update(monitor="val_loss"), ("protocol", "INVALID_PROTOCOL_FIELDS")),
    (lambda c: c["protocol"]["budget"].update(max_attempts_per_member=0),
     ("protocol.budget.max_attempts_per_member", "INVALID_PARAMETER_VALUE")),
])
def test_invalid_configurations_are_rejected_by_field(catalog, mutate, expected):
    c = small(catalog)
    mutate(c)
    result = cc.resolve(c, COUNTS)
    assert not result["valid"] and expected in codes(result)


def test_cross_field_rules_remain_the_resolver_authority(catalog):
    c = small(catalog)
    c["variants"][0]["parameters"]["vgg16"]["fine_tune_layers"] = 0  # fine_tune_epochs stays 5
    result = cc.resolve(c, COUNTS)
    assert not result["valid"] and ("", "INCOMPATIBLE_FINE_TUNING") in codes(result)


def test_duplicate_equivalent_variants_are_rejected(catalog):
    c = small(catalog)
    c["variants"].append(deepcopy(c["variants"][0]) | {"name": "copia"})
    result = cc.resolve(c, COUNTS)
    assert ("", "EQUIVALENT_VARIANTS_DUPLICATE_MEMBER") in codes(result)
    c["variants"][1]["name"] = c["variants"][0]["name"]
    assert ("variants[1].name", "DUPLICATE_VARIANT_NAME") in codes(cc.resolve(c, COUNTS))


# --- total of experiments ------------------------------------------------------------------

def test_total_is_expand_matrix_expected_count(catalog):
    c = small(catalog)
    second = deepcopy(c["variants"][0])
    second["name"] = "configuracion_2"
    second["parameters"]["custom_cnn"]["dropout"] = 0.3
    second["parameters"]["vgg16"]["dropout"] = 0.3
    c["variants"].append(second)
    result = cc.resolve(c, COUNTS)
    assert result["valid"]
    summary = result["summary"]
    assert summary["configurations"] == 2 * 2 * 2 == len(result["matrix"]["configurations"])
    assert summary["total_experiments"] == 2 * 2 * 2 * 2 == result["matrix"]["expected_count"]
    assert summary["total_experiments"] == len(result["matrix"]["members"])
    again = expand_matrix(result["request"], result["protocol"], frozen=True, dataset={"counts": COUNTS})
    assert again["expected_count"] == summary["total_experiments"]
    assert summary["experiments_per_model"] == {"custom_cnn": 8, "vgg16": 8}


def test_resolution_is_deterministic(catalog):
    a, b = cc.resolve(small(catalog), COUNTS), cc.resolve(small(catalog), COUNTS)
    assert digest(a["matrix"]) == digest(b["matrix"]) and a["protocol"] == b["protocol"]


# --- protocol ------------------------------------------------------------------------------

def test_budget_is_sized_to_the_matrix(catalog):
    result = cc.resolve(small(catalog), COUNTS)
    assert result["protocol"]["budget"]["max_members"] == result["summary"]["total_experiments"]


def test_derived_protocol_never_claims_the_approved_version(catalog):
    approved = cc.resolve(preset(catalog, "capstone_science_e7_v1"), COUNTS)["protocol"]["version"]
    c = preset(catalog, "capstone_science_e7_v1")
    c["protocol"]["early_stopping"]["patience"] = 5
    derived = cc.resolve(c, COUNTS)["protocol"]
    assert derived["early_stopping"]["patience"] == 5
    assert derived["version"] != approved and derived["version"].startswith(cc.CONFIGURATION_VERSION + ":")
    for item in cc.resolve(c, COUNTS)["matrix"]["configurations"].values():
        assert item["configuration"]["resolved"]["execution"]["early_stopping_patience"] == 5


def test_early_stopping_disabled_is_carried_to_every_configuration(catalog):
    c = small(catalog)
    c["protocol"]["early_stopping"]["enabled"] = False
    result = cc.resolve(c, COUNTS)
    assert result["valid"]
    assert all(i["configuration"]["resolved"]["execution"]["early_stopping"] is False
               for i in result["matrix"]["configurations"].values())


def test_clinical_target_respects_the_v2_domain(monkeypatch, catalog):
    request, protocol = cc.protocol_template()
    for invalid in (0, 1.01):
        bad = deepcopy(protocol)
        bad["sensitivity_target"] = invalid
        monkeypatch.setattr(cc, "protocol_template", lambda bad=bad: (request, bad))
        result = cc.resolve(small(catalog), COUNTS)
        assert ("", "SENSITIVITY_TARGET_OUTSIDE_V2_DOMAIN") in codes(result)


def test_test_split_is_never_used_for_training_or_selection(catalog):
    result = cc.resolve(small(catalog), COUNTS)
    assert result["protocol"]["test_access"] == "final_only_after_candidate_lock"
    assert result["protocol"]["roles"] == {"train": "train", "selection": "val", "calibration": "val",
                                           "final_test": "test"}
    assert all(i["configuration"]["resolved"]["execution"]["evaluate_best_on_test"] is False
               for i in result["matrix"]["configurations"].values())
