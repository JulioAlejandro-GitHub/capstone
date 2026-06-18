import argparse
from pathlib import Path

import tensorflow as tf

from src.data import load_malaria_splits
from src.metrics import collect_predictions, evaluate_binary_predictions


def parse_args():
    parser = argparse.ArgumentParser(description="Evalúa un modelo Keras guardado.")
    parser.add_argument("--checkpoint", required=True, help="Ruta a .keras")
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--track-db",
        action="store_true",
        help="Registrar esta ejecución y sus resultados en PostgreSQL.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    checkpoint = Path(args.checkpoint)
    run_context = None

    if not checkpoint.exists():
        raise FileNotFoundError(f"No existe el checkpoint: {checkpoint}")

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
                extra={"checkpoint": str(checkpoint)},
            ),
        )

    try:
        _, _, ds_test, ds_info = load_malaria_splits(
            img_size=args.img_size,
            batch_size=args.batch_size,
            augment=False,
        )

        class_names = ds_info.features["label"].names

        model = tf.keras.models.load_model(checkpoint)
        output_dir = checkpoint.parent / "evaluation"

        y_true, y_pred, y_score = collect_predictions(
            model,
            ds_test,
            class_names=class_names,
            threshold=args.threshold,
        )
        metrics = evaluate_binary_predictions(
            y_true=y_true,
            y_pred=y_pred,
            y_score=y_score,
            class_names=class_names,
            output_dir=output_dir,
            prefix=checkpoint.stem,
            threshold=args.threshold,
        )

        if args.track_db and run_context:
            from src.tracking_integration import (
                finish_tracking_run,
                log_metrics_and_reports,
                log_output_artifacts,
                log_predictions,
            )

            log_metrics_and_reports(run_context, metrics, class_names, split_name="test")
            log_predictions(
                run_context,
                y_true=y_true,
                y_pred=y_pred,
                y_score=y_score,
                class_names=class_names,
                threshold=args.threshold,
            )
            log_output_artifacts(run_context, output_dir)
            finish_tracking_run(run_context, metadata={"status_detail": "evaluation completed"})
    except Exception as exc:
        if args.track_db and run_context:
            from src.tracking_integration import fail_tracking_run

            fail_tracking_run(run_context, exc, script_name="src.evaluate")
        raise


if __name__ == "__main__":
    main()
