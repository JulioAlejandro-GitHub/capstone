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


def collect_predictions(model, dataset):
    y_true = []
    y_score = []

    for images, labels in dataset:
        probs = model.predict(images, verbose=0).ravel()
        y_score.extend(probs)
        y_true.extend(labels.numpy())

    y_true = np.asarray(y_true).astype(int)
    y_score = np.asarray(y_score)
    y_pred = (y_score >= 0.5).astype(int)

    return y_true, y_pred, y_score


def evaluate_binary_predictions(
    y_true,
    y_pred,
    y_score,
    class_names,
    output_dir=None,
    prefix="test",
):
    report_text = classification_report(
        y_true,
        y_pred,
        target_names=class_names,
        digits=4,
    )
    report_dict = classification_report(
        y_true,
        y_pred,
        target_names=class_names,
        digits=4,
        output_dict=True,
        zero_division=0,
    )

    cm = confusion_matrix(y_true, y_pred)
    auc = roc_auc_score(y_true, y_score)

    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "auc": float(auc),
        "confusion_matrix": cm.tolist(),
        "classification_report": report_text,
        "classification_report_dict": report_dict,
    }

    print(report_text)
    print("Confusion matrix:")
    print(cm)
    print(f"AUC: {auc:.4f}")

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
                "y_score": y_score,
            }
        )
        pred_df.to_csv(output_dir / f"{prefix}_predictions.csv", index=False)

    return metrics


def evaluate_keras_model(model, dataset, class_names, output_dir=None, prefix="test"):
    y_true, y_pred, y_score = collect_predictions(model, dataset)
    return evaluate_binary_predictions(
        y_true=y_true,
        y_pred=y_pred,
        y_score=y_score,
        class_names=class_names,
        output_dir=output_dir,
        prefix=prefix,
    )
