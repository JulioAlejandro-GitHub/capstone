-- Operational activation may have no scientific evaluation yet.
-- Keep mutually exclusive evaluation references and all identity/ownership FKs.
BEGIN;
ALTER TABLE public.stage2_model_publications
    DROP CONSTRAINT ck_publication_evaluation_source;
ALTER TABLE public.stage2_model_publications
    ADD CONSTRAINT ck_publication_evaluation_source
    CHECK (num_nonnulls(evaluation_run_id, evaluation_attempt_id) <= 1);
ALTER TABLE public.stage2_model_publication_events
    DROP CONSTRAINT ck_publication_event_source;
ALTER TABLE public.stage2_model_publication_events
    ADD CONSTRAINT ck_publication_event_source
    CHECK (num_nonnulls(evaluation_run_id, evaluation_attempt_id) <= 1);
CREATE OR REPLACE FUNCTION public.validate_cell_classification_run_snapshot()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
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
        OR snapshot#>>'{stage2_default,environment}' IS DISTINCT FROM 'stage2'
        OR snapshot#>>'{stage2_default,alias}' IS DISTINCT FROM 'default'
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
        OR num_nonnulls(snapshot->>'source_evaluation_run_id',snapshot->>'source_evaluation_attempt_id')>1
        OR (COALESCE(snapshot->>'source_evaluation_run_id',snapshot->>'source_evaluation_attempt_id') IS NOT NULL
            AND COALESCE(snapshot->>'source_evaluation_run_id',snapshot->>'source_evaluation_attempt_id')
                !~ '^[0-9a-f-]{36}$')
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
        RAISE EXCEPTION
          'model snapshot numeric policy is invalid'
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

      IF NOT EXISTS(SELECT 1 FROM public.stage2_model_publications p WHERE p.id=NEW.stage2_publication_id
        AND p.training_run_id::text IS NOT DISTINCT FROM snapshot->>'source_training_run_id'
        AND p.evaluation_run_id::text IS NOT DISTINCT FROM snapshot->>'source_evaluation_run_id'
        AND p.evaluation_attempt_id::text IS NOT DISTINCT FROM snapshot->>'source_evaluation_attempt_id') THEN
        RAISE EXCEPTION 'CELL_SNAPSHOT_EVALUATION_MISMATCH' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END;
    $function$;
COMMIT;
