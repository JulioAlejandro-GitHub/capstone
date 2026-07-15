from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.db import fetch_all, fetch_one
from app.services.explainability import enrich_explainability_items
from app.services.serialization import row_to_dict, rows_to_list


router = APIRouter(tags=["runs"])

LABEL_MAPPING = {
    "0": "uninfected",
    "1": "parasitized",
    "negative_class": "uninfected",
    "negative_class_index": 0,
    "positive_class": "parasitized",
    "positive_class_index": 1,
    "raw_model_score_meaning": "probability_parasitized",
    "decision_rule": "probability_parasitized >= threshold -> parasitized",
}


def latest_item(rows):
    items = rows_to_list(rows)
    return items[0] if items else None


def clinical_summary_payload(
    run,
    clinical_metric,
    checkpoint_policy,
    threshold_calibration,
    artifacts_count,
    image_predictions_count,
):
    run_data = row_to_dict(run)
    metric = clinical_metric or {}
    checkpoint = checkpoint_policy or {}
    threshold = threshold_calibration or {}
    confusion_matrix = metric.get("confusion_matrix") or []
    tn = metric.get("tn")
    fp = metric.get("fp")
    fn = metric.get("fn")
    tp = metric.get("tp")

    if not confusion_matrix and all(value is not None for value in (tn, fp, fn, tp)):
        confusion_matrix = [[tn, fp], [fn, tp]]

    return {
        "run_id": run_data["id"],
        "model_name": run_data.get("model_name"),
        "script_name": run_data.get("script_name"),
        "run_type": run_data.get("run_type"),
        "status": run_data.get("status"),
        "started_at": run_data.get("started_at"),
        "finished_at": run_data.get("finished_at"),
        "label_mapping": LABEL_MAPPING,
        "clinical_metrics": {
            "accuracy": metric.get("accuracy"),
            "precision_parasitized": metric.get("precision_parasitized"),
            "recall_parasitized": metric.get("recall_parasitized"),
            "sensitivity_parasitized": metric.get("sensitivity_parasitized"),
            "specificity": metric.get("specificity"),
            "f1_parasitized": metric.get("f1_parasitized"),
            "f2_parasitized": metric.get("f2_parasitized"),
            "roc_auc_parasitized": metric.get("roc_auc_parasitized"),
            "pr_auc_parasitized": metric.get("pr_auc_parasitized"),
            "balanced_accuracy": metric.get("balanced_accuracy"),
            "prediction_collapse_detected": metric.get(
                "prediction_collapse_detected"
            ),
        },
        "confusion_matrix": {
            "labels": ["uninfected", "parasitized"],
            "matrix": confusion_matrix,
            "tn": tn,
            "fp": fp,
            "fn": fn,
            "tp": tp,
        },
        "checkpoint_policy": {
            "policy": checkpoint.get("checkpoint_policy"),
            "checkpoint_policy": checkpoint.get("checkpoint_policy"),
            "min_recall_required": checkpoint.get("min_recall_required"),
            "selected_epoch": checkpoint.get("selected_epoch"),
            "policy_satisfied": checkpoint.get("policy_satisfied"),
            "selected_metric": checkpoint.get("selected_metric"),
            "selected_metric_value": checkpoint.get("selected_metric_value"),
            "warning": checkpoint.get("checkpoint_warning"),
            "checkpoint_warning": checkpoint.get("checkpoint_warning"),
            "checkpoint_path": checkpoint.get("checkpoint_path"),
        },
        "clinical_threshold": {
            "enabled": bool(threshold),
            "threshold_source": threshold.get("threshold_source"),
            "threshold_selected": threshold.get("threshold_selected"),
            "threshold_used": (
                metric.get("threshold_used")
                if metric.get("threshold_used") is not None
                else threshold.get("threshold_selected")
            ),
            "default_threshold": threshold.get("default_threshold"),
            "target_recall": threshold.get("target_recall"),
            "target_recall_satisfied": threshold.get("target_recall_satisfied"),
            "validation_recall_at_threshold": threshold.get(
                "validation_recall_at_threshold"
            ),
            "validation_specificity_at_threshold": threshold.get(
                "validation_specificity_at_threshold"
            ),
            "warning": threshold.get("threshold_warning"),
            "threshold_warning": threshold.get("threshold_warning"),
        },
        "artifacts_count": artifacts_count,
        "image_predictions_count": image_predictions_count,
    }


