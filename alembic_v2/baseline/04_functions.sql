-- DBV2.2 + approved R1. Install exclusively via guarded Alembic v2.
CREATE OR REPLACE FUNCTION public.assessment_attempt_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE i record; n integer;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'ASSESSMENT_HISTORY_IMMUTABLE'; END IF;
 SELECT * INTO i FROM assessment_identities WHERE id=NEW.identity_id FOR UPDATE;
 IF TG_OP='INSERT' THEN
  IF NEW.state<>'active' OR NEW.verification IS NOT NULL THEN RAISE EXCEPTION 'ASSESSMENT_INVALID_START'; END IF;
  IF i.identity->>'purpose'='final' AND NOT EXISTS(SELECT 1 FROM assessment_final_locks l WHERE l.identity_hash=i.identity_hash
    AND l.evidence->'candidate'=i.identity->'model' AND l.evidence->'decision'=i.identity->'decision')
  THEN RAISE EXCEPTION 'TEST_FINAL_LOCK_REQUIRED'; END IF;
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
   THEN RAISE EXCEPTION 'ASSESSMENT_INCOMPLETE'; END IF;
  END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.assessment_consumer_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM campaign_members m JOIN campaign_attempts a ON a.id=m.accepted_attempt_id
 JOIN train_execution_sessions s ON s.run_id=a.training_run_id JOIN assessment_identities i ON i.id=NEW.identity_id
 WHERE m.id=NEW.member_id AND m.campaign_id=NEW.campaign_id AND a.member_id=m.id AND a.state='verified'
 AND s.state='verified' AND i.training_run_id=a.training_run_id AND i.identity->'dataset'=s.dataset
 AND i.identity->'model'->>'model_version_id'=s.verification->'artifact'->>'version_id'
 AND i.identity->'model'->>'sha256'=s.verification->'artifact'->>'sha256'
 AND i.identity->'model'->'bytes'=s.verification->'artifact'->'bytes'
 AND i.identity->'model'->>'path'=s.verification->'artifact'->>'path'
 AND i.identity->'model'->'input_contract'=s.configuration->'resolved'->'input_contract')
 THEN RAISE EXCEPTION 'ASSESSMENT_CAMPAIGN_CONFLICT'; END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.assessment_identity_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM runs WHERE id=NEW.training_run_id AND run_type='training')
 THEN RAISE EXCEPTION 'ASSESSMENT_TRAIN_REQUIRED'; END IF;
 IF jsonb_typeof(NEW.identity->'protocol') IS DISTINCT FROM 'object'
  OR NEW.identity->'protocol'->>'version' IS NULL
  OR NOT coalesce((NEW.identity->'protocol'->'splits') ? (NEW.identity->>'split'),false)
  OR NOT coalesce((NEW.identity->'protocol'->'purposes') ? (NEW.identity->>'purpose'),false)
  OR (SELECT count(*) FROM jsonb_array_elements(NEW.identity->'samples')) IS DISTINCT FROM
     (SELECT count(DISTINCT s->>'sample_id') FROM jsonb_array_elements(NEW.identity->'samples') s)
 THEN RAISE EXCEPTION 'ASSESSMENT_PROTOCOL_OR_SAMPLES_INVALID'; END IF;
 IF EXISTS(SELECT 1 FROM jsonb_array_elements(NEW.identity->'samples') s
   WHERE s->>'split' IS DISTINCT FROM NEW.identity->>'split'
      OR s->>'patient_id' IS NULL OR s->>'label' IS NULL OR s->>'label' NOT IN ('0','1')
      OR s->>'sha256' IS NULL OR s->>'sha256' !~ '^[a-f0-9]{64}$')
 THEN RAISE EXCEPTION 'ASSESSMENT_SAMPLE_INVALID'; END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.assessment_immutable() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
BEGIN RAISE EXCEPTION 'ASSESSMENT_HISTORY_IMMUTABLE'; END $$;

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
   ELSE
    IF NEW.payload->'specification' IS DISTINCT FROM i->'explanation'
      OR NEW.payload->'result'->>'score_explained' IS DISTINCT FROM 'raw'
    THEN RAISE EXCEPTION 'ASSESSMENT_EXPLANATION_CONFLICT'; END IF;
   END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.campaign_attempt_state() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
BEGIN
 UPDATE campaign_members SET state=NEW.state,
 accepted_attempt_id=CASE WHEN NEW.state='verified' THEN
   (SELECT id FROM campaign_attempts WHERE member_id=NEW.member_id AND state='verified' ORDER BY ordinal LIMIT 1)
   ELSE NULL END WHERE id=NEW.member_id;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.campaign_audit() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE before_value jsonb; after_value jsonb; event_id uuid;
BEGIN
 event_id=gen_random_uuid();
 IF TG_OP<>'INSERT' THEN before_value=to_jsonb(OLD); END IF;
 IF TG_OP<>'DELETE' THEN after_value=to_jsonb(NEW); END IF;
 INSERT INTO audit_events(id,event_type,action,resource_type,resource_id,request_method,request_path,correlation_id,
   actor_username_snapshot,before_state,after_state,metadata,success)
 VALUES(event_id,'ml.campaign.'||TG_TABLE_NAME,lower(TG_OP),TG_TABLE_NAME,
   coalesce(after_value->>'id',before_value->>'id',after_value->>'campaign_id',before_value->>'campaign_id'),
   'DB','campaigns.e4',event_id::text,current_user,before_value,after_value,'{}'::jsonb,true);
 RETURN coalesce(NEW,OLD);
END $$;

CREATE OR REPLACE FUNCTION public.campaign_catalog_identity_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
BEGIN
 IF NEW.name IS DISTINCT FROM OLD.name AND EXISTS(
   SELECT 1 FROM runs r JOIN campaign_attempts a ON a.training_run_id=r.id WHERE r.model_id=OLD.id)
 THEN RAISE EXCEPTION 'LINKED_MODEL_NAME_IMMUTABLE'; END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.campaign_configuration_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE state_value text;
BEGIN
 SELECT state INTO state_value FROM experimental_campaigns WHERE id=coalesce(NEW.campaign_id,OLD.campaign_id) FOR UPDATE;
 IF state_value IS DISTINCT FROM 'draft' THEN RAISE EXCEPTION 'FROZEN_CONFIGURATION_IMMUTABLE'; END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 IF TG_OP='UPDATE' AND (NEW.campaign_id<>OLD.campaign_id OR NEW.configuration_hash<>OLD.configuration_hash) THEN RAISE EXCEPTION 'CONFIGURATION_IDENTITY_IMMUTABLE'; END IF;
 IF NEW.canonical_configuration::jsonb IS DISTINCT FROM NEW.configuration
    OR encode(sha256(convert_to(NEW.canonical_configuration,'UTF8')),'hex')<>NEW.configuration_hash
    THEN RAISE EXCEPTION 'CONFIGURATION_HASH_CONFLICT'; END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.campaign_environment_identity(v jsonb) RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path TO 'public', 'pg_catalog' AS $$
 SELECT jsonb_build_object('source_sha256',v->'source_sha256','python',v->'python','tensorflow',v->'tensorflow',
                          'packages',v->'packages','determinism_environment',v->'determinism_environment')
$$;

CREATE OR REPLACE FUNCTION public.campaign_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE ev record; configs jsonb; members jsonb; p jsonb;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'CAMPAIGN_DELETE_FORBIDDEN'; END IF;
 IF TG_OP='UPDATE' THEN
   IF NEW.id<>OLD.id OR NEW.created_at<>OLD.created_at OR NEW.actor<>OLD.actor THEN RAISE EXCEPTION 'CAMPAIGN_IDENTITY_IMMUTABLE'; END IF;
   IF OLD.state<>'draft' AND (to_jsonb(NEW)-ARRAY['state','updated_at']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['state','updated_at'])
     THEN RAISE EXCEPTION 'FROZEN_CAMPAIGN_IMMUTABLE'; END IF;
   IF NEW.state<>OLD.state AND NOT (
     (OLD.state='draft' AND NEW.state='frozen') OR
     (OLD.state='frozen' AND NEW.state IN ('active','paused')) OR
     (OLD.state='active' AND NEW.state IN ('paused','finalized')) OR
     (OLD.state='paused' AND NEW.state IN ('active','finalized')))
     THEN RAISE EXCEPTION 'INVALID_CAMPAIGN_TRANSITION'; END IF;
   IF NEW.state='finalized' AND EXISTS(SELECT 1 FROM campaign_members WHERE campaign_id=NEW.id AND state IN ('pending','active'))
     THEN RAISE EXCEPTION 'CAMPAIGN_NOT_TERMINAL'; END IF;
 END IF;
 IF TG_OP='INSERT' AND NEW.state<>'draft' THEN RAISE EXCEPTION 'CAMPAIGN_STARTS_DRAFT'; END IF;
 IF TG_OP='INSERT' OR OLD.state='draft' THEN
   SELECT * INTO ev FROM audit_events WHERE id=NEW.dataset_evidence_id;
   IF NOT FOUND OR ev.event_type<>'ml.dataset_verification' OR NOT ev.success OR ev.error_code IS NOT NULL
      OR (ev.after_state->>'integrity_status') IS DISTINCT FROM 'verified'
      OR (ev.after_state->'snapshot') IS DISTINCT FROM NEW.dataset_snapshot
      OR (ev.after_state->>'dataset_version_id') IS DISTINCT FROM NEW.dataset_version_id::text
      THEN RAISE EXCEPTION 'CAMPAIGN_DATASET_EVIDENCE_CONFLICT'; END IF;
 END IF;
 IF TG_OP='UPDATE' AND OLD.state='draft' AND NEW.state='frozen' THEN
   IF NEW.canonical_contract::jsonb IS DISTINCT FROM NEW.contract
      OR encode(sha256(convert_to(NEW.canonical_contract,'UTF8')),'hex')<>NEW.contract_hash THEN RAISE EXCEPTION 'CAMPAIGN_HASH_CONFLICT'; END IF;
   SELECT coalesce(jsonb_object_agg(configuration_hash,jsonb_build_object('configuration',configuration,'requests',requests)),'{}'::jsonb)
      INTO configs FROM campaign_configurations WHERE campaign_id=NEW.id;
   SELECT coalesce(jsonb_agg(jsonb_build_object('configuration_hash',configuration_hash,'seed',seed,'position',position,'exclusion_reason',exclusion_reason) ORDER BY position),'[]'::jsonb)
      INTO members FROM campaign_members WHERE campaign_id=NEW.id;
   IF jsonb_array_length(members)<>NEW.expected_count OR NEW.expected_count=0
      OR (NEW.contract->'matrix'->'configurations') IS DISTINCT FROM configs
      OR (NEW.contract->'matrix'->'members') IS DISTINCT FROM members
      OR (NEW.contract->'matrix'->>'expected_count') IS DISTINCT FROM NEW.expected_count::text
      OR (NEW.contract->'dataset') IS DISTINCT FROM NEW.dataset_snapshot
      OR (NEW.contract->>'dataset_evidence_id') IS DISTINCT FROM NEW.dataset_evidence_id::text
      OR (NEW.contract->'protocol') IS DISTINCT FROM NEW.protocol
      OR (NEW.contract->'requested') IS DISTINCT FROM NEW.requested
      OR (NEW.contract->'environment') IS DISTINCT FROM NEW.environment
      OR (NEW.contract->'matrix'->'registry') IS DISTINCT FROM NEW.registry_snapshot
      OR (NEW.contract->>'name') IS DISTINCT FROM NEW.name
      OR (NEW.contract->>'purpose') IS DISTINCT FROM NEW.purpose
      OR (NEW.contract->>'experiment_id') IS DISTINCT FROM NEW.experiment_id::text
      THEN RAISE EXCEPTION 'INCOMPLETE_FROZEN_MATRIX'; END IF;
   IF NEW.expected_count<>(SELECT count(*) FROM campaign_configurations WHERE campaign_id=NEW.id)*jsonb_array_length(NEW.contract->'matrix'->'seeds')
      OR EXISTS(SELECT 1 FROM campaign_members WHERE campaign_id=NEW.id AND NOT ((NEW.contract->'matrix'->'seeds') @> jsonb_build_array(seed)))
      OR jsonb_array_length(NEW.contract->'matrix'->'seeds')<>(SELECT count(DISTINCT value) FROM jsonb_array_elements(NEW.contract->'matrix'->'seeds'))
      THEN RAISE EXCEPTION 'INCOMPLETE_CONFIGURATION_SEED_GRID'; END IF;
   p=NEW.protocol;
   IF NOT (p ?& ARRAY['version','objective','metrics','sensitivity_target','specificity_minimum','roles','ranking','checkpoint','early_stopping','calibration','budget','missing','retries','fallback','test_access','aggregation','uncertainty','limitations','pending'])
      OR p->'pending' IS DISTINCT FROM '[]'::jsonb
      OR p->'roles' IS DISTINCT FROM '{"train":"train","selection":"val","calibration":"val","final_test":"test"}'::jsonb
      OR p->>'test_access' IS DISTINCT FROM 'final_only_after_candidate_lock'
      OR p->'ranking'->>'partition' IS DISTINCT FROM 'val'
      OR p->'calibration'->>'population' IS DISTINCT FROM 'val'
      OR p->'limitations'->'independent_calibration' IS DISTINCT FROM 'false'::jsonb
      OR p->>'retries' IS DISTINCT FROM 'first_verified_attempt'
      OR p->>'missing' IS DISTINCT FROM 'report_all_members'
      OR p->>'fallback' IS DISTINCT FROM 'diagnostic_only'
      THEN RAISE EXCEPTION 'INVALID_FROZEN_PROTOCOL'; END IF;
   IF jsonb_typeof(p->'sensitivity_target') IS DISTINCT FROM 'number'
      OR jsonb_typeof(p->'specificity_minimum') IS DISTINCT FROM 'number'
      OR (p->>'sensitivity_target')::numeric NOT BETWEEN 0 AND 1
      OR (p->>'specificity_minimum')::numeric NOT BETWEEN 0 AND 1
      OR (p->'budget'->>'max_members')::integer < NEW.expected_count
      OR coalesce((p->'budget'->>'max_attempts_per_member')::integer,0)<1
      OR coalesce(length(btrim(p->>'version')),0)=0
      OR coalesce(length(btrim(p->>'objective')),0)=0
      OR coalesce(length(btrim(p->'limitations'->>'shared_val')),0)=0
      OR p->'limitations'->>'test_exposure' IS NULL
      OR p->'limitations'->>'test_exposure' NOT IN ('unknown','previously_accessed')
      OR p->'checkpoint'->'threshold' IS DISTINCT FROM '0.5'::jsonb
      THEN RAISE EXCEPTION 'INCOMPLETE_SCIENTIFIC_PROTOCOL'; END IF;
   IF EXISTS(SELECT 1 FROM campaign_members WHERE campaign_id=NEW.id AND state NOT IN ('pending','excluded'))
      OR NOT EXISTS(SELECT 1 FROM campaign_members WHERE campaign_id=NEW.id AND state='pending')
      THEN RAISE EXCEPTION 'INVALID_INITIAL_MEMBERS'; END IF;
 END IF;
 NEW.updated_at=now(); RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.campaign_json_integer(v jsonb, minimum_value numeric) RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE n numeric;
