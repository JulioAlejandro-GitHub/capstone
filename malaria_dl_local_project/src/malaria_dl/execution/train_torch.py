"""Campaign TRAIN of BiomedCLIP heads with PyTorch on the local Apple GPU.

Same scientific records, E10 events, selection policy, VAL calibration and completion as the
Keras engine (``execution.train``); only the computation differs. TRAIN feeds optimization,
VAL feeds selection/stopping/calibration, TEST is never opened.

Linear probing (``recipe.encoder == "frozen"``) extracts TRAIN/VAL embeddings once per RUN
and trains only the head. Fine-tuning trains the head with the encoder frozen (``base``)
and then the last ``fine_tune_layers`` ViT blocks (``fine_tuning``) at their own learning rate.
EarlyStopping and ReduceLROnPlateau reproduce the Keras callbacks the Keras engine uses.
"""
from __future__ import annotations

import math
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ..campaigns.contracts import CampaignError, digest
from .artifacts import file_identity

IMAGE_SUFFIXES = (".bmp", ".gif", ".jpeg", ".jpg", ".png")
# Keras-only optimizer options without a PyTorch counterpart in this engine: defaults only.
KERAS_ONLY = {"clipnorm": None, "global_clipnorm": None, "clipvalue": None, "use_ema": False,
              "ema_overwrite_frequency": None, "loss_scale_factor": None, "gradient_accumulation_steps": None}


def directory_samples(root, split):
    """(relative path, label) in the Keras loader order: class_names order, then sorted names."""
    from src.config import CLASS_NAMES

    samples = []
    for label, name in enumerate(CLASS_NAMES):
        directory = Path(root) / split / name
        for path in sorted(p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES):
            samples.append((str(path.relative_to(root)), label))
    if not samples:
        raise CampaignError("DATASET_SPLIT_EMPTY")
    return samples


def load_image(root, relative, transform, flips):
    from PIL import Image

    with Image.open(Path(root) / relative) as image:
        image = image.convert("RGB")
        if flips[0]:  # recipe.augmentation flip: label-preserving for single cells
            image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if flips[1]:
            image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        return transform(image)


class ThreadedBatches:
    """Decode and transform with a thread pool, one batch ahead of the GPU.

    Threads, not worker processes: PIL and the tensor transform release the GIL, and the
    TRAIN child leaves no descendant for the global gate. Order and augmentation draws are
    decided in the calling thread from the RUN generator, so results are deterministic.
    """

    def __init__(self, root, samples, transform, batch_size, workers):
        from concurrent.futures import ThreadPoolExecutor

        self.root, self.samples, self.transform, self.batch_size = str(root), samples, transform, batch_size
        self.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="capstone-images")

    def __call__(self, shuffle=False, augment=False, generator=None):
        import torch

        n = len(self.samples)
        order = torch.randperm(n, generator=generator).tolist() if shuffle else list(range(n))
        flips = (torch.rand((n, 2), generator=generator) < 0.5).tolist() if augment else [[False, False]] * n
        batches = [order[i:i + self.batch_size] for i in range(0, n, self.batch_size)]

        def submit(indices):
            return [self.pool.submit(load_image, self.root, self.samples[i][0], self.transform, flips[i])
                    for i in indices]

        pending = submit(batches[0]) if batches else None
        for position, indices in enumerate(batches):
            current, pending = pending, submit(batches[position + 1]) if position + 1 < len(batches) else None
            images = torch.stack([future.result() for future in current])
            labels = torch.tensor([float(self.samples[i][1]) for i in indices])
            yield images, labels

    def close(self):
        self.pool.shutdown(wait=True, cancel_futures=True)


def optimizer(name, parameters, groups):
    """PyTorch optimizer for a persisted Keras-named configuration; never a silent reinterpretation."""
    import torch

    for key, default in KERAS_ONLY.items():
        if parameters.get(key, default) != default:
            raise CampaignError("UNSUPPORTED_OPTIMIZER_PARAMETER_FOR_TORCH:" + key)
    decay = parameters.get("weight_decay")
    if name != "adamw" and decay is not None:
        # Keras applies decoupled decay for every optimizer; only AdamW has it in PyTorch.
        raise CampaignError("UNSUPPORTED_OPTIMIZER_PARAMETER_FOR_TORCH:weight_decay")
    if name == "adamw":
        return torch.optim.AdamW(groups, betas=(parameters["beta_1"], parameters["beta_2"]), eps=parameters["epsilon"],
                                 amsgrad=parameters["amsgrad"], weight_decay=decay or 0.0)
    if name == "adam":
        return torch.optim.Adam(groups, betas=(parameters["beta_1"], parameters["beta_2"]), eps=parameters["epsilon"],
                                amsgrad=parameters["amsgrad"])
    if name == "sgd":
        return torch.optim.SGD(groups, momentum=parameters["momentum"], nesterov=parameters["nesterov"])
    if name == "adadelta":
        return torch.optim.Adadelta(groups, rho=parameters["rho"], eps=parameters["epsilon"])
    raise CampaignError("UNKNOWN_OPTIMIZER:" + str(name))


