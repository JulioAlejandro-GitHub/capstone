from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PIL import Image

from app.models.cell_detection import CellCrop, ConnectedComponent
from app.services.crops import bbox_crop_v1

DEFAULT_CROP_STRATEGY_KEY = "bbox_crop_v1"


@dataclass(frozen=True)
class CropStrategy:
    key: str
    crop_image: Callable[[Image.Image, tuple[ConnectedComponent, ...], int], tuple[CellCrop, ...]]


def resolve_crop_strategy(key: str = DEFAULT_CROP_STRATEGY_KEY) -> CropStrategy:
    """Resolve the crop implementation separately from the detector."""
    if key != bbox_crop_v1.CROP_STRATEGY_KEY:
        raise ValueError(f"Unsupported cell crop strategy: {key}")
    return CropStrategy(key=bbox_crop_v1.CROP_STRATEGY_KEY, crop_image=bbox_crop_v1.crop_image)
