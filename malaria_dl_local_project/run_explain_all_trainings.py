#!/usr/bin/env python3
"""E6 campaign explain entrypoint; legacy inventory is read-only and exposes ambiguity."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from src.malaria_dl.data.governed_dataset import (
    dataset_uuid_arg, normalize_dataset_version_id, GovernedDatasetError,
    training_dataset_metadata, assert_run_dataset_snapshot_unchanged,
)
from src.malaria_dl.persistence.dataset_evidence import verify_dataset_for_execution


@dataclass
class TrainingRun:
    training_run_id: str
    model_version_id: str
    run_name: str | None
    model_name: str | None
    optimizer: str | None
    checkpoint_path: str
    img_size: str
    batch_size: str
    preprocessing: str
    dataset_version_id: str | None = None
    exclusion_reasons: tuple[str, ...] = ()


def load_database_url(project_dir: Path) -> str:
    """Load the canonical Docker-only DATABASE_URL contract."""
    sys.path.insert(0, str(project_dir))
    from src.db import get_database_url  # type: ignore

    return str(get_database_url())


def connect(project_dir: Path):
    db_url = load_database_url(project_dir)

    # SQLAlchemy URL puede venir como postgresql+psycopg://; psycopg usa postgresql://
    psycopg_url = db_url.replace("postgresql+psycopg://", "postgresql://")

    try:
        import psycopg  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Falta psycopg. Instala requirements.txt en el entorno del proyecto."
        ) from exc

    return psycopg.connect(psycopg_url)


def fetch_training_inventory(
    project_dir: Path,
    dataset_version_id: str | None = None,
) -> list[TrainingRun]:
    dataset_version_id = normalize_dataset_version_id(dataset_version_id)
    query = """
        SELECT
            r.id::text AS training_run_id,
            mv.id::text AS model_version_id,
            r.run_name,
            m.name AS model_name,
            COALESCE(
                r.execution_parameters ->> 'optimizer',
                r.parameters ->> 'optimizer',
                ''
            ) AS optimizer,
            mv.checkpoint_path AS checkpoint_path,
            COALESCE(
                r.execution_parameters ->> 'img_size',
                r.parameters ->> 'img_size',
                '200'
            ) AS img_size,
            COALESCE(
                r.execution_parameters ->> 'batch_size',
                r.parameters ->> 'batch_size',
                '64'
            ) AS batch_size,
            COALESCE(
                r.execution_parameters ->> 'preprocessing',
                r.parameters ->> 'preprocessing',
                'auto'
            ) AS preprocessing,
            r.dataset_version_id::text,
            mv.status,
            mv.lineage_status,
            mv.checkpoint_artifact_id IS NOT NULL AS has_checkpoint_artifact,
            mv.artifact_sha256 IS NOT NULL AS has_artifact_sha
        FROM runs r
        LEFT JOIN models m ON m.id = r.model_id
        JOIN model_versions mv ON mv.training_run_id = r.id
        WHERE r.run_type = 'training'
          AND r.status = 'completed'
          AND r.dataset_version_id=CAST(%(dataset_version_id)s AS uuid)
        ORDER BY r.id, mv.id;
    """

    with connect(project_dir) as conn:
        with conn.cursor() as cur:
            cur.execute("BEGIN READ ONLY")
            cur.execute(query, {"dataset_version_id": dataset_version_id})
            rows = cur.fetchall()

    from collections import Counter
    multiplicity = Counter(row[0] for row in rows)
    inventory = []
    for row in rows:
        if normalize_dataset_version_id(row[9]) != dataset_version_id:
            raise GovernedDatasetError("BATCH_TRAIN_DATASET_MISMATCH")
        reasons = ["ambiguous model versions"] if multiplicity[row[0]] != 1 else []
        if row[10] not in {"candidate", "validated", "approved", "deployed"}:
            reasons.append(f"model_version status={row[10]}")
        if row[11] != "resolved":
            reasons.append(f"lineage_status={row[11]}")
        if not row[12]:
            reasons.append("missing checkpoint_artifact_id")
        if not row[13]:
            reasons.append("missing artifact_sha256")
        if not row[5]:
            reasons.append("missing checkpoint_path")
        inventory.append(TrainingRun(
            training_run_id=row[0],
            model_version_id=row[1],
            run_name=row[2],
            model_name=row[3],
            optimizer=row[4],
            checkpoint_path=row[5],
            img_size=str(row[6] or "200"),
            batch_size=str(row[7] or "64"),
            preprocessing=row[8] or "auto",
            dataset_version_id=row[9],
            exclusion_reasons=tuple(reasons),
        ))
    return inventory


def fetch_training_runs(project_dir: Path, dataset_version_id: str) -> list[TrainingRun]:
    return [run for run in fetch_training_inventory(project_dir, dataset_version_id) if not run.exclusion_reasons]


def filter_runs(
    runs: list[TrainingRun],
    models: list[str] | None,
    optimizers: list[str] | None,
    limit: int | None,
) -> list[TrainingRun]:
    filtered = runs

    if models:
        filtered = [r for r in filtered if (r.model_name or "") in models]

    if optimizers:
        filtered = [r for r in filtered if (r.optimizer or "") in optimizers]

    if limit is not None:
        filtered = filtered[:limit]

    return filtered


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


def build_explain_command(run: TrainingRun, *, method, num_samples, threshold, split, purpose, protocol, seed, layer=None):
    import json
    command = [sys.executable, "-m", "src.explain",
        "--model-version-id", run.model_version_id, "--source-training-run-id", run.training_run_id,
        "--dataset-version-id", normalize_dataset_version_id(run.dataset_version_id),
        "--threshold", str(threshold), "--split", split, "--purpose", purpose,
        "--protocol", json.dumps(protocol), "--seed", str(seed), "--batch-size", str(run.batch_size)]
    command += ["--method", method]
    if num_samples is not None:
        command += ["--num-samples", str(num_samples)]
    if layer is not None:
        command += ["--layer", layer]
    return command


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ejecuta explain para todos los trainings completados con linaje explícito."
    )
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--models", nargs="+", default=None)
    parser.add_argument("--optimizers", nargs="+", default=None)
    parser.add_argument("--method", default="all", choices=["gradcam", "lime", "shap", "all"])
    parser.add_argument("--num-samples", type=int, default=50)
    parser.add_argument("--threshold", default="clinical")
    parser.add_argument("--dataset-version-id", required=True, type=dataset_uuid_arg)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    return parser.parse_args(argv)


def main() -> int:
    from src.malaria_dl.assessment.cli import main as governed_main
    return governed_main("explain", batch=True)


if __name__ == "__main__":
    raise SystemExit(main())
