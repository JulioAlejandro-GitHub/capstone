from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ComponentStatus(StrEnum):
    CANDIDATE = "candidate"
    ACCEPTED = "accepted"
    REJECTED_BY_FILTER = "rejected_by_filter"


class ReviewDecision(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_ATTENTION = "needs_attention"
    COMMENT_ONLY = "comment_only"


@dataclass(frozen=True)
class BoundingBox:
    """Integer xywh box in the top-left-origin, EXIF-oriented source raster."""

    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def padded(self, padding: int, image_width: int, image_height: int) -> "BoundingBox":
        left = max(0, self.x - padding)
        top = max(0, self.y - padding)
        right = min(image_width, self.right + padding)
        bottom = min(image_height, self.bottom + padding)
        return BoundingBox(left, top, right - left, bottom - top)

    def is_within(self, image_width: int, image_height: int) -> bool:
        return (
            self.x >= 0
            and self.y >= 0
            and self.width > 0
            and self.height > 0
            and self.right <= image_width
            and self.bottom <= image_height
        )


@dataclass(frozen=True)
class ConnectedComponent:
    component_index: int
    bbox: BoundingBox
    centroid_x: float
    centroid_y: float
    area_px: int
    perimeter_px: float
    circularity: float
    solidity: float
    touches_border: bool
    component_status: ComponentStatus
    rejection_code: str | None
    rejection_codes: tuple[str, ...]
    detector_score: float


@dataclass(frozen=True)
class CellCrop:
    component_index: int
    bbox: BoundingBox
    padding_px: int
    png_bytes: bytes
    width_px: int
    height_px: int


@dataclass(frozen=True)
class ImageDetectionResult:
    raw_width_px: int
    raw_height_px: int
    oriented_width_px: int
    oriented_height_px: int
    threshold_value: int | None
    components: tuple[ConnectedComponent, ...]
    crops: tuple[CellCrop, ...]
    warnings: tuple[str, ...]
