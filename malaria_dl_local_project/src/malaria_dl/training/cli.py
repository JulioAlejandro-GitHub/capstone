"""TRAIN argument validation without importing TensorFlow or constructing a model."""

import argparse
import sys
import json
from .cli_constants import CHECKPOINT_METRIC_CHOICES
from ..models.registry import model_arg, resolve_descriptor, enabled_models
from pathlib import Path
from ..models.optimizers import OPTIMIZER_DEFAULTS
from ..models.configuration import resolve_config, load_selected, config_digest
from ..data.governed_dataset import dataset_uuid_arg
from ..data.cli import add_data_source_args

CHECKPOINT_POLICY_CHOICES = [
    "f2",
    "auc_with_min_recall",
    "val_auc",
    "balanced_accuracy",
]
PREPROCESSING_CHOICES = ["auto", "rescale_0_1", "vgg16_imagenet"]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Entrenamiento local para NIH/NLM Malaria Dataset."
    )
    parser.add_argument(
        "--model",
        type=model_arg,
        help="Modelos habilitados: " + ", ".join(enabled_models()),
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
        choices=tuple(OPTIMIZER_DEFAULTS),
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
    add_data_source_args(parser, governed=True)
    parser.add_argument(
        "--dataset-version-id",
        required=True,
        type=dataset_uuid_arg,
        help="UUID explícito de la versión gobernada (obligatorio; sin fallback).",
    )
    parser.add_argument(
        "--track-db",
        action="store_true",
        help="Compatible: todo TRAIN requiere PostgreSQL incluso sin esta opción.",
    )
    parser.add_argument(
        "--expected-dataset-evidence-id", type=dataset_uuid_arg, default=None
    )
    parser.add_argument("--configuration-json", help=argparse.SUPPRESS)
    parser.add_argument("--configuration-origin-json", help=argparse.SUPPRESS)
    parser.add_argument("--model-config", help="Selected JSON model configuration")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--deterministic-ops", action=argparse.BooleanOptionalAction, default=False
    )
    parser.add_argument("--config-digest", help=argparse.SUPPRESS)
    # First parse is syntactic only; only explicitly present flags override JSON.
    args = parser.parse_args(argv)
    tokens = list(sys.argv[1:] if argv is None else argv)
    explicit = {
        action.dest
        for action in parser._actions
        if any(token.split("=")[0] in action.option_strings for token in tokens)
    }
    try:
        if args.configuration_json and args.model_config:
            raise ValueError("CONFIGURATION_SOURCE_CONFLICT")
        selected = (
            json.loads(args.configuration_json)
            if args.configuration_json
            else load_selected(args.model_config)
        )
        override = {"model": {}, "optimizer": {}, "execution": {}}
        defaults = json.loads(
            Path(resolve_descriptor(args.model).config_path).read_text()
        )
        for key in defaults["execution"]:
            if key in explicit:
                override["execution"][key] = getattr(args, key)
        if "epochs" in explicit and "max_epochs" not in explicit:
            override["execution"]["max_epochs"] = args.epochs
        for key, target in [
            ("img_size", "input_shape"),
            ("preprocessing", "preprocessing"),
            ("pretrained_weights", "weights"),
        ]:
            if key in explicit:
                value = getattr(args, key)
                override["model"][target] = (
                    [value, value, 3] if key == "img_size" else value
                )
        if "optimizer" in explicit:
            override["optimizer"]["name"] = args.optimizer
        if "learning_rate" in explicit:
            override["optimizer"]["parameters"] = dict(
                selected.get("optimizer", {}).get("parameters", {}),
                learning_rate=args.learning_rate,
            )
        if "fine_tune_learning_rate" in explicit:
            override["optimizer"]["fine_tune_learning_rate"] = (
                args.fine_tune_learning_rate
            )
        if args.allow_collapsed_checkpoint:
            override["execution"]["reject_prediction_collapse"] = False
        if args.skip_final_test_evaluation:
            override["execution"]["evaluate_best_on_test"] = False
        args.model_configuration = resolve_config(args.model, selected, override)
        resolved = args.model_configuration["resolved"]
        if (
            "fine_tune_learning_rate" in explicit
            and not resolved["execution"]["fine_tune_epochs"]
        ):
            raise ValueError("IGNORED_FINE_TUNE_LEARNING_RATE")
        if (
            args.threshold_output_json
            and not resolved["execution"]["calibrate_threshold"]
        ):
            raise ValueError("IGNORED_THRESHOLD_OUTPUT")
        if args.config_digest and config_digest(resolved) != args.config_digest:
            raise ValueError("BATCH_CONFIGURATION_CHANGED")
        if args.configuration_origin_json:
            if not args.configuration_json or not args.config_digest:
                raise ValueError('BATCH_CONFIGURATION_ORIGIN_REQUIRES_DIGEST')
            origin = json.loads(args.configuration_origin_json)
            if set(origin) != {'requested','provenance'}:
                raise ValueError('INVALID_CONFIGURATION_ORIGIN')
            args.model_configuration['transport_requested'] = args.model_configuration['requested']
            args.model_configuration.update(origin)
    except (ValueError, TypeError, KeyError) as exc:
        parser.error(str(exc))
    explicit_max = args.max_epochs if "max_epochs" in explicit else None
    legacy = args.epochs
    for key, value in resolved["execution"].items():
        setattr(args, key, value)
    args.img_size = resolved["model"]["input_shape"][0]
    args.preprocessing = resolved["model"]["preprocessing"]
    args.pretrained_weights = resolved["model"]["weights"]
    args.optimizer = resolved["optimizer"]["name"]
    args.learning_rate = resolved["optimizer"]["parameters"]["learning_rate"]
    args.fine_tune_learning_rate = resolved["optimizer"]["fine_tune_learning_rate"]
    args.track_db = True
    args.max_epochs = explicit_max
    args.epochs = legacy
    legacy_epochs = args.epochs
    explicit_max_epochs = args.max_epochs
    if explicit_max_epochs is not None:
        resolved_max_epochs = explicit_max_epochs
        epochs_source = "max_epochs"
    elif legacy_epochs is not None:
        resolved_max_epochs = legacy_epochs
        epochs_source = "epochs_legacy"
    else:
        resolved_max_epochs = resolved["execution"]["max_epochs"]
        epochs_source = (
            "selected_configuration"
            if "max_epochs" in selected.get("execution", {})
            else "model_default"
        )
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
    if args.fine_tune_learning_rate is not None and args.fine_tune_learning_rate <= 0:
        parser.error("--fine-tune-learning-rate debe ser mayor que cero.")
    return args


def main():
    args = parse_args()
    if args.dry_run:
        print(json.dumps(args.model_configuration, sort_keys=True))
        print("PLAN ONLY: integridad operativa NO VERIFICADA")
        return
    from ..execution.train import standalone as train

    return train(args)


if __name__ == "__main__":
    main()
