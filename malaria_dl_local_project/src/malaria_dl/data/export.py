import argparse
from pathlib import Path

from PIL import Image
import tensorflow_datasets as tfds

from src.config import (
    CLASS_NAMES,
    LABEL_MAPPING_VERSION,
    NEGATIVE_LABEL,
    POSITIVE_LABEL,
    TFDS_ORIGINAL_CLASS_NAMES,
)
from src.data import get_tfds_data_dir


def parse_args():
    parser = argparse.ArgumentParser(description="Exporta TFDS malaria a carpetas por clase.")
    parser.add_argument("--output-dir", default="data/malaria_images")
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ds_raw, _ = tfds.load(
        "malaria",
        split="train",
        as_supervised=True,
        with_info=True,
        data_dir=str(get_tfds_data_dir()),
    )

    class_names = CLASS_NAMES
    for class_name in class_names:
        (output_dir / class_name).mkdir(parents=True, exist_ok=True)

    for idx, (image, label) in enumerate(tfds.as_numpy(ds_raw)):
        original_class_name = TFDS_ORIGINAL_CLASS_NAMES[int(label)]
        class_name = POSITIVE_LABEL if original_class_name == POSITIVE_LABEL else NEGATIVE_LABEL
        img = Image.fromarray(image)
        img.save(output_dir / class_name / f"{idx:05d}.png")

    print(f"Dataset exportado en: {output_dir.resolve()}")
    print(f"Convención de etiquetas exportada: {LABEL_MAPPING_VERSION} ({CLASS_NAMES})")


if __name__ == "__main__":
    main()
