"""Harden frozen assignment protection across version-changing updates.

Revision ID: 20260812_02
Revises: 20260812_01
"""

from alembic import op


revision = "20260812_02"
down_revision = "20260812_01"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE FUNCTION protect_frozen_dataset_assignment_updates()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE old_status TEXT; new_status TEXT;
        BEGIN
          SELECT status INTO old_status
          FROM dataset_versions WHERE id = OLD.dataset_version_id;
          SELECT status INTO new_status
          FROM dataset_versions WHERE id = NEW.dataset_version_id;
          IF old_status = 'FROZEN' OR new_status = 'FROZEN' THEN
            RAISE EXCEPTION 'assignments of a FROZEN dataset version are immutable'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_protect_frozen_dataset_assignment_updates
          BEFORE UPDATE ON dataset_split_assignments
          FOR EACH ROW EXECUTE FUNCTION protect_frozen_dataset_assignment_updates();
        """
    )


def downgrade():
    raise RuntimeError(
        "Downgrade is intentionally prohibited for scientific lineage migrations"
    )
