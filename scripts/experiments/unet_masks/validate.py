"""U1B.1: independent validation and freeze of stain_morph v2.

Phase 1 (blind): images only. Contrast distribution, valley check, delta sweep,
pre-registered delta rule, stability, freeze (spec + implementation hash).
Phase 2 (audit): only after the freeze, read validation_labels.csv for per-class
statistics, the geometry-vs-label diagnostic and the otsu_intensity control.

Usage:
    python validate.py --data-root <.../d8c0...> --out results/u1b_validation
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import gaussian_kde
from skimage.color import rgb2hsv
from skimage.filters import gaussian

import masks
from masks import cell_region, generate_mask, mask_stats, method_spec
from run_lab import (
    GEOMETRY_FEATURES,
    edge_case_panel,
    iou,
    load_rgb,
    method_panel,
    oof_auc,
    raw_image_features,
)

METHOD = "stain_morph"
PRIOR_DELTA = 0.15
DELTA_GRID = (0.10, 0.125, 0.15, 0.175, 0.20)
BORDERLINE_HALF_WIDTH = 0.025
VALLEY_SEARCH = (0.05, 0.30)
U1B_MANIFEST = "results/u1b/sample_manifest.csv"
U1B_SUMMARY = "results/u1b/summary.json"
CLASSES = ("parasitized", "uninfected")


def read_csv(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


# ---------------------------------------------------------------- phase 1: blind
def saturation_contrast(rgb):
    """Per-cell p99.5 - median of blurred saturation inside the eroded cell (same region as the generator)."""
    p = masks.METHODS[METHOD]["parameters"]
    rgbf = rgb.astype(np.float64) / 255.0
    cell = cell_region(rgbf, p["background_max_value"], p["cell_erosion_radius"])
    sat = gaussian(rgb2hsv(rgbf)[..., 1], sigma=p["blur_sigma"])[cell]
    return float(np.percentile(sat, 99.5) - np.median(sat))


def kde_modes_and_valley(values):
    grid = np.linspace(0, max(0.7, float(np.max(values))), 701)
    density = gaussian_kde(values)(grid)
    peaks = [i for i in range(1, len(grid) - 1) if density[i] >= density[i - 1] and density[i] > density[i + 1]]
    top = sorted(sorted(peaks, key=lambda i: density[i])[-2:])
    lo, hi = VALLEY_SEARCH
    window = [i for i in range(len(grid)) if lo <= grid[i] <= hi and (len(top) < 2 or top[0] <= i <= top[1])]
    valley = min(window, key=lambda i: density[i])
    return {
        "modes": [float(grid[i]) for i in top],
        "valley": float(grid[valley]),
        "valley_density_ratio_to_lower_mode_peak": float(density[valley] / density[top[0]]) if top else None,
        "grid": grid,
        "density": density,
    }


def empty_cause(rgb, delta):
    """Why a stain_morph mask is empty, computed from pixels only."""
    p = masks.METHODS[METHOD]["parameters"]
    rgbf = rgb.astype(np.float64) / 255.0
    sat = gaussian(rgb2hsv(rgbf)[..., 1], sigma=p["blur_sigma"])
    eroded = cell_region(rgbf, p["background_max_value"], p["cell_erosion_radius"])
    full = cell_region(rgbf, p["background_max_value"], 0)
    threshold = np.median(sat[eroded]) + delta
    if (sat[eroded] > threshold).any():
        return "removed_by_size_or_morphology"
    if (sat[full] > threshold).any():
        return "stain_only_at_cell_rim"
    return "no_pixel_above_threshold"


def blind_phase(records, u1b_records, out):
    for group in (records, u1b_records):
        for r in group:
            r["contrast"] = saturation_contrast(r["rgb"])
    contrast = {
        "u1b": np.array([r["contrast"] for r in u1b_records]),
        "u1b_1": np.array([r["contrast"] for r in records]),
    }
    kde = {k: kde_modes_and_valley(v) for k, v in contrast.items()}

    sweep = {}
    reference = {r["source_record_id"]: generate_mask(r["rgb"], METHOD, {"stain_delta": PRIOR_DELTA}) for r in records}
    for delta in DELTA_GRID:
        ms = [generate_mask(r["rgb"], METHOD, {"stain_delta": delta}) for r in records]
        st = [mask_stats(m) for m in ms]
        nonempty = [s for s in st if not s["empty_mask"]]
        refs = [reference[r["source_record_id"]] for r in records]
        # Two empty masks agree trivially; IoU is reported only where either mask is non-empty.
        informative = [iou(m, ref) for m, ref in zip(ms, refs) if m.any() or ref.any()]
        sweep[str(delta)] = {
            "empty_mask_rate": float(np.mean([s["empty_mask"] for s in st])),
            "foreground_fraction_median_nonempty": float(np.median([s["foreground_fraction"] for s in nonempty])) if nonempty else 0.0,
            "components_mean": float(np.mean([s["connected_components"] for s in st])),
            f"median_iou_vs_{PRIOR_DELTA}_informative_cells": float(np.median(informative)),
            f"empty_status_flips_vs_{PRIOR_DELTA}": int(sum(m.any() != ref.any() for m, ref in zip(ms, refs))),
            "borderline_cells_fraction": {
                k: float(np.mean(np.abs(v - delta) <= BORDERLINE_HALF_WIDTH)) for k, v in contrast.items()
            },
        }
    # Pre-registered rule: fewest borderline cells in the new sample; ties keep the prior.
    best = min(
        DELTA_GRID,
        key=lambda d: (sweep[str(d)]["borderline_cells_fraction"]["u1b_1"], abs(d - PRIOR_DELTA)),
    )
    plot_contrast(contrast, kde, best, out / "samples" / "contrast_distribution.png")
    plot_sweep(sweep, out / "samples" / "delta_sweep.png")
    return contrast, kde, sweep, best


def stability(records, delta):
    values, informative = [], []
    for r in records:
        variants = [generate_mask(r["rgb"], METHOD, {"stain_delta": round(delta * f, 4)}) for f in (0.8, 1.2)]
        value = min(iou(r["masks"][METHOD], v) for v in variants)
        values.append(value)
        if r["masks"][METHOD].any() or any(v.any() for v in variants):
            informative.append(value)
    return {
        "perturbation": "delta x0.8 and x1.2, min IoU",
        "all_cells": {"median": float(np.median(values)), "p10": float(np.percentile(values, 10))},
        "informative_cells": {
            "n": len(informative),
            "median": float(np.median(informative)),
            "p10": float(np.percentile(informative, 10)),
        },
    }


def blind_stats(records):
    st = [r["stats"][METHOD] for r in records]
    nonempty = [s for s in st if not s["empty_mask"]]
    return {
        "n": len(st),
        "empty_mask_rate": float(np.mean([s["empty_mask"] for s in st])),
        "foreground_fraction_median_nonempty": float(np.median([s["foreground_fraction"] for s in nonempty])),
        "components_mean_nonempty": float(np.mean([s["connected_components"] for s in nonempty])),
        "largest_component_fraction_median_nonempty": float(np.median([s["largest_component_fraction"] for s in nonempty])),
    }


def freeze(delta):
    frozen = masks.FROZEN_PSEUDO_MASK
    if frozen["method"] != METHOD or frozen["parameters"] != {"stain_delta": delta}:
        raise ValueError(f"FROZEN_CONSTANT_DIFFERS_FROM_RULE_OUTPUT:{delta}")
    spec = method_spec(METHOD, {"stain_delta": delta})
    source = Path(masks.__file__).read_bytes()
    canonical = json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()
    return {
        **spec,
        "mask_dtype_generation": "bool",
        "resize": "nearest",
        "implementation_file": "scripts/experiments/unet_masks/masks.py",
        "implementation_sha256": hashlib.sha256(source).hexdigest(),
        "spec_sha256": hashlib.sha256(canonical).hexdigest(),
    }


def plot_contrast(contrast, kde, delta, path):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4), sharey=True)
    for ax, (key, title) in zip(axes, (("u1b", "U1B (n=200)"), ("u1b_1", "U1B.1 independiente (n=200)"))):
        ax.hist(contrast[key], bins=np.arange(0, 0.72, 0.02), density=True, color="#b9a7d6", edgecolor="white")
        ax.plot(kde[key]["grid"], kde[key]["density"], color="#4b2a7b", lw=1.6, label="KDE")
        ax.axvline(delta, color="#c0392b", lw=1.6, label=f"delta = {delta}")
        ax.axvline(kde[key]["valley"], color="#4b2a7b", lw=1, ls="--", label=f"valle KDE = {kde[key]['valley']:.3f}")
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("contraste de saturación por célula (p99.5 − mediana)", fontsize=8)
        ax.legend(fontsize=7)
    axes[0].set_ylabel("densidad")
    fig.suptitle("Distribución de contraste sin labels", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def plot_sweep(sweep, path):
    deltas = [float(d) for d in sweep]
    fig, ax = plt.subplots(figsize=(6, 3.2))
    ax.plot(deltas, [sweep[str(d)]["empty_mask_rate"] for d in deltas], "o-", color="#4b2a7b", label="tasa de máscaras vacías (U1B.1)")
    ax.plot(deltas, [sweep[str(d)]["borderline_cells_fraction"]["u1b_1"] for d in deltas], "s-", color="#c0392b", label="células ambiguas ±0.025 (U1B.1)")
    ax.plot(deltas, [sweep[str(d)]["borderline_cells_fraction"]["u1b"] for d in deltas], "s--", color="#e8a39b", label="células ambiguas ±0.025 (U1B)")
    ax.set_xlabel("stain_delta")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=7)
    ax.set_title("Barrido de delta (sin labels)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def by_class(records, method):
    out = {}
    for c in CLASSES:
        st = [r["stats"][method] for r in records if r["class"] == c]
        out[c] = {
            "n": len(st),
            "empty_mask_rate": float(np.mean([s["empty_mask"] for s in st])),
            "foreground_fraction_median": float(np.median([s["foreground_fraction"] for s in st])),
            "foreground_fraction_p10_p90": [float(np.percentile([s["foreground_fraction"] for s in st], q)) for q in (10, 90)],
            "components_mean": float(np.mean([s["connected_components"] for s in st])),
            "largest_component_fraction_median": float(np.median([s["largest_component_fraction"] for s in st])),
        }
    return out


# ---------------------------------------------------------------- phase 2: audit
def audit_phase(records, labels, frozen_delta, out):
    for r in records:
        r["class"] = labels[r["source_record_id"]]
        r["masks"]["otsu_intensity"] = generate_mask(r["rgb"], "otsu_intensity")
        r["stats"]["otsu_intensity"] = mask_stats(r["masks"]["otsu_intensity"])
    y = np.array([r["class"] == "parasitized" for r in records], int)
    groups = np.array([r["patient"] for r in records])

    causes = {}
    for r in records:
        if r["stats"][METHOD]["empty_mask"]:
            cause = empty_cause(r["rgb"], frozen_delta)
            causes.setdefault(cause, {c: 0 for c in CLASSES})[r["class"]] += 1

    kept = []
    for r in records:
        stain = r["masks"][METHOD]
        if stain.any():
            kept.append(float((stain & r["masks"]["otsu_intensity"]).sum() / stain.sum()))

    geometry = {
        m: oof_auc(np.array([[r["stats"][m][f] for f in GEOMETRY_FEATURES] for r in records], float), y, groups)
        for m in (METHOD, "otsu_intensity")
    }
    method_panel(records, METHOD, out / "samples" / "panel_stain_morph.png")
    edge_case_panel(records, METHOD, out / "samples" / "edge_cases_stain_morph.png")
    return {
        "class_counts": {c: int(sum(r["class"] == c for r in records)) for c in CLASSES},
        "stain_morph_by_class": by_class(records, METHOD),
        "empty_mask_causes": causes,
        "geometry_only_oof_roc_auc": geometry,
        "raw_image_reference_oof_roc_auc": oof_auc(np.array([raw_image_features(r["rgb"]) for r in records]), y, groups),
        "otsu_intensity_control": {
            "by_class": by_class(records, "otsu_intensity"),
            "median_fraction_of_stain_focus_inside_cell_mask": float(np.median(kept)) if kept else None,
        },
        "cv": "StratifiedGroupKFold(5) grouped by patient, StandardScaler + LogisticRegression, out-of-fold ROC-AUC",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    (out / "samples").mkdir(parents=True, exist_ok=True)

    # Phase 1 inputs: manifests without any class column being read.
    records = [
        {k: r[k] for k in ("source_record_id", "patient", "split", "relative_path")}
        for r in read_csv(out / "validation_manifest.csv")
    ]
    u1b_records = [
        {k: r[k] for k in ("source_record_id", "patient", "split", "relative_path")}
        for r in read_csv(U1B_MANIFEST)
    ]
    if any(r["split"] != "train" for r in records + u1b_records):
        raise ValueError("U1B1_TRAIN_ONLY")
    for r in records + u1b_records:
        r["rgb"] = load_rgb(Path(args.data_root) / r["relative_path"])

    contrast, kde, sweep, delta = blind_phase(records, u1b_records, out)
    for group in (records, u1b_records):
        for r in group:
            r["masks"] = {METHOD: generate_mask(r["rgb"], METHOD, {"stain_delta": delta})}
            r["stats"] = {METHOD: mask_stats(r["masks"][METHOD])}
    frozen = freeze(delta)
    blind = {
        "u1b": {**blind_stats(u1b_records), "stability": stability(u1b_records, delta)},
        "u1b_1": {**blind_stats(records), "stability": stability(records, delta)},
    }

    # Phase 2: labels are opened only here, after the freeze.
    labels = {r["source_record_id"]: r["class"] for r in read_csv(out / "validation_labels.csv")}
    audit = audit_phase(records, labels, delta, out)
    u1b_labels = {r["source_record_id"]: r["class"] for r in read_csv(U1B_MANIFEST)}
    for r in u1b_records:
        r["class"] = u1b_labels[r["source_record_id"]]
    u1b_audit = {
        "at_frozen_delta": by_class(u1b_records, METHOD),
        "as_reported_in_u1b_delta_0.15": json.loads(Path(U1B_SUMMARY).read_text())["methods"][METHOD]["by_class"],
    }

    summary = {
        "stage": "U1B.1",
        "dataset_version_id": "d8c0cab5-09dd-597f-9de7-7ca01aee2ec2",
        "split": "train",
        "independence": {
            "images": len(records),
            "patients": len({r["patient"] for r in records}),
            "overlap_images_with_u1b": len({r["source_record_id"] for r in records} & {r["source_record_id"] for r in u1b_records}),
            "overlap_patients_with_u1b": len({r["patient"] for r in records} & {r["patient"] for r in u1b_records}),
            "selection": "label-blind md5('u1b1-2026-10-02' || source_record_id), excluding U1B images and patients",
        },
        "phase1_blind": {
            "contrast_definition": "p99.5 - median of gaussian(sigma=1) HSV saturation inside the eroded cell",
            "kde": {k: {kk: vv for kk, vv in v.items() if kk not in ("grid", "density")} for k, v in kde.items()},
            "contrast_percentiles_10_25_50_75_90": {k: [float(x) for x in np.percentile(v, [10, 25, 50, 75, 90])] for k, v in contrast.items()},
            "delta_rule": f"argmin over {list(DELTA_GRID)} of fraction of U1B.1 cells with |contrast - delta| <= {BORDERLINE_HALF_WIDTH}; ties keep {PRIOR_DELTA}",
            "delta_sweep": sweep,
            "delta_final": delta,
            "stain_morph_blind_stats": blind,
        },
        "frozen_generator": frozen,
        "phase2_audit": {**audit, "u1b_stain_morph_by_class": u1b_audit},
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: summary[k] for k in ("independence",)} | {"kde": summary["phase1_blind"]["kde"], "delta_final": delta}, indent=1))
    print(json.dumps(sweep, indent=1))
    print(json.dumps(blind, indent=1))
    print(json.dumps(frozen, indent=1))
    print(json.dumps(audit, indent=1))


if __name__ == "__main__":
    main()
