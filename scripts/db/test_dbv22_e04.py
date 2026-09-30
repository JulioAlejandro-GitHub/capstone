"""DBV2.2 SQL-only E-04 regression suite.

exercise/main below retain the existing probe_v2_e4_contract cases and assertions.
Only its seed is replaced: fixed synthetic event/metrics, no application producer,
calibration algorithm, ResultService, credentials or historical environment.
"""

import copy
import itertools
import json
from types import SimpleNamespace
from uuid import uuid4, uuid5

import psycopg
from certify_dbv22 import E, connect, guard, save
from psycopg.types.json import Jsonb
from test_dbv22_server import insert, retained

RUNTIME = "capstone_v2_runtime"


def seed(c):
    ids = retained.fixture(c)
    c.execute("SELECT pg_advisory_xact_lock(120994,1)")
    c.execute(
        "SELECT set_config('capstone.execution_token',%s,true),set_config('capstone.train_owner',%s,true)",
        (str(ids["owner"]), str(ids["owner"])),
    )
    c.execute(
        "UPDATE experiment_execution_gate SET owner=%s,db_pid=pg_backend_pid()",
        (ids["owner"],),
    )
    insert(
        c,
        "train_execution_sessions",
        {
            "run_id": ids["train"],
            "owner": ids["owner"],
            "host": "DBV22-synthetic",
            "parent_pid": 1,
            "configuration": {},
            "dataset": {},
            "environment": {},
            "artifact_root": "synthetic://DBV22",
        },
    )
    event_id = uuid4()
    metrics = {
        "tn": 9,
        "fp": 1,
        "fn": 1,
        "tp": 9,
        "roc_auc_parasitized": 0.9,
        "pr_auc_parasitized": 0.9,
    }
    result = {
        "calibration_split": "val",
        "threshold_source": "validation_calibration",
        "threshold_selected": 0.6,
        "threshold_used": 0.6,
        "default_threshold": 0.5,
        "target_recall": 0.98,
        "default_threshold_metrics": metrics,
        "selected_metrics": metrics,
    }
    ev = {
        "event_type": "calibration_completed",
        "event_id": str(event_id),
        "run_id": str(ids["train"]),
        "schema_version": "run_event_v1",
        "payload": {"result": {"split": "val", "result": result}},
    }
    canonical = json.dumps(ev, sort_keys=True, separators=(",", ":"))
    event = SimpleNamespace(event_id=event_id, to_dict=lambda: copy.deepcopy(ev))
    insert(
        c,
        "train_execution_records",
        {
            "run_id": ids["train"],
            "kind": "e10_event",
            "phase": "run_event_v1",
            "record_key": str(event_id),
            "event_id": event_id,
            "event_sequence": 1,
            "payload": {"canonical_event": canonical},
        },
    )
    calibration_id = uuid4()
    d = retained.evaluation(
        ids,
        id=uuid5(event_id, "calibration_default"),
        run_id=ids["train"],
        dataset_version_id=ids["version"],
        split="val",
        evaluation_role="calibration_default",
        purpose="development",
        dataset_origin_id=None,
        dataset_origin_role=None,
        source_kind="e10",
        source_event_id=event_id,
        event_kind="e10_event",
        event_phase="run_event_v1",
        event_key=str(event_id),
        source_record_phase="run_event_v1",
        source_record_key=str(event_id) + ":calibration_default",
    )
    s = dict(
        d,
        id=uuid5(event_id, "calibration_selected"),
        evaluation_role="calibration_selected",
        threshold_used=0.6,
        threshold_source="validation_calibration",
        calibration_id=calibration_id,
        source_record_key=str(event_id) + ":calibration_selected",
    )
    cal = {
        "run_threshold_calibration_id": calibration_id,
        "run_id": ids["train"],
        "model_version_id": ids["model_version"],
        "threshold_selected": 0.6,
        "target_recall": 0.98,
        "default_evaluation_id": d["id"],
        "selected_evaluation_id": s["id"],
    }
    context = {
        k: str(d[k]) if k in ("model_version_id", "checkpoint_artifact_id") else d[k]
        for k in (
            "model_version_id",
            "checkpoint_artifact_id",
            "protocol_version",
            "protocol_hash",
            "protocol_snapshot",
            "population_hash",
            "input_contract_hash",
            "comparison_contract_hash",
        )
    }
    c.execute(
        "UPDATE runs SET execution_parameters=execution_parameters || %s WHERE id=%s",
        (Jsonb({"e10_v2_evaluation_context_v1": context}), ids["train"]),
    )
    return ids, event, canonical, d, s, cal