BEGIN
 IF jsonb_typeof(v) IS DISTINCT FROM 'number' THEN RETURN false; END IF;
 n=(v #>> '{}')::numeric;
 RETURN n=trunc(n) AND n>=minimum_value AND n<=2147483647;
END $$;

CREATE OR REPLACE FUNCTION public.campaign_json_object(v jsonb, required_keys text[]) RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE k text;
BEGIN
 IF jsonb_typeof(v) IS DISTINCT FROM 'object' THEN RETURN false; END IF;
 FOREACH k IN ARRAY required_keys LOOP
   IF NOT (v ? k) OR v->k='null'::jsonb THEN RETURN false; END IF;
 END LOOP;
 RETURN true;
END $$;

CREATE OR REPLACE FUNCTION public.campaign_json_string(v jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path TO 'public', 'pg_catalog' AS $$
 SELECT coalesce(jsonb_typeof(v)='string' AND length(btrim(v #>> '{}'))>0,false)
$$;

CREATE OR REPLACE FUNCTION public.campaign_member_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE parent_state text; current_attempt text;
BEGIN
 SELECT state INTO parent_state FROM experimental_campaigns WHERE id=coalesce(NEW.campaign_id,OLD.campaign_id) FOR UPDATE;
 IF TG_OP='DELETE' THEN
   IF parent_state<>'draft' THEN RAISE EXCEPTION 'FROZEN_MEMBER_IMMUTABLE'; END IF; RETURN OLD;
 END IF;
 IF TG_OP='INSERT' AND (parent_state IS DISTINCT FROM 'draft' OR NEW.state NOT IN ('pending','excluded')) THEN RAISE EXCEPTION 'MEMBERS_REQUIRE_DRAFT'; END IF;
 IF TG_OP='UPDATE' THEN
   IF NEW.id<>OLD.id OR NEW.campaign_id<>OLD.campaign_id THEN RAISE EXCEPTION 'MEMBER_IDENTITY_IMMUTABLE'; END IF;
   IF parent_state<>'draft' AND (to_jsonb(NEW)-ARRAY['state','accepted_attempt_id']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['state','accepted_attempt_id']) THEN RAISE EXCEPTION 'FROZEN_MEMBER_IMMUTABLE'; END IF;
   IF NEW.state='verified' OR NEW.accepted_attempt_id IS NOT NULL THEN
     IF NEW.state IS DISTINCT FROM 'verified' OR NEW.accepted_attempt_id IS DISTINCT FROM
       (SELECT id FROM campaign_attempts WHERE member_id=NEW.id AND state='verified' ORDER BY ordinal LIMIT 1)
       OR NEW.accepted_attempt_id IS NULL THEN RAISE EXCEPTION 'FIRST_VERIFIED_ATTEMPT_REQUIRED'; END IF;
   END IF;
   IF NEW.state<>OLD.state THEN
     SELECT state INTO current_attempt FROM campaign_attempts WHERE member_id=NEW.id ORDER BY ordinal DESC LIMIT 1;
     IF NEW.state IS DISTINCT FROM current_attempt THEN RAISE EXCEPTION 'MEMBER_STATE_MUST_FOLLOW_ATTEMPT'; END IF;
   END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.campaign_model_matches(run_id uuid, member uuid) RETURNS boolean LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE model_name text; cfg jsonb; registry jsonb; d jsonb; matches integer;
BEGIN
 SELECT mo.name,cf.configuration,c.registry_snapshot INTO model_name,cfg,registry
 FROM runs r JOIN models mo ON mo.id=r.model_id
 JOIN campaign_members m ON m.id=member
 JOIN campaign_configurations cf ON cf.campaign_id=m.campaign_id AND cf.configuration_hash=m.configuration_hash
 JOIN experimental_campaigns c ON c.id=m.campaign_id WHERE r.id=run_id;
 IF NOT FOUND THEN RETURN false; END IF;
 SELECT count(*) INTO matches FROM jsonb_array_elements(registry) item
 WHERE item->>'id'=cfg->>'model_id' AND item->>'version'=cfg->>'adapter_version'
   AND (item->>'id'=model_name OR item->'aliases' @> to_jsonb(ARRAY[model_name]));
 RETURN matches=1;
END $$;

CREATE OR REPLACE FUNCTION public.controlled_binding_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
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

CREATE OR REPLACE FUNCTION public.controlled_pause_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
BEGIN
 IF NEW.state IS DISTINCT FROM 'paused' AND EXISTS(
  SELECT 1 FROM campaign_controlled_requests q JOIN campaign_attempts a ON a.id=q.attempt_id
  WHERE q.campaign_id=NEW.id AND a.state IN ('active','completed'))
 THEN RAISE EXCEPTION 'CONTROLLED_TRAIN_REQUIRES_PAUSED'; END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.controlled_run_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE q record;
BEGIN
 SELECT * INTO q FROM campaign_controlled_requests WHERE run_id=NEW.id;
 IF FOUND AND NEW.campaign_id IS DISTINCT FROM q.campaign_id THEN RAISE EXCEPTION 'CONTROLLED_CAMPAIGN_ID_REQUIRED'; END IF;
 IF TG_OP='UPDATE' AND NEW.campaign_id IS DISTINCT FROM OLD.campaign_id THEN RAISE EXCEPTION 'RUN_CAMPAIGN_IMMUTABLE'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.e04_assert_calibration(member_id uuid) RETURNS void LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE e public.evaluations%ROWTYPE; d public.evaluations%ROWTYPE; s public.evaluations%ROWTYPE;
 c public.run_threshold_calibration%ROWTYPE; ev jsonb; result jsonb; context jsonb;
 n integer; m public.run_clinical_metrics%ROWTYPE; expected jsonb; k text;
BEGIN
 SELECT * INTO e FROM public.evaluations WHERE id=member_id;
 IF NOT FOUND OR e.source_kind<>'e10'
 OR e.evaluation_role NOT IN ('calibration_default','calibration_selected') THEN RETURN; END IF;
 SELECT count(*) INTO n FROM public.run_threshold_calibration
 WHERE default_evaluation_id=e.id OR selected_evaluation_id=e.id;
 IF n<>1 THEN RAISE EXCEPTION 'E04_PAIR_REQUIRED'; END IF;
 SELECT * INTO STRICT c FROM public.run_threshold_calibration
 WHERE default_evaluation_id=e.id OR selected_evaluation_id=e.id;
 SELECT * INTO d FROM public.evaluations WHERE id=c.default_evaluation_id;
 SELECT * INTO s FROM public.evaluations WHERE id=c.selected_evaluation_id;
 IF d.id IS NULL OR s.id IS NULL THEN RAISE EXCEPTION 'E04_PAIR_REQUIRED'; END IF;
 IF d.id=s.id OR d.evaluation_role IS DISTINCT FROM 'calibration_default'
 OR s.evaluation_role IS DISTINCT FROM 'calibration_selected'
 OR d.source_kind IS DISTINCT FROM 'e10' OR s.source_kind IS DISTINCT FROM 'e10'
 OR d.split IS DISTINCT FROM 'val' OR s.split IS DISTINCT FROM 'val'
 OR c.calibration_split IS DISTINCT FROM 'val'
 OR d.run_id IS DISTINCT FROM s.run_id OR d.training_run_id IS DISTINCT FROM s.training_run_id
 OR d.run_id IS DISTINCT FROM d.training_run_id OR d.training_run_id IS DISTINCT FROM c.run_id
 OR d.model_version_id IS DISTINCT FROM s.model_version_id
 OR c.model_version_id IS DISTINCT FROM d.model_version_id
 OR d.checkpoint_artifact_id IS DISTINCT FROM s.checkpoint_artifact_id
 OR d.dataset_version_id IS DISTINCT FROM s.dataset_version_id
 OR d.population_hash IS DISTINCT FROM s.population_hash
 OR d.protocol_version IS DISTINCT FROM s.protocol_version
 OR d.protocol_hash IS DISTINCT FROM s.protocol_hash
 OR d.protocol_snapshot IS DISTINCT FROM s.protocol_snapshot
 OR d.input_contract_hash IS DISTINCT FROM s.input_contract_hash
 OR d.comparison_contract_hash IS DISTINCT FROM s.comparison_contract_hash
 OR d.subject_kind IS DISTINCT FROM s.subject_kind
 OR d.source_event_id IS DISTINCT FROM s.source_event_id
 THEN RAISE EXCEPTION 'E04_PAIR_IDENTITY_MISMATCH'; END IF;
 IF d.threshold_source IS DISTINCT FROM 'default' OR d.calibration_id IS NOT NULL
 OR d.threshold_used IS DISTINCT FROM c.default_threshold
 OR s.threshold_source IS DISTINCT FROM 'validation_calibration'
 OR s.calibration_id IS DISTINCT FROM c.run_threshold_calibration_id
 OR s.threshold_used IS DISTINCT FROM c.threshold_selected
 THEN RAISE EXCEPTION 'E04_THRESHOLD_PROVENANCE'; END IF;
 SELECT (payload->>'canonical_event')::jsonb INTO ev FROM public.train_execution_records
 WHERE run_id=d.run_id AND event_id=d.source_event_id AND kind='e10_event'
 AND phase='run_event_v1' AND record_key=d.source_event_id::text;
 result:=ev#>'{payload,result,result}';
 IF ev->>'event_type' IS DISTINCT FROM 'calibration_completed'
 OR ev->>'event_id' IS DISTINCT FROM d.source_event_id::text
 OR ev->>'run_id' IS DISTINCT FROM d.run_id::text
 OR ev->>'schema_version' IS DISTINCT FROM 'run_event_v1'
 OR ev#>>'{payload,result,split}' IS DISTINCT FROM 'val'
 OR result->>'calibration_split' IS DISTINCT FROM 'val'
 OR result->>'threshold_source' IS DISTINCT FROM 'validation_calibration'
 OR (result->>'threshold_selected')::numeric IS DISTINCT FROM c.threshold_selected
 OR (result->>'threshold_used')::numeric IS DISTINCT FROM c.threshold_selected
 OR (result->>'default_threshold')::numeric IS DISTINCT FROM c.default_threshold
 OR (result->>'target_recall')::numeric IS DISTINCT FROM c.target_recall
 THEN RAISE EXCEPTION 'E04_EVENT_PROVENANCE'; END IF;
 SELECT execution_parameters->'e10_v2_evaluation_context_v1' INTO context
 FROM public.runs WHERE id=d.run_id;
 IF context IS NULL OR context->>'checkpoint_artifact_id' IS DISTINCT FROM d.checkpoint_artifact_id::text
 OR context->>'model_version_id' IS DISTINCT FROM d.model_version_id::text
 OR context->>'protocol_version' IS DISTINCT FROM d.protocol_version
 OR context->>'protocol_hash' IS DISTINCT FROM d.protocol_hash
 OR context->'protocol_snapshot' IS DISTINCT FROM d.protocol_snapshot
 OR context->>'population_hash' IS DISTINCT FROM d.population_hash
 OR context->>'input_contract_hash' IS DISTINCT FROM d.input_contract_hash
 OR context->>'comparison_contract_hash' IS DISTINCT FROM d.comparison_contract_hash
 THEN RAISE EXCEPTION 'E04_CONTEXT_PROVENANCE'; END IF;
 FOR m IN SELECT * FROM public.run_clinical_metrics WHERE evaluation_id IN (d.id,s.id) LOOP
   expected:=CASE WHEN m.evaluation_id=d.id THEN result->'default_threshold_metrics' ELSE result->'selected_metrics' END;
   IF expected IS NULL OR jsonb_typeof(expected) IS DISTINCT FROM 'object' THEN
     RAISE EXCEPTION 'E04_METRIC_PROVENANCE';
   END IF;
   FOREACH k IN ARRAY ARRAY['tn','fp','fn','tp','roc_auc_parasitized','pr_auc_parasitized'] LOOP
     IF NOT (expected ? k) OR (to_jsonb(m)->k) IS DISTINCT FROM expected->k THEN
       RAISE EXCEPTION 'E04_METRIC_PROVENANCE';
     END IF;
   END LOOP;
 END LOOP;
 IF (SELECT count(*) FROM public.run_clinical_metrics WHERE evaluation_id IN (d.id,s.id))<>2 THEN
   RAISE EXCEPTION 'E04_PAIR_METRICS_REQUIRED';
 END IF;
END $$;

CREATE FUNCTION public.e04_calibration_immutable() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM public.evaluations WHERE source_kind='e10'
 AND id IN (OLD.default_evaluation_id,OLD.selected_evaluation_id)) THEN
   RAISE EXCEPTION 'E04_CALIBRATION_IMMUTABLE';
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.e04_legacy_admission() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
BEGIN
 IF NEW.source_kind='legacy' AND current_user <> 'capstone_v2_migrator' THEN
   RAISE EXCEPTION 'E04_LEGACY_MIGRATOR_REQUIRED' USING ERRCODE='42501';
 END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.enforce_activation_materialization_consistency() RETURNS trigger LANGUAGE plpgsql AS $$
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

CREATE OR REPLACE FUNCTION public.enforce_dataset_assignment_consistency() RETURNS trigger LANGUAGE plpgsql AS $$
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

CREATE OR REPLACE FUNCTION public.enforce_dataset_version_lifecycle() RETURNS trigger LANGUAGE plpgsql AS $$
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

CREATE OR REPLACE FUNCTION public.enforce_model_version_governance() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    owner_run_type TEXT;
BEGIN
    IF NEW.training_run_id IS NOT NULL THEN
        SELECT run_type
        INTO owner_run_type
        FROM runs
        WHERE id = NEW.training_run_id;

        IF owner_run_type IS DISTINCT FROM 'training' THEN
            RAISE EXCEPTION
                'model_versions.training_run_id debe referenciar un run training; recibió % (%)',
                NEW.training_run_id,
                owner_run_type
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF TG_OP = 'UPDATE'
       AND (
           OLD.status IN (
               'candidate', 'validated', 'approved', 'deployed', 'rejected', 'retired'
           )
           OR NEW.status IN (
               'candidate', 'validated', 'approved', 'deployed', 'rejected', 'retired'
           )
       )
       AND ROW(
           NEW.model_id,
           NEW.model_name,
           NEW.version_number,
           NEW.checkpoint_path,
           NEW.final_model_path,
           NEW.best_model_path,
           NEW.training_run_id,
           NEW.checkpoint_artifact_id,
           NEW.artifact_uri,
           NEW.artifact_sha256,
           NEW.artifact_size_bytes,
           NEW.artifact_hash_reuse_justification,
           NEW.framework,
           NEW.framework_version,
           NEW.preprocessing_profile_snapshot,
           NEW.class_mapping,
           NEW.input_signature,
           NEW.output_signature
       ) IS DISTINCT FROM ROW(
           OLD.model_id,
           OLD.model_name,
           OLD.version_number,
           OLD.checkpoint_path,
           OLD.final_model_path,
           OLD.best_model_path,
           OLD.training_run_id,
           OLD.checkpoint_artifact_id,
           OLD.artifact_uri,
           OLD.artifact_sha256,
           OLD.artifact_size_bytes,
           OLD.artifact_hash_reuse_justification,
           OLD.framework,
           OLD.framework_version,
           OLD.preprocessing_profile_snapshot,
           OLD.class_mapping,
           OLD.input_signature,
           OLD.output_signature
       ) THEN
        RAISE EXCEPTION
            'El payload de una model_version gobernada es inmutable (%)',
            OLD.id
            USING ERRCODE = '55000';
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.enforce_run_lineage_governance() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    parent_type TEXT;
    child_type TEXT;
BEGIN
    SELECT run_type INTO parent_type FROM runs WHERE id = NEW.parent_run_id;
    SELECT run_type INTO child_type FROM runs WHERE id = NEW.child_run_id;

    IF NEW.relationship_type = 'evaluates_checkpoint_from'
       AND (parent_type IS DISTINCT FROM 'training' OR child_type IS DISTINCT FROM 'evaluation') THEN
        RAISE EXCEPTION
            'evaluates_checkpoint_from exige parent training y child evaluation; recibió % -> %',
            parent_type,
            child_type
            USING ERRCODE = '23514';
    END IF;

    IF NEW.relationship_type = 'explains_checkpoint_from'
       AND (parent_type IS DISTINCT FROM 'training' OR child_type IS DISTINCT FROM 'explainability') THEN
        RAISE EXCEPTION
            'explains_checkpoint_from exige parent training y child explainability; recibió % -> %',
            parent_type,
            child_type
            USING ERRCODE = '23514';
    END IF;

    IF NEW.relationship_type IN (
           'evaluates_checkpoint_from', 'explains_checkpoint_from'
       )
       AND (
           NEW.model_version_id IS NULL
           OR NEW.checkpoint_artifact_id IS NULL
       ) THEN
        IF TG_OP = 'INSERT' THEN
            RAISE EXCEPTION
                'El linaje gobernado % exige model_version_id y checkpoint_artifact_id',
                NEW.relationship_type
                USING ERRCODE = '23514';
        ELSIF ROW(
            NEW.relationship_type,
            NEW.parent_run_id,
            NEW.child_run_id,
            NEW.model_version_id,
            NEW.checkpoint_artifact_id
        ) IS DISTINCT FROM ROW(
            OLD.relationship_type,
            OLD.parent_run_id,
            OLD.child_run_id,
            OLD.model_version_id,
            OLD.checkpoint_artifact_id
        ) THEN
            RAISE EXCEPTION
                'Cambiar la identidad de linaje % exige model_version_id y checkpoint_artifact_id',
                NEW.relationship_type
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.execution_event_immutable() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
BEGIN RAISE EXCEPTION 'EXECUTION_HISTORY_IMMUTABLE'; END $$;

CREATE OR REPLACE FUNCTION public.experiment_require_owner() RETURNS void LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE g record;
BEGIN
 SELECT * INTO g FROM experiment_execution_gate WHERE singleton FOR UPDATE;
 IF g.owner IS NULL OR g.owner::text IS DISTINCT FROM current_setting('capstone.execution_token',true)
 OR NOT (EXISTS(SELECT 1 FROM pg_locks WHERE locktype='advisory' AND classid=120994 AND objid=1 AND objsubid=2 AND pid=g.db_pid AND granted)
 OR EXISTS(SELECT 1 FROM local_execution_jobs WHERE owner=g.owner AND state IN ('held','calculation_reported')))
 THEN RAISE EXCEPTION 'GLOBAL_EXECUTION_OWNER_REQUIRED'; END IF;
END $$;

CREATE OR REPLACE FUNCTION public.prevent_audit_event_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        RAISE EXCEPTION 'audit_events is append-only';
      END $$;

CREATE OR REPLACE FUNCTION public.prevent_stage2_publication_event_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'stage2_model_publication_events es append-only';
END;
$$;

CREATE OR REPLACE FUNCTION public.prevent_validation_annotation_event_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      RAISE EXCEPTION 'scientific validation annotation events are append-only'
        USING ERRCODE='55000';
    END $$;

CREATE OR REPLACE FUNCTION public.prevent_validation_membership_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      RAISE EXCEPTION 'scientific validation membership is append-only';
    END $$;

CREATE OR REPLACE FUNCTION public.protect_cell_classification_run() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
      actual_input_count INTEGER;
      actual_eligible_count INTEGER;
      actual_excluded_count INTEGER;
      actual_processed_count INTEGER;
      actual_parasitized_count INTEGER;
      actual_uninfected_count INTEGER;
      actual_near_threshold_count INTEGER;
      actual_failed_count INTEGER;
      actual_summary_count INTEGER;
    BEGIN
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'cell_classification_runs cannot be deleted'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status IN ('completed','completed_with_warnings','failed') THEN
        RAISE EXCEPTION 'terminal cell_classification_runs are immutable'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status = 'created' AND NEW.status NOT IN ('processing','failed') THEN
        RAISE EXCEPTION 'invalid cell classification run transition'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status = 'created' AND NEW.status = 'processing' THEN
        SELECT
          count(*),
          count(*) FILTER (WHERE eligible),
          count(*) FILTER (WHERE NOT eligible)
        INTO
          actual_input_count,
          actual_eligible_count,
          actual_excluded_count
        FROM cell_classification_inputs
        WHERE classification_run_id=OLD.id;
        IF actual_input_count <> OLD.input_count
          OR actual_eligible_count <> OLD.eligible_count
          OR actual_excluded_count <> OLD.excluded_count
        THEN
          RAISE EXCEPTION
            'frozen classification inputs do not match run counters'
            USING ERRCODE = '23514';
        END IF;
      END IF;
      IF OLD.status = 'processing'
        AND NEW.status NOT IN (
          'processing','completed','completed_with_warnings','failed'
        )
      THEN
        RAISE EXCEPTION 'invalid cell classification run transition'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status IN ('created','processing') THEN
        SELECT
          count(*),
          count(*) FILTER (
            WHERE prediction_status='completed'
              AND predicted_label='parasitized'
          ),
          count(*) FILTER (
            WHERE prediction_status='completed'
              AND predicted_label='uninfected'
          ),
          count(*) FILTER (
            WHERE prediction_status='completed' AND near_threshold
          ),
          count(*) FILTER (WHERE prediction_status='failed')
        INTO
          actual_processed_count,
          actual_parasitized_count,
          actual_uninfected_count,
          actual_near_threshold_count,
          actual_failed_count
        FROM cell_predictions
        WHERE classification_run_id=OLD.id;
        IF actual_processed_count <> NEW.processed_count
          OR actual_parasitized_count <> NEW.parasitized_count
          OR actual_uninfected_count <> NEW.uninfected_count
          OR actual_near_threshold_count <> NEW.near_threshold_count
          OR actual_failed_count <> NEW.failed_count
        THEN
          RAISE EXCEPTION
            'persisted predictions do not match run counters'
            USING ERRCODE = '23514';
        END IF;
      END IF;
      IF NEW.status IN ('completed','completed_with_warnings') THEN
        SELECT count(*)
        INTO actual_summary_count
        FROM smear_analysis_summaries
        WHERE classification_run_id=OLD.id;
        IF actual_summary_count <> 1 THEN
          RAISE EXCEPTION
            'completed classification run requires one immutable summary'
            USING ERRCODE = '23514';
        END IF;
      END IF;
      IF NEW.updated_at < OLD.updated_at THEN
        RAISE EXCEPTION 'classification run time cannot move backwards'
          USING ERRCODE = '23514';
      END IF;
      IF OLD.started_at IS NOT NULL
        AND NEW.started_at IS DISTINCT FROM OLD.started_at
      THEN
        RAISE EXCEPTION 'classification run started_at is immutable once set'
          USING ERRCODE = '55000';
      END IF;
      IF NEW.analysis_run_id IS DISTINCT FROM OLD.analysis_run_id
        OR NEW.detection_run_id IS DISTINCT FROM OLD.detection_run_id
        OR NEW.classification_run_code
          IS DISTINCT FROM OLD.classification_run_code
        OR NEW.production_model_id IS DISTINCT FROM OLD.production_model_id
        OR NEW.stage2_publication_id
          IS DISTINCT FROM OLD.stage2_publication_id
        OR NEW.model_registry_id IS DISTINCT FROM OLD.model_registry_id
        OR NEW.model_name IS DISTINCT FROM OLD.model_name
        OR NEW.model_version IS DISTINCT FROM OLD.model_version
        OR NEW.model_snapshot IS DISTINCT FROM OLD.model_snapshot
        OR NEW.input_manifest_sha256
          IS DISTINCT FROM OLD.input_manifest_sha256
        OR NEW.input_count IS DISTINCT FROM OLD.input_count
        OR NEW.eligible_count IS DISTINCT FROM OLD.eligible_count
        OR NEW.excluded_count IS DISTINCT FROM OLD.excluded_count
        OR NEW.requested_by IS DISTINCT FROM OLD.requested_by
        OR NEW.retry_of_run_id IS DISTINCT FROM OLD.retry_of_run_id
        OR NEW.created_at IS DISTINCT FROM OLD.created_at
      THEN
        RAISE EXCEPTION
          'cell_classification_runs identity, model and inputs are immutable'
          USING ERRCODE = '55000';
      END IF;
      RETURN NEW;
    END;
    $$;

CREATE OR REPLACE FUNCTION public.protect_cell_detection_run_identity() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'cell_detection_runs cannot be deleted'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status IN ('completed','completed_with_warnings','failed') THEN
        RAISE EXCEPTION 'terminal cell_detection_runs are immutable'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status = 'created' AND NEW.status NOT IN ('processing','failed') THEN
        RAISE EXCEPTION 'invalid cell detection run transition'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status = 'processing'
        AND NEW.status NOT IN (
          'processing','completed','completed_with_warnings','failed'
        )
      THEN
        RAISE EXCEPTION 'invalid cell detection run transition'
          USING ERRCODE = '55000';
      END IF;
      IF NEW.analysis_run_id IS DISTINCT FROM OLD.analysis_run_id
        OR NEW.detection_run_code IS DISTINCT FROM OLD.detection_run_code
        OR NEW.detector_key IS DISTINCT FROM OLD.detector_key
        OR NEW.detector_version IS DISTINCT FROM OLD.detector_version
        OR NEW.algorithm_version IS DISTINCT FROM OLD.algorithm_version
        OR NEW.profile_snapshot IS DISTINCT FROM OLD.profile_snapshot
        OR NEW.input_manifest_sha256 IS DISTINCT FROM OLD.input_manifest_sha256
        OR NEW.image_count IS DISTINCT FROM OLD.image_count
        OR NEW.requested_by IS DISTINCT FROM OLD.requested_by
        OR NEW.created_at IS DISTINCT FROM OLD.created_at
      THEN
        RAISE EXCEPTION 'cell_detection_runs identity and profile are immutable'
          USING ERRCODE = '55000';
      END IF;
      RETURN NEW;
    END;
    $$;

CREATE OR REPLACE FUNCTION public.protect_cell_explanation() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'cell_explanations cannot be deleted'
          USING ERRCODE = '55000';
      END IF;
      IF NEW.cell_prediction_id IS DISTINCT FROM OLD.cell_prediction_id
        OR NEW.method IS DISTINCT FROM OLD.method
        OR NEW.method_version IS DISTINCT FROM OLD.method_version
        OR NEW.parameters_json IS DISTINCT FROM OLD.parameters_json
        OR NEW.created_at IS DISTINCT FROM OLD.created_at
      THEN
        RAISE EXCEPTION 'cell explanation identity and parameters are immutable'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status IN ('generated','unsupported') THEN
        RAISE EXCEPTION 'terminal cell explanations are immutable'
          USING ERRCODE = '55000';
      END IF;
      IF NOT (
        (OLD.status = 'not_requested' AND NEW.status = 'pending')
        OR
        (
          OLD.status = 'pending'
          AND NEW.status IN ('generated','failed','unsupported')
        )
        OR
        (OLD.status = 'failed' AND NEW.status = 'pending')
      ) THEN
        RAISE EXCEPTION 'invalid cell explanation transition'
          USING ERRCODE = '55000';
      END IF;
      RETURN NEW;
    END;
    $$;

CREATE OR REPLACE FUNCTION public.protect_deployed_model_version_payload() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE'
       AND ROW(
           NEW.model_version_id,
           NEW.checkpoint_artifact_id,
           NEW.threshold_calibration_id,
           NEW.deployment_name,
           NEW.environment,
           NEW.alias,
           NEW.artifact_sha256,
           NEW.artifact_size_bytes,
           NEW.threshold_value,
           NEW.threshold_profile_snapshot,
           NEW.preprocessing_profile_snapshot,
           NEW.image_quality_policy_snapshot,
           NEW.label_mapping_snapshot,
           NEW.positive_label,
           NEW.score_name,
           NEW.supersedes_deployment_id,
           NEW.rollback_of_deployment_id,
           NEW.created_at
       ) IS DISTINCT FROM ROW(
           OLD.model_version_id,
           OLD.checkpoint_artifact_id,
           OLD.threshold_calibration_id,
           OLD.deployment_name,
           OLD.environment,
           OLD.alias,
           OLD.artifact_sha256,
           OLD.artifact_size_bytes,
           OLD.threshold_value,
           OLD.threshold_profile_snapshot,
           OLD.preprocessing_profile_snapshot,
           OLD.image_quality_policy_snapshot,
           OLD.label_mapping_snapshot,
           OLD.positive_label,
           OLD.score_name,
           OLD.supersedes_deployment_id,
           OLD.rollback_of_deployment_id,
           OLD.created_at
       ) THEN
        RAISE EXCEPTION
            'El payload de deployed_model_versions es inmutable; cree una nueva revisión (%)',
            OLD.id
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.protect_frozen_dataset_assignment_updates() RETURNS trigger LANGUAGE plpgsql AS $$
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

CREATE OR REPLACE FUNCTION public.protect_frozen_dataset_assignments() RETURNS trigger LANGUAGE plpgsql AS $$
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

CREATE OR REPLACE FUNCTION public.protect_frozen_dataset_version_sources() RETURNS trigger LANGUAGE plpgsql AS $$
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

CREATE OR REPLACE FUNCTION public.protect_governed_artifact_identity() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM model_versions
        WHERE checkpoint_artifact_id = OLD.id
    )
       AND ROW(
           NEW.run_id,
           NEW.path,
           NEW.checksum,
           NEW.file_size_bytes
       ) IS DISTINCT FROM ROW(
           OLD.run_id,
           OLD.path,
           OLD.checksum,
           OLD.file_size_bytes
       ) THEN
        RAISE EXCEPTION
            'No se puede mutar path/checksum/tamaño de un artifact ligado a model_version (%)',
            OLD.id
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.protect_validation_annotation() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'scientific validation annotations cannot be deleted'
          USING ERRCODE='55000';
      END IF;
      IF OLD.validation_session_id IS DISTINCT FROM NEW.validation_session_id
        OR OLD.target_type IS DISTINCT FROM NEW.target_type
        OR OLD.cell_detection_id IS DISTINCT FROM NEW.cell_detection_id
        OR OLD.analysis_run_id IS DISTINCT FROM NEW.analysis_run_id
        OR OLD.sample_id IS DISTINCT FROM NEW.sample_id
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

CREATE OR REPLACE FUNCTION public.protect_validation_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
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

CREATE OR REPLACE FUNCTION public.reject_cell_analysis_row_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      RAISE EXCEPTION 'cell analysis result and review rows are append-only'
        USING ERRCODE = '55000';
    END;
    $$;

CREATE OR REPLACE FUNCTION public.reject_cell_classification_row_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      RAISE EXCEPTION
        'cell classification inputs, predictions, summaries, events and reviews are append-only'
        USING ERRCODE = '55000';
    END;
    $$;

CREATE OR REPLACE FUNCTION public.train_record_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE s record;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'TRAIN_RECORD_IMMUTABLE'; END IF;
 SELECT * INTO s FROM train_execution_sessions WHERE run_id=NEW.run_id FOR UPDATE;
 IF s.state IS DISTINCT FROM 'active' OR s.owner::text IS DISTINCT FROM current_setting('capstone.train_owner',true)
 THEN RAISE EXCEPTION 'TRAIN_OWNER_FENCED'; END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.train_revision_binding_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM campaign_attempts a JOIN campaign_members m ON m.id=a.member_id
 JOIN train_execution_sessions s ON s.attempt_id=a.id JOIN campaign_technical_revisions v ON v.id=NEW.revision_id
 WHERE a.id=NEW.attempt_id AND m.campaign_id=NEW.campaign_id AND v.campaign_id=NEW.campaign_id
 AND s.environment IS NOT DISTINCT FROM v.payload->'environment')
 THEN RAISE EXCEPTION 'TRAIN_REVISION_BINDING_INVALID'; END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.train_session_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'TRAIN_HISTORY_IMMUTABLE'; END IF;
 IF NEW.run_id<>OLD.run_id OR NEW.owner<>OLD.owner OR NEW.attempt_id IS DISTINCT FROM OLD.attempt_id
 OR NEW.configuration IS DISTINCT FROM OLD.configuration OR NEW.dataset IS DISTINCT FROM OLD.dataset
 OR NEW.environment IS DISTINCT FROM OLD.environment OR NEW.artifact_root<>OLD.artifact_root
 THEN RAISE EXCEPTION 'TRAIN_IDENTITY_IMMUTABLE'; END IF;
 IF OLD.state IN ('verified','failed','interrupted') OR OLD.owner::text IS DISTINCT FROM current_setting('capstone.train_owner',true)
 THEN RAISE EXCEPTION 'TRAIN_OWNER_FENCED'; END IF;
 IF NOT ((OLD.state='active' AND NEW.state IN ('active','completed','failed','interrupted')) OR (OLD.state='completed' AND NEW.state='verified'))
 THEN RAISE EXCEPTION 'TRAIN_TRANSITION_INVALID'; END IF;
 IF NEW.state='verified' AND (
   NEW.verification->>'status' IS DISTINCT FROM 'verified'
   OR coalesce(NEW.completion->>'records_hash','') !~ '^[a-f0-9]{64}$'
   OR (NEW.completion->>'epochs')::integer IS DISTINCT FROM (SELECT count(*)::integer FROM train_execution_records WHERE run_id=NEW.run_id AND kind='epoch')
   OR NEW.completion->>'records_hash' IS DISTINCT FROM NEW.verification->>'records_hash'
   OR NOT EXISTS(SELECT 1 FROM train_execution_records WHERE run_id=NEW.run_id AND kind='epoch')
   OR NOT EXISTS(SELECT 1 FROM train_execution_records WHERE run_id=NEW.run_id AND kind='artifact')
 ) THEN RAISE EXCEPTION 'TRAIN_VERIFICATION_INCOMPLETE'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.v2_binary_metric_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE e public.evaluations%ROWTYPE;
BEGIN
 SELECT * INTO STRICT e FROM public.evaluations WHERE id=NEW.evaluation_id;
 IF NEW.run_id IS DISTINCT FROM e.run_id THEN RAISE EXCEPTION 'METRIC_RUN_MISMATCH'; END IF;
 IF e.subject_kind='single' THEN
 SELECT r.model_id,m.name INTO NEW.model_id,NEW.model_name FROM public.runs r JOIN public.models m ON m.id=r.model_id WHERE r.id=e.training_run_id;
 ELSE NEW.model_id:=NULL; NEW.model_name:='ensemble'; END IF;
 NEW.split_name:=e.split; NEW.threshold_used:=e.threshold_used; NEW.threshold_source:=e.threshold_source;
 NEW.recall_parasitized:=NEW.tp::numeric/nullif(NEW.tp::numeric+NEW.fn,0);
 NEW.sensitivity_parasitized:=NEW.recall_parasitized;
 NEW.specificity:=NEW.tn::numeric/nullif(NEW.tn::numeric+NEW.fp,0);
 NEW.precision_parasitized:=NEW.tp::numeric/nullif(NEW.tp::numeric+NEW.fp,0);
 NEW.f1_parasitized:=2*NEW.tp::numeric/nullif(2*NEW.tp::numeric+NEW.fp+NEW.fn,0);
 NEW.f2_parasitized:=5*NEW.tp::numeric/nullif(5*NEW.tp::numeric+NEW.fp+4*NEW.fn::numeric,0);
 NEW.balanced_accuracy:=(NEW.recall_parasitized+NEW.specificity)/2;
 NEW.accuracy:=(NEW.tp::numeric+NEW.tn)/nullif(NEW.tp::numeric+NEW.tn+NEW.fp+NEW.fn,0);
 NEW.confusion_matrix:=jsonb_build_array(jsonb_build_array(NEW.tn,NEW.fp),jsonb_build_array(NEW.fn,NEW.tp));
 IF NEW.tp::numeric+NEW.fn=0 OR NEW.tn::numeric+NEW.fp=0 THEN
   IF NEW.roc_auc_parasitized IS NOT NULL OR NEW.pr_auc_parasitized IS NOT NULL THEN RAISE EXCEPTION 'SINGLE_CLASS_AUC'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.v2_calibration_pair_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE d public.evaluations%ROWTYPE; s public.evaluations%ROWTYPE;
BEGIN
 IF NOT EXISTS (SELECT 1 FROM public.run_configurations rc WHERE rc.run_id=NEW.run_id AND rc.clinical_target_recall=NEW.target_recall) THEN RAISE EXCEPTION 'CALIBRATION_CONFIGURATION_TARGET_MISMATCH'; END IF;
 SELECT * INTO STRICT d FROM public.evaluations WHERE id=NEW.default_evaluation_id;
 SELECT * INTO STRICT s FROM public.evaluations WHERE id=NEW.selected_evaluation_id;
 IF d.id=s.id OR d.split<>'val' OR s.split<>'val'
 OR d.training_run_id IS DISTINCT FROM NEW.run_id OR s.training_run_id IS DISTINCT FROM NEW.run_id
 OR d.dataset_version_id IS DISTINCT FROM s.dataset_version_id OR d.population_hash IS DISTINCT FROM s.population_hash
 OR d.checkpoint_artifact_id IS DISTINCT FROM s.checkpoint_artifact_id
 OR d.threshold_used<>0.5 OR s.threshold_used IS DISTINCT FROM NEW.threshold_selected
 OR d.evaluation_role<>'calibration_default' OR s.evaluation_role<>'calibration_selected' THEN RAISE EXCEPTION 'CALIBRATION_PAIR_INVALID'; END IF;
 RETURN NULL;
END $$;

CREATE FUNCTION public.v2_configuration_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE r public.runs%ROWTYPE; j jsonb; cfg jsonb;
BEGIN
 SELECT * INTO STRICT r FROM public.runs WHERE id=NEW.run_id;
 j:=NEW.canonical_configuration::jsonb;
 cfg:=r.execution_parameters->'model_configuration_e2'->'configuration';
 IF r.run_type<>'training' OR r.random_seed IS DISTINCT FROM NEW.random_seed
 OR cfg->'resolved' IS DISTINCT FROM j OR cfg->>'model_id' IS DISTINCT FROM NEW.architecture
 OR cfg->>'adapter_version' IS DISTINCT FROM NEW.adapter_version
 OR j#>>'{optimizer,name}' IS DISTINCT FROM NEW.optimizer
 OR (j#>>'{optimizer,parameters,learning_rate}')::float8 IS DISTINCT FROM NEW.learning_rate
 OR (j#>>'{optimizer,fine_tune_learning_rate}')::float8 IS DISTINCT FROM NEW.fine_tune_learning_rate
 OR (j#>>'{execution,batch_size}')::integer IS DISTINCT FROM NEW.batch_size
 OR (j#>>'{execution,seed}')::bigint IS DISTINCT FROM NEW.random_seed
 OR (j#>>'{execution,max_epochs}')::integer IS DISTINCT FROM NEW.max_epochs
 OR (j#>>'{execution,fine_tune_epochs}')::integer IS DISTINCT FROM NEW.fine_tune_epochs
 OR (j#>>'{model,dropout}')::float8 IS DISTINCT FROM NEW.dropout
 OR (j#>>'{model,l2}')::float8 IS DISTINCT FROM NEW.l2
 OR j#>>'{model,preprocessing}' IS DISTINCT FROM NEW.normalization
 OR j#>>'{recipe,loss}' IS DISTINCT FROM NEW.loss_function
 OR (j#>>'{execution,calibrate_threshold}')::boolean IS DISTINCT FROM NEW.calibration_enabled
 OR (j#>>'{execution,target_recall}')::numeric IS DISTINCT FROM NEW.clinical_target_recall
 THEN RAISE EXCEPTION 'FROZEN_CONFIGURATION_MISMATCH'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.v2_evaluation_complete() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE e public.evaluations%ROWTYPE; n integer; w numeric; r public.runs%ROWTYPE; ai public.assessment_identities%ROWTYPE; ast text;
BEGIN
 IF TG_TABLE_NAME='evaluations' THEN e:=NEW; ELSE SELECT * INTO STRICT e FROM public.evaluations WHERE id=NEW.evaluation_id; END IF;
 SELECT * INTO STRICT r FROM public.runs WHERE id=e.training_run_id;
 IF r.run_type<>'training' OR (e.split<>'external' AND r.dataset_version_id IS DISTINCT FROM e.dataset_version_id) THEN RAISE EXCEPTION 'EVALUATION_TRAIN_DATASET_MISMATCH'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.run_clinical_metrics WHERE evaluation_id=e.id) THEN RAISE EXCEPTION 'EVALUATION_METRICS_MISSING'; END IF;
 IF e.checkpoint_artifact_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.artifacts WHERE id=e.checkpoint_artifact_id AND run_id=e.training_run_id) THEN RAISE EXCEPTION 'CHECKPOINT_TRAIN_MISMATCH'; END IF;
 IF e.model_version_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.model_versions WHERE id=e.model_version_id AND checkpoint_artifact_id=e.checkpoint_artifact_id) THEN RAISE EXCEPTION 'CHECKPOINT_VERSION_MISMATCH'; END IF;
 IF e.threshold_source='validation_calibration' AND NOT EXISTS(SELECT 1 FROM public.run_threshold_calibration WHERE run_threshold_calibration_id=e.calibration_id AND calibration_split='val' AND threshold_selected=e.threshold_used AND run_id=e.training_run_id) THEN RAISE EXCEPTION 'CALIBRATION_LINEAGE_MISMATCH'; END IF;
 IF e.source_kind='e10' AND NOT EXISTS(SELECT 1 FROM public.train_execution_records WHERE run_id=e.run_id AND event_id=e.source_event_id AND kind=e.event_kind AND phase=e.event_phase AND record_key=e.event_key) THEN RAISE EXCEPTION 'EVENT_LINEAGE_MISMATCH'; END IF;
 IF e.source_kind='assessment' THEN
 SELECT i.* INTO ai FROM public.assessment_attempts a JOIN public.assessment_identities i ON i.id=a.identity_id WHERE a.id=e.source_assessment_attempt_id;
 SELECT state INTO ast FROM public.assessment_attempts WHERE id=e.source_assessment_attempt_id;
 IF ai.id IS NULL OR ast IS DISTINCT FROM 'verified' OR ai.kind<>'evaluate' OR ai.training_run_id IS DISTINCT FROM e.training_run_id OR ai.identity->>'split' IS DISTINCT FROM e.split OR ai.identity->>'purpose' IS DISTINCT FROM e.purpose THEN RAISE EXCEPTION 'ASSESSMENT_PROJECTION_MISMATCH'; END IF;
 IF e.split='test' AND NOT EXISTS(SELECT 1 FROM public.assessment_final_locks l WHERE l.identity_hash=ai.identity_hash AND l.evidence->'candidate'=ai.identity->'model' AND l.evidence->'decision'=ai.identity->'decision') THEN RAISE EXCEPTION 'TEST_FINAL_LOCK_REQUIRED'; END IF;
 END IF;
 SELECT count(*),sum(weight) INTO n,w FROM public.evaluation_ensemble_members WHERE evaluation_id=e.id;
 IF (e.subject_kind='single' AND n<>0) OR (e.subject_kind='ensemble' AND (n<2 OR w IS DISTINCT FROM 1::numeric)) THEN RAISE EXCEPTION 'ENSEMBLE_INVALID'; END IF;
 IF EXISTS(SELECT 1 FROM public.evaluation_ensemble_members m JOIN public.model_versions v ON v.id=m.model_version_id JOIN public.runs tr ON tr.id=v.training_run_id WHERE m.evaluation_id=e.id AND (v.checkpoint_artifact_id IS DISTINCT FROM m.checkpoint_artifact_id OR tr.dataset_version_id IS DISTINCT FROM r.dataset_version_id)) THEN RAISE EXCEPTION 'ENSEMBLE_LINEAGE_MISMATCH'; END IF;
 RETURN NULL;
END $$;

CREATE FUNCTION public.v2_immutable() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$ BEGIN RAISE EXCEPTION 'V2_SCIENTIFIC_EVIDENCE_IMMUTABLE'; END $$;

CREATE FUNCTION public.v2_run_configuration_required() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$ BEGIN
 IF NEW.run_type='training' AND NOT EXISTS(SELECT 1 FROM public.run_configurations WHERE run_id=NEW.id) THEN RAISE EXCEPTION 'TRAIN_CONFIGURATION_REQUIRED'; END IF;
 RETURN NULL;
END $$;

CREATE FUNCTION public.v2_xai_artifact_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$ BEGIN
 IF TG_OP='DELETE' OR (to_jsonb(NEW)-'availability') IS DISTINCT FROM (to_jsonb(OLD)-'availability') THEN RAISE EXCEPTION 'XAI_ARTIFACT_IMMUTABLE'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.v2_xai_artifact_source_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE e public.xai_evidence%ROWTYPE; p jsonb;
BEGIN
 SELECT * INTO STRICT e FROM public.xai_evidence WHERE id=NEW.evidence_id;
 IF NEW.artifact_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.artifacts a WHERE a.id=NEW.artifact_id AND a.checksum=NEW.sha256 AND a.file_size_bytes=NEW.byte_size AND (a.path=NEW.storage_uri OR a.artifact_uri=NEW.storage_uri)) THEN RAISE EXCEPTION 'XAI_ARTIFACT_REFERENCE_MISMATCH'; END IF;
 IF NEW.assessment_artifact_id IS NOT NULL THEN
 SELECT a.payload INTO p FROM public.assessment_artifacts a WHERE a.artifact_id=NEW.assessment_artifact_id AND a.attempt_id=e.assessment_attempt_id AND a.sample_id=e.assessment_sample_id;
 IF p IS NULL OR p->>'sha256' IS DISTINCT FROM NEW.sha256 OR (p->>'bytes')::bigint IS DISTINCT FROM NEW.byte_size OR p->>'path' IS DISTINCT FROM NEW.storage_uri THEN RAISE EXCEPTION 'XAI_ASSESSMENT_ARTIFACT_MISMATCH'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.v2_xai_lineage_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE v public.model_versions%ROWTYPE; method_key text; training_id uuid;
BEGIN
 SELECT method INTO STRICT method_key FROM public.xai_method_configurations WHERE id=NEW.method_configuration_id;
 IF method_key='shap' AND (NEW.background_manifest_uri IS NULL OR NEW.background_manifest_sha256 IS NULL) THEN RAISE EXCEPTION 'XAI_SHAP_BACKGROUND_REQUIRED'; END IF;
 IF NEW.model_version_id IS NOT NULL THEN
 SELECT * INTO STRICT v FROM public.model_versions WHERE id=NEW.model_version_id;
 IF v.checkpoint_artifact_id IS DISTINCT FROM NEW.checkpoint_artifact_id OR v.artifact_sha256 IS DISTINCT FROM NEW.checkpoint_sha256 THEN RAISE EXCEPTION 'XAI_MODEL_CHECKPOINT_MISMATCH'; END IF;
 training_id:=v.training_run_id;
 ELSE
 SELECT a.run_id INTO training_id FROM public.artifacts a JOIN public.runs r ON r.id=a.run_id WHERE a.id=NEW.checkpoint_artifact_id AND a.checksum=NEW.checkpoint_sha256 AND r.run_type='training';
 IF training_id IS NULL OR training_id IS DISTINCT FROM NEW.run_id THEN RAISE EXCEPTION 'XAI_PROVISIONAL_CHECKPOINT_MISMATCH'; END IF;
 END IF;
 IF NEW.ml_explanation_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.explainability_results x WHERE x.id=NEW.ml_explanation_id AND x.run_id IS NOT DISTINCT FROM NEW.run_id AND x.prediction_id IS NOT DISTINCT FROM NEW.prediction_id AND lower(x.method)=method_key) THEN RAISE EXCEPTION 'XAI_ML_LINEAGE_MISMATCH'; END IF;
 IF NEW.cell_explanation_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.cell_explanations x WHERE x.id=NEW.cell_explanation_id AND x.cell_prediction_id=NEW.cell_prediction_id AND lower(x.method)=method_key) THEN RAISE EXCEPTION 'XAI_CELL_LINEAGE_MISMATCH'; END IF;
 IF NEW.prediction_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.predictions p WHERE p.id=NEW.prediction_id AND coalesce(p.model_version_id,p.classifier_model_version_id)=NEW.model_version_id) THEN RAISE EXCEPTION 'XAI_PREDICTION_MODEL_MISMATCH'; END IF;
 IF NEW.dataset_source_record_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.dataset_source_records d WHERE d.id=NEW.dataset_source_record_id AND d.source_file_sha256=NEW.input_sha256) THEN RAISE EXCEPTION 'XAI_SOURCE_IMAGE_MISMATCH'; END IF;
 IF NEW.assessment_attempt_id IS NOT NULL AND NEW.assessment_sample_id IS DISTINCT FROM NEW.dataset_source_record_id THEN RAISE EXCEPTION 'XAI_ASSESSMENT_SAMPLE_MISMATCH'; END IF;
 IF NEW.assessment_attempt_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.assessment_attempts aa JOIN public.assessment_identities ai ON ai.id=aa.identity_id WHERE aa.id=NEW.assessment_attempt_id AND ai.kind='explain' AND ai.training_run_id=training_id AND ai.identity#>>'{explanation,method}'=method_key AND (ai.identity#>>'{explanation,class}')::smallint=NEW.target_class AND ai.identity#>>'{model,sha256}'=NEW.checkpoint_sha256) THEN RAISE EXCEPTION 'XAI_ASSESSMENT_MODEL_MISMATCH'; END IF;
 IF NEW.cell_prediction_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.cell_predictions p JOIN public.cell_classification_inputs i ON i.id=p.classification_input_id JOIN public.cell_classification_runs cr ON cr.id=p.classification_run_id WHERE p.id=NEW.cell_prediction_id AND cr.model_registry_id=NEW.model_version_id AND i.microscopy_image_id=NEW.microscopy_image_id AND i.crop_sha256=NEW.input_sha256) THEN RAISE EXCEPTION 'XAI_CROP_MISMATCH'; END IF;
 IF NEW.evaluation_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.evaluations e WHERE e.id=NEW.evaluation_id AND (((e.model_version_id=NEW.model_version_id OR (e.model_version_id IS NULL AND e.training_run_id=training_id)) AND e.checkpoint_artifact_id=NEW.checkpoint_artifact_id) OR (e.subject_kind='ensemble' AND EXISTS(SELECT 1 FROM public.evaluation_ensemble_members em WHERE em.evaluation_id=e.id AND em.model_version_id=NEW.model_version_id AND em.checkpoint_artifact_id=NEW.checkpoint_artifact_id)))) THEN RAISE EXCEPTION 'XAI_EVALUATION_MISMATCH'; END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.validate_cell_classification_input_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
      source_cell_index INTEGER;
      source_cell_code VARCHAR(40);
      source_image_sequence INTEGER;
      source_detector_key VARCHAR(80);
      source_detector_version VARCHAR(40);
      source_algorithm_version VARCHAR(80);
      source_crop_id UUID;
      source_crop_sha256 CHAR(64);
      source_crop_width INTEGER;
      source_crop_height INTEGER;
    BEGIN
      SELECT
        detection.cell_index,
        detection.cell_code,
        image.sequence_number,
        run.detector_key,
        run.detector_version,
        run.algorithm_version,
        crop.id,
        crop.sha256,
        crop.width_px,
        crop.height_px
      INTO
        source_cell_index,
        source_cell_code,
        source_image_sequence,
        source_detector_key,
        source_detector_version,
        source_algorithm_version,
        source_crop_id,
        source_crop_sha256,
        source_crop_width,
        source_crop_height
      FROM cell_detections detection
      JOIN cell_detection_runs run
        ON run.id=detection.detection_run_id
      JOIN microscopy_analysis_run_images image
        ON image.id=detection.analysis_run_image_id
      LEFT JOIN cell_crops crop
        ON crop.cell_detection_id=detection.id
      WHERE detection.id=NEW.cell_detection_id
        AND detection.detection_run_id=NEW.detection_run_id
        AND detection.microscopy_image_id=NEW.microscopy_image_id
      FOR SHARE OF detection,run,image;

      IF source_cell_index IS NULL
        OR NEW.cell_index IS DISTINCT FROM source_cell_index
        OR NEW.cell_code IS DISTINCT FROM source_cell_code
        OR NEW.image_sequence_number IS DISTINCT FROM source_image_sequence
        OR NEW.detector_key IS DISTINCT FROM source_detector_key
        OR NEW.detector_version IS DISTINCT FROM source_detector_version
        OR NEW.detector_algorithm_version
          IS DISTINCT FROM source_algorithm_version
        OR NEW.crop_id IS DISTINCT FROM source_crop_id
        OR NEW.crop_sha256 IS DISTINCT FROM source_crop_sha256
        OR NEW.crop_width_px IS DISTINCT FROM source_crop_width
        OR NEW.crop_height_px IS DISTINCT FROM source_crop_height
      THEN
        RAISE EXCEPTION
          'classification input does not match immutable detection/crop metadata'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $$;

CREATE OR REPLACE FUNCTION public.validate_cell_classification_insert_state() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
      run_status VARCHAR(30);
      declared_count INTEGER;
      existing_count INTEGER;
    BEGIN
      IF TG_TABLE_NAME = 'cell_classification_inputs' THEN
        SELECT status,input_count
        INTO run_status,declared_count
        FROM cell_classification_runs
        WHERE id=NEW.classification_run_id
        FOR SHARE;
        IF run_status IS DISTINCT FROM 'created' THEN
          RAISE EXCEPTION
            'cell classification inputs require a created run'
            USING ERRCODE = '55000';
        END IF;
        SELECT count(*)
        INTO existing_count
        FROM cell_classification_inputs
        WHERE classification_run_id=NEW.classification_run_id;
      ELSIF TG_TABLE_NAME = 'cell_predictions' THEN
        SELECT status,eligible_count
        INTO run_status,declared_count
        FROM cell_classification_runs
        WHERE id=NEW.classification_run_id
        FOR SHARE;
        IF run_status IS DISTINCT FROM 'processing' THEN
          RAISE EXCEPTION
            'cell predictions require a processing run'
            USING ERRCODE = '55000';
        END IF;
        SELECT count(*)
        INTO existing_count
        FROM cell_predictions
        WHERE classification_run_id=NEW.classification_run_id;
      ELSIF TG_TABLE_NAME = 'smear_analysis_summaries' THEN
        SELECT status,1
        INTO run_status,declared_count
        FROM cell_classification_runs
        WHERE id=NEW.classification_run_id
        FOR SHARE;
        IF run_status IS DISTINCT FROM 'processing' THEN
          RAISE EXCEPTION
            'smear analysis summary requires a processing run'
            USING ERRCODE = '55000';
        END IF;
        SELECT count(*)
        INTO existing_count
        FROM smear_analysis_summaries
        WHERE classification_run_id=NEW.classification_run_id;
      ELSE
        RAISE EXCEPTION 'unsupported guarded classification table'
          USING ERRCODE = '55000';
      END IF;

      IF run_status IS NULL THEN
        RAISE EXCEPTION 'classification run does not exist'
          USING ERRCODE = '23503';
      END IF;
      IF existing_count >= declared_count THEN
        RAISE EXCEPTION
          'classification child rows exceed the frozen run count'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $$;

CREATE OR REPLACE FUNCTION public.validate_cell_classification_review() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
      automatic_status VARCHAR(20);
      automatic_label VARCHAR(20);
    BEGIN
      SELECT prediction_status,predicted_label
      INTO automatic_status,automatic_label
      FROM cell_predictions
      WHERE id=NEW.cell_prediction_id
      FOR SHARE;
      IF automatic_status IS NULL THEN
        RAISE EXCEPTION 'cell prediction does not exist'
          USING ERRCODE = '23503';
      END IF;
      IF automatic_status <> 'completed' THEN
        RAISE EXCEPTION
          'failed cell predictions cannot be reviewed'
          USING ERRCODE = '23514';
      END IF;
      IF NEW.decision = 'confirmed'
        AND NEW.reviewed_label IS NOT NULL
        AND NEW.reviewed_label IS DISTINCT FROM automatic_label
      THEN
        RAISE EXCEPTION
          'confirmed label must match the immutable automatic prediction'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $$;

CREATE OR REPLACE FUNCTION public.validate_cell_classification_run_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
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
      RETURN NEW;
    END;
    $$;

CREATE OR REPLACE FUNCTION public.validate_cell_explanation_contract() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
      prediction_status VARCHAR(20);
      prediction_class SMALLINT;
      prediction_preprocessing JSONB;
      source_analysis_run_id UUID;
      source_classification_run_id UUID;
      source_cell_detection_id UUID;
      source_input_width INTEGER;
      source_input_height INTEGER;
      expected_heatmap_key TEXT;
      expected_overlay_key TEXT;
    BEGIN
      SELECT
        prediction.prediction_status,
        prediction.predicted_class_index,
        prediction.preprocessing_snapshot,
        run.analysis_run_id,
        prediction.classification_run_id,
        prediction.cell_detection_id,
        (run.model_snapshot->>'input_width')::INTEGER,
        (run.model_snapshot->>'input_height')::INTEGER
      INTO
        prediction_status,
        prediction_class,
        prediction_preprocessing,
        source_analysis_run_id,
        source_classification_run_id,
        source_cell_detection_id,
        source_input_width,
        source_input_height
      FROM cell_predictions prediction
      JOIN cell_classification_runs run
        ON run.id=prediction.classification_run_id
      WHERE prediction.id=NEW.cell_prediction_id
      FOR SHARE OF prediction,run;

      IF prediction_status IS DISTINCT FROM 'completed'
        OR NEW.parameters_json->>'method' IS DISTINCT FROM 'gradcam'
        OR NEW.parameters_json->>'method_version'
          IS DISTINCT FROM NEW.method_version
        OR NEW.parameters_json->>'target_class_index'
          IS DISTINCT FROM prediction_class::text
        OR NEW.parameters_json->>'positive_class_index'
          IS DISTINCT FROM '1'
        OR NEW.parameters_json->'preprocessing'
          IS DISTINCT FROM prediction_preprocessing
      THEN
        RAISE EXCEPTION
          'cell explanation does not match the immutable prediction contract'
          USING ERRCODE = '23514';
      END IF;

      IF NEW.status='generated' THEN
        expected_heatmap_key := format(
          'cell-explanations/%s/%s/%s/gradcam_heatmap.png',
          source_analysis_run_id,
          source_classification_run_id,
          source_cell_detection_id
        );
        expected_overlay_key := format(
          'cell-explanations/%s/%s/%s/gradcam_overlay.png',
          source_analysis_run_id,
          source_classification_run_id,
          source_cell_detection_id
        );
        IF NEW.heatmap_storage_key IS DISTINCT FROM expected_heatmap_key
          OR NEW.overlay_storage_key IS DISTINCT FROM expected_overlay_key
          OR NEW.width_px IS DISTINCT FROM source_input_width
          OR NEW.height_px IS DISTINCT FROM source_input_height
        THEN
          RAISE EXCEPTION
            'generated explanation artifact lineage is inconsistent'
            USING ERRCODE = '23514';
        END IF;
      END IF;
      RETURN NEW;
    END;
    $$;

CREATE OR REPLACE FUNCTION public.validate_cell_prediction_input() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
      input_eligible BOOLEAN;
      run_snapshot JSONB;
      snapshot_threshold DOUBLE PRECISION;
      snapshot_review_margin DOUBLE PRECISION;
    BEGIN
      SELECT input.eligible,run.model_snapshot
      INTO input_eligible,run_snapshot
      FROM cell_classification_inputs input
      JOIN cell_classification_runs run
        ON run.id=input.classification_run_id
      WHERE input.id = NEW.classification_input_id
        AND input.classification_run_id = NEW.classification_run_id
        AND input.cell_detection_id = NEW.cell_detection_id
        AND input.crop_id = NEW.crop_id
      FOR SHARE OF input,run;
      IF input_eligible IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION
          'cell prediction requires an eligible frozen input'
          USING ERRCODE = '23514';
      END IF;
      snapshot_threshold :=
        (run_snapshot->>'threshold')::DOUBLE PRECISION;
      snapshot_review_margin :=
        (run_snapshot->>'review_margin')::DOUBLE PRECISION;
      IF abs(NEW.threshold_used - snapshot_threshold) > 1e-12
        OR NEW.threshold_source
          IS DISTINCT FROM run_snapshot->>'threshold_source'
        OR NEW.preprocessing_snapshot
          IS DISTINCT FROM run_snapshot->'preprocessing'
        OR NEW.positive_label
          IS DISTINCT FROM run_snapshot->>'positive_label'
        OR NEW.positive_class_index::text
          IS DISTINCT FROM run_snapshot->>'positive_class_index'
        OR (
          NEW.prediction_status='completed'
          AND NEW.near_threshold IS DISTINCT FROM
            (NEW.decision_margin <= snapshot_review_margin)
        )
      THEN
        RAISE EXCEPTION
          'cell prediction does not match the frozen model policy'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $$;

CREATE OR REPLACE FUNCTION public.validate_deployed_model_version() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    version_status TEXT;
    version_sha256 TEXT;
    version_size BIGINT;
    artifact_checksum TEXT;
    artifact_size BIGINT;
    physical_status TEXT;
    calibrated_threshold NUMERIC;
    is_stage2 BOOLEAN;
    is_technical_production BOOLEAN;
BEGIN
    SELECT mv.status,mv.artifact_sha256,mv.artifact_size_bytes,LOWER(a.checksum),
           a.file_size_bytes,a.artifact_status
      INTO version_status,version_sha256,version_size,artifact_checksum,
           artifact_size,physical_status
      FROM model_versions mv
      JOIN artifacts a ON a.id=mv.checkpoint_artifact_id
                      AND a.run_id=mv.training_run_id
     WHERE mv.id=NEW.model_version_id
       AND mv.checkpoint_artifact_id=NEW.checkpoint_artifact_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Deployment sin par version/artifact gobernado: version %, artifact %',
            NEW.model_version_id,NEW.checkpoint_artifact_id USING ERRCODE='23503';
    END IF;

    IF NEW.artifact_size_bytes IS NULL THEN NEW.artifact_size_bytes:=version_size; END IF;
    IF LOWER(NEW.artifact_sha256) IS DISTINCT FROM version_sha256
       OR version_sha256 IS DISTINCT FROM artifact_checksum THEN
        RAISE EXCEPTION 'SHA-256 de deployment, model_version y artifact no coincide'
            USING ERRCODE='23514';
    END IF;
    IF NEW.artifact_size_bytes IS DISTINCT FROM version_size
       OR version_size IS DISTINCT FROM artifact_size THEN
        RAISE EXCEPTION 'Tamaño de deployment, model_version y artifact no coincide'
            USING ERRCODE='23514';
    END IF;

    IF NEW.threshold_calibration_id IS NOT NULL THEN
        SELECT threshold_selected INTO calibrated_threshold
          FROM run_threshold_calibration
         WHERE run_threshold_calibration_id=NEW.threshold_calibration_id
           AND model_version_id=NEW.model_version_id;
        IF calibrated_threshold IS DISTINCT FROM NEW.threshold_value THEN
            RAISE EXCEPTION 'threshold_value (%) no coincide con calibración % (%)',
                NEW.threshold_value,NEW.threshold_calibration_id,calibrated_threshold
                USING ERRCODE='23514';
        END IF;
    END IF;

    IF NEW.status='active' THEN
        is_stage2:=NEW.environment='stage2' AND NEW.alias='default';
        is_technical_production:=NEW.environment='production' AND NEW.alias='champion'
          AND COALESCE(NEW.metadata->>'production_scope','')='stage2_technical';
        IF is_stage2 OR is_technical_production THEN
            IF version_status NOT IN ('candidate','validated','approved','deployed') THEN
                RAISE EXCEPTION 'Model version % no apta para Etapa 2',version_status
                    USING ERRCODE='23514';
            END IF;
            IF COALESCE(NEW.metadata#>>'{stage2,eligible}','false')<>'true'
               OR COALESCE(NEW.metadata#>>'{technical_smoke_test,status}',
                           NEW.metadata#>>'{stage2_smoke_test,status}','')<>'PASS' THEN
                RAISE EXCEPTION 'Etapa 2 exige elegibilidad técnica y smoke PASS'
                    USING ERRCODE='23514';
            END IF;
        ELSIF version_status NOT IN ('approved','deployed') THEN
            RAISE EXCEPTION 'Solo una model_version approved/deployed puede activarse; estado actual %',
                version_status USING ERRCODE='23514';
        END IF;
        IF physical_status IS DISTINCT FROM 'available' THEN
            RAISE EXCEPTION 'El artifact debe estar available para activar; estado actual %',
                physical_status USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.validate_image_analysis_job() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    inference_type TEXT;
    deployment_status TEXT;
    deployment_threshold NUMERIC;
BEGIN
    SELECT run_type
    INTO inference_type
    FROM runs
    WHERE id = NEW.inference_run_id;

    IF inference_type IS DISTINCT FROM 'inference' THEN
        RAISE EXCEPTION
            'image_analysis_jobs.inference_run_id debe ser inference; recibió %',
            inference_type
            USING ERRCODE = '23514';
    END IF;

    SELECT status, threshold_value
    INTO deployment_status, deployment_threshold
    FROM deployed_model_versions
    WHERE id = NEW.deployed_model_version_id
      AND model_version_id = NEW.model_version_id;

    IF TG_OP = 'INSERT'
       OR NEW.inference_run_id IS DISTINCT FROM OLD.inference_run_id
       OR NEW.deployed_model_version_id IS DISTINCT FROM OLD.deployed_model_version_id
       OR NEW.model_version_id IS DISTINCT FROM OLD.model_version_id THEN
        IF deployment_status IS DISTINCT FROM 'active' THEN
            RAISE EXCEPTION
                'Un image_analysis_job nuevo exige deployment active; recibió %',
                deployment_status
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.status IN ('running', 'completed') THEN
        IF NEW.threshold_used IS NULL
           OR NEW.threshold_used IS DISTINCT FROM deployment_threshold THEN
            RAISE EXCEPTION
                'threshold_used del job debe coincidir con threshold_value del deployment (%)',
                deployment_threshold
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.validate_run_model_deployment() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    inference_type TEXT;
    deployment_status TEXT;
BEGIN
    SELECT run_type INTO inference_type FROM runs WHERE id = NEW.run_id;
    IF inference_type IS DISTINCT FROM 'inference' THEN
        RAISE EXCEPTION
            'run_model_deployments.run_id debe ser inference; recibió %',
            inference_type
            USING ERRCODE = '23514';
    END IF;

    IF TG_OP = 'INSERT'
       OR NEW.run_id IS DISTINCT FROM OLD.run_id
       OR NEW.deployed_model_version_id IS DISTINCT FROM OLD.deployed_model_version_id
       OR NEW.model_version_id IS DISTINCT FROM OLD.model_version_id THEN
        SELECT status
        INTO deployment_status
        FROM deployed_model_versions
        WHERE id = NEW.deployed_model_version_id
          AND model_version_id = NEW.model_version_id;

        IF deployment_status IS DISTINCT FROM 'active' THEN
            RAISE EXCEPTION
                'Un inference run solo puede vincular un deployment active; recibió %',
                deployment_status
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.validate_smear_analysis_summary() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
      source_analysis_run_id UUID;
      source_detection_run_id UUID;
      source_eligible_count INTEGER;
      actual_classified_count INTEGER;
      actual_parasitized_count INTEGER;
      actual_uninfected_count INTEGER;
      actual_near_count INTEGER;
      actual_failed_count INTEGER;
      actual_maximum DOUBLE PRECISION;
      actual_mean DOUBLE PRECISION;
      actual_median DOUBLE PRECISION;
      expected_outcome VARCHAR(40);
      actual_per_image JSONB;
      expected_policy CONSTANT JSONB := '{
        "version":"cell-candidate-aggregation-v1",
        "scope":"candidate_cells",
        "suspicious_when_any_parasitized": true,
        "near_threshold_makes_negative_inconclusive": true,
        "partial_failure_makes_negative_inconclusive": true,
        "terminology":"experimental_screening_not_diagnosis"
      }'::jsonb;
    BEGIN
      SELECT analysis_run_id,detection_run_id,eligible_count
      INTO
        source_analysis_run_id,
        source_detection_run_id,
        source_eligible_count
      FROM cell_classification_runs
      WHERE id=NEW.classification_run_id
      FOR SHARE;

      SELECT
        count(*) FILTER (WHERE prediction_status='completed'),
        count(*) FILTER (
          WHERE prediction_status='completed'
            AND predicted_label='parasitized'
        ),
        count(*) FILTER (
          WHERE prediction_status='completed'
            AND predicted_label='uninfected'
        ),
        count(*) FILTER (
          WHERE prediction_status='completed' AND near_threshold
        ),
        count(*) FILTER (WHERE prediction_status='failed'),
        max(probability_parasitized) FILTER (
          WHERE prediction_status='completed'
        ),
        avg(probability_parasitized) FILTER (
          WHERE prediction_status='completed'
        ),
        percentile_cont(0.5) WITHIN GROUP (
          ORDER BY probability_parasitized
        ) FILTER (WHERE prediction_status='completed')
      INTO
        actual_classified_count,
        actual_parasitized_count,
        actual_uninfected_count,
        actual_near_count,
        actual_failed_count,
        actual_maximum,
        actual_mean,
        actual_median
      FROM cell_predictions
      WHERE classification_run_id=NEW.classification_run_id;

      SELECT jsonb_build_object(
        'images',
        COALESCE(
          jsonb_agg(
            jsonb_build_object(
              'microscopy_image_id',per_image.microscopy_image_id::text,
              'image_sequence_number',per_image.image_sequence_number,
              'eligible_cell_count',per_image.eligible_cell_count,
              'classified_cell_count',per_image.classified_cell_count,
              'parasitized_candidate_count',
                per_image.parasitized_candidate_count,
              'uninfected_candidate_count',
                per_image.uninfected_candidate_count,
              'near_threshold_count',per_image.near_threshold_count,
              'failed_prediction_count',per_image.failed_prediction_count
            )
            ORDER BY
              per_image.image_sequence_number,
              per_image.microscopy_image_id
          ),
          '[]'::jsonb
        )
      )
      INTO actual_per_image
      FROM (
        SELECT
          input.microscopy_image_id,
          min(input.image_sequence_number) image_sequence_number,
          count(*)::INTEGER eligible_cell_count,
          count(prediction.id) FILTER (
            WHERE prediction.prediction_status='completed'
          )::INTEGER classified_cell_count,
          count(prediction.id) FILTER (
            WHERE prediction.prediction_status='completed'
              AND prediction.predicted_label='parasitized'
          )::INTEGER parasitized_candidate_count,
          count(prediction.id) FILTER (
            WHERE prediction.prediction_status='completed'
              AND prediction.predicted_label='uninfected'
          )::INTEGER uninfected_candidate_count,
          count(prediction.id) FILTER (
            WHERE prediction.prediction_status='completed'
              AND prediction.near_threshold
          )::INTEGER near_threshold_count,
          count(prediction.id) FILTER (
            WHERE prediction.prediction_status='failed'
          )::INTEGER failed_prediction_count
        FROM cell_classification_inputs input
        LEFT JOIN cell_predictions prediction
          ON prediction.classification_input_id=input.id
        WHERE input.classification_run_id=NEW.classification_run_id
          AND input.eligible
        GROUP BY input.microscopy_image_id
      ) per_image;

      IF actual_parasitized_count > 0 THEN
        expected_outcome := 'suspicious_cells_detected';
      ELSIF source_eligible_count > 0
        AND actual_classified_count=source_eligible_count
        AND actual_failed_count=0
        AND actual_near_count=0
      THEN
        expected_outcome := 'no_suspicious_cells_detected';
      ELSE
        expected_outcome := 'inconclusive';
      END IF;

      IF NEW.analysis_run_id IS DISTINCT FROM source_analysis_run_id
        OR NEW.detection_run_id IS DISTINCT FROM source_detection_run_id
        OR NEW.eligible_cell_count IS DISTINCT FROM source_eligible_count
        OR NEW.classified_cell_count IS DISTINCT FROM actual_classified_count
        OR NEW.parasitized_candidate_count
          IS DISTINCT FROM actual_parasitized_count
        OR NEW.uninfected_candidate_count
          IS DISTINCT FROM actual_uninfected_count
        OR NEW.near_threshold_count IS DISTINCT FROM actual_near_count
        OR NEW.failed_prediction_count IS DISTINCT FROM actual_failed_count
        OR NEW.outcome IS DISTINCT FROM expected_outcome
        OR NEW.per_image_summary IS DISTINCT FROM actual_per_image
        OR NEW.aggregation_policy_snapshot IS DISTINCT FROM expected_policy
        OR (
          actual_classified_count > 0
          AND (
            NEW.maximum_probability_parasitized IS NULL
            OR NEW.mean_probability_parasitized IS NULL
            OR NEW.median_probability_parasitized IS NULL
            OR abs(
              NEW.maximum_probability_parasitized - actual_maximum
            ) > 1e-12
            OR abs(NEW.mean_probability_parasitized - actual_mean) > 1e-12
            OR abs(NEW.median_probability_parasitized - actual_median) > 1e-12
          )
        )
      THEN
        RAISE EXCEPTION
          'smear analysis summary does not match immutable predictions'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $$;

CREATE OR REPLACE FUNCTION public.campaign_attempt_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE m record; c record; r record; cfg jsonb; rcfg jsonb; maximum integer; technical jsonb;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'ATTEMPT_HISTORY_IMMUTABLE'; END IF;
 -- Campaign lock first, shared with planning and members; then member serialization.
 SELECT c0.* INTO c FROM experimental_campaigns c0 JOIN campaign_members m0 ON m0.campaign_id=c0.id WHERE m0.id=NEW.member_id FOR UPDATE OF c0;
 SELECT * INTO m FROM campaign_members WHERE id=NEW.member_id FOR UPDATE;
 IF m.id IS NULL OR c.state NOT IN ('frozen','active','paused') THEN RAISE EXCEPTION 'ATTEMPT_REQUIRES_FROZEN_CAMPAIGN'; END IF;
 SELECT v.payload->'environment' INTO technical FROM campaign_technical_revisions v WHERE v.id=coalesce((SELECT revision_id FROM campaign_controlled_requests WHERE attempt_id=NEW.id AND campaign_id=c.id AND member_id=NEW.member_id),(SELECT revision_id FROM train_execution_revisions WHERE attempt_id=NEW.id AND campaign_id=c.id));
 IF TG_OP='INSERT' THEN
   SELECT coalesce(max(ordinal),0)+1 INTO maximum FROM campaign_attempts WHERE member_id=NEW.member_id;
   IF (c.state='paused' AND NOT EXISTS(SELECT 1 FROM campaign_controlled_requests WHERE attempt_id=NEW.id AND campaign_id=c.id AND member_id=NEW.member_id)) OR NEW.state<>'active' OR m.state NOT IN ('pending','failed','interrupted')
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
END $$;

CREATE OR REPLACE FUNCTION public.campaign_configuration_valid(v jsonb) RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE r jsonb; m jsonb; e jsonb; i jsonb; o jsonb; x jsonb; k text;
BEGIN
 IF NOT campaign_json_object(v,ARRAY['schema_version','model_id','adapter_version','resolved'])
   OR v->>'schema_version' IS DISTINCT FROM 'model_config_v1'
   OR NOT campaign_json_string(v->'model_id') OR NOT campaign_json_string(v->'adapter_version') THEN RETURN false; END IF;
 r=v->'resolved';
 IF NOT campaign_json_object(r,ARRAY['model','optimizer','execution','recipe','selection','input_contract']) THEN RETURN false; END IF;
 m=r->'model';e=r->'execution';i=r->'input_contract';o=r->'optimizer';
 IF NOT campaign_json_object(m,ARRAY['input_shape','preprocessing','weights','dropout','l2','head_units','batch_normalization','fine_tune_layers'])
   OR NOT campaign_json_object(o,ARRAY['name','parameters','fine_tune_learning_rate'])
   OR NOT campaign_json_string(o->'name') OR jsonb_typeof(o->'parameters') IS DISTINCT FROM 'object'
   OR jsonb_typeof(o->'fine_tune_learning_rate') IS DISTINCT FROM 'number'
   OR NOT campaign_json_object(e,ARRAY['max_epochs','fine_tune_epochs','batch_size','deterministic_ops','no_augment','checkpoint_policy','checkpoint_mode','min_recall','beta','reject_prediction_collapse','min_class_fraction','calibrate_threshold','target_recall','min_specificity','early_stopping','early_stopping_mode','early_stopping_patience','early_stopping_min_delta','restore_best_weights','evaluate_best_on_test'])
   OR e ? 'seed' OR e->'evaluate_best_on_test' IS DISTINCT FROM 'false'::jsonb
   OR NOT campaign_json_integer(e->'max_epochs',1) OR NOT campaign_json_integer(e->'fine_tune_epochs',0)
   OR NOT campaign_json_integer(e->'batch_size',1) OR NOT campaign_json_integer(e->'early_stopping_patience',0)
   OR NOT campaign_json_object(r->'recipe',ARRAY['loss','metrics','augmentation','reduce_lr','selection_threshold','fallback','clinical_success_independent_of_technical_completion'])
   OR NOT campaign_json_object(r->'selection',ARRAY['monitor','mode','explicit','early_stopping_monitor','early_stopping_mode','threshold','beta','clinical_objective','fallback'])
   OR NOT campaign_json_object(i,ARRAY['schema_version','architecture','adapter_version','shape','dtype','channels','source_order','source_scale','decode','resize','external','internal','label_mapping','output'])
   THEN RETURN false; END IF;
 FOREACH k IN ARRAY ARRAY['preprocessing','weights','batch_normalization'] LOOP
   IF NOT campaign_json_string(m->k) THEN RETURN false; END IF;
 END LOOP;
 IF jsonb_typeof(m->'dropout') IS DISTINCT FROM 'number' OR jsonb_typeof(m->'l2') IS DISTINCT FROM 'number'
   OR NOT campaign_json_integer(m->'head_units',0) OR NOT campaign_json_integer(m->'fine_tune_layers',0)
   THEN RETURN false; END IF;
 FOREACH k IN ARRAY ARRAY['deterministic_ops','no_augment','reject_prediction_collapse','calibrate_threshold','early_stopping','restore_best_weights'] LOOP
   IF jsonb_typeof(e->k) IS DISTINCT FROM 'boolean' THEN RETURN false; END IF;
 END LOOP;
 FOREACH k IN ARRAY ARRAY['min_recall','beta','min_class_fraction','target_recall','min_specificity','early_stopping_min_delta'] LOOP
   IF jsonb_typeof(e->k) IS DISTINCT FROM 'number' THEN RETURN false; END IF;
 END LOOP;
 FOREACH k IN ARRAY ARRAY['checkpoint_policy','checkpoint_mode','early_stopping_mode'] LOOP
   IF NOT campaign_json_string(e->k) THEN RETURN false; END IF;
 END LOOP;
 -- Monitor values are optional in E2; presence is mandatory, JSON null is allowed.
 FOREACH k IN ARRAY ARRAY['checkpoint_monitor','early_stopping_monitor'] LOOP
   IF NOT (e ? k) OR (e->k<>'null'::jsonb AND NOT campaign_json_string(e->k)) THEN RETURN false; END IF;
 END LOOP;
 IF NOT campaign_json_string(r->'recipe'->'loss') OR NOT campaign_json_string(r->'recipe'->'metrics')
   OR jsonb_typeof(r->'recipe'->'augmentation') IS DISTINCT FROM 'object'
   OR jsonb_typeof(r->'recipe'->'reduce_lr') IS DISTINCT FROM 'object'
   OR jsonb_typeof(r->'recipe'->'selection_threshold') IS DISTINCT FROM 'number'
   OR NOT campaign_json_string(r->'recipe'->'fallback')
   OR r->'recipe'->'clinical_success_independent_of_technical_completion' IS DISTINCT FROM 'true'::jsonb
   OR jsonb_typeof(r->'selection'->'explicit') IS DISTINCT FROM 'boolean'
   OR jsonb_typeof(r->'selection'->'threshold') IS DISTINCT FROM 'number'
   OR jsonb_typeof(r->'selection'->'beta') IS DISTINCT FROM 'number' THEN RETURN false; END IF;
 FOREACH k IN ARRAY ARRAY['monitor','mode','early_stopping_monitor','early_stopping_mode','clinical_objective','fallback'] LOOP
   IF NOT campaign_json_string(r->'selection'->k) THEN RETURN false; END IF;
 END LOOP;
 IF i->>'schema_version' IS DISTINCT FROM 'malaria_input_v1'
   OR i->>'architecture' IS DISTINCT FROM v->>'model_id' OR i->>'adapter_version' IS DISTINCT FROM v->>'adapter_version'
   OR i->>'dtype' IS DISTINCT FROM 'float32' OR i->'channels' IS DISTINCT FROM '3'::jsonb
   OR i->>'source_order' IS DISTINCT FROM 'RGB' OR i->>'source_scale' IS DISTINCT FROM '0_255'
   OR i->>'decode' IS DISTINCT FROM 'tf_decode_image_rgb_v1'
   OR i->'resize' IS DISTINCT FROM '{"method":"bilinear","antialias": false,"location":"loader"}'::jsonb
   OR NOT campaign_json_object(i->'external',ARRAY['mode','version','location','output_order'])
   OR jsonb_typeof(i->'internal') IS DISTINCT FROM 'object'
   OR NOT ((i->'internal') ?& ARRAY['mode','location'])
   OR NOT campaign_json_object(i->'output',ARRAY['shape','dtype','meaning','activation'])
   OR i->'label_mapping' IS DISTINCT FROM '{"0":"uninfected","1":"parasitized","positive_class": 1,"positive_label":"parasitized"}'::jsonb
   OR jsonb_typeof(m->'input_shape') IS DISTINCT FROM 'array' OR jsonb_array_length(m->'input_shape')<>3
   OR jsonb_typeof(i->'shape') IS DISTINCT FROM 'array' OR jsonb_array_length(i->'shape')<>4
   OR i->'shape'->0 IS DISTINCT FROM 'null'::jsonb
   THEN RETURN false; END IF;
 FOR x IN SELECT value FROM jsonb_array_elements(m->'input_shape') LOOP
   IF NOT campaign_json_integer(x,1) THEN RETURN false; END IF;
 END LOOP;
 RETURN ((i->'shape') - 0) = m->'input_shape' AND (m->'input_shape'->2)='3'::jsonb
   AND i->'external'->>'mode'=m->>'preprocessing';
END $$;

CREATE OR REPLACE FUNCTION public.campaign_run_identity_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM campaign_attempts WHERE training_run_id=OLD.id) AND
   (NEW.model_id IS DISTINCT FROM OLD.model_id
    OR NEW.run_type IS DISTINCT FROM OLD.run_type OR NEW.dataset_version_id IS DISTINCT FROM OLD.dataset_version_id
    OR NEW.random_seed IS DISTINCT FROM OLD.random_seed OR NEW.experiment_id IS DISTINCT FROM OLD.experiment_id
    OR NEW.execution_parameters->'model_configuration_e2'->'configuration' IS DISTINCT FROM OLD.execution_parameters->'model_configuration_e2'->'configuration'
    OR NEW.execution_parameters->'model_configuration_e2'->'dataset' IS DISTINCT FROM OLD.execution_parameters->'model_configuration_e2'->'dataset'
    OR campaign_environment_identity(NEW.execution_parameters->'model_configuration_e2'->'environment') IS DISTINCT FROM
       campaign_environment_identity(OLD.execution_parameters->'model_configuration_e2'->'environment'))
 THEN RAISE EXCEPTION 'LINKED_TRAIN_IDENTITY_IMMUTABLE'; END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.campaign_technical_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
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
    OR ((e-ARRAY['source_sha256','git_commit']) IS DISTINCT FROM (c.environment-ARRAY['source_sha256','git_commit']) AND NOT (e->>'execution_mode'='local_python' AND e->>'platform'='Darwin' AND e->>'machine'='arm64' AND e->>'device'='CPU' AND e->>'precision'='float32' AND jsonb_typeof(e->'packages')='object' AND e->'packages'<>'{}'::jsonb AND jsonb_typeof(e->'determinism_environment')='object') IS TRUE)
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

CREATE FUNCTION public.e04_calibration_complete() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
BEGIN
 IF TG_TABLE_NAME='evaluations' THEN
   PERFORM public.e04_assert_calibration(NEW.id);
 ELSE
   PERFORM public.e04_assert_calibration(NEW.default_evaluation_id);
   PERFORM public.e04_assert_calibration(NEW.selected_evaluation_id);
 END IF;
 RETURN NULL;
END $$;

CREATE OR REPLACE FUNCTION public.experiment_reservation_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
BEGIN
 PERFORM experiment_require_owner();
 IF TG_OP='INSERT' THEN
  IF TG_TABLE_NAME='assessment_attempts' AND EXISTS(SELECT 1 FROM train_execution_sessions WHERE state IN ('active','completed'))
  THEN RAISE EXCEPTION 'GLOBAL_TRAIN_ALREADY_ACTIVE'; END IF;
  IF TG_TABLE_NAME IN ('train_execution_sessions','campaign_attempts') AND EXISTS(SELECT 1 FROM assessment_attempts WHERE state='active')
  THEN RAISE EXCEPTION 'GLOBAL_ASSESSMENT_ALREADY_ACTIVE'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.train_event_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
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

CREATE OR REPLACE FUNCTION public.campaign_contract_valid(v jsonb) RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE p jsonb; b jsonb; matrix jsonb; seeds jsonb; configs jsonb; members jsonb;
 env jsonb; x jsonb; item record; seen_seeds jsonb='[]'; descriptor jsonb; k text;
 n integer; idx integer=0;
BEGIN
 -- experiment_id alone is intentionally nullable; its presence remains mandatory.
 IF NOT campaign_json_object(v,ARRAY['version','name','purpose','dataset','dataset_evidence_id','requested','protocol','environment','matrix'])
   OR NOT (v ? 'experiment_id') OR v->>'version' IS DISTINCT FROM 'campaign_contract_v1'
   OR NOT campaign_json_string(v->'name') OR NOT campaign_json_string(v->'purpose')
   OR NOT campaign_json_string(v->'dataset_evidence_id')
   OR NOT campaign_json_object(v->'dataset',ARRAY['dataset_version_id','dataset_materialization_id','dataset_root','patient_assignment_fingerprint','record_assignment_fingerprint','source_population_fingerprint','clinical_identity_fingerprint','counts','selection_unit'])
   OR jsonb_typeof(v->'requested') IS DISTINCT FROM 'object' THEN RETURN false; END IF;
 p=v->'protocol';
 IF NOT campaign_json_object(p,ARRAY['version','objective','metrics','sensitivity_target','specificity_minimum','roles','ranking','checkpoint','early_stopping','calibration','budget','missing','retries','fallback','test_access','aggregation','uncertainty','limitations','pending'])
   OR NOT campaign_json_string(p->'version') OR NOT campaign_json_string(p->'objective')
   OR p->'pending' IS DISTINCT FROM '[]'::jsonb
   OR p->'roles' IS DISTINCT FROM '{"train":"train","selection":"val","calibration":"val","final_test":"test"}'::jsonb
   OR p->>'test_access' IS DISTINCT FROM 'final_only_after_candidate_lock'
   OR p->>'retries' IS DISTINCT FROM 'first_verified_attempt'
   OR p->>'missing' IS DISTINCT FROM 'report_all_members' OR p->>'fallback' IS DISTINCT FROM 'diagnostic_only'
   OR jsonb_typeof(p->'sensitivity_target') IS DISTINCT FROM 'number'
   OR jsonb_typeof(p->'specificity_minimum') IS DISTINCT FROM 'number' THEN RETURN false; END IF;
 IF (p->>'sensitivity_target')::numeric NOT BETWEEN 0 AND 1 OR (p->>'specificity_minimum')::numeric NOT BETWEEN 0 AND 1 THEN RETURN false; END IF;
 b=p->'budget';
 IF NOT campaign_json_object(b,ARRAY['max_members','max_attempts_per_member'])
   OR NOT campaign_json_integer(b->'max_members',1) OR NOT campaign_json_integer(b->'max_attempts_per_member',1)
   OR NOT campaign_json_object(p->'metrics',ARRAY['primary','secondary','definitions_version','compliance'])
   OR jsonb_typeof(p->'metrics'->'primary') IS DISTINCT FROM 'array' OR jsonb_array_length(p->'metrics'->'primary')=0
   OR jsonb_typeof(p->'metrics'->'secondary') IS DISTINCT FROM 'array'
   OR NOT campaign_json_string(p->'metrics'->'definitions_version')
   OR p->'metrics'->>'compliance' NOT IN ('point_estimate','confidence_bound')
   OR NOT campaign_json_object(p->'ranking',ARRAY['partition','criteria','tie_breaks'])
   OR p->'ranking'->>'partition' IS DISTINCT FROM 'val'
   OR jsonb_typeof(p->'ranking'->'criteria') IS DISTINCT FROM 'array' OR jsonb_array_length(p->'ranking'->'criteria')=0
   OR jsonb_typeof(p->'ranking'->'tie_breaks') IS DISTINCT FROM 'array' OR jsonb_array_length(p->'ranking'->'tie_breaks')=0
   OR NOT campaign_json_object(p->'checkpoint',ARRAY['policy','monitor','mode','threshold'])
   OR p->'checkpoint'->'threshold' IS DISTINCT FROM '0.5'::jsonb
   OR NOT campaign_json_object(p->'early_stopping',ARRAY['enabled','monitor','mode','patience','min_delta','restore_best_weights'])
   OR jsonb_typeof(p->'early_stopping'->'enabled') IS DISTINCT FROM 'boolean'
   OR jsonb_typeof(p->'early_stopping'->'restore_best_weights') IS DISTINCT FROM 'boolean'
   OR NOT campaign_json_integer(p->'early_stopping'->'patience',0)
   OR jsonb_typeof(p->'early_stopping'->'min_delta') IS DISTINCT FROM 'number'
   OR NOT campaign_json_object(p->'calibration',ARRAY['algorithm','population','version'])
   OR p->'calibration'->>'population' IS DISTINCT FROM 'val'
   OR p->'calibration'->>'algorithm' NOT IN ('none','threshold_grid')
   OR NOT campaign_json_string(p->'calibration'->'version')
   OR NOT campaign_json_object(p->'limitations',ARRAY['shared_val','independent_calibration','test_exposure'])
   OR NOT campaign_json_string(p->'limitations'->'shared_val')
   OR p->'limitations'->'independent_calibration' IS DISTINCT FROM 'false'::jsonb
   OR p->'limitations'->>'test_exposure' NOT IN ('unknown','previously_accessed')
   OR NOT campaign_json_object(p->'aggregation',ARRAY['version','specification'])
   OR NOT campaign_json_string(p->'aggregation'->'version') OR NOT campaign_json_string(p->'aggregation'->'specification')
   OR NOT campaign_json_object(p->'uncertainty',ARRAY['version','specification'])
   OR NOT campaign_json_string(p->'uncertainty'->'version') OR NOT campaign_json_string(p->'uncertainty'->'specification')
   THEN RETURN false; END IF;
 FOREACH k IN ARRAY ARRAY['primary','secondary'] LOOP
   FOR x IN SELECT value FROM jsonb_array_elements(p->'metrics'->k) LOOP
     IF NOT campaign_json_string(x) THEN RETURN false; END IF;
   END LOOP;
 END LOOP;
 FOREACH k IN ARRAY ARRAY['criteria','tie_breaks'] LOOP
   FOR x IN SELECT value FROM jsonb_array_elements(p->'ranking'->k) LOOP
     IF NOT campaign_json_string(x) THEN RETURN false; END IF;
   END LOOP;
 END LOOP;
 FOREACH k IN ARRAY ARRAY['policy','monitor','mode'] LOOP
   IF NOT campaign_json_string(p->'checkpoint'->k) THEN RETURN false; END IF;
 END LOOP;
 IF NOT campaign_json_string(p->'early_stopping'->'monitor')
   OR NOT campaign_json_string(p->'early_stopping'->'mode') THEN RETURN false; END IF;
 env=v->'environment';
 IF NOT campaign_json_object(env,ARRAY['source_sha256','python','tensorflow','packages','determinism_environment'])
   OR NOT campaign_json_string(env->'python') OR NOT campaign_json_string(env->'tensorflow')
   OR (env->>'source_sha256') !~ '^[a-f0-9]{64}$'
   OR jsonb_typeof(env->'packages') IS DISTINCT FROM 'object' OR env->'packages'='{}'::jsonb
   OR jsonb_typeof(env->'determinism_environment') IS DISTINCT FROM 'object' THEN RETURN false; END IF;
 matrix=v->'matrix';
 IF NOT campaign_json_object(matrix,ARRAY['canonical_version','registry','registry_hash','configurations','members','expected_count','seeds'])
   OR matrix->>'canonical_version' IS DISTINCT FROM 'campaign_json_v1'
   OR NOT campaign_json_integer(matrix->'expected_count',1)
   OR (matrix->>'registry_hash') !~ '^[a-f0-9]{64}$'
   OR jsonb_typeof(matrix->'registry') IS DISTINCT FROM 'array' OR jsonb_array_length(matrix->'registry')=0
   OR jsonb_typeof(matrix->'seeds') IS DISTINCT FROM 'array' OR jsonb_array_length(matrix->'seeds')=0
   OR jsonb_typeof(matrix->'configurations') IS DISTINCT FROM 'object' OR matrix->'configurations'='{}'::jsonb
   OR jsonb_typeof(matrix->'members') IS DISTINCT FROM 'array' THEN RETURN false; END IF;
 n=(matrix->>'expected_count')::integer; seeds=matrix->'seeds';configs=matrix->'configurations';members=matrix->'members';
 IF n>(b->>'max_members')::integer OR n<>jsonb_array_length(members)
   OR n<>(SELECT count(*) FROM jsonb_each(configs))*jsonb_array_length(seeds) THEN RETURN false; END IF;
 FOR x IN SELECT value FROM jsonb_array_elements(seeds) LOOP
   IF NOT campaign_json_integer(x,0) OR seen_seeds @> jsonb_build_array(x) THEN RETURN false; END IF;
   seen_seeds=seen_seeds || jsonb_build_array(x);
 END LOOP;
 FOR descriptor IN SELECT value FROM jsonb_array_elements(matrix->'registry') LOOP
   IF NOT campaign_json_object(descriptor,ARRAY['id','aliases','enabled','trainable','version','adapter','input_contract','output_contract','strategies','optimizers','preprocessing_modes','default_preprocessing'])
      OR NOT campaign_json_string(descriptor->'id') OR NOT campaign_json_string(descriptor->'version')
      OR descriptor->'enabled' IS DISTINCT FROM 'true'::jsonb OR descriptor->'trainable' IS DISTINCT FROM 'true'::jsonb
      OR jsonb_typeof(descriptor->'aliases') IS DISTINCT FROM 'array'
      OR jsonb_typeof(descriptor->'optimizers') IS DISTINCT FROM 'array' THEN RETURN false; END IF;
   FOREACH k IN ARRAY ARRAY['adapter','input_contract','output_contract','default_preprocessing'] LOOP
     IF NOT campaign_json_string(descriptor->k) THEN RETURN false; END IF;
   END LOOP;
   FOREACH k IN ARRAY ARRAY['aliases','strategies','optimizers','preprocessing_modes'] LOOP
     IF jsonb_typeof(descriptor->k) IS DISTINCT FROM 'array' THEN RETURN false; END IF;
     FOR x IN SELECT value FROM jsonb_array_elements(descriptor->k) LOOP
       IF NOT campaign_json_string(x) THEN RETURN false; END IF;
     END LOOP;
   END LOOP;
 END LOOP;
 FOR item IN SELECT * FROM jsonb_each(configs) LOOP
   IF item.key !~ '^[a-f0-9]{64}$' OR NOT campaign_json_object(item.value,ARRAY['configuration','requests'])
      OR campaign_configuration_valid(item.value->'configuration') IS NOT TRUE
      OR jsonb_typeof(item.value->'requests') IS DISTINCT FROM 'array' OR jsonb_array_length(item.value->'requests')=0 THEN RETURN false; END IF;
 END LOOP;
 FOR x IN SELECT value FROM jsonb_array_elements(members) LOOP
   IF NOT campaign_json_object(x,ARRAY['configuration_hash','seed','position']) OR NOT (x ? 'exclusion_reason')
     OR NOT campaign_json_string(x->'configuration_hash') OR NOT (configs ? (x->>'configuration_hash'))
     OR NOT campaign_json_integer(x->'seed',0) OR NOT (seeds @> jsonb_build_array(x->'seed'))
     OR NOT campaign_json_integer(x->'position',0) OR (x->>'position')::int<>idx
     OR (x->'exclusion_reason'<>'null'::jsonb AND NOT campaign_json_string(x->'exclusion_reason')) THEN RETURN false; END IF;
   idx=idx+1;
 END LOOP;
 RETURN true;
END $$;

CREATE FUNCTION public.dbv21_xai_configuration_guard() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE c jsonb; h text;
BEGIN
 IF TG_TABLE_NAME='xai_method_configurations' THEN
 c:=jsonb_build_object('method',NEW.method,'implementation',NEW.implementation,'implementation_version',NEW.implementation_version,'parameters',NEW.parameters);
 h:=encode(digest(convert_to(NEW.canonical_configuration,'UTF8'),'sha256'),'hex');
 IF NEW.canonical_configuration::jsonb IS DISTINCT FROM c OR h IS DISTINCT FROM NEW.configuration_hash THEN RAISE EXCEPTION 'XAI_CONFIGURATION_HASH_MISMATCH'; END IF;
 ELSE
 c:=jsonb_build_object('metric_name',NEW.metric_name,'metric_family',NEW.metric_family,'protocol_name',NEW.protocol_name,'protocol_version',NEW.protocol_version,'parameters',NEW.parameters,'normalization_strategy',NEW.normalization_strategy,'perturbation_strategy',NEW.perturbation_strategy,'reference_definition',NEW.reference_definition);
 h:=encode(digest(convert_to(NEW.canonical_protocol,'UTF8'),'sha256'),'hex');
 IF NEW.canonical_protocol::jsonb IS DISTINCT FROM c OR h IS DISTINCT FROM NEW.protocol_hash THEN RAISE EXCEPTION 'XAI_PROTOCOL_HASH_MISMATCH'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.dbv21_xai_evaluation_complete() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE eid uuid; q public.xai_quantitative_evaluations%ROWTYPE; p public.xai_evaluation_protocols%ROWTYPE; n integer;
BEGIN
 IF TG_TABLE_NAME = 'xai_quantitative_evaluations' THEN
     eid := NEW.id;
 ELSIF TG_TABLE_NAME = 'xai_evaluation_members' THEN
     eid := NEW.evaluation_id;
 ELSE
     RAISE EXCEPTION
         'dbv21_xai_evaluation_complete invoked from unsupported table: %',
         TG_TABLE_NAME;
 END IF;
 SELECT * INTO STRICT q FROM public.xai_quantitative_evaluations WHERE id=eid;
 SELECT * INTO STRICT p FROM public.xai_evaluation_protocols WHERE id=q.protocol_id;
 SELECT count(*) INTO n FROM public.xai_evaluation_members WHERE evaluation_id=eid;
 IF q.membership_hash IS DISTINCT FROM (SELECT encode(digest(convert_to(coalesce(string_agg(xai_evidence_id::text || ':' || member_role, E'\n' ORDER BY xai_evidence_id::text COLLATE "C"),''),'UTF8'),'sha256'),'hex') FROM public.xai_evaluation_members WHERE evaluation_id=eid) THEN RAISE EXCEPTION 'XAI_MEMBERSHIP_HASH_MISMATCH'; END IF;
 IF n<1 OR (p.metric_family='agreement' AND n<2) THEN RAISE EXCEPTION 'XAI_EVALUATION_MEMBERS_REQUIRED'; END IF;
 IF p.metric_family='agreement' AND EXISTS (
 SELECT 1 FROM public.xai_evaluation_members ma JOIN public.xai_evidence a ON a.id=ma.xai_evidence_id
 JOIN public.xai_evaluation_members mb ON mb.evaluation_id=ma.evaluation_id JOIN public.xai_evidence b ON b.id=mb.xai_evidence_id
 WHERE ma.evaluation_id=eid AND (a.input_sha256 IS DISTINCT FROM b.input_sha256 OR a.input_contract_hash IS DISTINCT FROM b.input_contract_hash OR a.target_class IS DISTINCT FROM b.target_class OR a.explained_output IS DISTINCT FROM b.explained_output OR a.processing_stage IS DISTINCT FROM b.processing_stage OR a.checkpoint_sha256 IS DISTINCT FROM b.checkpoint_sha256)) THEN RAISE EXCEPTION 'XAI_AGREEMENT_INCOMPATIBLE'; END IF;
 IF p.metric_family='localization' AND q.metric_value IS NOT NULL AND q.reference_annotation_id IS NULL THEN RAISE EXCEPTION 'XAI_LOCALIZATION_REFERENCE_REQUIRED'; END IF;
 IF q.reference_annotation_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.scientific_validation_annotations WHERE id=q.reference_annotation_id AND version=q.reference_annotation_version) THEN RAISE EXCEPTION 'XAI_REFERENCE_VERSION_MISMATCH'; END IF;
 RETURN NULL;
END $$;

