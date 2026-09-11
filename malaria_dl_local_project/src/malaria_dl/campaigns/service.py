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
from .repository import CampaignRepository, identifier


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
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "git_commit": result.stdout.strip() if result.returncode == 0 else None,
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
        snapshot = self.verifier(dataset_version_id, consumer="campaigns.create")
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
        )
        assert_run_dataset_snapshot_unchanged(snapshot, row["dataset_snapshot"])
        # Keep original immutable evidence reference; recheck event remains append-only evidence.
        contract = {
            "version": "campaign_contract_v1",
            "name": row["name"],
            "purpose": row["purpose"],
            "experiment_id": str(row["experiment_id"])
            if row["experiment_id"]
            else None,
            "dataset": row["dataset_snapshot"],
            "dataset_evidence_id": str(row["dataset_evidence_id"]),
            "requested": row["requested"],
            "protocol": row["protocol"],
            "environment": row["environment"],
            "matrix": matrix,
        }
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
