"""U1C: governed generation of stain-derived pseudo-masks (stain_morph v2, frozen).

One pseudo-mask per source record of the governed dataset version, written
outside the RGB materialization (dataset_integrity.verify_integrity requires
that root to contain exactly the governed files). Each mask is produced by
masks.generate_frozen_pseudo_mask(image): pixels only, no class.

Subcommands:
    precheck  -> counts, uniqueness, RGB existence and SHA-256 vs PostgreSQL, hashes
    generate  -> writes <out>.staging then renames to <out>; --limit for a smoke run
    verify    -> coverage, integrity, 1:1 with assignments, deterministic regeneration sample

Usage (from scripts/experiments/unet_masks/, .venv-local-train):
    U1B_DATABASE_URL=... python generate_pseudo_masks.py precheck --data-root <.../malaria_dl_local_project/data>
    U1B_DATABASE_URL=... python generate_pseudo_masks.py generate --data-root <...> [--out <dir>] [--limit N]
    U1B_DATABASE_URL=... python generate_pseudo_masks.py verify   --data-root <...> [--out <dir>]
"""

import argparse
import csv
import hashlib
import io
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from sqlalchemy import create_engine, text

import masks
from masks import FROZEN_PSEUDO_MASK, generate_frozen_pseudo_mask, method_spec

DATASET_VERSION_ID = "d8c0cab5-09dd-597f-9de7-7ca01aee2ec2"
MATERIALIZATION_ROOT = f"malaria_dataset_versions/{DATASET_VERSION_ID}"
DERIVED_ROOT = f"derived/pseudo_masks/{DATASET_VERSION_ID}/stain_morph_v2"
EXPECTED_COUNTS = {"train": 22180, "val": 2693, "test": 2685}
EXPECTED_IMPLEMENTATION_SHA256 = "65603c61c4925345d83ca305e5d097514679e54b1aea0159e63bfac7f9be24e9"
EXPECTED_SPEC_SHA256 = "4a84ad75d71dacf8f3d9c79d9de668ed57db176b09d2b265fd55c00ebbca078b"
REPRODUCIBILITY_SAMPLE_PER_SPLIT = 100
REPRODUCIBILITY_SEED = "u1c-repro-2026-10-02"

MANIFEST_FIELDS = (
    "dataset_version_id",
    "source_record_id",
    "source_filename",
    "split_name",
    "class_name",
    "patient",
    "source_path",
    "source_sha256",
    "mask_path",
    "mask_sha256",
    "mask_pixel_sha256",
    "mask_width",
    "mask_height",
    "foreground_pixels",
    "foreground_fraction",
    "empty_mask",
    "method_name",
    "method_version",
    "stain_delta",
    "implementation_sha256",
    "spec_sha256",
)

QUERY = text(
    """
    SELECT a.source_record_id::text AS source_record_id,
           r.source_filename,
           a.split_name,
           a.class_name,
           ci.source_identifier       AS patient,
           r.source_file_sha256,
           r.image_width,
           r.image_height
    FROM dataset_split_assignments a
    JOIN dataset_source_records r ON r.id = a.source_record_id
    JOIN clinical_identities ci   ON ci.id = a.clinical_identity_id
    WHERE a.dataset_version_id = :dataset_version_id
    ORDER BY a.split_name, a.source_record_id
    """
)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def generator_identity():
    implementation = sha256_bytes(Path(masks.__file__).read_bytes())
    spec = method_spec(FROZEN_PSEUDO_MASK["method"], FROZEN_PSEUDO_MASK["parameters"])
    spec_sha = sha256_bytes(json.dumps(spec, sort_keys=True, separators=(",", ":")).encode())
    return {
        "method_name": spec["method_name"],
        "method_version": spec["method_version"],
        "implementation_version": spec["implementation_version"],
        "stain_delta": spec["parameters"]["stain_delta"],
        "parameters": spec["parameters"],
        "implementation_sha256": implementation,
        "spec_sha256": spec_sha,
    }


def load_assignments():
    engine = create_engine(os.environ["U1B_DATABASE_URL"], future=True)
    try:
        with engine.connect() as connection, connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            return [dict(r) for r in connection.execute(QUERY, {"dataset_version_id": DATASET_VERSION_ID}).mappings()]
    finally:
        engine.dispose()


