ALTER TABLE run_io_records
    ADD COLUMN IF NOT EXISTS run_type TEXT NULL,
    ADD COLUMN IF NOT EXISTS model_name TEXT NULL,
    ADD COLUMN IF NOT EXISTS model_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS clinical_metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE run_io_records
    ALTER COLUMN label_mapping_version SET DEFAULT 'clinical_v1_parasitized_positive',
    ALTER COLUMN raw_model_score_meaning SET DEFAULT 'probability_parasitized';

CREATE TABLE IF NOT EXISTS run_clinical_metrics (
    run_clinical_metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    model_id UUID NULL REFERENCES models(id) ON DELETE SET NULL,
    model_name TEXT NULL,
    split_name TEXT NOT NULL,
    threshold_used NUMERIC NULL,
    threshold_source TEXT NULL,
    accuracy NUMERIC NULL,
    precision_parasitized NUMERIC NULL,
    recall_parasitized NUMERIC NULL,
    sensitivity_parasitized NUMERIC NULL,
    specificity NUMERIC NULL,
    f1_parasitized NUMERIC NULL,
    f2_parasitized NUMERIC NULL,
    roc_auc_parasitized NUMERIC NULL,
    pr_auc_parasitized NUMERIC NULL,
    balanced_accuracy NUMERIC NULL,
    tn INTEGER NULL,
    fp INTEGER NULL,
    fn INTEGER NULL,
    tp INTEGER NULL,
    confusion_matrix JSONB NOT NULL DEFAULT '[]'::jsonb,
    classification_report JSONB NOT NULL DEFAULT '{}'::jsonb,
    prediction_distribution JSONB NOT NULL DEFAULT '{}'::jsonb,
    prediction_collapse JSONB NOT NULL DEFAULT '{}'::jsonb,
    label_mapping_version TEXT NOT NULL DEFAULT 'clinical_v1_parasitized_positive',
    raw_model_score_meaning TEXT NOT NULL DEFAULT 'probability_parasitized',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT chk_run_clinical_metrics_split
        CHECK (split_name IN ('train', 'val', 'validation', 'test', 'external'))
);

