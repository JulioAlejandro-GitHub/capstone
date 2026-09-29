"""Invented fixtures only. Never reads users, datasets, credentials or DB connections."""

import json
from copy import deepcopy
from decimal import Decimal

from adoption_v2.core import contract, sha, stable_id, target

NOW = "2026-01-01T00:00:00+00:00"


def uid(name):
    return stable_id("synthetic_fixture", name)


def row(table, **values):
    cols = next(
        e["columns"]
        for e in target()[0]["statements"]
        if e["kind"] == "table" and e["name"] == table
    )
    result = {}
    for k, v in cols.items():
        if not v["nullable"] and v["default"] is None and not v["generated"]:
            typ = v["type"]
            result[k] = (
                {}
                if typ == "jsonb"
                else False
                if typ == "boolean"
                else 1
                if typ in ("integer", "bigint", "smallint", "numeric")
                else uid(table + k)
                if typ == "uuid"
                else "synthetic"
            )
    result.update(values)
    return result


def base():
    spec = contract()
    rows = {t: [] for t in spec["tables"]}
    rows["alembic_version"] = [{"version_num": "20260922_01"}]
    rows["schema_migrations"] = [
        {
            "migration_id": k,
            "checksum": v,
            "applied_at": NOW,
            "execution_metadata": {"synthetic": True},
        }
        for k, v in spec["historical_ledger"].items()
    ]
    rows["experiment_execution_gate"] = [
        row(
            "experiment_execution_gate",
            singleton=True,
            owner=None,
            db_pid=None,
            blocked_reason=None,
            process_evidence={},
            updated_at=NOW,
        )
    ]
    rows["models"] = [
        row(
            "models",
            id=uid(name),
            name=name,
            model_type=name,
            metadata={"synthetic": True},
        )
        for name in ("custom_cnn", "vgg16", "densenet121")
    ]
    rows["users"] = [
        row(
            "users",
            id=uid("user"),
            email="synthetic@example.invalid",
            password_hash="SYNTHETIC-NOT-A-CREDENTIAL",
        )
    ]
    return {"catalog": deepcopy(spec["expected_schema"]), "rows": rows}, {
        "documents": {},
        "configurations": {},
        "evaluations": [],
        "calibrations": {},
        "consolidations": [],
        "xai": [],
        "xai_excluded": [],
    }


