import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import tensorflow as tf

from src.calibration import CALIBRATION_SCHEMA_VERSION, fit_temperature_scaling
from src.config import (
    CLASS_NAMES,
    LABEL_MAPPING_CHOICES,
    LABEL_MAPPING_VERSION,
    LEGACY_TFDS_LABEL_MAPPING_VERSION,
    POSITIVE_LABEL,
    label_mapping_metadata,
)
from src.data import add_data_source_args, dataset_tracking_metadata, load_malaria_splits
from src.inference_pipeline import probability_rows_from_predictions
from src.model_metadata import update_model_metadata_with_clinical_threshold
from src.preprocessing import PREPROCESSING_CHOICES, resolve_preprocessing_mode
from src.threshold_calibration import (
    THRESHOLD_CALIBRATION_SCHEMA_VERSION,
    default_threshold_calibration_path,
    find_threshold_for_target_recall,
    validate_calibration_split,
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Calibra umbral clínico o temperatura usando el validation set."
    )
    parser.add_argument("--checkpoint", required=True, help="Ruta a best_model.keras o final_model.keras.")
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument(
        "--calibration-kind",
        choices=["threshold", "temperature_scaling"],
        default="threshold",
        help="Tipo de calibración. Default: threshold clínico por target_recall.",
    )
    parser.add_argument(
        "--dataset-split",
        choices=["val", "validation", "test"],
        default="val",
        help="Split usado para calibrar. test está bloqueado para evitar leakage.",
    )
    parser.add_argument("--target-recall", type=float, default=0.98)
    parser.add_argument("--min-specificity", type=float, default=None)
    parser.add_argument("--beta", type=float, default=2.0)
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
    parser.add_argument(
        "--output-file",
        default=None,
        help="Ruta de salida legacy. Para threshold, use --output-json si prefiere.",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Ruta de salida. Default threshold: <checkpoint_dir>/threshold_calibration.json.",
    )
    parser.add_argument(
        "--update-model-metadata",
        action="store_true",
        help="Actualizar model_metadata.json junto al checkpoint con clinical_threshold.",
    )
    parser.add_argument("--temperature-min", type=float, default=0.05)
    parser.add_argument("--temperature-max", type=float, default=10.0)
    parser.add_argument("--grid-size", type=int, default=200)
    parser.add_argument("--refinement-rounds", type=int, default=3)
    add_data_source_args(parser)
    parser.add_argument(
        "--track-db",
        action="store_true",
        help="Registrar la calibración en PostgreSQL.",
    )
    return parser.parse_args(argv)


def collect_validation_probabilities(
    model,
    dataset,
    class_names,
    label_mapping_version=LABEL_MAPPING_VERSION,
):
    y_true = []
    raw_scores = []

    for images, labels in dataset:
        predictions = model.predict(images, verbose=0)
        probability_rows = probability_rows_from_predictions(
            predictions,
            label_mapping_version=label_mapping_version,
        )
        batch_probability_parasitized = [
            row[POSITIVE_LABEL] for row in probability_rows
        ]
        raw_scores.extend(batch_probability_parasitized)
        y_true.extend(labels.numpy())

    y_true = np.asarray(y_true).astype(int)
    raw_scores = np.asarray(raw_scores, dtype=np.float32)
    probability_parasitized = raw_scores
    positive_index = list(class_names).index(POSITIVE_LABEL)
    y_true_positive = (y_true == positive_index).astype(np.float32)
    return y_true_positive, probability_parasitized, raw_scores


