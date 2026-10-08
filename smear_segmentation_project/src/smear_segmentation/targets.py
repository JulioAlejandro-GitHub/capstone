"""Target semantics for Full Smear RBC segmentation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from malaria_split.sources.polygon_set import PolygonAnnotation, PolygonEntry


RBC_SOURCE_LABELS = frozenset({
    "Uninfected",
    "Parasitized",
})

RBC_CLASS_ID = 0
RBC_CLASS_NAME = "RBC"


def select_rbc_polygons(
    annotation: PolygonAnnotation,
) -> tuple[PolygonEntry, ...]:
    """Return source polygons that belong to the RBC detector target."""

    return tuple(
        polygon
        for polygon in annotation.polygons
        if polygon.label in RBC_SOURCE_LABELS
    )

def polygon_to_normalized_tile_points(
    polygon: PolygonEntry,
    *,
    tile_x: int,
    tile_y: int,
    tile_size: int,
) -> tuple[tuple[float, float], ...]:
    """Convert a fully contained source polygon to normalized tile coordinates."""

    if tile_size <= 0:
        raise ValueError("tile_size must be positive")

    normalized = tuple(
        (
            (x - tile_x) / tile_size,
            (y - tile_y) / tile_size,
        )
        for x, y in polygon.points
    )

    if any(
        x < 0.0 or x > 1.0 or y < 0.0 or y > 1.0
        for x, y in normalized
    ):
        raise ValueError(
            f"Polygon {polygon.cell_id!r} is not fully contained in the tile"
        )

    return normalized

def serialize_yolo_segmentation_label(
    points: tuple[tuple[float, float], ...],
    *,
    class_id: int = RBC_CLASS_ID,
    precision: int = 8,
) -> str:
    """Serialize one normalized polygon as one YOLO segmentation label."""

    if class_id < 0:
        raise ValueError("class_id must be non-negative")

    if precision < 1:
        raise ValueError("precision must be positive")

    if len(points) < 3:
        raise ValueError("A segmentation polygon requires at least 3 points")

    if any(
        x < 0.0 or x > 1.0 or y < 0.0 or y > 1.0
        for x, y in points
    ):
        raise ValueError("Normalized polygon coordinates must be within [0, 1]")

    coordinates = " ".join(
        f"{value:.{precision}f}"
        for point in points
        for value in point
    )

    return f"{class_id} {coordinates}"