@router.get("/runs")
@router.get("/api/runs")
def list_runs(
    datasource: str | None = Query(default="malaria"),
    limit: int = Query(default=100, ge=1, le=500),
):
    rows = fetch_all(
        datasource,
        """
        SELECT *
        FROM vw_run_dashboard
        ORDER BY started_at DESC NULLS LAST
        LIMIT :limit
        """,
        {"limit": limit},
    )
    return {"items": rows_to_list(rows)}


@router.get("/runs/clinical/summary")
@router.get("/api/runs/clinical/summary")
def list_clinical_run_summary(
    datasource: str | None = Query(default="malaria"),
    run_type: str | None = Query(default=None),
    model_name: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    conditions = []
    params = {"limit": limit}
    if run_type is not None:
        conditions.append("run_type = :run_type")
        params["run_type"] = run_type
    if model_name is not None:
        conditions.append("model_name = :model_name")
        params["model_name"] = model_name
    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    rows = fetch_all(
        datasource,
        f"""
        SELECT *
        FROM vw_clinical_run_summary
        {where_sql}
        ORDER BY started_at DESC NULLS LAST
        LIMIT :limit
        """,
        params,
    )
    return {"items": rows_to_list(rows)}


@router.get("/runs/{run_id}/clinical-summary")
@router.get("/api/runs/{run_id}/clinical-summary")
def get_run_clinical_summary(
    run_id: str,
    datasource: str | None = Query(default="malaria"),
):
    run = fetch_one(
        datasource,
        """
        SELECT
            r.*,
            m.name AS model_name
        FROM runs r
        LEFT JOIN models m ON m.id = r.model_id
        WHERE r.id = CAST(:run_id AS uuid)
        """,
        {"run_id": run_id},
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Run no encontrado.")

    clinical_metric = latest_item(
        fetch_all(
            datasource,
            """
            SELECT
                *,
                CASE LOWER(COALESCE(
                    prediction_collapse->>'collapsed',
                    metadata->>'prediction_collapse_detected'
                ))
                    WHEN 'true' THEN true
                    WHEN 't' THEN true
                    WHEN '1' THEN true
                    WHEN 'false' THEN false
                    WHEN 'f' THEN false
                    WHEN '0' THEN false
                    ELSE NULL
                END AS prediction_collapse_detected
            FROM run_clinical_metrics
            WHERE run_id = CAST(:run_id AS uuid)
            ORDER BY
                CASE WHEN split_name IN ('test', 'external') THEN 0 ELSE 1 END,
                created_at DESC
            LIMIT 1
            """,
            {"run_id": run_id},
        )
    )
    checkpoint_policy = latest_item(
        fetch_all(
            datasource,
            """
            SELECT *
            FROM vw_checkpoint_policy_summary
            WHERE run_id = CAST(:run_id AS uuid)
            ORDER BY created_at DESC
            LIMIT 1
            """,
            {"run_id": run_id},
        )
    )
    threshold_calibration = latest_item(
        fetch_all(
            datasource,
            """
            SELECT *
            FROM vw_threshold_calibration_summary
            WHERE run_id = CAST(:run_id AS uuid)
            ORDER BY created_at DESC
            LIMIT 1
            """,
            {"run_id": run_id},
        )
    )
    artifacts_count_row = fetch_one(
        datasource,
        """
        SELECT COUNT(*) AS total
        FROM artifacts
        WHERE run_id = CAST(:run_id AS uuid)
        """,
        {"run_id": run_id},
    )
    image_predictions_count_row = fetch_one(
        datasource,
        """
        SELECT COUNT(*) AS total
        FROM run_image_predictions
        WHERE run_id = CAST(:run_id AS uuid)
        """,
        {"run_id": run_id},
    )

    return clinical_summary_payload(
        run,
        clinical_metric,
        checkpoint_policy,
        threshold_calibration,
        artifacts_count=(
            int(row_to_dict(artifacts_count_row)["total"])
            if artifacts_count_row is not None
            else 0
        ),
        image_predictions_count=(
            int(row_to_dict(image_predictions_count_row)["total"])
            if image_predictions_count_row is not None
            else 0
        ),
    )


@router.get("/runs/{run_id}")
@router.get("/api/runs/{run_id}")
def get_run(run_id: str, datasource: str | None = Query(default="malaria")):
    run = fetch_one(
        datasource,
        """
        SELECT
            r.*,
            e.name AS experiment_name,
            m.name AS model_name,
            m.model_type,
            d.name AS dataset_name
        FROM runs r
        LEFT JOIN experiments e ON e.id = r.experiment_id
        LEFT JOIN models m ON m.id = r.model_id
        LEFT JOIN datasets d ON d.id = r.dataset_id
        WHERE r.id = :run_id
        """,
        {"run_id": run_id},
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Run no encontrado.")

    metrics = fetch_all(
        datasource,
        "SELECT * FROM run_metrics WHERE run_id = :run_id ORDER BY created_at",
        {"run_id": run_id},
    )
    artifacts = fetch_all(
        datasource,
        "SELECT * FROM artifacts WHERE run_id = :run_id ORDER BY created_at DESC",
        {"run_id": run_id},
    )
    training_history = fetch_all(
        datasource,
        "SELECT * FROM training_history WHERE run_id = :run_id ORDER BY epoch",
        {"run_id": run_id},
    )
    errors = fetch_all(
        datasource,
        "SELECT * FROM errors WHERE run_id = :run_id ORDER BY created_at DESC",
        {"run_id": run_id},
    )
    return {
        "run": row_to_dict(run),
        "metrics": rows_to_list(metrics),
        "artifacts": rows_to_list(artifacts),
        "training_history": rows_to_list(training_history),
        "errors": rows_to_list(errors),
    }


@router.get("/runs/{run_id}/clinical-metrics")
@router.get("/api/runs/{run_id}/clinical-metrics")
def get_run_clinical_metrics(
    run_id: str,
    datasource: str | None = Query(default="malaria"),
):
    rows = fetch_all(
        datasource,
        """
        SELECT *
        FROM run_clinical_metrics
        WHERE run_id = CAST(:run_id AS uuid)
        ORDER BY created_at
        """,
        {"run_id": run_id},
    )
    return {"items": rows_to_list(rows)}


@router.get("/runs/{run_id}/checkpoint-policy")
@router.get("/api/runs/{run_id}/checkpoint-policy")
def get_run_checkpoint_policy(
    run_id: str,
    datasource: str | None = Query(default="malaria"),
):
    rows = fetch_all(
        datasource,
        """
        SELECT *
        FROM vw_checkpoint_policy_summary
        WHERE run_id = CAST(:run_id AS uuid)
        ORDER BY created_at DESC
        """,
        {"run_id": run_id},
    )
    return {"items": rows_to_list(rows)}


@router.get("/runs/{run_id}/threshold-calibration")
@router.get("/api/runs/{run_id}/threshold-calibration")
def get_run_threshold_calibration(
    run_id: str,
    datasource: str | None = Query(default="malaria"),
):
    rows = fetch_all(
        datasource,
        """
        SELECT *
        FROM vw_threshold_calibration_summary
        WHERE run_id = CAST(:run_id AS uuid)
        ORDER BY created_at DESC
        """,
        {"run_id": run_id},
    )
    return {"items": rows_to_list(rows)}


@router.get("/runs/{run_id}/artifacts-summary")
@router.get("/runs/{run_id}/artifacts")
@router.get("/api/runs/{run_id}/artifacts-summary")
@router.get("/api/runs/{run_id}/artifacts")
def get_run_artifacts_summary(
    run_id: str,
    datasource: str | None = Query(default="malaria"),
):
    rows = fetch_all(
        datasource,
        """
        SELECT *
        FROM vw_run_artifacts_summary
        WHERE run_id = CAST(:run_id AS uuid)
        ORDER BY created_at DESC
        """,
        {"run_id": run_id},
    )
    return {"items": rows_to_list(rows)}


@router.get("/runs/{run_id}/image-predictions")
@router.get("/api/runs/{run_id}/image-predictions")
def get_run_image_predictions(
    run_id: str,
    datasource: str | None = Query(default="malaria"),
    split: str | None = Query(default=None),
    case_type: str | None = Query(default=None),
    class_name: str | None = Query(default=None),
    is_correct: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    conditions = ["run_id = CAST(:run_id AS uuid)"]
    params = {"run_id": run_id, "limit": limit, "offset": offset}
    if split is not None:
        conditions.append("split_name = :split")
        params["split"] = split
    if case_type is not None:
        conditions.append("case_type = :case_type")
        params["case_type"] = case_type
    if class_name is not None:
        conditions.append(
            "(true_label_name = :class_name OR predicted_label_name = :class_name)"
        )
        params["class_name"] = class_name
    if is_correct is not None:
        conditions.append("is_correct = :is_correct")
        params["is_correct"] = is_correct
    where_sql = f"WHERE {' AND '.join(conditions)}"

    count_row = fetch_one(
        datasource,
        f"""
        SELECT COUNT(*) AS total
        FROM run_image_predictions
        {where_sql}
        """,
        params,
    )
    rows = fetch_all(
        datasource,
        f"""
        SELECT *
        FROM run_image_predictions
        {where_sql}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
        """,
        params,
    )
    total = int(row_to_dict(count_row)["total"]) if count_row else 0
    return {"items": rows_to_list(rows), "total": total, "limit": limit, "offset": offset}


@router.get("/runs/{run_id}/io-records")
@router.get("/api/runs/{run_id}/io-records")
def get_run_io_records(
    run_id: str,
    datasource: str | None = Query(default="malaria"),
):
    rows = fetch_all(
        datasource,
        """
        SELECT *
        FROM run_io_records
        WHERE run_id = CAST(:run_id AS uuid)
        ORDER BY created_at DESC
        """,
        {"run_id": run_id},
    )
    return {"items": rows_to_list(rows)}


@router.get("/runs/{run_id}/explainability")
@router.get("/api/runs/{run_id}/explainability")
def get_run_explainability(
    run_id: str,
    datasource: str | None = Query(default="malaria"),
    method: str | None = Query(default=None),
    case_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    try:
        normalized_run_id = str(UUID(str(run_id)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail="run_id debe ser un UUID valido.") from exc

    conditions = ["run_id = CAST(:run_id AS uuid)"]
    params = {"run_id": normalized_run_id, "limit": limit, "offset": offset}
    if method is not None:
        conditions.append("method = :method")
        params["method"] = method
    if case_type is not None:
        conditions.append("case_type = :case_type")
        params["case_type"] = case_type
    where_sql = f"WHERE {' AND '.join(conditions)}"

    count_row = fetch_one(
        datasource,
        f"SELECT COUNT(*) AS total FROM vw_visual_explainability_audit {where_sql}",
        params,
    )
    rows = fetch_all(
        datasource,
        f"""
        SELECT *
        FROM vw_visual_explainability_audit
        {where_sql}
        ORDER BY started_at DESC NULLS LAST
        LIMIT :limit OFFSET :offset
        """,
        params,
    )
    total = int(row_to_dict(count_row)["total"]) if count_row else 0
    return {
        "items": enrich_explainability_items(rows_to_list(rows)),
        "total": total,
        "limit": limit,
        "offset": offset,
    }
