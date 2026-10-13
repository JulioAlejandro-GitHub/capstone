"""HTTP adapter for the frozen 76.3A RBC detector; no local ML dependencies."""
from __future__ import annotations

import io
import math
from pathlib import PurePosixPath
from typing import Literal, Self

import httpx
from PIL import Image, ImageOps
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.config import get_settings, validate_yolo_runtime_url
from app.models.cell_detection import BoundingBox, ComponentStatus, ConnectedComponent, DetectionResult

DETECTOR_KEY = "yolo26_seg_v1"
DETECTOR_VERSION = "1.0.0"
ALGORITHM_VERSION = "yolo26-seg-tiling-global-nms-1.0.0"
# Frozen identity validated in 76.3A. A new checkpoint requires a versioned adapter.
CHECKPOINT_SHA256 = "1a64bc34d188a48b7ed4fcd3276a41aa61d4ab7c037e360ac4beab3e24c31c26"
MODEL_CHECKPOINT = "smear_segmentation_project/runs/yolo26_seg/yolo26n_rbc_1024_v1/weights/best.pt"


class YoloRuntimeError(RuntimeError):
    """Safe error code only: never retain HTTP bodies, tokens or image bytes."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class _Options(_StrictModel):
    confidence: float = Field(default=0.25, gt=0, le=1)
    nms_iou: float = Field(default=0.7, gt=0, le=1)
    max_detections_per_tile: int = Field(default=1000, ge=1, le=2000)


class _Profile(_Options):
    detector_key: Literal["yolo26_seg_v1"] = DETECTOR_KEY
    detector_version: Literal["1.0.0"] = DETECTOR_VERSION
    algorithm_version: Literal["yolo26-seg-tiling-global-nms-1.0.0"] = ALGORITHM_VERSION
    runtime_version: Literal["1.0.0"] = "1.0.0"
    model_checkpoint: Literal[MODEL_CHECKPOINT] = MODEL_CHECKPOINT
    checkpoint_sha256: Literal[CHECKPOINT_SHA256] = CHECKPOINT_SHA256
    device: Literal["mps"] = "mps"
    tile_size: Literal[1024] = 1024
    tile_overlap: Literal[256] = 256
    coordinate_space: Literal["original_image_pixels"] = "original_image_pixels"
    coordinate_origin: Literal["top_left"] = "top_left"
    bbox_format: Literal["xywh"] = "xywh"
    orientation_policy: Literal["exif_transpose"] = "exif_transpose"
    threshold_method: Literal["yolo_confidence"] = "yolo_confidence"
    crop_padding_px: int = Field(default=4, ge=0)
    maximum_components_per_image: int = Field(default=500, ge=1, le=500)
    geometric_metrics_policy: Literal["unavailable_as_null"] = "unavailable_as_null"
    area_policy: Literal["runtime_area_ceil"] = "runtime_area_ceil"
    component_order: Literal["confidence_desc_tile_bbox"] = "confidence_desc_tile_bbox"


def profile_snapshot(overrides: dict | None = None) -> dict:
    """Persist only reproducible scientific parameters; never transport secrets."""
    try:
        return _Profile.model_validate(overrides if overrides is not None else {}).model_dump()
    except ValidationError:
        raise ValueError("Invalid YOLO detector profile") from None


class _Box(_StrictModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class _Detection(_StrictModel):
    bbox: _Box
    confidence: float = Field(ge=0, le=1)
    centroid_x: float
    centroid_y: float
    area_px: float = Field(gt=0)
    geometry_source: Literal["mask_polygon", "bbox"]
    mask_polygon: list[tuple[float, float]] | None
    tile_id: str = Field(pattern=r"^image__x[0-9]{4,}_y[0-9]{4,}$")

    @model_validator(mode="after")
    def validate_geometry(self) -> Self:
        box = self.bbox
        if not (box.x <= self.centroid_x <= box.x + box.width
                and box.y <= self.centroid_y <= box.y + box.height
                and self.area_px <= box.width * box.height):
            raise ValueError("Invalid centroid or area")
        if self.geometry_source == "mask_polygon":
            if self.mask_polygon is None or len(self.mask_polygon) < 3:
                raise ValueError("Missing mask polygon")
            if any(not (box.x <= x <= box.x + box.width and box.y <= y <= box.y + box.height)
                   for x, y in self.mask_polygon):
                raise ValueError("Mask outside bounding box")
            points = self.mask_polygon
            polygon_area = abs(math.fsum(
                x1 * y2 - x2 * y1
                for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1])
            )) / 2
            if polygon_area <= 0 or not math.isclose(self.area_px, polygon_area, rel_tol=1e-4, abs_tol=1e-3):
                raise ValueError("Degenerate mask or inconsistent polygon area")
        elif (self.mask_polygon is not None or self.area_px != box.width * box.height
              or self.centroid_x != box.x + box.width / 2
              or self.centroid_y != box.y + box.height / 2):
            raise ValueError("Inconsistent bbox geometry")
        return self


class _ResponseOptions(_Options):
    # Unlike profiles, responses must explicitly contain every effective option.
    confidence: float = Field(gt=0, le=1)
    nms_iou: float = Field(gt=0, le=1)
    max_detections_per_tile: int = Field(ge=1, le=2000)


class _Response(_StrictModel):
    detector_key: Literal["yolo26_seg_v1"]
    detector_version: Literal["1.0.0"]
    algorithm_version: Literal["yolo26-seg-tiling-global-nms-1.0.0"]
    runtime_version: Literal["1.0.0"]
    model_checkpoint: str = Field(min_length=1)
    checkpoint_sha256: Literal[CHECKPOINT_SHA256]
    device: Literal["mps"]
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)
    tile_size: Literal[1024]
    tile_overlap: Literal[256]
    coordinate_space: Literal["original_image_pixels"]
    orientation_policy: Literal["exif_transpose"]
    bbox_format: Literal["xywh"]
    options: _ResponseOptions
    detections: list[_Detection]
    raw_detection_count: int = Field(ge=0)
    invalid_detection_count: int = Field(ge=0)
    consolidated_detection_count: int = Field(ge=0)
    final_detection_count: int = Field(ge=0)
    warnings: list[Literal["TILE_DETECTION_LIMIT_REACHED", "MASK_UNAVAILABLE_BBOX_GEOMETRY",
                           "INVALID_GEOMETRY_DISCARDED", "NO_DETECTIONS"]]

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        checkpoint = PurePosixPath(self.model_checkpoint)
        if (not checkpoint.is_absolute() or ".." in checkpoint.parts
                or not self.model_checkpoint.endswith("/" + MODEL_CHECKPOINT)):
            raise ValueError("Unexpected checkpoint path")
        if (self.final_detection_count != len(self.detections)
                or self.raw_detection_count != self.invalid_detection_count
                + self.consolidated_detection_count + self.final_detection_count):
            raise ValueError("Inconsistent detection counts")
        for detection in self.detections:
            if not BoundingBox(**detection.bbox.model_dump()).is_within(self.image_width, self.image_height):
                raise ValueError("Bounding box outside image")
            if detection.confidence < self.options.confidence:
                raise ValueError("Detection below requested confidence")
        if bool(self.invalid_detection_count) != ("INVALID_GEOMETRY_DISCARDED" in self.warnings):
            raise ValueError("Inconsistent invalid-geometry warning")
        if bool(self.detections) == ("NO_DETECTIONS" in self.warnings):
            raise ValueError("Inconsistent empty-result warning")
        missing_masks = any(d.geometry_source == "bbox" for d in self.detections)
        if missing_masks and "MASK_UNAVAILABLE_BBOX_GEOMETRY" not in self.warnings:
            raise ValueError("Missing bbox geometry warning")
        return self


def _request_detection(image: Image.Image, options: dict) -> _Response:
    settings = get_settings()
    url = validate_yolo_runtime_url(settings.yolo_runtime_url)
    token = settings.yolo_runtime_token
    if len(token) < 32 or not token.isascii() or any(c.isspace() or ord(c) < 33 or ord(c) > 126 for c in token):
        raise YoloRuntimeError("YOLO_RUNTIME_TOKEN_INVALID")
    output = io.BytesIO()
    # Drop metadata, especially EXIF, after orientation so the runtime cannot rotate twice.
    image = image.copy()
    image.info.clear()
    image.save(output, format="PNG")
    try:
        with httpx.Client(timeout=settings.yolo_runtime_timeout_seconds,
                          follow_redirects=False, trust_env=False) as client:
            response = client.post(url + "/v1/detect", content=output.getvalue(), params=options,
                                   headers={"Authorization": f"Bearer {token}",
                                            "Content-Type": "application/octet-stream"})
    except httpx.TimeoutException:
        raise YoloRuntimeError("YOLO_RUNTIME_TIMEOUT") from None
    except httpx.RequestError:
        raise YoloRuntimeError("YOLO_RUNTIME_UNAVAILABLE") from None
    if response.status_code != 200:
        raise YoloRuntimeError(f"YOLO_RUNTIME_HTTP_{response.status_code}")
    try:
        result = _Response.model_validate_json(response.content)
    except ValidationError:
        raise YoloRuntimeError("YOLO_RUNTIME_INVALID_RESPONSE") from None
    if (result.image_width, result.image_height) != image.size or result.options.model_dump() != options:
        raise YoloRuntimeError("YOLO_RUNTIME_RESPONSE_MISMATCH")
    return result


def _component(detection: _Detection, index: int, width: int, height: int, cap: int) -> ConnectedComponent:
    box = BoundingBox(**detection.bbox.model_dump())
    rejected = index > cap
    codes = ("MAXIMUM_COMPONENTS_EXCEEDED",) if rejected else ()
    return ConnectedComponent(
        component_index=index, bbox=box,
        centroid_x=detection.centroid_x, centroid_y=detection.centroid_y,
        area_px=math.ceil(detection.area_px),
        perimeter_px=None, circularity=None, solidity=None,
        touches_border=box.x == 0 or box.y == 0 or box.right == width or box.bottom == height,
        component_status=ComponentStatus.REJECTED_BY_FILTER if rejected else ComponentStatus.ACCEPTED,
        rejection_code=codes[0] if codes else None, rejection_codes=codes,
        detector_score=detection.confidence,
    )


def detect_image(image: Image.Image, profile: dict | None = None) -> DetectionResult:
    selected = profile_snapshot(profile)
    raw_width, raw_height = image.size
    oriented = ImageOps.exif_transpose(image).convert("RGB")
    options = {key: selected[key] for key in _Options.model_fields}
    result = _request_detection(oriented, options)
    # Tie-breaking covers all geometry so response ordering cannot alter component IDs.
    ordered = sorted(result.detections, key=lambda d: (
        -d.confidence, d.tile_id, d.bbox.y, d.bbox.x, d.bbox.width, d.bbox.height,
        d.centroid_y, d.centroid_x, d.area_px, d.geometry_source, tuple(d.mask_polygon or ()),
    ))
    components = tuple(_component(d, index, *oriented.size, selected["maximum_components_per_image"])
                       for index, d in enumerate(ordered, 1))
    warnings = set(result.warnings)
    if components:
        warnings.add("YOLO_GEOMETRIC_METRICS_UNAVAILABLE")
    else:
        warnings.add("NO_ACCEPTED_COMPONENTS")
    if len(components) > selected["maximum_components_per_image"]:
        warnings.add("MAXIMUM_COMPONENTS_REACHED")
    return DetectionResult(raw_width_px=raw_width, raw_height_px=raw_height,
                           oriented_width_px=oriented.width, oriented_height_px=oriented.height,
                           threshold_value=None, components=components, warnings=tuple(sorted(warnings)))
