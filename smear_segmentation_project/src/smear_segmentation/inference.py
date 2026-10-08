"""Local MPS inference; no datasets, persistence or classifier dependencies."""
from __future__ import annotations

import hashlib
import math
import os
import platform
from pathlib import Path
from threading import Lock
from typing import Literal

import numpy as np
from PIL import Image, ImageOps
from pydantic import BaseModel, ConfigDict, Field

from .targets import RBC_CLASS_ID, RBC_CLASS_NAME
from .tiling import TILE_OVERLAP, TILE_SIZE, tile_id, tiles_for_image

DETECTOR_KEY = "yolo26_seg_v1"
DETECTOR_VERSION = "1.0.0"
RUNTIME_VERSION = "1.0.0"
ALGORITHM_VERSION = "yolo26-seg-tiling-global-nms-1.0.0"
DEFAULT_CHECKPOINT = Path(__file__).resolve().parents[2] / "runs/yolo26_seg/yolo26n_rbc_1024_v1/weights/best.pt"


class InferenceOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    confidence: float = Field(default=0.25, gt=0, le=1)
    nms_iou: float = Field(default=0.7, gt=0, le=1)
    max_detections_per_tile: int = Field(default=1000, ge=1, le=2000)


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
    warnings: list[str]


def box_iou(first: Box, second: Box) -> float:
    width = max(0, min(first.x + first.width, second.x + second.width) - max(first.x, second.x))
    height = max(0, min(first.y + first.height, second.y + second.height) - max(first.y, second.y))
    intersection = width * height
    return intersection / (first.width * first.height + second.width * second.height - intersection)


def consolidate(detections: list[Detection], iou: float) -> list[Detection]:
    """Stable greedy global box NMS; proximity alone never removes a cell."""
    ordered = sorted(detections, key=lambda d: (-d.confidence, d.tile_id, d.bbox.y, d.bbox.x, d.bbox.width, d.bbox.height))
    kept: list[Detection] = []
    for candidate in ordered:
        if all(box_iou(candidate.bbox, previous.bbox) <= iou for previous in kept):
            kept.append(candidate)
    return kept


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


class YoloRuntime:
    def __init__(self, checkpoint: Path = DEFAULT_CHECKPOINT) -> None:
        if os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK") == "1":
            raise RuntimeError("CPU fallback must be disabled")
        import torch
        from ultralytics import YOLO

        if platform.system() != "Darwin" or not torch.backends.mps.is_available():
            raise RuntimeError("YOLO Runtime requires macOS with available MPS")
        checkpoint = checkpoint.resolve(strict=True)
        self.checkpoint = str(checkpoint)
        self.checkpoint_sha256 = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        self.model = YOLO(str(checkpoint))
        if self.model.task != "segment" or self.model.names != {RBC_CLASS_ID: RBC_CLASS_NAME}:
            raise RuntimeError("Checkpoint must be a single-class RBC segmentation model")
        self.model.to("mps")
        if next(self.model.model.parameters()).device.type != "mps":
            raise RuntimeError("Model was not loaded on MPS")
        self.lock = Lock()

    def detect(self, image: Image.Image, options: InferenceOptions) -> DetectionResponse:
        oriented = ImageOps.exif_transpose(image).convert("RGB")
        width, height = oriented.size
        detections: list[Detection] = []
        raw_count = invalid_count = 0
        warnings: set[str] = set()
        # Ultralytics keeps predictor state: concurrent calls must be serialized.
        with self.lock:
            for tile in tiles_for_image(width, height):
                crop = oriented.crop((tile.x, tile.y, min(tile.x_max, width), min(tile.y_max, height)))
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
                    if candidate is None:
                        invalid_count += 1
                    else:
                        detections.append(candidate)
                        if candidate.mask_polygon is None:
                            warnings.add("MASK_UNAVAILABLE_BBOX_GEOMETRY")
        final = consolidate(detections, options.nms_iou)
        if invalid_count:
            warnings.add("INVALID_GEOMETRY_DISCARDED")
        if not final:
            warnings.add("NO_DETECTIONS")
        return DetectionResponse(model_checkpoint=self.checkpoint, checkpoint_sha256=self.checkpoint_sha256,
                                 image_width=width, image_height=height, options=options, detections=final,
                                 raw_detection_count=raw_count, invalid_detection_count=invalid_count,
                                 consolidated_detection_count=len(detections) - len(final),
                                 final_detection_count=len(final), warnings=sorted(warnings))
