"""Strict, immutable scientific output contracts. No storage/runtime dependencies."""
from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields
import math

from ..evaluation.binary_counts import metrics_from_counts

METRIC_TOLERANCE = 1e-12


def _keys(value, names):
    if not isinstance(value, Mapping) or set(value) != set(names):
        raise ValueError("Invalid scientific contract fields")


def _unit(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Expected a finite number in [0, 1]")


@dataclass(frozen=True, slots=True)
class ThresholdResult:
    value: float
    source: str

    def __post_init__(self):
        _unit(self.value)
        if self.source not in ("validation_calibration", "default"):
            raise ValueError("Unknown threshold source")
        if self.source == "default" and self.value != 0.5:
            raise ValueError("TRAIN default threshold is 0.5")


@dataclass(frozen=True, slots=True)
class ConfusionMatrix:
    tn: int
    fp: int
    fn: int
    tp: int

    def __post_init__(self):
        if any(type(v) is not int or v < 0 for v in asdict(self).values()):
            raise ValueError("Counts must be nonnegative integers")


@dataclass(frozen=True, slots=True)
class BinaryMetrics:
    recall: float
    specificity: float
    precision: float
    f1: float
    f2: float
    balanced_accuracy: float
    roc_auc: float | None
    pr_auc: float | None

    def __post_init__(self):
        for key, value in asdict(self).items():
            if value is None and key in ("roc_auc", "pr_auc"):
                continue
            _unit(value)


@dataclass(frozen=True, slots=True)
class ValidationEvaluationV1:
    n_samples: int
    threshold: ThresholdResult
    confusion_matrix: ConfusionMatrix
    metrics: BinaryMetrics
    schema_version: str = "validation_evaluation_v1"
    evaluation_role: str = "training_validation_final"
    split: str = "val"

    def __post_init__(self):
        if (self.schema_version != "validation_evaluation_v1"
                or self.evaluation_role != "training_validation_final" or self.split != "val"):
            raise ValueError("Unsupported evaluation contract")
        if type(self.n_samples) is not int or self.n_samples <= 0:
            raise ValueError("Empty or invalid validation population")
        for name, cls in (("threshold", ThresholdResult), ("confusion_matrix", ConfusionMatrix),
                          ("metrics", BinaryMetrics)):
            if type(getattr(self, name)) is not cls:
                raise ValueError("Typed scientific component required")
        counts = asdict(self.confusion_matrix)
        if sum(counts.values()) != self.n_samples:
            raise ValueError("Confusion matrix population mismatch")
        for name, expected in metrics_from_counts(**counts).items():
            if not math.isclose(getattr(self.metrics, name), expected,
                                rel_tol=METRIC_TOLERANCE, abs_tol=METRIC_TOLERANCE):
                raise ValueError("Metric disagrees with confusion matrix")
        single_class = counts['tp'] + counts['fn'] == 0 or counts['tn'] + counts['fp'] == 0
        for value in (self.metrics.roc_auc, self.metrics.pr_auc):
            if (value is None) != single_class:
                raise ValueError("AUC must be null exactly for single-class validation")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        _keys(value, (f.name for f in fields(cls)))
        data = dict(value)
        for name, component in (("threshold", ThresholdResult), ("confusion_matrix", ConfusionMatrix),
                                ("metrics", BinaryMetrics)):
            _keys(data[name], (f.name for f in fields(component)))
            data[name] = component(**data[name])
        return cls(**data)


@dataclass(frozen=True, slots=True)
class TrainingResultsV1:
    validation: ValidationEvaluationV1
    schema_version: str = "training_results_v1"

    def __post_init__(self):
        if self.schema_version != "training_results_v1" or type(self.validation) is not ValidationEvaluationV1:
            raise ValueError("Unsupported training result")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        _keys(value, ("schema_version", "validation"))
        return cls(ValidationEvaluationV1.from_dict(value['validation']), value['schema_version'])
