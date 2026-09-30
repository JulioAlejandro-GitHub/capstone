"""Synthetic PostgreSQL 17 constraint tests; no application configuration or real data."""

import hashlib
import json
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from verify_v2_route_a import RUNTIME, connect, guard, save

RESULTS = []


def insert(c, table, values):
    values = {
        k: Jsonb(v) if isinstance(v, (dict, list)) else v for k, v in values.items()
    }
    c.execute(
        sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            sql.Identifier(table),
            sql.SQL(",").join(map(sql.Identifier, values)),
            sql.SQL(",").join(sql.Placeholder() for _ in values),
        ),
        list(values.values()),
    )


def negative(c, name, action, state, marker):
    try:
        with c.transaction():
            action()
            c.execute("SET CONSTRAINTS ALL IMMEDIATE")
    except psycopg.Error as e:
        passed = e.sqlstate == state and marker in str(e)
        RESULTS.append(
            {
                "name": name,
                "passed": passed,
                "expected_sqlstate": state,
                "expected_marker": marker,
                "sqlstate": e.sqlstate,
                "error": str(e),
            }
        )
        save("server_tests.json", RESULTS)
        assert passed, f"Wrong rejection in {name}: {e}"
    else:
        RESULTS.append(
            {"name": name, "passed": False, "error": "Invalid operation was accepted"}
        )
        save("server_tests.json", RESULTS)
        raise AssertionError(name)


def fixture(c):
    ids = {
        k: uuid4()
        for k in (
            "dataset",
            "version",
            "external_version",
            "model",
            "train",
            "train2",
            "evaluation_run",
            "artifact",
            "artifact2",
            "model_version",
            "owner",
        )
    }
    insert(
        c,
        "datasets",
        {"id": ids["dataset"], "name": "B synthetic only", "source": "route_a_fixture"},
    )
    for key in ("version", "external_version"):
        insert(
            c,
            "dataset_versions",
            {
                "id": ids[key],
                "name": "B synthetic " + key + str(ids[key]),
                "semantic_version": "0.0.0-test",
                "grouping_strategy": "synthetic",
                "grouping_field": "patient",
                "stratification_strategy": "synthetic",
                "split_algorithm": "synthetic",
                "split_algorithm_version": "1",
                "random_seed": 7,
                "target_train_ratio": 0.7,
                "target_val_ratio": 0.15,
                "target_test_ratio": 0.15,
                "positive_class": "parasitized",
            },
        )
    insert(
        c,
        "dataset_version_sources",
        {
            "dataset_version_id": ids["external_version"],
            "dataset_id": ids["dataset"],
            "role": "EXTERNAL_VALIDATION",
        },
    )
    insert(
        c,
        "models",
        {"id": ids["model"], "name": "B synthetic model", "model_type": "custom_cnn"},
    )
    canonical = {
        "optimizer": {
            "name": "adam",
            "parameters": {"learning_rate": 0.001},
            "fine_tune_learning_rate": 0.0001,
        },
        "execution": {
            "batch_size": 8,
            "seed": 7,
            "max_epochs": 2,
            "fine_tune_epochs": 0,
            "calibrate_threshold": False,
        },
        "model": {"dropout": 0.1, "l2": 0.0, "preprocessing": "rescale_0_1"},
        "recipe": {"loss": "binary_crossentropy"},
    }
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    for key in ("train", "train2"):
        insert(
            c,
            "runs",
            {
                "id": ids[key],
                "model_id": ids["model"],
                "dataset_version_id": ids["version"],
                "run_type": "training",
                "status": "completed",
                "random_seed": 7,
                "execution_parameters": {
                    "model_configuration_e2": {
                        "configuration": {
                            "resolved": canonical,
                            "model_id": "custom_cnn",
                            "adapter_version": "fixture-v1",
                        }
                    }
                },
            },
        )
        insert(
            c,
            "run_configurations",
            {
                "run_id": ids[key],
                "architecture": "custom_cnn",
                "adapter_version": "fixture-v1",
                "optimizer": "adam",
                "learning_rate": 0.001,
                "fine_tune_learning_rate": 0.0001,
                "batch_size": 8,
                "random_seed": 7,
                "max_epochs": 2,
                "fine_tune_epochs": 0,
                "early_stopping": False,
                "early_stopping_patience": 0,
                "early_stopping_min_delta": 0,
                "early_stopping_monitor": "val_loss",
                "early_stopping_mode": "min",
                "restore_best_weights": True,
                "checkpoint_monitor": "val_loss",
                "checkpoint_mode": "min",
                "dropout": 0.1,
                "l2": 0,
                "input_height": 32,
                "input_width": 32,
                "input_channels": 3,
                "weights": "none",
                "fine_tune_layers": 0,
                "normalization": "rescale_0_1",
                "loss_function": "binary_crossentropy",
                "calibration_enabled": False,
                "configuration_hash": hashlib.sha256(raw.encode()).hexdigest(),
                "canonical_configuration": raw,
                "provenance_snapshot": {"source": "B synthetic"},
            },
        )
    insert(
        c,
        "runs",
        {
            "id": ids["evaluation_run"],
            "model_id": ids["model"],
            "dataset_version_id": ids["version"],
            "run_type": "evaluation",
            "status": "completed",
        },
    )
    for key, train in [("artifact", "train"), ("artifact2", "train2")]:
        insert(
            c,
            "artifacts",
            {
                "id": ids[key],
                "run_id": ids[train],
                "artifact_type": "checkpoint",
                "path": "synthetic://B/" + key,
                "checksum": "a" * 64,
            },
        )
    insert(
        c,
        "model_versions",
        {
            "id": ids["model_version"],
            "model_id": ids["model"],
            "training_run_id": ids["train"],
            "checkpoint_artifact_id": ids["artifact"],
            "status": "discovered",
        },
    )
    c.execute("SET CONSTRAINTS ALL IMMEDIATE")
    c.execute("SET CONSTRAINTS ALL DEFERRED")
    return ids


