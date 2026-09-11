"""Binary checkpoint verification; structured evidence remains in PostgreSQL."""

import hashlib
from pathlib import Path

from ..campaigns.contracts import CampaignError, digest


def file_identity(path):
    p = Path(path)
    if not p.is_file() or p.is_symlink() or p.name.endswith(".partial"):
        raise CampaignError("CHECKPOINT_NOT_FINALIZED")
    h = hashlib.sha256()
    with p.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return {"sha256": h.hexdigest(), "bytes": p.stat().st_size}


def verify_session(repository, session, loader):
    records = repository.records(session["run_id"])
    completion = session["completion"]
    if not completion or completion.get("records_hash") != digest(records):
        raise CampaignError("TRAIN_RESULTS_INCOMPLETE")
    epochs = [r for r in records if r["kind"] == "epoch"]
    artifacts = [r["payload"] for r in records if r["kind"] == "artifact"]
    if not epochs or len(epochs) != completion.get("epochs"):
        raise CampaignError("TRAIN_EPOCHS_INCOMPLETE")
    by_key = {(r["kind"], r["phase"], r["record_key"]): r["payload"] for r in records}
    phases = {r["phase"] for r in epochs}
    expected_phases = {"base"}
    if session["configuration"]["resolved"]["execution"]["fine_tune_epochs"]:
        expected_phases.add("fine_tuning")
    if phases != expected_phases or ("calibration", "val", "selected") not in by_key:
        raise CampaignError("TRAIN_PHASE_OR_CALIBRATION_INCOMPLETE")
    for phase in phases:
        phase_epochs = [r for r in epochs if r["phase"] == phase]
        if ("runtime", phase, "configuration") not in by_key or (
            "phase",
            phase,
            "completed",
        ) not in by_key:
            raise CampaignError("TRAIN_RUNTIME_INCOMPLETE")
        count = by_key[("phase", phase, "completed")]["epochs"]
        if count != len(phase_epochs) or {
            int(r["record_key"]) for r in phase_epochs
        } != set(range(1, count + 1)):
            raise CampaignError("TRAIN_EPOCH_SEQUENCE_INCOMPLETE")
        for epoch in phase_epochs:
            key = epoch["record_key"]
            for kind in ("artifact_prepared", "artifact", "selection", "predictions"):
                if (kind, phase, key) not in by_key:
                    raise CampaignError("TRAIN_EPOCH_EVIDENCE_INCOMPLETE")
            samples = by_key[("predictions", phase, key)]["samples"]
            if len(samples) != session["dataset"]["counts"]["val"] or len(
                {s["sample"] for s in samples}
            ) != len(samples):
                raise CampaignError("TRAIN_PREDICTIONS_INCOMPLETE")
    latest = max(epochs, key=lambda r: r["payload"]["epoch"])
    if (
        by_key[("selection", latest["phase"], latest["record_key"])]
        != completion["selection"]
    ):
        raise CampaignError("TRAIN_SELECTION_CONFLICT")
    selected = [
        a for a in artifacts if a["epoch"] == completion["selection"]["selected_epoch"]
    ]
    if len(selected) != 1:
        raise CampaignError("EXACT_CHECKPOINT_REQUIRED")
    artifact = selected[0]
    path = Path(artifact["path"])
    if not path.resolve().is_relative_to(
        Path(session["artifact_root"]).resolve()
    ) or artifact["run_id"] != str(session["run_id"]):
        raise CampaignError("CHECKPOINT_OWNERSHIP_CONFLICT")
    if file_identity(path) != {k: artifact[k] for k in ("sha256", "bytes")}:
        raise CampaignError("CHECKPOINT_CONTENT_CHANGED")
    try:
        loader(path, session["configuration"]["resolved"]["input_contract"])
    except CampaignError:
        raise
    except Exception:  # noqa: BLE001 -- sanitized artifact validation boundary
        raise CampaignError("CHECKPOINT_NOT_LOADABLE") from None
    return {
        "status": "verified",
        "records_hash": digest(records),
        "artifact": artifact,
        "selection": completion["selection"],
    }


def keras_loader(path, contract):
    import tensorflow as tf

    from ..data.input_contract import validate_model_input

    model = tf.keras.models.load_model(path, compile=False)
    validate_model_input(model, contract)
    if (
        model.output_shape != (None, 1)
        or getattr(model.layers[-1].activation, "__name__", None) != "sigmoid"
    ):
        raise CampaignError("CHECKPOINT_OUTPUT_CONTRACT_CONFLICT")
