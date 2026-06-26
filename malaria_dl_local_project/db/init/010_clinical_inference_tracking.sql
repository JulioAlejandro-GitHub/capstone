CREATE INDEX IF NOT EXISTS idx_predictions_metadata_workflow
    ON predictions ((metadata->>'workflow'));

CREATE INDEX IF NOT EXISTS idx_runs_inference_script
    ON runs (run_type, script_name);

DROP VIEW IF EXISTS vw_clinical_inference_predictions CASCADE;

CREATE VIEW vw_clinical_inference_predictions AS
SELECT
    up.prediction_id,
    up.run_id,
    up.experiment_id,
    up.model_id,
    up.model_name,
    up.model_type,
    up.run_name,
    up.run_type,
    up.run_status,
    up.script_name,
    up.command,
    up.started_at,
    up.finished_at,
    up.created_at,
    COALESCE(
        up.prediction_metadata->>'workflow',
        up.parameters->>'workflow',
        'clinical_inference_experimental'
    ) AS workflow,
    up.image_id,
    up.image_path,
    up.artifact_id,
    COALESCE(up.artifact_path, up.image_path) AS image_stored_path,
    up.original_image_path AS image_original_path,
    up.original_filename,
    up.stored_filename,
    up.mime_type,
    up.file_size_bytes,
    up.checksum,
    up.true_label,
    up.predicted_label,
    up.probability_parasitized,
    up.probability_uninfected,
    up.score,
    up.score_positive_label,
    up.threshold,
    up.is_correct,
    up.case_type,
    up.confidence_level,
    up.decision AS decision_code,
    COALESCE(
        up.prediction_metadata->>'human_readable_response',
        up.parameters->>'human_readable_response'
    ) AS human_readable_response,
    NULLIF(
        COALESCE(
            up.prediction_metadata #>> '{quality,passed}',
            up.parameters #>> '{quality,passed}'
        ),
        ''
    )::BOOLEAN AS quality_passed,
    COALESCE(
        up.prediction_metadata #> '{quality,warnings}',
        up.parameters #> '{quality,warnings}',
        '[]'::jsonb
    ) AS quality_warnings,
    COALESCE(
        up.prediction_metadata #> '{quality,metrics}',
        up.parameters #> '{quality,metrics}',
        '{}'::jsonb
    ) AS quality_metrics,
    NULLIF(
        COALESCE(
            up.prediction_metadata->>'raw_model_score',
            up.parameters->>'raw_model_score'
        ),
        ''
    )::NUMERIC AS raw_model_score,
    COALESCE(
        up.prediction_metadata #>> '{calibration,method}',
        up.parameters #>> '{calibration,method}',
        'none'
    ) AS calibration_method,
    NULLIF(
        COALESCE(
            up.prediction_metadata #>> '{calibration,applied}',
            up.parameters #>> '{calibration,applied}'
        ),
        ''
    )::BOOLEAN AS calibration_applied,
    up.tta AS tta_applied,
    up.n_aug,
    NULLIF(
        COALESCE(
            up.prediction_metadata->>'ensemble_applied',
            up.parameters->>'ensemble_applied'
        ),
        ''
    )::BOOLEAN AS ensemble_applied,
    COALESCE(
        up.prediction_metadata #> '{ensemble_models}',
        up.parameters #> '{ensemble_models}',
        '[]'::jsonb
    ) AS ensemble_models,
    COALESCE(
        up.prediction_metadata #> '{ensemble_weights}',
        up.parameters #> '{ensemble_weights}',
        '[]'::jsonb
    ) AS ensemble_weights,
    up.explainability_method,
    up.explainability_path,
    up.explainability_success,
    up.prediction_metadata,
    up.artifact_metadata,
    up.parameters AS run_parameters,
    up.run_metadata
FROM vw_uploaded_predictions up
WHERE
    up.run_type = 'inference'
    AND up.script_name = 'src.predict_image'
    AND COALESCE(
        up.prediction_metadata->>'source',
        up.artifact_metadata->>'source',
        up.source
    ) = 'uploaded_for_prediction';
