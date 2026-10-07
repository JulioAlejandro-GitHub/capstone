"""Materialization model for the YOLO RBC tile dataset."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from smear_segmentation.tiling import Tile, tile_id

from PIL import Image

from malaria_split.sources.polygon_set import PolygonEntry

from smear_segmentation.targets import (
    polygon_to_normalized_tile_points,
    serialize_yolo_segmentation_label,
)
from smear_segmentation.tiling import (
    Tile,
    polygons_fully_contained_in_tile,
    tile_id,
    tiles_for_image,
)


@dataclass(frozen=True, slots=True)
class MaterializedTile:
    source_record_id: UUID
    split: str
    source_image_path: Path
    tile: Tile

    @property
    def id(self) -> str:
        return tile_id(
            self.source_record_id,
            self.tile,
        )

    @property
    def image_relative_path(self) -> Path:
        return Path("images") / self.split / f"{self.id}.jpg"

    @property
    def label_relative_path(self) -> Path:
        return Path("labels") / self.split / f"{self.id}.txt"

@dataclass(frozen=True, slots=True)
class SmearMaterializationInput:
    source_record_id: UUID
    split: str
    source_image_path: Path
    polygons: tuple[PolygonEntry, ...]
    image_width: int
    image_height: int

def crop_tile_image(
    source_image: Image.Image,
    tile: Tile,
) -> Image.Image:
    """Crop one tile from a Full Smear image."""

    if tile.x < 0 or tile.y < 0:
        raise ValueError("Tile origin must be non-negative")

    if (
        tile.x_max > source_image.width
        or tile.y_max > source_image.height
    ):
        raise ValueError(
            f"Tile exceeds source image bounds: "
            f"tile=({tile.x}, {tile.y}, {tile.x_max}, {tile.y_max}), "
            f"image=({source_image.width}, {source_image.height})"
        )

    return source_image.crop(
        (
            tile.x,
            tile.y,
            tile.x_max,
            tile.y_max,
        )
    )

def build_tile_labels(
    polygons: tuple[PolygonEntry, ...],
    tile: Tile,
) -> tuple[str, ...]:
    """Build YOLO-seg labels for all complete polygons visible in a tile."""

    visible_polygons = polygons_fully_contained_in_tile(
        polygons,
        tile,
    )

    return tuple(
        serialize_yolo_segmentation_label(
            polygon_to_normalized_tile_points(
                polygon,
                tile_x=tile.x,
                tile_y=tile.y,
                tile_size=tile.size,
            )
        )
        for polygon in visible_polygons
    )

def write_materialized_tile(
    item: MaterializedTile,
    source_image: Image.Image,
    labels: tuple[str, ...],
    output_root: Path,
) -> tuple[Path, Path]:
    """Write one tile image and its YOLO-seg label file."""

    image_path = output_root / item.image_relative_path
    label_path = output_root / item.label_relative_path

    image_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    label_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    cropped = crop_tile_image(
        source_image,
        item.tile,
    )

    cropped.save(
        image_path,
        format="JPEG",
        quality=95,
    )

    label_text = (
        "\n".join(labels) + "\n"
        if labels
        else ""
    )

    label_path.write_text(
        label_text,
        encoding="utf-8",
    )

    return image_path, label_path

def materialize_smear(
    *,
    source_record_id: UUID,
    split: str,
    source_image_path: Path,
    polygons: tuple[PolygonEntry, ...],
    image_width: int,
    image_height: int,
    output_root: Path,
) -> tuple[MaterializedTile, ...]:
    """Materialize all tiles and YOLO-seg labels for one Full Smear."""

    items = []

    with Image.open(source_image_path) as source_image:
        source_image.load()

        if source_image.size != (image_width, image_height):
            raise ValueError(
                f"Source image dimensions differ from governed dimensions: "
                f"actual={source_image.size}, "
                f"expected={(image_width, image_height)}"
            )

        for tile in tiles_for_image(
            image_width,
            image_height,
        ):
            item = MaterializedTile(
                source_record_id=source_record_id,
                split=split,
                source_image_path=source_image_path,
                tile=tile,
            )

            labels = build_tile_labels(
                polygons,
                tile,
            )

            write_materialized_tile(
                item,
                source_image,
                labels,
                output_root,
            )

            items.append(item)

    return tuple(items)

def materialize_dataset(
    records: tuple[SmearMaterializationInput, ...],
    *,
    output_root: Path,
) -> tuple[MaterializedTile, ...]:
    """Materialize a governed collection of Full Smear records."""

    items = []

    for record in records:
        items.extend(
            materialize_smear(
                source_record_id=record.source_record_id,
                split=record.split,
                source_image_path=record.source_image_path,
                polygons=record.polygons,
                image_width=record.image_width,
                image_height=record.image_height,
                output_root=output_root,
            )
        )

    return tuple(items)

