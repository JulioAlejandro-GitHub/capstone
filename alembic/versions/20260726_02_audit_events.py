"""Append-only security audit events."""

from alembic import op

revision = "20260726_02"
down_revision = "20260726_01"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
      CREATE TABLE audit_events (
        id UUID PRIMARY KEY,
        event_type TEXT NOT NULL,
        action TEXT NOT NULL,
        actor_user_id UUID REFERENCES users(id) ON DELETE RESTRICT,
        actor_username_snapshot TEXT,
        resource_type TEXT NOT NULL,
        resource_id TEXT,
        request_method TEXT NOT NULL,
        request_path TEXT NOT NULL,
        correlation_id TEXT NOT NULL,
        before_state JSONB,
        after_state JSONB,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        success BOOLEAN NOT NULL,
        error_code TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      );
      CREATE INDEX ix_audit_events_created_at ON audit_events(created_at);
      CREATE INDEX ix_audit_events_actor ON audit_events(actor_user_id, created_at);
      CREATE INDEX ix_audit_events_resource ON audit_events(resource_type, resource_id, created_at);
      CREATE FUNCTION prevent_audit_event_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        RAISE EXCEPTION 'audit_events is append-only';
      END $$;
      CREATE TRIGGER audit_events_append_only
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_event_mutation();
    """)


def downgrade():
    op.execute("""
      DROP TRIGGER audit_events_append_only ON audit_events;
      DROP FUNCTION prevent_audit_event_mutation();
      DROP TABLE audit_events;
    """)
