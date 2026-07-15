import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import tensorflow as tf


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models import build_densenet121_transfer  # noqa: E402


def tiny_backbone(include_top, weights, input_shape):
    del include_top, weights
    inputs = tf.keras.layers.Input(shape=input_shape)
    outputs = tf.keras.layers.Conv2D(4, 3, padding="same")(inputs)
    return tf.keras.Model(inputs, outputs, name="tiny_densenet121")


class DenseNetModelTests(unittest.TestCase):
    def test_builds_binary_transfer_model_without_downloading_weights(self):
        with patch("src.models.DenseNet121", side_effect=tiny_backbone) as builder:
            model, base_model = build_densenet121_transfer(
                input_shape=(32, 32, 3),
                weights=None,
            )

        builder.assert_called_once_with(
            include_top=False,
            weights=None,
            input_shape=(32, 32, 3),
        )
        self.assertEqual(model.name, "tl_densenet121_malaria")
        self.assertEqual(model.output_shape, (None, 1))
        self.assertEqual(model.layers[-1].activation.__name__, "sigmoid")
        self.assertTrue(all(not layer.trainable for layer in base_model.layers))

        normalized_rgb = np.asarray([[[[0.0, 0.5, 1.0]]]], dtype=np.float32)
        normalization = model.get_layer("densenet_imagenet_normalization")
        actual = normalization(normalized_rgb).numpy()
        expected = np.asarray(
            tf.keras.applications.densenet.preprocess_input(
                normalized_rgb * 255.0
            )
        )
        self.assertTrue(np.allclose(actual, expected, atol=1e-5))


if __name__ == "__main__":
    unittest.main()
