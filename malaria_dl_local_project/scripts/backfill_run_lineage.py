"""Backfill seguro de relaciones train -> evaluate/explain históricas."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.db import get_connection  # noqa: E402
from src.run_lineage import (  # noqa: E402
    create_run_lineage_with_metadata,
    resolve_training_run_from_checkpoint,
)


RELATIONSHIP_BY_RUN_TYPE = {
    "evaluation": "evaluates_checkpoint_from",
    "explainability": "explains_checkpoint_from",
}
EXACT_RESOLUTION_CONFIDENCES = {
    "inferred_exact_checkpoint",
    "inferred_model_version",
}


def _mapping_rows(connection, sql, params=None):
    rows = connection.execute(text(sql), params or {}).mappings().all()
    return [dict(row) for row in rows]


def find_unlinked_child_runs():
    """Return evaluate/explain runs that lack their canonical parent relation."""
    with get_connection() as connection:
        return _mapping_rows(
            connection,
            """
            SELECT
                child.id::text AS child_run_id,
                child.run_name,
                child.run_type,
                child.started_at,
                COALESCE(
                    NULLIF(child.metadata->>'source_checkpoint_path', ''),
                    NULLIF(child.metadata->>'checkpoint_path', ''),
                    NULLIF(child.metadata->>'checkpoint', ''),
                    NULLIF(child.execution_parameters->>'checkpoint_path', ''),
                    NULLIF(child.execution_parameters->>'checkpoint', ''),
                    NULLIF(child.parameters->>'checkpoint_path', ''),
                    NULLIF(child.parameters->>'checkpoint', ''),
                    NULLIF(child.parameters #>> '{cli_arguments,checkpoint}', '')
                ) AS checkpoint_path,
                COALESCE(
                    NULLIF(child.metadata->>'source_model_name', ''),
                    NULLIF(model.name, ''),
                    NULLIF(child.execution_parameters->>'model_name', ''),
                    NULLIF(child.execution_parameters->>'model', ''),
                    NULLIF(child.parameters->>'model_name', ''),
                    NULLIF(child.parameters->>'model', '')
                ) AS model_name
            FROM runs child
            LEFT JOIN models model ON model.id = child.model_id
            WHERE child.run_type IN ('evaluation', 'explainability')
              AND NOT EXISTS (
                  SELECT 1
                  FROM run_lineage lineage
                  JOIN runs parent ON parent.id = lineage.parent_run_id
                  WHERE lineage.child_run_id = child.id
                    AND parent.run_type = 'training'
                    AND lineage.relationship_type = CASE child.run_type
                        WHEN 'evaluation' THEN 'evaluates_checkpoint_from'
                        WHEN 'explainability' THEN 'explains_checkpoint_from'
                    END
              )
            ORDER BY child.started_at ASC, child.id ASC
            """,
        )


def find_training_candidates_by_model(model_name):
    """Return all training runs with the exact same normalized model name."""
    if not model_name:
        return []
    with get_connection() as connection:
        return _mapping_rows(
            connection,
            """
            SELECT
                training.id::text AS training_run_id,
                training.id::text AS id,
                training.run_name,
                training.run_type,
                training.status AS training_status,
                training.command,
                training.started_at,
                COALESCE(
                    NULLIF(model.name, ''),
                    NULLIF(training.execution_parameters->>'model_name', ''),
                    NULLIF(training.execution_parameters->>'model', ''),
                    NULLIF(training.parameters->>'model_name', ''),
                    NULLIF(training.parameters->>'model', ''),
                    NULLIF(training.metadata->>'model_name', '')
                ) AS model_name,
                COALESCE(
                    NULLIF(training.execution_parameters->>'optimizer', ''),
                    NULLIF(training.parameters->>'optimizer', ''),
                    NULLIF(training.metadata->>'optimizer', '')
                ) AS optimizer
            FROM runs training
            LEFT JOIN models model ON model.id = training.model_id
            WHERE training.run_type = 'training'
              AND LOWER(COALESCE(
                    NULLIF(model.name, ''),
                    NULLIF(training.execution_parameters->>'model_name', ''),
                    NULLIF(training.execution_parameters->>'model', ''),
                    NULLIF(training.parameters->>'model_name', ''),
                    NULLIF(training.parameters->>'model', ''),
                    NULLIF(training.metadata->>'model_name', '')
                  )) = LOWER(:model_name)
            ORDER BY training.started_at DESC, training.id DESC
            """,
            {"model_name": str(model_name)},
        )


def _resolved_training_run_id(resolution):
    if not resolution:
        return None
    return resolution.get("training_run_id") or resolution.get("id")


def _heuristic_resolution(child):
    candidates = find_training_candidates_by_model(child.get("model_name"))
    unique = {}
    for candidate in candidates:
        training_run_id = _resolved_training_run_id(candidate)
        if training_run_id:
            unique[str(training_run_id)] = candidate
    if len(unique) != 1:
        return None, len(unique)

    candidate = dict(next(iter(unique.values())))
    candidate.update(
        {
            "status": "resolved",
            "confidence": "inferred_heuristic",
            "resolution_method": "unique_training_run_for_model",
            "checkpoint_path": child.get("checkpoint_path"),
        }
    )
    return candidate, 1


def _normalized_model_name(model_name):
    normalized = str(model_name or "").strip().lower()
    return {
        "vgg16_transfer_learning": "vgg16",
    }.get(normalized, normalized)


def is_generic_legacy_checkpoint(checkpoint_path, model_name=None):
    """Reconoce outputs/<model> legacy y exige acuerdo con metadata del hijo."""
    if not checkpoint_path:
        return False
    parts = [part.lower() for part in Path(str(checkpoint_path)).parts]
    if len(parts) < 3:
        return False
    has_generic_shape = (
        parts[-3] == "outputs"
        and parts[-1] in {"best_model.keras", "final_model.keras"}
    )
    if not has_generic_shape or not model_name:
        return False
    return _normalized_model_name(parts[-2]) == _normalized_model_name(model_name)


def backfill_run_lineage(*, apply=False, allow_heuristic=False, child_runs=None):
    """Plan or apply safe backfill; ambiguity is always skipped."""
    children = list(find_unlinked_child_runs() if child_runs is None else child_runs)
    summary = {
        "mode": "APPLY" if apply else "DRY RUN",
        "scanned": len(children),
        "planned": 0,
        "created": 0,
        "exact": 0,
        "heuristic": 0,
        "ambiguous": 0,
        "unresolved": 0,
        "errors": 0,
        "relationships": [],
    }

    for child in children:
        child_id = str(child.get("child_run_id") or "")
        run_type = child.get("run_type")
        relationship_type = RELATIONSHIP_BY_RUN_TYPE.get(run_type)
        checkpoint_path = child.get("checkpoint_path")
        if not child_id or relationship_type is None or not checkpoint_path:
            summary["unresolved"] += 1
            continue

        try:
            resolution = resolve_training_run_from_checkpoint(
                str(checkpoint_path),
                model_name=child.get("model_name"),
            )
        except Exception as exc:
            summary["errors"] += 1
            summary["relationships"].append(
                {
                    "child_run_id": child_id,
                    "status": "error",
                    "message": str(exc),
                }
            )
            continue

        resolution_status = (resolution or {}).get("status")
        if resolution_status == "ambiguous":
            # An exact ambiguity must never be converted into a heuristic link.
            summary["ambiguous"] += 1
            continue

        confidence = (resolution or {}).get("confidence")
        if (
            resolution_status == "resolved"
            and confidence in EXACT_RESOLUTION_CONFIDENCES
            and _resolved_training_run_id(resolution)
        ):
            summary["exact"] += 1
        elif (
            allow_heuristic
            and resolution_status != "ambiguous"
            and is_generic_legacy_checkpoint(
                checkpoint_path,
                child.get("model_name"),
            )
        ):
            resolution, candidate_count = _heuristic_resolution(child)
            if resolution is None:
                if candidate_count > 1:
                    summary["ambiguous"] += 1
                else:
                    summary["unresolved"] += 1
                continue
            confidence = "inferred_heuristic"
            summary["heuristic"] += 1
        else:
            summary["unresolved"] += 1
            continue

        parent_id = str(_resolved_training_run_id(resolution))
        planned = {
            "parent_run_id": parent_id,
            "child_run_id": child_id,
            "relationship_type": relationship_type,
            "checkpoint_path": str(checkpoint_path),
            "confidence": confidence,
            "resolution_method": resolution.get("resolution_method"),
            "status": "planned" if not apply else "pending",
        }
        summary["planned"] += 1

        if apply:
            try:
                lineage_id = create_run_lineage_with_metadata(
                    parent_run_id=parent_id,
                    child_run_id=child_id,
                    relationship_type=relationship_type,
                    source_training_run=resolution,
                    checkpoint_path=str(checkpoint_path),
                    checkpoint_artifact_id=resolution.get(
                        "checkpoint_artifact_id"
                    ),
                    model_version_id=resolution.get("model_version_id"),
                    confidence=confidence,
                    metadata={
                        "source": "scripts/backfill_run_lineage.py",
                        "backfilled": True,
                        "resolution_method": resolution.get(
                            "resolution_method"
                        ),
                    },
                )
                if lineage_id is None:
                    raise RuntimeError(
                        "create_run_lineage_with_metadata no devolvió un id"
                    )
                planned["lineage_id"] = str(lineage_id)
                planned["status"] = "created"
                summary["created"] += 1
            except Exception as exc:
                planned["status"] = "error"
                planned["message"] = str(exc)
                summary["errors"] += 1

        summary["relationships"].append(planned)

    return summary


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Backfill seguro del linaje train -> evaluate/explain. "
            "No escribe en PostgreSQL salvo que se use --apply."
        )
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Sólo muestra relaciones candidatas (modo por defecto).",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Inserta las relaciones resolubles de forma segura.",
    )
    parser.add_argument(
        "--allow-heuristic",
        action="store_true",
        help=(
            "Permite enlazar sólo si existe un único training del mismo modelo; "
            "nunca resuelve una coincidencia exacta ambigua."
        ),
    )
    return parser.parse_args(argv)


def print_summary(summary):
    print(f"Run Lineage backfill — {summary['mode']}")
    print(f"Runs hijos inspeccionados: {summary['scanned']}")
    print(f"Relaciones planificadas: {summary['planned']}")
    print(f"Coincidencias exactas: {summary['exact']}")
    print(f"Coincidencias heurísticas: {summary['heuristic']}")
    print(f"Ambiguos omitidos: {summary['ambiguous']}")
    print(f"No resueltos omitidos: {summary['unresolved']}")
    print(f"Errores: {summary['errors']}")
    if summary["mode"] == "APPLY":
        print(f"Relaciones creadas/actualizadas: {summary['created']}")

    for relationship in summary["relationships"]:
        print(
            "- "
            f"{relationship.get('status')}: "
            f"{relationship.get('child_run_id')} <- "
            f"{relationship.get('parent_run_id', '-')} "
            f"[{relationship.get('relationship_type', '-')}]"
        )


def main(argv=None):
    args = parse_args(argv)
    try:
        summary = backfill_run_lineage(
            apply=bool(args.apply),
            allow_heuristic=bool(args.allow_heuristic),
        )
    except Exception as exc:
        print(f"ERROR: no se pudo ejecutar backfill de run lineage: {exc}")
        return 1

    print_summary(summary)
    if summary["mode"] == "DRY RUN":
        print("DRY RUN: no se modificó PostgreSQL. Use --apply para persistir.")
    if summary["errors"]:
        print("WARNING: el backfill terminó con errores parciales")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
