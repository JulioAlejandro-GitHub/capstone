"""C only: pure fixtures, parser checks and mocked boundary assertions; no DB."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fixtures import NOW, base, document, ref, rich, row, uid

from adoption_v2.core import Blocked, canonical, contract, decode, encode
from adoption_v2.ddl import delta
from adoption_v2.execute import apply, private_write
from adoption_v2.planner import build_plan
from adoption_v2.preflight import check_e10


class AdoptionTests(unittest.TestCase):
    def assertBlocked(self, code, s, b):
        with self.assertRaises(Blocked) as caught:
            build_plan(s, b)
        self.assertEqual(caught.exception.code, code)

    def test_empty_scientific_copy_maps_all_tables(self):
        s, b = base()
        p = build_plan(s, b)
        self.assertEqual(len(p["source_inventory"]), 97)
        self.assertEqual(len(p["rows"]), 103)
        self.assertEqual(p["rows"]["models"], s["rows"]["models"])

    def test_rich_mapping_preserves_ids_raw_hashes_and_credentials(self):
        s, b = rich()
        p = build_plan(s, b)
        for t in p["preserved_tables"]:
            self.assertEqual(p["rows"][t], s["rows"][t])
        self.assertEqual(
            p["rows"]["run_clinical_metrics"][0]["run_clinical_metric_id"],
            uid("metric"),
        )
        self.assertEqual(
            p["rows"]["run_configurations"][0]["configuration_hash"],
            json.loads(b["documents"]["configuration_hash"]["raw"]),
        )
        self.assertEqual(p["original_archive"], s)
        self.assertEqual(p["rows"]["training_history"][0]["train_loss"], 0.5)

    def test_planning_is_deterministic_and_does_not_mutate_inputs(self):
        s, b = rich()
        original = copy.deepcopy((s, b))
        a = build_plan(s, b)
        z = build_plan(s, b)
        self.assertEqual(canonical(a), canonical(z))
        self.assertEqual((s, b), original)

    def test_typed_archive_round_trip_no_json_tag_collision(self):
        from decimal import Decimal

        value = {"number": Decimal("1.000"), "json": {"$decimal": "not a number"}}
        self.assertEqual(decode(encode(value)), value)

    def test_all_22_historical_hashes_fail_closed(self):
        for i in range(22):
            s, b = base()
            s["rows"]["schema_migrations"][i]["checksum"] = "0" * 64
            self.assertBlocked("HISTORICAL_CHECKSUM_MISMATCH", s, b)

    def test_missing_and_duplicate_ledger(self):
        s, b = base()
        s["rows"]["schema_migrations"].pop()
        self.assertBlocked("HISTORICAL_LEDGER_CARDINALITY", s, b)
        s, b = base()
        s["rows"]["schema_migrations"][0] = copy.deepcopy(
            s["rows"]["schema_migrations"][1]
        )
        self.assertBlocked("HISTORICAL_CHECKSUM_MISMATCH", s, b)

    def test_legacy_revision_mismatch(self):
        s, b = base()
        s["rows"]["alembic_version"][0]["version_num"] = "pg_v2_baseline"
        self.assertBlocked("LEGACY_REVISION_MISMATCH", s, b)

    def test_schema_drift_even_if_head_matches(self):
        s, b = base()
        s["catalog"]["functions"][0]["definition"] = "damaged"
        self.assertBlocked("LEGACY_SCHEMA_DRIFT", s, b)

    def test_disabled_E10_trigger_rejected(self):
        s, b = base()
        next(t for t in s["catalog"]["triggers"] if t["name"] == "a_train_event_guard")[
            "enabled"
        ] = "D"
        self.assertBlocked("LEGACY_SCHEMA_DRIFT", s, b)

    def test_three_original_models_required(self):
        s, b = base()
        s["rows"]["models"].pop()
        self.assertBlocked("THREE_MODELS_REQUIRED", s, b)

    def test_duplicate_identifiers(self):
        s, b = base()
        s["rows"]["models"].append(copy.deepcopy(s["rows"]["models"][0]))
        self.assertBlocked("DUPLICATE_SOURCE_IDENTIFIER", s, b)

    def test_active_states_and_gate_rejected(self):
        from adoption_v2.preflight import ACTIVE

        for t, (col, states) in ACTIVE.items():
            for state in states:
                s, b = base()
                r = {k: uid(t + k) for k in contract()["primary_keys"][t]}
                r[col] = state
                s["rows"][t] = [r]
                self.assertBlocked("ACTIVE_STATE_FORBIDDEN", s, b)
        s, b = base()
        s["rows"]["experiment_execution_gate"][0]["owner"] = uid("owner")
        self.assertBlocked("EXECUTION_GATE_NOT_FREE", s, b)

    def test_external_missing_provenance(self):
        for k in (
            "dataset_origin_id",
            "dataset_origin_role",
            "population_manifest_uri",
            "population_manifest_sha256",
            "dataset_provenance_uri",
            "dataset_provenance_sha256",
        ):
            s, b = rich()
            v = json.loads(b["documents"]["evaluation"]["raw"])
            v.pop(k)
            document(b, "evaluation", v)
            self.assertBlocked("EXTERNAL_PROVENANCE_MISSING", s, b)

    def test_external_not_mapped_to_val_or_test(self):
        for role in ("development", "calibration_default", "final_test"):
            s, b = rich()
            v = json.loads(b["documents"]["evaluation"]["raw"])
            v["evaluation_role"] = role
            document(b, "evaluation", v)
            self.assertBlocked("EVALUATION_SCOPE_INVALID", s, b)

    def test_document_hash_conflict(self):
        s, b = rich()
        b["documents"]["evaluation"]["raw"] += " "
        self.assertBlocked("DOCUMENT_HASH_MISMATCH", s, b)

    def test_canonical_configuration_hash_conflict(self):
        s, b = rich()
        document(b, "configuration_hash", "0" * 64)
        self.assertBlocked("CONFIGURATION_HASH_MISMATCH", s, b)

    def test_missing_configuration_blocks_not_defaulted(self):
        s, b = rich()
        b["configurations"] = {}
        self.assertBlocked("TRAIN_CONFIGURATION_EVIDENCE_MISSING", s, b)

    def test_missing_measurement_mapping(self):
        s, b = rich()
        b["evaluations"] = []
        self.assertBlocked("UNMAPPED_CLINICAL_METRIC", s, b)

    def test_duplicate_measurement_mapping(self):
        s, b = rich()
        v = copy.deepcopy(b["evaluations"][0])
        v["key"] = "second"
        b["evaluations"].append(v)
        self.assertBlocked("MEASUREMENT_CARDINALITY_CONFLICT", s, b)

    def test_metric_counts_reject_bool_float_negative(self):
        for value in (True, 1.0, -1):
            s, b = rich()
            s["rows"]["run_clinical_metrics"][0]["tn"] = value
            with self.assertRaises(Blocked):
                build_plan(s, b)

    def test_metric_contradiction(self):
        s, b = rich()
        s["rows"]["run_clinical_metrics"][0]["recall_parasitized"] = 0.2
        self.assertBlocked("METRIC_COUNTS_CONFLICT", s, b)

    def test_nullable_projection_preserves_original_zero(self):
        s, b = rich()
        m = s["rows"]["run_clinical_metrics"][0]
        m.update(tp=0, fn=0, recall_parasitized=0)
        p = build_plan(s, b)
        self.assertIsNone(p["rows"]["run_clinical_metrics"][0]["recall_parasitized"])
        self.assertEqual(
            p["original_archive"]["rows"]["run_clinical_metrics"][0][
                "recall_parasitized"
            ],
            0,
        )

    def test_auc_not_invented_from_matrix(self):
        s, b = rich()
        s["rows"]["run_clinical_metrics"][0].pop("pr_auc_parasitized")
        self.assertBlocked("AUC_EVIDENCE_REQUIRED", s, b)

    def test_history_cardinality_conflict(self):
        s, b = rich()
        r = copy.deepcopy(s["rows"]["training_history"][0])
        r["id"] = uid("duplicate-epoch")
        s["rows"]["training_history"].append(r)
        self.assertBlocked("HISTORY_CARDINALITY_CONFLICT", s, b)

    def test_history_alias_conflict(self):
        s, b = rich()
        s["rows"]["training_history"][0]["train_loss"] = 0.1
        self.assertBlocked("HISTORY_ALIAS_CONFLICT", s, b)

    def test_unmapped_matrix_blocks(self):
        s, b = rich()
        s["rows"]["confusion_matrices"] = [{"id": uid("matrix")}]
        self.assertBlocked("UNMAPPED_CONSOLIDATION", s, b)

    def test_matrix_consolidation_keeps_original_id_in_archive(self):
        s, b = rich()
        m = {
            "id": uid("matrix"),
            "run_id": uid("train"),
            "split_name": "external",
            "labels": ["uninfected", "parasitized"],
            "matrix": [[9, 1], [1, 9]],
            "true_negative": 9,
            "false_positive": 1,
            "false_negative": 1,
            "true_positive": 9,
        }
        s["rows"]["confusion_matrices"] = [m]
        b["consolidations"] = [
            {
                "source": ref("confusion_matrices", [m["id"]]),
                "evaluation_id": document(b, "evaluation_id", uid("evaluation")),
            }
        ]
        p = build_plan(s, b)
        self.assertEqual(p["original_archive"]["rows"]["confusion_matrices"][0], m)
        self.assertNotIn("confusion_matrices", p["rows"])

    def test_xai_incomplete_requires_explicit_disposition(self):
        s, b = rich()
        s["rows"]["explainability_results"] = [
            row("explainability_results", id=uid("xai"), method="gradcam")
        ]
        self.assertBlocked("XAI_DISPOSITION_REQUIRED", s, b)
        b["xai_excluded"] = [
            {
                "source": ref("explainability_results", [uid("xai")]),
                "reason": "Synthetic legacy fixture has no input/checkpoint evidence",
            }
        ]
        p = build_plan(s, b)
        self.assertEqual(p["rows"]["xai_evidence"], [])
        self.assertEqual(
            p["rows"]["explainability_results"], s["rows"]["explainability_results"]
        )

    def test_E10_exact_bytes_sequence_and_identity(self):
        event = {
            "event_id": uid("event"),
            "run_id": uid("train"),
            "sequence": 1,
            "event_type": "heartbeat",
            "occurred_at": NOW,
            "payload": {},
            "attempt_id": None,
            "schema_version": "run_event_v1",
        }
        raw = json.dumps(
            event, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        r = {
            "run_id": event["run_id"],
            "kind": "e10_event",
            "phase": "run_event_v1",
            "record_key": event["event_id"],
            "event_id": event["event_id"],
            "event_sequence": 1,
            "payload": {"canonical_event": raw},
        }
        check_e10([r])
        saved = copy.deepcopy(r)
        with self.assertRaises(Blocked):
            check_e10([r, r])
        r["event_sequence"] = 2
        with self.assertRaises(Blocked):
            check_e10([r])
        self.assertEqual(saved["payload"]["canonical_event"], raw)

    def test_C_cannot_open_any_database(self):
        with patch("alembic_v2.safety.inspect_isolation") as inspect:
            with self.assertRaisesRegex(Blocked, "GATE_C_REQUIRED"):
                apply(
                    {"authorized_stage": "E10.10.5C", "gate_c_approved": False},
                    "",
                    {},
                    "/tmp",
                )
            inspect.assert_not_called()

    def test_ddl_parse_and_order_no_stamp_or_guard_disable(self):
        d = delta()
        joined = "\n".join(x for group in d.values() for x in group)
        self.assertNotIn("DISABLE TRIGGER", joined)
        self.assertNotIn("session_replication_role", joined)
        self.assertNotIn("DROP SCHEMA", joined)
        self.assertEqual(sum(x.startswith("DROP TABLE") for x in d["finalize"]), 2)
        self.assertNotIn("UPDATE public.alembic_version", joined)
        self.assertTrue(any("v2_evaluation_complete" in x for x in d["validate"]))

    def test_private_archive_is_exclusive_and_mode_600(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "source.json"
            private_write(p, {"credential": "synthetic"})
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)
            self.assertEqual(
                decode(json.loads(p.read_text())), {"credential": "synthetic"}
            )
            with self.assertRaises(FileExistsError):
                private_write(p, {})
