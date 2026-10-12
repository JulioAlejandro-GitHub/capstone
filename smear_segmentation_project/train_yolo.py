from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from ultralytics import YOLO


PROJECT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PROJECT_ROOT.parent

DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "yolo26n_seg_train_v1.yaml"


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    if not isinstance(config, dict):
        raise ValueError(f"Invalid training configuration: {path}")

    return config


def resolve_repository_path(value: str) -> Path:
    path = Path(value)

    if path.is_absolute():
        return path.resolve()

    return (REPOSITORY_ROOT / path).resolve()


def prepare_config(config: dict) -> dict:
    resolved = dict(config)

    resolved["data"] = str(resolve_repository_path(config["data"]))
    resolved["project"] = str(resolve_repository_path(config["project"]))

    model_path = resolve_repository_path(config["model"])
    if model_path.is_file():
        resolved["model"] = str(model_path)

    return resolved


def validate_config(config: dict) -> None:
    required = {
        "model",
        "data",
        "task",
        "imgsz",
        "epochs",
        "patience",
        "optimizer",
        "pretrained",
        "seed",
        "deterministic",
        "device",
        "cache",
        "batch",
        "amp",
        "save",
        "plots",
        "project",
        "name",
        "exist_ok",
    }

    missing = sorted(required - config.keys())

    if missing:
        raise ValueError(
            "Missing required training parameters: "
            + ", ".join(missing)
        )

    if config["task"] != "segment":
        raise ValueError("YOLO Detector Train requires task=segment")

    if config["device"] != "mps":
        raise ValueError("YOLO Detector Train v1 requires device=mps")

    if config["batch"] != 8:
        raise ValueError("YOLO Detector Train v1 requires batch=8")

    if config["amp"] is not True:
        raise ValueError("YOLO Detector Train v1 requires amp=true")


def print_contract(config_path: Path, config: dict) -> bool:
    data_path = Path(config["data"])
    project_path = Path(config["project"])

    data_ok = data_path.is_file()
    project_absolute = project_path.is_absolute()
    project_inside_repository = project_path.is_relative_to(REPOSITORY_ROOT)

    print("=== YOLO DETECTOR TRAIN ===")
    print("config:", config_path)
    print("model:", config["model"])
    print("data:", config["data"])
    print("project:", config["project"])
    print("task:", config["task"])
    print("device:", config["device"])
    print("imgsz:", config["imgsz"])
    print("batch:", config["batch"])
    print("amp:", config["amp"])
    print("epochs:", config["epochs"])
    print("patience:", config["patience"])
    print("seed:", config["seed"])

    print()
    print("data_exists:", data_ok)
    print("project_is_absolute:", project_absolute)
    print("project_inside_repository:", project_inside_repository)

    contract_ok = (
        data_ok
        and project_absolute
        and project_inside_repository
    )

    print("contract_check:", contract_ok)

    return contract_ok


def main() -> None:
    parser = argparse.ArgumentParser(description="YOLO Detector Train")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Training configuration YAML",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the resolved configuration without training",
    )
    args = parser.parse_args()

    config_path = args.config.resolve()

    config = load_config(config_path)
    validate_config(config)

    resolved = prepare_config(config)

    if not print_contract(config_path, resolved):
        raise SystemExit(1)

    if args.dry_run:
        print()
        print("TRAIN: NOT STARTED (--dry-run)")
        return

    print()
    print("Starting YOLO Detector Train...")

    model = YOLO(resolved["model"])

    train_args = dict(resolved)
    train_args.pop("model")

    results = model.train(**train_args)

    print()
    print("=== YOLO DETECTOR TRAIN COMPLETED ===")
    print("save_dir:", results.save_dir)


if __name__ == "__main__":
    main()
