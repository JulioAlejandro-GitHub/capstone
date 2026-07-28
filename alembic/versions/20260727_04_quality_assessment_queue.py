"""Persistent manually-operated quality assessment queue."""

from alembic import op

revision = "20260727_04"
down_revision = "20260727_03"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE quality_assessment_queue_items (
      id UUID PRIMARY KEY,
      analysis_run_id UUID NOT NULL REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT,
      priority SMALLINT NOT NULL DEFAULT 50 CHECK (priority IN (1, 50, 100)),
      status VARCHAR(20) NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'completed', 'failed')),
      requested_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
      requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      started_at TIMESTAMPTZ,
      completed_at TIMESTAMPTZ,
      failed_at TIMESTAMPTZ,
      attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
      last_error_code VARCHAR(80),
      last_error_message TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE UNIQUE INDEX uq_quality_queue_active_run
      ON quality_assessment_queue_items (analysis_run_id)
      WHERE status IN ('queued', 'running');
    CREATE INDEX ix_quality_queue_order
      ON quality_assessment_queue_items (status, priority DESC, requested_at ASC);
    CREATE INDEX ix_quality_queue_priority_requested
      ON quality_assessment_queue_items (priority DESC, requested_at ASC);
    """)


def downgrade():
    op.execute("DROP TABLE quality_assessment_queue_items")
