#!/usr/bin/env python3
"""
run_explain_all_trainings.py

Ejecuta src.explain para todos los training runs completados, usando:
- checkpoint inmutable registrado en model_versions
- --source-training-run-id
- --require-lineage

Uso recomendado:
  cd ".../capstone/malaria_dl_local_project"
  source .venv/bin/activate
  python run_explain_all_trainings.py

Opciones útiles:
  python run_explain_all_trainings.py --dry-run
  python run_explain_all_trainings.py --models custom_cnn densenet121 --optimizers adam adamw
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TrainingRun:
    training_run_id: str
    run_name: str | None
    model_name: str | None
    optimizer: str | None
    checkpoint_path: str
    img_size: str
    batch_size: str
    preprocessing: str


def load_database_url(project_dir: Path) -> str:
    """
    Intenta usar src.db.get_database_url() para respetar la configuración real del proyecto.
    Fallback: DATABASE_URL del entorno.
    """
    sys.path.insert(0, str(project_dir))
    try:
        from src.db import get_database_url  # type: ignore

        return str(get_database_url())
    except Exception:
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            raise RuntimeError(
                "No se pudo obtener DATABASE_URL. Ejecuta desde malaria_dl_local_project "
                "con .venv activo y .env configurado."
            )
        return db_url


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


def fetch_training_runs(project_dir: Path) -> list[TrainingRun]:
    query = """
        SELECT DISTINCT ON (r.id)
            r.id::text AS training_run_id,
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
            ) AS preprocessing
        FROM runs r
        LEFT JOIN models m ON m.id = r.model_id
        JOIN model_versions mv ON mv.training_run_id = r.id
        WHERE r.run_type = 'training'
          AND r.status = 'completed'
          AND COALESCE(mv.best_model_path, mv.checkpoint_path) IS NOT NULL
        ORDER BY r.id, mv.created_at DESC;
    """

    with connect(project_dir) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    return [
        TrainingRun(
            training_run_id=row[0],
            run_name=row[1],
            model_name=row[2],
            optimizer=row[3],
            checkpoint_path=row[4],
            img_size=str(row[5] or "200"),
            batch_size=str(row[6] or "64"),
            preprocessing=row[7] or "auto",
        )
        for row in rows
    ]


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


def build_explain_command(
    run: TrainingRun,
    method: str,
    num_samples: int,
    threshold: str,
) -> list[str]:
    return [
        sys.executable,
        "-m", "src.explain",
        "--checkpoint", run.checkpoint_path,
        "--source-training-run-id", run.training_run_id,
        "--method", method,
        "--img-size", run.img_size,
        "--batch-size", run.batch_size,
        "--num-samples", str(num_samples),
        "--threshold", threshold,
        "--positive-label", "parasitized",
        "--track-db",
        "--require-lineage",
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ejecuta explain para todos los trainings completados con linaje explícito."
    )
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--models", nargs="+", default=None)
    parser.add_argument("--optimizers", nargs="+", default=None)
    parser.add_argument("--method", default="all", choices=["gradcam", "lime", "shap", "all"])
    parser.add_argument("--num-samples", type=int, default=50)
    parser.add_argument("--threshold", default="clinical")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()

    if not (project_dir / "src" / "explain.py").exists():
        print(
            f"ERROR: no se encontró src/explain.py en {project_dir}. "
            "Ejecuta desde malaria_dl_local_project o usa --project-dir.",
            file=sys.stderr,
        )
        return 2

    runs = fetch_training_runs(project_dir)
    runs = filter_runs(runs, args.models, args.optimizers, args.limit)

    if not runs:
        print("No hay training runs completados que coincidan con los filtros.")
        return 0

    print(f"Training runs a explicar: {len(runs)}")

    failures: list[tuple[str, str]] = []
    for run in runs:
        print(
            f"\nTraining: {run.training_run_id} | "
            f"model={run.model_name} | optimizer={run.optimizer} | checkpoint={run.checkpoint_path}"
        )
        cmd = build_explain_command(
            run,
            method=args.method,
            num_samples=args.num_samples,
            threshold=args.threshold,
        )
        rc = run_command(cmd, cwd=project_dir, dry_run=args.dry_run)
        if rc != 0:
            failures.append((run.training_run_id, run.checkpoint_path))
            if not args.continue_on_error:
                break

    print("\nResumen explain")
    if not failures:
        print("OK: todas las explicaciones finalizaron sin error.")
        return 0

    for training_run_id, checkpoint in failures:
        print(f"FALLÓ: training_run_id={training_run_id}, checkpoint={checkpoint}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
