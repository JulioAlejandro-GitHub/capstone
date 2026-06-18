import argparse
from pathlib import Path

import numpy as np
import tensorflow as tf

from src.data import build_augmentation, load_raw_test_split, preprocess_single
from src.metrics import clinical_predictions_from_raw_scores, evaluate_binary_predictions


def parse_args():
    parser = argparse.ArgumentParser(description="Evalúa modelo con Test Time Augmentation.")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--n-aug", type=int, default=8)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--track-db",
        action="store_true",
        help="Registrar esta ejecución y sus resultados en PostgreSQL.",
    )
    return parser.parse_args()


def predict_with_tta(model, image, augmentation, n_aug: int = 8):
    preds = []
    image_batch = tf.expand_dims(image, axis=0)

    preds.append(model.predict(image_batch, verbose=0)[0][0])

    for _ in range(n_aug):
        aug_img = augmentation(image, training=True)
        aug_img = tf.expand_dims(aug_img, axis=0)
        preds.append(model.predict(aug_img, verbose=0)[0][0])

    return float(np.mean(preds))


def main():
    args = parse_args()
    checkpoint = Path(args.checkpoint)
    run_context = None
    if not checkpoint.exists():
        raise FileNotFoundError(f"No existe el checkpoint: {checkpoint}")

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
                    "threshold": args.threshold,
                },
            ),
        )

    try:
        model = tf.keras.models.load_model(checkpoint)
        raw_test = load_raw_test_split()
        augmentation = build_augmentation()

        y_true = []
        y_score = []

        for image, label in raw_test.map(lambda x, y: preprocess_single(x, y, args.img_size)):
            score = predict_with_tta(model, image, augmentation, n_aug=args.n_aug)
            y_score.append(score)
            y_true.append(int(label.numpy()))

        y_true = np.asarray(y_true)
        y_score = np.asarray(y_score)

        class_names = ["parasitized", "uninfected"]
        y_pred = clinical_predictions_from_raw_scores(
            y_score,
            class_names=class_names,
            threshold=args.threshold,
        )

        metrics = evaluate_binary_predictions(
            y_true=y_true,
            y_pred=y_pred,
            y_score=y_score,
            class_names=class_names,
            output_dir=output_dir,
            prefix="tta_test",
            threshold=args.threshold,
        )

        if args.track_db and run_context:
            from src.tracking_integration import (
                finish_tracking_run,
                log_metrics_and_reports,
                log_output_artifacts,
            )

            log_metrics_and_reports(run_context, metrics, class_names, split_name="test")
            log_output_artifacts(run_context, output_dir)
            finish_tracking_run(run_context, metadata={"status_detail": "tta completed"})
    except Exception as exc:
        if args.track_db and run_context:
            from src.tracking_integration import fail_tracking_run

            fail_tracking_run(run_context, exc, script_name="src.tta")
        raise


if __name__ == "__main__":
    main()
