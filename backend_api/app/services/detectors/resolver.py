from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PIL import Image

from app.models.cell_detection import DetectionResult
from app.services.detectors import connected_components_v1, yolo26_seg_v1

DEFAULT_DETECTOR_KEY = "connected_components_v1"
_IMPLEMENTATIONS = {
    connected_components_v1.DETECTOR_KEY: connected_components_v1,
    yolo26_seg_v1.DETECTOR_KEY: yolo26_seg_v1,
}


@dataclass(frozen=True)
class Detector:
    key: str
    version: str
    algorithm_version: str
    profile_snapshot: Callable[[dict | None], dict]
    detect_image: Callable[[Image.Image, dict | None], DetectionResult]


def resolve_detector(key: str = DEFAULT_DETECTOR_KEY) -> Detector:
    """Resolve a versioned implementation; unknown detectors never fall back silently."""
    implementation = _IMPLEMENTATIONS.get(key)
    if implementation is None:
        raise ValueError(f"Unsupported cell detector: {key}")
    return Detector(
        key=implementation.DETECTOR_KEY,
        version=implementation.DETECTOR_VERSION,
        algorithm_version=implementation.ALGORITHM_VERSION,
        profile_snapshot=implementation.profile_snapshot,
        detect_image=implementation.detect_image,
    )