def build_calibration_payload(
    args,
    checkpoint,
    preprocessing_mode,
    class_names,
    y_true_positive,
    fit_result,
    dataset_info=None,
):
    metrics = {
        key: float(value)
        for key, value in fit_result["metrics"].items()
        if value is not None
    }
    mapping_metadata = label_mapping_metadata(args.label_mapping)
    return {
        "schema_version": CALIBRATION_SCHEMA_VERSION,
        "method": "temperature_scaling",
        "temperature": float(fit_result["temperature"]),
        "params": {"temperature": float(fit_result["temperature"])},
        "positive_label": POSITIVE_LABEL,
        "score_name": "probability_parasitized",
        "raw_model_score_meaning": mapping_metadata["raw_model_score_meaning"],
        "label_mapping_version": args.label_mapping,
        "label_mapping": mapping_metadata,
        "checkpoint": str(checkpoint),
        "class_names": list(class_names),
        "split": "validation",
        "num_samples": int(len(y_true_positive)),
        "positive_samples": int(np.sum(y_true_positive)),
        "negative_samples": int(len(y_true_positive) - np.sum(y_true_positive)),
        "img_size": int(args.img_size),
        "batch_size": int(args.batch_size),
        "preprocessing_mode": preprocessing_mode,
        "dataset": dataset_info or {},
        "temperature_search": {
            "temperature_min": float(args.temperature_min),
            "temperature_max": float(args.temperature_max),
            "grid_size": int(args.grid_size),
            "refinement_rounds": int(args.refinement_rounds),
        },
        "metrics": metrics,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def build_threshold_calibration_payload(
    args,
    checkpoint,
    preprocessing_mode,
    class_names,
    y_true_positive,
    calibration_result,
    dataset_info=None,
):
    return {
        **calibration_result,
        "schema_version": THRESHOLD_CALIBRATION_SCHEMA_VERSION,
        "method": "threshold_target_recall",
        "positive_label": POSITIVE_LABEL,
        "score_name": "probability_parasitized",
        "raw_model_score_meaning": label_mapping_metadata(args.label_mapping)[
            "raw_model_score_meaning"
        ],
        "label_mapping_version": args.label_mapping,
        "label_mapping": label_mapping_metadata(args.label_mapping),
        "checkpoint": str(checkpoint),
        "class_names": list(class_names),
        "split": "validation",
        "dataset_split": "val",
        "num_samples": int(len(y_true_positive)),
        "positive_samples": int(np.sum(y_true_positive)),
        "negative_samples": int(len(y_true_positive) - np.sum(y_true_positive)),
        "img_size": int(args.img_size),
        "batch_size": int(args.batch_size),
        "preprocessing_mode": preprocessing_mode,
        "dataset": dataset_info or {},
    }


def save_calibration(payload, output_file):
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path


def track_calibration_run(args, checkpoint, output_file, payload):
    if not args.track_db:
        return

    from src.tracking_integration import (
        artifact_record,
        args_to_parameters,
        fail_tracking_run,
        finish_tracking_run,
        model_name_from_checkpoint,
        record_run_io,
        record_threshold_calibration,
        start_tracking_run,
    )

    context = None
    try:
        method = payload.get("method", payload.get("threshold_policy", "calibration"))
        tracked_model_name = model_name_from_checkpoint(checkpoint)
        context = start_tracking_run(
            args=args,
            run_type="calibration",
            script_name="src.calibrate",
            model_name=tracked_model_name,
            run_name=f"calibrate:{checkpoint.stem}",
            parameters=args_to_parameters(
                args,
                extra={
                    "checkpoint": str(checkpoint),
                    "output_file": str(output_file),
                    "calibration_method": method,
                    "temperature": payload.get("temperature"),
                    "threshold_policy": payload.get("threshold_policy"),
                    "threshold_source": payload.get("threshold_source"),
                    "threshold_selected": payload.get("threshold_selected"),
                    "default_threshold": payload.get("default_threshold"),
                    "target_recall": payload.get("target_recall"),
                    "target_recall_satisfied": payload.get(
                        "target_recall_satisfied"
                    ),
                    "preprocessing_mode": payload["preprocessing_mode"],
                    "label_mapping_version": payload["label_mapping_version"],
                    "label_mapping": payload["label_mapping"],
                    "raw_model_score_meaning": payload["raw_model_score_meaning"],
                    **payload.get("dataset", {}),
                },
            ),
        )
        tracker = context["tracker"]
        run_id = context.get("run_id")
        if not run_id:
            return

        model_metadata_path = payload.get("model_metadata_path")
        if not model_metadata_path:
            candidate_metadata_path = checkpoint.parent / "model_metadata.json"
            if candidate_metadata_path.exists():
                model_metadata_path = str(candidate_metadata_path)

        if payload.get("threshold_selected") is not None:
            record_threshold_calibration(
                context,
                {
                    **payload,
                    "threshold_calibration_path": str(output_file),
                    "model_metadata_path": model_metadata_path,
                },
                model_name=tracked_model_name,
            )

        record_run_io(
            context,
            script_name="src.calibrate",
            input_parameters=args_to_parameters(
                args,
                extra={
                    "checkpoint": str(checkpoint),
                    "output_file": str(output_file),
                    "calibration_method": method,
                },
            ),
            output_results={
                "method": method,
                "threshold_selected": payload.get("threshold_selected"),
                "default_threshold": payload.get("default_threshold"),
                "target_recall": payload.get("target_recall"),
                "target_recall_satisfied": payload.get("target_recall_satisfied"),
                "selected_metrics": payload.get("selected_metrics"),
                "temperature": payload.get("temperature"),
                "metrics": payload.get("metrics"),
            },
            output_artifacts=[
                artifact_record(
                    output_file,
                    artifact_type=(
                        "threshold_calibration"
                        if payload.get("threshold_selected") is not None
                        else "calibration_file"
                    ),
                )
            ],
            dataset_metadata=payload.get("dataset", {}),
            model_metadata={
                "checkpoint": str(checkpoint),
                "model_metadata_path": model_metadata_path,
                "preprocessing_mode": payload.get("preprocessing_mode"),
            },
            clinical_metadata={
                "method": method,
                "threshold_policy": payload.get("threshold_policy"),
                "threshold_source": payload.get("threshold_source"),
                "threshold_selected": payload.get("threshold_selected"),
                "default_threshold": payload.get("default_threshold"),
                "target_recall": payload.get("target_recall"),
                "target_recall_satisfied": payload.get("target_recall_satisfied"),
                "selected_metrics": payload.get("selected_metrics"),
                "raw_model_score_meaning": payload.get("raw_model_score_meaning"),
            },
            label_mapping_version=payload.get("label_mapping_version"),
            raw_model_score_meaning=payload.get("raw_model_score_meaning"),
            metadata={"status_detail": "calibration completed"},
        )

        metric_payload = payload.get("metrics") or payload.get("selected_metrics") or {}
        metric_prefix = (
            "calibration"
            if payload.get("method") == "temperature_scaling"
            else "threshold_validation"
        )
        for metric_name, metric_value in metric_payload.items():
            if metric_value is None or isinstance(metric_value, (dict, list)):
                continue
            tracker.safe_track(
                tracker.log_metric,
                run_id,
                metric_name=f"{metric_prefix}_{metric_name}",
                metric_value=float(metric_value),
                split_name="validation",
            )
        if payload.get("temperature") is not None:
            tracker.safe_track(
                tracker.log_metric,
                run_id,
                metric_name="calibration_temperature",
                metric_value=float(payload["temperature"]),
                split_name="validation",
            )
        if payload.get("threshold_selected") is not None:
            tracker.safe_track(
                tracker.log_metric,
                run_id,
                metric_name="threshold_selected",
                metric_value=float(payload["threshold_selected"]),
                split_name="validation",
            )
        tracker.safe_track(
            tracker.log_artifact,
            run_id,
            artifact_type="calibration_file",
            name=Path(output_file).name,
            path=str(output_file),
            mime_type="application/json",
            metadata={
                "source": "src.calibrate",
                "method": method,
                "temperature": payload.get("temperature"),
                "threshold_policy": payload.get("threshold_policy"),
                "threshold_source": payload.get("threshold_source"),
                "threshold_selected": payload.get("threshold_selected"),
                "target_recall": payload.get("target_recall"),
                "target_recall_satisfied": payload.get("target_recall_satisfied"),
                "checkpoint": str(checkpoint),
                "label_mapping_version": payload["label_mapping_version"],
                "label_mapping": payload["label_mapping"],
                "raw_model_score_meaning": payload["raw_model_score_meaning"],
                **payload.get("dataset", {}),
            },
        )
        finish_tracking_run(
            context,
            metadata={
                "status_detail": "calibration completed",
                "calibration": payload,
                **payload.get("dataset", {}),
            },
        )
    except Exception as exc:
        try:
            fail_tracking_run(context, exc, script_name="src.calibrate")
        except Exception:
            pass
        raise


def main():
    args = parse_args()
    validate_calibration_split(args.dataset_split)
    checkpoint = Path(args.checkpoint).expanduser()
    if not checkpoint.exists():
        raise FileNotFoundError(f"No existe el checkpoint: {checkpoint}")

    output_file = (
        Path(args.output_json or args.output_file).expanduser()
        if (args.output_json or args.output_file)
        else (
            default_threshold_calibration_path(checkpoint.parent)
            if args.calibration_kind == "threshold"
            else checkpoint.parent / "calibration.json"
        )
    )
    preprocessing_mode = resolve_preprocessing_mode(checkpoint.parent.name, args.preprocessing)
    if args.label_mapping == LEGACY_TFDS_LABEL_MAPPING_VERSION:
        print("Advertencia: calibrando checkpoint legacy_tfds_parasitized_zero.")
    dataset_info = dataset_tracking_metadata(args.data_source, args.dataset_dir)

    _, ds_val, _, _ = load_malaria_splits(
        img_size=args.img_size,
        batch_size=args.batch_size,
        augment=False,
        preprocessing_mode=preprocessing_mode,
        data_source=args.data_source,
        dataset_dir=args.dataset_dir,
    )
    class_names = CLASS_NAMES
    if POSITIVE_LABEL not in class_names:
        raise ValueError(f"No existe la clase positiva {POSITIVE_LABEL!r}: {class_names}")

    print(f"Cargando modelo: {checkpoint}")
    model = tf.keras.models.load_model(checkpoint, compile=False)
    print("Calculando probabilidades sobre validation set...")
    y_true_positive, probability_parasitized, _ = collect_validation_probabilities(
        model,
        ds_val,
        class_names,
        label_mapping_version=args.label_mapping,
    )

    if args.calibration_kind == "temperature_scaling":
        print("Estimando temperatura...")
        fit_result = fit_temperature_scaling(
            y_true=y_true_positive,
            raw_probabilities=probability_parasitized,
            temperature_min=args.temperature_min,
            temperature_max=args.temperature_max,
            grid_size=args.grid_size,
            refinement_rounds=args.refinement_rounds,
        )
        payload = build_calibration_payload(
            args=args,
            checkpoint=checkpoint,
            preprocessing_mode=preprocessing_mode,
            class_names=class_names,
            y_true_positive=y_true_positive,
            fit_result=fit_result,
            dataset_info=dataset_info,
        )
    else:
        print("Calibrando threshold clínico sobre validation set...")
        calibration_result = find_threshold_for_target_recall(
            y_true=y_true_positive,
            y_scores=probability_parasitized,
            target_recall=args.target_recall,
            min_specificity=args.min_specificity,
            beta=args.beta,
        )
        payload = build_threshold_calibration_payload(
            args=args,
            checkpoint=checkpoint,
            preprocessing_mode=preprocessing_mode,
            class_names=class_names,
            y_true_positive=y_true_positive,
            calibration_result=calibration_result,
            dataset_info=dataset_info,
        )
    output_path = save_calibration(payload, output_file)
    metadata_path = None
    if args.update_model_metadata and args.calibration_kind == "threshold":
        metadata_path, _ = update_model_metadata_with_clinical_threshold(
            checkpoint,
            payload,
        )
    track_calibration_run(args, checkpoint, output_path, payload)

    if args.calibration_kind == "temperature_scaling":
        print(f"Temperatura estimada: {payload['temperature']:.6f}")
        print(
            "NLL validation:",
            f"{payload['metrics']['nll_before']:.6f}",
            "->",
            f"{payload['metrics']['nll_after']:.6f}",
        )
    else:
        print(f"Threshold clínico seleccionado: {payload['threshold_selected']:.6f}")
        print(f"Target recall satisfecho: {payload['target_recall_satisfied']}")
        print(
            "Recall validation:",
            f"{payload['selected_metrics']['recall_parasitized']:.6f}",
        )
        print(
            "Specificity validation:",
            f"{payload['selected_metrics']['specificity']:.6f}",
        )
        if payload.get("warning"):
            print(f"WARNING: {payload['warning']}")
        if metadata_path:
            print(f"Metadata actualizada en: {metadata_path}")
    print(f"Calibración guardada en: {output_path}")


if __name__ == "__main__":
    main()
