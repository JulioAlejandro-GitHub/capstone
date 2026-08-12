"""Add scientific dataset invariants and lifecycle protection.

Revision ID: 20260812_01
Revises: 20260811_01
"""

from alembic import op


revision = "20260812_01"
down_revision = "20260811_01"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE FUNCTION enforce_dataset_assignment_consistency()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
          source_identity UUID;
          source_class_index INTEGER;
          source_class_name TEXT;
          conflicting_split TEXT;
          version_status TEXT;
        BEGIN
          SELECT status INTO version_status
          FROM dataset_versions WHERE id = NEW.dataset_version_id;
          IF version_status = 'FROZEN' THEN
            RAISE EXCEPTION 'assignments of a FROZEN dataset version are immutable'
              USING ERRCODE = '23514';
          END IF;

          SELECT clinical_identity_id, class_index, class_name
            INTO source_identity, source_class_index, source_class_name
          FROM dataset_source_records WHERE id = NEW.source_record_id;
          IF source_identity IS NULL OR source_identity IS DISTINCT FROM NEW.clinical_identity_id THEN
            RAISE EXCEPTION 'assignment clinical identity differs from source record identity'
              USING ERRCODE = '23514';
          END IF;
          IF source_class_index IS DISTINCT FROM NEW.class_index
             OR source_class_name IS DISTINCT FROM NEW.class_name THEN
            RAISE EXCEPTION 'assignment class differs from source record class'
              USING ERRCODE = '23514';
          END IF;

          PERFORM pg_advisory_xact_lock(
            hashtextextended(NEW.dataset_version_id::text || ':' || NEW.clinical_identity_id::text, 0)
          );
          SELECT split_name INTO conflicting_split
          FROM dataset_split_assignments
          WHERE dataset_version_id = NEW.dataset_version_id
            AND clinical_identity_id = NEW.clinical_identity_id
            AND id IS DISTINCT FROM NEW.id
            AND split_name <> NEW.split_name
          LIMIT 1;
          IF conflicting_split IS NOT NULL THEN
            RAISE EXCEPTION 'patient is already assigned to split % in this dataset version', conflicting_split
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_dataset_assignment_consistency
          BEFORE INSERT OR UPDATE ON dataset_split_assignments
          FOR EACH ROW EXECUTE FUNCTION enforce_dataset_assignment_consistency();

        CREATE FUNCTION protect_frozen_dataset_assignments()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE version_id UUID; version_status TEXT;
        BEGIN
          version_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.dataset_version_id ELSE NEW.dataset_version_id END;
          SELECT status INTO version_status FROM dataset_versions WHERE id = version_id;
          IF version_status = 'FROZEN' THEN
            RAISE EXCEPTION 'assignments of a FROZEN dataset version are immutable'
              USING ERRCODE = '23514';
          END IF;
          RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END;
        $$;

        CREATE TRIGGER trg_protect_frozen_dataset_assignments_delete
          BEFORE DELETE ON dataset_split_assignments
          FOR EACH ROW EXECUTE FUNCTION protect_frozen_dataset_assignments();

        CREATE FUNCTION enforce_dataset_version_lifecycle()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.status = 'FROZEN' AND (
            NEW.name IS DISTINCT FROM OLD.name OR
            NEW.semantic_version IS DISTINCT FROM OLD.semantic_version OR
            NEW.grouping_strategy IS DISTINCT FROM OLD.grouping_strategy OR
            NEW.grouping_field IS DISTINCT FROM OLD.grouping_field OR
            NEW.stratification_strategy IS DISTINCT FROM OLD.stratification_strategy OR
            NEW.split_algorithm IS DISTINCT FROM OLD.split_algorithm OR
            NEW.split_algorithm_version IS DISTINCT FROM OLD.split_algorithm_version OR
            NEW.random_seed IS DISTINCT FROM OLD.random_seed OR
            NEW.target_train_ratio IS DISTINCT FROM OLD.target_train_ratio OR
            NEW.target_val_ratio IS DISTINCT FROM OLD.target_val_ratio OR
            NEW.target_test_ratio IS DISTINCT FROM OLD.target_test_ratio OR
            NEW.positive_class IS DISTINCT FROM OLD.positive_class OR
            NEW.class_mapping IS DISTINCT FROM OLD.class_mapping OR
            NEW.source_record_count IS DISTINCT FROM OLD.source_record_count OR
            NEW.methodology_json IS DISTINCT FROM OLD.methodology_json
          ) THEN
            RAISE EXCEPTION 'scientific fields of a FROZEN dataset version are immutable'
              USING ERRCODE = '23514';
          END IF;

          IF NEW.status IS DISTINCT FROM OLD.status THEN
            IF NOT (
              (OLD.status = 'DRAFT' AND NEW.status IN ('GENERATED','ARCHIVED')) OR
              (OLD.status = 'GENERATED' AND NEW.status IN ('VALIDATED','ARCHIVED')) OR
              (OLD.status = 'VALIDATED' AND NEW.status IN ('FROZEN','ARCHIVED')) OR
              (OLD.status = 'FROZEN' AND NEW.status = 'ARCHIVED')
            ) THEN
              RAISE EXCEPTION 'invalid dataset version lifecycle transition: % -> %', OLD.status, NEW.status
                USING ERRCODE = '23514';
            END IF;
            IF NEW.status = 'GENERATED' THEN NEW.generated_at := COALESCE(NEW.generated_at, now()); END IF;
            IF NEW.status = 'VALIDATED' THEN NEW.validated_at := COALESCE(NEW.validated_at, now()); END IF;
            IF NEW.status = 'FROZEN' THEN NEW.frozen_at := COALESCE(NEW.frozen_at, now()); END IF;
            IF NEW.status = 'ARCHIVED' THEN NEW.archived_at := COALESCE(NEW.archived_at, now()); END IF;
          END IF;
          RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_dataset_version_lifecycle
          BEFORE UPDATE ON dataset_versions
          FOR EACH ROW EXECUTE FUNCTION enforce_dataset_version_lifecycle();

        CREATE FUNCTION protect_frozen_dataset_version_sources()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE old_status TEXT; new_status TEXT;
        BEGIN
          IF TG_OP <> 'INSERT' THEN
            SELECT status INTO old_status FROM dataset_versions WHERE id = OLD.dataset_version_id;
          END IF;
          IF TG_OP <> 'DELETE' THEN
            SELECT status INTO new_status FROM dataset_versions WHERE id = NEW.dataset_version_id;
          END IF;
          IF old_status = 'FROZEN' OR new_status = 'FROZEN' THEN
            RAISE EXCEPTION 'source composition of a FROZEN dataset version is immutable'
              USING ERRCODE = '23514';
          END IF;
          RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END;
        $$;

        CREATE TRIGGER trg_protect_frozen_dataset_version_sources
          BEFORE INSERT OR UPDATE OR DELETE ON dataset_version_sources
          FOR EACH ROW EXECUTE FUNCTION protect_frozen_dataset_version_sources();

        CREATE FUNCTION enforce_activation_materialization_consistency()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE materialization_version UUID;
        BEGIN
          SELECT dataset_version_id INTO materialization_version
          FROM dataset_materializations WHERE id = NEW.materialization_id;
          IF materialization_version IS DISTINCT FROM NEW.dataset_version_id THEN
            RAISE EXCEPTION 'activation version differs from materialization version'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_activation_materialization_consistency
          BEFORE INSERT OR UPDATE ON dataset_materialization_activations
          FOR EACH ROW EXECUTE FUNCTION enforce_activation_materialization_consistency();
        """
    )


def downgrade():
    raise RuntimeError(
        "Downgrade is intentionally prohibited for scientific lineage migrations"
    )
