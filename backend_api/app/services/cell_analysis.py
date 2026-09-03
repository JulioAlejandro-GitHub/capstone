from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import Request
from sqlalchemy.engine import Engine

from app.audit import mutation_connection, record_event
from app.db import get_primary_engine
from app.models.cell_detection import ComponentStatus
from app.repositories.cell_analysis import CellAnalysisRepository
from app.security import Principal
from app.services.cell_crop_storage import CellCropStorage, StagedCellCrop
from app.services.detectors.connected_components_v1 import (
    ALGORITHM_VERSION,
    COORDINATE_SPACE,
    DETECTOR_KEY,
    DETECTOR_VERSION,
    DetectorInputError,
    detect_path,
    profile_snapshot,
)
from app.services.local_storage import (
    LocalStorage,
    StorageChecksumMismatchError,
    StorageError,
    StorageSizeMismatchError,
)


class CellAnalysisError(ValueError):
    def __init__(self, status_code: int, detail: str, code: str = "CELL_ANALYSIS_ERROR"):
        self.status_code = status_code
        self.detail = detail
        self.code = code
        super().__init__(detail)


def frozen_manifest(images: list[dict]) -> str:
    items = [
        {
            "microscopy_image_id": str(item["microscopy_image_id"]),
            "sha256": item["input_sha256"].strip(),
            "file_size_bytes": item["input_file_size_bytes"],
            "width_px": item["input_width_px"],
            "height_px": item["input_height_px"],
            "sequence_number": item["sequence_number"],
        }
        for item in sorted(
            images, key=lambda value: (value["sequence_number"], str(value["microscopy_image_id"]))
        )
    ]
    canonical = json.dumps(items, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def _safe_cell_code(used: set[str]) -> str:
    while True:
        code = f"CELL-{uuid4().hex[:12].upper()}"
        if code not in used:
            used.add(code)
            return code


class CellAnalysisService:
    def __init__(
        self,
        *,
        engine: Engine | None = None,
        local_storage: LocalStorage | None = None,
        crop_storage: CellCropStorage | None = None,
    ):
        self.engine = engine or get_primary_engine()
        self.local_storage = local_storage
        self.crop_storage = crop_storage

    def _local(self) -> LocalStorage:
        return self.local_storage or LocalStorage()

    def _crops(self) -> CellCropStorage:
        return self.crop_storage or CellCropStorage(self._local())

    @staticmethod
    def _eligible(run: dict) -> None:
        if not run["ready_for_analysis"]:
            raise CellAnalysisError(
                409,
                "La ejecución no está habilitada para análisis celular.",
                "ANALYSIS_RUN_NOT_READY",
            )
        gate_eligible = run["quality_gate_status"] == "pass" or (
            run["quality_gate_status"] == "warning" and run["warning_approved"]
        )
        if not gate_eligible:
            raise CellAnalysisError(
                409,
                "El control técnico no autoriza la detección celular.",
                "QUALITY_GATE_NOT_APPROVED",
            )
        images = run["images"]
        if not images or len(images) != run["input_image_count"]:
            raise CellAnalysisError(
                409,
                "El conjunto congelado de imágenes está incompleto.",
                "FROZEN_IMAGE_SET_INCOMPLETE",
            )
        for image in images:
            unchanged = (
                image["current_image_status"] == "available"
                and image["storage_provider"] == "local"
                and image["current_sha256"] == image["input_sha256"]
                and image["current_file_size_bytes"] == image["input_file_size_bytes"]
                and image["current_width_px"] == image["input_width_px"]
                and image["current_height_px"] == image["input_height_px"]
            )
            if not unchanged:
                raise CellAnalysisError(
                    409,
                    "Una imagen congelada ya no coincide con su metadata original.",
                    "FROZEN_IMAGE_METADATA_MISMATCH",
                )
        if frozen_manifest(images) != run["input_manifest_sha256"]:
            raise CellAnalysisError(
                409,
                "El manifiesto congelado no coincide con la ejecución de análisis.",
                "INPUT_MANIFEST_MISMATCH",
            )

    def eligible_analysis_runs(self, *, limit: int, offset: int) -> dict:
        with self.engine.connect() as connection:
            return CellAnalysisRepository(connection).eligible_analysis_runs(
                detector_key=DETECTOR_KEY,
                detector_version=DETECTOR_VERSION,
                algorithm_version=ALGORITHM_VERSION,
                limit=limit,
                offset=offset,
            )

    def _create_or_existing(
        self, analysis_run_id: str, principal: Principal, request: Request
    ) -> tuple[dict, bool]:
        profile = profile_snapshot()
        with self.engine.begin() as connection:
            repository = CellAnalysisRepository(connection)
            analysis = repository.analysis_input(analysis_run_id, for_update=True)
            if not analysis:
                raise CellAnalysisError(404, "Ejecución de análisis inexistente.", "NOT_FOUND")
            self._eligible(analysis)
            existing = repository.find_equivalent(
                analysis_run_id=analysis["id"],
                detector_key=DETECTOR_KEY,
                detector_version=DETECTOR_VERSION,
                algorithm_version=ALGORITHM_VERSION,
                input_manifest_sha256=analysis["input_manifest_sha256"],
            )
            if existing:
                return existing, True
            detection_run_id = uuid4()
            detection_run_code = f"DET-{secrets.token_hex(4).upper()}"
            run = repository.create_run(
                run_id=detection_run_id,
                analysis_run_id=analysis["id"],
                detection_run_code=detection_run_code,
                detector_key=DETECTOR_KEY,
                detector_version=DETECTOR_VERSION,
                algorithm_version=ALGORITHM_VERSION,
                profile_snapshot=profile,
                input_manifest_sha256=analysis["input_manifest_sha256"],
                image_count=len(analysis["images"]),
                requested_by=principal.user_id,
            )
            repository.add_event(
                detection_run_id=detection_run_id,
                event_type="cell_detection.run.created",
                stage="created",
                status="completed",
                progress_current=0,
                progress_total=len(analysis["images"]),
                metadata={
                    "analysis_run_id": str(analysis["id"]),
                    "detector_key": DETECTOR_KEY,
                    "detector_version": DETECTOR_VERSION,
                    "algorithm_version": ALGORITHM_VERSION,
                },
            )
            record_event(
                event_type="scientific.cell_detection.created",
                action="create",
                principal=principal,
                request=request,
                success=True,
                connection=connection,
                resource_type="cell_detection_run",
                resource_id=str(detection_run_id),
                after_state={
                    "detection_run_id": str(detection_run_id),
                    "detection_run_code": detection_run_code,
                    "analysis_run_id": str(analysis["id"]),
                    "detector_key": DETECTOR_KEY,
                    "detector_version": DETECTOR_VERSION,
                    "algorithm_version": ALGORITHM_VERSION,
                    "input_manifest_sha256": analysis["input_manifest_sha256"],
                    "image_count": len(analysis["images"]),
                },
            )
            run["analysis_input"] = analysis
            return run, False

    def _start(self, detection_run_id: UUID, principal: Principal, request: Request) -> None:
        with self.engine.begin() as connection:
            repository = CellAnalysisRepository(connection)
            repository.start_run(detection_run_id)
            repository.add_event(
                detection_run_id=detection_run_id,
                event_type="cell_detection.run.started",
                stage="detection",
                status="processing",
            )
            record_event(
                event_type="scientific.cell_detection.started",
                action="execute",
                principal=principal,
                request=request,
                success=True,
                connection=connection,
                resource_type="cell_detection_run",
                resource_id=str(detection_run_id),
            )

    @staticmethod
    def _failure(exc: Exception) -> tuple[str, str, int]:
        if isinstance(exc, DetectorInputError):
            return exc.code, "La integridad de una imagen original no pudo verificarse.", 409
        if isinstance(exc, StorageError):
            return "CELL_CROP_STORAGE_ERROR", "No fue posible persistir un crop derivado.", 500
        if isinstance(exc, CellAnalysisError):
            return exc.code, exc.detail, exc.status_code
        return "CELL_DETECTION_FAILED", "La detección celular no pudo completarse.", 500

    def _mark_failed(
        self,
        detection_run_id: UUID,
        principal: Principal,
        request: Request,
        error_code: str,
        error_message: str,
    ) -> None:
        with self.engine.begin() as connection:
            repository = CellAnalysisRepository(connection)
            repository.fail_run(
                detection_run_id,
                error_code=error_code,
                error_message=error_message,
            )
            repository.add_event(
                detection_run_id=detection_run_id,
                event_type="cell_detection.run.failed",
                stage="detection",
                status="failed",
                message_code=error_code,
                message=error_message,
            )
            record_event(
                event_type="scientific.cell_detection.failed",
                action="execute",
                principal=principal,
                request=request,
                success=False,
                error_code=error_code,
                connection=connection,
                resource_type="cell_detection_run",
                resource_id=str(detection_run_id),
                after_state={
                    "detection_run_id": str(detection_run_id),
                    "status": "failed",
                    "error_code": error_code,
                },
            )

    def execute_detection(
        self, analysis_run_id: str, principal: Principal, request: Request
    ) -> dict:
        created, idempotent = self._create_or_existing(
            analysis_run_id, principal, request
        )
        if idempotent:
            result = self.get_run(str(created["id"]))
            result["idempotent"] = True
            return result

        detection_run_id = UUID(str(created["id"]))
        analysis = created.pop("analysis_input")
        profile = dict(created["profile_snapshot"])
        crop_storage: CellCropStorage | None = None
        staged_crops: list[StagedCellCrop] = []
        promoted_paths: list[Path] = []
        prepared_images: list[dict] = []
        component_total = 0
        detection_total = 0
        warning_total = 0
        cell_index = 0
        used_cell_codes: set[str] = set()
        try:
            self._start(detection_run_id, principal, request)
            crop_storage = self._crops()
            for current, image in enumerate(analysis["images"], 1):
                source_path = self._local().resolve_verified(
                    image["storage_key"],
                    expected_size_bytes=image["input_file_size_bytes"],
                    expected_sha256=image["input_sha256"],
                )
                result = detect_path(
                    source_path,
                    expected_sha256=image["input_sha256"],
                    expected_width_px=image["input_width_px"],
                    expected_height_px=image["input_height_px"],
                    expected_file_size_bytes=image["input_file_size_bytes"],
                    profile=profile,
                    integrity_preverified=True,
                )
                crops_by_component = {
                    crop.component_index: crop for crop in result.crops
                }
                image_components: list[dict] = []
                image_detections: list[dict] = []
                for component in result.components:
                    component_id = uuid4()
                    component_total += 1
                    component_row = {
                        "id": component_id,
                        "detection_run_id": detection_run_id,
                        "analysis_run_id": analysis["id"],
                        "analysis_run_image_id": image["analysis_run_image_id"],
                        "microscopy_image_id": image["microscopy_image_id"],
                        "component_index": component.component_index,
                        "bbox_x": component.bbox.x,
                        "bbox_y": component.bbox.y,
                        "bbox_width": component.bbox.width,
                        "bbox_height": component.bbox.height,
                        "centroid_x": component.centroid_x,
                        "centroid_y": component.centroid_y,
                        "area_px": component.area_px,
                        "perimeter_px": component.perimeter_px,
                        "circularity": component.circularity,
                        "solidity": component.solidity,
                        "touches_border": component.touches_border,
                        "component_status": component.component_status.value,
                        "rejection_code": component.rejection_code,
                        "metrics_json": {
                            "rejection_codes": list(component.rejection_codes),
                            "detector_score": component.detector_score,
                            "threshold_value": result.threshold_value,
                            "threshold_method": profile["threshold_method"],
                            "orientation_policy": profile["orientation_policy"],
                            "oriented_width_px": result.oriented_width_px,
                            "oriented_height_px": result.oriented_height_px,
                        },
                    }
                    image_components.append(component_row)
                    if component.component_status != ComponentStatus.ACCEPTED:
                        continue
                    crop = crops_by_component.get(component.component_index)
                    if crop is None:
                        raise CellAnalysisError(
                            500,
                            "Una detección aceptada no generó su crop.",
                            "MISSING_ACCEPTED_CROP",
                        )
                    cell_index += 1
                    detection_total += 1
                    cell_detection_id = uuid4()
                    crop_id = uuid4()
                    detection_row = {
                        "id": cell_detection_id,
                        "detection_run_id": detection_run_id,
                        "analysis_run_id": analysis["id"],
                        "connected_component_id": component_id,
                        "analysis_run_image_id": image["analysis_run_image_id"],
                        "microscopy_image_id": image["microscopy_image_id"],
                        "cell_index": cell_index,
                        "cell_code": _safe_cell_code(used_cell_codes),
                        "bbox_x": component.bbox.x,
                        "bbox_y": component.bbox.y,
                        "bbox_width": component.bbox.width,
                        "bbox_height": component.bbox.height,
                        "coordinate_space": COORDINATE_SPACE,
                        "detector_score": component.detector_score,
                        "automated_status": "candidate",
                    }
                    staged = crop_storage.stage(
                        analysis_run_id=UUID(str(analysis["id"])),
                        detection_run_id=detection_run_id,
                        microscopy_image_id=UUID(str(image["microscopy_image_id"])),
                        cell_detection_id=cell_detection_id,
                        png_bytes=crop.png_bytes,
                        expected_width_px=crop.width_px,
                        expected_height_px=crop.height_px,
                        padding_px=crop.padding_px,
                    )
                    staged_crops.append(staged)
                    detection_row["crop"] = {
                        "id": crop_id,
                        "cell_detection_id": cell_detection_id,
                        "relative_storage_key": staged.relative_storage_key,
                        "sha256": staged.sha256,
                        "file_size_bytes": staged.file_size_bytes,
                        "width_px": staged.width_px,
                        "height_px": staged.height_px,
                        "format": staged.format,
                        "padding_px": staged.padding_px,
                    }
                    detection_row["staged"] = staged
                    image_detections.append(detection_row)
                warning_total += len(result.warnings)
                prepared_images.append(
                    {
                        "current": current,
                        "source": image,
                        "result": result,
                        "components": image_components,
                        "detections": image_detections,
                    }
                )

            final_status = (
                "completed_with_warnings" if warning_total else "completed"
            )
            with self.engine.begin() as connection:
                repository = CellAnalysisRepository(connection)
                for prepared in prepared_images:
                    for component in prepared["components"]:
                        repository.insert_component(component)
                    for detection in prepared["detections"]:
                        repository.insert_detection(
                            {
                                key: value
                                for key, value in detection.items()
                                if key not in {"crop", "staged"}
                            }
                        )
                        repository.insert_crop(detection["crop"])
                    for detection in prepared["detections"]:
                        promoted_paths.append(
                            crop_storage.promote(detection["staged"])
                        )
                    source = prepared["source"]
                    result = prepared["result"]
                    repository.add_event(
                        detection_run_id=detection_run_id,
                        microscopy_image_id=source["microscopy_image_id"],
                        event_type="cell_detection.image.completed",
                        stage="detection",
                        status="completed_with_warnings"
                        if result.warnings
                        else "completed",
                        progress_current=prepared["current"],
                        progress_total=len(prepared_images),
                        metadata={
                            "sequence_number": source["sequence_number"],
                            "raw_width_px": result.raw_width_px,
                            "raw_height_px": result.raw_height_px,
                            "oriented_width_px": result.oriented_width_px,
                            "oriented_height_px": result.oriented_height_px,
                            "orientation_policy": profile["orientation_policy"],
                            "threshold_value": result.threshold_value,
                            "component_count": len(result.components),
                            "detection_count": len(result.crops),
                            "warning_codes": list(result.warnings),
                        },
                    )
                repository.complete_run(
                    detection_run_id,
                    status=final_status,
                    image_count=len(prepared_images),
                    component_count=component_total,
                    detection_count=detection_total,
                    crop_count=len(staged_crops),
                    warning_count=warning_total,
                )
                repository.add_event(
                    detection_run_id=detection_run_id,
                    event_type="cell_detection.run.completed",
                    stage="persistence",
                    status=final_status,
                    progress_current=len(prepared_images),
                    progress_total=len(prepared_images),
                    metadata={
                        "component_count": component_total,
                        "detection_count": detection_total,
                        "crop_count": len(staged_crops),
                        "warning_count": warning_total,
                    },
                )
                record_event(
                    event_type="scientific.cell_detection.completed",
                    action="execute",
                    principal=principal,
                    request=request,
                    success=True,
                    connection=connection,
                    resource_type="cell_detection_run",
                    resource_id=str(detection_run_id),
                    after_state={
                        "detection_run_id": str(detection_run_id),
                        "status": final_status,
                        "processed_image_count": len(prepared_images),
                        "component_count": component_total,
                        "detection_count": detection_total,
                        "crop_count": len(staged_crops),
                        "warning_count": warning_total,
                    },
                )
        except Exception as exc:
            if crop_storage is not None:
                crop_storage.cleanup(
                    [staged.path for staged in staged_crops] + promoted_paths
                )
            error_code, error_message, status_code = self._failure(exc)
            self._mark_failed(
                detection_run_id,
                principal,
                request,
                error_code,
                error_message,
            )
            raise CellAnalysisError(status_code, error_message, error_code) from exc
        result = self.get_run(str(detection_run_id))
        result["idempotent"] = False
        return result

    @staticmethod
    def _run_dto(run: dict) -> dict:
        return dict(run)

    @staticmethod
    def _image_dto(detection_run_id: str, image: dict) -> dict:
        return {
            **image,
            "content_url": (
                f"/api/v1/cell-analysis/detection-runs/{detection_run_id}/"
                f"images/{image['microscopy_image_id']}/content"
            ),
        }

    @staticmethod
    def _detection_dto(row: dict) -> dict:
        latest_review = None
        if row.get("latest_review_id"):
            latest_review = {
                "id": row["latest_review_id"],
                "entity_type": "cell_detection",
                "entity_id": row["id"],
                "decision": row["review_status"],
                "comment": row["latest_review_comment"],
                "actor_user_id": row["latest_review_actor_user_id"],
                "actor_username": row["latest_review_actor_username"],
                "created_at": row["latest_review_created_at"],
            }
        return {
            "id": row["id"],
            "detection_run_id": row["detection_run_id"],
            "detection_run_code": row["detection_run_code"],
            "analysis_run_image_id": row["analysis_run_image_id"],
            "microscopy_image_id": row["microscopy_image_id"],
            "cell_index": row["cell_index"],
            "cell_code": row["cell_code"],
            "bbox_x": row["bbox_x"],
            "bbox_y": row["bbox_y"],
            "bbox_width": row["bbox_width"],
            "bbox_height": row["bbox_height"],
            "coordinate_space": row["coordinate_space"],
            "detector_score": row["detector_score"],
            "automated_status": row["automated_status"],
            "created_at": row["created_at"],
            "review_status": row["review_status"],
            "latest_review": latest_review,
            "detector": {
                "key": row["detector_key"],
                "version": row["detector_version"],
                "algorithm_version": row["algorithm_version"],
            },
            "component": {
                "area_px": row["area_px"],
                "perimeter_px": row["perimeter_px"],
                "circularity": row["circularity"],
                "solidity": row["solidity"],
                "touches_border": row["touches_border"],
                "metrics_json": row["component_metrics_json"],
            },
            "crop": {
                "id": row["crop_id"],
                "sha256": row["crop_sha256"],
                "file_size_bytes": row["crop_file_size_bytes"],
                "width_px": row["crop_width_px"],
                "height_px": row["crop_height_px"],
                "format": row["crop_format"],
                "padding_px": row["crop_padding_px"],
                "content_url": f"/api/v1/cell-analysis/crops/{row['crop_id']}/content",
            },
            "source_image": {
                "microscopy_image_id": row["microscopy_image_id"],
                "sequence_number": row["source_sequence_number"],
                "safe_name": row["source_safe_name"],
                "mime_type": row["source_mime_type"],
                "width_px": row["source_width_px"],
                "height_px": row["source_height_px"],
                "content_url": (
                    f"/api/v1/cell-analysis/detection-runs/{row['detection_run_id']}/"
                    f"images/{row['microscopy_image_id']}/content"
                ),
            },
        }

    def list_runs(
        self,
        *,
        status: str | None,
        analysis_run_id: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        with self.engine.connect() as connection:
            return CellAnalysisRepository(connection).list_runs(
                status=status,
                analysis_run_id=analysis_run_id,
                limit=limit,
                offset=offset,
            )

    def get_run(self, detection_run_id: str) -> dict:
        with self.engine.connect() as connection:
            repository = CellAnalysisRepository(connection)
            run = repository.get_run(detection_run_id)
            if not run:
                raise CellAnalysisError(404, "Ejecución de detección inexistente.", "NOT_FOUND")
            images = repository.list_images(detection_run_id)
            events = repository.events(detection_run_id)
        result = self._run_dto(run)
        result["images"] = [
            self._image_dto(detection_run_id, image) for image in (images or [])
        ]
        result["events"] = events or []
        result["review_counts"] = {
            "reviewed": result["reviewed_count"],
            "pending": result["pending_review_count"],
            "unreviewed": result["pending_review_count"],
            "accepted": result["accepted_count"],
            "rejected": result["rejected_count"],
            "needs_attention": result["needs_attention_count"],
        }
        return result

    def list_images(self, detection_run_id: str) -> dict:
        with self.engine.connect() as connection:
            rows = CellAnalysisRepository(connection).list_images(detection_run_id)
        if rows is None:
            raise CellAnalysisError(404, "Ejecución de detección inexistente.", "NOT_FOUND")
        return {
            "items": [self._image_dto(detection_run_id, row) for row in rows],
            "total": len(rows),
        }

    def list_detections(
        self,
        *,
        detection_run_id: str,
        microscopy_image_id: str,
        review_status: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        with self.engine.connect() as connection:
            result = CellAnalysisRepository(connection).list_detections(
                detection_run_id=detection_run_id,
                microscopy_image_id=microscopy_image_id,
                review_status=review_status,
                limit=limit,
                offset=offset,
            )
        if result is None:
            raise CellAnalysisError(
                404, "La imagen no pertenece a la ejecución de detección.", "NOT_FOUND"
            )
        result["items"] = [self._detection_dto(row) for row in result["items"]]
        return result

    def get_detection(self, cell_detection_id: str) -> dict:
        with self.engine.connect() as connection:
            repository = CellAnalysisRepository(connection)
            row = repository.get_detection(cell_detection_id)
            reviews = (
                repository.reviews(cell_detection_id, limit=500, offset=0)
                if row
                else None
            )
        if not row:
            raise CellAnalysisError(404, "Detección celular inexistente.", "NOT_FOUND")
        result = self._detection_dto(row)
        result["review_history"] = reviews["items"] if reviews else []
        return result

    def create_review(
        self,
        *,
        cell_detection_id: str,
        decision: str,
        comment: str | None,
        principal: Principal,
        request: Request,
    ) -> dict:
        clean = comment.strip() if comment else None
        if decision in {"rejected", "needs_attention", "comment_only"} and not clean:
            raise CellAnalysisError(
                422,
                "La decisión seleccionada requiere un comentario.",
                "REVIEW_COMMENT_REQUIRED",
            )
        if decision == "accepted" and comment is not None and not clean:
            clean = None
        with mutation_connection(self.engine) as connection:
            repository = CellAnalysisRepository(connection)
            review = repository.create_review(
                cell_detection_id=cell_detection_id,
                decision=decision,
                comment=clean,
                actor_user_id=principal.user_id,
            )
            if not review:
                raise CellAnalysisError(404, "Detección celular inexistente.", "NOT_FOUND")
            record_event(
                event_type="scientific.cell_review.created",
                action="review",
                principal=principal,
                request=request,
                success=True,
                connection=connection,
                resource_type="cell_detection",
                resource_id=cell_detection_id,
                after_state={
                    "review_id": str(review["id"]),
                    "cell_detection_id": cell_detection_id,
                    "decision": decision,
                    "comment_present": clean is not None,
                    "comment_length": len(clean) if clean else 0,
                    "actor_user_id": principal.user_id,
                },
            )
            effective = repository.get_detection(cell_detection_id)
        return {
            **review,
            "effective_review_status": effective["review_status"] if effective else "unreviewed",
        }

    def reviews(
        self, cell_detection_id: str, *, limit: int, offset: int
    ) -> dict:
        with self.engine.connect() as connection:
            result = CellAnalysisRepository(connection).reviews(
                cell_detection_id, limit=limit, offset=offset
            )
        if result is None:
            raise CellAnalysisError(404, "Detección celular inexistente.", "NOT_FOUND")
        return result

    def crop_content(self, crop_id: str) -> tuple[dict, Path]:
        with self.engine.connect() as connection:
            crop = CellAnalysisRepository(connection).crop(crop_id)
        if not crop:
            raise CellAnalysisError(404, "Crop inexistente.", "NOT_FOUND")
        try:
            path = self._crops().resolve_verified(
                crop["relative_storage_key"],
                expected_size_bytes=crop["file_size_bytes"],
                expected_sha256=crop["sha256"],
            )
        except (StorageSizeMismatchError, StorageChecksumMismatchError) as exc:
            raise CellAnalysisError(
                409,
                "El contenido no supera la verificación de integridad.",
                "CONTENT_INTEGRITY_MISMATCH",
            ) from exc
        except (StorageError, FileNotFoundError, OSError) as exc:
            raise CellAnalysisError(404, "Contenido no disponible.", "CONTENT_UNAVAILABLE") from exc
        return crop, path

    def source_image_content(
        self, detection_run_id: str, microscopy_image_id: str
    ) -> tuple[dict, Path]:
        with self.engine.connect() as connection:
            image = CellAnalysisRepository(connection).source_image(
                detection_run_id, microscopy_image_id
            )
        if not image:
            raise CellAnalysisError(404, "Imagen original no disponible.", "NOT_FOUND")
        metadata_matches = (
            image["sha256"] == image["input_sha256"]
            and image["file_size_bytes"] == image["input_file_size_bytes"]
            and image["current_width_px"] == image["input_width_px"]
            and image["current_height_px"] == image["input_height_px"]
        )
        if not metadata_matches:
            raise CellAnalysisError(
                409,
                "La imagen original ya no coincide con el conjunto congelado.",
                "SOURCE_METADATA_MISMATCH",
            )
        if image["mime_type"] not in {"image/jpeg", "image/png", "image/tiff"}:
            raise CellAnalysisError(
                409,
                "El MIME de la imagen original no es compatible.",
                "SOURCE_MIME_MISMATCH",
            )
        try:
            path = self._local().resolve_verified(
                image["storage_key"],
                expected_size_bytes=image["input_file_size_bytes"],
                expected_sha256=image["input_sha256"],
            )
        except (StorageSizeMismatchError, StorageChecksumMismatchError) as exc:
            raise CellAnalysisError(
                409,
                "La imagen original no supera la verificación de integridad.",
                "CONTENT_INTEGRITY_MISMATCH",
            ) from exc
        except (StorageError, FileNotFoundError, OSError) as exc:
            raise CellAnalysisError(
                404, "Imagen original no disponible.", "CONTENT_UNAVAILABLE"
            ) from exc
        return image, path