def edges():
    t = guard()
    results = []

    def project(c, m):
        insert(c, "evaluations", m)
        retained.metric(
            c,
            m,
            roc_auc_parasitized=0.9,
            pr_auc_parasitized=0.9,
            auc_unavailability_reason=None,
        )

    with connect(t, role=RUNTIME) as c:
        for order in itertools.permutations("cds"):
            c.execute("BEGIN")
            try:
                ids, _ev, _raw, d, s, cal = seed(c)
                for item in order:
                    if item == "c":
                        insert(c, "run_threshold_calibration", cal)
                    else:
                        project(c, d if item == "d" else s)
                c.execute("SET CONSTRAINTS ALL IMMEDIATE")
                results.append(
                    {"name": "insertion_order_" + "".join(order), "passed": True}
                )
            finally:
                c.execute("ROLLBACK")
        # Real COMMIT failure must roll back all fixture rows, not just a savepoint.
        c.execute("BEGIN")
        ids, _ev, _raw, d, s, cal = seed(c)
        project(c, d)
        try:
            c.execute("COMMIT")
        except psycopg.Error as exc:
            assert exc.sqlstate == "P0001" and "E04_PAIR_REQUIRED" in str(exc)
            assert (
                c.execute(
                    "SELECT count(*) AS n FROM runs WHERE id=%s", (ids["train"],)
                ).fetchone()["n"]
                == 0
            )
            results.append(
                {
                    "name": "orphan_COMMIT_atomic_rollback",
                    "passed": True,
                    "sqlstate": exc.sqlstate,
                }
            )
        else:
            raise AssertionError("orphan COMMIT accepted")
    save("e04_edges_dbv22.json", results)


def exercise(c, name):
    ids, event, canonical, d, s, calibration = seed(c)

    def project(member):
        from test_v2_route_a_server import metric

        raw = event.to_dict()["payload"]["result"]["result"][
            "default_threshold_metrics"
            if member["evaluation_role"] == "calibration_default"
            else "selected_metrics"
        ]
        insert(c, "evaluations", member)
        metric(
            c,
            member,
            **{
                k: raw[k]
                for k in (
                    "tn",
                    "fp",
                    "fn",
                    "tp",
                    "roc_auc_parasitized",
                    "pr_auc_parasitized",
                )
            },
            auc_unavailability_reason=None,
        )

    if name == "default_fakes_selection":
        d.update(
            threshold_source="validation_calibration",
            calibration_id=calibration["run_threshold_calibration_id"],
        )
    if name == "default_reuses_calibration":
        d.update(calibration_id=calibration["run_threshold_calibration_id"])
    if name == "default_wrong_threshold":
        d.update(threshold_used=0.4, threshold_source="protocol_numeric")
    if name == "null_input":
        s.update(input_contract_hash=None)
    if name == "snapshot_mismatch":
        s.update(protocol_snapshot={"incompatible": True})
    if name == "different_event":
        s.update(source_event_id=uuid4(), event_key=str(uuid4()))
    if name == "threshold_mismatch":
        s.update(threshold_used=0.7)
    if name == "wrong_calibration_reference":
        s.update(calibration_id=uuid4())
    if name == "default_test":
        d.update(split="test")
    if name == "selected_test":
        s.update(split="test")
    if name == "unauthorized_role":
        d.update(evaluation_role="development")
    if name == "checkpoint_mismatch":
        artifact = uuid4()
        insert(
            c,
            "artifacts",
            {
                "id": artifact,
                "run_id": ids["train"],
                "artifact_type": "checkpoint",
                "path": "synthetic://E4/other",
                "checksum": "b" * 64,
            },
        )
        s.update(checkpoint_artifact_id=artifact, model_version_id=None)
    if name == "dataset_mismatch":
        s.update(dataset_version_id=ids["external_version"])
    if name == "population_mismatch":
        s.update(population_hash="1" * 64)
    if name == "protocol_mismatch":
        s.update(
            protocol_hash="2" * 64,
            protocol_version="incompatible",
            protocol_snapshot={"synthetic_sql_fixture": "incompatible_protocol"},
        )
    if name == "input_contract_mismatch":
        s.update(input_contract_hash="3" * 64)
    if name == "missing_event":
        missing = uuid4()
        s.update(source_event_id=missing, event_key=str(missing))
    if name == "null_event":
        s.update(source_event_id=None, event_key=None)
    if name == "selected_without_threshold_provenance":
        s.update(threshold_source="protocol_numeric", calibration_id=None)
    if name == "null_selected_member":
        calibration.update(selected_evaluation_id=None)
    if name == "null_protocol":
        s.update(protocol_hash=None)
    if name == "null_model_version":
        s.update(model_version_id=None)
    if name == "new_e10_as_legacy":
        for member in (d, s):
            member.update(
                source_kind="legacy",
                source_event_id=None,
                event_kind=None,
                event_phase=None,
                event_key=None,
            )
    if name == "orphan_default":
        project(d)
    elif name == "orphan_selected":
        project(dict(s, threshold_source="protocol_numeric", calibration_id=None))
    else:
        # FK selected -> calibration is immediate; reverse FKs are deferred.
        insert(c, "run_threshold_calibration", calibration)
        project(d)
        project(s)
        if name == "duplicate_member":
            project(dict(s, id=uuid4(), protocol_hash="4" * 64))
        if name == "second_selected_identity":
            project(
                dict(
                    s,
                    id=uuid4(),
                    source_record_key=s["source_record_key"] + ":retry",
                    threshold_used=0.7,
                )
            )
    c.execute("SET CONSTRAINTS ALL IMMEDIATE")
    assert (
        c.execute(
            "SELECT payload->>'canonical_event' AS value FROM "
            "train_execution_records WHERE event_id=%s",
            (event.event_id,),
        ).fetchone()["value"]
        == canonical
    )


