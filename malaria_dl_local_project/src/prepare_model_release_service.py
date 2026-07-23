"""Prepare or resume a governed model release from a training run identity."""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from uuid import UUID

from sqlalchemy import text

from src.model_deployment_service import ModelDeploymentService
from src.model_governance.releases import sha256_file
from src.model_governance.repository import create_model_version


EXPECTED_CLASS_MAPPING = {
    "0": "uninfected",
    "1": "parasitized",
    "positive_class": 1,
    "positive_label": "parasitized",
}
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _project_path(value: Any) -> Path:
    path = Path(str(value or "")).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path

NEXT_ACTION_LABELS = {
    "prepare_release": "Preparar despliegue",
    "review_model_version": "Ver modelo liberado",
    "approve_model_version": "Ver modelo liberado",
    "create_deployment": "Continuar despliegue",
    "review_pending_deployment": "Ver despliegue pendiente",
    "view_active_deployment": "Ver despliegue",
    "unavailable": "No disponible",
}


@dataclass(frozen=True)
class BlockingReason:
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass
class PromotionContext:
    training_run_id: str
    training_status: str | None = None
    run_type: str | None = None
    model_name: str | None = None
    model_version: dict[str, Any] | None = None
    versions_count: int = 0
    checkpoint: dict[str, Any] | None = None
    evaluation: dict[str, Any] | None = None
    explainability_run_ids: list[str] = field(default_factory=list)
    threshold: dict[str, Any] | None = None
    deployment: dict[str, Any] | None = None
    preprocessing: dict[str, Any] = field(default_factory=dict)
    class_mapping: dict[str, Any] = field(default_factory=dict)
    input_signature: dict[str, Any] = field(default_factory=dict)
    output_signature: dict[str, Any] = field(default_factory=dict)
    framework: str | None = None
    framework_version: str | None = None
    exists: bool = True
    model_loadable: bool = True


