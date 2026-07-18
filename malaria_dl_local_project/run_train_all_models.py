#!/usr/bin/env python3
"""
run_train_all_models.py

Ejecuta entrenamientos para todas las combinaciones:
- modelos: custom_cnn, vgg16, densenet121
- optimizers: adam, adamw, sgd, adadelta

Uso recomendado:
  cd ".../capstone/malaria_dl_local_project"
  source .venv/bin/activate
  python run_train_all_models.py

Opciones útiles:
  python run_train_all_models.py --dry-run
  python run_train_all_models.py --models custom_cnn densenet121 --optimizers adam adamw
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable


DEFAULT_MODELS = ["custom_cnn", "vgg16", "densenet121"]
DEFAULT_OPTIMIZERS = ["adam", "adamw", "sgd", "adadelta"]


def run_command(cmd: list[str], cwd: Path, dry_run: bool = False) -> int:
    print("\n" + "=" * 100)
    print("Ejecutando:")
    print(" ".join(cmd))
    print("=" * 100)

    if dry_run:
        return 0

    result = subprocess.run(cmd, cwd=str(cwd))
    if result.returncode != 0:
        print(f"\nERROR: comando falló con código {result.returncode}", file=sys.stderr)
    return result.returncode


def optimizer_learning_rates(optimizer: str) -> tuple[str, str]:
    """
    Learning rates recomendados por optimizer.
    - Adam/AdamW: conservador y estable para el pipeline clínico.
    - SGD: requiere LR mayor para evitar underfitting.
    - Adadelta: suele trabajar con LR cercano a 1.0.
    """
    if optimizer == "sgd":
        return "1e-3", "1e-4"
    if optimizer == "adadelta":
        return "1.0", "1.0"
    return "1e-4", "1e-5"


def model_training_params(model: str) -> tuple[str, str]:
    """
    Devuelve:
    - fine_tune_epochs
    - pretrained_weights
    """
    if model in {"vgg16", "densenet121"}:
        return "20", "imagenet"
    return "0", "none"


def build_train_command(
    model: str,
    optimizer: str,
    max_epochs: int,
    img_size: int,
    batch_size: int,
    seed: int,
    dataset_dir: str,
    target_recall: float,
    early_stopping_patience: int,
) -> list[str]:
    learning_rate, fine_tune_learning_rate = optimizer_learning_rates(optimizer)
    fine_tune_epochs, pretrained_weights = model_training_params(model)

    return [
        sys.executable,
        "-m", "src.train",
        "--model", model,
        "--max-epochs", str(max_epochs),
        "--fine-tune-epochs", fine_tune_epochs,
        "--img-size", str(img_size),
        "--batch-size", str(batch_size),
        "--seed", str(seed),
        "--learning-rate", learning_rate,
        "--fine-tune-learning-rate", fine_tune_learning_rate,
        "--pretrained-weights", pretrained_weights,
        "--optimizer", optimizer,
        "--checkpoint-monitor", "val_f2_parasitized",
        "--checkpoint-mode", "max",
        "--early-stopping",
        "--early-stopping-monitor", "val_f2_parasitized",
        "--early-stopping-mode", "max",
        "--early-stopping-patience", str(early_stopping_patience),
        "--early-stopping-min-delta", "0.0001",
        "--restore-best-weights",
        "--reject-prediction-collapse",
        "--min-class-fraction", "0.05",
        "--calibrate-threshold",
        "--target-recall", str(target_recall),
        "--evaluate-best-on-test",
        "--data-source", "physical",
        "--dataset-dir", dataset_dir,
        "--preprocessing", "auto",
        "--positive-label", "parasitized",
        "--track-db",
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ejecuta entrenamientos modelo x optimizer con tracking en PostgreSQL."
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Ruta a malaria_dl_local_project. Por defecto: directorio actual.",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        choices=DEFAULT_MODELS,
        help="Modelos a ejecutar.",
    )
    parser.add_argument(
        "--optimizers",
        nargs="+",
        default=DEFAULT_OPTIMIZERS,
        choices=DEFAULT_OPTIMIZERS,
        help="Optimizers a ejecutar.",
    )
    parser.add_argument("--max-epochs", type=int, default=100)
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--target-recall", type=float, default=0.98)
    parser.add_argument("--early-stopping-patience", type=int, default=12)
    parser.add_argument("--dataset-dir", default="data/malaria_physical_split")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo imprime comandos, no ejecuta.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continúa con la siguiente combinación si una ejecución falla.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()

    if not (project_dir / "src" / "train.py").exists():
        print(
            f"ERROR: no se encontró src/train.py en {project_dir}. "
            "Ejecuta desde malaria_dl_local_project o usa --project-dir.",
            file=sys.stderr,
        )
        return 2

    print(f"Proyecto: {project_dir}")
    print(f"Modelos: {', '.join(args.models)}")
    print(f"Optimizers: {', '.join(args.optimizers)}")

    failures: list[tuple[str, str, int]] = []

    for model in args.models:
        for optimizer in args.optimizers:
            cmd = build_train_command(
                model=model,
                optimizer=optimizer,
                max_epochs=args.max_epochs,
                img_size=args.img_size,
                batch_size=args.batch_size,
                seed=args.seed,
                dataset_dir=args.dataset_dir,
                target_recall=args.target_recall,
                early_stopping_patience=args.early_stopping_patience,
            )
            rc = run_command(cmd, cwd=project_dir, dry_run=args.dry_run)
            if rc != 0:
                failures.append((model, optimizer, rc))
                if not args.continue_on_error:
                    break
        if failures and not args.continue_on_error:
            break

    print("\nResumen train")
    if not failures:
        print("OK: todas las combinaciones finalizaron sin error.")
        return 0

    for model, optimizer, rc in failures:
        print(f"FALLÓ: model={model}, optimizer={optimizer}, returncode={rc}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
