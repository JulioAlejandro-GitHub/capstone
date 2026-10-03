"""U1B pseudo-mask lab: every method is mask = f(image, parameters).

No function in this module receives a class label, a class directory or any
clinical metadata. The same method and parameters are applied to every image.
"""

from copy import deepcopy

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.color import rgb2gray, rgb2hsv
from skimage.filters import gaussian, threshold_otsu
from skimage.measure import label as label_components
from skimage.morphology import (
    closing,
    erosion,
    opening,
    disk,
    remove_small_holes,
    remove_small_objects,
)

IMPLEMENTATION_VERSION = "u1b-lab-1"

# Black padding around NIH crops has max(R,G,B) near 0; any pixel brighter than
# this (on a 0..1 scale) belongs to the cell. One global constant for all images.
BACKGROUND_MAX_VALUE = 0.04

METHODS = {
    # A: classic Otsu on luminance over the whole crop.
    "otsu_intensity": {
        "version": 1,
        "parameters": {
            "blur_sigma": 1.0,
            "polarity": "bright",  # foreground = pixels brighter than Otsu threshold
            "min_object_px": 64,
            "max_hole_px": 64,
        },
    },
    # B: Otsu on HSV saturation, computed only over cell pixels.
    "hsv_otsu": {
        "version": 1,
        "parameters": {
            "channel": "saturation",
            "blur_sigma": 1.0,
            "background_max_value": BACKGROUND_MAX_VALUE,
            "cell_erosion_radius": 3,
            "min_object_px": 16,
        },
    },
    # C: saturation contrast above the cell's own median, fixed global offset,
    # then morphological cleanup. Can legitimately return an empty mask.
    # v1 used rgb2hed hematoxylin with delta 0.03: mis-scaled, ~90% empty masks.
    # v2 delta sits in the valley of the pooled, label-blind distribution of
    # per-cell (p99.5 - median) saturation over the U1B sample (modes ~0.03 and ~0.4).
    "stain_morph": {
        "version": 2,
        "parameters": {
            "color_transform": "hsv_saturation",
            "blur_sigma": 1.0,
            "background_max_value": BACKGROUND_MAX_VALUE,
            "cell_erosion_radius": 3,
            "stain_delta": 0.15,
            "min_object_px": 20,
            "max_hole_px": 30,
            "opening_radius": 1,
        },
    },
}


# U1B.1 freeze: stain_delta chosen by the label-blind, pre-registered rule in
# validate.py (results/u1b_validation/report.md). METHODS defaults stay as in U1B
# so that the U1B results remain reproducible.
FROZEN_PSEUDO_MASK = {
    "method": "stain_morph",
    "method_version": 2,
    "parameters": {"stain_delta": 0.20},
}


def method_spec(method, parameters=None):
    if method not in METHODS:
        raise ValueError("UNKNOWN_MASK_METHOD:" + str(method))
    params = deepcopy(METHODS[method]["parameters"])
    for key, value in (parameters or {}).items():
        if key not in params:
            raise ValueError("UNKNOWN_MASK_PARAMETER:" + key)
        params[key] = value
    return {
        "method_name": method,
        "method_version": METHODS[method]["version"],
        "implementation_version": IMPLEMENTATION_VERSION,
        "parameters": params,
    }


def _as_rgb_float(image):
    image = np.asarray(image)
    if image.ndim != 3 or image.shape[-1] != 3:
        raise ValueError("EXPECTED_RGB_HWC")
    if image.dtype == np.uint8:
        return image.astype(np.float64) / 255.0
    return np.clip(image.astype(np.float64), 0.0, 1.0)


def cell_region(rgb, background_max_value, erosion_radius=0):
    cell = rgb.max(axis=-1) > background_max_value
    cell = ndi.binary_fill_holes(cell)
    if erosion_radius:
        cell = erosion(cell, disk(erosion_radius))
    return cell


def _otsu_intensity(rgb, p):
    gray = gaussian(rgb2gray(rgb), sigma=p["blur_sigma"])
    t = threshold_otsu(gray)
    mask = gray > t if p["polarity"] == "bright" else gray <= t
    mask = remove_small_objects(mask, max_size=p["min_object_px"] - 1)
    return remove_small_holes(mask, max_size=p["max_hole_px"])


def _hsv_otsu(rgb, p):
    cell = cell_region(rgb, p["background_max_value"], p["cell_erosion_radius"])
    if cell.sum() < 2:
        return np.zeros(cell.shape, bool)
    sat = gaussian(rgb2hsv(rgb)[..., 1], sigma=p["blur_sigma"])
    values = sat[cell]
    if values.min() == values.max():
        return np.zeros(cell.shape, bool)
    mask = (sat > threshold_otsu(values)) & cell
    return remove_small_objects(mask, max_size=p["min_object_px"] - 1)


def _stain_morph(rgb, p):
    cell = cell_region(rgb, p["background_max_value"], p["cell_erosion_radius"])
    if cell.sum() < 2:
        return np.zeros(cell.shape, bool)
    stain = gaussian(rgb2hsv(rgb)[..., 1], sigma=p["blur_sigma"])
    mask = (stain > np.median(stain[cell]) + p["stain_delta"]) & cell
    mask = remove_small_objects(mask, max_size=p["min_object_px"] - 1)
    mask = remove_small_holes(mask, max_size=p["max_hole_px"])
    if p["opening_radius"]:
        mask = opening(mask, disk(p["opening_radius"]))
        mask = closing(mask, disk(p["opening_radius"])) & cell
    return mask


_IMPLEMENTATIONS = {
    "otsu_intensity": _otsu_intensity,
    "hsv_otsu": _hsv_otsu,
    "stain_morph": _stain_morph,
}


def generate_mask(image, method, parameters=None):
    """Return a bool HxW mask. Depends only on the pixels and the parameters."""
    spec = method_spec(method, parameters)
    mask = _IMPLEMENTATIONS[method](_as_rgb_float(image), spec["parameters"])
    return np.asarray(mask, dtype=bool)


def generate_frozen_pseudo_mask(image):
    """Stain-derived pseudo-mask with the frozen U1B.1 configuration."""
    if METHODS[FROZEN_PSEUDO_MASK["method"]]["version"] != FROZEN_PSEUDO_MASK["method_version"]:
        raise ValueError("FROZEN_METHOD_VERSION_MISMATCH")
    return generate_mask(image, FROZEN_PSEUDO_MASK["method"], FROZEN_PSEUDO_MASK["parameters"])


def resize_mask(mask, size):
    """Nearest-neighbour resize; the result stays boolean."""
    resized = Image.fromarray(np.asarray(mask, np.uint8) * 255).resize(
        (size, size), Image.NEAREST
    )
    return np.asarray(resized) > 127


def mask_stats(mask):
    mask = np.asarray(mask, dtype=bool)
    h, w = mask.shape
    area = int(mask.sum())
    labels, count = label_components(mask, connectivity=2, return_num=True)
    largest = int(np.bincount(labels.ravel())[1:].max()) if count else 0
    border = np.concatenate([mask[0], mask[-1], mask[1:-1, 0], mask[1:-1, -1]])
    ys, xs = np.nonzero(mask)
    return {
        "foreground_fraction": area / (h * w),
        "connected_components": int(count),
        "largest_component_fraction": largest / area if area else 0.0,
        "empty_mask": area == 0,
        "full_mask": area / (h * w) >= 0.99,
        "centroid_y": float(ys.mean() / h) if area else None,
        "centroid_x": float(xs.mean() / w) if area else None,
        "border_touch_fraction": float(border.mean()),
    }
