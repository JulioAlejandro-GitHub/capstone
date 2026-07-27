from __future__ import annotations

import hashlib
import math
import statistics
from pathlib import Path

from PIL import Image, ImageOps

from app.services.image_validation import validate_image
from app.services.local_storage import LocalStorage, StorageError


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _entropy(values: list[float], bins: int = 256) -> float:
    histogram = [0] * bins
    for value in values:
        histogram[min(bins - 1, int(value * bins))] += 1
    total = len(values)
    return -sum((count / total) * math.log2(count / total) for count in histogram if count)


def _focus(values: list[float], width: int, height: int) -> tuple[float, float]:
    laplacian, gradients = [], []
    for y in range(1, height - 1):
        row = y * width
        for x in range(1, width - 1):
            index = row + x
            center = values[index]
            laplacian.append(values[index - 1] + values[index + 1] + values[index - width] + values[index + width] - 4 * center)
            gx = values[index + 1] - values[index - 1]
            gy = values[index + width] - values[index - width]
            gradients.append(gx * gx + gy * gy)
    return (statistics.pvariance(laplacian) if laplacian else 0.0,
            statistics.fmean(gradients) if gradients else 0.0)


def _border_and_field(values: list[float], width: int, height: int, dark: float) -> tuple[float, float]:
    thickness = max(1, round(min(width, height) * 0.05))
    border = [values[y * width + x] for y in range(height) for x in range(width)
              if x < thickness or x >= width - thickness or y < thickness or y >= height - thickness]
    border_ratio = sum(value <= dark for value in border) / len(border)
    usable = sum(value > dark for value in values) / len(values)
    return border_ratio, usable


def _codes(metrics: dict, profile: dict) -> tuple[list[str], list[str]]:
    warnings, failures = [], []
    if metrics["width_px"] < profile["minimum_width"] or metrics["height_px"] < profile["minimum_height"]:
        failures.append("DIMENSIONS_BELOW_MINIMUM")
    if metrics["pixel_count"] < profile["minimum_pixel_count"]:
        failures.append("PIXEL_COUNT_BELOW_MINIMUM")
    rules = (
        ("dark_pixel_ratio", "maximum_dark_ratio", "EXPOSURE_DARK"),
        ("bright_pixel_ratio", "maximum_bright_ratio", "EXPOSURE_BRIGHT"),
        ("near_black_border_ratio", "maximum_black_border", "BLACK_BORDER"),
    )
    for metric, prefix, code in rules:
        if metrics[metric] >= profile[f"{prefix}_fail"]: failures.append(code)
        elif metrics[metric] >= profile[f"{prefix}_warning"]: warnings.append(code)
    minima = (
        ("contrast_p95_p05", "minimum_contrast", "LOW_CONTRAST"),
        ("entropy_bits", "minimum_entropy", "LOW_ENTROPY"),
        ("usable_field_ratio", "minimum_usable_field", "LOW_USABLE_FIELD"),
    )
    for metric, prefix, code in minima:
        if metrics[metric] < profile[f"{prefix}_fail"]: failures.append(code)
        elif metrics[metric] < profile[f"{prefix}_warning"]: warnings.append(code)
    for metric, prefix, code in (
        ("laplacian_variance", "minimum_laplacian", "LOW_LAPLACIAN_FOCUS"),
        ("tenengrad_mean", "minimum_tenengrad", "LOW_TENENGRAD_FOCUS"),
    ):
        if metrics[metric] < profile[f"{prefix}_warning"]: warnings.append(code)
    return sorted(set(warnings)), sorted(set(failures))


def assess_image(image: dict, profile: dict, storage: LocalStorage | None = None) -> dict:
    storage = storage or LocalStorage()
    base = {"width_px": max(1, int(image["width_px"])), "height_px": max(1, int(image["height_px"])),
            "pixel_count": max(1, int(image["width_px"]) * int(image["height_px"])),
            "analyzed_width_px": 1, "analyzed_height_px": 1, "analysis_scale": 1.0,
            "integrity_verified": False, "checksum_verified": False, "decoded_successfully": False}
    try:
        path = storage.resolve(image["storage_key"], must_exist=True)
        info = path.stat()
        if info.st_size != int(image["file_size_bytes"]):
            raise ValueError("FILE_SIZE_MISMATCH")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024): digest.update(chunk)
        if digest.hexdigest() != image["sha256"].strip():
            raise ValueError("CHECKSUM_MISMATCH")
        base["checksum_verified"] = True
        metadata = validate_image(path)
        if (metadata.width_px, metadata.height_px) != (image["width_px"], image["height_px"]):
            raise ValueError("DIMENSIONS_MISMATCH")
        if metadata.detected_format != image["detected_format"]:
            raise ValueError("FORMAT_MISMATCH")
        with Image.open(path) as original:
            oriented = ImageOps.exif_transpose(original)
            oriented.thumbnail((profile["max_analysis_dimension"], profile["max_analysis_dimension"]), Image.Resampling.LANCZOS)
            rgb = oriented.convert("RGB")
            width, height = rgb.size
            luminance = [(0.2126*r + 0.7152*g + 0.0722*b) / 255 for r, g, b in rgb.getdata()]
            channels = tuple(statistics.fmean(pixel[i] for pixel in rgb.getdata()) / 255 for i in range(3))
        p05, p50, p95 = (_percentile(luminance, value) for value in (0.05, 0.50, 0.95))
        laplacian, tenengrad = _focus(luminance, width, height)
        border, usable = _border_and_field(luminance, width, height, profile["dark_threshold"])
        metrics = {**base, "integrity_verified": True, "decoded_successfully": True,
            "channel_count": metadata.channel_count, "bit_depth": metadata.bit_depth, "color_space": metadata.color_space,
            "analyzed_width_px": width, "analyzed_height_px": height,
            "analysis_scale": width / metadata.width_px,
            "brightness_mean": statistics.fmean(luminance), "brightness_p05": p05,
            "brightness_p50": p50, "brightness_p95": p95, "contrast_p95_p05": p95-p05,
            "luminance_stddev": statistics.pstdev(luminance), "entropy_bits": _entropy(luminance),
            "laplacian_variance": laplacian, "tenengrad_mean": tenengrad,
            "dark_pixel_ratio": sum(v <= profile["dark_threshold"] for v in luminance)/len(luminance),
            "bright_pixel_ratio": sum(v >= profile["bright_threshold"] for v in luminance)/len(luminance),
            "near_black_border_ratio": border, "usable_field_ratio": usable,
            "metrics_json": {"channel_means": {"red": channels[0], "green": channels[1], "blue": channels[2]}}}
        warnings, failures = _codes(metrics, profile)
        return {**metrics, "assessment_status": "completed",
                "quality_verdict": "fail" if failures else "warning" if warnings else "pass",
                "warning_codes": warnings, "failure_codes": failures, "error_code": None, "error_message": None}
    except (StorageError, FileNotFoundError, OSError, ValueError) as exc:
        code = str(exc) if str(exc).isupper() else "INTEGRITY_CHECK_FAILED"
        return {**base, "assessment_status": "completed", "quality_verdict": "fail",
                "warning_codes": [], "failure_codes": [code],
                "metrics_json": {}, "error_code": code, "error_message": "La integridad técnica no pudo verificarse."}
