from __future__ import annotations

import io

from PIL import Image

from app.models.cell_detection import (
    CellCrop,
    ComponentStatus,
    ConnectedComponent,
    DetectorInputError,
)

CROP_STRATEGY_KEY = "bbox_crop_v1"

_PNG_PIXEL_PRESERVING_MODES = {
    "1", "L", "LA", "P", "RGB", "RGBA", "I;16", "I;16L", "I;16B",
}


def crop_image(
    oriented: Image.Image,
    components: tuple[ConnectedComponent, ...],
    padding_px: int,
) -> tuple[CellCrop, ...]:
    """Crop accepted boxes on the original EXIF-oriented raster, without conversion."""
    width, height = oriented.size
    crops: list[CellCrop] = []
    if components and any(
        component.component_status == ComponentStatus.ACCEPTED
        for component in components
    ) and oriented.mode not in _PNG_PIXEL_PRESERVING_MODES:
        raise DetectorInputError(
            "UNSUPPORTED_CROP_MODE",
            "El modo de píxel original no admite un crop PNG sin conversión.",
        )
    for component in components:
        if component.component_status != ComponentStatus.ACCEPTED:
            continue
        padded = component.bbox.padded(padding_px, width, height)
        crop_image = oriented.crop(
            (padded.x, padded.y, padded.right, padded.bottom)
        )
        output = io.BytesIO()
        crop_image.save(output, format="PNG", optimize=False)
        crops.append(
            CellCrop(
                component_index=component.component_index,
                bbox=padded,
                padding_px=padding_px,
                png_bytes=output.getvalue(),
                width_px=padded.width,
                height_px=padded.height,
            )
        )
    return tuple(crops)
