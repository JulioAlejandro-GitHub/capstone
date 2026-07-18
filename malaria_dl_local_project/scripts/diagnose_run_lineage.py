"""Diagnóstico de cobertura y consistencia del linaje entre runs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.db import get_connection  # noqa: E402
from src.run_lineage import resolve_training_run_from_checkpoint  # noqa: E402


REQUIRED_LINEAGE_OBJECTS = (
    "run_lineage",
    "vw_run_lineage",
    "vw_evaluation_lineage",
    "vw_explainability_lineage",
)


class MissingLineageSchemaError(RuntimeError):
    """Raised when migration 022 has not materialized every required object."""

    def __init__(self, missing_objects):
        self.missing_objects = tuple(missing_objects)
        super().__init__(
            "No existen objetos requeridos de linaje: "
            + ", ".join(self.missing_objects)
        )


def _mapping_rows(connection, sql, params=None):
    rows = connection.execute(text(sql), params or {}).mappings().all()
    return [dict(row) for row in rows]


def _scalar(connection, sql, params=None):
    return connection.execute(text(sql), params or {}).scalar_one()


def validate_lineage_schema(connection):
    """Return object names present in PostgreSQL or raise with all missing ones."""
    row = connection.execute(
        text(
            """
            SELECT
                to_regclass('public.run_lineage')::text AS run_lineage,
                to_regclass('public.vw_run_lineage')::text AS vw_run_lineage,
                to_regclass('public.vw_evaluation_lineage')::text
                    AS vw_evaluation_lineage,
                to_regclass('public.vw_explainability_lineage')::text
                    AS vw_explainability_lineage
            """
        )
    ).mappings().one()
    present = dict(row)
    missing = [name for name in REQUIRED_LINEAGE_OBJECTS if not present.get(name)]
    if missing:
        raise MissingLineageSchemaError(missing)
    return present


def find_unlinked_checkpoint_candidates(connection):
    """Obtiene checkpoints de runs hijos que aún no tienen relación canónica."""
    return _mapping_rows(
        connection,
        """
        SELECT
            child.id::text AS child_run_id,
            child.run_type,
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
        ORDER BY child.started_at DESC, child.id DESC
        """,
    )


def resolve_ambiguous_checkpoints(child_checkpoints):
    """Aplica el resolver real una sola vez por combinación path/modelo."""
    grouped = {}
    for child in child_checkpoints:
        checkpoint_path = child.get("checkpoint_path")
        if not checkpoint_path:
            continue
        key = (str(checkpoint_path), child.get("model_name"))
        group = grouped.setdefault(
            key,
            {
                "checkpoint_path": str(checkpoint_path),
                "model_name": child.get("model_name"),
                "child_run_ids": [],
                "child_run_types": [],
            },
        )
        group["child_run_ids"].append(str(child.get("child_run_id")))
        group["child_run_types"].append(child.get("run_type"))

    ambiguous = []
    for (checkpoint_path, model_name), group in grouped.items():
        resolution = resolve_training_run_from_checkpoint(
            checkpoint_path,
            model_name=model_name,
        )
        if (resolution or {}).get("status") != "ambiguous":
            continue
        candidates = (resolution or {}).get("candidates") or []
        group.update(
            {
                "training_run_count": len(candidates),
                "training_run_ids": [
                    str(candidate.get("training_run_id") or candidate.get("id"))
                    for candidate in candidates
                    if candidate.get("training_run_id") or candidate.get("id")
                ],
                "resolution_method": (resolution or {}).get(
                    "resolution_method"
                ),
            }
        )
        ambiguous.append(group)
    return ambiguous


def collect_lineage_diagnostics(connection):
    """Collect the release diagnostics without mutating database state."""
    schema_objects = validate_lineage_schema(connection)

    run_counts = {name: 0 for name in ("training", "evaluation", "explainability")}
    for row in _mapping_rows(
        connection,
        """
        SELECT run_type, COUNT(*)::integer AS total
        FROM runs
        WHERE run_type IN ('training', 'evaluation', 'explainability')
        GROUP BY run_type
        ORDER BY run_type
        """,
    ):
        run_counts[str(row["run_type"])] = int(row["total"])

    relationship_count = int(
        _scalar(connection, "SELECT COUNT(*)::integer FROM run_lineage")
    )
    evaluations_without_lineage = int(
        _scalar(
            connection,
            """
            SELECT COUNT(*)::integer
            FROM runs child
            WHERE child.run_type = 'evaluation'
              AND NOT EXISTS (
                  SELECT 1
                  FROM run_lineage lineage
                  JOIN runs parent ON parent.id = lineage.parent_run_id
                  WHERE lineage.child_run_id = child.id
                    AND parent.run_type = 'training'
                    AND lineage.relationship_type = 'evaluates_checkpoint_from'
              )
            """,
        )
    )
    explanations_without_lineage = int(
        _scalar(
            connection,
            """
            SELECT COUNT(*)::integer
            FROM runs child
            WHERE child.run_type = 'explainability'
              AND NOT EXISTS (
                  SELECT 1
                  FROM run_lineage lineage
                  JOIN runs parent ON parent.id = lineage.parent_run_id
                  WHERE lineage.child_run_id = child.id
                    AND parent.run_type = 'training'
                    AND lineage.relationship_type = 'explains_checkpoint_from'
              )
            """,
        )
    )

    ambiguous_checkpoints = resolve_ambiguous_checkpoints(
        find_unlinked_checkpoint_candidates(connection)
    )

    unresolved_runs = _mapping_rows(
        connection,
        """
        SELECT
            id::text AS run_id,
            run_name,
            run_type,
            metadata->>'source_checkpoint_path' AS checkpoint_path,
            metadata->>'lineage_warning' AS lineage_warning,
            started_at
        FROM runs
        WHERE run_type IN ('evaluation', 'explainability')
          AND metadata->>'lineage_status' = 'unresolved'
        ORDER BY started_at DESC
        """,
    )

    top_relationships = _mapping_rows(
        connection,
        """
        SELECT *
        FROM vw_run_lineage
        ORDER BY child_started_at DESC
        LIMIT 20
        """,
    )

    return {
        "schema_objects": schema_objects,
        "run_counts": run_counts,
        "relationship_count": relationship_count,
        "evaluations_without_lineage": evaluations_without_lineage,
        "explanations_without_lineage": explanations_without_lineage,
        "ambiguous_checkpoints": ambiguous_checkpoints,
        "ambiguous_checkpoint_count": len(ambiguous_checkpoints),
        "unresolved_runs": unresolved_runs,
        "unresolved_run_count": len(unresolved_runs),
        "top_relationships": top_relationships,
    }


def diagnose_run_lineage():
    with get_connection() as connection:
        return collect_lineage_diagnostics(connection)


def print_diagnostics(result):
    counts = result["run_counts"]
    print("Run Lineage — diagnóstico")
    print(f"1. Runs training: {counts['training']}")
    print(f"2. Runs evaluation: {counts['evaluation']}")
    print(f"3. Runs explainability: {counts['explainability']}")
    print(f"4. Relaciones run_lineage: {result['relationship_count']}")
    print(
        "5. Evaluations sin linaje: "
        f"{result['evaluations_without_lineage']}"
    )
    print(
        "6. Explainability sin linaje: "
        f"{result['explanations_without_lineage']}"
    )
    print(
        "7. Checkpoints ambiguos: "
        f"{result['ambiguous_checkpoint_count']}"
    )
    print(
        "8. Runs con lineage_status=unresolved: "
        f"{result['unresolved_run_count']}"
    )

    if result["ambiguous_checkpoints"]:
        print("\nCheckpoints ambiguos:")
        for item in result["ambiguous_checkpoints"]:
            print(
                "- "
                f"{item.get('checkpoint_path')} "
                f"({item.get('training_run_count')} trainings)"
            )

    if result["unresolved_runs"]:
        print("\nRuns unresolved:")
        for item in result["unresolved_runs"]:
            print(
                "- "
                f"{item.get('run_id')} [{item.get('run_type')}] "
                f"{item.get('checkpoint_path') or '-'}"
            )

    print("\n9. Top 20 relaciones:")
    if not result["top_relationships"]:
        print("(sin relaciones)")
    for row in result["top_relationships"]:
        print(json.dumps(row, ensure_ascii=False, default=str, sort_keys=True))

    incomplete_children = (
        result["evaluations_without_lineage"]
        + result["explanations_without_lineage"]
    )
    if incomplete_children:
        print("\nWARNING: existen runs evaluate/explain sin parent training")
    elif result["unresolved_run_count"] or result["ambiguous_checkpoint_count"]:
        print("\nWARNING: existen checkpoints ambiguos o runs con lineage unresolved")
    else:
        print("\nOK: lineage completo")


def main():
    try:
        result = diagnose_run_lineage()
    except MissingLineageSchemaError as exc:
        print(f"ERROR: tabla/vistas no existen: {', '.join(exc.missing_objects)}")
        return 1
    except Exception as exc:
        print(f"ERROR: no se pudo diagnosticar run lineage: {exc}")
        return 1

    print_diagnostics(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
