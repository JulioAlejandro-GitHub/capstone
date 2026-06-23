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
from src.preprocessing import PREPROCESSING_CHOICES, resolve_preprocessing_mode


def parse_args():
    parser = argparse.ArgumentParser(
        description="Estima temperatura de calibración usando el validation set."
    )
    parser.add_argument("--checkpoint", required=True, help="Ruta a best_model.keras o final_model.keras.")
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
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
        help="Ruta de salida. Default: <checkpoint_dir>/calibration.json.",
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
    return parser.parse_args()


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
        args_to_parameters,
        fail_tracking_run,
        finish_tracking_run,
        model_name_from_checkpoint,
        start_tracking_run,
    )

    context = None
    try:
        context = start_tracking_run(
            args=args,
            run_type="calibration",
            script_name="src.calibrate",
            model_name=model_name_from_checkpoint(checkpoint),
            run_name=f"calibrate:{checkpoint.stem}",
            parameters=args_to_parameters(
                args,
                extra={
                    "checkpoint": str(checkpoint),
                    "output_file": str(output_file),
                    "calibration_method": payload["method"],
                    "temperature": payload["temperature"],
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

        for metric_name, metric_value in payload["metrics"].items():
            tracker.safe_track(
                tracker.log_metric,
                run_id,
                metric_name=f"calibration_{metric_name}",
                metric_value=float(metric_value),
                split_name="validation",
            )
        tracker.safe_track(
            tracker.log_metric,
            run_id,
            metric_name="calibration_temperature",
            metric_value=float(payload["temperature"]),
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
                "method": payload["method"],
                "temperature": payload["temperature"],
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
    checkpoint = Path(args.checkpoint).expanduser()
    if not checkpoint.exists():
        raise FileNotFoundError(f"No existe el checkpoint: {checkpoint}")

    output_file = (
        Path(args.output_file).expanduser()
        if args.output_file
        else checkpoint.parent / "calibration.json"
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
    output_path = save_calibration(payload, output_file)
    track_calibration_run(args, checkpoint, output_path, payload)

    print(f"Temperatura estimada: {payload['temperature']:.6f}")
    print(
        "NLL validation:",
        f"{payload['metrics']['nll_before']:.6f}",
        "->",
        f"{payload['metrics']['nll_after']:.6f}",
    )
    print(f"Calibración guardada en: {output_path}")


if __name__ == "__main__":
    main()
