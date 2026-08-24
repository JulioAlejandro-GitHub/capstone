from __future__ import annotations

from copy import deepcopy


BASE = {
    "profile_version": "1.0.0", "algorithm_version": "pillow-quality-1.0.0",
    "max_analysis_dimension": 2048, "minimum_width": 128, "minimum_height": 128,
    "minimum_pixel_count": 16384, "dark_threshold": 0.02, "bright_threshold": 0.98,
    "maximum_dark_ratio_warning": 0.35, "maximum_dark_ratio_fail": 0.80,
    "maximum_bright_ratio_warning": 0.35, "maximum_bright_ratio_fail": 0.80,
    "minimum_contrast_warning": 0.18, "minimum_contrast_fail": 0.04,
    "minimum_entropy_warning": 4.0, "minimum_entropy_fail": 1.0,
    "minimum_laplacian_warning": 0.00035, "minimum_laplacian_fail": 0.0,
    "minimum_tenengrad_warning": 0.0008, "minimum_tenengrad_fail": 0.0,
    "maximum_black_border_warning": 0.45, "maximum_black_border_fail": 0.85,
    "minimum_usable_field_warning": 0.45, "minimum_usable_field_fail": 0.10,
}

PROFILES = {
    key: {**BASE, "profile_key": key, "name": name, "logical_definition_date": "2026-07-27",
          "units": {"ratios": "0..1", "entropy": "bits", "focus": "normalized luminance"},
          "analysis_resolution": "aspect-preserving, longest side at most max_analysis_dimension",
          "rules": "fail thresholds precede warning thresholds"}
    for key, name in (
        ("manual_microscopy_v1", "Manual microscopy technical profile"),
        ("nih_nlm_v1", "NIH-NLM import technical profile"),
        ("external_capture_v1", "External capture technical profile"),
    )
}


def select_profile(acquisition_origin: str, source_system: str | None) -> dict:
    if acquisition_origin == "research_dataset_import" and source_system and "nih" in source_system.lower():
        key = "nih_nlm_v1"
    elif acquisition_origin == "external_capture_system":
        key = "external_capture_v1"
    else:
        key = "manual_microscopy_v1"
    return snapshot(key)


def snapshot(key: str) -> dict:
    profile = deepcopy(PROFILES[key])
    _validate(profile)
    return profile


def _validate(profile: dict) -> None:
    if profile["minimum_width"] <= 0 or profile["minimum_height"] <= 0:
        raise ValueError("Profile dimensions must be positive")
    pairs = (
        ("maximum_dark_ratio_warning", "maximum_dark_ratio_fail"),
        ("maximum_bright_ratio_warning", "maximum_bright_ratio_fail"),
        ("maximum_black_border_warning", "maximum_black_border_fail"),
    )
    if any(profile[warning] > profile[fail] for warning, fail in pairs):
        raise ValueError("Maximum warning thresholds cannot exceed fail thresholds")
    minima = (
        ("minimum_contrast_warning", "minimum_contrast_fail"),
        ("minimum_entropy_warning", "minimum_entropy_fail"),
        ("minimum_laplacian_warning", "minimum_laplacian_fail"),
        ("minimum_tenengrad_warning", "minimum_tenengrad_fail"),
        ("minimum_usable_field_warning", "minimum_usable_field_fail"),
    )
    if any(profile[warning] < profile[fail] for warning, fail in minima):
        raise ValueError("Minimum warning thresholds cannot be below fail thresholds")
