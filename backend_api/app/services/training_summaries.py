"""One-query, read-only listing of TRAIN summaries."""

from pydantic import ValidationError
from sqlalchemy import text

from app.db import read_only_transaction, resolve_datasource
from app.schemas.training_summaries import (
    TrainingSummary,
    TrainingSummaryCollection,
)


TRAINING_SUMMARIES_SQL = """
WITH selected_trainings AS MATERIALIZED (
    SELECT
        training.id,
        training.run_name,
        training.run_type,
        training.status,
        training.model_id,
        training.dataset_id,
        training.dataset_version_id,
        training.command,
        training.started_at,
        training.finished_at,
        training.duration_seconds,
        training.created_at,
        training.execution_parameters,
        training.parameters,
        training.metadata,
        training.release_status,
        training.release_updated_at,
        training.release_changed_by,
        training.release_reason
    FROM runs AS training
    WHERE training.run_type = 'training'
    ORDER BY
        training.started_at DESC NULLS LAST,
        training.created_at DESC,
        training.id
    LIMIT :limit
), visual_metrics AS (
    SELECT
        selected.id AS training_run_id,
        MAX(metric.metric_value) FILTER (
            WHERE metric.metric_name IN (
                'recall', 'recall_macro', 'sensitivity', 'test_recall'
            )
        ) AS recall,
        MAX(metric.metric_value) FILTER (
            WHERE metric.metric_name IN ('f2_score', 'f2_macro', 'test_f2')
        ) AS f2_score,
        MAX(metric.metric_value) FILTER (
            WHERE metric.metric_name IN ('auc', 'test_auc', 'val_auc')
        ) AS auc
    FROM selected_trainings AS selected
    LEFT JOIN run_metrics AS metric ON metric.run_id = selected.id
    GROUP BY selected.id
), child_counts AS (
    SELECT
        selected.id AS training_run_id,
        COUNT(DISTINCT lineage.child_run_id) FILTER (
            WHERE lineage.relationship_type = 'evaluates_checkpoint_from'
              AND child.run_type = 'evaluation'
        ) AS evaluation_count,
        COUNT(DISTINCT lineage.child_run_id) FILTER (
            WHERE lineage.relationship_type = 'explains_checkpoint_from'
              AND child.run_type = 'explainability'
        ) AS explainability_count
    FROM selected_trainings AS selected
    LEFT JOIN run_lineage AS lineage ON lineage.parent_run_id = selected.id
    LEFT JOIN runs AS child ON child.id = lineage.child_run_id
    GROUP BY selected.id
)
SELECT
    selected.id AS run_id,
    selected.run_type,
    selected.status,
    selected.release_status,
    selected.release_updated_at,
    selected.release_changed_by,
    selected.release_reason,
    COALESCE(children.evaluation_count, 0) AS evaluation_count,
    COALESCE(children.explainability_count, 0) AS explainability_count,
    selected.run_name,
    COALESCE(
        NULLIF(model.name, ''),
        NULLIF(selected.execution_parameters->>'model_name', ''),
        NULLIF(selected.execution_parameters->>'model', ''),
        NULLIF(selected.parameters->>'model_name', ''),
        NULLIF(selected.parameters->>'model', ''),
        NULLIF(selected.metadata->>'model_name', '')
    ) AS model_name,
    dataset.name AS dataset_name,
    selected.dataset_version_id,
    COALESCE(
        NULLIF(selected.execution_parameters->>'optimizer', ''),
        NULLIF(selected.execution_parameters #>> '{cli_arguments,optimizer}', ''),
        NULLIF(selected.parameters->>'optimizer', ''),
        NULLIF(selected.parameters #>> '{execution_parameters,optimizer}', ''),
        NULLIF(selected.parameters #>> '{cli_arguments,optimizer}', ''),
        NULLIF(selected.metadata->>'optimizer', ''),
        substring(
            selected.command
            FROM '--optimizer(?:[[:space:]]+|=)([^[:space:]]+)'
        )
    ) AS optimizer,
    selected.command,
    selected.started_at,
    selected.finished_at,
    selected.duration_seconds,
    metrics.recall,
    clinical.recall_parasitized,
    clinical.specificity,
    metrics.f2_score,
    clinical.f2_parasitized,
    metrics.auc,
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
FROM selected_trainings AS selected
JOIN child_counts AS children ON children.training_run_id = selected.id
JOIN visual_metrics AS metrics ON metrics.training_run_id = selected.id
LEFT JOIN models AS model ON model.id = selected.model_id
LEFT JOIN datasets AS dataset ON dataset.id = selected.dataset_id
LEFT JOIN LATERAL (
    SELECT
        clinical_metric.recall_parasitized,
        clinical_metric.specificity,
        clinical_metric.f2_parasitized,
        clinical_metric.roc_auc_parasitized,
        clinical_metric.split_name,
        clinical_metric.tn,
        clinical_metric.fp,
        clinical_metric.fn,
        clinical_metric.tp,
        clinical_metric.confusion_matrix,
        clinical_metric.prediction_collapse,
        clinical_metric.metadata
    FROM run_clinical_metrics AS clinical_metric
    WHERE clinical_metric.run_id = selected.id
    ORDER BY
        CASE WHEN clinical_metric.split_name IN ('test', 'external') THEN 0 ELSE 1 END,
        clinical_metric.created_at DESC
    LIMIT 1
) AS clinical ON TRUE
LEFT JOIN LATERAL (
    SELECT
        matrix.split_name,
        matrix.matrix,
        matrix.true_positive,
        matrix.true_negative,
        matrix.false_positive,
        matrix.false_negative
    FROM confusion_matrices AS matrix
    WHERE matrix.run_id = selected.id
    ORDER BY
        CASE
            WHEN clinical.split_name IS NOT NULL
                AND matrix.split_name = clinical.split_name THEN 0
            WHEN matrix.split_name IN ('test', 'external') THEN 1
            ELSE 2
        END,
        matrix.created_at DESC
    LIMIT 1
) AS legacy_confusion ON TRUE
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
            legacy_confusion.true_negative AS tn,
            legacy_confusion.false_positive AS fp,
            legacy_confusion.false_negative AS fn,
            legacy_confusion.true_positive AS tp,
            legacy_confusion.matrix AS confusion_matrix,
            1 AS source_rank
        WHERE
            legacy_confusion.true_negative IS NOT NULL
            OR legacy_confusion.false_positive IS NOT NULL
            OR legacy_confusion.false_negative IS NOT NULL
            OR legacy_confusion.true_positive IS NOT NULL
            OR NULLIF(legacy_confusion.matrix, '[]'::jsonb) IS NOT NULL
    ) AS candidate
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
) AS selected_confusion ON TRUE
ORDER BY
    selected.started_at DESC NULLS LAST,
    selected.created_at DESC,
    selected.id
"""


class TrainingSummaryContractError(RuntimeError):
    """Persisted data does not satisfy the public summary contract."""


def list_training_summaries(
    datasource: str | None,
    limit: int,
) -> TrainingSummaryCollection:
    if not 1 <= limit <= 500:
        raise ValueError("limit debe estar entre 1 y 500")

    key = resolve_datasource(datasource)
    with read_only_transaction(key) as connection:
        rows = connection.execute(
            text(TRAINING_SUMMARIES_SQL),
            {"limit": limit},
        ).mappings().all()

    try:
        items = [TrainingSummary.model_validate(dict(row)) for row in rows]
    except ValidationError as exc:
        raise TrainingSummaryContractError(
            "Los datos persistidos de TRAIN no cumplen el contrato de resumen."
        ) from exc

    return TrainingSummaryCollection(items=items, count=len(items), limit=limit)
