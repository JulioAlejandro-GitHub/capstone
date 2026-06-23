import argparse
import json
from pathlib import Path

import tensorflow as tf

from src.config import (
    CLASS_NAMES,
    LABEL_MAPPING_METADATA,
    LABEL_MAPPING_VERSION,
    RAW_MODEL_SCORE_MEANING,
    OUTPUT_DIR,
)
from src.data import add_data_source_args, dataset_tracking_metadata, load_malaria_splits
from src.metrics import evaluate_keras_model
from src.model_metadata import build_model_metadata, write_model_metadata
from src.models import (
    build_custom_cnn,
    build_vgg16_transfer,
    compile_binary_model,
    unfreeze_last_layers,
)
from src.preprocessing import PREPROCESSING_CHOICES, resolve_preprocessing_mode


CHECKPOINT_METRIC_CHOICES = [
    "val_auc",
    "val_balanced_accuracy",
    "val_recall_parasitized",
    "val_specificity",
    "val_precision",
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
    parser.add_argument("--fine-tune-learning-rate", type=float, default=None)
    parser.add_argument(
        "--optimizer",
        choices=["adam", "adamw", "sgd", "adadelta"],
        default="adam",
        help="Optimizador para entrenamiento. Default recomendado: adam.",
    )
    parser.add_argument("--no-augment", action="store_true")
    parser.add_argument(
        "--checkpoint-monitor",
        "--checkpoint-metric",
        dest="checkpoint_monitor",
        choices=CHECKPOINT_METRIC_CHOICES,
        default="val_auc",
        help=(
            "Métrica monitoreada para guardar best_model.keras. "
            "Default recomendado: val_auc. val_recall_parasitized queda "
            "disponible solo como opción explícita."
        ),
    )
    parser.add_argument(
        "--monitor-mode",
        "--checkpoint-mode",
        dest="monitor_mode",
        choices=["auto", "max", "min"],
        default="auto",
        help="Modo de comparación del checkpoint. 'auto' usa min para loss y max para el resto.",
    )
    parser.add_argument(
        "--early-stopping-monitor",
        choices=CHECKPOINT_METRIC_CHOICES,
        default="val_auc",
        help=(
            "Métrica para EarlyStopping. Default recomendado: val_auc."
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
    add_data_source_args(parser)
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
    checkpoint_monitor,
    checkpoint_mode,
    early_stopping_monitor,
    early_stopping_mode,
    checkpoint_callback,
    fine_tuning_enabled,
):
    report = {
        "best_model_path": str(output_dir / "best_model.keras"),
        "checkpoint_metric": checkpoint_monitor,
        "checkpoint_monitor": checkpoint_monitor,
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
        "label_mapping_version": LABEL_MAPPING_VERSION,
        "label_mapping": LABEL_MAPPING_METADATA,
        "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
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
    checkpoint_monitor = args.checkpoint_monitor
    checkpoint_mode = resolve_monitor_mode(checkpoint_monitor, args.monitor_mode)
    early_stopping_monitor = args.early_stopping_monitor or checkpoint_monitor
    early_stopping_mode = resolve_monitor_mode(
        early_stopping_monitor,
        args.early_stopping_mode,
    )
    dataset_info = dataset_tracking_metadata(args.data_source, args.dataset_dir)

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
                    "class_names": CLASS_NAMES,
                    "label_mapping_version": LABEL_MAPPING_VERSION,
                    "label_mapping": LABEL_MAPPING_METADATA,
                    "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
                    "checkpoint_monitor": checkpoint_monitor,
                    "checkpoint_metric": checkpoint_monitor,
                    "checkpoint_mode": checkpoint_mode,
                    "early_stopping_monitor": early_stopping_monitor,
                    "early_stopping_mode": early_stopping_mode,
                    "early_stopping_patience": args.early_stopping_patience,
                    "optimizer": args.optimizer,
                    **dataset_info,
                },
            ),
            random_seed=args.seed,
        )
    # if args.model == "vgg16"
    # if args.model == "custom_cnn":
    # validar datos de ejecucion antes de comenzar... en este caaso el nombre del modelo

    try:
        tf.keras.utils.set_random_seed(args.seed)

        output_dir.mkdir(parents=True, exist_ok=True)

        ds_train, ds_val, ds_test, _ = load_malaria_splits(
            img_size=args.img_size,
            batch_size=args.batch_size,
            seed=args.seed,
            augment=not args.no_augment,
            preprocessing_mode=preprocessing_mode,
            data_source=args.data_source,
            dataset_dir=args.dataset_dir,
        )

        class_names = CLASS_NAMES
        print("Clases clínicas:", class_names)
        print("Convención de etiquetas:", LABEL_MAPPING_VERSION)
        print("raw_model_score:", RAW_MODEL_SCORE_MEANING)
        print("Preprocesamiento:", preprocessing_mode)
        print(
            "Checkpoint metric:",
            checkpoint_monitor,
            f"(mode={checkpoint_mode})",
        )
        print(
            "EarlyStopping monitor:",
            early_stopping_monitor,
            f"(mode={early_stopping_mode}, patience={args.early_stopping_patience})",
        )

        input_shape = (args.img_size, args.img_size, 3)

        if args.model == "custom_cnn":
            lr = args.learning_rate if args.learning_rate is not None else 1e-4
            model = build_custom_cnn(
                input_shape=input_shape,
                learning_rate=lr,
                optimizer_name=args.optimizer,
            )
            base_model = None
        else:
            lr = args.learning_rate if args.learning_rate is not None else 1e-4
            model, base_model = build_vgg16_transfer(
                input_shape=input_shape,
                learning_rate=lr,
                optimizer_name=args.optimizer,
            )

        model.summary()

        checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
            filepath=str(output_dir / "best_model.keras"),
            monitor=checkpoint_monitor,
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
            fine_tune_lr = (
                args.fine_tune_learning_rate
                if args.fine_tune_learning_rate is not None
                else 1e-5
            )
            model = compile_binary_model(
                model,
                learning_rate=fine_tune_lr,
                optimizer_name=args.optimizer,
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
            metadata={
                "preprocessing_mode": preprocessing_mode,
                "label_mapping_version": LABEL_MAPPING_VERSION,
                "label_mapping": LABEL_MAPPING_METADATA,
                "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
                **dataset_info,
            },
        )

        model.save(output_dir / "final_model.keras")
        checkpoint_selection = write_checkpoint_selection_report(
            output_dir=output_dir,
            checkpoint_monitor=checkpoint_monitor,
            checkpoint_mode=checkpoint_mode,
            early_stopping_monitor=early_stopping_monitor,
            early_stopping_mode=early_stopping_mode,
            checkpoint_callback=checkpoint_callback,
            fine_tuning_enabled=fine_tune_history is not None,
        )
        model_metadata = build_model_metadata(
            model_name=args.model,
            threshold_default=0.5,
            preprocessing=preprocessing_mode,
            checkpoint_monitor=checkpoint_monitor,
            early_stopping_monitor=early_stopping_monitor,
            optimizer=args.optimizer,
            learning_rate=lr,
            extra={
                "checkpoint_mode": checkpoint_mode,
                "early_stopping_mode": early_stopping_mode,
                "early_stopping_patience": args.early_stopping_patience,
                "fine_tuning_enabled": fine_tune_history is not None,
                "fine_tune_learning_rate": (
                    None
                    if fine_tune_history is None
                    else (
                        args.fine_tune_learning_rate
                        if args.fine_tune_learning_rate is not None
                        else 1e-5
                    )
                ),
                "img_size": args.img_size,
                "batch_size": args.batch_size,
                "augment": not args.no_augment,
                **dataset_info,
            },
        )
        metadata_path = write_model_metadata(output_dir, model_metadata)
        print(f"Modelo final guardado en: {output_dir / 'final_model.keras'}")
        print(f"Mejor modelo guardado en: {output_dir / 'best_model.keras'}")
        print(f"Criterio de selección guardado en: {output_dir / 'checkpoint_selection.json'}")
        print(f"Metadata de modelo guardada en: {metadata_path}")

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
                    "label_mapping_version": LABEL_MAPPING_VERSION,
                    "label_mapping": LABEL_MAPPING_METADATA,
                    "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
                    "checkpoint_selection": checkpoint_selection,
                    "model_metadata": model_metadata,
                    **dataset_info,
                },
            )
            finish_tracking_run(
                run_context,
                metadata={
                    "status_detail": "training completed",
                    "label_mapping_version": LABEL_MAPPING_VERSION,
                    "label_mapping": LABEL_MAPPING_METADATA,
                    "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
                    "checkpoint_selection": checkpoint_selection,
                    "model_metadata": model_metadata,
                    **dataset_info,
                    "specificity": metrics.get("specificity"),
                    "balanced_accuracy": metrics.get("balanced_accuracy"),
                    "prediction_collapse_detected": metrics.get(
                        "prediction_collapse_detected"
                    ),
                    "n_pred_uninfected": metrics.get("n_pred_uninfected"),
                    "n_pred_parasitized": metrics.get("n_pred_parasitized"),
                    "percent_pred_uninfected": metrics.get("percent_pred_uninfected"),
                    "percent_pred_parasitized": metrics.get("percent_pred_parasitized"),
                },
            )
    except Exception as exc:
        if args.track_db and run_context:
            from src.tracking_integration import fail_tracking_run

            fail_tracking_run(run_context, exc, script_name="src.train")
        raise


if __name__ == "__main__":
    main()
