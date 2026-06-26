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
from src.data import add_data_source_args, dataset_tracking_metadata, load_malaria_splits
from src.metrics import clinical_predictions_from_raw_scores, evaluate_binary_predictions
from src.model_metadata import (
    build_model_metadata,
    resolve_threshold_for_checkpoint,
    verify_checkpoint_metadata,
    write_model_metadata,
)
from src.preprocessing import PREPROCESSING_CHOICES, resolve_preprocessing_mode


SVM_CLINICAL_THRESHOLD_ERROR = (
    "No clinical threshold found for SVM model. Run calibration first or use numeric threshold."
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="CNN feature extractor + SVM RBF.")
    parser.add_argument("--checkpoint", required=True, help="Ruta del modelo Keras entrenado, idealmente VGG16.")
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--gamma", type=float, default=0.1)
    parser.add_argument(
        "--threshold",
        default="0.5",
        help="Umbral numérico o 'clinical' para usar metadata calibrada del SVM.",
    )
    parser.add_argument(
        "--preprocessing",
        choices=PREPROCESSING_CHOICES,
        default="auto",
        help="Modo de preprocesamiento usado por el checkpoint extractor.",
    )
    add_data_source_args(parser)
    parser.add_argument(
        "--track-db",
        action="store_true",
        help="Registrar esta ejecución y sus resultados en PostgreSQL.",
    )
    return parser.parse_args(argv)


