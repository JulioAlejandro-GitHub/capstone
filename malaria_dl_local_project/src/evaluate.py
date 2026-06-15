import argparse
from pathlib import Path

import tensorflow as tf

from src.data import load_malaria_splits
from src.metrics import evaluate_keras_model


def parse_args():
    parser = argparse.ArgumentParser(description="Evalúa un modelo Keras guardado.")
    parser.add_argument("--checkpoint", required=True, help="Ruta a .keras")
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    return parser.parse_args()


def main():
    args = parse_args()
    checkpoint = Path(args.checkpoint)

    if not checkpoint.exists():
        raise FileNotFoundError(f"No existe el checkpoint: {checkpoint}")

    _, _, ds_test, ds_info = load_malaria_splits(
        img_size=args.img_size,
        batch_size=args.batch_size,
        augment=False,
    )

    class_names = ds_info.features["label"].names

    model = tf.keras.models.load_model(checkpoint)
    output_dir = checkpoint.parent / "evaluation"

    evaluate_keras_model(
        model=model,
        dataset=ds_test,
        class_names=class_names,
        output_dir=output_dir,
        prefix=checkpoint.stem,
    )


if __name__ == "__main__":
    main()
