"""E5 owned TRAIN sessions and immutable structured results."""

import sqlalchemy as sa

from alembic import op

revision = "20260912_01"
down_revision = "20260911_02"
branch_labels = None
depends_on = None
DDL = r"""
CREATE TABLE train_execution_sessions (
 run_id uuid PRIMARY KEY REFERENCES runs(id), attempt_id uuid UNIQUE REFERENCES campaign_attempts(id),
 owner uuid NOT NULL, host text NOT NULL, parent_pid integer NOT NULL CHECK(parent_pid>0), child_pid integer,
 state text NOT NULL DEFAULT 'active' CHECK(state IN ('active','completed','verified','failed','interrupted')),
 configuration jsonb NOT NULL, dataset jsonb NOT NULL, environment jsonb NOT NULL,
 artifact_root text NOT NULL UNIQUE, cause text, started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp(), completion jsonb, verification jsonb,
 CHECK(state NOT IN ('completed','verified') OR completion IS NOT NULL),
 CHECK(state<>'verified' OR verification IS NOT NULL)
);
CREATE TABLE train_execution_records (
 run_id uuid NOT NULL REFERENCES train_execution_sessions(run_id), kind text NOT NULL,
 phase text NOT NULL, record_key text NOT NULL, payload jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(run_id,kind,phase,record_key), CHECK(jsonb_typeof(payload)='object')
);
CREATE TABLE campaign_execution_events (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), campaign_id uuid NOT NULL REFERENCES experimental_campaigns(id),
 code text NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE FUNCTION train_record_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE s record;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'TRAIN_RECORD_IMMUTABLE'; END IF;
 SELECT * INTO s FROM train_execution_sessions WHERE run_id=NEW.run_id FOR UPDATE;
 IF s.state IS DISTINCT FROM 'active' OR s.owner::text IS DISTINCT FROM current_setting('capstone.train_owner',true)
 THEN RAISE EXCEPTION 'TRAIN_OWNER_FENCED'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER train_record_guard BEFORE INSERT OR UPDATE OR DELETE ON train_execution_records FOR EACH ROW EXECUTE FUNCTION train_record_guard();
CREATE FUNCTION train_session_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE TRIGGER train_session_guard BEFORE UPDATE OR DELETE ON train_execution_sessions FOR EACH ROW EXECUTE FUNCTION train_session_guard();
CREATE OR REPLACE FUNCTION campaign_attempt_state() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 UPDATE campaign_members SET state=NEW.state,
 accepted_attempt_id=CASE WHEN NEW.state='verified' THEN
   (SELECT id FROM campaign_attempts WHERE member_id=NEW.member_id AND state='verified' ORDER BY ordinal LIMIT 1)
   ELSE NULL END WHERE id=NEW.member_id;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION campaign_attempt_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
     OR r.execution_parameters->'model_configuration_e2'->'environment'->>'source_sha256' IS DISTINCT FROM c.environment->>'source_sha256'
     OR r.execution_parameters->'model_configuration_e2'->'environment'->'packages' IS DISTINCT FROM c.environment->'packages'
     OR r.execution_parameters->'model_configuration_e2'->'environment'->>'python' IS DISTINCT FROM c.environment->>'python'
     OR r.execution_parameters->'model_configuration_e2'->'environment'->>'tensorflow' IS DISTINCT FROM c.environment->>'tensorflow'
     OR r.execution_parameters->'model_configuration_e2'->'environment'->'determinism_environment' IS DISTINCT FROM c.environment->'determinism_environment'
     THEN RAISE EXCEPTION 'TRAIN_CAMPAIGN_CONTRACT_CONFLICT'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION campaign_member_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
"""


def upgrade():
    op.execute(DDL)
    ctx = op.get_context()
    schema = (
        "public"
        if ctx.as_sql
        else op.get_bind().execute(sa.text("SELECT current_schema()")).scalar_one()
    )
    schema = ctx.dialect.identifier_preparer.quote(schema)
    for name in (
        "train_record_guard",
        "train_session_guard",
        "campaign_attempt_guard",
        "campaign_attempt_state",
        "campaign_member_guard",
    ):
        op.execute(f"ALTER FUNCTION {name}() SET search_path = {schema}, pg_catalog")


def downgrade():
    raise RuntimeError("Use a forward migration; operational downgrade forbidden")
