from __future__ import annotations

import io
import math
from collections import deque
from copy import deepcopy
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError

from app.models.cell_detection import (
    BoundingBox,
    CellCrop,
    ComponentStatus,
    ConnectedComponent,
    ImageDetectionResult,
)


DETECTOR_KEY = "connected_components_v1"
DETECTOR_VERSION = "1.0.0"
ALGORITHM_VERSION = "pillow-connected-components-1.0.0"
COORDINATE_SPACE = "original_image_pixels"

_PROFILE = {
    "detector_key": DETECTOR_KEY,
    "detector_version": DETECTOR_VERSION,
    "algorithm_version": ALGORITHM_VERSION,
    "threshold_method": "otsu_dark_foreground",
    "foreground_polarity": "dark",
    "blur_kernel": 3,
    "morphology_kernel": 3,
    "morphology_iterations": 1,
    "minimum_component_area_px": 64,
    "maximum_component_area_px": 250_000,
    "minimum_width_px": 6,
    "minimum_height_px": 6,
    "minimum_circularity": 0.05,
    "minimum_solidity": 0.20,
    "reject_border_components": True,
    "crop_padding_px": 4,
    # The review overlay deliberately loads at most 500 candidates for the
    # current image. Keeping the accepted-candidate cap aligned with that
    # contract guarantees crop/box synchronization for every accepted result.
    "maximum_components_per_image": 500,
    "component_separation": "none",
    "connectivity": 8,
    "coordinate_space": COORDINATE_SPACE,
    "coordinate_origin": "top_left",
    "bbox_format": "xywh",
    "orientation_policy": "exif_transpose",
    "resampling": "none",
}

_FIXED_PROFILE_FIELDS = {
    "detector_key",
    "detector_version",
    "algorithm_version",
    "threshold_method",
    "foreground_polarity",
    "component_separation",
    "coordinate_space",
    "coordinate_origin",
    "bbox_format",
    "orientation_policy",
    "resampling",
}

_PNG_PIXEL_PRESERVING_MODES = {
    "1", "L", "LA", "P", "RGB", "RGBA", "I;16", "I;16L", "I;16B",
}


