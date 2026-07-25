from __future__ import annotations

from pathlib import Path

import numpy as np

from src.config import (
    CLASS_NAMES,
    LABEL_MAPPING_VERSION,
    LEGACY_TFDS_LABEL_MAPPING_VERSION,
    NEGATIVE_LABEL,
    POSITIVE_LABEL,
    RAW_MODEL_SCORE_MEANING,
    label_mapping_metadata,
)
RECOMMENDATION = (
    "Resultado experimental. Requiere revisión por profesional competente si se usa "
    "en contexto real."
)
DISCLAIMER = "Resultado experimental de apoyo. No corresponde a diagnóstico clínico definitivo."


def validate_binary_labels(class_names=None):
    class_names = list(class_names or CLASS_NAMES)
    if POSITIVE_LABEL not in class_names or NEGATIVE_LABEL not in class_names:
        raise ValueError(
            "Se esperaban clases binarias con etiquetas "
            f"{POSITIVE_LABEL!r} y {NEGATIVE_LABEL!r}. Recibido: {class_names}"
        )
    return class_names


def probability_by_class_from_scalar_score(
    score,
    class_names=None,
    label_mapping_version=LABEL_MAPPING_VERSION,
):
    """
    Convierte la salida sigmoid del proyecto a probabilidades por clase.

    clinical_v1_parasitized_positive:
      raw_model_score = probability_parasitized

    legacy_tfds_parasitized_zero:
      raw_model_score = probability_uninfected
    """
    class_names = validate_binary_labels(class_names)
    raw_model_score = float(np.clip(score, 0.0, 1.0))
    if label_mapping_version == LABEL_MAPPING_VERSION:
        probabilities = {
            POSITIVE_LABEL: raw_model_score,
            NEGATIVE_LABEL: float(1.0 - raw_model_score),
        }
    elif label_mapping_version == LEGACY_TFDS_LABEL_MAPPING_VERSION:
        probabilities = {
            POSITIVE_LABEL: float(1.0 - raw_model_score),
            NEGATIVE_LABEL: raw_model_score,
        }
    else:
        raise ValueError(f"label_mapping_version no soportado: {label_mapping_version}")
    return {
        POSITIVE_LABEL: float(probabilities[POSITIVE_LABEL]),
        NEGATIVE_LABEL: float(probabilities[NEGATIVE_LABEL]),
    }


def probabilities_by_class_from_prediction(
    prediction,
    class_names=None,
    label_mapping_version=LABEL_MAPPING_VERSION,
):
    class_names = validate_binary_labels(class_names)
    prediction = np.asarray(prediction, dtype=np.float32)

    if prediction.ndim == 2 and prediction.shape[1] == len(class_names):
        probabilities = {
            class_name: float(np.clip(prediction[0, index], 0.0, 1.0))
            for index, class_name in enumerate(class_names)
        }
        return {
            POSITIVE_LABEL: probabilities[POSITIVE_LABEL],
            NEGATIVE_LABEL: probabilities[NEGATIVE_LABEL],
        }

    if prediction.size == 1:
        return probability_by_class_from_scalar_score(
            prediction.reshape(-1)[0],
            class_names,
            label_mapping_version=label_mapping_version,
        )

    raise ValueError(
        f"Salida de modelo no soportada para {len(class_names)} clases: shape={prediction.shape}"
    )


def probabilities_array_from_prediction(
    prediction,
    class_names=None,
    label_mapping_version=LABEL_MAPPING_VERSION,
):
    class_names = validate_binary_labels(class_names)
    probabilities_by_class = probabilities_by_class_from_prediction(
        prediction,
        class_names,
        label_mapping_version=label_mapping_version,
    )
    return np.asarray(
        [probabilities_by_class[class_name] for class_name in class_names],
        dtype=np.float32,
    )


def label_from_probability_parasitized(probability_parasitized, threshold=0.5):
    return POSITIVE_LABEL if float(probability_parasitized) >= float(threshold) else NEGATIVE_LABEL


def classify_by_threshold(probability_parasitized: float, threshold: float = 0.5) -> str:
    return label_from_probability_parasitized(probability_parasitized, threshold)


def confidence_level_from_probability(probability_parasitized):
    probability_parasitized = float(probability_parasitized)
    if probability_parasitized >= 0.80 or probability_parasitized <= 0.20:
        return "alta"
    if probability_parasitized >= 0.60 or probability_parasitized <= 0.40:
        return "media"
    return "baja"


def get_confidence_level(probability_parasitized: float) -> str:
    return confidence_level_from_probability(probability_parasitized)


def decision_from_probability(probability_parasitized, threshold=0.5):
    probability_parasitized = float(probability_parasitized)
    predicted_label = label_from_probability_parasitized(probability_parasitized, threshold)
    if 0.40 < probability_parasitized < 0.60:
        return "caso_incierto_requiere_revision"
    if predicted_label == POSITIVE_LABEL:
        return "compatible_con_celula_parasitada"
    return "compatible_con_celula_no_parasitada"


