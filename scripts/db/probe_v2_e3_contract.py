"""Diagnose E-03's SQL contract on the attested candidate, never certify it.

Each case has a fresh synthetic fixture and forces every deferred constraint.
All writes roll back, including unexpectedly accepted invalid cases. Exit 1
means a required rejection is absent; it is not a successful negative test.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4, uuid5

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / "docs/audits/e10_10_5e3_evidence/route_a"
sys.path[:0] = [str(ROOT), str(ROOT / "malaria_dl_local_project")]
os.environ["PGV2_EVIDENCE_DIR"] = str(E)
os.environ["PGPASSFILE"] = json.loads((E / "private_paths.json").read_text())["pgpass"]

import psycopg
from test_v2_route_a_server import evaluation, fixture, insert, pair
from verify_v2_route_a import RUNTIME, connect, guard
from src.malaria_dl.execution.contracts import RunEvent, RunEventType
from src.malaria_dl.results.identity import canonical_event


def seed(c):
    ids = fixture(c)
    c.execute("SELECT pg_advisory_xact_lock(120994,1)")
    c.execute(
        "SELECT set_config('capstone.execution_token',%s,true),"
        "set_config('capstone.train_owner',%s,true)",
        (str(ids["owner"]), str(ids["owner"])),
    )
    c.execute("UPDATE experiment_execution_gate SET owner=%s,db_pid=pg_backend_pid()",
              (ids["owner"],))
    insert(c, "train_execution_sessions", dict(
        run_id=ids["train"], owner=ids["owner"], host="E3-synthetic",
        parent_pid=os.getpid(), configuration={}, dataset={}, environment={},
        artifact_root="synthetic://E3",
    ))
    event = RunEvent(event_id=uuid4(), run_id=ids["train"], sequence=1,
                     event_type=RunEventType.CALIBRATION_COMPLETED,
                     occurred_at=datetime.now(timezone.utc),
                     payload={"synthetic_sql_fixture": True})
    canonical = canonical_event(event)
    insert(c, "train_execution_records", dict(
        run_id=event.run_id, kind="e10_event", phase="run_event_v1",
        record_key=str(event.event_id), event_id=event.event_id, event_sequence=1,
        payload={"canonical_event": canonical},
    ))
    calibration_id = uuid4()
    d = evaluation(ids, id=uuid5(event.event_id, "calibration_default"),
        run_id=ids["train"], dataset_version_id=ids["version"], split="val",
        evaluation_role="calibration_default", purpose="development",
        dataset_origin_id=None, dataset_origin_role=None, source_kind="e10",
        source_event_id=event.event_id, event_kind="e10_event", event_phase="run_event_v1",
        event_key=str(event.event_id), source_record_phase="run_event_v1",
        source_record_key=str(event.event_id) + ":calibration_default")
    s = dict(d, id=uuid5(event.event_id, "calibration_selected"),
             evaluation_role="calibration_selected", threshold_used=0.6,
             threshold_source="validation_calibration", calibration_id=calibration_id,
             source_record_key=str(event.event_id) + ":calibration_selected")
    calibration = dict(run_threshold_calibration_id=calibration_id,
        run_id=ids["train"], threshold_selected=0.6, target_recall=0.98,
        default_evaluation_id=d["id"], selected_evaluation_id=s["id"])
    return ids, event, canonical, d, s, calibration


def exercise(c, name):
    ids, event, canonical, d, s, calibration = seed(c)
    if name == "default_test": d.update(split="test")
    if name == "selected_test": s.update(split="test")
    if name == "unauthorized_role": d.update(evaluation_role="development")
    if name == "checkpoint_mismatch":
        artifact = uuid4()
        insert(c, "artifacts", dict(id=artifact, run_id=ids["train"],
            artifact_type="checkpoint", path="synthetic://E3/other", checksum="b" * 64))
        s.update(checkpoint_artifact_id=artifact, model_version_id=None)
    if name == "dataset_mismatch": s.update(dataset_version_id=ids["external_version"])
    if name == "population_mismatch": s.update(population_hash="1" * 64)
    if name == "protocol_mismatch":
        s.update(protocol_hash="2" * 64, protocol_version="incompatible",
                 protocol_snapshot={"synthetic_sql_fixture": "incompatible_protocol"})
    if name == "input_contract_mismatch": s.update(input_contract_hash="3" * 64)
    if name == "missing_event":
        missing = uuid4()
        s.update(source_event_id=missing, event_key=str(missing))
    if name == "null_event": s.update(source_event_id=None, event_key=None)
    if name == "selected_without_threshold_provenance":
        s.update(threshold_source="protocol_numeric", calibration_id=None)
    if name == "null_selected_member": calibration.update(selected_evaluation_id=None)
    if name == "null_protocol": s.update(protocol_hash=None)
    if name == "null_model_version": s.update(model_version_id=None)
    if name == "new_e10_as_legacy":
        for member in (d, s):
            member.update(source_kind="legacy", source_event_id=None,
                          event_kind=None, event_phase=None, event_key=None)
    if name == "orphan_default":
        pair(c, d)
    elif name == "orphan_selected":
        pair(c, dict(s, threshold_source="protocol_numeric", calibration_id=None))
    else:
        # FK selected -> calibration is immediate; reverse FKs are deferred.
        insert(c, "run_threshold_calibration", calibration)
        pair(c, d)
        pair(c, s)
        if name == "duplicate_member":
            pair(c, dict(s, id=uuid4(), protocol_hash="4" * 64))
        if name == "second_selected_identity":
            pair(c, dict(s, id=uuid4(), source_record_key=s["source_record_key"] + ":retry",
                         threshold_source="protocol_numeric", calibration_id=None,
                         threshold_used=0.7))
    c.execute("SET CONSTRAINTS ALL IMMEDIATE")
    assert c.execute("SELECT payload->>'canonical_event' AS value FROM "
        "train_execution_records WHERE event_id=%s", (event.event_id,)).fetchone()["value"] == canonical


def main():
    target = guard()
    cases = ["valid_pair", "default_test", "selected_test", "unauthorized_role",
        "checkpoint_mismatch", "dataset_mismatch", "population_mismatch", "protocol_mismatch",
        "input_contract_mismatch", "missing_event", "null_event",
        "selected_without_threshold_provenance", "duplicate_member", "second_selected_identity",
        "new_e10_as_legacy", "null_selected_member", "null_protocol", "null_model_version",
        "orphan_default", "orphan_selected"]
    results = []
    expected_rejections = {
        "default_test": ("23514", "ck_v2_evaluation_scope"),
        "selected_test": ("23514", "ck_v2_evaluation_scope"),
        "unauthorized_role": ("23514", "v2_evaluations_check_28938a6edbaa"),
        "checkpoint_mismatch": ("P0001", "CALIBRATION_PAIR_INVALID"),
        "dataset_mismatch": ("P0001", "CALIBRATION_PAIR_INVALID"),
        "population_mismatch": ("P0001", "CALIBRATION_PAIR_INVALID"),
        "missing_event": ("23503", "fk_evaluation_e10_record"),
        "null_event": ("23514", "v2_evaluations_check_3b1acb9be108"),
        "duplicate_member": ("23505", "v2_evaluations_unique_2b29f071653b"),
        "null_selected_member": ("23502", "selected_evaluation_id"),
        "null_protocol": ("23502", "protocol_hash"),
    }
    with connect(target, role=RUNTIME) as c:
        assert c.execute("SHOW server_version_num").fetchone()["server_version_num"] == "170009"
        for name in cases:
            c.execute("BEGIN")
            error = None
            try:
                exercise(c, name)
            except psycopg.Error as exc:
                error = dict(sqlstate=exc.sqlstate, message=str(exc).splitlines()[0],
                             constraint=exc.diag.constraint_name)
            finally:
                c.execute("ROLLBACK")
            passed = (error is None) if name == "valid_pair" else (error is not None)
            if error is not None and name in expected_rejections:
                state, marker = expected_rejections[name]
                passed = error["sqlstate"] == state and marker in error["message"]
            results.append(dict(name=name, passed=passed, accepted=error is None, error=error))
            (E / "e03_contract_diagnostic.json").write_text(json.dumps(dict(
                scope="SQL-only synthetic diagnostic; not a producer or integration certificate",
                all_fixture_transactions_rolled_back=True, results=results,
                passed=all(row["passed"] for row in results)), indent=2) + "\n")
            print(name + ": " + ("PASS" if passed else "FAIL (required rejection absent)"))
    return 0 if all(row["passed"] for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