class PrepareModelReleaseService:
    """Resolve/create a model version; never create or activate a deployment."""

    def __init__(
        self,
        connection_factory: Callable | None = None,
        model_loader: Callable[[Path], Any] | None = None,
        deployment_service: ModelDeploymentService | None = None,
    ):
        if connection_factory is None:
            from src.db import get_connection

            connection_factory = get_connection
        self.connection_factory = connection_factory
        self.model_loader = model_loader or self._keras_loader
        self.deployment_service = deployment_service or ModelDeploymentService(
            connection_factory=connection_factory,
            model_loader=self.model_loader,
        )

    @staticmethod
    def _keras_loader(path: Path):
        import tensorflow as tf

        return tf.keras.models.load_model(path, compile=False)

    @staticmethod
    def _uuid(value: str) -> str:
        return str(UUID(str(value)))

    @staticmethod
    def _json(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    @staticmethod
    def _immutable_path(path: str | None, training_run_id: str) -> bool:
        if not path:
            return False
        normalized = str(path).replace("\\", "/")
        return f"/runs/{training_run_id}/" in f"/{normalized.lstrip('/')}"

    @contextmanager
    def _connection(self):
        with self.connection_factory() as connection:
            yield connection

    def _load_context(self, training_run_id: str, *, validate_model: bool) -> PromotionContext:
        context = PromotionContext(training_run_id=training_run_id)
        with self._connection() as connection:
            training = connection.execute(
                text(
                    """
                    SELECT r.id::text, r.run_type, r.status, r.model_id,
                           COALESCE(
                             NULLIF(m.name, ''),
                             NULLIF(r.execution_parameters->>'model_name', ''),
                             NULLIF(r.execution_parameters->>'model', ''),
                             NULLIF(r.parameters->>'model_name', ''),
                             NULLIF(r.parameters->>'model', ''),
                             NULLIF(r.metadata->>'model_name', '')
                           ) AS model_name,
                           r.tensorflow_version, r.keras_version, r.metadata
                    FROM runs r
                    LEFT JOIN models m ON m.id = r.model_id
                    WHERE r.id = :id
                    """
                ),
                {"id": training_run_id},
            ).mappings().one_or_none()
            if training is None:
                context.exists = False
                return context

            context.training_status = training["status"]
            context.run_type = training["run_type"]
            context.model_name = training["model_name"]
            context.framework_version = (
                training.get("keras_version") or training.get("tensorflow_version")
            )

            versions = connection.execute(
                text(
                    """
                    SELECT *
                    FROM model_versions
                    WHERE training_run_id = :id
                    ORDER BY created_at, id
                    """
                ),
                {"id": training_run_id},
            ).mappings().all()
            context.versions_count = len(versions)
            if len(versions) == 1:
                context.model_version = dict(versions[0])

            checkpoint = connection.execute(
                text(
                    """
                    SELECT a.id::text AS checkpoint_artifact_id, a.path,
                           a.artifact_uri, LOWER(a.checksum) AS artifact_sha256,
                           a.file_size_bytes AS artifact_size_bytes,
                           a.artifact_status, a.metadata,
                           policy.policy_satisfied,
                           policy.prediction_collapse_detected
                    FROM artifacts a
                    LEFT JOIN LATERAL (
                        SELECT policy_satisfied, prediction_collapse_detected
                        FROM run_checkpoint_policy
                        WHERE run_id = :id
                          AND (
                            checkpoint_artifact_id = a.id
                            OR checkpoint_path = a.path
                          )
                        ORDER BY created_at DESC
                        LIMIT 1
                    ) policy ON TRUE
                    WHERE a.run_id = :id
                      AND (
                        a.artifact_type = 'model_checkpoint'
                        OR LOWER(a.name) = 'best_model.keras'
                        OR LOWER(a.path) LIKE '%.keras'
                      )
                    ORDER BY
                      CASE WHEN a.path LIKE :immutable_pattern THEN 0 ELSE 1 END,
                      a.created_at DESC
                    """
                ),
                {
                    "id": training_run_id,
                    "immutable_pattern": f"%/runs/{training_run_id}/%",
                },
            ).mappings().all()

            if context.model_version and context.model_version.get("checkpoint_artifact_id"):
                matching = [
                    row
                    for row in checkpoint
                    if str(row["checkpoint_artifact_id"])
                    == str(context.model_version["checkpoint_artifact_id"])
                ]
                if len(matching) == 1:
                    context.checkpoint = dict(matching[0])
            else:
                immutable = [
                    row
                    for row in checkpoint
                    if self._immutable_path(row.get("path"), training_run_id)
                    or bool(row.get("artifact_uri"))
                ]
                if len(immutable) == 1:
                    context.checkpoint = dict(immutable[0])

            metadata = self._json(training.get("metadata"))
            model_metadata = self._json(metadata.get("model_metadata"))
            if context.model_version:
                context.preprocessing = self._json(
                    context.model_version.get("preprocessing_profile_snapshot")
                )
                context.class_mapping = self._json(
                    context.model_version.get("class_mapping")
                )
                context.input_signature = self._json(
                    context.model_version.get("input_signature")
                )
                context.output_signature = self._json(
                    context.model_version.get("output_signature")
                )
                context.framework = context.model_version.get("framework")
            else:
                raw_preprocessing = (
                    model_metadata.get("preprocessing")
                    or metadata.get("preprocessing")
                )
                context.preprocessing = (
                    {"mode": raw_preprocessing}
                    if isinstance(raw_preprocessing, str) and raw_preprocessing.strip()
                    else self._json(raw_preprocessing)
                )
                context.class_mapping = self._json(
                    model_metadata.get("class_mapping")
                    or metadata.get("label_mapping")
                )
                if not context.class_mapping and (
                    model_metadata.get("negative_class_index") == 0
                    and model_metadata.get("negative_class_name") == "uninfected"
                    and model_metadata.get("positive_class_index") == 1
                    and model_metadata.get("positive_class_name") == "parasitized"
                ):
                    context.class_mapping = dict(EXPECTED_CLASS_MAPPING)
                context.input_signature = self._json(
                    model_metadata.get("input_signature")
                )
                context.output_signature = self._json(
                    model_metadata.get("output_signature")
                )
                context.framework = (
                    model_metadata.get("framework")
                    or ("keras" if context.checkpoint else None)
                )

            version_id = (
                str(context.model_version["id"]) if context.model_version else None
            )
            artifact_id = (
                context.checkpoint.get("checkpoint_artifact_id")
                if context.checkpoint
                else None
            )
            evaluations = connection.execute(
                text(
                    """
                    SELECT child.id::text AS evaluation_run_id, child.status,
                           lineage.model_version_id::text,
                           lineage.checkpoint_artifact_id::text,
                           metrics.split_name, metrics.prediction_collapse,
                           metrics.threshold_used
                    FROM run_lineage lineage
                    JOIN runs child ON child.id = lineage.child_run_id
                    LEFT JOIN LATERAL (
                      SELECT split_name, prediction_collapse, threshold_used
                      FROM run_clinical_metrics
                      WHERE run_id = child.id
                      ORDER BY
                        CASE WHEN split_name IN ('test', 'external') THEN 0 ELSE 1 END,
                        created_at DESC
                      LIMIT 1
                    ) metrics ON TRUE
                    WHERE lineage.parent_run_id = :training_id
                      AND lineage.relationship_type = 'evaluates_checkpoint_from'
                      AND child.run_type = 'evaluation'
                      AND (CAST(:version_id AS uuid) IS NULL OR lineage.model_version_id = CAST(:version_id AS uuid))
                      AND (CAST(:artifact_id AS uuid) IS NULL OR lineage.checkpoint_artifact_id = CAST(:artifact_id AS uuid))
                    ORDER BY child.finished_at DESC NULLS LAST, child.id
                    """
                ),
                {
                    "training_id": training_run_id,
                    "version_id": version_id,
                    "artifact_id": artifact_id,
                },
            ).mappings().all()
            completed_evaluations = [
                dict(row) for row in evaluations if row["status"] == "completed"
            ]
            if len(completed_evaluations) == 1:
                context.evaluation = completed_evaluations[0]

            explanations = connection.execute(
                text(
                    """
                    SELECT child.id::text
                    FROM run_lineage lineage
                    JOIN runs child ON child.id = lineage.child_run_id
                    WHERE lineage.parent_run_id = :training_id
                      AND lineage.relationship_type = 'explains_checkpoint_from'
                      AND child.run_type = 'explainability'
                      AND child.status = 'completed'
                      AND (CAST(:version_id AS uuid) IS NULL OR lineage.model_version_id = CAST(:version_id AS uuid))
                      AND (CAST(:artifact_id AS uuid) IS NULL OR lineage.checkpoint_artifact_id = CAST(:artifact_id AS uuid))
                    ORDER BY child.finished_at DESC NULLS LAST, child.id
                    """
                ),
                {
                    "training_id": training_run_id,
                    "version_id": version_id,
                    "artifact_id": artifact_id,
                },
            ).scalars().all()
            context.explainability_run_ids = [str(item) for item in explanations]

            thresholds = connection.execute(
                text(
                    """
                    SELECT run_threshold_calibration_id::text AS id,
                           threshold_selected AS value,
                           threshold_source AS source,
                           calibration_split,
                           calibration_status,
                           positive_label,
                           score_name
                    FROM run_threshold_calibration
                    WHERE (CAST(:version_id AS uuid) IS NULL OR model_version_id = CAST(:version_id AS uuid))
                      AND (
                        run_id = CAST(:training_id AS uuid)
                        OR (CAST(:evaluation_id AS uuid) IS NOT NULL AND run_id = CAST(:evaluation_id AS uuid))
                      )
                    ORDER BY created_at DESC
                    """
                ),
                {
                    "training_id": training_run_id,
                    "version_id": version_id,
                    "evaluation_id": (
                        context.evaluation.get("evaluation_run_id")
                        if context.evaluation
                        else None
                    ),
                },
            ).mappings().all()
            valid_thresholds = [
                dict(row)
                for row in thresholds
                if row.get("positive_label") == "parasitized"
                and row.get("score_name") == "probability_parasitized"
                and row.get("calibration_status") in {"recorded", "validated"}
            ]
            if valid_thresholds:
                threshold = valid_thresholds[0]
                threshold["evaluated_on_test"] = bool(
                    context.evaluation
                    and context.evaluation.get("split_name") in {"test", "external"}
                    and context.evaluation.get("threshold_used") is not None
                )
                context.threshold = threshold

            if version_id:
                deployments = connection.execute(
                    text(
                        """
                        SELECT id::text, status, environment, alias, metadata, created_at
                        FROM deployed_model_versions
                        WHERE model_version_id = CAST(:version_id AS uuid)
                          AND status IN ('pending', 'failed', 'active')
                        ORDER BY
                          CASE
                            WHEN environment='production' AND alias='champion' AND status='active' THEN 0
                            WHEN status='active' THEN 1
                            WHEN status='pending' THEN 2
                            ELSE 3
                          END,
                          created_at DESC
                        """
                    ),
                    {"version_id": version_id},
                ).mappings().all()
                if deployments:
                    context.deployment = dict(deployments[0])

        if validate_model and context.checkpoint:
            path = _project_path(context.checkpoint.get("path")).resolve()
            try:
                if not path.is_file():
                    context.model_loadable = False
                else:
                    self.model_loader(path)
            except Exception:
                context.model_loadable = False
        return context

    def _release_blockers(self, context: PromotionContext) -> list[BlockingReason]:
        reasons: list[BlockingReason] = []
        if not context.exists:
            return [BlockingReason("TRAINING_RUN_NOT_FOUND", "Training run no encontrado.")]
        if context.run_type != "training":
            reasons.append(BlockingReason("INVALID_RUN_TYPE", "El run no es TRAIN."))
        if context.training_status != "completed":
            reasons.append(
                BlockingReason("TRAINING_NOT_COMPLETED", "El entrenamiento no está completed.")
            )
        if not context.model_name:
            reasons.append(
                BlockingReason("MODEL_NAME_REQUIRED", "No se pudo identificar model_name.")
            )
        if context.versions_count > 1:
            reasons.append(
                BlockingReason(
                    "MODEL_VERSION_CONFLICT",
                    "El training run tiene más de una model_version y requiere resolución manual.",
                )
            )
        if not context.checkpoint:
            reasons.append(
                BlockingReason(
                    "CHECKPOINT_NOT_FOUND",
                    "No existe un checkpoint inmutable inequívoco.",
                )
            )
            return reasons
        checkpoint = context.checkpoint
        if not (
            self._immutable_path(checkpoint.get("path"), context.training_run_id)
            or checkpoint.get("artifact_uri")
        ):
            reasons.append(
                BlockingReason(
                    "UNRESOLVED_LINEAGE",
                    "Una ruta genérica no constituye evidencia suficiente de linaje.",
                )
            )
        path = _project_path(checkpoint.get("path")).resolve()
        if not path.is_file():
            reasons.append(
                BlockingReason("CHECKPOINT_NOT_FOUND", "El artifact registrado no está disponible.")
            )
        else:
            expected = str(checkpoint.get("artifact_sha256") or "").lower()
            if not expected or sha256_file(path) != expected:
                reasons.append(
                    BlockingReason(
                        "CHECKPOINT_HASH_MISMATCH",
                        "El SHA-256 no coincide con el artifact registrado.",
                    )
                )
        if context.model_version:
            if context.model_version.get("status") in {"rejected", "retired"}:
                reasons.append(
                    BlockingReason(
                        "MODEL_VERSION_CONFLICT",
                        "La model_version existente está en un estado terminal.",
                    )
                )
            if str(context.model_version.get("training_run_id")) != context.training_run_id:
                reasons.append(
                    BlockingReason(
                        "UNRESOLVED_LINEAGE",
                        "source_training_run_id es inconsistente con la model_version.",
                    )
                )
            if str(context.model_version.get("checkpoint_artifact_id")) != str(
                checkpoint.get("checkpoint_artifact_id")
            ):
                reasons.append(
                    BlockingReason(
                        "MODEL_VERSION_CONFLICT",
                        "La model_version referencia otro checkpoint artifact.",
                    )
                )
            if str(context.model_version.get("artifact_sha256") or "").lower() != str(
                checkpoint.get("artifact_sha256") or ""
            ).lower():
                reasons.append(
                    BlockingReason(
                        "CHECKPOINT_HASH_MISMATCH",
                        "El SHA-256 de la model_version no coincide con el artifact.",
                    )
                )
            if context.model_version.get("lineage_status") != "resolved":
                reasons.append(
                    BlockingReason("UNRESOLVED_LINEAGE", "El linaje no está resolved.")
                )
        if not context.preprocessing:
            reasons.append(
                BlockingReason("PREPROCESSING_REQUIRED", "Falta preprocessing registrado.")
            )
        mapping = {str(key): value for key, value in context.class_mapping.items()}
        if (
            mapping.get("positive_class_index") == 1
            and mapping.get("positive_class_name") == "parasitized"
        ):
            mapping.setdefault("positive_class", 1)
            mapping.setdefault("positive_label", "parasitized")
        if any(mapping.get(key) != value for key, value in EXPECTED_CLASS_MAPPING.items()):
            reasons.append(
                BlockingReason(
                    "CLASS_MAPPING_INVALID",
                    "class_mapping no respeta la convención clínica.",
                )
            )
        if not context.model_loadable:
            reasons.append(
                BlockingReason("MODEL_NOT_LOADABLE", "El checkpoint no puede cargarse.")
            )
        return reasons

    def _deployment_blockers(self, context: PromotionContext) -> list[BlockingReason]:
        reasons: list[BlockingReason] = []
        version = context.model_version
        if not version or version.get("status") not in {"validated", "approved", "deployed"}:
            reasons.append(
                BlockingReason(
                    "DEPLOYMENT_NOT_ALLOWED",
                    "La model_version todavía no está validada o aprobada.",
                )
            )
        if not context.evaluation:
            reasons.append(
                BlockingReason("EVALUATION_REQUIRED", "Falta una evaluación formal vinculada.")
            )
        elif context.evaluation.get("split_name") not in {"test", "external"}:
            reasons.append(
                BlockingReason(
                    "EVALUATION_REQUIRED",
                    "La evaluación formal debe incluir test o external.",
                )
            )
        collapse = self._json(
            context.evaluation.get("prediction_collapse") if context.evaluation else None
        )
        if collapse.get("collapsed") is True:
            reasons.append(
                BlockingReason(
                    "DEPLOYMENT_NOT_ALLOWED",
                    "La evaluación registra colapso de predicciones.",
                )
            )
        if not context.threshold or not context.threshold.get("evaluated_on_test"):
            reasons.append(
                BlockingReason(
                    "CLINICAL_THRESHOLD_REQUIRED",
                    "Falta un threshold clínico evaluado en test.",
                )
            )
        if version and not reasons:
            try:
                self.deployment_service.validate_activation(
                    str(version["id"]), str(context.threshold["id"])
                )
            except Exception:
                reasons.append(
                    BlockingReason(
                        "DEPLOYMENT_NOT_ALLOWED",
                        "La validación del servicio de deployment rechazó la versión.",
                    )
                )
        return reasons

    @staticmethod
    def _next_action(context: PromotionContext, release_blockers, deploy_blockers) -> str:
        if release_blockers:
            return "unavailable"
        if context.deployment:
            if context.deployment.get("status") == "active":
                return "view_active_deployment"
            return "review_pending_deployment"
        if not context.model_version:
            return "prepare_release"
        status = context.model_version.get("status")
        if status in {"rejected", "retired"}:
            return "unavailable"
        if status in {"discovered", "candidate"}:
            return "review_model_version"
        if status == "validated":
            return "approve_model_version"
        if not deploy_blockers:
            return "create_deployment"
        return "review_model_version"

    @staticmethod
    def _target_url(action: str, context: PromotionContext) -> str | None:
        if action in {
            "review_model_version",
            "approve_model_version",
            "create_deployment",
        } and context.model_version:
            return f"/modelo-ia/modelos-liberados/{context.model_version['id']}"
        if action in {"review_pending_deployment", "view_active_deployment"}:
            return f"/modelo-ia/despliegues/{context.deployment['id']}"
        return None

    def _response(self, context: PromotionContext) -> dict[str, Any]:
        release_blockers = self._release_blockers(context)
        deploy_blockers = (
            self._deployment_blockers(context) if not release_blockers else []
        )
        action = self._next_action(context, release_blockers, deploy_blockers)
        blockers = release_blockers or deploy_blockers
        version = context.model_version or {}
        deployment = context.deployment or {}
        threshold = context.threshold
        return {
            "training_run_id": context.training_run_id,
            "training_status": context.training_status,
            "model_name": context.model_name,
            "model_version_id": str(version["id"]) if version.get("id") else None,
            "model_version_status": version.get("status"),
            "lineage_status": version.get("lineage_status")
            or ("resolved" if context.checkpoint and not release_blockers else "unresolved"),
            "evaluation_run_id": (
                context.evaluation.get("evaluation_run_id")
                if context.evaluation
                else None
            ),
            "explainability_run_ids": context.explainability_run_ids,
            "checkpoint_sha256": (
                context.checkpoint.get("artifact_sha256") if context.checkpoint else None
            ),
            "threshold": (
                {
                    "value": float(threshold["value"]),
                    "source": threshold["source"],
                    "evaluated_on_test": bool(threshold["evaluated_on_test"]),
                }
                if threshold
                else None
            ),
            "can_release": not release_blockers,
            "can_deploy": not release_blockers and not deploy_blockers,
            "deployment_id": str(deployment["id"]) if deployment.get("id") else None,
            "deployment_status": deployment.get("status"),
            "environment": deployment.get("environment"),
            "alias": deployment.get("alias"),
            "production_scope": self._json(deployment.get("metadata")).get("production_scope"),
            "next_action": action,
            "button_label": NEXT_ACTION_LABELS[action],
            "button_enabled": action != "unavailable",
            "blocking_reasons": [reason.as_dict() for reason in blockers],
            "target_url": self._target_url(action, context),
            "has_active_production_model": bool(
                deployment.get("status") == "active"
                and deployment.get("environment") == "production"
                and deployment.get("alias") == "champion"
            ),
        }

    def promotion_status(self, training_run_id: str) -> dict[str, Any]:
        """Read-only promotion state; it performs no inserts or updates."""
        normalized = self._uuid(training_run_id)
        return self._response(self._load_context(normalized, validate_model=True))

    def _create_model_version(self, context: PromotionContext) -> str:
        checkpoint = context.checkpoint or {}
        class_mapping = {str(key): value for key, value in context.class_mapping.items()}
        if (
            class_mapping.get("positive_class_index") == 1
            and class_mapping.get("positive_class_name") == "parasitized"
        ):
            class_mapping.setdefault("positive_class", 1)
            class_mapping.setdefault("positive_label", "parasitized")
        with self._connection() as connection:
            connection.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                {"key": f"prepare-release:{context.training_run_id}"},
            )
            existing = connection.execute(
                text(
                    """
                    SELECT id::text
                    FROM model_versions
                    WHERE training_run_id = :training_run_id
                       OR checkpoint_artifact_id = CAST(:artifact_id AS uuid)
                    ORDER BY created_at, id
                    """
                ),
                {
                    "training_run_id": context.training_run_id,
                    "artifact_id": checkpoint["checkpoint_artifact_id"],
                },
            ).scalars().all()
            if len(existing) == 1:
                return str(existing[0])
            if len(existing) > 1:
                raise RuntimeError("MODEL_VERSION_CONFLICT")
            version_number = connection.execute(
                text(
                    """
                    SELECT COALESCE(MAX(version_number), 0) + 1
                    FROM model_versions
                    WHERE model_name = :model_name
                    """
                ),
                {"model_name": context.model_name},
            ).scalar_one()
            created = create_model_version(
                training_run_id=context.training_run_id,
                model_name=str(context.model_name),
                version_number=int(version_number),
                checkpoint_artifact_id=checkpoint["checkpoint_artifact_id"],
                artifact_path=str(checkpoint["path"]),
                artifact_uri=checkpoint.get("artifact_uri"),
                artifact_sha256=str(checkpoint["artifact_sha256"]),
                artifact_size_bytes=int(checkpoint["artifact_size_bytes"]),
                framework=str(context.framework or "keras"),
                framework_version=context.framework_version,
                preprocessing_profile_snapshot=context.preprocessing,
                class_mapping=class_mapping,
                input_signature=context.input_signature,
                output_signature=context.output_signature,
                status="candidate",
                lineage_status="resolved",
                metadata={"source": "PrepareModelReleaseService"},
                connection_or_session=connection,
            )
            return str(created.id)

    def _audit(
        self,
        *,
        training_run_id: str,
        requester: str | None,
        request_id: str | None,
        model_version_id: str | None,
        result: str,
        blockers: list[dict[str, str]],
        target_environment: str | None,
    ) -> None:
        payload = {
            "action": "prepare_release",
            "requester": requester,
            "request_id": request_id,
            "training_run_id": training_run_id,
            "model_version_id": model_version_id,
            "result": result,
            "blocking_reasons": blockers,
            "target_environment": target_environment,
        }
        with self._connection() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO execution_logs
                      (run_id, log_level, message, source, metadata)
                    VALUES
                      (CAST(:run_id AS uuid), :level, :message, :source, CAST(:metadata AS jsonb))
                    """
                ),
                {
                    "run_id": training_run_id,
                    "level": "INFO" if result == "prepared" else "WARNING",
                    "message": f"prepare_release:{result}",
                    "source": "PrepareModelReleaseService",
                    "metadata": json.dumps(payload, ensure_ascii=False, sort_keys=True),
                },
            )

    def prepare_release(
        self,
        training_run_id: str,
        *,
        requester: str | None = None,
        target_environment: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        normalized = self._uuid(training_run_id)
        context = self._load_context(normalized, validate_model=True)
        initial = self._response(context)
        if initial["can_release"] and not context.model_version:
            self._create_model_version(context)
            context = self._load_context(normalized, validate_model=False)
        response = self._response(context)
        if context.exists:
            self._audit(
                training_run_id=normalized,
                requester=requester,
                request_id=request_id,
                model_version_id=response["model_version_id"],
                result="prepared" if response["can_release"] else "blocked",
                blockers=response["blocking_reasons"],
                target_environment=target_environment,
            )
        return response
