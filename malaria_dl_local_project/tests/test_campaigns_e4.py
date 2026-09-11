"""Pure synthetic E4 planning. No fit/predict, dataset edits, DB or publications."""

import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from src.malaria_dl.campaigns.contracts import (
    CampaignError,
    canonical,
    digest,
    expand_matrix,
    scientific_configuration,
    validate_protocol,
)
from src.malaria_dl.campaigns.service import CampaignService
from src.malaria_dl.models import registry
from src.malaria_dl.models.configuration import resolve_config


def request(seeds=None):
    return {
        "models": None,
        "optimizers": None,
        "seeds": seeds or [11],
        "variants": [{"name": "base", "selected": {}, "by_model": {}}],
        "exclusions": [],
    }


def dataset():
    return {
        "dataset_version_id": str(uuid4()),
        "dataset_materialization_id": str(uuid4()),
        "dataset_root": "/synthetic-only",
        "patient_assignment_fingerprint": "a" * 64,
        "record_assignment_fingerprint": "b" * 64,
        "source_population_fingerprint": "c" * 64,
        "clinical_identity_fingerprint": "d" * 64,
        "counts": {"train": 2, "val": 2, "test": 2},
        "selection_unit": "dataset_version_id",
    }


def protocol():
    """Explicit synthetic choices, not approved clinical defaults."""
    return {
        "version": "synthetic_protocol_v1",
        "objective": "Exercise planning only",
        "metrics": {
            "primary": ["f2"],
            "secondary": ["auc"],
            "definitions_version": "synthetic_v1",
            "compliance": "point_estimate",
        },
        "sensitivity_target": 0.8,
        "specificity_minimum": 0.7,
        "roles": {
            "train": "train",
            "selection": "val",
            "calibration": "val",
            "final_test": "test",
        },
        "ranking": {
            "partition": "val",
            "criteria": ["f2 desc"],
            "tie_breaks": ["configuration_hash asc"],
        },
        "checkpoint": {
            "policy": "f2",
            "monitor": "val_f2_parasitized",
            "mode": "max",
            "threshold": 0.5,
        },
        "early_stopping": {
            "enabled": True,
            "monitor": "val_f2_parasitized",
            "mode": "max",
            "patience": 12,
            "min_delta": 0.0001,
            "restore_best_weights": True,
        },
        "calibration": {
            "algorithm": "threshold_grid",
            "population": "val",
            "version": "synthetic_v1",
        },
        "budget": {"max_members": 100, "max_attempts_per_member": 3},
        "missing": "report_all_members",
        "retries": "first_verified_attempt",
        "fallback": "diagnostic_only",
        "test_access": "final_only_after_candidate_lock",
        "aggregation": {
            "version": "synthetic_v1",
            "specification": "mean of all planned seeds; report n/N",
        },
        "uncertainty": {
            "version": "synthetic_v1",
            "specification": "patient-grouped bootstrap; synthetic specification, not a scientific run",
        },
        "limitations": {
            "shared_val": "Same VAL used for selection and calibration; adaptive bias acknowledged",
            "independent_calibration": False,
            "test_exposure": "unknown",
        },
        "pending": [],
    }


@pytest.mark.parametrize(
    "seeds,count", [([11], 12), ([11, 12, 13], 36), ([11, 11], 12)]
)
def test_matrix_cardinality_and_input(seeds, count):
    plan = expand_matrix(request(seeds), protocol(), frozen=True, dataset=dataset())
    assert len(plan["members"]) == plan["expected_count"] == count
    assert len(plan["configurations"]) == 12
    assert len({(m["configuration_hash"], m["seed"]) for m in plan["members"]}) == count
    for item in plan["configurations"].values():
        c = item["configuration"]
        e = c["resolved"]["execution"]
        assert "seed" not in e and e["evaluate_best_on_test"] is False
        assert e["min_recall"] == 0.8 and e["min_specificity"] == 0.7
        assert c["resolved"]["input_contract"]["external"]["mode"] == (
            "vgg16_imagenet" if c["model_id"] == "vgg16" else "rescale_0_1"
        )
        assert item["requests"][0]["requested"]["batch"] is True


def test_canonical_order_number_and_scientific_sensitivity():
    assert canonical({"b": 1.0, "a": [-0.0, 2]}) == canonical({"a": [0, 2.0], "b": 1})
    assert digest({"a": [1, 2]}) != digest({"a": [2, 1]})
    cfg = resolve_config("custom_cnn")
    first = digest(scientific_configuration(cfg))
    cfg["resolved"]["execution"]["seed"] = 123
    assert first == digest(scientific_configuration(cfg))
    cfg["resolved"]["model"]["dropout"] = 0.2
    assert first != digest(scientific_configuration(cfg))


