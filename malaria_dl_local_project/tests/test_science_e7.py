"""Controlled methodology fixtures; never clinical inference or operational data."""

import json
from copy import deepcopy
from uuid import uuid4

import pytest
from src.malaria_dl.assessment.contracts import prediction, threshold, verify_rows
from src.malaria_dl.assessment.service import run
from src.malaria_dl.campaigns.contracts import digest, member_configuration
from src.malaria_dl.science import comparison
from src.malaria_dl.science.comparison import (
    classify,
    compare,
    read_evaluation,
    select_candidate,
)
from src.malaria_dl.science.protocol import (
    ScienceError,
    e6_protocol,
    load_protocol,
    matrix,
    protocol_document,
)
from src.malaria_dl.science.reporting import export_report, markdown
from src.malaria_dl.science.repository import validate_report
from src.malaria_dl.science.statistics import (
    cluster_interval,
    curves,
    metrics,
    seed_summary,
    threshold_selection,
)
from test_assessment_e6 import MemoryRepository, Runtime, value


def rows(labels=(0, 0, 1, 1), scores=(0.1, 0.7, 0.4, 0.9), patients=None):
    return [
        {
            "sample_id": str(i),
            "patient_id": patients[i] if patients else f"p{i // 2}",
            "label": y,
            "raw_score": float(s),
            "predicted": int(s >= 0.5),
        }
        for i, (y, s) in enumerate(zip(labels, scores))
    ]


def evidence(tmp_path, *, architecture="custom_cnn", seed=11):
    p = load_protocol()
    config = next(
        c for c in p["configurations"].values() if c["model_id"] == architecture
    )
    v = value(tmp_path)
    v["model"]["input_contract"] = config["resolved"]["input_contract"]
    v["seed"] = seed
    v["protocol"] = e6_protocol(p, 0.8)
    v["decision"] = threshold(".8", v["protocol"])
    rs = [
        prediction(s, 0.8 if s["label"] else 0.2, v["decision"]) for s in v["samples"]
    ]
    return {
        "evaluation_id": str(uuid4()),
        "identity": v,
        "proof": verify_rows(v, rs),
        "rows": rs,
        "configuration": member_configuration(config, seed),
        "training_environment": {"source": "synthetic"},
        "explanations": [],
    }


def test_protocol_document_and_full_matrix():
    from pathlib import Path

    p = load_protocol()
    root = Path(__file__).resolve().parents[2]
    assert (root / "docs/science/protocolo_e7_v1.md").read_text() == protocol_document(
        p
    )
    m = matrix(p)
    assert len(m) == 72 and sum(r["condition"] == "original" for r in m) == 36
    assert {r["seed"] for r in m} == {11, 29, 47}
    assert all(r["dataset"] is None and r["state"] == "planned" for r in m)
    assert all(
        r["configuration"]["resolved"]["execution"]["evaluate_best_on_test"] is False
        for r in m
    )
    checked = json.loads((root / "docs/science/matriz_e7_v1.json").read_text())
    assert checked["matrix"] == m and checked["protocol_hash"] == digest(p)


def test_frozen_protocol_change_rejected(tmp_path):
    p = load_protocol()
    p["objective"]["operator"] = ">="
    f = tmp_path / "changed.json"
    f.write_text(json.dumps(p))
    with pytest.raises(ScienceError, match="FROZEN_PROTOCOL"):
        load_protocol(f)


def test_positive_metrics_and_confusion():
    m = metrics(rows())
    assert m["confusion"] == [[1, 1], [1, 1]] and m["support"] == {
        "uninfected": 2,
        "parasitized": 2,
    }
    for n in (
        "sensitivity",
        "specificity",
        "precision",
        "f1",
        "f2",
        "balanced_accuracy",
    ):
        assert m[n] == 0.5
    assert m["roc_auc"] == 0.75 and m["average_precision"] == pytest.approx(5 / 6)
    assert m["prevalence"] == 0.5 and not m["undefined"]
    assert curves(rows())["roc"]["thresholds"][0] is None


