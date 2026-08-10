"""Allow optional comments on append-only human cell classifications."""

from alembic import op


revision = "20260810_03"
down_revision = "20260810_02"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE cell_classification_reviews
      DROP CONSTRAINT ck_cell_classification_review_payload;
    ALTER TABLE cell_classification_reviews
      ADD CONSTRAINT ck_cell_classification_review_payload CHECK (
        (
          decision='confirmed'
          AND (comment IS NULL OR btrim(comment) <> '')
        ) OR (
          decision='corrected'
          AND reviewed_label IS NOT NULL
          AND (comment IS NULL OR btrim(comment) <> '')
        ) OR (
          decision IN ('needs_attention','comment_only')
          AND reviewed_label IS NULL
          AND comment IS NOT NULL
          AND btrim(comment) <> ''
        )
      );
    ALTER TABLE cell_classification_reviews
      ALTER COLUMN created_at SET DEFAULT clock_timestamp();
    """)


def downgrade():
    op.execute("""
    ALTER TABLE cell_classification_reviews
      DROP CONSTRAINT ck_cell_classification_review_payload;
    ALTER TABLE cell_classification_reviews
      ADD CONSTRAINT ck_cell_classification_review_payload CHECK (
        (
          decision='confirmed'
          AND (comment IS NULL OR btrim(comment) <> '')
        ) OR (
          decision='corrected'
          AND reviewed_label IS NOT NULL
          AND comment IS NOT NULL
          AND btrim(comment) <> ''
        ) OR (
          decision IN ('needs_attention','comment_only')
          AND reviewed_label IS NULL
          AND comment IS NOT NULL
          AND btrim(comment) <> ''
        )
      );
    ALTER TABLE cell_classification_reviews
      ALTER COLUMN created_at SET DEFAULT now();
    """)
