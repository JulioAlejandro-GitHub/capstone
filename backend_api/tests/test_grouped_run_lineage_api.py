import sys
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest import mock


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.routes import runs as runs_routes  # noqa: E402
from app.routes.runs import list_grouped_run_lineage  # noqa: E402
from app.services.run_lineage import grouped_run_lineage_payload  # noqa: E402
from app.main import app  # noqa: E402


TRAINING_A = "11111111-1111-4111-8111-111111111111"
TRAINING_B = "22222222-2222-4222-8222-222222222222"
EVALUATION_A = "33333333-3333-4333-8333-333333333333"
EVALUATION_B = "77777777-7777-4777-8777-777777777777"
EXPLAIN_A = "44444444-4444-4444-8444-444444444444"
ORPHAN_EVALUATION = "55555555-5555-4555-8555-555555555555"
ORPHAN_EXPLAIN = "66666666-6666-4666-8666-666666666666"


def training_row(run_id, model_name):
    return {
        "run_id": run_id,
        "run_name": f"train:{model_name}",
        "run_type": "training",
        "status": "completed",
        "model_name": model_name,
        "dataset_name": "malaria",
        "started_at": datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc),
        "finished_at": datetime(2026, 7, 18, 12, 5, tzinfo=timezone.utc),
        "duration_seconds": Decimal("300.5"),
        "accuracy": Decimal("0.94"),
        "precision": Decimal("0.93"),
        "recall": Decimal("0.98"),
        "f1_score": Decimal("0.95"),
        "auc": Decimal("0.97"),
        "optimizer": "adamw",
        "command": f"python -m src.train --model {model_name}",
        "recall_parasitized": Decimal("0.98"),
        "sensitivity_parasitized": Decimal("0.98"),
        "specificity": Decimal("0.91"),
        "f2_parasitized": Decimal("0.97"),
        "roc_auc_parasitized": Decimal("0.98"),
        "pr_auc_parasitized": Decimal("0.96"),
        "balanced_accuracy": Decimal("0.945"),
        "threshold_used": Decimal("0.32"),
        "tn": 1260,
        "fp": 125,
        "fn": 26,
        "tp": 1345,
        "confusion_matrix": [[1260, 125], [26, 1345]],
        "prediction_collapse_detected": False,
    }


