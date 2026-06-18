import argparse
import json
from pathlib import Path

import tensorflow as tf

from src.config import OUTPUT_DIR
from src.data import load_malaria_splits
from src.metrics import evaluate_keras_model
from src.models import (
    build_custom_cnn,
    build_vgg16_transfer,
    compile_binary_model,
    unfreeze_last_layers,
)
from src.preprocessing import PREPROCESSING_CHOICES, resolve_preprocessing_mode


CHECKPOINT_METRIC_CHOICES = [
    "val_recall_parasitized",
    "val_auc",
    "val_recall",
    "val_accuracy",
    "val_loss",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Entrenamiento local para NIH/NLM Malaria Dataset.")
    parser.add_argument("--model", choices=["custom_cnn", "vgg16"], required=True)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--fine-tune-epochs", type=int, default=0)
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument("--no-augment", action="store_true")
    parser.add_argument(
        "--checkpoint-metric",
        choices=CHECKPOINT_METRIC_CHOICES,
        default="val_recall_parasitized",
        help=(
            "Métrica monitoreada para guardar best_model.keras. "
            "Default: val_recall_parasitized."
        ),
    )
    parser.add_argument(
        "--checkpoint-mode",
        choices=["auto", "max", "min"],
        default="auto",
        help="Modo de comparación del checkpoint. 'auto' usa min para loss y max para el resto.",
    )
    parser.add_argument(
        "--early-stopping-monitor",
        choices=CHECKPOINT_METRIC_CHOICES,
        default=None,
        help=(
            "Métrica para EarlyStopping. Si no se informa, usa la misma que "
            "--checkpoint-metric."
        ),
    )
    parser.add_argument(
        "--early-stopping-mode",
        choices=["auto", "max", "min"],
        default="auto",
        help="Modo de comparación de EarlyStopping.",
    )
    parser.add_argument(
        "--early-stopping-patience",
        type=int,
        default=10,
        help="Paciencia de EarlyStopping.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Directorio de salida opcional. Si no se informa, usa "
            "outputs/<model> como antes."
        ),
    )
    parser.add_argument(
        "--preprocessing",
        choices=PREPROCESSING_CHOICES,
        default="auto",
        help=(
            "Modo de preprocesamiento. 'auto' mantiene compatibilidad con "
            "checkpoints existentes; usa vgg16_imagenet solo al reentrenar VGG16."
        ),
    )
    parser.add_argument(
        "--track-db",
        action="store_true",
        help="Registrar esta ejecución y sus resultados en PostgreSQL.",
    )
    return parser.parse_args()


def resolve_monitor_mode(monitor, requested_mode="auto"):
    if requested_mode != "auto":
        return requested_mode
    return "min" if str(monitor).endswith("loss") else "max"


def build_phase_callbacks(
    output_dir,
    checkpoint_callback,
    phase,
    early_stopping_monitor,
    early_stopping_mode,
    early_stopping_patience,
):
    csv_loggers = [tf.keras.callbacks.CSVLogger(str(output_dir / f"{phase}_log.csv"))]
    if phase == "training_base":
        # Alias histórico para compatibilidad con reportes existentes.
        csv_loggers.append(tf.keras.callbacks.CSVLogger(str(output_dir / "training_log.csv")))

    return [
        checkpoint_callback,
        tf.keras.callbacks.EarlyStopping(
            monitor=early_stopping_monitor,
            patience=early_stopping_patience,
            restore_best_weights=True,
            mode=early_stopping_mode,
            verbose=1,
        ),
        *csv_loggers,
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=4,
            min_lr=1e-6,
            verbose=1,
        ),
    ]


def json_safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def write_checkpoint_selection_report(
    output_dir,
    checkpoint_metric,
    checkpoint_mode,
    early_stopping_monitor,
    early_stopping_mode,
    checkpoint_callback,
    fine_tuning_enabled,
):
    report = {
        "best_model_path": str(output_dir / "best_model.keras"),
        "checkpoint_metric": checkpoint_metric,
        "checkpoint_mode": checkpoint_mode,
        "best_checkpoint_value": json_safe_float(getattr(checkpoint_callback, "best", None)),
        "early_stopping_monitor": early_stopping_monitor,
        "early_stopping_mode": early_stopping_mode,
        "reduce_lr_monitor": "val_loss",
        "base_training_log": str(output_dir / "training_base_log.csv"),
        "legacy_training_log": str(output_dir / "training_log.csv"),
        "fine_tuning_log": str(output_dir / "fine_tuning_log.csv")
        if fine_tuning_enabled
        else None,
    }
    report_path = output_dir / "checkpoint_selection.json"
    with report_path.open("w", encoding="utf-8") as file_handle:
        json.dump(report, file_handle, indent=2, ensure_ascii=False)
    return report


