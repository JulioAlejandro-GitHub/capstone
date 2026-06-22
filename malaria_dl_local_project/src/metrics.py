import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)

from src.config import (
    CLASS_NAMES,
    LABEL_MAPPING_VERSION,
    LEGACY_TFDS_LABEL_MAPPING_VERSION,
    NEGATIVE_LABEL,
    POSITIVE_LABEL,
    RAW_MODEL_SCORE_MEANING,
    label_mapping_metadata,
)
from src.decision import probability_by_class_from_scalar_score


def _safe_divide(numerator, denominator):
    denominator = float(denominator)
    if denominator == 0.0:
        return 0.0
    return float(numerator) / denominator


def _safe_roc_auc(y_true_binary, y_score):
    try:
        return float(roc_auc_score(y_true_binary, y_score))
    except ValueError:
        return None


def _label_index(class_names, label):
    if label not in class_names:
        raise ValueError(f"No existe la etiqueta {label!r} en class_names={class_names}")
    return int(class_names.index(label))


def clinical_probabilities_from_raw_scores(
    y_score,
    class_names=None,
    label_mapping_version=LABEL_MAPPING_VERSION,
):
    class_names = list(class_names or CLASS_NAMES)
    raw_model_score = np.asarray(y_score, dtype=np.float32).reshape(-1)
    probabilities = [
        probability_by_class_from_scalar_score(
            score,
            class_names,
            label_mapping_version=label_mapping_version,
        )
        for score in raw_model_score
    ]
    probability_parasitized = np.asarray(
        [item[POSITIVE_LABEL] for item in probabilities],
        dtype=np.float32,
    )
    probability_uninfected = np.asarray(
        [item[NEGATIVE_LABEL] for item in probabilities],
        dtype=np.float32,
    )
    return raw_model_score, probability_parasitized, probability_uninfected


def clinical_predictions_from_probabilities(
    probability_parasitized,
    class_names=None,
    threshold=0.5,
):
    class_names = list(class_names or CLASS_NAMES)
    positive_idx = _label_index(class_names, POSITIVE_LABEL)
    negative_idx = _label_index(class_names, NEGATIVE_LABEL)
    probability_parasitized = np.asarray(probability_parasitized, dtype=np.float32)
    return np.where(
        probability_parasitized >= float(threshold),
        positive_idx,
        negative_idx,
    ).astype(int)


def clinical_predictions_from_raw_scores(
    y_score,
    class_names=None,
    threshold=0.5,
    label_mapping_version=LABEL_MAPPING_VERSION,
):
    _, probability_parasitized, _ = clinical_probabilities_from_raw_scores(
        y_score,
        class_names,
        label_mapping_version=label_mapping_version,
    )
    return clinical_predictions_from_probabilities(
        probability_parasitized,
        class_names,
        threshold,
    )


def clinical_confusion_counts(y_true, y_pred, class_names=None):
    class_names = list(class_names or CLASS_NAMES)
    positive_idx = _label_index(class_names, POSITIVE_LABEL)
    negative_idx = _label_index(class_names, NEGATIVE_LABEL)
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)

    true_positive = int(np.sum((y_true == positive_idx) & (y_pred == positive_idx)))
    false_negative = int(np.sum((y_true == positive_idx) & (y_pred == negative_idx)))
    false_positive = int(np.sum((y_true == negative_idx) & (y_pred == positive_idx)))
    true_negative = int(np.sum((y_true == negative_idx) & (y_pred == negative_idx)))
    return {
        "true_positive": true_positive,
        "false_negative": false_negative,
        "false_positive": false_positive,
        "true_negative": true_negative,
    }


