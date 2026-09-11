"""Controlled E8 probabilities, never operational inference or weight search."""

import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest
from src.malaria_dl.assessment.contracts import prediction, threshold, verify_rows
from src.malaria_dl.campaigns.contracts import digest
from src.malaria_dl.execution.artifacts import file_identity
from src.malaria_dl.science.ensemble import (
    combine,
    configuration_event_id,
    evaluate,
    experimental_matrix,
    prepare,
    validate_configuration,
    validate_evaluation,
    weights_for,
)
from src.malaria_dl.science.ensemble_reporting import compare_results, export
from src.malaria_dl.science.protocol import ScienceError, e6_protocol, load_protocol
from src.malaria_dl.science.statistics import threshold_selection
from test_science_e7 import evidence


def members(tmp_path):
    result = []
    shared = None
    for arch, scores in zip(
        ("custom_cnn", "vgg16", "densenet121"), ((0.1, 0.9), (0.3, 0.7), (0.5, 0.6))
    ):
        folder = tmp_path / arch
        folder.mkdir(parents=True, exist_ok=True)
        e = evidence(folder, architecture=arch)
        v = e["identity"]
        path = Path(v["model"]["path"])
        path.write_bytes(arch.encode())
        v["model"].update(file_identity(path))
        if shared is None:
            shared = (deepcopy(v["samples"]), deepcopy(v["dataset"]))
        v["samples"] = deepcopy(shared[0])
        v["dataset"] = deepcopy(shared[1])
        selected = scores[1]
        v["protocol"] = e6_protocol(load_protocol(), selected)
        v["decision"] = threshold(str(selected), v["protocol"])
        e["rows"] = [
            prediction(s, scores[s["label"]], v["decision"]) for s in v["samples"]
        ]
        e["proof"] = verify_rows(v, e["rows"])
        result.append(e)
    return result


def request(es, strategy="uniform", weights=None):
    return {
        "ensemble_id": str(uuid4()),
        "strategy": strategy,
        "members": [
            {
                "evaluation_id": e["evaluation_id"],
                **({"weight": w} if strategy == "weighted" else {}),
            }
            for e, w in zip(es, weights or [1 / 3] * 3)
        ],
        "weight_provenance": {"kind": "uniform_no_fit"}
        if strategy == "uniform"
        else {"kind": "predeclared", "reference": "synthetic fixture specification"},
    }


def ready(tmp_path, strategy="uniform"):
    es = members(tmp_path)
    req = request(es, strategy, [0.2, 0.3, 0.5])
    reader = lambda eid: next(e for e in es if e["evaluation_id"] == eid)
    config = prepare(req, reader, code={"fixture": True})
    result = evaluate(config, reader, configuration_id=configuration_event_id(config))
    return es, req, config, result, reader


def test_uniform_weighted_known_values_and_reports(tmp_path):
    es, _req, c, r, reader = ready(tmp_path)
    by_label = {v["label"]: v for v in r["rows"]}
    assert by_label[0]["raw_score"] == pytest.approx(0.3) and by_label[1][
        "raw_score"
    ] == pytest.approx(2.2 / 3)
    assert r["metrics"]["sensitivity"] == 1 and r["baseline"]["specificity"] == 0
    assert r["uncertainty"]["reason"] == "INSUFFICIENT_PATIENT_CLUSTERS"
    assert (
        len(r["member_comparisons"]) == 3
        and r["individual_reference"]["selection_partition"] == "val"
    )
    validate_evaluation(r)
    weighted = prepare(
        request(es, "weighted", [0.2, 0.3, 0.5]), reader, code={"fixture": True}
    )
    out = evaluate(weighted, reader, configuration_id=configuration_event_id(weighted))
    scores = {x["label"]: x["raw_score"] for x in out["rows"]}
    assert scores[0] == pytest.approx(0.36) and scores[1] == pytest.approx(0.69)
    assert weighted["revision"] != c["revision"]


