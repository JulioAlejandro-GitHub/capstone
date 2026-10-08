"""Physical IO guards, not just output filtering; all datasets are synthetic."""
# ruff: noqa: F811 -- shared pytest fixtures

import builtins
import io
import json
import os
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from src.malaria_dl.assessment import cli, lineage, service
from src.malaria_dl.assessment.contracts import AssessmentError
from src.malaria_dl.data import dataset_integrity as integrity
from src.malaria_dl.data import governed_dataset as gd
from src.malaria_dl.persistence import dataset_evidence as ev
from test_assessment_e6 import value
from test_dataset_resolution import persisted
from test_dataset_stage1 import (  # noqa: F401 -- fixtures
    TRAIN,
    VERSION,
    Result,
    evidence_store,
    fixture,
)


def guard_dataset_io(monkeypatch, root: Path, allowed: tuple[str, ...]) -> list:
    """Intercept enumeration, opens, stat/lstat and hashes under the dataset."""
    calls = []
    root = Path(os.path.abspath(root))

    def guard(path, action):
        if isinstance(path, int):
            return
        candidate = Path(os.path.abspath(os.fsdecode(path)))
        if not candidate.is_relative_to(root):
            return
        parts = candidate.relative_to(root).parts
        if not parts:
            assert action not in ("scandir", "listdir"), (
                "Must not enumerate dataset root"
            )
            return
        assert parts[0] in allowed, f"Forbidden physical {action}: {candidate}"
        calls.append((action, parts[0], str(candidate)))

    def wrap(original, action):
        def checked(path, *args, **kwargs):
            guard(path, action)
            return original(path, *args, **kwargs)

        return checked

    for module, name in (
        (os, "scandir"),
        (os, "listdir"),
        (os, "stat"),
        (os, "lstat"),
        (os, "open"),
        (io, "open"),
        (builtins, "open"),
    ):
        monkeypatch.setattr(module, name, wrap(getattr(module, name), name))
    monkeypatch.setattr(integrity, "file_sha256", wrap(integrity.file_sha256, "sha256"))
    return calls


def assessment_setup(fixture, monkeypatch):
    snapshot = persisted(fixture)
    template = value(fixture.root.parent)
    template["model"]["training_run_id"] = TRAIN
    monkeypatch.setattr(
        service, "resolve", lambda *args: (template["model"], snapshot, None)
    )
    monkeypatch.setattr(service, "inference_environment", lambda *args: {})
    monkeypatch.setattr(Result, "__iter__", lambda self: iter(self.rows), raising=False)
    repo = SimpleNamespace(transaction=lambda **kw: nullcontext(fixture.connection))
    return repo, snapshot, template


@pytest.mark.parametrize("kind", ["evaluate", "explain"])
@pytest.mark.parametrize("batch", [False, True])
@pytest.mark.parametrize("inspection", [False, True])
def test_val_cli_never_touches_train_or_test(
    fixture, evidence_store, monkeypatch, capsys, kind, batch, inspection
):
    repo, snapshot, template = assessment_setup(fixture, monkeypatch)
    repo.consume = lambda *args: None
    monkeypatch.setattr(cli, "AssessmentRepository", lambda: repo)
    monkeypatch.setattr(
        cli,
        "campaign_inventory",
        lambda *args: (
            {},
            [
                {
                    "member_id": "member",
                    "eligible": True,
                    "model": {
                        "training_run_id": TRAIN,
                        "model_version_id": template["model"]["model_version_id"],
                    },
                }
            ],
        ),
    )
    observed = []
    monkeypatch.setattr(
        cli,
        "run",
        lambda repo, prepared, root: (
            observed.append(prepared)
            or {
                "id": "attempt",
                "state": "verified",
                "verification": {},
                "identity_id": "identity",
            }
        ),
    )
    # Damage unauthorized subtrees: neither their absence nor contents are read.
    before = deepcopy(snapshot)
    calls = guard_dataset_io(monkeypatch, fixture.root, ("val",))
    args = ["--campaign-id", VERSION] if batch else ["--source-training-run-id", TRAIN]
    args += [
        "--split",
        "val",
        "--purpose",
        "development",
        "--seed",
        "42",
        "--threshold",
        ".5",
        "--protocol",
        json.dumps(template["protocol"]),
    ]
    if kind == "explain":
        args += ["--method", "gradcam", "--layer", "conv"]
    if inspection:
        args += ["--inspect"]
    assert cli._main(kind, batch, args) == 0
    output = json.loads(capsys.readouterr().out)
    assert snapshot == before
    assert {split for _, split, _ in calls} == {"val"}
    assert {action for action, _, _ in calls} >= {"scandir", "open", "sha256"}
    assert any("clinical_identities" in query for query, _ in fixture.queries)
    if inspection:
        assert not observed and not evidence_store
        proof = (
            output[0]["inspection_verification"]
            if batch
            else output["inspection_verification"]
        )
    else:
        proof = next(iter(evidence_store.values()))["after_state"]
        assert all(s["split"] == "val" for s in observed[0]["samples"])
    assert proof["required_splits"] == proof["physically_verified_splits"] == ["val"]
    assert proof["integrity_status"] == "verified_requested_splits"
    assert proof["global_integrity_status"] == "verified_frozen_metadata"


