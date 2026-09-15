BEGIN;

-- Running upgrade 20260912_02 -> 20260914_01

CREATE TABLE campaign_technical_revisions (
 id uuid PRIMARY KEY, campaign_id uuid NOT NULL REFERENCES experimental_campaigns(id),
 payload jsonb NOT NULL, canonical_payload text NOT NULL, payload_hash text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(), UNIQUE(campaign_id,id),
 CHECK(payload_hash ~ '^[a-f0-9]{64}$'),
 CHECK(canonical_payload::jsonb=payload),
 CHECK(encode(sha256(convert_to(canonical_payload,'UTF8')),'hex')=payload_hash)
);
ALTER TABLE runs ADD COLUMN campaign_id uuid REFERENCES experimental_campaigns(id);
CREATE TABLE campaign_controlled_requests (
 id uuid PRIMARY KEY, campaign_id uuid NOT NULL REFERENCES experimental_campaigns(id),
 member_id uuid NOT NULL REFERENCES campaign_members(id),
 revision_id uuid NOT NULL, previous_attempt_id uuid NOT NULL UNIQUE REFERENCES campaign_attempts(id),
 attempt_id uuid NOT NULL UNIQUE REFERENCES campaign_attempts(id) DEFERRABLE INITIALLY DEFERRED,
 run_id uuid NOT NULL UNIQUE REFERENCES runs(id) DEFERRABLE INITIALLY DEFERRED,
 reason text NOT NULL CHECK(length(trim(reason))>0),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(campaign_id,revision_id) REFERENCES campaign_technical_revisions(campaign_id,id)
);
CREATE FUNCTION campaign_technical_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE c record; m record; a record; e jsonb;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'TECHNICAL_HISTORY_IMMUTABLE'; END IF;
 SELECT * INTO c FROM experimental_campaigns WHERE id=NEW.campaign_id FOR UPDATE;
 IF c.state IS DISTINCT FROM 'paused' THEN RAISE EXCEPTION 'PAUSED_CAMPAIGN_REQUIRED'; END IF;
 IF TG_TABLE_NAME='campaign_technical_revisions' THEN
  IF (NEW.payload-ARRAY['original_environment','environment','contract_hash','reason','files','tests','authorization'])<>'{}'::jsonb OR NOT campaign_json_object(NEW.payload,ARRAY['original_environment','environment','contract_hash','reason','files','tests','authorization'])
   OR NEW.payload->'original_environment' IS DISTINCT FROM c.environment
   OR NEW.payload->>'contract_hash' IS DISTINCT FROM c.contract_hash
   OR jsonb_typeof(NEW.payload->'files') IS DISTINCT FROM 'object'
   OR NEW.payload->'files'='{}'::jsonb
   OR EXISTS(SELECT 1 FROM jsonb_each(NEW.payload->'files') f WHERE jsonb_typeof(f.value) IS DISTINCT FROM 'string' OR (f.value#>>'{}') !~ '^[a-f0-9]{64}$')
   OR jsonb_typeof(NEW.payload->'tests') IS DISTINCT FROM 'array'
   OR jsonb_array_length(NEW.payload->'tests')=0
   OR coalesce(length(trim(NEW.payload->>'reason')),0)=0
   OR coalesce(length(trim(NEW.payload->>'authorization')),0)=0
  THEN RAISE EXCEPTION 'TECHNICAL_REVISION_INVALID'; END IF;
  e=NEW.payload->'environment';
  IF jsonb_typeof(e) IS DISTINCT FROM 'object' OR coalesce(e->>'source_sha256','') !~ '^[a-f0-9]{64}$'
    OR (e-ARRAY['source_sha256','git_commit']) IS DISTINCT FROM (c.environment-ARRAY['source_sha256','git_commit'])
  THEN RAISE EXCEPTION 'TECHNICAL_ENVIRONMENT_CONFLICT'; END IF;
 ELSE
  SELECT * INTO m FROM campaign_members WHERE id=NEW.member_id FOR UPDATE;
  SELECT * INTO a FROM campaign_attempts WHERE id=NEW.previous_attempt_id;
  IF m.campaign_id IS DISTINCT FROM c.id OR a.member_id IS DISTINCT FROM m.id
   OR a.state NOT IN ('failed','interrupted') OR m.state NOT IN ('failed','interrupted')
   OR EXISTS(SELECT 1 FROM campaign_attempts a0 JOIN campaign_members m0 ON m0.id=a0.member_id
             WHERE m0.campaign_id=c.id AND a0.state IN ('active','completed'))
  THEN RAISE EXCEPTION 'CONTROLLED_ATTEMPT_INELIGIBLE'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER technical_revision_guard BEFORE INSERT OR UPDATE OR DELETE ON campaign_technical_revisions FOR EACH ROW EXECUTE FUNCTION campaign_technical_guard();
CREATE TRIGGER controlled_request_guard BEFORE INSERT OR UPDATE OR DELETE ON campaign_controlled_requests FOR EACH ROW EXECUTE FUNCTION campaign_technical_guard();
CREATE FUNCTION controlled_run_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE q record;
BEGIN
 SELECT * INTO q FROM campaign_controlled_requests WHERE run_id=NEW.id;
 IF FOUND AND NEW.campaign_id IS DISTINCT FROM q.campaign_id THEN RAISE EXCEPTION 'CONTROLLED_CAMPAIGN_ID_REQUIRED'; END IF;
 IF TG_OP='UPDATE' AND NEW.campaign_id IS DISTINCT FROM OLD.campaign_id THEN RAISE EXCEPTION 'RUN_CAMPAIGN_IMMUTABLE'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER controlled_run_guard BEFORE INSERT OR UPDATE ON runs FOR EACH ROW EXECUTE FUNCTION controlled_run_guard();

CREATE FUNCTION controlled_binding_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM campaign_attempts a JOIN train_execution_sessions s ON s.attempt_id=a.id
 JOIN campaign_technical_revisions v ON v.id=NEW.revision_id JOIN runs r ON r.id=NEW.run_id
 WHERE a.id=NEW.attempt_id AND a.member_id=NEW.member_id AND a.training_run_id=NEW.run_id
 AND s.run_id=NEW.run_id AND r.campaign_id=NEW.campaign_id AND s.environment=v.payload->'environment'
 AND s.configuration IS NOT DISTINCT FROM r.execution_parameters->'model_configuration_e2'->'configuration'
 AND s.dataset IS NOT DISTINCT FROM r.execution_parameters->'model_configuration_e2'->'dataset')
 THEN RAISE EXCEPTION 'CONTROLLED_BINDING_INVALID'; END IF;
 RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER controlled_binding_guard AFTER INSERT ON campaign_controlled_requests DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION controlled_binding_guard();
CREATE FUNCTION controlled_pause_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.state IS DISTINCT FROM 'paused' AND EXISTS(
  SELECT 1 FROM campaign_controlled_requests q JOIN campaign_attempts a ON a.id=q.attempt_id
  WHERE q.campaign_id=NEW.id AND a.state IN ('active','completed'))
 THEN RAISE EXCEPTION 'CONTROLLED_TRAIN_REQUIRES_PAUSED'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER controlled_pause_guard BEFORE UPDATE ON experimental_campaigns FOR EACH ROW EXECUTE FUNCTION controlled_pause_guard();
CREATE OR REPLACE FUNCTION campaign_attempt_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE m record; c record; r record; cfg jsonb; rcfg jsonb; maximum integer; technical jsonb;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'ATTEMPT_HISTORY_IMMUTABLE'; END IF;
 -- Campaign lock first, shared with planning and members; then member serialization.
 SELECT c0.* INTO c FROM experimental_campaigns c0 JOIN campaign_members m0 ON m0.campaign_id=c0.id WHERE m0.id=NEW.member_id FOR UPDATE OF c0;
 SELECT * INTO m FROM campaign_members WHERE id=NEW.member_id FOR UPDATE;
 IF m.id IS NULL OR c.state NOT IN ('frozen','active','paused') THEN RAISE EXCEPTION 'ATTEMPT_REQUIRES_FROZEN_CAMPAIGN'; END IF;
 SELECT v.payload->'environment' INTO technical FROM campaign_controlled_requests q JOIN campaign_technical_revisions v ON v.id=q.revision_id WHERE q.attempt_id=NEW.id AND q.campaign_id=c.id AND q.member_id=NEW.member_id;
 IF TG_OP='INSERT' THEN
   SELECT coalesce(max(ordinal),0)+1 INTO maximum FROM campaign_attempts WHERE member_id=NEW.member_id;
   IF (c.state='paused' AND technical IS NULL) OR NEW.state<>'active' OR m.state NOT IN ('pending','failed','interrupted')
      OR NEW.ordinal<>maximum OR NEW.ordinal>(c.protocol->'budget'->>'max_attempts_per_member')::int
      THEN RAISE EXCEPTION 'INVALID_NEW_ATTEMPT'; END IF;
 ELSE
   IF NEW.id<>OLD.id OR NEW.member_id<>OLD.member_id OR NEW.ordinal<>OLD.ordinal OR NEW.started_at<>OLD.started_at
     OR (OLD.training_run_id IS NOT NULL AND NEW.training_run_id IS DISTINCT FROM OLD.training_run_id)
     THEN RAISE EXCEPTION 'ATTEMPT_IDENTITY_IMMUTABLE'; END IF;
   IF NOT ((OLD.state='active' AND NEW.state IN ('active','failed','interrupted','completed')) OR (OLD.state='completed' AND NEW.state='verified')) THEN RAISE EXCEPTION 'INVALID_ATTEMPT_TRANSITION'; END IF;
 END IF;
 IF NEW.state='verified' AND NOT EXISTS(SELECT 1 FROM train_execution_sessions WHERE run_id=NEW.training_run_id AND state='verified') THEN RAISE EXCEPTION 'TRAIN_EVIDENCE_REQUIRED'; END IF;
 IF NEW.training_run_id IS NOT NULL THEN
   SELECT * INTO r FROM runs WHERE id=NEW.training_run_id FOR UPDATE;
   PERFORM 1 FROM models WHERE id=r.model_id FOR SHARE;
   IF NOT campaign_model_matches(NEW.training_run_id,NEW.member_id) THEN RAISE EXCEPTION 'TRAIN_RELATIONAL_MODEL_CONFLICT'; END IF;
   SELECT configuration INTO cfg FROM campaign_configurations WHERE campaign_id=m.campaign_id AND configuration_hash=m.configuration_hash;
   rcfg=r.execution_parameters->'model_configuration_e2'->'configuration';
   IF r.id IS NULL OR r.run_type<>'training' OR r.dataset_version_id IS DISTINCT FROM c.dataset_version_id
     OR (c.experiment_id IS NOT NULL AND r.experiment_id IS DISTINCT FROM c.experiment_id)
     OR r.random_seed IS DISTINCT FROM m.seed
     OR (rcfg->'resolved'->'execution'->>'seed') IS DISTINCT FROM m.seed::text
     OR (rcfg->>'model_id') IS DISTINCT FROM (cfg->>'model_id')
     OR (rcfg->>'adapter_version') IS DISTINCT FROM (cfg->>'adapter_version')
     OR (rcfg->>'schema_version') IS DISTINCT FROM (cfg->>'schema_version')
     OR (rcfg->'resolved' #- '{execution,seed}') IS DISTINCT FROM (cfg->'resolved')
     OR r.execution_parameters->'model_configuration_e2'->'dataset' IS DISTINCT FROM c.dataset_snapshot
     OR r.execution_parameters->'model_configuration_e2'->'environment'->>'source_sha256' IS DISTINCT FROM coalesce(technical,c.environment)->>'source_sha256'
     OR r.execution_parameters->'model_configuration_e2'->'environment'->'packages' IS DISTINCT FROM coalesce(technical,c.environment)->'packages'
     OR r.execution_parameters->'model_configuration_e2'->'environment'->>'python' IS DISTINCT FROM coalesce(technical,c.environment)->>'python'
     OR r.execution_parameters->'model_configuration_e2'->'environment'->>'tensorflow' IS DISTINCT FROM coalesce(technical,c.environment)->>'tensorflow'
     OR r.execution_parameters->'model_configuration_e2'->'environment'->'determinism_environment' IS DISTINCT FROM coalesce(technical,c.environment)->'determinism_environment'
     THEN RAISE EXCEPTION 'TRAIN_CAMPAIGN_CONTRACT_CONFLICT'; END IF;
 END IF;
 RETURN NEW;
END $$;;

ALTER FUNCTION campaign_technical_guard() SET search_path = public, pg_catalog;

ALTER FUNCTION controlled_run_guard() SET search_path = public, pg_catalog;

ALTER FUNCTION controlled_binding_guard() SET search_path = public, pg_catalog;

ALTER FUNCTION controlled_pause_guard() SET search_path = public, pg_catalog;

ALTER FUNCTION campaign_attempt_guard() SET search_path = public, pg_catalog;

UPDATE alembic_version SET version_num='20260914_01' WHERE alembic_version.version_num = '20260912_02';

COMMIT;

