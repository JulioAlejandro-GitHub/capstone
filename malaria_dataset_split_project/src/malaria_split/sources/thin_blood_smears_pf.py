"""Read-only Source Adapter for NIH/NLM ThinBloodSmearsPf (Polygon Set).

Official layout (ReadMe.pdf, verified on the real copy; the real folder is ``Img``):

```text
<root>/Polygon Set/<Patient ID>/Img/<ImageName>.jpg
<root>/Polygon Set/<Patient ID>/GT/<ImageName>.txt
```

The Patient-ID is the patient directory name, verbatim. One source record is one full
smear image plus its Polygon GT. Nothing here touches PostgreSQL or derives tiles.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from malaria_split.families import THIN_BLOOD_SMEARS_PF_SOURCE_NAME, DatasetFamily

from .polygon_set import PolygonParseError, parse_polygon_file


SOURCE_SLUG = "thin_blood_smears_pf"
SOURCE_NAME = THIN_BLOOD_SMEARS_PF_SOURCE_NAME
SOURCE_PROVIDER = "NLM/LHNCBC"
SOURCE_REFERENCE = "https://data.lhncbc.nlm.nih.gov/public/Malaria/NIH-NLM-ThinBloodSmearsPf/"
ADAPTER_VERSION = "1.0.0"
POLYGON_SET_DIR = "Polygon Set"
IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg"})
ANNOTATION_SUFFIX = ".txt"
IGNORED_FILENAMES = frozenset({"thumbs.db", ".ds_store"})
PROVENANCE_FILES = ("ReadMe.pdf", "Data License Agreement.docx", "Dataset_statistics.xlsx")
EXIF_ORIENTATION_TAG = 274


@dataclass(frozen=True, slots=True)
class SourceIssue:
    code: str
    path: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class SmearSourceRecord:
    patient_id: str
    image_relative_path: str
    image_sha256: str
    image_size_bytes: int
    image_width: int
    image_height: int
    annotation_relative_path: str
    annotation_sha256: str
    annotation_size_bytes: int
    polygon_count: int
    rbc_count: int
    wbc_count: int
    label_counts: dict[str, int]

    @property
    def image_filename(self) -> str:
        return self.image_relative_path.rsplit("/", 1)[-1]

    @property
    def source_record_key(self) -> str:
        return f"nih_nlm_thin_blood_smears_pf:polygon_set/{self.patient_id}/{self.image_filename}"


@dataclass(frozen=True, slots=True)
class SmearSourceInspection:
    records: tuple[SmearSourceRecord, ...]
    issues: tuple[SourceIssue, ...]
    ignored_files: tuple[str, ...]
    images_found: int
    annotations_found: int
    provenance_sha256: dict[str, str | None] = field(default_factory=dict)

    @property
    def patients(self) -> tuple[str, ...]:
        return tuple(sorted({record.patient_id for record in self.records}))

    @property
    def contract_passed(self) -> bool:
        return bool(self.records) and not self.issues

    @property
    def population_fingerprint(self) -> str:
        digest = hashlib.sha256()
        for record in sorted(self.records, key=lambda item: item.image_relative_path):
            digest.update("|".join((
                record.patient_id, record.image_relative_path, record.image_sha256,
                record.annotation_relative_path, record.annotation_sha256,
            )).encode())
            digest.update(b"\n")
        return digest.hexdigest()

    def report(self) -> dict[str, Any]:
        codes = Counter(issue.code for issue in self.issues)
        per_patient = Counter(record.patient_id for record in self.records)
        labels: Counter[str] = Counter()
        for record in self.records:
            labels.update(record.label_counts)
        return {
            "dataset_family": DatasetFamily.SMEAR_SEGMENTATION.value,
            "source_name": SOURCE_NAME,
            "source_slug": SOURCE_SLUG,
            "adapter_version": ADAPTER_VERSION,
            "ground_truth": "Polygon Set",
            "source_unit": "full_smear_image",
            "patients_found": len(per_patient),
            "images_found": self.images_found,
            "annotations_found": self.annotations_found,
            "valid_source_records": len(self.records),
            "images_without_annotation": codes["IMAGE_WITHOUT_ANNOTATION"],
            "annotations_without_image": codes["ANNOTATION_WITHOUT_IMAGE"],
            "invalid_annotations": codes["INVALID_ANNOTATION"],
            "duplicate_images": codes["DUPLICATE_IMAGE"],
            "ambiguous_associations": codes["AMBIGUOUS_ASSOCIATION"],
            "ambiguous_patient_ids": codes["AMBIGUOUS_PATIENT_ID"],
            "structure_issues": codes["STRUCTURE_INVALID"],
            "unexpected_files": codes["UNEXPECTED_FILE"],
            "ignored_files": len(self.ignored_files),
            "images_per_patient": {
                "min": min(per_patient.values(), default=0),
                "max": max(per_patient.values(), default=0),
            },
            "polygons": {
                "total": sum(record.polygon_count for record in self.records),
                "rbc": sum(record.rbc_count for record in self.records),
                "wbc": sum(record.wbc_count for record in self.records),
                "by_label": dict(sorted(labels.items())),
            },
            "population_fingerprint_sha256": self.population_fingerprint,
            "provenance_sha256": self.provenance_sha256,
            "issues": [
                {"code": issue.code, "path": issue.path, "detail": issue.detail}
                for issue in self.issues
            ],
            "contract_status": "PASS" if self.contract_passed else "FAIL",
        }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cell_images_candidate_identifier(patient_id: str) -> str:
    """Unverified hint: Polygon Set IDs look like ``<n>`` + an NLM cell-images Patient-ID."""
    return re.sub(r"^\d+", "", patient_id)


def _single_child_dir(
    patient_dir: Path, name: str, root: Path, issues: list[SourceIssue]
) -> Path | None:
    matches = [item for item in patient_dir.iterdir() if item.is_dir() and item.name.casefold() == name]
    if len(matches) != 1:
        issues.append(SourceIssue(
            "STRUCTURE_INVALID", patient_dir.relative_to(root).as_posix(),
            f"expected exactly one {name!r} directory, found {len(matches)}",
        ))
        return None
    return matches[0]


def _files_by_stem(
    directory: Path, suffixes: frozenset[str], root: Path,
    issues: list[SourceIssue], ignored: list[str],
) -> dict[str, Path]:
    grouped: dict[str, list[Path]] = defaultdict(list)
    for item in sorted(directory.iterdir()):
        relative = item.relative_to(root).as_posix()
        if item.is_file() and item.name.casefold() in IGNORED_FILENAMES:
            ignored.append(relative)
        elif item.is_file() and item.suffix.casefold() in suffixes:
            grouped[item.stem.casefold()].append(item)
        else:
            issues.append(SourceIssue("UNEXPECTED_FILE", relative))
    result: dict[str, Path] = {}
    for stem, paths in grouped.items():
        if len(paths) > 1:
            issues.append(SourceIssue(
                "AMBIGUOUS_ASSOCIATION", directory.relative_to(root).as_posix(),
                f"stem {stem!r} matches {[path.name for path in paths]}",
            ))
        else:
            result[stem] = paths[0]
    return result


def inspect_thin_blood_smears_pf(root: Path) -> SmearSourceInspection:
    """Discover patients, full smear images and Polygon GT under a local dataset copy."""
    root = root.expanduser().resolve()
    issues: list[SourceIssue] = []
    ignored: list[str] = []
    records: list[SmearSourceRecord] = []
    images_found = 0
    annotations_found = 0
    polygon_root = root / POLYGON_SET_DIR
    provenance = {
        name: file_sha256(root / name) if (root / name).is_file() else None
        for name in PROVENANCE_FILES
    }
    if not polygon_root.is_dir():
        issues.append(SourceIssue("STRUCTURE_INVALID", POLYGON_SET_DIR, "directory not found"))
        return SmearSourceInspection((), tuple(issues), (), 0, 0, provenance)

    patient_dirs: list[Path] = []
    for item in sorted(polygon_root.iterdir()):
        relative = item.relative_to(root).as_posix()
        if item.is_dir():
            patient_dirs.append(item)
        elif item.name.casefold() in IGNORED_FILENAMES:
            ignored.append(relative)
        else:
            issues.append(SourceIssue("UNEXPECTED_FILE", relative))
    folded = Counter(item.name.casefold() for item in patient_dirs)
    for patient_dir in patient_dirs:
        patient_id = patient_dir.name
        if folded[patient_id.casefold()] > 1 or patient_id != patient_id.strip():
            issues.append(SourceIssue(
                "AMBIGUOUS_PATIENT_ID", patient_dir.relative_to(root).as_posix()
            ))
            continue
        image_dir = _single_child_dir(patient_dir, "img", root, issues)
        gt_dir = _single_child_dir(patient_dir, "gt", root, issues)
        for item in patient_dir.iterdir():
            if item not in (image_dir, gt_dir) and item.name.casefold() not in ("img", "gt"):
                relative = item.relative_to(root).as_posix()
                if item.name.casefold() in IGNORED_FILENAMES:
                    ignored.append(relative)
                else:
                    issues.append(SourceIssue("UNEXPECTED_FILE", relative))
        if image_dir is None or gt_dir is None:
            continue
        images = _files_by_stem(image_dir, IMAGE_SUFFIXES, root, issues, ignored)
        annotations = _files_by_stem(
            gt_dir, frozenset({ANNOTATION_SUFFIX}), root, issues, ignored
        )
        images_found += len(images)
        annotations_found += len(annotations)
        for stem in sorted(set(annotations) - set(images)):
            issues.append(SourceIssue(
                "ANNOTATION_WITHOUT_IMAGE", annotations[stem].relative_to(root).as_posix()
            ))
        for stem in sorted(images):
            image_path = images[stem]
            image_relative = image_path.relative_to(root).as_posix()
            if stem not in annotations:
                issues.append(SourceIssue("IMAGE_WITHOUT_ANNOTATION", image_relative))
                continue
            annotation_path = annotations[stem]
            with Image.open(image_path) as image:
                width, height = image.size
                orientation = image.getexif().get(EXIF_ORIENTATION_TAG)
            if orientation not in (None, 1):
                # GT coordinates are in stored-pixel space; a rotation tag makes it ambiguous.
                issues.append(SourceIssue(
                    "EXIF_ORIENTATION_PRESENT", image_relative, f"orientation={orientation}"
                ))
                continue
            try:
                annotation = parse_polygon_file(annotation_path, image_size=(width, height))
            except PolygonParseError as error:
                issues.append(SourceIssue(
                    "INVALID_ANNOTATION", annotation_path.relative_to(root).as_posix(),
                    f"{error.code}: {error.detail}",
                ))
                continue
            records.append(SmearSourceRecord(
                patient_id=patient_id,
                image_relative_path=image_relative,
                image_sha256=file_sha256(image_path),
                image_size_bytes=image_path.stat().st_size,
                image_width=width,
                image_height=height,
                annotation_relative_path=annotation_path.relative_to(root).as_posix(),
                annotation_sha256=file_sha256(annotation_path),
                annotation_size_bytes=annotation_path.stat().st_size,
                polygon_count=len(annotation.polygons),
                rbc_count=annotation.rbc_count,
                wbc_count=annotation.wbc_count,
                label_counts=annotation.label_counts,
            ))

    seen: dict[str, str] = {}
    for record in records:
        if record.image_sha256 in seen:
            issues.append(SourceIssue(
                "DUPLICATE_IMAGE", record.image_relative_path,
                f"same sha256 as {seen[record.image_sha256]}",
            ))
        else:
            seen[record.image_sha256] = record.image_relative_path
    return SmearSourceInspection(
        tuple(sorted(records, key=lambda item: item.image_relative_path)),
        tuple(issues), tuple(sorted(ignored)), images_found, annotations_found, provenance,
    )
