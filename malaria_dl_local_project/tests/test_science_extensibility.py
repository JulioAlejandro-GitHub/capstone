"""E7/E8 take their architectures from the protocol/campaign, not from a fixed Python list.

Synthetic protocols clone custom_cnn configurations under new names; no database writes
(the catalog is substituted in memory) and no TRAIN.
"""

import math
from copy import deepcopy
from pathlib import Path

import pytest

import test_science_e7
from src.malaria_dl.assessment.contracts import prediction, threshold, verify_rows
from src.malaria_dl.campaigns.contracts import digest
from src.malaria_dl.execution.artifacts import file_identity
from src.malaria_dl.models import registry
from src.malaria_dl.science import ensemble
from src.malaria_dl.science.ensemble import (
    TOLERANCE,
    configuration_event_id,
    evaluate,
    experimental_matrix,
    extension_contract,
    prepare,
    validate_evaluation,
    weights_for,
)
from src.malaria_dl.science.protocol import (
    ScienceError,
    campaign_plan,
    e6_protocol,
    load_protocol,
    validate_architectures,
)

E7 = load_protocol()


def protocol(*, add=(), drop=()):
    """E7 copy whose architectures differ; new ones reuse custom_cnn configurations."""
    p = deepcopy(E7)
    p["configurations"] = {
        k: c for k, c in p["configurations"].items() if c["model_id"] not in drop
    }
    p["architectures"] = [a for a in p["architectures"] if a not in drop]
    base = [c for c in E7["configurations"].values() if c["model_id"] == "custom_cnn"]
    for name in add:
        for c in deepcopy(base):
            c["model_id"] = name
            c["resolved"]["input_contract"]["architecture"] = name
            p["configurations"][digest(c)] = c
        p["architectures"].append(name)
    return p


def catalog(monkeypatch, *names):
    rows = tuple(
        {"name": n, "architecture": n, "model_type": "classification", "framework": "tensorflow/keras"}
        for n in names
    )
    monkeypatch.setattr(registry, "model_catalog", lambda: rows)


def ensemble_rows():
    return [r for r in experimental_matrix() if r["entity_type"] == "ensemble"]


def test_protocol_accepts_architectures_beyond_the_historical_three():
    validate_architectures(protocol(add=("model_four",)))
    validate_architectures(protocol(add=("model_four", "model_five")))
    broken = protocol(add=("model_four",))
    broken["architectures"].append("model_without_configuration")
    with pytest.raises(ScienceError, match="^ARCHITECTURES_REQUIRED$"):
        validate_architectures(broken)
    duplicated = protocol()
    duplicated["architectures"].append("vgg16")
    with pytest.raises(ScienceError, match="^ARCHITECTURES_REQUIRED$"):
        validate_architectures(duplicated)


def test_new_campaign_requires_registered_models_not_a_fixed_list(monkeypatch):
    four = protocol(add=("model_four",))
    catalog(monkeypatch, "custom_cnn", "densenet121", "vgg16")
    with pytest.raises(ScienceError, match="^ARCHITECTURE_NOT_REGISTERED$"):
        campaign_plan(four)
    # Once in the catalog, model_four is no longer rejected by name; the remaining
    # gate is the Python implementation, which this test deliberately does not add.
    catalog(monkeypatch, "custom_cnn", "densenet121", "model_four", "vgg16")
    with pytest.raises(ValueError, match="^IMPLEMENTATION_NOT_AVAILABLE:model_four$"):
        campaign_plan(four)


def test_catalog_is_not_the_experimental_selection(monkeypatch):
    # catalog A B C D E; experiment A C D; comparison A C D.
    catalog(monkeypatch, "custom_cnn", "densenet121", "model_five", "model_four", "vgg16")
    assert campaign_plan(E7)["request"]["models"] == E7["architectures"]
    selected = protocol(add=("model_four",), drop=("vgg16",))
    monkeypatch.setattr(ensemble, "load_protocol", lambda: selected)
    expected = ["custom_cnn", "densenet121", "model_four"]
    assert ensemble.architectures() == expected
    assert extension_contract()["architectures"] == expected
    assert all(r["architectures"] == expected for r in ensemble_rows())


@pytest.mark.parametrize("n", (3, 4))
def test_uniform_weights_are_one_over_n(n):
    ws = weights_for("uniform", [{}] * n)
    assert ws == [1 / n] * n and abs(math.fsum(ws) - 1) <= TOLERANCE


def test_matrix_and_contract_follow_protocol_size(monkeypatch):
    four = protocol(add=("model_four",))
    monkeypatch.setattr(ensemble, "load_protocol", lambda: four)
    rows = ensemble_rows()
    uniform = [r for r in rows if r["strategy"] == "uniform"]
    assert all(r["weights"] == [0.25] * 4 for r in uniform)
    assert extension_contract()["matrix_rows"] == len(experimental_matrix())
    # 16 configurations x 2 conditions x 3 seeds + 2 strategies x 4 optimizers x 3 seeds.
    assert len(experimental_matrix()) == 16 * 2 * 3 + 2 * 4 * 3


def test_four_member_ensemble_end_to_end(tmp_path, monkeypatch):
    four = protocol(add=("model_four",))
    monkeypatch.setattr(ensemble, "load_protocol", lambda: four)
    monkeypatch.setattr(test_science_e7, "load_protocol", lambda: four)
    members, shared = [], None
    for arch, scores in zip(
        ("custom_cnn", "vgg16", "densenet121", "model_four"),
        ((0.1, 0.9), (0.3, 0.7), (0.5, 0.6), (0.2, 0.8)),
    ):
        folder = tmp_path / arch
        folder.mkdir()
        e = test_science_e7.evidence(folder, architecture=arch)
        v = e["identity"]
        path = Path(v["model"]["path"])
        path.write_bytes(arch.encode())
        v["model"].update(file_identity(path))
        shared = shared or (deepcopy(v["samples"]), deepcopy(v["dataset"]))
        v["samples"], v["dataset"] = deepcopy(shared[0]), deepcopy(shared[1])
        v["protocol"] = e6_protocol(four, scores[1])
        v["decision"] = threshold(str(scores[1]), v["protocol"])
        e["rows"] = [prediction(s, scores[s["label"]], v["decision"]) for s in v["samples"]]
        e["proof"] = verify_rows(v, e["rows"])
        members.append(e)
    reader = lambda eid: next(e for e in members if e["evaluation_id"] == eid)
    request = {
        "ensemble_id": "8c6f1d47-3a5b-4f0e-9d2c-1b7e6a5f4c3d",
        "members": [{"evaluation_id": e["evaluation_id"]} for e in members],
    }
    config = prepare(request, reader, code={"fixture": True})
    body = config["configuration"]
    assert [m["architecture"] for m in body["members"]] == [
        "custom_cnn", "densenet121", "model_four", "vgg16"
    ]
    assert [m["weight"] for m in body["members"]] == [0.25] * 4
    result = evaluate(config, reader, configuration_id=configuration_event_id(config))
    validate_evaluation(result)
    by_label = {r["label"]: r["raw_score"] for r in result["rows"]}
    assert by_label[0] == pytest.approx((0.1 + 0.3 + 0.5 + 0.2) / 4)
    assert by_label[1] == pytest.approx((0.9 + 0.7 + 0.6 + 0.8) / 4)
    assert len(result["member_comparisons"]) == 4
    # Dropping one member of the protocol's group is still rejected: no subset fallback.
    request["members"].pop()
    with pytest.raises(ScienceError, match="^ENSEMBLE_ARCHITECTURE_GROUP_INVALID$"):
        prepare(request, reader, code={"fixture": True})
