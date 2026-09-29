"""Deterministic complete row plan and reconciliation, independent of empty baseline."""

import json
from copy import deepcopy
from decimal import Decimal

from .core import (
    MANIFEST_HASH,
    Blocked,
    Evidence,
    contract,
    digest,
    number,
    require,
    row_key,
    stable_id,
    table_digest,
    target,
)
from .preflight import preflight
from .transforms import (
    RATES,
    RESERVED,
    calibration,
    configuration,
    evaluation,
    history,
    measurement,
)


def lookup(rows, table, **where):
    found = [
        r for r in rows[table] if all(str(r.get(k)) == str(v) for k, v in where.items())
    ]
    require(len(found) == 1, "RELATION_CARDINALITY", table)
    return found[0]


def validate_relations(rows):
    for e in rows["evaluations"]:
        tr = lookup(rows, "runs", id=e["training_run_id"])
        require(tr["run_type"] == "training", "EVALUATION_TRAIN_REQUIRED")
        require(
            e["split"] == "external"
            or e["dataset_version_id"] == tr["dataset_version_id"],
            "EVALUATION_DATASET_MISMATCH",
        )
        if e.get("checkpoint_artifact_id"):
            lookup(
                rows,
                "artifacts",
                id=e["checkpoint_artifact_id"],
                run_id=e["training_run_id"],
            )
        if e.get("model_version_id"):
            lookup(
                rows,
                "model_versions",
                id=e["model_version_id"],
                training_run_id=e["training_run_id"],
                checkpoint_artifact_id=e.get("checkpoint_artifact_id"),
            )
        lookup(rows, "run_clinical_metrics", evaluation_id=e["id"], run_id=e["run_id"])
        if e["split"] == "external":
            lookup(
                rows,
                "dataset_version_sources",
                dataset_version_id=e["dataset_version_id"],
                dataset_id=e["dataset_origin_id"],
                role=e["dataset_origin_role"],
            )
        if e["source_kind"] == "e10":
            record = lookup(
                rows,
                "train_execution_records",
                run_id=e["run_id"],
                kind=e["event_kind"],
                phase=e["event_phase"],
                record_key=e["event_key"],
                event_id=e["source_event_id"],
            )
            event = json.loads(record["payload"]["canonical_event"])
            require(
                event["event_type"] == "evaluation_completed", "E10_EVENT_TYPE_MISMATCH"
            )
            m = lookup(rows, "run_clinical_metrics", evaluation_id=e["id"])
            require(
                event["payload"].get("schema_version") == "validation_evaluation_v1",
                "E10_SCIENTIFIC_VERSION_INVALID",
            )
            checked = measurement(
                event["payload"],
                dict(e, auc_unavailability_reason=m["auc_unavailability_reason"]),
                e["id"],
            )
            for field in (
                "tn",
                "fp",
                "fn",
                "tp",
                "roc_auc_parasitized",
                "pr_auc_parasitized",
            ):
                require(
                    checked[field] == m[field], "E10_SCIENTIFIC_VALUE_CONFLICT", field
                )
            for k in ("tn", "fp", "fn", "tp"):
                require(
                    event["payload"]["confusion_matrix"][k] == m[k],
                    "E10_PROJECTION_CONFLICT",
                    k,
                )
            require(
                event["payload"]["split"] == e["split"]
                and event["payload"]["evaluation_role"] == e["evaluation_role"]
                and event["payload"]["threshold"]
                == {"value": e["threshold_used"], "source": e["threshold_source"]},
                "E10_PROJECTION_CONTEXT_CONFLICT",
            )
        if e["source_kind"] == "assessment":
            attempt = lookup(
                rows, "assessment_attempts", id=e["source_assessment_attempt_id"]
            )
            identity = lookup(rows, "assessment_identities", id=attempt["identity_id"])
            require(
                attempt["state"] == "verified"
                and identity["kind"] == "evaluate"
                and identity["training_run_id"] == e["training_run_id"]
                and identity["identity"]["split"] == e["split"]
                and identity["identity"]["purpose"] == e["purpose"],
                "ASSESSMENT_PROJECTION_MISMATCH",
            )
            if e["split"] == "test":
                lock = lookup(
                    rows,
                    "assessment_final_locks",
                    identity_hash=identity["identity_hash"],
                )
                require(
                    lock["evidence"]["candidate"] == identity["identity"]["model"]
                    and lock["evidence"]["decision"]
                    == identity["identity"]["decision"],
                    "TEST_FINAL_LOCK_MISMATCH",
                )
        if e["threshold_source"] == "validation_calibration":
            cal = lookup(
                rows,
                "run_threshold_calibration",
                run_threshold_calibration_id=e["calibration_id"],
                run_id=e["training_run_id"],
                calibration_split="val",
            )
            require(
                number(cal["threshold_selected"], "threshold")
                == number(e["threshold_used"], "threshold"),
                "CALIBRATION_THRESHOLD_MISMATCH",
            )
        members = [
            r
            for r in rows["evaluation_ensemble_members"]
            if r["evaluation_id"] == e["id"]
        ]
        require(
            (
                not members
                if e["subject_kind"] == "single"
                else len(members) >= 2
                and sum(number(r["weight"], "weight") for r in members) == 1
            ),
            "ENSEMBLE_CARDINALITY_OR_WEIGHT",
        )
        for m in members:
            require(number(m["weight"], "weight") > 0, "ENSEMBLE_WEIGHT_INVALID")
            mv = lookup(
                rows,
                "model_versions",
                id=m["model_version_id"],
                checkpoint_artifact_id=m["checkpoint_artifact_id"],
            )
            train = lookup(rows, "runs", id=mv["training_run_id"])
            require(
                train["dataset_version_id"] == tr["dataset_version_id"],
                "ENSEMBLE_TRAIN_DATASET_CONFLICT",
            )
    for pub in rows["stage2_model_publications"]:
        lookup(
            rows,
            "model_versions",
            id=pub["model_version_id"],
            training_run_id=pub["training_run_id"],
            checkpoint_artifact_id=pub["checkpoint_artifact_id"],
        )