class EarlyStopping:
    """keras.callbacks.EarlyStopping on val_early_stopping_score, mode max (Keras 3 semantics)."""

    def __init__(self, patience, min_delta, restore_best_weights):
        self.patience, self.min_delta, self.restore = patience, min_delta, restore_best_weights
        self.best, self.best_epoch, self.stopped_epoch, self.wait, self.best_state = -math.inf, 0, 0, 0, None

    def update(self, epoch, current, model):
        """True when training must stop after this phase epoch (0-based ``epoch``)."""
        if current is None:
            return False
        if self.restore and self.best_state is None:
            self.best_state, self.best_epoch = snapshot(model), epoch
        self.wait += 1
        if current - self.min_delta > self.best:
            self.best, self.best_epoch, self.wait = current, epoch, 0
            if self.restore:
                self.best_state = snapshot(model)
            return False
        if self.wait >= self.patience and epoch > 0:
            self.stopped_epoch = epoch
            return True
        return False

    def finish(self, model):
        if self.restore and self.best_state is not None:
            restore(model, self.best_state)


def snapshot(model):
    return {n: p.detach().clone() for n, p in model.named_parameters() if p.requires_grad}


def restore(model, state):
    import torch

    parameters = dict(model.named_parameters())
    with torch.no_grad():
        for name, value in state.items():
            parameters[name].copy_(value)


def train(repository, session: dict, descriptor, *, event_emitter=None) -> None:
    from ..models import biomedclip_training as biomedclip

    device = biomedclip.device()
    import random

    import numpy as np
    import torch

    from ..data.governed_dataset import local_dataset_root

    started_at = datetime.now(timezone.utc).isoformat()
    config = session["configuration"]
    r = config["resolved"]
    e, recipe, contract = r["execution"], r["recipe"], r["input_contract"]
    if e["evaluate_best_on_test"] is not False:
        raise CampaignError("TEST_FORBIDDEN")
    root = Path(session["artifact_root"])
    root.mkdir(parents=True, exist_ok=False)
    random.seed(e["seed"])
    np.random.seed(e["seed"])
    torch.manual_seed(e["seed"])
    if e["deterministic_ops"]:
        torch.use_deterministic_algorithms(True)
    dataset_root = local_dataset_root(session["dataset"]["dataset_root"])
    samples = {split: directory_samples(dataset_root, split) for split in ("train", "val")}
    sample_paths = [relative for relative, _ in samples["val"]]
    if len(sample_paths) != session["dataset"]["counts"]["val"]:
        raise CampaignError("VALIDATION_POPULATION_CONFLICT")
    val_labels = np.array([label for _, label in samples["val"]], dtype=np.float32)
    files = biomedclip.base_files(contract["external"]["base_model"])
    model, transform = biomedclip.build(files)
    model.to(device)
    frozen = recipe["encoder"] == "frozen"
    augment = not e["no_augment"] and bool(recipe["augmentation"])  # {}: no augmentation
    if frozen and augment:
        raise CampaignError("FROZEN_EMBEDDINGS_FORBID_AUGMENTATION")
    workers = max(1, (os.cpu_count() or 2) - 1)
    generator = torch.Generator().manual_seed(e["seed"])
    loaders = {split: ThreadedBatches(dataset_root, samples[split], transform, e["batch_size"], workers)
               for split in ("train", "val")}
    try:
        _run(repository, session, config, model, device, files, samples, sample_paths, val_labels, frozen,
             augment, workers, generator, loaders, event_emitter, biomedclip, started_at)
    finally:
        for loader in loaders.values():
            loader.close()


