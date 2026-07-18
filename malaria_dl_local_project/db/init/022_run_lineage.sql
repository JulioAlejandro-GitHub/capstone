-- Run Lineage: relaciones explicitas entre entrenamiento y ejecuciones derivadas.
-- Migracion incremental, idempotente y sin cambios sobre registros historicos.

CREATE TABLE IF NOT EXISTS run_lineage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    parent_run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    child_run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,

    relationship_type TEXT NOT NULL,

    checkpoint_path TEXT,
    checkpoint_artifact_id UUID NULL,
    model_version_id UUID NULL,

    confidence TEXT NOT NULL DEFAULT 'explicit',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_run_lineage_parent_child_type
        UNIQUE (parent_run_id, child_run_id, relationship_type),
    CONSTRAINT chk_run_lineage_relationship_type
        CHECK (
            relationship_type IN (
                'evaluates_checkpoint_from',
                'explains_checkpoint_from',
                'derived_from'
            )
        ),
    CONSTRAINT chk_run_lineage_confidence
        CHECK (
            confidence IN (
                'explicit',
                'inferred_exact_checkpoint',
                'inferred_model_version',
                'inferred_heuristic',
                'unknown'
            )
        ),
    CONSTRAINT chk_run_lineage_distinct_runs
        CHECK (parent_run_id <> child_run_id)
);

CREATE INDEX IF NOT EXISTS idx_run_lineage_parent_run_id
    ON run_lineage(parent_run_id);

CREATE INDEX IF NOT EXISTS idx_run_lineage_child_run_id
    ON run_lineage(child_run_id);

CREATE INDEX IF NOT EXISTS idx_run_lineage_relationship_type
    ON run_lineage(relationship_type);

CREATE INDEX IF NOT EXISTS idx_run_lineage_checkpoint_path
    ON run_lineage(checkpoint_path);

COMMENT ON TABLE run_lineage IS
    'Linaje auditable desde un run padre (normalmente training) hacia un run derivado.';

COMMENT ON COLUMN run_lineage.relationship_type IS
    'Relacion canonica: evaluates_checkpoint_from, explains_checkpoint_from o derived_from.';

COMMENT ON COLUMN run_lineage.confidence IS
    'Origen de la vinculacion: explicit, inferred_exact_checkpoint, inferred_model_version, inferred_heuristic o unknown.';

