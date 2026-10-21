"""SWV2.2 CLI contract of -m src.train: --campaign-id resolves a plan; TRAIN never starts."""
import json
from contextlib import contextmanager
from uuid import uuid4

import pytest

from src.malaria_dl.campaigns import configuration as cc
from src.malaria_dl.campaigns.contracts import CampaignError
from src.malaria_dl.campaigns.plan import execution_command, execution_readiness, resolve_plan
from src.malaria_dl.campaigns.service import frozen_contract
from src.malaria_dl.execution import campaign as executor

DATASET = "d8c0cab5-09dd-597f-9de7-7ca01aee2ec2"
OTHER = "00000000-0000-4000-8000-000000000001"
COUNTS = {"train": 22180, "val": 2693, "test": 2685}
ENVIRONMENT = {"source_sha256": "0" * 64, "python": "3.12", "tensorflow": "2.17.1",
               "packages": {"keras": "3"}, "determinism_environment": {}}


def frozen_row(campaign_id=None):
    catalog = cc.catalog()
    configuration = next(p for p in catalog["presets"] if p["id"] == "system_batch_defaults")["configuration"]
    configuration["models"], configuration["optimizers"], configuration["seeds"] = ["custom_cnn", "vgg16"], ["adam"], [11, 29]
    configuration["variants"][0]["parameters"].pop("densenet121")
    result = cc.resolve(configuration, COUNTS)
    assert result["valid"], result["errors"]
    dataset = {"dataset_version_id": DATASET, "counts": COUNTS, "dataset_materialization_id": str(uuid4())}
    contract = frozen_contract(name="n", purpose="p", experiment_id=None, dataset=dataset, evidence_id=uuid4(),
                               requested=result["request"], protocol=result["protocol"], environment=ENVIRONMENT,
                               matrix=result["matrix"])
    campaign_id = campaign_id or str(uuid4())
    members = [dict(m, id=uuid4(), state="pending", accepted_attempt_id=None) for m in result["matrix"]["members"]]
    return dict(id=campaign_id, name="n", purpose="p", state="frozen", contract=contract, contract_hash="h" * 64,
                frozen_at="2026-09-30", dataset_version_id=DATASET, dataset_snapshot=dataset,
                dataset_evidence_id=contract["dataset_evidence_id"], environment=ENVIRONMENT,
                expected_count=len(members), members=members, attempts=[], configurations=[]), result


class FakeRepository:
    """Records every call; claim/finish/pause would mean an execution attempt."""

    def __init__(self, row):
        self.row, self.calls = row, []

    def get(self, campaign_id, dataset_version_id=None):
        self.calls.append(("get", dataset_version_id))
        if dataset_version_id is not None and dataset_version_id != str(self.row["dataset_version_id"]):
            raise CampaignError("CAMPAIGN_DATASET_CONFLICT")
        return self.row

    @contextmanager
    def transaction(self, readonly=False):
        assert readonly, "plan must only open read-only transactions"

        class Result:
            def scalar_one(self):
                return 0

        class Connection:
            def execute(self, *args, **kwargs):
                return Result()

        yield Connection()

    def __getattr__(self, name):  # claim, finish, pause, resume, summary...
        raise AssertionError("EXECUTION_METHOD_CALLED:" + name)


def test_campaign_id_is_required_and_modes_are_exclusive():
    with pytest.raises(SystemExit):
        executor.parse_args(["--dataset-version-id", DATASET])
    with pytest.raises(SystemExit):
        executor.parse_args(["--campaign-id", str(uuid4()), "--plan", "--resume"])
    args = executor.parse_args(["--campaign-id", str(uuid4()), "--plan"])
    assert args.plan and args.dataset_version_id is None




