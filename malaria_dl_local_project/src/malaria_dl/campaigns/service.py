"""E4 service: integrity accreditation and planning, never execution."""

import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
from pathlib import Path

from ..data.governed_dataset import assert_run_dataset_snapshot_unchanged
from ..persistence.dataset_evidence import verify_dataset_for_execution
from .contracts import CampaignError, expand_matrix
from .repository import CampaignRepository, identifier, same_configuration


def planning_environment():
    root = Path(__file__).resolve().parents[3]
    files = {}
    for directory in (root / "src", root / "configs"):
        for p in sorted(directory.rglob("*")):
            if p.is_file() and p.suffix in (".py", ".json"):
                files[str(p.relative_to(root))] = hashlib.sha256(
                    p.read_bytes()
                ).hexdigest()
    for p in sorted(root.glob("run_*.py")):
        files[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    # Runtime images may omit git. The file digest remains the execution
    # identity; an unavailable Git revision must never be invented.
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        git_commit = result.stdout.strip() if result.returncode == 0 else None
    except FileNotFoundError:
        git_commit = None
    return {
        "git_commit": git_commit,
        "source_sha256": hashlib.sha256(
            json.dumps(files, sort_keys=True).encode()
        ).hexdigest(),
        "python": platform.python_version(),
        "tensorflow": importlib.metadata.version("tensorflow"),
        "determinism_environment": {
            k: os.environ.get(k) for k in ("TF_DETERMINISTIC_OPS", "PYTHONHASHSEED")
        },
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("keras", "numpy", "SQLAlchemy", "psycopg")
        },
    }


def frozen_contract(*, name, purpose, experiment_id, dataset, evidence_id, requested, protocol,
                    environment, matrix):
    return {
        "version": "campaign_contract_v1",
        "name": name,
        "purpose": purpose,
        "experiment_id": str(experiment_id) if experiment_id else None,
        "dataset": dataset,
        "dataset_evidence_id": str(evidence_id),
        "requested": requested,
        "protocol": protocol,
        "environment": environment,
        "matrix": matrix,
    }


class CampaignService:
    def __init__(
        self,
        repository=None,
        verifier=verify_dataset_for_execution,
        environment=planning_environment,
    ):
        self.repository = repository or CampaignRepository()
        self.verifier = verifier
        self.environment = environment

    def inspect(self, request, protocol=None):
        return expand_matrix(request, protocol)

    def create(
        self,
        *,
        name,
        purpose,
        dataset_version_id,
        request,
        protocol,
        actor,
        experiment_id=None,
    ):
        dataset_version_id = identifier(dataset_version_id)
        self.inspect(request, protocol)
        snapshot = self.verifier(dataset_version_id, consumer="campaigns.create", required_splits=("train", "val"))
        return self.repository.create(
            name=name,
            purpose=purpose,
            dataset=snapshot.metadata(),
            evidence_id=snapshot.evidence_id,
            requested=request,
            protocol=protocol,
            environment=self.environment(),
            actor=actor,
            experiment_id=experiment_id,
        )

    def configure(self, *, campaign_id, name, purpose, dataset_version_id, request, protocol, actor):
        """SWV2.2: create an already frozen campaign in one transaction; never starts TRAIN.

        Same checks as create + freeze (protocol and matrix before any write, dataset evidence,
        planning environment), without a persisted intermediate draft. A retried campaign_id
        with identical decisions returns the stored campaign without new evidence.
        """
        campaign_id = identifier(campaign_id)
        dataset_version_id = identifier(dataset_version_id)
        # Every input check precedes the dataset verifier: it persists append-only evidence.
        if any(not isinstance(x, str) or not x.strip() for x in (name, purpose, actor)):
            raise CampaignError("CAMPAIGN_NAME_PURPOSE_ACTOR_REQUIRED")
        expand_matrix(request, protocol)
        try:
            stored = self.repository.get(campaign_id)
        except CampaignError as exc:
            if str(exc) != "CAMPAIGN_NOT_FOUND":
                raise
            stored = None
        if stored is not None:
            candidate = {"name": name, "purpose": purpose, "requested": request, "protocol": protocol,
                         "dataset": {"dataset_version_id": dataset_version_id}}
            if stored["state"] == "draft" or not same_configuration(stored["contract"], candidate):
                raise CampaignError("CAMPAIGN_ID_CONFLICT")
            return stored
        snapshot = self.verifier(dataset_version_id, consumer="campaigns.configure", required_splits=("train", "val"))
        dataset = snapshot.metadata()
        matrix = expand_matrix(request, protocol, frozen=True, dataset=dataset)
        contract = frozen_contract(
            name=name, purpose=purpose, experiment_id=None, dataset=dataset,
            evidence_id=snapshot.evidence_id, requested=request, protocol=protocol,
            environment=self.environment(), matrix=matrix,
        )
        return self.repository.create_frozen(campaign_id, contract, actor)

    def edit(self, campaign_id, request, protocol):
        self.inspect(request, protocol)
        return self.repository.edit(campaign_id, request, protocol)

    def validate(self, campaign_id):
        row = self.repository.get(campaign_id)
        if row["state"] != "draft":
            return row["contract"]["matrix"]
        return expand_matrix(
            row["requested"],
            row["protocol"],
            frozen=True,
            dataset=row["dataset_snapshot"],
        )

    def freeze(self, campaign_id, dataset_version_id=None):
        row = self.repository.get(campaign_id, dataset_version_id)
        if row["state"] != "draft":
            raise CampaignError("CAMPAIGN_NOT_DRAFT")
        matrix = expand_matrix(
            row["requested"],
            row["protocol"],
            frozen=True,
            dataset=row["dataset_snapshot"],
        )
        if self.environment() != row["environment"]:
            raise CampaignError("DRAFT_CODE_ENVIRONMENT_CHANGED_CREATE_NEW_DRAFT")
        snapshot = self.verifier(
            str(row["dataset_version_id"]),
            expected_evidence_id=str(row["dataset_evidence_id"]),
            consumer="campaigns.freeze",
            required_splits=("train", "val"),
        )
        assert_run_dataset_snapshot_unchanged(snapshot, row["dataset_snapshot"])
        # Keep original immutable evidence reference; recheck event remains append-only evidence.
        contract = frozen_contract(
            name=row["name"],
            purpose=row["purpose"],
            experiment_id=row["experiment_id"],
            dataset=row["dataset_snapshot"],
            evidence_id=row["dataset_evidence_id"],
            requested=row["requested"],
            protocol=row["protocol"],
            environment=row["environment"],
            matrix=matrix,
        )
        expected = {
            k: row[k]
            for k in (
                "name",
                "purpose",
                "experiment_id",
                "dataset_version_id",
                "dataset_snapshot",
                "dataset_evidence_id",
                "requested",
                "protocol",
                "environment",
            )
        }
        return self.repository.freeze(campaign_id, contract, expected)
