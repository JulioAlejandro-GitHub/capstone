"""Regression tests for governed batch explainability."""

import unittest

from run_explain_all_trainings import TrainingRun, build_explain_command


class RunExplainAllTrainingsTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