def xai_project(binding, evidence, rows):
    from .core import target

    parent = evidence.get(binding["parent"])
    p = binding["parent"]
    table = p.get("table")
    require(
        table in ("explainability_results", "cell_explanations", "assessment_results")
        and p["path"] == [],
        "XAI_PARENT_REFERENCE_REQUIRED",
    )
    x = deepcopy(evidence.get(binding["context"]))
    x.setdefault("id", stable_id("xai", (table, p["key"])))
    cols = next(
        e["columns"]
        for e in target()[0]["statements"]
        if e["kind"] == "table" and e["name"] == "xai_evidence"
    )
    require(
        all(k in x and x[k] is not None for k, v in cols.items() if not v["nullable"]),
        "XAI_CONTEXT_INCOMPLETE",
    )
    parents = [
        bool(x.get("ml_explanation_id")),
        bool(x.get("cell_explanation_id")),
        bool(x.get("assessment_attempt_id")),
    ]
    require(sum(parents) == 1, "XAI_PARENT_XOR")
    if table == "explainability_results":
        require(
            x.get("ml_explanation_id") == parent["id"]
            and x.get("run_id") == parent.get("run_id")
            and x.get("prediction_id") == parent.get("prediction_id")
            and x["method"] == parent["method"].lower(),
            "XAI_PARENT_MISMATCH",
        )
    if table == "cell_explanations":
        require(
            x.get("cell_explanation_id") == parent["id"]
            and x.get("cell_prediction_id") == parent["cell_prediction_id"]
            and x["method"] == parent["method"].lower(),
            "XAI_PARENT_MISMATCH",
        )
    if table == "assessment_results":
        require(
            x.get("assessment_attempt_id") == parent["attempt_id"]
            and x.get("assessment_sample_id") == parent["sample_id"],
            "XAI_PARENT_MISMATCH",
        )
    require(
        sum(
            x.get(k) is not None
            for k in (
                "dataset_source_record_id",
                "input_artifact_id",
                "microscopy_image_id",
            )
        )
        == 1,
        "XAI_INPUT_XOR",
    )
    version = lookup(
        rows,
        "model_versions",
        id=x["model_version_id"],
        checkpoint_artifact_id=x["checkpoint_artifact_id"],
        artifact_sha256=x["checkpoint_sha256"],
    )
    if x.get("prediction_id"):
        prediction = lookup(rows, "predictions", id=x["prediction_id"])
        require(
            (
                prediction.get("model_version_id")
                or prediction.get("classifier_model_version_id")
            )
            == x["model_version_id"],
            "XAI_PREDICTION_MODEL_MISMATCH",
        )
    if x.get("assessment_attempt_id"):
        attempt = lookup(
            rows, "assessment_attempts", id=x["assessment_attempt_id"], state="verified"
        )
        identity = lookup(
            rows,
            "assessment_identities",
            id=attempt["identity_id"],
            kind="explain",
            training_run_id=version["training_run_id"],
        )["identity"]
        require(
            x["assessment_sample_id"] == x.get("dataset_source_record_id")
            and identity["explanation"]["method"] == x["method"]
            and identity["explanation"]["class"] == x["target_class"]
            and identity["model"]["sha256"] == x["checkpoint_sha256"],
            "XAI_ASSESSMENT_IDENTITY_MISMATCH",
        )
    if x.get("evaluation_id"):
        ev = lookup(rows, "evaluations", id=x["evaluation_id"])
        single = (
            ev.get("model_version_id") == x["model_version_id"]
            or (
                ev.get("model_version_id") is None
                and ev["training_run_id"] == version["training_run_id"]
            )
        ) and ev.get("checkpoint_artifact_id") == x["checkpoint_artifact_id"]
        ensemble = ev["subject_kind"] == "ensemble" and any(
            m["evaluation_id"] == ev["id"]
            and m["model_version_id"] == x["model_version_id"]
            and m["checkpoint_artifact_id"] == x["checkpoint_artifact_id"]
            for m in rows["evaluation_ensemble_members"]
        )
        require(single or ensemble, "XAI_EVALUATION_MISMATCH")
    if x.get("dataset_source_record_id"):
        lookup(
            rows,
            "dataset_source_records",
            id=x["dataset_source_record_id"],
            source_file_sha256=x["input_sha256"],
        )
    if x.get("input_artifact_id"):
        origin = lookup(
            rows, "artifacts", id=x["input_artifact_id"], checksum=x["input_sha256"]
        )
        require(
            x["input_storage_uri"] in (origin.get("path"), origin.get("artifact_uri")),
            "XAI_INPUT_URI_MISMATCH",
        )
    if x.get("cell_prediction_id"):
        prediction = lookup(rows, "cell_predictions", id=x["cell_prediction_id"])
        lookup(
            rows,
            "cell_classification_inputs",
            id=prediction["classification_input_id"],
            microscopy_image_id=x["microscopy_image_id"],
            crop_sha256=x["input_sha256"],
        )
        lookup(
            rows,
            "cell_classification_runs",
            id=prediction["classification_run_id"],
            model_registry_id=x["model_version_id"],
        )
    elif x.get("microscopy_image_id"):
        lookup(
            rows,
            "microscopy_images",
            id=x["microscopy_image_id"],
            sha256=x["input_sha256"],
        )
    if x["method"] == "shap":
        require(
            x.get("background_manifest_uri") and x.get("background_manifest_sha256"),
            "XAI_BACKGROUND_REQUIRED",
        )
    require(
        x["method"] in ("gradcam", "shap", "lime")
        and type(x["target_class"]) is int
        and x["target_class"] in (0, 1),
        "XAI_METHOD_TARGET_INVALID",
    )
    import re

    for field in (
        "configuration_hash",
        "input_contract_hash",
        "input_sha256",
        "checkpoint_sha256",
    ):
        require(
            re.fullmatch("[0-9a-f]{64}", x[field]) is not None,
            "XAI_HASH_INVALID",
            field,
        )
    artifacts = []
    for ref in binding["artifacts"]:
        a = deepcopy(evidence.get(ref))
        a.setdefault(
            "id", stable_id("xai_artifact", (x["id"], a["role"], a["ordinal"]))
        )
        a["evidence_id"] = x["id"]
        require(
            a.get("sha256") and a.get("storage_uri") and a.get("byte_size") is not None,
            "XAI_ARTIFACT_INCOMPLETE",
        )
        if a.get("artifact_id"):
            original = lookup(
                rows,
                "artifacts",
                id=a["artifact_id"],
                checksum=a["sha256"],
                file_size_bytes=a["byte_size"],
            )
            require(
                a["storage_uri"]
                in (original.get("path"), original.get("artifact_uri")),
                "XAI_ARTIFACT_URI_MISMATCH",
            )
        if a.get("assessment_artifact_id"):
            original = lookup(
                rows,
                "assessment_artifacts",
                artifact_id=a["assessment_artifact_id"],
                attempt_id=x["assessment_attempt_id"],
                sample_id=x["assessment_sample_id"],
            )["payload"]
            require(
                (original["path"], original["sha256"], original["bytes"])
                == (a["storage_uri"], a["sha256"], a["byte_size"]),
                "XAI_ASSESSMENT_ARTIFACT_MISMATCH",
            )
        artifacts.append(a)
    require(
        len({(a["role"], a["ordinal"]) for a in artifacts}) == len(artifacts),
        "XAI_ARTIFACT_DUPLICATE",
    )
    return x, artifacts


