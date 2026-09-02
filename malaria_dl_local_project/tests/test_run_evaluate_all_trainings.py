"""Regression tests for the governed batch-evaluation command."""

import unittest
from pathlib import Path
from unittest import mock

from run_evaluate_all_trainings import TrainingRun, build_evaluate_command, load_database_url


class RunEvaluateAllTrainingsTests(unittest.TestCase):
    def test_database_url_uses_canonical_loader_without_fallback(self):
        expected = "postgresql+psycopg://unused:unused@db:5432/capstone"
        with mock.patch("src.db.get_database_url", return_value=expected):
            self.assertEqual(load_database_url(Path.cwd()), expected)

    def test_command_uses_model_version_for_strict_lineage(self):
        run = TrainingRun(
            training_run_id="19b11953-561e-40ea-bd72-22033fd3c684",
            model_version_id="11111111-2222-4333-8444-555555555555",
            run_name="train:vgg16",
            model_name="vgg16_transfer_learning",
            optimizer="adamw",
            checkpoint_path="/tmp/historical/best_model.keras",
            img_size="200",
            batch_size="64",
            preprocessing="rescale_0_1",
            dataset_version_id="d8c0cab5-09dd-597f-9de7-7ca01aee2ec2",
        )

        command = build_evaluate_command(
            run,
            dataset_dir="data/malaria_physical_split",
            threshold="clinical",
        )

        self.assertEqual(command[1:3], ["-m", "src.evaluate"])
        self.assertIn("--require-lineage", command)
        self.assertEqual(command[command.index("--model-version-id") + 1], run.model_version_id)
        self.assertEqual(
            command[command.index("--source-training-run-id") + 1],
            run.training_run_id,
        )
        self.assertNotIn("--checkpoint", command)
        self.assertNotIn(run.checkpoint_path, command)
        self.assertEqual(
            command[command.index("--dataset-version-id") + 1],
            run.dataset_version_id,
        )


if __name__ == "__main__":
    unittest.main()
