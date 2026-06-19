CREATE OR REPLACE VIEW vw_case_level_explainability AS
SELECT
    er.id AS explainability_id,
    er.run_id,
    er.prediction_id,
    r.experiment_id,
    r.model_id,
    m.name AS model_name,
    m.model_type,
    COALESCE(p.dataset_id, r.dataset_id) AS dataset_id,
    d.name AS dataset_name,
    r.run_name,
    r.run_type,
    r.status AS run_status,
    r.script_name,
    r.command,
    r.started_at,
    r.finished_at,
    r.duration_seconds,
    er.method,
    CASE
        WHEN COALESCE(er.case_type, p.case_type) = 'low_confidence' THEN 'low_confidence'
        WHEN COALESCE(er.true_label, p.true_label) IS NULL
          OR COALESCE(er.predicted_label, p.predicted_label) IS NULL
            THEN COALESCE(er.case_type, p.case_type, 'unknown')
        WHEN COALESCE(er.true_label, p.true_label) = COALESCE(
            NULLIF(r.parameters ->> 'positive_label', ''),
            NULLIF(er.explanation_parameters ->> 'positive_label', ''),
            'parasitized'
        )
          AND COALESCE(er.predicted_label, p.predicted_label) = COALESCE(
            NULLIF(r.parameters ->> 'positive_label', ''),
            NULLIF(er.explanation_parameters ->> 'positive_label', ''),
            'parasitized'
        )
            THEN 'true_positive'
        WHEN COALESCE(er.true_label, p.true_label) <> COALESCE(
            NULLIF(r.parameters ->> 'positive_label', ''),
            NULLIF(er.explanation_parameters ->> 'positive_label', ''),
            'parasitized'
        )
          AND COALESCE(er.predicted_label, p.predicted_label) <> COALESCE(
            NULLIF(r.parameters ->> 'positive_label', ''),
            NULLIF(er.explanation_parameters ->> 'positive_label', ''),
            'parasitized'
        )
            THEN 'true_negative'
        WHEN COALESCE(er.true_label, p.true_label) <> COALESCE(
            NULLIF(r.parameters ->> 'positive_label', ''),
            NULLIF(er.explanation_parameters ->> 'positive_label', ''),
            'parasitized'
        )
          AND COALESCE(er.predicted_label, p.predicted_label) = COALESCE(
            NULLIF(r.parameters ->> 'positive_label', ''),
            NULLIF(er.explanation_parameters ->> 'positive_label', ''),
            'parasitized'
        )
            THEN 'false_positive'
        WHEN COALESCE(er.true_label, p.true_label) = COALESCE(
            NULLIF(r.parameters ->> 'positive_label', ''),
            NULLIF(er.explanation_parameters ->> 'positive_label', ''),
            'parasitized'
        )
          AND COALESCE(er.predicted_label, p.predicted_label) <> COALESCE(
            NULLIF(r.parameters ->> 'positive_label', ''),
            NULLIF(er.explanation_parameters ->> 'positive_label', ''),
            'parasitized'
        )
            THEN 'false_negative'
        ELSE COALESCE(er.case_type, p.case_type, 'unknown')
    END AS case_type,
    COALESCE(er.true_label, p.true_label) AS true_label,
    COALESCE(er.predicted_label, p.predicted_label) AS predicted_label,
    COALESCE(
        NULLIF(r.parameters ->> 'positive_label', ''),
        NULLIF(er.explanation_parameters ->> 'positive_label', ''),
        'parasitized'
    ) AS positive_label,
    COALESCE(p.score, er.score) AS score,
    COALESCE(p.score_positive_label, er.score) AS score_positive_label,
    COALESCE(
        p.threshold,
        CASE
            WHEN (er.explanation_parameters ->> 'threshold') ~ '^-?[0-9]+([.][0-9]+)?$'
                THEN (er.explanation_parameters ->> 'threshold')::NUMERIC
        END,
        CASE
            WHEN (r.parameters ->> 'threshold') ~ '^-?[0-9]+([.][0-9]+)?$'
                THEN (r.parameters ->> 'threshold')::NUMERIC
        END,
        0.5
    ) AS threshold,
    COALESCE(
        p.is_correct,
        COALESCE(er.true_label, p.true_label) = COALESCE(er.predicted_label, p.predicted_label)
    ) AS is_correct,
    p.image_id,
    COALESCE(NULLIF(er.image_path, ''), NULLIF(p.image_path, '')) AS image_path,
    NULLIF(er.output_path, '') AS explanation_output_path,
    a.path AS artifact_path,
    a.artifact_type,
    er.last_conv_layer,
    er.success,
    er.error_message,
    er.explanation_parameters,
    p.metadata AS prediction_metadata,
    er.metadata AS explainability_metadata,
    r.parameters AS run_parameters,
    r.metadata AS run_metadata,
    a.id AS artifact_id