@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), float("-inf"), {1: "a"}, (1, 2), object()]
)
def test_non_json_rejected(value):
    with pytest.raises(CampaignError):
        canonical(value)


def test_new_registry_only_affects_new_plans(monkeypatch):
    original = expand_matrix(request())
    saved = canonical(original)
    monkeypatch.setattr(registry, "MODEL_REGISTRY", dict(registry.MODEL_REGISTRY))
    registry.register(
        replace(
            registry.resolve_descriptor("custom_cnn"), id="synthetic_cnn", aliases=()
        )
    )
    assert expand_matrix(request())["expected_count"] == 16
    assert canonical(original) == saved


def test_exclusions_visible_and_unknown_not_silent():
    r = request()
    r["exclusions"] = [
        {
            "model": "vgg16",
            "optimizer": "sgd",
            "variant": "base",
            "reason": "Synthetic planned exclusion",
        }
    ]
    plan = expand_matrix(r)
    assert (
        plan["expected_count"] == 12
        and sum(m["exclusion_reason"] is not None for m in plan["members"]) == 1
    )
    r["exclusions"][0]["model"] = "unknown"
    with pytest.raises(CampaignError):
        expand_matrix(r)


@pytest.mark.parametrize(
    "change",
    [
        {"seeds": []},
        {"seeds": [True]},
        {"seeds": [-1]},
        {"optimizers": ["unknown"]},
        {
            "variants": [
                {
                    "name": "bad",
                    "selected": {"model": {"preprocessing": "vgg16_imagenet"}},
                    "by_model": {},
                }
            ]
        },
        {
            "variants": [
                {"name": "bad", "selected": {"execution": {"seed": 1}}, "by_model": {}}
            ]
        },
    ],
)
def test_bad_matrix(change):
    r = request()
    r.update(change)
    with pytest.raises(ValueError):
        expand_matrix(r)


@pytest.mark.parametrize(
    "path,value",
    [
        (("roles", "selection"), "test"),
        (("roles", "calibration"), "test"),
        (("ranking", "partition"), "test"),
        (("calibration", "population"), "test"),
        (("limitations", "independent_calibration"), True),
        (("limitations", "test_exposure"), "accredited_unexposed"),
        (("checkpoint", "threshold"), 0.7),
        (("retries",), "best_metric"),
        (("pending",), ["clinical decision"]),
        (("sensitivity_target",), None),
        (("specificity_minimum",), -1),
    ],
)
def test_protocol_blocks_invalid_or_pending(path, value):
    p = protocol()
    target = p
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(CampaignError):
        validate_protocol(p, frozen=True, dataset=dataset())


def test_draft_and_roles_accreditation():
    assert validate_protocol({"pending": ["clinical targets"]})
    with pytest.raises(CampaignError):
        validate_protocol({}, frozen=True, dataset=dataset())
    d = dataset()
    d["counts"]["val"] = 0
    with pytest.raises(CampaignError):
        validate_protocol(protocol(), frozen=True, dataset=d)


def test_protocol_variant_conflict():
    r = request()
    r["variants"][0]["selected"] = {"execution": {"min_recall": 0.99}}
    with pytest.raises(CampaignError, match="VARIANT_PROTOCOL_CONFLICT"):
        expand_matrix(r, protocol(), frozen=True, dataset=dataset())


def test_service_requires_uuid_and_no_implicit_db_or_training():
    repo = Mock()
    verify = Mock()
    s = CampaignService(repo, verify, dict)
    assert s.inspect(request())["expected_count"] == 12
    verify.assert_not_called()
    repo.create.assert_not_called()
    with pytest.raises(CampaignError):
        s.create(
            name="x",
            purpose="x",
            dataset_version_id=None,
            request=request(),
            protocol={},
            actor="test",
        )
    verify.assert_not_called()


def test_service_rechecks_exact_dataset_and_rejects_code_change():
    d = dataset()
    evidence = str(uuid4())
    row = {
        "id": uuid4(),
        "name": "synthetic",
        "purpose": "test",
        "experiment_id": None,
        "state": "draft",
        "dataset_version_id": d["dataset_version_id"],
        "dataset_snapshot": d,
        "dataset_evidence_id": evidence,
        "requested": request(),
        "protocol": protocol(),
        "environment": {"source": "one"},
    }
    repo = Mock()
    repo.get.return_value = row
    verifier = Mock(
        return_value=SimpleNamespace(metadata=lambda: d, evidence_id=evidence)
    )
    s = CampaignService(repo, verifier, lambda: {"source": "two"})
    with pytest.raises(CampaignError):
        s.freeze(str(row["id"]))
    verifier.assert_not_called()
    repo.freeze.assert_not_called()