def evaluation(ids, **changes):
    e = {
        "id": uuid4(),
        "run_id": ids["evaluation_run"],
        "training_run_id": ids["train"],
        "model_version_id": ids["model_version"],
        "checkpoint_artifact_id": ids["artifact"],
        "dataset_version_id": ids["external_version"],
        "split": "external",
        "evaluation_role": "external_complementary",
        "purpose": "complementary",
        "dataset_origin_id": ids["dataset"],
        "dataset_origin_role": "EXTERNAL_VALIDATION",
        "population_manifest_uri": "synthetic://population",
        "population_manifest_sha256": "a" * 64,
        "dataset_provenance_uri": "synthetic://provenance",
        "dataset_provenance_sha256": "b" * 64,
        "subject_kind": "single",
        "protocol_version": "fixture-v1",
        "protocol_hash": "c" * 64,
        "population_hash": "d" * 64,
        "input_contract_hash": "e" * 64,
        "comparison_contract_hash": "f" * 64,
        "protocol_snapshot": {"synthetic": True},
        "source_kind": "external_record",
        "source_record_key": str(uuid4()),
        "source_record_phase": "route_a",
        "threshold_used": 0.5,
        "threshold_source": "default",
    }
    e.update(changes)
    return e


def metric(c, e, **changes):
    m = {
        "run_id": e["run_id"],
        "evaluation_id": e["id"],
        "split_name": e["split"],
        "tn": 9,
        "fp": 1,
        "fn": 1,
        "tp": 9,
        "roc_auc_parasitized": None,
        "pr_auc_parasitized": None,
        "auc_unavailability_reason": "not_computed",
    }
    m.update(changes)
    insert(c, "run_clinical_metrics", m)


def pair(c, e):
    insert(c, "evaluations", e)
    metric(c, e)


