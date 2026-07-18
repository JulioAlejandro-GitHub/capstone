import sys
import unittest
import warnings
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import explain  # noqa: E402


class ExplainLineageTrackingTests(unittest.TestCase):
    def test_cli_aliases_share_source_training_run_id_destination(self):
        source_args = explain.parse_args(
            [
                "--checkpoint",
                "model.keras",
                "--method",
                "gradcam",
                "--source-training-run-id",
                "training-run",
            ]
        )
        parent_args = explain.parse_args(
            [
                "--checkpoint",
                "model.keras",
                "--method",
                "gradcam",
                "--parent-run-id",
                "training-run",
                "--require-lineage",
            ]
        )

        self.assertEqual(source_args.source_training_run_id, "training-run")
        self.assertEqual(parent_args.source_training_run_id, "training-run")
        self.assertTrue(parent_args.require_lineage)

    def test_explicit_training_run_creates_explain_lineage_and_metadata(self):
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
            "src.run_lineage.create_run_lineage_with_metadata",
            return_value="lineage-id",
        ) as create_mock, patch(
            "src.run_lineage.mark_lineage_unresolved"
        ) as unresolved_mock:
            result = explain.track_source_training_lineage(
                args=args,
                checkpoint=Path("outputs/densenet121/best_model.keras"),
                model_name="densenet121",
                run_context={"run_id": "explain-run"},
            )

        self.assertIs(result, resolution)
        resolve_mock.assert_called_once_with(
            source_training_run_id="training-run",
            checkpoint_path="outputs/densenet121/best_model.keras",
            model_name="densenet121",
        )
        create_mock.assert_called_once_with(
            parent_run_id="training-run",
            child_run_id="explain-run",
            relationship_type="explains_checkpoint_from",
            source_training_run=resolution,
            checkpoint_path="outputs/densenet121/best_model.keras",
            checkpoint_artifact_id="artifact-id",
            model_version_id="version-id",
            confidence="explicit",
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
            "confidence": "inferred_exact_checkpoint",
        }

        with patch(
            "src.run_lineage.resolve_source_training_run",
            return_value=resolution,
        ), patch(
            "src.run_lineage.create_run_lineage_with_metadata",
            return_value="lineage-id",
        ) as create_mock, patch(
            "src.run_lineage.mark_lineage_unresolved"
        ):
            explain.track_source_training_lineage(
                args=args,
                checkpoint=Path("outputs/densenet121/best_model.keras"),
                model_name="densenet121",
                run_context={"run_id": "explain-run"},
            )

        self.assertEqual(
            create_mock.call_args.kwargs["confidence"],
            "inferred_exact_checkpoint",
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
            "src.run_lineage.create_run_lineage_with_metadata"
        ) as create_mock, patch(
            "src.run_lineage.mark_lineage_unresolved"
        ) as unresolved_mock, warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = explain.track_source_training_lineage(
                args=args,
                checkpoint=Path("outputs/densenet121/best_model.keras"),
                model_name="densenet121",
                run_context={"run_id": "explain-run"},
            )

        self.assertIs(result, resolution)
        unresolved_mock.assert_called_once_with(
            child_run_id="explain-run",
            checkpoint_path="outputs/densenet121/best_model.keras",
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
            "src.run_lineage.create_run_lineage_with_metadata"
        ), patch(
            "src.run_lineage.mark_lineage_unresolved"
        ) as unresolved_mock:
            with self.assertRaisesRegex(RuntimeError, "entrenamiento origen"):
                explain.track_source_training_lineage(
                    args=strict_args,
                    checkpoint=Path("model.keras"),
                    model_name="densenet121",
                    run_context={"run_id": "explain-run"},
                )

        unresolved_mock.assert_called_once()
        no_tracking_args = SimpleNamespace(
            track_db=False,
            source_training_run_id=None,
            require_lineage=True,
        )
        self.assertIsNone(
            explain.track_source_training_lineage(
                args=no_tracking_args,
                checkpoint=Path("model.keras"),
                model_name="densenet121",
                run_context={"run_id": "explain-run"},
            )
        )

    def test_require_lineage_fails_when_child_run_could_not_be_created(self):
        args = SimpleNamespace(
            track_db=True,
            source_training_run_id="training-run",
            require_lineage=True,
        )

        with self.assertRaisesRegex(RuntimeError, "run de explicabilidad"):
            explain.track_source_training_lineage(
                args=args,
                checkpoint=Path("model.keras"),
                model_name="densenet121",
                run_context={"run_id": None},
            )

    def test_operational_resolution_failure_is_best_effort_without_strict(self):
        args = SimpleNamespace(
            track_db=True,
            source_training_run_id=None,
            require_lineage=False,
        )
        with patch(
            "src.run_lineage.resolve_source_training_run",
            side_effect=RuntimeError("connection unavailable"),
        ), patch(
            "src.run_lineage.mark_lineage_unresolved",
        ) as mark, warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = explain.track_source_training_lineage(
                args=args,
                checkpoint=Path("model.keras"),
                model_name="densenet121",
                run_context={"run_id": "explain-run"},
            )

        self.assertEqual(result["status"], "unresolved")
        mark.assert_called_once()
        self.assertIn("No se pudo resolver", str(caught[0].message))

    def test_operational_failure_remains_fatal_with_require_lineage(self):
        args = SimpleNamespace(
            track_db=True,
            source_training_run_id=None,
            require_lineage=True,
        )
        with patch(
            "src.run_lineage.resolve_source_training_run",
            side_effect=RuntimeError("connection unavailable"),
        ), patch("src.run_lineage.mark_lineage_unresolved"):
            with self.assertRaisesRegex(RuntimeError, "No se pudo resolver"):
                explain.track_source_training_lineage(
                    args=args,
                    checkpoint=Path("model.keras"),
                    model_name="densenet121",
                    run_context={"run_id": "explain-run"},
                )


if __name__ == "__main__":
    unittest.main()
