import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import run_lineage  # noqa: E402


RUN_A = "11111111-1111-4111-8111-111111111111"
RUN_B = "22222222-2222-4222-8222-222222222222"
VERSION_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
ARTIFACT_A = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


def training_row(run_id, optimizer="adamw"):
    return {
        "training_run_id": run_id,
        "id": run_id,
        "run_name": f"train:{run_id[:8]}",
        "run_type": "training",
        "model_name": "densenet121",
        "optimizer": optimizer,
        "command": "python -m src.train --model densenet121",
    }


class CheckpointLineageResolutionTests(unittest.TestCase):
    def test_resolves_exact_model_version_path(self):
        row = {
            **training_row(RUN_A),
            "model_version_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "checkpoint_artifact_id": None,
            "matched_path": "outputs/densenet121/best_model.keras",
        }
        with patch("src.run_lineage._fetch_all", return_value=[row]):
            result = run_lineage.resolve_training_run_from_checkpoint(
                "outputs/densenet121/best_model.keras",
                model_name="densenet121",
            )

        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["training_run_id"], RUN_A)
        self.assertEqual(result["confidence"], "inferred_model_version")

    def test_resolves_exact_checkpoint_artifact_after_model_version_miss(self):
        row = {
            **training_row(RUN_A),
            "model_version_id": None,
            "checkpoint_artifact_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            "matched_path": "outputs/densenet121/runs/run/best_model.keras",
        }
        with patch("src.run_lineage._fetch_all", return_value=[row]):
            result = run_lineage.resolve_training_run_from_checkpoint(
                row["matched_path"]
            )

        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["confidence"], "inferred_exact_checkpoint")
        self.assertEqual(
            result["checkpoint_artifact_id"],
            "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        )

    def test_detects_ambiguous_exact_checkpoint(self):
        rows = [
            {**training_row(RUN_A), "model_version_id": "version-a"},
            {**training_row(RUN_B, optimizer="sgd"), "model_version_id": "version-b"},
        ]
        with patch("src.run_lineage._fetch_all", return_value=rows):
            result = run_lineage.resolve_training_run_from_checkpoint(
                "outputs/densenet121/best_model.keras"
            )

        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(len(result["candidates"]), 2)
        self.assertIn("--source-training-run-id", result["message"])

    def test_detects_conflict_between_model_version_and_artifact_sources(self):
        rows = [
            {
                **training_row(RUN_A),
                "model_version_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "checkpoint_artifact_id": None,
                "match_source": "model_versions",
            },
            {
                **training_row(RUN_B, optimizer="sgd"),
                "model_version_id": None,
                "checkpoint_artifact_id": (
                    "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
                ),
                "match_source": "artifacts",
            },
        ]
        with patch("src.run_lineage._fetch_all", return_value=rows):
            result = run_lineage.resolve_training_run_from_checkpoint(
                "outputs/densenet121/best_model.keras"
            )

        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(
            result["resolution_method"],
            "exact_checkpoint_source_conflict",
        )
        self.assertEqual(len(result["candidates"]), 2)

    def test_combines_version_and_artifact_ids_for_the_same_training(self):
        rows = [
            {
                **training_row(RUN_A),
                "model_version_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "checkpoint_artifact_id": None,
            },
            {
                **training_row(RUN_A),
                "model_version_id": None,
                "checkpoint_artifact_id": (
                    "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
                ),
            },
        ]
        with patch("src.run_lineage._fetch_all", return_value=rows):
            result = run_lineage.resolve_training_run_from_checkpoint(
                "outputs/densenet121/runs/run/best_model.keras"
            )

        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["confidence"], "inferred_model_version")
        self.assertEqual(
            result["checkpoint_artifact_id"],
            "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        )

    def test_generic_checkpoint_is_ambiguous_with_multiple_model_trainings(self):
        rows = [training_row(RUN_A), training_row(RUN_B, optimizer="sgd")]
        with patch(
            "src.run_lineage._fetch_all",
            side_effect=[[], rows],
        ):
            result = run_lineage.resolve_training_run_from_checkpoint(
                "outputs/densenet121/best_model.keras",
                model_name="densenet121",
            )

        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(
            result["resolution_method"],
            "generic_checkpoint_model_candidates",
        )
        self.assertEqual(len(result["candidates"]), 2)

    def test_resolves_uuid_embedded_in_immutable_run_path(self):
        checkpoint = f"outputs/densenet121/runs/{RUN_A}/best_model.keras"
        with (
            patch("src.run_lineage._fetch_all", return_value=[]),
            patch(
                "src.run_lineage.get_training_run",
                return_value=training_row(RUN_A),
            ),
        ):
            result = run_lineage.resolve_training_run_from_checkpoint(checkpoint)

        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["training_run_id"], RUN_A)
        self.assertEqual(result["resolution_method"], "immutable_run_path")

    def test_immutable_path_supports_uuid_v7(self):
        run_v7 = "0190f123-4567-7abc-8def-0123456789ab"
        checkpoint = f"outputs/custom_cnn/runs/{run_v7}/best_model.keras"
        with (
            patch("src.run_lineage._fetch_all", return_value=[]),
            patch(
                "src.run_lineage.get_training_run",
                return_value=training_row(run_v7),
            ) as get_run,
        ):
            result = run_lineage.resolve_training_run_from_checkpoint(checkpoint)

        get_run.assert_called_once_with(run_v7)
        self.assertEqual(result["training_run_id"], run_v7)
        self.assertEqual(result["resolution_method"], "immutable_run_path")

    def test_explicit_source_must_exist_and_be_training(self):
        with patch("src.run_lineage.get_training_run", return_value=None):
            with self.assertRaisesRegex(
                run_lineage.LineageResolutionError,
                "No existe el run",
            ):
                run_lineage.resolve_source_training_run(
                    RUN_A,
                    "outputs/model.keras",
                )

        invalid_parent = {**training_row(RUN_A), "run_type": "evaluation"}
        with patch("src.run_lineage.get_training_run", return_value=invalid_parent):
            with self.assertRaisesRegex(
                run_lineage.LineageResolutionError,
                "run_type='training'",
            ):
                run_lineage.resolve_source_training_run(
                    RUN_A,
                    "outputs/model.keras",
                )

    def test_explicit_source_requires_exact_governed_checkpoint_identity(self):
        exact_resolution = {
            **training_row(RUN_A),
            "status": "resolved",
            "model_version_id": VERSION_A,
            "checkpoint_artifact_id": ARTIFACT_A,
            "resolution_method": "model_versions_exact_checkpoint",
            "confidence": "inferred_model_version",
        }
        with (
            patch(
                "src.run_lineage.get_training_run",
                return_value=training_row(RUN_A),
            ),
            patch(
                "src.run_lineage.resolve_training_run_from_checkpoint",
                return_value=exact_resolution,
            ) as resolve_checkpoint,
        ):
            result = run_lineage.resolve_source_training_run(
                RUN_A,
                "outputs/densenet121/best_model.keras",
                model_name="densenet121",
            )

        resolve_checkpoint.assert_called_once_with(
            "outputs/densenet121/best_model.keras",
            model_name="densenet121",
        )
        self.assertEqual(result["training_run_id"], RUN_A)
        self.assertEqual(result["model_version_id"], VERSION_A)
        self.assertEqual(result["checkpoint_artifact_id"], ARTIFACT_A)
        self.assertEqual(result["confidence"], "explicit")
        self.assertEqual(
            result["resolution_method"],
            "explicit_training_run_id_exact_checkpoint",
        )

    def test_explicit_source_rejects_checkpoint_owned_by_another_training(self):
        exact_resolution = {
            **training_row(RUN_B),
            "status": "resolved",
            "model_version_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
            "checkpoint_artifact_id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        }
        with (
            patch(
                "src.run_lineage.get_training_run",
                return_value=training_row(RUN_A),
            ),
            patch(
                "src.run_lineage.resolve_training_run_from_checkpoint",
                return_value=exact_resolution,
            ),
            self.assertRaisesRegex(
                run_lineage.LineageResolutionError,
                "training run distinto",
            ),
        ):
            run_lineage.resolve_source_training_run(
                RUN_A,
                "outputs/densenet121/best_model.keras",
            )

    def test_explicit_source_rejects_ambiguous_checkpoint_identity(self):
        with (
            patch(
                "src.run_lineage.get_training_run",
                return_value=training_row(RUN_A),
            ),
            patch(
                "src.run_lineage.resolve_training_run_from_checkpoint",
                return_value={"status": "ambiguous", "candidates": []},
            ),
            self.assertRaisesRegex(
                run_lineage.LineageResolutionError,
                "más de una identidad gobernada",
            ),
        ):
            run_lineage.resolve_source_training_run(
                RUN_A,
                "outputs/densenet121/best_model.keras",
            )

    def test_explicit_source_rejects_incomplete_checkpoint_identity(self):
        incomplete_resolution = {
            **training_row(RUN_A),
            "status": "resolved",
            "model_version_id": VERSION_A,
            "checkpoint_artifact_id": None,
        }
        with (
            patch(
                "src.run_lineage.get_training_run",
                return_value=training_row(RUN_A),
            ),
            patch(
                "src.run_lineage.resolve_training_run_from_checkpoint",
                return_value=incomplete_resolution,
            ),
            self.assertRaisesRegex(
                run_lineage.LineageResolutionError,
                "checkpoint_artifact_id gobernados",
            ),
        ):
            run_lineage.resolve_source_training_run(
                RUN_A,
                "outputs/densenet121/best_model.keras",
            )

    def test_unresolved_checkpoint_returns_actionable_status(self):
        with patch("src.run_lineage._fetch_all", return_value=[]):
            result = run_lineage.resolve_training_run_from_checkpoint(
                "outputs/unknown/best_model.keras"
            )

        self.assertEqual(result["status"], "unresolved")
        self.assertEqual(result["confidence"], "unknown")
        self.assertIn("--source-training-run-id", result["message"])


if __name__ == "__main__":
    unittest.main()
