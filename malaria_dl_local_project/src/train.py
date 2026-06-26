import argparse
import json
from pathlib import Path

import tensorflow as tf

from src.checkpoint_policy import (
    CHECKPOINT_POLICY_CHOICES,
    CheckpointPolicyConfig,
    ClinicalCheckpointCallback,
    ClinicalValidationMetricsCallback,
    checkpoint_policy_config_dict,
    get_monitor_for_policy,
    write_checkpoint_policy_summary,
)
from src.config import (
    CLASS_NAMES,
    LABEL_MAPPING_METADATA,
    LABEL_MAPPING_VERSION,
    RAW_MODEL_SCORE_MEANING,
    OUTPUT_DIR,
)
from src.data import add_data_source_args, dataset_tracking_metadata, load_malaria_splits
from src.metrics import collect_predictions, evaluate_keras_model
from src.model_metadata import (
    build_model_metadata,
    clinical_threshold_metadata_from_calibration,
    write_model_metadata,
)
from src.models import (
    build_custom_cnn,
    build_vgg16_transfer,
    compile_binary_model,
    unfreeze_last_layers,
)
from src.preprocessing import PREPROCESSING_CHOICES, resolve_preprocessing_mode
from src.threshold_calibration import (
    default_threshold_calibration_path,
    find_threshold_for_target_recall,
    write_threshold_calibration,
)


CHECKPOINT_METRIC_CHOICES = [
    "val_auc",
    "val_roc_auc_parasitized",
    "val_pr_auc",
    "val_pr_auc_parasitized",
    "val_f2_parasitized",
    "val_balanced_accuracy",
    "val_recall_parasitized",
    "val_sensitivity_parasitized",
    "val_specificity",
    "val_precision",
    "val_recall",
    "val_accuracy",
    "val_loss",
]


