"""Typed assessment-backed cell activation; retain all legacy evaluation FKs."""
from alembic import op
from alembic_v2.resources import load_baseline

revision = 'cell_activation_v1'
down_revision = 'pg_v2_baseline'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
ALTER TABLE public.stage2_model_publications
  ALTER COLUMN evaluation_run_id DROP NOT NULL,
  ADD COLUMN evaluation_attempt_id uuid REFERENCES public.assessment_attempts(id) ON DELETE RESTRICT,
  ADD CONSTRAINT ck_publication_evaluation_source CHECK
    (num_nonnulls(evaluation_run_id, evaluation_attempt_id)=1);
ALTER TABLE public.stage2_model_publication_events
  ALTER COLUMN evaluation_run_id DROP NOT NULL,
  ADD COLUMN evaluation_attempt_id uuid REFERENCES public.assessment_attempts(id) ON DELETE RESTRICT,
  ADD CONSTRAINT ck_publication_event_source CHECK
    (num_nonnulls(evaluation_run_id, evaluation_attempt_id)=1);
ALTER TABLE public.deployed_model_versions
  ADD COLUMN threshold_assessment_attempt_id uuid REFERENCES public.assessment_attempts(id) ON DELETE RESTRICT,
  ADD CONSTRAINT ck_deployment_threshold_source CHECK
    (num_nonnulls(threshold_calibration_id, threshold_assessment_attempt_id)<=1);
CREATE UNIQUE INDEX uq_cell_active_publication
  ON public.stage2_model_publications(datasource,scope) WHERE is_active;
CREATE UNIQUE INDEX uq_cell_active_deployment
  ON public.deployed_model_versions(environment,alias)
  WHERE status='active' AND environment='stage2' AND alias='default';

