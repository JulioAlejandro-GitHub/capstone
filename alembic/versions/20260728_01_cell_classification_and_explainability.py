"""Cell classification, Grad-CAM artifacts, aggregation, and human review."""

from alembic import op


revision = "20260728_01"
down_revision = "20260727_05"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    ALTER VIEW cell_predictions RENAME TO legacy_cell_predictions;
    COMMENT ON VIEW legacy_cell_predictions IS
      'Legacy read model over predictions rows with prediction_scope=cell.';

    CREATE UNIQUE INDEX uq_stage2_model_publications_id_version
      ON stage2_model_publications(id, model_version_id);
    CREATE UNIQUE INDEX uq_cell_crops_id_detection
      ON cell_crops(id, cell_detection_id);

    CREATE TABLE cell_classification_runs (
      id UUID PRIMARY KEY,
      analysis_run_id UUID NOT NULL,
      detection_run_id UUID NOT NULL,
      classification_run_code VARCHAR(20) NOT NULL UNIQUE
        CHECK (classification_run_code ~ '^CLS-[A-F0-9]{8}$'),
      production_model_id UUID NOT NULL,
      stage2_publication_id UUID NOT NULL,
      model_registry_id UUID NOT NULL,
      model_name VARCHAR(160) NOT NULL CHECK (btrim(model_name) <> ''),
      model_version VARCHAR(120),
      model_snapshot JSONB NOT NULL
        CHECK (jsonb_typeof(model_snapshot) = 'object'),
      input_manifest_sha256 CHAR(64) NOT NULL
        CHECK (input_manifest_sha256 ~ '^[0-9a-f]{64}$'),
      status VARCHAR(30) NOT NULL
        CHECK (status IN (
          'created','processing','completed','completed_with_warnings','failed'
        )),
      input_count INTEGER NOT NULL CHECK (input_count >= 0),
      eligible_count INTEGER NOT NULL CHECK (eligible_count >= 0),
      excluded_count INTEGER NOT NULL CHECK (excluded_count >= 0),
      processed_count INTEGER NOT NULL DEFAULT 0 CHECK (processed_count >= 0),
      parasitized_count INTEGER NOT NULL DEFAULT 0
        CHECK (parasitized_count >= 0),
      uninfected_count INTEGER NOT NULL DEFAULT 0
        CHECK (uninfected_count >= 0),
      near_threshold_count INTEGER NOT NULL DEFAULT 0
        CHECK (near_threshold_count >= 0),
      failed_count INTEGER NOT NULL DEFAULT 0 CHECK (failed_count >= 0),
      requested_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
      retry_of_run_id UUID
        REFERENCES cell_classification_runs(id) ON DELETE RESTRICT,
      started_at TIMESTAMPTZ,
      completed_at TIMESTAMPTZ,
      failed_at TIMESTAMPTZ,
      error_code VARCHAR(80),
      error_message TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CONSTRAINT fk_cell_classification_run_detection_analysis
        FOREIGN KEY(detection_run_id, analysis_run_id)
        REFERENCES cell_detection_runs(id, analysis_run_id)
        ON DELETE RESTRICT,
      CONSTRAINT fk_cell_classification_run_deployment_version
        FOREIGN KEY(production_model_id, model_registry_id)
        REFERENCES deployed_model_versions(id, model_version_id)
        ON DELETE RESTRICT,
      CONSTRAINT fk_cell_classification_run_publication_version
        FOREIGN KEY(stage2_publication_id, model_registry_id)
        REFERENCES stage2_model_publications(id, model_version_id)
        ON DELETE RESTRICT,
      CONSTRAINT uq_cell_classification_runs_identity
        UNIQUE(id, analysis_run_id, detection_run_id),
      CONSTRAINT uq_cell_classification_runs_detection_identity
        UNIQUE(id, detection_run_id),
      CONSTRAINT ck_cell_classification_run_counts CHECK (
        input_count = eligible_count + excluded_count
        AND processed_count <= eligible_count
        AND processed_count =
          parasitized_count + uninfected_count + failed_count
        AND near_threshold_count <= parasitized_count + uninfected_count
      ),
      CONSTRAINT ck_cell_classification_run_retry CHECK (
        retry_of_run_id IS NULL OR retry_of_run_id <> id
      ),
      CONSTRAINT ck_cell_classification_run_model_version CHECK (
        model_version IS NULL OR btrim(model_version) <> ''
      ),
      CONSTRAINT ck_cell_classification_run_terminal_state CHECK (
        (
          status = 'created'
          AND started_at IS NULL
          AND completed_at IS NULL
          AND failed_at IS NULL
          AND error_code IS NULL
          AND error_message IS NULL
        )
        OR
        (
          status = 'processing'
          AND started_at IS NOT NULL
          AND completed_at IS NULL
          AND failed_at IS NULL
          AND error_code IS NULL
          AND error_message IS NULL
        )
        OR
        (
          status IN ('completed','completed_with_warnings')
          AND started_at IS NOT NULL
          AND completed_at IS NOT NULL
          AND failed_at IS NULL
          AND error_code IS NULL
          AND error_message IS NULL
          AND processed_count = eligible_count
        )
        OR
        (
          status = 'failed'
          AND started_at IS NOT NULL
          AND completed_at IS NULL
          AND failed_at IS NOT NULL
          AND error_code IS NOT NULL
          AND btrim(error_code) <> ''
        )
      ),
      CONSTRAINT ck_cell_classification_run_time_order CHECK (
        updated_at >= created_at
        AND (started_at IS NULL OR started_at >= created_at)
        AND (completed_at IS NULL OR completed_at >= started_at)
        AND (failed_at IS NULL OR failed_at >= started_at)
      )
    );

    CREATE UNIQUE INDEX uq_cell_classification_runs_equivalent_active
      ON cell_classification_runs(
        detection_run_id,
        production_model_id,
        COALESCE(model_version, ''),
        COALESCE(model_snapshot->>'checkpoint_sha256', ''),
        COALESCE(model_snapshot->>'inference_version', ''),
        input_manifest_sha256
      )
      WHERE status IN (
        'created','processing','completed','completed_with_warnings'
      );
    CREATE INDEX ix_cell_classification_runs_status_created
      ON cell_classification_runs(status, created_at DESC, id DESC);
    CREATE INDEX ix_cell_classification_runs_analysis_created
      ON cell_classification_runs(analysis_run_id, created_at DESC, id DESC);
    CREATE INDEX ix_cell_classification_runs_detection_created
      ON cell_classification_runs(detection_run_id, created_at DESC, id DESC);
    CREATE INDEX ix_cell_classification_runs_model_created
      ON cell_classification_runs(
        production_model_id, created_at DESC, id DESC
      );

    CREATE TABLE cell_classification_inputs (
      id UUID PRIMARY KEY,
      classification_run_id UUID NOT NULL,
      detection_run_id UUID NOT NULL,
      cell_detection_id UUID NOT NULL,
      microscopy_image_id UUID NOT NULL,
      crop_id UUID,
      input_order INTEGER NOT NULL CHECK (input_order > 0),
      image_sequence_number INTEGER NOT NULL CHECK (image_sequence_number > 0),
      cell_index INTEGER NOT NULL CHECK (cell_index > 0),
      cell_code VARCHAR(40) NOT NULL
        CHECK (cell_code ~ '^CELL-[A-F0-9]{12}$'),
      detector_key VARCHAR(80) NOT NULL CHECK (btrim(detector_key) <> ''),
      detector_version VARCHAR(40) NOT NULL
        CHECK (btrim(detector_version) <> ''),
      detector_algorithm_version VARCHAR(80) NOT NULL
        CHECK (btrim(detector_algorithm_version) <> ''),
      crop_sha256 CHAR(64),
      crop_width_px INTEGER,
      crop_height_px INTEGER,
      detection_review_status_at_creation VARCHAR(30),
      eligible BOOLEAN NOT NULL,
      exclusion_reason VARCHAR(120),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CONSTRAINT fk_cell_classification_input_detection
        FOREIGN KEY(
          cell_detection_id, detection_run_id, microscopy_image_id
        )
        REFERENCES cell_detections(
          id, detection_run_id, microscopy_image_id
        )
        ON DELETE RESTRICT,
      CONSTRAINT fk_cell_classification_input_run_detection
        FOREIGN KEY(classification_run_id, detection_run_id)
        REFERENCES cell_classification_runs(id, detection_run_id)
        ON DELETE RESTRICT,
      CONSTRAINT fk_cell_classification_input_crop
        FOREIGN KEY(crop_id, cell_detection_id)
        REFERENCES cell_crops(id, cell_detection_id)
        ON DELETE RESTRICT,
      CONSTRAINT uq_cell_classification_inputs_detection
        UNIQUE(classification_run_id, cell_detection_id),
      CONSTRAINT uq_cell_classification_inputs_order
        UNIQUE(classification_run_id, input_order),
      CONSTRAINT uq_cell_classification_inputs_crop
        UNIQUE(classification_run_id, crop_id),
      CONSTRAINT uq_cell_classification_inputs_prediction_owner
        UNIQUE(
          id, classification_run_id, cell_detection_id, crop_id
        ),
      CONSTRAINT ck_cell_classification_input_review CHECK (
        detection_review_status_at_creation IS NULL
        OR detection_review_status_at_creation IN (
          'unreviewed','accepted','rejected','needs_attention'
        )
      ),
      CONSTRAINT ck_cell_classification_input_eligibility CHECK (
        (
          eligible
          AND crop_id IS NOT NULL
          AND exclusion_reason IS NULL
        )
        OR
        (
          NOT eligible
          AND exclusion_reason IS NOT NULL
          AND btrim(exclusion_reason) <> ''
        )
      ),
      CONSTRAINT ck_cell_classification_input_crop_metadata CHECK (
        (
          crop_id IS NULL
          AND NOT eligible
          AND crop_sha256 IS NULL
          AND crop_width_px IS NULL
          AND crop_height_px IS NULL
        )
        OR
        (
          crop_id IS NOT NULL
          AND crop_sha256 IS NOT NULL
          AND crop_sha256 ~ '^[0-9a-f]{64}$'
          AND crop_width_px IS NOT NULL
          AND crop_width_px > 0
          AND crop_height_px IS NOT NULL
          AND crop_height_px > 0
        )
      )
    );

    CREATE INDEX ix_cell_classification_inputs_run_eligible_order
      ON cell_classification_inputs(
        classification_run_id, eligible, input_order
      );
    CREATE INDEX ix_cell_classification_inputs_run_image_cell
      ON cell_classification_inputs(
        classification_run_id, image_sequence_number, cell_index, id
      );
    CREATE INDEX ix_cell_classification_inputs_detection
      ON cell_classification_inputs(cell_detection_id);
    CREATE INDEX ix_cell_classification_inputs_crop
      ON cell_classification_inputs(crop_id)
      WHERE crop_id IS NOT NULL;

    CREATE TABLE cell_predictions (
      id UUID PRIMARY KEY,
      classification_run_id UUID NOT NULL,
      classification_input_id UUID NOT NULL UNIQUE,
      cell_detection_id UUID NOT NULL,
      crop_id UUID NOT NULL,
      prediction_status VARCHAR(20) NOT NULL
        CHECK (prediction_status IN ('completed','failed')),
      raw_output JSONB NOT NULL
        CHECK (jsonb_typeof(raw_output) IN ('object','array')),
      probability_parasitized DOUBLE PRECISION,
      probability_uninfected DOUBLE PRECISION,
      predicted_label VARCHAR(20),
      predicted_class_index SMALLINT,
      positive_label VARCHAR(20) NOT NULL,
      positive_class_index SMALLINT NOT NULL,
      threshold_used DOUBLE PRECISION NOT NULL,
      threshold_source VARCHAR(120) NOT NULL
        CHECK (btrim(threshold_source) <> ''),
      decision_margin DOUBLE PRECISION,
      near_threshold BOOLEAN NOT NULL DEFAULT false,
      preprocessing_snapshot JSONB NOT NULL
        CHECK (jsonb_typeof(preprocessing_snapshot) = 'object'),
      inference_duration_ms DOUBLE PRECISION,
      error_code VARCHAR(80),
      error_message TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CONSTRAINT fk_cell_prediction_input_owner
        FOREIGN KEY(
          classification_input_id, classification_run_id,
          cell_detection_id, crop_id
        )
        REFERENCES cell_classification_inputs(
          id, classification_run_id, cell_detection_id, crop_id
        )
        ON DELETE RESTRICT,
      CONSTRAINT uq_cell_predictions_run_identity
        UNIQUE(id, classification_run_id),
      CONSTRAINT ck_cell_prediction_probability_parasitized CHECK (
        probability_parasitized IS NULL
        OR (
          probability_parasitized BETWEEN 0 AND 1
          AND probability_parasitized < 'Infinity'::DOUBLE PRECISION
        )
      ),
      CONSTRAINT ck_cell_prediction_probability_uninfected CHECK (
        probability_uninfected IS NULL
        OR (
          probability_uninfected BETWEEN 0 AND 1
          AND probability_uninfected < 'Infinity'::DOUBLE PRECISION
        )
      ),
      CONSTRAINT ck_cell_prediction_probability_sum CHECK (
        probability_parasitized IS NULL
        OR probability_uninfected IS NULL
        OR abs(
          probability_parasitized + probability_uninfected - 1.0
        ) <= 1e-9
      ),
      CONSTRAINT ck_cell_prediction_class_index CHECK (
        predicted_class_index IS NULL
        OR predicted_class_index IN (0,1)
      ),
      CONSTRAINT ck_cell_prediction_positive_class CHECK (
        positive_label = 'parasitized' AND positive_class_index = 1
      ),
      CONSTRAINT ck_cell_prediction_threshold CHECK (
        threshold_used BETWEEN 0 AND 1
        AND threshold_used < 'Infinity'::DOUBLE PRECISION
      ),
      CONSTRAINT ck_cell_prediction_margin CHECK (
        decision_margin IS NULL
        OR (
          decision_margin >= 0
          AND decision_margin < 'Infinity'::DOUBLE PRECISION
        )
      ),
      CONSTRAINT ck_cell_prediction_duration CHECK (
        inference_duration_ms IS NULL
        OR (
          inference_duration_ms >= 0
          AND inference_duration_ms < 'Infinity'::DOUBLE PRECISION
        )
      ),
      CONSTRAINT ck_cell_prediction_completed_payload CHECK (
        (
          prediction_status = 'completed'
          AND probability_parasitized IS NOT NULL
          AND probability_uninfected IS NOT NULL
          AND predicted_label IN ('parasitized','uninfected')
          AND predicted_class_index IN (0,1)
          AND decision_margin IS NOT NULL
          AND error_code IS NULL
          AND error_message IS NULL
        )
        OR
        (
          prediction_status = 'failed'
          AND probability_parasitized IS NULL
          AND probability_uninfected IS NULL
          AND predicted_label IS NULL
          AND predicted_class_index IS NULL
          AND decision_margin IS NULL
          AND NOT near_threshold
          AND error_code IS NOT NULL
          AND btrim(error_code) <> ''
        )
      ),
      CONSTRAINT ck_cell_prediction_label_index CHECK (
        prediction_status <> 'completed'
        OR (
          (
            predicted_class_index = 1
            AND predicted_label = 'parasitized'
            AND probability_parasitized >= threshold_used
          )
          OR
          (
            predicted_class_index = 0
            AND predicted_label = 'uninfected'
            AND probability_parasitized < threshold_used
          )
        )
      ),
      CONSTRAINT ck_cell_prediction_decision_margin CHECK (
        decision_margin IS NULL
        OR probability_parasitized IS NULL
        OR abs(
          decision_margin
          - abs(probability_parasitized - threshold_used)
        ) <= 1e-9
      )
    );

    CREATE INDEX ix_cell_predictions_run_status
      ON cell_predictions(
        classification_run_id, prediction_status, created_at, id
      );
    CREATE INDEX ix_cell_predictions_run_label
      ON cell_predictions(
        classification_run_id, predicted_label, created_at, id
      )
      WHERE prediction_status = 'completed';
    CREATE INDEX ix_cell_predictions_run_near_threshold
      ON cell_predictions(
        classification_run_id, near_threshold, created_at, id
      );
    CREATE INDEX ix_cell_predictions_detection
      ON cell_predictions(cell_detection_id);
    CREATE INDEX ix_cell_predictions_crop
      ON cell_predictions(crop_id);

    CREATE TABLE cell_explanations (
      id UUID PRIMARY KEY,
      cell_prediction_id UUID NOT NULL UNIQUE
        REFERENCES cell_predictions(id) ON DELETE RESTRICT,
      method VARCHAR(40) NOT NULL CHECK (method = 'gradcam'),
      method_version VARCHAR(80) NOT NULL
        CHECK (btrim(method_version) <> ''),
      status VARCHAR(30) NOT NULL
        CHECK (status IN (
          'pending','generated','failed','unsupported','not_requested'
        )),
      last_conv_layer VARCHAR(255),
      parameters_json JSONB NOT NULL
        CHECK (jsonb_typeof(parameters_json) = 'object'),
      heatmap_storage_key TEXT,
      heatmap_sha256 CHAR(64),
      heatmap_file_size_bytes BIGINT,
      overlay_storage_key TEXT,
      overlay_sha256 CHAR(64),
      overlay_file_size_bytes BIGINT,
      width_px INTEGER,
      height_px INTEGER,
      started_at TIMESTAMPTZ,
      completed_at TIMESTAMPTZ,
      error_code VARCHAR(80),
      error_message TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CONSTRAINT ck_cell_explanation_heatmap_key CHECK (
        heatmap_storage_key IS NULL
        OR heatmap_storage_key ~
          '^cell-explanations/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gradcam_heatmap[.]png$'
      ),
      CONSTRAINT ck_cell_explanation_overlay_key CHECK (
        overlay_storage_key IS NULL
        OR overlay_storage_key ~
          '^cell-explanations/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gradcam_overlay[.]png$'
      ),
      CONSTRAINT ck_cell_explanation_hashes CHECK (
        (heatmap_sha256 IS NULL OR heatmap_sha256 ~ '^[0-9a-f]{64}$')
        AND (overlay_sha256 IS NULL OR overlay_sha256 ~ '^[0-9a-f]{64}$')
      ),
      CONSTRAINT ck_cell_explanation_sizes CHECK (
        (
          heatmap_file_size_bytes IS NULL
          OR heatmap_file_size_bytes > 0
        )
        AND (
          overlay_file_size_bytes IS NULL
          OR overlay_file_size_bytes > 0
        )
      ),
      CONSTRAINT ck_cell_explanation_dimensions CHECK (
        (width_px IS NULL OR width_px > 0)
        AND (height_px IS NULL OR height_px > 0)
        AND (
          (width_px IS NULL AND height_px IS NULL)
          OR (width_px IS NOT NULL AND height_px IS NOT NULL)
        )
      ),
      CONSTRAINT ck_cell_explanation_state CHECK (
        (
          status = 'not_requested'
          AND started_at IS NULL
          AND completed_at IS NULL
          AND error_code IS NULL
          AND error_message IS NULL
          AND heatmap_storage_key IS NULL
          AND heatmap_sha256 IS NULL
          AND heatmap_file_size_bytes IS NULL
          AND overlay_storage_key IS NULL
          AND overlay_sha256 IS NULL
          AND overlay_file_size_bytes IS NULL
          AND width_px IS NULL
          AND height_px IS NULL
        )
        OR
        (
          status = 'pending'
          AND started_at IS NOT NULL
          AND completed_at IS NULL
          AND error_code IS NULL
          AND error_message IS NULL
          AND heatmap_storage_key IS NULL
          AND heatmap_sha256 IS NULL
          AND heatmap_file_size_bytes IS NULL
          AND overlay_storage_key IS NULL
          AND overlay_sha256 IS NULL
          AND overlay_file_size_bytes IS NULL
          AND width_px IS NULL
          AND height_px IS NULL
        )
        OR
        (
          status = 'generated'
          AND started_at IS NOT NULL
          AND completed_at IS NOT NULL
          AND last_conv_layer IS NOT NULL
          AND btrim(last_conv_layer) <> ''
          AND heatmap_storage_key IS NOT NULL
          AND heatmap_sha256 IS NOT NULL
          AND heatmap_file_size_bytes IS NOT NULL
          AND overlay_storage_key IS NOT NULL
          AND overlay_sha256 IS NOT NULL
          AND overlay_file_size_bytes IS NOT NULL
          AND width_px IS NOT NULL
          AND height_px IS NOT NULL
          AND error_code IS NULL
          AND error_message IS NULL
        )
        OR
        (
          status IN ('failed','unsupported')
          AND started_at IS NOT NULL
          AND completed_at IS NOT NULL
          AND error_code IS NOT NULL
          AND btrim(error_code) <> ''
          AND heatmap_storage_key IS NULL
          AND heatmap_sha256 IS NULL
          AND heatmap_file_size_bytes IS NULL
          AND overlay_storage_key IS NULL
          AND overlay_sha256 IS NULL
          AND overlay_file_size_bytes IS NULL
          AND width_px IS NULL
          AND height_px IS NULL
        )
      ),
      CONSTRAINT ck_cell_explanation_time_order CHECK (
        (started_at IS NULL OR started_at >= created_at)
        AND (completed_at IS NULL OR completed_at >= started_at)
      )
    );

    CREATE INDEX ix_cell_explanations_status_created
      ON cell_explanations(status, created_at DESC, id DESC);

    CREATE TABLE smear_analysis_summaries (
      id UUID PRIMARY KEY,
      classification_run_id UUID NOT NULL UNIQUE,
      analysis_run_id UUID NOT NULL,
      detection_run_id UUID NOT NULL,
      outcome VARCHAR(40) NOT NULL
        CHECK (outcome IN (
          'suspicious_cells_detected',
          'no_suspicious_cells_detected',
          'inconclusive'
        )),
      eligible_cell_count INTEGER NOT NULL CHECK (eligible_cell_count >= 0),
      classified_cell_count INTEGER NOT NULL
        CHECK (classified_cell_count >= 0),
      parasitized_candidate_count INTEGER NOT NULL
        CHECK (parasitized_candidate_count >= 0),
      uninfected_candidate_count INTEGER NOT NULL
        CHECK (uninfected_candidate_count >= 0),
      near_threshold_count INTEGER NOT NULL CHECK (near_threshold_count >= 0),
      failed_prediction_count INTEGER NOT NULL
        CHECK (failed_prediction_count >= 0),
      parasitized_candidate_fraction DOUBLE PRECISION,
      maximum_probability_parasitized DOUBLE PRECISION,
      mean_probability_parasitized DOUBLE PRECISION,
      median_probability_parasitized DOUBLE PRECISION,
      per_image_summary JSONB NOT NULL
        CHECK (jsonb_typeof(per_image_summary) = 'object'),
      aggregation_policy_snapshot JSONB NOT NULL
        CHECK (jsonb_typeof(aggregation_policy_snapshot) = 'object'),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CONSTRAINT fk_smear_summary_classification_lineage
        FOREIGN KEY(
          classification_run_id, analysis_run_id, detection_run_id
        )
        REFERENCES cell_classification_runs(
          id, analysis_run_id, detection_run_id
        )
        ON DELETE RESTRICT,
      CONSTRAINT ck_smear_summary_counts CHECK (
        classified_cell_count =
          parasitized_candidate_count + uninfected_candidate_count
        AND classified_cell_count + failed_prediction_count =
          eligible_cell_count
        AND near_threshold_count <= classified_cell_count
      ),
      CONSTRAINT ck_smear_summary_fraction CHECK (
        (
          classified_cell_count = 0
          AND parasitized_candidate_fraction IS NULL
        )
        OR
        (
          classified_cell_count > 0
          AND parasitized_candidate_fraction BETWEEN 0 AND 1
          AND abs(
            parasitized_candidate_fraction
            - (
              parasitized_candidate_count::DOUBLE PRECISION
              / classified_cell_count
            )
          ) <= 1e-9
        )
      ),
      CONSTRAINT ck_smear_summary_probabilities CHECK (
        (
          classified_cell_count = 0
          AND maximum_probability_parasitized IS NULL
          AND mean_probability_parasitized IS NULL
          AND median_probability_parasitized IS NULL
        )
        OR
        (
          classified_cell_count > 0
          AND maximum_probability_parasitized BETWEEN 0 AND 1
          AND mean_probability_parasitized BETWEEN 0 AND 1
          AND median_probability_parasitized BETWEEN 0 AND 1
        )
      )
    );

    CREATE INDEX ix_smear_analysis_summaries_analysis_created
      ON smear_analysis_summaries(
        analysis_run_id, created_at DESC, id DESC
      );
    CREATE INDEX ix_smear_analysis_summaries_detection_created
      ON smear_analysis_summaries(
        detection_run_id, created_at DESC, id DESC
      );
    CREATE INDEX ix_smear_analysis_summaries_outcome_created
      ON smear_analysis_summaries(outcome, created_at DESC, id DESC);

    CREATE TABLE cell_classification_events (
      id UUID PRIMARY KEY,
      classification_run_id UUID NOT NULL
        REFERENCES cell_classification_runs(id) ON DELETE RESTRICT,
      cell_detection_id UUID
        REFERENCES cell_detections(id) ON DELETE RESTRICT,
      cell_prediction_id UUID,
      event_type VARCHAR(120) NOT NULL CHECK (btrim(event_type) <> ''),
      status VARCHAR(40) NOT NULL CHECK (btrim(status) <> ''),
      message_code VARCHAR(80),
      message TEXT,
      progress_current INTEGER
        CHECK (progress_current IS NULL OR progress_current >= 0),
      progress_total INTEGER
        CHECK (progress_total IS NULL OR progress_total >= 0),
      metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(metadata_json) = 'object'),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CONSTRAINT fk_cell_classification_event_prediction
        FOREIGN KEY(cell_prediction_id, classification_run_id)
        REFERENCES cell_predictions(id, classification_run_id)
        ON DELETE RESTRICT,
      CONSTRAINT ck_cell_classification_event_progress CHECK (
        progress_current IS NULL
        OR progress_total IS NULL
        OR progress_current <= progress_total
      )
    );

    CREATE INDEX ix_cell_classification_events_run_created
      ON cell_classification_events(
        classification_run_id, created_at, id
      );
    CREATE INDEX ix_cell_classification_events_run_detection
      ON cell_classification_events(
        classification_run_id, cell_detection_id, created_at, id
      );
    CREATE INDEX ix_cell_classification_events_run_prediction
      ON cell_classification_events(
        classification_run_id, cell_prediction_id, created_at, id
      );

    CREATE TABLE cell_classification_reviews (
      id UUID PRIMARY KEY,
      cell_prediction_id UUID NOT NULL
        REFERENCES cell_predictions(id) ON DELETE RESTRICT,
      decision VARCHAR(30) NOT NULL
        CHECK (decision IN (
          'confirmed','corrected','needs_attention','comment_only'
        )),
      reviewed_label VARCHAR(20)
        CHECK (
          reviewed_label IS NULL
          OR reviewed_label IN ('parasitized','uninfected')
        ),
      comment TEXT,
      actor_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CONSTRAINT ck_cell_classification_review_payload CHECK (
        (
          decision = 'confirmed'
          AND (
            comment IS NULL
            OR btrim(comment) <> ''
          )
        )
        OR
        (
          decision = 'corrected'
          AND reviewed_label IS NOT NULL
          AND comment IS NOT NULL
          AND btrim(comment) <> ''
        )
        OR
        (
          decision IN ('needs_attention','comment_only')
          AND reviewed_label IS NULL
          AND comment IS NOT NULL
          AND btrim(comment) <> ''
        )
      )
    );

    CREATE INDEX ix_cell_classification_reviews_prediction_created
      ON cell_classification_reviews(
        cell_prediction_id, created_at, id
      );
    CREATE INDEX ix_cell_classification_reviews_actor_created
      ON cell_classification_reviews(
        actor_user_id, created_at DESC, id DESC
      );

    CREATE FUNCTION validate_cell_classification_review()
    RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
      automatic_status VARCHAR(20);
      automatic_label VARCHAR(20);
    BEGIN
      SELECT prediction_status,predicted_label
      INTO automatic_status,automatic_label
      FROM cell_predictions
      WHERE id=NEW.cell_prediction_id
      FOR SHARE;
      IF automatic_status IS NULL THEN
        RAISE EXCEPTION 'cell prediction does not exist'
          USING ERRCODE = '23503';
      END IF;
      IF automatic_status <> 'completed' THEN
        RAISE EXCEPTION
          'failed cell predictions cannot be reviewed'
          USING ERRCODE = '23514';
      END IF;
      IF NEW.decision = 'confirmed'
        AND NEW.reviewed_label IS NOT NULL
        AND NEW.reviewed_label IS DISTINCT FROM automatic_label
      THEN
        RAISE EXCEPTION
          'confirmed label must match the immutable automatic prediction'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $$;

    CREATE TRIGGER trg_cell_classification_reviews_validate
      BEFORE INSERT ON cell_classification_reviews
      FOR EACH ROW EXECUTE FUNCTION validate_cell_classification_review();

    CREATE FUNCTION validate_cell_classification_run_snapshot()
    RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
      snapshot JSONB := NEW.model_snapshot;
      published_threshold DOUBLE PRECISION;
      published_review_margin DOUBLE PRECISION;
    BEGIN
      IF jsonb_typeof(snapshot) IS DISTINCT FROM 'object'
        OR snapshot->>'schema_version' IS DISTINCT FROM '1'
        OR snapshot->>'production_model_id'
          IS DISTINCT FROM NEW.production_model_id::text
        OR snapshot->>'stage2_publication_id'
          IS DISTINCT FROM NEW.stage2_publication_id::text
        OR snapshot->>'model_registry_id'
          IS DISTINCT FROM NEW.model_registry_id::text
        OR snapshot->>'model_name' IS DISTINCT FROM NEW.model_name
        OR snapshot->>'model_version' IS DISTINCT FROM NEW.model_version
        OR snapshot->>'positive_label' IS DISTINCT FROM 'parasitized'
        OR snapshot->>'positive_class_index' IS DISTINCT FROM '1'
        OR snapshot->>'production_status' IS DISTINCT FROM 'active'
        OR snapshot->>'checkpoint_sha256' IS NULL
        OR snapshot->>'checkpoint_sha256' !~ '^[0-9a-f]{64}$'
        OR COALESCE(snapshot->>'checkpoint_size_bytes','')
          !~ '^[1-9][0-9]*$'
        OR snapshot->>'loader_version' IS NULL
        OR btrim(snapshot->>'loader_version') = ''
        OR snapshot->>'inference_version' IS NULL
        OR btrim(snapshot->>'inference_version') = ''
        OR snapshot->>'threshold_source' IS NULL
        OR btrim(snapshot->>'threshold_source') = ''
        OR jsonb_typeof(snapshot->'preprocessing') IS DISTINCT FROM 'object'
        OR jsonb_typeof(snapshot->'input_signature') IS DISTINCT FROM 'object'
        OR jsonb_typeof(snapshot->'output_signature') IS DISTINCT FROM 'object'
        OR jsonb_typeof(snapshot->'calibration_metadata')
          IS DISTINCT FROM 'object'
        OR jsonb_typeof(snapshot->'stage2_default') IS DISTINCT FROM 'object'
        OR jsonb_typeof(snapshot->'explainability_policy')
          IS DISTINCT FROM 'object'
        OR jsonb_typeof(snapshot->'label_mapping') IS DISTINCT FROM 'object'
        OR NOT (
          snapshot->'label_mapping' @>
            '{
              "0":"uninfected",
              "1":"parasitized",
              "positive_class": 1,
              "positive_label":"parasitized"
            }'::jsonb
        )
        OR snapshot#>>'{stage2_default,environment}' IS DISTINCT FROM 'stage2'
        OR snapshot#>>'{stage2_default,alias}' IS DISTINCT FROM 'default'
        OR snapshot#>>'{stage2_default,deployment_id}'
          IS DISTINCT FROM NEW.production_model_id::text
        OR snapshot#>>'{explainability_policy,version}'
          IS DISTINCT FROM 'cell-gradcam-manual-v1'
        OR snapshot#>>'{explainability_policy,method}'
          IS DISTINCT FROM 'gradcam'
        OR snapshot#>>'{explainability_policy,scope}'
          IS DISTINCT FROM 'single_cell_on_demand'
        OR snapshot#>>'{explainability_policy,automatic_generation}'
          IS DISTINCT FROM 'false'
        OR snapshot#>>'{explainability_policy,manual_retry_required}'
          IS DISTINCT FROM 'true'
        OR snapshot#>>'{explainability_policy,bulk_generation}'
          IS DISTINCT FROM 'false'
        OR COALESCE(snapshot->>'source_training_run_id','')
          !~ '^[0-9a-f-]{36}$'
        OR COALESCE(snapshot->>'source_evaluation_run_id','')
          !~ '^[0-9a-f-]{36}$'
        OR COALESCE(snapshot->>'checkpoint_artifact_id','')
          !~ '^[0-9a-f-]{36}$'
        OR COALESCE(snapshot->>'batch_size','') !~ '^[1-9][0-9]*$'
        OR COALESCE(snapshot->>'input_width','') !~ '^[1-9][0-9]*$'
        OR COALESCE(snapshot->>'input_height','') !~ '^[1-9][0-9]*$'
        OR COALESCE(snapshot->>'input_channels','') !~ '^[1-9][0-9]*$'
      THEN
        RAISE EXCEPTION
          'model snapshot identity or required contract is invalid'
          USING ERRCODE = '23514';
      END IF;

      IF jsonb_typeof(snapshot->'threshold') IS DISTINCT FROM 'number'
        OR jsonb_typeof(snapshot->'review_margin') IS DISTINCT FROM 'number'
      THEN
        RAISE EXCEPTION
          'model snapshot numeric policy is invalid'
          USING ERRCODE = '23514';
      END IF;
      published_threshold := (snapshot->>'threshold')::DOUBLE PRECISION;
      published_review_margin :=
        (snapshot->>'review_margin')::DOUBLE PRECISION;
      IF published_threshold < 0 OR published_threshold > 1
        OR published_review_margin < 0 OR published_review_margin > 1
      THEN
        RAISE EXCEPTION
          'model snapshot numeric policy is outside allowed bounds'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $$;

    CREATE TRIGGER trg_cell_classification_runs_snapshot
      BEFORE INSERT ON cell_classification_runs
      FOR EACH ROW
      EXECUTE FUNCTION validate_cell_classification_run_snapshot();

    CREATE FUNCTION validate_cell_classification_input_snapshot()
    RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
      source_cell_index INTEGER;
      source_cell_code VARCHAR(40);
      source_image_sequence INTEGER;
      source_detector_key VARCHAR(80);
      source_detector_version VARCHAR(40);
      source_algorithm_version VARCHAR(80);
      source_crop_id UUID;
      source_crop_sha256 CHAR(64);
      source_crop_width INTEGER;
      source_crop_height INTEGER;
    BEGIN
      SELECT
        detection.cell_index,
        detection.cell_code,
        image.sequence_number,
        run.detector_key,
        run.detector_version,
        run.algorithm_version,
        crop.id,
        crop.sha256,
        crop.width_px,
        crop.height_px
      INTO
        source_cell_index,
        source_cell_code,
        source_image_sequence,
        source_detector_key,
        source_detector_version,
        source_algorithm_version,
        source_crop_id,
        source_crop_sha256,
        source_crop_width,
        source_crop_height
      FROM cell_detections detection
      JOIN cell_detection_runs run
        ON run.id=detection.detection_run_id
      JOIN microscopy_analysis_run_images image
        ON image.id=detection.analysis_run_image_id
      LEFT JOIN cell_crops crop
        ON crop.cell_detection_id=detection.id
      WHERE detection.id=NEW.cell_detection_id
        AND detection.detection_run_id=NEW.detection_run_id
        AND detection.microscopy_image_id=NEW.microscopy_image_id
      FOR SHARE OF detection,run,image;

      IF source_cell_index IS NULL
        OR NEW.cell_index IS DISTINCT FROM source_cell_index
        OR NEW.cell_code IS DISTINCT FROM source_cell_code
        OR NEW.image_sequence_number IS DISTINCT FROM source_image_sequence
        OR NEW.detector_key IS DISTINCT FROM source_detector_key
        OR NEW.detector_version IS DISTINCT FROM source_detector_version
        OR NEW.detector_algorithm_version
          IS DISTINCT FROM source_algorithm_version
        OR NEW.crop_id IS DISTINCT FROM source_crop_id
        OR NEW.crop_sha256 IS DISTINCT FROM source_crop_sha256
        OR NEW.crop_width_px IS DISTINCT FROM source_crop_width
        OR NEW.crop_height_px IS DISTINCT FROM source_crop_height
      THEN
        RAISE EXCEPTION
          'classification input does not match immutable detection/crop metadata'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $$;

    CREATE TRIGGER trg_cell_classification_inputs_snapshot
      BEFORE INSERT ON cell_classification_inputs
      FOR EACH ROW
      EXECUTE FUNCTION validate_cell_classification_input_snapshot();

    CREATE FUNCTION reject_cell_classification_row_mutation()
    RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      RAISE EXCEPTION
        'cell classification inputs, predictions, summaries, events and reviews are append-only'
        USING ERRCODE = '55000';
    END;
    $$;

    CREATE FUNCTION validate_cell_classification_insert_state()
    RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
      run_status VARCHAR(30);
      declared_count INTEGER;
      existing_count INTEGER;
    BEGIN
      IF TG_TABLE_NAME = 'cell_classification_inputs' THEN
        SELECT status,input_count
        INTO run_status,declared_count
        FROM cell_classification_runs
        WHERE id=NEW.classification_run_id
        FOR SHARE;
        IF run_status IS DISTINCT FROM 'created' THEN
          RAISE EXCEPTION
            'cell classification inputs require a created run'
            USING ERRCODE = '55000';
        END IF;
        SELECT count(*)
        INTO existing_count
        FROM cell_classification_inputs
        WHERE classification_run_id=NEW.classification_run_id;
      ELSIF TG_TABLE_NAME = 'cell_predictions' THEN
        SELECT status,eligible_count
        INTO run_status,declared_count
        FROM cell_classification_runs
        WHERE id=NEW.classification_run_id
        FOR SHARE;
        IF run_status IS DISTINCT FROM 'processing' THEN
          RAISE EXCEPTION
            'cell predictions require a processing run'
            USING ERRCODE = '55000';
        END IF;
        SELECT count(*)
        INTO existing_count
        FROM cell_predictions
        WHERE classification_run_id=NEW.classification_run_id;
      ELSIF TG_TABLE_NAME = 'smear_analysis_summaries' THEN
        SELECT status,1
        INTO run_status,declared_count
        FROM cell_classification_runs
        WHERE id=NEW.classification_run_id
        FOR SHARE;
        IF run_status IS DISTINCT FROM 'processing' THEN
          RAISE EXCEPTION
            'smear analysis summary requires a processing run'
            USING ERRCODE = '55000';
        END IF;
        SELECT count(*)
        INTO existing_count
        FROM smear_analysis_summaries
        WHERE classification_run_id=NEW.classification_run_id;
      ELSE
        RAISE EXCEPTION 'unsupported guarded classification table'
          USING ERRCODE = '55000';
      END IF;

      IF run_status IS NULL THEN
        RAISE EXCEPTION 'classification run does not exist'
          USING ERRCODE = '23503';
      END IF;
      IF existing_count >= declared_count THEN
        RAISE EXCEPTION
          'classification child rows exceed the frozen run count'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $$;

    CREATE TRIGGER trg_cell_classification_inputs_insert_state
      BEFORE INSERT ON cell_classification_inputs
      FOR EACH ROW
      EXECUTE FUNCTION validate_cell_classification_insert_state();
    CREATE TRIGGER trg_cell_predictions_insert_state
      BEFORE INSERT ON cell_predictions
      FOR EACH ROW
      EXECUTE FUNCTION validate_cell_classification_insert_state();
    CREATE TRIGGER trg_smear_analysis_summaries_insert_state
      BEFORE INSERT ON smear_analysis_summaries
      FOR EACH ROW
      EXECUTE FUNCTION validate_cell_classification_insert_state();

    CREATE FUNCTION validate_smear_analysis_summary()
    RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
      source_analysis_run_id UUID;
      source_detection_run_id UUID;
      source_eligible_count INTEGER;
      actual_classified_count INTEGER;
      actual_parasitized_count INTEGER;
      actual_uninfected_count INTEGER;
      actual_near_count INTEGER;
      actual_failed_count INTEGER;
      actual_maximum DOUBLE PRECISION;
      actual_mean DOUBLE PRECISION;
      actual_median DOUBLE PRECISION;
      expected_outcome VARCHAR(40);
      actual_per_image JSONB;
      expected_policy CONSTANT JSONB := '{
        "version":"cell-candidate-aggregation-v1",
        "scope":"candidate_cells",
        "suspicious_when_any_parasitized": true,
        "near_threshold_makes_negative_inconclusive": true,
        "partial_failure_makes_negative_inconclusive": true,
        "terminology":"experimental_screening_not_diagnosis"
      }'::jsonb;
    BEGIN
      SELECT analysis_run_id,detection_run_id,eligible_count
      INTO
        source_analysis_run_id,
        source_detection_run_id,
        source_eligible_count
      FROM cell_classification_runs
      WHERE id=NEW.classification_run_id
      FOR SHARE;

      SELECT
        count(*) FILTER (WHERE prediction_status='completed'),
        count(*) FILTER (
          WHERE prediction_status='completed'
            AND predicted_label='parasitized'
        ),
        count(*) FILTER (
          WHERE prediction_status='completed'
            AND predicted_label='uninfected'
        ),
        count(*) FILTER (
          WHERE prediction_status='completed' AND near_threshold
        ),
        count(*) FILTER (WHERE prediction_status='failed'),
        max(probability_parasitized) FILTER (
          WHERE prediction_status='completed'
        ),
        avg(probability_parasitized) FILTER (
          WHERE prediction_status='completed'
        ),
        percentile_cont(0.5) WITHIN GROUP (
          ORDER BY probability_parasitized
        ) FILTER (WHERE prediction_status='completed')
      INTO
        actual_classified_count,
        actual_parasitized_count,
        actual_uninfected_count,
        actual_near_count,
        actual_failed_count,
        actual_maximum,
        actual_mean,
        actual_median
      FROM cell_predictions
      WHERE classification_run_id=NEW.classification_run_id;

      SELECT jsonb_build_object(
        'images',
        COALESCE(
          jsonb_agg(
            jsonb_build_object(
              'microscopy_image_id',per_image.microscopy_image_id::text,
              'image_sequence_number',per_image.image_sequence_number,
              'eligible_cell_count',per_image.eligible_cell_count,
              'classified_cell_count',per_image.classified_cell_count,
              'parasitized_candidate_count',
                per_image.parasitized_candidate_count,
              'uninfected_candidate_count',
                per_image.uninfected_candidate_count,
              'near_threshold_count',per_image.near_threshold_count,
              'failed_prediction_count',per_image.failed_prediction_count
            )
            ORDER BY
              per_image.image_sequence_number,
              per_image.microscopy_image_id
          ),
          '[]'::jsonb
        )
      )
      INTO actual_per_image
      FROM (
        SELECT
          input.microscopy_image_id,
          min(input.image_sequence_number) image_sequence_number,
          count(*)::INTEGER eligible_cell_count,
          count(prediction.id) FILTER (
            WHERE prediction.prediction_status='completed'
          )::INTEGER classified_cell_count,
          count(prediction.id) FILTER (
            WHERE prediction.prediction_status='completed'
              AND prediction.predicted_label='parasitized'
          )::INTEGER parasitized_candidate_count,
          count(prediction.id) FILTER (
            WHERE prediction.prediction_status='completed'
              AND prediction.predicted_label='uninfected'
          )::INTEGER uninfected_candidate_count,
          count(prediction.id) FILTER (
            WHERE prediction.prediction_status='completed'
              AND prediction.near_threshold
          )::INTEGER near_threshold_count,
          count(prediction.id) FILTER (
            WHERE prediction.prediction_status='failed'
          )::INTEGER failed_prediction_count
        FROM cell_classification_inputs input
        LEFT JOIN cell_predictions prediction
          ON prediction.classification_input_id=input.id
        WHERE input.classification_run_id=NEW.classification_run_id
          AND input.eligible
        GROUP BY input.microscopy_image_id
      ) per_image;

      IF actual_parasitized_count > 0 THEN
        expected_outcome := 'suspicious_cells_detected';
      ELSIF source_eligible_count > 0
        AND actual_classified_count=source_eligible_count
        AND actual_failed_count=0
        AND actual_near_count=0
      THEN
        expected_outcome := 'no_suspicious_cells_detected';
      ELSE
        expected_outcome := 'inconclusive';
      END IF;

      IF NEW.analysis_run_id IS DISTINCT FROM source_analysis_run_id
        OR NEW.detection_run_id IS DISTINCT FROM source_detection_run_id
        OR NEW.eligible_cell_count IS DISTINCT FROM source_eligible_count
        OR NEW.classified_cell_count IS DISTINCT FROM actual_classified_count
        OR NEW.parasitized_candidate_count
          IS DISTINCT FROM actual_parasitized_count
        OR NEW.uninfected_candidate_count
          IS DISTINCT FROM actual_uninfected_count
        OR NEW.near_threshold_count IS DISTINCT FROM actual_near_count
        OR NEW.failed_prediction_count IS DISTINCT FROM actual_failed_count
        OR NEW.outcome IS DISTINCT FROM expected_outcome
        OR NEW.per_image_summary IS DISTINCT FROM actual_per_image
        OR NEW.aggregation_policy_snapshot IS DISTINCT FROM expected_policy
        OR (
          actual_classified_count > 0
          AND (
            abs(NEW.maximum_probability_parasitized - actual_maximum) > 1e-12
            OR abs(NEW.mean_probability_parasitized - actual_mean) > 1e-12
            OR abs(NEW.median_probability_parasitized - actual_median) > 1e-12
          )
        )
      THEN
        RAISE EXCEPTION
          'smear analysis summary does not match immutable predictions'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $$;

    CREATE TRIGGER trg_smear_analysis_summaries_validate
      BEFORE INSERT ON smear_analysis_summaries
      FOR EACH ROW EXECUTE FUNCTION validate_smear_analysis_summary();

    CREATE TRIGGER trg_cell_classification_inputs_append_only
      BEFORE UPDATE OR DELETE ON cell_classification_inputs
      FOR EACH ROW EXECUTE FUNCTION reject_cell_classification_row_mutation();
    CREATE TRIGGER trg_cell_predictions_append_only
      BEFORE UPDATE OR DELETE ON cell_predictions
      FOR EACH ROW EXECUTE FUNCTION reject_cell_classification_row_mutation();
    CREATE TRIGGER trg_smear_analysis_summaries_append_only
      BEFORE UPDATE OR DELETE ON smear_analysis_summaries
      FOR EACH ROW EXECUTE FUNCTION reject_cell_classification_row_mutation();
    CREATE TRIGGER trg_cell_classification_events_append_only
      BEFORE UPDATE OR DELETE ON cell_classification_events
      FOR EACH ROW EXECUTE FUNCTION reject_cell_classification_row_mutation();
    CREATE TRIGGER trg_cell_classification_reviews_append_only
      BEFORE UPDATE OR DELETE ON cell_classification_reviews
      FOR EACH ROW EXECUTE FUNCTION reject_cell_classification_row_mutation();

    CREATE FUNCTION protect_cell_classification_run()
    RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
      actual_input_count INTEGER;
      actual_eligible_count INTEGER;
      actual_excluded_count INTEGER;
      actual_processed_count INTEGER;
      actual_parasitized_count INTEGER;
      actual_uninfected_count INTEGER;
      actual_near_threshold_count INTEGER;
      actual_failed_count INTEGER;
      actual_summary_count INTEGER;
    BEGIN
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'cell_classification_runs cannot be deleted'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status IN ('completed','completed_with_warnings','failed') THEN
        RAISE EXCEPTION 'terminal cell_classification_runs are immutable'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status = 'created' AND NEW.status NOT IN ('processing','failed') THEN
        RAISE EXCEPTION 'invalid cell classification run transition'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status = 'created' AND NEW.status = 'processing' THEN
        SELECT
          count(*),
          count(*) FILTER (WHERE eligible),
          count(*) FILTER (WHERE NOT eligible)
        INTO
          actual_input_count,
          actual_eligible_count,
          actual_excluded_count
        FROM cell_classification_inputs
        WHERE classification_run_id=OLD.id;
        IF actual_input_count <> OLD.input_count
          OR actual_eligible_count <> OLD.eligible_count
          OR actual_excluded_count <> OLD.excluded_count
        THEN
          RAISE EXCEPTION
            'frozen classification inputs do not match run counters'
            USING ERRCODE = '23514';
        END IF;
      END IF;
      IF OLD.status = 'processing'
        AND NEW.status NOT IN (
          'processing','completed','completed_with_warnings','failed'
        )
      THEN
        RAISE EXCEPTION 'invalid cell classification run transition'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status IN ('created','processing') THEN
        SELECT
          count(*),
          count(*) FILTER (
            WHERE prediction_status='completed'
              AND predicted_label='parasitized'
          ),
          count(*) FILTER (
            WHERE prediction_status='completed'
              AND predicted_label='uninfected'
          ),
          count(*) FILTER (
            WHERE prediction_status='completed' AND near_threshold
          ),
          count(*) FILTER (WHERE prediction_status='failed')
        INTO
          actual_processed_count,
          actual_parasitized_count,
          actual_uninfected_count,
          actual_near_threshold_count,
          actual_failed_count
        FROM cell_predictions
        WHERE classification_run_id=OLD.id;
        IF actual_processed_count <> NEW.processed_count
          OR actual_parasitized_count <> NEW.parasitized_count
          OR actual_uninfected_count <> NEW.uninfected_count
          OR actual_near_threshold_count <> NEW.near_threshold_count
          OR actual_failed_count <> NEW.failed_count
        THEN
          RAISE EXCEPTION
            'persisted predictions do not match run counters'
            USING ERRCODE = '23514';
        END IF;
      END IF;
      IF NEW.status IN ('completed','completed_with_warnings') THEN
        SELECT count(*)
        INTO actual_summary_count
        FROM smear_analysis_summaries
        WHERE classification_run_id=OLD.id;
        IF actual_summary_count <> 1 THEN
          RAISE EXCEPTION
            'completed classification run requires one immutable summary'
            USING ERRCODE = '23514';
        END IF;
      END IF;
      IF NEW.updated_at < OLD.updated_at THEN
        RAISE EXCEPTION 'classification run time cannot move backwards'
          USING ERRCODE = '23514';
      END IF;
      IF OLD.started_at IS NOT NULL
        AND NEW.started_at IS DISTINCT FROM OLD.started_at
      THEN
        RAISE EXCEPTION 'classification run started_at is immutable once set'
          USING ERRCODE = '55000';
      END IF;
      IF NEW.analysis_run_id IS DISTINCT FROM OLD.analysis_run_id
        OR NEW.detection_run_id IS DISTINCT FROM OLD.detection_run_id
        OR NEW.classification_run_code
          IS DISTINCT FROM OLD.classification_run_code
        OR NEW.production_model_id IS DISTINCT FROM OLD.production_model_id
        OR NEW.stage2_publication_id
          IS DISTINCT FROM OLD.stage2_publication_id
        OR NEW.model_registry_id IS DISTINCT FROM OLD.model_registry_id
        OR NEW.model_name IS DISTINCT FROM OLD.model_name
        OR NEW.model_version IS DISTINCT FROM OLD.model_version
        OR NEW.model_snapshot IS DISTINCT FROM OLD.model_snapshot
        OR NEW.input_manifest_sha256
          IS DISTINCT FROM OLD.input_manifest_sha256
        OR NEW.input_count IS DISTINCT FROM OLD.input_count
        OR NEW.eligible_count IS DISTINCT FROM OLD.eligible_count
        OR NEW.excluded_count IS DISTINCT FROM OLD.excluded_count
        OR NEW.requested_by IS DISTINCT FROM OLD.requested_by
        OR NEW.retry_of_run_id IS DISTINCT FROM OLD.retry_of_run_id
        OR NEW.created_at IS DISTINCT FROM OLD.created_at
      THEN
        RAISE EXCEPTION
          'cell_classification_runs identity, model and inputs are immutable'
          USING ERRCODE = '55000';
      END IF;
      RETURN NEW;
    END;
    $$;

    CREATE TRIGGER trg_cell_classification_runs_protected
      BEFORE UPDATE OR DELETE ON cell_classification_runs
      FOR EACH ROW EXECUTE FUNCTION protect_cell_classification_run();

    CREATE FUNCTION validate_cell_prediction_input()
    RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
      input_eligible BOOLEAN;
      run_snapshot JSONB;
      snapshot_threshold DOUBLE PRECISION;
      snapshot_review_margin DOUBLE PRECISION;
    BEGIN
      SELECT input.eligible,run.model_snapshot
      INTO input_eligible,run_snapshot
      FROM cell_classification_inputs input
      JOIN cell_classification_runs run
        ON run.id=input.classification_run_id
      WHERE input.id = NEW.classification_input_id
        AND input.classification_run_id = NEW.classification_run_id
        AND input.cell_detection_id = NEW.cell_detection_id
        AND input.crop_id = NEW.crop_id
      FOR SHARE OF input,run;
      IF input_eligible IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION
          'cell prediction requires an eligible frozen input'
          USING ERRCODE = '23514';
      END IF;
      snapshot_threshold :=
        (run_snapshot->>'threshold')::DOUBLE PRECISION;
      snapshot_review_margin :=
        (run_snapshot->>'review_margin')::DOUBLE PRECISION;
      IF abs(NEW.threshold_used - snapshot_threshold) > 1e-12
        OR NEW.threshold_source
          IS DISTINCT FROM run_snapshot->>'threshold_source'
        OR NEW.preprocessing_snapshot
          IS DISTINCT FROM run_snapshot->'preprocessing'
        OR NEW.positive_label
          IS DISTINCT FROM run_snapshot->>'positive_label'
        OR NEW.positive_class_index::text
          IS DISTINCT FROM run_snapshot->>'positive_class_index'
        OR (
          NEW.prediction_status='completed'
          AND NEW.near_threshold IS DISTINCT FROM
            (NEW.decision_margin <= snapshot_review_margin)
        )
      THEN
        RAISE EXCEPTION
          'cell prediction does not match the frozen model policy'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $$;

    CREATE TRIGGER trg_cell_predictions_validate_input
      BEFORE INSERT ON cell_predictions
      FOR EACH ROW EXECUTE FUNCTION validate_cell_prediction_input();

    CREATE FUNCTION protect_cell_explanation()
    RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'cell_explanations cannot be deleted'
          USING ERRCODE = '55000';
      END IF;
      IF NEW.cell_prediction_id IS DISTINCT FROM OLD.cell_prediction_id
        OR NEW.method IS DISTINCT FROM OLD.method
        OR NEW.method_version IS DISTINCT FROM OLD.method_version
        OR NEW.parameters_json IS DISTINCT FROM OLD.parameters_json
        OR NEW.created_at IS DISTINCT FROM OLD.created_at
      THEN
        RAISE EXCEPTION 'cell explanation identity and parameters are immutable'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status IN ('generated','unsupported') THEN
        RAISE EXCEPTION 'terminal cell explanations are immutable'
          USING ERRCODE = '55000';
      END IF;
      IF NOT (
        (OLD.status = 'not_requested' AND NEW.status = 'pending')
        OR
        (
          OLD.status = 'pending'
          AND NEW.status IN ('generated','failed','unsupported')
        )
        OR
        (OLD.status = 'failed' AND NEW.status = 'pending')
      ) THEN
        RAISE EXCEPTION 'invalid cell explanation transition'
          USING ERRCODE = '55000';
      END IF;
      RETURN NEW;
    END;
    $$;

    CREATE TRIGGER trg_cell_explanations_protected
      BEFORE UPDATE OR DELETE ON cell_explanations
      FOR EACH ROW EXECUTE FUNCTION protect_cell_explanation();

    CREATE FUNCTION validate_cell_explanation_contract()
    RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
      prediction_status VARCHAR(20);
      prediction_class SMALLINT;
      prediction_preprocessing JSONB;
      source_analysis_run_id UUID;
      source_classification_run_id UUID;
      source_cell_detection_id UUID;
      source_input_width INTEGER;
      source_input_height INTEGER;
      expected_heatmap_key TEXT;
      expected_overlay_key TEXT;
    BEGIN
      SELECT
        prediction.prediction_status,
        prediction.predicted_class_index,
        prediction.preprocessing_snapshot,
        run.analysis_run_id,
        prediction.classification_run_id,
        prediction.cell_detection_id,
        (run.model_snapshot->>'input_width')::INTEGER,
        (run.model_snapshot->>'input_height')::INTEGER
      INTO
        prediction_status,
        prediction_class,
        prediction_preprocessing,
        source_analysis_run_id,
        source_classification_run_id,
        source_cell_detection_id,
        source_input_width,
        source_input_height
      FROM cell_predictions prediction
      JOIN cell_classification_runs run
        ON run.id=prediction.classification_run_id
      WHERE prediction.id=NEW.cell_prediction_id
      FOR SHARE OF prediction,run;

      IF prediction_status IS DISTINCT FROM 'completed'
        OR NEW.parameters_json->>'method' IS DISTINCT FROM 'gradcam'
        OR NEW.parameters_json->>'method_version'
          IS DISTINCT FROM NEW.method_version
        OR NEW.parameters_json->>'target_class_index'
          IS DISTINCT FROM prediction_class::text
        OR NEW.parameters_json->>'positive_class_index'
          IS DISTINCT FROM '1'
        OR NEW.parameters_json->'preprocessing'
          IS DISTINCT FROM prediction_preprocessing
      THEN
        RAISE EXCEPTION
          'cell explanation does not match the immutable prediction contract'
          USING ERRCODE = '23514';
      END IF;

      IF NEW.status='generated' THEN
        expected_heatmap_key := format(
          'cell-explanations/%s/%s/%s/gradcam_heatmap.png',
          source_analysis_run_id,
          source_classification_run_id,
          source_cell_detection_id
        );
        expected_overlay_key := format(
          'cell-explanations/%s/%s/%s/gradcam_overlay.png',
          source_analysis_run_id,
          source_classification_run_id,
          source_cell_detection_id
        );
        IF NEW.heatmap_storage_key IS DISTINCT FROM expected_heatmap_key
          OR NEW.overlay_storage_key IS DISTINCT FROM expected_overlay_key
          OR NEW.width_px IS DISTINCT FROM source_input_width
          OR NEW.height_px IS DISTINCT FROM source_input_height
        THEN
          RAISE EXCEPTION
            'generated explanation artifact lineage is inconsistent'
            USING ERRCODE = '23514';
        END IF;
      END IF;
      RETURN NEW;
    END;
    $$;

    CREATE TRIGGER trg_cell_explanations_contract
      BEFORE INSERT OR UPDATE ON cell_explanations
      FOR EACH ROW EXECUTE FUNCTION validate_cell_explanation_contract();
    """)


def downgrade():
    op.execute("""
    DROP TABLE cell_classification_reviews;
    DROP TABLE cell_classification_events;
    DROP TABLE smear_analysis_summaries;
    DROP TABLE cell_explanations;
    DROP TABLE cell_predictions;
    DROP TABLE cell_classification_inputs;
    DROP TABLE cell_classification_runs;

    DROP FUNCTION protect_cell_explanation();
    DROP FUNCTION validate_cell_explanation_contract();
    DROP FUNCTION validate_cell_prediction_input();
    DROP FUNCTION protect_cell_classification_run();
    DROP FUNCTION validate_cell_classification_insert_state();
    DROP FUNCTION validate_smear_analysis_summary();
    DROP FUNCTION validate_cell_classification_review();
    DROP FUNCTION validate_cell_classification_run_snapshot();
    DROP FUNCTION validate_cell_classification_input_snapshot();
    DROP FUNCTION reject_cell_classification_row_mutation();

    DROP INDEX uq_cell_crops_id_detection;
    DROP INDEX uq_stage2_model_publications_id_version;

    ALTER VIEW legacy_cell_predictions RENAME TO cell_predictions;
    COMMENT ON VIEW cell_predictions IS
      'Contrato lógico de predicciones celulares almacenadas canónicamente en predictions.';
    """)