def parse_args(argv=None):
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
        default=None,
        help=(
            "Métrica legacy monitoreada para reportes/compatibilidad. "
            "La selección de best_model.keras usa --checkpoint-policy."
        ),
    )
    parser.add_argument(
        "--checkpoint-policy",
        choices=CHECKPOINT_POLICY_CHOICES,
        default="auc_with_min_recall",
        help=(
            "Política clínica para seleccionar best_model.keras. "
            "Default recomendado: auc_with_min_recall."
        ),
    )
    parser.add_argument(
        "--min-recall",
        type=float,
        default=0.98,
        help="Sensibilidad mínima requerida para auc_with_min_recall.",
    )
    parser.add_argument(
        "--beta",
        type=float,
        default=2.0,
        help="Beta del F-score usado por la política f2.",
    )
    parser.add_argument(
        "--reject-prediction-collapse",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Excluir epochs con colapso de predicción al seleccionar checkpoint.",
    )
    parser.add_argument(
        "--allow-collapsed-checkpoint",
        action="store_true",
        help="Permite seleccionar checkpoints colapsados si se solicita explícitamente.",
    )
    parser.add_argument(
        "--min-class-fraction",
        type=float,
        default=0.05,
        help="Fracción mínima por clase predicha para no marcar colapso.",
    )
    parser.add_argument(
        "--calibrate-threshold",
        action="store_true",
        help="Calibrar threshold clínico con validation al terminar entrenamiento.",
    )
    parser.add_argument(
        "--target-recall",
        type=float,
        default=0.98,
        help="Sensibilidad objetivo para calibración de threshold clínico.",
    )
    parser.add_argument(
        "--min-specificity",
        type=float,
        default=None,
        help="Especificidad mínima opcional durante calibración de threshold.",
    )
    parser.add_argument(
        "--threshold-output-json",
        default=None,
        help="Ruta opcional para threshold_calibration.json.",
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
    args = parser.parse_args(argv)
    if args.allow_collapsed_checkpoint:
        args.reject_prediction_collapse = False
    return args


def resolve_monitor_mode(monitor, requested_mode="auto"):
    if requested_mode != "auto":
        return requested_mode
    return "min" if str(monitor).endswith("loss") else "max"


def build_phase_callbacks(
    output_dir,
    checkpoint_callback,
    clinical_validation_callback,
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
        clinical_validation_callback,
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
    checkpoint_policy_config,
    checkpoint_monitor,
    checkpoint_mode,
    early_stopping_monitor,
    early_stopping_mode,
    checkpoint_callback,
    fine_tuning_enabled,
):
    policy_selection = checkpoint_callback.best_selection or {}
    policy_summary = checkpoint_callback.selection_summary() or {}
    write_checkpoint_policy_summary(output_dir, policy_summary)
    report = {
        "best_model_path": str(output_dir / "best_model.keras"),
        "checkpoint_policy": checkpoint_policy_config.policy,
        "checkpoint_policy_config": checkpoint_policy_config_dict(checkpoint_policy_config),
        "checkpoint_selection": policy_selection,
        "checkpoint_policy_summary": policy_summary,
        "checkpoint_metric": checkpoint_monitor,
        "checkpoint_monitor": checkpoint_monitor,
        "checkpoint_mode": checkpoint_mode,
        "best_checkpoint_value": json_safe_float(
            policy_selection.get("selected_metric_value")
        ),
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
    checkpoint_policy_config = CheckpointPolicyConfig(
        policy=args.checkpoint_policy,
        min_recall=args.min_recall,
        beta=args.beta,
        threshold=0.5,
        reject_prediction_collapse=args.reject_prediction_collapse,
        min_class_fraction=args.min_class_fraction,
    )
    policy_monitor, policy_mode = get_monitor_for_policy(checkpoint_policy_config)
    checkpoint_monitor = args.checkpoint_monitor or policy_monitor
    checkpoint_mode = resolve_monitor_mode(
        checkpoint_monitor,
        args.monitor_mode if args.checkpoint_monitor else policy_mode,
    )
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
                    "checkpoint_policy": checkpoint_policy_config.policy,
                    "checkpoint_policy_config": checkpoint_policy_config_dict(
                        checkpoint_policy_config
                    ),
                    "min_recall_required": checkpoint_policy_config.min_recall,
                    "reject_prediction_collapse": (
                        checkpoint_policy_config.reject_prediction_collapse
                    ),
                    "min_class_fraction": checkpoint_policy_config.min_class_fraction,
                    "calibrate_threshold": bool(args.calibrate_threshold),
                    "target_recall": args.target_recall,
                    "min_specificity": args.min_specificity,
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
        print("Checkpoint policy:", checkpoint_policy_config.policy)
        print("Minimum validation recall required:", checkpoint_policy_config.min_recall)
        print("Beta for F-score:", checkpoint_policy_config.beta)
        print(
            "Reject prediction collapse:",
            str(checkpoint_policy_config.reject_prediction_collapse).lower(),
        )
        print("Min class fraction:", checkpoint_policy_config.min_class_fraction)
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

        clinical_validation_callback = ClinicalValidationMetricsCallback(
            validation_data=ds_val,
            threshold=checkpoint_policy_config.threshold,
            min_class_fraction=checkpoint_policy_config.min_class_fraction,
            class_names=class_names,
            verbose=0,
        )
        checkpoint_callback = ClinicalCheckpointCallback(
            output_dir=output_dir,
            config=checkpoint_policy_config,
            verbose=1,
        )

        checkpoint_callback.set_phase("training_base", epoch_offset=0)
        history = model.fit(
            ds_train,
            validation_data=ds_val,
            epochs=args.epochs,
            callbacks=build_phase_callbacks(
                output_dir=output_dir,
                checkpoint_callback=checkpoint_callback,
                clinical_validation_callback=clinical_validation_callback,
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

            checkpoint_callback.set_phase(
                "fine_tuning",
                epoch_offset=len(history.epoch),
            )
            fine_tune_history = model.fit(
                ds_train,
                validation_data=ds_val,
                epochs=args.fine_tune_epochs,
                callbacks=build_phase_callbacks(
                    output_dir=output_dir,
                    checkpoint_callback=checkpoint_callback,
                    clinical_validation_callback=clinical_validation_callback,
                    phase="fine_tuning",
                    early_stopping_monitor=early_stopping_monitor,
                    early_stopping_mode=early_stopping_mode,
                    early_stopping_patience=args.early_stopping_patience,
                ),
            )

        final_model_path = output_dir / "final_model.keras"
        best_model_path = output_dir / "best_model.keras"
        model.save(final_model_path)
        if best_model_path.exists():
            print(f"Cargando mejor checkpoint para evaluación: {best_model_path}")
            evaluation_model = tf.keras.models.load_model(best_model_path)
        else:
            print(
                "WARNING: no existe best_model.keras; se guardará el modelo final "
                "como fallback."
            )
            model.save(best_model_path)
            evaluation_model = model

        threshold_calibration = None
        threshold_calibration_path = None
        clinical_threshold_metadata = None
        test_threshold = 0.5
        threshold_info = {
            "threshold_requested": 0.5,
            "threshold_mode": "fixed",
            "threshold_used": 0.5,
            "threshold_source": "fixed",
            "clinical_threshold": None,
            "target_recall": None,
            "target_recall_satisfied_on_validation": None,
            "expected_specificity": None,
            "warning": None,
        }
        if args.calibrate_threshold:
            print("Calibrando threshold clínico con validation set...")
            y_val_true, _, y_val_score = collect_predictions(
                evaluation_model,
                ds_val,
                class_names=class_names,
                threshold=0.5,
                label_mapping_version=LABEL_MAPPING_VERSION,
            )
            threshold_calibration = find_threshold_for_target_recall(
                y_true=y_val_true,
                y_scores=y_val_score,
                target_recall=args.target_recall,
                min_specificity=args.min_specificity,
                beta=args.beta,
            )
            threshold_calibration.update(
                {
                    "checkpoint": str(best_model_path),
                    "model_name": args.model,
                    "img_size": args.img_size,
                    "batch_size": args.batch_size,
                    "preprocessing_mode": preprocessing_mode,
                    "dataset": dataset_info,
                }
            )
            threshold_calibration_path = Path(
                args.threshold_output_json
            ).expanduser() if args.threshold_output_json else default_threshold_calibration_path(
                output_dir
            )
            write_threshold_calibration(
                threshold_calibration_path,
                threshold_calibration,
            )
            clinical_threshold_metadata = clinical_threshold_metadata_from_calibration(
                threshold_calibration
            )
            test_threshold = float(threshold_calibration["threshold_selected"])
            threshold_info = {
                "threshold_requested": "clinical",
                "threshold_mode": "clinical",
                "threshold_used": test_threshold,
                "threshold_source": "validation_calibration",
                "clinical_threshold": clinical_threshold_metadata,
                "target_recall": threshold_calibration.get("target_recall"),
                "target_recall_satisfied_on_validation": threshold_calibration.get(
                    "target_recall_satisfied_on_validation"
                ),
                "expected_specificity": (
                    threshold_calibration.get("selected_metrics", {}).get(
                        "specificity"
                    )
                ),
                "warning": threshold_calibration.get("warning"),
            }
            print(f"Threshold clínico seleccionado: {test_threshold:.6f}")
            print(
                "Target recall satisfecho en validation:",
                threshold_calibration.get("target_recall_satisfied"),
            )
            if threshold_calibration.get("warning"):
                print(f"WARNING: {threshold_calibration['warning']}")

        print("Evaluación en test:")
        metrics = evaluate_keras_model(
            model=evaluation_model,
            dataset=ds_test,
            class_names=class_names,
            output_dir=output_dir,
            prefix="test",
            threshold=test_threshold,
            metadata={
                "preprocessing_mode": preprocessing_mode,
                "label_mapping_version": LABEL_MAPPING_VERSION,
                "label_mapping": LABEL_MAPPING_METADATA,
                "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
                **threshold_info,
                **dataset_info,
            },
        )

        checkpoint_selection = write_checkpoint_selection_report(
            output_dir=output_dir,
            checkpoint_policy_config=checkpoint_policy_config,
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
                "checkpoint_policy": checkpoint_policy_config.policy,
                "checkpoint_policy_config": checkpoint_policy_config_dict(
                    checkpoint_policy_config
                ),
                "checkpoint_selection": checkpoint_selection.get(
                    "checkpoint_selection"
                ),
                "checkpoint_policy_summary": checkpoint_selection.get(
                    "checkpoint_policy_summary"
                ),
                "early_stopping_mode": early_stopping_mode,
                "early_stopping_patience": args.early_stopping_patience,
                "fine_tuning_enabled": fine_tune_history is not None,
                "calibrate_threshold": bool(args.calibrate_threshold),
                "threshold_calibration": threshold_calibration,
                "threshold_calibration_path": (
                    None if threshold_calibration_path is None else str(threshold_calibration_path)
                ),
                "clinical_threshold": clinical_threshold_metadata,
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
        policy_summary = checkpoint_selection.get("checkpoint_policy_summary") or {}
        print("Best checkpoint selection:")
        print(f"- policy: {policy_summary.get('policy')}")
        print(f"- selected_epoch: {policy_summary.get('selected_epoch')}")
        print(f"- policy_satisfied: {policy_summary.get('policy_satisfied')}")
        print(
            "- val_recall_parasitized: "
            f"{policy_summary.get('selected_metrics', {}).get('val_recall_parasitized')}"
        )
        print(
            "- val_auc: "
            f"{policy_summary.get('selected_metrics', {}).get('val_auc')}"
        )
        print(
            "- val_f2_parasitized: "
            f"{policy_summary.get('selected_metrics', {}).get('val_f2_parasitized')}"
        )
        print(
            "- val_specificity: "
            f"{policy_summary.get('selected_metrics', {}).get('val_specificity')}"
        )
        print(
            "- collapsed: "
            f"{policy_summary.get('prediction_collapse_detected')}"
        )
        print(f"- checkpoint_path: {policy_summary.get('checkpoint_path')}")
        if policy_summary.get("warning"):
            print(f"- warning: {policy_summary.get('warning')}")
        print(f"Modelo final guardado en: {output_dir / 'final_model.keras'}")
        print(f"Mejor modelo guardado en: {output_dir / 'best_model.keras'}")
        if threshold_calibration_path is not None:
            print(f"Calibración de threshold guardada en: {threshold_calibration_path}")
        print(f"Criterio de selección guardado en: {output_dir / 'checkpoint_selection.json'}")
        print(
            "Resumen de política guardado en: "
            f"{output_dir / 'checkpoint_policy_summary.json'}"
        )
        print(f"Metadata de modelo guardada en: {metadata_path}")

        if args.track_db and run_context:
            from src.tracking_integration import (
                args_to_parameters,
                clinical_metrics_for_tracking,
                finish_tracking_run,
                log_metrics_and_reports,
                log_model_version,
                log_output_artifacts,
                log_training_history,
                output_artifacts_from_directory,
                record_run_dataset_images,
                record_run_io,
                threshold_calibration_for_tracking,
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
            record_run_dataset_images(
                run_context,
                dataset_info=dataset_info,
                usage_context="train",
                splits=["train"],
                batch_size=args.batch_size,
            )
            record_run_dataset_images(
                run_context,
                dataset_info=dataset_info,
                usage_context="validation",
                splits=["val"],
                batch_size=args.batch_size,
            )
            record_run_dataset_images(
                run_context,
                dataset_info=dataset_info,
                usage_context="evaluation",
                splits=["test"],
                batch_size=args.batch_size,
            )
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
                    "checkpoint_policy": checkpoint_policy_config.policy,
                    "checkpoint_policy_config": checkpoint_policy_config_dict(
                        checkpoint_policy_config
                    ),
                    "checkpoint_selection": checkpoint_selection,
                    "checkpoint_policy_summary": policy_summary,
                    "threshold_calibration": threshold_calibration,
                    "clinical_threshold": clinical_threshold_metadata,
                    **threshold_calibration_for_tracking(threshold_calibration),
                    "model_metadata": model_metadata,
                    **dataset_info,
                },
            )
            record_run_io(
                run_context,
                script_name="src.train",
                input_parameters=args_to_parameters(
                    args,
                    extra={
                        "augment": not args.no_augment,
                        "output_dir": str(output_dir),
                        "preprocessing_mode": preprocessing_mode,
                        "checkpoint_policy": checkpoint_policy_config.policy,
                        "checkpoint_policy_config": checkpoint_policy_config_dict(
                            checkpoint_policy_config
                        ),
                        "selected_epoch": policy_summary.get("selected_epoch"),
                        "policy_satisfied": policy_summary.get("policy_satisfied"),
                        "selected_metric": policy_summary.get("selected_metric"),
                        "selected_metric_value": policy_summary.get(
                            "selected_metric_value"
                        ),
                        "min_recall_required": checkpoint_policy_config.min_recall,
                        "prediction_collapse_detected": policy_summary.get(
                            "prediction_collapse_detected"
                        ),
                        "all_epochs_collapsed": policy_summary.get(
                            "all_epochs_collapsed"
                        ),
                        "checkpoint_warning": policy_summary.get("warning"),
                        "calibrate_threshold": bool(args.calibrate_threshold),
                        "threshold_calibration": threshold_calibration,
                        "clinical_threshold": clinical_threshold_metadata,
                        "threshold_calibration_path": (
                            None
                            if threshold_calibration_path is None
                            else str(threshold_calibration_path)
                        ),
                        **threshold_calibration_for_tracking(threshold_calibration),
                        "checkpoint_monitor": checkpoint_monitor,
                        "checkpoint_mode": checkpoint_mode,
                        "early_stopping_monitor": early_stopping_monitor,
                        "early_stopping_mode": early_stopping_mode,
                        "early_stopping_patience": args.early_stopping_patience,
                        "optimizer": args.optimizer,
                        **dataset_info,
                    },
                ),
                output_results={
                    "final_epoch": len(history.epoch)
                    + (0 if fine_tune_history is None else len(fine_tune_history.epoch)),
                    "best_checkpoint": str(output_dir / "best_model.keras"),
                    "final_model": str(output_dir / "final_model.keras"),
                    "training_log": str(output_dir / "training_log.csv"),
                    "test_metrics": str(output_dir / "test_metrics.json"),
                    "test_predictions": str(output_dir / "test_predictions.csv"),
                    "test_confusion_matrix": str(output_dir / "test_confusion_matrix.csv"),
                    "threshold_used": test_threshold,
                    "threshold_calibration": threshold_calibration,
                    "clinical_threshold": clinical_threshold_metadata,
                    "threshold_calibration_path": (
                        None
                        if threshold_calibration_path is None
                        else str(threshold_calibration_path)
                    ),
                    **threshold_calibration_for_tracking(threshold_calibration),
                    "checkpoint_policy": checkpoint_policy_config.policy,
                    "checkpoint_policy_config": checkpoint_policy_config_dict(
                        checkpoint_policy_config
                    ),
                    "checkpoint_selection": checkpoint_selection,
                    "checkpoint_policy_summary": policy_summary,
                    "checkpoint_policy_summary_path": str(
                        output_dir / "checkpoint_policy_summary.json"
                    ),
                    "selected_epoch": policy_summary.get("selected_epoch"),
                    "policy_satisfied": policy_summary.get("policy_satisfied"),
                    "selected_metric": policy_summary.get("selected_metric"),
                    "selected_metric_value": policy_summary.get("selected_metric_value"),
                    "min_recall_required": checkpoint_policy_config.min_recall,
                    "val_recall_parasitized_selected": (
                        policy_summary.get("selected_metrics", {}).get(
                            "val_recall_parasitized"
                        )
                    ),
                    "val_f2_parasitized_selected": (
                        policy_summary.get("selected_metrics", {}).get(
                            "val_f2_parasitized"
                        )
                    ),
                    "val_specificity_selected": (
                        policy_summary.get("selected_metrics", {}).get(
                            "val_specificity"
                        )
                    ),
                    "val_auc_selected": (
                        policy_summary.get("selected_metrics", {}).get("val_auc")
                    ),
                    "prediction_collapse_detected": policy_summary.get(
                        "prediction_collapse_detected"
                    ),
                    "all_epochs_collapsed": policy_summary.get("all_epochs_collapsed"),
                    "checkpoint_warning": policy_summary.get("warning"),
                    "metrics": metrics,
                    **threshold_info,
                    **clinical_metrics_for_tracking(metrics),
                },
                output_artifacts=output_artifacts_from_directory(output_dir),
                dataset_metadata=dataset_info,
                metadata={"status_detail": "training completed"},
            )
            finish_tracking_run(
                run_context,
                metadata={
                    "status_detail": "training completed",
                    "label_mapping_version": LABEL_MAPPING_VERSION,
                    "label_mapping": LABEL_MAPPING_METADATA,
                    "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
                    "checkpoint_policy": checkpoint_policy_config.policy,
                    "checkpoint_policy_config": checkpoint_policy_config_dict(
                        checkpoint_policy_config
                    ),
                    "checkpoint_selection": checkpoint_selection,
                    "checkpoint_policy_summary": policy_summary,
                    "selected_epoch": policy_summary.get("selected_epoch"),
                    "policy_satisfied": policy_summary.get("policy_satisfied"),
                    "selected_metric": policy_summary.get("selected_metric"),
                    "selected_metric_value": policy_summary.get("selected_metric_value"),
                    "min_recall_required": checkpoint_policy_config.min_recall,
                    "val_recall_parasitized_selected": (
                        policy_summary.get("selected_metrics", {}).get(
                            "val_recall_parasitized"
                        )
                    ),
                    "val_f2_parasitized_selected": (
                        policy_summary.get("selected_metrics", {}).get(
                            "val_f2_parasitized"
                        )
                    ),
                    "val_specificity_selected": (
                        policy_summary.get("selected_metrics", {}).get(
                            "val_specificity"
                        )
                    ),
                    "val_auc_selected": (
                        policy_summary.get("selected_metrics", {}).get("val_auc")
                    ),
                    "prediction_collapse_detected": policy_summary.get(
                        "prediction_collapse_detected"
                    ),
                    "all_epochs_collapsed": policy_summary.get("all_epochs_collapsed"),
                    "checkpoint_warning": policy_summary.get("warning"),
                    "threshold_calibration": threshold_calibration,
                    "clinical_threshold": clinical_threshold_metadata,
                    "threshold_calibration_path": (
                        None
                        if threshold_calibration_path is None
                        else str(threshold_calibration_path)
                    ),
                    **threshold_calibration_for_tracking(threshold_calibration),
                    "model_metadata": model_metadata,
                    **threshold_info,
                    **dataset_info,
                    **clinical_metrics_for_tracking(metrics),
                },
            )
    except Exception as exc:
        if args.track_db and run_context:
            from src.tracking_integration import fail_tracking_run

            fail_tracking_run(run_context, exc, script_name="src.train")
        raise


if __name__ == "__main__":
    main()
