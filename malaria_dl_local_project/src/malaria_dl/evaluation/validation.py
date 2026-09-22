"""Final selected-checkpoint VAL evaluation, shared by every TRAIN transport."""
import numpy as np

from .clinical_metrics import compute_clinical_metrics
from ..results.training import BinaryMetrics, ConfusionMatrix, ThresholdResult, ValidationEvaluationV1


def evaluate_validation_predictions(y_true, probabilities, threshold: ThresholdResult) -> ValidationEvaluationV1:
    labels = np.asarray(y_true)
    scores = np.asarray(probabilities)
    if (labels.ndim != 1 or scores.ndim != 1 or len(labels) != len(scores)
            or not len(labels) or not np.isin(labels, [0, 1]).all()
            or not np.isfinite(scores).all() or not ((scores >= 0) & (scores <= 1)).all()):
        raise ValueError("Invalid final validation predictions")
    if not isinstance(threshold, ThresholdResult):
        raise ValueError("Explicit effective threshold required")
    result = compute_clinical_metrics(labels, scores, threshold=threshold.value)
    return ValidationEvaluationV1(
        n_samples=len(labels), threshold=threshold,
        confusion_matrix=ConfusionMatrix(**{k: result[k] for k in ('tn', 'fp', 'fn', 'tp')}),
        metrics=BinaryMetrics(recall=result['recall_parasitized'], specificity=result['specificity'],
            precision=result['precision_parasitized'], f1=result['f1_parasitized'],
            f2=result['f2_parasitized'], balanced_accuracy=result['balanced_accuracy'],
            roc_auc=result['roc_auc_parasitized'], pr_auc=result['pr_auc_parasitized']),
    )
