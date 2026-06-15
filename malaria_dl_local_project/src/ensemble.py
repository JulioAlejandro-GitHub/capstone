import argparse
from pathlib import Path

import numpy as np
import tensorflow as tf

from src.config import OUTPUT_DIR
from src.data import load_malaria_splits
from src.metrics import evaluate_binary_predictions


def parse_args():
    parser = argparse.ArgumentParser(description="Ensemble ponderado de modelos Keras.")
    parser.add_argument("--models", nargs="+", required=True, help="Rutas a modelos .keras")
    parser.add_argument("--weights", nargs="+", type=float, default=None, help="Pesos del ensemble")
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    return parser.parse_args()


def main():
    args = parse_args()

    model_paths = [Path(p) for p in args.models]
    for path in model_paths:
        if not path.exists():
            raise FileNotFoundError(f"No existe el modelo: {path}")

    models = [tf.keras.models.load_model(path) for path in model_paths]

    if args.weights is None:
        weights = np.ones(len(models), dtype=float) / len(models)
    else:
        weights = np.asarray(args.weights, dtype=float)
        if len(weights) != len(models):
            raise ValueError("La cantidad de pesos debe coincidir con la cantidad de modelos.")
        weights = weights / weights.sum()

    _, _, ds_test, ds_info = load_malaria_splits(
        img_size=args.img_size,
        batch_size=args.batch_size,
        augment=False,
    )
    class_names = ds_info.features["label"].names

    y_true = []
    y_score = []

    for images, labels in ds_test:
        batch_scores = []
        for model in models:
            probs = model.predict(images, verbose=0).ravel()
            batch_scores.append(probs)

        batch_scores = np.vstack(batch_scores)
        weighted_scores = np.average(batch_scores, axis=0, weights=weights)

        y_score.extend(weighted_scores)
        y_true.extend(labels.numpy())

    y_true = np.asarray(y_true).astype(int)
    y_score = np.asarray(y_score)
    y_pred = (y_score >= 0.5).astype(int)

    output_dir = OUTPUT_DIR / "ensemble"
    output_dir.mkdir(parents=True, exist_ok=True)

    evaluate_binary_predictions(
        y_true=y_true,
        y_pred=y_pred,
        y_score=y_score,
        class_names=class_names,
        output_dir=output_dir,
        prefix="ensemble_test",
    )


if __name__ == "__main__":
    main()
