"""Fixed-query, read-only loading of direct children for one TRAIN."""

from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import text

from app.db import read_only_transaction, resolve_datasource
from app.schemas.lineage_children import (
    EvaluationLineageChild,
    ExplainabilityLineageChild,
    TrainingLineageChildren,
)


PARENT_RUN_SQL = """
SELECT id, run_type
FROM runs
WHERE id = :training_run_id
"""


LINEAGE_CHILDREN_SQL = """
WITH eligible_lineage AS MATERIALIZED (
    SELECT
        lineage.id AS lineage_id,
        lineage.parent_run_id,
        lineage.child_run_id,
        lineage.relationship_type,
        lineage.confidence,
        lineage.model_version_id,
        lineage.checkpoint_artifact_id,
        lineage.created_at AS lineage_created_at,
        child.run_name,
        child.run_type,
        child.status,
        child.model_id,
        child.dataset_id,
        child.dataset_version_id,
        child.execution_parameters,
        child.parameters,
        child.metadata,
        child.started_at,
        child.finished_at,
        child.duration_seconds,
        child.created_at,
        ROW_NUMBER() OVER (
            PARTITION BY lineage.child_run_id
            ORDER BY lineage.created_at ASC, lineage.id ASC
        ) AS lineage_rank
    FROM run_lineage AS lineage
    JOIN runs AS child ON child.id = lineage.child_run_id
    WHERE lineage.parent_run_id = :training_run_id
      AND (
          (
              lineage.relationship_type = 'evaluates_checkpoint_from'
              AND child.run_type = 'evaluation'
          )
          OR (
              lineage.relationship_type = 'explains_checkpoint_from'
              AND child.run_type = 'explainability'
          )
      )
), direct_children AS MATERIALIZED (
    SELECT *
    FROM eligible_lineage
    WHERE lineage_rank = 1
), child_counts AS (
    SELECT
        COUNT(DISTINCT child_run_id) FILTER (
            WHERE relationship_type = 'evaluates_checkpoint_from'
              AND run_type = 'evaluation'
        ) AS evaluation_count,
        COUNT(DISTINCT child_run_id) FILTER (
            WHERE relationship_type = 'explains_checkpoint_from'
              AND run_type = 'explainability'
        ) AS explainability_count
    FROM direct_children
), generic_metrics AS (
    SELECT
        child.child_run_id AS run_id,
        MAX(metric.metric_value) FILTER (
            WHERE LOWER(metric.metric_name) IN (
                'accuracy', 'test_accuracy', 'val_accuracy'
            )
        ) AS accuracy,
        MAX(metric.metric_value) FILTER (
            WHERE LOWER(metric.metric_name) IN (
                'recall', 'recall_macro', 'recall_parasitized',
                'sensitivity', 'sensitivity_parasitized', 'test_recall'
            )
        ) AS recall,
        MAX(metric.metric_value) FILTER (
            WHERE LOWER(metric.metric_name) IN ('specificity', 'test_specificity')
        ) AS specificity,
        MAX(metric.metric_value) FILTER (
            WHERE LOWER(metric.metric_name) IN (
                'f2', 'f2_score', 'f2_parasitized', 'test_f2'
            )
        ) AS f2_score,
        MAX(metric.metric_value) FILTER (
            WHERE LOWER(metric.metric_name) IN (
                'auc', 'auc_parasitized', 'roc_auc',
                'roc_auc_parasitized', 'test_auc'
            )
        ) AS auc
    FROM direct_children AS child
    LEFT JOIN run_metrics AS metric ON metric.run_id = child.child_run_id
    WHERE child.run_type = 'evaluation'
    GROUP BY child.child_run_id
), latest_clinical_metrics AS (
    SELECT DISTINCT ON (metric.run_id)
        metric.run_id,
        metric.split_name,
        metric.accuracy,
        metric.precision_parasitized,
        metric.recall_parasitized,
        metric.sensitivity_parasitized,
        metric.specificity,
        metric.f2_parasitized,
        metric.roc_auc_parasitized,
        metric.pr_auc_parasitized,
        metric.balanced_accuracy,
        metric.threshold_used,
        metric.tn,
        metric.fp,
        metric.fn,
        metric.tp,
        metric.confusion_matrix,
        metric.prediction_collapse,
        metric.metadata
    FROM run_clinical_metrics AS metric
    JOIN direct_children AS child
      ON child.child_run_id = metric.run_id
     AND child.run_type = 'evaluation'
    ORDER BY
        metric.run_id,
        CASE
            WHEN metric.split_name = 'test' THEN 0
            WHEN metric.split_name = 'external' THEN 1
            ELSE 2
        END,
        metric.created_at DESC
), latest_confusion_matrices AS (
    SELECT DISTINCT ON (matrix.run_id)
        matrix.run_id,
        matrix.matrix,
        matrix.true_positive,
        matrix.true_negative,
        matrix.false_positive,
        matrix.false_negative
    FROM confusion_matrices AS matrix
    JOIN direct_children AS child
      ON child.child_run_id = matrix.run_id
     AND child.run_type = 'evaluation'
    LEFT JOIN latest_clinical_metrics AS clinical ON clinical.run_id = matrix.run_id
    ORDER BY
        matrix.run_id,
        CASE
            WHEN clinical.split_name IS NOT NULL
                AND matrix.split_name = clinical.split_name THEN 0
            WHEN matrix.split_name IN ('test', 'external') THEN 1
            ELSE 2
        END,
        matrix.created_at DESC
), explanation_summary AS (
    SELECT
        result.run_id,
        ARRAY_AGG(DISTINCT result.method ORDER BY result.method)
            FILTER (WHERE result.method IS NOT NULL) AS methods,
        COUNT(*) AS total_explanations,
        COUNT(*) FILTER (WHERE result.success IS TRUE) AS success_count,
        COUNT(*) FILTER (WHERE result.success IS FALSE) AS failed_count
    FROM explainability_results AS result
    JOIN direct_children AS child
      ON child.child_run_id = result.run_id
     AND child.run_type = 'explainability'
    GROUP BY result.run_id
), hydrated_children AS (
    SELECT
        child.child_run_id AS run_id,
        child.run_type,
        child.status,
        child.run_name,
        COALESCE(
            NULLIF(child_model.name, ''),
            NULLIF(child.execution_parameters->>'model_name', ''),
            NULLIF(child.execution_parameters->>'model', ''),
            NULLIF(child.parameters->>'model_name', ''),
            NULLIF(child.parameters->>'model', ''),
            NULLIF(child.metadata->>'model_name', ''),
            NULLIF(parent_model.name, ''),
            NULLIF(parent.execution_parameters->>'model_name', ''),
            NULLIF(parent.execution_parameters->>'model', ''),
            NULLIF(parent.parameters->>'model_name', ''),
            NULLIF(parent.parameters->>'model', ''),
            NULLIF(parent.metadata->>'model_name', '')
        ) AS model_name,
        dataset.name AS dataset_name,
        child.dataset_version_id,
        COALESCE(
            NULLIF(child.execution_parameters->>'optimizer', ''),
            NULLIF(child.parameters->>'optimizer', ''),
            NULLIF(child.metadata->>'optimizer', ''),
            NULLIF(parent.execution_parameters->>'optimizer', ''),
            NULLIF(parent.parameters->>'optimizer', ''),
            NULLIF(parent.metadata->>'optimizer', ''),
            substring(
                parent.command
                FROM '--optimizer(?:[[:space:]]+|=)([^[:space:]]+)'
            )
        ) AS optimizer,
        child.started_at,
        child.finished_at,
        child.duration_seconds,
        child.parent_run_id,
        child.relationship_type,
        child.confidence,
        child.model_version_id,
        child.checkpoint_artifact_id,
        COALESCE(clinical.accuracy, generic.accuracy) AS accuracy,
        clinical.precision_parasitized,
        COALESCE(
            clinical.recall_parasitized,
            clinical.sensitivity_parasitized,
            generic.recall
        ) AS recall,
        clinical.recall_parasitized,
        clinical.sensitivity_parasitized,
        COALESCE(clinical.specificity, generic.specificity) AS specificity,
        COALESCE(clinical.f2_parasitized, generic.f2_score) AS f2_score,
        clinical.f2_parasitized,
        COALESCE(clinical.roc_auc_parasitized, generic.auc) AS auc,
        clinical.roc_auc_parasitized,
        clinical.pr_auc_parasitized,
        clinical.balanced_accuracy,
        clinical.threshold_used,
        COALESCE(clinical.tn, legacy.true_negative) AS tn,
        COALESCE(clinical.fp, legacy.false_positive) AS fp,
        COALESCE(clinical.fn, legacy.false_negative) AS fn,
        COALESCE(clinical.tp, legacy.true_positive) AS tp,
        COALESCE(
            NULLIF(clinical.confusion_matrix, '[]'::jsonb),
            NULLIF(legacy.matrix, '[]'::jsonb)
        ) AS confusion_matrix,
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
        END AS prediction_collapse_detected,
        explanation.methods,
        COALESCE(
            NULLIF(child.parameters->>'method', ''),
            NULLIF(child.metadata->>'method', '')
        ) AS fallback_method,
        COALESCE(explanation.total_explanations, 0) AS total_explanations,
        COALESCE(explanation.success_count, 0) AS success_count,
        COALESCE(explanation.failed_count, 0) AS failed_count,
        child.created_at
    FROM direct_children AS child
    JOIN runs AS parent ON parent.id = child.parent_run_id
    LEFT JOIN models AS child_model ON child_model.id = child.model_id
    LEFT JOIN models AS parent_model ON parent_model.id = parent.model_id
    LEFT JOIN datasets AS dataset ON dataset.id = child.dataset_id
    LEFT JOIN generic_metrics AS generic ON generic.run_id = child.child_run_id
    LEFT JOIN latest_clinical_metrics AS clinical
      ON clinical.run_id = child.child_run_id
    LEFT JOIN latest_confusion_matrices AS legacy
      ON legacy.run_id = child.child_run_id
    LEFT JOIN explanation_summary AS explanation
      ON explanation.run_id = child.child_run_id
), page AS MATERIALIZED (
    SELECT *
    FROM hydrated_children
    ORDER BY started_at ASC NULLS LAST, created_at ASC, run_id ASC
    LIMIT :limit
)
SELECT
    counts.evaluation_count,
    counts.explainability_count,
    page.*
FROM child_counts AS counts
LEFT JOIN page ON TRUE
ORDER BY page.started_at ASC NULLS LAST, page.created_at ASC, page.run_id ASC
"""