def _run(repository, session, config, model, device, files, samples, sample_paths, val_labels, frozen,
         augment, workers, generator, loaders, event_emitter, biomedclip, started_at):
    import numpy as np
    import torch

    from ..training.checkpoint_policy import (
        CheckpointPolicyConfig,
        clinical_validation_logs,
        select_best_epoch_by_monitor,
        select_best_epoch_from_history,
    )
    from .train import finish_training, recorder

    run, owner = str(session["run_id"]), str(session["owner"])
    r = config["resolved"]
    e, sel, recipe, contract = r["execution"], r["selection"], r["recipe"], r["input_contract"]
    root = Path(session["artifact_root"])

    def embeddings(split):
        model.eval()
        chunks = []
        with torch.inference_mode():
            for images, _ in loaders[split]():
                chunks.append(model.embed(images.to(device)))
        return torch.cat(chunks)

    cache = {split: embeddings(split) for split in ("train", "val")} if frozen else None
    train_labels = torch.tensor([label for _, label in samples["train"]], dtype=torch.float32, device=device)
    loss_function = torch.nn.BCEWithLogitsLoss()
    policy = CheckpointPolicyConfig(
        policy=e["checkpoint_policy"], min_recall=e["min_recall"], beta=e["beta"], threshold=0.5,
        reject_prediction_collapse=e["reject_prediction_collapse"], min_class_fraction=e["min_class_fraction"])
    put = recorder(repository, run, owner, e, event_emitter)
    history, selection, epoch_offset = [], None, 0
    identity = {"architecture": config["model_id"], "base_model": contract["external"]["base_model"],
                "embedding": contract["external"]["embedding"],
                "fine_tune_layers": r["model"]["fine_tune_layers"]}

    def val_scores():
        model.eval()
        with torch.inference_mode():
            if frozen:
                logits = model.head(cache["val"])
            else:
                logits = torch.cat([model(images.to(device)) for images, _ in loaders["val"]()])
        logits = logits.reshape(-1).float().cpu()
        loss = float(loss_function(logits, torch.from_numpy(val_labels)))
        return torch.sigmoid(logits).numpy().astype(np.float64), loss

    def train_epoch(optimizer_, encoder_trainable):
        model.train()
        if not encoder_trainable:
            model.visual.eval()  # frozen encoder: inference statistics, no dropout
        total, correct, count = 0.0, 0, 0
        if frozen:
            order = torch.randperm(len(samples["train"]), generator=generator).to(device)
            batches = ((cache["train"][i], train_labels[i]) for i in order.split(e["batch_size"]))
        else:
            batches = ((x.to(device), y.to(device)) for x, y in loaders["train"](True, augment, generator))
        for inputs, labels in batches:
            optimizer_.zero_grad(set_to_none=True)
            if frozen:
                logits = model.head(inputs)
            elif encoder_trainable:
                logits = model(inputs)
            else:
                with torch.no_grad():
                    embedded = model.embed(inputs)
                logits = model.head(embedded)
            logits = logits.reshape(-1)
            loss = loss_function(logits, labels)
            if not torch.isfinite(loss):
                raise CampaignError("NONFINITE_TRAIN_LOSS")
            loss.backward()
            optimizer_.step()
            total += float(loss.detach()) * len(labels)
            correct += int(((logits.detach() >= 0) == (labels >= 0.5)).sum())
            count += len(labels)
        return total / count, correct / count

    phases = [("base", e["max_epochs"])]
    if e["fine_tune_epochs"]:
        phases.append(("fine_tuning", e["fine_tune_epochs"]))
    trained = []
    for phase, epochs in phases:
        encoder_trainable = phase == "fine_tuning"
        names = biomedclip.trainable_names(model, r["model"]["fine_tune_layers"] if encoder_trainable else 0)
        names = biomedclip.set_trainable(model, names)
        trained = sorted(set(trained) | set(names))
        parameters = dict(model.named_parameters())
        o = r["optimizer"]
        head = [parameters[n] for n in names if n.startswith("head.")]
        encoder = [parameters[n] for n in names if not n.startswith("head.")]
        groups = [{"params": head, "lr": o["parameters"]["learning_rate"], "name": "head"}]
        if encoder:
            groups.append({"params": encoder, "lr": o["fine_tune_learning_rate"], "name": "encoder"})
        optimizer_ = optimizer(o["name"], o["parameters"], groups)
        reduce = recipe["reduce_lr"]
        if reduce["monitor"] != "val_loss":
            raise CampaignError("UNSUPPORTED_REDUCE_LR_MONITOR")
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer_, mode="min", factor=reduce["factor"], patience=reduce["patience"],
            threshold=1e-4, threshold_mode="abs", min_lr=reduce["min_lr"])  # Keras min_delta=1e-4
        stopper = EarlyStopping(e["early_stopping_patience"], e["early_stopping_min_delta"],
                                e["restore_best_weights"]) if e["early_stopping"] else None
        callbacks = [{"type": "ClinicalValidationMetricsCallback", "monitor": None}]
        if stopper:
            callbacks.append({"type": "EarlyStopping", "monitor": "val_early_stopping_score"})
        callbacks += [{"type": "ReduceLROnPlateau", "monitor": "val_loss"}, {"type": "PersistEpoch", "monitor": None}]
        runtime = {
            "framework": "pytorch", "device": str(device), "phase": phase,
            "optimizer": {"name": o["name"], "groups": [{"name": g["name"], "lr": g["lr"],
                                                         "parameters": sum(p.numel() for p in g["params"])}
                                                        for g in groups]},
            "trainable_parameters": {"names_sha256": digest(names), "count": len(names),
                                     "elements": sum(parameters[n].numel() for n in names)},
            "encoder": "frozen" if not encoder_trainable else f"last_{r['model']['fine_tune_layers']}_blocks",
            "embedding_cache": "per_run_memory" if frozen else "none", "augmentation": augment,
            "data_loader": {"kind": "thread_pool_prefetch", "workers": workers, "batch_size": e["batch_size"]},
            "base_model": {"checkpoint": {k: files["checkpoint"][k] for k in ("sha256", "bytes")},
                           "dependencies": [{k: d[k] for k in ("role", "artifact_id", "sha256", "bytes")}
                                            for d in files["dependencies"]]},
            "callbacks": callbacks,
        }
        if phase == "base":
            from .campaign import runtime_environment

            runtime.update(runtime_environment={**runtime_environment(), "accelerator": {
                "framework": "pytorch", "torch": torch.__version__, "device": str(device),
                "mps_fallback": os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK")}}, started_at=started_at)
        put("runtime", phase, "configuration", runtime)
        count = 0
        for epoch in range(epochs):
            loss, accuracy = train_epoch(optimizer_, encoder_trainable)
            scores, val_loss = val_scores()
            logs = {"loss": loss, "accuracy": accuracy, "val_loss": val_loss,
                    "val_accuracy": float(((scores >= 0.5) == (val_labels >= 0.5)).mean())}
            clinical_validation_logs(
                logs, val_labels.astype(int), scores, threshold=0.5, min_class_fraction=e["min_class_fraction"],
                checkpoint_policy_config=policy, early_stopping_monitor=sel["early_stopping_monitor"],
                early_stopping_mode=sel["early_stopping_mode"])
            stop = stopper.update(epoch, logs.get("val_early_stopping_score"), model) if stopper else False
            scheduler.step(val_loss)
            count = epoch + 1
            global_epoch = epoch_offset + count
            row = dict(logs, epoch=global_epoch, phase=phase, phase_epoch=count,
                       learning_rate=float(optimizer_.param_groups[0]["lr"]))
            put("epoch", phase, count, row)
            history.append(row)
            selection = (select_best_epoch_by_monitor(history, policy, sel["monitor"], sel["mode"])
                         if sel["explicit"] else select_best_epoch_from_history(history, policy))
            path = root / f"epoch_{global_epoch}.pt"
            put("artifact_prepared", phase, count, {"path": str(path), "epoch": global_epoch, "run_id": run})
            biomedclip.save_checkpoint(path, model, trained, identity)
            put("artifact", phase, count, dict(path=str(path), epoch=global_epoch, phase=phase, phase_epoch=count,
                                               run_id=run, version_id=str(uuid4()), **file_identity(path)))
            put("selection", phase, count, selection)
            put("predictions", phase, count, {"role": "val", "epoch": global_epoch, "samples": [
                {"sample": p, "label": int(y), "score": float(s)}
                for p, y, s in zip(sample_paths, val_labels, scores)]})
            if stop:
                break
        if stopper:
            stopper.finish(model)
        put("phase", phase, "completed", {"epochs": count, "early_stopping": [
            {"stopped_epoch": stopper.stopped_epoch, "best_epoch": stopper.best_epoch}] if stopper else []})
        epoch_offset += count
    if selection is None:
        raise CampaignError("NO_CHECKPOINT_SELECTED")

    def selected_scores():
        # The selected checkpoint is reloaded from its file, never the in-memory state.
        selected, _ = biomedclip.load_classifier(root / f"epoch_{selection['selected_epoch']}.pt", contract)
        nonlocal model
        model = selected.to(device)
        scores, _ = val_scores()
        return val_labels.astype(int), scores

    finish_training(repository, run, owner, config, history, selection, sample_paths,
                    selected_scores, put, event_emitter)