@pytest.mark.parametrize(
    "labels,scores,missing",
    [
        ((0, 0), (0.1, 0.2), "sensitivity"),
        ((1, 1), (0.1, 0.2), "specificity"),
        ((0, 1), (0.1, 0.2), "precision"),
    ],
)
def test_undefined_is_absent_with_reason(labels, scores, missing):
    m = metrics(rows(labels, scores))
    assert m[missing] is None and m["undefined"][missing]
    if len(set(labels)) == 1:
        assert curves(rows(labels, scores))["roc"] is None


def test_strict_threshold_098_not_success_and_stable_ties():
    rs = rows((1,) * 50 + (0,) * 2, (0.9,) * 49 + (0.1, 0.05, 0.15))
    selected = threshold_selection(rs, split="val")
    assert (
        selected["threshold"] == 0.1
        and selected["sensitivity"] == 1
        and selected["specificity"] == 0.5
    )
    assert selected == threshold_selection(list(reversed(rs)), split="val")
    with pytest.raises(ScienceError, match="VAL_ONLY"):
        threshold_selection(rs, split="test")
    missing = threshold_selection(rows((0, 0), (0.1, 0.2)), split="val")
    assert missing["threshold"] is None and missing["objective_met"] is False


def test_baseline_is_tradeoff():
    m = metrics(rows((0, 1), (1, 1)))
    assert m["sensitivity"] == 1 and m["specificity"] == 0


def test_patient_bootstrap_reproducible_and_paired():
    rs = rows(
        tuple([0, 1] * 20),
        tuple([0.2, 0.8] * 20),
        patients=[f"p{i // 2}" for i in range(40)],
    )
    spec = {**load_protocol()["uncertainty"], "replicates": 30}
    a = cluster_interval(rs, spec)
    assert a == cluster_interval(list(reversed(rs)), spec) and a["patients"] == 20
    b = cluster_interval(rs, spec, rs)
    assert all(v["low"] == v["high"] == 0 for v in b["intervals"].values())
    modified = deepcopy(rs)
    modified[0]["patient_id"] = "alien"
    with pytest.raises(ScienceError, match="PAIRED_POPULATION"):
        cluster_interval(rs, spec, modified)
    modified[0]["patient_id"] = None
    assert cluster_interval(modified, spec)["reason"] == "PATIENT_GROUPING_UNAVAILABLE"
    assert cluster_interval(rows(), spec)["reason"] == "INSUFFICIENT_PATIENT_CLUSTERS"


def test_seed_variability_not_pooled():
    m = metrics(rows())
    other = {**m, "sensitivity": 1.0}
    s = seed_summary([{"seed": 11, "metrics": m}, {"seed": 29, "metrics": other}])
    assert s["sensitivity"]["mean"] == 0.75 and s["sensitivity"]["sd"] == pytest.approx(
        0.35355339
    )
    with pytest.raises(ScienceError, match="AMBIGUOUS_SEED"):
        seed_summary([{"seed": 11, "metrics": m}] * 2)


def test_compare_lineage_protocol_and_empty_report(tmp_path):
    p = load_protocol()
    e = evidence(tmp_path)
    refs = [{"evaluation_id": e["evaluation_id"]}]
    report = compare(
        p,
        e["identity"]["dataset"],
        "val",
        refs,
        lambda *_: e,
        provenance={"synthetic": True},
    )
    validate_report(report)
    assert (
        report["items"][0]["method_compatible"]
        and report["items"][0]["status"] == "exploratory"
    )
    assert report["selection"]["candidate"] is None and "rows" not in report["items"][0]
    assert report["items"][0]["lineage"]["prediction_reference"]["proof"] == e["proof"]
    assert e["evaluation_id"] in markdown(report)
    report = compare(
        p, e["identity"]["dataset"], "val", [], lambda *_: pytest.fail(), provenance={}
    )
    assert not report["items"] and report["state"] == "preparation_missing_evidence"
    assert report["selection"]["candidate"] is None


