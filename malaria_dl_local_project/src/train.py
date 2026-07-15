import argparse
import csv
import json
import shutil
from pathlib import Path
from uuid import uuid4

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
from src.execution_types import FINE_TUNING, TRAIN_BASE, TRAIN_COMBINED
from src.metrics import collect_predictions, evaluate_keras_model
from src.model_execution_config import ModelExecutionConfig
from src.model_metadata import (
    build_model_metadata,
    clinical_threshold_metadata_from_calibration,
    disabled_clinical_threshold_metadata,
    write_model_metadata,
)
from src.models import (
    build_custom_cnn,
    build_densenet121_transfer,
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
    parser.add_argument(
        "--model",
        choices=["custom_cnn", "vgg16", "densenet121"],
        required=True,
    )
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--fine-tune-epochs", type=int, default=0)
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument("--fine-tune-learning-rate", type=float, default=None)
    parser.add_argument(
        "--pretrained-weights",
        choices=["imagenet", "none"],
        default="imagenet",
        help=(
            "Pesos iniciales de backbones transfer-learning. Use 'none' para "
            "evitar descarga y entrenar desde inicialización aleatoria."
        ),
    )
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
    parser.add_argument(
        "--positive-label",
        choices=["parasitized"],
        default="parasitized",
        help="Clase clínica positiva fija del proyecto (1 = parasitized).",
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
    if args.epochs <= 0:
        parser.error("--epochs debe ser mayor que cero.")
    if args.fine_tune_epochs < 0:
        parser.error("--fine-tune-epochs no puede ser negativo.")
    if args.img_size <= 0 or args.batch_size <= 0:
        parser.error("--img-size y --batch-size deben ser mayores que cero.")
    if args.learning_rate is not None and args.learning_rate <= 0:
        parser.error("--learning-rate debe ser mayor que cero.")
    if (
        args.fine_tune_learning_rate is not None
        and args.fine_tune_learning_rate <= 0
    ):
        parser.error("--fine-tune-learning-rate debe ser mayor que cero.")
    if args.model == "custom_cnn" and args.fine_tune_epochs > 0:
        parser.error(
            "--fine-tune-epochs requiere un backbone transfer-learning "
            "(vgg16 o densenet121)."
        )
    if args.model == "densenet121" and args.preprocessing == "vgg16_imagenet":
        parser.error(
            "densenet121 no es compatible con --preprocessing vgg16_imagenet; "
            "use auto o rescale_0_1."
        )
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


def resolve_training_execution_type(fine_tune_epochs):
    return TRAIN_COMBINED if int(fine_tune_epochs or 0) > 0 else TRAIN_BASE


def _history_epoch_count(history):
    if history is None:
        return 0
    epochs = getattr(history, "epoch", None)
    if epochs is not None:
        return len(epochs)
    history_dict = getattr(history, "history", {}) or {}
    return max((len(values) for values in history_dict.values()), default=0)


def _history_scalar(history_dict, index, *keys, default=None):
    for key in keys:
        values = history_dict.get(key)
        if values is None or index >= len(values):
            continue
        value = values[index]
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            return value
    return default


def write_combined_training_history(
    output_dir,
    base_history,
    fine_tune_history=None,
    base_learning_rate=None,
    fine_tune_learning_rate=None,
):
    """Write a continuous, phase-aware history CSV for one training run."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []

    for phase, phase_history, fallback_learning_rate in (
        ("base", base_history, base_learning_rate),
        ("fine_tuning", fine_tune_history, fine_tune_learning_rate),
    ):
        if phase_history is None:
            continue
        history_dict = getattr(phase_history, "history", {}) or {}
        for phase_index in range(_history_epoch_count(phase_history)):
            rows.append(
                {
                    "epoch": len(rows),
                    "phase": phase,
                    "accuracy": _history_scalar(
                        history_dict,
                        phase_index,
                        "accuracy",
                    ),
                    "val_accuracy": _history_scalar(
                        history_dict,
                        phase_index,
                        "val_accuracy",
                    ),
                    "loss": _history_scalar(history_dict, phase_index, "loss"),
                    "val_loss": _history_scalar(
                        history_dict,
                        phase_index,
                        "val_loss",
                    ),
                    "learning_rate": _history_scalar(
                        history_dict,
                        phase_index,
                        "learning_rate",
                        "lr",
                        default=fallback_learning_rate,
                    ),
                }
            )

    if not rows:
        raise ValueError("No hay épocas completadas para crear el historial combinado.")

    history_path = output_dir / "combined_training_history.csv"
    fieldnames = [
        "epoch",
        "phase",
        "accuracy",
        "val_accuracy",
        "loss",
        "val_loss",
        "learning_rate",
    ]
    with history_path.open("w", encoding="utf-8", newline="") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    base_epochs_completed = _history_epoch_count(base_history)
    fine_tuning_start_epoch = (
        max(base_epochs_completed - 1, 0)
        if _history_epoch_count(fine_tune_history) > 0
        else None
    )
    return history_path, fine_tuning_start_epoch, rows


def _json_safe_value(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe_value(item) for item in value]
    if hasattr(value, "item") and callable(value.item):
        try:
            return value.item()
        except Exception:
            pass
    return value


def write_model_execution_summary(output_dir, summary):
    """Persist the machine-readable and academic presentation summaries."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = _json_safe_value(summary)
    json_path = output_dir / "model_execution_summary.json"
    markdown_path = output_dir / "model_execution_summary.md"

    with json_path.open("w", encoding="utf-8") as file_handle:
        json.dump(summary, file_handle, indent=2, ensure_ascii=False)

    parameters = summary.get("parameters") or {}
    artifacts = summary.get("artifacts") or []
    plots = summary.get("plots") or {}
    def display(value):
        return "-" if value is None else value

    markdown_lines = [
        f"## Resumen de ejecución — {summary.get('model_name', '-')}",
        "",
        f"- Modelo: {summary.get('model_name', '-')}",
        f"- Tipo de ejecución: {summary.get('execution_type', '-')}",
        f"- Épocas base solicitadas: {summary.get('base_epochs', '-')}",
        f"- Épocas fine-tuning solicitadas: {summary.get('fine_tune_epochs', '-')}",
        f"- Épocas completadas: {summary.get('completed_epochs', '-')}",
        f"- Inicio de fine-tuning: época {display(summary.get('fine_tuning_start_epoch'))}",
        f"- Mejor época (numeración 1-based): {display(summary.get('best_epoch'))}",
        f"- Índice de mejor época en CSV (0-based): {display(summary.get('best_epoch_index'))}",
        f"- Batch size: {parameters.get('batch_size', '-')}",
        f"- Imagen: {parameters.get('img_size', '-')}x{parameters.get('img_size', '-')}",
        f"- Preprocesamiento: {summary.get('preprocessing', '-')}",
        f"- Preprocesamiento interno: {display(summary.get('model_internal_preprocessing'))}",
        f"- Positive label: {summary.get('positive_label', '-')}",
        f"- Política de checkpoint: {summary.get('checkpoint_policy', '-')}",
        f"- Métrica de checkpoint: {summary.get('checkpoint_metric', '-')}",
        f"- Min recall requerido: {parameters.get('min_recall', '-')}",
        f"- Execution ID: {summary.get('execution_id', '-')}",
        f"- Run ID: {summary.get('run_id') or '-'}",
        f"- Tracking PostgreSQL activo: {summary.get('db_tracking_active', False)}",
        f"- Snapshot de artefactos: {summary.get('artifact_snapshot_dir', '-')}",
        "",
        "## Artefactos generados",
        "",
    ]
    markdown_lines.extend(
        f"- {Path(path).name}" for path in artifacts
    )
    if plots:
        markdown_lines.extend(["", "## Gráficos", ""])
        markdown_lines.extend(
            f"- {name}: {Path(path).name}" for name, path in plots.items()
        )
    markdown_lines.extend(
        [
            "",
            "## Reproducibilidad",
            "",
            (
                "Los parámetros completos recibidos y resueltos están disponibles "
                "en `model_execution_summary.json` y, si se habilitó tracking, "
                "en PostgreSQL."
            ),
            "",
        ]
    )
    markdown_path.write_text("\n".join(markdown_lines), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(markdown_path)}


def snapshot_execution_artifacts(
    output_dir,
    execution_id,
    artifact_paths=None,
):
    """Copy this run's files to an immutable per-execution directory."""
    output_dir = Path(output_dir)
    snapshot_dir = output_dir / "runs" / str(execution_id)
    snapshot_dir.mkdir(parents=True, exist_ok=False)

    sources = (
        [Path(path) for path in artifact_paths if Path(path).is_file()]
        if artifact_paths is not None
        else [path for path in output_dir.iterdir() if path.is_file()]
    )
    copied_paths = []
    seen_names = set()
    for source in sources:
        if source.name in seen_names:
            continue
        seen_names.add(source.name)
        destination = snapshot_dir / source.name
        shutil.copy2(source, destination)
        copied_paths.append(str(destination))
    return snapshot_dir, copied_paths


def snapshot_artifact_path(snapshot_dir, path):
    if path is None:
        return None
    candidate = Path(snapshot_dir) / Path(path).name
    return str(candidate) if candidate.exists() else str(path)


def rewrite_snapshot_json_paths(snapshot_dir, source_output_dir):
    """Make copied JSON metadata self-contained without altering CLI inputs."""
    snapshot_dir = Path(snapshot_dir)
    source_output_dir = Path(source_output_dir)
    path_mappings = [
        (str(source_output_dir), str(snapshot_dir)),
        (str(source_output_dir.resolve()), str(snapshot_dir.resolve())),
    ]

    def rewrite(value, parent_key=None):
        if isinstance(value, dict):
            return {
                key: (
                    item
                    if key == "cli_arguments"
                    else rewrite(item, parent_key=key)
                )
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [rewrite(item, parent_key=parent_key) for item in value]
        if not isinstance(value, str):
            return value

        for source, target in path_mappings:
            if value == target or value.startswith(f"{target}/"):
                return value
            if value == source:
                return target
            if value.startswith(f"{source}/"):
                return f"{target}{value[len(source):]}"
        return value

    rewritten_paths = []
    for json_path in sorted(snapshot_dir.glob("*.json")):
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        rewritten = rewrite(payload)
        json_path.write_text(
            json.dumps(rewritten, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        rewritten_paths.append(str(json_path))
    return rewritten_paths


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
    execution_id = str(uuid4())
    execution_type = resolve_training_execution_type(args.fine_tune_epochs)
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
    learning_rate = args.learning_rate if args.learning_rate is not None else 1e-4
    fine_tune_learning_rate = (
        args.fine_tune_learning_rate
        if args.fine_tune_learning_rate is not None
        else (1e-5 if args.fine_tune_epochs > 0 else None)
    )
    execution_config = ModelExecutionConfig(
        model_name=args.model,
        execution_type=execution_type,
        img_size=args.img_size,
        batch_size=args.batch_size,
        epochs=args.epochs,
        fine_tune_epochs=args.fine_tune_epochs,
        learning_rate=learning_rate,
        fine_tune_learning_rate=fine_tune_learning_rate,
        preprocessing=preprocessing_mode,
        checkpoint_policy=args.checkpoint_policy,
        checkpoint_metric=checkpoint_monitor,
        min_recall=args.min_recall,
        target_recall=args.target_recall,
        threshold="clinical" if args.calibrate_threshold else 0.5,
        positive_label=args.positive_label,
        seed=args.seed,
        output_dir=str(output_dir),
        track_db=bool(args.track_db),
    )
    execution_parameters = {
        **execution_config.to_dict(),
        "execution_id": execution_id,
        "cli_arguments": vars(args).copy(),
        "optimizer": args.optimizer,
        "augment": not args.no_augment,
        "pretrained_weights": args.pretrained_weights,
        "checkpoint_mode": checkpoint_mode,
        "early_stopping_monitor": early_stopping_monitor,
        "early_stopping_mode": early_stopping_mode,
        "early_stopping_patience": args.early_stopping_patience,
        "calibrate_threshold": bool(args.calibrate_threshold),
        "model_internal_preprocessing": (
            "densenet_imagenet_channel_mean_std"
            if args.model == "densenet121"
            else None
        ),
        **dataset_info,
    }
    planned_snapshot_dir = output_dir / "runs" / execution_id
    execution_parameters["artifact_snapshot_dir"] = str(planned_snapshot_dir)

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
            run_name=f"{execution_type}:{args.model}",
            parameters=args_to_parameters(
                args,
                extra={
                    "execution_type": execution_type,
                    "execution_parameters": execution_parameters,
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
            execution_type=execution_type,
            execution_parameters=execution_parameters,
            total_epochs=args.epochs + args.fine_tune_epochs,
            completed_epochs=0,
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
        print("Tipo de ejecución:", execution_type)
        print("Preprocesamiento:", preprocessing_mode)
        print("Checkpoint policy:", checkpoint_policy_config.policy)
        print("Minimum validation recall required:", checkpoint_policy_config.min_recall)
        print("Beta for F-score:", checkpoint_policy_config.beta)
        print(
            "Reject prediction collapse:",
            str(checkpoint_policy_config.reject_prediction_collapse).lower(),
        )
        print(
            "Clinical threshold calibration:",
            "enabled" if args.calibrate_threshold else "disabled",
        )
        print("Target recall:", args.target_recall)
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
        pretrained_weights = (
            None if args.pretrained_weights == "none" else args.pretrained_weights
        )

        if args.model == "custom_cnn":
            model = build_custom_cnn(
                input_shape=input_shape,
                learning_rate=learning_rate,
                optimizer_name=args.optimizer,
            )
            base_model = None
        elif args.model == "vgg16":
            model, base_model = build_vgg16_transfer(
                input_shape=input_shape,
                learning_rate=learning_rate,
                optimizer_name=args.optimizer,
                weights=pretrained_weights,
            )
        else:
            model, base_model = build_densenet121_transfer(
                input_shape=input_shape,
                learning_rate=learning_rate,
                optimizer_name=args.optimizer,
                weights=pretrained_weights,
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
        if base_model is not None and args.fine_tune_epochs > 0:
            print(f"Iniciando fine-tuning parcial de {args.model}...")
            unfreeze_last_layers(base_model, n_layers=4)
            model = compile_binary_model(
                model,
                learning_rate=fine_tune_learning_rate,
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

        combined_history_path, fine_tuning_start_epoch, combined_history_rows = (
            write_combined_training_history(
                output_dir=output_dir,
                base_history=history,
                fine_tune_history=fine_tune_history,
                base_learning_rate=learning_rate,
                fine_tune_learning_rate=fine_tune_learning_rate,
            )
        )
        from src.training_plots import plot_combined_training_curves

        plot_paths = plot_combined_training_curves(
            history_csv=str(combined_history_path),
            model_name=args.model,
            output_dir=str(output_dir),
            fine_tuning_start_epoch=fine_tuning_start_epoch,
        )
        execution_parameters.update(
            {
                "total_epochs": args.epochs + args.fine_tune_epochs,
                "completed_epochs": len(combined_history_rows),
                "completed_base_epochs": _history_epoch_count(history),
                "completed_fine_tune_epochs": _history_epoch_count(
                    fine_tune_history
                ),
                "fine_tuning_start_epoch": fine_tuning_start_epoch,
                "phases": (
                    [TRAIN_BASE, FINE_TUNING]
                    if fine_tune_history is not None
                    else [TRAIN_BASE]
                ),
            }
        )
        print(f"Historial combinado guardado en: {combined_history_path}")
        print(f"Curvas combinadas guardadas en: {plot_paths['combined_training_curves']}")

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
        clinical_threshold_metadata = disabled_clinical_threshold_metadata()
        test_threshold = 0.5
        threshold_info = {
            "threshold_requested": 0.5,
            "threshold_mode": "fixed",
            "threshold_used": 0.5,
            "threshold_source": "fixed_cli",
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
                "evaluation_split": "test",
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
            learning_rate=learning_rate,
            extra={
                "execution_type": execution_type,
                "execution_parameters": execution_parameters,
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
                    else fine_tune_learning_rate
                ),
                "fine_tuning_start_epoch": fine_tuning_start_epoch,
                "completed_epochs": len(combined_history_rows),
                "combined_training_history": str(combined_history_path),
                "training_plots": plot_paths,
                "img_size": args.img_size,
                "batch_size": args.batch_size,
                "augment": not args.no_augment,
                **dataset_info,
            },
        )
        metadata_path = write_model_metadata(output_dir, model_metadata)
        policy_summary = checkpoint_selection.get("checkpoint_policy_summary") or {}
        latest_artifacts = [
            str(combined_history_path),
            *plot_paths.values(),
            str(final_model_path),
            str(best_model_path),
            str(output_dir / "checkpoint_selection.json"),
            str(output_dir / "checkpoint_policy_summary.json"),
            str(metadata_path),
            str(output_dir / "test_metrics.json"),
            str(output_dir / "test_predictions.csv"),
            str(output_dir / "test_confusion_matrix.csv"),
            str(output_dir / "training_base_log.csv"),
            str(output_dir / "training_log.csv"),
            str(output_dir / "model_execution_summary.json"),
            str(output_dir / "model_execution_summary.md"),
        ]
        if fine_tune_history is not None:
            latest_artifacts.append(str(output_dir / "fine_tuning_log.csv"))
        if threshold_calibration_path is not None:
            latest_artifacts.append(str(threshold_calibration_path))
        predicted_snapshot_artifacts = [
            str(planned_snapshot_dir / Path(path).name)
            for path in latest_artifacts
        ]
        predicted_snapshot_plots = {
            name: str(planned_snapshot_dir / Path(path).name)
            for name, path in plot_paths.items()
        }
        best_epoch = policy_summary.get("selected_epoch")
        try:
            best_epoch_index = int(best_epoch) - 1 if best_epoch is not None else None
        except (TypeError, ValueError):
            best_epoch_index = None
        db_tracking_active = bool(run_context and run_context.get("run_id"))
        execution_summary = {
            "execution_id": execution_id,
            "model_name": args.model,
            "execution_type": execution_type,
            "parameters": execution_parameters,
            "total_epochs": args.epochs + args.fine_tune_epochs,
            "completed_epochs": len(combined_history_rows),
            "base_epochs": args.epochs,
            "completed_base_epochs": _history_epoch_count(history),
            "fine_tune_epochs": args.fine_tune_epochs,
            "completed_fine_tune_epochs": _history_epoch_count(fine_tune_history),
            "fine_tuning_start_epoch": fine_tuning_start_epoch,
            "best_epoch": best_epoch,
            "best_epoch_index": best_epoch_index,
            "checkpoint_policy": checkpoint_policy_config.policy,
            "checkpoint_metric": checkpoint_monitor,
            "best_validation_metric_name": policy_summary.get(
                "selected_metric"
            ),
            "best_validation_metric": policy_summary.get(
                "selected_metric_value"
            ),
            "threshold": test_threshold,
            "positive_label": args.positive_label,
            "preprocessing": preprocessing_mode,
            "model_internal_preprocessing": execution_parameters.get(
                "model_internal_preprocessing"
            ),
            "output_dir": str(output_dir),
            "artifact_snapshot_dir": str(planned_snapshot_dir),
            "latest_artifacts": latest_artifacts,
            "artifacts": predicted_snapshot_artifacts,
            "plots": predicted_snapshot_plots,
            "test_metrics_path": str(
                planned_snapshot_dir / "test_metrics.json"
            ),
            "db_tracking_requested": bool(args.track_db),
            "db_tracking_enabled": db_tracking_active,
            "db_tracking_active": db_tracking_active,
            "run_id": run_context.get("run_id") if run_context else None,
        }
        summary_paths = write_model_execution_summary(output_dir, execution_summary)
        snapshot_dir, snapshot_artifacts = snapshot_execution_artifacts(
            output_dir,
            execution_id,
            artifact_paths=latest_artifacts,
        )
        snapshot_plot_paths = {
            name: snapshot_artifact_path(snapshot_dir, path)
            for name, path in plot_paths.items()
        }
        execution_parameters.update(
            {
                "artifact_snapshot_dir": str(snapshot_dir),
                "artifact_snapshot_paths": snapshot_artifacts,
                "best_epoch": best_epoch,
                "best_epoch_index": best_epoch_index,
            }
        )
        execution_summary["artifacts"] = snapshot_artifacts
        execution_summary["plots"] = snapshot_plot_paths
        execution_summary["test_metrics_path"] = snapshot_artifact_path(
            snapshot_dir,
            output_dir / "test_metrics.json",
        )
        summary_paths = write_model_execution_summary(output_dir, execution_summary)
        snapshot_summary_paths = {
            name: str(snapshot_dir / Path(path).name)
            for name, path in summary_paths.items()
        }
        for path in summary_paths.values():
            shutil.copy2(path, snapshot_dir / Path(path).name)
        rewrite_snapshot_json_paths(snapshot_dir, output_dir)
        print(f"Snapshot inmutable de la ejecución: {snapshot_dir}")
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
        print(f"Resumen de ejecución JSON: {summary_paths['json']}")
        print(f"Resumen de ejecución Markdown: {summary_paths['markdown']}")

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
                record_checkpoint_policy,
                record_run_dataset_images,
                record_run_io,
                record_threshold_calibration,
                threshold_calibration_for_tracking,
                update_execution_tracking,
            )

            update_execution_tracking(
                run_context,
                execution_type=execution_type,
                execution_parameters=execution_parameters,
                fine_tuning_start_epoch=fine_tuning_start_epoch,
                total_epochs=args.epochs + args.fine_tune_epochs,
                completed_epochs=len(combined_history_rows),
            )
            log_training_history(run_context, history, phase=TRAIN_BASE)
            if fine_tune_history is not None:
                log_training_history(
                    run_context,
                    fine_tune_history,
                    phase=FINE_TUNING,
                    epoch_offset=len(history.epoch),
                )
            log_metrics_and_reports(run_context, metrics, class_names, split_name="test")
            log_output_artifacts(run_context, snapshot_dir)
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
                best_model_path=snapshot_artifact_path(
                    snapshot_dir,
                    best_model_path,
                ),
                final_model_path=snapshot_artifact_path(
                    snapshot_dir,
                    final_model_path,
                ),
                metadata={
                    "source": "src.train",
                    "execution_id": execution_id,
                    "artifact_snapshot_dir": str(snapshot_dir),
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
            checkpoint_policy_payload = {
                **(policy_summary or {}),
                "checkpoint_policy": checkpoint_policy_config.policy,
                "checkpoint_policy_config": checkpoint_policy_config_dict(
                    checkpoint_policy_config
                ),
                "checkpoint_policy_summary_path": str(
                    snapshot_dir / "checkpoint_policy_summary.json"
                ),
                "model_metadata_path": snapshot_artifact_path(
                    snapshot_dir,
                    metadata_path,
                ),
            }
            record_checkpoint_policy(
                run_context,
                checkpoint_policy_payload,
                model_name=run_context.get("model_name"),
            )
            if threshold_calibration:
                record_threshold_calibration(
                    run_context,
                    {
                        **threshold_calibration,
                        "threshold_calibration_path": (
                            None
                            if threshold_calibration_path is None
                            else snapshot_artifact_path(
                                snapshot_dir,
                                threshold_calibration_path,
                            )
                        ),
                        "model_metadata_path": snapshot_artifact_path(
                            snapshot_dir,
                            metadata_path,
                        ),
                    },
                    model_name=run_context.get("model_name"),
                )
            record_run_io(
                run_context,
                script_name="src.train",
                input_parameters=args_to_parameters(
                    args,
                    extra={
                        "execution_type": execution_type,
                        "execution_parameters": execution_parameters,
                        "augment": not args.no_augment,
                        "output_dir": str(output_dir),
                        "artifact_snapshot_dir": str(snapshot_dir),
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
                    "execution_type": execution_type,
                    "total_epochs": args.epochs + args.fine_tune_epochs,
                    "completed_epochs": len(combined_history_rows),
                    "fine_tuning_start_epoch": fine_tuning_start_epoch,
                    "execution_id": execution_id,
                    "artifact_snapshot_dir": str(snapshot_dir),
                    "combined_training_history": snapshot_artifact_path(
                        snapshot_dir,
                        combined_history_path,
                    ),
                    "training_plots": snapshot_plot_paths,
                    "model_execution_summary": snapshot_summary_paths,
                    "best_checkpoint": snapshot_artifact_path(
                        snapshot_dir,
                        best_model_path,
                    ),
                    "final_model": snapshot_artifact_path(
                        snapshot_dir,
                        final_model_path,
                    ),
                    "training_log": snapshot_artifact_path(
                        snapshot_dir,
                        output_dir / "training_log.csv",
                    ),
                    "test_metrics": snapshot_artifact_path(
                        snapshot_dir,
                        output_dir / "test_metrics.json",
                    ),
                    "test_predictions": snapshot_artifact_path(
                        snapshot_dir,
                        output_dir / "test_predictions.csv",
                    ),
                    "test_confusion_matrix": snapshot_artifact_path(
                        snapshot_dir,
                        output_dir / "test_confusion_matrix.csv",
                    ),
                    "threshold_used": test_threshold,
                    "threshold_calibration": threshold_calibration,
                    "clinical_threshold": clinical_threshold_metadata,
                    "threshold_calibration_path": (
                        None
                        if threshold_calibration_path is None
                        else snapshot_artifact_path(
                            snapshot_dir,
                            threshold_calibration_path,
                        )
                    ),
                    **threshold_calibration_for_tracking(threshold_calibration),
                    "checkpoint_policy": checkpoint_policy_config.policy,
                    "checkpoint_policy_config": checkpoint_policy_config_dict(
                        checkpoint_policy_config
                    ),
                    "checkpoint_selection": checkpoint_selection,
                    "checkpoint_policy_summary": policy_summary,
                    "checkpoint_policy_summary_path": str(
                        snapshot_dir / "checkpoint_policy_summary.json"
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
                output_artifacts=output_artifacts_from_directory(snapshot_dir),
                dataset_metadata=dataset_info,
                model_metadata=model_metadata,
                clinical_metadata={
                    "checkpoint_policy": checkpoint_policy_config.policy,
                    "checkpoint_policy_config": checkpoint_policy_config_dict(
                        checkpoint_policy_config
                    ),
                    "checkpoint_selection": checkpoint_selection,
                    "checkpoint_policy_summary": policy_summary,
                    "threshold_calibration": threshold_calibration,
                    "clinical_threshold": clinical_threshold_metadata,
                    **threshold_calibration_for_tracking(threshold_calibration),
                    **threshold_info,
                    **clinical_metrics_for_tracking(metrics),
                },
                metadata={"status_detail": "training completed"},
            )
            finish_tracking_run(
                run_context,
                completed_epochs=len(combined_history_rows),
                metadata={
                    "status_detail": "training completed",
                    "execution_type": execution_type,
                    "execution_parameters": execution_parameters,
                    "fine_tuning_start_epoch": fine_tuning_start_epoch,
                    "total_epochs": args.epochs + args.fine_tune_epochs,
                    "completed_epochs": len(combined_history_rows),
                    "execution_id": execution_id,
                    "artifact_snapshot_dir": str(snapshot_dir),
                    "combined_training_history": snapshot_artifact_path(
                        snapshot_dir,
                        combined_history_path,
                    ),
                    "training_plots": snapshot_plot_paths,
                    "model_execution_summary": snapshot_summary_paths,
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
                        else snapshot_artifact_path(
                            snapshot_dir,
                            threshold_calibration_path,
                        )
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
