"""SW-v3 U2: train the U-Net segmenter on stain-derived pseudo-masks (TRAIN), select on VAL.

TEST is never read: the paired loader refuses it.

Usage (from the repo root, .venv-local-train):
    python scripts/experiments/unet_segmenter/train_u2.py --data-root <.../malaria_dl_local_project/data> \
        --out <run dir> [--threads N] [--smoke]

--smoke runs the whole cycle (fit, checkpoint, reload, evaluation, panels) on a
small TRAIN/VAL subset for 2 epochs. Its numbers are not U2 results.
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3] / "malaria_dl_local_project"
sys.path.insert(0, str(PROJECT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import tensorflow as tf  # noqa: E402

from src.malaria_dl.data.pseudo_mask_loader import (  # noqa: E402
    DATASET_VERSION_ID,
    EXPECTED_GENERATOR,
    EXPECTED_MANIFEST_SHA256,
    load_pseudo_mask_rows,
    make_pair_dataset,
)
from src.malaria_dl.models.unet.builders import build_unet_segmenter  # noqa: E402
from src.malaria_dl.models.unet.losses import (  # noqa: E402
    PREDICTION_THRESHOLD,
    DiceLoss,
    binarize,
    per_image_overlap,
    segmentation_report,
)

CONFIG = {
    "stage": "SW-v3 U2",
    "model_name": "unet_segmenter",
    "model_type": "segmentation",
    "dataset_version_id": DATASET_VERSION_ID,
    "train_split": "train",
    "selection_split": "val",
    "test_split_used": False,
    "pseudo_mask_method": EXPECTED_GENERATOR["method_name"],
    "pseudo_mask_version": EXPECTED_GENERATOR["method_version"],
    "pseudo_mask_stain_delta": EXPECTED_GENERATOR["stain_delta"],
    "pseudo_mask_implementation_sha256": EXPECTED_GENERATOR["implementation_sha256"],
    "pseudo_mask_spec_sha256": EXPECTED_GENERATOR["spec_sha256"],
    "pseudo_mask_manifest_sha256": EXPECTED_MANIFEST_SHA256,
    "input_size": 200,
    "image_preprocessing": "bilinear resize, float32 / 255 (rescale_0_1); no ImageNet preprocessing",
    "mask_preprocessing": "nearest resize, float32 in {0,1}",
    "filters": [32, 64, 128],
    "bottleneck_filters": 256,
    "conv_block": "(Conv2D 3x3 no bias -> BatchNorm -> ReLU) x 2",
    "upsampling": "Conv2DTranspose 2x2 stride 2 + skip concat",
    "batch_size": 16,
    "optimizer": "adam",
    "learning_rate": 1e-3,
    "max_epochs": 40,
    "early_stopping_patience": 8,
    "loss": "DiceLoss(batch-level soft Dice, epsilon=1.0)",
    "prediction_threshold": PREDICTION_THRESHOLD,
    "predicted_empty_rule": "0 foreground pixels after probability >= 0.5",
    # val_dice_nonempty alone ignores empty targets and can select a model that marks every
    # image (seen in the smoke run). Pooled Dice: its numerator grows only with overlap on
    # non-empty targets, and every predicted pixel on an empty target enlarges the denominator.
    "checkpoint_monitor": "val_dice_pooled_pixels",
    "checkpoint_monitor_definition": "hard Dice (threshold 0.5) pooled over all pixels of all VAL images: 2*sum(T&P) / (sum(T) + sum(P))",
    "checkpoint_mode": "max",
    "early_stopping_monitor": "val_dice_pooled_pixels",
    "primary_reported_metric": "val dice_nonempty (with empty-target counts and all-black baseline)",
    "augmentation": "paired: random horizontal flip, vertical flip, rot90 k in {0,1,2,3}; no photometric",
    "random_seed": 42,
}


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def predict_masks(model, dataset):
    targets, probs = [], []
    for images, masks in dataset:
        probs.append(model.predict_on_batch(images))
        targets.append(masks.numpy())
    return np.concatenate(targets) > 0.5, np.concatenate(probs)


class ValSegmentationMetrics(tf.keras.callbacks.Callback):
    """Adds val_dice_nonempty and companions to the epoch logs (before checkpointing)."""

    def __init__(self, dataset):
        super().__init__()
        self.dataset = dataset

    def on_epoch_end(self, epoch, logs=None):
        target, probs = predict_masks(self.model, self.dataset)
        report = segmentation_report(target, binarize(probs))
        for key in ("dice_nonempty", "iou_nonempty", "dice_all", "dice_pooled_pixels",
                    "predicted_empty_count", "empty_target_false_positive", "nonempty_target_predicted_empty"):
            logs["val_" + key] = report[key]
        print(f" — val_dice_nonempty={report['dice_nonempty']:.4f} empty_fp={report['empty_target_false_positive']} "
              f"nonempty_pred_empty={report['nonempty_target_predicted_empty']}")


def panel(rows, target, probs, path):
    pred = binarize(probs)
    dice, _, t_sum, p_sum = per_image_overlap(target, pred)
    empty_t, empty_p = t_sum == 0, p_sum == 0
    groups = [
        ("vacío → vacío", np.where(empty_t & empty_p)[0]),
        ("vacío → falso positivo", np.where(empty_t & ~empty_p)[0][np.argsort(-p_sum[empty_t & ~empty_p])]),
        ("no vacío → localizado", np.where(~empty_t)[0][np.argsort(-dice[~empty_t])]),
        ("no vacío → fallado", np.where(~empty_t)[0][np.argsort(dice[~empty_t])]),
    ]
    chosen = [(name, int(i)) for name, idx in groups for i in idx[:2]]
    fig, axes = plt.subplots(len(chosen), 4, figsize=(8.4, 2.15 * len(chosen)), squeeze=False)
    for r, (name, i) in enumerate(chosen):
        image = plt.imread(rows[i]["_image_path"])[..., :3]
        image = tf.image.resize(image, (200, 200)).numpy()
        t, p = target[i, ..., 0], pred[i, ..., 0]
        over = image.copy()
        over[t] = 0.5 * over[t] + 0.5 * np.array([0.0, 0.8, 1.0])
        over[p] = 0.5 * over[p] + 0.5 * np.array([1.0, 0.85, 0.0])
        for ax, img in zip(axes[r], (image, t, p, over)):
            ax.imshow(img, cmap="gray" if img.ndim == 2 else None, vmin=0, vmax=1)
            ax.set_xticks([])
            ax.set_yticks([])
        axes[r][0].set_ylabel(f"{name}\nDice={dice[i]:.2f}", fontsize=7)
    for j, t in enumerate(("RGB", "TARGET PSEUDO-MASK", "PREDICTED MASK", "OVERLAY (cian=target, amarillo=pred)")):
        axes[0][j].set_title(t, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--threads", type=int, default=0, help="TF intra/inter op threads (0 = TF default)")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if args.threads:
        tf.config.threading.set_intra_op_parallelism_threads(args.threads)
        tf.config.threading.set_inter_op_parallelism_threads(max(1, args.threads // 2))
    config = dict(CONFIG)
    if args.smoke:
        config.update(max_epochs=2, early_stopping_patience=1, smoke=True, smoke_train_records=256, smoke_val_records=128)
    tf.keras.utils.set_random_seed(config["random_seed"])

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    rows = load_pseudo_mask_rows(args.data_root, verify_files=not args.smoke)
    train_rows, val_rows = rows["train"], rows["val"]
    if args.smoke:
        train_rows, val_rows = train_rows[: config["smoke_train_records"]], val_rows[: config["smoke_val_records"]]
    for r in val_rows:
        r["_image_path"] = str(Path(args.data_root) / r["source_path"])

    bs, size = config["batch_size"], config["input_size"]
    train_ds = make_pair_dataset(train_rows, args.data_root, size, bs, shuffle=True, augment=True, seed=config["random_seed"])
    val_ds = make_pair_dataset(val_rows, args.data_root, size, bs)

    model = build_unet_segmenter((size, size, 3), tuple(config["filters"]), config["bottleneck_filters"])
    model.compile(optimizer=tf.keras.optimizers.Adam(config["learning_rate"]), loss=DiceLoss())
    config["parameter_count"] = int(model.count_params())
    config["effective"] = {"train_records": len(train_rows), "val_records": len(val_rows)}
    (out / "config.json").write_text(json.dumps(config, indent=2) + "\n")

    checkpoint = out / "best.keras"
    callbacks = [
        ValSegmentationMetrics(val_ds),  # must precede checkpoint/early stopping
        tf.keras.callbacks.ModelCheckpoint(checkpoint, monitor=config["checkpoint_monitor"], mode="max", save_best_only=True),
        tf.keras.callbacks.EarlyStopping(monitor=config["early_stopping_monitor"], mode="max",
                                         patience=config["early_stopping_patience"], restore_best_weights=True),
        tf.keras.callbacks.CSVLogger(str(out / "history.csv")),
    ]
    started = time.time()
    history = model.fit(train_ds, epochs=config["max_epochs"], callbacks=callbacks, verbose=2)
    elapsed = time.time() - started

    monitor = history.history[config["checkpoint_monitor"]]
    best_epoch = int(np.argmax(monitor))
    reloaded = tf.keras.models.load_model(checkpoint)  # safe_mode default (True)
    target, probs = predict_masks(reloaded, val_ds)
    report = segmentation_report(target, binarize(probs))
    baseline = segmentation_report(target, np.zeros_like(target))
    panel(val_rows, target, probs, out / "val_panel.png")

    result = {
        "smoke": bool(args.smoke),
        "test_split_used": False,
        "checkpoint": {
            "path": str(checkpoint),
            "sha256": sha256_file(checkpoint),
            "selected_epoch": best_epoch + 1,
            "epochs_run": len(monitor),
            "monitor": config["checkpoint_monitor"],
            "monitor_value": float(monitor[best_epoch]),
            "reloaded_with_safe_mode": True,
        },
        "train_seconds": round(elapsed, 1),
        "val_final": report,
        "val_baseline_all_black": baseline,
    }
    (out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
