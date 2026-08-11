from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import Request
from PIL import Image
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.audit import record_event
from app.db import get_primary_engine
from app.security import Principal
from app.services.artifacts import (
    CAPSTONE_ROOT,
    MALARIA_PROJECT_ROOT,
    resolve_artifact_path,
    resolve_artifact_reference,
)
from app.services.cell_explanation_storage import CellExplanationStorage
from app.services.explainability import enrich_explainability_case
from app.services.local_storage import LocalStorage
from app.services.productive_model import sha256_file


METHOD_VERSION = "gradcam-on-demand-v1"
_locks_guard = threading.Lock()
_prediction_locks: dict[str, threading.Lock] = {}


class CaseGradCamError(ValueError):
    def __init__(self, status_code: int, detail: str, code: str):
        self.status_code = status_code
        self.detail = detail
        self.code = code
        super().__init__(detail)


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return dict(parsed) if isinstance(parsed, Mapping) else {}
    return {}


def _prediction_lock(prediction_id: str) -> threading.Lock:
    with _locks_guard:
        return _prediction_locks.setdefault(prediction_id, threading.Lock())


class CaseGradCamService:
    """Synchronous, single-case Grad-CAM orchestration for governed model runs."""

    def __init__(
        self,
        engine: Engine | None = None,
        *,
        storage_factory: Callable[[], LocalStorage] = LocalStorage,
        model_loader: Callable[[Path], Any] | None = None,
        gradcam: Callable[..., Any] | None = None,
    ):
        self.engine = engine or get_primary_engine()
        self.storage_factory = storage_factory
        self.model_loader = model_loader
        self.gradcam = gradcam

    def _target(self, source_explanation_id: str) -> dict[str, Any]:
        with self.engine.connect() as connection:
            row = connection.execute(
                text("""
                    SELECT * FROM vw_visual_explainability_audit
                    WHERE explainability_id=CAST(:id AS uuid)
                """),
                {"id": source_explanation_id},
            ).mappings().one_or_none()
        if not row or not row.get("prediction_id"):
            raise CaseGradCamError(404, "Caso explicable inexistente.", "NOT_FOUND")
        target = dict(row)
        target["run_parameters"] = _mapping(target.get("run_parameters"))
        target["run_metadata"] = _mapping(target.get("run_metadata"))
        return target

    def _existing(self, target: Mapping[str, Any]) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text("""
                    SELECT * FROM vw_visual_explainability_audit
                    WHERE prediction_id=CAST(:prediction_id AS uuid)
                      AND run_id=CAST(:run_id AS uuid)
                      AND lower(replace(replace(method, '-', ''), '_', ''))='gradcam'
                      AND success IS TRUE
                    ORDER BY created_at DESC
                """),
                {"prediction_id": str(target["prediction_id"]), "run_id": str(target["run_id"])},
            ).mappings().all()
        for row in rows:
            path = row.get("explanation_output_path")
            if not path:
                continue
            try:
                resolve_artifact_reference(path=str(path))
            except Exception:
                continue
            return enrich_explainability_case(row)
        return None

    def _resolve_model(self, target: Mapping[str, Any]) -> tuple[Path, str, dict[str, Any]]:
        parameters = target["run_parameters"]
        metadata = target["run_metadata"]
        model_version_id = parameters.get("model_version_id") or metadata.get("model_version_id")
        if not model_version_id:
            raise CaseGradCamError(409, "El caso no conserva model version original.", "MODEL_VERSION_MISSING")
        with self.engine.connect() as connection:
            row = connection.execute(
                text("""
                    SELECT id::text, model_name, checkpoint_path, artifact_sha256,
                           preprocessing_profile_snapshot, class_mapping, input_signature,
                           status, lineage_status
                    FROM model_versions WHERE id=CAST(:id AS uuid)
                """), {"id": str(model_version_id)},
            ).mappings().one_or_none()
        if not row or row["status"] in {"rejected", "retired"} or row["lineage_status"] != "resolved":
            raise CaseGradCamError(409, "La model version histórica no está disponible.", "MODEL_VERSION_UNAVAILABLE")
        try:
            checkpoint = resolve_artifact_path(str(row["checkpoint_path"]))
        except Exception as exc:
            raise CaseGradCamError(
                409,
                "El checkpoint histórico no supera integridad.",
                "CHECKPOINT_UNAVAILABLE",
            ) from exc
        if not checkpoint.is_file() or sha256_file(checkpoint) != str(row["artifact_sha256"]):
            raise CaseGradCamError(409, "El checkpoint histórico no supera integridad.", "CHECKPOINT_UNAVAILABLE")
        snapshot = {
            "model_version_id": str(row["id"]),
            "model_name": row["model_name"],
            "preprocessing": _mapping(row["preprocessing_profile_snapshot"]),
            "class_mapping": _mapping(row["class_mapping"]),
            "input_signature": _mapping(row["input_signature"]),
            "checkpoint_sha256": str(row["artifact_sha256"]),
        }
        return checkpoint, str(model_version_id), snapshot

    @staticmethod
    def _input(target: Mapping[str, Any]) -> tuple[Path, str]:
        path = target.get("crop_path") or target.get("image_path") or target.get("source_image_path")
        if not path:
            raise CaseGradCamError(409, "El input histórico no está registrado.", "INPUT_MISSING")
        artifact = resolve_artifact_reference(path=str(path))
        return artifact.path, sha256_file(artifact.path)

    def _runtime(self):
        root = MALARIA_PROJECT_ROOT
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from src.malaria_dl.data.preprocessing import preprocess_numpy_image
        from src.malaria_dl.explainability.gradcam import compute_gradcam_artifacts
        if self.model_loader is None:
            import tensorflow as tf
            loader = lambda path: tf.keras.models.load_model(path, compile=False)
        else:
            loader = self.model_loader
        return loader, preprocess_numpy_image, self.gradcam or compute_gradcam_artifacts

    def _persist_png(self, prediction_id: str, explanation_id: UUID, payload: bytes) -> tuple[str, str, int]:
        storage = self.storage_factory()
        key = f"model-explanations/{prediction_id}/{explanation_id}/gradcam_overlay.png"
        staged = storage.staging / f"{explanation_id}.gradcam.png"
        try:
            with staged.open("xb") as output:
                os.chmod(staged, 0o600)
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            storage.promote(staged, key)
        except Exception:
            staged.unlink(missing_ok=True)
            raise
        return f"var/storage/{key}", hashlib.sha256(payload).hexdigest(), len(payload)

    def generate(self, source_explanation_id: str, principal: Principal, request: Request) -> dict[str, Any]:
        target = self._target(source_explanation_id)
        prediction_id = str(target["prediction_id"])
        with _prediction_lock(prediction_id):
            existing = self._existing(target)
            if existing:
                record_event(event_type="scientific.case_gradcam.reused", action="reuse", principal=principal,
                             request=request, success=True, resource_type="prediction", resource_id=prediction_id,
                             after_state={"explainability_id": str(existing["explainability_id"]), "method": "gradcam"})
                return existing
            checkpoint, model_version_id, model_snapshot = self._resolve_model(target)
            input_path, input_sha256 = self._input(target)
            parameters = target["run_parameters"]
            preprocessing = model_snapshot["preprocessing"].get("mode") or parameters.get("preprocessing_mode") or parameters.get("preprocessing")
            img_size = parameters.get("img_size") or model_snapshot["input_signature"].get("width")
            if not preprocessing or not img_size:
                raise CaseGradCamError(409, "El preprocessing histórico está incompleto.", "PREPROCESSING_MISSING")
            predicted_label = str(target["predicted_label"])
            mapping = model_snapshot["class_mapping"] or _mapping(parameters.get("class_mapping"))
            predicted_index = next((int(key) for key, value in mapping.items() if str(key).isdigit() and value == predicted_label), None)
            if predicted_index is None:
                raise CaseGradCamError(409, "No se pudo resolver la clase predicha histórica.", "CLASS_MAPPING_MISSING")
            explanation_id = uuid4()
            promoted_path: Path | None = None
            try:
                loader, preprocess, gradcam = self._runtime()
                model = loader(checkpoint)
                with Image.open(input_path) as image:
                    model_image = preprocess(image.convert("RGB"), int(img_size), preprocessing)
                _, overlay, layer = gradcam(
                    model=model, image=model_image, pred_idx=predicted_index,
                    invert_scalar_output=predicted_index == 0, preprocessing_mode=preprocessing,
                )
                png = CellExplanationStorage.encode_overlay_png(overlay)
                output_path, checksum, size = self._persist_png(prediction_id, explanation_id, png)
                promoted_path = CAPSTONE_ROOT / output_path
                explanation_parameters = {
                    "method": "gradcam", "method_version": METHOD_VERSION,
                    "execution_mode": "on_demand", "model_version_id": model_version_id,
                    "checkpoint_sha256": model_snapshot["checkpoint_sha256"],
                    "input_sha256": input_sha256, "preprocessing": preprocessing,
                    "img_size": int(img_size), "target_class_index": predicted_index,
                }
                with self.engine.begin() as connection:
                    connection.execute(text("""
                        INSERT INTO explainability_results(
                          id,run_id,prediction_id,method,image_path,output_path,true_label,
                          predicted_label,score,case_type,last_conv_layer,explanation_parameters,
                          success,error_message,metadata
                        ) VALUES(
                          :id,CAST(:run_id AS uuid),CAST(:prediction_id AS uuid),'gradcam',:image_path,
                          :output_path,:true_label,:predicted_label,:score,:case_type,:layer,
                          CAST(:parameters AS jsonb),TRUE,NULL,CAST(:metadata AS jsonb)
                        )
                    """), {
                        "id": explanation_id, "run_id": str(target["run_id"]), "prediction_id": prediction_id,
                        "image_path": str(input_path), "output_path": output_path, "true_label": target.get("true_label"),
                        "predicted_label": predicted_label, "score": target.get("score_positive_label"),
                        "case_type": target.get("case_type"), "layer": layer,
                        "parameters": json.dumps(explanation_parameters),
                        "metadata": json.dumps({"created_by": principal.user_id, "input_sha256": input_sha256}),
                    })
                    artifact_id = uuid4()
                    connection.execute(text("""
                        INSERT INTO artifacts(id,run_id,artifact_type,name,path,mime_type,file_size_bytes,
                          checksum,metadata,artifact_status)
                        VALUES(:id,CAST(:run_id AS uuid),'gradcam_image','Grad-CAM on-demand',:path,
                          'image/png',:size,:checksum,CAST(:metadata AS jsonb),'available')
                    """), {"id": artifact_id, "run_id": str(target["run_id"]), "path": output_path,
                           "size": size, "checksum": checksum,
                           "metadata": json.dumps({"explainability_result_id": str(explanation_id), "prediction_id": prediction_id,
                                                   "model_version_id": model_version_id, "input_sha256": input_sha256,
                                                   "created_by": principal.user_id})})
                    record_event(event_type="scientific.case_gradcam.generated", action="explain", principal=principal,
                                 request=request, success=True, connection=connection, resource_type="prediction",
                                 resource_id=prediction_id, after_state={"explainability_id": str(explanation_id),
                                 "artifact_id": str(artifact_id), "method": "gradcam", "model_version_id": model_version_id,
                                 "input_sha256": input_sha256, "last_conv_layer": layer})
                with self.engine.connect() as connection:
                    result = connection.execute(text("SELECT * FROM vw_visual_explainability_audit WHERE explainability_id=:id"),
                                                {"id": explanation_id}).mappings().one()
                return enrich_explainability_case(result)
            except CaseGradCamError:
                raise
            except Exception as exc:
                if promoted_path is not None:
                    promoted_path.unlink(missing_ok=True)
                with self.engine.begin() as connection:
                    connection.execute(text("""
                        INSERT INTO explainability_results(
                          id,run_id,prediction_id,method,image_path,true_label,predicted_label,
                          score,case_type,explanation_parameters,success,error_message,metadata
                        ) VALUES(
                          :id,CAST(:run_id AS uuid),CAST(:prediction_id AS uuid),'gradcam',:image_path,
                          :true_label,:predicted_label,:score,:case_type,CAST(:parameters AS jsonb),FALSE,
                          'No fue posible generar Grad-CAM para este caso.',CAST(:metadata AS jsonb)
                        )
                    """), {
                        "id": explanation_id, "run_id": str(target["run_id"]), "prediction_id": prediction_id,
                        "image_path": str(input_path), "true_label": target.get("true_label"),
                        "predicted_label": predicted_label, "score": target.get("score_positive_label"),
                        "case_type": target.get("case_type"),
                        "parameters": json.dumps({"method": "gradcam", "method_version": METHOD_VERSION,
                                                  "execution_mode": "on_demand", "model_version_id": model_version_id,
                                                  "input_sha256": input_sha256, "preprocessing": preprocessing}),
                        "metadata": json.dumps({"created_by": principal.user_id, "failure_type": type(exc).__name__}),
                    })
                    record_event(event_type="scientific.case_gradcam.failed", action="explain", principal=principal,
                                 request=request, success=False, error_code="GRADCAM_GENERATION_FAILED",
                                 connection=connection, resource_type="prediction", resource_id=prediction_id,
                                 after_state={"explainability_id": str(explanation_id), "method": "gradcam",
                                              "model_version_id": model_version_id})
                with self.engine.connect() as connection:
                    failed = connection.execute(text("SELECT * FROM vw_visual_explainability_audit WHERE explainability_id=:id"),
                                                {"id": explanation_id}).mappings().one()
                return enrich_explainability_case(failed)
