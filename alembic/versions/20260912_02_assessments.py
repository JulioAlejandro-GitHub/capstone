"""E6 exact inference identities, immutable results and fenced attempts."""

import sqlalchemy as sa

from alembic import op

revision = "20260912_02"
down_revision = "20260912_01"
branch_labels = None
depends_on = None
DDL = r"""
CREATE FUNCTION assessment_canonical(v jsonb) RETURNS text LANGUAGE plpgsql IMMUTABLE STRICT AS $$
DECLARE result text;
BEGIN
 CASE jsonb_typeof(v)
 WHEN 'object' THEN
   SELECT '{'||coalesce(string_agg(to_jsonb(key)::text||':'||assessment_canonical(value),',' ORDER BY key COLLATE "C"),'')||'}' INTO result FROM jsonb_each(v);
 WHEN 'array' THEN
   SELECT '['||coalesce(string_agg(assessment_canonical(value),',' ORDER BY ord),'')||']' INTO result FROM jsonb_array_elements(v) WITH ORDINALITY a(value,ord);
 WHEN 'number' THEN result=trim_scale((v::text)::numeric)::text;
 ELSE result=v::text;
 END CASE;
 RETURN result;
END $$;
CREATE FUNCTION assessment_structural_hash(v jsonb) RETURNS text LANGUAGE sql IMMUTABLE STRICT AS $$
 SELECT encode(sha256(convert_to(assessment_canonical(v),'UTF8')),'hex')
$$;
CREATE TABLE assessment_identities (
 id uuid PRIMARY KEY, identity_hash text NOT NULL UNIQUE CHECK(identity_hash ~ '^[a-f0-9]{64}$'),
 training_run_id uuid NOT NULL REFERENCES runs(id), kind text NOT NULL CHECK(kind IN ('evaluate','explain')),
 identity jsonb NOT NULL CHECK(jsonb_typeof(identity)='object'), canonical_identity text NOT NULL,
 structural_hash text GENERATED ALWAYS AS (assessment_structural_hash(identity)) STORED UNIQUE, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(canonical_identity::jsonb IS NOT DISTINCT FROM identity),
 CHECK(identity_hash=encode(sha256(convert_to(canonical_identity,'UTF8')),'hex')),
 CHECK(identity->>'schema' IS NOT DISTINCT FROM 'assessment_identity_v1'),
 CHECK(identity->>'kind' IS NOT DISTINCT FROM kind),
 CHECK(identity->'model'->>'training_run_id' IS NOT DISTINCT FROM training_run_id::text),
 CHECK(jsonb_typeof(identity->'samples') IS NOT DISTINCT FROM 'array'),
 CHECK(jsonb_array_length(identity->'samples')>0),
 CHECK((identity->>'purpose'='development' AND identity->>'split' IN ('train','val')) OR (identity->>'purpose'='final' AND identity->>'split'='test')),
 CHECK(identity->>'purpose' IS NOT NULL AND identity->>'split' IS NOT NULL),
 CHECK(jsonb_typeof(identity->'model'->'input_contract') IS NOT DISTINCT FROM 'object'),
 CHECK(identity->'model'->>'sha256' IS NOT NULL AND identity->'model'->>'sha256' ~ '^[a-f0-9]{64}$'),
 CHECK(identity->'model'->>'model_version_id' IS NOT NULL AND (identity->'model'->>'model_version_id')::uuid IS NOT NULL),
 CHECK(identity->'model'->>'checkpoint_artifact_id' IS NOT NULL AND (identity->'model'->>'checkpoint_artifact_id')::uuid IS NOT NULL),
 CHECK(jsonb_typeof(identity->'decision'->'effective') IS NOT DISTINCT FROM 'number'),
 CHECK((identity->'decision'->>'effective')::numeric BETWEEN 0 AND 1),
 CHECK(identity->'decision'->>'score_domain' IS NOT DISTINCT FROM 'raw'),
 CHECK(identity->'decision'->>'comparison' IS NOT DISTINCT FROM '>='),
 CHECK(jsonb_typeof(identity->'dataset') IS NOT DISTINCT FROM 'object')
);
CREATE FUNCTION assessment_identity_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE TRIGGER assessment_identity_guard BEFORE INSERT ON assessment_identities FOR EACH ROW EXECUTE FUNCTION assessment_identity_guard();
CREATE TABLE assessment_final_locks (
 id uuid PRIMARY KEY, identity_hash text NOT NULL UNIQUE CHECK(identity_hash ~ '^[a-f0-9]{64}$'),
 evidence jsonb NOT NULL CHECK(jsonb_typeof(evidence)='object'),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(evidence->>'status' IS NOT DISTINCT FROM 'locked'),
 CHECK(evidence->>'identity_hash' IS NOT DISTINCT FROM identity_hash),
 CHECK(jsonb_typeof(evidence->'candidate') IS NOT DISTINCT FROM 'object'),
 CHECK(jsonb_typeof(evidence->'decision') IS NOT DISTINCT FROM 'object')
);
CREATE TABLE assessment_attempts (
 id uuid PRIMARY KEY, identity_id uuid NOT NULL REFERENCES assessment_identities(id),
 owner uuid NOT NULL, host text NOT NULL, pid integer NOT NULL CHECK(pid>0),
 ordinal integer NOT NULL CHECK(ordinal>0), state text NOT NULL DEFAULT 'active' CHECK(state IN ('active','verified','failed','interrupted')),
 artifact_root text NOT NULL UNIQUE, cause text, verification jsonb,
 started_at timestamptz NOT NULL DEFAULT clock_timestamp(), finished_at timestamptz,
 UNIQUE(identity_id,ordinal), CHECK(state<>'verified' OR verification IS NOT NULL)
);
CREATE UNIQUE INDEX uq_assessment_live ON assessment_attempts(identity_id) WHERE state IN ('active','verified');
CREATE TABLE assessment_results (
 attempt_id uuid NOT NULL REFERENCES assessment_attempts(id), sample_id uuid NOT NULL,
 payload jsonb NOT NULL CHECK(jsonb_typeof(payload)='object'),
 PRIMARY KEY(attempt_id,sample_id), CHECK(payload->>'sample_id' IS NOT DISTINCT FROM sample_id::text)
);
CREATE TABLE assessment_artifacts (
 attempt_id uuid NOT NULL REFERENCES assessment_attempts(id), artifact_id uuid NOT NULL UNIQUE,
 sample_id uuid NOT NULL, role text NOT NULL, payload jsonb NOT NULL CHECK(jsonb_typeof(payload)='object'),
 PRIMARY KEY(attempt_id,sample_id,role),
 CHECK(payload->>'sha256' IS NOT NULL AND payload->>'sha256' ~ '^[a-f0-9]{64}$'),
 CHECK(jsonb_typeof(payload->'bytes') IS NOT DISTINCT FROM 'number' AND (payload->>'bytes')::bigint>0),
 CHECK(payload->>'state' IS NOT DISTINCT FROM 'finalized')
);
CREATE TABLE assessment_campaign_consumers (
 campaign_id uuid NOT NULL REFERENCES experimental_campaigns(id), member_id uuid NOT NULL REFERENCES campaign_members(id),
 identity_id uuid NOT NULL REFERENCES assessment_identities(id), PRIMARY KEY(campaign_id,member_id,identity_id)
);
CREATE FUNCTION assessment_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'ASSESSMENT_HISTORY_IMMUTABLE'; END $$;
CREATE TRIGGER assessment_identity_immutable BEFORE UPDATE OR DELETE ON assessment_identities FOR EACH ROW EXECUTE FUNCTION assessment_immutable();
CREATE TRIGGER assessment_lock_immutable BEFORE UPDATE OR DELETE ON assessment_final_locks FOR EACH ROW EXECUTE FUNCTION assessment_immutable();
CREATE TRIGGER assessment_consumer_immutable BEFORE UPDATE OR DELETE ON assessment_campaign_consumers FOR EACH ROW EXECUTE FUNCTION assessment_immutable();
CREATE FUNCTION assessment_result_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE TRIGGER assessment_result_guard BEFORE INSERT OR UPDATE OR DELETE ON assessment_results FOR EACH ROW EXECUTE FUNCTION assessment_result_guard();
CREATE TRIGGER assessment_artifact_guard BEFORE INSERT OR UPDATE OR DELETE ON assessment_artifacts FOR EACH ROW EXECUTE FUNCTION assessment_result_guard();
CREATE FUNCTION assessment_attempt_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE TRIGGER assessment_attempt_guard BEFORE INSERT OR UPDATE OR DELETE ON assessment_attempts FOR EACH ROW EXECUTE FUNCTION assessment_attempt_guard();
CREATE FUNCTION assessment_consumer_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE TRIGGER assessment_consumer_guard BEFORE INSERT ON assessment_campaign_consumers FOR EACH ROW EXECUTE FUNCTION assessment_consumer_guard();
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
        "assessment_canonical",
        "assessment_structural_hash",
        "assessment_immutable",
        "assessment_identity_guard",
        "assessment_result_guard",
        "assessment_attempt_guard",
        "assessment_consumer_guard",
    ):
        signature = (
            "jsonb"
            if name in ("assessment_canonical", "assessment_structural_hash")
            else ""
        )
        op.execute(
            f"ALTER FUNCTION {name}({signature}) SET search_path = {schema}, pg_catalog"
        )


def downgrade():
    raise RuntimeError("Use a forward migration; operational downgrade forbidden")
