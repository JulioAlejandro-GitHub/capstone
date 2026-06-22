import sys
import unittest
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models import ParasitizedRecall
from src.train import resolve_monitor_mode


class TrainingSelectionTests(unittest.TestCase):
    def test_parasitized_recall_treats_label_one_as_clinical_positive(self):
        metric = ParasitizedRecall(threshold=0.5)

        y_true = np.asarray([0, 0, 1, 1], dtype=np.float32)
        y_pred = np.asarray([0.2, 0.8, 0.2, 0.9], dtype=np.float32)
        metric.update_state(y_true, y_pred)

        self.assertAlmostEqual(float(metric.result().numpy()), 0.5)

    def test_monitor_mode_uses_min_for_loss_and_max_for_clinical_metrics(self):
        self.assertEqual(resolve_monitor_mode("val_loss", "auto"), "min")
        self.assertEqual(resolve_monitor_mode("val_recall_parasitized", "auto"), "max")
        self.assertEqual(resolve_monitor_mode("val_auc", "auto"), "max")
        self.assertEqual(resolve_monitor_mode("val_auc", "min"), "min")


if __name__ == "__main__":
    unittest.main()
