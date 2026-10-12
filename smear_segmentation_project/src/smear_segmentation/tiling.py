"""Deterministic tiling for Full Smear RBC segmentation."""

from __future__ import annotations

from dataclasses import dataclass

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from malaria_split.sources.polygon_set import PolygonEntry


TILE_SIZE = 1024
TILE_OVERLAP = 256
TILE_STRIDE = TILE_SIZE - TILE_OVERLAP


@dataclass(frozen=True, slots=True)
class Tile:
    x: int
    y: int
    size: int = TILE_SIZE

    @property
    def x_max(self) -> int:
        return self.x + self.size

    @property
    def y_max(self) -> int:
        return self.y + self.size


def axis_starts(
    length: int,
    *,
    tile_size: int = TILE_SIZE,
    overlap: int = TILE_OVERLAP,
) -> tuple[int, ...]:
    """Return deterministic tile starts including the image's far edge."""

    if length <= 0:
        raise ValueError("length must be positive")

    if tile_size <= 0:
        raise ValueError("tile_size must be positive")

    if overlap < 0 or overlap >= tile_size:
        raise ValueError("overlap must satisfy 0 <= overlap < tile_size")

    if length <= tile_size:
        return (0,)

    stride = tile_size - overlap

    starts = list(range(0, length - tile_size + 1, stride))
    last = length - tile_size

    if starts[-1] != last:
        starts.append(last)

    return tuple(starts)


def tiles_for_image(
    width: int,
    height: int,
) -> tuple[Tile, ...]:
    """Return the deterministic tile grid for an image."""

    return tuple(
        Tile(x=x, y=y)
        for y in axis_starts(height)
        for x in axis_starts(width)
    )


def polygon_margin(
    polygon: PolygonEntry,
    tile: Tile,
) -> float | None:
    """
    Return the minimum border margin when the polygon is fully contained.

    Return None when any part of the polygon lies outside the tile.
    """

    xs = tuple(point[0] for point in polygon.points)
    ys = tuple(point[1] for point in polygon.points)

    x_min = min(xs)
    x_max = max(xs)
    y_min = min(ys)
    y_max = max(ys)

    if (
        x_min < tile.x
        or x_max > tile.x_max
        or y_min < tile.y
        or y_max > tile.y_max
    ):
        return None

    return min(
        x_min - tile.x,
        tile.x_max - x_max,
        y_min - tile.y,
        tile.y_max - y_max,
    )


def select_tile_for_polygon(
    polygon: PolygonEntry,
    tiles: tuple[Tile, ...],
) -> Tile:
    """
    Select exactly one complete tile for a polygon.

    Prefer the tile with the greatest minimum border margin.
    Resolve ties deterministically by top-most, then left-most tile.
    """

    candidates = []

    for tile in tiles:
        margin = polygon_margin(polygon, tile)

        if margin is not None:
            candidates.append((margin, tile))

    if not candidates:
        raise ValueError(
            f"No tile fully contains polygon {polygon.cell_id!r}"
        )

    _, selected = max(
        candidates,
        key=lambda item: (
            item[0],
            -item[1].y,
            -item[1].x,
        ),
    )

    return selected

def polygons_fully_contained_in_tile(
    polygons: tuple[PolygonEntry, ...],
    tile: Tile,
) -> tuple[PolygonEntry, ...]:
    """Return all polygons fully contained in a tile."""

    return tuple(
        polygon
        for polygon in polygons
        if polygon_margin(polygon, tile) is not None
    )

def tile_id(
    source_record_id: object,
    tile: Tile,
) -> str:
    """Return the deterministic identity of a materialized tile."""

    return (
        f"{source_record_id}"
        f"__x{tile.x:04d}"
        f"_y{tile.y:04d}"
    )