def main():
    target = guard()
    cases = [
        "valid_pair",
        "default_test",
        "selected_test",
        "unauthorized_role",
        "checkpoint_mismatch",
        "dataset_mismatch",
        "population_mismatch",
        "protocol_mismatch",
        "input_contract_mismatch",
        "missing_event",
        "null_event",
        "selected_without_threshold_provenance",
        "duplicate_member",
        "second_selected_identity",
        "new_e10_as_legacy",
        "null_selected_member",
        "null_protocol",
        "null_model_version",
        "orphan_default",
        "orphan_selected",
        "default_fakes_selection",
        "default_reuses_calibration",
        "default_wrong_threshold",
        "null_input",
        "snapshot_mismatch",
        "threshold_mismatch",
        "wrong_calibration_reference",
    ]
    results = []
    expected_rejections = {
        "default_test": ("23514", "ck_v2_evaluation_scope"),
        "selected_test": ("23514", "ck_v2_evaluation_scope"),
        "unauthorized_role": ("23514", "v2_evaluations_check_28938a6edbaa"),
        "checkpoint_mismatch": ("P0001", "E04_PAIR_IDENTITY_MISMATCH"),
        "dataset_mismatch": ("P0001", "E04_PAIR_IDENTITY_MISMATCH"),
        "population_mismatch": ("P0001", "E04_PAIR_IDENTITY_MISMATCH"),
        "missing_event": ("P0001", "E04_PAIR_IDENTITY_MISMATCH"),
        "null_event": ("23514", "v2_evaluations_check_3b1acb9be108"),
        "duplicate_member": ("23505", "v2_evaluations_unique_2b29f071653b"),
        "null_selected_member": ("23502", "selected_evaluation_id"),
        "null_protocol": ("23502", "protocol_hash"),
    }
    expected_rejections.update(
        {
            "protocol_mismatch": ("P0001", "E04_PAIR_IDENTITY_MISMATCH"),
            "input_contract_mismatch": ("P0001", "E04_PAIR_IDENTITY_MISMATCH"),
            "snapshot_mismatch": ("P0001", "E04_PAIR_IDENTITY_MISMATCH"),
            "null_model_version": ("P0001", "E04_PAIR_IDENTITY_MISMATCH"),
            "selected_without_threshold_provenance": (
                "23514",
                "ck_e04_selected_source",
            ),
            "second_selected_identity": ("23505", "uq_e04_event_role"),
            "new_e10_as_legacy": ("42501", "E04_LEGACY_MIGRATOR_REQUIRED"),
            "orphan_default": ("P0001", "E04_PAIR_REQUIRED"),
            "orphan_selected": ("23514", "ck_e04_selected_source"),
            "default_fakes_selection": ("23514", "ck_e04_default_source"),
            "default_reuses_calibration": ("23514", "ck_e04_default_source"),
            "default_wrong_threshold": ("23514", "ck_e04_default_source"),
            "null_input": ("23502", "input_contract_hash"),
            "threshold_mismatch": ("P0001", "E04_THRESHOLD_PROVENANCE"),
            "wrong_calibration_reference": ("P0001", "E04_THRESHOLD_PROVENANCE"),
        }
    )
    assert set(cases) - {"valid_pair"} == set(expected_rejections)
    with connect(target, role=RUNTIME) as c:
        assert c.execute("SELECT session_user, current_user").fetchone() == {
            "session_user": RUNTIME,
            "current_user": RUNTIME,
        }
        assert (
            c.execute("SHOW server_version_num").fetchone()["server_version_num"]
            == "170009"
        )
        for name in cases:
            c.execute("BEGIN")
            error = None
            try:
                exercise(c, name)
            except psycopg.Error as exc:
                error = {
                    "sqlstate": exc.sqlstate,
                    "message": str(exc).splitlines()[0],
                    "constraint": exc.diag.constraint_name,
                }
            finally:
                c.execute("ROLLBACK")
            passed = (error is None) if name == "valid_pair" else (error is not None)
            if error is not None and name in expected_rejections:
                state, marker = expected_rejections[name]
                passed = error["sqlstate"] == state and marker in error["message"]
            results.append(
                {
                    "name": name,
                    "passed": passed,
                    "accepted": error is None,
                    "error": error,
                }
            )
            (E / "e04_contract_tests.json").write_text(
                json.dumps(
                    {
                        "scope": "SQL-only synthetic diagnostic; not a producer or integration certificate",
                        "all_fixture_transactions_rolled_back": True,
                        "results": results,
                        "passed": all(row["passed"] for row in results),
                    },
                    indent=2,
                )
                + "\n"
            )
            print(name + ": " + ("PASS" if passed else "FAIL " + str(error)))
    return 0 if all(row["passed"] for row in results) else 1


if __name__ == "__main__":
    status = main()
    if status:
        raise SystemExit(status)
    edges()
