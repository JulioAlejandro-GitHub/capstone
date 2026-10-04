from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.models.cell_detection import DetectorInputError, ImageDetectionResult
from app.services.detectors.resolver import Detector, resolve_detector
from app.services.crops.resolver import CropStrategy, resolve_crop_strategy


def detect_image(
    image: Image.Image,
    profile: dict | None = None,
    *,
    detector: Detector | None = None,
    crop_strategy: CropStrategy | None = None,
) -> ImageDetectionResult:
    """Run CELL DETECTION then CELL CROP; keep the persistence output unchanged."""
    detector = detector or resolve_detector()
    crop_strategy = crop_strategy or resolve_crop_strategy()
    selected = detector.profile_snapshot(profile)
    detected = detector.detect_image(image, selected)
    oriented = ImageOps.exif_transpose(image)
    oriented.load()
    crops = crop_strategy.crop_image(
        oriented, detected.components, int(selected["crop_padding_px"])
    )
    return ImageDetectionResult(
        raw_width_px=detected.raw_width_px,
        raw_height_px=detected.raw_height_px,
        oriented_width_px=detected.oriented_width_px,
        oriented_height_px=detected.oriented_height_px,
        threshold_value=detected.threshold_value,
        components=detected.components,
        warnings=detected.warnings,
        crops=crops,
    )


def detect_path(
    path: Path,
    *,
    expected_sha256: str,
    expected_width_px: int,
    expected_height_px: int,
    expected_file_size_bytes: int,
    profile: dict | None = None,
    integrity_preverified: bool = False,
    detector: Detector | None = None,
    crop_strategy: CropStrategy | None = None,
) -> ImageDetectionResult:
    """Verify a frozen source, then detect on its EXIF-oriented full raster."""

    try:
        path.stat()
        if not path.is_file() or path.is_symlink():
            raise DetectorInputError("SOURCE_NOT_REGULAR", "La imagen original no es regular.")
        if not integrity_preverified:
            from app.services.local_storage import (
                StorageChecksumMismatchError,
                StorageError,
                StorageSizeMismatchError,
                verify_regular_file,
            )

            try:
                verify_regular_file(
                    path,
                    expected_size_bytes=expected_file_size_bytes,
                    expected_sha256=expected_sha256,
                )
            except StorageSizeMismatchError as exc:
                raise DetectorInputError(
                    "FILE_SIZE_MISMATCH", "El tamaño del original cambió."
                ) from exc
            except StorageChecksumMismatchError as exc:
                raise DetectorInputError(
                    "CHECKSUM_MISMATCH", "El checksum del original cambió."
                ) from exc
            except StorageError as exc:
                raise DetectorInputError(
                    "SOURCE_NOT_REGULAR", "La imagen original no es regular."
                ) from exc
        with Image.open(path) as source:
            if source.size != (expected_width_px, expected_height_px):
                raise DetectorInputError("DIMENSIONS_MISMATCH", "Las dimensiones del original cambiaron.")
            source.load()
            return detect_image(
                source, profile, detector=detector, crop_strategy=crop_strategy
            )
    except DetectorInputError:
        raise
    except (FileNotFoundError, UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise DetectorInputError(
            "SOURCE_DECODE_FAILED", "La imagen original no pudo decodificarse."
        ) from exc
