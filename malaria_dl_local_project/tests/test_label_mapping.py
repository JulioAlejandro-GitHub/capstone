import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import tensorflow as tf

    from src.data import remap_tfds_malaria_label
except Exception as exc:  # pragma: no cover - exercised only when local env lacks TF.
    tf = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

from src.config import (
    CLASS_NAMES,
    LABEL_MAPPING_VERSION,
    NEGATIVE_CLASS_INDEX,
    NEGATIVE_LABEL,
    POSITIVE_CLASS_INDEX,
    POSITIVE_LABEL,
    RAW_MODEL_SCORE_MEANING,
)
from src.decision import probabilities_by_class_from_prediction


class LabelMappingTests(unittest.TestCase):
    def test_label_mapping_is_clinical(self):
        self.assertEqual(CLASS_NAMES, ["uninfected", "parasitized"])
        self.assertEqual(POSITIVE_CLASS_INDEX, 1)
        self.assertEqual(POSITIVE_LABEL, "parasitized")

    def test_official_class_order_is_uninfected_then_parasitized(self):
        self.assertEqual(CLASS_NAMES, ["uninfected", "parasitized"])
        self.assertEqual(LABEL_MAPPING_VERSION, "clinical_v1_parasitized_positive")

    def test_positive_class_is_parasitized(self):
        self.assertEqual(POSITIVE_LABEL, "parasitized")
        self.assertEqual(POSITIVE_CLASS_INDEX, 1)

    def test_negative_class_is_uninfected(self):
        self.assertEqual(NEGATIVE_LABEL, "uninfected")
        self.assertEqual(NEGATIVE_CLASS_INDEX, 0)

    def test_raw_score_means_probability_parasitized(self):
        raw_model_score = 0.8
        probability_parasitized = raw_model_score
        probability_uninfected = 1.0 - raw_model_score

        self.assertEqual(RAW_MODEL_SCORE_MEANING, "probability_parasitized")
        self.assertAlmostEqual(probability_parasitized, 0.8)
        self.assertAlmostEqual(probability_uninfected, 0.2)

    @unittest.skipIf(tf is None, f"TensorFlow no disponible: {IMPORT_ERROR}")
    def test_tfds_label_is_remapped_to_clinical_label(self):
        # TFDS malaria original: 0=parasitized, 1=uninfected.
        # Proyecto clinical_v1: 0=uninfected, 1=parasitized.
        self.assertEqual(float(remap_tfds_malaria_label(tf.constant(0)).numpy()), 1.0)
        self.assertEqual(float(remap_tfds_malaria_label(tf.constant(1)).numpy()), 0.0)

    def test_raw_model_score_defaults_to_probability_parasitized(self):
        probabilities = probabilities_by_class_from_prediction([[0.8]])

        self.assertAlmostEqual(probabilities["parasitized"], 0.8, places=6)
        self.assertAlmostEqual(probabilities["uninfected"], 0.2, places=6)

    def test_legacy_mapping_is_only_explicit(self):
        probabilities = probabilities_by_class_from_prediction(
            [[0.8]],
            label_mapping_version="legacy_tfds_parasitized_zero",
        )

        self.assertAlmostEqual(probabilities["parasitized"], 0.2, places=6)
        self.assertAlmostEqual(probabilities["uninfected"], 0.8, places=6)


if __name__ == "__main__":
    unittest.main()