def test_cli_inspect_without_db_or_tensorflow(tmp_path, monkeypatch, capsys):
    from src.campaign import main
    from src.malaria_dl.campaigns import repository

    monkeypatch.setattr(
        repository, "get_engine", Mock(side_effect=AssertionError("DB forbidden"))
    )
    p = tmp_path / "request.json"
    p.write_text(json.dumps(request()))
    assert main(["inspect", "--request", str(p)]) == 0
    assert json.loads(capsys.readouterr().out)["expected_count"] == 12
    assert not list(tmp_path.rglob("*.csv"))


def test_protocol_draft_cannot_use_test():
    for p in (
        {"calibration": {"population": "test"}},
        {"ranking": {"partition": "test"}},
    ):
        with pytest.raises(CampaignError):
            validate_protocol(p)


def test_repository_failure_sanitized_no_fallback(tmp_path):
    from contextlib import contextmanager

    from src.malaria_dl.campaigns.repository import CampaignRepository

    @contextmanager
    def unavailable(readonly=False):
        raise RuntimeError("driver details must not escape")
        yield

    with pytest.raises(CampaignError, match="^CAMPAIGN_DATABASE_OPERATION_FAILED$"):
        CampaignRepository(unavailable).get(str(uuid4()))
    assert list(tmp_path.iterdir()) == []


def test_frozen_contract_self_contained_and_tamper_rejected():
    from src.malaria_dl.campaigns.contracts import validate_frozen_contract

    d = dataset()
    p = protocol()
    r = request()
    c = {
        "version": "campaign_contract_v1",
        "name": "synthetic",
        "purpose": "unit test",
        "experiment_id": None,
        "dataset": d,
        "dataset_evidence_id": str(uuid4()),
        "requested": r,
        "protocol": p,
        "environment": {
            "source_sha256": "a" * 64,
            "python": "synthetic",
            "tensorflow": "synthetic",
            "packages": {"synthetic": "1"},
            "determinism_environment": {},
        },
        "matrix": expand_matrix(r, p, frozen=True, dataset=d),
    }
    assert validate_frozen_contract(json.loads(canonical(c))) == c
    changed = json.loads(canonical(c))
    changed["matrix"]["members"][0]["seed"] = -1
    with pytest.raises(CampaignError):
        validate_frozen_contract(changed)


def test_additive_migration_offline_and_linear():
    import importlib.util
    from io import StringIO
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "e4_migration", root / "alembic/versions/20260911_01_experimental_campaigns.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = StringIO()
    module.op = Operations(
        MigrationContext.configure(
            dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
        )
    )
    module.upgrade()
    ddl = output.getvalue()
    assert module.down_revision == "20260901_01"
    assert "CREATE TABLE experimental_campaigns" in ddl
    assert "CREATE UNIQUE INDEX uq_campaign_one_active_attempt" in ddl
    assert "DROP TABLE" not in ddl and "TRUNCATE" not in ddl
    assert "SET search_path = public, pg_catalog" in ddl
    assert "UPDATE runs SET" not in ddl


def test_read_repository_does_not_import_model_registry():
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            (
                "import sys; from src.malaria_dl.campaigns.repository import CampaignRepository; "
                "assert 'src.malaria_dl.models.registry' not in sys.modules; "
                "assert 'tensorflow' not in sys.modules"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "source,target",
    [
        ("draft", "active"),
        ("frozen", "draft"),
        ("finalized", "active"),
        ("active", "frozen"),
    ],
)
def test_invalid_state_transition_before_update(source, target):
    from contextlib import contextmanager

    from src.malaria_dl.campaigns.repository import CampaignRepository

    @contextmanager
    def scope(readonly=False):
        yield object()

    repo = CampaignRepository(scope)
    repo._campaign = lambda *a, **kw: {"id": uuid4(), "state": source}
    with pytest.raises(CampaignError, match="INVALID_CAMPAIGN_TRANSITION"):
        repo.transition(str(uuid4()), target)


def test_conflicting_dataset_read_rejected_before_members():
    from contextlib import contextmanager

    from src.malaria_dl.campaigns.repository import CampaignRepository

    @contextmanager
    def scope(readonly=False):
        yield object()

    repo = CampaignRepository(scope)
    repo._campaign = lambda *a, **kw: {"dataset_version_id": str(uuid4())}
    with pytest.raises(CampaignError, match="CAMPAIGN_DATASET_CONFLICT"):
        repo.get(str(uuid4()), str(uuid4()))