def main():
    args = parse_args()
    run_context = None
    output_dir = (
        Path(args.output_dir).expanduser()
        if args.output_dir
        else OUTPUT_DIR / args.model
    )
    preprocessing_mode = resolve_preprocessing_mode(args.model, args.preprocessing)
    checkpoint_metric = args.checkpoint_metric
    checkpoint_mode = resolve_monitor_mode(checkpoint_metric, args.checkpoint_mode)
    early_stopping_monitor = args.early_stopping_monitor or checkpoint_metric
    early_stopping_mode = resolve_monitor_mode(
        early_stopping_monitor,
        args.early_stopping_mode,
    )

    if args.track_db:
        from src.tracking_integration import (
            args_to_parameters,
            model_name_from_train_arg,
            start_tracking_run,
        )

        run_context = start_tracking_run(
            args=args,
            run_type="training",
            script_name="src.train",
            model_name=model_name_from_train_arg(args.model),
            run_name=f"train:{args.model}",
            parameters=args_to_parameters(
                args,
                extra={
                    "augment": not args.no_augment,
                    "checkpoint_dir": str(output_dir),
                    "output_dir": str(output_dir),
                    "preprocessing_mode": preprocessing_mode,
                    "checkpoint_metric": checkpoint_metric,
                    "checkpoint_mode": checkpoint_mode,
                    "early_stopping_monitor": early_stopping_monitor,
                    "early_stopping_mode": early_stopping_mode,
                    "early_stopping_patience": args.early_stopping_patience,
                },
            ),
            random_seed=args.seed,
        )

    try:
        tf.keras.utils.set_random_seed(args.seed)

        output_dir.mkdir(parents=True, exist_ok=True)

        ds_train, ds_val, ds_test, ds_info = load_malaria_splits(
            img_size=args.img_size,
            batch_size=args.batch_size,
            seed=args.seed,
            augment=not args.no_augment,
            preprocessing_mode=preprocessing_mode,
        )

        class_names = ds_info.features["label"].names
        print("Clases:", class_names)
        print("Preprocesamiento:", preprocessing_mode)
        print(
            "Checkpoint metric:",
            checkpoint_metric,
            f"(mode={checkpoint_mode})",
        )
        print(
            "EarlyStopping monitor:",
            early_stopping_monitor,
            f"(mode={early_stopping_mode}, patience={args.early_stopping_patience})",
        )

        input_shape = (args.img_size, args.img_size, 3)

        if args.model == "custom_cnn":
            lr = args.learning_rate if args.learning_rate is not None else 1.0
            model = build_custom_cnn(input_shape=input_shape, learning_rate=lr)
            base_model = None
        else:
            lr = args.learning_rate if args.learning_rate is not None else 0.01
            model, base_model = build_vgg16_transfer(input_shape=input_shape, learning_rate=lr)

        model.summary()

        checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
            filepath=str(output_dir / "best_model.keras"),
            monitor=checkpoint_metric,
            save_best_only=True,
            mode=checkpoint_mode,
            verbose=1,
        )

        history = model.fit(
            ds_train,
            validation_data=ds_val,
            epochs=args.epochs,
            callbacks=build_phase_callbacks(
                output_dir=output_dir,
                checkpoint_callback=checkpoint_callback,
                phase="training_base",
                early_stopping_monitor=early_stopping_monitor,
                early_stopping_mode=early_stopping_mode,
                early_stopping_patience=args.early_stopping_patience,
            ),
        )

        fine_tune_history = None
        if args.model == "vgg16" and args.fine_tune_epochs > 0:
            print("Iniciando fine-tuning parcial de VGG16...")
            unfreeze_last_layers(base_model, n_layers=4)
            model = compile_binary_model(
                model,
                learning_rate=0.001,
                optimizer_name="adadelta",
            )

            fine_tune_history = model.fit(
                ds_train,
                validation_data=ds_val,
                epochs=args.fine_tune_epochs,
                callbacks=build_phase_callbacks(
                    output_dir=output_dir,
                    checkpoint_callback=checkpoint_callback,
                    phase="fine_tuning",
                    early_stopping_monitor=early_stopping_monitor,
                    early_stopping_mode=early_stopping_mode,
                    early_stopping_patience=args.early_stopping_patience,
                ),
            )

        print("Evaluación en test:")
        metrics = evaluate_keras_model(
            model=model,
            dataset=ds_test,
            class_names=class_names,
            output_dir=output_dir,
            prefix="test",
            threshold=0.5,
            metadata={"preprocessing_mode": preprocessing_mode},
        )

        model.save(output_dir / "final_model.keras")
        checkpoint_selection = write_checkpoint_selection_report(
            output_dir=output_dir,
            checkpoint_metric=checkpoint_metric,
            checkpoint_mode=checkpoint_mode,
            early_stopping_monitor=early_stopping_monitor,
            early_stopping_mode=early_stopping_mode,
            checkpoint_callback=checkpoint_callback,
            fine_tuning_enabled=fine_tune_history is not None,
        )
        print(f"Modelo final guardado en: {output_dir / 'final_model.keras'}")
        print(f"Mejor modelo guardado en: {output_dir / 'best_model.keras'}")
        print(f"Criterio de selección guardado en: {output_dir / 'checkpoint_selection.json'}")

        if args.track_db and run_context:
            from src.tracking_integration import (
                finish_tracking_run,
                log_metrics_and_reports,
                log_model_version,
                log_output_artifacts,
                log_training_history,
            )

            log_training_history(run_context, history, phase="training_base")
            if fine_tune_history is not None:
                log_training_history(
                    run_context,
                    fine_tune_history,
                    phase="fine_tuning",
                    epoch_offset=len(history.epoch),
                )
            log_metrics_and_reports(run_context, metrics, class_names, split_name="test")
            log_output_artifacts(run_context, output_dir)
            log_model_version(
                run_context,
                version_name=f"{args.model}_tracked",
                best_model_path=str(output_dir / "best_model.keras"),
                final_model_path=str(output_dir / "final_model.keras"),
                metadata={
                    "source": "src.train",
                    "checkpoint_selection": checkpoint_selection,
                },
            )
            finish_tracking_run(
                run_context,
                metadata={
                    "status_detail": "training completed",
                    "checkpoint_selection": checkpoint_selection,
                },
            )
    except Exception as exc:
        if args.track_db and run_context:
            from src.tracking_integration import fail_tracking_run

            fail_tracking_run(run_context, exc, script_name="src.train")
        raise


if __name__ == "__main__":
    main()
