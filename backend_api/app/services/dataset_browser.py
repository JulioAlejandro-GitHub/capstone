import json
from math import ceil
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.db import fetch_all, fetch_one
from app.services.artifacts import IMAGE_MIME_BY_EXTENSION, detect_image_mime
from app.services.serialization import row_to_dict, rows_to_list


CAPSTONE_ROOT = Path(__file__).resolve().parents[3]
MALARIA_PROJECT_ROOT = CAPSTONE_ROOT / "malaria_dl_local_project"
PHYSICAL_DATASET_ROOT = (MALARIA_PROJECT_ROOT / "data" / "malaria_physical_split").resolve()
SOURCE_URL = "https://www.tensorflow.org/datasets/catalog/malaria"
NIH_NLM_URL = "https://lhncbc.nlm.nih.gov/publication/pub9932"
DATASET_DESCRIPTION = (
    "Dataset de imágenes microscópicas de células sanguíneas clasificadas como "
    "uninfected o parasitized."
)
SPLIT_NAMES = ("train", "val", "test")
CLASS_NAMES = ("uninfected", "parasitized")
PAGE_SIZE_CHOICES = {12, 24, 48, 96}


def missing_dataset_views(exc: Exception) -> bool:
    message = str(exc).lower()
    return "vw_dataset_browser_" in message and (
        "does not exist" in message or "undefinedtable" in message
    )


def safe_fetch_all(datasource, sql, params=None):
    try:
        return fetch_all(datasource, sql, params)
    except SQLAlchemyError as exc:
        if missing_dataset_views(exc):
            return []
        raise


def safe_fetch_one(datasource, sql, params=None):
    try:
        return fetch_one(datasource, sql, params)
    except SQLAlchemyError as exc:
        if missing_dataset_views(exc):
            return None
        raise


def read_metadata_fallback(dataset_dir: str | None) -> dict:
    if not dataset_dir:
        metadata_path = PHYSICAL_DATASET_ROOT / "metadata.json"
    else:
        path = Path(dataset_dir)
        if not path.is_absolute():
            path = MALARIA_PROJECT_ROOT / path
        metadata_path = path / "metadata.json"
    try:
        resolved = metadata_path.resolve()
        if PHYSICAL_DATASET_ROOT not in resolved.parents and resolved != PHYSICAL_DATASET_ROOT:
            return {}
        if not resolved.exists():
            return {}
        return json.loads(resolved.read_text(encoding="utf-8"))
    except Exception:
        return {}


def empty_counts():
    counts = {
        split: {class_name: 0 for class_name in CLASS_NAMES}
        for split in SPLIT_NAMES
    }
    for split in SPLIT_NAMES:
        counts[split]["total"] = 0
    counts["total"] = 0
    return counts


def counts_from_rows(rows):
    counts = empty_counts()
    for row in rows:
        split = row["split_name"]
        class_name = row["class_name"]
        image_count = int(row["image_count"] or 0)
        if split not in counts or class_name not in counts[split]:
            continue
        counts[split][class_name] = image_count
        counts[split]["total"] += image_count
        counts["total"] += image_count
    return counts


def split_table_from_counts(counts):
    rows = []
    for split in SPLIT_NAMES:
        rows.append(
            {
                "split_name": split,
                "display_name": {
                    "train": "Entrenamiento",
                    "val": "Validación",
                    "test": "Prueba",
                }[split],
                "uninfected": counts[split]["uninfected"],
                "parasitized": counts[split]["parasitized"],
                "total": counts[split]["total"],
            }
        )
    rows.append(
        {
            "split_name": "total",
            "display_name": "Total",
            "uninfected": sum(counts[split]["uninfected"] for split in SPLIT_NAMES),
            "parasitized": sum(counts[split]["parasitized"] for split in SPLIT_NAMES),
            "total": counts["total"],
        }
    )
    return rows


