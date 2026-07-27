from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.config import Settings, get_settings


FORMAT_INFO = {
    "JPEG": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "TIFF": ("image/tiff", "tif"),
}


class ImageValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ImageMetadata:
    detected_format: str
    mime_type: str
    extension: str
    width_px: int
    height_px: int
    bit_depth: int | None
    channel_count: int | None
    color_space: str | None
    orientation: str | None


def _bit_depth(mode: str) -> int | None:
    if mode in {"1"}:
        return 1
    if mode in {"L", "P", "RGB", "RGBA", "CMYK", "YCbCr", "LAB", "HSV"}:
        return 8
    if mode.startswith("I;16"):
        return 16
    if mode in {"I", "F"}:
        return 32
    return None


def validate_image(path: Path, settings: Settings | None = None) -> ImageMetadata:
    settings = settings or get_settings()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            Image.MAX_IMAGE_PIXELS = settings.max_image_pixels
            with Image.open(path) as image:
                detected = (image.format or "").upper()
                if detected not in settings.allowed_microscopy_formats or detected not in FORMAT_INFO:
                    raise ImageValidationError("Formato no permitido.")
                frames = getattr(image, "n_frames", 1)
                if frames != 1 or bool(getattr(image, "is_animated", False)):
                    raise ImageValidationError("Solo se permiten imágenes de un frame.")
                width, height = image.size
                if width <= 0 or height <= 0 or width * height > settings.max_image_pixels:
                    raise ImageValidationError("Dimensiones fuera de límite.")
                image.load()
                orientation_value = image.getexif().get(274) if detected == "JPEG" else None
                bands = image.getbands()
                mime, extension = FORMAT_INFO[detected]
                return ImageMetadata(
                    detected, mime, extension, width, height, _bit_depth(image.mode),
                    len(bands) if bands else None, image.mode or None,
                    str(orientation_value) if orientation_value is not None else None,
                )
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise ImageValidationError("Imagen corrupta, truncada o insegura.") from exc
