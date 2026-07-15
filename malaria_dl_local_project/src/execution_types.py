"""Canonical execution type names used across model workflows."""

TRAIN_BASE = "train_base"
FINE_TUNING = "fine_tuning"
TRAIN_COMBINED = "train_combined"
EVALUATE = "evaluate"
THRESHOLD_CALIBRATION = "threshold_calibration"
EXPLAINABILITY = "explainability"
INFERENCE = "inference"
TTA = "tta"
ENSEMBLE = "ensemble"


SUPPORTED_EXECUTION_TYPES = [
    TRAIN_BASE,
    FINE_TUNING,
    TRAIN_COMBINED,
    EVALUATE,
    THRESHOLD_CALIBRATION,
    EXPLAINABILITY,
    INFERENCE,
    TTA,
    ENSEMBLE,
]


def validate_execution_type(execution_type: str) -> str:
    """Return a supported execution type or raise a descriptive error."""
    if not isinstance(execution_type, str) or execution_type not in SUPPORTED_EXECUTION_TYPES:
        supported = ", ".join(SUPPORTED_EXECUTION_TYPES)
        raise ValueError(
            f"Tipo de ejecución no soportado: {execution_type!r}. "
            f"Valores permitidos: {supported}."
        )
    return execution_type
