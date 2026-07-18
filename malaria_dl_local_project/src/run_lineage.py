"""Persistencia y resolución del linaje entre ejecuciones de modelos.

El módulo mantiene deliberadamente separadas dos operaciones:

* resolver qué entrenamiento produjo un checkpoint;
* persistir la relación una vez que el run hijo ya existe.

Nunca se selecciona el entrenamiento más reciente para una ruta mutable. Si una
coincidencia exacta apunta a más de un entrenamiento, el resultado es ambiguo y
el llamador debe solicitar ``--source-training-run-id``.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from uuid import UUID

from sqlalchemy import text

from src.db import get_connection


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RELATIONSHIP_TYPES = {
    "evaluates_checkpoint_from",
    "explains_checkpoint_from",
    "derived_from",
}
LINEAGE_CONFIDENCES = {
    "explicit",
    "inferred_exact_checkpoint",
    "inferred_model_version",
    "inferred_heuristic",
    "unknown",
}
_UUID_PATTERN = re.compile(
    r"(?<![0-9a-fA-F])"
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    r"(?![0-9a-fA-F])"
)


class LineageResolutionError(ValueError):
    """Error de validación de una referencia explícita de linaje."""


def _json(value: dict | None) -> str:
    return json.dumps(value or {}, ensure_ascii=False, default=str)


def _validated_uuid(value: str, field_name: str) -> str:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise LineageResolutionError(
            f"{field_name} debe ser un UUID válido. Valor recibido: {value!r}."
        ) from exc


def _checkpoint_path_candidates(checkpoint_path: str) -> list[str]:
    """Representaciones canónicas del mismo path, sin hacer matching por basename."""
    raw_path = str(checkpoint_path).strip()
    if not raw_path:
        return []

    candidates: list[str] = []

    def add(value: str | Path) -> None:
        normalized = str(value)
        if normalized and normalized not in candidates:
            candidates.append(normalized)

    add(raw_path)
    add(os.path.normpath(raw_path))

    path = Path(raw_path).expanduser()
    try:
        absolute_path = path.resolve(strict=False)
        add(absolute_path)
        try:
            add(absolute_path.relative_to(PROJECT_ROOT))
        except ValueError:
            pass
    except (OSError, RuntimeError):
        pass

    if not path.is_absolute():
        project_path = (PROJECT_ROOT / path).resolve(strict=False)
        add(project_path)
        try:
            add(project_path.relative_to(PROJECT_ROOT))
        except ValueError:
            pass

    return candidates


def _fetch_all(sql: str, params: dict | None = None) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(text(sql), params or {}).mappings().all()
    return [dict(row) for row in rows]


def _training_run_projection(run_alias: str = "r", model_alias: str = "m") -> str:
    return f"""
        {run_alias}.id::text AS training_run_id,
        {run_alias}.id::text AS id,
        {run_alias}.run_name,
        {run_alias}.run_type,
        {run_alias}.status AS training_status,
        {run_alias}.command,
        {run_alias}.started_at,
        COALESCE(
            NULLIF({model_alias}.name, ''),
            NULLIF({run_alias}.execution_parameters->>'model_name', ''),
            NULLIF({run_alias}.execution_parameters->>'model', ''),
            NULLIF({run_alias}.parameters->>'model_name', ''),
            NULLIF({run_alias}.parameters->>'model', ''),
            NULLIF({run_alias}.metadata->>'model_name', '')
        ) AS model_name,
        COALESCE(
            NULLIF({run_alias}.execution_parameters->>'optimizer', ''),
            NULLIF(
                {run_alias}.execution_parameters
                    #>> ARRAY['cli_arguments', 'optimizer'],
                ''
            ),
            NULLIF({run_alias}.parameters->>'optimizer', ''),
            NULLIF(
                {run_alias}.parameters
                    #>> ARRAY['execution_parameters', 'optimizer'],
                ''
            ),
            NULLIF(
                {run_alias}.parameters #>> ARRAY['cli_arguments', 'optimizer'],
                ''
            ),
            NULLIF({run_alias}.metadata->>'optimizer', ''),
            substring(
                {run_alias}.command
                FROM '--optimizer[[:space:]=]+([^[:space:]]+)'
            )
        ) AS optimizer
    """


def get_training_run(training_run_id: str) -> dict | None:
    """Obtiene un run por UUID; devuelve también modelo, optimizer y comando."""
    run_id = _validated_uuid(training_run_id, "source_training_run_id")
    rows = _fetch_all(
        f"""
        SELECT {_training_run_projection()}
        FROM runs r
        LEFT JOIN models m ON m.id = r.model_id
        WHERE r.id = CAST(:run_id AS uuid)
        LIMIT 1
        """,
        {"run_id": run_id},
    )
    return rows[0] if rows else None


def _resolved_candidate(
    candidate: dict,
    *,
    confidence: str,
    resolution_method: str,
    checkpoint_path: str,
) -> dict:
    result = dict(candidate)
    result.update(
        {
            "status": "resolved",
            "confidence": confidence,
            "resolution_method": resolution_method,
            "checkpoint_path": checkpoint_path,
        }
    )
    result.setdefault("id", result.get("training_run_id"))
    return result


def _unique_training_candidates(rows: list[dict]) -> list[dict]:
    candidates: dict[str, dict] = {}
    for row in rows:
        run_id = str(row.get("training_run_id") or row.get("id") or "")
        if not run_id:
            continue
        if run_id not in candidates:
            candidates[run_id] = dict(row)
            continue

        # Una misma ejecución puede tener más de una fila de model_versions o
        # artifacts. Conservamos los ids disponibles sin volverla ambigua.
        current = candidates[run_id]
        for key in ("model_version_id", "checkpoint_artifact_id", "matched_path"):
            if current.get(key) is None and row.get(key) is not None:
                current[key] = row[key]
    return list(candidates.values())


def _ambiguity_result(
    checkpoint_path: str,
    candidates: list[dict],
    resolution_method: str,
) -> dict:
    return {
        "status": "ambiguous",
        "checkpoint_path": checkpoint_path,
        "resolution_method": resolution_method,
        "confidence": "unknown",
        "message": (
            "No se pudo inferir de forma única el training_run_id. "
            "Use --source-training-run-id."
        ),
        "candidates": candidates,
    }


def find_training_runs_for_model(model_name: str | None) -> list[dict]:
    """Lista candidatos por modelo para diagnosticar un checkpoint genérico.

    Esta función no resuelve linaje: sólo permite distinguir ``unresolved`` de
    ``ambiguous`` y sirve como base explícita para el modo heurístico del
    backfill.
    """
    if not model_name:
        return []

    normalized_name = str(model_name).strip().lower()
    alternate_name = {
        "vgg16_transfer_learning": "vgg16",
        "vgg16": "vgg16_transfer_learning",
    }.get(normalized_name, normalized_name)
    rows = _fetch_all(
        f"""
        SELECT {_training_run_projection()}
        FROM runs r
        LEFT JOIN models m ON m.id = r.model_id
        WHERE r.run_type = 'training'
          AND LOWER(COALESCE(
              NULLIF(m.name, ''),
              NULLIF(r.execution_parameters->>'model_name', ''),
              NULLIF(r.execution_parameters->>'model', ''),
              NULLIF(r.parameters->>'model_name', ''),
              NULLIF(r.parameters->>'model', ''),
              NULLIF(r.metadata->>'model_name', '')
          )) IN (:model_name, :alternate_name)
        ORDER BY r.started_at DESC NULLS LAST, r.created_at DESC
        """,
        {
            "model_name": normalized_name,
            "alternate_name": alternate_name,
        },
    )
    return _unique_training_candidates(rows)


def resolve_training_run_from_checkpoint(
    checkpoint_path: str,
    model_name: str | None = None,
) -> dict | None:
    """Resuelve el entrenamiento origen sin realizar inferencias silenciosas.

    ``model_name`` se conserva como contexto de diagnóstico. No se usa para
    elegir entre dos entrenamientos que escribieron la misma ruta mutable.
    """
    path_candidates = _checkpoint_path_candidates(checkpoint_path)
    if not path_candidates:
        return {
            "status": "unresolved",
            "checkpoint_path": checkpoint_path,
            "model_name": model_name,
            "confidence": "unknown",
            "message": "No se recibió una ruta de checkpoint válida.",
            "candidates": [],
        }

    common_params = {
        "path_0": path_candidates[0],
        "path_1": path_candidates[1] if len(path_candidates) > 1 else path_candidates[0],
        "path_2": path_candidates[2] if len(path_candidates) > 2 else path_candidates[0],
        "path_3": path_candidates[3] if len(path_candidates) > 3 else path_candidates[0],
        "path_4": path_candidates[4] if len(path_candidates) > 4 else path_candidates[0],
    }
    path_predicate = "IN (:path_0, :path_1, :path_2, :path_3, :path_4)"

    exact_rows = _fetch_all(
        f"""
        SELECT exact_matches.*
        FROM (
            SELECT
                {_training_run_projection()},
                mv.id::text AS model_version_id,
                NULL::text AS checkpoint_artifact_id,
                CASE
                    WHEN mv.best_model_path {path_predicate}
                        THEN mv.best_model_path
                    ELSE mv.checkpoint_path
                END AS matched_path,
                'model_versions'::text AS match_source,
                mv.created_at AS matched_created_at
            FROM model_versions mv
            JOIN runs r ON r.id = mv.training_run_id
            LEFT JOIN models m ON m.id = COALESCE(mv.model_id, r.model_id)
            WHERE r.run_type = 'training'
              AND (
                  mv.best_model_path {path_predicate}
                  OR mv.checkpoint_path {path_predicate}
              )

            UNION ALL

            SELECT
                {_training_run_projection()},
                NULL::text AS model_version_id,
                a.id::text AS checkpoint_artifact_id,
                a.path AS matched_path,
                'artifacts'::text AS match_source,
                a.created_at AS matched_created_at
            FROM artifacts a
            JOIN runs r ON r.id = a.run_id
            LEFT JOIN models m ON m.id = r.model_id
            WHERE r.run_type = 'training'
              AND a.path {path_predicate}
              AND (
                  LOWER(a.artifact_type) IN (
                      'checkpoint', 'model', 'best_model', 'final_model',
                      'keras_model', 'model_checkpoint',
                      'immutable_checkpoint'
                  )
                  OR LOWER(a.artifact_type) LIKE '%checkpoint%'
                  OR LOWER(a.artifact_type) LIKE '%model%'
              )
        ) AS exact_matches
        ORDER BY exact_matches.matched_created_at DESC
        """,
        common_params,
    )
    exact_candidates = _unique_training_candidates(exact_rows)
    if len(exact_candidates) == 1:
        candidate = exact_candidates[0]
        matched_model_version = bool(candidate.get("model_version_id"))
        return _resolved_candidate(
            candidate,
            confidence=(
                "inferred_model_version"
                if matched_model_version
                else "inferred_exact_checkpoint"
            ),
            resolution_method=(
                "model_versions_exact_checkpoint"
                if matched_model_version
                else "artifact_exact_checkpoint"
            ),
            checkpoint_path=str(checkpoint_path),
        )
    if len(exact_candidates) > 1:
        return _ambiguity_result(
            str(checkpoint_path),
            exact_candidates,
            "exact_checkpoint_source_conflict",
        )

    embedded_ids = []
    for candidate_path in path_candidates:
        for match in _UUID_PATTERN.findall(candidate_path):
            normalized_id = str(UUID(match))
            if normalized_id not in embedded_ids:
                embedded_ids.append(normalized_id)

    immutable_candidates = []
    for embedded_id in embedded_ids:
        candidate = get_training_run(embedded_id)
        if candidate and candidate.get("run_type") == "training":
            immutable_candidates.append(candidate)
    immutable_candidates = _unique_training_candidates(immutable_candidates)
    if len(immutable_candidates) == 1:
        return _resolved_candidate(
            immutable_candidates[0],
            confidence="inferred_exact_checkpoint",
            resolution_method="immutable_run_path",
            checkpoint_path=str(checkpoint_path),
        )
    if len(immutable_candidates) > 1:
        return _ambiguity_result(
            str(checkpoint_path),
            immutable_candidates,
            "immutable_run_path",
        )

    generic_candidates = find_training_runs_for_model(model_name)
    if len(generic_candidates) > 1:
        return _ambiguity_result(
            str(checkpoint_path),
            generic_candidates,
            "generic_checkpoint_model_candidates",
        )

    return {
        "status": "unresolved",
        "checkpoint_path": str(checkpoint_path),
        "model_name": model_name,
        "confidence": "unknown",
        "message": (
            "No se pudo inferir el training_run_id desde el checkpoint. "
            "Use --source-training-run-id."
        ),
        "candidates": generic_candidates,
    }


def resolve_source_training_run(
    source_training_run_id: str | None,
    checkpoint_path: str,
    model_name: str | None = None,
) -> dict:
    """Valida un origen explícito o intenta resolverlo desde el checkpoint."""
    if source_training_run_id:
        source_run = get_training_run(source_training_run_id)
        if source_run is None:
            raise LineageResolutionError(
                "No existe el run indicado por --source-training-run-id: "
                f"{source_training_run_id}."
            )
        if source_run.get("run_type") != "training":
            raise LineageResolutionError(
                "--source-training-run-id debe referenciar un run con "
                f"run_type='training'; se encontró {source_run.get('run_type')!r}."
            )
        return _resolved_candidate(
            source_run,
            confidence="explicit",
            resolution_method="explicit_training_run_id",
            checkpoint_path=str(checkpoint_path),
        )

    result = resolve_training_run_from_checkpoint(
        checkpoint_path,
        model_name=model_name,
    )
    if result is None:
        return {
            "status": "unresolved",
            "checkpoint_path": str(checkpoint_path),
            "confidence": "unknown",
            "message": (
                "No se pudo inferir el training_run_id desde el checkpoint. "
                "Use --source-training-run-id."
            ),
            "candidates": [],
        }
    return result


def _prepare_lineage_insert(
    parent_run_id: str,
    child_run_id: str,
    relationship_type: str,
    checkpoint_path: str | None = None,
    checkpoint_artifact_id: str | None = None,
    model_version_id: str | None = None,
    confidence: str = "explicit",
    metadata: dict | None = None,
) -> dict:
    if relationship_type not in RELATIONSHIP_TYPES:
        raise ValueError(
            f"relationship_type inválido: {relationship_type!r}. "
            f"Opciones: {sorted(RELATIONSHIP_TYPES)}"
        )
    if confidence not in LINEAGE_CONFIDENCES:
        raise ValueError(
            f"confidence inválido: {confidence!r}. "
            f"Opciones: {sorted(LINEAGE_CONFIDENCES)}"
        )

    parent_id = _validated_uuid(parent_run_id, "parent_run_id")
    child_id = _validated_uuid(child_run_id, "child_run_id")
    if parent_id == child_id:
        raise ValueError("Un run no puede ser padre de sí mismo.")

    artifact_id = (
        _validated_uuid(checkpoint_artifact_id, "checkpoint_artifact_id")
        if checkpoint_artifact_id
        else None
    )
    version_id = (
        _validated_uuid(model_version_id, "model_version_id")
        if model_version_id
        else None
    )

    return {
        "parent_run_id": parent_id,
        "child_run_id": child_id,
        "relationship_type": relationship_type,
        "checkpoint_path": str(checkpoint_path) if checkpoint_path else None,
        "checkpoint_artifact_id": artifact_id,
        "model_version_id": version_id,
        "confidence": confidence,
        "metadata": _json(metadata),
    }


def _insert_run_lineage(connection, params: dict) -> str | None:
    row = connection.execute(
        text(
            """
            INSERT INTO run_lineage (
                parent_run_id, child_run_id, relationship_type,
                checkpoint_path, checkpoint_artifact_id, model_version_id,
                confidence, metadata
            )
            VALUES (
                CAST(:parent_run_id AS uuid), CAST(:child_run_id AS uuid),
                :relationship_type, :checkpoint_path,
                CAST(:checkpoint_artifact_id AS uuid),
                CAST(:model_version_id AS uuid), :confidence,
                CAST(:metadata AS jsonb)
            )
            ON CONFLICT (parent_run_id, child_run_id, relationship_type)
            DO UPDATE SET
                checkpoint_path = COALESCE(
                    EXCLUDED.checkpoint_path,
                    run_lineage.checkpoint_path
                ),
                checkpoint_artifact_id = COALESCE(
                    EXCLUDED.checkpoint_artifact_id,
                    run_lineage.checkpoint_artifact_id
                ),
                model_version_id = COALESCE(
                    EXCLUDED.model_version_id,
                    run_lineage.model_version_id
                ),
                confidence = EXCLUDED.confidence,
                metadata = COALESCE(run_lineage.metadata, '{}'::jsonb)
                    || EXCLUDED.metadata
            RETURNING id::text
            """
        ),
        params,
    ).first()
    return str(row[0]) if row else None


def create_run_lineage(
    parent_run_id: str,
    child_run_id: str,
    relationship_type: str,
    checkpoint_path: str | None = None,
    checkpoint_artifact_id: str | None = None,
    model_version_id: str | None = None,
    confidence: str = "explicit",
    metadata: dict | None = None,
) -> str | None:
    """Crea una relación idempotente y devuelve su UUID."""
    params = _prepare_lineage_insert(
        parent_run_id=parent_run_id,
        child_run_id=child_run_id,
        relationship_type=relationship_type,
        checkpoint_path=checkpoint_path,
        checkpoint_artifact_id=checkpoint_artifact_id,
        model_version_id=model_version_id,
        confidence=confidence,
        metadata=metadata,
    )
    with get_connection() as connection:
        return _insert_run_lineage(connection, params)


def _source_training_metadata_payload(
    source_training_run: dict,
    relationship_type: str,
    checkpoint_path: str | None = None,
) -> dict:
    if relationship_type not in RELATIONSHIP_TYPES:
        raise ValueError(f"relationship_type inválido: {relationship_type!r}.")
    source_id = source_training_run.get("training_run_id") or source_training_run.get("id")
    if not source_id:
        raise ValueError("source_training_run no contiene training_run_id.")
    source_id = _validated_uuid(source_id, "source_training_run.training_run_id")

    return {
        "source_training_run_id": source_id,
        "source_training_run_name": source_training_run.get("run_name"),
        "source_model_name": source_training_run.get("model_name"),
        "source_optimizer": source_training_run.get("optimizer"),
        "source_checkpoint_path": (
            str(checkpoint_path)
            if checkpoint_path is not None
            else source_training_run.get("checkpoint_path")
        ),
        "source_relationship_type": relationship_type,
        "lineage_confidence": source_training_run.get("confidence", "unknown"),
        "lineage_status": "resolved",
        "lineage_resolution_method": source_training_run.get("resolution_method"),
    }


def _attach_source_training_metadata(connection, child_id: str, payload: dict) -> None:
    result = connection.execute(
        text(
            """
            UPDATE runs
            SET metadata = (COALESCE(metadata, '{}'::jsonb) - 'lineage_warning')
                    || CAST(:metadata AS jsonb),
                updated_at = NOW()
            WHERE id = CAST(:child_run_id AS uuid)
            """
        ),
        {"child_run_id": child_id, "metadata": _json(payload)},
    )
    rowcount = getattr(result, "rowcount", None)
    if isinstance(rowcount, int) and rowcount != 1:
        raise RuntimeError(
            f"No se pudo actualizar metadata del child_run_id={child_id}."
        )


def attach_source_training_metadata(
    child_run_id: str,
    source_training_run: dict,
    relationship_type: str,
    checkpoint_path: str | None = None,
) -> None:
    """Materializa en runs.metadata el resumen consultable del padre."""
    child_id = _validated_uuid(child_run_id, "child_run_id")
    payload = _source_training_metadata_payload(
        source_training_run,
        relationship_type,
        checkpoint_path,
    )
    with get_connection() as connection:
        _attach_source_training_metadata(connection, child_id, payload)


def create_run_lineage_with_metadata(
    parent_run_id: str,
    child_run_id: str,
    relationship_type: str,
    source_training_run: dict,
    checkpoint_path: str | None = None,
    checkpoint_artifact_id: str | None = None,
    model_version_id: str | None = None,
    confidence: str = "explicit",
    metadata: dict | None = None,
) -> str:
    """Inserta relación y metadata del hijo dentro de una sola transacción."""
    params = _prepare_lineage_insert(
        parent_run_id=parent_run_id,
        child_run_id=child_run_id,
        relationship_type=relationship_type,
        checkpoint_path=checkpoint_path,
        checkpoint_artifact_id=checkpoint_artifact_id,
        model_version_id=model_version_id,
        confidence=confidence,
        metadata=metadata,
    )
    payload_source = dict(source_training_run)
    payload_source["confidence"] = confidence
    payload = _source_training_metadata_payload(
        payload_source,
        relationship_type,
        checkpoint_path,
    )
    if payload["source_training_run_id"] != params["parent_run_id"]:
        raise ValueError(
            "source_training_run no coincide con parent_run_id al registrar linaje."
        )

    with get_connection() as connection:
        lineage_id = _insert_run_lineage(connection, params)
        if not lineage_id:
            raise RuntimeError("No se pudo persistir la relación de run lineage.")
        _attach_source_training_metadata(
            connection,
            params["child_run_id"],
            payload,
        )
    return lineage_id


def mark_lineage_unresolved(
    child_run_id: str,
    checkpoint_path: str | None,
    warning: str,
    *,
    status: str = "unresolved",
) -> None:
    """Guarda un diagnóstico explícito cuando el run puede continuar sin padre."""
    child_id = _validated_uuid(child_run_id, "child_run_id")
    payload = {
        "lineage_status": status,
        "lineage_warning": str(warning),
        "lineage_confidence": "unknown",
        "source_checkpoint_path": (
            str(checkpoint_path) if checkpoint_path is not None else None
        ),
    }
    with get_connection() as connection:
        connection.execute(
            text(
                """
                UPDATE runs
                SET metadata = (
                        COALESCE(metadata, '{}'::jsonb)
                        - ARRAY[
                            'source_training_run_id',
                            'source_training_run_name',
                            'source_model_name',
                            'source_optimizer',
                            'source_relationship_type',
                            'lineage_resolution_method'
                        ]::text[]
                    )
                        || CAST(:metadata AS jsonb),
                    updated_at = NOW()
                WHERE id = CAST(:child_run_id AS uuid)
                """
            ),
            {"child_run_id": child_id, "metadata": _json(payload)},
        )