class GroupedRunLineageApiTests(unittest.TestCase):
    def test_groups_children_preserves_metrics_and_separates_unlinked_runs(self):
        trainings = [
            training_row(TRAINING_A, "densenet121"),
            training_row(TRAINING_B, "custom_cnn"),
        ]
        trainings[0].update(
            {
                "model_name": None,
                "optimizer": None,
                "resolved_model_name": "densenet121",
                "resolved_optimizer": "adamw",
            }
        )
        evaluations = [
            {
                "training_run_id": TRAINING_A,
                "evaluation_run_id": EVALUATION_A,
                "evaluation_run_name": "evaluate:densenet121",
                "evaluation_started_at": datetime(
                    2026, 7, 18, 13, 0, tzinfo=timezone.utc
                ),
                "status": "completed",
                "finished_at": datetime(2026, 7, 18, 13, 2, tzinfo=timezone.utc),
                "duration_seconds": Decimal("120"),
                "model_name": "densenet121",
                "optimizer": "adamw",
                "relationship_type": "evaluates_checkpoint_from",
                "confidence": "inferred_model_version",
                "checkpoint_path": "outputs/densenet121/runs/train/best_model.keras",
                "command": "python -m src.evaluate --checkpoint model.keras",
                "accuracy": Decimal("0.95"),
                "precision_parasitized": Decimal("0.94"),
                "recall": Decimal("0.98"),
                "recall_parasitized": Decimal("0.98"),
                "sensitivity_parasitized": Decimal("0.98"),
                "specificity": Decimal("0.92"),
                "f2_score": Decimal("0.97"),
                "auc": Decimal("0.99"),
                "pr_auc_parasitized": Decimal("0.98"),
                "balanced_accuracy": Decimal("0.95"),
                "threshold_used": Decimal("0.32"),
                "tn": 100,
                "fp": 10,
                "fn": 2,
                "tp": 110,
                "confusion_matrix": [[100, 10], [2, 110]],
                "prediction_collapse_detected": False,
            },
            {
                "training_run_id": TRAINING_A,
                "evaluation_run_id": EVALUATION_B,
                "evaluation_run_name": "evaluate:densenet121:external",
                "evaluation_started_at": "2026-07-18T13:30:00+00:00",
                "status": "completed",
                "model_name": "densenet121",
                "optimizer": "adamw",
                "relationship_type": "evaluates_checkpoint_from",
                "confidence": "explicit",
                "recall": Decimal("0.97"),
                "specificity": Decimal("0.90"),
                "f2_score": Decimal("0.96"),
                "auc": Decimal("0.98"),
            },
        ]
        explainability = [
            {
                "training_run_id": TRAINING_A,
                "explain_run_id": EXPLAIN_A,
                "explain_run_name": "explain:densenet121",
                "explain_started_at": "2026-07-18T14:00:00+00:00",
                "status": "completed",
                "model_name": "densenet121",
                "optimizer": "adamw",
                "relationship_type": "explains_checkpoint_from",
                "confidence": "explicit",
                "checkpoint_path": "outputs/densenet121/runs/train/best_model.keras",
                "method": "gradcam",
                "total_explanations": 4,
                "success_count": 3,
                "failed_count": 1,
            },
            {
                "training_run_id": TRAINING_A,
                "explain_run_id": EXPLAIN_A,
                "explain_run_name": "explain:densenet121",
                "explain_started_at": "2026-07-18T14:00:00+00:00",
                "status": "completed",
                "model_name": "densenet121",
                "optimizer": "adamw",
                "relationship_type": "explains_checkpoint_from",
                "confidence": "explicit",
                "checkpoint_path": "outputs/densenet121/runs/train/best_model.keras",
                "method": "lime",
                "total_explanations": Decimal("2"),
                "success_count": Decimal("2"),
                "failed_count": 0,
            },
            # Defensive duplicate: a run/method must not be counted twice.
            {
                "training_run_id": TRAINING_A,
                "explain_run_id": EXPLAIN_A,
                "method": "lime",
                "total_explanations": 2,
                "success_count": 2,
                "failed_count": 0,
            },
        ]
        unlinked = [
            {
                "run_id": ORPHAN_EVALUATION,
                "run_name": "evaluate:orphan",
                "run_type": "evaluation",
                "status": "completed",
                "started_at": "2026-07-17T10:00:00+00:00",
                "model_name": "vgg16",
                "lineage_status": "unresolved",
                "lineage_warning": "Use --source-training-run-id.",
            },
            {
                "run_id": ORPHAN_EXPLAIN,
                "run_name": "explain:orphan",
                "run_type": "explainability",
                "status": "failed",
                "started_at": "2026-07-17T11:00:00+00:00",
                "model_name": "custom_cnn",
            },
        ]

        with mock.patch(
            "app.services.run_lineage.fetch_all",
            side_effect=[trainings, evaluations, explainability, unlinked],
        ) as fetch_all:
            payload = grouped_run_lineage_payload(datasource="malaria", limit=25)

        self.assertEqual(fetch_all.call_count, 4)
        self.assertEqual(len(payload["items"]), 2)
        first = payload["items"][0]
        self.assertEqual(first["training"]["run_id"], TRAINING_A)
        self.assertEqual(first["training"]["model_name"], "densenet121")
        self.assertEqual(first["training"]["optimizer"], "adamw")
        self.assertNotIn("resolved_model_name", first["training"])
        self.assertNotIn("resolved_optimizer", first["training"])
        self.assertEqual(first["training"]["duration_seconds"], 300.5)
        self.assertEqual(first["training"]["recall_parasitized"], 0.98)
        self.assertEqual(first["training"]["tn"], 1260)
        self.assertIs(first["training"]["prediction_collapse_detected"], False)

        evaluation = first["evaluations"][0]
        self.assertEqual(len(first["evaluations"]), 2)
        self.assertEqual(evaluation["run_id"], EVALUATION_A)
        self.assertEqual(evaluation["recall"], 0.98)
        self.assertEqual(evaluation["specificity"], 0.92)
        self.assertEqual(evaluation["f2_score"], 0.97)
        self.assertEqual(evaluation["auc"], 0.99)
        self.assertEqual(evaluation["confusion_matrix"], [[100, 10], [2, 110]])

        self.assertEqual(len(first["explainability"]), 1)
        explanation = first["explainability"][0]
        self.assertEqual(explanation["methods"], ["gradcam", "lime"])
        self.assertEqual(explanation["method"], "multiple")
        self.assertEqual(explanation["total_explanations"], 6)
        self.assertEqual(explanation["success_count"], 5)
        self.assertEqual(explanation["failed_count"], 1)
        self.assertEqual(payload["items"][1]["evaluations"], [])
        self.assertEqual(payload["items"][1]["explainability"], [])

        self.assertEqual(
            payload["unlinked"]["evaluations"][0]["run_id"],
            ORPHAN_EVALUATION,
        )
        self.assertEqual(
            payload["unlinked"]["explainability"][0]["model_name"],
            "custom_cnn",
        )
        self.assertEqual(
            payload["totals"],
            {
                "training_runs": 2,
                "linked_evaluations": 2,
                "linked_explainability": 1,
                "unlinked_evaluations": 1,
                "unlinked_explainability": 1,
                "conflicting_evaluations": 0,
                "conflicting_explainability": 0,
            },
        )

        sql_statements = [call.args[1] for call in fetch_all.call_args_list]
        self.assertIn("vw_run_dashboard", sql_statements[0])
        self.assertIn("AS resolved_optimizer", sql_statements[0])
        self.assertIn("vw_evaluation_lineage", sql_statements[1])
        self.assertIn("WHEN 'test' THEN 0", sql_statements[1])
        self.assertIn("vw_explainability_lineage", sql_statements[2])
        self.assertIn("NOT EXISTS", sql_statements[3])
        for sql in sql_statements:
            upper_sql = sql.upper()
            for mutating_keyword in (
                "INSERT INTO",
                "UPDATE ",
                "DELETE FROM",
                "ALTER ",
                "DROP ",
                "TRUNCATE ",
            ):
                self.assertNotIn(mutating_keyword, upper_sql)
        self.assertEqual(fetch_all.call_args_list[0].args[2], {"limit": 25})
        self.assertEqual(fetch_all.call_args_list[1].args[2], {"limit": 25})
        self.assertEqual(fetch_all.call_args_list[2].args[2], {"limit": 25})

    def test_empty_database_returns_stable_empty_contract(self):
        with mock.patch(
            "app.services.run_lineage.fetch_all",
            side_effect=[[], [], [], []],
        ):
            payload = grouped_run_lineage_payload(datasource="malaria", limit=100)

        self.assertEqual(payload["items"], [])
        self.assertEqual(payload["unlinked"], {"evaluations": [], "explainability": []})
        self.assertEqual(payload["conflicts"], {"evaluations": [], "explainability": []})
        self.assertEqual(payload["totals"]["training_runs"], 0)
        self.assertEqual(payload["totals"]["linked_evaluations"], 0)

    def test_children_with_multiple_training_parents_are_reported_as_conflicts(self):
        evaluations = [
            {
                "training_run_id": TRAINING_A,
                "evaluation_run_id": EVALUATION_A,
                "evaluation_run_name": "evaluate:ambiguous",
                "model_name": "densenet121",
                "optimizer": "adamw",
                "checkpoint_path": "outputs/densenet121/best_model.keras",
            },
            {
                "training_run_id": TRAINING_B,
                "evaluation_run_id": EVALUATION_A,
                "evaluation_run_name": "evaluate:ambiguous",
                "model_name": "custom_cnn",
                "optimizer": "adam",
                "checkpoint_path": "outputs/custom_cnn/best_model.keras",
            },
        ]
        explanations = [
            {
                "training_run_id": TRAINING_A,
                "explain_run_id": EXPLAIN_A,
                "explain_run_name": "explain:ambiguous",
                "method": "gradcam",
                "total_explanations": 4,
                "success_count": 4,
                "failed_count": 0,
                "model_name": "densenet121",
                "optimizer": "adamw",
                "checkpoint_path": "outputs/densenet121/best_model.keras",
            },
            {
                "training_run_id": TRAINING_B,
                "explain_run_id": EXPLAIN_A,
                "explain_run_name": "explain:ambiguous",
                "method": "gradcam",
                "total_explanations": 4,
                "success_count": 4,
                "failed_count": 0,
                "model_name": "custom_cnn",
                "optimizer": "adam",
                "checkpoint_path": "outputs/custom_cnn/best_model.keras",
            },
        ]
        with mock.patch(
            "app.services.run_lineage.fetch_all",
            side_effect=[
                [training_row(TRAINING_A, "densenet121")],
                evaluations,
                explanations,
                [],
            ],
        ):
            payload = grouped_run_lineage_payload(datasource="malaria", limit=100)

        self.assertTrue(all(not group["evaluations"] for group in payload["items"]))
        self.assertTrue(all(not group["explainability"] for group in payload["items"]))
        evaluation_conflict = payload["conflicts"]["evaluations"][0]
        self.assertEqual(
            evaluation_conflict["candidate_training_run_ids"],
            [TRAINING_A, TRAINING_B],
        )
        self.assertEqual(evaluation_conflict["confidence"], "unknown")
        self.assertIsNone(evaluation_conflict["model_name"])
        self.assertIsNone(evaluation_conflict["optimizer"])
        self.assertIsNone(evaluation_conflict["checkpoint_path"])
        explanation_conflict = payload["conflicts"]["explainability"][0]
        self.assertEqual(explanation_conflict["methods"], ["gradcam"])
        self.assertEqual(explanation_conflict["total_explanations"], 4)
        self.assertIsNone(explanation_conflict["model_name"])
        self.assertEqual(payload["totals"]["conflicting_evaluations"], 1)
        self.assertEqual(payload["totals"]["conflicting_explainability"], 1)

    def test_route_forwards_datasource_and_limit(self):
        expected = {
            "items": [],
            "unlinked": {"evaluations": [], "explainability": []},
            "totals": {},
        }
        with mock.patch(
            "app.routes.runs.grouped_run_lineage_payload",
            return_value=expected,
        ) as grouped:
            payload = list_grouped_run_lineage(datasource="malaria", limit=50)

        self.assertIs(payload, expected)
        grouped.assert_called_once_with(datasource="malaria", limit=50)

    def test_static_grouped_routes_are_registered_before_dynamic_run_route(self):
        paths = [route.path for route in runs_routes.router.routes]
        dynamic_index = paths.index("/runs/{run_id}")
        self.assertLess(paths.index("/runs/grouped-lineage"), dynamic_index)
        self.assertLess(
            paths.index("/api/runs/grouped-lineage"),
            paths.index("/api/runs/{run_id}"),
        )

    def test_openapi_declares_read_only_endpoint_and_limit_contract(self):
        operation = app.openapi()["paths"]["/runs/grouped-lineage"]["get"]
        parameters = {item["name"]: item for item in operation["parameters"]}
        limit_schema = parameters["limit"]["schema"]

        self.assertEqual(limit_schema["default"], 100)
        self.assertEqual(limit_schema["minimum"], 1)
        self.assertEqual(limit_schema["maximum"], 500)
        self.assertNotIn("post", app.openapi()["paths"]["/runs/grouped-lineage"])


if __name__ == "__main__":
    unittest.main()
