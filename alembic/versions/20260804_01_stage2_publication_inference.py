"""Decouple Stage 2 publications from deployment-backed inference identity."""

from alembic import op


revision = "20260804_01"
down_revision = "20260728_03"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        DROP INDEX uq_cell_classification_runs_equivalent_active;

        ALTER TABLE cell_classification_runs
          ALTER COLUMN production_model_id DROP NOT NULL;

        CREATE UNIQUE INDEX uq_cell_classification_runs_equivalent_active
          ON cell_classification_runs(
            detection_run_id,
            COALESCE(model_snapshot->>'schema_version', ''),
            COALESCE(production_model_id, stage2_publication_id),
            stage2_publication_id,
            model_registry_id,
            COALESCE(model_version, ''),
            COALESCE(
              model_snapshot#>>'{calibration_metadata,threshold_calibration_id}',
              ''
            ),
            md5(model_snapshot::text),
            input_manifest_sha256
          )
          WHERE status IN (
            'created','processing','completed','completed_with_warnings'
          );

        CREATE INDEX ix_cell_classification_runs_publication_created
          ON cell_classification_runs(
            stage2_publication_id,created_at DESC,id DESC
          );

        COMMENT ON COLUMN cell_classification_runs.production_model_id IS
          'Legacy deployment identity for schema-v1 snapshots; NULL for publication-first Stage 2 inference.';

        CREATE OR REPLACE FUNCTION validate_cell_classification_run_snapshot()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
          snapshot JSONB := NEW.model_snapshot;
          snapshot_version TEXT := snapshot->>'schema_version';
          published_threshold DOUBLE PRECISION;
          published_review_margin DOUBLE PRECISION;
        BEGIN
          IF snapshot_version = '1' THEN
            IF NEW.production_model_id IS NULL
              OR snapshot->>'production_model_id'
                IS DISTINCT FROM NEW.production_model_id::text
              OR jsonb_typeof(snapshot->'stage2_default')
                IS DISTINCT FROM 'object'
              OR snapshot#>>'{stage2_default,environment}'
                IS DISTINCT FROM 'stage2'
              OR snapshot#>>'{stage2_default,alias}'
                IS DISTINCT FROM 'default'
              OR snapshot#>>'{stage2_default,deployment_id}'
                IS DISTINCT FROM NEW.production_model_id::text
            THEN
              RAISE EXCEPTION
                'legacy model snapshot deployment identity is invalid'
                USING ERRCODE = '23514';
            END IF;
          ELSIF snapshot_version = '2' THEN
            IF NEW.production_model_id IS NOT NULL
              OR snapshot ? 'production_model_id'
              OR jsonb_typeof(snapshot->'stage2_publication')
                IS DISTINCT FROM 'object'
              OR snapshot#>>'{stage2_publication,publication_id}'
                IS DISTINCT FROM NEW.stage2_publication_id::text
              OR snapshot#>>'{stage2_publication,scope}'
                IS DISTINCT FROM 'stage2'
            THEN
              RAISE EXCEPTION
                'publication-first model snapshot identity is invalid'
                USING ERRCODE = '23514';
            END IF;
          ELSE
            RAISE EXCEPTION 'unsupported model snapshot schema_version'
              USING ERRCODE = '23514';
          END IF;

          IF jsonb_typeof(snapshot) IS DISTINCT FROM 'object'
            OR snapshot->>'stage2_publication_id'
              IS DISTINCT FROM NEW.stage2_publication_id::text
            OR snapshot->>'model_registry_id'
              IS DISTINCT FROM NEW.model_registry_id::text
            OR snapshot->>'model_name' IS DISTINCT FROM NEW.model_name
            OR snapshot->>'model_version' IS DISTINCT FROM NEW.model_version
            OR snapshot->>'positive_label' IS DISTINCT FROM 'parasitized'
            OR snapshot->>'positive_class_index' IS DISTINCT FROM '1'
            OR snapshot->>'production_status' IS DISTINCT FROM 'active'
            OR snapshot->>'checkpoint_sha256' IS NULL
            OR snapshot->>'checkpoint_sha256' !~ '^[0-9a-f]{64}$'
            OR COALESCE(snapshot->>'checkpoint_size_bytes','')
              !~ '^[1-9][0-9]*$'
            OR snapshot->>'loader_version' IS NULL
            OR btrim(snapshot->>'loader_version') = ''
            OR snapshot->>'inference_version' IS NULL
            OR btrim(snapshot->>'inference_version') = ''
            OR snapshot->>'threshold_source' IS NULL
            OR btrim(snapshot->>'threshold_source') = ''
            OR jsonb_typeof(snapshot->'preprocessing') IS DISTINCT FROM 'object'
            OR jsonb_typeof(snapshot->'input_signature') IS DISTINCT FROM 'object'
            OR jsonb_typeof(snapshot->'output_signature') IS DISTINCT FROM 'object'
            OR jsonb_typeof(snapshot->'calibration_metadata')
              IS DISTINCT FROM 'object'
            OR jsonb_typeof(snapshot->'explainability_policy')
              IS DISTINCT FROM 'object'
            OR jsonb_typeof(snapshot->'label_mapping') IS DISTINCT FROM 'object'
            OR NOT (
              snapshot->'label_mapping' @>
                '{
                  "0":"uninfected",
                  "1":"parasitized",
                  "positive_class": 1,
                  "positive_label":"parasitized"
                }'::jsonb
            )
            OR snapshot#>>'{explainability_policy,version}'
              IS DISTINCT FROM 'cell-gradcam-manual-v1'
            OR snapshot#>>'{explainability_policy,method}'
              IS DISTINCT FROM 'gradcam'
            OR snapshot#>>'{explainability_policy,scope}'
              IS DISTINCT FROM 'single_cell_on_demand'
            OR snapshot#>>'{explainability_policy,automatic_generation}'
              IS DISTINCT FROM 'false'
            OR snapshot#>>'{explainability_policy,manual_retry_required}'
              IS DISTINCT FROM 'true'
            OR snapshot#>>'{explainability_policy,bulk_generation}'
              IS DISTINCT FROM 'false'
            OR COALESCE(snapshot->>'source_training_run_id','')
              !~ '^[0-9a-f-]{36}$'
            OR COALESCE(snapshot->>'source_evaluation_run_id','')
              !~ '^[0-9a-f-]{36}$'
            OR COALESCE(snapshot->>'checkpoint_artifact_id','')
              !~ '^[0-9a-f-]{36}$'
            OR COALESCE(snapshot->>'batch_size','') !~ '^[1-9][0-9]*$'
            OR COALESCE(snapshot->>'input_width','') !~ '^[1-9][0-9]*$'
            OR COALESCE(snapshot->>'input_height','') !~ '^[1-9][0-9]*$'
            OR COALESCE(snapshot->>'input_channels','') !~ '^[1-9][0-9]*$'
          THEN
            RAISE EXCEPTION
              'model snapshot identity or required contract is invalid'
              USING ERRCODE = '23514';
          END IF;

          IF jsonb_typeof(snapshot->'threshold') IS DISTINCT FROM 'number'
            OR jsonb_typeof(snapshot->'review_margin') IS DISTINCT FROM 'number'
          THEN
            RAISE EXCEPTION 'model snapshot numeric policy is invalid'
              USING ERRCODE = '23514';
          END IF;
          published_threshold := (snapshot->>'threshold')::DOUBLE PRECISION;
          published_review_margin :=
            (snapshot->>'review_margin')::DOUBLE PRECISION;
          IF published_threshold < 0 OR published_threshold > 1
            OR published_review_margin < 0 OR published_review_margin > 1
          THEN
            RAISE EXCEPTION
              'model snapshot numeric policy is outside allowed bounds'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END;
        $$;
        """
    )


def downgrade():
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM cell_classification_runs
            WHERE production_model_id IS NULL
          ) THEN
            RAISE EXCEPTION
              'cannot restore deployment-only identity while schema-v2 runs exist';
          END IF;
        END;
        $$;

        DROP INDEX ix_cell_classification_runs_publication_created;
        DROP INDEX uq_cell_classification_runs_equivalent_active;

        CREATE UNIQUE INDEX uq_cell_classification_runs_equivalent_active
          ON cell_classification_runs(
            detection_run_id,
            production_model_id,
            COALESCE(model_version, ''),
            COALESCE(model_snapshot->>'checkpoint_sha256', ''),
            COALESCE(model_snapshot->>'inference_version', ''),
            input_manifest_sha256
          )
          WHERE status IN (
            'created','processing','completed','completed_with_warnings'
          );

        ALTER TABLE cell_classification_runs
          ALTER COLUMN production_model_id SET NOT NULL;

        COMMENT ON COLUMN cell_classification_runs.production_model_id IS NULL;

        CREATE OR REPLACE FUNCTION validate_cell_classification_run_snapshot()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
          snapshot JSONB := NEW.model_snapshot;
          published_threshold DOUBLE PRECISION;
          published_review_margin DOUBLE PRECISION;
        BEGIN
          IF jsonb_typeof(snapshot) IS DISTINCT FROM 'object'
            OR snapshot->>'schema_version' IS DISTINCT FROM '1'
            OR snapshot->>'production_model_id'
              IS DISTINCT FROM NEW.production_model_id::text
            OR snapshot->>'stage2_publication_id'
              IS DISTINCT FROM NEW.stage2_publication_id::text
            OR snapshot->>'model_registry_id'
              IS DISTINCT FROM NEW.model_registry_id::text
            OR snapshot->>'model_name' IS DISTINCT FROM NEW.model_name
            OR snapshot->>'model_version' IS DISTINCT FROM NEW.model_version
            OR snapshot->>'positive_label' IS DISTINCT FROM 'parasitized'
            OR snapshot->>'positive_class_index' IS DISTINCT FROM '1'
            OR snapshot->>'production_status' IS DISTINCT FROM 'active'
            OR snapshot->>'checkpoint_sha256' IS NULL
            OR snapshot->>'checkpoint_sha256' !~ '^[0-9a-f]{64}$'
            OR COALESCE(snapshot->>'checkpoint_size_bytes','')
              !~ '^[1-9][0-9]*$'
            OR snapshot->>'loader_version' IS NULL
            OR btrim(snapshot->>'loader_version') = ''
            OR snapshot->>'inference_version' IS NULL
            OR btrim(snapshot->>'inference_version') = ''
            OR snapshot->>'threshold_source' IS NULL
            OR btrim(snapshot->>'threshold_source') = ''
            OR jsonb_typeof(snapshot->'preprocessing') IS DISTINCT FROM 'object'
            OR jsonb_typeof(snapshot->'input_signature') IS DISTINCT FROM 'object'
            OR jsonb_typeof(snapshot->'output_signature') IS DISTINCT FROM 'object'
            OR jsonb_typeof(snapshot->'calibration_metadata')
              IS DISTINCT FROM 'object'
            OR jsonb_typeof(snapshot->'stage2_default') IS DISTINCT FROM 'object'
            OR jsonb_typeof(snapshot->'explainability_policy')
              IS DISTINCT FROM 'object'
            OR jsonb_typeof(snapshot->'label_mapping') IS DISTINCT FROM 'object'
            OR NOT (
              snapshot->'label_mapping' @>
                '{
                  "0":"uninfected",
                  "1":"parasitized",
                  "positive_class": 1,
                  "positive_label":"parasitized"
                }'::jsonb
            )
            OR snapshot#>>'{stage2_default,environment}'
              IS DISTINCT FROM 'stage2'
            OR snapshot#>>'{stage2_default,alias}'
              IS DISTINCT FROM 'default'
            OR snapshot#>>'{stage2_default,deployment_id}'
              IS DISTINCT FROM NEW.production_model_id::text
            OR snapshot#>>'{explainability_policy,version}'
              IS DISTINCT FROM 'cell-gradcam-manual-v1'
            OR snapshot#>>'{explainability_policy,method}'
              IS DISTINCT FROM 'gradcam'
            OR snapshot#>>'{explainability_policy,scope}'
              IS DISTINCT FROM 'single_cell_on_demand'
            OR snapshot#>>'{explainability_policy,automatic_generation}'
              IS DISTINCT FROM 'false'
            OR snapshot#>>'{explainability_policy,manual_retry_required}'
              IS DISTINCT FROM 'true'
            OR snapshot#>>'{explainability_policy,bulk_generation}'
              IS DISTINCT FROM 'false'
            OR COALESCE(snapshot->>'source_training_run_id','')
              !~ '^[0-9a-f-]{36}$'
            OR COALESCE(snapshot->>'source_evaluation_run_id','')
              !~ '^[0-9a-f-]{36}$'
            OR COALESCE(snapshot->>'checkpoint_artifact_id','')
              !~ '^[0-9a-f-]{36}$'
            OR COALESCE(snapshot->>'batch_size','') !~ '^[1-9][0-9]*$'
            OR COALESCE(snapshot->>'input_width','') !~ '^[1-9][0-9]*$'
            OR COALESCE(snapshot->>'input_height','') !~ '^[1-9][0-9]*$'
            OR COALESCE(snapshot->>'input_channels','') !~ '^[1-9][0-9]*$'
          THEN
            RAISE EXCEPTION
              'model snapshot identity or required contract is invalid'
              USING ERRCODE = '23514';
          END IF;
          IF jsonb_typeof(snapshot->'threshold') IS DISTINCT FROM 'number'
            OR jsonb_typeof(snapshot->'review_margin') IS DISTINCT FROM 'number'
          THEN
            RAISE EXCEPTION 'model snapshot numeric policy is invalid'
              USING ERRCODE = '23514';
          END IF;
          published_threshold := (snapshot->>'threshold')::DOUBLE PRECISION;
          published_review_margin :=
            (snapshot->>'review_margin')::DOUBLE PRECISION;
          IF published_threshold < 0 OR published_threshold > 1
            OR published_review_margin < 0 OR published_review_margin > 1
          THEN
            RAISE EXCEPTION
              'model snapshot numeric policy is outside allowed bounds'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END;
        $$;
        """
    )
