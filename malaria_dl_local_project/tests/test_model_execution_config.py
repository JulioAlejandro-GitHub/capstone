import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.execution_types import TRAIN_COMBINED
from src.model_execution_config import ModelExecutionConfig


class ModelExecutionConfigTests(unittest.TestCase):
    def test_to_dict_returns_complete_json_serializable_configuration(self):
        config = ModelExecutionConfig(
            model_name="densenet121",
            execution_type=TRAIN_COMBINED,
            img_size=200,
            batch_size=64,
            epochs=5,
            fine_tune_epochs=6,
            learning_rate=0.001,
            fine_tune_learning_rate=0.00001,
            preprocessing="auto",
            checkpoint_policy="auc_with_min_recall",
            checkpoint_metric="val_auc",
            min_recall=0.98,
            target_recall=0.98,
            threshold="clinical",
            positive_label="parasitized",
            seed=42,
            output_dir="outputs/densenet121",
            track_db=True,
        )

        result = config.to_dict()

        self.assertEqual(result["model_name"], "densenet121")
        self.assertEqual(result["execution_type"], TRAIN_COMBINED)
        self.assertEqual(result["fine_tune_epochs"], 6)
        self.assertAlmostEqual(result["fine_tune_learning_rate"], 0.00001)
        self.assertEqual(result["positive_label"], "parasitized")
        self.assertTrue(result["track_db"])
        self.assertEqual(len(result), 18)
        json.dumps(result)

    def test_invalid_execution_type_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "no soportado"):
            ModelExecutionConfig(
                model_name="custom_cnn",
                execution_type="unsupported",
                img_size=200,
                batch_size=32,
                epochs=1,
                fine_tune_epochs=None,
                learning_rate=None,
                fine_tune_learning_rate=None,
                preprocessing="auto",
                checkpoint_policy=None,
                checkpoint_metric=None,
                min_recall=None,
                target_recall=None,
                threshold=None,
                positive_label="parasitized",
                seed=42,
                output_dir="outputs/custom_cnn",
                track_db=False,
            )


if __name__ == "__main__":
    unittest.main()
