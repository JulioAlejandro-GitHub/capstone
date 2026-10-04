"""Coordinate existing post-checkpoint VAL calibration without changing policy."""
from __future__ import annotations

from copy import deepcopy
from typing import Mapping, Sequence

from .threshold_calibration import find_threshold_for_target_recall, validate_calibration_split
from ..results.training import ThresholdResult


class CalibrationController:
    """Consume an effective snapshot already validated by resolve_config.

    Historical snapshots must not be resolved against today's defaults. New
    requests use from_request, which delegates all validation to the contract.
    The caller owns checkpoint selection, provenance and persistence.
    """

    def __init__(self, configuration: Mapping[str, object]) -> None:
        self.execution = deepcopy(configuration["resolved"]["execution"])

    @classmethod
    def from_request(cls, model_name: str, selected: dict | None = None,
                     overrides: dict | None = None, *, batch: bool = False) -> CalibrationController:
        from ..models.configuration import resolve_config
        return cls(resolve_config(model_name, selected, overrides, batch=batch))

    def calibrate(self, labels: Sequence[int], scores: Sequence[float], *,
                  split: str = "val") -> dict:
        validate_calibration_split(split)
        e = self.execution
        if not e["calibrate_threshold"]:
            return {"enabled": False, "threshold": 0.5}
        return find_threshold_for_target_recall(
            labels, scores, target_recall=e["target_recall"],
            min_specificity=e["min_specificity"], beta=e["beta"],
        )

    def threshold(self, result: dict) -> ThresholdResult:
        if self.execution["calibrate_threshold"]:
            return ThresholdResult(result["threshold_used"], result["threshold_source"])
        return ThresholdResult(result["threshold"], "default")
