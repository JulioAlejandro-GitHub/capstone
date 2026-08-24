from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.db import fetch_all, fetch_one
from app.services.explainability import enrich_explainability_items
from app.services.run_lineage import grouped_run_lineage_payload
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


RUN_EXPLAINABILITY_SCOPE_SQL = """
WITH requested_run AS (
    SELECT id, run_type, dataset_version_id
    FROM runs
    WHERE id = CAST(:run_id AS uuid)
), evaluation_source AS (
    SELECT
        lineage.parent_run_id,
        lineage.model_version_id,
        lineage.checkpoint_artifact_id,
        lineage.checkpoint_path,
        requested.dataset_version_id
    FROM requested_run requested
    JOIN run_lineage lineage ON lineage.child_run_id = requested.id
    WHERE requested.run_type = 'evaluation'
      AND lineage.relationship_type = 'evaluates_checkpoint_from'
), scope_candidates AS (
    -- Preserve the historical exact-run lookup for every run type.
    SELECT
        requested.id AS run_id,
        direct_lineage.model_version_id
    FROM requested_run requested
    LEFT JOIN LATERAL (
        SELECT lineage.model_version_id
        FROM run_lineage lineage
        WHERE requested.run_type = 'explainability'
          AND lineage.child_run_id = requested.id
          AND lineage.relationship_type = 'explains_checkpoint_from'
        ORDER BY lineage.created_at DESC, lineage.id
        LIMIT 1
    ) direct_lineage ON TRUE

    UNION ALL

    -- A TRAIN detail owns every explicitly linked EXPLAIN child.
    SELECT lineage.child_run_id, lineage.model_version_id
    FROM requested_run requested
    JOIN run_lineage lineage ON lineage.parent_run_id = requested.id
    JOIN runs child ON child.id = lineage.child_run_id
    WHERE requested.run_type = 'training'
      AND child.run_type = 'explainability'
      AND lineage.relationship_type = 'explains_checkpoint_from'

    UNION ALL

    -- An EVALUATE detail may expose only EXPLAIN siblings for the same governed
    -- model/checkpoint identity. Each fallback is used only when the stronger
    -- identity is absent, so legacy siblings are never selected by recency.
    SELECT explanation.child_run_id, explanation.model_version_id
    FROM evaluation_source evaluation
    JOIN run_lineage explanation
      ON explanation.parent_run_id = evaluation.parent_run_id
     AND explanation.relationship_type = 'explains_checkpoint_from'
    JOIN runs child
      ON child.id = explanation.child_run_id
     AND child.run_type = 'explainability'
    WHERE
        (
            evaluation.dataset_version_id IS NULL
            OR child.dataset_version_id = evaluation.dataset_version_id
        )
        AND (
            (
                evaluation.model_version_id IS NOT NULL
                AND explanation.model_version_id = evaluation.model_version_id
            )
            OR (
                evaluation.model_version_id IS NULL
                AND evaluation.checkpoint_artifact_id IS NOT NULL
                AND explanation.checkpoint_artifact_id = evaluation.checkpoint_artifact_id
            )
            OR (
                evaluation.model_version_id IS NULL
                AND evaluation.checkpoint_artifact_id IS NULL
                AND evaluation.checkpoint_path IS NOT NULL
                AND explanation.checkpoint_path = evaluation.checkpoint_path
            )
        )
), explainability_scope AS (
    SELECT
        run_id,
        CASE
            WHEN COUNT(DISTINCT model_version_id) = 1
            THEN MIN(model_version_id::text)::uuid
            ELSE NULL
        END AS model_version_id
    FROM scope_candidates
    GROUP BY run_id
)
SELECT run_id::text AS run_id, model_version_id::text AS model_version_id
FROM explainability_scope
ORDER BY run_id
"""