def document(bindings, name, value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"))
    bindings["documents"][name] = {"raw": raw, "sha256": sha(raw)}
    return {"document": name, "path": []}


def ref(table, key, path=()):
    return {"table": table, "key": [str(k) for k in key], "path": list(path)}


def rich():
    s, b = base()
    r = s["rows"]
    run = uid("train")
    dataset = uid("dataset")
    version = uid("version")
    artifact = uid("checkpoint")
    model = uid("custom_cnn")
    mv = uid("model_version")
    resolved = {
        "model": {
            "input_shape": [32, 32, 3],
            "dropout": 0.1,
            "l2": 0.0,
            "weights": "none",
            "fine_tune_layers": 0,
            "preprocessing": "rescale_0_1",
        },
        "optimizer": {
            "name": "adam",
            "parameters": {"learning_rate": 0.001, "epsilon": 1e-7},
            "fine_tune_learning_rate": 0.0001,
        },
        "execution": {
            "seed": 7,
            "batch_size": 8,
            "max_epochs": 2,
            "fine_tune_epochs": 0,
            "early_stopping": False,
            "early_stopping_patience": 0,
            "early_stopping_min_delta": 0.0,
            "restore_best_weights": True,
            "calibrate_threshold": False,
            "target_recall": 0.98,
        },
        "selection": {
            "monitor": "val_loss",
            "mode": "min",
            "early_stopping_monitor": "val_loss",
            "early_stopping_mode": "min",
            "threshold": 0.5,
        },
        "input_contract": {"internal": {"mode": None}},
        "recipe": {"loss": "binary_crossentropy"},
    }
    raw = json.dumps(resolved, sort_keys=True, separators=(",", ":"))
    cfg = {
        "model_id": "custom_cnn",
        "adapter_version": "synthetic-v1",
        "resolved": resolved,
        "requested": {},
        "provenance": {},
    }
    r["datasets"] = [row("datasets", id=dataset, name="synthetic only")]
    r["dataset_versions"] = [
        row(
            "dataset_versions",
            id=version,
            name="synthetic",
            semantic_version="0.0.0",
            status="FROZEN",
            class_mapping={},
            methodology_json={},
            random_seed=7,
            target_train_ratio=Decimal(".7"),
            target_val_ratio=Decimal(".15"),
            target_test_ratio=Decimal(".15"),
        )
    ]
    r["dataset_version_sources"] = [
        row(
            "dataset_version_sources",
            dataset_version_id=version,
            dataset_id=dataset,
            role="EXTERNAL_VALIDATION",
        )
    ]
    r["runs"] = [
        row(
            "runs",
            id=run,
            run_type="training",
            status="completed",
            model_id=model,
            dataset_version_id=version,
            random_seed=7,
            parameters={"note": "preserve"},
            execution_parameters={"model_configuration_e2": {"configuration": cfg}},
            created_at=NOW,
        )
    ]
    b["configurations"][run] = {
        "canonical": document(b, "canonical", raw),
        "sha256": document(b, "configuration_hash", sha(raw)),
    }
    r["artifacts"] = [
        row(
            "artifacts",
            id=artifact,
            run_id=run,
            artifact_type="checkpoint",
            path="synthetic://checkpoint",
            checksum="a" * 64,
            file_size_bytes=42,
        )
    ]
    r["model_versions"] = [
        row(
            "model_versions",
            id=mv,
            model_id=model,
            training_run_id=run,
            checkpoint_artifact_id=artifact,
            artifact_sha256="a" * 64,
        )
    ]
    ctx = {
        "id": uid("evaluation"),
        "run_id": run,
        "training_run_id": run,
        "model_version_id": mv,
        "checkpoint_artifact_id": artifact,
        "dataset_version_id": version,
        "split": "external",
        "purpose": "complementary",
        "evaluation_role": "external_complementary",
        "subject_kind": "single",
        "protocol_version": "synthetic-v1",
        "protocol_hash": "b" * 64,
        "population_hash": "c" * 64,
        "input_contract_hash": "d" * 64,
        "comparison_contract_hash": "e" * 64,
        "protocol_snapshot": {"synthetic": True},
        "source_kind": "legacy",
        "source_record_key": "synthetic-evaluation",
        "source_record_phase": "legacy",
        "threshold_used": 0.5,
        "threshold_source": "default",
        "created_at": NOW,
        "auc_unavailability_reason": "not_computed",
        "dataset_origin_id": dataset,
        "dataset_origin_role": "EXTERNAL_VALIDATION",
        "population_manifest_uri": "synthetic://population",
        "population_manifest_sha256": "f" * 64,
        "dataset_provenance_uri": "synthetic://provenance",
        "dataset_provenance_sha256": "1" * 64,
    }
    metric = {
        "run_clinical_metric_id": uid("metric"),
        "run_id": run,
        "split_name": "external",
        "tn": 9,
        "fp": 1,
        "fn": 1,
        "tp": 9,
        "roc_auc_parasitized": None,
        "pr_auc_parasitized": None,
        "created_at": NOW,
    }
    r["run_clinical_metrics"] = [metric]
    b["evaluations"] = [
        {
            "key": "synthetic",
            "context": document(b, "evaluation", ctx),
            "measurement": ref(
                "run_clinical_metrics", [metric["run_clinical_metric_id"]]
            ),
        }
    ]
    r["training_history"] = [
        row(
            "training_history",
            id=uid("epoch"),
            run_id=run,
            phase="base",
            epoch=0,
            loss=0.5,
            accuracy=0.9,
            train_loss=None,
            train_accuracy=None,
        )
    ]
    return s, b


def calibrated():
    s, b = rich()
    r = s["rows"]
    ctx = json.loads(b["documents"]["evaluation"]["raw"])
    cid = uid("calibration")
    r["run_clinical_metrics"] = []
    b["evaluations"] = []
    for label, threshold, role in [
        ("default", 0.5, "calibration_default"),
        ("selected", 0.4, "calibration_selected"),
    ]:
        e = dict(
            ctx,
            id=uid(label),
            split="val",
            purpose="development",
            evaluation_role=role,
            source_record_key=label,
            threshold_used=threshold,
            threshold_source="default"
            if label == "default"
            else "validation_calibration",
        )
        for k in (
            "dataset_origin_id",
            "dataset_origin_role",
            "population_manifest_uri",
            "population_manifest_sha256",
            "dataset_provenance_uri",
            "dataset_provenance_sha256",
        ):
            e.pop(k)
        if label == "selected":
            e["calibration_id"] = cid
        metric = {
            "run_clinical_metric_id": uid("metric" + label),
            "run_id": uid("train"),
            "split_name": "val",
            "tn": 9,
            "fp": 1,
            "fn": 1,
            "tp": 9,
            "roc_auc_parasitized": None,
            "pr_auc_parasitized": None,
            "created_at": NOW,
        }
        r["run_clinical_metrics"].append(metric)
        b["evaluations"].append(
            {
                "key": label,
                "context": document(b, label, e),
                "measurement": ref(
                    "run_clinical_metrics", [metric["run_clinical_metric_id"]]
                ),
            }
        )
    c = {
        "run_threshold_calibration_id": cid,
        "run_id": uid("train"),
        "calibration_split": "val",
        "default_threshold": 0.5,
        "target_recall": 0.98,
        "threshold_selected": 0.4,
    }
    r["run_threshold_calibration"] = [c]
    b["calibrations"][cid] = {
        k: document(b, k, uid(label))
        for k, label in [
            ("default_evaluation_id", "default"),
            ("selected_evaluation_id", "selected"),
        ]
    }
    return s, b


def explained():
    s, b = rich()
    r = s["rows"]
    parent = {
        "id": uid("xai"),
        "run_id": uid("train"),
        "prediction_id": None,
        "method": "gradcam",
    }
    r["explainability_results"] = [parent]
    a = row(
        "artifacts",
        id=uid("input"),
        run_id=uid("train"),
        artifact_type="input",
        path="synthetic://input",
        checksum="2" * 64,
        file_size_bytes=9,
    )
    r["artifacts"].append(a)
    x = {
        "model_version_id": uid("model_version"),
        "checkpoint_artifact_id": uid("checkpoint"),
        "method": "gradcam",
        "method_version": "synthetic-v1",
        "implementation_path": "synthetic.py",
        "source_commit": "3" * 40,
        "method_configuration": {},
        "configuration_hash": "4" * 64,
        "input_contract": {},
        "input_contract_hash": "5" * 64,
        "input_storage_uri": a["path"],
        "input_sha256": a["checksum"],
        "checkpoint_sha256": "a" * 64,
        "target_class": 1,
        "explained_output": "probability_parasitized",
        "processing_stage": "raw",
        "environment_snapshot": {"synthetic": True},
        "generated_at": NOW,
        "run_id": uid("train"),
        "ml_explanation_id": parent["id"],
        "input_artifact_id": a["id"],
        "evaluation_id": uid("evaluation"),
    }
    b["xai"] = [
        {
            "parent": ref("explainability_results", [parent["id"]]),
            "context": document(b, "xai", x),
            "artifacts": [],
        }
    ]
    return s, b
