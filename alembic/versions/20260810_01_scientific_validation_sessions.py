"""Reproducible scientific-validation session snapshots."""

from alembic import op


revision = "20260810_01"
down_revision = "20260728_03"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE scientific_validation_sessions (
      id UUID PRIMARY KEY,
      name VARCHAR(200) NOT NULL CHECK (btrim(name) <> ''),
      description TEXT,
      datasource VARCHAR(80) NOT NULL CHECK (btrim(datasource) <> ''),
      protocol_key VARCHAR(120) NOT NULL CHECK (btrim(protocol_key) <> ''),
      protocol_version VARCHAR(80) NOT NULL CHECK (btrim(protocol_version) <> ''),
      matching_iou_threshold DOUBLE PRECISION NOT NULL
        CHECK (matching_iou_threshold > 0 AND matching_iou_threshold <= 1),
      status VARCHAR(30) NOT NULL DEFAULT 'draft' CHECK (status IN (
        'draft','annotation_in_progress','ready_for_analysis','completed','archived'
      )),
      initial_snapshot JSONB NOT NULL CHECK (jsonb_typeof(initial_snapshot) = 'object'),
      snapshot_sha256 CHAR(64) NOT NULL CHECK (snapshot_sha256 ~ '^[0-9a-f]{64}$'),
      created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
      updated_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      archived_at TIMESTAMPTZ,
      archived_by UUID REFERENCES users(id) ON DELETE RESTRICT,
      CONSTRAINT ck_validation_session_archive CHECK (
        (status <> 'archived' AND archived_at IS NULL AND archived_by IS NULL) OR
        (status = 'archived' AND archived_at IS NOT NULL AND archived_by IS NOT NULL)
      )
    );
    CREATE INDEX ix_validation_sessions_status_created
      ON scientific_validation_sessions(status, created_at DESC, id DESC);
    CREATE INDEX ix_validation_sessions_creator_created
      ON scientific_validation_sessions(created_by, created_at DESC, id DESC);

    CREATE TABLE scientific_validation_images (
      session_id UUID NOT NULL REFERENCES scientific_validation_sessions(id) ON DELETE RESTRICT,
      microscopy_image_id UUID NOT NULL REFERENCES microscopy_images(id) ON DELETE RESTRICT,
      image_sha256 CHAR(64) NOT NULL CHECK (image_sha256 ~ '^[0-9a-f]{64}$'),
      sequence_number INTEGER NOT NULL CHECK (sequence_number > 0),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      PRIMARY KEY(session_id, microscopy_image_id),
      UNIQUE(session_id, sequence_number)
    );

    CREATE TABLE scientific_validation_detection_runs (
      session_id UUID NOT NULL REFERENCES scientific_validation_sessions(id) ON DELETE RESTRICT,
      detection_run_id UUID NOT NULL REFERENCES cell_detection_runs(id) ON DELETE RESTRICT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      PRIMARY KEY(session_id, detection_run_id)
    );

    CREATE TABLE scientific_validation_classification_runs (
      session_id UUID NOT NULL REFERENCES scientific_validation_sessions(id) ON DELETE RESTRICT,
      classification_run_id UUID NOT NULL REFERENCES cell_classification_runs(id) ON DELETE RESTRICT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      PRIMARY KEY(session_id, classification_run_id)
    );

    CREATE FUNCTION protect_validation_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'scientific validation snapshots cannot be deleted';
      END IF;
      IF OLD.datasource IS DISTINCT FROM NEW.datasource
        OR OLD.protocol_key IS DISTINCT FROM NEW.protocol_key
        OR OLD.protocol_version IS DISTINCT FROM NEW.protocol_version
        OR OLD.matching_iou_threshold IS DISTINCT FROM NEW.matching_iou_threshold
        OR OLD.initial_snapshot IS DISTINCT FROM NEW.initial_snapshot
        OR OLD.snapshot_sha256 IS DISTINCT FROM NEW.snapshot_sha256
        OR OLD.created_by IS DISTINCT FROM NEW.created_by
        OR OLD.created_at IS DISTINCT FROM NEW.created_at THEN
        RAISE EXCEPTION 'scientific validation snapshot identity is immutable';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER trg_validation_snapshot_protected
      BEFORE UPDATE OR DELETE ON scientific_validation_sessions
      FOR EACH ROW EXECUTE FUNCTION protect_validation_snapshot();

    CREATE FUNCTION prevent_validation_membership_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      RAISE EXCEPTION 'scientific validation membership is append-only';
    END $$;
    CREATE TRIGGER trg_validation_images_immutable
      BEFORE UPDATE OR DELETE ON scientific_validation_images
      FOR EACH ROW EXECUTE FUNCTION prevent_validation_membership_mutation();
    CREATE TRIGGER trg_validation_detection_runs_immutable
      BEFORE UPDATE OR DELETE ON scientific_validation_detection_runs
      FOR EACH ROW EXECUTE FUNCTION prevent_validation_membership_mutation();
    CREATE TRIGGER trg_validation_classification_runs_immutable
      BEFORE UPDATE OR DELETE ON scientific_validation_classification_runs
      FOR EACH ROW EXECUTE FUNCTION prevent_validation_membership_mutation();
    """)


def downgrade():
    op.execute("""
    DROP TRIGGER trg_validation_classification_runs_immutable ON scientific_validation_classification_runs;
    DROP TRIGGER trg_validation_detection_runs_immutable ON scientific_validation_detection_runs;
    DROP TRIGGER trg_validation_images_immutable ON scientific_validation_images;
    DROP FUNCTION prevent_validation_membership_mutation();
    DROP TRIGGER trg_validation_snapshot_protected ON scientific_validation_sessions;
    DROP FUNCTION protect_validation_snapshot();
    DROP TABLE scientific_validation_classification_runs;
    DROP TABLE scientific_validation_detection_runs;
    DROP TABLE scientific_validation_images;
    DROP TABLE scientific_validation_sessions;
    """)