def dataset_summary(datasource: str | None = "malaria"):
    rows = rows_to_list(
        safe_fetch_all(
            datasource,
            """
            SELECT *
            FROM vw_dataset_browser_summary
            ORDER BY
                CASE split_name
                    WHEN 'train' THEN 1
                    WHEN 'val' THEN 2
                    WHEN 'validation' THEN 2
                    WHEN 'test' THEN 3
                    ELSE 9
                END,
                class_index
            """,
        )
    )
    first = rows[0] if rows else {}
    metadata = first.get("dataset_metadata") if isinstance(first.get("dataset_metadata"), dict) else {}
    fallback = read_metadata_fallback(first.get("dataset_dir"))
    counts = counts_from_rows(rows)

    dataset_dir = first.get("dataset_dir") or str(PHYSICAL_DATASET_ROOT)
    source_url = first.get("source_url") or metadata.get("source_url") or SOURCE_URL
    description = first.get("description") or metadata.get("description") or DATASET_DESCRIPTION
    split_process = {
        "type": first.get("split_type")
        or metadata.get("split_type")
        or fallback.get("split_type")
        or "physical_stratified_split",
        "train_ratio": first.get("train_ratio")
        or metadata.get("train_ratio")
        or fallback.get("train_ratio")
        or 0.8,
        "val_ratio": first.get("val_ratio")
        or metadata.get("val_ratio")
        or fallback.get("val_ratio")
        or 0.1,
        "test_ratio": first.get("test_ratio")
        or metadata.get("test_ratio")
        or fallback.get("test_ratio")
        or 0.1,
        "seed": first.get("seed")
        or metadata.get("seed")
        or fallback.get("seed")
        or 42,
        "description": (
            "El dataset original se divide físicamente en carpetas locales para "
            "asegurar reproducibilidad y comparación justa entre modelos."
        ),
    }

    return {
        "dataset": {
            "name": first.get("dataset_name") or "malaria_physical_split",
            "source": first.get("dataset_source") or "tensorflow_datasets/malaria",
            "source_url": source_url,
            "nih_nlm_url": NIH_NLM_URL,
            "description": description,
            "dataset_dir": dataset_dir,
            "original_dataset_modified": False,
        },
        "label_mapping": {
            "0": "uninfected",
            "1": "parasitized",
            "negative_class": "uninfected",
            "negative_class_index": 0,
            "positive_class": "parasitized",
            "positive_class_index": 1,
            "version": first.get("label_mapping_version")
            or metadata.get("label_mapping_version")
            or fallback.get("label_mapping_version")
            or "clinical_v1_parasitized_positive",
            "raw_model_score_meaning": "probability_parasitized",
        },
        "split_process": split_process,
        "counts": counts,
        "split_table": split_table_from_counts(counts),
        "summary_rows": rows,
    }


def dataset_image_filters(split=None, class_name=None):
    conditions = []
    params = {}
    if split:
        normalized_split = "val" if split == "validation" else split
        if normalized_split not in SPLIT_NAMES:
            raise HTTPException(status_code=400, detail="split no soportado.")
        conditions.append("split_name = :split")
        params["split"] = normalized_split
    if class_name and class_name != "all":
        if class_name not in CLASS_NAMES:
            raise HTTPException(status_code=400, detail="class_name no soportado.")
        conditions.append("class_name = :class_name")
        params["class_name"] = class_name
    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where_sql, params


def paginated_dataset_images(
    datasource: str | None = "malaria",
    split: str | None = None,
    class_name: str | None = None,
    page: int = 1,
    page_size: int = 24,
):
    if page_size not in PAGE_SIZE_CHOICES:
        raise HTTPException(status_code=400, detail="page_size debe ser 12, 24, 48 o 96.")
    where_sql, params = dataset_image_filters(split=split, class_name=class_name)
    count_row = row_to_dict(
        safe_fetch_one(
            datasource,
            f"SELECT COUNT(*) AS total FROM vw_dataset_browser_images {where_sql}",
            params,
        )
    )
    total_items = int(count_row["total"]) if count_row else 0
    total_pages = max(1, ceil(total_items / page_size))
    page = min(max(page, 1), total_pages)
    offset = (page - 1) * page_size
    rows = rows_to_list(
        safe_fetch_all(
            datasource,
            f"""
            SELECT *
            FROM vw_dataset_browser_images
            {where_sql}
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
            LIMIT :limit OFFSET :offset
            """,
            {**params, "limit": page_size, "offset": offset},
        )
    )
    items = []
    for row in rows:
        items.append(
            {
                **row,
                "image_url": f"/api/dataset/images/{row['image_id']}/file",
            }
        )
    return {
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "filters": {
            "split": split,
            "class_name": class_name or "all",
        },
        "items": items,
    }


def dataset_image_detail(datasource: str | None, image_id: str):
    try:
        parsed_image_id = UUID(image_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="image_id inválido.") from exc
    row = row_to_dict(
        safe_fetch_one(
            datasource,
            """
            SELECT *
            FROM vw_dataset_browser_images
            WHERE image_id = CAST(:image_id AS uuid)
            """,
            {"image_id": str(parsed_image_id)},
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Imagen no encontrada.")
    row["image_url"] = f"/api/dataset/images/{row['image_id']}/file"
    return row


def resolve_dataset_image_file(datasource: str | None, image_id: str):
    row = dataset_image_detail(datasource, image_id)
    dataset_dir = Path(row["dataset_dir"])
    if not dataset_dir.is_absolute():
        dataset_dir = MALARIA_PROJECT_ROOT / dataset_dir
    dataset_dir = dataset_dir.resolve()

    if dataset_dir != PHYSICAL_DATASET_ROOT:
        raise HTTPException(status_code=403, detail="Dataset fuera de la carpeta permitida.")

    candidate = Path(row["absolute_path"]) if row.get("absolute_path") else dataset_dir / row["relative_path"]
    resolved = candidate.resolve()
    if resolved != PHYSICAL_DATASET_ROOT and PHYSICAL_DATASET_ROOT not in resolved.parents:
        raise HTTPException(status_code=403, detail="Imagen fuera del split físico permitido.")
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="Archivo de imagen no encontrado.")
    suffix = resolved.suffix.lower()
    if suffix not in IMAGE_MIME_BY_EXTENSION:
        raise HTTPException(status_code=403, detail="Extensión de imagen no permitida.")
    media_type = detect_image_mime(resolved)
    return resolved, media_type
