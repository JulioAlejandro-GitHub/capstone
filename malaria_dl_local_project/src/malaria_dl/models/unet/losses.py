"""Dice loss (training) and per-image segmentation metrics (evaluation).

Training loss, batch-level soft Dice:

    D = (2 * sum_b,i(y * p) + eps) / (sum_b,i(y) + sum_b,i(p) + eps)
    L = 1 - D

Sums run over every pixel of every image in the batch; y in {0,1} is the
pseudo-mask and p in [0,1] the sigmoid output; eps = 1.0 (one pixel).
Empty targets add nothing to the numerator or to sum(y), but every
probability they predict adds to sum(p): false positives on empty
targets are penalised, and an empty target never earns a "free" Dice of 1.
eps = 1 pixel is negligible next to the ~390 foreground pixels of a typical
non-empty 200x200 target; it only keeps D defined when the whole batch has
empty targets and near-zero predictions (then L -> 0).

Evaluation (numpy, hard masks at threshold 0.5), see segmentation_report.
"""

import numpy as np
import tensorflow as tf


@tf.keras.utils.register_keras_serializable(package="malaria_unet")
class DiceLoss(tf.keras.losses.Loss):
    def __init__(self, epsilon=1.0, name="dice_loss", **kwargs):
        super().__init__(name=name, **kwargs)
        self.epsilon = float(epsilon)

    def call(self, y_true, y_pred):
        y_true = tf.cast(y_true, y_pred.dtype)
        intersection = tf.reduce_sum(y_true * y_pred)
        total = tf.reduce_sum(y_true) + tf.reduce_sum(y_pred)
        dice = (2.0 * intersection + self.epsilon) / (total + self.epsilon)
        # Keras applies sample reduction to the returned value; a scalar per batch
        # is broadcast so the reduced loss equals 1 - D exactly.
        return tf.fill(tf.shape(y_true)[:1], 1.0 - dice)

    def get_config(self):
        return {**super().get_config(), "epsilon": self.epsilon}


PREDICTION_THRESHOLD = 0.5


def binarize(probabilities, threshold=PREDICTION_THRESHOLD):
    return np.asarray(probabilities) >= threshold


def per_image_overlap(target, predicted):
    """Hard Dice and IoU per image. target, predicted: bool arrays (N, H, W[, 1])."""
    t = target.reshape(len(target), -1)
    p = predicted.reshape(len(predicted), -1)
    inter = np.logical_and(t, p).sum(1)
    t_sum, p_sum = t.sum(1), p.sum(1)
    union = t_sum + p_sum - inter
    both_empty = (t_sum == 0) & (p_sum == 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        dice = np.where(both_empty, 1.0, 2 * inter / (t_sum + p_sum))
        iou = np.where(both_empty, 1.0, inter / union)
    return dice, iou, t_sum, p_sum


def segmentation_report(target, predicted):
    """Metrics split into ALL / EMPTY TARGET / NON-EMPTY TARGET.

    Conventions:
    - predicted_empty: 0 foreground pixels after thresholding at 0.5.
    - Per-image Dice/IoU; an image with empty target AND empty prediction scores 1.
      For empty targets per-image Dice equals 1 iff the prediction is empty, so the
      EMPTY subset is reported as counts, not as Dice.
    - Pooled (micro) Dice/IoU over all pixels is reported alongside, because it
      cannot be inflated by agreeing on empty images.
    """
    target, predicted = np.asarray(target, bool), np.asarray(predicted, bool)
    dice, iou, t_sum, p_sum = per_image_overlap(target, predicted)
    empty_t, empty_p = t_sum == 0, p_sum == 0
    nonempty_t = ~empty_t
    inter_all = np.logical_and(target, predicted).sum()
    t_all, p_all = target.sum(), predicted.sum()
    return {
        "images": int(len(target)),
        "dice_all": float(dice.mean()),
        "iou_all": float(iou.mean()),
        "dice_nonempty": float(dice[nonempty_t].mean()) if nonempty_t.any() else None,
        "iou_nonempty": float(iou[nonempty_t].mean()) if nonempty_t.any() else None,
        "dice_nonempty_median": float(np.median(dice[nonempty_t])) if nonempty_t.any() else None,
        "dice_pooled_pixels": float(2 * inter_all / (t_all + p_all)) if (t_all + p_all) else 1.0,
        "iou_pooled_pixels": float(inter_all / (t_all + p_all - inter_all)) if (t_all + p_all) else 1.0,
        "target_empty_count": int(empty_t.sum()),
        "target_nonempty_count": int(nonempty_t.sum()),
        "predicted_empty_count": int(empty_p.sum()),
        "empty_target_correct_empty": int((empty_t & empty_p).sum()),
        "empty_target_false_positive": int((empty_t & ~empty_p).sum()),
        "nonempty_target_predicted_empty": int((nonempty_t & empty_p).sum()),
        "nonempty_target_zero_overlap": int((nonempty_t & (dice == 0)).sum()),
    }
