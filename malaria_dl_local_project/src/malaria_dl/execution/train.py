"""Campaign TRAIN from persisted configuration. No CSV or JSON sidecars."""

import os
from pathlib import Path
from uuid import uuid4

from ..campaigns.contracts import CampaignError, digest
from .artifacts import file_identity


def clean(value):
    import math

    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value


def train(repository, session, descriptor):
    import tensorflow as tf

    from src.metrics import collect_predictions

    from ..data.loaders import (
        make_image_dataset_from_directory,
        preprocess_physical_dataset,
    )
    from ..evaluation.threshold_calibration import find_threshold_for_target_recall
    from ..models.adapters import compile_phase
    from ..training.checkpoint_policy import (
        CheckpointPolicyConfig,
        ClinicalValidationMetricsCallback,
        select_best_epoch_by_monitor,
        select_best_epoch_from_history,
    )

    run, owner = str(session["run_id"]), str(session["owner"])
    config = session["configuration"]
    r = config["resolved"]
    e = r["execution"]
    sel = r["selection"]
    if e["evaluate_best_on_test"] is not False:
        raise CampaignError("TEST_FORBIDDEN")
    root = Path(session["artifact_root"])
    root.mkdir(parents=True, exist_ok=False)
    tf.keras.utils.set_random_seed(e["seed"])
    if e["deterministic_ops"]:
        tf.config.experimental.enable_op_determinism()
    datasets = {}
    sample_paths = []
    for role in ("train", "val"):
        raw = make_image_dataset_from_directory(
            Path(session["dataset"]["dataset_root"]) / role,
            r["model"]["input_shape"][0],
            e["batch_size"],
            role == "train",
            e["seed"],
        )
        if role == "val":
            sample_paths = [
                str(Path(p).relative_to(session["dataset"]["dataset_root"]))
                for p in raw.file_paths
            ]
        datasets[role] = preprocess_physical_dataset(
            raw,
            r["model"]["preprocessing"],
            augment=role == "train" and not e["no_augment"],
        )
    adapter = descriptor.create_adapter()
    built = adapter.build(r)
    model = built.model
    policy = CheckpointPolicyConfig(
        policy=e["checkpoint_policy"],
        min_recall=e["min_recall"],
        beta=e["beta"],
        threshold=0.5,
        reject_prediction_collapse=e["reject_prediction_collapse"],
        min_class_fraction=e["min_class_fraction"],
    )
    history = []
    selection = None
    epoch_offset = 0

    def put(kind, phase, key, payload):
        repository.put(run, owner, kind, phase, key, clean(payload))

    class PersistEpoch(tf.keras.callbacks.Callback):
        def on_epoch_end(self, epoch, logs=None):
            nonlocal selection
            global_epoch = epoch_offset + epoch + 1
            row = dict(
                clean(logs or {}),
                epoch=global_epoch,
                phase=phase,
                phase_epoch=epoch + 1,
                learning_rate=float(
                    tf.keras.backend.get_value(model.optimizer.learning_rate)
                ),
            )
            put("epoch", phase, epoch + 1, row)
            history.append(row)
            selection = (
                select_best_epoch_by_monitor(
                    history, policy, sel["monitor"], sel["mode"]
                )
                if sel["explicit"]
                else select_best_epoch_from_history(history, policy)
            )
            # Each epoch artifact is exclusive; a later selection never overwrites it.
            path = root / f"epoch_{global_epoch}.keras"
            partial = root / f"epoch_{global_epoch}.partial.keras"
            put(
                "artifact_prepared",
                phase,
                epoch + 1,
                {"path": str(path), "epoch": global_epoch, "run_id": run},
            )
            model.save(partial)
            if path.exists():
                raise CampaignError("ARTIFACT_ALREADY_EXISTS")
            os.rename(partial, path)
            artifact = dict(
                path=str(path),
                epoch=global_epoch,
                phase=phase,
                phase_epoch=epoch + 1,
                run_id=run,
                version_id=str(uuid4()),
                **file_identity(path),
            )
            put("artifact", phase, epoch + 1, artifact)
            put("selection", phase, epoch + 1, selection)
            # Preserve per-sample evidence consumed for validation; TEST is never loaded.
            labels, _, scores = collect_predictions(
                model, datasets["val"], threshold=0.5
            )
            if len(scores) != len(sample_paths):
                raise CampaignError("VALIDATION_POPULATION_CONFLICT")
            put(
                "predictions",
                phase,
                epoch + 1,
                {
                    "role": "val",
                    "epoch": global_epoch,
                    "samples": [
                        {"sample": path, "label": int(y), "score": float(score)}
                        for path, y, score in zip(sample_paths, labels, scores)
                    ],
                },
            )

    phases = [("base", e["max_epochs"])]
    if e["fine_tune_epochs"]:
        phases.append(("fine_tuning", e["fine_tune_epochs"]))
    for phase, epochs in phases:
        runtime = compile_phase(adapter, built, r, phase)
        clinical = ClinicalValidationMetricsCallback(
            datasets["val"],
            threshold=0.5,
            min_class_fraction=e["min_class_fraction"],
            checkpoint_policy_config=policy,
            early_stopping_monitor=sel["early_stopping_monitor"],
            early_stopping_mode=sel["early_stopping_mode"],
        )
        callbacks = [clinical]
        if e["early_stopping"]:
            callbacks.append(
                tf.keras.callbacks.EarlyStopping(
                    monitor="val_early_stopping_score",
                    mode="max",
                    patience=e["early_stopping_patience"],
                    min_delta=e["early_stopping_min_delta"],
                    restore_best_weights=e["restore_best_weights"],
                )
            )
        reduce = r["recipe"]["reduce_lr"]
        callbacks.append(tf.keras.callbacks.ReduceLROnPlateau(**reduce))
        callbacks.append(PersistEpoch())
        runtime["callbacks"] = [
            {"type": type(c).__name__, "monitor": getattr(c, "monitor", None)}
            for c in callbacks
        ]
        put("runtime", phase, "configuration", runtime)
        h = model.fit(
            datasets["train"],
            validation_data=datasets["val"],
            epochs=epochs,
            callbacks=callbacks,
        )
        count = len(h.epoch)
        put(
            "phase",
            phase,
            "completed",
            {
                "epochs": count,
                "early_stopping": [
                    {
                        "stopped_epoch": getattr(c, "stopped_epoch", None),
                        "best_epoch": getattr(c, "best_epoch", None),
                    }
                    for c in callbacks
                    if isinstance(c, tf.keras.callbacks.EarlyStopping)
                ],
            },
        )
        epoch_offset += count
    if selection is None:
        raise CampaignError("NO_CHECKPOINT_SELECTED")
    selected_path = root / f"epoch_{selection['selected_epoch']}.keras"
    selected = tf.keras.models.load_model(selected_path, compile=False)
    labels, _, scores = collect_predictions(selected, datasets["val"], threshold=0.5)
    calibration = (
        find_threshold_for_target_recall(
            labels,
            scores,
            target_recall=e["target_recall"],
            min_specificity=e["min_specificity"],
            beta=e["beta"],
        )
        if e["calibrate_threshold"]
        else {"enabled": False, "threshold": 0.5}
    )
    put(
        "calibration",
        "val",
        "selected",
        {
            "result": calibration,
            "checkpoint_epoch": selection["selected_epoch"],
            "samples": [
                {"sample": p, "label": int(y), "score": float(v)}
                for p, y, v in zip(sample_paths, labels, scores)
            ],
        },
    )
    records = repository.records(run)
    completion = {
        "epochs": len(history),
        "selection": selection,
        "records_hash": digest(records),
        "clinical_objective_met": bool(
            (selection.get("val_recall_parasitized") or 0) >= e["min_recall"]
            and (
                e["min_specificity"] is None
                or (selection.get("val_specificity") or 0) >= e["min_specificity"]
            )
        ),
    }
    repository.finish(run, owner, "completed", completion)


