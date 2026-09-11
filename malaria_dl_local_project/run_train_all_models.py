#!/usr/bin/env python3
"""Discover and validate the enabled registry matrix; no campaign persistence."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

from src.malaria_dl.data.governed_dataset import (
    dataset_uuid_arg,
    normalize_dataset_version_id,
)
from src.malaria_dl.persistence.dataset_evidence import verify_dataset_for_execution
from src.malaria_dl.models.registry import enabled_models, model_arg, resolve_descriptor
from src.malaria_dl.models.optimizers import OPTIMIZER_DEFAULTS
from src.malaria_dl.models.configuration import (
    resolve_config,
    load_selected,
    config_digest,
)


def run_command(cmd, cwd, dry_run=False):
    print(" ".join(cmd))
    if dry_run:
        return 0
    return subprocess.run(cmd, cwd=str(cwd)).returncode


def build_train_command(
    model,
    optimizer,
    max_epochs,
    img_size,
    batch_size,
    seed,
    dataset_version_id,
    target_recall,
    early_stopping_patience,
    expected_evidence_id=None,
    selected=None,
):
    dataset_version_id = normalize_dataset_version_id(dataset_version_id)
    overrides = {"execution": {}, "optimizer": {"name": optimizer}, "model": {}}
    for key, value in dict(
        max_epochs=max_epochs,
        batch_size=batch_size,
        seed=seed,
        target_recall=target_recall,
        early_stopping_patience=early_stopping_patience,
    ).items():
        if value is not None:
            overrides["execution"][key] = value
    if img_size is not None:
        overrides["model"]["input_shape"] = [img_size, img_size, 3]
    config = resolve_config(model, selected, overrides, batch=True)
    r = config["resolved"]
    selected_for_child = dict(
        schema_version=config["schema_version"],
        **{k: v for k, v in r.items() if k not in ("selection", "input_contract")},
    )
    return [
        sys.executable,
        "-m",
        "src.train",
        "--model",
        config["model_id"],
        "--optimizer",
        optimizer,
        "--configuration-json",
        json.dumps(selected_for_child, sort_keys=True),
        "--configuration-origin-json",
        json.dumps({k:config[k] for k in ('requested','provenance')}, sort_keys=True),
        "--config-digest",
        config_digest(r),
        "--dataset-version-id",
        dataset_version_id,
        *(
            ["--expected-dataset-evidence-id", expected_evidence_id]
            if expected_evidence_id
            else []
        ),
        "--track-db",
    ]


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Registry model × optimizer matrix; PostgreSQL tracking required"
    )
    p.add_argument("--project-dir", default=".")
    p.add_argument("--models", nargs="+", type=model_arg, default=None)
    p.add_argument(
        "--optimizers", nargs="+", choices=tuple(OPTIMIZER_DEFAULTS), default=None
    )
    for name in (
        "max-epochs",
        "img-size",
        "batch-size",
        "seed",
        "early-stopping-patience",
    ):
        p.add_argument("--" + name, type=int, default=None)
    p.add_argument("--target-recall", type=float, default=None)
    p.add_argument("--model-config")
    p.add_argument("--dataset-version-id", required=True, type=dataset_uuid_arg)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--continue-on-error", action="store_true")
    args = p.parse_args(argv)
    args.models_explicit = args.models is not None
    args.models = args.models if args.models is not None else list(enabled_models())
    if not args.models or len(set(args.models)) != len(args.models):
        p.error("Empty or duplicate model selection")
    if args.optimizers is not None and len(set(args.optimizers)) != len(
        args.optimizers
    ):
        p.error("Duplicate optimizer selection")
    return args


def build_matrix(args):
    selected = load_selected(args.model_config)
    matrix = []
    for model in args.models:
        descriptor = resolve_descriptor(model)
        for optimizer in (
            args.optimizers if args.optimizers is not None else descriptor.optimizers
        ):
            cmd = build_train_command(
                model,
                optimizer,
                args.max_epochs,
                args.img_size,
                args.batch_size,
                args.seed,
                args.dataset_version_id,
                args.target_recall,
                args.early_stopping_patience,
                selected=selected,
            )
            matrix.append((descriptor.id, optimizer, cmd))
    return matrix


def main():
    args = parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()
    if not (project_dir / "src/train.py").is_file():
        raise ValueError("src/train.py not found")
    # Validate every combination before dataset auditing or the first subprocess.
    matrix = build_matrix(args)
    print(
        "Model selection:",
        "explicit subset" if args.models_explicit else "enabled trainable registry",
    )
    print("Combinations:", len(matrix))
    if args.dry_run:
        print("PLAN ONLY: integridad operativa NO VERIFICADA; no BD ni entrenamiento.")
        snapshot = None
    else:
        snapshot = verify_dataset_for_execution(
            args.dataset_version_id, consumer="run_train_all_models"
        )
    failures = []
    for model, optimizer, cmd in matrix:
        if snapshot:
            cmd.extend(["--expected-dataset-evidence-id", snapshot.evidence_id])
        rc = run_command(cmd, project_dir, args.dry_run)
        if rc:
            failures.append((model, optimizer, rc))
            if not args.continue_on_error:
                break
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
