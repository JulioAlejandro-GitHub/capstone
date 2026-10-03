"""U1B lab run: masks, statistics, panels, stability and label-leakage check.

Masks are generated with masks.generate_mask(image, method) only. The class
column of the manifest is read afterwards, for aggregated audit statistics,
panel captions and the leakage diagnostic. No parameter is chosen here.

Usage:
    python run_lab.py --data-root <.../d8c0...> --manifest results/u1b/sample_manifest.csv --out results/u1b
"""

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from skimage.color import rgb2gray, rgb2hsv
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from masks import (
    BACKGROUND_MAX_VALUE,
    METHODS,
    cell_region,
    generate_mask,
    mask_stats,
    method_spec,
    resize_mask,
)

PIPELINE_SIZE = 200
PANEL_PER_CLASS = 4
GEOMETRY_FEATURES = (
    "foreground_fraction",
    "connected_components",
    "largest_component_fraction",
)
# Small perturbation of each method's main free parameter, for stability only.
PERTURBATIONS = {
    "otsu_intensity": [{"blur_sigma": 1.5}, {"blur_sigma": 0.5}],
    "hsv_otsu": [{"blur_sigma": 1.5}, {"blur_sigma": 0.5}],
    "stain_morph": [{"stain_delta": 0.12}, {"stain_delta": 0.18}],
}
CLASSES = ("parasitized", "uninfected")


def load_rgb(path):
    return np.asarray(Image.open(path).convert("RGB"))


def iou(a, b):
    union = np.logical_or(a, b).sum()
    return 1.0 if union == 0 else float(np.logical_and(a, b).sum() / union)


def pipeline_view(rgb, mask):
    """Image as the TRAIN pipeline sees it (bilinear 200x200, [0,1]) and the nearest-resized mask."""
    image = (
        np.asarray(
            Image.fromarray(rgb).resize((PIPELINE_SIZE, PIPELINE_SIZE), Image.BILINEAR),
            np.float32,
        )
        / 255.0
    )
    small = resize_mask(mask, PIPELINE_SIZE)
    assert small.dtype == bool and small.shape == (PIPELINE_SIZE, PIPELINE_SIZE)
    return image, small


def overlay(image, mask):
    out = image.copy()
    tint = np.array([1.0, 0.85, 0.0], np.float32)
    out[mask] = 0.55 * out[mask] + 0.45 * tint
    return out


def raw_image_features(rgb):
    """Mask-free reference: global stain statistics of the cell pixels."""
    rgbf = rgb.astype(np.float64) / 255.0
    cell = cell_region(rgbf, BACKGROUND_MAX_VALUE)
    gray = rgb2gray(rgbf)[cell]
    sat = rgb2hsv(rgbf)[..., 1][cell]
    return [float(np.percentile(gray, 1)), float(np.percentile(sat, 99))]


def oof_auc(X, y, groups):
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=0)
    scores = np.zeros(len(y))
    for train, test in cv.split(X, y, groups):
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
        model.fit(X[train], y[train])
        scores[test] = model.predict_proba(X[test])[:, 1]
    return float(roc_auc_score(y, scores))


def class_summary(records, method):
    out = {}
    for c in CLASSES:
        stats = [r["stats"][method] for r in records if r["class"] == c]
        ff = np.array([s["foreground_fraction"] for s in stats])
        cc = np.array([s["connected_components"] for s in stats])
        lc = np.array([s["largest_component_fraction"] for s in stats])
        out[c] = {
            "n": len(stats),
            "foreground_fraction_median": float(np.median(ff)),
            "foreground_fraction_p10_p90": [float(np.percentile(ff, 10)), float(np.percentile(ff, 90))],
            "empty_mask_rate": float(np.mean([s["empty_mask"] for s in stats])),
            "full_mask_rate": float(np.mean([s["full_mask"] for s in stats])),
            "components_mean": float(cc.mean()),
            "components_median": float(np.median(cc)),
            "largest_component_fraction_median": float(np.median(lc)),
            "border_touch_fraction_median": float(
                np.median([s["border_touch_fraction"] for s in stats])
            ),
        }
    return out


