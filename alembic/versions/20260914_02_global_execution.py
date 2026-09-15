"""Global experimental exclusivity and sequential technical revision binding."""
import sqlalchemy as sa
from alembic import op
revision = "20260914_02"
down_revision = "20260914_01"
branch_labels = None
depends_on = None
DDL = r"""
CREATE TABLE experiment_execution_gate (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton), owner uuid, db_pid integer,
 process_evidence jsonb NOT NULL DEFAULT '{}', blocked_reason text,
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO experiment_execution_gate(singleton) VALUES(true);
CREATE TABLE experiment_execution_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, owner uuid NOT NULL,
 event text NOT NULL, payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE FUNCTION experiment_require_owner() RETURNS void LANGUAGE plpgsql AS $$
DECLARE g record;
BEGIN
 SELECT * INTO g FROM experiment_execution_gate WHERE singleton FOR UPDATE;
 IF g.owner IS NULL OR g.owner::text IS DISTINCT FROM current_setting('capstone.execution_token',true)
 OR NOT EXISTS(SELECT 1 FROM pg_locks WHERE locktype='advisory' AND classid=120994 AND objid=1 AND objsubid=2 AND pid=g.db_pid AND granted)
 THEN RAISE EXCEPTION 'GLOBAL_EXECUTION_OWNER_REQUIRED'; END IF;
END $$;
CREATE FUNCTION experiment_reservation_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE TRIGGER global_train_reservation BEFORE INSERT OR UPDATE ON train_execution_sessions FOR EACH ROW EXECUTE FUNCTION experiment_reservation_guard();
CREATE TRIGGER global_attempt_reservation BEFORE INSERT ON campaign_attempts FOR EACH ROW EXECUTE FUNCTION experiment_reservation_guard();
CREATE TRIGGER global_assessment_reservation BEFORE INSERT OR UPDATE ON assessment_attempts FOR EACH ROW EXECUTE FUNCTION experiment_reservation_guard();
CREATE UNIQUE INDEX uq_global_train_active ON train_execution_sessions((true)) WHERE state IN ('active','completed');
CREATE UNIQUE INDEX uq_global_assessment_active ON assessment_attempts((true)) WHERE state='active';
CREATE FUNCTION execution_event_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'EXECUTION_HISTORY_IMMUTABLE'; END $$;
CREATE TRIGGER global_execution_event_immutable BEFORE UPDATE OR DELETE ON experiment_execution_events FOR EACH ROW EXECUTE FUNCTION execution_event_immutable();
CREATE TABLE train_execution_revisions (
 attempt_id uuid PRIMARY KEY REFERENCES campaign_attempts(id) DEFERRABLE INITIALLY DEFERRED,
 campaign_id uuid NOT NULL REFERENCES experimental_campaigns(id), revision_id uuid NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(campaign_id,revision_id) REFERENCES campaign_technical_revisions(campaign_id,id)
);
CREATE TRIGGER train_execution_revision_immutable BEFORE UPDATE OR DELETE ON train_execution_revisions FOR EACH ROW EXECUTE FUNCTION execution_event_immutable();
CREATE FUNCTION train_revision_binding_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM campaign_attempts a JOIN campaign_members m ON m.id=a.member_id
 JOIN train_execution_sessions s ON s.attempt_id=a.id JOIN campaign_technical_revisions v ON v.id=NEW.revision_id
 WHERE a.id=NEW.attempt_id AND m.campaign_id=NEW.campaign_id AND v.campaign_id=NEW.campaign_id
 AND s.environment IS NOT DISTINCT FROM v.payload->'environment')
 THEN RAISE EXCEPTION 'TRAIN_REVISION_BINDING_INVALID'; END IF;
 RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER train_revision_binding_guard AFTER INSERT ON train_execution_revisions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION train_revision_binding_guard();
CREATE OR REPLACE FUNCTION campaign_attempt_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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

"""
def upgrade():
    op.execute(DDL)
    ctx = op.get_context()
    schema = "public" if ctx.as_sql else op.get_bind().execute(sa.text("SELECT current_schema()")).scalar_one()
    schema = ctx.dialect.identifier_preparer.quote(schema)
    for name in ("experiment_require_owner", "experiment_reservation_guard", "execution_event_immutable", "train_revision_binding_guard", "campaign_attempt_guard"):
        op.execute(f"ALTER FUNCTION {name}() SET search_path = {schema}, pg_catalog")

def downgrade():
    raise RuntimeError("Forward migration required")
