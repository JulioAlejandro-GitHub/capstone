import math
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import tensorflow as tf

    from src.predict_image import run_clinical_inference
except Exception as exc:  # pragma: no cover - exercised only when local env lacks TF.
    tf = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


def create_checkerboard_image(path, size=80):
    grid = np.indices((size, size)).sum(axis=0) % 2
    red = np.where(grid == 0, 220, 80)
    green = np.where(grid == 0, 70, 190)
    blue = np.where(grid == 0, 90, 210)
    image = np.stack([red, green, blue], axis=-1).astype(np.uint8)
    Image.fromarray(image, mode="RGB").save(path)


@unittest.skipIf(tf is None, f"TensorFlow no disponible: {IMPORT_ERROR}")
class MinimalKerasInferenceTests(unittest.TestCase):
    def test_run_clinical_inference_with_minimal_keras_model(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            checkpoint = temp_path / "minimal_model.keras"
            image_path = temp_path / "input.png"
            create_checkerboard_image(image_path)

            model = tf.keras.Sequential(
                [
                    tf.keras.layers.Input(shape=(32, 32, 3)),
                    tf.keras.layers.GlobalAveragePooling2D(),
                    tf.keras.layers.Dense(
                        1,
                        activation="sigmoid",
                        kernel_initializer="zeros",
                        bias_initializer=tf.keras.initializers.Constant(math.log(0.2 / 0.8)),
                    ),
                ]
            )
            model.save(checkpoint)

            result = run_clinical_inference(
                checkpoint=checkpoint,
                image_path=image_path,
                img_size=32,
                preprocessing="rescale_0_1",
                track_db=False,
                explain="none",
            )

        self.assertEqual(result["workflow"], "clinical_inference_experimental")
        self.assertEqual(result["predicted_label"], "parasitized")
        self.assertAlmostEqual(result["raw_model_score"], 0.2, places=4)
        self.assertAlmostEqual(result["probability_parasitized"], 0.8, places=4)
        self.assertAlmostEqual(result["probability_uninfected"], 0.2, places=4)
        self.assertFalse(result["tracking"]["track_db"])
        self.assertEqual(result["model"]["mode"], "single_model")
        self.assertEqual(result["preprocessing"]["mode"], "rescale_0_1")
        self.assertIn("disclaimer", result)


if __name__ == "__main__":
    unittest.main()
