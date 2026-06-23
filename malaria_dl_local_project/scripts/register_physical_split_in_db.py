import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dataset_registry import (  # noqa: E402
    DEFAULT_DATASET_NAME,
    DEFAULT_DATASET_SOURCE,
    register_physical_split_images,
    scan_physical_split,
    summarize_records,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Registra el split físico de malaria en PostgreSQL."
    )
    parser.add_argument(
        "--dataset-dir",
        default="data/malaria_physical_split",
        help="Ruta del split físico. Default: data/malaria_physical_split.",
    )
    parser.add_argument(
        "--dataset-name",
        default=DEFAULT_DATASET_NAME,
        help=f"Nombre del dataset en BD. Default: {DEFAULT_DATASET_NAME}.",
    )
    parser.add_argument(
        "--dataset-source",
        default=DEFAULT_DATASET_SOURCE,
        help=f"Fuente del dataset en BD. Default: {DEFAULT_DATASET_SOURCE}.",
    )
    parser.add_argument(
        "--compute-checksum",
        action="store_true",
        help="Calcula checksum SHA-256 para cada imagen.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Escribe en PostgreSQL. Sin esta opción se ejecuta dry-run.",
    )
    parser.add_argument(
        "--track-db",
        action="store_true",
        help="Alias compatible para ejecutar el registro real en PostgreSQL.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fuerza dry-run aunque se informe otra opción.",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def print_summary(dataset_dir, records):
    counts = summarize_records(records)
    print(f"Dataset dir: {dataset_dir}")
    print("Imágenes detectadas:")
    for split in ("train", "val", "test"):
        print(f"  {split}/uninfected: {counts[split]['uninfected']}")
        print(f"  {split}/parasitized: {counts[split]['parasitized']}")
    print(f"  total: {counts['total']}")


def main():
    args = parse_args()
    execute = (args.execute or args.track_db) and not args.dry_run
    records = scan_physical_split(
        Path(args.dataset_dir),
        compute_checksum=args.compute_checksum and execute,
    )
    print_summary(args.dataset_dir, records)

    if args.verbose:
        print(f"Dataset name: {args.dataset_name}")
        print(f"Dataset source: {args.dataset_source}")
        print(f"Checksums: {'sí' if args.compute_checksum else 'no'}")

    if not execute:
        print("No se registró nada. Use --execute para registrar en PostgreSQL.")
        return

    result = register_physical_split_images(
        dataset_dir=Path(args.dataset_dir),
        dataset_name=args.dataset_name,
        dataset_source=args.dataset_source,
        compute_checksum=args.compute_checksum,
    )
    print("Registro completado:")
    print(f"  dataset_id: {result.get('dataset_id')}")
    print(f"  total: {result['total']}")
    print(f"  insertadas: {result['inserted']}")
    print(f"  actualizadas: {result['updated']}")


if __name__ == "__main__":
    main()