@pytest.mark.parametrize("split", ["train", "val"])
def test_train_scope_rejects_changed_authorized_file(
    fixture, evidence_store, monkeypatch, split
):
    persisted(fixture)
    next((fixture.root / split).rglob("*.png")).write_bytes(b"altered")
    calls = guard_dataset_io(monkeypatch, fixture.root, ("train", "val"))
    with pytest.raises(gd.GovernedDatasetError, match="CONTENT_HASH_MISMATCH"):
        ev.verify_dataset_for_execution(VERSION, required_splits=("train", "val"))
    assert calls
    proof = next(iter(evidence_store.values()))["after_state"]
    assert proof["physically_verified_splits"] == []
    assert proof["integrity_status"] == "rejected"


@pytest.mark.parametrize("kind", ["evaluate", "explain"])
@pytest.mark.parametrize(
    "fault", ["changed_val", "snapshot", "global_metadata", "val_symlink"]
)
def test_val_rejects_without_accessing_other_splits(
    fixture, evidence_store, monkeypatch, kind, fault
):
    repo, snapshot, template = assessment_setup(fixture, monkeypatch)
    path = next((fixture.root / "val").rglob("*.png"))
    if fault == "changed_val":
        path.write_bytes(b"altered")
    elif fault == "snapshot":
        snapshot["record_assignment_fingerprint"] = "f" * 64
    elif fault == "global_metadata":
        # Global TRAIN metadata must still be checked; no TRAIN bytes are needed.
        row = list(fixture.sources[0])
        row[3] = "f" * 64
        fixture.sources[0] = tuple(row)
    else:
        path.unlink()
        path.symlink_to(next((fixture.root / "train").rglob("*.png")))
    guard_dataset_io(monkeypatch, fixture.root, ("val",))
    with pytest.raises(gd.GovernedDatasetError):
        service.prepare(
            repo,
            training_run_id=TRAIN,
            split="val",
            purpose="development",
            protocol=template["protocol"],
            requested_threshold=".5",
            seed=42,
            batch_size=1,
            explanation=service.explanation_spec("gradcam", "conv", 1, None, [])
            if kind == "explain"
            else None,
        )


@pytest.mark.parametrize(
    "splits", [None, "val", ("unknown",), ("val", "val"), ("test",)]
)
def test_invalid_or_unauthorized_scope_fails_before_database_and_files(
    monkeypatch, splits
):
    monkeypatch.setattr(
        gd, "dataset_read_connection", lambda: pytest.fail("No database access")
    )
    monkeypatch.setattr(
        ev, "persist_dataset_evidence", lambda *a, **kw: pytest.fail("No writes")
    )
    with pytest.raises(gd.GovernedDatasetError):
        ev.verify_dataset_for_execution(VERSION, required_splits=splits)


@pytest.mark.parametrize("purpose", ["development", "final"])
def test_test_without_lock_rejected_before_filesystem(fixture, monkeypatch, purpose):
    from src.malaria_dl.assessment import repository as repository_module
    from src.malaria_dl.assessment.repository import AssessmentRepository

    repo = AssessmentRepository()
    monkeypatch.setattr(repo, "transaction", lambda **kw: nullcontext(None))
    monkeypatch.setattr(
        repository_module,
        "execute",
        lambda *args, **kw: SimpleNamespace(mappings=list),
    )
    monkeypatch.setattr(
        service, "resolve", lambda *args: pytest.fail("No checkpoint access")
    )
    monkeypatch.setattr(
        service,
        "inference_environment",
        lambda *args: pytest.fail("No source file access"),
    )
    guard_dataset_io(monkeypatch, fixture.root, ())
    with pytest.raises(AssessmentError, match="TEST_FINAL_LOCK_REQUIRED"):
        service.prepare(
            repo,
            training_run_id=TRAIN,
            split="test",
            purpose=purpose,
            protocol={"version": "explicit", "splits": ["test"], "purposes": [purpose]},
            requested_threshold=".5",
            seed=42,
            batch_size=1,
        )