def _build_plan(snapshot, bindings):
    inventory = preflight(snapshot)
    source = snapshot["rows"]
    manifest, _ = target()
    spec = contract()
    dest = {
        e["name"]: deepcopy(source.get(e["name"], []))
        for e in manifest["statements"]
        if e["kind"] == "table"
    }
    dest["alembic_version"] = deepcopy(
        source["alembic_version"]
    )  # Promotion occurs only AFTER full equivalence.
    evidence = Evidence(source, bindings.get("documents", {}))
    trace = []
    for run in source["runs"]:
        if run["run_type"] == "training":
            require(
                str(run["id"]) in bindings.get("configurations", {}),
                "TRAIN_CONFIGURATION_EVIDENCE_MISSING",
            )
            dest["run_configurations"].append(
                configuration(run, bindings["configurations"][str(run["id"])], evidence)
            )
    used_metrics = set()
    evaluation_keys = set()
    coverage = set()
    for b in bindings.get("evaluations", []):
        require(b["key"] not in evaluation_keys, "DUPLICATE_EVALUATION_KEY")
        evaluation_keys.add(b["key"])
        context = evidence.get(b["context"])
        e = evaluation(context, b["key"])
        context = dict(context, id=e["id"])
        original = evidence.get(b["measurement"])
        m = measurement(original, context, b["key"])
        tr = lookup(source, "runs", id=e["training_run_id"])
        if e["subject_kind"] == "single":
            model = lookup(source, "models", id=tr["model_id"])
            m.update(model_id=model["id"], model_name=model["name"])
        else:
            m.update(model_id=None, model_name="ensemble")
        dest["evaluations"].append(e)
        ref = b["measurement"]
        if ref.get("table") == "run_clinical_metrics":
            require(ref["path"] == [], "MEASUREMENT_ROW_REQUIRED")
            key = row_key("run_clinical_metrics", original)
            require(key not in used_metrics, "MEASUREMENT_CARDINALITY_CONFLICT")
            used_metrics.add(key)
            dest["run_clinical_metrics"] = [
                r
                for r in dest["run_clinical_metrics"]
                if row_key("run_clinical_metrics", r) != key
            ]
        dest["run_clinical_metrics"].append(m)
        if "table" in ref:
            coverage.add((ref["table"], tuple(ref["key"]), tuple(ref["path"])))
        for member_ref in b.get("members", []):
            member = deepcopy(evidence.get(member_ref))
            member["evaluation_id"] = e["id"]
            dest["evaluation_ensemble_members"].append(member)
        trace.append(
            {
                "source": deepcopy(ref),
                "evaluation_id": e["id"],
                "measurement_id": m["run_clinical_metric_id"],
                "source_sha256": digest(original),
            }
        )
    require(
        used_metrics
        == {row_key("run_clinical_metrics", r) for r in source["run_clinical_metrics"]},
        "UNMAPPED_CLINICAL_METRIC",
    )
    for r in dest["runs"]:
        if "training_results" in (r.get("parameters") or {}):
            expected = (
                "runs",
                row_key("runs", r),
                ("parameters", "training_results", "validation"),
            )
            require(expected in coverage, "UNMAPPED_TRAINING_RESULTS")
            require(
                r["parameters"]["training_results"].get("schema_version")
                == "training_results_v1",
                "TRAINING_RESULTS_VERSION_INVALID",
            )
            r["parameters"] = deepcopy(r["parameters"])
            del r["parameters"]["training_results"]
    for r in source["train_execution_records"]:
        if (
            r.get("event_id")
            and json.loads(r["payload"]["canonical_event"])["event_type"]
            == "evaluation_completed"
        ):
            require(
                any(
                    e.get("source_event_id") == r["event_id"]
                    for e in dest["evaluations"]
                ),
                "UNMAPPED_E10_EVALUATION_EVENT",
            )
    dest["training_history"] = [history(r) for r in source["training_history"]]
    for record in source["train_execution_records"]:
        if record.get("event_id") is not None or record["kind"] != "epoch":
            continue
        payload = record["payload"]
        require(
            payload.get("phase") == record["phase"]
            and type(payload.get("epoch")) is int,
            "EPOCH_RECORD_IDENTITY_INVALID",
        )
        matches = [
            r
            for r in dest["training_history"]
            if r["run_id"] == record["run_id"]
            and r["phase"] == record["phase"]
            and r["epoch"] == payload["epoch"]
        ]
        require(len(matches) <= 1, "HISTORY_CARDINALITY_CONFLICT")
        aliases = {
            "loss": "train_loss",
            "accuracy": "train_accuracy",
            "precision": "precision_value",
            "recall": "recall_value",
            "f2_parasitized": "train_f2",
            "specificity": "train_specificity",
            "balanced_accuracy": "train_balanced_accuracy",
            "val_f2_parasitized": "val_f2",
        }
        columns = next(
            e["columns"]
            for e in manifest["statements"]
            if e["kind"] == "table" and e["name"] == "training_history"
        )
        projected = {
            aliases.get(k, k): v
            for k, v in payload.items()
            if aliases.get(k, k) in columns and k not in ("phase_epoch",)
        }
        projected.update(
            run_id=record["run_id"], phase=record["phase"], epoch=payload["epoch"]
        )
        if matches:
            existing = matches[0]
            for k, v in projected.items():
                require(
                    existing.get(k) is None or existing[k] == v,
                    "EPOCH_PROJECTION_CONFLICT",
                    k,
                )
                if existing.get(k) is None:
                    existing[k] = v
            existing.update(history(existing))
        else:
            projected.update(
                id=stable_id(
                    "epoch", (str(record["run_id"]), record["phase"], payload["epoch"])
                ),
                created_at=record["created_at"],
                metadata={
                    "legacy_record": list(row_key("train_execution_records", record)),
                    "legacy_payload": deepcopy(payload),
                },
            )
            dest["training_history"].append(history(projected))
    keys = [
        (str(r["run_id"]), r["phase"], r["epoch"]) for r in dest["training_history"]
    ]
    require(len(keys) == len(set(keys)), "HISTORY_CARDINALITY_CONFLICT")
    dest["run_threshold_calibration"] = []
    for r in source["run_threshold_calibration"]:
        key = str(r["run_threshold_calibration_id"])
        require(key in bindings.get("calibrations", {}), "CALIBRATION_BINDING_REQUIRED")
        dest["run_threshold_calibration"].append(
            calibration(r, bindings["calibrations"][key], evidence, dest["evaluations"])
        )
    consumed = set()
    for b in bindings.get("consolidations", []):
        ref = b["source"]
        require(
            ref["path"] == []
            and ref["table"]
            in ("confusion_matrices", "classification_reports", "run_metrics"),
            "CONSOLIDATION_REFERENCE_INVALID",
        )
        r = evidence.get(ref)
        loc = (ref["table"], tuple(ref["key"]))
        require(loc not in consumed, "DUPLICATE_CONSOLIDATION")
        consumed.add(loc)
        m = lookup(
            dest, "run_clinical_metrics", evaluation_id=evidence.get(b["evaluation_id"])
        )
        require(
            r["run_id"] == m["run_id"] and r["split_name"] == m["split_name"],
            "CONSOLIDATION_SCOPE_CONFLICT",
        )
        if ref["table"] == "confusion_matrices":
            require(
                r["labels"] == ["uninfected", "parasitized"]
                and r["matrix"] == m["confusion_matrix"],
                "MATRIX_CONFLICT",
            )
            for a, k in [
                ("true_negative", "tn"),
                ("false_positive", "fp"),
                ("false_negative", "fn"),
                ("true_positive", "tp"),
            ]:
                require(r.get(a) == m[k], "MATRIX_COUNTS_CONFLICT")
        elif ref["table"] == "classification_reports":
            cls = r["class_name"]
            require(cls in ("parasitized", "uninfected"), "REPORT_CLASS_UNSUPPORTED")
            tp, tn, fp, fn = (Decimal(m[k]) for k in ("tp", "tn", "fp", "fn"))
            n, d = (tp, tp + fp) if cls == "parasitized" else (tn, tn + fn)
            expected = {
                "precision_value": n / d if d else None,
                "recall_value": m["recall_parasitized"]
                if cls == "parasitized"
                else m["specificity"],
                "f1_score": m["f1_parasitized"]
                if cls == "parasitized"
                else 2 * tn / (2 * tn + fn + fp)
                if 2 * tn + fn + fp
                else None,
                "support": tp + fn if cls == "parasitized" else tn + fp,
            }
            for k, v in expected.items():
                require(
                    (r.get(k) is None or r.get(k) == 0)
                    if v is None
                    else r.get(k) is not None
                    and abs(number(r[k], k) - v) <= Decimal("1e-12"),
                    "REPORT_METRIC_CONFLICT",
                    k,
                )
        else:
            name = r["metric_name"].lower()
            dest_name = RATES.get(name, name)
            require(
                name in RESERVED and dest_name in m, "EAV_RESERVED_MAPPING_REQUIRED"
            )
            value = m[dest_name]
            require(
                (r["metric_value"] is None or r["metric_value"] == 0)
                if value is None
                else abs(number(r["metric_value"], name) - number(value, name))
                <= Decimal("1e-12"),
                "EAV_METRIC_CONFLICT",
            )
            dest["run_metrics"] = [
                v
                for v in dest["run_metrics"]
                if row_key("run_metrics", v) != row_key("run_metrics", r)
            ]
        trace.append(
            {
                "source": deepcopy(ref),
                "measurement_id": m["run_clinical_metric_id"],
                "source_sha256": digest(r),
            }
        )
    needed = {
        (t, row_key(t, r))
        for t in ("confusion_matrices", "classification_reports")
        for r in source[t]
    }
    needed |= {
        ("run_metrics", row_key("run_metrics", r))
        for r in source["run_metrics"]
        if r["metric_name"].lower() in RESERVED
    }
    require(needed == consumed, "UNMAPPED_CONSOLIDATION")
    for r in dest["run_metrics"]:
        require(
            "." in r["metric_name"] and r["metric_name"].lower() not in RESERVED,
            "UNREVIEWED_METRIC_ALIAS",
        )
    xai_parents = set()
    for b in bindings.get("xai", []):
        ref = b["parent"]
        loc = (ref["table"], tuple(ref["key"]))
        require(loc not in xai_parents, "XAI_PARENT_DUPLICATE")
        xai_parents.add(loc)
        x, artifacts = xai_project(b, evidence, dest)
        dest["xai_evidence"].append(x)
        dest["xai_artifacts"].extend(artifacts)
    # Incomplete parents may remain untouched, but must be explicitly documented.
    excluded = set()
    for b in bindings.get("xai_excluded", []):
        ref = b["source"]
        evidence.get(ref)
        require(b.get("reason") and ref["path"] == [], "XAI_EXCLUSION_REASON_REQUIRED")
        excluded.add((ref["table"], tuple(ref["key"])))
    all_xai = {
        (t, row_key(t, r))
        for t in ("explainability_results", "cell_explanations")
        for r in source[t]
    }
    require(
        not (xai_parents & excluded) and all_xai <= xai_parents | excluded,
        "XAI_DISPOSITION_REQUIRED",
    )
    primary = {
        e["table"]: e["keys"]
        for e in manifest["statements"]
        if e["kind"] == "constraint" and e.get("constraint_type") == "CONSTR_PRIMARY"
    }
    primary["alembic_version"] = ["version_num"]
    for t, rows in dest.items():
        ids = [tuple(str(r[k]) for k in primary[t]) for r in rows]
        require(len(ids) == len(set(ids)), "DUPLICATE_DESTINATION_IDENTIFIER", t)
    eval_sources = [
        (
            e["source_kind"],
            str(e["run_id"]),
            e["source_record_phase"],
            e["source_record_key"],
        )
        for e in dest["evaluations"]
    ]
    require(
        len(eval_sources) == len(set(eval_sources)), "EVALUATION_SOURCE_CARDINALITY"
    )
    validate_relations(dest)
    preserved = [
        t
        for t, v in spec["tables"].items()
        if v["action"] in ("PROTECTED", "KEEP") and t != "alembic_version"
    ]
    for t in preserved:
        require(
            table_digest(source[t]) == table_digest(dest[t]), "PRESERVATION_FAILURE", t
        )
    # Target column validation prevents unknown metadata being silently dropped.
    tables = {
        e["name"]: e["columns"] for e in manifest["statements"] if e["kind"] == "table"
    }
    for t, cols in tables.items():
        for r in dest[t]:
            require(set(r) <= set(cols), "UNKNOWN_TARGET_COLUMN", t)
            for k, v in cols.items():
                if t not in source and not v["nullable"] and not v["generated"]:
                    require(
                        r.get(k) is not None, "EXPLICIT_NEW_VALUE_REQUIRED", t + "." + k
                    )
                if not v["nullable"] and v["default"] is None and not v["generated"]:
                    require(r.get(k) is not None, "REQUIRED_TARGET_COLUMN", t + "." + k)
    plan = {
        "format_version": 1,
        "legacy_revision": spec["legacy_revision"],
        "target_revision": "pg_v2_baseline",
        "source_inventory": inventory,
        "source_inventory_sha256": digest(inventory),
        "bindings_sha256": digest(bindings),
        "rows": dest,
        "mapping": trace,
        "xai_excluded": deepcopy(bindings.get("xai_excluded", [])),
        "preserved_tables": preserved,
        "original_archive": deepcopy(snapshot),
        "original_archive_sha256": digest(snapshot),
        "target_manifest_sha256": MANIFEST_HASH,
    }
    plan["plan_sha256"] = digest(plan)
    return plan


def build_plan(snapshot, bindings):
    try:
        return _build_plan(snapshot, bindings)
    except Blocked:
        raise
    except (KeyError, TypeError, ValueError, IndexError, ArithmeticError):
        raise Blocked("INCOMPLETE_OR_INCOMPATIBLE_EVIDENCE") from None
