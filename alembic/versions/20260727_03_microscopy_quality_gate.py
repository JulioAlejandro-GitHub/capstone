"""Microscopy technical quality gate and immutable analysis runs."""

from alembic import op

revision = "20260727_03"
down_revision = "20260727_02"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE microscopy_analysis_runs (
      id UUID PRIMARY KEY, ingestion_batch_id UUID NOT NULL REFERENCES image_ingestion_batches(id) ON DELETE RESTRICT,
      subject_id UUID NOT NULL REFERENCES research_subjects(id) ON DELETE RESTRICT,
      case_id UUID NOT NULL REFERENCES scientific_cases(id) ON DELETE RESTRICT,
      sample_id UUID NOT NULL REFERENCES blood_samples(id) ON DELETE RESTRICT,
      slide_id UUID NOT NULL REFERENCES smear_slides(id) ON DELETE RESTRICT,
      run_code VARCHAR(20) NOT NULL UNIQUE,
      run_status VARCHAR(30) NOT NULL CHECK (run_status IN ('created','quality_pending','quality_processing','quality_completed','review_required','ready_for_analysis','blocked','failed','cancelled')),
      active_stage VARCHAR(30) NOT NULL CHECK (active_stage IN ('created','integrity_check','quality_assessment','quality_aggregation','technical_review','completed','failed')),
      quality_gate_status VARCHAR(20) NOT NULL CHECK (quality_gate_status IN ('pending','pass','warning','fail','error')),
      ready_for_analysis BOOLEAN NOT NULL DEFAULT false,
      quality_profile_key VARCHAR(80) NOT NULL, quality_profile_version VARCHAR(40) NOT NULL,
      quality_algorithm_version VARCHAR(40) NOT NULL,
      quality_profile_snapshot JSONB NOT NULL CHECK (jsonb_typeof(quality_profile_snapshot)='object'),
      input_manifest_sha256 CHAR(64) NOT NULL, input_image_count INTEGER NOT NULL CHECK (input_image_count>0),
      requested_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
      started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ, failed_at TIMESTAMPTZ,
      error_code VARCHAR(80), error_message TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE UNIQUE INDEX uq_microscopy_analysis_equivalent ON microscopy_analysis_runs(
      ingestion_batch_id,quality_profile_key,quality_profile_version,quality_algorithm_version,input_manifest_sha256);
    CREATE INDEX ix_microscopy_analysis_runs_status ON microscopy_analysis_runs(run_status,created_at DESC);
    CREATE INDEX ix_microscopy_analysis_runs_subject ON microscopy_analysis_runs(subject_id,created_at DESC);

    CREATE TABLE microscopy_analysis_run_images (
      id UUID PRIMARY KEY, analysis_run_id UUID NOT NULL REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT,
      microscopy_image_id UUID NOT NULL REFERENCES microscopy_images(id) ON DELETE RESTRICT,
      sequence_number INTEGER NOT NULL CHECK(sequence_number>0), input_sha256 CHAR(64) NOT NULL,
      input_file_size_bytes BIGINT NOT NULL CHECK(input_file_size_bytes>0),
      input_width_px INTEGER NOT NULL CHECK(input_width_px>0), input_height_px INTEGER NOT NULL CHECK(input_height_px>0),
      image_status_at_creation VARCHAR(30) NOT NULL,
      quality_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK(quality_status IN ('pending','pass','warning','fail','error')),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE(analysis_run_id,microscopy_image_id), UNIQUE(analysis_run_id,sequence_number),
      UNIQUE(id,analysis_run_id,microscopy_image_id)
    );

    CREATE TABLE image_quality_assessments (
      id UUID PRIMARY KEY, analysis_run_id UUID NOT NULL REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT,
      analysis_run_image_id UUID NOT NULL, microscopy_image_id UUID NOT NULL REFERENCES microscopy_images(id) ON DELETE RESTRICT,
      assessment_status VARCHAR(20) NOT NULL CHECK(assessment_status IN ('pending','processing','completed','error')),
      quality_verdict VARCHAR(20) NOT NULL CHECK(quality_verdict IN ('pending','pass','warning','fail','error')),
      integrity_verified BOOLEAN NOT NULL DEFAULT false, checksum_verified BOOLEAN NOT NULL DEFAULT false,
      decoded_successfully BOOLEAN NOT NULL DEFAULT false,
      width_px INTEGER NOT NULL CHECK(width_px>0), height_px INTEGER NOT NULL CHECK(height_px>0),
      pixel_count BIGINT NOT NULL CHECK(pixel_count>0), channel_count INTEGER, bit_depth INTEGER, color_space VARCHAR(80),
      analyzed_width_px INTEGER NOT NULL CHECK(analyzed_width_px>0), analyzed_height_px INTEGER NOT NULL CHECK(analyzed_height_px>0),
      analysis_scale DOUBLE PRECISION NOT NULL CHECK(analysis_scale>0),
      brightness_mean DOUBLE PRECISION, brightness_p05 DOUBLE PRECISION, brightness_p50 DOUBLE PRECISION, brightness_p95 DOUBLE PRECISION,
      contrast_p95_p05 DOUBLE PRECISION, luminance_stddev DOUBLE PRECISION, entropy_bits DOUBLE PRECISION,
      laplacian_variance DOUBLE PRECISION, tenengrad_mean DOUBLE PRECISION,
      dark_pixel_ratio DOUBLE PRECISION CHECK(dark_pixel_ratio BETWEEN 0 AND 1),
      bright_pixel_ratio DOUBLE PRECISION CHECK(bright_pixel_ratio BETWEEN 0 AND 1),
      near_black_border_ratio DOUBLE PRECISION CHECK(near_black_border_ratio BETWEEN 0 AND 1),
      usable_field_ratio DOUBLE PRECISION CHECK(usable_field_ratio BETWEEN 0 AND 1),
      warning_codes JSONB NOT NULL DEFAULT '[]' CHECK(jsonb_typeof(warning_codes)='array'),
      failure_codes JSONB NOT NULL DEFAULT '[]' CHECK(jsonb_typeof(failure_codes)='array'),
      metrics_json JSONB NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(metrics_json)='object'),
      started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ, error_code VARCHAR(80), error_message TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE(analysis_run_id,microscopy_image_id),
      FOREIGN KEY(analysis_run_image_id,analysis_run_id,microscopy_image_id)
        REFERENCES microscopy_analysis_run_images(id,analysis_run_id,microscopy_image_id) ON DELETE RESTRICT
    );

    CREATE TABLE microscopy_analysis_events (
      id UUID PRIMARY KEY, analysis_run_id UUID NOT NULL REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT,
      microscopy_image_id UUID REFERENCES microscopy_images(id) ON DELETE RESTRICT,
      event_type VARCHAR(80) NOT NULL, stage VARCHAR(40) NOT NULL, status VARCHAR(30) NOT NULL,
      message_code VARCHAR(80), message TEXT, progress_current INTEGER, progress_total INTEGER,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CHECK(progress_current IS NULL OR progress_current>=0), CHECK(progress_total IS NULL OR progress_total>=0)
    );
    CREATE INDEX ix_microscopy_analysis_events_run ON microscopy_analysis_events(analysis_run_id,created_at,id);

    CREATE TABLE quality_gate_decisions (
      id UUID PRIMARY KEY, analysis_run_id UUID NOT NULL REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT,
      decision VARCHAR(30) NOT NULL CHECK(decision IN ('approve_with_warnings','reject')),
      comment TEXT NOT NULL CHECK(length(btrim(comment))>0),
      actor_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE INDEX ix_quality_gate_decisions_run ON quality_gate_decisions(analysis_run_id,created_at,id);
    """)


def downgrade():
    op.execute("""
    DROP TABLE quality_gate_decisions;
    DROP TABLE microscopy_analysis_events;
    DROP TABLE image_quality_assessments;
    DROP TABLE microscopy_analysis_run_images;
    DROP TABLE microscopy_analysis_runs;
    """)
