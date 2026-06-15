import argparse
from pathlib import Path

import joblib
import numpy as np
import tensorflow as tf
from sklearn.svm import SVC

from src.config import OUTPUT_DIR
from src.data import load_malaria_splits
from src.metrics import evaluate_binary_predictions


def parse_args():
    parser = argparse.ArgumentParser(description="CNN feature extractor + SVM RBF.")
    parser.add_argument("--checkpoint", required=True, help="Ruta del modelo Keras entrenado, idealmente VGG16.")
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--gamma", type=float, default=0.1)
    return parser.parse_args()


def build_feature_extractor(model):
    """
    Intenta usar la capa 'feature_dense_1024'. Si no existe, toma la penúltima capa.
    """
    try:
        return tf.keras.Model(
            inputs=model.input,
            outputs=model.get_layer("feature_dense_1024").output,
        )
    except ValueError:
        return tf.keras.Model(
            inputs=model.input,
            outputs=model.layers[-2].output,
        )


def extract_features(dataset, extractor):
    X_features = []
    y_labels = []

    for images, labels in dataset:
        features = extractor.predict(images, verbose=0)
        X_features.append(features)
        y_labels.append(labels.numpy())

    return np.vstack(X_features), np.concatenate(y_labels).astype(int)


def main():
    args = parse_args()
    checkpoint = Path(args.checkpoint)
    if not checkpoint.exists():
        raise FileNotFoundError(f"No existe el checkpoint: {checkpoint}")

    ds_train, _, ds_test, ds_info = load_malaria_splits(
        img_size=args.img_size,
        batch_size=args.batch_size,
        augment=False,
    )
    class_names = ds_info.features["label"].names

    model = tf.keras.models.load_model(checkpoint)
    extractor = build_feature_extractor(model)

    print("Extrayendo features de entrenamiento...")
    X_train, y_train = extract_features(ds_train, extractor)

    print("Extrayendo features de test...")
    X_test, y_test = extract_features(ds_test, extractor)

    print("Entrenando SVM RBF...")
    svm = SVC(kernel="rbf", gamma=args.gamma, probability=True)
    svm.fit(X_train, y_train)

    y_pred = svm.predict(X_test)
    y_score = svm.predict_proba(X_test)[:, 1]

    output_dir = OUTPUT_DIR / "cnn_features_svm"
    output_dir.mkdir(parents=True, exist_ok=True)

    evaluate_binary_predictions(
        y_true=y_test,
        y_pred=y_pred,
        y_score=y_score,
        class_names=class_names,
        output_dir=output_dir,
        prefix="svm_test",
    )

    joblib.dump(svm, output_dir / "svm_rbf.joblib")
    print(f"SVM guardado en: {output_dir / 'svm_rbf.joblib'}")


if __name__ == "__main__":
    main()
