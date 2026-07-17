CREATE OR REPLACE VIEW vw_model_run_summary AS
SELECT
    m.id AS model_id,
    m.name AS model_name,
    m.model_type,
    COUNT(DISTINCT r.id) AS total_runs,
    COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'completed') AS completed_runs,
    COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'failed') AS failed_runs,
    MAX(r.started_at) AS last_run_at,
    MAX(rm.metric_value) FILTER (
        WHERE rm.metric_name IN ('accuracy', 'test_accuracy', 'val_accuracy')
    ) AS best_accuracy,
    MAX(rm.metric_value) FILTER (
        WHERE rm.metric_name IN ('recall', 'recall_macro', 'sensitivity', 'test_recall')
    ) AS best_recall,
    MAX(rm.metric_value) FILTER (
        WHERE rm.metric_name IN ('f1_score', 'f1_macro', 'test_f1')
    ) AS best_f1_score,
    MAX(rm.metric_value) FILTER (
        WHERE rm.metric_name IN ('auc', 'test_auc', 'val_auc')
    ) AS best_auc
FROM models m
LEFT JOIN runs r ON r.model_id = m.id
LEFT JOIN run_metrics rm ON rm.run_id = r.id
GROUP BY m.id, m.name, m.model_type;

CREATE OR REPLACE VIEW vw_run_dashboard AS
SELECT
    r.id AS run_id,
    r.run_name,
    r.run_type,
    r.status,
    m.name AS model_name,
    d.name AS dataset_name,
    r.started_at,
    r.finished_at,
    r.duration_seconds,
    MAX(rm.metric_value) FILTER (
        WHERE rm.metric_name IN ('accuracy', 'test_accuracy', 'val_accuracy')
    ) AS accuracy,
    MAX(rm.metric_value) FILTER (
        WHERE rm.metric_name IN ('precision', 'precision_macro', 'test_precision')
    ) AS precision,
    MAX(rm.metric_value) FILTER (
        WHERE rm.metric_name IN ('recall', 'recall_macro', 'sensitivity', 'test_recall')
    ) AS recall,
    MAX(rm.metric_value) FILTER (
        WHERE rm.metric_name IN ('f1_score', 'f1_macro', 'test_f1')
    ) AS f1_score,
    MAX(rm.metric_value) FILTER (
        WHERE rm.metric_name IN ('auc', 'test_auc', 'val_auc')
    ) AS auc,
    substring(
        r.command
        FROM '--optimizer(?:[[:space:]]+|=)([^[:space:]]+)'
    ) AS optimizer
FROM runs r
LEFT JOIN models m ON m.id = r.model_id
LEFT JOIN datasets d ON d.id = r.dataset_id
LEFT JOIN run_metrics rm ON rm.run_id = r.id
GROUP BY
    r.id,
    r.run_name,
    r.run_type,
    r.status,
    m.name,
    d.name,
    r.started_at,
    r.finished_at,
    r.duration_seconds;

CREATE OR REPLACE VIEW vw_explainability_summary AS
SELECT
    run_id,
    method,
    COUNT(*) AS total_explanations,
    COUNT(*) FILTER (WHERE success IS TRUE) AS successful_explanations,
    COUNT(*) FILTER (WHERE success IS FALSE) AS failed_explanations,
    COUNT(*) FILTER (WHERE case_type = 'true_positive') AS true_positive_count,
    COUNT(*) FILTER (WHERE case_type = 'true_negative') AS true_negative_count,
    COUNT(*) FILTER (WHERE case_type = 'false_positive') AS false_positive_count,
    COUNT(*) FILTER (WHERE case_type = 'false_negative') AS false_negative_count,
    COUNT(*) FILTER (WHERE case_type = 'low_confidence') AS low_confidence_count
FROM explainability_results
GROUP BY run_id, method;