def legacy_pair_suite(t):
    # New authenticated connection; runtime never receives migrator authority.
    with connect(t, role="capstone_v2_migrator") as c:
        assert c.execute("SELECT session_user,current_user").fetchone() == dict(session_user="capstone_v2_migrator",current_user="capstone_v2_migrator")
        c.execute("BEGIN")
        try:
            ids = fixture(c)
            base = evaluation(ids)
            pair(c, base)
            default = evaluation(
                ids,
                split="val",
                purpose="development",
                evaluation_role="calibration_default",
                source_kind="legacy",
                dataset_version_id=ids["version"],
                dataset_origin_id=None,
                dataset_origin_role=None,
            )
            selected = dict(
                default,
                id=uuid4(),
                evaluation_role="calibration_selected",
                threshold_source="protocol_numeric",
                threshold_used=0.6,
                source_record_key=str(uuid4()),
            )
            pair(c, default)
            pair(c, selected)
            calibration = {
                "run_id": ids["train"],
                "threshold_selected": 0.6,
                "target_recall": 0.98,
                "default_evaluation_id": default["id"],
                "selected_evaluation_id": selected["id"],
            }
            insert(c, "run_threshold_calibration", calibration)
            c.execute("SET CONSTRAINTS ALL IMMEDIATE")
            c.execute("SET CONSTRAINTS ALL DEFERRED")
            RESULTS.append({"name": "calibration_VAL_pair_positive", "passed": True})
            for split in ("test", "external", "train", "validation"):
                negative(
                    c,
                    "calibration_rejects_" + split,
                    lambda split=split: insert(
                        c,
                        "run_threshold_calibration",
                        dict(calibration, calibration_split=split),
                    ),
                    "23514",
                    "ck_v2_calibration_val"
                    if split == "validation"
                    else "chk_run_threshold_calibration_split",
                )
            negative(
                c,
                "calibration_pair_cannot_be_same",
                lambda: insert(
                    c,
                    "run_threshold_calibration",
                    dict(calibration, selected_evaluation_id=default["id"]),
                ),
                "P0001",
                "CALIBRATION_PAIR_INVALID",
            )
            negative(
                c,
                "calibration_pair_excludes_external",
                lambda: insert(
                    c,
                    "run_threshold_calibration",
                    dict(calibration, selected_evaluation_id=base["id"]),
                ),
                "P0001",
                "CALIBRATION_PAIR_INVALID",
            )
        finally:
            c.execute("ROLLBACK")