@pytest.mark.parametrize(
    "weights",
    [
        [1, 0, 0],
        [0.5, 0.5, -0.1],
        [0.3, 0.3, 0.3],
        [float("nan"), 0.5, 0.5],
        [float("inf"), 0, 1],
        [True, 0, 0],
        [None, 0.5, 0.5],
    ],
)
def test_weights_reject_without_normalizing(weights):
    with pytest.raises(ScienceError):
        weights_for("weighted", [{"weight": w} for w in weights])


def test_reordered_rows_and_members_preserve_identity(tmp_path):
    es, req, c, r, reader = ready(tmp_path)
    for e in es:
        e["rows"].reverse()
    req["members"].reverse()
    assert prepare(req, reader, code={"fixture": True}) == c
    assert evaluate(c, reader, configuration_id=configuration_event_id(c)) == r
    minimal = {"ensemble_id": req["ensemble_id"], "members": req["members"]}
    assert prepare(minimal, reader, code={"fixture": True}) == c


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "duplicate",
        "label",
        "patient",
        "nan",
        "negative",
        "above_one",
        "mapping",
        "checkpoint",
        "dataset",
        "split",
        "calibrator",
        "post_calibrator",
        "seed",
    ],
)
def test_reject_incompatible_member(tmp_path, change):
    es = members(tmp_path)
    e = es[1]
    if change == "missing":
        e["rows"].pop()
    if change == "duplicate":
        e["rows"] = [e["rows"][0]] * 2
    if change == "label":
        e["rows"][0]["label"] = 1 - e["rows"][0]["label"]
    if change == "patient":
        e["identity"]["samples"][0]["patient_id"] = str(uuid4())
    if change in ("nan", "negative", "above_one"):
        e["rows"][0]["raw_score"] = {
            "nan": float("nan"),
            "negative": -0.1,
            "above_one": 1.1,
        }[change]
    if change == "mapping":
        e["identity"]["model"]["input_contract"]["label_mapping"]["positive_class"] = 0
    if change == "checkpoint":
        e["identity"]["model"]["sha256"] = es[0]["identity"]["model"]["sha256"]
    if change == "dataset":
        e["identity"]["dataset"]["dataset_version_id"] = str(uuid4())
    if change == "split":
        e["identity"]["split"] = "test"
    if change == "calibrator":
        e["identity"]["decision"]["calibrator"] = {"id": "unverified"}
    if change == "post_calibrator":
        e["rows"][0]["calibrated_score"] = 0.2
    if change == "seed":
        e["configuration"]["resolved"]["execution"]["seed"] = 29
    with pytest.raises(ValueError):
        combine(es, [1 / 3] * 3, 0.5)


def test_missing_failure_does_not_drop_member(tmp_path):
    es = members(tmp_path)
    req = request(es)
    calls = []

    def bad(eid):
        calls.append(eid)
        if eid == es[1]["evaluation_id"]:
            raise ValueError("MEMBER_UNAVAILABLE")
        return es[0]

    with pytest.raises(ValueError, match="MEMBER_UNAVAILABLE"):
        prepare(req, bad, code={})
    assert len(calls) == 2
    req["members"][1]["evaluation_id"] = req["members"][0]["evaluation_id"]
    with pytest.raises(ScienceError, match="DUPLICATE_MEMBER"):
        prepare(req, bad, code={})


def test_provenance_and_threshold_revision(tmp_path):
    _es, req, c, r, reader = ready(tmp_path, "weighted")
    req["weight_provenance"] = {"kind": "test_optimized", "reference": "forbidden"}
    with pytest.raises(ScienceError, match="PREDECLARED"):
        prepare(req, reader, code={})
    bad = deepcopy(c)
    bad["configuration"]["decision"]["effective"] = 0.25
    with pytest.raises(ScienceError, match="REVISION"):
        validate_configuration(bad)
    bad["revision"] = digest(bad["configuration"])
    with pytest.raises(ScienceError, match="PROVENANCE"):
        validate_configuration(bad)
    with pytest.raises(ScienceError, match="VAL_ONLY"):
        threshold_selection(r["rows"], split="test")


