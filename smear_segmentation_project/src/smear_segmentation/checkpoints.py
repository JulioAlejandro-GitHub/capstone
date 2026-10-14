"""Checkpoint selection shared by the HTTP adapter and local runtime (no ML imports)."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

HISTORICAL_RUN = "yolo26n_rbc_1024_v1"
DEFAULT_RUNS_ROOT = "smear_segmentation_project/runs/yolo26_seg"


def checkpoint_reference(environment: Mapping[str, str | None]) -> Path:
    run = environment.get("YOLO_RUN_UUID", HISTORICAL_RUN)
    if (not run or not run.strip() or run in {".", ".."}
            or any(c in run for c in ("/", "\\", "\x00", ":"))):
        raise ValueError("YOLO_RUN_UUID debe ser un único nombre de directorio")
    root = environment.get("YOLO_RUNS_ROOT", DEFAULT_RUNS_ROOT)
    if not root or not root.strip():
        raise ValueError("YOLO_RUNS_ROOT no puede estar vacío")
    return Path(root) / run / "weights" / "best.pt"


def resolve_checkpoint(reference: Path, repository_root: Path) -> Path:
    # Absolute host references stay absolute; relative references never use cwd.
    absolute = reference if reference.is_absolute() else repository_root / reference
    resolved = absolute.resolve()
    if not resolved.is_relative_to(absolute.parents[2].resolve()):
        raise ValueError("YOLO checkpoint escapes YOLO_RUNS_ROOT")
    return resolved
