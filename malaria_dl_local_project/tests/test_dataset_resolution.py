"""Shared dataset contract: temporary synthetic population, no operational TEST."""
# ruff: noqa: F811 -- pytest fixtures imported from the sealed population suite

from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from src.malaria_dl.assessment import lineage, service
from src.malaria_dl.assessment.contracts import AssessmentError
from src.malaria_dl.data import governed_dataset as gd
from src.malaria_dl.persistence import dataset_evidence as ev
from test_dataset_stage1 import (
    TRAIN,
    VERSION,
    Result,
    evidence_store,  # noqa: F401 -- pytest fixture
    fixture,  # noqa: F401 -- pytest fixture
)


def persisted(fixture) -> dict:
    snapshot = gd.resolve_governed_dataset(VERSION).metadata()
    snapshot["dataset_root"] = "/app/malaria_dl_local_project/data/sealed"
    fixture.training = {
        "dataset_version_id": VERSION,
        "session_dataset": deepcopy(snapshot),
        "execution_parameters": {
            "model_configuration_e2": {"dataset": deepcopy(snapshot)}
        },
        "parameters": {},
    }
    return snapshot


@pytest.mark.parametrize(
    "source", ["session", "nested", "execution_parameters", "parameters"]
)
def test_retrieve_one_complete_persisted_snapshot(fixture, source: str) -> None:
    snapshot = persisted(fixture)
    fixture.training.update(
        session_dataset=None, execution_parameters={}, parameters={}
    )
    if source == "session":
        fixture.training["session_dataset"] = deepcopy(snapshot)
    elif source == "nested":
        fixture.training["execution_parameters"] = {
            "model_configuration_e2": {"dataset": deepcopy(snapshot)}
        }
    else:
        fixture.training[source] = deepcopy(snapshot)
    before = deepcopy(fixture.training)
    result = gd.training_dataset_metadata(TRAIN)
    assert result == snapshot
    result["counts"]["val"] = 999
    assert fixture.training == before
    assert all("UPDATE" not in q and "INSERT" not in q for q, _ in fixture.queries)


@pytest.mark.parametrize(
    "field,value",
    [
        ("dataset_version_id", str(uuid4())),
        ("dataset_materialization_id", str(uuid4())),
        ("patient_assignment_fingerprint", "a" * 64),
        ("record_assignment_fingerprint", "b" * 64),
        ("source_population_fingerprint", "c" * 64),
        ("clinical_identity_fingerprint", "d" * 64),
        ("dataset_root", "/app/project/data/other"),
        ("counts", {"train": 1, "val": 1, "test": 1}),
    ],
)
@pytest.mark.parametrize("partial", [False, True])
def test_conflicting_representations_rejected(
    fixture, field: str, value: object, partial: bool
) -> None:
    snapshot = persisted(fixture)
    candidate = {} if partial else deepcopy(snapshot)
    candidate[field] = value
    fixture.training["parameters"] = candidate
    with pytest.raises(gd.GovernedDatasetError, match="SNAPSHOT_CONFLICT"):
        gd.training_dataset_metadata(TRAIN)


def test_incomplete_evidence_is_never_assembled(fixture) -> None:
    persisted(fixture)
    del fixture.training["session_dataset"]["clinical_identity_fingerprint"]
    del fixture.training["execution_parameters"]["model_configuration_e2"]["dataset"][
        "counts"
    ]
    with pytest.raises(gd.GovernedDatasetError, match="SNAPSHOT_MISSING"):
        gd.training_dataset_metadata(TRAIN)


def test_host_prefix_difference_preserves_snapshot(fixture, evidence_store) -> None:
    original = persisted(fixture)
    fixture.training["parameters"] = {"dataset_root": str(fixture.root)}
    before = deepcopy(fixture.training)
    resolved = ev.verify_dataset_for_execution(training_run_id=TRAIN)
    gd.assert_run_dataset_snapshot_unchanged(resolved, original)
    assert resolved.dataset_root == fixture.root
    assert fixture.training == before
    assert (
        evidence_store[resolved.evidence_id]["after_state"]["training_run_id"] == TRAIN
    )


