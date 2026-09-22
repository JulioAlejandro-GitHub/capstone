"""E10 durable event metadata on the existing append-only evidence ledger."""
from alembic import op
import sqlalchemy as sa

revision = "20260922_01"
down_revision = "20260915_01"
branch_labels = None
depends_on = None

DDL = r"""
ALTER TABLE train_execution_records
 ADD COLUMN event_id uuid,
 ADD COLUMN event_sequence numeric,
 ADD CONSTRAINT train_event_metadata CHECK (
   (event_id IS NULL AND event_sequence IS NULL AND kind <> 'e10_event') OR
   (event_id IS NOT NULL AND event_sequence IS NOT NULL AND
    event_sequence >= 1 AND event_sequence = trunc(event_sequence) AND
    event_sequence NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND
    kind = 'e10_event' AND phase = 'run_event_v1' AND record_key = event_id::text AND
    jsonb_typeof(payload->'canonical_event') IS NOT DISTINCT FROM 'string' AND
    payload - 'canonical_event' = '{}'::jsonb)
 );
CREATE UNIQUE INDEX train_event_id_unique ON train_execution_records(event_id)
 WHERE event_id IS NOT NULL;
CREATE UNIQUE INDEX train_event_sequence_unique ON train_execution_records(run_id,event_sequence)
 WHERE event_sequence IS NOT NULL;
CREATE FUNCTION train_event_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE s record; previous numeric;
BEGIN
 IF NEW.event_id IS NULL THEN RETURN NEW; END IF;
 -- Same global ownership guard as reservations. Acquired before the session lock.
 PERFORM experiment_require_owner();
 SELECT * INTO s FROM train_execution_sessions WHERE run_id=NEW.run_id FOR UPDATE NOWAIT;
 IF s.run_id IS NULL OR s.state IS DISTINCT FROM 'active'
 OR s.owner::text IS DISTINCT FROM current_setting('capstone.train_owner',true)
 THEN RAISE EXCEPTION 'TRAIN_OWNER_FENCED'; END IF;
 SELECT coalesce(max(event_sequence),0) INTO previous FROM train_execution_records WHERE run_id=NEW.run_id;
 IF NEW.event_sequence IS DISTINCT FROM previous+1
 THEN RAISE EXCEPTION 'RESULT_EVENT_SEQUENCE_INVALID'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER a_train_event_guard BEFORE INSERT ON train_execution_records
 FOR EACH ROW EXECUTE FUNCTION train_event_guard();
"""


def upgrade():
    op.execute(DDL)
    ctx = op.get_context()
    schema = "public" if ctx.as_sql else op.get_bind().execute(sa.text("SELECT current_schema()")).scalar_one()
    quoted = ctx.dialect.identifier_preparer.quote(schema)
    op.execute(f"ALTER FUNCTION train_event_guard() SET search_path={quoted},pg_catalog")


def downgrade():
    # Dropping metadata after events exist would erase durable retry identity.
    op.execute("LOCK TABLE train_execution_records IN ACCESS EXCLUSIVE MODE")
    op.execute("""DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM train_execution_records WHERE event_id IS NOT NULL)
      THEN RAISE EXCEPTION 'E10_EVENTS_REQUIRE_FORWARD_MIGRATION'; END IF;
    END $$""")
    op.execute("""DROP TRIGGER a_train_event_guard ON train_execution_records;
      DROP FUNCTION train_event_guard();
      DROP INDEX train_event_sequence_unique;
      DROP INDEX train_event_id_unique;
      ALTER TABLE train_execution_records DROP CONSTRAINT train_event_metadata,
        DROP COLUMN event_sequence, DROP COLUMN event_id;""")
