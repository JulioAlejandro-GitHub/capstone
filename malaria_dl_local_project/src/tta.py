import argparse
from pathlib import Path

import numpy as np
import tensorflow as tf

from src.data import build_augmentation, load_raw_test_split, preprocess_single
from src.metrics import evaluate_binary_predictions


def parse_args():
    parser = argparse.ArgumentParser(description="Evalúa modelo con Test Time Augmentation.")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--n-aug", type=int, default=8)
    return parser.parse_args()


def predict_with_tta(model, image, augmentation, n_aug: int = 8):
    preds = []
    image_batch = tf.expand_dims(image, axis=0)

    preds.append(model.predict(image_batch, verbose=0)[0][0])

    for _ in range(n_aug):
        aug_img = augmentation(image, training=True)
        aug_img = tf.expand_dims(aug_img, axis=0)
        preds.append(model.predict(aug_img, verbose=0)[0][0])

    return float(np.mean(preds))


def main():
    args = parse_args()
    checkpoint = Path(args.checkpoint)
    if not checkpoint.exists():
        raise FileNotFoundError(f"No existe el checkpoint: {checkpoint}")

    model = tf.keras.models.load_model(checkpoint)
    raw_test = load_raw_test_split()
    augmentation = build_augmentation()

    y_true = []
    y_score = []

    for image, label in raw_test.map(lambda x, y: preprocess_single(x, y, args.img_size)):
        score = predict_with_tta(model, image, augmentation, n_aug=args.n_aug)
        y_score.append(score)
        y_true.append(int(label.numpy()))

    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)
    y_pred = (y_score >= 0.5).astype(int)

    class_names = ["parasitized", "uninfected"]
    output_dir = checkpoint.parent / "tta_evaluation"

    evaluate_binary_predictions(
        y_true=y_true,
        y_pred=y_pred,
        y_score=y_score,
        class_names=class_names,
        output_dir=output_dir,
        prefix="tta_test",
    )


if __name__ == "__main__":
    main()