@pytest.mark.parametrize(
    "change,reason",
    [
        ("split", "SPLIT_CONFLICT"),
        ("dataset", "DATASET_SNAPSHOT_CONFLICT"),
        ("threshold", "THRESHOLD_PROVENANCE_REQUIRED"),
    ],
)
def test_incompatible_evidence_excluded(tmp_path, change, reason):
    p = load_protocol()
    e = evidence(tmp_path)
    ds = deepcopy(e["identity"]["dataset"])
    if change == "split":
        e["identity"]["split"] = "test"
    if change == "dataset":
        e["identity"]["dataset"]["dataset_version_id"] = str(uuid4())
    if change == "threshold":
        e["identity"]["decision"]["source"] = {}
    result = compare(
        p,
        ds,
        "val",
        [{"evaluation_id": e["evaluation_id"]}],
        lambda *_: e,
        provenance={},
    )
    assert not result["items"] and result["exclusions"][0]["reason"] == reason


def test_historical_protocol_exploratory_not_relabelled(tmp_path):
    p = load_protocol()
    e = evidence(tmp_path)
    e["identity"]["protocol"]["scientific_protocol_hash"] = "a" * 64
    x = classify(e, p, e["identity"]["dataset"], "val")
    assert (
        not x["method_compatible"]
        and "HISTORICAL_PROTOCOL_DIFFERENT" in x["limitations"]
    )
    e["identity"]["decision"]["effective"] = 0.5
    x = classify(e, p, e["identity"]["dataset"], "val")
    assert (
        x["threshold_proposal_val_only"]["threshold"] == 0.8
        and x["lineage"]["identity"]["decision"]["effective"] == 0.5
    )


def test_ambiguity_and_incomplete_exclusion(tmp_path):
    p = load_protocol()
    e = evidence(tmp_path)
    other = deepcopy(e)
    other["evaluation_id"] = str(uuid4())
    lookup = {x["evaluation_id"]: x for x in [e, other]}
    report = compare(
        p,
        e["identity"]["dataset"],
        "val",
        [{"evaluation_id": i} for i in lookup],
        lambda i, *_: lookup[i],
        provenance={},
    )
    assert len(report["exclusions"]) == 2 and not report["items"]
    with pytest.raises(ScienceError, match="UNIQUE_EVALUATIONS"):
        compare(
            p,
            {},
            "val",
            [{"evaluation_id": e["evaluation_id"]}] * 2,
            lambda *_: e,
            provenance={},
        )

    def failed(*a):
        raise RuntimeError("secret driver URL")

    r = compare(
        p, {}, "val", [{"evaluation_id": e["evaluation_id"]}], failed, provenance={}
    )
    assert r["exclusions"][0][
        "reason"
    ] == "EVIDENCE_UNVERIFIED" and "secret" not in json.dumps(r)


def test_candidate_complete_matrix_deterministic_and_unmet(tmp_path):
    p = load_protocol()
    e = evidence(tmp_path)
    base = classify(e, p, e["identity"]["dataset"], "val")
    items = []
    for key in p["configurations"]:
        for seed in p["seeds"]:
            r = deepcopy(base)
            r.update(configuration_hash=key, seed=seed, evaluation_id=str(uuid4()))
            items.append(r)
    selected = select_candidate(items, p, "val")
    assert selected["candidate"]["configuration_hash"] == min(p["configurations"])
    assert selected == select_candidate(list(reversed(items)), p, "val")
    assert selected["candidate"]["representative_seed"] == 11
    for r in items:
        r["metrics"]["sensitivity"] = 0.98
    fail = select_candidate(items, p, "val")
    assert (
        not fail["objective_met_all_seeds"]
        and "OBJECTIVE_NOT_REACHED" in fail["reason"]
    )
    assert select_candidate(items, p, "test")["candidate"] is None
    assert select_candidate(items[:-1], p, "val")["candidate"] is None


def test_export_never_falls_back_on_database_failure(tmp_path):
    class Bad:
        def read_report(self, _):
            raise RuntimeError("unavailable")

    with pytest.raises(RuntimeError):
        export_report(Bad(), str(uuid4()), tmp_path / "export")
    assert not (tmp_path / "export").exists()


