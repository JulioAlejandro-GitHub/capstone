"""Local API jobs: persistent non-expiring reservation and explicit Darwin revisions."""
from alembic import op
import sqlalchemy as sa
revision='20260915_01'
down_revision='20260914_02'
branch_labels=None
depends_on=None
DDL=r"""
CREATE TABLE local_execution_jobs (
 id uuid PRIMARY KEY, principal text NOT NULL, agent_id uuid NOT NULL,
 owner uuid NOT NULL UNIQUE, request_hash text NOT NULL,
 campaign_id uuid NOT NULL REFERENCES experimental_campaigns(id),
 run_id uuid UNIQUE REFERENCES runs(id),
 state text NOT NULL CHECK(state IN ('held','calculation_reported','released','failed')),
 session jsonb, heartbeat_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 process jsonb, completion jsonb, exit_proof jsonb, result jsonb,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX local_one_active ON local_execution_jobs((true)) WHERE state IN ('held','calculation_reported');
CREATE OR REPLACE FUNCTION experiment_require_owner() RETURNS void LANGUAGE plpgsql AS $$
DECLARE g record;
BEGIN
 SELECT * INTO g FROM experiment_execution_gate WHERE singleton FOR UPDATE;
 IF g.owner IS NULL OR g.owner::text IS DISTINCT FROM current_setting('capstone.execution_token',true)
 OR NOT (EXISTS(SELECT 1 FROM pg_locks WHERE locktype='advisory' AND classid=120994 AND objid=1 AND objsubid=2 AND pid=g.db_pid AND granted)
 OR EXISTS(SELECT 1 FROM local_execution_jobs WHERE owner=g.owner AND state IN ('held','calculation_reported')))
 THEN RAISE EXCEPTION 'GLOBAL_EXECUTION_OWNER_REQUIRED'; END IF;
END $$;
CREATE OR REPLACE FUNCTION campaign_technical_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
"""
def upgrade():
    op.execute(DDL)
    ctx=op.get_context()
    schema='public' if ctx.as_sql else op.get_bind().execute(sa.text('SELECT current_schema()')).scalar_one()
    schema=ctx.dialect.identifier_preparer.quote(schema)
    for name in ('experiment_require_owner','campaign_technical_guard'):
        op.execute(f'ALTER FUNCTION {name}() SET search_path={schema},pg_catalog')
def downgrade():
    raise RuntimeError('Forward migration required; preserve local execution history')