CREATE TABLE IF NOT EXISTS run_checkpoint_policy (
    run_checkpoint_policy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    model_name TEXT NULL,
    checkpoint_policy TEXT NOT NULL,
    checkpoint_policy_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    selected_epoch INTEGER NULL,
    policy_satisfied BOOLEAN NULL,
    selected_metric TEXT NULL,
    selected_metric_value NUMERIC NULL,
    min_recall_required NUMERIC NULL,
    val_recall_parasitized_selected NUMERIC NULL,
    val_f2_parasitized_selected NUMERIC NULL,
    val_specificity_selected NUMERIC NULL,
    val_auc_selected NUMERIC NULL,
    val_pr_auc_selected NUMERIC NULL,
    val_balanced_accuracy_selected NUMERIC NULL,
    prediction_collapse_detected BOOLEAN NULL,
    all_epochs_collapsed BOOLEAN NULL,
    checkpoint_warning TEXT NULL,
    checkpoint_path TEXT NULL,
    checkpoint_policy_summary_path TEXT NULL,
    model_metadata_path TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS run_threshold_calibration (
    run_threshold_calibration_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    model_name TEXT NULL,
    threshold_policy TEXT NOT NULL DEFAULT 'target_recall',
    threshold_source TEXT NOT NULL DEFAULT 'validation_calibration',
    threshold_selected NUMERIC NOT NULL,
    default_threshold NUMERIC NOT NULL DEFAULT 0.5,
    target_recall NUMERIC NULL,
    target_recall_satisfied BOOLEAN NULL,
    min_specificity NUMERIC NULL,
    validation_recall_at_threshold NUMERIC NULL,
    validation_specificity_at_threshold NUMERIC NULL,
    validation_precision_at_threshold NUMERIC NULL,
    validation_f1_at_threshold NUMERIC NULL,
    validation_f2_at_threshold NUMERIC NULL,
    validation_balanced_accuracy_at_threshold NUMERIC NULL,
    validation_pr_auc NUMERIC NULL,
    validation_roc_auc NUMERIC NULL,
    default_threshold_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    selected_threshold_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    candidate_count INTEGER NULL,
    threshold_warning TEXT NULL,
    calibration_split TEXT NOT NULL DEFAULT 'val',
    threshold_calibration_path TEXT NULL,
    model_metadata_path TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT chk_run_threshold_calibration_split
        CHECK (calibration_split IN ('val', 'validation'))
);

CREATE TABLE IF NOT EXISTS run_image_predictions (
    run_image_prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    image_id UUID NULL REFERENCES dataset_split_images(image_id) ON DELETE SET NULL,
    split_name TEXT NULL,
    usage_context TEXT NULL,
    filename TEXT NULL,
    relative_path TEXT NULL,
    true_label INTEGER NULL,
    true_label_name TEXT NULL,
    predicted_label INTEGER NULL,
    predicted_label_name TEXT NULL,
    probability_parasitized NUMERIC NULL,
    probability_uninfected NUMERIC NULL,
    raw_model_score NUMERIC NULL,
    raw_model_score_meaning TEXT NOT NULL DEFAULT 'probability_parasitized',
    threshold_used NUMERIC NULL,
    threshold_source TEXT NULL,
    is_correct BOOLEAN NULL,
    case_type TEXT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_run_image_predictions_split
        CHECK (split_name IS NULL OR split_name IN ('train', 'val', 'validation', 'test', 'external')),
    CONSTRAINT chk_run_image_predictions_usage_context
        CHECK (
            usage_context IS NULL OR usage_context IN (
                'train',
                'validation',
                'evaluation',
                'explainability',
                'tta',
                'ensemble',
                'svm_features',
                'inference'
            )
        ),
    CONSTRAINT chk_run_image_predictions_case_type
        CHECK (
            case_type IS NULL OR case_type IN (
                'true_positive',
                'true_negative',
                'false_positive',
                'false_negative',
                'low_confidence',
                'unknown'
            )
        )
);

CREATE INDEX IF NOT EXISTS idx_run_io_records_run_type
    ON run_io_records(run_type);
CREATE INDEX IF NOT EXISTS idx_run_io_records_model_name
    ON run_io_records(model_name);
CREATE INDEX IF NOT EXISTS idx_run_io_records_model_metadata_gin
    ON run_io_records USING GIN (model_metadata);
CREATE INDEX IF NOT EXISTS idx_run_io_records_clinical_metadata_gin
    ON run_io_records USING GIN (clinical_metadata);

CREATE INDEX IF NOT EXISTS idx_run_clinical_metrics_run_id
    ON run_clinical_metrics(run_id);
CREATE INDEX IF NOT EXISTS idx_run_clinical_metrics_model_name
    ON run_clinical_metrics(model_name);
CREATE INDEX IF NOT EXISTS idx_run_clinical_metrics_split_name
    ON run_clinical_metrics(split_name);

CREATE INDEX IF NOT EXISTS idx_run_checkpoint_policy_run_id
    ON run_checkpoint_policy(run_id);
CREATE INDEX IF NOT EXISTS idx_run_threshold_calibration_run_id
    ON run_threshold_calibration(run_id);

CREATE INDEX IF NOT EXISTS idx_run_image_predictions_run_id
    ON run_image_predictions(run_id);
CREATE INDEX IF NOT EXISTS idx_run_image_predictions_case_type
    ON run_image_predictions(case_type);
CREATE INDEX IF NOT EXISTS idx_run_image_predictions_split
    ON run_image_predictions(split_name);

DROP VIEW IF EXISTS vw_run_image_predictions_summary CASCADE;
DROP VIEW IF EXISTS vw_run_artifacts_summary CASCADE;
DROP VIEW IF EXISTS vw_threshold_calibration_summary CASCADE;
DROP VIEW IF EXISTS vw_checkpoint_policy_summary CASCADE;
DROP VIEW IF EXISTS vw_clinical_run_summary CASCADE;

CREATE VIEW vw_checkpoint_policy_summary AS
SELECT
    rcp.run_id,
    rcp.model_name,
    rcp.checkpoint_policy,
    rcp.min_recall_required,
    rcp.selected_epoch,
    rcp.policy_satisfied,
    rcp.selected_metric,
    rcp.selected_metric_value,
    rcp.val_recall_parasitized_selected,
    rcp.val_f2_parasitized_selected,
    rcp.val_specificity_selected,
    rcp.val_auc_selected,
    rcp.prediction_collapse_detected,
    rcp.all_epochs_collapsed,
    rcp.checkpoint_warning,
    rcp.checkpoint_path,
    rcp.created_at
FROM run_checkpoint_policy rcp;

CREATE VIEW vw_threshold_calibration_summary AS
SELECT
    rtc.run_id,
    rtc.model_name,
    rtc.threshold_policy,
    rtc.threshold_source,
    rtc.threshold_selected,
    rtc.default_threshold,
    rtc.target_recall,
    rtc.target_recall_satisfied,
    rtc.validation_recall_at_threshold,
    rtc.validation_specificity_at_threshold,
    rtc.validation_f2_at_threshold,
    rtc.validation_pr_auc,
    rtc.validation_roc_auc,
    rtc.threshold_warning,
    rtc.calibration_split,
    rtc.created_at
FROM run_threshold_calibration rtc;

CREATE VIEW vw_run_artifacts_summary AS
SELECT
    a.run_id,
    a.artifact_type,
    a.path AS artifact_path,
    CASE LOWER(COALESCE(a.metadata->>'exists', 'true'))
        WHEN 'true' THEN true
        WHEN 't' THEN true
        WHEN '1' THEN true
        WHEN 'false' THEN false
        WHEN 'f' THEN false
        WHEN '0' THEN false
        ELSE true
    END AS exists,
    a.created_at,
    a.name,
    a.mime_type,
    a.file_size_bytes,
    a.metadata
FROM artifacts a;

CREATE VIEW vw_run_image_predictions_summary AS
SELECT
    rip.run_id,
    rip.split_name,
    rip.usage_context,
    rip.filename,
    rip.relative_path,
    rip.true_label_name,
    rip.predicted_label_name,
    rip.probability_parasitized,
    rip.threshold_used,
    rip.threshold_source,
    rip.case_type,
    rip.is_correct,
    rip.created_at
FROM run_image_predictions rip;

CREATE VIEW vw_clinical_run_summary AS
WITH latest_io AS (
    SELECT DISTINCT ON (run_id)
        run_id,
        model_name,
        clinical_metadata,
        output_results
    FROM run_io_records
    ORDER BY run_id, created_at DESC
),
latest_metrics AS (
    SELECT DISTINCT ON (run_id)
        *
    FROM run_clinical_metrics
    WHERE split_name IN ('test', 'external')
    ORDER BY run_id, created_at DESC
),
latest_checkpoint AS (
    SELECT DISTINCT ON (run_id)
        *
    FROM run_checkpoint_policy
    ORDER BY run_id, created_at DESC
),
latest_threshold AS (
    SELECT DISTINCT ON (run_id)
        *
    FROM run_threshold_calibration
    ORDER BY run_id, created_at DESC
)
SELECT
    r.id AS run_id,
    r.run_name,
    r.run_type,
    r.script_name,
    COALESCE(lm.model_name, lc.model_name, lt.model_name, lio.model_name, m.name) AS model_name,
    r.started_at,
    r.finished_at,
    r.status,
    lc.checkpoint_policy,
    COALESCE(lm.threshold_source, lt.threshold_source) AS threshold_source,
    COALESCE(lm.threshold_used, lt.threshold_selected) AS threshold_used,
    lt.target_recall,
    lm.accuracy,
    lm.recall_parasitized,
    lm.specificity,
    lm.f2_parasitized,
    lm.pr_auc_parasitized,
    lm.roc_auc_parasitized,
    lm.balanced_accuracy,
    CASE LOWER(COALESCE(
        lm.prediction_collapse->>'collapsed',
        lm.metadata->>'prediction_collapse_detected'
    ))
        WHEN 'true' THEN true
        WHEN 't' THEN true
        WHEN '1' THEN true
        WHEN 'false' THEN false
        WHEN 'f' THEN false
        WHEN '0' THEN false
        ELSE NULL
    END AS prediction_collapse_detected,
    lc.checkpoint_warning,
    lt.threshold_warning,
    lio.clinical_metadata,
    lio.output_results
FROM runs r
LEFT JOIN models m ON m.id = r.model_id
LEFT JOIN latest_io lio ON lio.run_id = r.id
LEFT JOIN latest_metrics lm ON lm.run_id = r.id
LEFT JOIN latest_checkpoint lc ON lc.run_id = r.id
LEFT JOIN latest_threshold lt ON lt.run_id = r.id;
