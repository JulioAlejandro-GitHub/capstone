import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from sqlalchemy import text

from src.config import (
    CLASS_NAMES,
    LABEL_MAPPING_METADATA,
    LABEL_MAPPING_VERSION,
    NEGATIVE_LABEL,
    PHYSICAL_DATASET_DIR,
    POSITIVE_LABEL,
    PROJECT_ROOT,
    RAW_MODEL_SCORE_MEANING,
    TFDS_ORIGINAL_CLASS_NAMES,
)
from src.db import get_connection


SPLIT_NAMES = ("train", "val", "test")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif"}
DEFAULT_DATASET_NAME = "malaria_physical_split"
DEFAULT_DATASET_SOURCE = "tensorflow_datasets/malaria"
DEFAULT_SOURCE_URL = "https://www.tensorflow.org/datasets/catalog/malaria"
DEFAULT_DATASET_DESCRIPTION = (
    "Dataset de imágenes microscópicas de células sanguíneas clasificadas como "
    "uninfected o parasitized."
)
DATASET_VERSION = f"physical-split-{LABEL_MAPPING_VERSION}"


def resolve_dataset_dir(dataset_dir=None) -> Path:
    if dataset_dir is None:
        return PHYSICAL_DATASET_DIR
    dataset_dir = Path(dataset_dir).expanduser()
    if dataset_dir.is_absolute():
        return dataset_dir
    return PROJECT_ROOT / dataset_dir


def compute_file_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _optional_image_size(path: Path) -> tuple[int | None, int | None]:
    try:
        from PIL import Image

        with Image.open(path) as image:
            return image.size
    except Exception:
        return None, None


