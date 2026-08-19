"""Reconcile discovered model versions created by completed TRAIN runs."""
from __future__ import annotations

import argparse
from uuid import UUID

from sqlalchemy import text

from src.db import get_connection
from src.malaria_dl.governance.services.training_model_version_finalizer import (
    TrainingModelVersionFinalizationError,
    finalize_training_model_version,
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-version-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        dataset_version_id = str(UUID(args.dataset_version_id))
    except ValueError:
        print("ERROR: dataset-version-id inválido")
        return 2
    with get_connection() as connection:
        run_ids = connection.execute(
            text(
                """
                SELECT id::text FROM runs
                WHERE run_type='training' AND status='completed'
                  AND dataset_version_id=CAST(:dataset_version_id AS uuid)
                ORDER BY created_at, id
                """
            ),
            {"dataset_version_id": dataset_version_id},
        ).scalars().all()
    print(f"TRAIN encontrados: {len(run_ids)}")
    failures = 0
    for run_id in run_ids:
        try:
            result = finalize_training_model_version(run_id, dry_run=args.dry_run)
            print(f"{result.action}: training_run_id={run_id} model_version_id={result.model_version_id}")
        except TrainingModelVersionFinalizationError as exc:
            failures += 1
            print(f"blocked: training_run_id={run_id} reason={exc}")
    print(f"Resumen: total={len(run_ids)} blocked={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
