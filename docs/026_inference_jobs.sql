-- Columnas adicionales en `runs` para trazabilidad de inferencia.
ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS backend_version TEXT,
    ADD COLUMN IF NOT EXISTS pipeline_version TEXT,
    ADD COLUMN IF NOT EXISTS configuration JSONB,
    ADD COLUMN IF NOT EXISTS error_message TEXT;

ALTER TABLE runs
    ADD CONSTRAINT chk_runs_configuration_object
    CHECK (configuration IS NULL OR jsonb_typeof(configuration) = 'object');

-- Representa una solicitud de análisis de imagen dentro de un inference run.
CREATE TABLE IF NOT EXISTS image_analysis_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inference_run_id UUID NOT NULL,
    deployed_model_version_id UUID NOT NULL,
    model_version_id UUID NOT NULL,
    input_artifact_id UUID,
    source_image_id UUID,
    idempotency_key TEXT,
    sample_id TEXT,
    patient_id TEXT,
    slide_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    quality_status TEXT NOT NULL DEFAULT 'not_assessed',
    quality_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    threshold_used NUMERIC,
    threshold_source TEXT,
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    total_cells INTEGER,
    positive_cells INTEGER,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

COMMENT ON TABLE image_analysis_jobs IS
    'Solicitud de análisis de una imagen/caso dentro de un inference run.';

-- Columnas adicionales en `predictions` para predicciones celulares gobernadas.
ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS image_analysis_job_id UUID,
    ADD COLUMN IF NOT EXISTS model_version_id UUID,
    ADD COLUMN IF NOT EXISTS deployed_model_version_id UUID,
    ADD COLUMN IF NOT EXISTS inference_run_id UUID,
    ADD COLUMN IF NOT EXISTS classifier_model_version_id UUID,
    ADD COLUMN IF NOT EXISTS detector_model_version_id UUID,
    ADD COLUMN IF NOT EXISTS prediction_scope TEXT,
    ADD COLUMN IF NOT EXISTS cell_index INTEGER,
    ADD COLUMN IF NOT EXISTS source_image_id UUID,
    ADD COLUMN IF NOT EXISTS bbox_x NUMERIC,
    ADD COLUMN IF NOT EXISTS bbox_y NUMERIC,
    ADD COLUMN IF NOT EXISTS bbox_width NUMERIC,
    ADD COLUMN IF NOT EXISTS bbox_height NUMERIC,
    ADD COLUMN IF NOT EXISTS crop_artifact_id UUID,
    ADD COLUMN IF NOT EXISTS explanation_artifact_id UUID,
    ADD COLUMN IF NOT EXISTS probability_parasitized NUMERIC,
    ADD COLUMN IF NOT EXISTS probability_uninfected NUMERIC,
    ADD COLUMN IF NOT EXISTS threshold_used NUMERIC,
    ADD COLUMN IF NOT EXISTS predicted_class SMALLINT,
    ADD COLUMN IF NOT EXISTS confidence_level TEXT,
    ADD COLUMN IF NOT EXISTS quality_status TEXT,
    ADD COLUMN IF NOT EXISTS review_status TEXT,
    ADD COLUMN IF NOT EXISTS reviewed_label TEXT,
    ADD COLUMN IF NOT EXISTS reviewed_by TEXT,
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;

UPDATE predictions
SET prediction_scope = 'legacy_image'
WHERE prediction_scope IS NULL;

ALTER TABLE predictions
    ALTER COLUMN prediction_scope SET DEFAULT 'legacy_image';

ALTER TABLE predictions
    ALTER COLUMN prediction_scope SET NOT NULL;

UPDATE predictions
SET review_status = 'unreviewed'
WHERE review_status IS NULL;

ALTER TABLE predictions
    ALTER COLUMN review_status SET DEFAULT 'unreviewed';

ALTER TABLE predictions
    ALTER COLUMN review_status SET NOT NULL;