def _read_json(path: Path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _to_int(value, default=None):
    if value in (None, ""):
        return default
    return int(value)


def _class_index(class_name: str) -> int:
    if class_name not in CLASS_NAMES:
        raise ValueError(
            f"Clase no soportada: {class_name!r}. Esperado: {CLASS_NAMES}."
        )
    return CLASS_NAMES.index(class_name)


def _original_tfds_label(class_name: str) -> int | None:
    try:
        return TFDS_ORIGINAL_CLASS_NAMES.index(class_name)
    except ValueError:
        return None


def _validate_physical_structure(dataset_dir: Path):
    missing = []
    for split in SPLIT_NAMES:
        for class_name in CLASS_NAMES:
            class_dir = dataset_dir / split / class_name
            if not class_dir.is_dir():
                missing.append(class_dir)
    if missing:
        formatted = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(f"Split físico incompleto:\n{formatted}")


def _manifest_rows(dataset_dir: Path):
    manifest_path = dataset_dir / "files_manifest.csv"
    if not manifest_path.exists():
        return []
    with manifest_path.open(newline="", encoding="utf-8") as file_handle:
        return list(csv.DictReader(file_handle))


def _record_from_manifest_row(row, dataset_dir: Path, metadata: dict, compute_checksum=False):
    relative_path = Path(row["relative_path"])
    absolute_path = dataset_dir / relative_path
    class_name = row.get("class_name") or relative_path.parent.name
    class_index = _to_int(row.get("class_index"), _class_index(class_name))
    project_label = _to_int(row.get("project_label"), class_index)
    width = _to_int(row.get("image_width"))
    height = _to_int(row.get("image_height"))
    if width is None or height is None:
        width, height = _optional_image_size(absolute_path)

    return {
        "split_name": row.get("split") or relative_path.parts[0],
        "class_name": class_name,
        "class_index": int(class_index),
        "project_label": int(project_label),
        "relative_path": relative_path.as_posix(),
        "absolute_path": str(absolute_path),
        "filename": absolute_path.name,
        "original_tfds_label": _to_int(
            row.get("original_tfds_label"),
            _original_tfds_label(class_name),
        ),
        "label_mapping_version": metadata.get(
            "label_mapping_version",
            LABEL_MAPPING_VERSION,
        ),
        "image_width": width,
        "image_height": height,
        "file_size_bytes": absolute_path.stat().st_size if absolute_path.exists() else None,
        "checksum_sha256": compute_file_checksum(absolute_path)
        if compute_checksum and absolute_path.exists()
        else None,
        "metadata": {
            "source": "files_manifest.csv",
            "split_type": metadata.get("split_type", "physical_stratified_split"),
            "train_ratio": metadata.get("train_ratio"),
            "val_ratio": metadata.get("val_ratio"),
            "test_ratio": metadata.get("test_ratio"),
            "seed": metadata.get("seed"),
            "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
            "label_mapping": LABEL_MAPPING_METADATA,
        },
    }


def _record_from_file(path: Path, dataset_dir: Path, metadata: dict, compute_checksum=False):
    relative_path = path.relative_to(dataset_dir)
    split_name = relative_path.parts[0]
    class_name = relative_path.parts[1]
    class_index = _class_index(class_name)
    width, height = _optional_image_size(path)
    return {
        "split_name": split_name,
        "class_name": class_name,
        "class_index": class_index,
        "project_label": class_index,
        "relative_path": relative_path.as_posix(),
        "absolute_path": str(path),
        "filename": path.name,
        "original_tfds_label": _original_tfds_label(class_name),
        "label_mapping_version": metadata.get(
            "label_mapping_version",
            LABEL_MAPPING_VERSION,
        ),
        "image_width": width,
        "image_height": height,
        "file_size_bytes": path.stat().st_size,
        "checksum_sha256": compute_file_checksum(path) if compute_checksum else None,
        "metadata": {
            "source": "filesystem_scan",
            "split_type": metadata.get("split_type", "physical_stratified_split"),
            "train_ratio": metadata.get("train_ratio"),
            "val_ratio": metadata.get("val_ratio"),
            "test_ratio": metadata.get("test_ratio"),
            "seed": metadata.get("seed"),
            "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
            "label_mapping": LABEL_MAPPING_METADATA,
        },
    }


def scan_physical_split(dataset_dir: Path, compute_checksum=False) -> list[dict]:
    dataset_dir = resolve_dataset_dir(dataset_dir).resolve()
    if not dataset_dir.exists():
        raise FileNotFoundError(f"No existe el directorio del split físico: {dataset_dir}")
    _validate_physical_structure(dataset_dir)
    metadata = _read_json(dataset_dir / "metadata.json")

    manifest = _manifest_rows(dataset_dir)
    if manifest:
        records = [
            _record_from_manifest_row(
                row,
                dataset_dir=dataset_dir,
                metadata=metadata,
                compute_checksum=compute_checksum,
            )
            for row in manifest
        ]
    else:
        image_paths = []
        for split in SPLIT_NAMES:
            for class_name in CLASS_NAMES:
                image_paths.extend(
                    sorted(
                        path
                        for path in (dataset_dir / split / class_name).rglob("*")
                        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
                    )
                )
        records = [
            _record_from_file(
                path,
                dataset_dir=dataset_dir,
                metadata=metadata,
                compute_checksum=compute_checksum,
            )
            for path in image_paths
        ]

    return sorted(
        records,
        key=lambda item: (
            SPLIT_NAMES.index(item["split_name"])
            if item["split_name"] in SPLIT_NAMES
            else 99,
            item["class_index"],
            item["relative_path"],
        ),
    )


def summarize_records(records: list[dict]) -> dict:
    summary = defaultdict(Counter)
    total = 0
    for record in records:
        summary[record["split_name"]][record["class_name"]] += 1
        summary[record["split_name"]]["total"] += 1
        total += 1
    return {
        **{
            split: {
                NEGATIVE_LABEL: int(summary[split][NEGATIVE_LABEL]),
                POSITIVE_LABEL: int(summary[split][POSITIVE_LABEL]),
                "total": int(summary[split]["total"]),
            }
            for split in SPLIT_NAMES
        },
        "total": int(total),
    }


def _json(value, default=None):
    if value is None:
        value = {} if default is None else default
    return json.dumps(value, ensure_ascii=False)


def _split_metadata(dataset_dir, records, source_url, description):
    metadata = _read_json(Path(dataset_dir) / "metadata.json")
    summary = summarize_records(records)
    return {
        "source": "src.dataset_registry",
        "source_url": source_url,
        "description": description,
        "split_type": metadata.get("split_type", "physical_stratified_split"),
        "train_ratio": metadata.get("train_ratio", 0.8),
        "val_ratio": metadata.get("val_ratio", 0.1),
        "test_ratio": metadata.get("test_ratio", 0.1),
        "seed": metadata.get("seed", 42),
        "split_counts": summary,
        "label_mapping_version": LABEL_MAPPING_VERSION,
        "label_mapping": LABEL_MAPPING_METADATA,
        "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
        "physical_split_structure": {
            "metadata": "metadata.json",
            "summary": "split_summary.csv",
            "manifest": "files_manifest.csv",
            "splits": list(SPLIT_NAMES),
            "classes": CLASS_NAMES,
        },
    }


def _ensure_dataset(
    connection,
    dataset_name,
    dataset_source,
    dataset_dir,
    records,
    source_url=DEFAULT_SOURCE_URL,
    description=DEFAULT_DATASET_DESCRIPTION,
):
    registry_metadata = _split_metadata(dataset_dir, records, source_url, description)
    row = connection.execute(
        text(
            """
            SELECT id
            FROM datasets
            WHERE name = :name
              AND COALESCE(source, '') = COALESCE(:source, '')
            LIMIT 1
            """
        ),
        {"name": dataset_name, "source": dataset_source},
    ).first()
    if row:
        connection.execute(
            text(
                """
                UPDATE datasets
                SET
                    description = COALESCE(NULLIF(:description, ''), description),
                    total_images = :total_images,
                    num_classes = :num_classes,
                    class_names = :class_names,
                    class_distribution = CAST(:class_distribution AS jsonb),
                    url = COALESCE(NULLIF(:source_url, ''), url),
                    local_path = :local_path,
                    metadata = metadata || CAST(:metadata AS jsonb)
                WHERE id = :dataset_id
                """
            ),
            {
                "dataset_id": str(row[0]),
                "description": description,
                "total_images": registry_metadata["split_counts"]["total"],
                "num_classes": len(CLASS_NAMES),
                "class_names": CLASS_NAMES,
                "class_distribution": _json(
                    {
                        NEGATIVE_LABEL: sum(
                            registry_metadata["split_counts"][split][NEGATIVE_LABEL]
                            for split in SPLIT_NAMES
                        ),
                        POSITIVE_LABEL: sum(
                            registry_metadata["split_counts"][split][POSITIVE_LABEL]
                            for split in SPLIT_NAMES
                        ),
                    }
                ),
                "source_url": source_url,
                "local_path": str(dataset_dir),
                "metadata": _json(registry_metadata),
            },
        )
        return str(row[0])

    inserted = connection.execute(
        text(
            """
            INSERT INTO datasets (
                name, source, version, description, total_images, num_classes,
                class_names, class_distribution, url, local_path, metadata
            )
            VALUES (
                :name, :source, :version, :description, :total_images, :num_classes,
                :class_names, CAST(:class_distribution AS jsonb), :source_url,
                :local_path, CAST(:metadata AS jsonb)
            )
            RETURNING id
            """
        ),
        {
            "name": dataset_name,
            "source": dataset_source,
            "version": DATASET_VERSION,
            "description": description,
            "total_images": registry_metadata["split_counts"]["total"],
            "num_classes": len(CLASS_NAMES),
            "class_names": CLASS_NAMES,
            "class_distribution": _json(
                {
                    NEGATIVE_LABEL: sum(
                        registry_metadata["split_counts"][split][NEGATIVE_LABEL]
                        for split in SPLIT_NAMES
                    ),
                    POSITIVE_LABEL: sum(
                        registry_metadata["split_counts"][split][POSITIVE_LABEL]
                        for split in SPLIT_NAMES
                    ),
                }
            ),
            "source_url": source_url,
            "local_path": str(dataset_dir),
            "metadata": _json(registry_metadata),
        },
    ).first()
    return str(inserted[0]) if inserted else None


def build_dataset_image_params(
    record,
    dataset_id,
    dataset_name,
    dataset_source,
    dataset_dir,
):
    return {
        "dataset_id": dataset_id,
        "dataset_name": dataset_name,
        "dataset_source": dataset_source,
        "dataset_dir": str(dataset_dir),
        "split_name": record["split_name"],
        "class_index": int(record["class_index"]),
        "class_name": record["class_name"],
        "relative_path": record["relative_path"],
        "absolute_path": record.get("absolute_path"),
        "filename": record["filename"],
        "original_tfds_label": record.get("original_tfds_label"),
        "project_label": int(record["project_label"]),
        "label_mapping_version": record.get("label_mapping_version")
        or LABEL_MAPPING_VERSION,
        "image_width": record.get("image_width"),
        "image_height": record.get("image_height"),
        "file_size_bytes": record.get("file_size_bytes"),
        "checksum_sha256": record.get("checksum_sha256"),
        "metadata": _json(record.get("metadata")),
    }


def _upsert_image(connection, params):
    row = connection.execute(
        text(
            """
            INSERT INTO dataset_split_images (
                dataset_id, dataset_name, dataset_source, dataset_dir, split_name,
                class_index, class_name, relative_path, absolute_path, filename,
                original_tfds_label, project_label, label_mapping_version,
                image_width, image_height, file_size_bytes, checksum_sha256, metadata
            )
            VALUES (
                :dataset_id, :dataset_name, :dataset_source, :dataset_dir, :split_name,
                :class_index, :class_name, :relative_path, :absolute_path, :filename,
                :original_tfds_label, :project_label, :label_mapping_version,
                :image_width, :image_height, :file_size_bytes, :checksum_sha256,
                CAST(:metadata AS jsonb)
            )
            ON CONFLICT (dataset_dir, relative_path)
            DO UPDATE SET
                dataset_id = EXCLUDED.dataset_id,
                dataset_name = EXCLUDED.dataset_name,
                dataset_source = EXCLUDED.dataset_source,
                split_name = EXCLUDED.split_name,
                class_index = EXCLUDED.class_index,
                class_name = EXCLUDED.class_name,
                absolute_path = EXCLUDED.absolute_path,
                filename = EXCLUDED.filename,
                original_tfds_label = EXCLUDED.original_tfds_label,
                project_label = EXCLUDED.project_label,
                label_mapping_version = EXCLUDED.label_mapping_version,
                image_width = EXCLUDED.image_width,
                image_height = EXCLUDED.image_height,
                file_size_bytes = EXCLUDED.file_size_bytes,
                checksum_sha256 = COALESCE(EXCLUDED.checksum_sha256, dataset_split_images.checksum_sha256),
                updated_at = NOW(),
                metadata = dataset_split_images.metadata || EXCLUDED.metadata
            RETURNING image_id, (xmax = 0) AS inserted
            """
        ),
        params,
    ).first()
    return row


def _register_with_connection(
    connection,
    dataset_dir,
    dataset_name,
    dataset_source,
    compute_checksum=False,
    source_url=DEFAULT_SOURCE_URL,
    description=DEFAULT_DATASET_DESCRIPTION,
):
    dataset_dir = resolve_dataset_dir(dataset_dir).resolve()
    records = scan_physical_split(dataset_dir, compute_checksum=compute_checksum)
    dataset_id = _ensure_dataset(
        connection,
        dataset_name=dataset_name,
        dataset_source=dataset_source,
        dataset_dir=dataset_dir,
        records=records,
        source_url=source_url,
        description=description,
    )

    inserted = 0
    updated = 0
    image_ids = {}
    for record in records:
        params = build_dataset_image_params(
            record,
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            dataset_source=dataset_source,
            dataset_dir=dataset_dir,
        )
        row = _upsert_image(connection, params)
        if row:
            image_ids[record["relative_path"]] = str(row[0])
            if bool(row[1]):
                inserted += 1
            else:
                updated += 1

    return {
        "dataset_id": dataset_id,
        "dataset_name": dataset_name,
        "dataset_source": dataset_source,
        "source_url": source_url,
        "description": description,
        "dataset_dir": str(dataset_dir),
        "total": len(records),
        "inserted": inserted,
        "updated": updated,
        "counts": summarize_records(records),
        "image_ids": image_ids,
    }


def register_physical_split_images(
    dataset_dir: Path,
    dataset_name: str = DEFAULT_DATASET_NAME,
    dataset_source: str = DEFAULT_DATASET_SOURCE,
    connection_or_session=None,
    compute_checksum=False,
    source_url: str = DEFAULT_SOURCE_URL,
    description: str = DEFAULT_DATASET_DESCRIPTION,
) -> dict:
    if connection_or_session is not None:
        return _register_with_connection(
            connection_or_session,
            dataset_dir=dataset_dir,
            dataset_name=dataset_name,
            dataset_source=dataset_source,
            compute_checksum=compute_checksum,
            source_url=source_url,
            description=description,
        )

    with get_connection() as connection:
        return _register_with_connection(
            connection,
            dataset_dir=dataset_dir,
            dataset_name=dataset_name,
            dataset_source=dataset_source,
            compute_checksum=compute_checksum,
            source_url=source_url,
            description=description,
        )


def load_registered_split_images(
    dataset_dir: Path,
    splits=None,
    connection_or_session=None,
) -> list[dict]:
    dataset_dir = str(resolve_dataset_dir(dataset_dir).resolve())
    split_filter = list(splits or SPLIT_NAMES)

    def run_query(connection):
        rows = connection.execute(
            text(
                """
                SELECT
                    image_id,
                    dataset_id,
                    dataset_name,
                    dataset_source,
                    dataset_dir,
                    split_name,
                    class_index,
                    class_name,
                    relative_path,
                    absolute_path,
                    filename,
                    original_tfds_label,
                    project_label,
                    label_mapping_version,
                    image_width,
                    image_height,
                    file_size_bytes,
                    checksum_sha256,
                    metadata
                FROM dataset_split_images
                WHERE dataset_dir = :dataset_dir
                  AND split_name = ANY(:splits)
                ORDER BY
                    CASE split_name
                        WHEN 'train' THEN 1
                        WHEN 'val' THEN 2
                        WHEN 'validation' THEN 2
                        WHEN 'test' THEN 3
                        ELSE 9
                    END,
                    class_index,
                    relative_path
                """
            ),
            {"dataset_dir": dataset_dir, "splits": split_filter},
        ).mappings()
        return [dict(row) for row in rows]

    if connection_or_session is not None:
        return run_query(connection_or_session)

    with get_connection() as connection:
        return run_query(connection)
