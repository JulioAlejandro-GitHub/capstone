"""Local MPS inference; no datasets, persistence or classifier dependencies."""
from __future__ import annotations

import hashlib
import math
import os
import platform
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Literal

import numpy as np
from PIL import Image, ImageOps
from pydantic import BaseModel, ConfigDict, Field

from .targets import RBC_CLASS_ID, RBC_CLASS_NAME
from .tiling import TILE_OVERLAP, TILE_SIZE, tile_id, tiles_for_image

DETECTOR_KEY = "yolo26_seg_v1"
DETECTOR_VERSION = "1.1.0"
RUNTIME_VERSION = "1.1.0"
ALGORITHM_VERSION = "yolo26-seg-scale-normalized-containment-1.1.0"

# Median polygon width of the training cells; recall on VAL drops below this scale.
TARGET_CELL_PX = 129.0
MIN_RELIABLE_CELL_PX = 64.0
MIN_SCALE_EVIDENCE = 3
PROBE_SCALES = (2.0, 3.0, 4.0)
MAX_INPUT_SCALE = 8.0
MAX_SCALED_PIXELS = 64_000_000
SCALE_REUSE_TOLERANCE = 0.05


def selected_checkpoint() -> Path:
    from dotenv import dotenv_values
    from .checkpoints import checkpoint_reference, resolve_checkpoint

    project_root = Path(__file__).resolve().parents[2]
    environment = {**dotenv_values(project_root / ".env"), **os.environ}
    # Legacy override is only effective when no run selector is configured.
    reference = (checkpoint_reference(environment) if "YOLO_RUN_UUID" in environment
                 or not environment.get("YOLO_RUNTIME_CHECKPOINT")
                 else Path(environment["YOLO_RUNTIME_CHECKPOINT"]))
    return resolve_checkpoint(reference, project_root.parent)


class InferenceOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    confidence: float = Field(default=0.25, gt=0, le=1)
    nms_iou: float = Field(default=0.7, gt=0, le=1)
    max_detections_per_tile: int = Field(default=1000, ge=1, le=2000)
    target_cell_px: float = Field(default=TARGET_CELL_PX, gt=0)
    containment_threshold: float = Field(default=0.6, gt=0, le=1)


class Box(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class Detection(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    bbox: Box
    confidence: float = Field(ge=0, le=1)
    centroid_x: float
    centroid_y: float
    area_px: float = Field(gt=0)
    geometry_source: Literal["mask_polygon", "bbox"]
    mask_polygon: list[tuple[float, float]] | None = None
    tile_id: str


class DetectionResponse(BaseModel):
    detector_key: str = DETECTOR_KEY
    detector_version: str = DETECTOR_VERSION
    runtime_version: str = RUNTIME_VERSION
    algorithm_version: str = ALGORITHM_VERSION
    model_checkpoint: str
    checkpoint_sha256: str
    device: Literal["mps"] = "mps"
    image_width: int
    image_height: int
    tile_size: int = TILE_SIZE
    tile_overlap: int = TILE_OVERLAP
    coordinate_space: str = "original_image_pixels"
    orientation_policy: str = "exif_transpose"
    bbox_format: str = "xywh"
    options: InferenceOptions
    detections: list[Detection]
    raw_detection_count: int
    invalid_detection_count: int
    consolidated_detection_count: int
    final_detection_count: int
    input_scale: float = Field(default=1.0, ge=1)
    estimated_cell_px: float | None = None
    warnings: list[str]


def _intersection(first: Box, second: Box) -> int:
    width = max(0, min(first.x + first.width, second.x + second.width) - max(first.x, second.x))
    height = max(0, min(first.y + first.height, second.y + second.height) - max(first.y, second.y))
    return width * height


def box_iou(first: Box, second: Box) -> float:
    intersection = _intersection(first, second)
    return intersection / (first.width * first.height + second.width * second.height - intersection)


def consolidate(detections: list[Detection], iou: float) -> list[Detection]:
    """Stable greedy global box NMS; proximity alone never removes a cell."""
    ordered = sorted(detections, key=lambda d: (-d.confidence, d.tile_id, d.bbox.y, d.bbox.x, d.bbox.width, d.bbox.height))
    kept: list[Detection] = []
    for candidate in ordered:
        if all(box_iou(candidate.bbox, previous.bbox) <= iou for previous in kept):
            kept.append(candidate)
    return kept


def suppress_contained(detections: list[Detection], threshold: float) -> list[Detection]:
    """Drop tile-border fragments: boxes mostly inside a larger detection (intersection over own area)."""
    ordered = sorted(detections, key=lambda d: (-d.bbox.width * d.bbox.height, -d.confidence, d.tile_id, d.bbox.y, d.bbox.x))
    kept: list[Detection] = []
    for candidate in ordered:
        box = candidate.bbox
        area = box.width * box.height
        if all(_intersection(box, previous.bbox) / area <= threshold for previous in kept):
            kept.append(candidate)
    return sorted(kept, key=lambda d: (-d.confidence, d.tile_id, d.bbox.y, d.bbox.x, d.bbox.width, d.bbox.height))


def scale_limit(width: int, height: int) -> float:
    return min(MAX_INPUT_SCALE, math.sqrt(MAX_SCALED_PIXELS / (width * height)))


def estimate_cell_px(detections: list[Detection]) -> float | None:
    """Median largest box side, in source pixels; None without enough evidence."""
    if len(detections) < MIN_SCALE_EVIDENCE:
        return None
    return float(np.median([max(d.bbox.width, d.bbox.height) for d in detections]))


def rescale_detection(detection: Detection, scale_x: float, scale_y: float, width: int, height: int) -> Detection | None:
    """Map a detection from the resampled raster back to oriented source pixels."""
    if scale_x == 1 and scale_y == 1:
        return detection
    box = detection.bbox
    left, top = math.floor(box.x / scale_x), math.floor(box.y / scale_y)
    right = min(width, math.ceil((box.x + box.width) / scale_x))
    bottom = min(height, math.ceil((box.y + box.height) / scale_y))
    if right <= left or bottom <= top:
        return None
    scaled = Box(x=left, y=top, width=right - left, height=bottom - top)
    if detection.mask_polygon is None:
        return detection.model_copy(update={"bbox": scaled, "area_px": float(scaled.width * scaled.height),
                                            "centroid_x": left + scaled.width / 2,
                                            "centroid_y": top + scaled.height / 2})
    points = [(min(max(x / scale_x, left), right), min(max(y / scale_y, top), bottom))
              for x, y in detection.mask_polygon]
    area = abs(math.fsum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]))) / 2
    if area <= 0:
        return None
    return detection.model_copy(update={"bbox": scaled, "area_px": area, "mask_polygon": points,
                                        "centroid_x": detection.centroid_x / scale_x,
                                        "centroid_y": detection.centroid_y / scale_y})


