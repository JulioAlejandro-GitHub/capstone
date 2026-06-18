import math

import numpy as np


def _logit(probability):
    probability = float(np.clip(probability, 1e-7, 1.0 - 1e-7))
    return math.log(probability / (1.0 - probability))


def _sigmoid(value):
    return 1.0 / (1.0 + math.exp(-float(value)))


def calibrate_probability(raw_probability, method="none", calibration_params=None):
    raw_probability = float(np.clip(raw_probability, 0.0, 1.0))
    calibration_params = calibration_params or {}
    method = (method or "none").lower()

    if method == "none":
        return {
            "method": "none",
            "applied": False,
            "raw_probability": raw_probability,
            "calibrated_probability": raw_probability,
            "params": {},
        }

    if method == "temperature_scaling":
        temperature = calibration_params.get("temperature")
        if temperature is None:
            return {
                "method": "temperature_scaling",
                "applied": False,
                "raw_probability": raw_probability,
                "calibrated_probability": raw_probability,
                "params": {},
                "warning": "temperature no informado; se mantiene probabilidad sin calibrar.",
            }

        temperature = float(temperature)
        if temperature <= 0:
            raise ValueError("temperature debe ser mayor que cero.")

        calibrated_probability = _sigmoid(_logit(raw_probability) / temperature)
        return {
            "method": "temperature_scaling",
            "applied": True,
            "raw_probability": raw_probability,
            "calibrated_probability": float(np.clip(calibrated_probability, 0.0, 1.0)),
            "params": {"temperature": temperature},
        }

    raise ValueError(f"Método de calibración no soportado: {method}")
