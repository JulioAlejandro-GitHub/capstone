import sys
import unittest
from pathlib import Path

import tensorflow as tf


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.checkpoint_policy import ClinicalValidationMetricsCallback


def _sigmoid_identity_model():
    inputs = tf.keras.Input(shape=(1,))
    outputs = tf.keras.layers.Activation("sigmoid")(inputs)
    return tf.keras.Model(inputs, outputs)


class ClinicalValidationMetricsCallbackTests(unittest.TestCase):
    def test_callback_adds_clinical_validation_metrics_to_logs(self):
        model = _sigmoid_identity_model()
        x = tf.constant([[-4.0], [4.0], [-3.0], [3.0]], dtype=tf.float32)
        y = tf.constant([0, 1, 0, 1], dtype=tf.int32)
        validation_data = tf.data.Dataset.from_tensor_slices((x, y)).batch(2)
        callback = ClinicalValidationMetricsCallback(validation_data=validation_data)
        callback.set_model(model)

        logs = {}
        callback.on_epoch_end(0, logs)

        self.assertAlmostEqual(logs["val_recall_parasitized"], 1.0)
        self.assertAlmostEqual(logs["val_sensitivity_parasitized"], 1.0)
        self.assertAlmostEqual(logs["val_specificity"], 1.0)
        self.assertAlmostEqual(logs["val_f2_parasitized"], 1.0)
        self.assertAlmostEqual(logs["val_balanced_accuracy"], 1.0)
        self.assertAlmostEqual(logs["val_prediction_collapse_detected"], 0.0)

    def test_callback_detects_validation_prediction_collapse(self):
        model = _sigmoid_identity_model()
        x = tf.constant([[4.0], [4.0], [4.0], [4.0]], dtype=tf.float32)
        y = tf.constant([0, 1, 0, 1], dtype=tf.int32)
        validation_data = tf.data.Dataset.from_tensor_slices((x, y)).batch(2)
        callback = ClinicalValidationMetricsCallback(validation_data=validation_data)
        callback.set_model(model)

        logs = {}
        callback.on_epoch_end(0, logs)

        self.assertAlmostEqual(logs["val_recall_parasitized"], 1.0)
        self.assertAlmostEqual(logs["val_specificity"], 0.0)
        self.assertAlmostEqual(logs["val_prediction_collapse_detected"], 1.0)
        self.assertEqual(logs["val_n_pred_uninfected"], 0.0)
        self.assertEqual(logs["val_n_pred_parasitized"], 4.0)


if __name__ == "__main__":
    unittest.main()
