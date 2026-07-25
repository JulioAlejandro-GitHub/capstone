import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    average_precision_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    fbeta_score,
)

from src.config import (
    CLASS_NAMES,
    LABEL_MAPPING_VERSION,
    LEGACY_TFDS_LABEL_MAPPING_VERSION,
    NEGATIVE_CLASS_INDEX,
    NEGATIVE_LABEL,
    POSITIVE_CLASS_INDEX,
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
    y_true_binary = np.asarray(y_true_binary).astype(int).reshape(-1)
    y_score = np.asarray(y_score, dtype=np.float32).reshape(-1)
    if len(np.unique(y_true_binary)) < 2:
        return None
    try:
        return float(roc_auc_score(y_true_binary, y_score))
    except ValueError:
        return None


def _safe_pr_auc(y_true_binary, y_score):
    y_true_binary = np.asarray(y_true_binary).astype(int).reshape(-1)
    y_score = np.asarray(y_score, dtype=np.float32).reshape(-1)
    if len(np.unique(y_true_binary)) < 2:
        return None
    try:
        return float(average_precision_score(y_true_binary, y_score))
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


def compute_prediction_distribution(y_pred, class_names=None) -> dict:
    """
    Resume la distribución de predicciones con la convención clínica oficial.

    Convención:
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

    return {
        "n_pred_uninfected": n_pred_uninfected,
        "n_pred_parasitized": n_pred_parasitized,
        "percent_pred_uninfected": float(_safe_divide(n_pred_uninfected, total)),
        "percent_pred_parasitized": float(_safe_divide(n_pred_parasitized, total)),
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
    distribution = compute_prediction_distribution(y_pred, class_names)
    n_pred_uninfected = distribution["n_pred_uninfected"]
    n_pred_parasitized = distribution["n_pred_parasitized"]
    percent_pred_uninfected = distribution["percent_pred_uninfected"]
    percent_pred_parasitized = distribution["percent_pred_parasitized"]

    predicted_classes = [
        class_names[index]
        for index, count in (
            (negative_idx, n_pred_uninfected),
            (positive_idx, n_pred_parasitized),
        )
        if count > 0
    ]

    collapsed = False
    collapse_type = None
    warning = None

    if total == 0:
        warning = "No hay predicciones para evaluar colapso."
    elif n_pred_uninfected == 0:
        collapsed = True
        collapse_type = "all_parasitized"
    elif n_pred_parasitized == 0:
        collapsed = True
        collapse_type = "all_uninfected"
    elif percent_pred_uninfected < float(min_class_fraction):
        collapsed = True
        collapse_type = "low_fraction_uninfected"
    elif percent_pred_parasitized < float(min_class_fraction):
        collapsed = True
        collapse_type = "low_fraction_parasitized"

    if collapsed:
        warning = "El modelo predijo solo una clase o casi una sola clase."

    return {
        "collapsed": bool(collapsed),
        "collapse_type": collapse_type,
        "predicted_classes": predicted_classes,
        "n_pred_uninfected": n_pred_uninfected,
        "n_pred_parasitized": n_pred_parasitized,
        "percent_pred_uninfected": float(percent_pred_uninfected),
        "percent_pred_parasitized": float(percent_pred_parasitized),
        "min_class_fraction": float(min_class_fraction),
        "warning": warning,
    }


def compute_clinical_metrics(y_true, y_scores, threshold: float = 0.5) -> dict:
    """
    Calcula métricas clínicas para clasificación binaria de malaria.

    Convención:
    0 = uninfected
    1 = parasitized

    y_scores debe representar probability_parasitized.
    """
    y_true = np.asarray(y_true).astype(int).reshape(-1)
    probability_parasitized = np.asarray(y_scores, dtype=np.float32).reshape(-1)
    if len(y_true) != len(probability_parasitized):
        raise ValueError(
            "y_true y y_scores deben tener el mismo largo. "
            f"Recibido: {len(y_true)} y {len(probability_parasitized)}."
        )

    class_names = list(CLASS_NAMES)
    negative_idx = NEGATIVE_CLASS_INDEX
    positive_idx = POSITIVE_CLASS_INDEX
    y_pred = clinical_predictions_from_probabilities(
        probability_parasitized,
        class_names=class_names,
        threshold=threshold,
    )

    cm = confusion_matrix(y_true, y_pred, labels=[negative_idx, positive_idx])
    tn, fp, fn, tp = [int(value) for value in cm.ravel()]
    y_true_positive = (y_true == positive_idx).astype(int)

    sensitivity = _safe_divide(tp, tp + fn)
    specificity = _safe_divide(tn, tn + fp)
    prediction_distribution = compute_prediction_distribution(y_pred, class_names)
    collapse_summary = detect_prediction_collapse(y_pred, class_names)
    report_text = classification_report(
        y_true,
        y_pred,
        labels=[negative_idx, positive_idx],
        target_names=class_names,
        digits=4,
        zero_division=0,
    )
    report_dict = classification_report(
        y_true,
        y_pred,
        labels=[negative_idx, positive_idx],
        target_names=class_names,
        digits=4,
        output_dict=True,
        zero_division=0,
    )
    roc_auc = _safe_roc_auc(y_true_positive, probability_parasitized)
    pr_auc = _safe_pr_auc(y_true_positive, probability_parasitized)

    metrics = {
        "label_mapping_version": LABEL_MAPPING_VERSION,
        "negative_class_name": NEGATIVE_LABEL,
        "negative_class_index": negative_idx,
        "positive_class_name": POSITIVE_LABEL,
        "positive_class_index": positive_idx,
        "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_parasitized": float(
            precision_score(
                y_true,
                y_pred,
                pos_label=positive_idx,
                zero_division=0,
            )
        ),
        "recall_parasitized": float(sensitivity),
        "sensitivity_parasitized": float(sensitivity),
        "specificity": float(specificity),
        "f1_parasitized": float(
            f1_score(
                y_true,
                y_pred,
                pos_label=positive_idx,
                zero_division=0,
            )
        ),
        "f2_parasitized": float(
            fbeta_score(
                y_true,
                y_pred,
                beta=2.0,
                pos_label=positive_idx,
                zero_division=0,
            )
        ),
        "roc_auc_parasitized": roc_auc,
        "pr_auc_parasitized": pr_auc,
        "balanced_accuracy": float((sensitivity + specificity) / 2.0),
        "confusion_matrix": cm.tolist(),
        "confusion_matrix_labels": class_names,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "false_positives": fp,
        "false_negatives": fn,
        "true_positive": tp,
        "classification_report": report_text,
        "classification_report_dict": report_dict,
        "prediction_distribution": prediction_distribution,
        "prediction_collapse": collapse_summary,
        "prediction_collapse_detected": bool(collapse_summary["collapsed"]),
        "n_pred_uninfected": prediction_distribution["n_pred_uninfected"],
        "n_pred_parasitized": prediction_distribution["n_pred_parasitized"],
        "percent_pred_uninfected": prediction_distribution["percent_pred_uninfected"],
        "percent_pred_parasitized": prediction_distribution["percent_pred_parasitized"],
        "false_negative_rate": float(_safe_divide(fn, tp + fn)),
        "false_positive_rate": float(_safe_divide(fp, tn + fp)),
    }
    metrics["auc"] = metrics["roc_auc_parasitized"]
    metrics["roc_auc"] = metrics["roc_auc_parasitized"]
    metrics["pr_auc"] = metrics["pr_auc_parasitized"]
    metrics["auc_parasitized"] = metrics["roc_auc_parasitized"]
    metrics["average_precision_parasitized"] = metrics["pr_auc_parasitized"]
    metrics["clinical_positive_label"] = POSITIVE_LABEL
    metrics["clinical_negative_label"] = NEGATIVE_LABEL
    metrics["positive_class"] = POSITIVE_LABEL
    metrics["negative_class"] = NEGATIVE_LABEL
    return metrics


def clinical_metric_summary(y_true, y_pred, probability_parasitized, class_names=None):
    class_names = list(class_names or CLASS_NAMES)
    positive_idx = _label_index(class_names, POSITIVE_LABEL)
    y_true = np.asarray(y_true).astype(int).reshape(-1)
    y_pred = np.asarray(y_pred).astype(int).reshape(-1)
    probability_parasitized = np.asarray(probability_parasitized, dtype=np.float32).reshape(-1)
    y_true_positive = (y_true == positive_idx).astype(int)
    counts = clinical_confusion_counts(y_true, y_pred, class_names)

    sensitivity = _safe_divide(
        counts["true_positive"],
        counts["true_positive"] + counts["false_negative"],
    )
    specificity = _safe_divide(
        counts["true_negative"],
        counts["true_negative"] + counts["false_positive"],
    )
    clinical_metrics = {
        **counts,
        "sensitivity_parasitized": sensitivity,
        "recall_parasitized": sensitivity,
        "specificity": specificity,
        "false_negative_rate": _safe_divide(
            counts["false_negative"],
            counts["true_positive"] + counts["false_negative"],
        ),
        "false_positive_rate": _safe_divide(
            counts["false_positive"],
            counts["true_negative"] + counts["false_positive"],
        ),
        "balanced_accuracy": float((sensitivity + specificity) / 2.0),
        "auc_parasitized": _safe_roc_auc(y_true_positive, probability_parasitized),
        "roc_auc_parasitized": _safe_roc_auc(y_true_positive, probability_parasitized),
        "pr_auc_parasitized": _safe_pr_auc(y_true_positive, probability_parasitized),
        "f2_parasitized": float(
            fbeta_score(
                y_true,
                y_pred,
                beta=2.0,
                pos_label=positive_idx,
                zero_division=0,
            )
        ),
    }
    return {
        key: clinical_metrics[key]
        for key in (
            "true_positive",
            "false_negative",
            "false_positive",
            "true_negative",
            "sensitivity_parasitized",
            "recall_parasitized",
            "specificity",
            "false_negative_rate",
            "false_positive_rate",
            "balanced_accuracy",
            "auc_parasitized",
            "roc_auc_parasitized",
            "pr_auc_parasitized",
            "f2_parasitized",
        )
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

    clinical_metrics = compute_clinical_metrics(
        y_true,
        probability_parasitized,
        threshold=threshold,
    )
    report_text = clinical_metrics["classification_report"]
    report_dict = clinical_metrics["classification_report_dict"]
    cm = np.asarray(clinical_metrics["confusion_matrix"], dtype=int)
    collapse_summary = detect_prediction_collapse(y_pred, class_names)
    roc_auc = clinical_metrics["roc_auc_parasitized"]
    pr_auc = clinical_metrics["pr_auc_parasitized"]
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

    metrics = {
        **clinical_metrics,
        "evaluation_split": metadata.get("evaluation_split"),
        "threshold_used": float(threshold),
        "threshold_source": metadata.get("threshold_source", "fixed_cli"),
        "threshold_mode": metadata.get("threshold_mode", "fixed"),
        "target_recall": metadata.get("target_recall"),
        "target_recall_satisfied_on_validation": metadata.get(
            "target_recall_satisfied_on_validation"
        ),
        "clinical_threshold": metadata.get("clinical_threshold"),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "raw_model_auc_parasitized": raw_model_auc_parasitized,
        "raw_model_score_label": raw_model_score_label,
        "raw_model_score_meaning": raw_model_score_meaning,
        "label_mapping_version": label_mapping_version,
        "label_mapping": mapping_metadata,
        "preprocessing_mode": metadata.get("preprocessing_mode"),
        "metadata": metadata,
        "raw_model_confusion_matrix": confusion_matrix(
            y_true,
            raw_model_y_pred,
            labels=list(range(len(class_names))),
        ).tolist(),
    }
    metrics["metrics"] = {
        key: metrics.get(key)
        for key in (
            "accuracy",
            "precision_parasitized",
            "recall_parasitized",
            "sensitivity_parasitized",
            "specificity",
            "f1_parasitized",
            "f2_parasitized",
            "roc_auc_parasitized",
            "pr_auc_parasitized",
            "balanced_accuracy",
            "prediction_collapse_detected",
        )
    }

    print(f"Clase positiva clínica: {POSITIVE_LABEL}")
    print(f"raw_model_score: {raw_model_score_meaning}")
    if raw_model_score_meaning != RAW_MODEL_SCORE_MEANING:
        print(f"score clínico usado en métricas: {RAW_MODEL_SCORE_MEANING}")
    print(report_text)
    print("Confusion matrix clínica:")
    print(cm)
    print("Métricas clínicas:")
    print(f"- accuracy: {metrics['accuracy']:.4f}")
    print(f"- precision_parasitized: {metrics['precision_parasitized']:.4f}")
    print(
        "- recall_parasitized / sensibilidad: "
        f"{metrics['recall_parasitized']:.4f}"
    )
    print(f"- specificity: {metrics['specificity']:.4f}")
    print(f"- f1_parasitized: {metrics['f1_parasitized']:.4f}")
    print(f"- f2_parasitized: {metrics['f2_parasitized']:.4f}")
    print(
        "- ROC-AUC parasitized: "
        f"{roc_auc:.4f}" if roc_auc is not None else "- ROC-AUC parasitized: no disponible"
    )
    print(
        "- PR-AUC parasitized: "
        f"{pr_auc:.4f}" if pr_auc is not None else "- PR-AUC parasitized: no disponible"
    )
    print(f"- balanced_accuracy: {metrics['balanced_accuracy']:.4f}")
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
                "threshold": float(threshold),
                "threshold_source": metadata.get("threshold_source", "fixed_cli"),
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
