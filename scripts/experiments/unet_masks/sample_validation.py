"""U1B.1 validation sample: 200 TRAIN images disjoint from U1B in images and patients.

Selection is label-blind (no class filter, no stratification). The class is
fetched only into a separate audit file, validation_labels.csv, which the
blind phase of validate.py never opens.

Usage:
    U1B_DATABASE_URL=... python sample_validation.py --data-root <.../d8c0...> \
        --exclude results/u1b/sample_manifest.csv --out-dir results/u1b_validation
"""

import argparse
import csv
import os
from pathlib import Path

from sqlalchemy import bindparam, create_engine, text

DATASET_VERSION_ID = "d8c0cab5-09dd-597f-9de7-7ca01aee2ec2"
SPLIT = "train"
SEED = "u1b1-2026-10-02"
SIZE = 200

QUERY = text(
    """
    SELECT a.source_record_id::text AS source_record_id,
           r.source_filename,
           ci.source_identifier       AS patient,
           a.split_name               AS split,
           a.class_name               AS class
    FROM dataset_split_assignments a
    JOIN dataset_source_records r ON r.id = a.source_record_id
    JOIN clinical_identities ci   ON ci.id = a.clinical_identity_id
    WHERE a.dataset_version_id = :dataset_version_id
      AND a.split_name = :split
      AND a.source_record_id::text NOT IN :excluded_records
      AND ci.source_identifier NOT IN :excluded_patients
    ORDER BY md5(:seed || a.source_record_id::text)
    LIMIT :size
    """
).bindparams(
    bindparam("excluded_records", expanding=True),
    bindparam("excluded_patients", expanding=True),
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--exclude", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    with open(args.exclude, newline="") as handle:
        previous = list(csv.DictReader(handle))
    engine = create_engine(os.environ["U1B_DATABASE_URL"], future=True)
    try:
        with engine.connect() as connection, connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            rows = [
                dict(r)
                for r in connection.execute(
                    QUERY,
                    dict(
                        dataset_version_id=DATASET_VERSION_ID,
                        split=SPLIT,
                        excluded_records=sorted({r["source_record_id"] for r in previous}),
                        excluded_patients=sorted({r["patient"] for r in previous}),
                        seed=SEED,
                        size=SIZE,
                    ),
                ).mappings()
            ]
    finally:
        engine.dispose()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest, labels = [], []
    for row in rows:
        # The materialized layout stores files under their class directory; the
        # path is only used to open the file, never passed to the generator.
        relative = f"{SPLIT}/{row['class']}/{row['source_filename']}"
        if not (Path(args.data_root) / relative).is_file():
            raise FileNotFoundError("SAMPLE_FILE_MISSING:" + relative)
        manifest.append(
            {k: row[k] for k in ("source_record_id", "source_filename", "patient", "split")}
            | {"relative_path": relative}
        )
        labels.append({"source_record_id": row["source_record_id"], "class": row["class"]})
    for name, data in (("validation_manifest.csv", manifest), ("validation_labels.csv", labels)):
        with (out / name).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)

    overlap_images = len({r["source_record_id"] for r in rows} & {r["source_record_id"] for r in previous})
    overlap_patients = len({r["patient"] for r in rows} & {r["patient"] for r in previous})
    print(
        f"{len(rows)} images, {len({r['patient'] for r in rows})} patients, "
        f"overlap images={overlap_images}, overlap patients={overlap_patients}"
    )


if __name__ == "__main__":
    main()
