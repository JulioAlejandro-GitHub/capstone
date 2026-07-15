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

DEFAULT_MAX_EPOCHS_BY_MODEL = {
    "custom_cnn": 50,
    "vgg16": 30,
    "densenet121": 30,
}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Entrenamiento local para NIH/NLM Malaria Dataset.")
    parser.add_argument(
        "--model",
        choices=["custom_cnn", "vgg16", "densenet121"],
        required=True,
    )
    parser.add_argument(
        "--max-epochs",
        type=int,
        default=None,
        help=(
            "Máximo de épocas de la fase base. Tiene prioridad sobre --epochs. "
            "La cantidad real la determina EarlyStopping usando validation."
        ),
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=None,
        help="Alias legacy de --max-epochs; se mantiene por compatibilidad.",
    )
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
            "Métrica de validation para seleccionar best_model.keras. Si no se "
            "indica, se usa la política clínica de --checkpoint-policy."
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
        "--checkpoint-mode",
        "--monitor-mode",
        dest="checkpoint_mode",
        choices=["auto", "max", "min"],
        default="auto",
        help="Modo de comparación del checkpoint. 'auto' usa min para loss y max para el resto.",
    )
    parser.add_argument(
        "--early-stopping",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Activar EarlyStopping basado exclusivamente en validation.",
    )
    parser.add_argument(
        "--early-stopping-monitor",
        choices=CHECKPOINT_METRIC_CHOICES,
        default=None,
        help=(
            "Override opcional de la métrica de EarlyStopping. Por defecto usa "
            "--checkpoint-monitor o la métrica resuelta por la política clínica."
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
        "--early-stopping-min-delta",
        type=float,
        default=0.0001,
        help="Mejora mínima requerida en validation para reiniciar la paciencia.",
    )
    parser.add_argument(
        "--restore-best-weights",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Restaurar los mejores pesos observados por EarlyStopping.",
    )
    parser.add_argument(
        "--evaluate-best-on-test",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Evaluar una sola vez en test el checkpoint seleccionado en validation.",
    )
    parser.add_argument(
        "--skip-final-test-evaluation",
        action="store_true",
        help="Omitir test final para smoke tests; tiene prioridad sobre la evaluación.",
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
    legacy_epochs = args.epochs
    explicit_max_epochs = args.max_epochs
    if explicit_max_epochs is not None:
        resolved_max_epochs = explicit_max_epochs
        epochs_source = "max_epochs"
    elif legacy_epochs is not None:
        resolved_max_epochs = legacy_epochs
        epochs_source = "epochs_legacy"
    else:
        resolved_max_epochs = DEFAULT_MAX_EPOCHS_BY_MODEL[args.model]
        epochs_source = "model_default"
    args.max_epochs = resolved_max_epochs
    # El resto del pipeline histórico consume args.epochs. Mantener ambos valores
    # resueltos evita bifurcar el flujo y deja explícita la prioridad de max_epochs.
    args.epochs = resolved_max_epochs
    args.epochs_source = epochs_source
    args.epochs_legacy_requested = legacy_epochs
    args.max_epochs_requested = explicit_max_epochs
    # Compatibilidad con consumidores que aún esperan el nombre monitor_mode.
    args.monitor_mode = args.checkpoint_mode
    if args.skip_final_test_evaluation:
        args.evaluate_best_on_test = False
    if args.allow_collapsed_checkpoint:
        args.reject_prediction_collapse = False
    if args.max_epochs <= 0:
        parser.error("--max-epochs/--epochs debe ser mayor que cero.")
    if args.fine_tune_epochs < 0:
        parser.error("--fine-tune-epochs no puede ser negativo.")
    if args.img_size <= 0 or args.batch_size <= 0:
        parser.error("--img-size y --batch-size deben ser mayores que cero.")
    if args.early_stopping_patience < 0:
        parser.error("--early-stopping-patience no puede ser negativo.")
    if args.early_stopping_min_delta < 0:
        parser.error("--early-stopping-min-delta no puede ser negativo.")
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


def uses_explicit_metric_checkpoint(checkpoint_monitor, checkpoint_mode="auto"):
    # Every clinical policy currently maximizes its objective. An explicit
    # `max` therefore remains compatible with the policy; `min` requires the
    # resolved scalar monitor to govern selection directly.
    return checkpoint_monitor is not None or checkpoint_mode == "min"


class ValidationEarlyStopping(tf.keras.callbacks.EarlyStopping):
    """EarlyStopping que conserva también el valor lógico sin normalizar."""

    def __init__(self, *args, value_monitor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.value_monitor = value_monitor or self.monitor
        self.best_validation_value = None

    def on_train_begin(self, logs=None):
        super().on_train_begin(logs)
        self.best_validation_value = None

    def on_epoch_end(self, epoch, logs=None):
        super().on_epoch_end(epoch, logs)
        logs = logs or {}
        if self.best_epoch == epoch and logs.get(self.value_monitor) is not None:
            self.best_validation_value = json_safe_float(
                logs.get(self.value_monitor)
            )


def build_phase_callbacks(
    output_dir,
    checkpoint_callback,
    clinical_validation_callback,
    phase,
    early_stopping_monitor,
    early_stopping_mode,
    early_stopping_patience,
    early_stopping_enabled=True,
    early_stopping_min_delta=0.0001,
    restore_best_weights=True,
    early_stopping_value_monitor=None,
):
    output_dir = Path(output_dir)
    csv_loggers = [tf.keras.callbacks.CSVLogger(str(output_dir / f"{phase}_log.csv"))]
    if phase == "training_base":
        # Alias histórico para compatibilidad con reportes existentes.
        csv_loggers.append(tf.keras.callbacks.CSVLogger(str(output_dir / "training_log.csv")))

    callbacks = [
        clinical_validation_callback,
        checkpoint_callback,
    ]
    if early_stopping_enabled:
        callbacks.append(
            ValidationEarlyStopping(
                monitor=early_stopping_monitor,
                value_monitor=early_stopping_value_monitor,
                patience=early_stopping_patience,
                min_delta=early_stopping_min_delta,
                restore_best_weights=restore_best_weights,
                mode=early_stopping_mode,
                verbose=1,
            )
        )
    callbacks.extend(
        [
            *csv_loggers,
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=4,
            min_lr=1e-6,
            verbose=1,
        ),
        ]
    )
    return callbacks


def find_early_stopping_callback(callbacks):
    return next(
        (
            callback
            for callback in callbacks
            if isinstance(callback, tf.keras.callbacks.EarlyStopping)
        ),
        None,
    )


def early_stopping_phase_summary(
    callback,
    *,
    phase,
    epoch_offset,
    completed_epochs,
):
    if callback is None:
        return {
            "phase": phase,
            "enabled": False,
            "triggered": False,
            "completed_epochs": int(completed_epochs),
            "stopped_epoch": None,
            "best_epoch": None,
            "best_validation_value": None,
        }
    local_stopped_epoch = int(getattr(callback, "stopped_epoch", 0) or 0)
    local_best_epoch = int(getattr(callback, "best_epoch", 0) or 0)
    best_validation_value = getattr(callback, "best_validation_value", None)
    if best_validation_value is None:
        best_validation_value = getattr(callback, "best", None)
    return {
        "phase": phase,
        "enabled": True,
        "triggered": local_stopped_epoch > 0,
        "completed_epochs": int(completed_epochs),
        "stopped_epoch": (
            int(epoch_offset) + local_stopped_epoch + 1
            if local_stopped_epoch > 0
            else int(epoch_offset) + int(completed_epochs)
        ),
        "best_epoch": int(epoch_offset) + local_best_epoch + 1,
        "best_validation_value": json_safe_float(best_validation_value),
    }


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
                    "loss": _history_scalar(history_dict, phase_index, "loss"),
                    "accuracy": _history_scalar(
                        history_dict,
                        phase_index,
                        "accuracy",
                    ),
                    "val_loss": _history_scalar(
                        history_dict,
                        phase_index,
                        "val_loss",
                    ),
                    "val_accuracy": _history_scalar(
                        history_dict,
                        phase_index,
                        "val_accuracy",
                    ),
                    "auc": _history_scalar(history_dict, phase_index, "auc"),
                    "val_auc": _history_scalar(
                        history_dict,
                        phase_index,
                        "val_auc",
                        "val_roc_auc_parasitized",
                    ),
                    "pr_auc": _history_scalar(
                        history_dict,
                        phase_index,
                        "pr_auc",
                    ),
                    "val_pr_auc": _history_scalar(
                        history_dict,
                        phase_index,
                        "val_pr_auc",
                        "val_pr_auc_parasitized",
                    ),
                    "recall_parasitized": _history_scalar(
                        history_dict,
                        phase_index,
                        "recall_parasitized",
                    ),
                    "val_recall_parasitized": _history_scalar(
                        history_dict,
                        phase_index,
                        "val_recall_parasitized",
                        "val_sensitivity_parasitized",
                    ),
                    "f2_parasitized": _history_scalar(
                        history_dict,
                        phase_index,
                        "f2_parasitized",
                    ),
                    "val_f2_parasitized": _history_scalar(
                        history_dict,
                        phase_index,
                        "val_f2_parasitized",
                    ),
                    "val_checkpoint_policy_score": _history_scalar(
                        history_dict,
                        phase_index,
                        "val_checkpoint_policy_score",
                    ),
                    "val_early_stopping_score": _history_scalar(
                        history_dict,
                        phase_index,
                        "val_early_stopping_score",
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

    fieldnames = [
        "epoch",
        "phase",
        "loss",
        "accuracy",
        "val_loss",
        "val_accuracy",
        "auc",
        "val_auc",
        "pr_auc",
        "val_pr_auc",
        "recall_parasitized",
        "val_recall_parasitized",
        "f2_parasitized",
        "val_f2_parasitized",
        "val_checkpoint_policy_score",
        "val_early_stopping_score",
        "learning_rate",
    ]
    history_path = output_dir / "combined_training_history.csv"
    canonical_history_path = output_dir / "training_history.csv"
    for destination in (canonical_history_path, history_path):
        with destination.open("w", encoding="utf-8", newline="") as file_handle:
            writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    base_epochs_completed = _history_epoch_count(base_history)
    fine_tuning_start_epoch = (
        base_epochs_completed
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

    triggered_phases = [
        phase
        for phase in summary.get("early_stopping_phases", [])
        if phase.get("triggered")
    ]
    if triggered_phases:
        phase_details = ", ".join(
            f"{phase.get('phase', 'fase')} (época global {phase.get('stopped_epoch', '-')})"
            for phase in triggered_phases
        )
        stopping_explanation = (
            f"EarlyStopping se activó en {phase_details} porque la métrica de "
            f"validation dejó de mejorar. La ejecución completa finalizó en la "
            f"época {display(summary.get('stopped_epoch'))}."
        )
    else:
        stopping_explanation = (
            f"El entrenamiento finalizó en la época "
            f"{display(summary.get('stopped_epoch'))} sin que EarlyStopping "
            "se activara antes del máximo configurado."
        )

    markdown_lines = [
        f"## Resumen de ejecución — {summary.get('model_name', '-')}",
        "",
        f"- Modelo: {summary.get('model_name', '-')}",
        f"- Tipo de ejecución: {summary.get('execution_type', '-')}",
        f"- Máximo de épocas base: {summary.get('base_max_epochs', summary.get('base_epochs', '-'))}",
        f"- Máximo de épocas fine-tuning: {summary.get('fine_tune_max_epochs', summary.get('fine_tune_epochs', '-'))}",
        f"- Máximo total de épocas: {summary.get('total_max_epochs', summary.get('total_epochs', '-'))}",
        f"- Épocas completadas: {summary.get('completed_epochs', '-')}",
        f"- Época de detención: {display(summary.get('stopped_epoch'))}",
        f"- Inicio de fine-tuning: época {display(summary.get('fine_tuning_start_epoch'))}",
        f"- Mejor época (numeración 1-based): {display(summary.get('best_epoch'))}",
        f"- Índice de mejor época en CSV (0-based): {display(summary.get('best_epoch_index'))}",
        f"- Batch size: {parameters.get('batch_size', '-')}",
        f"- Imagen: {parameters.get('img_size', '-')}x{parameters.get('img_size', '-')}",
        f"- Preprocesamiento: {summary.get('preprocessing', '-')}",
        f"- Preprocesamiento interno: {display(summary.get('model_internal_preprocessing'))}",
        f"- Positive label: {summary.get('positive_label', '-')}",
        f"- Política de checkpoint: {summary.get('checkpoint_policy', '-')}",
        f"- Métrica de checkpoint: {summary.get('checkpoint_monitor', summary.get('checkpoint_metric', '-'))}",
        f"- Modo de checkpoint: {summary.get('checkpoint_mode', '-')}",
        f"- Mejor valor de validation: {display(summary.get('best_validation_value'))}",
        f"- Early stopping activo: {summary.get('early_stopping_enabled', False)}",
        f"- Paciencia: {summary.get('early_stopping_patience', '-')}",
        f"- Min delta: {summary.get('early_stopping_min_delta', '-')}",
        f"- Restore best weights: {summary.get('restore_best_weights', False)}",
        f"- Política de test: {summary.get('test_evaluation_policy', '-')}",
        f"- Test usado para selección: {summary.get('test_used_for_selection', False)}",
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
    if summary.get("final_test_metrics"):
        markdown_lines.extend(["", "## Métricas finales de test", ""])
        for name, value in summary["final_test_metrics"].items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                markdown_lines.append(f"- {name}: {display(value)}")
    markdown_lines.extend(
        [
            "",
            "## Política metodológica",
            "",
            (
                f"El modelo fue entrenado con un máximo de "
                f"{summary.get('total_max_epochs', summary.get('total_epochs', '-'))} "
                f"épocas. {stopping_explanation} El mejor checkpoint "
                f"corresponde a la época {display(summary.get('best_epoch'))} según "
                f"{summary.get('checkpoint_monitor', summary.get('checkpoint_metric', '-'))}. "
                + (
                    "El conjunto test se evaluó una sola vez usando ese checkpoint."
                    if summary.get("test_evaluation_policy") == "single_final_evaluation"
                    else "La evaluación final en test fue omitida por configuración."
                )
            ),
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
    seen_names = {}
    for source in sources:
        resolved_source = source.resolve()
        previous_source = seen_names.get(source.name)
        if previous_source is not None:
            if previous_source == resolved_source:
                continue
            raise ValueError(
                "No se puede crear un snapshot inequívoco: dos artefactos "
                f"distintos usan el nombre {source.name!r}: "
                f"{previous_source} y {resolved_source}."
            )
        seen_names[source.name] = resolved_source
        destination = snapshot_dir / source.name
        shutil.copy2(source, destination)
        copied_paths.append(str(destination))
    return snapshot_dir, copied_paths


RESERVED_ARTIFACT_BASENAMES = {
    "best_model.keras",
    "final_model.keras",
    "training_history.csv",
    "combined_training_history.csv",
    "training_base_log.csv",
    "training_log.csv",
    "fine_tuning_log.csv",
    "combined_accuracy.png",
    "combined_loss.png",
    "combined_training_curves.png",
    "checkpoint_selection.json",
    "checkpoint_policy_summary.json",
    "model_metadata.json",
    "model_execution_summary.json",
    "model_execution_summary.md",
    "test_metrics.json",
    "test_predictions.csv",
    "test_confusion_matrix.csv",
    "classification_report.json",
}


def resolve_threshold_calibration_output_path(output_dir, requested_path=None):
    output_dir = Path(output_dir)
    candidate = (
        Path(requested_path).expanduser()
        if requested_path
        else default_threshold_calibration_path(output_dir)
    )
    snapshot_root = (output_dir / "runs").resolve()
    if candidate.resolve().is_relative_to(snapshot_root):
        raise ValueError(
            "--threshold-output-json no puede escribir dentro de output_dir/runs; "
            "esa carpeta contiene snapshots inmutables de ejecuciones anteriores."
        )
    if candidate.name in RESERVED_ARTIFACT_BASENAMES:
        raise ValueError(
            "--threshold-output-json colisiona con un artefacto reservado: "
            f"{candidate.name}. Usa un nombre JSON exclusivo para la calibración."
        )
    if candidate.suffix.lower() != ".json":
        raise ValueError("--threshold-output-json debe terminar en .json.")
    return candidate


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
    base_max_epochs,
    fine_tune_max_epochs,
    completed_epochs,
    stopped_epoch,
    early_stopping_enabled,
    early_stopping_patience,
    early_stopping_min_delta,
    restore_best_weights,
    evaluate_best_on_test,
    early_stopping_phases=None,
):
    output_dir = Path(output_dir)
    policy_selection = checkpoint_callback.best_selection or {}
    policy_summary = checkpoint_callback.selection_summary() or {}
    write_checkpoint_policy_summary(output_dir, policy_summary)
    total_max_epochs = int(base_max_epochs) + int(fine_tune_max_epochs)
    if int(completed_epochs) > total_max_epochs:
        raise ValueError(
            "completed_epochs no puede superar base_max_epochs + fine_tune_max_epochs."
        )
    best_epoch = policy_summary.get("selected_epoch")
    selected_validation_metric = (
        policy_summary.get("selected_metric") or checkpoint_monitor
    )
    best_validation_value = json_safe_float(
        policy_summary.get("selected_metric_value")
    )
    report = {
        "selection_policy": "validation_best_checkpoint",
        "test_used_for_selection": False,
        "test_used_for_checkpoint_selection": False,
        "test_used_for_early_stopping": False,
        "test_evaluation_requested": bool(evaluate_best_on_test),
        "test_evaluation_after_selection": False,
        "test_evaluation_completed": False,
        "test_evaluation_policy": (
            "pending"
            if evaluate_best_on_test
            else "skipped_by_configuration"
        ),
        "max_epochs": int(base_max_epochs),
        "base_max_epochs": int(base_max_epochs),
        "fine_tune_max_epochs": int(fine_tune_max_epochs),
        "total_max_epochs": total_max_epochs,
        "completed_epochs": int(completed_epochs),
        "stopped_epoch": stopped_epoch,
        "best_epoch": best_epoch,
        "best_validation_value": best_validation_value,
        "early_stopping_enabled": bool(early_stopping_enabled),
        "early_stopping_patience": int(early_stopping_patience),
        "early_stopping_min_delta": float(early_stopping_min_delta),
        "restore_best_weights": bool(restore_best_weights),
        "early_stopping_phases": list(early_stopping_phases or []),
        "best_checkpoint_path": str(output_dir / "best_model.keras"),
        "best_model_path": str(output_dir / "best_model.keras"),
        "checkpoint_policy": checkpoint_policy_config.policy,
        "checkpoint_policy_config": checkpoint_policy_config_dict(checkpoint_policy_config),
        "checkpoint_selection": policy_selection,
        "checkpoint_policy_summary": policy_summary,
        "checkpoint_metric": selected_validation_metric,
        "checkpoint_monitor": selected_validation_metric,
        "checkpoint_monitor_configured": checkpoint_monitor,
        "selected_validation_metric": selected_validation_metric,
        "checkpoint_mode": checkpoint_mode,
        "best_checkpoint_value": best_validation_value,
        "early_stopping_monitor": early_stopping_monitor,
        "early_stopping_internal_monitor": "val_early_stopping_score",
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


def finalize_checkpoint_test_evaluation(output_dir, report, evaluated):
    finalized = dict(report)
    finalized["test_evaluation_after_selection"] = bool(evaluated)
    finalized["test_evaluation_completed"] = bool(evaluated)
    finalized["test_evaluation_policy"] = (
        "single_final_evaluation"
        if evaluated
        else "skipped_by_configuration"
    )
    report_path = Path(output_dir) / "checkpoint_selection.json"
    report_path.write_text(
        json.dumps(_json_safe_value(finalized), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return finalized


FINAL_TEST_ARTIFACT_NAMES = (
    "test_metrics.json",
    "test_predictions.csv",
    "test_confusion_matrix.csv",
    "classification_report.json",
)


def clear_final_test_artifacts(output_dir):
    """Prevent files from an older run from masquerading as current test output."""
    output_dir = Path(output_dir)
    for filename in FINAL_TEST_ARTIFACT_NAMES:
        candidate = output_dir / filename
        if candidate.is_file():
            candidate.unlink()


def clear_latest_run_artifacts(output_dir):
    """Clear mutable latest outputs while preserving immutable run snapshots."""
    output_dir = Path(output_dir)
    for filename in RESERVED_ARTIFACT_BASENAMES | {"threshold_calibration.json"}:
        candidate = output_dir / filename
        if candidate.is_file():
            candidate.unlink()


def stage_latest_run_artifacts(output_dir, execution_id):
    """Temporarily preserve the previous latest aliases until this run succeeds."""
    output_dir = Path(output_dir)
    backup_dir = output_dir / ".latest_backups" / str(execution_id)
    if backup_dir.exists():
        raise FileExistsError(
            f"Ya existe un respaldo transaccional para la ejecución: {backup_dir}"
        )
    staged = False
    moved_names = []
    try:
        for filename in RESERVED_ARTIFACT_BASENAMES | {"threshold_calibration.json"}:
            source = output_dir / filename
            if not source.is_file():
                continue
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(backup_dir / filename))
            moved_names.append(filename)
            staged = True
    except BaseException:
        for filename in reversed(moved_names):
            backup = backup_dir / filename
            if backup.is_file():
                shutil.move(str(backup), str(output_dir / filename))
        discard_latest_artifact_backup(backup_dir)
        raise
    return backup_dir if staged else None


def discard_latest_artifact_backup(backup_dir):
    if backup_dir is None:
        return
    backup_dir = Path(backup_dir)
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    parent = backup_dir.parent
    if parent.is_dir() and not any(parent.iterdir()):
        parent.rmdir()


def restore_latest_artifact_backup(output_dir, backup_dir):
    """Remove partial latest outputs and restore the last successful aliases."""
    output_dir = Path(output_dir)
    clear_latest_run_artifacts(output_dir)
    if backup_dir is None:
        return
    backup_dir = Path(backup_dir)
    if backup_dir.is_dir():
        for source in backup_dir.iterdir():
            if source.is_file():
                shutil.move(str(source), str(output_dir / source.name))
    discard_latest_artifact_backup(backup_dir)


def evaluate_selected_checkpoint_once(
    *,
    model,
    dataset,
    class_names,
    output_dir,
    checkpoint_path,
    threshold,
    metadata,
):
    """Run the single final test pass after validation-based model selection."""
    methodology = {
        "evaluated_checkpoint": str(checkpoint_path),
        "test_evaluation_policy": "single_final_evaluation",
        "test_used_for_selection": False,
        "test_used_for_checkpoint_selection": False,
        "test_used_for_early_stopping": False,
        "test_used_for_threshold_selection": False,
    }
    metrics = evaluate_keras_model(
        model=model,
        dataset=dataset,
        class_names=class_names,
        output_dir=output_dir,
        prefix="test",
        threshold=threshold,
        metadata={**metadata, **methodology},
    )
    metrics.update(methodology)
    metrics_path = Path(output_dir) / "test_metrics.json"
    metrics_path.write_text(
        json.dumps(_json_safe_value(metrics), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    classification_report_path = Path(output_dir) / "classification_report.json"
    classification_report_path.write_text(
        json.dumps(
            _json_safe_value(metrics.get("classification_report_dict") or {}),
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return metrics


def evaluate_selected_checkpoint_if_enabled(enabled, **evaluation_kwargs):
    if not enabled:
        return None
    return evaluate_selected_checkpoint_once(**evaluation_kwargs)


def main():
    args = parse_args()
    run_context = None
    latest_backup_dir = None
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
    explicit_checkpoint_monitor = args.checkpoint_monitor is not None
    explicit_checkpoint_selection = uses_explicit_metric_checkpoint(
        args.checkpoint_monitor,
        args.checkpoint_mode,
    )
    checkpoint_monitor = args.checkpoint_monitor or policy_monitor
    checkpoint_mode = resolve_monitor_mode(
        checkpoint_monitor,
        args.checkpoint_mode if explicit_checkpoint_monitor else (
            policy_mode if args.checkpoint_mode == "auto" else args.checkpoint_mode
        ),
    )
    if args.early_stopping_monitor is not None:
        early_stopping_monitor = args.early_stopping_monitor
    elif explicit_checkpoint_selection:
        early_stopping_monitor = checkpoint_monitor
    else:
        early_stopping_monitor = "val_checkpoint_policy_score"
    early_stopping_mode = (
        checkpoint_mode
        if args.early_stopping_monitor is None and explicit_checkpoint_selection
        and args.early_stopping_mode == "auto"
        else resolve_monitor_mode(
            early_stopping_monitor,
            args.early_stopping_mode,
        )
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
        "max_epochs": args.max_epochs,
        "base_max_epochs": args.max_epochs,
        "fine_tune_max_epochs": args.fine_tune_epochs,
        "total_max_epochs": args.max_epochs + args.fine_tune_epochs,
        "epochs_source": args.epochs_source,
        "epochs_legacy_requested": args.epochs_legacy_requested,
        "max_epochs_requested": args.max_epochs_requested,
        "checkpoint_mode": checkpoint_mode,
        "checkpoint_selection_source": (
            "explicit_validation_metric"
            if explicit_checkpoint_selection
            else "clinical_policy"
        ),
        "early_stopping": bool(args.early_stopping),
        "early_stopping_monitor": early_stopping_monitor,
        "early_stopping_internal_monitor": "val_early_stopping_score",
        "early_stopping_mode": early_stopping_mode,
        "early_stopping_patience": args.early_stopping_patience,
        "early_stopping_min_delta": args.early_stopping_min_delta,
        "restore_best_weights": bool(args.restore_best_weights),
        "evaluate_best_on_test": bool(args.evaluate_best_on_test),
        "skip_final_test_evaluation": bool(args.skip_final_test_evaluation),
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
                    "max_epochs": args.max_epochs,
                    "base_max_epochs": args.max_epochs,
                    "fine_tune_max_epochs": args.fine_tune_epochs,
                    "total_max_epochs": args.max_epochs + args.fine_tune_epochs,
                    "early_stopping": bool(args.early_stopping),
                    "early_stopping_monitor": early_stopping_monitor,
                    "early_stopping_internal_monitor": (
                        "val_early_stopping_score"
                    ),
                    "early_stopping_mode": early_stopping_mode,
                    "early_stopping_patience": args.early_stopping_patience,
                    "early_stopping_min_delta": args.early_stopping_min_delta,
                    "restore_best_weights": bool(args.restore_best_weights),
                    "evaluate_best_on_test": bool(args.evaluate_best_on_test),
                    "skip_final_test_evaluation": bool(
                        args.skip_final_test_evaluation
                    ),
                    "optimizer": args.optimizer,
                    **dataset_info,
                },
            ),
            execution_type=execution_type,
            execution_parameters=execution_parameters,
            total_epochs=args.max_epochs + args.fine_tune_epochs,
            completed_epochs=0,
            max_epochs=args.max_epochs,
            checkpoint_monitor=checkpoint_monitor,
            checkpoint_mode=checkpoint_mode,
            early_stopping_enabled=args.early_stopping,
            early_stopping_patience=args.early_stopping_patience,
            early_stopping_min_delta=args.early_stopping_min_delta,
            restore_best_weights=args.restore_best_weights,
            random_seed=args.seed,
        )
    # if args.model == "vgg16"
    # if args.model == "custom_cnn":
    # validar datos de ejecucion antes de comenzar... en este caaso el nombre del modelo

    try:
        tf.keras.utils.set_random_seed(args.seed)

        output_dir.mkdir(parents=True, exist_ok=True)
        latest_backup_dir = stage_latest_run_artifacts(output_dir, execution_id)

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
        print(
            "Máximo de épocas:",
            f"base={args.max_epochs}",
            f"fine_tuning={args.fine_tune_epochs}",
            f"total={args.max_epochs + args.fine_tune_epochs}",
        )
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
            (
                f"(enabled={args.early_stopping}, mode={early_stopping_mode}, "
                f"patience={args.early_stopping_patience}, "
                f"min_delta={args.early_stopping_min_delta}, "
                f"restore_best_weights={args.restore_best_weights})"
            ),
        )
        print(
            "Evaluación final única en test:",
            "enabled" if args.evaluate_best_on_test else "skipped",
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
            checkpoint_policy_config=checkpoint_policy_config,
            early_stopping_monitor=early_stopping_monitor,
            early_stopping_mode=early_stopping_mode,
            verbose=0,
        )
        checkpoint_callback = ClinicalCheckpointCallback(
            output_dir=output_dir,
            config=checkpoint_policy_config,
            monitor=checkpoint_monitor if explicit_checkpoint_selection else None,
            mode=checkpoint_mode,
            verbose=1,
        )

        checkpoint_callback.set_phase("training_base", epoch_offset=0)
        base_callbacks = build_phase_callbacks(
            output_dir=output_dir,
            checkpoint_callback=checkpoint_callback,
            clinical_validation_callback=clinical_validation_callback,
            phase="training_base",
            early_stopping_monitor="val_early_stopping_score",
            early_stopping_mode="max",
            early_stopping_patience=args.early_stopping_patience,
            early_stopping_enabled=args.early_stopping,
            early_stopping_min_delta=args.early_stopping_min_delta,
            restore_best_weights=args.restore_best_weights,
            early_stopping_value_monitor=early_stopping_monitor,
        )
        history = model.fit(
            ds_train,
            validation_data=ds_val,
            epochs=args.max_epochs,
            callbacks=base_callbacks,
        )

        fine_tune_history = None
        fine_tune_callbacks = []
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
            fine_tune_callbacks = build_phase_callbacks(
                output_dir=output_dir,
                checkpoint_callback=checkpoint_callback,
                clinical_validation_callback=clinical_validation_callback,
                phase="fine_tuning",
                early_stopping_monitor="val_early_stopping_score",
                early_stopping_mode="max",
                early_stopping_patience=args.early_stopping_patience,
                early_stopping_enabled=args.early_stopping,
                early_stopping_min_delta=args.early_stopping_min_delta,
                restore_best_weights=args.restore_best_weights,
                early_stopping_value_monitor=early_stopping_monitor,
            )
            fine_tune_history = model.fit(
                ds_train,
                validation_data=ds_val,
                epochs=args.fine_tune_epochs,
                callbacks=fine_tune_callbacks,
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
        base_completed_epochs = _history_epoch_count(history)
        fine_tune_completed_epochs = _history_epoch_count(fine_tune_history)
        early_stopping_phases = [
            early_stopping_phase_summary(
                find_early_stopping_callback(base_callbacks),
                phase="base",
                epoch_offset=0,
                completed_epochs=base_completed_epochs,
            )
        ]
        if fine_tune_history is not None:
            early_stopping_phases.append(
                early_stopping_phase_summary(
                    find_early_stopping_callback(fine_tune_callbacks),
                    phase="fine_tuning",
                    epoch_offset=base_completed_epochs,
                    completed_epochs=fine_tune_completed_epochs,
                )
            )
        early_stopping_triggered = any(
            phase.get("triggered") for phase in early_stopping_phases
        )
        stopped_epoch = (
            len(combined_history_rows) if args.early_stopping else None
        )
        execution_parameters.update(
            {
                "max_epochs": args.max_epochs,
                "base_max_epochs": args.max_epochs,
                "fine_tune_max_epochs": args.fine_tune_epochs,
                "total_max_epochs": args.max_epochs + args.fine_tune_epochs,
                "total_epochs": args.max_epochs + args.fine_tune_epochs,
                "completed_epochs": len(combined_history_rows),
                "completed_base_epochs": base_completed_epochs,
                "completed_fine_tune_epochs": fine_tune_completed_epochs,
                "stopped_epoch": stopped_epoch,
                "early_stopping_triggered": early_stopping_triggered,
                "early_stopping_phases": early_stopping_phases,
                "fine_tuning_start_epoch": fine_tuning_start_epoch,
                "training_history": str(output_dir / "training_history.csv"),
                "phases": (
                    [TRAIN_BASE, FINE_TUNING]
                    if fine_tune_history is not None
                    else [TRAIN_BASE]
                ),
            }
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
            base_max_epochs=args.max_epochs,
            fine_tune_max_epochs=args.fine_tune_epochs,
            completed_epochs=len(combined_history_rows),
            stopped_epoch=stopped_epoch,
            early_stopping_enabled=args.early_stopping,
            early_stopping_patience=args.early_stopping_patience,
            early_stopping_min_delta=args.early_stopping_min_delta,
            restore_best_weights=args.restore_best_weights,
            evaluate_best_on_test=args.evaluate_best_on_test,
            early_stopping_phases=early_stopping_phases,
        )
        selected_checkpoint_monitor = checkpoint_selection["checkpoint_monitor"]
        execution_parameters.update(
            {
                "best_epoch": checkpoint_selection.get("best_epoch"),
                "best_validation_value": checkpoint_selection.get(
                    "best_validation_value"
                ),
                "checkpoint_monitor": selected_checkpoint_monitor,
                "checkpoint_monitor_configured": checkpoint_monitor,
                "checkpoint_mode": checkpoint_mode,
                "test_evaluation_policy": "pending"
                if args.evaluate_best_on_test
                else "skipped_by_configuration",
                "test_used_for_selection": False,
            }
        )
        if args.track_db and run_context:
            from src.tracking_integration import (
                log_training_history,
                update_execution_tracking,
            )

            update_execution_tracking(
                run_context,
                execution_type=execution_type,
                execution_parameters=execution_parameters,
                fine_tuning_start_epoch=fine_tuning_start_epoch,
                total_epochs=args.max_epochs + args.fine_tune_epochs,
                completed_epochs=len(combined_history_rows),
                max_epochs=args.max_epochs,
                stopped_epoch=stopped_epoch,
                best_epoch=checkpoint_selection.get("best_epoch"),
                checkpoint_monitor=selected_checkpoint_monitor,
                checkpoint_mode=checkpoint_mode,
                best_validation_value=checkpoint_selection.get(
                    "best_validation_value"
                ),
                early_stopping_enabled=args.early_stopping,
                early_stopping_patience=args.early_stopping_patience,
                early_stopping_min_delta=args.early_stopping_min_delta,
                restore_best_weights=args.restore_best_weights,
            )
            log_training_history(run_context, history, phase=TRAIN_BASE)
            if fine_tune_history is not None:
                log_training_history(
                    run_context,
                    fine_tune_history,
                    phase=FINE_TUNING,
                    epoch_offset=len(history.epoch),
                )

        from src.training_plots import plot_combined_training_curves

        plot_paths = plot_combined_training_curves(
            history_csv=str(combined_history_path),
            model_name=args.model,
            output_dir=str(output_dir),
            fine_tuning_start_epoch=fine_tuning_start_epoch,
        )
        print(f"Historial combinado guardado en: {combined_history_path}")
        print(f"Curvas combinadas guardadas en: {plot_paths['combined_training_curves']}")

        final_model_path = output_dir / "final_model.keras"
        best_model_path = output_dir / "best_model.keras"
        model.save(final_model_path)
        if not best_model_path.is_file():
            raise RuntimeError(
                "No se generó best_model.keras desde validation; se rechaza usar "
                "el modelo final como fallback porque rompería la política de selección."
            )
        print(f"Cargando mejor checkpoint seleccionado en validation: {best_model_path}")
        evaluation_model = tf.keras.models.load_model(best_model_path)

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
            threshold_calibration_path = resolve_threshold_calibration_output_path(
                output_dir,
                args.threshold_output_json,
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

        clear_final_test_artifacts(output_dir)
        metrics = None
        if args.evaluate_best_on_test:
            print("Evaluación final única en test con el mejor checkpoint:")
            metrics = evaluate_selected_checkpoint_once(
                model=evaluation_model,
                dataset=ds_test,
                class_names=class_names,
                output_dir=output_dir,
                checkpoint_path=best_model_path,
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
        else:
            print(
                "Evaluación final en test omitida por configuración; validation "
                "sigue siendo la única fuente de selección."
            )
        checkpoint_selection = finalize_checkpoint_test_evaluation(
            output_dir,
            checkpoint_selection,
            evaluated=metrics is not None,
        )
        execution_parameters["test_evaluation_policy"] = checkpoint_selection[
            "test_evaluation_policy"
        ]
        execution_parameters["test_evaluation_completed"] = bool(
            metrics is not None
        )
        if args.track_db and run_context:
            from src.tracking_integration import update_execution_tracking

            update_execution_tracking(
                run_context,
                execution_type=execution_type,
                execution_parameters=execution_parameters,
                fine_tuning_start_epoch=fine_tuning_start_epoch,
                total_epochs=args.max_epochs + args.fine_tune_epochs,
                completed_epochs=len(combined_history_rows),
                max_epochs=args.max_epochs,
                stopped_epoch=stopped_epoch,
                best_epoch=checkpoint_selection.get("best_epoch"),
                checkpoint_monitor=selected_checkpoint_monitor,
                checkpoint_mode=checkpoint_mode,
                best_validation_value=checkpoint_selection.get(
                    "best_validation_value"
                ),
                early_stopping_enabled=args.early_stopping,
                early_stopping_patience=args.early_stopping_patience,
                early_stopping_min_delta=args.early_stopping_min_delta,
                restore_best_weights=args.restore_best_weights,
            )
        model_metadata = build_model_metadata(
            model_name=args.model,
            threshold_default=0.5,
            preprocessing=preprocessing_mode,
            checkpoint_monitor=selected_checkpoint_monitor,
            early_stopping_monitor=early_stopping_monitor,
            optimizer=args.optimizer,
            learning_rate=learning_rate,
            extra={
                "execution_type": execution_type,
                "execution_parameters": execution_parameters,
                "checkpoint_mode": checkpoint_mode,
                "checkpoint_monitor_configured": checkpoint_monitor,
                "selected_validation_metric": selected_checkpoint_monitor,
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
                "early_stopping_enabled": bool(args.early_stopping),
                "early_stopping_patience": args.early_stopping_patience,
                "early_stopping_min_delta": args.early_stopping_min_delta,
                "restore_best_weights": bool(args.restore_best_weights),
                "early_stopping_triggered": early_stopping_triggered,
                "early_stopping_phases": early_stopping_phases,
                "max_epochs": args.max_epochs,
                "base_max_epochs": args.max_epochs,
                "fine_tune_max_epochs": args.fine_tune_epochs,
                "total_max_epochs": args.max_epochs + args.fine_tune_epochs,
                "stopped_epoch": stopped_epoch,
                "best_epoch": checkpoint_selection.get("best_epoch"),
                "best_validation_value": checkpoint_selection.get(
                    "best_validation_value"
                ),
                "evaluate_best_on_test": bool(args.evaluate_best_on_test),
                "test_evaluation_policy": checkpoint_selection.get(
                    "test_evaluation_policy"
                ),
                "test_used_for_selection": False,
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
                "training_history": str(output_dir / "training_history.csv"),
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
            str(output_dir / "training_history.csv"),
            str(combined_history_path),
            *plot_paths.values(),
            str(final_model_path),
            str(best_model_path),
            str(output_dir / "checkpoint_selection.json"),
            str(output_dir / "checkpoint_policy_summary.json"),
            str(metadata_path),
            str(output_dir / "training_base_log.csv"),
            str(output_dir / "training_log.csv"),
            str(output_dir / "model_execution_summary.json"),
            str(output_dir / "model_execution_summary.md"),
        ]
        if metrics is not None:
            latest_artifacts.extend(
                [
                    str(output_dir / "test_metrics.json"),
                    str(output_dir / "test_predictions.csv"),
                    str(output_dir / "test_confusion_matrix.csv"),
                    str(output_dir / "classification_report.json"),
                ]
            )
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
            "max_epochs": args.max_epochs,
            "base_max_epochs": args.max_epochs,
            "fine_tune_max_epochs": args.fine_tune_epochs,
            "total_max_epochs": args.max_epochs + args.fine_tune_epochs,
            "total_epochs": args.max_epochs + args.fine_tune_epochs,
            "completed_epochs": len(combined_history_rows),
            "stopped_epoch": stopped_epoch,
            "base_epochs": args.max_epochs,
            "completed_base_epochs": base_completed_epochs,
            "fine_tune_epochs": args.fine_tune_epochs,
            "completed_fine_tune_epochs": fine_tune_completed_epochs,
            "fine_tuning_start_epoch": fine_tuning_start_epoch,
            "best_epoch": best_epoch,
            "best_epoch_index": best_epoch_index,
            "checkpoint_policy": checkpoint_policy_config.policy,
            "checkpoint_metric": selected_checkpoint_monitor,
            "checkpoint_monitor": selected_checkpoint_monitor,
            "checkpoint_monitor_configured": checkpoint_monitor,
            "checkpoint_mode": checkpoint_mode,
            "best_validation_value": checkpoint_selection.get(
                "best_validation_value"
            ),
            "early_stopping_enabled": bool(args.early_stopping),
            "early_stopping_triggered": early_stopping_triggered,
            "early_stopping_patience": args.early_stopping_patience,
            "early_stopping_min_delta": args.early_stopping_min_delta,
            "restore_best_weights": bool(args.restore_best_weights),
            "early_stopping_phases": early_stopping_phases,
            "best_checkpoint_path": str(best_model_path),
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
            "final_test_metrics": (
                None if metrics is None else metrics.get("metrics", metrics)
            ),
            "test_evaluation_policy": checkpoint_selection.get(
                "test_evaluation_policy"
            ),
            "test_used_for_selection": False,
            "test_used_for_checkpoint_selection": False,
            "test_used_for_early_stopping": False,
            "test_metrics_path": (
                str(planned_snapshot_dir / "test_metrics.json")
                if metrics is not None
                else None
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
                "best_validation_value": checkpoint_selection.get(
                    "best_validation_value"
                ),
                "checkpoint_monitor": selected_checkpoint_monitor,
                "checkpoint_monitor_configured": checkpoint_monitor,
                "checkpoint_mode": checkpoint_mode,
                "test_evaluation_policy": checkpoint_selection.get(
                    "test_evaluation_policy"
                ),
                "test_used_for_selection": False,
            }
        )
        execution_summary["artifacts"] = snapshot_artifacts
        execution_summary["plots"] = snapshot_plot_paths
        execution_summary["test_metrics_path"] = (
            snapshot_artifact_path(
                snapshot_dir,
                output_dir / "test_metrics.json",
            )
            if metrics is not None
            else None
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
                output_artifacts_from_directory,
                record_checkpoint_policy,
                record_run_dataset_images,
                record_run_io,
                record_threshold_calibration,
                threshold_calibration_for_tracking,
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
            if metrics is not None:
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
                        "checkpoint_monitor": selected_checkpoint_monitor,
                        "checkpoint_monitor_configured": checkpoint_monitor,
                        "checkpoint_mode": checkpoint_mode,
                        "max_epochs": args.max_epochs,
                        "base_max_epochs": args.max_epochs,
                        "fine_tune_max_epochs": args.fine_tune_epochs,
                        "total_max_epochs": args.max_epochs + args.fine_tune_epochs,
                        "early_stopping": bool(args.early_stopping),
                        "early_stopping_monitor": early_stopping_monitor,
                        "early_stopping_mode": early_stopping_mode,
                        "early_stopping_patience": args.early_stopping_patience,
                        "early_stopping_min_delta": args.early_stopping_min_delta,
                        "restore_best_weights": bool(args.restore_best_weights),
                        "evaluate_best_on_test": bool(args.evaluate_best_on_test),
                        "test_used_for_selection": False,
                        "optimizer": args.optimizer,
                        **dataset_info,
                    },
                ),
                output_results={
                    "final_epoch": len(history.epoch)
                    + (0 if fine_tune_history is None else len(fine_tune_history.epoch)),
                    "execution_type": execution_type,
                    "max_epochs": args.max_epochs,
                    "base_max_epochs": args.max_epochs,
                    "fine_tune_max_epochs": args.fine_tune_epochs,
                    "total_max_epochs": args.max_epochs + args.fine_tune_epochs,
                    "total_epochs": args.max_epochs + args.fine_tune_epochs,
                    "completed_epochs": len(combined_history_rows),
                    "stopped_epoch": stopped_epoch,
                    "early_stopping_triggered": early_stopping_triggered,
                    "fine_tuning_start_epoch": fine_tuning_start_epoch,
                    "execution_id": execution_id,
                    "artifact_snapshot_dir": str(snapshot_dir),
                    "combined_training_history": snapshot_artifact_path(
                        snapshot_dir,
                        combined_history_path,
                    ),
                    "training_history": snapshot_artifact_path(
                        snapshot_dir,
                        output_dir / "training_history.csv",
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
                    "test_metrics": (
                        snapshot_artifact_path(
                            snapshot_dir,
                            output_dir / "test_metrics.json",
                        )
                        if metrics is not None
                        else None
                    ),
                    "test_predictions": (
                        snapshot_artifact_path(
                            snapshot_dir,
                            output_dir / "test_predictions.csv",
                        )
                        if metrics is not None
                        else None
                    ),
                    "test_confusion_matrix": (
                        snapshot_artifact_path(
                            snapshot_dir,
                            output_dir / "test_confusion_matrix.csv",
                        )
                        if metrics is not None
                        else None
                    ),
                    "classification_report": (
                        snapshot_artifact_path(
                            snapshot_dir,
                            output_dir / "classification_report.json",
                        )
                        if metrics is not None
                        else None
                    ),
                    "test_evaluation_policy": checkpoint_selection.get(
                        "test_evaluation_policy"
                    ),
                    "test_used_for_selection": False,
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
                max_epochs=args.max_epochs,
                stopped_epoch=stopped_epoch,
                best_epoch=best_epoch,
                checkpoint_monitor=selected_checkpoint_monitor,
                checkpoint_mode=checkpoint_mode,
                best_validation_value=checkpoint_selection.get(
                    "best_validation_value"
                ),
                early_stopping_enabled=args.early_stopping,
                early_stopping_patience=args.early_stopping_patience,
                early_stopping_min_delta=args.early_stopping_min_delta,
                restore_best_weights=args.restore_best_weights,
                metadata={
                    "status_detail": "training completed",
                    "execution_type": execution_type,
                    "execution_parameters": execution_parameters,
                    "fine_tuning_start_epoch": fine_tuning_start_epoch,
                    "max_epochs": args.max_epochs,
                    "base_max_epochs": args.max_epochs,
                    "fine_tune_max_epochs": args.fine_tune_epochs,
                    "total_max_epochs": args.max_epochs + args.fine_tune_epochs,
                    "total_epochs": args.max_epochs + args.fine_tune_epochs,
                    "completed_epochs": len(combined_history_rows),
                    "stopped_epoch": stopped_epoch,
                    "early_stopping_enabled": bool(args.early_stopping),
                    "early_stopping_triggered": early_stopping_triggered,
                    "early_stopping_patience": args.early_stopping_patience,
                    "early_stopping_min_delta": args.early_stopping_min_delta,
                    "restore_best_weights": bool(args.restore_best_weights),
                    "test_evaluation_policy": checkpoint_selection.get(
                        "test_evaluation_policy"
                    ),
                    "test_used_for_selection": False,
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
        try:
            discard_latest_artifact_backup(latest_backup_dir)
            latest_backup_dir = None
        except OSError as cleanup_error:
            print(
                "WARNING: no se pudo eliminar el respaldo transaccional de "
                f"artefactos latest: {cleanup_error}"
            )
    except BaseException as exc:
        try:
            restore_latest_artifact_backup(output_dir, latest_backup_dir)
        except Exception as restore_error:
            print(
                "WARNING: no se pudieron restaurar por completo los artefactos "
                f"latest anteriores: {restore_error}"
            )
        if args.track_db and run_context:
            from src.tracking_integration import fail_tracking_run

            fail_tracking_run(run_context, exc, script_name="src.train")
        raise


if __name__ == "__main__":
    main()
