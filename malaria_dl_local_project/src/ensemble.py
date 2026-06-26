import argparse
from pathlib import Path

import numpy as np
import tensorflow as tf

from src.config import (
    CLASS_NAMES,
    LABEL_MAPPING_CHOICES,
    LABEL_MAPPING_VERSION,
    LEGACY_TFDS_LABEL_MAPPING_VERSION,
    OUTPUT_DIR,
    label_mapping_metadata,
)
from src.data import add_data_source_args, dataset_tracking_metadata, load_malaria_splits
from src.decision import POSITIVE_LABEL
from src.inference_pipeline import probability_rows_from_predictions
from src.metrics import clinical_predictions_from_raw_scores, evaluate_binary_predictions
from src.model_metadata import verify_checkpoint_metadata
from src.preprocessing import PREPROCESSING_CHOICES, resolve_preprocessing_mode


def parse_args():
    parser = argparse.ArgumentParser(description="Ensemble ponderado de modelos Keras.")
    parser.add_argument("--models", nargs="+", required=True, help="Rutas a modelos .keras")
    parser.add_argument("--weights", nargs="+", type=float, default=None, help="Pesos del ensemble")
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--label-mapping",
        choices=LABEL_MAPPING_CHOICES,
        default=LABEL_MAPPING_VERSION,
        help="Convención del checkpoint. Usa legacy_tfds solo para modelos antiguos.",
    )
    parser.add_argument(
        "--preprocessing",
        choices=PREPROCESSING_CHOICES,
        default="auto",
        help="Modo de preprocesamiento aplicado a todos los modelos del ensemble.",
    )
    add_data_source_args(parser)
    parser.add_argument(
        "--track-db",
        action="store_true",
        help="Registrar esta ejecución y sus resultados en PostgreSQL.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    run_context = None

    model_paths = [Path(p) for p in args.models]
    for path in model_paths:
        if not path.exists():
            raise FileNotFoundError(f"No existe el modelo: {path}")
    preprocessing_mode = resolve_preprocessing_mode("ensemble", args.preprocessing)
    mapping_metadata = label_mapping_metadata(args.label_mapping)
    for path in model_paths:
        verify_checkpoint_metadata(
            path,
            expected_label_mapping=args.label_mapping,
            expected_raw_score_meaning=mapping_metadata["raw_model_score_meaning"],
        )
    if args.label_mapping == LEGACY_TFDS_LABEL_MAPPING_VERSION:
        print("Advertencia: ensemble usando convención legacy_tfds_parasitized_zero.")
    dataset_info = dataset_tracking_metadata(args.data_source, args.dataset_dir)

    output_dir = OUTPUT_DIR / "ensemble"
    if args.track_db:
        from src.tracking_integration import args_to_parameters, start_tracking_run

        run_context = start_tracking_run(
            args=args,
            run_type="ensemble",
            script_name="src.ensemble",
            model_name="ensemble",
            run_name="ensemble:weighted_average",
            parameters=args_to_parameters(
                args,
                extra={
                    "models": [str(path) for path in model_paths],
                    "output_dir": str(output_dir),
                    "threshold": args.threshold,
                    "preprocessing_mode": preprocessing_mode,
                    "class_names": CLASS_NAMES,
                    "base_model_label_mapping_version": args.label_mapping,
                    "base_model_label_mapping": mapping_metadata,
                    "label_mapping_version": LABEL_MAPPING_VERSION,
                    "label_mapping": label_mapping_metadata(LABEL_MAPPING_VERSION),
                    "raw_model_score_meaning": "probability_parasitized",
                    **dataset_info,
                },
            ),
        )

    try:
        models = [tf.keras.models.load_model(path, compile=False) for path in model_paths]

        if args.weights is None:
            weights = np.ones(len(models), dtype=float) / len(models)
        else:
            weights = np.asarray(args.weights, dtype=float)
            if len(weights) != len(models):
                raise ValueError("La cantidad de pesos debe coincidir con la cantidad de modelos.")
            weights = weights / weights.sum()

        _, _, ds_test, _ = load_malaria_splits(
            img_size=args.img_size,
            batch_size=args.batch_size,
            augment=False,
            preprocessing_mode=preprocessing_mode,
            data_source=args.data_source,
            dataset_dir=args.dataset_dir,
        )
        class_names = CLASS_NAMES

        y_true = []
        y_score = []

        for images, labels in ds_test:
            batch_scores = []
            for model in models:
                predictions = model.predict(images, verbose=0)
                probability_rows = probability_rows_from_predictions(
                    predictions,
                    label_mapping_version=args.label_mapping,
                )
                batch_scores.append(
                    [row[POSITIVE_LABEL] for row in probability_rows]
                )

            batch_scores = np.vstack(batch_scores)
            weighted_scores = np.average(batch_scores, axis=0, weights=weights)

            y_score.extend(weighted_scores)
            y_true.extend(labels.numpy())

        y_true = np.asarray(y_true).astype(int)
        y_score = np.asarray(y_score)
        y_pred = clinical_predictions_from_raw_scores(
            y_score,
            class_names=class_names,
            threshold=args.threshold,
            label_mapping_version=LABEL_MAPPING_VERSION,
        )

        output_dir.mkdir(parents=True, exist_ok=True)

        metrics = evaluate_binary_predictions(
            y_true=y_true,
            y_pred=y_pred,
            y_score=y_score,
            class_names=class_names,
            output_dir=output_dir,
            prefix="ensemble_test",
            threshold=args.threshold,
            metadata={
                "preprocessing_mode": preprocessing_mode,
                "label_mapping_version": LABEL_MAPPING_VERSION,
                "label_mapping": label_mapping_metadata(LABEL_MAPPING_VERSION),
                "raw_model_score_meaning": "probability_parasitized",
                **dataset_info,
            },
        )

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
                usage_context="ensemble",
                splits=["test"],
                batch_size=args.batch_size,
            )
            record_run_io(
                run_context,
                script_name="src.ensemble",
                input_parameters=args_to_parameters(
                    args,
                    extra={
                        "models": [str(path) for path in model_paths],
                        "weights": weights.tolist(),
                        "dataset_split": "test",
                        "output_dir": str(output_dir),
                        "preprocessing_mode": preprocessing_mode,
                        "base_model_label_mapping_version": args.label_mapping,
                        "base_model_label_mapping": mapping_metadata,
                        "label_mapping_version": LABEL_MAPPING_VERSION,
                        "label_mapping": label_mapping_metadata(LABEL_MAPPING_VERSION),
                        "raw_model_score_meaning": "probability_parasitized",
                        **dataset_info,
                    },
                ),
                output_results={
                    "metrics_json": str(output_dir / "ensemble_test_metrics.json"),
                    "predictions_csv": str(output_dir / "ensemble_test_predictions.csv"),
                    "confusion_matrix_csv": str(
                        output_dir / "ensemble_test_confusion_matrix.csv"
                    ),
                    "metrics": metrics,
                    **clinical_metrics_for_tracking(metrics),
                },
                output_artifacts=output_artifacts_from_directory(output_dir),
                dataset_metadata=dataset_info,
                metadata={"status_detail": "ensemble completed"},
            )
            finish_tracking_run(
                run_context,
                metadata={
                    "status_detail": "ensemble completed",
                    "label_mapping_version": LABEL_MAPPING_VERSION,
                    "label_mapping": label_mapping_metadata(LABEL_MAPPING_VERSION),
                    "base_model_label_mapping_version": args.label_mapping,
                    "raw_model_score_meaning": "probability_parasitized",
                    **dataset_info,
                    **clinical_metrics_for_tracking(metrics),
                },
            )
    except Exception as exc:
        if args.track_db and run_context:
            from src.tracking_integration import fail_tracking_run

            fail_tracking_run(run_context, exc, script_name="src.ensemble")
        raise


if __name__ == "__main__":
    main()
