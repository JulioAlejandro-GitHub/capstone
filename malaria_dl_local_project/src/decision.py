from __future__ import annotations

from pathlib import Path

import numpy as np

from src.config import CLASS_NAMES


POSITIVE_LABEL = "parasitized"
NEGATIVE_LABEL = "uninfected"
RECOMMENDATION = (
    "Resultado experimental. Requiere revisión por profesional competente si se usa "
    "en contexto real."
)


def validate_binary_labels(class_names=None):
    class_names = list(class_names or CLASS_NAMES)
    if POSITIVE_LABEL not in class_names or NEGATIVE_LABEL not in class_names:
        raise ValueError(
            "Se esperaban clases binarias con etiquetas "
            f"{POSITIVE_LABEL!r} y {NEGATIVE_LABEL!r}. Recibido: {class_names}"
        )
    return class_names


def probability_by_class_from_scalar_score(score, class_names=None):
    """
    Convierte la salida sigmoid del proyecto a probabilidades por clase.

    Los modelos actuales fueron entrenados con TFDS, donde:
      0 = parasitized
      1 = uninfected

    Por eso la salida sigmoid representa P(label=1) = P(uninfected), no la
    probabilidad clínica positiva.
    """
    class_names = validate_binary_labels(class_names)
    score_class_1 = float(np.clip(score, 0.0, 1.0))
    probabilities = {
        class_names[0]: float(1.0 - score_class_1),
        class_names[1]: score_class_1,
    }
    return {
        POSITIVE_LABEL: float(probabilities[POSITIVE_LABEL]),
        NEGATIVE_LABEL: float(probabilities[NEGATIVE_LABEL]),
    }


def probabilities_by_class_from_prediction(prediction, class_names=None):
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
        return probability_by_class_from_scalar_score(prediction.reshape(-1)[0], class_names)

    raise ValueError(
        f"Salida de modelo no soportada para {len(class_names)} clases: shape={prediction.shape}"
    )


def probabilities_array_from_prediction(prediction, class_names=None):
    class_names = validate_binary_labels(class_names)
    probabilities_by_class = probabilities_by_class_from_prediction(prediction, class_names)
    return np.asarray(
        [probabilities_by_class[class_name] for class_name in class_names],
        dtype=np.float32,
    )


def label_from_probability_parasitized(probability_parasitized, threshold=0.5):
    return POSITIVE_LABEL if float(probability_parasitized) >= float(threshold) else NEGATIVE_LABEL


def confidence_level_from_probability(probability_parasitized):
    probability_parasitized = float(probability_parasitized)
    if probability_parasitized >= 0.80 or probability_parasitized <= 0.20:
        return "alta"
    if probability_parasitized >= 0.60 or probability_parasitized <= 0.40:
        return "media"
    return "baja"


def decision_from_probability(probability_parasitized, threshold=0.5):
    probability_parasitized = float(probability_parasitized)
    predicted_label = label_from_probability_parasitized(probability_parasitized, threshold)
    if 0.40 < probability_parasitized < 0.60:
        return "caso_incierto_requiere_revision"
    if predicted_label == POSITIVE_LABEL:
        return "compatible_con_celula_parasitada"
    return "compatible_con_celula_no_parasitada"


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
        "threshold": float(threshold),
        "confidence_level": confidence_level,
        "decision": decision,
        "human_readable_response": human_response_from_decision(
            decision,
            probability_parasitized,
        ),
        "recommendation": RECOMMENDATION,
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