def standalone(args):
    """Individual TRAIN keeps an explicit dataset; no artificial campaign."""
    import socket

    from ..campaigns.service import planning_environment
    from ..models.registry import resolve_descriptor
    from ..persistence.dataset_evidence import verify_dataset_for_execution
    from .artifacts import keras_loader, verify_session
    from .repository import ExecutionRepository

    if args.evaluate_best_on_test or args.threshold_output_json:
        raise CampaignError("E5_TRAIN_TEST_OR_SIDECAR_FORBIDDEN")
    repo = ExecutionRepository()
    repo.preflight()
    snapshot = verify_dataset_for_execution(
        args.dataset_version_id,
        consumer="train.e5",
        dataset_dir=args.dataset_dir,
        data_source=args.data_source,
        expected_evidence_id=getattr(args, "expected_dataset_evidence_id", None),
    )
    session = repo.standalone(
        args.model_configuration,
        snapshot.metadata(),
        planning_environment(),
        args.output_dir or "outputs/train_runs",
        socket.gethostname(),
        os.getpid(),
        snapshot.evidence_id,
    )
    try:
        train(repo, session, resolve_descriptor(args.model))
        verified_snapshot = verify_dataset_for_execution(
            args.dataset_version_id,
            consumer="train.e5.finalize",
            expected_evidence_id=snapshot.evidence_id,
        )
        if verified_snapshot.metadata() != snapshot.metadata():
            raise CampaignError("DATASET_CHANGED_DURING_TRAIN")
        current = repo.session(session["run_id"])
        verification = verify_session(repo, current, keras_loader)
        repo.finish(session["run_id"], session["owner"], "verified", verification)
    except BaseException:
        current = repo.session(session["run_id"])
        if current["state"] == "active":
            repo.finish(
                session["run_id"],
                session["owner"],
                "failed",
                cause="INDIVIDUAL_TRAIN_FAILED",
            )
        raise