CREATE OR REPLACE VIEW vw_run_lineage AS
SELECT
    child_run.id AS child_run_id,
    child_run.run_name AS child_run_name,
    child_run.run_type AS child_run_type,
    child_run.status AS child_status,
    child_run.started_at AS child_started_at,

    parent_run.id AS parent_run_id,
    parent_run.run_name AS parent_run_name,
    parent_run.run_type AS parent_run_type,
    parent_run.status AS parent_status,
    parent_run.started_at AS parent_started_at,

    lineage.relationship_type,
    lineage.confidence,
    lineage.checkpoint_path,

    COALESCE(
        parent_model.name,
        NULLIF(parent_run.execution_parameters->>'model_name', ''),
        NULLIF(parent_run.execution_parameters->>'model', ''),
        NULLIF(parent_run.parameters->>'model_name', ''),
        NULLIF(parent_run.parameters->>'model', ''),
        NULLIF(parent_run.metadata->>'model_name', '')
    ) AS parent_model_name,
    COALESCE(
        NULLIF(parent_run.execution_parameters->>'optimizer', ''),
        NULLIF(parent_run.execution_parameters #>> '{cli_arguments,optimizer}', ''),
        NULLIF(parent_run.parameters->>'optimizer', ''),
        NULLIF(parent_run.parameters #>> '{execution_parameters,optimizer}', ''),
        NULLIF(parent_run.parameters #>> '{cli_arguments,optimizer}', ''),
        NULLIF(parent_run.metadata->>'optimizer', ''),
        substring(
            parent_run.command
            FROM '--optimizer[[:space:]=]+([^[:space:]]+)'
        )
    ) AS parent_optimizer,
    parent_run.command AS parent_command,
    child_run.command AS child_command
FROM run_lineage lineage
JOIN runs child_run ON child_run.id = lineage.child_run_id
JOIN runs parent_run ON parent_run.id = lineage.parent_run_id
LEFT JOIN models parent_model ON parent_model.id = parent_run.model_id;

COMMENT ON VIEW vw_run_lineage IS
    'Relaciones de linaje con identidad, estado, modelo, optimizer y comandos de ambos runs.';

CREATE OR REPLACE VIEW vw_evaluation_lineage AS
WITH generic_metrics AS (
    SELECT
        run_id,
        MAX(metric_value) FILTER (
            WHERE LOWER(metric_name) IN (
                'accuracy',
                'test_accuracy',
                'val_accuracy'
            )
        ) AS accuracy,
        MAX(metric_value) FILTER (
            WHERE LOWER(metric_name) IN (
                'recall',
                'recall_macro',
                'recall_parasitized',
                'sensitivity',
                'sensitivity_parasitized',
                'test_recall'
            )
        ) AS recall,
        MAX(metric_value) FILTER (
            WHERE LOWER(metric_name) IN (
                'specificity',
                'test_specificity'
            )
        ) AS specificity,
        MAX(metric_value) FILTER (
            WHERE LOWER(metric_name) IN (
                'f2',
                'f2_score',
                'f2_parasitized',
                'test_f2'
            )
        ) AS f2_score,
        MAX(metric_value) FILTER (
            WHERE LOWER(metric_name) IN (
                'auc',
                'auc_parasitized',
                'roc_auc',
                'roc_auc_parasitized',
                'test_auc'
            )
        ) AS auc
    FROM run_metrics
    GROUP BY run_id
),
latest_clinical_metrics AS (
    SELECT DISTINCT ON (run_id)
        run_id,
        accuracy,
        COALESCE(recall_parasitized, sensitivity_parasitized) AS recall,
        specificity,
        f2_parasitized AS f2_score,
        roc_auc_parasitized AS auc
    FROM run_clinical_metrics
    WHERE split_name IN ('test', 'external')
    ORDER BY
        run_id,
        CASE split_name
            WHEN 'test' THEN 0
            WHEN 'external' THEN 1
            ELSE 2
        END,
        created_at DESC
)
SELECT
    lineage.child_run_id AS evaluation_run_id,
    lineage.child_run_name AS evaluation_run_name,
    lineage.child_started_at AS evaluation_started_at,
    lineage.parent_run_id AS training_run_id,
    lineage.parent_run_name AS training_run_name,
    lineage.parent_model_name AS model_name,
    lineage.parent_optimizer AS optimizer,
    lineage.checkpoint_path,
    lineage.relationship_type,
    lineage.confidence,
    COALESCE(clinical.accuracy, metrics.accuracy) AS accuracy,
    COALESCE(clinical.recall, metrics.recall) AS recall,
    COALESCE(clinical.specificity, metrics.specificity) AS specificity,
    COALESCE(clinical.f2_score, metrics.f2_score) AS f2_score,
    COALESCE(clinical.auc, metrics.auc) AS auc
FROM vw_run_lineage lineage
LEFT JOIN generic_metrics metrics
    ON metrics.run_id = lineage.child_run_id
LEFT JOIN latest_clinical_metrics clinical
    ON clinical.run_id = lineage.child_run_id
WHERE lineage.child_run_type = 'evaluation'
  AND lineage.parent_run_type = 'training'
  AND lineage.relationship_type = 'evaluates_checkpoint_from';

COMMENT ON VIEW vw_evaluation_lineage IS
    'Evaluaciones enlazadas a su entrenamiento; las metricas ausentes permanecen NULL.';

CREATE OR REPLACE VIEW vw_explainability_lineage AS
WITH explanation_summary AS (
    SELECT
        run_id,
        method,
        COUNT(*) AS total_explanations,
        COUNT(*) FILTER (WHERE success IS TRUE) AS success_count,
        COUNT(*) FILTER (WHERE success IS FALSE) AS failed_count
    FROM explainability_results
    GROUP BY run_id, method
)
SELECT
    lineage.child_run_id AS explain_run_id,
    lineage.child_run_name AS explain_run_name,
    lineage.child_started_at AS explain_started_at,
    lineage.parent_run_id AS training_run_id,
    lineage.parent_run_name AS training_run_name,
    lineage.parent_model_name AS model_name,
    lineage.parent_optimizer AS optimizer,
    lineage.checkpoint_path,
    lineage.relationship_type,
    lineage.confidence,
    COALESCE(
        summary.method,
        NULLIF(explain_run.parameters->>'method', ''),
        NULLIF(explain_run.metadata->>'method', '')
    ) AS method,
    COALESCE(summary.total_explanations, 0::BIGINT) AS total_explanations,
    COALESCE(summary.success_count, 0::BIGINT) AS success_count,
    COALESCE(summary.failed_count, 0::BIGINT) AS failed_count
FROM vw_run_lineage lineage
JOIN runs explain_run ON explain_run.id = lineage.child_run_id
LEFT JOIN explanation_summary summary
    ON summary.run_id = lineage.child_run_id
WHERE lineage.child_run_type = 'explainability'
  AND lineage.parent_run_type = 'training'
  AND lineage.relationship_type = 'explains_checkpoint_from';

COMMENT ON VIEW vw_explainability_lineage IS
    'Runs de explicabilidad enlazados a su entrenamiento, resumidos por metodo.';
