"""Allow CELL and SAMPLE annotations without a validation session."""

from alembic import op


revision = "20260810_05"
down_revision = "20260810_04"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE scientific_validation_annotations
      ALTER COLUMN validation_session_id DROP NOT NULL;
    ALTER TABLE scientific_validation_annotation_events
      ALTER COLUMN validation_session_id DROP NOT NULL;
    CREATE INDEX ix_validation_annotations_general_target
      ON scientific_validation_annotations(target_type, cell_detection_id, sample_id, created_at, id)
      WHERE validation_session_id IS NULL;
    """)


def downgrade():
    op.execute("""
    DO $$
    BEGIN
      IF EXISTS(
        SELECT 1 FROM scientific_validation_annotations WHERE validation_session_id IS NULL
      ) THEN
        RAISE EXCEPTION 'cannot downgrade while general scientific annotations exist';
      END IF;
    END $$;
    DROP INDEX ix_validation_annotations_general_target;
    ALTER TABLE scientific_validation_annotation_events
      ALTER COLUMN validation_session_id SET NOT NULL;
    ALTER TABLE scientific_validation_annotations
      ALTER COLUMN validation_session_id SET NOT NULL;
    """)