def method_panel(records, method, path):
    rows = [r for c in CLASSES for r in [x for x in records if x["class"] == c][:PANEL_PER_CLASS]]
    titles = ("RGB", "MASK", "OVERLAY", "MASKED RGB")
    fig, axes = plt.subplots(len(rows), 4, figsize=(8.4, 2.15 * len(rows)))
    for i, r in enumerate(rows):
        image, small = pipeline_view(r["rgb"], r["masks"][method])
        s = r["stats"][method]
        panels = (image, small, overlay(image, small), image * small[..., None])
        for j, ax in enumerate(axes[i]):
            ax.imshow(panels[j], cmap="gray" if j == 1 else None, vmin=0, vmax=1)
            ax.set_xticks([])
            ax.set_yticks([])
            if i == 0:
                ax.set_title(titles[j], fontsize=9)
        axes[i][0].set_ylabel(
            f"{r['class']}\n{r['patient']}\nfg={s['foreground_fraction']:.2f} cc={s['connected_components']}",
            fontsize=7,
        )
    fig.suptitle(f"{method} v{METHODS[method]['version']} (200x200, mask nearest)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def compare_panel(records, path):
    rows = [r for c in CLASSES for r in [x for x in records if x["class"] == c][:PANEL_PER_CLASS]]
    methods = list(METHODS)
    fig, axes = plt.subplots(len(rows), 1 + len(methods), figsize=(2.1 * (1 + len(methods)), 2.15 * len(rows)))
    for i, r in enumerate(rows):
        image, _ = pipeline_view(r["rgb"], r["masks"][methods[0]])
        axes[i][0].imshow(image)
        axes[i][0].set_ylabel(f"{r['class']}\n{r['patient']}", fontsize=7)
        for j, m in enumerate(methods, start=1):
            _, small = pipeline_view(r["rgb"], r["masks"][m])
            axes[i][j].imshow(overlay(image, small))
        for ax in axes[i]:
            ax.set_xticks([])
            ax.set_yticks([])
    for j, title in enumerate(["RGB", *methods]):
        axes[0][j].set_title(title, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def edge_case_panel(records, method, path):
    """Parasitized with empty mask and uninfected with non-empty mask (audit only)."""
    groups = [
        ("parasitized, empty mask", [r for r in records if r["class"] == "parasitized" and r["stats"][method]["empty_mask"]]),
        ("uninfected, non-empty mask", [r for r in records if r["class"] == "uninfected" and not r["stats"][method]["empty_mask"]]),
    ]
    rows = [(name, r) for name, items in groups for r in items[:PANEL_PER_CLASS]]
    if not rows:
        return None
    fig, axes = plt.subplots(len(rows), 3, figsize=(6.3, 2.15 * len(rows)), squeeze=False)
    for i, (name, r) in enumerate(rows):
        image, small = pipeline_view(r["rgb"], r["masks"][method])
        for ax, panel in zip(axes[i], (image, overlay(image, small), image * small[..., None])):
            ax.imshow(panel)
            ax.set_xticks([])
            ax.set_yticks([])
        axes[i][0].set_ylabel(f"{name}\n{r['patient']}", fontsize=7)
    for j, t in enumerate(("RGB", "OVERLAY", "MASKED RGB")):
        axes[0][j].set_title(t, fontsize=9)
    fig.suptitle(f"{method}: casos límite", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return {name: len(items) for name, items in groups}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    (out / "samples").mkdir(parents=True, exist_ok=True)

    with open(args.manifest, newline="") as handle:
        records = list(csv.DictReader(handle))
    if any(r["split"] != "train" for r in records):
        raise ValueError("U1B_TRAIN_ONLY")

    stability = {m: [] for m in METHODS}
    for r in records:
        r["rgb"] = load_rgb(Path(args.data_root) / r["relative_path"])
        # Masks first, from pixels only; no class value is passed.
        r["masks"] = {m: generate_mask(r["rgb"], m) for m in METHODS}
        r["stats"] = {m: mask_stats(r["masks"][m]) for m in METHODS}
        for m, variants in PERTURBATIONS.items():
            stability[m].append(
                min(iou(r["masks"][m], generate_mask(r["rgb"], m, v)) for v in variants)
            )

    y = np.array([r["class"] == "parasitized" for r in records], int)
    groups = np.array([r["patient"] for r in records])
    summary = {
        "stage": "U1B",
        "dataset_version_id": "d8c0cab5-09dd-597f-9de7-7ca01aee2ec2",
        "split": "train",
        "sample": {
            "images": len(records),
            "patients": int(len(set(groups))),
            "per_class": {c: int(sum(r["class"] == c for r in records)) for c in CLASSES},
            "selection": "md5(seed || source_record_id), seed=u1b-2026-10-02, 100 per class",
        },
        "pipeline_size": PIPELINE_SIZE,
        "mask_resize": "nearest",
        "methods": {},
        "raw_image_reference": {
            "features": ["cell_gray_p1", "cell_saturation_p99"],
            "oof_roc_auc": oof_auc(
                np.array([raw_image_features(r["rgb"]) for r in records]), y, groups
            ),
        },
        "leakage_check": {
            "classifier": "StandardScaler + LogisticRegression",
            "cv": "StratifiedGroupKFold(5) grouped by patient, out-of-fold ROC-AUC",
            "features": list(GEOMETRY_FEATURES),
            "note": "Diagnostic only; not used to choose parameters.",
        },
    }
    for m in METHODS:
        X = np.array([[r["stats"][m][f] for f in GEOMETRY_FEATURES] for r in records], float)
        summary["methods"][m] = {
            **method_spec(m),
            "by_class": class_summary(records, m),
            "overall_empty_mask_rate": float(np.mean([r["stats"][m]["empty_mask"] for r in records])),
            "overall_full_mask_rate": float(np.mean([r["stats"][m]["full_mask"] for r in records])),
            "stability_min_iou_under_perturbation": {
                "perturbations": PERTURBATIONS[m],
                "median": float(np.median(stability[m])),
                "p10": float(np.percentile(stability[m], 10)),
            },
            "geometry_only_oof_roc_auc": oof_auc(X, y, groups),
        }
        method_panel(records, m, out / "samples" / f"panel_{m}.png")
        counts = edge_case_panel(records, m, out / "samples" / f"edge_cases_{m}.png")
        summary["methods"][m]["edge_case_counts"] = counts
    compare_panel(records, out / "samples" / "compare_methods.png")

    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({m: {k: v for k, v in s.items() if k in ("by_class", "geometry_only_oof_roc_auc", "stability_min_iou_under_perturbation", "edge_case_counts")} for m, s in summary["methods"].items()}, indent=1))
    print("raw reference AUC", summary["raw_image_reference"]["oof_roc_auc"])


if __name__ == "__main__":
    main()
