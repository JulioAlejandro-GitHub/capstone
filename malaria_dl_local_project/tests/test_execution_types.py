import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.execution_types import (
    ENSEMBLE,
    EVALUATE,
    EXPLAINABILITY,
    FINE_TUNING,
    INFERENCE,
    SUPPORTED_EXECUTION_TYPES,
    THRESHOLD_CALIBRATION,
    TRAIN_BASE,
    TRAIN_COMBINED,
    TTA,
    validate_execution_type,
)


class ExecutionTypesTests(unittest.TestCase):
    def test_validate_execution_type_accepts_all_supported_values(self):
        expected = [
            TRAIN_BASE,
            FINE_TUNING,
            TRAIN_COMBINED,
            EVALUATE,
            THRESHOLD_CALIBRATION,
            EXPLAINABILITY,
            INFERENCE,
            TTA,
            ENSEMBLE,
        ]

        self.assertEqual(SUPPORTED_EXECUTION_TYPES, expected)
        for execution_type in expected:
            with self.subTest(execution_type=execution_type):
                self.assertEqual(
                    validate_execution_type(execution_type),
                    execution_type,
                )

    def test_validate_execution_type_rejects_unknown_value(self):
        with self.assertRaisesRegex(ValueError, "no soportado"):
            validate_execution_type("training")


if __name__ == "__main__":
    unittest.main()
