CREATE OR REPLACE FUNCTION public.campaign_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
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
      OR ((ev.after_state->>'integrity_status') = 'verified'
          OR ((ev.after_state->>'integrity_status') = 'verified_requested_splits'
              AND (ev.after_state->'required_splits') @> '["train","val"]'::jsonb
              AND (ev.after_state->'physically_verified_splits') @> '["train","val"]'::jsonb))
         IS DISTINCT FROM TRUE
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
END $function$

