"""Baseline cell detection, derived crops, and append-only scientific review."""

from alembic import op


revision = "20260727_05"
down_revision = "20260727_04"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE cell_detection_runs (
      id UUID PRIMARY KEY,
      analysis_run_id UUID NOT NULL
        REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT,
      detection_run_code VARCHAR(20) NOT NULL UNIQUE
        CHECK (detection_run_code ~ '^DET-[A-F0-9]{8}$'),
      detector_key VARCHAR(80) NOT NULL CHECK (btrim(detector_key) <> ''),
      detector_version VARCHAR(40) NOT NULL CHECK (btrim(detector_version) <> ''),
      algorithm_version VARCHAR(80) NOT NULL CHECK (btrim(algorithm_version) <> ''),
      profile_snapshot JSONB NOT NULL
        CHECK (jsonb_typeof(profile_snapshot) = 'object'),
      input_manifest_sha256 CHAR(64) NOT NULL
        CHECK (input_manifest_sha256 ~ '^[0-9a-f]{64}$'),
      status VARCHAR(30) NOT NULL
        CHECK (status IN (
          'created','processing','completed','completed_with_warnings','failed'
        )),
      image_count INTEGER NOT NULL CHECK (image_count > 0),
      processed_image_count INTEGER NOT NULL DEFAULT 0
        CHECK (processed_image_count >= 0 AND processed_image_count <= image_count),
      component_count INTEGER NOT NULL DEFAULT 0 CHECK (component_count >= 0),
      detection_count INTEGER NOT NULL DEFAULT 0 CHECK (detection_count >= 0),
      crop_count INTEGER NOT NULL DEFAULT 0 CHECK (crop_count >= 0),
      warning_count INTEGER NOT NULL DEFAULT 0 CHECK (warning_count >= 0),
      requested_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
      started_at TIMESTAMPTZ,
      completed_at TIMESTAMPTZ,
      failed_at TIMESTAMPTZ,
      error_code VARCHAR(80),
      error_message TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CONSTRAINT uq_cell_detection_runs_identity UNIQUE(id, analysis_run_id),
      CONSTRAINT ck_cell_detection_run_terminal_state CHECK (
        (status = 'created' AND started_at IS NULL AND completed_at IS NULL
          AND failed_at IS NULL AND error_code IS NULL AND error_message IS NULL)
        OR
        (status = 'processing' AND started_at IS NOT NULL AND completed_at IS NULL
          AND failed_at IS NULL AND error_code IS NULL AND error_message IS NULL)
        OR
        (status IN ('completed','completed_with_warnings') AND started_at IS NOT NULL
          AND completed_at IS NOT NULL AND failed_at IS NULL
          AND error_code IS NULL AND error_message IS NULL)
        OR
        (status = 'failed' AND started_at IS NOT NULL AND completed_at IS NULL
          AND failed_at IS NOT NULL AND error_code IS NOT NULL)
      )
    );
    CREATE UNIQUE INDEX uq_cell_detection_runs_equivalent_active
      ON cell_detection_runs(
        analysis_run_id, detector_key, detector_version, algorithm_version,
        input_manifest_sha256
      )
      WHERE status IN (
        'created','processing','completed','completed_with_warnings'
      );
    CREATE INDEX ix_cell_detection_runs_status_created
      ON cell_detection_runs(status, created_at DESC, id DESC);
    CREATE INDEX ix_cell_detection_runs_analysis_created
      ON cell_detection_runs(analysis_run_id, created_at DESC, id DESC);

    CREATE TABLE image_connected_components (
      id UUID PRIMARY KEY,
      detection_run_id UUID NOT NULL,
      analysis_run_id UUID NOT NULL,
      analysis_run_image_id UUID NOT NULL,
      microscopy_image_id UUID NOT NULL,
      component_index INTEGER NOT NULL CHECK (component_index > 0),
      bbox_x INTEGER NOT NULL CHECK (bbox_x >= 0),
      bbox_y INTEGER NOT NULL CHECK (bbox_y >= 0),
      bbox_width INTEGER NOT NULL CHECK (bbox_width > 0),
      bbox_height INTEGER NOT NULL CHECK (bbox_height > 0),
      centroid_x DOUBLE PRECISION NOT NULL CHECK (centroid_x >= 0),
      centroid_y DOUBLE PRECISION NOT NULL CHECK (centroid_y >= 0),
      area_px INTEGER NOT NULL CHECK (area_px > 0),
      perimeter_px DOUBLE PRECISION CHECK (perimeter_px IS NULL OR perimeter_px >= 0),
      circularity DOUBLE PRECISION
        CHECK (circularity IS NULL OR circularity BETWEEN 0 AND 1),
      solidity DOUBLE PRECISION
        CHECK (solidity IS NULL OR solidity BETWEEN 0 AND 1),
      touches_border BOOLEAN NOT NULL,
      component_status VARCHAR(30) NOT NULL
        CHECK (component_status IN ('candidate','accepted','rejected_by_filter')),
      rejection_code VARCHAR(80),
      metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(metrics_json) = 'object'),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CONSTRAINT fk_components_detection_analysis
        FOREIGN KEY(detection_run_id, analysis_run_id)
        REFERENCES cell_detection_runs(id, analysis_run_id) ON DELETE RESTRICT,
      CONSTRAINT fk_components_frozen_image
        FOREIGN KEY(analysis_run_image_id, analysis_run_id, microscopy_image_id)
        REFERENCES microscopy_analysis_run_images(
          id, analysis_run_id, microscopy_image_id
        ) ON DELETE RESTRICT,
      CONSTRAINT uq_image_connected_components_run_image_index
        UNIQUE(detection_run_id, analysis_run_image_id, component_index),
      CONSTRAINT uq_image_connected_components_identity
        UNIQUE(
          id, detection_run_id, analysis_run_image_id, microscopy_image_id
        ),
      CONSTRAINT ck_connected_component_rejection CHECK (
        (component_status = 'rejected_by_filter' AND rejection_code IS NOT NULL)
        OR
        (component_status <> 'rejected_by_filter' AND rejection_code IS NULL)
      )
    );
    CREATE INDEX ix_image_connected_components_run_image
      ON image_connected_components(
        detection_run_id, microscopy_image_id, component_index
      );
    CREATE INDEX ix_image_connected_components_status
      ON image_connected_components(
        detection_run_id, component_status, component_index
      );

    CREATE TABLE cell_detections (
      id UUID PRIMARY KEY,
      detection_run_id UUID NOT NULL,
      analysis_run_id UUID NOT NULL,
      connected_component_id UUID NOT NULL,
      analysis_run_image_id UUID NOT NULL,
      microscopy_image_id UUID NOT NULL,
      cell_index INTEGER NOT NULL CHECK (cell_index > 0),
      cell_code VARCHAR(40) NOT NULL
        CHECK (cell_code ~ '^CELL-[A-F0-9]{12}$'),
      bbox_x INTEGER NOT NULL CHECK (bbox_x >= 0),
      bbox_y INTEGER NOT NULL CHECK (bbox_y >= 0),
      bbox_width INTEGER NOT NULL CHECK (bbox_width > 0),
      bbox_height INTEGER NOT NULL CHECK (bbox_height > 0),
      coordinate_space VARCHAR(40) NOT NULL
        CHECK (coordinate_space = 'original_image_pixels'),
      detector_score DOUBLE PRECISION
        CHECK (detector_score IS NULL OR detector_score BETWEEN 0 AND 1),
      automated_status VARCHAR(30) NOT NULL
        CHECK (automated_status = 'candidate'),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CONSTRAINT fk_cell_detections_run_analysis
        FOREIGN KEY(detection_run_id, analysis_run_id)
        REFERENCES cell_detection_runs(id, analysis_run_id) ON DELETE RESTRICT,
      CONSTRAINT fk_cell_detections_component
        FOREIGN KEY(
          connected_component_id, detection_run_id, analysis_run_image_id,
          microscopy_image_id
        )
        REFERENCES image_connected_components(
          id, detection_run_id, analysis_run_image_id, microscopy_image_id
        ) ON DELETE RESTRICT,
      CONSTRAINT uq_cell_detections_component UNIQUE(connected_component_id),
      CONSTRAINT uq_cell_detections_run_index
        UNIQUE(detection_run_id, cell_index),
      CONSTRAINT uq_cell_detections_identity
        UNIQUE(id, detection_run_id, microscopy_image_id),
      CONSTRAINT uq_cell_detections_cell_code UNIQUE(cell_code)
    );
    CREATE INDEX ix_cell_detections_run_image
      ON cell_detections(detection_run_id, microscopy_image_id, cell_index);

    CREATE TABLE cell_crops (
      id UUID PRIMARY KEY,
      cell_detection_id UUID NOT NULL,
      relative_storage_key TEXT NOT NULL CHECK (
        relative_storage_key ~
        '^cell-crops/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/crop[.]png$'
      ),
      sha256 CHAR(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
      file_size_bytes BIGINT NOT NULL CHECK (file_size_bytes > 0),
      width_px INTEGER NOT NULL CHECK (width_px > 0),
      height_px INTEGER NOT NULL CHECK (height_px > 0),
      format VARCHAR(20) NOT NULL CHECK (format = 'PNG'),
      padding_px INTEGER NOT NULL CHECK (padding_px >= 0),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CONSTRAINT uq_cell_crops_detection UNIQUE(cell_detection_id),
      CONSTRAINT uq_cell_crops_storage_key UNIQUE(relative_storage_key),
      CONSTRAINT fk_cell_crops_detection
        FOREIGN KEY(cell_detection_id)
        REFERENCES cell_detections(id) ON DELETE RESTRICT
    );

    CREATE TABLE cell_detection_events (
      id UUID PRIMARY KEY,
      detection_run_id UUID NOT NULL
        REFERENCES cell_detection_runs(id) ON DELETE RESTRICT,
      microscopy_image_id UUID
        REFERENCES microscopy_images(id) ON DELETE RESTRICT,
      event_type VARCHAR(100) NOT NULL CHECK (btrim(event_type) <> ''),
      stage VARCHAR(50) NOT NULL CHECK (btrim(stage) <> ''),
      status VARCHAR(30) NOT NULL CHECK (btrim(status) <> ''),
      message_code VARCHAR(80),
      message TEXT,
      progress_current INTEGER CHECK (progress_current IS NULL OR progress_current >= 0),
      progress_total INTEGER CHECK (progress_total IS NULL OR progress_total >= 0),
      metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(metadata_json) = 'object'),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CONSTRAINT ck_cell_detection_event_progress CHECK (
        progress_current IS NULL OR progress_total IS NULL
        OR progress_current <= progress_total
      )
    );
    CREATE INDEX ix_cell_detection_events_run_created
      ON cell_detection_events(detection_run_id, created_at, id);
    CREATE INDEX ix_cell_detection_events_run_image
      ON cell_detection_events(detection_run_id, microscopy_image_id, created_at, id);

    CREATE TABLE scientific_reviews (
      id UUID PRIMARY KEY,
      entity_type VARCHAR(40) NOT NULL CHECK (entity_type = 'cell_detection'),
      entity_id UUID NOT NULL REFERENCES cell_detections(id) ON DELETE RESTRICT,
      decision VARCHAR(30) NOT NULL
        CHECK (decision IN (
          'accepted','rejected','needs_attention','comment_only'
        )),
      comment TEXT,
      actor_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CONSTRAINT ck_scientific_review_comment CHECK (
        (decision = 'accepted' AND (comment IS NULL OR btrim(comment) <> ''))
        OR
        (decision IN ('rejected','needs_attention','comment_only')
          AND comment IS NOT NULL AND btrim(comment) <> '')
      )
    );
    CREATE INDEX ix_scientific_reviews_entity_created
      ON scientific_reviews(entity_type, entity_id, created_at, id);
    CREATE INDEX ix_scientific_reviews_actor_created
      ON scientific_reviews(actor_user_id, created_at DESC, id DESC);

    CREATE FUNCTION reject_cell_analysis_row_mutation()
    RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      RAISE EXCEPTION 'cell analysis result and review rows are append-only'
        USING ERRCODE = '55000';
    END;
    $$;

    CREATE TRIGGER trg_image_connected_components_append_only
      BEFORE UPDATE OR DELETE ON image_connected_components
      FOR EACH ROW EXECUTE FUNCTION reject_cell_analysis_row_mutation();
    CREATE TRIGGER trg_cell_detections_append_only
      BEFORE UPDATE OR DELETE ON cell_detections
      FOR EACH ROW EXECUTE FUNCTION reject_cell_analysis_row_mutation();
    CREATE TRIGGER trg_cell_crops_append_only
      BEFORE UPDATE OR DELETE ON cell_crops
      FOR EACH ROW EXECUTE FUNCTION reject_cell_analysis_row_mutation();
    CREATE TRIGGER trg_cell_detection_events_append_only
      BEFORE UPDATE OR DELETE ON cell_detection_events
      FOR EACH ROW EXECUTE FUNCTION reject_cell_analysis_row_mutation();
    CREATE TRIGGER trg_scientific_reviews_append_only
      BEFORE UPDATE OR DELETE ON scientific_reviews
      FOR EACH ROW EXECUTE FUNCTION reject_cell_analysis_row_mutation();

    CREATE FUNCTION protect_cell_detection_run_identity()
    RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'cell_detection_runs cannot be deleted'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status IN ('completed','completed_with_warnings','failed') THEN
        RAISE EXCEPTION 'terminal cell_detection_runs are immutable'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status = 'created' AND NEW.status NOT IN ('processing','failed') THEN
        RAISE EXCEPTION 'invalid cell detection run transition'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status = 'processing'
        AND NEW.status NOT IN (
          'processing','completed','completed_with_warnings','failed'
        )
      THEN
        RAISE EXCEPTION 'invalid cell detection run transition'
          USING ERRCODE = '55000';
      END IF;
      IF NEW.analysis_run_id IS DISTINCT FROM OLD.analysis_run_id
        OR NEW.detection_run_code IS DISTINCT FROM OLD.detection_run_code
        OR NEW.detector_key IS DISTINCT FROM OLD.detector_key
        OR NEW.detector_version IS DISTINCT FROM OLD.detector_version
        OR NEW.algorithm_version IS DISTINCT FROM OLD.algorithm_version
        OR NEW.profile_snapshot IS DISTINCT FROM OLD.profile_snapshot
        OR NEW.input_manifest_sha256 IS DISTINCT FROM OLD.input_manifest_sha256
        OR NEW.image_count IS DISTINCT FROM OLD.image_count
        OR NEW.requested_by IS DISTINCT FROM OLD.requested_by
        OR NEW.created_at IS DISTINCT FROM OLD.created_at
      THEN
        RAISE EXCEPTION 'cell_detection_runs identity and profile are immutable'
          USING ERRCODE = '55000';
      END IF;
      RETURN NEW;
    END;
    $$;
    CREATE TRIGGER trg_cell_detection_runs_immutable_identity
      BEFORE UPDATE OR DELETE ON cell_detection_runs
      FOR EACH ROW EXECUTE FUNCTION protect_cell_detection_run_identity();
    """)


def downgrade():
    op.execute("""
    DROP TABLE scientific_reviews;
    DROP TABLE cell_detection_events;
    DROP TABLE cell_crops;
    DROP TABLE cell_detections;
    DROP TABLE image_connected_components;
    DROP TABLE cell_detection_runs;
    DROP FUNCTION protect_cell_detection_run_identity();
    DROP FUNCTION reject_cell_analysis_row_mutation();
    """)
