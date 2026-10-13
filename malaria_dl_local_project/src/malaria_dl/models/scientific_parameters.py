"""Scientific parameter dictionary: documentation and persisted-value queries only.

Contracts remain authoritative. Importing this module never resolves a RUN,
loads TensorFlow, accesses a dataset, or queries PostgreSQL.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping

from .optimizers import OPTIMIZER_DEFAULTS


@dataclass(frozen=True)
class Parameter:
    path: str
    contract: str
    restriction: str
    consumers: tuple[str, ...]
    related: tuple[str, ...]
    condition: str
    effect: str
    phase: str
    relations: tuple[str, ...]
    evidence: str = "Código"

    @property
    def persistence(self) -> str:
        return "run_configurations.extension_configuration." + self.path


TRAIN = "execution/train.py:train"
RESOLVE = "models/configuration.py:resolve_config"
SELECT = "models/configuration.py:selection_semantics"
POLICY = "training/checkpoint_policy.py:select_best_epoch_from_history"
MONITOR = "training/checkpoint_policy.py:select_best_epoch_by_monitor"
CALLBACK = "training/checkpoint_policy.py:ClinicalValidationMetricsCallback"
CALIBRATE = "evaluation/threshold_calibration.py:find_threshold_for_target_recall"
ADAPTER = "models/adapters.py:compile_phase"
CONTROLLER = "evaluation/calibration_controller.py:CalibrationController.calibrate"
PARAMETERS: dict[str, Parameter] = {}


def _add(path: str, restriction: str, consumers: tuple[str, ...],
         related: tuple[str, ...], condition: str, effect: str, phase: str,
         relations: tuple[str, ...] = ("Configuración",),
         contract: str = RESOLVE, evidence: str = "Código") -> None:
    PARAMETERS[path] = Parameter(path, contract, restriction, consumers, related,
                                 condition, effect, phase, relations, evidence)


_add('execution.max_epochs', 'int >=1', (TRAIN,), (), 'Siempre', 'Máximo de épocas base; puede cambiar pesos y métricas finales', 'TRAIN base', ('Configuración',))
_add('execution.fine_tune_epochs', 'int >=0; arquitectura compatible', (TRAIN,), ('model.fine_tune_layers',), '>0', 'Activa segunda fase; selección sobre historia global', 'fine-tuning', ('Configuración', 'Dependencia'))
_add('execution.batch_size', 'int >=1', (TRAIN,), (), 'Siempre', 'Batch de carga y optimización; efecto numérico en métricas pendiente de medir', 'TRAIN/VAL', ('Configuración',))
_add('execution.seed', 'int >=0; matriz <=2147483647', (TRAIN,), ('execution.deterministic_ops',), 'Siempre', 'Inicialización y orden de muestras; no garantiza igualdad entre dispositivos', 'TRAIN', ('Configuración', 'Dependencia'))
_add('execution.deterministic_ops', 'bool', (TRAIN,), ('execution.seed',), 'true', 'Activa determinismo TensorFlow; reproducibilidad dependiente del entorno', 'TRAIN', ('Configuración', 'Dependencia'))
_add('execution.no_augment', 'bool', (TRAIN,), ('recipe.augmentation.flip',), 'false y split train', 'Habilita aumento; cambia entradas de entrenamiento', 'TRAIN', ('Configuración', 'Dependencia'))
_add('execution.checkpoint_policy', 'f2 / auc_with_min_recall / val_auc / balanced_accuracy', (POLICY, SELECT,), ('execution.checkpoint_monitor', 'execution.min_recall'), 'selection.explicit=false', 'Ranking de épocas por política; puede cambiar checkpoint y métricas finales', 'selección', ('Configuración', 'Dependencia', 'Selección', 'Cálculo'))
_add('execution.checkpoint_monitor', 'null o CHECKPOINT_METRIC_CHOICES', (SELECT, MONITOR,), ('execution.checkpoint_policy', 'execution.checkpoint_mode'), 'No null activa monitor explícito', 'Selecciona por monitor; evita filtro min_recall de política', 'selección', ('Configuración', 'Dependencia', 'Selección', 'Cálculo'))
_add('execution.checkpoint_mode', 'auto / min / max', (SELECT, MONITOR,), ('execution.checkpoint_monitor',), 'min también activa selection.explicit', 'Dirección de ranking; auto usa min para loss', 'selección', ('Configuración', 'Dependencia', 'Selección', 'Cálculo'))
_add('execution.min_recall', 'number [0,1]', (POLICY, TRAIN,), ('execution.checkpoint_policy', 'execution.checkpoint_monitor'), 'Política auc_with_min_recall sin monitor explícito; siempre en completion', 'Factibilidad de selección y clinical_objective_met a .5; no gobierna calibrador', 'selección/cierre', ('Configuración', 'Dependencia', 'Selección', 'Cálculo'))
_add('execution.beta', 'number =2', (CALLBACK, CONTROLLER, CALIBRATE,), (), 'Siempre', 'F2 fijo; calibrador directo sólo registra beta; contrato rechaza otro valor', 'VAL/calibración', ('Configuración', 'Selección', 'Cálculo'))
_add('execution.reject_prediction_collapse', 'bool', (POLICY, MONITOR, CALLBACK,), ('execution.min_class_fraction',), 'true', 'Excluye épocas colapsadas si hay alternativas; fallback si todas colapsan; no filtra umbrales', 'selección/early stopping', ('Configuración', 'Dependencia', 'Selección', 'Cálculo'))
_add('execution.min_class_fraction', 'number [0,.5]', (CALLBACK,), ('execution.reject_prediction_collapse',), 'Por época', 'Diagnóstico de colapso; calibrador no recibe este valor (usa .05)', 'VAL', ('Configuración', 'Dependencia'))
_add('execution.calibrate_threshold', 'bool', (TRAIN, CONTROLLER,), ('execution.target_recall', 'execution.min_specificity'), 'true; protocolo algorithm=threshold_grid', 'Invoca calibrador una vez tras selección; false conserva .5 y omite evento de calibración', 'calibración/persistencia', ('Configuración', 'Dependencia', 'Selección', 'Cálculo', 'Persistencia'))
_add('execution.target_recall', 'number [0,1]; campaña/v2 (0,1]', (CONTROLLER, CALIBRATE,), ('execution.calibrate_threshold',), 'calibrate_threshold=true', 'Filtro recall >= objetivo; ranking especificidad/precision/F2/BA/umbral; no garantiza factibilidad conjunta', 'calibración', ('Configuración', 'Dependencia', 'Selección', 'Cálculo'))
_add('execution.min_specificity', 'null o number [0,1]', (CONTROLLER, CALIBRATE, TRAIN,), ('execution.calibrate_threshold', 'execution.min_recall'), 'No null; calibración habilitada para búsqueda', 'Restricción relajable con warning; también completion a .5; afecta umbral, matriz, recall, especificidad y F2', 'calibración/cierre', ('Configuración', 'Dependencia', 'Selección', 'Cálculo'))
_add('execution.early_stopping', 'bool', (TRAIN,), (), 'true', 'Añade EarlyStopping por fase; reduce épocas ejecutadas', 'TRAIN', ('Configuración',))
_add('execution.early_stopping_monitor', 'null o CHECKPOINT_METRIC_CHOICES', (SELECT, CALLBACK,), ('execution.early_stopping', 'execution.checkpoint_monitor'), 'early_stopping=true', 'Monitor lógico transformado a val_early_stopping_score; puede cambiar parada', 'TRAIN', ('Configuración', 'Dependencia'))
_add('execution.early_stopping_mode', 'auto / min / max', (SELECT, CALLBACK,), ('execution.early_stopping_monitor',), 'early_stopping=true', 'Dirección del score normalizado; auto hereda selección explícita', 'TRAIN', ('Configuración', 'Dependencia'))
_add('execution.early_stopping_patience', 'int >=0', (TRAIN,), ('execution.early_stopping',), 'early_stopping=true', 'Épocas sin mejora toleradas', 'TRAIN', ('Configuración', 'Dependencia'))
_add('execution.early_stopping_min_delta', 'number >=0', (TRAIN,), ('execution.early_stopping',), 'early_stopping=true', 'Mejora mínima sobre score normalizado; no sobre métrica cruda', 'TRAIN', ('Configuración', 'Dependencia'))
_add('execution.restore_best_weights', 'bool', (TRAIN,), ('execution.early_stopping', 'execution.fine_tune_epochs'), 'early_stopping=true', 'Restauración por fase; final recarga checkpoint global; puede afectar inicio FT', 'TRAIN', ('Configuración', 'Dependencia'))
_add('execution.evaluate_best_on_test', 'bool; motor gobernado exige false', (TRAIN,), (), 'Siempre', 'true rechaza ejecución antes de cargar datos; no activa TEST', 'preflight', ('Configuración',))

_MODEL = {
    "input_shape": ("[h,h,3]; int h>=32", "Forma de entradas; métricas indirectamente vía modelo"),
    "preprocessing": ("auto o modo admitido por descriptor", "Transformación externa; auto se resuelve antes de persistir"),
    "weights": ("none/imagenet según arquitectura", "Inicialización de pesos"),
    "dropout": ("number [0,1)", "Regularización Dropout; efecto sobre métricas no monotónico"),
    "l2": ("number [0,1); fijo 0 si default 0", "Penalización de pesos en Custom CNN"),
    "head_units": ("Fijo al default versionado", "Contrato de arquitectura; constructor usa constante, no este campo"),
    "batch_normalization": ("Fijo al default versionado", "Contrato de arquitectura; constructor usa política fija"),
    "fine_tune_layers": ("int entre 0 y default; compatible con arquitectura", "Últimas capas entrenables en FT"),
}
for key, (restriction, effect) in _MODEL.items():
    _add("model." + key, restriction,
         (RESOLVE,) if key in ("head_units", "batch_normalization") else
         (("models/adapters.py:BaseAdapter.set_phase",) if key == "fine_tune_layers" else
          ("models/adapters.py:CustomCNNAdapter.build", "models/adapters.py:VGG16Adapter.build",
           "models/adapters.py:DenseNet121Adapter.build", TRAIN)),
         ("execution.fine_tune_epochs",) if key == "fine_tune_layers" else (),
         "Según arquitectura; fine_tune_layers sólo FT", effect, "construcción/TRAIN")

_add("optimizer.name", "adam/adamw/sgd/adadelta admitido por descriptor", (ADAPTER,), (),
     "Siempre", "Algoritmo de actualización de pesos", "TRAIN")
_add("optimizer.fine_tune_learning_rate", "number >0", (ADAPTER,),
     ("execution.fine_tune_epochs", "optimizer.parameters.learning_rate"), "FT activa",
     "Sustituye learning_rate en FT; estado optimizador nuevo por fase", "fine-tuning")
_OPT_EFFECTS = {
    "learning_rate": "Escala del paso de actualización; FT la sustituye",
    "weight_decay": "Decaimiento de pesos",
    "clipnorm": "Recorte por norma por variable",
    "global_clipnorm": "Recorte por norma global",
    "clipvalue": "Recorte por valor",
    "use_ema": "Activa media móvil de pesos",
    "ema_momentum": "Factor de media móvil; relevante con use_ema",
    "ema_overwrite_frequency": "Frecuencia de sustitución por media móvil; requiere use_ema",
    "loss_scale_factor": "Escala de loss/gradientes",
    "gradient_accumulation_steps": "Acumulación de gradientes antes del paso",
    "beta_1": "Decaimiento primer momento Adam/AdamW",
    "beta_2": "Decaimiento segundo momento Adam/AdamW",
    "epsilon": "Estabilización numérica",
    "amsgrad": "Variante AMSGrad Adam/AdamW",
    "momentum": "Momento SGD",
    "nesterov": "Variante Nesterov SGD",
    "rho": "Decaimiento Adadelta",
}
for key, effect in _OPT_EFFECTS.items():
    names = [name for name, values in OPTIMIZER_DEFAULTS.items() if key in values]
    restriction = "bool" if key in ("use_ema", "amsgrad", "nesterov") else "number finito >=0; null sólo si default null"
    if key in ("learning_rate", "epsilon", "clipnorm", "global_clipnorm", "clipvalue", "loss_scale_factor"):
        restriction += "; si no null, >0"
    if key in ("beta_1", "beta_2", "rho", "momentum", "ema_momentum"):
        restriction += "; <1"
    if key in ("ema_overwrite_frequency", "gradient_accumulation_steps"):
        restriction += "; int >=" + ("2" if key == "gradient_accumulation_steps" else "1")
    related = ("optimizer.name",)
    if key.startswith("ema_"):
        related += ("optimizer.parameters.use_ema",)
    if key in ("clipnorm", "global_clipnorm", "clipvalue"):
        restriction += "; clipping mutuamente exclusivo"
        related += tuple("optimizer.parameters." + k for k in ("clipnorm", "global_clipnorm", "clipvalue") if k != key)
    _add("optimizer.parameters." + key, restriction,
         ("models/optimizers.py:build_optimizer", ADAPTER), related,
         "Optimizador en " + ", ".join(names), effect + "; impacto en métricas pendiente de medir",
         "TRAIN/FT", ("Configuración", "Dependencia"), "models/optimizers.py:optimizer_config")


def flatten(value: Mapping[str, object], prefix: str = "") -> dict[str, object]:
    result = {}
    for key, item in value.items():
        path = prefix + key
        if isinstance(item, dict) and item:
            result.update(flatten(item, path + "."))
        else:
            result[path] = deepcopy(item)
    return result


def defaults_by_model() -> dict[str, dict]:
    directory = Path(__file__).resolve().parents[3] / "configs/models"
    return {p.stem: json.loads(p.read_text()) for p in sorted(directory.glob("*.json"))}


# Recipe values are immutable declarations. Only reduce_lr is consumed as a dict;
# augmentation/loss constants are implemented separately, not configurable knobs.
for key in flatten(next(iter(defaults_by_model().values()))["recipe"]):
    reduce = key.startswith("reduce_lr.")
    _add("recipe." + key, "Inmutable: igualdad con receta versionada",
         (TRAIN,) if reduce else (RESOLVE,), (), "Siempre" if reduce else "Validación de receta",
         "Configura ReduceLROnPlateau; afecta learning rate" if reduce else
         "Declaración validada; no se pasa como argumento al algoritmo. Correspondencia con constantes requiere revisión",
         "TRAIN", ("Configuración", "Persistencia"), evidence="Código" if reduce else "Pendiente de verificar correspondencia")

_SELECTION_EFFECTS = {
    "monitor": "Métrica efectiva usada por selección explícita",
    "mode": "Dirección efectiva min/max de selección explícita",
    "explicit": "Elige select_best_epoch_by_monitor frente a select_best_epoch_from_history",
    "early_stopping_monitor": "Monitor lógico del callback que calcula val_early_stopping_score",
    "early_stopping_mode": "Dirección efectiva del monitor lógico de early stopping",
    "threshold": "Persistido como default_threshold; TRAIN usa .5 literal, no lee este campo",
    "beta": "Declaración derivada; TRAIN usa execution.beta, no lee este campo",
    "clinical_objective": "Texto descriptivo; completion usa min_recall/min_specificity directamente",
    "fallback": "Texto descriptivo; las funciones de selección implementan fallback",
}
for key, effect in _SELECTION_EFFECTS.items():
    descriptive = key in ("beta", "clinical_objective", "fallback")
    consumers = (("persistence/v2_projection.py:project_configuration",) if key == "threshold" else
                 (SELECT,) if descriptive else (TRAIN,))
    _add("selection." + key, "Derivado por selection_semantics; threshold=.5, beta=2",
         consumers, ("execution.checkpoint_monitor", "execution.checkpoint_policy"),
         "Snapshot resuelto", effect, "selección",
         ("Persistencia",) if descriptive or key == "threshold" else ("Configuración", "Selección"), SELECT)


def effective_values(resolved: Mapping[str, object]) -> dict[str, dict]:
    """Read extension_configuration (or snapshot['resolved']); never fill defaults.

    Unknown historical fields are preserved, and missing differs from JSON null.
    This is configuration evidence, not a claim that an inactive branch executed.
    """
    actual = flatten(resolved)
    return {path: {"present": path in actual, "value": deepcopy(actual.get(path)),
                   "governed": path in PARAMETERS}
            for path in sorted(set(PARAMETERS) | set(actual))}


def compare_runs(runs: Mapping[str, Mapping[str, object]]) -> dict[str, dict]:
    """RUN id -> persisted resolved snapshot; include unchanged and missing values."""
    values = {run: effective_values(resolved) for run, resolved in runs.items()}
    paths = sorted({path for row in values.values() for path in row})
    return {path: {run: row.get(path, {"present": False, "value": None, "governed": path in PARAMETERS})
                   for run, row in values.items()} for path in paths}


def consumer_map() -> dict[str, tuple[str, ...]]:
    return {consumer: tuple(p.path for p in PARAMETERS.values() if consumer in p.consumers)
            for consumer in sorted({c for p in PARAMETERS.values() for c in p.consumers})}