def source_relative(row):
    # The materialized layout stores RGB under its class directory; the path is
    # used only to open the file. The generator receives pixels only.
    return f"{MATERIALIZATION_ROOT}/{row['split_name']}/{row['class_name']}/{row['source_filename']}"


def mask_relative(row):
    return f"{DERIVED_ROOT}/{row['split_name']}/{row['source_record_id']}.png"


def encode_mask(mask):
    buffer = io.BytesIO()
    Image.fromarray(np.where(mask, 255, 0).astype(np.uint8), mode="L").save(buffer, format="PNG", optimize=False)
    return buffer.getvalue()


def pixel_sha(mask_bool):
    return sha256_bytes(np.ascontiguousarray(mask_bool, dtype=np.uint8).tobytes() + str(mask_bool.shape).encode())


def fail(code, detail=""):
    print(f"STOP {code} {detail}".rstrip())
    sys.exit(2)


# ------------------------------------------------------------------- precheck
def precheck(data_root, rows, out_root, *, check_sources=True):
    report = {}
    identity = generator_identity()
    if identity["implementation_sha256"] != EXPECTED_IMPLEMENTATION_SHA256:
        fail("IMPLEMENTATION_SHA256_MISMATCH", identity["implementation_sha256"])
    if identity["spec_sha256"] != EXPECTED_SPEC_SHA256:
        fail("SPEC_SHA256_MISMATCH", identity["spec_sha256"])
    report["generator"] = identity

    counts = {s: sum(r["split_name"] == s for r in rows) for s in EXPECTED_COUNTS}
    report["counts"] = counts | {"total": len(rows)}
    if set(r["split_name"] for r in rows) - set(EXPECTED_COUNTS):
        fail("UNKNOWN_SPLIT")
    if counts != EXPECTED_COUNTS or len(rows) != sum(EXPECTED_COUNTS.values()):
        fail("COUNT_MISMATCH", json.dumps(report["counts"]))
    ids = [r["source_record_id"] for r in rows]
    if len(set(ids)) != len(ids):
        fail("DUPLICATE_SOURCE_RECORD_ID")
    report["unique_source_record_ids"] = len(set(ids))

    materialization = (data_root / MATERIALIZATION_ROOT).resolve()
    out_resolved = out_root.resolve()
    if out_resolved == materialization or out_resolved.is_relative_to(materialization):
        fail("OUTPUT_INSIDE_GOVERNED_MATERIALIZATION")
    report["output_outside_materialization"] = True

    if check_sources:
        missing, sha_mismatch = [], []
        for r in rows:
            path = data_root / source_relative(r)
            if not path.is_file():
                missing.append(r["source_record_id"])
                continue
            if sha256_bytes(path.read_bytes()) != r["source_file_sha256"]:
                sha_mismatch.append(r["source_record_id"])
        report["rgb_missing"] = len(missing)
        report["rgb_sha256_mismatch_vs_postgresql"] = len(sha_mismatch)
        if missing or sha_mismatch:
            fail("RGB_SOURCE_INVALID", json.dumps(report))
    return report


