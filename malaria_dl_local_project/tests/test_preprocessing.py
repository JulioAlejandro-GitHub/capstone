import sys
import unittest
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.explain import display_images_to_model_inputs, model_image_to_display
from src.preprocessing import (
    PREPROCESSING_RESCALE_0_1,
    PREPROCESSING_VGG16_IMAGENET,
    apply_model_preprocessing,
    preprocessing_metadata,
    recommended_preprocessing_mode,
    resolve_preprocessing_mode,
)


class PreprocessingTests(unittest.TestCase):
    def test_auto_keeps_legacy_rescale_mode(self):
        self.assertEqual(
            resolve_preprocessing_mode("vgg16", "auto"),
            PREPROCESSING_RESCALE_0_1,
        )
        self.assertEqual(
            recommended_preprocessing_mode("vgg16"),
            PREPROCESSING_VGG16_IMAGENET,
        )

    def test_rescale_mode_maps_pixels_to_zero_one(self):
        image = np.asarray([[[0.0, 127.5, 255.0]]], dtype=np.float32)

        result = apply_model_preprocessing(image, PREPROCESSING_RESCALE_0_1).numpy()

        self.assertTrue(np.allclose(result, [[[0.0, 0.5, 1.0]]], atol=1e-6))

    def test_vgg16_imagenet_mode_uses_keras_preprocess_input_contract(self):
        rgb_pixel = np.asarray([[[10.0, 20.0, 30.0]]], dtype=np.float32)

        result = apply_model_preprocessing(
            rgb_pixel,
            PREPROCESSING_VGG16_IMAGENET,
        ).numpy()

        expected_bgr_centered = np.asarray(
            [[[30.0 - 103.939, 20.0 - 116.779, 10.0 - 123.68]]],
            dtype=np.float32,
        )
        self.assertTrue(np.allclose(result, expected_bgr_centered, atol=1e-4))

    def test_vgg16_display_roundtrip_preserves_original_rgb_values(self):
        rgb_pixel = np.asarray([[[10.0, 20.0, 30.0]]], dtype=np.float32)
        model_image = apply_model_preprocessing(
            rgb_pixel,
            PREPROCESSING_VGG16_IMAGENET,
        ).numpy()

        display_image = model_image_to_display(
            model_image,
            PREPROCESSING_VGG16_IMAGENET,
        )
        model_image_again = display_images_to_model_inputs(
            np.expand_dims(display_image, axis=0),
            PREPROCESSING_VGG16_IMAGENET,
        )[0]

        self.assertTrue(np.allclose(display_image * 255.0, rgb_pixel, atol=1e-4))
        self.assertTrue(np.allclose(model_image_again, model_image, atol=1e-4))

    def test_preprocessing_metadata_is_explicit(self):
        metadata = preprocessing_metadata(PREPROCESSING_VGG16_IMAGENET)

        self.assertEqual(metadata["mode"], PREPROCESSING_VGG16_IMAGENET)
        self.assertIn("vgg16.preprocess_input", metadata["description"])


if __name__ == "__main__":
    unittest.main()