def clinical_metric_summary(y_true, y_pred, probability_parasitized, class_names=None):
    class_names = list(class_names or CLASS_NAMES)
    positive_idx = _label_index(class_names, POSITIVE_LABEL)
    y_true_positive = (np.asarray(y_true).astype(int) == positive_idx).astype(int)
    counts = clinical_confusion_counts(y_true, y_pred, class_names)

    sensitivity = _safe_divide(
        counts["true_positive"],
        counts["true_positive"] + counts["false_negative"],
    )
    specificity = _safe_divide(
        counts["true_negative"],
        counts["true_negative"] + counts["false_positive"],
    )
    false_negative_rate = _safe_divide(
        counts["false_negative"],
        counts["true_positive"] + counts["false_negative"],
    )
    false_positive_rate = _safe_divide(
        counts["false_positive"],
        counts["true_negative"] + counts["false_positive"],
    )

    return {
        **counts,
        "sensitivity_parasitized": sensitivity,
        "recall_parasitized": sensitivity,
        "specificity": specificity,
        "false_negative_rate": false_negative_rate,
        "false_positive_rate": false_positive_rate,
        "balanced_accuracy": float((sensitivity + specificity) / 2.0),
        "auc_parasitized": _safe_roc_auc(y_true_positive, probability_parasitized),
    }


def detect_prediction_collapse(y_pred, class_names=None, min_class_fraction=0.05) -> dict:
    """
    Detecta predicciones concentradas en una sola clase o bajo el mínimo esperado.

    Convención clínica:
      0 = uninfected
      1 = parasitized
    """
    class_names = list(class_names or CLASS_NAMES)
    negative_idx = _label_index(class_names, NEGATIVE_LABEL)
    positive_idx = _label_index(class_names, POSITIVE_LABEL)
    y_pred = np.asarray(y_pred).astype(int).reshape(-1)
    total = int(len(y_pred))

    n_pred_uninfected = int(np.sum(y_pred == negative_idx))
    n_pred_parasitized = int(np.sum(y_pred == positive_idx))
    percent_pred_uninfected = _safe_divide(n_pred_uninfected, total)
    percent_pred_parasitized = _safe_divide(n_pred_parasitized, total)

    predicted_classes = [
        class_names[index]
        for index, count in (
            (negative_idx, n_pred_uninfected),
            (positive_idx, n_pred_parasitized),
        )
        if count > 0
    ]
    fractions = [percent_pred_uninfected, percent_pred_parasitized]
    collapsed = total > 0 and (
        len(predicted_classes) == 1
        or any(fraction < float(min_class_fraction) for fraction in fractions)
    )
    warning = None
    if total == 0:
        warning = "No hay predicciones para evaluar colapso."
    elif len(predicted_classes) == 1:
        warning = "El modelo predijo solo una clase."
    elif collapsed:
        warning = (
            "Distribución de predicciones fuertemente desbalanceada. "
            "Posible colapso de entrenamiento."
        )

    return {
        "collapsed": bool(collapsed),
        "predicted_classes": predicted_classes,
        "n_pred_uninfected": n_pred_uninfected,
        "n_pred_parasitized": n_pred_parasitized,
        "percent_pred_uninfected": float(percent_pred_uninfected),
        "percent_pred_parasitized": float(percent_pred_parasitized),
        "min_class_fraction": float(min_class_fraction),
        "warning": warning,
    }


def collect_predictions(
    model,
    dataset,
    class_names=None,
    threshold=0.5,
    label_mapping_version=LABEL_MAPPING_VERSION,
):
    from src.inference_pipeline import probability_rows_from_predictions

    y_true = []
    y_score = []

    for images, labels in dataset:
        predictions = model.predict(images, verbose=0)
        prediction_array = np.asarray(predictions, dtype=np.float32)
        if prediction_array.ndim == 2 and prediction_array.shape[1] == len(CLASS_NAMES):
            probability_rows = probability_rows_from_predictions(
                predictions,
                label_mapping_version=label_mapping_version,
            )
            y_score.extend([row[POSITIVE_LABEL] for row in probability_rows])
        else:
            y_score.extend(prediction_array.reshape(-1))
        y_true.extend(labels.numpy())

    y_true = np.asarray(y_true).astype(int)
    y_score = np.asarray(y_score)
    y_pred = clinical_predictions_from_raw_scores(
        y_score,
        class_names or CLASS_NAMES,
        threshold,
        label_mapping_version=label_mapping_version,
    )

    return y_true, y_pred, y_score


