from __future__ import annotations

import hashlib
import json

from fastapi import Request

from app.audit import mutation_connection, record_event
from app.db import get_primary_engine
from app.repositories.scientific_validation import ScientificValidationRepository
from app.security import Principal
from app.services.scientific import ScientificError


TRANSITIONS = {
    "draft": {"draft", "annotation_in_progress"},
    "annotation_in_progress": {"annotation_in_progress", "ready_for_analysis"},
    "ready_for_analysis": {"ready_for_analysis", "annotation_in_progress", "completed"},
    "completed": {"completed"},
    "archived": set(),
}


def _actor(principal: Principal) -> str:
    if principal.insecure_local:
        raise ScientificError(403, "La validación científica requiere un usuario persistido.")
    return principal.user_id


def _state(row: dict) -> dict:
    return {
        "id": str(row["id"]), "name": row["name"], "status": row["status"],
        "snapshot_sha256": row["snapshot_sha256"],
    }


class ScientificValidationService:
    def __init__(self, engine=None):
        self.engine = engine

    @property
    def _engine(self):
        return self.engine or get_primary_engine()

    def create(self, values: dict, principal: Principal, request: Request) -> dict:
        actor_id = _actor(principal)
        image_ids = [str(value) for value in values.pop("image_ids")]
        detection_ids = [str(value) for value in values.pop("detection_run_ids")]
        classification_ids = [str(value) for value in values.pop("classification_run_ids")]
        with mutation_connection(self._engine) as connection:
            repository = ScientificValidationRepository(connection)
            images = repository.source_rows("microscopy_images", image_ids)
            detections = repository.source_rows("cell_detection_runs", detection_ids)
            classifications = repository.source_rows("cell_classification_runs", classification_ids)
            if len(images) != len(image_ids):
                raise ScientificError(404, "Una o más imágenes no existen.")
            if len(detections) != len(detection_ids) or len(classifications) != len(classification_ids):
                raise ScientificError(404, "Uno o más runs no existen.")
            if any(row["status"] == "archived" for row in images):
                raise ScientificError(409, "Una sesión no puede incluir imágenes archivadas.")
            terminal = {"completed", "completed_with_warnings"}
            if any(row["status"] not in terminal for row in detections + classifications):
                raise ScientificError(409, "Sólo pueden congelarse runs completados.")
            selected_detection_ids = set(detection_ids)
            if any(str(row["detection_run_id"]) not in selected_detection_ids for row in classifications):
                raise ScientificError(409, "Cada classification run requiere incluir su detection run de origen.")
            image_set = set(image_ids)
            for table, ids in (("cell_detection_runs", detection_ids), ("cell_classification_runs", classification_ids)):
                if ids:
                    membership = repository.image_run_membership(image_ids, ids, table)
                    if any(not any(run_id == pair[0] for pair in membership) for run_id in ids):
                        raise ScientificError(409, "Cada run debe contener al menos una imagen seleccionada.")
                    if any(pair[1] not in image_set for pair in membership):
                        raise ScientificError(409, "La selección de imágenes y runs es inconsistente.")
            image_by_id = {str(row["id"]): row for row in images}
            detection_by_id = {str(row["id"]): row for row in detections}
            classification_by_id = {str(row["id"]): row for row in classifications}
            snapshot = {
                "schema_version": "scientific-validation-snapshot-v1",
                "datasource": values["datasource"],
                "protocol": {"key": values["protocol_key"], "version": values["protocol_version"]},
                "matching": {"iou_threshold": values["matching_iou_threshold"]},
                "images": [
                    {"id": identifier, "sha256": image_by_id[identifier]["sha256"]}
                    for identifier in image_ids
                ],
                "detection_runs": [
                    {
                        "id": identifier,
                        "analysis_run_id": str(detection_by_id[identifier]["analysis_run_id"]),
                        "detector_key": detection_by_id[identifier]["detector_key"],
                        "detector_version": detection_by_id[identifier]["detector_version"],
                        "algorithm_version": detection_by_id[identifier]["algorithm_version"],
                        "input_manifest_sha256": detection_by_id[identifier]["input_manifest_sha256"],
                        "profile_snapshot": detection_by_id[identifier]["profile_snapshot"],
                    } for identifier in detection_ids
                ],
                "classification_runs": [
                    {
                        "id": identifier,
                        "analysis_run_id": str(classification_by_id[identifier]["analysis_run_id"]),
                        "detection_run_id": str(classification_by_id[identifier]["detection_run_id"]),
                        "model_registry_id": str(classification_by_id[identifier]["model_registry_id"]),
                        "model_name": classification_by_id[identifier]["model_name"],
                        "model_version": classification_by_id[identifier]["model_version"],
                        "input_manifest_sha256": classification_by_id[identifier]["input_manifest_sha256"],
                        "productive_threshold": classification_by_id[identifier]["model_snapshot"].get("threshold"),
                        "threshold_source": classification_by_id[identifier]["model_snapshot"].get("threshold_source"),
                        "model_snapshot": classification_by_id[identifier]["model_snapshot"],
                    } for identifier in classification_ids
                ],
            }
            canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)
            digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            row = repository.create(values, snapshot, digest, actor_id)
            record_event(
                event_type="SCIENTIFIC_VALIDATION_SESSION_CREATED",
                action="scientific.validation.created", principal=principal, request=request,
                success=True, after_state=_state(row), connection=connection,
                resource_type="scientific_validation_session", resource_id=str(row["id"]),
                metadata={"image_count": len(image_ids), "detection_run_count": len(detection_ids),
                          "classification_run_count": len(classification_ids)},
            )
            return row

    def get(self, session_id: str) -> dict:
        with self._engine.connect() as connection:
            row = ScientificValidationRepository(connection).get(session_id)
        if not row:
            raise ScientificError(404, "Sesión de validación no encontrada.")
        return row

    def list(self, status: str | None, limit: int, offset: int) -> dict:
        with self._engine.connect() as connection:
            return ScientificValidationRepository(connection).list(status, limit, offset)

    def update(self, session_id: str, values: dict, principal: Principal, request: Request) -> dict:
        actor_id = _actor(principal)
        if not values:
            return self.get(session_id)
        with mutation_connection(self._engine) as connection:
            repository = ScientificValidationRepository(connection)
            before = repository.get(session_id, for_update=True)
            if not before:
                raise ScientificError(404, "Sesión de validación no encontrada.")
            if before["status"] == "archived":
                raise ScientificError(409, "Una sesión archivada es inmutable.")
            if before["status"] == "completed":
                raise ScientificError(409, "Una sesión completada es inmutable; sólo puede archivarse.")
            next_status = values.get("status", before["status"])
            if next_status not in TRANSITIONS[before["status"]]:
                raise ScientificError(409, "Transición de estado inválida.")
            after = repository.update(session_id, values, actor_id)
            record_event(
                event_type="SCIENTIFIC_VALIDATION_SESSION_UPDATED",
                action="scientific.validation.updated", principal=principal, request=request,
                success=True, before_state=_state(before), after_state=_state(after),
                connection=connection, resource_type="scientific_validation_session", resource_id=session_id,
            )
            return after

    def archive(self, session_id: str, principal: Principal, request: Request, reason: str | None) -> dict:
        actor_id = _actor(principal)
        with mutation_connection(self._engine) as connection:
            repository = ScientificValidationRepository(connection)
            before = repository.get(session_id, for_update=True)
            if not before:
                raise ScientificError(404, "Sesión de validación no encontrada.")
            if before["status"] == "archived":
                raise ScientificError(409, "La sesión ya está archivada.")
            after = repository.archive(session_id, actor_id)
            record_event(
                event_type="SCIENTIFIC_VALIDATION_SESSION_ARCHIVED",
                action="scientific.validation.archived", principal=principal, request=request,
                success=True, before_state=_state(before), after_state=_state(after),
                metadata={"reason": reason} if reason else {}, connection=connection,
                resource_type="scientific_validation_session", resource_id=session_id,
            )
            return after

    @staticmethod
    def _annotation_audit_state(row: dict) -> dict:
        return ScientificValidationRepository._annotation_state(row)

    @staticmethod
    def _ensure_annotation_session(session: dict | None) -> None:
        if not session:
            raise ScientificError(404, "Sesión de validación no encontrada.")
        if session["status"] == "archived":
            raise ScientificError(409, "La sesión no admite cambios de anotaciones.")

    def create_annotation(
        self, session_id: str | None, values: dict, principal: Principal, request: Request
    ) -> dict:
        actor_id = _actor(principal)
        target_type = values["target_type"]
        target_id = str({
            "cell": values.get("cell_id"),
            "analysis": values.get("analysis_run_id"),
            "sample": values.get("sample_id"),
        }[target_type])
        with mutation_connection(self._engine) as connection:
            repository = ScientificValidationRepository(connection)
            if session_id:
                session = repository.get(session_id, for_update=True)
                self._ensure_annotation_session(session)
                target_valid = repository.target_belongs_to_session(
                    session_id, target_type=target_type, target_id=target_id
                )
            else:
                target_valid = repository.target_exists(
                    target_type=target_type, target_id=target_id
                )
            if not target_valid:
                raise ScientificError(409, "El target científico no existe o no pertenece al contexto.")
            row = repository.create_annotation(session_id, values, actor_id)
            state = self._annotation_audit_state(row)
            record_event(
                event_type="SCIENTIFIC_VALIDATION_ANNOTATION_CREATED",
                action="scientific.validation.annotation.created",
                principal=principal, request=request, success=True,
                after_state=state, connection=connection,
                resource_type="scientific_validation_annotation",
                resource_id=str(row["id"]),
                metadata={"validation_session_id": session_id, "target_type": target_type},
            )
            return row

    def list_annotations(self, session_id: str | None, **filters) -> dict:
        with self._engine.connect() as connection:
            repository = ScientificValidationRepository(connection)
            if session_id and not repository.get(session_id):
                raise ScientificError(404, "Sesión de validación no encontrada.")
            return repository.list_annotations(session_id, **filters)

    def get_annotation(self, session_id: str | None, annotation_id: str) -> dict:
        with self._engine.connect() as connection:
            repository = ScientificValidationRepository(connection)
            if session_id and not repository.get(session_id):
                raise ScientificError(404, "Sesión de validación no encontrada.")
            row = repository.get_annotation(session_id, annotation_id)
        if not row:
            raise ScientificError(404, "Anotación no encontrada.")
        return row

    def update_annotation(
        self,
        session_id: str | None,
        annotation_id: str,
        values: dict,
        principal: Principal,
        request: Request,
    ) -> dict:
        actor_id = _actor(principal)
        expected_version = values.pop("version")
        with mutation_connection(self._engine) as connection:
            repository = ScientificValidationRepository(connection)
            if session_id:
                session = repository.get(session_id)
                self._ensure_annotation_session(session)
            outcome = repository.update_annotation(
                session_id, annotation_id, values, expected_version, actor_id
            )
            if outcome is None:
                raise ScientificError(404, "Anotación no encontrada.")
            after, before = outcome
            if not after:
                raise ScientificError(409, "La anotación fue modificada por otro usuario.")
            record_event(
                event_type="SCIENTIFIC_VALIDATION_ANNOTATION_UPDATED",
                action="scientific.validation.annotation.updated",
                principal=principal, request=request, success=True,
                before_state=self._annotation_audit_state(before),
                after_state=self._annotation_audit_state(after),
                connection=connection, resource_type="scientific_validation_annotation",
                resource_id=annotation_id,
                metadata={"validation_session_id": session_id,
                          "previous_version": expected_version,
                          "version": after["version"]},
            )
            return after

    def annotation_history(
        self, session_id: str | None, annotation_id: str, *, limit: int, offset: int
    ) -> dict:
        with self._engine.connect() as connection:
            repository = ScientificValidationRepository(connection)
            if session_id and not repository.get(session_id):
                raise ScientificError(404, "Sesión de validación no encontrada.")
            result = repository.annotation_history(
                session_id, annotation_id, limit=limit, offset=offset
            )
        if result is None:
            raise ScientificError(404, "Anotación no encontrada.")
        return result
