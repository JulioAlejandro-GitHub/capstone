CREATE INDEX IF NOT EXISTS idx_predictions_predicted_label ON predictions(predicted_label);
CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions(created_at);
CREATE INDEX IF NOT EXISTS idx_predictions_metadata_source
    ON predictions ((metadata->>'source'));
CREATE INDEX IF NOT EXISTS idx_artifacts_artifact_type ON artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS idx_artifacts_metadata_source
    ON artifacts ((metadata->>'source'));

CREATE OR REPLACE VIEW vw_uploaded_predictions AS
SELECT
    p.id AS prediction_id,
    p.run_id,
    r.experiment_id,
    r.model_id,
    m.name AS model_name,
    m.model_type,
    r.run_name,
    r.run_type,
    r.status AS run_status,
    r.script_name,
    r.command,
    r.started_at,
    r.finished_at,
    r.duration_seconds,
    p.dataset_id,
    d.name AS dataset_name,
    p.image_id,
    p.image_path,
    a.id AS artifact_id,
    a.path AS artifact_path,
    a.name AS artifact_name,
    a.mime_type,
    a.file_size_bytes,
    a.checksum,
    p.true_label,
    p.predicted_label,
    p.score,
    p.score_positive_label,
    p.threshold,
    p.is_correct,
    p.case_type,
    p.created_at,
    p.metadata AS prediction_metadata,
    a.metadata AS artifact_metadata,
    r.parameters,
    r.metadata AS run_metadata,
    COALESCE(p.metadata->>'source', a.metadata->>'source') AS source,
    COALESCE(
        p.metadata->>'original_image_path',
        a.metadata->>'original_image_path'
    ) AS original_image_path,
    COALESCE(
        p.metadata->>'original_filename',
        a.metadata->>'original_filename'
    ) AS original_filename,
    COALESCE(
        p.metadata->>'stored_filename',
        a.metadata->>'stored_filename',
        a.name
    ) AS stored_filename,
    COALESCE(
        NULLIF(p.metadata->>'probability_parasitized', '')::NUMERIC,
        p.score_positive_label
    ) AS probability_parasitized,
    NULLIF(p.metadata->>'probability_uninfected', '')::NUMERIC AS probability_uninfected,
    p.metadata->>'confidence_level' AS confidence_level,
    p.metadata->>'decision' AS decision,
    COALESCE(
        NULLIF(p.metadata->>'tta', '')::BOOLEAN,
        NULLIF(r.parameters->>'tta', '')::BOOLEAN,
        FALSE
    ) AS tta,
    NULLIF(
        COALESCE(p.metadata->>'n_aug', r.parameters->>'n_aug'),
        ''
    )::INTEGER AS n_aug,
    er.method AS explainability_method,
    er.output_path AS explainability_path,
    er.success AS explainability_success
FROM predictions p
LEFT JOIN runs r ON r.id = p.run_id
LEFT JOIN models m ON m.id = r.model_id
LEFT JOIN datasets d ON d.id = p.dataset_id
LEFT JOIN LATERAL (
    SELECT art.*
    FROM artifacts art
    WHERE art.run_id = p.run_id
      AND (
        art.path = p.image_path
        OR art.artifact_type = 'uploaded_input_image'
        OR art.metadata->>'source' = 'uploaded_for_prediction'
      )
    ORDER BY
        (art.path = p.image_path) DESC,
        (art.artifact_type = 'uploaded_input_image') DESC,
        art.created_at DESC
    LIMIT 1
) a ON TRUE
LEFT JOIN LATERAL (
    SELECT exp.*
    FROM explainability_results exp
    WHERE exp.run_id = p.run_id
      AND (exp.prediction_id = p.id OR exp.image_path = p.image_path)
    ORDER BY exp.created_at DESC
    LIMIT 1
) er ON TRUE
WHERE
    p.metadata->>'source' = 'uploaded_for_prediction'
    OR a.metadata->>'source' = 'uploaded_for_prediction'
    OR a.artifact_type = 'uploaded_input_image';
