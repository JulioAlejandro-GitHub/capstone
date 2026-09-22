"""Count-derived binary metrics, with the project's zero_division=0 policy."""


def metrics_from_counts(tn: int, fp: int, fn: int, tp: int) -> dict[str, float]:
    def divide(a, b):
        return a / b if b else 0.0

    recall = divide(tp, tp + fn)
    specificity = divide(tn, tn + fp)
    return dict(recall=recall, specificity=specificity,
                precision=divide(tp, tp + fp), f1=divide(2 * tp, 2 * tp + fp + fn),
                f2=divide(5 * tp, 5 * tp + fp + 4 * fn),
                balanced_accuracy=(recall + specificity) / 2)
