"""Additional scientific and reconciliation cases using only synthetic memory."""

import copy
import json
import unittest
from unittest.mock import patch

from fixtures import NOW, calibrated, document, explained, ref, rich, uid

from adoption_v2.core import Blocked
from adoption_v2.execute import reconcile
from adoption_v2.planner import build_plan
from adoption_v2.preflight import authorization


class ExtendedTests(unittest.TestCase):
    def test_calibration_VAL_pair_preserves_original(self):
        s, b = calibrated()
        p = build_plan(s, b)
        cal = p["rows"]["run_threshold_calibration"][0]
        self.assertEqual(cal["run_threshold_calibration_id"], uid("calibration"))
        self.assertEqual(cal["default_evaluation_id"], uid("default"))
        self.assertEqual(cal["selected_evaluation_id"], uid("selected"))
        self.assertEqual(p["original_archive"], s)

    def test_calibration_test_and_external_forbidden(self):
        for split in ("test", "external", "validation"):
            s, b = calibrated()
            s["rows"]["run_threshold_calibration"][0]["calibration_split"] = split
            with self.assertRaisesRegex(Blocked, "CALIBRATION_VAL_ONLY"):
                build_plan(s, b)

    def test_calibration_population_and_threshold_conflicts(self):
        for field, value in [("population_hash", "9" * 64), ("threshold_used", 0.3)]:
            s, b = calibrated()
            ctx = json.loads(b["documents"]["selected"]["raw"])
            ctx[field] = value
            document(b, "selected", ctx)
            with self.assertRaisesRegex(Blocked, "CALIBRATION_PAIR_LINEAGE"):
                build_plan(s, b)

    def test_report_consolidation_and_conflict(self):
        s, b = rich()
        r = {
            "id": uid("report"),
            "run_id": uid("train"),
            "split_name": "external",
            "class_name": "parasitized",
            "precision_value": 0.9,
            "recall_value": 0.9,
            "f1_score": 0.9,
            "support": 10,
        }
        s["rows"]["classification_reports"] = [r]
        b["consolidations"] = [
            {
                "source": ref("classification_reports", [r["id"]]),
                "evaluation_id": document(b, "eid", uid("evaluation")),
            }
        ]
        p = build_plan(s, b)
        self.assertEqual(p["original_archive"]["rows"]["classification_reports"], [r])
        r["support"] = 11
        with self.assertRaisesRegex(Blocked, "REPORT_METRIC_CONFLICT"):
            build_plan(s, b)

    def test_xai_complete_lineage(self):
        s, b = explained()
        p = build_plan(s, b)
        self.assertEqual(len(p["rows"]["xai_evidence"]), 1)
        self.assertEqual(
            p["rows"]["explainability_results"], s["rows"]["explainability_results"]
        )
        self.assertEqual(p["rows"]["xai_evidence"][0]["input_sha256"], "2" * 64)

    def test_xai_input_and_checkpoint_conflicts(self):
        for field in ("input_sha256", "checkpoint_sha256"):
            s, b = explained()
            ctx = json.loads(b["documents"]["xai"]["raw"])
            ctx[field] = "9" * 64
            document(b, "xai", ctx)
            with self.assertRaisesRegex(Blocked, "RELATION_CARDINALITY"):
                build_plan(s, b)

    def test_epoch_projection_and_E10_original_payload(self):
        s, b = rich()
        r = s["rows"]
        payload = {
            "epoch": 0,
            "phase": "base",
            "phase_epoch": 0,
            "loss": 0.5,
            "accuracy": 0.9,
        }
        legacy = {
            "run_id": uid("train"),
            "kind": "epoch",
            "phase": "base",
            "record_key": "0",
            "payload": payload,
            "event_id": None,
            "created_at": NOW,
        }
        event = {
            "event_id": uid("epoch_event"),
            "run_id": uid("train"),
            "sequence": 1,
            "event_type": "epoch_completed",
            "occurred_at": NOW,
            "payload": {
                "legacy_record": {
                    k: legacy[k] for k in ("kind", "phase", "record_key")
                },
                "result": copy.deepcopy(payload),
            },
            "attempt_id": None,
            "schema_version": "run_event_v1",
        }
        raw = json.dumps(
            event, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        r["train_execution_records"] = [
            legacy,
            {
                "run_id": uid("train"),
                "kind": "e10_event",
                "phase": "run_event_v1",
                "record_key": event["event_id"],
                "event_id": event["event_id"],
                "event_sequence": 1,
                "payload": {"canonical_event": raw},
                "created_at": NOW,
            },
        ]
        p = build_plan(s, b)
        self.assertEqual(
            p["rows"]["train_execution_records"], r["train_execution_records"]
        )
        self.assertEqual(len(p["rows"]["training_history"]), 1)
        legacy["payload"]["loss"] = 0.7
        with self.assertRaisesRegex(Blocked, "E10_EPOCH_LEGACY_CONFLICT"):
            build_plan(s, b)

    def test_verified_legacy_records_hash_conflict(self):
        s, b = rich()
        s["rows"]["train_execution_sessions"] = [
            {
                "run_id": uid("train"),
                "state": "verified",
                "completion": {"records_hash": "0" * 64},
                "verification": {"records_hash": "0" * 64},
            }
        ]
        with self.assertRaisesRegex(Blocked, "E10_LEGACY_RECORDS_HASH_MISMATCH"):
            build_plan(s, b)

    def test_duplicate_new_evaluation_identifier(self):
        s, b = calibrated()
        v = json.loads(b["documents"]["selected"]["raw"])
        v["id"] = uid("default")
        document(b, "selected", v)
        # A calibration reference becomes invalid first: either blocker is safe.
        with self.assertRaises(Blocked):
            build_plan(s, b)

    def test_incomplete_context_is_explicit_block(self):
        s, b = rich()
        document(b, "evaluation", None)
        with self.assertRaisesRegex(Blocked, "INCOMPLETE_OR_INCOMPATIBLE"):
            build_plan(s, b)

    def test_identity_rejects_operational_url_role_cluster_and_stage(self):
        t = dict(
            authorized_stage="E10.10.5D",
            gate_c_approved=True,
            copy_only=True,
            writers_fenced=True,
            isolation_id=uid("isolation"),
            container_id="1" * 64,
            database="capstone_v2_isolated_synthetic",
            volume="capstone_v2_isolated_synthetic",
            host_port=55599,
            database_oid=123,
            postgres_system_identifier="12345",
            origin_system_identifier="12344",
            migration_role="capstone_v2_migrator",
            runtime_role="capstone_v2_runtime",
            **{
                k: "2" * 64
                for k in (
                    "backup_sha256",
                    "mapping_sha256",
                    "source_inventory_sha256",
                    "legacy_schema_sha256",
                )
            },
        )
        url = "postgresql+psycopg://capstone_v2_migrator@127.0.0.1:55599/capstone_v2_isolated_synthetic"
        self.assertEqual(authorization(t, url), t)
        for k, v in [
            ("authorized_stage", "E10.10.5C"),
            ("gate_c_approved", False),
            ("host_port", 5432),
            ("postgres_system_identifier", "12344"),
            ("writers_fenced", False),
            ("migration_role", "postgres"),
            ("isolation_id", "bad"),
        ]:
            bad = dict(t)
            bad[k] = v
            with self.assertRaises(Blocked):
                authorization(bad, url)
        for bad in (
            url.replace("127.0.0.1", "localhost"),
            url + "?options=-csearch_path=other",
            url.replace("55599", "invalid"),
            url.replace("capstone_v2_migrator", "capstone_v2_runtime"),
        ):
            with self.assertRaises(Blocked):
                authorization(t, bad)

    def test_reconciliation_detects_catalog_and_protected_drift(self):
        s, b = rich()
        p = build_plan(s, b)

        class Memory:
            def execute(self, sql):
                name = sql.split('"')[1]
                self.rows = p["rows"][name]
                return self

            def fetchall(self):
                return self.rows

        with (
            patch(
                "adoption_v2.execute.catalog_snapshot", return_value={"synthetic": True}
            ),
            patch(
                "adoption_v2.execute.certified_catalog",
                return_value={"synthetic": True},
            ),
        ):
            self.assertEqual(reconcile(Memory(), p)["users"]["count"], 1)
        with (
            patch("adoption_v2.execute.catalog_snapshot", return_value={"drift": True}),
            patch(
                "adoption_v2.execute.certified_catalog",
                return_value={"synthetic": True},
            ),
            self.assertRaisesRegex(Blocked, "FINAL_CATALOG_MISMATCH"),
        ):
            reconcile(Memory(), p)

        class Corrupt(Memory):
            def fetchall(self):
                value = copy.deepcopy(self.rows)
                if value and "password_hash" in value[0]:
                    value[0]["password_hash"] = "changed"
                return value

        with self.assertRaisesRegex(Blocked, "PROTECTED_RECONCILIATION_FAILED"):
            reconcile(Corrupt(), p)

    def test_E10_evaluation_projection_matches_canonical_payload(self):
        s, b = rich()
        r = s["rows"]
        ctx = json.loads(b["documents"]["evaluation"]["raw"])
        for k in (
            "dataset_origin_id",
            "dataset_origin_role",
            "population_manifest_uri",
            "population_manifest_sha256",
            "dataset_provenance_uri",
            "dataset_provenance_sha256",
        ):
            ctx.pop(k)
        ctx.update(
            split="val",
            purpose="development",
            evaluation_role="training_validation_final",
            source_kind="e10",
            source_event_id=uid("evaluation_event"),
            event_kind="e10_event",
            event_phase="run_event_v1",
            event_key=uid("evaluation_event"),
        )
        document(b, "evaluation", ctx)
        r["run_clinical_metrics"][0]["split_name"] = "val"
        payload = {
            "schema_version": "validation_evaluation_v1",
            "split": "val",
            "evaluation_role": "training_validation_final",
            "confusion_matrix": {"tn": 9, "fp": 1, "fn": 1, "tp": 9},
            "metrics": {"roc_auc": None, "pr_auc": None},
            "threshold": {"value": 0.5, "source": "default"},
            "n_samples": 20,
        }
        event = {
            "event_id": uid("evaluation_event"),
            "run_id": uid("train"),
            "sequence": 1,
            "event_type": "evaluation_completed",
            "occurred_at": NOW,
            "payload": payload,
            "attempt_id": None,
            "schema_version": "run_event_v1",
        }
        raw = json.dumps(
            event, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        r["train_execution_records"] = [
            {
                "run_id": uid("train"),
                "kind": "e10_event",
                "phase": "run_event_v1",
                "record_key": event["event_id"],
                "event_id": event["event_id"],
                "event_sequence": 1,
                "payload": {"canonical_event": raw},
                "created_at": NOW,
            }
        ]
        p = build_plan(s, b)
        self.assertEqual(
            p["rows"]["train_execution_records"], r["train_execution_records"]
        )
        payload["metrics"]["roc_auc"] = 0.9
        r["train_execution_records"][0]["payload"]["canonical_event"] = json.dumps(
            event, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        with self.assertRaisesRegex(Blocked, "E10_SCIENTIFIC_VALUE_CONFLICT"):
            build_plan(s, b)

    def test_delta_preserves_physical_column_order(self):
        from adoption_v2.core import contract, target

        spec = contract()
        for table in (
            e
            for e in target()[0]["statements"]
            if e["kind"] == "table" and e["name"] in spec["tables"]
        ):
            original = [
                r["column_name"]
                for r in sorted(
                    spec["expected_schema"]["columns"],
                    key=lambda r: r["ordinal_position"],
                )
                if r["table_name"] == table["name"]
            ]
            installed = original + [k for k in table["columns"] if k not in original]
            self.assertEqual(installed, list(table["columns"]), table["name"])
