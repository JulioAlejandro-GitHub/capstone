"""Paired (image, stain-derived pseudo-mask) loader for the U-Net segmenter (SW-v3 U2).

Pairs come from the sealed U1C manifest: one row per source_record_id of the
governed dataset version, holding both the RGB path and the pseudo-mask path.
The mask is resolved by source_record_id, never from a class directory.

- RGB:  decode -> bilinear resize to img_size -> float32 / 255  (same contract as rescale_0_1)
- Mask: decode -> NEAREST resize to img_size -> float32 in {0, 1}
- Paired augmentation (train only): flips and rot90 applied to concat([image, mask]),
  so geometry is identical for both; no photometric transforms.
"""

import csv
import hashlib
import json
from pathlib import Path

import tensorflow as tf

DATASET_VERSION_ID = "d8c0cab5-09dd-597f-9de7-7ca01aee2ec2"
PSEUDO_MASK_ROOT = f"derived/pseudo_masks/{DATASET_VERSION_ID}/stain_morph_v2"
EXPECTED_GENERATOR = {
    "method_name": "stain_morph",
    "method_version": 2,
    "stain_delta": 0.2,
    "implementation_sha256": "65603c61c4925345d83ca305e5d097514679e54b1aea0159e63bfac7f9be24e9",
    "spec_sha256": "4a84ad75d71dacf8f3d9c79d9de668ed57db176b09d2b265fd55c00ebbca078b",
}
EXPECTED_MANIFEST_SHA256 = "b79d701753b35e183e28316251f0b72268607cba3a86b231cd16e6c746548f7c"
EXPECTED_COUNTS = {"train": 22180, "val": 2693}
ALLOWED_SPLITS = ("train", "val")  # TEST is reserved: this loader refuses it.


class PseudoMaskManifestError(ValueError):
    pass


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_pseudo_mask_rows(data_root, splits=ALLOWED_SPLITS, verify_files=True):
    """Rows of the sealed U1C manifest for the requested splits (train/val only)."""
    if not set(splits) <= set(ALLOWED_SPLITS):
        raise PseudoMaskManifestError("SPLIT_NOT_ALLOWED_IN_U2:" + ",".join(sorted(set(splits) - set(ALLOWED_SPLITS))))
    data_root = Path(data_root)
    root = data_root / PSEUDO_MASK_ROOT
    generator = json.loads((root / "generator.json").read_text())
    if generator["dataset_version_id"] != DATASET_VERSION_ID:
        raise PseudoMaskManifestError("DATASET_VERSION_MISMATCH")
    if {k: generator["generator"][k] for k in EXPECTED_GENERATOR} != EXPECTED_GENERATOR:
        raise PseudoMaskManifestError("GENERATOR_IDENTITY_MISMATCH")
    if generator["manifest_sha256"] != EXPECTED_MANIFEST_SHA256 or _sha256(root / "manifest.csv") != EXPECTED_MANIFEST_SHA256:
        raise PseudoMaskManifestError("MANIFEST_SHA256_MISMATCH")

    rows = {s: [] for s in splits}
    with (root / "manifest.csv").open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row["split_name"] in rows:  # other splits are never materialized in memory
                rows[row["split_name"]].append(row)
    for split, items in rows.items():
        if len(items) != EXPECTED_COUNTS[split]:
            raise PseudoMaskManifestError(f"COUNT_MISMATCH:{split}:{len(items)}")
        if verify_files:
            for row in items:
                if _sha256(data_root / row["mask_path"]) != row["mask_sha256"]:
                    raise PseudoMaskManifestError("MASK_SHA256_MISMATCH:" + row["source_record_id"])
                if _sha256(data_root / row["source_path"]) != row["source_sha256"]:
                    raise PseudoMaskManifestError("SOURCE_SHA256_MISMATCH:" + row["source_record_id"])
    return rows


def _decode_pair(image_path, mask_path, img_size):
    image = tf.io.decode_png(tf.io.read_file(image_path), channels=3)
    image = tf.image.resize(image, (img_size, img_size), method="bilinear")
    image = tf.cast(image, tf.float32) / 255.0
    mask = tf.io.decode_png(tf.io.read_file(mask_path), channels=1)
    mask = tf.image.resize(mask, (img_size, img_size), method="nearest")
    mask = tf.cast(mask > 127, tf.float32)
    image.set_shape((img_size, img_size, 3))
    mask.set_shape((img_size, img_size, 1))
    return image, mask


def paired_augment(image, mask, seed):
    """Same flips and rot90 for image and mask. seed: int64 tensor of shape (2,)."""
    stacked = tf.concat([image, mask], axis=-1)
    stacked = tf.image.stateless_random_flip_left_right(stacked, seed=seed)
    stacked = tf.image.stateless_random_flip_up_down(stacked, seed=seed + [0, 1])
    k = tf.random.stateless_uniform((), seed=seed + [0, 2], minval=0, maxval=4, dtype=tf.int32)
    stacked = tf.image.rot90(stacked, k=k)
    return stacked[..., :3], stacked[..., 3:]


def make_pair_dataset(rows, data_root, img_size=200, batch_size=16, shuffle=False, augment=False, seed=42):
    data_root = Path(data_root)
    images = [str(data_root / r["source_path"]) for r in rows]
    masks = [str(data_root / r["mask_path"]) for r in rows]
    ds = tf.data.Dataset.from_tensor_slices((images, masks))
    if shuffle:
        ds = ds.shuffle(len(rows), seed=seed, reshuffle_each_iteration=True)
    ds = ds.map(lambda i, m: _decode_pair(i, m, img_size), num_parallel_calls=tf.data.AUTOTUNE, deterministic=True)
    if augment:
        seeds = tf.data.Dataset.random(seed=seed, rerandomize_each_iteration=True).batch(2)
        ds = tf.data.Dataset.zip((ds, seeds)).map(
            lambda pair, s: paired_augment(pair[0], pair[1], tf.cast(s, tf.int64)),
            num_parallel_calls=tf.data.AUTOTUNE,
            deterministic=True,
        )
    return ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)
