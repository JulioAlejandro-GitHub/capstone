"""Characterization tests for canonical and legacy module compatibility."""

import importlib
import unittest
from pathlib import Path


class CanonicalArchitectureTests(unittest.TestCase):
    def test_stable_project_paths(self):
        from src.malaria_dl.common.paths import DATA_DIR, OUTPUT_DIR, PROJECT_ROOT
        from src.config import PHYSICAL_DATASET_DIR, TEST_DIR, TRAIN_DIR, VAL_DIR

        expected = Path(__file__).resolve().parents[1]
        self.assertEqual(PROJECT_ROOT, expected)
        self.assertEqual(DATA_DIR, expected / "data")
        self.assertEqual(OUTPUT_DIR, expected / "outputs")
        self.assertEqual(PHYSICAL_DATASET_DIR, DATA_DIR / "malaria_physical_split")
        self.assertEqual(TRAIN_DIR, PHYSICAL_DATASET_DIR / "train")
        self.assertEqual(VAL_DIR, PHYSICAL_DATASET_DIR / "val")
        self.assertEqual(TEST_DIR, PHYSICAL_DATASET_DIR / "test")

    def test_clinical_convention_is_unchanged(self):
        from src.malaria_dl.config.clinical_labels import (
            NEGATIVE_CLASS_INDEX,
            NEGATIVE_LABEL,
            POSITIVE_CLASS_INDEX,
            POSITIVE_LABEL,
            RAW_MODEL_SCORE_MEANING,
        )

        self.assertEqual((NEGATIVE_CLASS_INDEX, NEGATIVE_LABEL), (0, "uninfected"))
        self.assertEqual((POSITIVE_CLASS_INDEX, POSITIVE_LABEL), (1, "parasitized"))
        self.assertEqual(RAW_MODEL_SCORE_MEANING, "probability_parasitized")

    def test_legacy_and_canonical_services_are_identical(self):
        from src.model_deployment_service import ModelDeploymentService as Legacy
        from src.malaria_dl.governance.services.deployment_service import (
            ModelDeploymentService as Canonical,
        )

        self.assertIs(Legacy, Canonical)

    def test_canonical_modules_import_without_cycles(self):
        modules = [
            "src.malaria_dl.common.paths",
            "src.malaria_dl.config.settings",
            "src.malaria_dl.data.preprocessing",
            "src.malaria_dl.models.architectures",
            "src.malaria_dl.training.checkpoint_policy",
            "src.malaria_dl.evaluation.clinical_metrics",
            "src.malaria_dl.evaluation.threshold_calibration",
            "src.malaria_dl.explainability.pipeline",
            "src.malaria_dl.inference.pipeline",
            "src.malaria_dl.persistence.lineage",
            "src.malaria_dl.governance.repository",
            "src.malaria_dl.governance.services.stage2_publication_service",
        ]
        for module in modules:
            with self.subTest(module=module):
                self.assertIsNotNone(importlib.import_module(module))


if __name__ == "__main__":
    unittest.main()