def test_exact_e6_reader_revalidates_and_rejects_inconsistency(tmp_path, monkeypatch):
    repo = MemoryRepository()
    v = value(tmp_path)
    v["model"]["source"] = {"kind": "legacy_registered_artifact"}
    a = run(repo, v, tmp_path, Runtime)
    monkeypatch.setattr(
        comparison.lineage, "resolve", lambda *args: (v["model"], v["dataset"], None)
    )
    monkeypatch.setattr(
        comparison.lineage, "dataset_samples", lambda *args, **kw: v["samples"]
    )
    e = read_evaluation(repo, a["id"], [])
    assert e["configuration"] is None and e["proof"] == a["verification"]
    changed = deepcopy(v["model"])
    changed["sha256"] = "b" * 64
    monkeypatch.setattr(
        comparison.lineage, "resolve", lambda *args: (changed, v["dataset"], None)
    )
    with pytest.raises(ScienceError, match="TRAIN_LINEAGE"):
        read_evaluation(repo, a["id"], [])


def test_e4_plan_reconstructs_exact_frozen_configurations():
    from src.malaria_dl.campaigns.contracts import expand_matrix
    from src.malaria_dl.science.protocol import campaign_plan

    p = load_protocol()
    plan = campaign_plan(p)
    expanded = expand_matrix(
        plan["request"],
        plan["campaign_protocol"],
        frozen=True,
        dataset={"counts": dict.fromkeys(("train", "val", "test"), 2)},
    )
    assert (
        set(expanded["configurations"]) == set(p["configurations"])
        and len(expanded["members"]) == 36
    )


def test_report_artifact_protocol_and_metrics_correspondence(tmp_path):
    p = load_protocol()
    e = evidence(tmp_path)
    report = compare(
        p,
        e["identity"]["dataset"],
        "val",
        [{"evaluation_id": e["evaluation_id"]}],
        lambda *_: e,
        provenance={},
    )
    validate_report(report)
    for field in ("hash", "metrics", "selection"):
        bad = deepcopy(report)
        if field == "hash":
            bad["items"][0]["lineage"]["identity"]["model"]["sha256"] = "f" * 64
        if field == "metrics":
            bad["items"][0]["metrics"]["tp"] = 0
        if field == "selection":
            bad["selection"]["reason"] = "arbitrary"
        with pytest.raises(ScienceError):
            validate_report(bad)


def test_no_patient_independence_imputed_and_no_test_tuning(tmp_path):
    p = load_protocol()
    e = evidence(tmp_path)
    for r in e["rows"]:
        r["patient_id"] = None
    c = classify(e, p, e["identity"]["dataset"], "val")
    assert c["uncertainty"]["intervals"] is None
    e["identity"]["split"] = "test"
    e["identity"]["purpose"] = "final"
    c = classify(e, p, e["identity"]["dataset"], "test")
    assert c["threshold_proposal_val_only"] is None


def test_campaign_inventory_keeps_failures_and_first_verified_policy(tmp_path):
    from src.malaria_dl.science.protocol import campaign_plan

    p = load_protocol()
    e = evidence(tmp_path)
    from src.malaria_dl.science.protocol import configuration_key

    key = configuration_key(e["configuration"])
    members = [
        {
            "id": str(uuid4()),
            "configuration_hash": h,
            "seed": s,
            "state": "failed",
            "exclusion_reason": None,
        }
        for h in p["configurations"]
        for s in p["seeds"]
    ]
    member = next(
        m for m in members if m["configuration_hash"] == key and m["seed"] == 11
    )
    member["state"] = "verified"
    campaign = {
        "id": str(uuid4()),
        "state": "active",
        "contract_hash": "a" * 64,
        "dataset": e["identity"]["dataset"],
        "protocol": campaign_plan(p)["campaign_protocol"],
        "configuration_hashes": list(p["configurations"]),
        "members": members,
        "attempts": [
            {
                "id": str(uuid4()),
                "member_id": member["id"],
                "ordinal": 1,
                "state": "verified",
                "training_run_id": e["identity"]["model"]["training_run_id"],
            }
        ],
    }
    r = compare(
        p,
        e["identity"]["dataset"],
        "val",
        [{"evaluation_id": e["evaluation_id"]}],
        lambda *_: e,
        provenance={},
        campaign=campaign,
    )
    assert sum(x.get("train_state") == "failed" for x in r["matrix"]) == 35
    assert r["campaign"] == campaign and r["selection"]["candidate"] is None
    campaign["attempts"][0]["ordinal"] = 2
    prior = {
        **campaign["attempts"][0],
        "id": str(uuid4()),
        "ordinal": 1,
        "training_run_id": str(uuid4()),
    }
    campaign["attempts"].append(prior)
    r = compare(
        p,
        e["identity"]["dataset"],
        "val",
        [{"evaluation_id": e["evaluation_id"]}],
        lambda *_: e,
        provenance={},
        campaign=campaign,
    )
    assert r["exclusions"][0]["reason"] == "FIRST_VERIFIED_ATTEMPT_REQUIRED"