def test_plan_resolves_without_execution(monkeypatch, capsys):
    row, result = frozen_row()
    repo = FakeRepository(row)
    monkeypatch.setattr(executor, "ExecutionRepository", lambda: repo)
    monkeypatch.setattr("src.malaria_dl.campaigns.plan.execution_readiness",
                        lambda repository, r: {"ready": False, "checks": []})
    monkeypatch.setattr(executor, "execute_campaign", lambda *a, **k: pytest.fail("TRAIN boundary crossed"))
    assert executor.main(["--campaign-id", row["id"], "--plan"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["campaign_id"] == row["id"] and plan["dataset_version_id"] == DATASET
    assert plan["total_experiments"] == result["summary"]["total_experiments"] == 4
    assert plan["command"] == f"python -m src.train --campaign-id {row['id']}"
    assert [c for c in repo.calls if c[0] != "get"] == []


def test_plan_rejects_a_contradicting_dataset(monkeypatch):
    row, _ = frozen_row()
    monkeypatch.setattr(executor, "ExecutionRepository", lambda: FakeRepository(row))
    with pytest.raises(CampaignError, match="CAMPAIGN_DATASET_CONFLICT"):
        executor.main(["--campaign-id", row["id"], "--plan", "--dataset-version-id", OTHER])


def test_execution_takes_the_dataset_from_the_campaign(monkeypatch):
    row, _ = frozen_row()
    repo = FakeRepository(row)
    seen = {}

    class Gate:
        def __init__(self, *a):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def boundary(repository, campaign_id, root, **kwargs):
        seen.update(kwargs, campaign_id=campaign_id)
        return 0, {"state": "frozen", "expected": 4, "members": dict(
            verified=0, failed=0, interrupted=0, pending=4)}

    monkeypatch.setattr(executor, "ExecutionRepository", lambda: repo)
    monkeypatch.setattr("src.malaria_dl.execution.global_gate.GlobalGate", Gate)
    monkeypatch.setattr(executor, "execute_campaign", boundary)
    assert executor.main(["--campaign-id", row["id"]]) == 0
    assert seen["dataset"] == DATASET and seen["campaign_id"] == row["id"]
    # No --resume needed: an interrupted/paused campaign continues on rerun.
    assert seen["resume"] is True and seen["revision_id"] is None


def test_resolved_plan_matches_the_configuration():
    row, result = frozen_row()
    plan = resolve_plan(row)
    assert plan["models"] == ["custom_cnn", "vgg16"] and plan["optimizers"] == ["adam"] and plan["seeds"] == [11, 29]
    assert len(plan["configurations"]) == result["summary"]["configurations"] == 2
    assert [e["position"] for e in plan["experiments"]] == list(range(4))
    assert {(e["model_id"], e["seed"]) for e in plan["experiments"]} == {
        ("custom_cnn", 11), ("custom_cnn", 29), ("vgg16", 11), ("vgg16", 29)}
    assert plan["experiments_per_model"] == {"custom_cnn": 2, "vgg16": 2}
    by_model = {c["model_id"]: c for c in plan["configurations"]}
    assert by_model["custom_cnn"]["execution"]["max_epochs"] == 100
    assert by_model["vgg16"]["execution"]["fine_tune_epochs"] == 20


def test_draft_campaign_has_no_plan():
    row, _ = frozen_row()
    row["state"] = "draft"
    with pytest.raises(CampaignError, match="CAMPAIGN_NOT_FROZEN"):
        resolve_plan(row)


def test_command_uses_only_the_campaign_id():
    campaign_id = str(uuid4())
    assert execution_command(campaign_id) == f"python -m src.train --campaign-id {campaign_id}"
    assert "--dataset-version-id" not in execution_command(campaign_id)
    with pytest.raises(CampaignError):
        execution_command("not-a-uuid")


def test_runtime_difference_is_recorded_not_enforced(monkeypatch):
    row, _ = frozen_row()

    class Snapshot:
        def metadata(self):
            return dict(row["dataset_snapshot"])

    monkeypatch.setattr("src.malaria_dl.data.governed_dataset.assert_run_dataset_snapshot_unchanged",
                        lambda a, b: None)
    report = execution_readiness(FakeRepository(row), row, environment=lambda: dict(ENVIRONMENT, python="3.13"),
                                 dataset_resolver=lambda _id: Snapshot())
    status = {c["check"]: c for c in report["checks"]}
    # A different runtime (e.g. local macOS venv vs Docker) is information, not a barrier;
    # an empty model catalog is filled on the first claim.
    assert report["ready"]
    assert status["code_environment_identity"] == dict(
        check="code_environment_identity", status="INFO", code=None, differing_keys=["python"])
    assert status["model_catalog_identity"]["status"] == "PASS"
    assert status["test_forbidden"]["status"] == "PASS"
    assert "e10_schema" not in status


def test_paused_campaign_is_executable_and_duplicate_catalog_rows_are_not(monkeypatch):
    row, _ = frozen_row()
    row["state"] = "paused"

    class Snapshot:
        def metadata(self):
            return dict(row["dataset_snapshot"])

    class Duplicates(FakeRepository):
        @contextmanager
        def transaction(self, readonly=False):
            class Result:
                def scalar_one(self):
                    return 2

            class Connection:
                def execute(self, *args, **kwargs):
                    return Result()

            yield Connection()

    monkeypatch.setattr("src.malaria_dl.data.governed_dataset.assert_run_dataset_snapshot_unchanged",
                        lambda a, b: None)
    report = execution_readiness(Duplicates(row), row, environment=lambda: dict(ENVIRONMENT),
                                 dataset_resolver=lambda _id: Snapshot())
    status = {c["check"]: c for c in report["checks"]}
    assert status["campaign_state_executable"]["status"] == "PASS"
    assert status["model_catalog_identity"]["code"] == "CANONICAL_MODEL_CATALOG_IDENTITY_REQUIRED"
    assert not report["ready"]


def test_default_dataset_resolver_checks_train_and_val_like_dry_run(monkeypatch):
    """Without an injected resolver the readiness uses the governed resolver with explicit splits."""
    from src.malaria_dl.data import governed_dataset
    row, _ = frozen_row()
    calls = []

    class Snapshot:
        def metadata(self):
            return dict(row["dataset_snapshot"])

    def resolve(version, *, required_splits=None, test_authorized=False):
        calls.append((version, required_splits))
        # The real resolver rejects a missing scope (DATASET_REQUIRED_SPLITS_REQUIRED).
        governed_dataset.normalize_required_splits(required_splits, test_authorized=test_authorized)
        return Snapshot()

    monkeypatch.setattr(governed_dataset, "resolve_governed_dataset", resolve)
    monkeypatch.setattr(governed_dataset, "assert_run_dataset_snapshot_unchanged", lambda a, b: None)
    report = execution_readiness(FakeRepository(row), row, environment=lambda: dict(ENVIRONMENT))
    status = {c["check"]: c for c in report["checks"]}
    assert calls == [(str(row["dataset_version_id"]), ("train", "val"))]
    assert status["dataset_snapshot_unchanged"] == dict(check="dataset_snapshot_unchanged", status="PASS", code=None)
    assert report["ready"]


@pytest.mark.parametrize("field", ["name", "purpose", "actor"])
def test_configure_rejects_blank_identity_before_writing_dataset_evidence(field):
    from src.malaria_dl.campaigns.service import CampaignService

    _, result = frozen_row()

    class NoDatabase:
        def __getattr__(self, name):
            raise AssertionError("REPOSITORY_CALLED:" + name)

    def verifier(*a, **k):
        raise AssertionError("DATASET_EVIDENCE_WOULD_BE_WRITTEN")

    values = dict(name="n", purpose="p", actor="a")
    values[field] = "   "
    with pytest.raises(CampaignError, match="CAMPAIGN_NAME_PURPOSE_ACTOR_REQUIRED"):
        CampaignService(repository=NoDatabase(), verifier=verifier, environment=dict).configure(
            campaign_id=str(uuid4()), dataset_version_id=DATASET, request=result["request"],
            protocol=result["protocol"], **values)


@pytest.fixture(autouse=True)
def synthetic_catalog(monkeypatch):
    from src.malaria_dl.models import registry
    monkeypatch.setattr(registry, "model_catalog", lambda: tuple(
        {"name": name, "architecture": name, "model_type": "classification", "framework": "tensorflow/keras"}
        for name in registry.MODEL_REGISTRY))