def resolve_svm_threshold(threshold, svm_model_path):
    try:
        return resolve_threshold_for_checkpoint(threshold, svm_model_path)
    except ValueError as exc:
        if isinstance(threshold, str) and threshold.strip().lower() == "clinical":
            raise ValueError(SVM_CLINICAL_THRESHOLD_ERROR) from exc
        raise


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
    dataset_info = dataset_tracking_metadata(args.data_source, args.dataset_dir)

    output_dir = OUTPUT_DIR / "cnn_features_svm"
    svm_model_path = output_dir / "svm_rbf.joblib"
    threshold_info = resolve_svm_threshold(args.threshold, svm_model_path)
    threshold_value = threshold_info["threshold_used"]
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
                    "threshold": threshold_value,
                    "preprocessing_mode": preprocessing_mode,
                    "class_names": CLASS_NAMES,
                    "label_mapping_version": LABEL_MAPPING_VERSION,
                    "label_mapping": LABEL_MAPPING_METADATA,
                    "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
                    **threshold_info,
                    **dataset_info,
                },
            ),
        )

    try:
        ds_train, _, ds_test, _ = load_malaria_splits(
            img_size=args.img_size,
            batch_size=args.batch_size,
            augment=False,
            preprocessing_mode=preprocessing_mode,
            data_source=args.data_source,
            dataset_dir=args.dataset_dir,
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

        if 1 not in list(svm.classes_):
            raise ValueError(
                "SVM no contiene la clase clínica positiva 1 = parasitized en svm.classes_."
            )
        parasitized_probability_index = list(svm.classes_).index(1)
        y_score = svm.predict_proba(X_test)[:, parasitized_probability_index]
        y_pred = clinical_predictions_from_raw_scores(
            y_score,
            class_names=class_names,
            threshold=threshold_value,
        )

        output_dir.mkdir(parents=True, exist_ok=True)

        metrics = evaluate_binary_predictions(
            y_true=y_test,
            y_pred=y_pred,
            y_score=y_score,
            class_names=class_names,
            output_dir=output_dir,
            prefix="svm_test",
            threshold=threshold_value,
            metadata={
                "preprocessing_mode": preprocessing_mode,
                "evaluation_split": "test",
                "label_mapping_version": LABEL_MAPPING_VERSION,
                "label_mapping": LABEL_MAPPING_METADATA,
                "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
                **threshold_info,
                **dataset_info,
            },
        )

        joblib.dump(svm, svm_model_path)
        svm_metadata_extra = dict(threshold_info)
        if svm_metadata_extra.get("clinical_threshold") is None:
            svm_metadata_extra.pop("clinical_threshold", None)
        write_model_metadata(
            output_dir,
            build_model_metadata(
                "cnn_features_svm",
                preprocessing=preprocessing_mode,
                extra={
                    "checkpoint_path": str(svm_model_path),
                    "feature_extractor_checkpoint": str(checkpoint),
                    "svm_classes": [int(item) for item in svm.classes_],
                    "svm_positive_probability_index": int(
                        parasitized_probability_index
                    ),
                    "svm_kernel": "rbf",
                    "svm_gamma": args.gamma,
                    **svm_metadata_extra,
                    **dataset_info,
                },
            ),
        )
        print(f"SVM guardado en: {svm_model_path}")

        if args.track_db and run_context:
            from src.tracking_integration import (
                args_to_parameters,
                clinical_metrics_for_tracking,
                finish_tracking_run,
                log_metrics_and_reports,
                log_output_artifacts,
                output_artifacts_from_directory,
                record_run_dataset_images,
                record_run_io,
            )

            log_metrics_and_reports(run_context, metrics, class_names, split_name="test")
            log_output_artifacts(run_context, output_dir)
            record_run_dataset_images(
                run_context,
                dataset_info=dataset_info,
                usage_context="svm_features",
                splits=["train"],
                batch_size=args.batch_size,
                metadata_by_relative_path={},
            )
            record_run_dataset_images(
                run_context,
                dataset_info=dataset_info,
                usage_context="svm_features",
                splits=["test"],
                batch_size=args.batch_size,
            )
            record_run_io(
                run_context,
                script_name="src.svm_features",
                input_parameters=args_to_parameters(
                    args,
                    extra={
                        "checkpoint": str(checkpoint),
                        "feature_extractor_checkpoint": str(checkpoint),
                        "kernel": "rbf",
                        "gamma": args.gamma,
                        "svm_classes": [int(item) for item in svm.classes_],
                        "dataset_splits": ["train", "test"],
                        "output_dir": str(output_dir),
                        "preprocessing_mode": preprocessing_mode,
                        "class_names": CLASS_NAMES,
                        "label_mapping_version": LABEL_MAPPING_VERSION,
                        "label_mapping": LABEL_MAPPING_METADATA,
                        "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
                        **threshold_info,
                        **dataset_info,
                    },
                ),
                output_results={
                    "svm_model": str(svm_model_path),
                    "metrics_json": str(output_dir / "svm_test_metrics.json"),
                    "predictions_csv": str(output_dir / "svm_test_predictions.csv"),
                    "confusion_matrix_csv": str(output_dir / "svm_test_confusion_matrix.csv"),
                    "metrics": metrics,
                    **threshold_info,
                    **clinical_metrics_for_tracking(metrics),
                },
                output_artifacts=output_artifacts_from_directory(output_dir),
                dataset_metadata=dataset_info,
                model_metadata={
                    "svm_model": str(svm_model_path),
                    "svm_classes": [int(item) for item in svm.classes_],
                    "feature_extractor_checkpoint": str(checkpoint),
                    **(threshold_info.get("clinical_threshold") or {}),
                },
                clinical_metadata={
                    "svm_kernel": "rbf",
                    "svm_gamma": args.gamma,
                    **threshold_info,
                    **clinical_metrics_for_tracking(metrics),
                },
                metadata={"status_detail": "svm_features completed"},
            )
            finish_tracking_run(
                run_context,
                metadata={
                    "status_detail": "svm_features completed",
                    "label_mapping_version": LABEL_MAPPING_VERSION,
                    "label_mapping": LABEL_MAPPING_METADATA,
                    "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
                    **threshold_info,
                    **dataset_info,
                    **clinical_metrics_for_tracking(metrics),
                },
            )
    except Exception as exc:
        if args.track_db and run_context:
            from src.tracking_integration import fail_tracking_run

            fail_tracking_run(run_context, exc, script_name="src.svm_features")
        raise


if __name__ == "__main__":
    main()