# ------------------------------------------------------------------- generate
def generate(data_root, rows, out_root, limit=None):
    identity = generator_identity()
    if limit:
        by_split = {}
        for r in rows:
            by_split.setdefault(r["split_name"], []).append(r)
        rows = [r for s in sorted(by_split) for r in by_split[s][:limit]]
    staging = out_root.with_name(out_root.name + ".staging")
    if out_root.exists():
        fail("OUTPUT_EXISTS", str(out_root))
    if staging.exists():
        fail("STAGING_EXISTS", str(staging))
    for split in EXPECTED_COUNTS:
        (staging / split).mkdir(parents=True)

    manifest = []
    for i, r in enumerate(rows, 1):
        source = data_root / source_relative(r)
        raw = source.read_bytes()
        rgb = np.asarray(Image.open(io.BytesIO(raw)).convert("RGB"))
        mask = generate_frozen_pseudo_mask(rgb)  # pixels only
        if mask.dtype != bool or mask.shape != rgb.shape[:2]:
            fail("GENERATOR_CONTRACT_VIOLATION", r["source_record_id"])
        encoded = encode_mask(mask)
        relative = mask_relative(r)
        (staging / r["split_name"] / f"{r['source_record_id']}.png").write_bytes(encoded)
        fg = int(mask.sum())
        manifest.append(
            {
                "dataset_version_id": DATASET_VERSION_ID,
                "source_record_id": r["source_record_id"],
                "source_filename": r["source_filename"],
                "split_name": r["split_name"],
                "class_name": r["class_name"],
                "patient": r["patient"],
                "source_path": source_relative(r),
                "source_sha256": sha256_bytes(raw),
                "mask_path": relative,
                "mask_sha256": sha256_bytes(encoded),
                "mask_pixel_sha256": pixel_sha(mask),
                "mask_width": mask.shape[1],
                "mask_height": mask.shape[0],
                "foreground_pixels": fg,
                "foreground_fraction": f"{fg / mask.size:.8f}",
                "empty_mask": int(fg == 0),
                "method_name": identity["method_name"],
                "method_version": identity["method_version"],
                "stain_delta": identity["stain_delta"],
                "implementation_sha256": identity["implementation_sha256"],
                "spec_sha256": identity["spec_sha256"],
            }
        )
        if i % 2000 == 0:
            print(f"{i}/{len(rows)}", flush=True)

    with (staging / "manifest.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(manifest)
    manifest_sha = sha256_bytes((staging / "manifest.csv").read_bytes())
    (staging / "generator.json").write_text(
        json.dumps(
            {
                "dataset_version_id": DATASET_VERSION_ID,
                "source_materialization_root": MATERIALIZATION_ROOT,
                "artifact": "stain-derived pseudo-masks (PNG, L mode, 0=background, 255=foreground, source resolution)",
                "generator": identity,
                "entry_point": "masks.generate_frozen_pseudo_mask(image)",
                "record_count": len(manifest),
                "manifest_sha256": manifest_sha,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    staging.rename(out_root)
    print(f"generated {len(manifest)} pseudo-masks -> {out_root} (manifest sha256 {manifest_sha})")


# ------------------------------------------------------------------- verify
def verify(data_root, rows, out_root):
    with (out_root / "manifest.csv").open(newline="") as handle:
        manifest = list(csv.DictReader(handle))
    generator = json.loads((out_root / "generator.json").read_text())
    identity = generator_identity()
    result = {"manifest_rows": len(manifest)}
    result["manifest_sha256_matches_generator_json"] = (
        sha256_bytes((out_root / "manifest.csv").read_bytes()) == generator["manifest_sha256"]
    )

    expected = {r["source_record_id"]: r for r in rows}
    ids = [m["source_record_id"] for m in manifest]
    paths = [m["mask_path"] for m in manifest]
    coverage = {}
    for split, n in EXPECTED_COUNTS.items():
        have = {m["source_record_id"] for m in manifest if m["split_name"] == split}
        want = {r["source_record_id"] for r in rows if r["split_name"] == split}
        files = {p.stem for p in (out_root / split).glob("*.png")}
        coverage[split] = {
            "expected": n,
            "manifest_rows": sum(m["split_name"] == split for m in manifest),
            "mask_files": len(files),
            "missing": len(want - have),
            "unexpected": len(have - want),
            "files_without_manifest_row": len(files - have),
        }
    result["coverage"] = coverage
    result["duplicate_source_record_ids"] = len(ids) - len(set(ids))
    result["duplicate_mask_paths"] = len(paths) - len(set(paths))

    problems = {
        "missing_file": 0,
        "hash_failure": 0,
        "invalid_binary": 0,
        "dimension_mismatch_vs_source": 0,
        "foreground_count_mismatch": 0,
        "split_or_class_mismatch_vs_postgresql": 0,
        "generator_identity_mismatch": 0,
    }
    for m in manifest:
        src = expected.get(m["source_record_id"])
        if src is None or m["mask_path"] != mask_relative(src) or m["source_path"] != source_relative(src):
            problems["split_or_class_mismatch_vs_postgresql"] += 1
        path = out_root / m["split_name"] / f"{m['source_record_id']}.png"
        if not path.is_file():
            problems["missing_file"] += 1
            continue
        data = path.read_bytes()
        if sha256_bytes(data) != m["mask_sha256"]:
            problems["hash_failure"] += 1
        image = Image.open(io.BytesIO(data))
        array = np.asarray(image)
        if image.mode != "L" or not set(np.unique(array).tolist()) <= {0, 255}:
            problems["invalid_binary"] += 1
        if src is None or (array.shape[1], array.shape[0]) != (src["image_width"], src["image_height"]) \
                or (int(m["mask_width"]), int(m["mask_height"])) != (src["image_width"], src["image_height"]):
            problems["dimension_mismatch_vs_source"] += 1
        if int((array == 255).sum()) != int(m["foreground_pixels"]):
            problems["foreground_count_mismatch"] += 1
        if src is None or (m["split_name"], m["class_name"], m["source_sha256"]) != (
            src["split_name"], src["class_name"], src["source_file_sha256"]
        ):
            problems["split_or_class_mismatch_vs_postgresql"] += 1
        if (m["implementation_sha256"], m["spec_sha256"], m["method_name"], m["method_version"], float(m["stain_delta"])) != (
            identity["implementation_sha256"], identity["spec_sha256"], identity["method_name"],
            str(identity["method_version"]), identity["stain_delta"],
        ):
            problems["generator_identity_mismatch"] += 1
    result["integrity"] = problems

    # Deterministic regeneration on a fixed per-split sample.
    sample = []
    for split in EXPECTED_COUNTS:
        rows_split = sorted(
            (m for m in manifest if m["split_name"] == split),
            key=lambda m: sha256_bytes((REPRODUCIBILITY_SEED + m["source_record_id"]).encode()),
        )
        sample.extend(rows_split[:REPRODUCIBILITY_SAMPLE_PER_SPLIT])
    mismatches = 0
    for m in sample:
        rgb = np.asarray(Image.open(data_root / m["source_path"]).convert("RGB"))
        mask = generate_frozen_pseudo_mask(rgb)
        if sha256_bytes(encode_mask(mask)) != m["mask_sha256"] or pixel_sha(mask) != m["mask_pixel_sha256"]:
            mismatches += 1
    result["reproducibility"] = {
        "sample_size": len(sample),
        "per_split": REPRODUCIBILITY_SAMPLE_PER_SPLIT,
        "selection": f"sha256('{REPRODUCIBILITY_SEED}' || source_record_id) order",
        "mismatches": mismatches,
    }

    descriptive = {}
    for split in ("train", "val"):  # TEST: coverage and integrity only
        ff = np.array([float(m["foreground_fraction"]) for m in manifest if m["split_name"] == split])
        empty = np.array([m["empty_mask"] == "1" for m in manifest if m["split_name"] == split])
        nonempty = ff[~empty]
        descriptive[split] = {
            "masks": int(len(ff)),
            "empty_mask_count": int(empty.sum()),
            "empty_mask_rate": float(empty.mean()),
            "foreground_fraction_median_nonempty": float(np.median(nonempty)),
            "foreground_fraction_p10_p90_nonempty": [float(np.percentile(nonempty, q)) for q in (10, 90)],
        }
    result["descriptive_train_val"] = descriptive
    ok = (
        all(c["missing"] == c["unexpected"] == c["files_without_manifest_row"] == 0 and c["manifest_rows"] == c["mask_files"] == c["expected"] for c in coverage.values())
        and result["duplicate_source_record_ids"] == result["duplicate_mask_paths"] == 0
        and not any(problems.values())
        and mismatches == 0
        and result["manifest_sha256_matches_generator_json"]
    )
    result["status"] = "PASS" if ok else "FAIL"
    print(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("precheck", "generate", "verify"))
    parser.add_argument("--data-root", required=True, help="malaria_dl_local_project/data")
    parser.add_argument("--out", help="override output directory (smoke runs)")
    parser.add_argument("--limit", type=int, help="records per split (smoke run)")
    parser.add_argument("--report", help="write the command result as JSON")
    args = parser.parse_args()
    data_root = Path(args.data_root).resolve()
    out_root = Path(args.out).resolve() if args.out else data_root / DERIVED_ROOT
    rows = load_assignments()
    if args.command == "precheck":
        result = precheck(data_root, rows, out_root)
        print(json.dumps(result, indent=2))
    elif args.command == "generate":
        precheck(data_root, rows, out_root, check_sources=False)
        generate(data_root, rows, out_root, args.limit)
        return
    else:
        result = verify(data_root, rows, out_root)
    if args.report:
        Path(args.report).write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
