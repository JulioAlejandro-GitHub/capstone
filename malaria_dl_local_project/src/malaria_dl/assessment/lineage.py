"""Resolve evidence, never latest/version order/folder names."""

from collections import Counter
from pathlib import Path
from uuid import UUID, uuid5

from ..campaigns.contracts import CampaignError
from ..campaigns.repository import execute, identifier
from ..data.governed_dataset import (
    assert_run_dataset_snapshot_unchanged,
    resolve_governed_dataset,
    training_dataset_metadata,
)
from ..data.input_contract import resolve_checkpoint_input, validate_input_contract
from ..execution.artifacts import file_identity, verify_session
from ..execution.repository import ExecutionRepository
from ..persistence.dataset_evidence import verify_dataset_for_execution
from .contracts import require


def resolve(repository, training_run_id=None, model_version_id=None):
    require(training_run_id or model_version_id, "EXPLICIT_MODEL_IDENTITY_REQUIRED")
    with repository.transaction(readonly=True) as c:
        if training_run_id:
            rows = list(
                execute(
                    c,
                    "SELECT * FROM train_execution_sessions WHERE run_id=CAST(:id AS uuid)",
                    id=identifier(training_run_id),
                ).mappings()
            )
        else:
            rows = list(
                execute(
                    c,
                    "SELECT * FROM train_execution_sessions WHERE verification->'artifact'->>'version_id'=:id",
                    id=identifier(model_version_id),
                ).mappings()
            )
    require(len(rows) <= 1, "AMBIGUOUS_MODEL_VERSION")
    if rows:
        session = dict(rows[0])
        require(session["state"] == "verified", "TRAIN_NOT_VERIFIED")
        # Revalidate immutable E5 structured records and binary. Model load follows after protocol guard.
        train_repo = ExecutionRepository(repository.scope)
        proof = verify_session(train_repo, session, lambda path, contract: None)
        require(proof == session["verification"], "TRAIN_VERIFICATION_CONFLICT")
        artifact = proof["artifact"]
        version = identifier(artifact["version_id"])
        require(
            not model_version_id or identifier(model_version_id) == version,
            "MODEL_VERSION_TRAIN_CONFLICT",
        )
        records = train_repo.records(session["run_id"])
        calibration = [
            r["payload"]
            for r in records
            if (r["kind"], r["phase"], r["record_key"])
            == ("calibration", "val", "selected")
        ]
        require(len(calibration) == 1, "CALIBRATION_REFERENCE_AMBIGUOUS")
        require(
            calibration[0].get("checkpoint_epoch") == artifact["epoch"],
            "CALIBRATION_CHECKPOINT_CONFLICT",
        )
        binding = {
            "training_run_id": str(session["run_id"]),
            "model_version_id": version,
            "checkpoint_artifact_id": str(
                uuid5(UUID(version), "e5-selected-checkpoint")
            ),
            "path": artifact["path"],
            "sha256": artifact["sha256"],
            "bytes": artifact["bytes"],
            "input_contract": validate_input_contract(
                session["configuration"]["resolved"]["input_contract"]
            ),
            "source": {
                "kind": "e5_selected_record",
                "records_hash": proof["records_hash"],
                "epoch": artifact["epoch"],
            },
        }
        return binding, session["dataset"], calibration[0]
    # Historical consultation is unchanged. New execution requires the original complete evidence.
    from contextlib import contextmanager

    from ..governance.services.model_version_resolver import ModelVersionResolver

    @contextmanager
    def connection():
        with repository.transaction(readonly=True) as c:
            yield c

    old = ModelVersionResolver(connection).resolve(
        model_version_id=model_version_id, source_training_run_id=training_run_id
    )
    require(old is not None, "HISTORICAL_MODEL_EVIDENCE_REQUIRED")
    with repository.transaction(readonly=True) as c:
        a = (
            execute(
                c,
                "SELECT run_id,path,file_size_bytes,checksum FROM artifacts WHERE id=CAST(:id AS uuid)",
                id=identifier(old.checkpoint_artifact_id),
            )
            .mappings()
            .one_or_none()
        )
    require(
        a is not None and str(a["run_id"]) == old.source_training_run_id,
        "CHECKPOINT_ARTIFACT_OWNERSHIP_CONFLICT",
    )
    require(
        Path(a["path"]).resolve() == old.checkpoint_path.resolve()
        and a["checksum"] == old.checkpoint_sha256
        and file_identity(old.checkpoint_path)
        == {"sha256": a["checksum"], "bytes": a["file_size_bytes"]},
        "CHECKPOINT_ARTIFACT_CONTENT_CONFLICT",
    )
    contract = resolve_checkpoint_input(
        old.preprocessing,
        old.input_signature,
        old.output_signature,
        old.class_mapping,
        architecture=old.model_name,
    )
    return (
        {
            "training_run_id": old.source_training_run_id,
            "model_version_id": old.model_version_id,
            "checkpoint_artifact_id": old.checkpoint_artifact_id,
            "path": str(old.checkpoint_path),
            "sha256": old.checkpoint_sha256,
            "bytes": a["file_size_bytes"],
            "input_contract": contract,
            "source": {"kind": "legacy_registered_artifact"},
        },
        training_dataset_metadata(old.source_training_run_id),
        None,
    )


