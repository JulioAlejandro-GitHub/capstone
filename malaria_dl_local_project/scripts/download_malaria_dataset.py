import sys
from pathlib import Path

import tensorflow_datasets as tfds


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data import get_tfds_data_dir


def main():
    data_dir = get_tfds_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    print("Descargando/verificando dataset TFDS 'malaria'...")
    print(f"Ruta TFDS: {data_dir}")

    _, ds_info = tfds.load(
        "malaria",
        split="train",
        as_supervised=True,
        with_info=True,
        data_dir=str(data_dir),
    )

    dataset_path = Path(data_dir) / "malaria" / str(ds_info.version)
    print("Dataset disponible.")
    print(f"Nombre: {ds_info.name}")
    print(f"Version: {ds_info.version}")
    print(f"Ejemplos: {ds_info.splits['train'].num_examples}")
    print(f"Clases: {ds_info.features['label'].names}")
    print(f"Ruta esperada: {dataset_path}")


if __name__ == "__main__":
    main()
