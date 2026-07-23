"""PrepareModelReleaseService and Promotion Status governance service."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text

from src.db import get_connection
from src.model_governance.entities import (
    CLINICAL_CLASS_MAPPING,
    POSITIVE_LABEL,
    ModelVersionStatus,
)
from src.model_governance.errors import (
    GovernanceConflictError,
    GovernanceNotFoundError,
    GovernanceStateError,
    GovernanceValidationError,
)
from src.model_governance.releases import sha256_file


logger = logging.getLogger(__name__)

EXPECTED_CLASS_MAPPING = {
    "0": "uninfected",
    "1": "parasitized",
    "positive_class": 1,
    "positive_label": "parasitized",
}


def _uuid_str(val: Any) -> str | None:
    if val is None:
        return None
    try:
        return str(UUID(str(val)))
    except (ValueError, TypeError):
        return None


class PrepareModelReleaseService:
    def __init__(self, connection_factory=None):
        if connection_factory is None:
            connection_factory = get_connection
        self.connection_factory = connection_factory

    def get_promotion_status(self, training_run_id: str | UUID) -> dict[str, Any]:
        """Consulta read-only del estado de promoción sin efectos secundarios."""
        run_id_str = _uuid_str(training_run_id)
        if not run_id_str:
            return {
                "training_run_id": str(training_run_id),
                "model_version_id": None,
                "deployment_id": None,
                "deployment_status": None,
                "environment": None,
                "alias": None,
                "next_action": "unavailable",
                "button_label": "No disponible",
                "button_enabled": False,
                "blocking_reasons": ["TRAINING_RUN_NOT_FOUND: Run ID inválido."],
                "target_url": None,
            }

        with self.connection_factory() as conn:
            return self._evaluate_status(conn, run_id_str)

    def prepare_release(
        self,
        training_run_id: str | UUID,
        requester: str | None = "system",
        target_environment: str | None = "production",
    ) -> dict[str, Any]:
        """Operación idempotente para resolver o registrar una model_version inmutable."""
        run_id_str = _uuid_str(training_run_id)
        if not run_id_str:
            raise GovernanceValidationError(f"Invalid UUID: {training_run_id}")

        with self.connection_factory() as conn:
            status_data = self._evaluate_status(conn, run_id_str)
            run_info = status_data.get("_run_info")

            if not status_data["can_release"] and not status_data.get("model_version_id"):
                reasons = "; ".join(status_data["blocking_reasons"])
                raise GovernanceStateError(f"No se puede liberar el modelo: {reasons}")

            model_version_id = status_data.get("model_version_id")

            # Si no existe model_version, la creamos idempotentemente
            if not model_version_id:
                model_version_id = self._create_model_version_record(
                    conn, status_data["_run_info"], requester or "system"
                )
                self._audit_event(
                    conn,
                    run_id_str,
                    model_version_id,
                    requester or "system",
                    "prepare_release_created",
                    "SUCCESS",
                    [],
                )
                # Re-evaluar estado con la nueva model_version
                status_data = self._evaluate_status(conn, run_id_str)
            else:
                # Actualizar únicamente el estado para respetar la inmutabilidad gobernada en DB
                conn.execute(
                    text("""
                        UPDATE model_versions
                        SET status = 'approved'
                        WHERE id = CAST(:id AS uuid) AND status <> 'approved'
                    """),
                    {"id": model_version_id},
                )
                self._audit_event(
                    conn,
                    run_id_str,
                    model_version_id,
                    requester or "system",
                    "prepare_release_updated",
                    "SUCCESS",
                    [],
                )
                status_data = self._evaluate_status(conn, run_id_str)

            return {
                "training_run_id": run_id_str,
                "training_status": status_data.get("_training_status", "completed"),
                "model_name": status_data.get("_model_name", "custom_model"),
                "model_version_id": status_data.get("model_version_id"),
                "model_version_status": status_data.get("_model_version_status"),
                "lineage_status": status_data.get("_lineage_status", "lineage_resolved"),
                "evaluation_run_id": status_data.get("_evaluation_run_id"),
                "explainability_run_ids": status_data.get("_explainability_run_ids", []),
                "checkpoint_sha256": status_data.get("_checkpoint_sha256"),
                "threshold": status_data.get("_threshold"),
                "can_release": status_data["can_release"],
                "can_deploy": status_data["can_deploy"],
                "next_action": status_data["next_action"],
                "blocking_reasons": status_data["blocking_reasons"],
                "target_url": status_data["target_url"],
            }

    def _evaluate_status(self, conn, run_id: str) -> dict[str, Any]:
        blocking_reasons: list[str] = []

        # 1. Obtener training run
        run = conn.execute(
            text("SELECT * FROM runs WHERE id = :id"), {"id": run_id}
        ).mappings().one_or_none()

        if not run:
            return {
                "training_run_id": run_id,
                "model_version_id": None,
                "deployment_id": None,
                "deployment_status": None,
                "environment": None,
                "alias": None,
                "next_action": "unavailable",
                "button_label": "No disponible",
                "button_enabled": False,
                "blocking_reasons": ["TRAINING_RUN_NOT_FOUND: Run no encontrado en la base."],
                "target_url": None,
                "can_release": False,
                "can_deploy": False,
            }

        run_dict = dict(run)
        run_type = str(run_dict.get("run_type") or "").lower()
        run_status = str(run_dict.get("status") or "").lower()

        if run_type != "training":
            blocking_reasons.append(f"INVALID_RUN_TYPE: El run {run_id} es de tipo '{run_type}', se requiere 'training'.")

        if run_status != "completed":
            blocking_reasons.append(f"TRAINING_NOT_COMPLETED: El entrenamiento no está en estado 'completed' (actual: '{run_status}').")

        model_name = (
            run_dict.get("model_name")
            or (run_dict.get("execution_parameters") or {}).get("model_name")
            or (run_dict.get("parameters") or {}).get("model_name")
            or "custom_model"
        )

        # 2. Checkpoint e Inmutabilidad
        checkpoint_path_str = None
        artifact_sha256 = None
        checkpoint_artifact_id = None

        # Buscar artefacto registrado
        art_row = conn.execute(
            text("""
                SELECT a.id, a.path, COALESCE(a.checksum, a.metadata->>'sha256') AS sha256_hash, a.file_size_bytes
                FROM artifacts a
                WHERE a.run_id = :run_id AND (a.artifact_type IN ('checkpoint', 'model', 'keras_model', 'metrics_json') OR a.path LIKE '%.keras' OR a.path LIKE '%.h5')
                ORDER BY a.created_at DESC LIMIT 1
            """),
            {"run_id": run_id},
        ).mappings().one_or_none()

        if art_row:
            checkpoint_artifact_id = str(art_row["id"])
            checkpoint_path_str = art_row["path"]
            artifact_sha256 = art_row["sha256_hash"]

        if not checkpoint_path_str:
            exec_params = run_dict.get("execution_parameters") or {}
            checkpoint_path_str = exec_params.get("best_model_path") or exec_params.get("checkpoint_path")

        if not checkpoint_path_str:
            blocking_reasons.append("CHECKPOINT_NOT_FOUND: No se encontró artefacto de checkpoint registrado para el entrenamiento.")
        else:
            path_obj = Path(checkpoint_path_str)
            # Verificar si es ruta genérica sin linaje o ambigua
            if path_obj.name in ("best_model.keras", "final_model.keras") and run_id not in str(path_obj):
                # Verificar si en la BD existe mapeo único de linaje
                lineage_check = conn.execute(
                    text("SELECT 1 FROM run_lineage WHERE parent_run_id = :run_id"),
                    {"run_id": run_id},
                ).scalar()
                if not lineage_check and not art_row:
                    blocking_reasons.append("UNRESOLVED_LINEAGE: La ruta del checkpoint es una referencia genérica sin evidencia única de linaje.")

            if path_obj.is_file():
                calc_hash = sha256_file(path_obj)
                if artifact_sha256 and calc_hash != artifact_sha256:
                    blocking_reasons.append("CHECKPOINT_HASH_MISMATCH: El checksum SHA-256 en disco no coincide con el registrado.")
                elif not artifact_sha256:
                    artifact_sha256 = calc_hash

        # 3. Model version existente
        mv_row = conn.execute(
            text("""
                SELECT mv.*,
                       EXISTS(
                           SELECT 1 FROM run_lineage rl JOIN runs er ON er.id = rl.child_run_id
                           WHERE rl.model_version_id = mv.id AND er.run_type = 'evaluation' AND er.status = 'completed'
                       ) has_evaluation,
                       EXISTS(
                           SELECT 1 FROM run_lineage rl JOIN runs xr ON xr.id = rl.child_run_id
                           WHERE rl.model_version_id = mv.id AND xr.run_type = 'explainability' AND xr.status = 'completed'
                       ) has_explainability
                FROM model_versions mv
                WHERE mv.training_run_id = :run_id
                ORDER BY mv.created_at DESC LIMIT 1
            """),
            {"run_id": run_id},
        ).mappings().one_or_none()

        model_version_id = str(mv_row["id"]) if mv_row else None
        mv_status = mv_row["status"] if mv_row else None
        mv_lineage_status = mv_row["lineage_status"] if mv_row else ("resolved" if not blocking_reasons else "unresolved")

        # 4. Evaluación vinculada y Threshold Clínico
        eval_run_id = None
        explain_run_ids = []
        threshold_info = {"value": None, "source": "clinical", "evaluated_on_test": False}

        if mv_row:
            # Buscar eval run id
            eval_row = conn.execute(
                text("""
                    SELECT er.id, rcm.threshold_used, rcm.split_name, rcm.prediction_collapse
                    FROM run_lineage rl
                    JOIN runs er ON er.id = rl.child_run_id
                    LEFT JOIN run_clinical_metrics rcm ON rcm.run_id = er.id
                    WHERE rl.model_version_id = :mv_id AND er.run_type = 'evaluation' AND er.status = 'completed'
                    ORDER BY CASE WHEN rcm.split_name = 'test' THEN 0 ELSE 1 END, er.finished_at DESC LIMIT 1
                """),
                {"mv_id": model_version_id},
            ).mappings().one_or_none()

            if eval_row:
                eval_run_id = str(eval_row["id"])
                threshold_info["value"] = float(eval_row["threshold_used"]) if eval_row.get("threshold_used") is not None else 0.5
                threshold_info["evaluated_on_test"] = (eval_row.get("split_name") == "test")
                collapse = eval_row.get("prediction_collapse") or {}
                if isinstance(collapse, str):
                    try:
                        collapse = json.loads(collapse)
                    except Exception:
                        collapse = {}
                if collapse.get("collapsed"):
                    blocking_reasons.append("EVALUATION_COLLAPSED: Se detectó colapso de predicciones en la evaluación del modelo.")

            # Buscar explainability runs
            ex_rows = conn.execute(
                text("""
                    SELECT DISTINCT er.id
                    FROM run_lineage rl
                    JOIN runs er ON er.id = rl.child_run_id
                    WHERE rl.model_version_id = :mv_id AND er.run_type = 'explainability' AND er.status = 'completed'
                """),
                {"mv_id": model_version_id},
            ).mappings().all()
            explain_run_ids = [str(r["id"]) for r in ex_rows]

        # 5. Deployment existente
        dep_row = None
        if model_version_id:
            dep_row = conn.execute(
                text("""
                    SELECT * FROM deployed_model_versions
                    WHERE model_version_id = :mv_id
                    ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END, created_at DESC LIMIT 1
                """),
                {"mv_id": model_version_id},
            ).mappings().one_or_none()

        dep_id = str(dep_row["id"]) if dep_row else None
        dep_status = dep_row["status"] if dep_row else None
        dep_env = dep_row["environment"] if dep_row else None
        dep_alias = dep_row["alias"] if dep_row else None

        # 6. Preprocessing & Class Mapping Validation
        class_mapping = mv_row.get("class_mapping") if mv_row else EXPECTED_CLASS_MAPPING
        if isinstance(class_mapping, str):
            try:
                class_mapping = json.loads(class_mapping)
            except Exception:
                class_mapping = {}

        pos_label = class_mapping.get("positive_label") or class_mapping.get("1")
        if pos_label != "parasitized":
            blocking_reasons.append("CLASS_MAPPING_INVALID: La etiqueta positiva debe ser 'parasitized'.")

        # 7. Calcular can_release y can_deploy
        has_critical_blocker = any(
            r.startswith(("TRAINING_RUN_NOT_FOUND", "INVALID_RUN_TYPE", "TRAINING_NOT_COMPLETED", "CHECKPOINT_NOT_FOUND", "CHECKPOINT_HASH_MISMATCH", "UNRESOLVED_LINEAGE"))
            for r in blocking_reasons
        )
        can_release = not has_critical_blocker

        can_deploy = False
        if can_release and model_version_id and mv_status in (ModelVersionStatus.APPROVED.value, ModelVersionStatus.VALIDATED.value):
            if not eval_run_id:
                blocking_reasons.append("EVALUATION_REQUIRED: El modelo requiere una evaluación formal antes del despliegue.")
            elif not threshold_info["evaluated_on_test"]:
                blocking_reasons.append("CLINICAL_THRESHOLD_REQUIRED: El umbral diagnóstico debe estar evaluado en el conjunto de test.")
            else:
                can_deploy = True

        # 8. Determinación de next_action & button
        if has_critical_blocker or mv_status == ModelVersionStatus.REJECTED.value:
            next_action = "unavailable"
            button_label = "No disponible"
            button_enabled = False
            target_url = None
        elif not model_version_id:
            next_action = "prepare_release"
            button_label = "Preparar despliegue"
            button_enabled = True
            target_url = None
        elif mv_status in (ModelVersionStatus.DISCOVERED.value, ModelVersionStatus.CANDIDATE.value, ModelVersionStatus.VALIDATED.value):
            next_action = "review_model_version"
            button_label = "Ver modelo liberado"
            button_enabled = True
            target_url = f"/modelo-ia/modelos-liberados/{model_version_id}"
        elif mv_status == ModelVersionStatus.VALIDATED.value:
            next_action = "approve_model_version"
            button_label = "Aprobar modelo"
            button_enabled = True
            target_url = f"/modelo-ia/modelos-liberados/{model_version_id}"
        elif mv_status == ModelVersionStatus.APPROVED.value and not dep_id:
            next_action = "create_deployment"
            button_label = "Continuar despliegue"
            button_enabled = True
            target_url = f"/modelo-ia/modelos-liberados/{model_version_id}?action=deploy"
        elif dep_status in ("pending", "inactive"):
            next_action = "review_pending_deployment"
            button_label = "Ver despliegue pendiente"
            button_enabled = True
            target_url = f"/modelo-ia/despliegues/{dep_id}"
        elif dep_status == "active":
            next_action = "view_active_deployment"
            button_label = "Ver despliegue"
            button_enabled = True
            target_url = f"/modelo-ia/despliegues/{dep_id}"
        else:
            next_action = "unavailable"
            button_label = "No disponible"
            button_enabled = False
            target_url = None

        return {
            "training_run_id": run_id,
            "model_version_id": model_version_id,
            "deployment_id": dep_id,
            "deployment_status": dep_status,
            "environment": dep_env,
            "alias": dep_alias,
            "next_action": next_action,
            "button_label": button_label,
            "button_enabled": button_enabled,
            "blocking_reasons": list(set(blocking_reasons)),
            "target_url": target_url,
            "can_release": can_release,
            "can_deploy": can_deploy,
            "_run_info": {
                "run_id": run_id,
                "model_name": model_name,
                "checkpoint_path": checkpoint_path_str,
                "checkpoint_artifact_id": checkpoint_artifact_id,
                "artifact_sha256": artifact_sha256,
            },
            "_training_status": run_status,
            "_model_name": model_name,
            "_model_version_status": mv_status,
            "_lineage_status": mv_lineage_status,
            "_evaluation_run_id": eval_run_id,
            "_explainability_run_ids": explain_run_ids,
            "_checkpoint_sha256": artifact_sha256,
            "_threshold": threshold_info,
        }

    def _create_model_version_record(self, conn, run_info: dict, requester: str) -> str:
        from src.model_governance.repository import create_model_version
        from uuid import uuid4

        row_ver = conn.execute(
            text("SELECT COALESCE(MAX(version_number), 0) + 1 FROM model_versions WHERE model_name = :mname"),
            {"mname": run_info["model_name"]},
        ).scalar()
        ver_num = int(row_ver or 1)

        art_row = conn.execute(
            text("""
                SELECT a.id, a.path, a.checksum AS sha256_hash, a.file_size_bytes
                FROM artifacts a
                WHERE a.run_id = :run_id AND (a.artifact_type IN ('checkpoint', 'model', 'keras_model') OR a.path LIKE '%.keras' OR a.path LIKE '%.h5')
                ORDER BY a.created_at DESC LIMIT 1
            """),
            {"run_id": run_info["run_id"]},
        ).mappings().one_or_none()

        if not art_row:
            art_id = uuid4()
            path_str = run_info.get("checkpoint_path") or f"outputs/{run_info['model_name']}/best_model.keras"
            sha_str = run_info.get("artifact_sha256") or ("0" * 64)
            size_int = 1024 * 1024
            conn.execute(
                text("""
                    INSERT INTO artifacts (id, run_id, artifact_type, name, path, checksum, file_size_bytes)
                    VALUES (:id, :run_id, 'checkpoint', 'best_model.keras', :path, :checksum, :file_size_bytes)
                """),
                {
                    "id": art_id,
                    "run_id": run_info["run_id"],
                    "path": path_str,
                    "checksum": sha_str.lower(),
                    "file_size_bytes": size_int,
                },
            )
            artifact_id = art_id
            art_path = path_str
            art_sha = sha_str.lower()
            art_size = size_int
        else:
            artifact_id = art_row["id"]
            art_path = art_row["path"]
            art_sha = (art_row["sha256_hash"] or "0" * 64).lower()
            art_size = art_row["file_size_bytes"] or (1024 * 1024)

        mv = create_model_version(
            training_run_id=run_info["run_id"],
            model_name=run_info["model_name"],
            version_number=ver_num,
            checkpoint_artifact_id=artifact_id,
            artifact_path=art_path,
            artifact_sha256=art_sha,
            artifact_size_bytes=art_size,
            framework="keras",
            framework_version="2.15.0",
            preprocessing_profile_snapshot={
                "target_size": [200, 200],
                "color_mode": "rgb",
                "rescaling": "1/255.0",
            },
            class_mapping=EXPECTED_CLASS_MAPPING,
            input_signature={"shape": [None, 200, 200, 3], "dtype": "float32"},
            output_signature={"shape": [None, 1], "dtype": "float32"},
            status=ModelVersionStatus.APPROVED,
            connection_or_session=conn,
        )
        return str(mv.id)

    def _audit_event(
        self,
        conn,
        training_run_id: str,
        model_version_id: str | None,
        requester: str,
        action: str,
        result: str,
        blocking_reasons: list[str],
    ):
        try:
            conn.execute(
                text("""
                    INSERT INTO execution_logs (run_id, log_level, message, metadata)
                    VALUES (:run_id, 'INFO', :msg, :meta)
                """),
                {
                    "run_id": training_run_id,
                    "msg": f"[PROMOTION_AUDIT] Action: {action} | Result: {result} | User: {requester}",
                    "meta": json.dumps({
                        "event": "model_promotion_audit",
                        "action": action,
                        "result": result,
                        "requester": requester,
                        "training_run_id": training_run_id,
                        "model_version_id": model_version_id,
                        "blocking_reasons": blocking_reasons,
                        "timestamp": datetime.now(UTC).isoformat(),
                    }),
                },
            )
        except Exception as exc:
            logger.warning(f"No se pudo registrar log de auditoría en execution_logs: {exc}")
