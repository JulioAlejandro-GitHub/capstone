import argparse
from pathlib import Path

import numpy as np
import tensorflow as tf

from src.config import OUTPUT_DIR
from src.data import load_malaria_splits
from src.metrics import clinical_predictions_from_raw_scores, evaluate_binary_predictions
from src.preprocessing import PREPROCESSING_CHOICES, resolve_preprocessing_mode


def parse_args():
    parser = argparse.ArgumentParser(description="Ensemble ponderado de modelos Keras.")
    parser.add_argument("--models", nargs="+", required=True, help="Rutas a modelos .keras")
    parser.add_argument("--weights", nargs="+", type=float, default=None, help="Pesos del ensemble")
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--preprocessing",
        choices=PREPROCESSING_CHOICES,
        default="auto",
        help="Modo de preprocesamiento aplicado a todos los modelos del ensemble.",
    )
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

        _, _, ds_test, ds_info = load_malaria_splits(
            img_size=args.img_size,
            batch_size=args.batch_size,
            augment=False,
            preprocessing_mode=preprocessing_mode,
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
        y_pred = clinical_predictions_from_raw_scores(
            y_score,
            class_names=class_names,
            threshold=args.threshold,
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
            metadata={"preprocessing_mode": preprocessing_mode},
        )

        if args.track_db and run_context:
            from src.tracking_integration import (
                finish_tracking_run,
                log_metrics_and_reports,
                log_output_artifacts,
            )

            log_metrics_and_reports(run_context, metrics, class_names, split_name="test")
            log_output_artifacts(run_context, output_dir)
            finish_tracking_run(run_context, metadata={"status_detail": "ensemble completed"})
    except Exception as exc:
        if args.track_db and run_context:
            from src.tracking_integration import fail_tracking_run

            fail_tracking_run(run_context, exc, script_name="src.ensemble")
        raise


if __name__ == "__main__":
    main()
