"""Editable scientific validation annotations with append-only history."""

from alembic import op


revision = "20260810_02"
down_revision = "20260810_01"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE scientific_validation_annotations (
      id UUID PRIMARY KEY,
      validation_session_id UUID NOT NULL
        REFERENCES scientific_validation_sessions(id) ON DELETE RESTRICT,
      target_type VARCHAR(20) NOT NULL CHECK (target_type IN ('cell','analysis')),
      cell_detection_id UUID REFERENCES cell_detections(id) ON DELETE RESTRICT,
      analysis_run_id UUID REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT,
      category VARCHAR(120) NOT NULL CHECK (btrim(category) <> ''),
      content TEXT NOT NULL CHECK (btrim(content) <> ''),
      version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
      created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CONSTRAINT ck_validation_annotation_exact_target CHECK (
        (target_type='cell' AND cell_detection_id IS NOT NULL AND analysis_run_id IS NULL)
        OR
        (target_type='analysis' AND analysis_run_id IS NOT NULL AND cell_detection_id IS NULL)
      )
    );
    CREATE INDEX ix_validation_annotations_session_created
      ON scientific_validation_annotations(validation_session_id, created_at, id);
    CREATE INDEX ix_validation_annotations_session_cell
      ON scientific_validation_annotations(validation_session_id, cell_detection_id, created_at, id)
      WHERE target_type='cell';
    CREATE INDEX ix_validation_annotations_session_analysis
      ON scientific_validation_annotations(validation_session_id, analysis_run_id, created_at, id)
      WHERE target_type='analysis';
    CREATE INDEX ix_validation_annotations_session_category
      ON scientific_validation_annotations(validation_session_id, category, created_at, id);

    CREATE TABLE scientific_validation_annotation_events (
      id UUID PRIMARY KEY,
      annotation_id UUID NOT NULL
        REFERENCES scientific_validation_annotations(id) ON DELETE RESTRICT,
      validation_session_id UUID NOT NULL
        REFERENCES scientific_validation_sessions(id) ON DELETE RESTRICT,
      event_type VARCHAR(20) NOT NULL CHECK (event_type IN ('created','updated')),
      annotation_version INTEGER NOT NULL CHECK (annotation_version > 0),
      actor_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
      before_state JSONB,
      after_state JSONB NOT NULL CHECK (jsonb_typeof(after_state)='object'),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CONSTRAINT ck_validation_annotation_event_before CHECK (
        (event_type='created' AND before_state IS NULL AND annotation_version=1)
        OR
        (event_type='updated' AND jsonb_typeof(before_state)='object' AND annotation_version>1)
      ),
      UNIQUE(annotation_id, annotation_version)
    );
    CREATE INDEX ix_validation_annotation_events_annotation_created
      ON scientific_validation_annotation_events(annotation_id, created_at, id);
    CREATE INDEX ix_validation_annotation_events_actor_created
      ON scientific_validation_annotation_events(actor_user_id, created_at DESC, id DESC);

    CREATE FUNCTION protect_validation_annotation() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'scientific validation annotations cannot be deleted'
          USING ERRCODE='55000';
      END IF;
      IF OLD.validation_session_id IS DISTINCT FROM NEW.validation_session_id
        OR OLD.target_type IS DISTINCT FROM NEW.target_type
        OR OLD.cell_detection_id IS DISTINCT FROM NEW.cell_detection_id
        OR OLD.analysis_run_id IS DISTINCT FROM NEW.analysis_run_id
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
    CREATE TRIGGER trg_validation_annotation_protected
      BEFORE UPDATE OR DELETE ON scientific_validation_annotations
      FOR EACH ROW EXECUTE FUNCTION protect_validation_annotation();

    CREATE FUNCTION prevent_validation_annotation_event_mutation()
    RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      RAISE EXCEPTION 'scientific validation annotation events are append-only'
        USING ERRCODE='55000';
    END $$;
    CREATE TRIGGER trg_validation_annotation_events_append_only
      BEFORE UPDATE OR DELETE ON scientific_validation_annotation_events
      FOR EACH ROW EXECUTE FUNCTION prevent_validation_annotation_event_mutation();
    """)


def downgrade():
    op.execute("""
    DROP TRIGGER trg_validation_annotation_events_append_only
      ON scientific_validation_annotation_events;
    DROP FUNCTION prevent_validation_annotation_event_mutation();
    DROP TRIGGER trg_validation_annotation_protected
      ON scientific_validation_annotations;
    DROP FUNCTION protect_validation_annotation();
    DROP TABLE scientific_validation_annotation_events;
    DROP TABLE scientific_validation_annotations;
    """)