@pytest.mark.parametrize("host", ["macOS", "Docker"])
def test_same_relative_mount_even_when_foreign_directory_exists(
    tmp_path, monkeypatch, host: str
) -> None:
    foreign = tmp_path / "foreign" / "data" / "sealed"
    foreign.mkdir(parents=True)
    project = tmp_path / host
    local = project / "data" / "sealed"
    local.mkdir(parents=True)
    monkeypatch.setattr(gd, "PROJECT_ROOT", project)
    assert gd.local_dataset_root(foreign) == local
    assert gd.local_dataset_root(local) == local


def test_dataset_dir_cannot_select_alternate_population(fixture) -> None:
    snapshot = gd.resolve_governed_dataset(VERSION)
    gd.validate_dataset_location(snapshot, "/app/project/data/sealed")
    alternate = fixture.root.parent / "malaria_physical_split"
    alternate.mkdir()
    with pytest.raises(gd.GovernedDatasetError, match="DATASET_DIR_CONFLICT"):
        gd.validate_dataset_location(snapshot, alternate)


@pytest.mark.parametrize("inspection", [False, True])
def test_assessment_selects_verified_local_val_only(
    fixture, evidence_store, monkeypatch, inspection: bool
) -> None:
    inherited = persisted(fixture)
    before = deepcopy(inherited)
    monkeypatch.setattr(Result, "__iter__", lambda self: iter(self.rows), raising=False)
    repo = SimpleNamespace(transaction=lambda **kw: nullcontext(fixture.connection))
    accessed = []
    original = lineage.file_identity

    def read(path: Path) -> dict:
        accessed.append(path)
        assert path.is_relative_to(fixture.root / "val")
        return original(path)

    monkeypatch.setattr(lineage, "file_identity", read)
    samples = lineage.dataset_samples(
        repo, inherited, "val", inspection=inspection, training_run_id=TRAIN
    )
    assert len(samples) == len(accessed) == 2
    assert {s["label"] for s in samples} == {0, 1}
    assert all(s["split"] == "val" for s in samples)
    assert inherited == before
    if not inspection:
        assert (
            next(iter(evidence_store.values()))["after_state"]["training_run_id"]
            == TRAIN
        )


@pytest.mark.parametrize(
    "split,purpose,code",
    [
        ("test", "development", "TEST_FINAL_LOCK_REQUIRED"),
        ("val", "final", "TEST_FINAL_LOCK_REQUIRED"),
        ("unknown", "development", "PROTOCOL_REQUIRED"),
        ("train", "development", "PROTOCOL_CONFLICT"),
    ],
)
def test_split_rejected_before_dataset_or_checkpoint_access(
    monkeypatch, split: str, purpose: str, code: str
) -> None:
    monkeypatch.setattr(
        service, "resolve", lambda *a: pytest.fail("No file or DB access allowed")
    )
    protocol = {
        "version": "synthetic",
        "splits": ["val", "test", "unknown"],
        "purposes": ["development", "final"],
    }
    with pytest.raises(AssessmentError, match=code):
        service.prepare(
            None,
            split=split,
            purpose=purpose,
            protocol=protocol,
            requested_threshold=".5",
            seed=42,
            batch_size=1,
        )