def global_detection(xyxy: list[float], confidence: float, polygon: np.ndarray | None,
                     origin: tuple[int, int], size: tuple[int, int], identity: str) -> Detection | None:
    """Clip to the real tile raster, then translate to oriented source pixels."""
    import cv2

    if not all(math.isfinite(v) for v in [*xyxy, confidence]) or not 0 <= confidence <= 1:
        return None
    ox, oy = origin
    width, height = size
    left, top, right, bottom = xyxy
    left, right = max(0, left), min(width, right)
    top, bottom = max(0, top), min(height, bottom)
    if right <= left or bottom <= top:
        return None
    x, y = math.floor(left) + ox, math.floor(top) + oy
    box = Box(x=x, y=y, width=math.ceil(right) + ox - x, height=math.ceil(bottom) + oy - y)
    points = None
    area = float(box.width * box.height)
    cx, cy = x + box.width / 2, y + box.height / 2
    if polygon is not None:
        contour = np.asarray(polygon, dtype=np.float32).reshape(-1, 2).copy()
        if len(contour) < 3 or not np.isfinite(contour).all():
            return None
        contour[:, 0] = np.clip(contour[:, 0], left, right) + ox
        contour[:, 1] = np.clip(contour[:, 1], top, bottom) + oy
        moments = cv2.moments(contour)
        area = moments["m00"]
        if area <= 0:
            return None
        cx, cy = moments["m10"] / area, moments["m01"] / area
        if not x <= cx <= x + box.width or not y <= cy <= y + box.height:
            return None
        points = [(float(px), float(py)) for px, py in contour]
    return Detection(bbox=box, confidence=confidence, centroid_x=cx, centroid_y=cy,
                     area_px=area, geometry_source="mask_polygon" if points else "bbox",
                     mask_polygon=points, tile_id=identity)


@dataclass(frozen=True)
class _Pass:
    scale: float
    detections: list[Detection]
    raw_count: int
    invalid_count: int
    consolidated_count: int
    warnings: frozenset[str]