def evaluate_binary_predictions(
    y_true,
    y_pred,
    y_score,
    class_names,
    output_dir=None,
    prefix="test",
    threshold=0.5,
    positive_label=POSITIVE_LABEL,
    label_mapping_version=LABEL_MAPPING_VERSION,
    metadata=None,
):
    if positive_label != POSITIVE_LABEL:
        raise ValueError(
            f"Este pipeline clínico usa {POSITIVE_LABEL!r} como clase positiva."
        )

    class_names = list(class_names)
    metadata = dict(metadata or {})
    y_true = np.asarray(y_true).astype(int)
    raw_input_y_pred = np.asarray(y_pred).astype(int)
    raw_model_score, probability_parasitized, probability_uninfected = (
        clinical_probabilities_from_raw_scores(
            y_score,
            class_names,
            label_mapping_version=label_mapping_version,
        )
    )
    y_pred = clinical_predictions_from_probabilities(
        probability_parasitized,
        class_names,
        threshold,
    )
    positive_idx = _label_index(class_names, POSITIVE_LABEL)
    negative_idx = _label_index(class_names, NEGATIVE_LABEL)
    if label_mapping_version == LEGACY_TFDS_LABEL_MAPPING_VERSION:
        raw_model_y_pred = np.where(
            raw_model_score >= float(threshold),
            negative_idx,
            positive_idx,
        ).astype(int)
    else:
        raw_model_y_pred = np.where(
            raw_model_score >= float(threshold),
            positive_idx,
            negative_idx,
        ).astype(int)

    report_text = classification_report(
        y_true,
        y_pred,
        labels=list(range(len(class_names))),
        target_names=class_names,
        digits=4,
        zero_division=0,
    )
    report_dict = classification_report(
        y_true,
        y_pred,
        labels=list(range(len(class_names))),
        target_names=class_names,
        digits=4,
        output_dict=True,
        zero_division=0,
    )

    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(class_names))))
    clinical_summary = clinical_metric_summary(
        y_true,
        y_pred,
        probability_parasitized,
        class_names,
    )
    collapse_summary = detect_prediction_collapse(y_pred, class_names)
    auc = clinical_summary["auc_parasitized"]
    mapping_metadata = label_mapping_metadata(label_mapping_version)
    raw_model_score_meaning = mapping_metadata["raw_model_score_meaning"]
    raw_model_score_label = (
        POSITIVE_LABEL
        if raw_model_score_meaning == RAW_MODEL_SCORE_MEANING
        else NEGATIVE_LABEL
    )
    raw_model_auc_parasitized = _safe_roc_auc(
        (y_true == positive_idx).astype(int),
        probability_parasitized,
    )
    y_pred_positive = (y_pred == positive_idx).astype(int)
    y_true_positive = (y_true == positive_idx).astype(int)

    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "precision_parasitized": float(
            precision_score(y_true_positive, y_pred_positive, zero_division=0)
        ),
        "f1_parasitized": float(
            f1_score(y_true_positive, y_pred_positive, zero_division=0)
        ),
        "auc": auc,
        "auc_parasitized": auc,
        "raw_model_auc_parasitized": raw_model_auc_parasitized,
        "clinical_positive_label": POSITIVE_LABEL,
        "clinical_negative_label": NEGATIVE_LABEL,
        "positive_class": POSITIVE_LABEL,
        "negative_class": NEGATIVE_LABEL,
        "positive_class_index": positive_idx,
        "negative_class_index": negative_idx,
        "raw_model_score_label": raw_model_score_label,
        "raw_model_score_meaning": raw_model_score_meaning,
        "label_mapping_version": label_mapping_version,
        "label_mapping": mapping_metadata,
        "threshold": float(threshold),
        "preprocessing_mode": metadata.get("preprocessing_mode"),
        "metadata": metadata,
        "confusion_matrix": cm.tolist(),
        "raw_model_confusion_matrix": confusion_matrix(
            y_true,
            raw_model_y_pred,
            labels=list(range(len(class_names))),
        ).tolist(),
        "classification_report": report_text,
        "classification_report_dict": report_dict,
        "prediction_distribution": {
            "n_pred_uninfected": collapse_summary["n_pred_uninfected"],
            "n_pred_parasitized": collapse_summary["n_pred_parasitized"],
            "percent_pred_uninfected": collapse_summary["percent_pred_uninfected"],
            "percent_pred_parasitized": collapse_summary["percent_pred_parasitized"],
        },
        "prediction_collapse": collapse_summary,
        "prediction_collapse_detected": bool(collapse_summary["collapsed"]),
        "n_pred_uninfected": collapse_summary["n_pred_uninfected"],
        "n_pred_parasitized": collapse_summary["n_pred_parasitized"],
        "percent_pred_uninfected": collapse_summary["percent_pred_uninfected"],
        "percent_pred_parasitized": collapse_summary["percent_pred_parasitized"],
        **clinical_summary,
    }

    print(f"Clase positiva clínica: {POSITIVE_LABEL}")
    print(report_text)
    print("Confusion matrix clínica:")
    print(cm)
    print(f"AUC parasitized: {auc:.4f}" if auc is not None else "AUC parasitized: no disponible")
    print(
        "Sensibilidad parasitized: "
        f"{metrics['sensitivity_parasitized']:.4f} | "
        f"Especificidad: {metrics['specificity']:.4f} | "
        f"Balanced accuracy: {metrics['balanced_accuracy']:.4f}"
    )
    print("Distribución de predicciones:")
    print(f"pred_uninfected: {metrics['n_pred_uninfected']}")
    print(f"pred_parasitized: {metrics['n_pred_parasitized']}")
    if collapse_summary["warning"]:
        print(f"WARNING: {collapse_summary['warning']}")
        if collapse_summary["collapsed"]:
            print(
                "WARNING: No usar este checkpoint como modelo clínico experimental "
                "sin reentrenamiento o revisión."
            )

    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir / f"{prefix}_metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

        pd.DataFrame(cm).to_csv(output_dir / f"{prefix}_confusion_matrix.csv", index=False)

        pred_df = pd.DataFrame(
            {
                "y_true": y_true,
                "y_pred": y_pred,
                "y_score": raw_model_score,
                "raw_model_score": raw_model_score,
                "raw_model_score_meaning": raw_model_score_meaning,
                "raw_model_pred_class_index": raw_model_y_pred,
                "input_y_pred": raw_input_y_pred,
                "probability_parasitized": probability_parasitized,
                "probability_uninfected": probability_uninfected,
                "positive_label": POSITIVE_LABEL,
                "negative_label": NEGATIVE_LABEL,
                "positive_class_name": POSITIVE_LABEL,
                "positive_class_index": positive_idx,
                "negative_class_name": NEGATIVE_LABEL,
                "negative_class_index": negative_idx,
                "label_mapping_version": label_mapping_version,
            }
        )
        if metadata.get("preprocessing_mode") is not None:
            pred_df["preprocessing_mode"] = metadata["preprocessing_mode"]
        pred_df["true_label"] = [class_names[int(index)] for index in y_true]
        pred_df["predicted_label"] = [class_names[int(index)] for index in y_pred]
        pred_df["raw_model_predicted_label"] = [
            class_names[int(index)] for index in raw_model_y_pred
        ]
        pred_df.to_csv(output_dir / f"{prefix}_predictions.csv", index=False)

    return metrics


def evaluate_keras_model(
    model,
    dataset,
    class_names,
    output_dir=None,
    prefix="test",
    threshold=0.5,
    label_mapping_version=LABEL_MAPPING_VERSION,
    metadata=None,
):
    y_true, y_pred, y_score = collect_predictions(
        model,
        dataset,
        class_names=class_names,
        threshold=threshold,
        label_mapping_version=label_mapping_version,
    )
    return evaluate_binary_predictions(
        y_true=y_true,
        y_pred=y_pred,
        y_score=y_score,
        class_names=class_names,
        output_dir=output_dir,
        prefix=prefix,
        threshold=threshold,
        label_mapping_version=label_mapping_version,
        metadata=metadata,
    )