FROM explainability_results er
LEFT JOIN predictions p ON p.id = er.prediction_id
LEFT JOIN runs r ON r.id = er.run_id
LEFT JOIN models m ON m.id = r.model_id
LEFT JOIN datasets d ON d.id = COALESCE(p.dataset_id, r.dataset_id)
LEFT JOIN LATERAL (
    SELECT
        artifacts.id,
        artifacts.path,
        artifacts.artifact_type
    FROM artifacts
    WHERE artifacts.run_id = er.run_id
      AND (
          (er.output_path IS NOT NULL AND artifacts.path = er.output_path)
          OR (er.image_path IS NOT NULL AND artifacts.path = er.image_path)
          OR (p.image_path IS NOT NULL AND artifacts.path = p.image_path)
      )
    ORDER BY
        CASE
            WHEN er.output_path IS NOT NULL AND artifacts.path = er.output_path THEN 1
            WHEN er.image_path IS NOT NULL AND artifacts.path = er.image_path THEN 2
            ELSE 3
        END,
        artifacts.created_at DESC
    LIMIT 1
) a ON TRUE;

CREATE OR REPLACE VIEW vw_false_positive_cases AS
SELECT
    explainability_id,
    prediction_id,
    run_id,
    model_name,
    dataset_name,
    method,
    case_type,
    true_label,
    predicted_label,
    positive_label,
    score_positive_label,
    threshold,
    image_id,
    image_path,
    explanation_output_path,
    artifact_path,
    artifact_type,
    last_conv_layer,
    success,
    error_message,
    started_at,
    command,
    artifact_id
FROM vw_case_level_explainability
WHERE case_type = 'false_positive'
   OR (
       true_label IS NOT NULL
       AND predicted_label IS NOT NULL
       AND true_label <> positive_label
       AND predicted_label = positive_label
   );

CREATE OR REPLACE VIEW vw_false_negative_cases AS
SELECT
    explainability_id,
    prediction_id,
    run_id,
    model_name,
    dataset_name,
    method,
    case_type,
    true_label,
    predicted_label,
    positive_label,
    score_positive_label,
    threshold,
    image_id,
    image_path,
    explanation_output_path,
    artifact_path,
    artifact_type,
    last_conv_layer,
    success,
    error_message,
    started_at,
    command,
    artifact_id
FROM vw_case_level_explainability
WHERE case_type = 'false_negative'
   OR (
       true_label IS NOT NULL
       AND predicted_label IS NOT NULL
       AND true_label = positive_label
       AND predicted_label <> positive_label
   );

CREATE OR REPLACE VIEW vw_low_confidence_cases AS
SELECT
    explainability_id,
    prediction_id,
    run_id,
    model_name,
    dataset_name,
    method,
    case_type,
    true_label,
    predicted_label,
    positive_label,
    score_positive_label,
    threshold,
    ABS(score_positive_label - threshold) AS confidence_distance,
    image_id,
    image_path,
    explanation_output_path,
    artifact_path,
    artifact_type,
    last_conv_layer,
    success,
    error_message,
    started_at,
    artifact_id
FROM vw_case_level_explainability
WHERE case_type = 'low_confidence'
   OR (
       score_positive_label IS NOT NULL
       AND threshold IS NOT NULL
       AND ABS(score_positive_label - threshold) <= 0.10
   );

CREATE OR REPLACE VIEW vw_case_type_summary AS
SELECT
    model_name,
    dataset_name,
    method,
    case_type,
    COUNT(*) AS total_cases,
    AVG(score_positive_label) AS avg_score,
    MIN(score_positive_label) AS min_score,
    MAX(score_positive_label) AS max_score,
    MAX(started_at) AS latest_run_at
FROM vw_case_level_explainability
GROUP BY model_name, dataset_name, method, case_type;

CREATE OR REPLACE VIEW vw_explainability_gallery AS
SELECT
    explainability_id AS gallery_id,
    run_id,
    model_name,
    dataset_name,
    method,
    case_type,
    true_label,
    predicted_label,
    positive_label,
    score_positive_label,
    threshold,
    image_id,
    image_path,
    explanation_output_path,
    artifact_path,
    artifact_type,
    last_conv_layer,
    success,
    error_message,
    started_at,
    artifact_id
FROM vw_case_level_explainability
WHERE explanation_output_path IS NOT NULL;