def test_freeze_rejects_missing_candidate_without_database():
    from src.malaria_dl.science.repository import ScienceRepository

    class Repo(ScienceRepository):
        def read_report(self, _):
            return {"split": "val", "selection": {"candidate": None}}

    with pytest.raises(ScienceError, match="VAL_CANDIDATE_REQUIRED"):
        Repo().freeze_final(str(uuid4()), {})


def test_explain_exact_parent_rejection(tmp_path, monkeypatch):
    from src.malaria_dl.assessment.service import explanation_spec

    repo = MemoryRepository()
    v = value(tmp_path)
    v["model"]["source"] = {"kind": "legacy_registered_artifact"}
    a = run(repo, v, tmp_path, Runtime)
    ev = deepcopy(v)
    ev["kind"] = "explain"
    ev["explanation"] = explanation_spec("gradcam", "fake", 1, None, None)
    ev["evaluation"] = {"attempt_id": str(uuid4()), "identity_hash": digest(v)}
    ea = run(repo, ev, tmp_path, Runtime)
    monkeypatch.setattr(
        comparison.lineage, "resolve", lambda *args: (v["model"], v["dataset"], None)
    )
    monkeypatch.setattr(
        comparison.lineage, "dataset_samples", lambda *args, **kw: v["samples"]
    )
    with pytest.raises(ScienceError, match="EXPLAIN_PARENT_CONFLICT"):
        read_evaluation(repo, a["id"], [ea["id"]])


def test_invalid_prediction_mapping_duplicate_and_nonfinite():
    for field, bad in [
        ("label", 2),
        ("label", True),
        ("raw_score", float("nan")),
        ("predicted", -1),
    ]:
        r = rows()
        r[0][field] = bad
        with pytest.raises(ScienceError, match="PREDICTION_INVALID"):
            metrics(r)
    with pytest.raises(ScienceError, match="DUPLICATE_SAMPLE"):
        metrics(rows() + rows())


def test_structured_export_and_curves_follow_persisted_report(tmp_path):
    p = load_protocol()
    e = evidence(tmp_path)
    r = compare(
        p,
        e["identity"]["dataset"],
        "val",
        [{"evaluation_id": e["evaluation_id"]}],
        lambda *_: e,
        provenance={},
    )

    class Stored:
        def read_report(self, _):
            return deepcopy(r)

    dest = tmp_path / "export"
    assert export_report(Stored(), str(uuid4()), dest) == digest(r)
    assert json.loads((dest / "report.json").read_text()) == r
    assert (dest / "curves.png").stat().st_size > 0 and (
        dest / "curves.svg"
    ).stat().st_size > 0
    assert not list(dest.glob("*.csv"))


def test_export_refuses_to_replace_another_report(tmp_path):
    r = compare(
        load_protocol(), {}, "val", [], lambda *_: None, provenance={"revision": 1}
    )

    class Stored:
        def read_report(self, _):
            return deepcopy(r)

    export_report(Stored(), str(uuid4()), tmp_path / "export")
    r["provenance"]["revision"] = 2
    with pytest.raises(ScienceError, match="EXPORT_DESTINATION_CONFLICT"):
        export_report(Stored(), str(uuid4()), tmp_path / "export")
    assert (
        json.loads((tmp_path / "export/report.json").read_text())["provenance"][
            "revision"
        ]
        == 1
    )