@pytest.mark.parametrize("background_split", ["val", "train"])
def test_shap_background_cannot_cross_split(
    fixture, evidence_store, monkeypatch, background_split
):
    repo, _, template = assessment_setup(fixture, monkeypatch)
    background = next(
        r["source_record_id"]
        for r in fixture.files
        if r["split_name"] == background_split
    )
    calls = guard_dataset_io(monkeypatch, fixture.root, ("val",))

    def prepare():
        return service.prepare(
            repo,
            training_run_id=TRAIN,
            split="val",
            purpose="development",
            protocol=template["protocol"],
            requested_threshold=".5",
            seed=42,
            batch_size=1,
            explanation=service.explanation_spec("shap", None, 1, 8, [background]),
        )

    if background_split == "val":
        prepared = prepare()
        assert prepared["explanation"]["background"][0]["split"] == "val"
    else:
        with pytest.raises(AssessmentError, match="BACKGROUND_NOT_ACCREDITED"):
            prepare()
    assert {split for _, split, _ in calls} == {"val"}


def test_metadata_only_never_claims_physical_integrity(fixture, monkeypatch):
    guard_dataset_io(monkeypatch, fixture.root, ())
    snapshot = gd.resolve_governed_dataset(VERSION, required_splits=())
    proof = snapshot.verification_metadata()
    assert snapshot.counts == {"train": 2, "val": 2, "test": 2}
    assert proof["physically_verified_splits"] == []
    assert proof["physical_integrity_status"] == "not_checked"
    assert proof["integrity_status"] == "verified_metadata_only"


def test_val_does_not_require_other_physical_splits(fixture, monkeypatch):
    before = gd.resolve_governed_dataset(VERSION, required_splits=()).metadata()
    for split in ("train", "test"):
        (fixture.root / split).rename(fixture.root.parent / (split + "-unavailable"))
    guard_dataset_io(monkeypatch, fixture.root, ("val",))
    after = gd.resolve_governed_dataset(VERSION, required_splits=("val",))
    assert after.metadata() == before
    assert after.verified_splits == ("val",)


@pytest.mark.parametrize(
    "fault", [None, "candidate", "decision", "hash", "scope", "missing_identity"]
)
def test_exact_existing_lock_precedes_test_files(
    fixture, evidence_store, monkeypatch, fault
):
    from src.malaria_dl.assessment import repository as repository_module
    from src.malaria_dl.assessment.contracts import identity, threshold
    from src.malaria_dl.campaigns.contracts import digest

    repo, snapshot, template = assessment_setup(fixture, monkeypatch)
    samples = lineage.dataset_samples(
        repo, snapshot, "test", inspection=True, metadata_only=True
    )
    protocol = {
        "version": "synthetic-final",
        "splits": ["test"],
        "purposes": ["final"],
        "allowed_numeric_thresholds": [0.5],
    }
    locked = identity(
        template["model"],
        snapshot,
        samples,
        split="test",
        purpose="final",
        protocol=protocol,
        decision=threshold(".5", protocol),
        code={},
        seed=42,
        batch_size=1,
    )
    row = {
        "identity_hash": digest(locked),
        "identity": locked,
        "evidence": {
            "status": "locked",
            "candidate": deepcopy(locked["model"]),
            "decision": deepcopy(locked["decision"]),
        },
    }
    if fault in ("candidate", "decision"):
        row["evidence"][fault] = {}
    elif fault == "hash":
        row["identity_hash"] = "0" * 64
    elif fault == "scope":
        locked["protocol"] = {**protocol, "version": "other"}
        row["identity_hash"] = digest(locked)
    elif fault == "missing_identity":
        row["identity"] = None
    monkeypatch.setattr(
        repository_module,
        "execute",
        lambda *args, **kw: SimpleNamespace(mappings=lambda: [row]),
    )
    repo.authorize_test_request = (
        repository_module.AssessmentRepository.authorize_test_request.__get__(repo)
    )
    calls = guard_dataset_io(
        monkeypatch, fixture.root, ("test",) if fault is None else ()
    )

    def prepare():
        return service.prepare(
            repo,
            training_run_id=TRAIN,
            split="test",
            purpose="final",
            protocol=protocol,
            requested_threshold=".5",
            seed=42,
            batch_size=1,
        )

    if fault is None:
        assert prepare() == locked
        assert {split for _, split, _ in calls} == {"test"}
    else:
        with pytest.raises(AssessmentError, match="TEST_FINAL_LOCK_REQUIRED"):
            prepare()
        assert not calls


