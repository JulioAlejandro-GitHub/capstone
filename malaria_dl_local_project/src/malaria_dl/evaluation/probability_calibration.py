import math
import json
from pathlib import Path

import numpy as np


CALIBRATION_SCHEMA_VERSION = 1


def _logit(probability):
    probability = float(np.clip(probability, 1e-7, 1.0 - 1e-7))
    return math.log(probability / (1.0 - probability))


def _sigmoid(value):
    return 1.0 / (1.0 + math.exp(-float(value)))


def logit_array(probabilities):
    probabilities = np.asarray(probabilities, dtype=np.float64)
    probabilities = np.clip(probabilities, 1e-7, 1.0 - 1e-7)
    return np.log(probabilities / (1.0 - probabilities))


def sigmoid_array(values):
    values = np.asarray(values, dtype=np.float64)
    return 1.0 / (1.0 + np.exp(-values))


def apply_temperature_scaling(probabilities, temperature):
    temperature = float(temperature)
    if temperature <= 0:
        raise ValueError("temperature debe ser mayor que cero.")
    return sigmoid_array(logit_array(probabilities) / temperature)


def binary_nll(y_true, probabilities):
    y_true = np.asarray(y_true, dtype=np.float64).reshape(-1)
    probabilities = np.asarray(probabilities, dtype=np.float64).reshape(-1)
    if len(y_true) != len(probabilities):
        raise ValueError("y_true y probabilities deben tener el mismo largo.")
    probabilities = np.clip(probabilities, 1e-7, 1.0 - 1e-7)
    loss = (y_true * np.log(probabilities)) + (
        (1.0 - y_true) * np.log(1.0 - probabilities)
    )
    return float(-np.mean(loss))


def brier_score(y_true, probabilities):
    y_true = np.asarray(y_true, dtype=np.float64).reshape(-1)
    probabilities = np.asarray(probabilities, dtype=np.float64).reshape(-1)
    if len(y_true) != len(probabilities):
        raise ValueError("y_true y probabilities deben tener el mismo largo.")
    return float(np.mean(np.square(probabilities - y_true)))


def expected_calibration_error(y_true, probabilities, n_bins=10):
    y_true = np.asarray(y_true, dtype=np.float64).reshape(-1)
    probabilities = np.asarray(probabilities, dtype=np.float64).reshape(-1)
    if len(y_true) != len(probabilities):
        raise ValueError("y_true y probabilities deben tener el mismo largo.")

    bins = np.linspace(0.0, 1.0, int(n_bins) + 1)
    ece = 0.0
    for index in range(int(n_bins)):
        lower = bins[index]
        upper = bins[index + 1]
        if index == int(n_bins) - 1:
            mask = (probabilities >= lower) & (probabilities <= upper)
        else:
            mask = (probabilities >= lower) & (probabilities < upper)
        if not np.any(mask):
            continue
        bin_confidence = float(np.mean(probabilities[mask]))
        bin_accuracy = float(np.mean(y_true[mask]))
        ece += float(np.mean(mask)) * abs(bin_accuracy - bin_confidence)
    return float(ece)


def calibration_metrics(y_true, raw_probabilities, calibrated_probabilities, n_bins=10):
    return {
        "nll_before": binary_nll(y_true, raw_probabilities),
        "nll_after": binary_nll(y_true, calibrated_probabilities),
        "brier_before": brier_score(y_true, raw_probabilities),
        "brier_after": brier_score(y_true, calibrated_probabilities),
        "ece_before": expected_calibration_error(y_true, raw_probabilities, n_bins=n_bins),
        "ece_after": expected_calibration_error(y_true, calibrated_probabilities, n_bins=n_bins),
    }


def fit_temperature_scaling(
    y_true,
    raw_probabilities,
    temperature_min=0.05,
    temperature_max=10.0,
    grid_size=200,
    refinement_rounds=3,
):
    y_true = np.asarray(y_true, dtype=np.float64).reshape(-1)
    raw_probabilities = np.asarray(raw_probabilities, dtype=np.float64).reshape(-1)
    if len(y_true) == 0:
        raise ValueError("No hay muestras para calibrar.")
    if len(y_true) != len(raw_probabilities):
        raise ValueError("y_true y raw_probabilities deben tener el mismo largo.")
    if temperature_min <= 0 or temperature_max <= 0 or temperature_min >= temperature_max:
        raise ValueError("Rango de temperatura inválido.")
    if grid_size < 3:
        raise ValueError("grid_size debe ser al menos 3.")

    lower = float(temperature_min)
    upper = float(temperature_max)
    best_temperature = 1.0
    best_nll = float("inf")

    for _ in range(int(refinement_rounds) + 1):
        temperatures = np.geomspace(lower, upper, int(grid_size))
        losses = np.asarray(
            [
                binary_nll(y_true, apply_temperature_scaling(raw_probabilities, temperature))
                for temperature in temperatures
            ],
            dtype=np.float64,
        )
        best_index = int(np.argmin(losses))
        best_temperature = float(temperatures[best_index])
        best_nll = float(losses[best_index])

        left_index = max(0, best_index - 1)
        right_index = min(len(temperatures) - 1, best_index + 1)
        next_lower = float(temperatures[left_index])
        next_upper = float(temperatures[right_index])
        if next_lower == next_upper:
            break
        lower, upper = next_lower, next_upper

    calibrated = apply_temperature_scaling(raw_probabilities, best_temperature)
    metrics = calibration_metrics(y_true, raw_probabilities, calibrated)
    metrics["best_validation_nll"] = best_nll
    return {
        "temperature": best_temperature,
        "metrics": metrics,
        "calibrated_probabilities": calibrated.astype(float),
    }


def load_calibration_file(calibration_file):
    path = Path(calibration_file).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo de calibración: {path}")
    with path.open("r", encoding="utf-8") as file_handle:
        payload = json.load(file_handle)

    method = payload.get("method")
    if method != "temperature_scaling":
        raise ValueError(f"Método de calibración no soportado en archivo: {method}")
    temperature = payload.get("temperature") or (payload.get("params") or {}).get("temperature")
    if temperature is None:
        raise ValueError("Archivo de calibración inválido: falta temperature.")
    if float(temperature) <= 0:
        raise ValueError("Archivo de calibración inválido: temperature debe ser mayor que cero.")
    payload["temperature"] = float(temperature)
    payload["calibration_file"] = str(path)
    return payload


def calibration_params_from_file(calibration_payload):
    return {
        "temperature": calibration_payload["temperature"],
        "calibration_file": calibration_payload.get("calibration_file"),
        "source": "calibration_file",
        "schema_version": calibration_payload.get("schema_version"),
        "metrics": calibration_payload.get("metrics"),
        "positive_label": calibration_payload.get("positive_label"),
        "score_name": calibration_payload.get("score_name"),
    }


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
        params = {"temperature": temperature}
        if calibration_params.get("calibration_file"):
            params["calibration_file"] = calibration_params.get("calibration_file")
        return {
            "method": "temperature_scaling",
            "applied": True,
            "raw_probability": raw_probability,
            "calibrated_probability": float(np.clip(calibrated_probability, 0.0, 1.0)),
            "params": params,
            "calibration_file": calibration_params.get("calibration_file"),
            "source": calibration_params.get("source", "manual_temperature"),
            "metrics": calibration_params.get("metrics"),
            "positive_label": calibration_params.get("positive_label"),
            "score_name": calibration_params.get("score_name"),
        }

    raise ValueError(f"Método de calibración no soportado: {method}")