DO $constraints$
BEGIN
    ALTER TABLE image_analysis_jobs
        ADD CONSTRAINT chk_image_analysis_jobs_status
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'rejected', 'cancelled'));

    ALTER TABLE image_analysis_jobs
        ADD CONSTRAINT chk_image_analysis_jobs_quality_status
        CHECK (quality_status IN ('not_assessed', 'pending', 'passed', 'warning', 'rejected', 'failed', 'skipped'));

    ALTER TABLE image_analysis_jobs
        ADD CONSTRAINT chk_image_analysis_jobs_source
        CHECK (input_artifact_id IS NOT NULL OR source_image_id IS NOT NULL);

    ALTER TABLE image_analysis_jobs
        ADD CONSTRAINT chk_image_analysis_jobs_counts
        CHECK ((total_cells IS NULL OR total_cells >= 0) AND (positive_cells IS NULL OR positive_cells >= 0) AND (positive_cells IS NULL OR total_cells IS NULL OR positive_cells <= total_cells));

    ALTER TABLE predictions
        ADD CONSTRAINT chk_predictions_scope
        CHECK (prediction_scope IN ('legacy_image', 'image', 'cell'));

    ALTER TABLE predictions
        ADD CONSTRAINT chk_predictions_probability_parasitized
        CHECK (probability_parasitized IS NULL OR (probability_parasitized >= 0 AND probability_parasitized <= 1));

    ALTER TABLE predictions
        ADD CONSTRAINT chk_predictions_probability_uninfected
        CHECK (probability_uninfected IS NULL OR (probability_uninfected >= 0 AND probability_uninfected <= 1));

    ALTER TABLE predictions
        ADD CONSTRAINT chk_predictions_threshold_used
        CHECK (threshold_used IS NULL OR (threshold_used >= 0 AND threshold_used <= 1));

    ALTER TABLE predictions
        ADD CONSTRAINT chk_predictions_predicted_class
        CHECK (predicted_class IS NULL OR predicted_class IN (0, 1));

    ALTER TABLE predictions
        ADD CONSTRAINT chk_predictions_class_label
        CHECK (
            (predicted_class = 0 AND predicted_label = 'uninfected')
            OR (predicted_class = 1 AND predicted_label = 'parasitized')
            OR predicted_class IS NULL
        );

    ALTER TABLE predictions
        ADD CONSTRAINT chk_predictions_cell_requirements
        CHECK (
            prediction_scope <> 'cell'
            OR (
                image_analysis_job_id IS NOT NULL
                AND inference_run_id IS NOT NULL
                AND deployed_model_version_id IS NOT NULL
                AND classifier_model_version_id IS NOT NULL
                AND cell_index IS NOT NULL
                AND bbox_x IS NOT NULL AND bbox_y IS NOT NULL
                AND bbox_width IS NOT NULL AND bbox_height IS NOT NULL
                AND probability_parasitized IS NOT NULL
                AND probability_uninfected IS NOT NULL
                AND threshold_used IS NOT NULL
                AND predicted_class IS NOT NULL
                AND predicted_label IS NOT NULL
            )
        );