class DetectorInputError(ValueError):
    """Raised when a frozen source image cannot be processed safely."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def profile_snapshot(overrides: dict | None = None) -> dict:
    profile = deepcopy(_PROFILE)
    if overrides:
        unknown = set(overrides).difference(profile)
        if unknown:
            raise ValueError(f"Unknown detector profile fields: {sorted(unknown)}")
        changed_fixed = sorted(
            key
            for key in _FIXED_PROFILE_FIELDS.intersection(overrides)
            if overrides[key] != _PROFILE[key]
        )
        if changed_fixed:
            raise ValueError(
                f"Fixed detector profile fields cannot be overridden: {changed_fixed}"
            )
        profile.update(overrides)
    _validate_profile(profile)
    return profile


def _validate_profile(profile: dict) -> None:
    odd_positive = ("blur_kernel", "morphology_kernel")
    if any(int(profile[key]) <= 0 or int(profile[key]) % 2 == 0 for key in odd_positive):
        raise ValueError("Blur and morphology kernels must be positive odd integers")
    positive = (
        "minimum_component_area_px",
        "maximum_component_area_px",
        "minimum_width_px",
        "minimum_height_px",
        "maximum_components_per_image",
    )
    if any(int(profile[key]) <= 0 for key in positive):
        raise ValueError("Detector geometric limits must be positive")
    if profile["minimum_component_area_px"] > profile["maximum_component_area_px"]:
        raise ValueError("Minimum component area cannot exceed maximum")
    if int(profile["morphology_iterations"]) < 0:
        raise ValueError("Morphology iterations cannot be negative")
    if int(profile["crop_padding_px"]) < 0:
        raise ValueError("Crop padding cannot be negative")
    if int(profile["connectivity"]) not in {4, 8}:
        raise ValueError("Connectivity must be 4 or 8")
    if not 0 <= float(profile["minimum_circularity"]) <= 1:
        raise ValueError("Minimum circularity must be in [0, 1]")
    if not 0 <= float(profile["minimum_solidity"]) <= 1:
        raise ValueError("Minimum solidity must be in [0, 1]")


def _otsu_threshold(histogram: list[int], total: int) -> int:
    weighted_total = sum(index * count for index, count in enumerate(histogram))
    background_weight = 0
    background_sum = 0
    maximum_variance = -1.0
    selected = 0
    for threshold, count in enumerate(histogram):
        background_weight += count
        if background_weight == 0:
            continue
        foreground_weight = total - background_weight
        if foreground_weight == 0:
            break
        background_sum += threshold * count
        background_mean = background_sum / background_weight
        foreground_mean = (weighted_total - background_sum) / foreground_weight
        variance = background_weight * foreground_weight * (
            background_mean - foreground_mean
        ) ** 2
        if variance > maximum_variance:
            maximum_variance = variance
            selected = threshold
    return selected


def _foreground_mask(luminance: Image.Image, profile: dict) -> tuple[bytearray, int | None]:
    histogram = luminance.histogram()[:256]
    populated = [index for index, count in enumerate(histogram) if count]
    if len(populated) < 2 or populated[-1] - populated[0] < 2:
        return bytearray(luminance.width * luminance.height), None
    threshold = _otsu_threshold(histogram, luminance.width * luminance.height)
    mask = luminance.point(lambda value: 255 if value <= threshold else 0, mode="L")
    kernel = int(profile["morphology_kernel"])
    for _ in range(int(profile["morphology_iterations"])):
        # Binary opening removes isolated dark noise; closing fills small gaps.
        mask = mask.filter(ImageFilter.MinFilter(kernel))
        mask = mask.filter(ImageFilter.MaxFilter(kernel))
        mask = mask.filter(ImageFilter.MaxFilter(kernel))
        mask = mask.filter(ImageFilter.MinFilter(kernel))
    return bytearray(mask.tobytes()), threshold


def _convex_hull(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    unique = sorted(set(points))
    if len(unique) <= 1:
        return unique

    def cross(origin, first, second):
        return (
            (first[0] - origin[0]) * (second[1] - origin[1])
            - (first[1] - origin[1]) * (second[0] - origin[0])
        )

    lower: list[tuple[int, int]] = []
    for point in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper: list[tuple[int, int]] = []
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def _polygon_area(points: list[tuple[int, int]]) -> float:
    if len(points) < 3:
        return 0.0
    return abs(
        sum(
            x1 * y2 - x2 * y1
            for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1])
        )
    ) / 2


def _solidity(boundary: list[tuple[int, int]], area: int, bbox: BoundingBox) -> float:
    # Pixel centres underestimate a convex hull at small scales. Expanding the
    # hull estimate by half a pixel preserves a bounded, deterministic metric.
    hull_area = _polygon_area(_convex_hull(boundary))
    estimate = max(float(area), hull_area + (bbox.width + bbox.height) / 2)
    return min(1.0, area / estimate) if estimate else 1.0


def _rejection_codes(
    *,
    area: int,
    bbox: BoundingBox,
    circularity: float,
    solidity: float,
    touches_border: bool,
    profile: dict,
) -> list[str]:
    codes: list[str] = []
    if touches_border and profile["reject_border_components"]:
        codes.append("BORDER_COMPONENT")
    if area < profile["minimum_component_area_px"]:
        codes.append("COMPONENT_AREA_BELOW_MINIMUM")
    if area > profile["maximum_component_area_px"]:
        codes.append("COMPONENT_AREA_ABOVE_MAXIMUM")
    if bbox.width < profile["minimum_width_px"]:
        codes.append("COMPONENT_WIDTH_BELOW_MINIMUM")
    if bbox.height < profile["minimum_height_px"]:
        codes.append("COMPONENT_HEIGHT_BELOW_MINIMUM")
    if circularity < profile["minimum_circularity"]:
        codes.append("COMPONENT_CIRCULARITY_BELOW_MINIMUM")
    if solidity < profile["minimum_solidity"]:
        codes.append("COMPONENT_SOLIDITY_BELOW_MINIMUM")
    return codes


def _components(mask: bytearray, width: int, height: int, profile: dict) -> list[ConnectedComponent]:
    visited = bytearray(width * height)
    neighbors = (
        ((-1, 0), (1, 0), (0, -1), (0, 1))
        if profile["connectivity"] == 4
        else (
            (-1, -1), (0, -1), (1, -1),
            (-1, 0), (1, 0),
            (-1, 1), (0, 1), (1, 1),
        )
    )
    found: list[ConnectedComponent] = []
    accepted_count = 0
    for seed in range(width * height):
        if not mask[seed] or visited[seed]:
            continue
        queue = deque([seed])
        visited[seed] = 1
        area = 0
        sum_x = 0
        sum_y = 0
        minimum_x = maximum_x = seed % width
        minimum_y = maximum_y = seed // width
        perimeter = 0
        boundary: list[tuple[int, int]] = []
        while queue:
            index = queue.popleft()
            y, x = divmod(index, width)
            area += 1
            sum_x += x
            sum_y += y
            minimum_x = min(minimum_x, x)
            maximum_x = max(maximum_x, x)
            minimum_y = min(minimum_y, y)
            maximum_y = max(maximum_y, y)
            exposed = 0
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = x + dx, y + dy
                if nx < 0 or nx >= width or ny < 0 or ny >= height:
                    exposed += 1
                elif not mask[ny * width + nx]:
                    exposed += 1
            perimeter += exposed
            if exposed:
                boundary.append((x, y))
            for dx, dy in neighbors:
                nx, ny = x + dx, y + dy
                if nx < 0 or nx >= width or ny < 0 or ny >= height:
                    continue
                neighbor = ny * width + nx
                if mask[neighbor] and not visited[neighbor]:
                    visited[neighbor] = 1
                    queue.append(neighbor)
        bbox = BoundingBox(
            minimum_x,
            minimum_y,
            maximum_x - minimum_x + 1,
            maximum_y - minimum_y + 1,
        )
        circularity = min(1.0, 4 * math.pi * area / (perimeter * perimeter)) if perimeter else 1.0
        solidity = _solidity(boundary, area, bbox)
        touches_border = (
            bbox.x == 0 or bbox.y == 0 or bbox.right == width or bbox.bottom == height
        )
        codes = _rejection_codes(
            area=area,
            bbox=bbox,
            circularity=circularity,
            solidity=solidity,
            touches_border=touches_border,
            profile=profile,
        )
        if not codes and accepted_count >= profile["maximum_components_per_image"]:
            codes.append("MAXIMUM_COMPONENTS_EXCEEDED")
        if not codes:
            accepted_count += 1
        status = (
            ComponentStatus.REJECTED_BY_FILTER if codes else ComponentStatus.ACCEPTED
        )
        found.append(
            ConnectedComponent(
                component_index=len(found) + 1,
                bbox=bbox,
                centroid_x=sum_x / area,
                centroid_y=sum_y / area,
                area_px=area,
                perimeter_px=float(perimeter),
                circularity=circularity,
                solidity=solidity,
                touches_border=touches_border,
                component_status=status,
                rejection_code=codes[0] if codes else None,
                rejection_codes=tuple(codes),
                detector_score=min(1.0, max(0.0, (circularity + solidity) / 2)),
            )
        )
    return found


def detect_image(image: Image.Image, profile: dict | None = None) -> ImageDetectionResult:
    """Detect candidates in a Pillow image without touching a database or filesystem."""

    selected = profile_snapshot(profile)
    raw_width, raw_height = image.size
    oriented = ImageOps.exif_transpose(image)
    oriented.load()
    analysis_rgb = oriented.convert("RGB")
    width, height = analysis_rgb.size
    luminance = ImageOps.grayscale(analysis_rgb)
    blur_kernel = int(selected["blur_kernel"])
    if blur_kernel > 1:
        luminance = luminance.filter(ImageFilter.GaussianBlur((blur_kernel - 1) / 2))
    mask, threshold = _foreground_mask(luminance, selected)
    components = _components(mask, width, height, selected)
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
        padded = component.bbox.padded(
            int(selected["crop_padding_px"]), width, height
        )
        crop_image = oriented.crop(
            (padded.x, padded.y, padded.right, padded.bottom)
        )
        output = io.BytesIO()
        crop_image.save(output, format="PNG", optimize=False)
        crops.append(
            CellCrop(
                component_index=component.component_index,
                bbox=padded,
                padding_px=int(selected["crop_padding_px"]),
                png_bytes=output.getvalue(),
                width_px=padded.width,
                height_px=padded.height,
            )
        )
    warnings: list[str] = []
    if not any(c.component_status == ComponentStatus.ACCEPTED for c in components):
        warnings.append("NO_ACCEPTED_COMPONENTS")
    if any(c.rejection_code == "MAXIMUM_COMPONENTS_EXCEEDED" for c in components):
        warnings.append("MAXIMUM_COMPONENTS_REACHED")
    return ImageDetectionResult(
        raw_width_px=raw_width,
        raw_height_px=raw_height,
        oriented_width_px=width,
        oriented_height_px=height,
        threshold_value=threshold,
        components=tuple(components),
        crops=tuple(crops),
        warnings=tuple(warnings),
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
) -> ImageDetectionResult:
    """Verify a frozen source, then detect on its EXIF-oriented full raster."""

    try:
        info = path.stat()
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
            return detect_image(source, profile)
    except DetectorInputError:
        raise
    except (FileNotFoundError, UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise DetectorInputError(
            "SOURCE_DECODE_FAILED", "La imagen original no pudo decodificarse."
        ) from exc