class TrainingRunNotFoundError(LookupError):
    """The requested run does not exist."""


class TrainingParentTypeError(ValueError):
    """The requested run exists but is not a TRAIN."""


class LineageChildrenContractError(RuntimeError):
    """Persisted lineage data violates the public response contract."""


COMMON_CHILD_FIELDS = (
    "run_id",
    "run_type",
    "status",
    "run_name",
    "model_name",
    "dataset_name",
    "dataset_version_id",
    "optimizer",
    "started_at",
    "finished_at",
    "duration_seconds",
    "parent_run_id",
    "relationship_type",
    "confidence",
    "model_version_id",
    "checkpoint_artifact_id",
)

EVALUATION_FIELDS = COMMON_CHILD_FIELDS + (
    "accuracy",
    "precision_parasitized",
    "recall",
    "recall_parasitized",
    "sensitivity_parasitized",
    "specificity",
    "f2_score",
    "f2_parasitized",
    "auc",
    "roc_auc_parasitized",
    "pr_auc_parasitized",
    "balanced_accuracy",
    "threshold_used",
    "tn",
    "fp",
    "fn",
    "tp",
    "confusion_matrix",
    "prediction_collapse_detected",
)


def _explainability_payload(row: dict) -> dict:
    methods = list(row.get("methods") or [])
    fallback_method = row.get("fallback_method")
    if not methods and fallback_method:
        methods = [fallback_method]
    if len(methods) == 1:
        method = methods[0]
    elif len(methods) > 1:
        method = "multiple"
    else:
        method = None
    return {
        **{field: row.get(field) for field in COMMON_CHILD_FIELDS},
        "method": method,
        "methods": methods,
        "total_explanations": int(row.get("total_explanations") or 0),
        "success_count": int(row.get("success_count") or 0),
        "failed_count": int(row.get("failed_count") or 0),
    }


