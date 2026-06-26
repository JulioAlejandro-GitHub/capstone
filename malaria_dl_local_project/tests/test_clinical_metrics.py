import sys
from pathlib import Path

from sklearn.metrics import average_precision_score, fbeta_score


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import CLASS_NAMES, POSITIVE_CLASS_INDEX, POSITIVE_LABEL
from src.metrics import compute_clinical_metrics, detect_prediction_collapse


def test_label_mapping_is_clinical():
    assert CLASS_NAMES == ["uninfected", "parasitized"]
    assert POSITIVE_CLASS_INDEX == 1
    assert POSITIVE_LABEL == "parasitized"


def test_confusion_matrix_values_clinical_order():
    y_true = [0, 0, 1, 1]
    y_scores = [0.10, 0.80, 0.20, 0.90]

    metrics = compute_clinical_metrics(y_true, y_scores, threshold=0.5)

    assert metrics["confusion_matrix"] == [[1, 1], [1, 1]]
    assert metrics["tn"] == 1
    assert metrics["fp"] == 1
    assert metrics["fn"] == 1
    assert metrics["tp"] == 1
    assert metrics["confusion_matrix_labels"] == ["uninfected", "parasitized"]


def test_f2_score_prioritizes_recall_for_parasitized():
    y_true = [0, 0, 1, 1, 1]
    y_scores = [0.10, 0.80, 0.20, 0.90, 0.30]
    y_pred = [0, 1, 0, 1, 0]

    metrics = compute_clinical_metrics(y_true, y_scores, threshold=0.5)
    expected = fbeta_score(
        y_true,
        y_pred,
        beta=2.0,
        pos_label=1,
        zero_division=0,
    )

    assert metrics["positive_class_index"] == 1
    assert metrics["f2_parasitized"] == expected


def test_pr_auc_uses_probability_parasitized():
    y_true = [0, 0, 1, 1]
    probability_parasitized = [0.10, 0.80, 0.20, 0.90]
    probability_uninfected = [1.0 - score for score in probability_parasitized]

    metrics = compute_clinical_metrics(
        y_true,
        probability_parasitized,
        threshold=0.5,
    )

    assert metrics["pr_auc_parasitized"] == average_precision_score(
        y_true,
        probability_parasitized,
    )
    assert metrics["pr_auc_parasitized"] != average_precision_score(
        y_true,
        probability_uninfected,
    )


def test_prediction_collapse_all_parasitized():
    result = detect_prediction_collapse([1, 1, 1, 1])

    assert result["collapsed"] is True
    assert result["collapse_type"] == "all_parasitized"


def test_prediction_collapse_all_uninfected():
    result = detect_prediction_collapse([0, 0, 0, 0])

    assert result["collapsed"] is True
    assert result["collapse_type"] == "all_uninfected"
