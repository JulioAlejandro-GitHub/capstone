"""Read-only aggregation for the runs lineage tree."""

from app.db import fetch_all
from app.services.serialization import rows_to_list


TRAINING_RUNS_SQL = """
WITH selected_trainings AS (
    SELECT id
    FROM runs
    WHERE run_type = 'training'
    ORDER BY started_at DESC NULLS LAST, created_at DESC, id
    LIMIT :limit
), page AS (
    SELECT dashboard.*
    FROM vw_run_dashboard dashboard
    JOIN selected_trainings selected ON selected.id = dashboard.run_id
)
SELECT
    page.*,
    r.command,
    COALESCE(
        NULLIF(page.model_name, ''),
        NULLIF(r.execution_parameters->>'model_name', ''),
        NULLIF(r.execution_parameters->>'model', ''),
        NULLIF(r.parameters->>'model_name', ''),
        NULLIF(r.parameters->>'model', ''),
        NULLIF(r.metadata->>'model_name', '')
    ) AS resolved_model_name,
    COALESCE(
        NULLIF(page.optimizer, ''),
        NULLIF(r.execution_parameters->>'optimizer', ''),
        NULLIF(r.execution_parameters #>> '{cli_arguments,optimizer}', ''),
        NULLIF(r.parameters->>'optimizer', ''),
        NULLIF(r.parameters #>> '{execution_parameters,optimizer}', ''),
        NULLIF(r.parameters #>> '{cli_arguments,optimizer}', ''),
        NULLIF(r.metadata->>'optimizer', ''),
        substring(r.command FROM '--optimizer[[:space:]=]+([^[:space:]]+)')
    ) AS resolved_optimizer,
    clinical.recall_parasitized,
    clinical.sensitivity_parasitized,
    clinical.specificity,
    clinical.f2_parasitized,
    clinical.roc_auc_parasitized,
    clinical.pr_auc_parasitized,
    clinical.balanced_accuracy,
    clinical.threshold_used,
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
        rcm.pr_auc_parasitized,
        rcm.balanced_accuracy,
        rcm.threshold_used,
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
ORDER BY page.started_at DESC NULLS LAST, page.run_id
"""


EVALUATION_LINEAGE_SQL = """
WITH selected_trainings AS (
    SELECT id
    FROM runs
    WHERE run_type = 'training'
    ORDER BY started_at DESC NULLS LAST, created_at DESC, id
    LIMIT :limit
), eligible_evaluations AS (
    SELECT DISTINCT lineage.evaluation_run_id
    FROM vw_evaluation_lineage lineage
    JOIN selected_trainings selected ON selected.id = lineage.training_run_id
)
SELECT
    lineage.evaluation_run_id,
    lineage.evaluation_run_name,
    lineage.evaluation_started_at,
    lineage.training_run_id,
    lineage.training_run_name,
    lineage.model_name,
    lineage.optimizer,
    lineage.checkpoint_path,
    lineage.relationship_type,
    lineage.confidence,
    lineage.accuracy,
    lineage.recall,
    lineage.specificity,
    lineage.f2_score,
    lineage.auc,
    child.status,
    child.finished_at,
    child.duration_seconds,
    child.command,
    clinical.precision_parasitized,
    clinical.recall_parasitized,
    clinical.sensitivity_parasitized,
    clinical.pr_auc_parasitized,
    clinical.balanced_accuracy,
    clinical.threshold_used,
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
FROM vw_evaluation_lineage lineage
JOIN eligible_evaluations eligible
    ON eligible.evaluation_run_id = lineage.evaluation_run_id
JOIN runs child ON child.id = lineage.evaluation_run_id
LEFT JOIN LATERAL (
    SELECT
        rcm.precision_parasitized,
        rcm.recall_parasitized,
        rcm.sensitivity_parasitized,
        rcm.pr_auc_parasitized,
        rcm.balanced_accuracy,
        rcm.threshold_used,
        rcm.split_name,
        rcm.tn,
        rcm.fp,
        rcm.fn,
        rcm.tp,
        rcm.confusion_matrix,
        rcm.prediction_collapse,
        rcm.metadata
    FROM run_clinical_metrics rcm
    WHERE rcm.run_id = lineage.evaluation_run_id
    ORDER BY
        CASE rcm.split_name
            WHEN 'test' THEN 0
            WHEN 'external' THEN 1
            ELSE 2
        END,
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
    WHERE cm.run_id = lineage.evaluation_run_id
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
ORDER BY lineage.evaluation_started_at DESC NULLS LAST, lineage.evaluation_run_id
"""