def get_training_lineage_children(
    training_run_id: UUID,
    datasource: str | None,
    limit: int,
) -> TrainingLineageChildren:
    if not 1 <= limit <= 500:
        raise ValueError("limit debe estar entre 1 y 500")

    key = resolve_datasource(datasource)
    params = {"training_run_id": training_run_id, "limit": limit}
    with read_only_transaction(key) as connection:
        parent = connection.execute(
            text(PARENT_RUN_SQL),
            {"training_run_id": training_run_id},
        ).mappings().first()
        if parent is None:
            raise TrainingRunNotFoundError(str(training_run_id))
        if parent["run_type"] != "training":
            raise TrainingParentTypeError(str(training_run_id))

        rows = connection.execute(
            text(LINEAGE_CHILDREN_SQL),
            params,
        ).mappings().all()

    if not rows:
        raise LineageChildrenContractError(
            "La consulta de linaje no devolvió su fila de conteos."
        )
    first = dict(rows[0])
    evaluation_count = int(first["evaluation_count"] or 0)
    explainability_count = int(first["explainability_count"] or 0)
    evaluations = []
    explainabilities = []
    try:
        for raw_row in rows:
            row = dict(raw_row)
            if row.get("run_id") is None:
                continue
            if row["run_type"] == "evaluation":
                payload = {field: row.get(field) for field in EVALUATION_FIELDS}
                evaluations.append(EvaluationLineageChild.model_validate(payload))
            elif row["run_type"] == "explainability":
                explainabilities.append(
                    ExplainabilityLineageChild.model_validate(
                        _explainability_payload(row)
                    )
                )
            else:
                raise LineageChildrenContractError(
                    f"Tipo de hijo de linaje desconocido: {row['run_type']}"
                )
    except ValidationError as exc:
        raise LineageChildrenContractError(
            "Los hijos persistidos no cumplen el contrato de linaje."
        ) from exc

    total_count = evaluation_count + explainability_count
    returned_count = len(evaluations) + len(explainabilities)
    return TrainingLineageChildren(
        training_run_id=parent["id"],
        evaluation_count=evaluation_count,
        explainability_count=explainability_count,
        total_count=total_count,
        evaluations=evaluations,
        explainabilities=explainabilities,
        limit=limit,
        truncated=total_count > returned_count,
    )