def test_comparator_exclusions_and_export(tmp_path):
    _es, _req, _c, r, _reader = ready(tmp_path)
    eid = str(uuid4())
    missing = str(uuid4())

    def lookup(i):
        if i == missing:
            raise ValueError("MEMBER_UNAVAILABLE")
        return r

    report = compare_results([eid, missing], lookup)
    assert (
        len(report["items"]) == 1
        and report["exclusions"][0]["reason"] == "MEMBER_UNAVAILABLE"
    )
    assert report["seed_summaries"][0]["missing_seeds"] == [29, 47]

    class Stored:
        def read_report(self, _):
            return report

    assert export(Stored(), str(uuid4()), tmp_path / "export") == digest(report)
    assert not list((tmp_path / "export").glob("*.csv"))
    assert json.loads((tmp_path / "export/report.json").read_text()) == report
    assert (tmp_path / "export/curves.png").exists()
    empty = compare_results([], lookup)
    assert empty["state"] == "preparation_missing_evidence" and not empty["items"]
    assert len(experimental_matrix()) == 96


def test_no_seed_ensemble_or_repeated_configuration_rank(tmp_path):
    es, req, _c, r, reader = ready(tmp_path)
    es[1]["configuration"]["model_id"] = "custom_cnn"
    with pytest.raises(ValueError):
        prepare(req, reader, code={})
    report = compare_results([str(uuid4()), str(uuid4())], lambda _: r)
    assert not report["items"] and len(report["exclusions"]) == 2


def test_legacy_main_routes_to_governed_cli(monkeypatch):
    from src.malaria_dl.inference import ensemble
    from src.malaria_dl.science import ensemble_cli

    calls = []
    monkeypatch.setattr(ensemble_cli, "main", lambda argv: calls.append(argv) or 0)
    assert ensemble.main(["compare"]) == 0 and calls == [["compare"]]


def test_error_corrections_introductions_and_descriptive_disagreement(tmp_path):
    es = members(tmp_path)
    samples = []
    for i in range(4):
        s = deepcopy(es[0]["identity"]["samples"][0])
        s.update(
            sample_id=str(uuid4()),
            patient_id=str(uuid4()),
            label=int(i >= 2),
            relative_path=f"val/{i}.png",
        )
        samples.append(s)
    samples.sort(key=lambda s: s["sample_id"])
    score_sets = ((0.7, 0.1, 0.8, 0.6), (0.1, 0.7, 0.6, 0.8), (0.1, 0.1, 0.8, 0.8))
    # Assign the two negative/positive scores by class, independently of UUID order.
    for e, ss in zip(es, score_sets):
        v = e["identity"]
        v["samples"] = deepcopy(samples)
        t = min(ss[2:])
        v["protocol"] = e6_protocol(load_protocol(), t)
        v["decision"] = threshold(str(t), v["protocol"])
        order = sorted(samples, key=lambda s: (s["label"], s["sample_id"]))
        e["rows"] = [prediction(s, score, v["decision"]) for s, score in zip(order, ss)]
        e["proof"] = verify_rows(v, e["rows"])
    reader = lambda eid: next(e for e in es if e["evaluation_id"] == eid)
    c = prepare(
        request(es, "weighted", [0.9, 0.05, 0.05]), reader, code={"fixture": True}
    )
    r = evaluate(c, reader, configuration_id=configuration_event_id(c))
    assert any(x["introduced_sample_ids"] for x in r["member_comparisons"])
    assert any(x["corrected_sample_ids"] for x in r["member_comparisons"])
    assert any(x["member_decisions_disagree"] for x in r["disagreement"])


def test_roundoff_is_explicit_not_weight_normalization(tmp_path):
    es = members(tmp_path)
    for e in es:
        v = e["identity"]
        v["protocol"] = e6_protocol(load_protocol(), 1.0)
        v["decision"] = threshold("1.0", v["protocol"])
        e["rows"] = [prediction(s, 1.0, v["decision"]) for s in v["samples"]]
        e["proof"] = verify_rows(v, e["rows"])
    rs = combine(es, [0.5, 0.5, 1e-13], 1.0)
    assert rs[0]["raw_score"] == 1.0 and rs[0]["combination_sum"] > 1.0
    assert rs[0]["contributions"][2]["weight"] == 1e-13


