"""Evidence-backed completion and workflow readiness for governed model versions."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text

from src.model_deployment_service import EXPECTED_MAPPING, ModelDeploymentService, _project_path
from src.model_governance.errors import (
    GovernanceNotFoundError,
    GovernanceStateError,
)
from src.model_governance.releases import sha256_file


CONTRACT_FIELDS = (
    "preprocessing_profile_snapshot",
    "class_mapping",
    "input_signature",
    "output_signature",
)


class ModelContractService:
    """Completes only mutable discovered versions; governed payload stays immutable afterwards."""

    def __init__(self, connection_factory, model_loader=None):
        self.connection_factory = connection_factory
        self.model_loader = model_loader or ModelDeploymentService._keras_loader

    @staticmethod
    def _id(value: Any) -> str:
        return str(UUID(str(value)))

    @staticmethod
    def _object(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    @staticmethod
    def _mapping(raw: Any) -> dict[str, Any]:
        mapping = dict(raw) if isinstance(raw, dict) else {}
        if (
            mapping.get("negative_class_index") == 0
            and mapping.get("negative_class_name") == "uninfected"
            and mapping.get("positive_class_index") == 1
            and mapping.get("positive_class_name") == "parasitized"
        ):
            mapping.update(
                {
                    "0": "uninfected",
                    "1": "parasitized",
                    "positive_class": 1,
                    "positive_label": "parasitized",
                }
            )
        return mapping

    def _load(self, model_version_id: str):
        with self.connection_factory() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT mv.*, a.path AS artifact_path, a.checksum AS artifact_checksum,
                           a.file_size_bytes AS artifact_file_size, a.artifact_status,
                           r.parameters, r.execution_parameters, r.configuration,
                           r.metadata AS run_metadata
                    FROM model_versions mv
                    JOIN artifacts a ON a.id=mv.checkpoint_artifact_id
                    JOIN runs r ON r.id=mv.training_run_id
                    WHERE mv.id=CAST(:id AS uuid)
                    """
                ),
                {"id": model_version_id},
            ).mappings().one_or_none()
        if not row:
            raise GovernanceNotFoundError("model version inexistente")
        return dict(row)

    @staticmethod
    def _public_version(row: dict[str, Any]) -> dict[str, Any]:
        hidden = {"checkpoint_path", "final_model_path", "best_model_path", "artifact_path"}
        return {key: value for key, value in row.items() if key not in hidden}

    def _artifact_signatures(self, row: dict[str, Any]) -> tuple[dict, dict, str | None]:
        path = _project_path(row["artifact_path"]).resolve()
        if not path.is_file():
            return {}, {}, "El artifact registrado no está disponible."
        if sha256_file(path) != str(row.get("artifact_sha256") or "").lower():
            return {}, {}, "El SHA-256 del artifact no coincide."
        try:
            model = self.model_loader(path)
            inputs = getattr(model, "inputs", None) or []
            outputs = getattr(model, "outputs", None) or []

            def signature(tensors):
                if not tensors:
                    return {}
                tensor = tensors[0]
                shape = [int(item) if item is not None else None for item in tensor.shape]
                return {"shape": shape, "dtype": str(getattr(tensor, "dtype", "float32"))}

            return signature(inputs), signature(outputs), None
        except ModuleNotFoundError as exc:
            return {}, {}, (
                "El runtime de la API no puede cargar modelos Keras porque falta "
                f"la dependencia {exc.name or 'requerida'}. Reinicie la API con "
                "el entorno ML Python 3.12 del proyecto."
            )
        except Exception as exc:
            return {}, {}, f"No fue posible inspeccionar el artifact: {type(exc).__name__}."

    @staticmethod
    def _field(key, label, current, candidates, searched):
        unique = []
        seen = set()
        for candidate in candidates:
            marker = json.dumps(candidate["value"], sort_keys=True, default=str)
            if marker not in seen:
                unique.append(candidate)
                seen.add(marker)
        proposed = unique[0] if len(unique) == 1 else None
        return {
            "key": key,
            "label": label,
            "current_value": current or None,
            "candidates": unique,
            "proposed_value": proposed["value"] if proposed else None,
            "proposed_source_id": proposed["source_id"] if proposed else None,
            "status": "complete" if current else ("ready" if proposed else ("ambiguous" if unique else "blocked")),
            "sources_searched": searched,
        }

    def candidates(self, model_version_id: str) -> dict[str, Any]:
        model_version_id = self._id(model_version_id)
        row = self._load(model_version_id)
        parameters = self._object(row.get("parameters"))
        execution = self._object(row.get("execution_parameters"))
        metadata = self._object(row.get("run_metadata"))
        model_metadata = self._object(metadata.get("model_metadata"))
        searched = ["training metadata", "execution parameters", "governed artifact"]

        preprocessing = (
            model_metadata.get("preprocessing")
            or metadata.get("preprocessing")
            or execution.get("preprocessing")
            or execution.get("preprocessing_mode")
            or parameters.get("preprocessing_mode")
            or parameters.get("preprocessing")
        )
        preprocessing_value = (
            {"mode": preprocessing} if isinstance(preprocessing, str) and preprocessing else {}
        )
        mapping = self._mapping(
            model_metadata.get("class_mapping")
            or metadata.get("label_mapping")
            or parameters.get("label_mapping")
        )
        artifact_input, artifact_output, artifact_error = self._artifact_signatures(row)
        fields = [
            self._field(
                "preprocessing_profile_snapshot",
                "Preprocesamiento",
                row.get("preprocessing_profile_snapshot"),
                [{"source_id": "training_metadata", "source": "training metadata", "value": preprocessing_value}] if preprocessing_value else [],
                searched,
            ),
            self._field(
                "class_mapping",
                "Convención de clases",
                row.get("class_mapping"),
                [{"source_id": "training_metadata", "source": "training metadata", "value": mapping}] if mapping else [],
                searched,
            ),
            self._field(
                "input_signature",
                "Firma de entrada",
                row.get("input_signature"),
                [{"source_id": "artifact_inspection", "source": "artifact verificado", "value": artifact_input}] if artifact_input else [],
                searched,
            ),
            self._field(
                "output_signature",
                "Firma de salida",
                row.get("output_signature"),
                [{"source_id": "artifact_inspection", "source": "artifact verificado", "value": artifact_output}] if artifact_output else [],
                searched,
            ),
        ]
        with self.connection_factory() as connection:
            evaluations = connection.execute(
                text(
                    """
                    SELECT child.id::text id
                    FROM run_lineage rl JOIN runs child ON child.id=rl.child_run_id
                    WHERE rl.parent_run_id=CAST(:training AS uuid)
                      AND rl.model_version_id=CAST(:mv AS uuid)
                      AND rl.relationship_type='evaluates_checkpoint_from'
                      AND child.run_type='evaluation' AND child.status='completed'
                    ORDER BY child.finished_at DESC NULLS LAST
                    """
                ),
                {"mv": model_version_id, "training": str(row["training_run_id"])},
            ).scalars().all()
            thresholds = connection.execute(
                text(
                    """
                    SELECT run_threshold_calibration_id::text id, threshold_selected,
                           threshold_source, calibration_split, calibration_status,
                           positive_label, score_name
                    FROM run_threshold_calibration
                    WHERE (model_version_id=:mv OR model_version_id IS NULL)
                      AND (
                        run_id=CAST(:training AS uuid)
                        OR run_id IN (
                          SELECT child_run_id FROM run_lineage
                          WHERE parent_run_id=CAST(:training AS uuid)
                            AND relationship_type='evaluates_checkpoint_from'
                        )
                      )
                      AND calibration_status IN ('recorded','validated')
                      AND positive_label='parasitized'
                      AND score_name='probability_parasitized'
                    ORDER BY created_at DESC
                    """
                ),
                {"mv": model_version_id, "training": str(row["training_run_id"])},
            ).mappings().all()
        threshold_candidates = [
            {
                "source_id": str(item["id"]),
                "source": "threshold calibration",
                "value": {
                    "threshold_profile_id": str(item["id"]),
                    "threshold": float(item["threshold_selected"]),
                    "score_name": item["score_name"],
                    "positive_label": item["positive_label"],
                },
            }
            for item in thresholds
        ]
        threshold = self._field(
            "threshold_profile_id",
            "Threshold clínico versionado",
            threshold_candidates[0]["value"] if len(threshold_candidates) == 1 and row["status"] != "discovered" else None,
            threshold_candidates,
            ["training threshold calibration", "linked evaluation threshold calibration"],
        )
        fields.append(threshold)
        complete = all(item["status"] == "complete" for item in fields[:4]) and bool(threshold_candidates)
        return {
            "model_version_id": model_version_id,
            "training_run_id": str(row["training_run_id"]),
            "model_name": row["model_name"],
            "version_number": row["version_number"],
            "status": row["status"],
            "lineage_status": row["lineage_status"],
            "fields": fields,
            "contract_complete": complete,
            "can_complete_contract": row["status"] == "discovered" and all(
                item["status"] in {"complete", "ready"} for item in fields
            ),
            "artifact_inspection_error": artifact_error,
            "immutable_reason": (
                None
                if row["status"] == "discovered"
                else "El contrato de una model_version gobernada es inmutable; prepare una nueva versión si requiere corrección."
            ),
            "production_package": {
                "artifact_id": str(row["checkpoint_artifact_id"]),
                "artifact_sha256": row["artifact_sha256"],
                "artifact_size_bytes": row["artifact_size_bytes"],
                "artifact_status": row["artifact_status"],
                "artifact_immutable": bool(
                    row.get("artifact_uri")
                    or f"/runs/{row['training_run_id']}/" in str(row["artifact_path"]).replace("\\", "/")
                ),
                "training_run_id": str(row["training_run_id"]),
                "evaluation_run_ids": [str(item) for item in evaluations],
                "framework": row["framework"],
                "framework_version": row["framework_version"],
                "manifest_registered": bool(
                    self._object(row.get("metadata")).get("production_manifest")
                ),
            },
        }

    def complete(self, model_version_id: str, selections: dict[str, str], actor: str, reason: str):
        if not actor or not reason:
            raise GovernanceStateError("completar contrato exige actor y motivo")
        preview = self.candidates(model_version_id)
        if preview["contract_complete"] and preview["status"] in {
            "candidate", "validated", "approved", "deployed"
        }:
            threshold = next(
                item for item in preview["fields"] if item["key"] == "threshold_profile_id"
            )
            row = self._load(self._id(model_version_id))
            return {
                "model_version": self._public_version(row),
                "threshold_profile_id": (
                    threshold["current_value"]["threshold_profile_id"]
                    if threshold.get("current_value") else None
                ),
                "idempotent": True,
            }
        if preview["status"] != "discovered":
            raise GovernanceStateError(preview["immutable_reason"])
        values = {}
        for field in preview["fields"]:
            if field["key"] in CONTRACT_FIELDS:
                if field["status"] == "complete":
                    values[field["key"]] = field["current_value"]
                    continue
                source_id = selections.get(field["key"]) or field.get("proposed_source_id")
                matches = [item for item in field["candidates"] if item["source_id"] == source_id]
                if len(matches) != 1:
                    raise GovernanceStateError(f"selección inequívoca requerida para {field['label']}")
                values[field["key"]] = matches[0]["value"]
        mapping = self._mapping(values["class_mapping"])
        if any(mapping.get(key) != value for key, value in EXPECTED_MAPPING.items()):
            raise GovernanceStateError("class_mapping clínico inválido")
        if mapping.get("positive_class") != 1 or mapping.get("positive_label") != "parasitized":
            raise GovernanceStateError("clase positiva clínica inválida")
        threshold_field = next(item for item in preview["fields"] if item["key"] == "threshold_profile_id")
        threshold_id = selections.get("threshold_profile_id") or threshold_field.get("proposed_source_id")
        if not any(item["source_id"] == threshold_id for item in threshold_field["candidates"]):
            raise GovernanceStateError("selección inequívoca de threshold profile requerida")
        audit = {
            "last_audit_event": "technical_contract_completed",
            "actor": actor,
            "reason": reason,
            "at": datetime.now(UTC).isoformat(),
            "sources": selections,
        }
        package = preview["production_package"]
        if not package["artifact_immutable"]:
            raise GovernanceStateError(
                "el artifact no es inmutable; prepare una copia gobernada desde el training run"
            )
        manifest = {
            "schema_version": 1,
            "model_version_id": model_version_id,
            "training_run_id": preview["training_run_id"],
            "checkpoint_artifact_id": package["artifact_id"],
            "artifact_sha256": package["artifact_sha256"],
            "artifact_size_bytes": package["artifact_size_bytes"],
            "framework": package["framework"],
            "framework_version": package["framework_version"],
            "class_mapping": mapping,
            "preprocessing_profile_snapshot": values["preprocessing_profile_snapshot"],
            "input_signature": values["input_signature"],
            "output_signature": values["output_signature"],
            "threshold_profile_id": threshold_id,
            "evaluation_run_ids": package["evaluation_run_ids"],
            "created_at": datetime.now(UTC).isoformat(),
        }
        audit["production_manifest"] = manifest
        with self.connection_factory() as connection:
            connection.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                {"key": f"complete-contract:{model_version_id}"},
            )
            row = connection.execute(
                text(
                    """
                    UPDATE model_versions SET
                      preprocessing_profile_snapshot=CAST(:preprocessing AS jsonb),
                      class_mapping=CAST(:mapping AS jsonb),
                      input_signature=CAST(:input AS jsonb),
                      output_signature=CAST(:output AS jsonb),
                      metadata=metadata||CAST(:audit AS jsonb)
                    WHERE id=CAST(:id AS uuid) AND status='discovered'
                    RETURNING *
                    """
                ),
                {
                    "id": model_version_id,
                    "preprocessing": json.dumps(values["preprocessing_profile_snapshot"]),
                    "mapping": json.dumps(mapping),
                    "input": json.dumps(values["input_signature"]),
                    "output": json.dumps(values["output_signature"]),
                    "audit": json.dumps(audit),
                },
            ).mappings().one_or_none()
            if not row:
                raise GovernanceStateError("el contrato ya no es mutable")
            attached = connection.execute(
                text(
                    """
                    UPDATE run_threshold_calibration
                    SET model_version_id=CAST(:mv AS uuid)
                    WHERE run_threshold_calibration_id=CAST(:threshold AS uuid)
                      AND (model_version_id IS NULL OR model_version_id=CAST(:mv AS uuid))
                    RETURNING run_threshold_calibration_id
                    """
                ),
                {"mv": model_version_id, "threshold": threshold_id},
            ).scalar_one_or_none()
            if not attached:
                raise GovernanceStateError("threshold profile no pertenece al linaje del modelo")
            connection.execute(
                text(
                    """
                    UPDATE artifacts SET artifact_status='available',
                      metadata=metadata||CAST(:audit AS jsonb)
                    WHERE id=CAST(:artifact AS uuid)
                    """
                ),
                {
                    "artifact": package["artifact_id"],
                    "audit": json.dumps({
                        "last_integrity_verification": manifest["created_at"],
                        "verified_sha256": package["artifact_sha256"],
                        "verified_for_model_version_id": model_version_id,
                    }),
                },
            )
            row = connection.execute(
                text(
                    """
                    UPDATE model_versions SET status='candidate'
                    WHERE id=CAST(:id AS uuid) AND status='discovered'
                    RETURNING *
                    """
                ),
                {"id": model_version_id},
            ).mappings().one()
        return {
            "model_version": self._public_version(dict(row)),
            "threshold_profile_id": str(attached),
            "manifest": manifest,
        }

    def readiness(self, model_version_id: str) -> dict[str, Any]:
        preview = self.candidates(model_version_id)
        row = self._load(self._id(model_version_id))
        with self.connection_factory() as connection:
            deployment = connection.execute(
                text(
                    """
                    SELECT * FROM deployed_model_versions
                    WHERE model_version_id=CAST(:id AS uuid)
                    ORDER BY
                      CASE WHEN environment='production' AND status='active' THEN 0
                           WHEN environment='production' AND status='pending' THEN 1
                           ELSE 2 END,
                      created_at DESC LIMIT 1
                    """
                ),
                {"id": model_version_id},
            ).mappings().one_or_none()
            compatible_threshold_count = connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM run_threshold_calibration
                    WHERE model_version_id=CAST(:id AS uuid)
                      AND calibration_status IN ('recorded','validated')
                      AND positive_label='parasitized'
                      AND score_name='probability_parasitized'
                    """
                ),
                {"id": model_version_id},
            ).scalar_one()
        deployment_readiness = None
        if deployment:
            deployment_readiness = ModelDeploymentService(
                self.connection_factory, model_loader=self.model_loader
            ).readiness(str(deployment["id"]))
        status = row["status"]
        production_blockers = []
        if not preview["production_package"]["artifact_immutable"]:
            production_blockers.append(
                preview["artifact_inspection_error"]
                or "El artifact no tiene integridad inmutable verificada."
            )
        if not preview["contract_complete"]:
            production_blockers.append("El contrato técnico está incompleto.")
        if compatible_threshold_count != 1:
            production_blockers.append(
                "Falta un threshold profile formal asociado a esta model_version."
                if compatible_threshold_count == 0 else
                f"Hay {compatible_threshold_count} threshold profiles formales; debe existir exactamente uno."
            )
        can_publish = status in {"approved", "deployed"} and not production_blockers
        production_active = bool(
            deployment and deployment["environment"] == "production"
            and deployment["alias"] == "champion" and deployment["status"] == "active"
        )
        if not preview["contract_complete"]:
            step, action, label = 1, "build_production_model_version", "Completar versión productiva"
        elif status in {"discovered", "candidate"}:
            step, action, label = 2, "validate_model_version", "Validar versión"
        elif status == "validated":
            step, action, label = 3, "approve_model_version", "Aprobar versión"
        elif production_active:
            step, action, label = 4, "view_production_model", "Ver modelo productivo"
        elif can_publish:
            step, action, label = 4, "publish_to_production", "Publicar en producción"
        else:
            step, action, label = 4, "production_blocked", "Publicación bloqueada"
        return {
            "model_version_id": self._id(model_version_id),
            "deployment_id": str(deployment["id"]) if deployment else None,
            "current_step": step,
            "next_action": action,
            "action_label": label,
            "can_complete_contract": preview["can_complete_contract"],
            "can_validate": preview["contract_complete"] and status in {"discovered", "candidate"},
            "can_approve": status == "validated",
            "can_promote_to_production": can_publish,
            "can_build_package": preview["can_complete_contract"],
            "can_publish": can_publish,
            "is_active_in_production": production_active,
            "requirements": [
                {
                    "key": "immutable_artifact",
                    "status": "pass" if preview["production_package"]["artifact_immutable"] else "blocked",
                    "blocking": not preview["production_package"]["artifact_immutable"],
                    "action_key": "build_production_model_version",
                },
                {
                    "key": "technical_contract",
                    "status": "pass" if preview["contract_complete"] else "blocked",
                    "blocking": not preview["contract_complete"],
                    "action_key": "build_production_model_version",
                },
                {
                    "key": "formal_threshold",
                    "status": "pass" if compatible_threshold_count == 1 else "blocked",
                    "blocking": compatible_threshold_count != 1,
                    "action_key": "build_production_model_version",
                    "detail": (
                        "Existe un threshold profile formal compatible."
                        if compatible_threshold_count == 1 else production_blockers[-1]
                    ),
                },
            ],
            "production_blockers": production_blockers,
            "contract": preview,
            "deployment_readiness": deployment_readiness,
            "production_status": {
                "deployment_id": str(deployment["id"]) if deployment else None,
                "status": deployment["status"] if deployment else None,
                "environment": deployment["environment"] if deployment else None,
                "alias": deployment["alias"] if deployment else None,
                "smoke_status": (
                    self._object(deployment.get("metadata")).get("smoke_test", {}).get("status")
                    if deployment else None
                ),
                "available_for_inference": production_active,
            },
        }