def main():
    t = guard()
    # All behavioral tests run as the minimally privileged runtime.
    with connect(t, role=RUNTIME) as c:
        c.execute("BEGIN")
        try:
            external_before = c.execute(
                "SELECT count(*) AS n FROM vw_v2_external_evidence"
            ).fetchone()["n"]
            comparison_before = c.execute("SELECT count(*) AS n FROM vw_v2_model_comparison").fetchone()['n']
            ids = fixture(c)
            RESULTS.append(
                {"name": "positive_synthetic_training_configuration", "passed": True}
            )
            base = evaluation(ids)
            pair(c, base)
            c.execute("SET CONSTRAINTS ALL IMMEDIATE")
            c.execute("SET CONSTRAINTS ALL DEFERRED")
            assert (
                c.execute(
                    "SELECT split_name FROM run_clinical_metrics WHERE evaluation_id=%s",
                    (base["id"],),
                ).fetchone()["split_name"]
                == "external"
            )
            assert (
                c.execute(
                    "SELECT count(*) AS n FROM vw_v2_external_evidence"
                ).fetchone()["n"]
                == external_before + 1
            )
            assert (
                c.execute(
                    "SELECT count(*) AS n FROM vw_v2_model_comparison"
                ).fetchone()["n"]
                == comparison_before
            )
            RESULTS.append(
                {
                    "name": "A01_external_complementary_cross_dataset_positive_and_view_separation",
                    "passed": True,
                }
            )
            for role in (
                "development",
                "final_test",
                "training_validation_final",
                "calibration_default",
                "calibration_selected",
            ):
                negative(
                    c,
                    "A01_external_rejects_" + role,
                    lambda role=role: insert(
                        c, "evaluations", evaluation(ids, evaluation_role=role)
                    ),
                    "23514",
                    "ck_v2_evaluation_scope",
                )
            for field in (
                "dataset_origin_id",
                "dataset_origin_role",
                "population_manifest_uri",
                "population_manifest_sha256",
                "dataset_provenance_uri",
                "dataset_provenance_sha256",
            ):
                negative(
                    c,
                    "A01_missing_" + field,
                    lambda field=field: insert(
                        c, "evaluations", evaluation(ids, **{field: None})
                    ),
                    "23514",
                    "ck_v2_external_provenance",
                )
            negative(
                c,
                "A01_invalid_provenance_hash",
                lambda: insert(
                    c, "evaluations", evaluation(ids, dataset_provenance_sha256="bad")
                ),
                "23514",
                "ck_v2_external_provenance",
            )
            negative(
                c,
                "A01_origin_FK",
                lambda: insert(
                    c, "evaluations", evaluation(ids, dataset_origin_id=uuid4())
                ),
                "23503",
                "fk_v2_evaluation_dataset_origin",
            )
            negative(
                c,
                "A01_no_external_validation_alias",
                lambda: insert(
                    c, "evaluations", evaluation(ids, split="external_validation")
                ),
                "23514",
                "ck_v2_evaluation_scope",
            )
            negative(
                c,
                "evaluation_immutable",
                lambda: c.execute(
                    "UPDATE evaluations SET protocol_version='changed' WHERE id=%s",
                    (base["id"],),
                ),
                "P0001",
                "V2_SCIENTIFIC_EVIDENCE_IMMUTABLE",
            )
            negative(
                c,
                "training_requires_configuration",
                lambda: insert(
                    c, "runs", {"run_type": "training", "status": "completed"}
                ),
                "P0001",
                "TRAIN_CONFIGURATION_REQUIRED",
            )
            missing = evaluation(ids)
            negative(
                c,
                "evaluation_requires_metrics_at_transaction_end",
                lambda: insert(c, "evaluations", missing),
                "P0001",
                "EVALUATION_METRICS_MISSING",
            )
            negative(
                c,
                "evaluation_checkpoint_training_mismatch",
                lambda: pair(
                    c,
                    evaluation(
                        ids,
                        model_version_id=None,
                        checkpoint_artifact_id=ids["artifact2"],
                    ),
                ),
                "P0001",
                "CHECKPOINT_TRAIN_MISMATCH",
            )
            e10_id = uuid4()
            e10 = evaluation(
                ids,
                run_id=ids["train"],
                dataset_version_id=ids["version"],
                dataset_origin_id=None,
                dataset_origin_role=None,
                split="val",
                purpose="development",
                evaluation_role="training_validation_final",
                source_kind="e10",
                source_event_id=e10_id,
                event_kind="e10_event",
                event_phase="run_event_v1",
                event_key=str(e10_id),
            )
            negative(
                c,
                "E10_missing_record_FK",
                lambda: pair(c, e10),
                "23503",
                "fk_evaluation_e10_record",
            )
            negative(
                c,
                "E10_event_key_identity",
                lambda: insert(
                    c, "evaluations", dict(e10, id=uuid4(), event_key=str(uuid4()))
                ),
                "23514",
                "v2_evaluations_check_3b1acb9be108",
            )
            c.execute("SELECT pg_advisory_xact_lock(120994,1)")
            c.execute(
                "SELECT set_config('capstone.execution_token',%s,true),set_config('capstone.train_owner',%s,true)",
                (str(ids["owner"]), str(ids["owner"])),
            )
            c.execute(
                "UPDATE experiment_execution_gate SET owner=%s,db_pid=pg_backend_pid() WHERE singleton",
                (ids["owner"],),
            )
            insert(
                c,
                "train_execution_sessions",
                {
                    "run_id": ids["train"],
                    "owner": ids["owner"],
                    "host": "synthetic",
                    "parent_pid": 1,
                    "configuration": {},
                    "dataset": {},
                    "environment": {},
                    "artifact_root": "synthetic://B",
                },
            )
            record = {
                "run_id": ids["train"],
                "kind": "e10_event",
                "phase": "run_event_v1",
                "record_key": str(e10_id),
                "event_id": e10_id,
                "event_sequence": 1,
                "payload": {"canonical_event": '{"synthetic":true}'},
            }
            insert(c, "train_execution_records", record)
            pair(c, e10)
            c.execute("SET CONSTRAINTS ALL IMMEDIATE")
            c.execute("SET CONSTRAINTS ALL DEFERRED")
            RESULTS.append({"name": "E10_positive_record_projection", "passed": True})
            negative(
                c,
                "E10_sequence_gap",
                lambda: insert(
                    c, "train_execution_records", dict(record, event_sequence=3)
                ),
                "P0001",
                "RESULT_EVENT_SEQUENCE_INVALID",
            )
            negative(
                c,
                "E10_record_append_only",
                lambda: c.execute(
                    "UPDATE train_execution_records SET payload='{}' WHERE run_id=%s",
                    (ids["train"],),
                ),
                "P0001",
                "TRAIN_RECORD_IMMUTABLE",
            )
            negative(
                c,
                "E10_record_delete_forbidden",
                lambda: c.execute(
                    "DELETE FROM train_execution_records WHERE run_id=%s",
                    (ids["train"],),
                ),
                "P0001",
                "TRAIN_RECORD_IMMUTABLE",
            )
            c.execute(
                "SELECT set_config('capstone.train_owner',%s,true)", (str(uuid4()),)
            )
            negative(
                c,
                "E10_owner_fencing",
                lambda: insert(
                    c, "train_execution_records", dict(record, event_sequence=2)
                ),
                "P0001",
                "TRAIN_OWNER_FENCED",
            )
            c.execute(
                "SELECT set_config('capstone.train_owner',%s,true)",
                (str(ids["owner"]),),
            )
            denied = evaluation(ids, split="val", purpose="development", evaluation_role="calibration_default",
                                source_kind="legacy", dataset_version_id=ids["version"], dataset_origin_id=None, dataset_origin_role=None)
            negative(c, "E04_runtime_legacy_admission", lambda: insert(c, "evaluations", denied), "42501", "E04_LEGACY_MIGRATOR_REQUIRED")
            c.execute("SELECT set_config('capstone.adoption_authorized','true',true)")
            negative(c, "E04_runtime_cannot_self_authorize", lambda: insert(c, "evaluations", denied), "42501", "E04_LEGACY_MIGRATOR_REQUIRED")
            negative(c, "E04_runtime_cannot_set_migrator", lambda: c.execute("SET ROLE capstone_v2_migrator"), "42501", "permission denied")
            legacy_pair_suite(t)
            publication = {
                "id": uuid4(),
                "datasource": "B-synthetic",
                "model_version_id": ids["model_version"],
                "training_run_id": ids["train"],
                "evaluation_run_id": ids["evaluation_run"],
                "checkpoint_artifact_id": ids["artifact"],
            }
            negative(
                c,
                "publication_model_training_FK",
                lambda: insert(
                    c,
                    "stage2_model_publications",
                    dict(
                        publication,
                        id=uuid4(),
                        datasource="B-wrong-train",
                        training_run_id=ids["train2"],
                    ),
                ),
                "23503",
                "fk_stage2_publication_model_training",
            )
            negative(
                c,
                "publication_checkpoint_FK",
                lambda: insert(
                    c,
                    "stage2_model_publications",
                    dict(
                        publication,
                        id=uuid4(),
                        datasource="B-wrong-artifact",
                        checkpoint_artifact_id=ids["artifact2"],
                    ),
                ),
                "23503",
                "fk_stage2_publication_version_artifact",
            )
            negative(
                c,
                "publication_invalid_state",
                lambda: insert(
                    c,
                    "stage2_model_publications",
                    dict(publication, id=uuid4(), is_active=False),
                ),
                "23514",
                "chk_stage2_publication_state",
            )
            insert(c, "stage2_model_publications", publication)
            RESULTS.append(
                {"name": "publication_valid_lineage_positive", "passed": True}
            )
            negative(
                c,
                "publication_one_active_per_model_version",
                lambda: insert(
                    c, "stage2_model_publications", dict(publication, id=uuid4())
                ),
                "23505",
                "uq_stage2_publication_active_version",
            )
            event = {
                "publication_id": publication["id"],
                "event_type": "MODEL_STAGE2_PUBLISHED",
                "model_version_id": ids["model_version"],
                "training_run_id": ids["train"],
                "evaluation_run_id": ids["evaluation_run"],
                "datasource": "B-synthetic",
                "new_status": "active",
            }
            insert(c, "stage2_model_publication_events", event)
            negative(
                c,
                "publication_event_append_only",
                lambda: c.execute(
                    "UPDATE stage2_model_publication_events SET actor='changed'"
                ),
                "P0001",
                "append-only",
            )
            for name, statement in [
                ("no_DDL", "CREATE TABLE public.runtime_forbidden(id int)"),
                ("no_TEMP", "CREATE TEMP TABLE runtime_temp_forbidden(id int)"),
                ("no_TRUNCATE", "TRUNCATE public.datasets"),
                (
                    "no_alembic_write",
                    "UPDATE alembic_version SET version_num='false_head'",
                ),
                (
                    "no_ledger_write",
                    "INSERT INTO schema_migrations(migration_id,checksum) VALUES ('synthetic','bad')",
                ),
            ]:
                negative(
                    c,
                    name,
                    lambda statement=statement: c.execute(statement),
                    "42501",
                    "permission denied",
                )
            c.execute("SET CONSTRAINTS ALL IMMEDIATE")
            RESULTS.append(
                {"name": "all_valid_fixtures_pass_deferred_constraints", "passed": True}
            )
            save("server_tests.json", RESULTS)
        finally:
            c.execute("ROLLBACK")


if __name__ == "__main__":
    main()