EXPLAINABILITY_LINEAGE_SQL = """
WITH selected_trainings AS (
    SELECT id
    FROM runs
    WHERE run_type = 'training'
    ORDER BY started_at DESC NULLS LAST, created_at DESC, id
    LIMIT :limit
), eligible_explanations AS (
    SELECT DISTINCT lineage.explain_run_id
    FROM vw_explainability_lineage lineage
    JOIN selected_trainings selected ON selected.id = lineage.training_run_id
)
SELECT
    lineage.*,
    child.status,
    child.finished_at,
    child.duration_seconds,
    child.command
FROM vw_explainability_lineage lineage
JOIN eligible_explanations eligible ON eligible.explain_run_id = lineage.explain_run_id
JOIN runs child ON child.id = lineage.explain_run_id
ORDER BY
    lineage.explain_started_at DESC NULLS LAST,
    lineage.explain_run_id,
    lineage.method
"""


UNLINKED_CHILD_RUNS_SQL = """
SELECT
    child.id::text AS run_id,
    child.run_name,
    child.run_type,
    child.status,
    child.started_at,
    child.finished_at,
    child.duration_seconds,
    child.command,
    COALESCE(
        NULLIF(model.name, ''),
        NULLIF(child.execution_parameters->>'model_name', ''),
        NULLIF(child.execution_parameters->>'model', ''),
        NULLIF(child.parameters->>'model_name', ''),
        NULLIF(child.parameters->>'model', ''),
        NULLIF(child.metadata->>'model_name', '')
    ) AS model_name,
    COALESCE(
        NULLIF(child.execution_parameters->>'optimizer', ''),
        NULLIF(child.execution_parameters #>> '{cli_arguments,optimizer}', ''),
        NULLIF(child.parameters->>'optimizer', ''),
        NULLIF(child.parameters #>> '{execution_parameters,optimizer}', ''),
        NULLIF(child.parameters #>> '{cli_arguments,optimizer}', ''),
        NULLIF(child.metadata->>'optimizer', '')
    ) AS optimizer,
    child.metadata->>'lineage_status' AS lineage_status,
    child.metadata->>'lineage_warning' AS lineage_warning,
    child.metadata->>'lineage_confidence' AS lineage_confidence,
    child.metadata->>'source_checkpoint_path' AS checkpoint_path
FROM runs child
LEFT JOIN models model ON model.id = child.model_id
WHERE child.run_type IN ('evaluation', 'explainability')
  AND NOT EXISTS (
      SELECT 1
      FROM vw_run_lineage lineage
      WHERE lineage.child_run_id = child.id
        AND lineage.parent_run_type = 'training'
        AND (
            (
                child.run_type = 'evaluation'
                AND lineage.relationship_type = 'evaluates_checkpoint_from'
            )
            OR (
                child.run_type = 'explainability'
                AND lineage.relationship_type = 'explains_checkpoint_from'
            )
        )
  )
ORDER BY child.started_at DESC NULLS LAST, child.id
"""


