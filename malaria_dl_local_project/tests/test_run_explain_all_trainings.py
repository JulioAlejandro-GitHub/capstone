"""Regression tests for governed batch explainability."""

import unittest
from pathlib import Path
from unittest import mock

from run_explain_all_trainings import TrainingRun, build_explain_command, load_database_url


class RunExplainAllTrainingsTests(unittest.TestCase):
    def test_database_url_uses_canonical_loader_without_fallback(self):
        expected = "postgresql+psycopg://unused:unused@db:5432/capstone"
        with mock.patch("src.db.get_database_url", return_value=expected):
            self.assertEqual(load_database_url(Path.cwd()), expected)

    def test_command_uses_governed_model_version(self):
        run = TrainingRun(
            training_run_id="19b11953-561e-40ea-bd72-22033fd3c684",
            model_version_id="7700cc38-ff59-45a8-b043-f386670f11b4",
            run_name="train:vgg16",
            model_name="vgg16_transfer_learning",
            optimizer="adamw",
            checkpoint_path="/tmp/historical/best_model.keras",
            img_size="200",
            batch_size="64",
            preprocessing="rescale_0_1",
            dataset_version_id="d8c0cab5-09dd-597f-9de7-7ca01aee2ec2",
        )

        command = build_explain_command(
            run,
            method="all",
            num_samples=50,
            threshold="clinical",
        )

        self.assertIn("--require-lineage", command)
        self.assertEqual(command[command.index("--model-version-id") + 1], run.model_version_id)
        self.assertEqual(
            command[command.index("--source-training-run-id") + 1],
            run.training_run_id,
        )
        self.assertEqual(
            command[command.index("--preprocessing") + 1],
            "rescale_0_1",
        )
        self.assertNotIn("--checkpoint", command)
        self.assertNotIn(run.checkpoint_path, command)
        self.assertEqual(
            command[command.index("--dataset-version-id") + 1],
            run.dataset_version_id,
        )

    def test_pipeline_loads_inherited_dataset_as_governed(self):
        pipeline = Path("src/malaria_dl/explainability/pipeline.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("governed=governed_dataset is not None", pipeline)


if __name__ == "__main__":
    unittest.main()
