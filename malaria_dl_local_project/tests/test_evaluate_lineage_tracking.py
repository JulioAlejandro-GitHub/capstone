import sys
import unittest
import warnings
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import evaluate  # noqa: E402


class EvaluateLineageTrackingTests(unittest.TestCase):
    def test_cli_aliases_share_source_training_run_id_destination(self):
        source_args = evaluate.parse_args(
            [
                "--checkpoint",
                "model.keras",
                "--source-training-run-id",
                "training-run",
            ]
        )
        parent_args = evaluate.parse_args(
            [
                "--checkpoint",
                "model.keras",
                "--parent-run-id",
                "training-run",
                "--require-lineage",
            ]
        )

        self.assertEqual(source_args.source_training_run_id, "training-run")
        self.assertEqual(parent_args.source_training_run_id, "training-run")
        self.assertTrue(parent_args.require_lineage)

    def test_explicit_training_run_creates_evaluation_lineage_and_metadata(self):
        args = SimpleNamespace(
            track_db=True,
            source_training_run_id="training-run",
            require_lineage=False,
        )
        resolution = {
            "status": "resolved",
            "training_run_id": "training-run",
            "id": "training-run",
            "run_type": "training",
            "confidence": "explicit",
            "checkpoint_artifact_id": "artifact-id",
            "model_version_id": "version-id",
        }

        with patch(
            "src.run_lineage.resolve_source_training_run",
            return_value=resolution,
        ) as resolve_mock, patch(
            "src.malaria_dl.evaluation.evaluation_training_lineage_service."
            "create_or_confirm_evaluation_training_lineage",
            return_value=SimpleNamespace(lineage_id="lineage-id", created=True),
        ) as create_mock, patch(
            "src.run_lineage.mark_lineage_unresolved"
        ) as unresolved_mock:
            result = evaluate.track_source_training_lineage(
                args=args,
                checkpoint=Path("outputs/custom_cnn/best_model.keras"),
                model_name="custom_cnn",
                run_context={"run_id": "evaluation-run"},
            )

        self.assertIs(result, resolution)
        resolve_mock.assert_called_once_with(
            source_training_run_id="training-run",
            checkpoint_path="outputs/custom_cnn/best_model.keras",
            model_name="custom_cnn",
        )
        create_mock.assert_called_once_with(
            training_run_id="training-run",
            evaluation_run_id="evaluation-run",
            model_version_id="version-id",
            checkpoint_artifact_id="artifact-id",
            checkpoint_path="outputs/custom_cnn/best_model.keras",
            confidence="explicit",
            metadata={"phase": "evaluation_started"},
        )
        unresolved_mock.assert_not_called()

    def test_automatic_resolution_preserves_inferred_confidence(self):
        args = SimpleNamespace(
            track_db=True,
            source_training_run_id=None,
            require_lineage=False,
        )
        resolution = {
            "status": "resolved",
            "training_run_id": "training-run",
            "confidence": "inferred_model_version",
        }

        with patch(
            "src.run_lineage.resolve_source_training_run",
            return_value=resolution,
        ), patch(
            "src.malaria_dl.evaluation.evaluation_training_lineage_service."
            "create_or_confirm_evaluation_training_lineage",
            return_value=SimpleNamespace(lineage_id="lineage-id", created=True),
        ) as create_mock, patch(
            "src.run_lineage.mark_lineage_unresolved"
        ):
            evaluate.track_source_training_lineage(
                args=args,
                checkpoint=Path("outputs/custom_cnn/best_model.keras"),
                model_name="custom_cnn",
                run_context={"run_id": "evaluation-run"},
            )

        self.assertEqual(
            create_mock.call_args.kwargs["confidence"],
            "inferred_model_version",
        )

    def test_unresolved_lineage_warns_and_marks_child_run(self):
        args = SimpleNamespace(
            track_db=True,
            source_training_run_id=None,
            require_lineage=False,
        )
        resolution = {
            "status": "ambiguous",
            "message": "Checkpoint ambiguo; use --source-training-run-id.",
        }

        with patch(
            "src.run_lineage.resolve_source_training_run",
            return_value=resolution,
        ), patch(
            "src.malaria_dl.evaluation.evaluation_training_lineage_service."
            "create_or_confirm_evaluation_training_lineage"
        ) as create_mock, patch(
            "src.run_lineage.mark_lineage_unresolved"
        ) as unresolved_mock, warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = evaluate.track_source_training_lineage(
                args=args,
                checkpoint=Path("outputs/custom_cnn/best_model.keras"),
                model_name="custom_cnn",
                run_context={"run_id": "evaluation-run"},
            )

        self.assertIs(result, resolution)
        unresolved_mock.assert_called_once_with(
            child_run_id="evaluation-run",
            checkpoint_path="outputs/custom_cnn/best_model.keras",
            warning="Checkpoint ambiguo; use --source-training-run-id.",
        )
        create_mock.assert_not_called()
        self.assertIn("Checkpoint ambiguo", str(caught[0].message))

    def test_require_lineage_fails_only_when_database_tracking_is_active(self):
        strict_args = SimpleNamespace(
            track_db=True,
            source_training_run_id=None,
            require_lineage=True,
        )
        resolution = {
            "status": "unresolved",
            "message": "No existe un entrenamiento origen único.",
        }

        with patch(
            "src.run_lineage.resolve_source_training_run",
            return_value=resolution,
        ), patch(
            "src.malaria_dl.evaluation.evaluation_training_lineage_service."
            "create_or_confirm_evaluation_training_lineage"
        ), patch(
            "src.run_lineage.mark_lineage_unresolved"
        ) as unresolved_mock:
            with self.assertRaisesRegex(RuntimeError, "entrenamiento origen"):
                evaluate.track_source_training_lineage(
                    args=strict_args,
                    checkpoint=Path("model.keras"),
                    model_name="custom_cnn",
                    run_context={"run_id": "evaluation-run"},
                )

        unresolved_mock.assert_called_once()
        no_tracking_args = SimpleNamespace(
            track_db=False,
            source_training_run_id=None,
            require_lineage=True,
        )
        self.assertIsNone(
            evaluate.track_source_training_lineage(
                args=no_tracking_args,
                checkpoint=Path("model.keras"),
                model_name="custom_cnn",
                run_context={"run_id": "evaluation-run"},
            )
        )

    def test_require_lineage_fails_when_child_run_could_not_be_created(self):
        args = SimpleNamespace(
            track_db=True,
            source_training_run_id="training-run",
            require_lineage=True,
        )

        with self.assertRaisesRegex(RuntimeError, "run de evaluación"):
            evaluate.track_source_training_lineage(
                args=args,
                checkpoint=Path("model.keras"),
                model_name="custom_cnn",
                run_context={"run_id": None},
            )

    def test_operational_persistence_failure_is_always_fatal(self):
        args = SimpleNamespace(
            track_db=True,
            source_training_run_id=None,
            require_lineage=False,
        )
        resolution = {
            "status": "resolved",
            "training_run_id": "training-run",
            "confidence": "inferred_exact_checkpoint",
        }
        with patch(
            "src.run_lineage.resolve_source_training_run",
            return_value=resolution,
        ), patch(
            "src.malaria_dl.evaluation.evaluation_training_lineage_service."
            "create_or_confirm_evaluation_training_lineage",
            side_effect=RuntimeError("database temporarily unavailable"),
        ), patch("src.run_lineage.mark_lineage_unresolved") as mark:
            with self.assertRaisesRegex(
                RuntimeError, "database temporarily unavailable"
            ):
                evaluate.track_source_training_lineage(
                    args=args,
                    checkpoint=Path("model.keras"),
                    model_name="custom_cnn",
                    run_context={"run_id": "evaluation-run"},
                )

        mark.assert_not_called()

    def test_explicit_lineage_validation_error_is_always_fatal(self):
        from src.run_lineage import LineageResolutionError

        args = SimpleNamespace(
            track_db=True,
            source_training_run_id="missing-training",
            require_lineage=False,
        )
        with patch(
            "src.run_lineage.resolve_source_training_run",
            side_effect=LineageResolutionError("No existe el run"),
        ), patch("src.run_lineage.mark_lineage_unresolved") as mark:
            with self.assertRaisesRegex(LineageResolutionError, "No existe"):
                evaluate.track_source_training_lineage(
                    args=args,
                    checkpoint=Path("model.keras"),
                    model_name="custom_cnn",
                    run_context={"run_id": "evaluation-run"},
                )

        mark.assert_not_called()


if __name__ == "__main__":
    unittest.main()
