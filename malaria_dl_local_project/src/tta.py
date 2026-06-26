import argparse
from pathlib import Path

import numpy as np
import tensorflow as tf

from src.config import (
    CLASS_NAMES,
    LABEL_MAPPING_CHOICES,
    LABEL_MAPPING_VERSION,
    LEGACY_TFDS_LABEL_MAPPING_VERSION,
    label_mapping_metadata,
)
from src.data import (
    add_data_source_args,
    build_augmentation,
    dataset_tracking_metadata,
    load_raw_test_split,
)
from src.decision import POSITIVE_LABEL
from src.inference_pipeline import probability_rows_from_predictions
from src.metrics import clinical_predictions_from_raw_scores, evaluate_binary_predictions
from src.model_metadata import resolve_threshold_for_checkpoint, verify_checkpoint_metadata
from src.preprocessing import (
    PREPROCESSING_CHOICES,
    PREPROCESSING_VGG16_IMAGENET,
    apply_model_preprocessing,
    resolve_preprocessing_mode,
)


def prediction_to_parasitized_probability(prediction, label_mapping_version=LABEL_MAPPING_VERSION):
    return probability_rows_from_predictions(
        prediction,
        label_mapping_version=label_mapping_version,
    )[0][POSITIVE_LABEL]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Evalúa modelo con Test Time Augmentation.")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--n-aug", type=int, default=8)
    parser.add_argument(
        "--threshold",
        default="0.5",
        help="Umbral numérico o 'clinical' para usar model_metadata.json.",
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


def predict_with_tta(
    model,
    image,
    augmentation,
    n_aug: int = 8,
    preprocessing_mode="rescale_0_1",
    label_mapping_version=LABEL_MAPPING_VERSION,
):
    preprocessing_mode = resolve_preprocessing_mode(requested=preprocessing_mode)

    if preprocessing_mode == PREPROCESSING_VGG16_IMAGENET:
        augmented_images = [np.asarray(image, dtype=np.float32)]
        for _ in range(n_aug):
            aug_img = augmentation(image, training=True)
            augmented_images.append(np.asarray(aug_img, dtype=np.float32))
        batch = apply_model_preprocessing(
            np.asarray(augmented_images, dtype=np.float32),
            preprocessing_mode,
        ).numpy()
        predictions = model.predict(batch, verbose=0)
        probability_rows = probability_rows_from_predictions(
            predictions,
            label_mapping_version=label_mapping_version,
        )
        return float(np.mean([row[POSITIVE_LABEL] for row in probability_rows]))

    preds = []
    image_batch = tf.expand_dims(image, axis=0)
    preds.append(
        prediction_to_parasitized_probability(
            model.predict(image_batch, verbose=0),
            label_mapping_version=label_mapping_version,
        )
    )
    for _ in range(n_aug):
        aug_img = augmentation(image, training=True)
        aug_img = tf.expand_dims(aug_img, axis=0)
        preds.append(
            prediction_to_parasitized_probability(
                model.predict(aug_img, verbose=0),
                label_mapping_version=label_mapping_version,
            )
        )

    return float(np.mean(preds))


def main():
    args = parse_args()
    checkpoint = Path(args.checkpoint)
    run_context = None
    if not checkpoint.exists():
        raise FileNotFoundError(f"No existe el checkpoint: {checkpoint}")
    preprocessing_mode = resolve_preprocessing_mode(checkpoint.parent.name, args.preprocessing)
    mapping_metadata = label_mapping_metadata(args.label_mapping)
    verify_checkpoint_metadata(
        checkpoint,
        expected_label_mapping=args.label_mapping,
        expected_raw_score_meaning=mapping_metadata["raw_model_score_meaning"],
    )
    if args.label_mapping == LEGACY_TFDS_LABEL_MAPPING_VERSION:
        print("Advertencia: TTA usando checkpoint legacy_tfds_parasitized_zero.")
    dataset_info = dataset_tracking_metadata(args.data_source, args.dataset_dir)
    threshold_info = resolve_threshold_for_checkpoint(args.threshold, checkpoint)
    threshold_value = threshold_info["threshold_used"]

    output_dir = checkpoint.parent / "tta_evaluation"
    if args.track_db:
        from src.tracking_integration import (
            args_to_parameters,
            model_name_from_checkpoint,
            start_tracking_run,
        )

        run_context = start_tracking_run(
            args=args,
            run_type="tta",
            script_name="src.tta",
            model_name=model_name_from_checkpoint(checkpoint),
            run_name=f"tta:{checkpoint.stem}",
            parameters=args_to_parameters(
                args,
                extra={
                    "checkpoint": str(checkpoint),
                    "output_dir": str(output_dir),
                    "threshold": threshold_value,
                    "preprocessing_mode": preprocessing_mode,
                    "class_names": CLASS_NAMES,
                    "base_model_label_mapping_version": args.label_mapping,
                    "base_model_label_mapping": mapping_metadata,
                    "label_mapping_version": LABEL_MAPPING_VERSION,
                    "label_mapping": label_mapping_metadata(LABEL_MAPPING_VERSION),
                    "raw_model_score_meaning": "probability_parasitized",
                    **threshold_info,
                    **dataset_info,
                },
            ),
        )

    try:
        model = tf.keras.models.load_model(checkpoint, compile=False)
        raw_test = load_raw_test_split(
            data_source=args.data_source,
            dataset_dir=args.dataset_dir,
            img_size=args.img_size,
        )
        augmentation = build_augmentation()

        y_true = []
        y_score = []

        for image, label in raw_test:
            if preprocessing_mode == PREPROCESSING_VGG16_IMAGENET:
                model_image = image
            else:
                model_image = apply_model_preprocessing(image, preprocessing_mode)
            score = predict_with_tta(
                model,
                model_image,
                augmentation,
                n_aug=args.n_aug,
                preprocessing_mode=preprocessing_mode,
                label_mapping_version=args.label_mapping,
            )
            y_score.append(score)
            y_true.append(int(float(label.numpy())))

        y_true = np.asarray(y_true)
        y_score = np.asarray(y_score)

        class_names = CLASS_NAMES
        y_pred = clinical_predictions_from_raw_scores(
            y_score,
            class_names=class_names,
            threshold=threshold_value,
            label_mapping_version=LABEL_MAPPING_VERSION,
        )

        metrics = evaluate_binary_predictions(
            y_true=y_true,
            y_pred=y_pred,
            y_score=y_score,
            class_names=class_names,
            output_dir=output_dir,
            prefix="tta_test",
            threshold=threshold_value,
            metadata={
                "preprocessing_mode": preprocessing_mode,
                "label_mapping_version": LABEL_MAPPING_VERSION,
                "label_mapping": label_mapping_metadata(LABEL_MAPPING_VERSION),
                "base_model_label_mapping_version": args.label_mapping,
                "raw_model_score_meaning": "probability_parasitized",
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
                output_artifacts_from_directory,
                record_run_dataset_images,
                record_run_io,
            )

            log_metrics_and_reports(run_context, metrics, class_names, split_name="test")
            log_output_artifacts(run_context, output_dir)
            record_run_dataset_images(
                run_context,
                dataset_info=dataset_info,
                usage_context="tta",
                splits=["test"],
                batch_size=None,
            )
            record_run_io(
                run_context,
                script_name="src.tta",
                input_parameters=args_to_parameters(
                    args,
                    extra={
                        "checkpoint": str(checkpoint),
                        "n_aug": args.n_aug,
                        "dataset_split": "test",
                        "output_dir": str(output_dir),
                        "preprocessing_mode": preprocessing_mode,
                        "base_model_label_mapping_version": args.label_mapping,
                        "base_model_label_mapping": mapping_metadata,
                        "label_mapping_version": LABEL_MAPPING_VERSION,
                        "label_mapping": label_mapping_metadata(LABEL_MAPPING_VERSION),
                        "raw_model_score_meaning": "probability_parasitized",
                        **threshold_info,
                        **dataset_info,
                    },
                ),
                output_results={
                    "metrics_json": str(output_dir / "tta_test_metrics.json"),
                    "predictions_csv": str(output_dir / "tta_test_predictions.csv"),
                    "confusion_matrix_csv": str(
                        output_dir / "tta_test_confusion_matrix.csv"
                    ),
                    "metrics": metrics,
                    **threshold_info,
                    **clinical_metrics_for_tracking(metrics),
                },
                output_artifacts=output_artifacts_from_directory(output_dir),
                dataset_metadata=dataset_info,
                metadata={"status_detail": "tta completed"},
            )
            finish_tracking_run(
                run_context,
                metadata={
                    "status_detail": "tta completed",
                    "label_mapping_version": LABEL_MAPPING_VERSION,
                    "label_mapping": label_mapping_metadata(LABEL_MAPPING_VERSION),
                    "base_model_label_mapping_version": args.label_mapping,
                    "raw_model_score_meaning": "probability_parasitized",
                    **threshold_info,
                    **dataset_info,
                    **clinical_metrics_for_tracking(metrics),
                },
            )
    except Exception as exc:
        if args.track_db and run_context:
            from src.tracking_integration import fail_tracking_run

            fail_tracking_run(run_context, exc, script_name="src.tta")
        raise


if __name__ == "__main__":
    main()