def _evaluation_item(row: dict) -> dict:
    return {
        "run_id": row.get("evaluation_run_id"),
        "run_name": row.get("evaluation_run_name"),
        "run_type": "evaluation",
        "status": row.get("status"),
        "started_at": row.get("evaluation_started_at"),
        "finished_at": row.get("finished_at"),
        "duration_seconds": row.get("duration_seconds"),
        "model_name": row.get("model_name"),
        "optimizer": row.get("optimizer"),
        "relationship_type": row.get("relationship_type"),
        "confidence": row.get("confidence"),
        "checkpoint_path": row.get("checkpoint_path"),
        "command": row.get("command"),
        "accuracy": row.get("accuracy"),
        "precision_parasitized": row.get("precision_parasitized"),
        "recall": row.get("recall"),
        "recall_parasitized": row.get("recall_parasitized"),
        "sensitivity_parasitized": row.get("sensitivity_parasitized"),
        "specificity": row.get("specificity"),
        "f2_score": row.get("f2_score"),
        "auc": row.get("auc"),
        "pr_auc_parasitized": row.get("pr_auc_parasitized"),
        "balanced_accuracy": row.get("balanced_accuracy"),
        "threshold_used": row.get("threshold_used"),
        "tn": row.get("tn"),
        "fp": row.get("fp"),
        "fn": row.get("fn"),
        "tp": row.get("tp"),
        "confusion_matrix": row.get("confusion_matrix"),
        "prediction_collapse_detected": row.get(
            "prediction_collapse_detected"
        ),
    }


def _training_item(row: dict) -> dict:
    item = dict(row)
    resolved_model_name = item.pop("resolved_model_name", None)
    resolved_optimizer = item.pop("resolved_optimizer", None)
    if resolved_model_name:
        item["model_name"] = resolved_model_name
    if resolved_optimizer:
        item["optimizer"] = resolved_optimizer
    return item


def _shared_value(rows: list[dict], key: str):
    values = {row.get(key) for row in rows if row.get(key) is not None}
    return next(iter(values)) if len(values) == 1 else None


def _explainability_item(row: dict) -> dict:
    method = row.get("method")
    return {
        "run_id": row.get("explain_run_id"),
        "run_name": row.get("explain_run_name"),
        "run_type": "explainability",
        "status": row.get("status"),
        "started_at": row.get("explain_started_at"),
        "finished_at": row.get("finished_at"),
        "duration_seconds": row.get("duration_seconds"),
        "model_name": row.get("model_name"),
        "optimizer": row.get("optimizer"),
        "relationship_type": row.get("relationship_type"),
        "confidence": row.get("confidence"),
        "checkpoint_path": row.get("checkpoint_path"),
        "command": row.get("command"),
        "method": method,
        "methods": [method] if method else [],
        "total_explanations": int(row.get("total_explanations") or 0),
        "success_count": int(row.get("success_count") or 0),
        "failed_count": int(row.get("failed_count") or 0),
        "_seen_methods": {method},
    }


def _aggregate_explainability_rows(rows: list[dict]) -> dict:
    item = _explainability_item(rows[0])
    for row in rows[1:]:
        method = row.get("method")
        if method in item["_seen_methods"]:
            continue
        item["_seen_methods"].add(method)
        if method:
            item["methods"].append(method)
        item["total_explanations"] += int(row.get("total_explanations") or 0)
        item["success_count"] += int(row.get("success_count") or 0)
        item["failed_count"] += int(row.get("failed_count") or 0)

    item.pop("_seen_methods", None)
    item["methods"] = sorted(set(item["methods"]))
    if len(item["methods"]) == 1:
        item["method"] = item["methods"][0]
    elif len(item["methods"]) > 1:
        item["method"] = "multiple"
    else:
        item["method"] = None
    return item


def _unlinked_item(row: dict) -> dict:
    return {
        "run_id": row.get("run_id"),
        "run_name": row.get("run_name"),
        "run_type": row.get("run_type"),
        "status": row.get("status"),
        "started_at": row.get("started_at"),
        "finished_at": row.get("finished_at"),
        "duration_seconds": row.get("duration_seconds"),
        "model_name": row.get("model_name"),
        "optimizer": row.get("optimizer"),
        "command": row.get("command"),
        "relationship_type": None,
        "confidence": row.get("lineage_confidence"),
        "checkpoint_path": row.get("checkpoint_path"),
        "lineage_status": row.get("lineage_status"),
        "lineage_warning": row.get("lineage_warning"),
    }