def test_runtime_uses_local_val_preserves_input_and_refuses_unlisted_image(
    fixture, evidence_store, monkeypatch
) -> None:
    import numpy as np
    from src.malaria_dl.assessment.runtime import KerasRuntime
    from src.malaria_dl.data import preprocessing

    inherited = persisted(fixture)
    monkeypatch.setattr(Result, "__iter__", lambda self: iter(self.rows), raising=False)
    repo = SimpleNamespace(transaction=lambda **kw: nullcontext(fixture.connection))
    samples = lineage.dataset_samples(repo, inherited, "val", training_run_id=TRAIN)
    calls = []
    runtime = object.__new__(KerasRuntime)
    runtime.value = {
        "dataset": inherited,
        "samples": samples,
        "model": {
            "input_contract": {
                "shape": [None, 8, 8, 3],
                "external": {"mode": "rescale_0_1"},
            }
        },
    }
    runtime.dataset_root = gd.local_dataset_root(inherited["dataset_root"])
    runtime.tf = SimpleNamespace(
        io=SimpleNamespace(decode_image=lambda contents, **kw: np.ones((8, 8, 3))),
        image=SimpleNamespace(resize=lambda rgb, shape, **kw: rgb),
        stack=np.stack,
    )
    monkeypatch.setattr(
        preprocessing,
        "apply_model_preprocessing",
        lambda rgb, mode: calls.append(mode) or rgb,
    )
    before = deepcopy(runtime.value)
    assert runtime.images(samples).shape == (2, 8, 8, 3)
    assert calls == ["rescale_0_1", "rescale_0_1"]
    assert runtime.value == before
    unlisted = {
        **samples[0],
        "split": "test",
        "relative_path": "test/not-authorized.png",
    }
    with pytest.raises(AssessmentError, match="SAMPLE_NOT_AUTHORIZED"):
        runtime.images([unlisted])


@pytest.mark.parametrize("kind", ["evaluate", "explain"])
def test_individual_and_campaign_cli_share_preparation(monkeypatch, kind: str) -> None:
    from src.malaria_dl.assessment import cli

    seen = []
    repo = SimpleNamespace(consume=lambda *a: None)
    monkeypatch.setattr(cli, "AssessmentRepository", lambda: repo)
    monkeypatch.setattr(
        cli,
        "campaign_inventory",
        lambda *a: (
            {},
            [
                {
                    "eligible": True,
                    "member_id": "member",
                    "model": {"training_run_id": TRAIN, "model_version_id": VERSION},
                }
            ],
        ),
    )
    monkeypatch.setattr(cli, "prepare", lambda repo, **kw: seen.append(kw) or {})
    monkeypatch.setattr(
        cli,
        "run",
        lambda *a: {"id": "attempt", "state": "verified", "verification": {}},
    )
    options = [
        "--model",
        "custom_cnn",
        "--split",
        "val",
        "--purpose",
        "development",
        "--protocol",
        "{}",
        "--threshold",
        ".5",
        "--seed",
        "42",
        "--dataset-dir",
        "/app/project/data/sealed",
    ]
    if kind == "explain":
        options += ["--method", "gradcam", "--layer", "conv"]
    assert (
        cli._main(
            kind,
            False,
            [
                "--source-training-run-id",
                TRAIN,
                "--model-version-id",
                VERSION,
                *options,
            ],
        )
        == 0
    )
    assert cli._main(kind, True, ["--campaign-id", "campaign", *options]) == 0
    individual, campaign = seen
    assert individual.pop("evaluation_id") is None
    assert individual == campaign


def test_model_constraint_rejected_before_loading_dataset(monkeypatch) -> None:
    monkeypatch.setattr(
        service,
        "resolve",
        lambda *args: ({"input_contract": {"architecture": "custom_cnn"}}, {}, None),
    )
    monkeypatch.setattr(
        service,
        "dataset_samples",
        lambda *args, **kw: pytest.fail("Dataset access forbidden"),
    )
    with pytest.raises(AssessmentError, match="MODEL_TRAIN_CONFLICT"):
        service.prepare(
            None,
            model="vgg16",
            split="val",
            purpose="development",
            protocol={
                "version": "synthetic",
                "splits": ["val"],
                "purposes": ["development"],
            },
            requested_threshold=".5",
            seed=42,
            batch_size=1,
        )


