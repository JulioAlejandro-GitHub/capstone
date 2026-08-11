import ast
import csv
import hashlib
from collections import defaultdict
from pathlib import Path

from PIL import Image

from .identity_evidence import EvidenceType, SourceIdentityRecord


def decoded_pixel_key(path: Path | str) -> str:
    """Hash exact decoded RGB pixels together with shape; never mutates the image."""
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        payload = rgb.tobytes()
        digest = hashlib.sha256(payload).hexdigest()
        return f"{rgb.width}x{rgb.height}x3:{digest}"


def load_official_patient_mapping(paths: list[Path]) -> tuple[dict[str, set[str]], list[str]]:
    filename_to_patients: dict[str, set[str]] = defaultdict(set)
    errors: list[str] = []
    for path in paths:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            for line_number, row in enumerate(csv.reader(handle), start=1):
                if len(row) < 2 or not row[0].strip():
                    errors.append(f"invalid_mapping_row:{path.name}:{line_number}")
                    continue
                patient_id = row[0].strip()
                serialized = ",".join(part for part in row[1:] if part.strip())
                try:
                    filenames = ast.literal_eval(serialized)
                except (ValueError, SyntaxError):
                    errors.append(f"invalid_filename_list:{path.name}:{line_number}")
                    continue
                if not isinstance(filenames, list):
                    errors.append(f"invalid_filename_list:{path.name}:{line_number}")
                    continue
                for filename in filenames:
                    filename_to_patients[str(filename)].add(patient_id)
    return dict(filename_to_patients), errors


def build_source_identity_index(
    original_root: Path,
    official_mapping_paths: list[Path],
) -> tuple[dict[str, list[SourceIdentityRecord]], dict]:
    filename_to_patients, errors = load_official_patient_mapping(official_mapping_paths)
    index: dict[str, list[SourceIdentityRecord]] = defaultdict(list)
    source_files = sorted(original_root.glob("*/*.png"))
    missing_metadata = 0
    for path in source_files:
        class_name = path.parent.name.lower()
        patients = filename_to_patients.get(path.name, set())
        if not patients:
            missing_metadata += 1
        key = decoded_pixel_key(path)
        for patient_id in sorted(patients) or [None]:
            index[key].append(
                SourceIdentityRecord(
                    source_record_id=f"{class_name}/{path.name}",
                    source_filename=path.name,
                    class_name=class_name,
                    patient_id=patient_id,
                    evidence_type=EvidenceType.OFFICIAL_METADATA,
                    evidence_reference=",".join(item.name for item in official_mapping_paths),
                    mapping_key=key,
                )
            )
    collisions = {key: records for key, records in index.items() if len(records) > 1}
    return dict(index), {
        "source_files": len(source_files),
        "official_mapping_filenames": len(filename_to_patients),
        "mapping_errors": errors,
        "source_files_without_official_metadata": missing_metadata,
        "unique_mapping_keys": len(index),
        "colliding_mapping_keys": len(collisions),
        "exact_duplicate_groups": len(collisions),
        "exact_duplicate_records": sum(len(records) for records in collisions.values()),
    }