RUN_EXPLAINABILITY_COMPACT_COLUMNS = """
    audit.explainability_id,
    audit.prediction_id,
    audit.run_id,
    audit.model_name,
    audit.dataset_name,
    audit.run_name,
    audit.run_type,
    audit.run_status,
    audit.dataset_source,
    audit.dataset_split,
    audit.dataset_index,
    audit.manifest_id,
    audit.dataset_image_id,
    audit.original_tfds_label,
    audit.remapped_label,
    audit.label_mapping_version,
    audit.method,
    audit.case_type,
    audit.true_label,
    audit.predicted_label,
    audit.positive_label,
    audit.score,
    audit.score_positive_label,
    audit.probability_parasitized,
    audit.probability_uninfected,
    audit.threshold,
    audit.threshold_used,
    audit.threshold_source,
    audit.confidence_distance,
    audit.confidence_status,
    audit.is_correct,
    audit.image_id,
    audit.image_path,
    audit.source_image_path,
    audit.original_image_path,
    audit.original_filename,
    audit.image_stored_path,
    audit.crop_path,
    audit.source_image_id,
    audit.patient_id,
    audit.slide_id,
    audit.bbox_x,
    audit.bbox_y,
    audit.bbox_width,
    audit.bbox_height,
    audit.prediction_upload_id,
    audit.uploaded_at,
    audit.explanation_output_path,
    audit.last_conv_layer,
    audit.success,
    audit.error_message,
    audit.explanation_parameters,
    audit.interpretation,
    audit.artifact_id,
    audit.artifact_path,
    audit.artifact_type,
    audit.started_at,
    audit.created_at,
    {model_version_expression} AS model_version,
    {model_version_expression} AS model_version_id
"""


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
        WITH page AS (
            SELECT *
            FROM vw_run_dashboard
            ORDER BY run_name DESC, started_at DESC NULLS LAST
            LIMIT :limit
        )
        SELECT
            page.*,
            r.command,
            clinical.recall_parasitized,
            clinical.sensitivity_parasitized,
            clinical.specificity,
            clinical.f2_parasitized,
            clinical.roc_auc_parasitized,
            selected_confusion.tn,
            selected_confusion.fp,
            selected_confusion.fn,
            selected_confusion.tp,
            selected_confusion.confusion_matrix,
            CASE LOWER(COALESCE(
                clinical.prediction_collapse->>'collapsed',
                clinical.metadata->>'prediction_collapse_detected'
            ))
                WHEN 'true' THEN true
                WHEN 't' THEN true
                WHEN '1' THEN true
                WHEN 'false' THEN false
                WHEN 'f' THEN false
                WHEN '0' THEN false
                ELSE NULL
            END AS prediction_collapse_detected
        FROM page
        JOIN runs r ON r.id = page.run_id
        LEFT JOIN LATERAL (
            SELECT
                rcm.recall_parasitized,
                rcm.sensitivity_parasitized,
                rcm.specificity,
                rcm.f2_parasitized,
                rcm.roc_auc_parasitized,
                rcm.split_name,
                rcm.tn,
                rcm.fp,
                rcm.fn,
                rcm.tp,
                rcm.confusion_matrix,
                rcm.prediction_collapse,
                rcm.metadata
            FROM run_clinical_metrics rcm
            WHERE rcm.run_id = page.run_id
            ORDER BY
                CASE WHEN rcm.split_name IN ('test', 'external') THEN 0 ELSE 1 END,
                rcm.created_at DESC
            LIMIT 1
        ) clinical ON TRUE
        LEFT JOIN LATERAL (
            SELECT
                cm.split_name,
                cm.matrix,
                cm.true_positive,
                cm.true_negative,
                cm.false_positive,
                cm.false_negative
            FROM confusion_matrices cm
            WHERE cm.run_id = page.run_id
            ORDER BY
                CASE
                    WHEN clinical.split_name IS NOT NULL
                        AND cm.split_name = clinical.split_name THEN 0
                    WHEN cm.split_name IN ('test', 'external') THEN 1
                    ELSE 2
                END,
                cm.created_at DESC
            LIMIT 1
        ) legacy ON TRUE
        LEFT JOIN LATERAL (
            SELECT
                candidate.tn,
                candidate.fp,
                candidate.fn,
                candidate.tp,
                candidate.confusion_matrix
            FROM (
                SELECT
                    clinical.tn,
                    clinical.fp,
                    clinical.fn,
                    clinical.tp,
                    clinical.confusion_matrix,
                    0 AS source_rank
                WHERE
                    clinical.tn IS NOT NULL
                    OR clinical.fp IS NOT NULL
                    OR clinical.fn IS NOT NULL
                    OR clinical.tp IS NOT NULL
                    OR NULLIF(clinical.confusion_matrix, '[]'::jsonb) IS NOT NULL

                UNION ALL

                SELECT
                    legacy.true_negative AS tn,
                    legacy.false_positive AS fp,
                    legacy.false_negative AS fn,
                    legacy.true_positive AS tp,
                    legacy.matrix AS confusion_matrix,
                    1 AS source_rank
                WHERE
                    legacy.true_negative IS NOT NULL
                    OR legacy.false_positive IS NOT NULL
                    OR legacy.false_negative IS NOT NULL
                    OR legacy.true_positive IS NOT NULL
                    OR NULLIF(legacy.matrix, '[]'::jsonb) IS NOT NULL
            ) candidate
            ORDER BY
                CASE
                    WHEN (
                        candidate.tn IS NOT NULL
                        AND candidate.fp IS NOT NULL
                        AND candidate.fn IS NOT NULL
                        AND candidate.tp IS NOT NULL
                    ) OR NULLIF(candidate.confusion_matrix, '[]'::jsonb) IS NOT NULL
                    THEN 0
                    ELSE 1
                END,
                candidate.source_rank
            LIMIT 1
        ) selected_confusion ON TRUE
        ORDER BY page.run_name DESC, page.started_at DESC NULLS LAST
        """,
        {"limit": limit},
    )
    return {"items": rows_to_list(rows)}


@router.get("/runs/grouped-lineage")
@router.get("/api/runs/grouped-lineage")
def list_grouped_run_lineage(
    datasource: str | None = Query(default="malaria"),
    limit: int = Query(default=100, ge=1, le=500),
):
    """Group recent training runs with linked children and separate orphans."""
    return grouped_run_lineage_payload(datasource=datasource, limit=limit)


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
    compact: bool = False,
):
    try:
        normalized_run_id = str(UUID(str(run_id)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail="run_id debe ser un UUID valido.") from exc

    scope = rows_to_list(
        fetch_all(
            datasource,
            RUN_EXPLAINABILITY_SCOPE_SQL,
            {"run_id": normalized_run_id},
        )
    )
    if not scope:
        return {"items": [], "total": 0, "limit": limit, "offset": offset}

    params = {"limit": limit, "offset": offset}
    scope_placeholders = []
    model_version_cases = []
    for index, scoped_run in enumerate(scope):
        run_key = f"scope_run_id_{index}"
        params[run_key] = scoped_run["run_id"]
        scope_placeholders.append(f"CAST(:{run_key} AS uuid)")
        if scoped_run.get("model_version_id"):
            version_key = f"scope_model_version_id_{index}"
            params[version_key] = scoped_run["model_version_id"]
            model_version_cases.append(
                f"WHEN audit.run_id = CAST(:{run_key} AS uuid) THEN :{version_key}"
            )

    conditions = [f"audit.run_id IN ({', '.join(scope_placeholders)})"]
    if method is not None:
        conditions.append("audit.method = :method")
        params["method"] = method
    if case_type is not None:
        conditions.append("audit.case_type = :case_type")
        params["case_type"] = case_type
    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    model_version_expression = (
        "COALESCE("
        f"CASE {' '.join(model_version_cases)} ELSE NULL END, "
        "NULLIF(audit.run_parameters->>'model_version_id', ''), "
        "NULLIF(audit.run_metadata->>'model_version_id', '')"
        ")"
        if model_version_cases
        else (
            "COALESCE(NULLIF(audit.run_parameters->>'model_version_id', ''), "
            "NULLIF(audit.run_metadata->>'model_version_id', ''))"
        )
    )
    selected_columns = (
        RUN_EXPLAINABILITY_COMPACT_COLUMNS.format(
            model_version_expression=model_version_expression
        )
        if compact
        else "audit.*"
    )

    items = rows_to_list(
        fetch_all(
            datasource,
            f"""
            SELECT
                {selected_columns},
                COUNT(*) OVER () AS _total_count
            FROM vw_visual_explainability_audit audit
            {where_sql}
            ORDER BY
                audit.started_at DESC NULLS LAST,
                audit.created_at DESC NULLS LAST,
                audit.explainability_id
            LIMIT :limit OFFSET :offset
            """,
            params,
        )
    )
    total = int(items[0].get("_total_count", 0)) if items else 0
    for item in items:
        item.pop("_total_count", None)

    # COUNT(*) OVER() avoids a second scan of the expensive audit view. Only an
    # out-of-range page needs a fallback query to preserve the total contract.
    if not items and offset > 0:
        count_row = fetch_one(
            datasource,
            f"""
            SELECT COUNT(*) AS total
            FROM vw_visual_explainability_audit audit
            {where_sql}
            """,
            params,
        )
        total = int(row_to_dict(count_row)["total"]) if count_row else 0

    return {
        "items": enrich_explainability_items(items),
        "total": total,
        "limit": limit,
        "offset": offset,
    }