@pytest.mark.parametrize("root", ["/app/project/data/sealed", "data/sealed"])
def test_train_shared_consumer_keeps_snapshot_and_loads_train_val(
    tmp_path, monkeypatch, root: str
) -> None:
    from src.malaria_dl.data import loaders
    from src.malaria_dl.execution.train import train
    from src.malaria_dl.models import registry
    from test_campaign_executor_e5 import evidence

    monkeypatch.setattr(
        registry, "registered_models", lambda: tuple(registry.MODEL_REGISTRY)
    )
    monkeypatch.setattr(gd, "PROJECT_ROOT", tmp_path)
    session, _ = evidence(tmp_path)
    session.update(owner=str(uuid4()), artifact_root=str(tmp_path / "artifacts"))
    session["configuration"]["resolved"]["execution"]["seed"] = 42
    session["dataset"]["dataset_root"] = root
    before = deepcopy(session)
    loaded = []

    class StopBeforeModel(Exception):
        pass

    def loader(path, *args):
        loaded.append(path)
        return SimpleNamespace(file_paths=[str(path / "uninfected/a.png")])

    monkeypatch.setattr(loaders, "make_image_dataset_from_directory", loader)
    monkeypatch.setattr(
        loaders, "preprocess_physical_dataset", lambda raw, *a, **kw: raw
    )

    def adapter():
        raise StopBeforeModel

    with pytest.raises(StopBeforeModel):
        train(None, session, SimpleNamespace(create_adapter=adapter))
    assert loaded == [tmp_path / "data/sealed/train", tmp_path / "data/sealed/val"]
    assert session == before


def test_campaign_and_individual_train_use_same_verifier(
    fixture, evidence_store, monkeypatch
) -> None:
    from src.malaria_dl.campaigns import service as campaigns
    from src.malaria_dl.execution import (
        artifacts,
        campaign,
        global_gate,
        repository,
        train,
    )
    from src.malaria_dl.models import registry

    original = persisted(fixture)
    initial = ev.verify_dataset_for_execution(VERSION)
    verified = []
    verifier = ev.verify_dataset_for_execution

    def verify(*args, **kwargs):
        snapshot = verifier(*args, **kwargs)
        verified.append(snapshot)
        return snapshot

    frozen = {
        "state": "frozen",
        "dataset_version_id": VERSION,
        "dataset_evidence_id": initial.evidence_id,
        "dataset_snapshot": original,
        "contract": {"matrix": {"configurations": {}}},
    }
    session = {"run_id": TRAIN, "owner": str(uuid4()), "state": "active"}

    def standalone(config, dataset, *args):
        session["dataset"] = deepcopy(dataset)
        return session

    repo = SimpleNamespace(
        preflight=lambda: None,
        standalone=standalone,
        session=lambda run: session,
        finish=lambda *args: None,
    )
    campaign.preflight(repo, frozen, fixture.root.parent / "artifacts", verifier=verify)
    monkeypatch.setattr(global_gate, "GlobalGate", lambda *args: nullcontext())
    monkeypatch.setattr(repository, "ExecutionRepository", lambda: repo)
    monkeypatch.setattr(ev, "verify_dataset_for_execution", verify)
    monkeypatch.setattr(campaigns, "planning_environment", dict)
    monkeypatch.setattr(registry, "resolve_descriptor", lambda model: None)
    monkeypatch.setattr(artifacts, "verify_session", lambda *args: {})
    consumed = []
    monkeypatch.setattr(
        train,
        "train",
        lambda repo, session, descriptor: consumed.append(deepcopy(session["dataset"])),
    )
    args = SimpleNamespace(
        evaluate_best_on_test=False,
        threshold_output_json=None,
        dataset_version_id=VERSION,
        dataset_dir=None,
        data_source="physical",
        model_configuration={},
        output_dir=None,
        model="synthetic",
    )
    train.standalone(args)
    assert (
        len(verified) == 3
    )  # campaign preflight; individual preflight and final verification
    assert all(snapshot.metadata() == consumed[0] for snapshot in verified)
    gd.assert_run_dataset_snapshot_unchanged(consumed[0], original)
    assert frozen["dataset_snapshot"] == original
