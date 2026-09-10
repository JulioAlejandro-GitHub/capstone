"""Read-only verification of the upstream freeze v1 (no split generation).

Wire formats mirror malaria_split.governance.freeze._canonical_digest and
persistence.split_generation._sha256_lines; filename collisions mirror
persistence.materialization.build_materialization_plan. Keep parity tests.
"""

from collections import Counter
import hashlib
from pathlib import Path

from sqlalchemy import text

VERIFIER_VERSION = "ml_dataset_integrity_v1"


def canonical_digest(rows, *, trailing_newline=True):
    lines = [
        "|".join("" if value is None else str(value) for value in row) for row in rows
    ]
    data = "\n".join(lines)
    if trailing_newline and lines:
        data += "\n"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_integrity(connection, version_id, root, contract):
    # Import lazily to keep errors in the public dataset domain.
    from .governed_dataset import GovernedDatasetError

    def require(condition, code):
        if not condition:
            raise GovernedDatasetError(code)

    params = {"id": version_id}
    patients = connection.execute(
        text("""
        SELECT clinical_identity_id,split_name FROM dataset_split_assignments
        WHERE dataset_version_id=:id GROUP BY clinical_identity_id,split_name
        ORDER BY clinical_identity_id,split_name
    """),
        params,
    ).all()
    assignments = connection.execute(
        text("""
        SELECT source_record_id,clinical_identity_id,split_name
        FROM dataset_split_assignments WHERE dataset_version_id=:id ORDER BY source_record_id
    """),
        params,
    ).all()
    sources = connection.execute(
        text("""
        SELECT r.id,r.clinical_identity_id,r.class_name,
               r.source_file_sha256,r.decoded_pixel_sha256
        FROM dataset_source_records r
        JOIN dataset_version_sources vs ON vs.dataset_id=r.dataset_id
        WHERE vs.dataset_version_id=:id ORDER BY r.id
    """),
        params,
    ).all()
    identities = connection.execute(
        text("""
        SELECT i.id,i.source_identifier,i.status FROM clinical_identities i
        JOIN dataset_version_sources vs ON vs.dataset_id=i.dataset_id
        WHERE vs.dataset_version_id=:id ORDER BY i.id
    """),
        params,
    ).all()
    observed = {
        "patient_assignment_sha256": canonical_digest(patients, trailing_newline=False),
        "record_assignment_sha256": canonical_digest(
            assignments, trailing_newline=False
        ),
        "source_population_sha256": canonical_digest(sources),
        "clinical_identity_sha256": canonical_digest(identities),
    }
    for name, value in observed.items():
        require(
            value == contract["fingerprints"][name],
            "DATASET_FINGERPRINT_MISMATCH:" + name,
        )
    require(
        bool(assignments) and len(assignments) == contract.get("assignment_count"),
        "DATASET_ASSIGNMENT_COUNT_MISMATCH",
    )
    require(
        len(sources) == contract.get("source_record_count"),
        "DATASET_SOURCE_COUNT_MISMATCH",
    )
    require(
        len(identities) == contract.get("clinical_identity_count"),
        "DATASET_IDENTITY_COUNT_MISMATCH",
    )
    require(
        len({r[0] for r in assignments}) == len(assignments),
        "DATASET_DUPLICATE_ASSIGNMENT",
    )
    require(len({r[0] for r in patients}) == len(patients), "DATASET_PATIENT_OVERLAP")
    source_map = {r[0]: r for r in sources}
    identity_ids = {r[0] for r in identities}
    require(
        set(source_map) == {r[0] for r in assignments},
        "DATASET_SOURCE_COVERAGE_MISMATCH",
    )
    for record, patient, split in assignments:
        require(
            patient in identity_ids and source_map[record][1] == patient,
            "DATASET_CLINICAL_IDENTITY_MISMATCH",
        )
        require(split in {"train", "val", "test"}, "DATASET_SPLIT_INVALID")
    rows = (
        connection.execute(
            text("""
        SELECT a.source_record_id,a.clinical_identity_id,a.split_name,r.class_name,
               r.source_filename,r.source_file_sha256
        FROM dataset_split_assignments a JOIN dataset_source_records r ON r.id=a.source_record_id
        WHERE a.dataset_version_id=:id ORDER BY a.source_record_id
    """),
            params,
        )
        .mappings()
        .all()
    )
    require(len(rows) == len(assignments), "DATASET_CONTENT_REFERENCE_MISSING")
    collisions = Counter(
        (r["split_name"], r["class_name"], r["source_filename"]) for r in rows
    )
    expected = {}
    counts = Counter()
    for row in rows:
        filename = row["source_filename"]
        require(
            isinstance(filename, str)
            and Path(filename).name == filename
            and filename not in {".", "..", ""},
            "DATASET_FILENAME_INVALID",
        )
        require(
            row["class_name"] in {"parasitized", "uninfected"}, "DATASET_CLASS_INVALID"
        )
        key = (row["split_name"], row["class_name"], filename)
        if collisions[key] > 1:
            filename = f"{row['source_record_id']}__{filename}"
        relative = Path(row["split_name"]) / row["class_name"] / filename
        checksum = row["source_file_sha256"]
        require(
            isinstance(checksum, str) and len(checksum) == 64,
            "DATASET_CONTENT_REFERENCE_MISSING",
        )
        # These file hashes must be part of the independently sealed population.
        require(
            source_map[row["source_record_id"]][3] == checksum,
            "DATASET_CONTENT_REFERENCE_MISMATCH",
        )
        expected[relative.as_posix()] = checksum
        counts[row["split_name"]] += 1
    require(len(expected) == len(rows), "DATASET_PATH_COLLISION")
    actual = {p.relative_to(root).as_posix(): p for p in root.rglob("*") if p.is_file()}
    require(set(actual) == set(expected), "DATASET_CONTENT_SET_MISMATCH")
    for relative, checksum in expected.items():
        require(
            actual[relative].resolve().is_relative_to(root.resolve()),
            "DATASET_PATH_ESCAPE",
        )
        require(
            file_sha256(actual[relative]) == checksum, "DATASET_CONTENT_HASH_MISMATCH"
        )
    require(all(counts[s] > 0 for s in ("train", "val", "test")), "DATASET_SPLIT_EMPTY")
    return dict(counts)
