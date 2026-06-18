import argparse
from pathlib import Path

from PIL import Image
import tensorflow_datasets as tfds

from src.data import get_tfds_data_dir


def parse_args():
    parser = argparse.ArgumentParser(description="Exporta TFDS malaria a carpetas por clase.")
    parser.add_argument("--output-dir", default="data/malaria_images")
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ds_raw, ds_info = tfds.load(
        "malaria",
        split="train",
        as_supervised=True,
        with_info=True,
        data_dir=str(get_tfds_data_dir()),
    )

    class_names = ds_info.features["label"].names
    for class_name in class_names:
        (output_dir / class_name).mkdir(parents=True, exist_ok=True)

    for idx, (image, label) in enumerate(tfds.as_numpy(ds_raw)):
        class_name = class_names[int(label)]
        img = Image.fromarray(image)
        img.save(output_dir / class_name / f"{idx:05d}.png")

    print(f"Dataset exportado en: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
