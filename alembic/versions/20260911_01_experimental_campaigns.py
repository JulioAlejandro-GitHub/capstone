"""E4 additive campaign planning and attempt ledger. No historic backfill."""

import sqlalchemy as sa

from alembic import op

revision = "20260911_01"
down_revision = "20260901_01"
branch_labels = None
depends_on = None

DDL = r"""
CREATE TABLE experimental_campaigns (
 id uuid PRIMARY KEY,
 experiment_id uuid REFERENCES experiments(id) ON DELETE RESTRICT,
 name text NOT NULL CHECK (length(btrim(name))>0),
 purpose text NOT NULL CHECK (length(btrim(purpose))>0),
 state text NOT NULL DEFAULT 'draft' CHECK (state IN ('draft','frozen','active','paused','finalized')),
 dataset_version_id uuid NOT NULL REFERENCES dataset_versions(id) ON DELETE RESTRICT,
 dataset_snapshot jsonb NOT NULL CHECK (jsonb_typeof(dataset_snapshot)='object'),
 dataset_evidence_id uuid NOT NULL REFERENCES audit_events(id) ON DELETE RESTRICT,
 requested jsonb NOT NULL CHECK (jsonb_typeof(requested)='object'),
 protocol jsonb NOT NULL CHECK (jsonb_typeof(protocol)='object'),
 environment jsonb NOT NULL CHECK (jsonb_typeof(environment)='object'),
 registry_snapshot jsonb,
 contract jsonb,
 canonical_contract text,
 contract_hash text,
 expected_count integer NOT NULL DEFAULT 0 CHECK(expected_count>=0),
 actor text NOT NULL CHECK(length(btrim(actor))>0),
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now(),
 frozen_at timestamptz,
 CHECK ((state='draft' AND contract IS NULL AND canonical_contract IS NULL AND contract_hash IS NULL AND frozen_at IS NULL)
     OR (state<>'draft' AND contract IS NOT NULL AND canonical_contract IS NOT NULL AND contract_hash ~ '^[a-f0-9]{64}$'
         AND registry_snapshot IS NOT NULL AND frozen_at IS NOT NULL AND expected_count>0)),
 CHECK((dataset_snapshot->>'dataset_version_id') IS NOT DISTINCT FROM dataset_version_id::text)
);
CREATE INDEX ix_campaign_dataset_state ON experimental_campaigns(dataset_version_id,state);
CREATE TABLE campaign_configurations (
 campaign_id uuid NOT NULL REFERENCES experimental_campaigns(id) ON DELETE RESTRICT,
 configuration_hash text NOT NULL CHECK(configuration_hash ~ '^[a-f0-9]{64}$'),
 configuration jsonb NOT NULL CHECK(jsonb_typeof(configuration)='object'),
 canonical_configuration text NOT NULL,
 requests jsonb NOT NULL CHECK(jsonb_typeof(requests)='array'),
 PRIMARY KEY(campaign_id,configuration_hash)
);
CREATE TABLE campaign_members (
 id uuid PRIMARY KEY,
 campaign_id uuid NOT NULL REFERENCES experimental_campaigns(id) ON DELETE RESTRICT,
 configuration_hash text NOT NULL,
 seed integer NOT NULL CHECK(seed>=0),
 position integer NOT NULL CHECK(position>=0),
 exclusion_reason text,
 state text NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','active','failed','interrupted','completed','verified','excluded')),
 accepted_attempt_id uuid,
 FOREIGN KEY(campaign_id,configuration_hash) REFERENCES campaign_configurations(campaign_id,configuration_hash) ON DELETE RESTRICT,
 UNIQUE(campaign_id,configuration_hash,seed), UNIQUE(campaign_id,position),
 CHECK((state='excluded')=(exclusion_reason IS NOT NULL)),
 CHECK(exclusion_reason IS NULL OR length(btrim(exclusion_reason))>0),
 CHECK((state='verified')=(accepted_attempt_id IS NOT NULL))
);
CREATE INDEX ix_campaign_member_state ON campaign_members(campaign_id,state);
CREATE TABLE campaign_attempts (
 id uuid PRIMARY KEY,
 member_id uuid NOT NULL REFERENCES campaign_members(id) ON DELETE RESTRICT,
 ordinal integer NOT NULL CHECK(ordinal>0),
 state text NOT NULL CHECK(state IN ('active','failed','interrupted','completed','verified')),
 training_run_id uuid UNIQUE REFERENCES runs(id) ON DELETE RESTRICT,
 cause text,
 started_at timestamptz NOT NULL DEFAULT now(),
 finished_at timestamptz,
 UNIQUE(member_id,ordinal), UNIQUE(member_id,id),
 CHECK((state='active')=(finished_at IS NULL)),
 CHECK(state NOT IN ('failed','interrupted') OR (cause IS NOT NULL AND length(btrim(cause))>0)),
 CHECK(state NOT IN ('completed','verified') OR training_run_id IS NOT NULL)
);
CREATE UNIQUE INDEX uq_campaign_one_active_attempt ON campaign_attempts(member_id) WHERE state='active';
CREATE INDEX ix_campaign_attempt_state ON campaign_attempts(state);
ALTER TABLE campaign_members ADD CONSTRAINT fk_member_accepted_attempt FOREIGN KEY(id,accepted_attempt_id)
 REFERENCES campaign_attempts(member_id,id) DEFERRABLE INITIALLY DEFERRED;

CREATE FUNCTION campaign_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE TRIGGER campaign_guard BEFORE INSERT OR UPDATE OR DELETE ON experimental_campaigns FOR EACH ROW EXECUTE FUNCTION campaign_guard();

CREATE FUNCTION campaign_configuration_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE TRIGGER campaign_configuration_guard BEFORE INSERT OR UPDATE OR DELETE ON campaign_configurations FOR EACH ROW EXECUTE FUNCTION campaign_configuration_guard();

CREATE FUNCTION campaign_member_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
   IF NEW.state='verified' OR NEW.accepted_attempt_id IS NOT NULL THEN RAISE EXCEPTION 'VERIFICATION_REQUIRES_E5'; END IF;
   IF NEW.state<>OLD.state THEN
     SELECT state INTO current_attempt FROM campaign_attempts WHERE member_id=NEW.id ORDER BY ordinal DESC LIMIT 1;
     IF NEW.state IS DISTINCT FROM current_attempt THEN RAISE EXCEPTION 'MEMBER_STATE_MUST_FOLLOW_ATTEMPT'; END IF;
   END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER campaign_member_guard BEFORE INSERT OR UPDATE OR DELETE ON campaign_members FOR EACH ROW EXECUTE FUNCTION campaign_member_guard();

CREATE FUNCTION campaign_attempt_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE m record; c record; r record; cfg jsonb; rcfg jsonb; maximum integer;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'ATTEMPT_HISTORY_IMMUTABLE'; END IF;
 -- Campaign lock first, shared with planning and members; then member serialization.
 SELECT c0.* INTO c FROM experimental_campaigns c0 JOIN campaign_members m0 ON m0.campaign_id=c0.id WHERE m0.id=NEW.member_id FOR UPDATE OF c0;
 SELECT * INTO m FROM campaign_members WHERE id=NEW.member_id FOR UPDATE;
 IF m.id IS NULL OR c.state NOT IN ('frozen','active','paused') THEN RAISE EXCEPTION 'ATTEMPT_REQUIRES_FROZEN_CAMPAIGN'; END IF;
 IF TG_OP='INSERT' THEN
   SELECT coalesce(max(ordinal),0)+1 INTO maximum FROM campaign_attempts WHERE member_id=NEW.member_id;
   IF c.state='paused' OR NEW.state<>'active' OR m.state NOT IN ('pending','failed','interrupted')
      OR NEW.ordinal<>maximum OR NEW.ordinal>(c.protocol->'budget'->>'max_attempts_per_member')::int
      THEN RAISE EXCEPTION 'INVALID_NEW_ATTEMPT'; END IF;
 ELSE
   IF NEW.id<>OLD.id OR NEW.member_id<>OLD.member_id OR NEW.ordinal<>OLD.ordinal OR NEW.started_at<>OLD.started_at
     OR (OLD.training_run_id IS NOT NULL AND NEW.training_run_id IS DISTINCT FROM OLD.training_run_id)
     THEN RAISE EXCEPTION 'ATTEMPT_IDENTITY_IMMUTABLE'; END IF;
   IF OLD.state<>'active' OR NEW.state NOT IN ('active','failed','interrupted','completed') THEN RAISE EXCEPTION 'INVALID_ATTEMPT_TRANSITION'; END IF;
 END IF;
 IF NEW.training_run_id IS NOT NULL THEN
   SELECT * INTO r FROM runs WHERE id=NEW.training_run_id FOR UPDATE;
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
     OR r.execution_parameters->'model_configuration_e2'->'environment'->>'source_sha256' IS DISTINCT FROM c.environment->>'source_sha256'
     OR r.execution_parameters->'model_configuration_e2'->'environment'->'packages' IS DISTINCT FROM c.environment->'packages'
     OR r.execution_parameters->'model_configuration_e2'->'environment'->>'python' IS DISTINCT FROM c.environment->>'python'
     OR r.execution_parameters->'model_configuration_e2'->'environment'->>'tensorflow' IS DISTINCT FROM c.environment->>'tensorflow'
     OR r.execution_parameters->'model_configuration_e2'->'environment'->'determinism_environment' IS DISTINCT FROM c.environment->'determinism_environment'
     THEN RAISE EXCEPTION 'TRAIN_CAMPAIGN_CONTRACT_CONFLICT'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER campaign_attempt_guard BEFORE INSERT OR UPDATE OR DELETE ON campaign_attempts FOR EACH ROW EXECUTE FUNCTION campaign_attempt_guard();
CREATE FUNCTION campaign_attempt_state() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN UPDATE campaign_members SET state=NEW.state WHERE id=NEW.member_id; RETURN NEW; END $$;
CREATE TRIGGER campaign_attempt_state AFTER INSERT OR UPDATE ON campaign_attempts FOR EACH ROW EXECUTE FUNCTION campaign_attempt_state();

CREATE FUNCTION campaign_run_identity_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM campaign_attempts WHERE training_run_id=OLD.id) AND
   (NEW.run_type IS DISTINCT FROM OLD.run_type OR NEW.dataset_version_id IS DISTINCT FROM OLD.dataset_version_id
    OR NEW.random_seed IS DISTINCT FROM OLD.random_seed OR NEW.experiment_id IS DISTINCT FROM OLD.experiment_id
    OR NEW.execution_parameters->'model_configuration_e2'->'configuration' IS DISTINCT FROM OLD.execution_parameters->'model_configuration_e2'->'configuration'
    OR NEW.execution_parameters->'model_configuration_e2'->'dataset' IS DISTINCT FROM OLD.execution_parameters->'model_configuration_e2'->'dataset'
    OR NEW.execution_parameters->'model_configuration_e2'->'environment' IS DISTINCT FROM OLD.execution_parameters->'model_configuration_e2'->'environment')
 THEN RAISE EXCEPTION 'LINKED_TRAIN_IDENTITY_IMMUTABLE'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER campaign_run_identity_guard BEFORE UPDATE ON runs FOR EACH ROW EXECUTE FUNCTION campaign_run_identity_guard();

CREATE FUNCTION campaign_audit() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE TRIGGER campaign_audit AFTER INSERT OR UPDATE ON experimental_campaigns FOR EACH ROW EXECUTE FUNCTION campaign_audit();
CREATE TRIGGER campaign_configuration_audit AFTER INSERT OR UPDATE OR DELETE ON campaign_configurations FOR EACH ROW EXECUTE FUNCTION campaign_audit();
CREATE TRIGGER campaign_member_audit AFTER INSERT OR UPDATE OR DELETE ON campaign_members FOR EACH ROW EXECUTE FUNCTION campaign_audit();
CREATE TRIGGER campaign_attempt_audit AFTER INSERT OR UPDATE ON campaign_attempts FOR EACH ROW EXECUTE FUNCTION campaign_audit();
"""

FUNCTIONS = (
    "campaign_guard",
    "campaign_configuration_guard",
    "campaign_member_guard",
    "campaign_attempt_guard",
    "campaign_attempt_state",
    "campaign_run_identity_guard",
    "campaign_audit",
)


def upgrade():
    op.execute(DDL)
    # Bind SECURITY INVOKER functions to the installation schema, never caller search_path.
    context = op.get_context()
    schema = (
        "public"
        if context.as_sql
        else op.get_bind().execute(sa.text("SELECT current_schema()")).scalar_one()
    )
    quoted = context.dialect.identifier_preparer.quote(schema)
    for name in FUNCTIONS:
        op.execute(f"ALTER FUNCTION {name}() SET search_path = {quoted}, pg_catalog")


def downgrade():
    raise RuntimeError("Operational downgrade forbidden; use a forward migration")
