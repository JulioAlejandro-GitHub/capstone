"""Deterministic TRAIN-only audit sample from the governed dataset version.

Reads PostgreSQL in a READ ONLY transaction and writes one CSV manifest.
The class is used only to stratify the audit sample; it never reaches
masks.generate_mask.

Usage:
    U1B_DATABASE_URL=postgresql+psycopg://user:pass@127.0.0.1:5432/malaria_experiments \
    python sample.py --data-root <.../malaria_dataset_versions/d8c0...> --out results/u1b/sample_manifest.csv
"""

import argparse
import csv
import os
from pathlib import Path

from sqlalchemy import create_engine, text

DATASET_VERSION_ID = "d8c0cab5-09dd-597f-9de7-7ca01aee2ec2"
SPLIT = "train"
SEED = "u1b-2026-10-02"
PER_CLASS = 100

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
      AND a.class_name = :class_name
    ORDER BY md5(:seed || a.source_record_id::text)
    LIMIT :per_class
    """
)


def build_sample(database_url, data_root):
    engine = create_engine(database_url, future=True)
    rows = []
    try:
        with engine.connect() as connection, connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            for class_name in ("parasitized", "uninfected"):
                rows.extend(
                    dict(r)
                    for r in connection.execute(
                        QUERY,
                        dict(
                            dataset_version_id=DATASET_VERSION_ID,
                            split=SPLIT,
                            class_name=class_name,
                            seed=SEED,
                            per_class=PER_CLASS,
                        ),
                    ).mappings()
                )
    finally:
        engine.dispose()
    for row in rows:
        path = Path(data_root) / SPLIT / row["class"] / row["source_filename"]
        if not path.is_file():
            raise FileNotFoundError("SAMPLE_FILE_MISSING:" + str(path))
        row["relative_path"] = f"{SPLIT}/{row['class']}/{row['source_filename']}"
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    rows = build_sample(os.environ["U1B_DATABASE_URL"], args.data_root)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} rows, {len({r['patient'] for r in rows})} patients -> {out}")


if __name__ == "__main__":
    main()