CREATE FUNCTION public.validate_cell_assessment_reference() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE evidence jsonb; attempt_state text; reference_attempt uuid; train uuid;
BEGIN
  IF TG_TABLE_NAME='stage2_model_publications' THEN
    IF TG_OP='UPDATE' AND ROW(NEW.model_version_id,NEW.training_run_id,NEW.checkpoint_artifact_id,
        NEW.evaluation_run_id,NEW.evaluation_attempt_id) IS DISTINCT FROM
       ROW(OLD.model_version_id,OLD.training_run_id,OLD.checkpoint_artifact_id,
        OLD.evaluation_run_id,OLD.evaluation_attempt_id) THEN
      RAISE EXCEPTION 'CELL_PUBLICATION_IDENTITY_IMMUTABLE' USING ERRCODE='23514';
    END IF;
    reference_attempt:=NEW.evaluation_attempt_id; train:=NEW.training_run_id;
  ELSE
    IF TG_OP='UPDATE' AND NEW.threshold_assessment_attempt_id IS DISTINCT FROM OLD.threshold_assessment_attempt_id THEN
      RAISE EXCEPTION 'CELL_THRESHOLD_IDENTITY_IMMUTABLE' USING ERRCODE='23514';
    END IF;
    reference_attempt:=NEW.threshold_assessment_attempt_id;
    SELECT training_run_id INTO train FROM public.model_versions WHERE id=NEW.model_version_id;
  END IF;
  IF reference_attempt IS NULL THEN RETURN NEW; END IF;
  SELECT i.identity,a.state INTO evidence,attempt_state
    FROM public.assessment_attempts a JOIN public.assessment_identities i ON i.id=a.identity_id
    WHERE a.id=reference_attempt AND i.training_run_id=train AND i.kind='evaluate'
      AND a.finished_at IS NOT NULL AND a.verification IS NOT NULL;
  IF attempt_state IS DISTINCT FROM 'verified'
    OR evidence#>>'{model,training_run_id}' IS DISTINCT FROM train::text
    OR evidence#>>'{model,model_version_id}' IS DISTINCT FROM NEW.model_version_id::text
    OR evidence#>>'{model,checkpoint_artifact_id}' IS DISTINCT FROM NEW.checkpoint_artifact_id::text THEN
    RAISE EXCEPTION 'CELL_ASSESSMENT_LINEAGE_MISMATCH' USING ERRCODE='23514';
  END IF;
  IF TG_TABLE_NAME='deployed_model_versions' THEN
    IF (evidence#>>'{decision,effective}')::numeric IS DISTINCT FROM NEW.threshold_value
      OR (NEW.threshold_profile_snapshot->>'value')::numeric IS DISTINCT FROM NEW.threshold_value
      OR NEW.threshold_profile_snapshot->>'source' IS DISTINCT FROM 'assessment_decision' THEN
      RAISE EXCEPTION 'CELL_ASSESSMENT_THRESHOLD_MISMATCH' USING ERRCODE='23514';
    END IF;
  END IF;
  RETURN NEW;
END; $$;
CREATE TRIGGER cell_publication_reference BEFORE INSERT OR UPDATE ON public.stage2_model_publications
  FOR EACH ROW EXECUTE FUNCTION public.validate_cell_assessment_reference();
CREATE TRIGGER cell_threshold_reference BEFORE INSERT OR UPDATE ON public.deployed_model_versions
  FOR EACH ROW EXECUTE FUNCTION public.validate_cell_assessment_reference();
""")

    # Preserve every frozen crop-snapshot check and extend only its typed evaluation source.
    original = next(sql for sql in load_baseline()[1] if sql.startswith(
        'CREATE OR REPLACE FUNCTION public.validate_cell_classification_run_snapshot()'))
    old = "OR COALESCE(snapshot->>'source_evaluation_run_id','')\n          !~ '^[0-9a-f-]{36}$'"
    new = """OR num_nonnulls(snapshot->>'source_evaluation_run_id',snapshot->>'source_evaluation_attempt_id')<>1
        OR COALESCE(snapshot->>'source_evaluation_run_id',snapshot->>'source_evaluation_attempt_id','')
          !~ '^[0-9a-f-]{36}$'"""
    if old not in original:
        raise RuntimeError('CELL_SNAPSHOT_BASELINE_MISMATCH')
    upgraded = original.replace(old, new).replace('      RETURN NEW;', """
      IF NOT EXISTS(SELECT 1 FROM public.stage2_model_publications p WHERE p.id=NEW.stage2_publication_id
        AND p.training_run_id::text IS NOT DISTINCT FROM snapshot->>'source_training_run_id'
        AND p.evaluation_run_id::text IS NOT DISTINCT FROM snapshot->>'source_evaluation_run_id'
        AND p.evaluation_attempt_id::text IS NOT DISTINCT FROM snapshot->>'source_evaluation_attempt_id') THEN
        RAISE EXCEPTION 'CELL_SNAPSHOT_EVALUATION_MISMATCH' USING ERRCODE='23514';
      END IF;
      RETURN NEW;""")
    op.execute(upgraded)


def downgrade():
    original = next(sql for sql in load_baseline()[1] if sql.startswith(
        'CREATE OR REPLACE FUNCTION public.validate_cell_classification_run_snapshot()'))
    # Never discard live assessment references or weaken their integrity.
    op.execute("""DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM public.stage2_model_publications WHERE evaluation_attempt_id IS NOT NULL)
        OR EXISTS(SELECT 1 FROM public.deployed_model_versions WHERE threshold_assessment_attempt_id IS NOT NULL)
      THEN RAISE EXCEPTION 'CELL_ACTIVATION_DOWNGRADE_HAS_REFERENCES'; END IF;
    END; $$;
    DROP TRIGGER cell_publication_reference ON public.stage2_model_publications;
    DROP TRIGGER cell_threshold_reference ON public.deployed_model_versions;
    DROP FUNCTION public.validate_cell_assessment_reference();
    DROP INDEX public.uq_cell_active_publication;
    DROP INDEX public.uq_cell_active_deployment;
    ALTER TABLE public.stage2_model_publication_events DROP CONSTRAINT ck_publication_event_source,
      DROP COLUMN evaluation_attempt_id, ALTER COLUMN evaluation_run_id SET NOT NULL;
    ALTER TABLE public.deployed_model_versions DROP CONSTRAINT ck_deployment_threshold_source,
      DROP COLUMN threshold_assessment_attempt_id;
    ALTER TABLE public.stage2_model_publications DROP CONSTRAINT ck_publication_evaluation_source,
      DROP COLUMN evaluation_attempt_id, ALTER COLUMN evaluation_run_id SET NOT NULL;
    """)
    op.execute(original)