def test_inspection_does_not_acquire_writing_global_gate(monkeypatch):
    from src.malaria_dl.execution import global_gate, local_launch

    monkeypatch.setattr(local_launch, "bootstrap", lambda: None)
    monkeypatch.setattr(
        global_gate, "GlobalGate", lambda *args: pytest.fail("No PostgreSQL writes")
    )
    monkeypatch.setattr(cli, "_main", lambda *args: 0)
    assert (
        cli.main("evaluate", argv=["--source-training-run-id", TRAIN, "--inspect"]) == 0
    )


def test_v1_evidence_pins_identity_but_never_claims_current_full_verification(
    fixture, evidence_store, monkeypatch
):
    snapshot = gd.resolve_governed_dataset(VERSION, required_splits=()).metadata()
    evidence_store["historical"] = {
        "success": True,
        "after_state": {
            "verifier_version": "ml_dataset_integrity_v1",
            "snapshot": snapshot,
            "integrity_status": "verified",
        },
    }
    historical = deepcopy(evidence_store["historical"])
    guard_dataset_io(monkeypatch, fixture.root, ("val",))
    result = ev.verify_dataset_for_execution(
        VERSION, required_splits=("val",), expected_evidence_id="historical"
    )
    assert evidence_store["historical"] == historical
    proof = evidence_store[result.evidence_id]["after_state"]
    assert proof["verifier_version"] == "ml_dataset_integrity_v2"
    assert proof["physically_verified_splits"] == ["val"]


@pytest.mark.parametrize("kind", ["evaluate", "explain"])
@pytest.mark.parametrize("purpose", ["development", "final"])
def test_campaign_test_authorization_precedes_checkpoint_and_dataset(
    fixture, monkeypatch, kind, purpose
):
    from src.malaria_dl.assessment import repository as repository_module

    snapshot = persisted(fixture)
    repo = repository_module.AssessmentRepository()
    monkeypatch.setattr(
        repo,
        "get",
        lambda *args: {
            "state": "frozen",
            "dataset_snapshot": snapshot,
            "attempts": [
                {
                    "id": "attempt",
                    "member_id": "member",
                    "training_run_id": TRAIN,
                    "state": "verified",
                }
            ],
            "members": [
                {"id": "member", "state": "verified", "accepted_attempt_id": "attempt"}
            ],
        },
    )
    monkeypatch.setattr(repo, "transaction", lambda **kw: nullcontext(None))
    monkeypatch.setattr(
        repository_module, "execute", lambda *args, **kw: SimpleNamespace(mappings=list)
    )
    monkeypatch.setattr(cli, "AssessmentRepository", lambda: repo)
    monkeypatch.setattr(lineage, "training_dataset_metadata", lambda run: snapshot)
    monkeypatch.setattr(
        lineage,
        "resolve",
        lambda *a, **kw: pytest.fail("Checkpoint access before authorization"),
    )
    monkeypatch.setattr(
        service,
        "resolve",
        lambda *a, **kw: pytest.fail("Checkpoint access before authorization"),
    )
    guard_dataset_io(monkeypatch, fixture.root, ())
    args = [
        "--campaign-id",
        VERSION,
        "--inspect",
        "--split",
        "test",
        "--purpose",
        purpose,
        "--protocol",
        json.dumps({"version": "synthetic", "splits": ["test"], "purposes": [purpose]}),
        "--threshold",
        ".5",
        "--seed",
        "42",
    ]
    if kind == "explain":
        args += ["--method", "gradcam", "--layer", "conv"]
    assert cli._main(kind, True, args) == 2
