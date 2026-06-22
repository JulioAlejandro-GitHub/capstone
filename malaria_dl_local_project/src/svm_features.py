import argparse
from pathlib import Path

import joblib
import numpy as np
import tensorflow as tf
from sklearn.svm import SVC

from src.config import (
    CLASS_NAMES,
    LABEL_MAPPING_METADATA,
    LABEL_MAPPING_VERSION,
    OUTPUT_DIR,
    RAW_MODEL_SCORE_MEANING,
)
from src.data import load_malaria_splits
from src.metrics import clinical_predictions_from_raw_scores, evaluate_binary_predictions
from src.model_metadata import verify_checkpoint_metadata
from src.preprocessing import PREPROCESSING_CHOICES, resolve_preprocessing_mode


def parse_args():
    parser = argparse.ArgumentParser(description="CNN feature extractor + SVM RBF.")
    parser.add_argument("--checkpoint", required=True, help="Ruta del modelo Keras entrenado, idealmente VGG16.")
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--gamma", type=float, default=0.1)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--preprocessing",
        choices=PREPROCESSING_CHOICES,
        default="auto",
        help="Modo de preprocesamiento usado por el checkpoint extractor.",
    )
    parser.add_argument(
        "--track-db",
        action="store_true",
        help="Registrar esta ejecución y sus resultados en PostgreSQL.",
    )
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
    run_context = None
    if not checkpoint.exists():
        raise FileNotFoundError(f"No existe el checkpoint: {checkpoint}")
    preprocessing_mode = resolve_preprocessing_mode(checkpoint.parent.name, args.preprocessing)
    verify_checkpoint_metadata(checkpoint)

    output_dir = OUTPUT_DIR / "cnn_features_svm"
    if args.track_db:
        from src.tracking_integration import args_to_parameters, start_tracking_run

        run_context = start_tracking_run(
            args=args,
            run_type="svm_features",
            script_name="src.svm_features",
            model_name="cnn_features_svm",
            run_name="svm_features:cnn_features_svm",
            parameters=args_to_parameters(
                args,
                extra={
                    "checkpoint": str(checkpoint),
                    "output_dir": str(output_dir),
                    "threshold": args.threshold,
                    "preprocessing_mode": preprocessing_mode,
                    "class_names": CLASS_NAMES,
                    "label_mapping_version": LABEL_MAPPING_VERSION,
                    "label_mapping": LABEL_MAPPING_METADATA,
                    "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
                },
            ),
        )

    try:
        ds_train, _, ds_test, _ = load_malaria_splits(
            img_size=args.img_size,
            batch_size=args.batch_size,
            augment=False,
            preprocessing_mode=preprocessing_mode,
        )
        class_names = CLASS_NAMES

        model = tf.keras.models.load_model(checkpoint, compile=False)
        extractor = build_feature_extractor(model)

        print("Extrayendo features de entrenamiento...")
        X_train, y_train = extract_features(ds_train, extractor)

        print("Extrayendo features de test...")
        X_test, y_test = extract_features(ds_test, extractor)

        print("Entrenando SVM RBF...")
        svm = SVC(kernel="rbf", gamma=args.gamma, probability=True)
        svm.fit(X_train, y_train)

        parasitized_probability_index = list(svm.classes_).index(1)
        y_score = svm.predict_proba(X_test)[:, parasitized_probability_index]
        y_pred = clinical_predictions_from_raw_scores(
            y_score,
            class_names=class_names,
            threshold=args.threshold,
        )

        output_dir.mkdir(parents=True, exist_ok=True)

        metrics = evaluate_binary_predictions(
            y_true=y_test,
            y_pred=y_pred,
            y_score=y_score,
            class_names=class_names,
            output_dir=output_dir,
            prefix="svm_test",
            threshold=args.threshold,
            metadata={
                "preprocessing_mode": preprocessing_mode,
                "label_mapping_version": LABEL_MAPPING_VERSION,
                "label_mapping": LABEL_MAPPING_METADATA,
                "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
            },
        )

        joblib.dump(svm, output_dir / "svm_rbf.joblib")
        print(f"SVM guardado en: {output_dir / 'svm_rbf.joblib'}")

        if args.track_db and run_context:
            from src.tracking_integration import (
                finish_tracking_run,
                log_metrics_and_reports,
                log_output_artifacts,
            )

            log_metrics_and_reports(run_context, metrics, class_names, split_name="test")
            log_output_artifacts(run_context, output_dir)
            finish_tracking_run(
                run_context,
                metadata={
                    "status_detail": "svm_features completed",
                    "label_mapping_version": LABEL_MAPPING_VERSION,
                    "label_mapping": LABEL_MAPPING_METADATA,
                    "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
                },
            )
    except Exception as exc:
        if args.track_db and run_context:
            from src.tracking_integration import fail_tracking_run

            fail_tracking_run(run_context, exc, script_name="src.svm_features")
        raise


if __name__ == "__main__":
    main()
