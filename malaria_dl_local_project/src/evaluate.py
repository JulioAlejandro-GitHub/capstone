import argparse
from pathlib import Path

import tensorflow as tf

from src.config import (
    CLASS_NAMES,
    LABEL_MAPPING_CHOICES,
    LABEL_MAPPING_VERSION,
    LEGACY_TFDS_LABEL_MAPPING_VERSION,
    POSITIVE_LABEL,
    label_mapping_metadata,
)
from src.data import add_data_source_args, dataset_tracking_metadata, load_malaria_splits
from src.metrics import collect_predictions, evaluate_binary_predictions
from src.model_metadata import resolve_threshold_for_checkpoint, verify_checkpoint_metadata
from src.preprocessing import PREPROCESSING_CHOICES, resolve_preprocessing_mode


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Evalúa un modelo Keras guardado.")
    parser.add_argument("--checkpoint", required=True, help="Ruta a .keras")
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument(
        "--threshold",
        default="0.5",
        help="Umbral numérico o 'clinical' para usar model_metadata.json.",
    )
    parser.add_argument(
        "--positive-label",
        default=POSITIVE_LABEL,
        help="Clase clínica positiva. Este proyecto usa parasitized.",
    )
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
        help="Modo de preprocesamiento usado por el checkpoint.",
    )
    add_data_source_args(parser)
    parser.add_argument(
        "--track-db",
        action="store_true",
        help="Registrar esta ejecución y sus resultados en PostgreSQL.",
    )
    return parser.parse_args(argv)


def main():
    args = parse_args()
    checkpoint = Path(args.checkpoint)
    run_context = None

    if not checkpoint.exists():
        raise FileNotFoundError(f"No existe el checkpoint: {checkpoint}")
    preprocessing_mode = resolve_preprocessing_mode(checkpoint.parent.name, args.preprocessing)
    mapping_metadata = label_mapping_metadata(args.label_mapping)
    if args.positive_label != POSITIVE_LABEL:
        raise ValueError(
            f"Este pipeline clínico usa {POSITIVE_LABEL!r} como clase positiva."
        )
    verify_checkpoint_metadata(
        checkpoint,
        expected_label_mapping=args.label_mapping,
        expected_raw_score_meaning=mapping_metadata["raw_model_score_meaning"],
    )
    if args.label_mapping == LEGACY_TFDS_LABEL_MAPPING_VERSION:
        print("Advertencia: evaluando checkpoint legacy_tfds_parasitized_zero.")
    dataset_info = dataset_tracking_metadata(args.data_source, args.dataset_dir)
    threshold_info = resolve_threshold_for_checkpoint(args.threshold, checkpoint)
    threshold_value = threshold_info["threshold_used"]

    if args.track_db:
        from src.tracking_integration import (
            args_to_parameters,
            model_name_from_checkpoint,
            start_tracking_run,
        )

        run_context = start_tracking_run(
            args=args,
            run_type="evaluation",
            script_name="src.evaluate",
            model_name=model_name_from_checkpoint(checkpoint),
            run_name=f"evaluate:{checkpoint.stem}",
            parameters=args_to_parameters(
                args,
                extra={
                    "checkpoint": str(checkpoint),
                    "preprocessing_mode": preprocessing_mode,
                    "class_names": CLASS_NAMES,
                    "label_mapping_version": args.label_mapping,
                    "label_mapping": mapping_metadata,
                    "raw_model_score_meaning": mapping_metadata["raw_model_score_meaning"],
                    "positive_label": args.positive_label,
                    **threshold_info,
                    **dataset_info,
                },
            ),
        )

    try:
        _, _, ds_test, _ = load_malaria_splits(
            img_size=args.img_size,
            batch_size=args.batch_size,
            augment=False,
            preprocessing_mode=preprocessing_mode,
            data_source=args.data_source,
            dataset_dir=args.dataset_dir,
        )

        class_names = CLASS_NAMES

        model = tf.keras.models.load_model(checkpoint, compile=False)
        output_dir = checkpoint.parent / "evaluation"

        y_true, y_pred, y_score = collect_predictions(
            model,
            ds_test,
            class_names=class_names,
            threshold=threshold_value,
            label_mapping_version=args.label_mapping,
        )
        metrics = evaluate_binary_predictions(
            y_true=y_true,
            y_pred=y_pred,
            y_score=y_score,
            class_names=class_names,
            output_dir=output_dir,
            prefix=checkpoint.stem,
            threshold=threshold_value,
            positive_label=args.positive_label,
            metadata={
                "preprocessing_mode": preprocessing_mode,
                "evaluation_split": "test",
                "label_mapping_version": args.label_mapping,
                "label_mapping": mapping_metadata,
                "raw_model_score_meaning": mapping_metadata["raw_model_score_meaning"],
                **threshold_info,
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
                log_predictions,
                output_artifacts_from_directory,
                record_run_dataset_images,
                record_run_io,
            )

            log_metrics_and_reports(run_context, metrics, class_names, split_name="test")
            log_predictions(
                run_context,
                y_true=y_true,
                y_pred=y_pred,
                y_score=y_score,
                class_names=class_names,
                threshold=threshold_value,
                label_mapping_version=args.label_mapping,
            )
            log_output_artifacts(run_context, output_dir)
            record_run_dataset_images(
                run_context,
                dataset_info=dataset_info,
                usage_context="evaluation",
                splits=["test"],
                batch_size=args.batch_size,
            )
            record_run_io(
                run_context,
                script_name="src.evaluate",
                input_parameters=args_to_parameters(
                    args,
                    extra={
                        "checkpoint": str(checkpoint),
                        "dataset_split": "test",
                        "output_dir": str(output_dir),
                        "preprocessing_mode": preprocessing_mode,
                        "class_names": CLASS_NAMES,
                        "label_mapping_version": args.label_mapping,
                        "label_mapping": mapping_metadata,
                        "raw_model_score_meaning": mapping_metadata[
                            "raw_model_score_meaning"
                        ],
                        **threshold_info,
                        **dataset_info,
                    },
                ),
                output_results={
                    "metrics_json": str(output_dir / f"{checkpoint.stem}_metrics.json"),
                    "predictions_csv": str(
                        output_dir / f"{checkpoint.stem}_predictions.csv"
                    ),
                    "confusion_matrix_csv": str(
                        output_dir / f"{checkpoint.stem}_confusion_matrix.csv"
                    ),
                    "metrics": metrics,
                    **threshold_info,
                    **clinical_metrics_for_tracking(metrics),
                },
                output_artifacts=output_artifacts_from_directory(output_dir),
                dataset_metadata=dataset_info,
                label_mapping_version=args.label_mapping,
                raw_model_score_meaning=mapping_metadata["raw_model_score_meaning"],
                metadata={"status_detail": "evaluation completed"},
            )
            finish_tracking_run(
                run_context,
                metadata={
                    "status_detail": "evaluation completed",
                    "label_mapping_version": args.label_mapping,
                    "label_mapping": mapping_metadata,
                    "raw_model_score_meaning": mapping_metadata["raw_model_score_meaning"],
                    **threshold_info,
                    **dataset_info,
                    **clinical_metrics_for_tracking(metrics),
                },
            )
    except Exception as exc:
        if args.track_db and run_context:
            from src.tracking_integration import fail_tracking_run

            fail_tracking_run(run_context, exc, script_name="src.evaluate")
        raise


if __name__ == "__main__":
    main()
