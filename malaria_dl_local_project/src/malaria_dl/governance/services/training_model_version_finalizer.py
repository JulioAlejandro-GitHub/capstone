"""Finalize the immutable model version produced by a successful TRAIN run."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from uuid import UUID

from sqlalchemy import text

from src.config import LABEL_MAPPING_METADATA


class TrainingModelVersionFinalizationError(RuntimeError):
    pass


@dataclass(frozen=True)
class FinalizationResult:
    training_run_id: str
    model_version_id: str | None
    action: str
    reason: str | None = None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _object(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _contract(row: dict[str, Any]) -> dict[str, Any]:
    metadata = _object(row.get("metadata"))
    model_metadata = _object(metadata.get("model_metadata"))
    execution = _object(row.get("execution_parameters"))
    parameters = _object(row.get("parameters"))
    preprocessing = (
        model_metadata.get("preprocessing")
        or execution.get("preprocessing")
        or parameters.get("preprocessing")
        or metadata.get("preprocessing_mode")
    )
    img_size = int(
        model_metadata.get("img_size")
        or execution.get("img_size")
        or parameters.get("img_size")
        or 200
    )
    mapping = dict(LABEL_MAPPING_METADATA)
    mapping.update({"positive_class": 1, "positive_label": "parasitized"})
    return {
        "preprocessing": {"mode": preprocessing or "rescale_0_1"},
        "mapping": mapping,
        "input": {"shape": [None, img_size, img_size, 3], "dtype": "float32"},
        "output": {"shape": [None, 1], "dtype": "float32"},
    }


def finalize_training_model_version(
    training_run_id: str,
    *,
    connection_factory: Callable | None = None,
    dry_run: bool = False,
) -> FinalizationResult:
    """Complete a discovered version from the exact checkpoint artifact.

    The operation is idempotent. Governed versions are verified and never
    rewritten; only the mutable ``discovered`` row for this TRAIN may change.
    """
    try:
        normalized_run_id = str(UUID(str(training_run_id)))
    except ValueError as exc:
        raise TrainingModelVersionFinalizationError("training_run_id inválido") from exc
    if connection_factory is None:
        from src.db import get_connection

        connection_factory = get_connection

    with connection_factory() as connection:
        connection.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"finalize-training-model-version:{normalized_run_id}"},
        )
        rows = connection.execute(
            text(
                """
                SELECT mv.*, r.run_type, r.status AS run_status, r.parameters,
                       r.execution_parameters, m.name AS registered_model_name
                FROM runs r
                JOIN model_versions mv ON mv.training_run_id=r.id
                LEFT JOIN models m ON m.id=r.model_id
                WHERE r.id=CAST(:run_id AS uuid)
                ORDER BY mv.created_at DESC, mv.id
                FOR UPDATE OF mv
                """
            ),
            {"run_id": normalized_run_id},
        ).mappings().all()
        if not rows:
            raise TrainingModelVersionFinalizationError(
                "TRAIN sin model_version registrada"
            )
        if any(row["run_type"] != "training" for row in rows):
            raise TrainingModelVersionFinalizationError("el run no es TRAIN")
        mutable = [dict(row) for row in rows if row["status"] == "discovered"]
        governed = [dict(row) for row in rows if row["status"] != "discovered"]
        if governed:
            row = governed[0]
            required = (
                row.get("lineage_status") == "resolved"
                and row.get("checkpoint_artifact_id")
                and row.get("artifact_sha256")
            )
            if not required:
                raise TrainingModelVersionFinalizationError(
                    "model_version inmutable incompleta"
                )
            return FinalizationResult(normalized_run_id, str(row["id"]), "unchanged")
        if len(mutable) != 1:
            raise TrainingModelVersionFinalizationError(
                "se requiere exactamente una model_version discovered"
            )
        row = mutable[0]
        checkpoint_path = row.get("best_model_path") or row.get("checkpoint_path")
        artifacts = connection.execute(
            text(
                """
                SELECT id::text, path, checksum, file_size_bytes, artifact_uri
                FROM artifacts
                WHERE run_id=CAST(:run_id AS uuid)
                  AND path=:path
                  AND artifact_type='model_checkpoint'
                ORDER BY created_at DESC, id
                """
            ),
            {"run_id": normalized_run_id, "path": checkpoint_path},
        ).mappings().all()
        if len(artifacts) != 1:
            raise TrainingModelVersionFinalizationError(
                "se requiere exactamente un model_checkpoint para el TRAIN"
            )
        artifact = dict(artifacts[0])
        path = Path(str(artifact["path"])).expanduser().resolve()
        if not path.is_file():
            raise TrainingModelVersionFinalizationError(f"checkpoint inexistente: {path}")
        actual_sha = _sha256(path)
        registered_sha = str(artifact.get("checksum") or "").lower()
        if actual_sha != registered_sha:
            raise TrainingModelVersionFinalizationError(
                "SHA-256 del checkpoint no coincide con artifacts.checksum"
            )
        actual_size = path.stat().st_size
        if artifact.get("file_size_bytes") is not None and int(artifact["file_size_bytes"]) != actual_size:
            raise TrainingModelVersionFinalizationError(
                "tamaño del checkpoint no coincide con artifacts.file_size_bytes"
            )
        if dry_run:
            return FinalizationResult(normalized_run_id, str(row["id"]), "would_finalize")

        contract = _contract(row)
        audit = {
            "last_audit_event": "training_model_version_finalized",
            "source": "training_close",
            "training_run_id": normalized_run_id,
            "checkpoint_artifact_id": artifact["id"],
        }
        updated = connection.execute(
            text(
                """
                UPDATE model_versions SET
                  checkpoint_path=:path,
                  best_model_path=:path,
                  model_name=COALESCE(model_name,:model_name),
                  checkpoint_artifact_id=CAST(:artifact_id AS uuid),
                  artifact_uri=:artifact_uri,
                  artifact_sha256=:sha,
                  artifact_size_bytes=:size,
                  framework=COALESCE(framework,'tensorflow.keras'),
                  preprocessing_profile_snapshot=CAST(:preprocessing AS jsonb),
                  class_mapping=CAST(:mapping AS jsonb),
                  input_signature=CAST(:input AS jsonb),
                  output_signature=CAST(:output AS jsonb),
                  lineage_status='resolved',
                  metadata=metadata||CAST(:audit AS jsonb)
                WHERE id=CAST(:id AS uuid) AND status='discovered'
                RETURNING id::text
                """
            ),
            {
                "id": str(row["id"]),
                "path": str(path),
                "model_name": row.get("registered_model_name") or row.get("model_name"),
                "artifact_id": artifact["id"],
                "artifact_uri": artifact.get("artifact_uri"),
                "sha": actual_sha,
                "size": actual_size,
                "preprocessing": json.dumps(contract["preprocessing"]),
                "mapping": json.dumps(contract["mapping"]),
                "input": json.dumps(contract["input"]),
                "output": json.dumps(contract["output"]),
                "audit": json.dumps(audit),
            },
        ).scalar_one_or_none()
        if not updated:
            raise TrainingModelVersionFinalizationError(
                "la model_version cambió durante la finalización"
            )
        promoted = connection.execute(
            text(
                """
                UPDATE model_versions SET status='candidate'
                WHERE id=CAST(:id AS uuid) AND status='discovered'
                RETURNING id::text
                """
            ),
            {"id": updated},
        ).scalar_one_or_none()
        if not promoted:
            raise TrainingModelVersionFinalizationError(
                "la model_version no pudo promoverse a candidate"
            )
        connection.execute(
            text(
                """
                UPDATE artifacts SET artifact_status='available'
                WHERE id=CAST(:artifact_id AS uuid)
                """
            ),
            {"artifact_id": artifact["id"]},
        )
        connection.execute(
            text(
                """
                UPDATE run_checkpoint_policy
                SET model_version_id=CAST(:model_version_id AS uuid),
                    checkpoint_artifact_id=CAST(:artifact_id AS uuid)
                WHERE run_id=CAST(:run_id AS uuid)
                """
            ),
            {
                "model_version_id": updated,
                "artifact_id": artifact["id"],
                "run_id": normalized_run_id,
            },
        )
        connection.execute(
            text(
                """
                UPDATE run_threshold_calibration
                SET model_version_id=CAST(:model_version_id AS uuid)
                WHERE run_id=CAST(:run_id AS uuid) AND model_version_id IS NULL
                """
            ),
            {"model_version_id": updated, "run_id": normalized_run_id},
        )
    return FinalizationResult(normalized_run_id, str(updated), "finalized")