class YoloRuntime:
    def __init__(self, checkpoint: Path | None = None) -> None:
        if os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK") == "1":
            raise RuntimeError("CPU fallback must be disabled")
        import torch
        from ultralytics import YOLO

        if platform.system() != "Darwin" or not torch.backends.mps.is_available():
            raise RuntimeError("YOLO Runtime requires macOS with available MPS")
        checkpoint = (checkpoint if checkpoint is not None else selected_checkpoint()).resolve(strict=True)
        self.checkpoint = str(checkpoint)
        self.checkpoint_sha256 = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        self.model = YOLO(str(checkpoint))
        if self.model.task != "segment" or self.model.names != {RBC_CLASS_ID: RBC_CLASS_NAME}:
            raise RuntimeError("Checkpoint must be a single-class RBC segmentation model")
        self.model.to("mps")
        if next(self.model.model.parameters()).device.type != "mps":
            raise RuntimeError("Model was not loaded on MPS")
        self.lock = Lock()

    def _run_pass(self, oriented: Image.Image, scale: float, options: InferenceOptions) -> _Pass:
        """Tiled inference at one scale; detections are returned in source pixels."""
        width, height = oriented.size
        resampled = (oriented if scale == 1 else
                     oriented.resize((round(width * scale), round(height * scale)), Image.Resampling.BICUBIC))
        scale_x, scale_y = resampled.width / width, resampled.height / height
        detections: list[Detection] = []
        raw_count = invalid_count = 0
        warnings: set[str] = set()
        for tile in tiles_for_image(resampled.width, resampled.height):
            crop = resampled.crop((tile.x, tile.y, min(tile.x_max, resampled.width), min(tile.y_max, resampled.height)))
            result = self.model.predict(source=crop, device="mps", imgsz=TILE_SIZE,
                                        conf=options.confidence, iou=options.nms_iou,
                                        max_det=options.max_detections_per_tile,
                                        retina_masks=True, verbose=False, save=False)[0]
            boxes = result.boxes.xyxy.cpu().tolist()
            scores = result.boxes.conf.cpu().tolist()
            polygons = result.masks.xy if result.masks is not None else None
            raw_count += len(boxes)
            if len(boxes) >= options.max_detections_per_tile:
                warnings.add("TILE_DETECTION_LIMIT_REACHED")
            for index, (box, score) in enumerate(zip(boxes, scores)):
                candidate = global_detection(box, score, polygons[index] if polygons is not None else None,
                                             (tile.x, tile.y), crop.size, tile_id("image", tile))
                if candidate is not None:
                    candidate = rescale_detection(candidate, scale_x, scale_y, width, height)
                if candidate is None:
                    invalid_count += 1
                else:
                    detections.append(candidate)
                    if candidate.mask_polygon is None:
                        warnings.add("MASK_UNAVAILABLE_BBOX_GEOMETRY")
        final = suppress_contained(consolidate(detections, options.nms_iou), options.containment_threshold)
        return _Pass(scale, final, raw_count, invalid_count, len(detections) - len(final), frozenset(warnings))

    def _normalized_pass(self, oriented: Image.Image, options: InferenceOptions) -> tuple[_Pass, float | None, set[str]]:
        """Bring cells near the training size; images already in range keep a single pass."""
        limit = scale_limit(*oriented.size)
        best = self._run_pass(oriented, 1.0, options)
        estimated = estimate_cell_px(best.detections)
        if estimated is not None and estimated >= MIN_RELIABLE_CELL_PX:
            return best, estimated, set()
        for scale in PROBE_SCALES:
            if scale > limit:
                break
            probe = self._run_pass(oriented, scale, options)
            if len(probe.detections) > len(best.detections):
                best = probe
        estimated = estimate_cell_px(best.detections)
        if estimated is None:
            return best, None, {"CELL_SCALE_UNRESOLVED"}
        wanted = options.target_cell_px / estimated
        # Box sides are measured in source pixels, so a probe's blur cannot shift the target.
        scale = max(1.0, min(wanted, limit))
        notes = {"CELL_SCALE_LIMIT_REACHED"} if wanted > limit else set()
        if abs(scale - best.scale) > SCALE_REUSE_TOLERANCE * best.scale:
            final = self._run_pass(oriented, scale, options)
            if final.detections:
                best = final
        return best, estimated, notes

    def detect(self, image: Image.Image, options: InferenceOptions) -> DetectionResponse:
        oriented = ImageOps.exif_transpose(image).convert("RGB")
        width, height = oriented.size
        # Ultralytics keeps predictor state: concurrent calls must be serialized.
        with self.lock:
            selected, estimated, notes = self._normalized_pass(oriented, options)
        warnings = set(selected.warnings) | notes
        if selected.invalid_count:
            warnings.add("INVALID_GEOMETRY_DISCARDED")
        if not selected.detections:
            warnings.add("NO_DETECTIONS")
        return DetectionResponse(model_checkpoint=self.checkpoint, checkpoint_sha256=self.checkpoint_sha256,
                                 image_width=width, image_height=height, options=options,
                                 detections=selected.detections, raw_detection_count=selected.raw_count,
                                 invalid_detection_count=selected.invalid_count,
                                 consolidated_detection_count=selected.consolidated_count,
                                 final_detection_count=len(selected.detections),
                                 input_scale=selected.scale, estimated_cell_px=estimated,
                                 warnings=sorted(warnings))