def grouped_run_lineage_payload(
    datasource: str | None,
    limit: int,
) -> dict:
    """Build a training -> evaluation/explainability tree with orphan children."""
    params = {"limit": limit}
    training_rows = rows_to_list(fetch_all(datasource, TRAINING_RUNS_SQL, params))
    evaluation_rows = rows_to_list(
        fetch_all(datasource, EVALUATION_LINEAGE_SQL, params)
    )
    explainability_rows = rows_to_list(
        fetch_all(datasource, EXPLAINABILITY_LINEAGE_SQL, params)
    )
    unlinked_rows = rows_to_list(fetch_all(datasource, UNLINKED_CHILD_RUNS_SQL))

    groups = []
    groups_by_training_id = {}
    for raw_training in training_rows:
        training = _training_item(raw_training)
        training_id = training.get("run_id")
        if training_id is None or training_id in groups_by_training_id:
            continue
        group = {"training": training, "evaluations": [], "explainability": []}
        groups.append(group)
        groups_by_training_id[training_id] = group

    conflicts = {"evaluations": [], "explainability": []}
    evaluation_rows_by_run = {}
    for row in evaluation_rows:
        training_id = row.get("training_run_id")
        evaluation_id = row.get("evaluation_run_id")
        if training_id is None or evaluation_id is None:
            continue
        evaluation_rows_by_run.setdefault(evaluation_id, []).append(row)

    for evaluation_id, rows in evaluation_rows_by_run.items():
        parent_ids = sorted({row.get("training_run_id") for row in rows})
        item = _evaluation_item(rows[0])
        if len(parent_ids) > 1:
            item.update(
                {
                    "confidence": "unknown",
                    "lineage_status": "ambiguous",
                    "lineage_warning": (
                        "El run de evaluación tiene múltiples parent training."
                    ),
                    "candidate_training_run_ids": parent_ids,
                    "model_name": _shared_value(rows, "model_name"),
                    "optimizer": _shared_value(rows, "optimizer"),
                    "checkpoint_path": _shared_value(rows, "checkpoint_path"),
                }
            )
            conflicts["evaluations"].append(item)
            continue
        group = groups_by_training_id.get(parent_ids[0])
        if group is not None:
            group["evaluations"].append(item)

    explainability_rows_by_run = {}
    for row in explainability_rows:
        training_id = row.get("training_run_id")
        explain_run_id = row.get("explain_run_id")
        if training_id is None or explain_run_id is None:
            continue
        explainability_rows_by_run.setdefault(explain_run_id, []).append(row)

    for explain_run_id, rows in explainability_rows_by_run.items():
        parent_ids = sorted({row.get("training_run_id") for row in rows})
        item = _aggregate_explainability_rows(rows)
        if len(parent_ids) > 1:
            item.update(
                {
                    "confidence": "unknown",
                    "lineage_status": "ambiguous",
                    "lineage_warning": (
                        "El run de explicabilidad tiene múltiples parent training."
                    ),
                    "candidate_training_run_ids": parent_ids,
                    "model_name": _shared_value(rows, "model_name"),
                    "optimizer": _shared_value(rows, "optimizer"),
                    "checkpoint_path": _shared_value(rows, "checkpoint_path"),
                }
            )
            conflicts["explainability"].append(item)
            continue
        group = groups_by_training_id.get(parent_ids[0])
        if group is not None:
            group["explainability"].append(item)

    unlinked = {"evaluations": [], "explainability": []}
    for row in unlinked_rows:
        item = _unlinked_item(row)
        if item["run_type"] == "evaluation":
            unlinked["evaluations"].append(item)
        elif item["run_type"] == "explainability":
            unlinked["explainability"].append(item)

    linked_evaluations = sum(len(group["evaluations"]) for group in groups)
    linked_explainability = sum(len(group["explainability"]) for group in groups)
    return {
        "items": groups,
        "unlinked": unlinked,
        "conflicts": conflicts,
        "totals": {
            "training_runs": len(groups),
            "linked_evaluations": linked_evaluations,
            "linked_explainability": linked_explainability,
            "unlinked_evaluations": len(unlinked["evaluations"]),
            "unlinked_explainability": len(unlinked["explainability"]),
            "conflicting_evaluations": len(conflicts["evaluations"]),
            "conflicting_explainability": len(conflicts["explainability"]),
        },
    }
