-- REPRESENT: governed embeddings (global average pooling) of an EVALUATE population, with PCA/UMAP projections.
-- Same identity, attempt and fencing rules as EVALUATE/EXPLAIN; binaries stay outside PostgreSQL.
-- Applied as capstone_v2_migrator, like explain_host_executor.sql; the runtime role only reads and writes rows.
SET ROLE capstone_v2_migrator;
BEGIN;

ALTER TABLE public.assessment_identities DROP CONSTRAINT assessment_identities_kind_check;
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_kind_check
  CHECK (kind = ANY (ARRAY['evaluate'::text, 'explain'::text, 'represent'::text]));
-- Only a REPRESENT identity carries a representation specification (keeps historical hashes unchanged).
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_representation_check
  CHECK ((kind = 'represent') = coalesce(jsonb_typeof(identity->'representation') = 'object', false));

CREATE OR REPLACE FUNCTION public.assessment_result_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE a record; i jsonb; sample jsonb;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'ASSESSMENT_RESULT_IMMUTABLE'; END IF;
 SELECT * INTO a FROM assessment_attempts WHERE id=NEW.attempt_id FOR UPDATE;
 IF a.state IS DISTINCT FROM 'active' OR a.owner::text IS DISTINCT FROM current_setting('capstone.assessment_owner',true)
 THEN RAISE EXCEPTION 'ASSESSMENT_OWNER_FENCED'; END IF;
 IF NOT EXISTS (SELECT 1 FROM assessment_identities i, jsonb_array_elements(i.identity->'samples') s
 WHERE i.id=a.identity_id AND s->>'sample_id'=NEW.sample_id::text) THEN RAISE EXCEPTION 'ASSESSMENT_SAMPLE_CONFLICT'; END IF;
 SELECT identity INTO i FROM assessment_identities WHERE id=a.identity_id;
 SELECT s INTO sample FROM jsonb_array_elements(i->'samples') s WHERE s->>'sample_id'=NEW.sample_id::text;
 IF TG_TABLE_NAME='assessment_results' THEN
   IF NEW.payload->>'patient_id' IS DISTINCT FROM sample->>'patient_id' THEN RAISE EXCEPTION 'ASSESSMENT_PATIENT_CONFLICT'; END IF;
   IF i->>'kind'='evaluate' THEN
    IF NEW.payload->'label' IS DISTINCT FROM sample->'label'
      OR jsonb_typeof(NEW.payload->'raw_score') IS DISTINCT FROM 'number'
      OR NOT ((NEW.payload->>'raw_score')::numeric BETWEEN 0 AND 1)
      OR NEW.payload->'calibrated_score' IS DISTINCT FROM 'null'::jsonb
      OR NEW.payload->'threshold' IS DISTINCT FROM i->'decision'->'effective'
      OR NEW.payload->'predicted' IS DISTINCT FROM to_jsonb(CASE WHEN (NEW.payload->>'raw_score')::numeric >= (i->'decision'->>'effective')::numeric THEN 1 ELSE 0 END)
    THEN RAISE EXCEPTION 'ASSESSMENT_PREDICTION_CONFLICT'; END IF;
   ELSIF i->>'kind'='represent' THEN
    IF NEW.payload->'specification' IS DISTINCT FROM i->'representation'
      OR NEW.payload->'label' IS DISTINCT FROM sample->'label'
      OR jsonb_typeof(NEW.payload->'result'->'row') IS DISTINCT FROM 'number'
      OR jsonb_typeof(NEW.payload->'result'->'raw_score') IS DISTINCT FROM 'number'
      OR NOT ((NEW.payload->'result'->>'raw_score')::numeric BETWEEN 0 AND 1)
      OR NEW.payload->'result'->'predicted' IS DISTINCT FROM to_jsonb(CASE WHEN (NEW.payload->'result'->>'raw_score')::numeric >= (i->'decision'->>'effective')::numeric THEN 1 ELSE 0 END)
    THEN RAISE EXCEPTION 'ASSESSMENT_REPRESENTATION_CONFLICT'; END IF;
   ELSE
    IF NEW.payload->'specification' IS DISTINCT FROM i->'explanation'
      OR NEW.payload->'result'->>'score_explained' IS DISTINCT FROM 'raw'
    THEN RAISE EXCEPTION 'ASSESSMENT_EXPLANATION_CONFLICT'; END IF;
   END IF;
 ELSIF i->>'kind'='represent' THEN
   -- Population matrices (embeddings, projections) are attached to the first sample of the ordered population.
   IF NEW.role NOT IN ('embeddings','pca','pca_variance','umap')
     OR NEW.sample_id::text IS DISTINCT FROM (SELECT min((s->>'sample_id') COLLATE "C") FROM jsonb_array_elements(i->'samples') s)
   THEN RAISE EXCEPTION 'ASSESSMENT_REPRESENTATION_ARTIFACT_CONFLICT'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.assessment_attempt_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE i record; n integer;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'ASSESSMENT_HISTORY_IMMUTABLE'; END IF;
 SELECT * INTO i FROM assessment_identities WHERE id=NEW.identity_id FOR UPDATE;
 IF TG_OP='INSERT' THEN
  IF NEW.state<>'active' OR NEW.verification IS NOT NULL THEN RAISE EXCEPTION 'ASSESSMENT_INVALID_START'; END IF;
 ELSE
  IF OLD.state<>'active' OR OLD.owner::text IS DISTINCT FROM current_setting('capstone.assessment_owner',true)
    OR (to_jsonb(NEW)-ARRAY['state','cause','verification','finished_at']) IS DISTINCT FROM
       (to_jsonb(OLD)-ARRAY['state','cause','verification','finished_at'])
    OR NEW.state NOT IN ('verified','failed','interrupted') THEN RAISE EXCEPTION 'ASSESSMENT_OWNER_FENCED'; END IF;
  IF NEW.state='verified' THEN
   SELECT count(*) INTO n FROM assessment_results WHERE attempt_id=NEW.id;
   IF n IS DISTINCT FROM jsonb_array_length(i.identity->'samples')
     OR (NEW.verification->>'count')::integer IS DISTINCT FROM n
     OR coalesce(NEW.verification->>'sha256','') !~ '^[a-f0-9]{64}$'
     OR (i.kind='explain' AND (SELECT count(*) FROM assessment_artifacts WHERE attempt_id=NEW.id)<>2*n)
     OR (i.kind='represent' AND (SELECT count(*) FROM assessment_artifacts WHERE attempt_id=NEW.id)<>4)
   THEN RAISE EXCEPTION 'ASSESSMENT_INCOMPLETE'; END IF;
  END IF;
 END IF;
 RETURN NEW;
END $$;

COMMIT;
