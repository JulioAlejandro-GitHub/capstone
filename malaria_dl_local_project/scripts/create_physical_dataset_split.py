import argparse
import csv
import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import tensorflow_datasets as tfds
from PIL import Image
from sklearn.model_selection import train_test_split


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    CLASS_NAMES,
    LABEL_MAPPING_VERSION,
    NEGATIVE_CLASS_INDEX,
    NEGATIVE_LABEL,
    PHYSICAL_DATASET_DIR,
    POSITIVE_CLASS_INDEX,
    POSITIVE_LABEL,
    TFDS_ORIGINAL_CLASS_NAMES,
)
from src.dataset_registry import (  # noqa: E402
    DEFAULT_DATASET_DESCRIPTION,
    DEFAULT_SOURCE_URL,
)
from src.data import get_tfds_data_dir  # noqa: E402


SPLIT_NAMES = ["train", "val", "test"]


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Crea un split físico estratificado de TFDS malaria sin modificar "
            "el dataset original."
        )
    )
    parser.add_argument("--output-dir", default=str(PHYSICAL_DATASET_DIR))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--image-format", choices=["png", "jpg", "jpeg"], default="png")
    parser.add_argument(
        "--register-db",
        action="store_true",
        help="Registra el split físico generado en PostgreSQL.",
    )
    parser.add_argument(
        "--register-db-compute-checksum",
        action="store_true",
        help="Calcula SHA-256 por imagen al registrar en PostgreSQL.",
    )
    parser.add_argument(
        "--dataset-name",
        default="malaria_physical_split",
        help="Nombre del dataset al usar --register-db.",
    )
    parser.add_argument(
        "--dataset-source",
        default="tensorflow_datasets/malaria",
        help="Fuente del dataset al usar --register-db.",
    )
    parser.add_argument(
        "--source-url",
        default=DEFAULT_SOURCE_URL,
        help="URL de fuente original al usar --register-db.",
    )
    parser.add_argument(
        "--description",
        default=DEFAULT_DATASET_DESCRIPTION,
        help="Descripción del dataset al usar --register-db.",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def validate_ratios(train_ratio, val_ratio, test_ratio):
    ratios = {
        "train_ratio": float(train_ratio),
        "val_ratio": float(val_ratio),
        "test_ratio": float(test_ratio),
    }
    if any(value <= 0.0 for value in ratios.values()):
        raise ValueError(f"Todos los ratios deben ser mayores que cero: {ratios}")
    total = sum(ratios.values())
    if not np.isclose(total, 1.0):
        raise ValueError(f"Los ratios deben sumar 1.0. Suma recibida: {total:.6f}")
    return ratios


def project_label_from_tfds_label(original_label):
    original_label = int(original_label)
    original_class_name = TFDS_ORIGINAL_CLASS_NAMES[original_label]
    if original_class_name == POSITIVE_LABEL:
        return POSITIVE_CLASS_INDEX, POSITIVE_LABEL
    if original_class_name == NEGATIVE_LABEL:
        return NEGATIVE_CLASS_INDEX, NEGATIVE_LABEL
    raise ValueError(
        f"Etiqueta TFDS no soportada: {original_label} -> {original_class_name!r}"
    )


def collect_tfds_records(verbose=False):
    ds_raw, ds_info = tfds.load(
        "malaria",
        split="train",
        as_supervised=True,
        with_info=True,
        shuffle_files=False,
        data_dir=str(get_tfds_data_dir()),
    )
    records = []
    for index, (_, label) in enumerate(tfds.as_numpy(ds_raw)):
        project_label, class_name = project_label_from_tfds_label(label)
        records.append(
            {
                "tfds_index": index,
                "original_tfds_label": int(label),
                "project_label": int(project_label),
                "class_name": class_name,
            }
        )
        if verbose and (index + 1) % 5000 == 0:
            print(f"Etiquetas leídas: {index + 1}")
    return records, ds_info


def stratified_split_records(records, seed, train_ratio, val_ratio, test_ratio):
    indices = np.arange(len(records))
    labels = np.asarray([record["project_label"] for record in records], dtype=int)

    train_indices, temp_indices = train_test_split(
        indices,
        train_size=train_ratio,
        random_state=seed,
        shuffle=True,
        stratify=labels,
    )
    relative_val_ratio = val_ratio / (val_ratio + test_ratio)
    temp_labels = labels[temp_indices]
    val_indices, test_indices = train_test_split(
        temp_indices,
        train_size=relative_val_ratio,
        random_state=seed,
        shuffle=True,
        stratify=temp_labels,
    )

    assignments = {}
    for split, split_indices in (
        ("train", train_indices),
        ("val", val_indices),
        ("test", test_indices),
    ):
        for index in split_indices:
            assignments[int(index)] = split
    return assignments


def count_assignments(records, assignments):
    counts = {}
    total = 0
    for split in SPLIT_NAMES:
        split_records = [
            records[index]
            for index, assigned_split in assignments.items()
            if assigned_split == split
        ]
        class_counts = Counter(record["class_name"] for record in split_records)
        split_total = int(sum(class_counts.values()))
        counts[split] = {
            NEGATIVE_LABEL: int(class_counts.get(NEGATIVE_LABEL, 0)),
            POSITIVE_LABEL: int(class_counts.get(POSITIVE_LABEL, 0)),
            "total": split_total,
        }
        total += split_total
    counts["total"] = int(total)
    return counts


def build_metadata(args, counts):
    return {
        "dataset_source": "tensorflow_datasets/malaria",
        "split_type": "physical_stratified_split",
        "train_ratio": float(args.train_ratio),
        "val_ratio": float(args.val_ratio),
        "test_ratio": float(args.test_ratio),
        "seed": int(args.seed),
        "label_mapping_version": LABEL_MAPPING_VERSION,
        "class_names": CLASS_NAMES,
        "negative_class_index": NEGATIVE_CLASS_INDEX,
        "negative_class_name": NEGATIVE_LABEL,
        "positive_class_index": POSITIVE_CLASS_INDEX,
        "positive_class_name": POSITIVE_LABEL,
        "tfds_original_mapping": {
            "0": "parasitized",
            "1": "uninfected",
        },
        "project_mapping": {
            "0": "uninfected",
            "1": "parasitized",
        },
        "image_format": args.image_format,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
    }


def split_summary_rows(counts):
    rows = []
    for split in SPLIT_NAMES:
        split_total = counts[split]["total"]
        for class_index, class_name in enumerate(CLASS_NAMES):
            count = counts[split][class_name]
            percentage = 0.0 if split_total == 0 else float(count) / float(split_total)
            rows.append(
                {
                    "split": split,
                    "class_name": class_name,
                    "class_index": class_index,
                    "count": count,
                    "percentage": percentage,
                }
            )
    return rows


def prepare_output_dir(output_dir, overwrite=False, dry_run=False):
    if dry_run:
        return
    if output_dir.exists():
        if not overwrite:
            raise FileExistsError(
                f"El split físico ya existe en {output_dir}.\n"
                "Use --overwrite para regenerarlo."
            )
        shutil.rmtree(output_dir)
    for split in SPLIT_NAMES:
        for class_name in CLASS_NAMES:
            (output_dir / split / class_name).mkdir(parents=True, exist_ok=True)


def safe_image_suffix(image_format):
    return "jpg" if image_format == "jpeg" else image_format


def export_images(records, assignments, output_dir, image_format, verbose=False):
    ds_raw = tfds.load(
        "malaria",
        split="train",
        as_supervised=True,
        shuffle_files=False,
        data_dir=str(get_tfds_data_dir()),
    )
    counters = {
        (split, class_name): 0
        for split in SPLIT_NAMES
        for class_name in CLASS_NAMES
    }
    manifest_rows = []
    suffix = safe_image_suffix(image_format)

    for index, (image, label) in enumerate(tfds.as_numpy(ds_raw)):
        split = assignments[index]
        record = records[index]
        class_name = record["class_name"]
        project_label = record["project_label"]
        original_tfds_label = int(label)
        if original_tfds_label != record["original_tfds_label"]:
            raise ValueError(
                f"Orden TFDS no reproducible en índice {index}: "
                f"esperado {record['original_tfds_label']}, recibido {original_tfds_label}"
            )

        counters[(split, class_name)] += 1
        filename = f"{counters[(split, class_name)]:06d}_{class_name}.{suffix}"
        relative_path = Path(split) / class_name / filename
        output_path = output_dir / relative_path

        pil_image = Image.fromarray(image)
        if image_format in {"jpg", "jpeg"}:
            pil_image = pil_image.convert("RGB")
        pil_image.save(output_path)

        width, height = pil_image.size
        manifest_rows.append(
            {
                "split": split,
                "class_name": class_name,
                "class_index": project_label,
                "relative_path": relative_path.as_posix(),
                "original_tfds_label": original_tfds_label,
                "project_label": project_label,
                "image_width": width,
                "image_height": height,
            }
        )
        if verbose and (index + 1) % 5000 == 0:
            print(f"Imágenes exportadas: {index + 1}")

    return manifest_rows


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(output_dir, metadata, summary_rows, manifest_rows):
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_csv(
        output_dir / "split_summary.csv",
        summary_rows,
        ["split", "class_name", "class_index", "count", "percentage"],
    )
    write_csv(
        output_dir / "files_manifest.csv",
        manifest_rows,
        [
            "split",
            "class_name",
            "class_index",
            "relative_path",
            "original_tfds_label",
            "project_label",
            "image_width",
            "image_height",
        ],
    )


def print_counts(counts):
    print("Split físico propuesto:")
    for split in SPLIT_NAMES:
        print(
            f"  {split}: total={counts[split]['total']}, "
            f"uninfected={counts[split][NEGATIVE_LABEL]}, "
            f"parasitized={counts[split][POSITIVE_LABEL]}"
        )
    print(f"  total: {counts['total']}")


def main():
    args = parse_args()
    validate_ratios(args.train_ratio, args.val_ratio, args.test_ratio)
    output_dir = Path(args.output_dir).expanduser()
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    if output_dir.exists() and not args.overwrite and not args.dry_run:
        raise FileExistsError(
            f"El split físico ya existe en {output_dir}.\n"
            "Use --overwrite para regenerarlo."
        )

    print("Leyendo etiquetas desde TensorFlow Datasets malaria...")
    print(f"Ruta TFDS: {get_tfds_data_dir()}")
    print("El dataset original de TFDS no se modifica.")
    records, ds_info = collect_tfds_records(verbose=args.verbose)
    print(f"Ejemplos TFDS: {ds_info.splits['train'].num_examples}")
    print(f"Clases clínicas exportadas: {CLASS_NAMES}")
    print(f"Convención de etiquetas: {LABEL_MAPPING_VERSION}")

    assignments = stratified_split_records(
        records,
        seed=args.seed,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
    )
    counts = count_assignments(records, assignments)
    print_counts(counts)

    if args.dry_run:
        print("Dry-run activo: no se escribieron archivos.")
        return

    prepare_output_dir(output_dir, overwrite=args.overwrite, dry_run=False)
    manifest_rows = export_images(
        records,
        assignments,
        output_dir,
        image_format=args.image_format,
        verbose=args.verbose,
    )
    metadata = build_metadata(args, counts)
    summary_rows = split_summary_rows(counts)
    write_outputs(output_dir, metadata, summary_rows, manifest_rows)

    print(f"Split físico creado en: {output_dir}")
    print(f"Metadata: {output_dir / 'metadata.json'}")
    print(f"Resumen: {output_dir / 'split_summary.csv'}")
    print(f"Manifest: {output_dir / 'files_manifest.csv'}")

    if args.register_db:
        from src.dataset_registry import register_physical_split_images

        result = register_physical_split_images(
            dataset_dir=output_dir,
            dataset_name=args.dataset_name,
            dataset_source=args.dataset_source,
            source_url=args.source_url,
            description=args.description,
            compute_checksum=args.register_db_compute_checksum,
        )
        print("Registro PostgreSQL completado:")
        print(f"  dataset_id: {result.get('dataset_id')}")
        print(f"  total: {result['total']}")
        print(f"  insertadas: {result['inserted']}")
        print(f"  actualizadas: {result['updated']}")


if __name__ == "__main__":
    main()
