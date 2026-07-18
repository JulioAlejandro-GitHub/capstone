import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import backfill_run_lineage  # noqa: E402


CHILD = {
    "child_run_id": "22222222-2222-4222-8222-222222222222",
    "run_type": "evaluation",
    "checkpoint_path": "outputs/model/runs/parent/best_model.keras",
    "model_name": "densenet121",
}
GENERIC_CHILD = {
    **CHILD,
    "checkpoint_path": "outputs/densenet121/best_model.keras",
}
EXPLAIN_CHILD = {
    **CHILD,
    "child_run_id": "55555555-5555-4555-8555-555555555555",
    "run_type": "explainability",
}
EXACT_RESOLUTION = {
    "status": "resolved",
    "training_run_id": "11111111-1111-4111-8111-111111111111",
    "confidence": "inferred_exact_checkpoint",
    "resolution_method": "artifact_exact_checkpoint",
    "checkpoint_artifact_id": "33333333-3333-4333-8333-333333333333",
}


class BackfillRunLineageTests(unittest.TestCase):
    def test_unlinked_query_requires_a_training_parent(self):
        connection = MagicMock()
        connection.execute.return_value.mappings.return_value.all.return_value = []
        context = MagicMock()
        context.__enter__.return_value = connection
        context.__exit__.return_value = False

        with patch.object(
            backfill_run_lineage,
            "get_connection",
            return_value=context,
        ):
            self.assertEqual(backfill_run_lineage.find_unlinked_child_runs(), [])

        sql = str(connection.execute.call_args.args[0])
        self.assertIn("JOIN runs parent ON parent.id = lineage.parent_run_id", sql)
        self.assertIn("parent.run_type = 'training'", sql)

    def test_dry_run_is_default_and_never_writes(self):
        args = backfill_run_lineage.parse_args([])
        self.assertFalse(args.apply)

        with patch.object(
            backfill_run_lineage,
            "resolve_training_run_from_checkpoint",
            return_value=EXACT_RESOLUTION,
        ), patch.object(
            backfill_run_lineage,
            "create_run_lineage_with_metadata",
        ) as create:
            summary = backfill_run_lineage.backfill_run_lineage(
                child_runs=[CHILD]
            )

        self.assertEqual(summary["mode"], "DRY RUN")
        self.assertEqual(summary["planned"], 1)
        self.assertEqual(summary["exact"], 1)
        create.assert_not_called()

    def test_apply_persists_exact_resolution(self):
        with patch.object(
            backfill_run_lineage,
            "resolve_training_run_from_checkpoint",
            return_value=EXACT_RESOLUTION,
        ), patch.object(
            backfill_run_lineage,
            "create_run_lineage_with_metadata",
            return_value="44444444-4444-4444-8444-444444444444",
        ) as create:
            summary = backfill_run_lineage.backfill_run_lineage(
                apply=True,
                child_runs=[CHILD],
            )

        self.assertEqual(summary["created"], 1)
        create.assert_called_once()
        self.assertEqual(
            create.call_args.kwargs["relationship_type"],
            "evaluates_checkpoint_from",
        )
        self.assertEqual(
            create.call_args.kwargs["checkpoint_artifact_id"],
            EXACT_RESOLUTION["checkpoint_artifact_id"],
        )
        self.assertIs(
            create.call_args.kwargs["source_training_run"],
            EXACT_RESOLUTION,
        )

    def test_exact_ambiguity_is_never_replaced_by_heuristic(self):
        ambiguous = {
            "status": "ambiguous",
            "confidence": "unknown",
            "candidates": [{"training_run_id": "one"}, {"training_run_id": "two"}],
        }
        with patch.object(
            backfill_run_lineage,
            "resolve_training_run_from_checkpoint",
            return_value=ambiguous,
        ), patch.object(
            backfill_run_lineage,
            "find_training_candidates_by_model",
        ) as heuristic, patch.object(
            backfill_run_lineage,
            "create_run_lineage_with_metadata",
        ) as create:
            summary = backfill_run_lineage.backfill_run_lineage(
                apply=True,
                allow_heuristic=True,
                child_runs=[CHILD],
            )

        self.assertEqual(summary["ambiguous"], 1)
        self.assertEqual(summary["planned"], 0)
        heuristic.assert_not_called()
        create.assert_not_called()

    def test_heuristic_requires_flag_and_single_same_model_candidate(self):
        unresolved = {"status": "unresolved", "confidence": "unknown"}
        sole_candidate = {
            "training_run_id": "11111111-1111-4111-8111-111111111111",
            "model_name": "densenet121",
        }
        with patch.object(
            backfill_run_lineage,
            "resolve_training_run_from_checkpoint",
            return_value=unresolved,
        ), patch.object(
            backfill_run_lineage,
            "find_training_candidates_by_model",
            return_value=[sole_candidate],
        ) as candidates:
            without_flag = backfill_run_lineage.backfill_run_lineage(
                child_runs=[GENERIC_CHILD]
            )
            with_flag = backfill_run_lineage.backfill_run_lineage(
                allow_heuristic=True,
                child_runs=[GENERIC_CHILD],
            )

        self.assertEqual(without_flag["planned"], 0)
        self.assertEqual(without_flag["unresolved"], 1)
        self.assertEqual(with_flag["planned"], 1)
        self.assertEqual(with_flag["heuristic"], 1)
        self.assertEqual(
            with_flag["relationships"][0]["confidence"],
            "inferred_heuristic",
        )
        candidates.assert_called_once_with("densenet121")

    def test_heuristic_never_applies_to_immutable_or_foreign_path(self):
        unresolved = {"status": "unresolved", "confidence": "unknown"}
        foreign_child = {
            **CHILD,
            "checkpoint_path": "/tmp/best_model.keras",
        }
        with patch.object(
            backfill_run_lineage,
            "resolve_training_run_from_checkpoint",
            return_value=unresolved,
        ), patch.object(
            backfill_run_lineage,
            "find_training_candidates_by_model",
        ) as candidates:
            immutable = backfill_run_lineage.backfill_run_lineage(
                allow_heuristic=True,
                child_runs=[CHILD],
            )
            foreign = backfill_run_lineage.backfill_run_lineage(
                allow_heuristic=True,
                child_runs=[foreign_child],
            )

        self.assertEqual(immutable["unresolved"], 1)
        self.assertEqual(foreign["unresolved"], 1)
        candidates.assert_not_called()

    def test_heuristic_requires_checkpoint_model_to_match_child_model(self):
        unresolved = {"status": "unresolved", "confidence": "unknown"}
        mismatch = {
            **GENERIC_CHILD,
            "checkpoint_path": "outputs/vgg16/best_model.keras",
            "model_name": "densenet121",
        }
        with patch.object(
            backfill_run_lineage,
            "resolve_training_run_from_checkpoint",
            return_value=unresolved,
        ), patch.object(
            backfill_run_lineage,
            "find_training_candidates_by_model",
        ) as candidates:
            result = backfill_run_lineage.backfill_run_lineage(
                allow_heuristic=True,
                child_runs=[mismatch],
            )

        self.assertEqual(result["planned"], 0)
        self.assertEqual(result["unresolved"], 1)
        candidates.assert_not_called()

    def test_vgg16_tracking_alias_matches_legacy_checkpoint_folder(self):
        self.assertTrue(
            backfill_run_lineage.is_generic_legacy_checkpoint(
                "outputs/vgg16/best_model.keras",
                "vgg16_transfer_learning",
            )
        )

    def test_explainability_uses_explains_relationship(self):
        with patch.object(
            backfill_run_lineage,
            "resolve_training_run_from_checkpoint",
            return_value=EXACT_RESOLUTION,
        ), patch.object(
            backfill_run_lineage,
            "create_run_lineage_with_metadata",
            return_value="44444444-4444-4444-8444-444444444444",
        ) as create:
            summary = backfill_run_lineage.backfill_run_lineage(
                apply=True,
                child_runs=[EXPLAIN_CHILD],
            )

        self.assertEqual(summary["created"], 1)
        self.assertEqual(
            create.call_args.kwargs["relationship_type"],
            "explains_checkpoint_from",
        )


if __name__ == "__main__":
    unittest.main()
