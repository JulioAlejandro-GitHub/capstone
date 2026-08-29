#!/usr/bin/env python3
"""
run_evaluate_all_trainings.py

Ejecuta src.evaluate para todos los training runs completados, usando:
- checkpoint inmutable registrado en model_versions
- --source-training-run-id
- --require-lineage

Uso recomendado:
  cd ".../capstone/malaria_dl_local_project"
  source .venv/bin/activate
  python run_evaluate_all_trainings.py

Opciones útiles:
  python run_evaluate_all_trainings.py --dry-run
  python run_evaluate_all_trainings.py --models custom_cnn densenet121 --optimizers adam adamw
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


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
    query = """
        SELECT DISTINCT ON (r.id)
            r.id::text AS training_run_id,
            mv.id::text AS model_version_id,
            r.run_name,
            m.name AS model_name,
            COALESCE(
                r.execution_parameters ->> 'optimizer',
                r.parameters ->> 'optimizer',
                ''
            ) AS optimizer,
            COALESCE(mv.best_model_path, mv.checkpoint_path) AS checkpoint_path,
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
          AND (
              CAST(%(dataset_version_id)s AS uuid) IS NULL
              OR r.dataset_version_id=CAST(%(dataset_version_id)s AS uuid)
          )
        ORDER BY r.id, mv.created_at DESC;
    """

    with connect(project_dir) as conn:
        with conn.cursor() as cur:
            cur.execute(query, {"dataset_version_id": dataset_version_id})
            rows = cur.fetchall()

    inventory = []
    for row in rows:
        reasons = []
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


def fetch_training_runs(project_dir: Path) -> list[TrainingRun]:
    return [run for run in fetch_training_inventory(project_dir) if not run.exclusion_reasons]


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


def build_evaluate_command(run: TrainingRun, dataset_dir: str, threshold: str) -> list[str]:
    return [
        sys.executable,
        "-m", "src.evaluate",
        "--model-version-id", run.model_version_id,
        "--source-training-run-id", run.training_run_id,
        *(
            ["--dataset-version-id", run.dataset_version_id]
            if run.dataset_version_id else []
        ),
        "--img-size", run.img_size,
        "--batch-size", run.batch_size,
        "--threshold", threshold,
        "--data-source", "physical",
        "--dataset-dir", dataset_dir,
        "--preprocessing", run.preprocessing,
        "--positive-label", "parasitized",
        "--track-db",
        "--require-lineage",
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ejecuta evaluate para todos los trainings completados con linaje explícito."
    )
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--models", nargs="+", default=None)
    parser.add_argument("--optimizers", nargs="+", default=None)
    parser.add_argument("--dataset-dir", default="data/malaria_physical_split")
    parser.add_argument("--dataset-version-id", default=None)
    parser.add_argument("--threshold", default="clinical")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()

    if not (project_dir / "src" / "evaluate.py").exists():
        print(
            f"ERROR: no se encontró src/evaluate.py en {project_dir}. "
            "Ejecuta desde malaria_dl_local_project o usa --project-dir.",
            file=sys.stderr,
        )
        return 2

    inventory = fetch_training_inventory(project_dir, args.dataset_version_id)
    excluded = [run for run in inventory if run.exclusion_reasons]
    runs = [run for run in inventory if not run.exclusion_reasons]
    runs = filter_runs(runs, args.models, args.optimizers, args.limit)

    print(
        f"TRAIN encontrados: {len(inventory)} | elegibles: {len(inventory) - len(excluded)} "
        f"| excluidos: {len(excluded)}"
    )
    for run in excluded:
        print(
            f"EXCLUIDO: training_run_id={run.training_run_id} | "
            + " | ".join(run.exclusion_reasons)
        )

    if not runs:
        print("No hay training runs completados que coincidan con los filtros.")
        return 0

    print(f"Training runs a evaluar: {len(runs)}")

    failures: list[tuple[str, str]] = []
    for run in runs:
        print(
            f"\nTraining: {run.training_run_id} | "
            f"model_version={run.model_version_id} | model={run.model_name} | "
            f"optimizer={run.optimizer} | checkpoint={run.checkpoint_path}"
        )
        cmd = build_evaluate_command(run, dataset_dir=args.dataset_dir, threshold=args.threshold)
        rc = run_command(cmd, cwd=project_dir, dry_run=args.dry_run)
        if rc != 0:
            failures.append((run.training_run_id, run.checkpoint_path))
            if not args.continue_on_error:
                break

    print("\nResumen evaluate")
    if not failures:
        print("OK: todas las evaluaciones finalizaron sin error.")
        return 0

    for training_run_id, checkpoint in failures:
        print(f"FALLÓ: training_run_id={training_run_id}, checkpoint={checkpoint}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
