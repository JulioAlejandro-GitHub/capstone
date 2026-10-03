"""SW-v3 U2 functional verification (brief item 27). Not a test suite; exits 1 on any FAIL.

Usage (from the repo root, .venv-local-train):
    python scripts/experiments/unet_segmenter/verify_u2.py --data-root <.../malaria_dl_local_project/data> [--threads 2]
"""

import argparse
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3] / "malaria_dl_local_project"
sys.path.insert(0, str(PROJECT))

import numpy as np  # noqa: E402
import tensorflow as tf  # noqa: E402

from src.malaria_dl.data.pseudo_mask_loader import (  # noqa: E402
    PseudoMaskManifestError,
    load_pseudo_mask_rows,
    make_pair_dataset,
    paired_augment,
)
from src.malaria_dl.models.unet.builders import build_unet_segmenter  # noqa: E402
from src.malaria_dl.models.unet.losses import DiceLoss, segmentation_report  # noqa: E402

FAILURES = []


def check(name, condition):
    print(("PASS " if condition else "FAIL ") + name)
    if not condition:
        FAILURES.append(name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    tf.config.threading.set_intra_op_parallelism_threads(args.threads)
    tf.config.threading.set_inter_op_parallelism_threads(1)
    data_root = args.data_root

    model = build_unet_segmenter()
    check(f"model builds, output (None,200,200,1), params={model.count_params()}", model.output_shape == (None, 200, 200, 1))

    try:
        load_pseudo_mask_rows(data_root, splits=("test",), verify_files=False)
        check("loader refuses TEST", False)
    except PseudoMaskManifestError as exc:
        check(f"loader refuses TEST ({exc})", True)

    rows = load_pseudo_mask_rows(data_root, verify_files=False)
    check("manifest sealed, counts train=22180 val=2693, no test rows",
          set(rows) == {"train", "val"} and len(rows["train"]) == 22180 and len(rows["val"]) == 2693)

    sample = rows["train"][:512]
    image, mask = next(iter(make_pair_dataset(sample, data_root, 200, 32)))
    check("image float32 (B,200,200,3) in [0,1]",
          image.dtype == tf.float32 and tuple(image.shape) == (32, 200, 200, 3)
          and 0.0 <= float(tf.reduce_min(image)) and float(tf.reduce_max(image)) <= 1.0)
    check("mask float32 (B,200,200,1)", mask.dtype == tf.float32 and tuple(mask.shape) == (32, 200, 200, 1))

    values, nonempty_after = set(), 0
    for _, masks in make_pair_dataset(sample, data_root, 200, 64, shuffle=True, augment=True):
        values |= set(np.unique(masks.numpy()).tolist())
    for _, masks in make_pair_dataset(sample, data_root, 200, 64):
        nonempty_after += int((masks.numpy().reshape(len(masks), -1).sum(1) > 0).sum())
    nonempty_native = sum(int(r["foreground_pixels"]) > 0 for r in sample)
    check(f"mask values after nearest resize + augmentation: {sorted(values)}", values <= {0.0, 1.0})
    check(f"non-empty masks survive 200x200 nearest resize ({nonempty_after}/{nonempty_native})", nonempty_after == nonempty_native)

    probe = tf.cast(tf.random.stateless_uniform((200, 200, 1), seed=[1, 2]) > 0.7, tf.float32)
    aligned = all(
        bool(tf.reduce_all(a[..., :1] == b))
        for a, b in (paired_augment(tf.repeat(probe, 3, -1), probe, tf.constant([7, s], tf.int64)) for s in range(40))
    )
    check("paired augmentation keeps image/mask aligned (40 seeds)", aligned)

    loss = DiceLoss()
    zeros = tf.zeros((2, 200, 200, 1))
    target = tf.concat([zeros[:1], tf.pad(tf.ones((1, 20, 20, 1)), [[0, 0], [90, 90], [90, 90], [0, 0]])], 0)
    false_pos = tf.pad(tf.ones((2, 10, 10, 1)) * 0.9, [[0, 0], [0, 190], [0, 190], [0, 0]])
    check("dice loss: empty/empty=0, empty/FP~1, perfect=0, non-empty/all-black~1",
          float(loss(zeros, zeros)) < 1e-6 and float(loss(zeros, false_pos)) > 0.9
          and float(loss(target, target)) < 1e-6 and float(loss(target, zeros)) > 0.9)

    t = np.zeros((4, 8, 8, 1), bool)
    t[2, 2:4, 2:4] = t[3, 0:2, 0:2] = True
    black = segmentation_report(t, np.zeros_like(t))
    everywhere = segmentation_report(t, np.ones_like(t))
    check("pooled Dice monitor: all-black=0 and all-foreground penalised",
          black["dice_pooled_pixels"] == 0.0 and black["dice_nonempty"] == 0.0
          and everywhere["dice_pooled_pixels"] < 0.1 and everywhere["empty_target_false_positive"] == 2)

    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss=DiceLoss())
    history = model.fit(make_pair_dataset(sample[:64], data_root, 200, 32, augment=True), epochs=1, verbose=0)
    check("forward/backward step finite", bool(np.isfinite(history.history["loss"][-1])))

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "unet.keras"
        model.save(path)
        reloaded = tf.keras.models.load_model(path)  # safe_mode default (True)
        check("save/reload with safe_mode gives identical predictions",
              np.allclose(model.predict_on_batch(image), reloaded.predict_on_batch(image), atol=1e-6)
              and type(reloaded.loss).__name__ == "DiceLoss")

    print("ALL PASS" if not FAILURES else f"{len(FAILURES)} FAIL")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