def dataset_samples(repository, inherited, split, override=None, *, inspection=False):
    require(
        override is None or identifier(override) == inherited["dataset_version_id"],
        "DATASET_OVERRIDE_CONFLICT",
    )
    snapshot = (
        resolve_governed_dataset(inherited["dataset_version_id"])
        if inspection
        else verify_dataset_for_execution(
            inherited["dataset_version_id"], consumer="assessment.e6"
        )
    )
    assert_run_dataset_snapshot_unchanged(snapshot, inherited)
    with repository.transaction(readonly=True) as c:
        rows = list(
            execute(
                c,
                """SELECT a.source_record_id,a.clinical_identity_id,a.split_name,r.class_name,r.source_filename,r.source_file_sha256
          FROM dataset_split_assignments a JOIN dataset_source_records r ON r.id=a.source_record_id
          WHERE a.dataset_version_id=CAST(:id AS uuid) ORDER BY a.source_record_id""",
                id=inherited["dataset_version_id"],
            ).mappings()
        )
    collisions = Counter(
        (r["split_name"], r["class_name"], r["source_filename"]) for r in rows
    )
    from ..data.dataset_integrity import materialized_relative_path

    samples = []
    for r in rows:
        if r["split_name"] != split:
            continue
        relative = materialized_relative_path(r, collisions).as_posix()
        path = Path(inherited["dataset_root"]) / relative
        require(
            file_identity(path)["sha256"] == r["source_file_sha256"],
            "SAMPLE_CONTENT_CHANGED",
        )
        samples.append(
            {
                "sample_id": str(r["source_record_id"]),
                "patient_id": str(r["clinical_identity_id"]),
                "split": split,
                "label": int(r["class_name"] == "parasitized"),
                "relative_path": relative,
                "sha256": r["source_file_sha256"],
            }
        )
    require(len(samples) == inherited["counts"][split], "SAMPLE_COUNT_CONFLICT")
    return samples


def campaign_inventory(repository, campaign_id, dataset_version_id=None):
    campaign = repository.get(campaign_id, dataset_version_id)
    require(
        campaign["state"] in ("frozen", "active", "paused", "finalized"),
        "CAMPAIGN_NOT_FROZEN",
    )
    attempts = {str(a["id"]): a for a in campaign["attempts"]}
    items = []
    for m in campaign["members"]:
        a = attempts.get(str(m["accepted_attempt_id"]))
        item = {
            "member_id": str(m["id"]),
            "state": m["state"],
            "eligible": False,
            "reason": "NO_VERIFIED_ACCEPTED_ATTEMPT",
        }
        if a and a["state"] == "verified" and str(a["member_id"]) == str(m["id"]):
            try:
                binding, dataset, _ = resolve(
                    repository, training_run_id=a["training_run_id"]
                )
                require(
                    dataset == campaign["dataset_snapshot"], "CAMPAIGN_DATASET_CONFLICT"
                )
                item.update(eligible=True, reason=None, model=binding)
            except CampaignError:
                item["reason"] = "ACCEPTED_TRAIN_EVIDENCE_INVALID_OR_UNAVAILABLE"
        items.append(item)
    return campaign, items
