-- Inferencia reutiliza runs y predicciones reutiliza predictions. Las vistas al
-- final exponen los contratos lógicos inference_runs y cell_predictions sin
-- crear tablas duplicadas.

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS backend_version TEXT;

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS pipeline_version TEXT;

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS configuration JSONB;

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS error_message TEXT;

DO $run_constraints$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'runs'::regclass
          AND conname = 'chk_runs_configuration_object'
    ) THEN
        ALTER TABLE runs
            ADD CONSTRAINT chk_runs_configuration_object
            CHECK (configuration IS NULL OR jsonb_typeof(configuration) = 'object')
            NOT VALID;
    END IF;
END;
$run_constraints$;

CREATE TABLE IF NOT EXISTS image_analysis_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inference_run_id UUID NOT NULL,
    deployed_model_version_id UUID NOT NULL,
    model_version_id UUID NOT NULL,
    input_artifact_id UUID NULL,
    source_image_id UUID NULL,
    idempotency_key TEXT NULL,
    sample_id TEXT NULL,
    patient_id TEXT NULL,
    slide_id TEXT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    quality_status TEXT NOT NULL DEFAULT 'not_assessed',
    quality_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    threshold_used NUMERIC NULL,
    threshold_source TEXT NULL,
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    total_cells INTEGER NULL,
    positive_cells INTEGER NULL,
    started_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    error_message TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT fk_image_analysis_jobs_run_deployment_version
        FOREIGN KEY (
            inference_run_id,
            deployed_model_version_id,
            model_version_id
        )
        REFERENCES run_model_deployments(
            run_id,
            deployed_model_version_id,
            model_version_id
        )
        ON DELETE RESTRICT,
    CONSTRAINT fk_image_analysis_jobs_input_artifact
        FOREIGN KEY (input_artifact_id)
        REFERENCES artifacts(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_image_analysis_jobs_source_image
        FOREIGN KEY (source_image_id)
        REFERENCES dataset_split_images(image_id)
        ON DELETE RESTRICT,
    CONSTRAINT chk_image_analysis_jobs_status
        CHECK (
            status IN (
                'pending', 'running', 'completed', 'failed', 'rejected', 'cancelled'
            )
        ),
    CONSTRAINT chk_image_analysis_jobs_quality_status
        CHECK (
            quality_status IN (
                'not_assessed', 'pending', 'passed', 'warning', 'rejected',
                'failed', 'skipped'
            )
        ),
    CONSTRAINT chk_image_analysis_jobs_source
        CHECK (input_artifact_id IS NOT NULL OR source_image_id IS NOT NULL),
    CONSTRAINT chk_image_analysis_jobs_idempotency_key
        CHECK (idempotency_key IS NULL OR NULLIF(BTRIM(idempotency_key), '') IS NOT NULL),
    CONSTRAINT chk_image_analysis_jobs_threshold
        CHECK (threshold_used IS NULL OR (threshold_used >= 0 AND threshold_used <= 1)),
    CONSTRAINT chk_image_analysis_jobs_counts
        CHECK (
            (total_cells IS NULL OR total_cells >= 0)
            AND (positive_cells IS NULL OR positive_cells >= 0)
            AND (
                total_cells IS NULL
                OR positive_cells IS NULL
                OR positive_cells <= total_cells
            )
        ),
    CONSTRAINT chk_image_analysis_jobs_timestamp_order
        CHECK (
            completed_at IS NULL
            OR started_at IS NULL
            OR completed_at >= started_at
        ),
    CONSTRAINT chk_image_analysis_jobs_status_timestamps
        CHECK (
            (
                status NOT IN ('running', 'completed')
                OR started_at IS NOT NULL
            )
            AND (
                status NOT IN (
                    'completed', 'failed', 'rejected', 'cancelled'
                )
                OR completed_at IS NOT NULL
            )
        ),
    CONSTRAINT chk_image_analysis_jobs_payload_objects
        CHECK (
            jsonb_typeof(quality_metrics) = 'object'
            AND jsonb_typeof(summary) = 'object'
            AND jsonb_typeof(metadata) = 'object'
        )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_image_analysis_jobs_identity
    ON image_analysis_jobs(
        id,
        inference_run_id,
        deployed_model_version_id,
        model_version_id
    );

CREATE UNIQUE INDEX IF NOT EXISTS uq_image_analysis_jobs_idempotency
    ON image_analysis_jobs(inference_run_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_image_analysis_jobs_run
    ON image_analysis_jobs(inference_run_id);

CREATE INDEX IF NOT EXISTS idx_image_analysis_jobs_deployment
    ON image_analysis_jobs(deployed_model_version_id);

CREATE INDEX IF NOT EXISTS idx_image_analysis_jobs_model_version
    ON image_analysis_jobs(model_version_id);

CREATE INDEX IF NOT EXISTS idx_image_analysis_jobs_input_artifact
    ON image_analysis_jobs(input_artifact_id)
    WHERE input_artifact_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_image_analysis_jobs_source_image
    ON image_analysis_jobs(source_image_id)
    WHERE source_image_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_image_analysis_jobs_status_created
    ON image_analysis_jobs(status, created_at DESC);

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS image_analysis_job_id UUID;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS model_version_id UUID;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS deployed_model_version_id UUID;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS inference_run_id UUID;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS classifier_model_version_id UUID;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS detector_model_version_id UUID;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS prediction_scope TEXT NOT NULL DEFAULT 'legacy_image';

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS cell_index INTEGER;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS source_image_id UUID;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS bbox_x NUMERIC;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS bbox_y NUMERIC;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS bbox_width NUMERIC;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS bbox_height NUMERIC;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS crop_artifact_id UUID;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS explanation_artifact_id UUID;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS probability_parasitized NUMERIC;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS probability_uninfected NUMERIC;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS threshold_used NUMERIC;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS predicted_class SMALLINT;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS confidence_level TEXT;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS quality_status TEXT;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS review_status TEXT NOT NULL DEFAULT 'unreviewed';

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS reviewed_label TEXT;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS reviewed_by TEXT;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;

DO $prediction_constraints$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'chk_predictions_probability_parasitized'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT chk_predictions_probability_parasitized
            CHECK (
                probability_parasitized IS NULL
                OR (
                    probability_parasitized >= 0
                    AND probability_parasitized <= 1
                )
            ) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'chk_predictions_probability_uninfected'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT chk_predictions_probability_uninfected
            CHECK (
                probability_uninfected IS NULL
                OR (
                    probability_uninfected >= 0
                    AND probability_uninfected <= 1
                )
            ) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'chk_predictions_predicted_class'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT chk_predictions_predicted_class
            CHECK (predicted_class IS NULL OR predicted_class IN (0, 1))
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'chk_predictions_class_label'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT chk_predictions_class_label
            CHECK (
                predicted_class IS NULL
                OR (predicted_class = 0 AND predicted_label = 'uninfected')
                OR (predicted_class = 1 AND predicted_label = 'parasitized')
            ) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'chk_predictions_threshold_used'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT chk_predictions_threshold_used
            CHECK (
                threshold_used IS NULL
                OR (threshold_used >= 0 AND threshold_used <= 1)
            ) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'chk_predictions_scope'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT chk_predictions_scope
            CHECK (prediction_scope IN ('legacy_image', 'image', 'cell'))
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'chk_predictions_bbox'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT chk_predictions_bbox
            CHECK (
                (bbox_x IS NULL OR bbox_x >= 0)
                AND (bbox_y IS NULL OR bbox_y >= 0)
                AND (bbox_width IS NULL OR bbox_width > 0)
                AND (bbox_height IS NULL OR bbox_height > 0)
            ) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'chk_predictions_quality_status'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT chk_predictions_quality_status
            CHECK (
                quality_status IS NULL
                OR quality_status IN (
                    'not_assessed', 'pending', 'passed', 'warning', 'rejected',
                    'failed', 'skipped'
                )
            ) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'chk_predictions_confidence_level'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT chk_predictions_confidence_level
            CHECK (
                confidence_level IS NULL
                OR confidence_level IN (
                    'low', 'medium', 'high', 'uncertain', 'not_assessed'
                )
            ) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'chk_predictions_review_status'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT chk_predictions_review_status
            CHECK (
                review_status IN (
                    'unreviewed', 'pending', 'confirmed', 'corrected', 'rejected'
                )
            ) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'chk_predictions_reviewed_label'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT chk_predictions_reviewed_label
            CHECK (
                reviewed_label IS NULL
                OR reviewed_label IN ('uninfected', 'parasitized')
            ) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'chk_predictions_cell_requirements'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT chk_predictions_cell_requirements
            CHECK (
                prediction_scope <> 'cell'
                OR (
                    image_analysis_job_id IS NOT NULL
                    AND inference_run_id IS NOT NULL
                    AND deployed_model_version_id IS NOT NULL
                    AND model_version_id IS NOT NULL
                    AND classifier_model_version_id IS NOT NULL
                    AND model_version_id = classifier_model_version_id
                    AND run_id IS NOT NULL
                    AND run_id = inference_run_id
                    AND cell_index IS NOT NULL
                    AND cell_index >= 0
                    AND bbox_x IS NOT NULL
                    AND bbox_y IS NOT NULL
                    AND bbox_width IS NOT NULL
                    AND bbox_height IS NOT NULL
                    AND probability_parasitized IS NOT NULL
                    AND probability_uninfected IS NOT NULL
                    AND threshold_used IS NOT NULL
                    AND predicted_class IS NOT NULL
                    AND predicted_label IS NOT NULL
                )
            ) NOT VALID;
    END IF;
END;
$prediction_constraints$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_predictions_job_cell_index
    ON predictions(image_analysis_job_id, cell_index)
    WHERE prediction_scope = 'cell';

CREATE INDEX IF NOT EXISTS idx_predictions_analysis_job
    ON predictions(image_analysis_job_id);

CREATE INDEX IF NOT EXISTS idx_predictions_model_version
    ON predictions(model_version_id);

CREATE INDEX IF NOT EXISTS idx_predictions_deployed_model_version
    ON predictions(deployed_model_version_id);

CREATE INDEX IF NOT EXISTS idx_predictions_inference_run
    ON predictions(inference_run_id);

CREATE INDEX IF NOT EXISTS idx_predictions_classifier_model_version
    ON predictions(classifier_model_version_id);

CREATE INDEX IF NOT EXISTS idx_predictions_detector_model_version
    ON predictions(detector_model_version_id)
    WHERE detector_model_version_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_predictions_review_status
    ON predictions(review_status, created_at DESC);

DO $prediction_foreign_keys$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'fk_predictions_analysis_job'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT fk_predictions_analysis_job
            FOREIGN KEY (image_analysis_job_id)
            REFERENCES image_analysis_jobs(id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'fk_predictions_model_version'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT fk_predictions_model_version
            FOREIGN KEY (model_version_id)
            REFERENCES model_versions(id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'fk_predictions_deployed_model_version'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT fk_predictions_deployed_model_version
            FOREIGN KEY (deployed_model_version_id)
            REFERENCES deployed_model_versions(id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'fk_predictions_inference_run'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT fk_predictions_inference_run
            FOREIGN KEY (inference_run_id)
            REFERENCES runs(id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'fk_predictions_classifier_model_version'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT fk_predictions_classifier_model_version
            FOREIGN KEY (classifier_model_version_id)
            REFERENCES model_versions(id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'fk_predictions_detector_model_version'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT fk_predictions_detector_model_version
            FOREIGN KEY (detector_model_version_id)
            REFERENCES model_versions(id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'fk_predictions_source_image'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT fk_predictions_source_image
            FOREIGN KEY (source_image_id)
            REFERENCES dataset_split_images(image_id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'fk_predictions_crop_artifact'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT fk_predictions_crop_artifact
            FOREIGN KEY (crop_artifact_id)
            REFERENCES artifacts(id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'fk_predictions_explanation_artifact'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT fk_predictions_explanation_artifact
            FOREIGN KEY (explanation_artifact_id)
            REFERENCES artifacts(id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'predictions'::regclass
          AND conname = 'fk_predictions_job_provenance'
    ) THEN
        ALTER TABLE predictions
            ADD CONSTRAINT fk_predictions_job_provenance
            FOREIGN KEY (
                image_analysis_job_id,
                inference_run_id,
                deployed_model_version_id,
                model_version_id
            )
            REFERENCES image_analysis_jobs(
                id,
                inference_run_id,
                deployed_model_version_id,
                model_version_id
            )
            ON DELETE RESTRICT
            NOT VALID;
    END IF;
END;
$prediction_foreign_keys$;

CREATE OR REPLACE VIEW inference_runs AS
SELECT
    r.id,
    r.id AS run_id,
    primary_binding.deployed_model_version_id,
    primary_binding.model_version_id,
    r.backend_version,
    r.pipeline_version,
    r.started_at,
    r.finished_at AS completed_at,
    r.status,
    COALESCE(
        r.configuration,
        r.execution_parameters,
        r.parameters,
        '{}'::jsonb
    ) AS configuration,
    r.metadata,
    r.error_message,
    COALESCE(all_bindings.bindings, '[]'::jsonb) AS deployment_bindings
FROM runs r
LEFT JOIN LATERAL (
    SELECT
        rmd.deployed_model_version_id,
        rmd.model_version_id
    FROM run_model_deployments rmd
    WHERE rmd.run_id = r.id
    ORDER BY
        (rmd.role = 'primary') DESC,
        rmd.ordinal,
        rmd.created_at,
        rmd.id
    LIMIT 1
) primary_binding ON TRUE
LEFT JOIN LATERAL (
    SELECT jsonb_agg(
        jsonb_build_object(
            'deployed_model_version_id', rmd.deployed_model_version_id,
            'model_version_id', rmd.model_version_id,
            'role', rmd.role,
            'ordinal', rmd.ordinal,
            'weight', rmd.weight
        )
        ORDER BY rmd.ordinal, rmd.created_at, rmd.id
    ) AS bindings
    FROM run_model_deployments rmd
    WHERE rmd.run_id = r.id
) all_bindings ON TRUE
WHERE r.run_type = 'inference';

CREATE OR REPLACE VIEW cell_predictions AS
SELECT
    p.id,
    p.id AS cell_prediction_id,
    p.image_analysis_job_id,
    p.cell_index,
    p.inference_run_id,
    p.deployed_model_version_id,
    p.model_version_id,
    p.classifier_model_version_id,
    p.detector_model_version_id,
    p.source_image_id,
    p.bbox_x,
    p.bbox_y,
    p.bbox_width,
    p.bbox_height,
    p.crop_artifact_id,
    p.probability_parasitized,
    p.probability_uninfected,
    p.threshold_used,
    p.predicted_class,
    p.predicted_label,
    p.confidence_level,
    p.quality_status,
    p.explanation_artifact_id,
    p.review_status,
    p.reviewed_label,
    p.reviewed_by,
    p.reviewed_at,
    p.created_at,
    p.metadata
FROM predictions p
WHERE p.prediction_scope = 'cell';

COMMENT ON TABLE image_analysis_jobs IS
    'Caso/imagen procesado dentro de un inference run y mediante un deployment/version explícitos.';

COMMENT ON VIEW inference_runs IS
    'Contrato lógico sobre runs de tipo inference; completed_at conserva finished_at y los IDs se resuelven por el puente.';

COMMENT ON VIEW cell_predictions IS
    'Contrato lógico de predicciones celulares almacenadas canónicamente en predictions.';
