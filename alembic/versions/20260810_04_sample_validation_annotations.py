"""Add canonical blood-sample targets to scientific validation annotations."""

from alembic import op


revision = "20260810_04"
down_revision = "20260810_03"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE scientific_validation_annotations
      ADD COLUMN sample_id UUID REFERENCES blood_samples(id) ON DELETE RESTRICT;

    ALTER TABLE scientific_validation_annotations
      DROP CONSTRAINT ck_validation_annotation_exact_target,
      DROP CONSTRAINT scientific_validation_annotations_target_type_check;

    ALTER TABLE scientific_validation_annotations
      ADD CONSTRAINT scientific_validation_annotations_target_type_check
        CHECK (target_type IN ('cell','analysis','sample')),
      ADD CONSTRAINT ck_validation_annotation_exact_target CHECK (
        (target_type='cell' AND cell_detection_id IS NOT NULL
          AND analysis_run_id IS NULL AND sample_id IS NULL)
        OR
        (target_type='analysis' AND analysis_run_id IS NOT NULL
          AND cell_detection_id IS NULL AND sample_id IS NULL)
        OR
        (target_type='sample' AND sample_id IS NOT NULL
          AND cell_detection_id IS NULL AND analysis_run_id IS NULL)
      );

    CREATE INDEX ix_validation_annotations_session_sample
      ON scientific_validation_annotations(validation_session_id, sample_id, created_at, id)
      WHERE target_type='sample';

    CREATE OR REPLACE FUNCTION protect_validation_annotation()
    RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'scientific validation annotations cannot be deleted'
          USING ERRCODE='55000';
      END IF;
      IF OLD.validation_session_id IS DISTINCT FROM NEW.validation_session_id
        OR OLD.target_type IS DISTINCT FROM NEW.target_type
        OR OLD.cell_detection_id IS DISTINCT FROM NEW.cell_detection_id
        OR OLD.analysis_run_id IS DISTINCT FROM NEW.analysis_run_id
        OR OLD.sample_id IS DISTINCT FROM NEW.sample_id
        OR OLD.created_by IS DISTINCT FROM NEW.created_by
        OR OLD.created_at IS DISTINCT FROM NEW.created_at THEN
        RAISE EXCEPTION 'scientific validation annotation identity is immutable'
          USING ERRCODE='55000';
      END IF;
      IF NEW.version <> OLD.version + 1 OR NEW.updated_at <= OLD.updated_at THEN
        RAISE EXCEPTION 'scientific validation annotation version must advance once'
          USING ERRCODE='40001';
      END IF;
      RETURN NEW;
    END $$;
    """)


def downgrade():
    op.execute("""
    DO $$
    BEGIN
      IF EXISTS(
        SELECT 1 FROM scientific_validation_annotations WHERE target_type='sample'
      ) THEN
        RAISE EXCEPTION 'cannot downgrade while canonical sample annotations exist';
      END IF;
    END $$;
    DROP INDEX ix_validation_annotations_session_sample;
    ALTER TABLE scientific_validation_annotations
      DROP CONSTRAINT ck_validation_annotation_exact_target,
      DROP CONSTRAINT scientific_validation_annotations_target_type_check,
      DROP COLUMN sample_id;
    ALTER TABLE scientific_validation_annotations
      ADD CONSTRAINT scientific_validation_annotations_target_type_check
        CHECK (target_type IN ('cell','analysis')),
      ADD CONSTRAINT ck_validation_annotation_exact_target CHECK (
        (target_type='cell' AND cell_detection_id IS NOT NULL AND analysis_run_id IS NULL)
        OR
        (target_type='analysis' AND analysis_run_id IS NOT NULL AND cell_detection_id IS NULL)
      );
    """)