END;
$constraints$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_image_analysis_jobs_identity
    ON image_analysis_jobs(id, inference_run_id, deployed_model_version_id, model_version_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_image_analysis_jobs_idempotency
    ON image_analysis_jobs(inference_run_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_image_analysis_jobs_run ON image_analysis_jobs(inference_run_id);
CREATE INDEX IF NOT EXISTS idx_image_analysis_jobs_deployment ON image_analysis_jobs(deployed_model_version_id);
CREATE INDEX IF NOT EXISTS idx_image_analysis_jobs_model_version ON image_analysis_jobs(model_version_id);
CREATE INDEX IF NOT EXISTS idx_image_analysis_jobs_status_created ON image_analysis_jobs(status, created_at);

CREATE UNIQUE INDEX IF NOT EXISTS uq_predictions_job_cell_index
    ON predictions(image_analysis_job_id, cell_index)
    WHERE prediction_scope = 'cell';

CREATE INDEX IF NOT EXISTS idx_predictions_analysis_job ON predictions(image_analysis_job_id);
CREATE INDEX IF NOT EXISTS idx_predictions_model_version ON predictions(model_version_id);
CREATE INDEX IF NOT EXISTS idx_predictions_deployed_model_version ON predictions(deployed_model_version_id);
CREATE INDEX IF NOT EXISTS idx_predictions_inference_run ON predictions(inference_run_id);
CREATE INDEX IF NOT EXISTS idx_predictions_classifier_model_version ON predictions(classifier_model_version_id);

DO $foreign_keys$
BEGIN
    ALTER TABLE image_analysis_jobs
        ADD CONSTRAINT fk_image_analysis_jobs_run_deployment_version
        FOREIGN KEY (inference_run_id, deployed_model_version_id, model_version_id)
        REFERENCES run_model_deployments(run_id, deployed_model_version_id, model_version_id)
        ON DELETE RESTRICT;

    ALTER TABLE image_analysis_jobs
        ADD CONSTRAINT fk_image_analysis_jobs_input_artifact
        FOREIGN KEY (input_artifact_id) REFERENCES artifacts(id) ON DELETE RESTRICT;

    ALTER TABLE image_analysis_jobs
        ADD CONSTRAINT fk_image_analysis_jobs_source_image
        FOREIGN KEY (source_image_id) REFERENCES dataset_split_images(image_id) ON DELETE RESTRICT;

    ALTER TABLE predictions
        ADD CONSTRAINT fk_predictions_job_provenance
        FOREIGN KEY (image_analysis_job_id, inference_run_id, deployed_model_version_id, model_version_id)
        REFERENCES image_analysis_jobs(id, inference_run_id, deployed_model_version_id, model_version_id)
        ON DELETE RESTRICT;

    ALTER TABLE predictions
        ADD CONSTRAINT fk_predictions_classifier_model_version
        FOREIGN KEY (classifier_model_version_id) REFERENCES model_versions(id) ON DELETE RESTRICT;
END;
$foreign_keys$;

-- Vista gobernada de runs de inferencia.
CREATE OR REPLACE VIEW inference_runs AS
SELECT
    run.id AS id,
    run.id AS run_id,
    COALESCE(primary_binding.deployed_model_version_id, first_binding.deployed_model_version_id) AS deployed_model_version_id,
    COALESCE(primary_binding.model_version_id, first_binding.model_version_id) AS model_version_id,
    run.backend_version,
    run.pipeline_version,
    run.started_at,
    run.finished_at AS completed_at,
    run.status,
    COALESCE(run.configuration, run.execution_parameters, run.parameters, '{}'::jsonb) AS configuration,
    run.metadata,
    run.error_message,
    (
        SELECT jsonb_agg(
            jsonb_build_object(
                'deployed_model_version_id', b.deployed_model_version_id,
                'model_version_id', b.model_version_id,
                'role', b.role,
                'ordinal', b.ordinal,
                'weight', b.weight
            ) ORDER BY b.ordinal
        )
        FROM run_model_deployments b
        WHERE b.run_id = run.id
    ) AS deployment_bindings
FROM runs AS run
LEFT JOIN run_model_deployments AS primary_binding
    ON primary_binding.run_id = run.id AND primary_binding.role = 'primary'
LEFT JOIN LATERAL (
    SELECT deployed_model_version_id, model_version_id
    FROM run_model_deployments
    WHERE run_id = run.id
    ORDER BY ordinal
    LIMIT 1
) AS first_binding ON true
WHERE run.run_type = 'inference';

-- Vista gobernada de predicciones celulares.
CREATE OR REPLACE VIEW cell_predictions AS
SELECT
    p.id AS cell_prediction_id,
    p.*
FROM predictions p
WHERE p.prediction_scope = 'cell';