def test_read_verified_rejects_changed_e6_source(tmp_path, monkeypatch):
    from src.malaria_dl.science import comparison
    from src.malaria_dl.science.ensemble_repository import EvaluationRepository

    _es, _req, _c, result, reader = ready(tmp_path)
    repo = EvaluationRepository()
    monkeypatch.setattr(repo, "read_report", lambda _: result)
    monkeypatch.setattr(comparison, "read_evaluation", lambda _repo, eid: reader(eid))
    assert repo.read_verified(str(uuid4())) == result

    def missing(*args):
        raise ScienceError("CHECKPOINT_CONTENT_CHANGED")

    monkeypatch.setattr(comparison, "read_evaluation", missing)
    with pytest.raises(ScienceError, match="CHECKPOINT_CONTENT_CHANGED"):
        repo.read_verified(str(uuid4()))


def test_shared_repetitions_aggregate_without_pooling(tmp_path):
    es = members(tmp_path)
    request_value = request(es)
    lookup = {}
    outputs = {}
    for seed in (11, 29, 47):
        current = deepcopy(es)
        for e in current:
            e["configuration"]["resolved"]["execution"]["seed"] = seed
            e["identity"]["seed"] = seed
            e["evaluation_id"] = str(uuid4())
            e["identity"]["model"]["training_run_id"] = str(uuid4())
            lookup[e["evaluation_id"]] = e
        req = {
            **request_value,
            "members": [{"evaluation_id": e["evaluation_id"]} for e in current],
        }
        c = prepare(req, lookup.__getitem__, code={"fixture": True})
        outputs[str(uuid4())] = evaluate(
            c, lookup.__getitem__, configuration_id=configuration_event_id(c)
        )
    report = compare_results(list(outputs), outputs.__getitem__)
    assert len(report["seed_summaries"]) == 1
    summary = report["seed_summaries"][0]
    assert (
        summary["seeds"] == [11, 29, 47]
        and summary["metrics"]["f2"]["n"] == 3
        and not summary["missing_seeds"]
    )
    assert len(report["items"]) == 3 and all(
        len(i["result"]["rows"]) == 2 for i in report["items"]
    )
    assert (
        sum(r["state"] == "evaluated_explicit_references" for r in report["matrix"])
        == 12
    )


def test_versioned_plan_matches_machine_artifacts():
    from src.malaria_dl.science.ensemble import extension_contract

    root = Path(__file__).resolve().parents[2]
    spec = json.loads(
        (root / "malaria_dl_local_project/configs/science/e8_v1.json").read_text()
    )
    assert spec == extension_contract()
    plan = json.loads((root / "docs/science/matriz_e8_v1.json").read_text())
    assert (
        plan["extension_hash"] == digest(spec)
        and plan["matrix"] == experimental_matrix()
    )


def test_cli_validation_and_legacy_test_flags_rejected(tmp_path, capsys):
    from src.malaria_dl.science.ensemble_cli import main

    _es, _req, config, _result, _reader = ready(tmp_path)
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    assert main(["validate", "--configuration", str(path)]) == 0
    assert "structure_and_hash_only" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main(["--models", "old.keras"])


def test_cli_failure_audited_without_output_fallback(tmp_path, monkeypatch, capsys):
    from src.malaria_dl.science import ensemble_cli

    es = members(tmp_path)
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request(es)))
    recorded = []

    class Configs:
        pass

    class Audit:
        def persist_report(self, payload):
            recorded.append(payload)

    def unavailable(*args):
        raise RuntimeError("driver secret URL not allowed")

    monkeypatch.setattr(ensemble_cli, "ConfigurationRepository", Configs)
    monkeypatch.setattr(ensemble_cli, "FailureRepository", Audit)
    monkeypatch.setattr(ensemble_cli, "read_evaluation", unavailable)
    monkeypatch.setattr(ensemble_cli, "provenance", lambda: {"fixture": True})
    assert ensemble_cli.main(["prepare", "--request", str(path)]) == 2
    output = capsys.readouterr().out
    assert "secret" not in output and recorded[0]["state"] == "failed"
    assert recorded[0]["reason"] == "EVIDENCE_UNVERIFIED"
    assert not list(tmp_path.glob("*.csv"))
