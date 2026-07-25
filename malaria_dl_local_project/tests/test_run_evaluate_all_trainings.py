"""Regression tests for the governed batch-evaluation command."""

import unittest

from run_evaluate_all_trainings import TrainingRun, build_evaluate_command


class RunEvaluateAllTrainingsTests(unittest.TestCase):
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
        )

        command = build_evaluate_command(
            run,
            dataset_dir="data/malaria_physical_split",
            threshold="clinical",
        )

        self.assertIn("--require-lineage", command)
        self.assertEqual(command[command.index("--model-version-id") + 1], run.model_version_id)
        self.assertEqual(
            command[command.index("--source-training-run-id") + 1],
            run.training_run_id,
        )
        self.assertNotIn("--checkpoint", command)
        self.assertNotIn(run.checkpoint_path, command)


if __name__ == "__main__":
    unittest.main()