def build_decision_text(
    predicted_label,
    probability_parasitized,
    confidence_level,
    threshold=0.5,
):
    decision_code = decision_from_probability(probability_parasitized, threshold)
    if predicted_label == POSITIVE_LABEL and decision_code != "caso_incierto_requiere_revision":
        short_text = "Compatible con célula parasitada."
    elif predicted_label == NEGATIVE_LABEL and decision_code != "caso_incierto_requiere_revision":
        short_text = "Compatible con célula no parasitada."
    else:
        short_text = "Caso incierto, requiere revisión humana."

    return {
        "decision_code": decision_code,
        "confidence_level": confidence_level,
        "short_text": short_text,
        "human_readable_response": human_response_from_decision(
            decision_code,
            probability_parasitized,
        ),
        "recommendation": RECOMMENDATION,
        "disclaimer": DISCLAIMER,
    }


def human_response_from_decision(decision, probability_parasitized):
    percentage = round(float(probability_parasitized) * 100)
    if decision == "caso_incierto_requiere_revision":
        return (
            "La imagen corresponde a un caso incierto y requiere revisión humana. "
            f"La probabilidad estimada de célula parasitada es {percentage}%."
        )
    if decision == "compatible_con_celula_parasitada":
        return (
            "La imagen es compatible con una célula parasitada, con probabilidad "
            f"estimada de malaria de {percentage}%."
        )
    return (
        "La imagen es compatible con una célula no parasitada, con probabilidad "
        f"estimada de malaria de {percentage}%."
    )


def build_clinical_inference_response(
    image,
    preprocessing,
    model,
    probabilities,
    threshold,
    explainability=None,
    tracking=None,
):
    probability_parasitized = float(probabilities["probability_parasitized"])
    probability_uninfected = float(probabilities["probability_uninfected"])
    predicted_label = classify_by_threshold(probability_parasitized, threshold)
    confidence_level = get_confidence_level(probability_parasitized)
    decision_text = build_decision_text(
        predicted_label,
        probability_parasitized,
        confidence_level,
        threshold,
    )

    return {
        "workflow": "clinical_inference_experimental",
        "image": image,
        "preprocessing": preprocessing,
        "model": model,
        "probabilities": {
            **probabilities,
            "probability_parasitized": probability_parasitized,
            "probability_uninfected": probability_uninfected,
            "raw_model_score_meaning": probabilities.get(
                "raw_model_score_meaning",
                RAW_MODEL_SCORE_MEANING,
            ),
        },
        "label_mapping": label_mapping_metadata(
            probabilities.get("label_mapping_version", LABEL_MAPPING_VERSION)
        ),
        "decision": {
            "threshold": float(threshold),
            "predicted_label": predicted_label,
            "confidence_level": confidence_level,
            **decision_text,
        },
        "explainability": explainability
        or {
            "requested": False,
            "methods": [],
            "success": False,
            "outputs": [],
            "error": None,
        },
        "tracking": tracking
        or {
            "track_db": False,
            "registered": False,
            "run_id": None,
            "prediction_id": None,
            "error": None,
        },
        "disclaimer": DISCLAIMER,
    }


def build_prediction_response(
    image_path,
    stored_image_path,
    model_checkpoint,
    probability_parasitized,
    threshold,
    model_name=None,
    explainability_result=None,
    tracking_result=None,
    extra=None,
):
    probability_parasitized = float(np.clip(probability_parasitized, 0.0, 1.0))
    probability_uninfected = float(np.clip(1.0 - probability_parasitized, 0.0, 1.0))
    predicted_label = label_from_probability_parasitized(probability_parasitized, threshold)
    confidence_level = confidence_level_from_probability(probability_parasitized)
    decision = decision_from_probability(probability_parasitized, threshold)

    response = {
        "image_path": str(image_path),
        "stored_image_path": None if stored_image_path is None else str(stored_image_path),
        "model_checkpoint": str(model_checkpoint),
        "model_name": model_name or Path(model_checkpoint).parent.name or Path(model_checkpoint).stem,
        "predicted_label": predicted_label,
        "probability_parasitized": probability_parasitized,
        "probability_uninfected": probability_uninfected,
        "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
        "label_mapping": label_mapping_metadata(),
        "threshold": float(threshold),
        "confidence_level": confidence_level,
        "decision": decision,
        "human_readable_response": human_response_from_decision(
            decision,
            probability_parasitized,
        ),
        "recommendation": RECOMMENDATION,
        "disclaimer": DISCLAIMER,
        "explainability": explainability_result
        or {
            "method": None,
            "success": False,
            "image_path": None,
            "last_conv_layer": None,
            "error": None,
        },
        "tracking": tracking_result
        or {
            "track_db": False,
            "registered": False,
            "run_id": None,
            "prediction_id": None,
            "error": None,
        },
    }

    if extra:
        response.update(extra)

    return response
