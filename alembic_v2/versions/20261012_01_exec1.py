"""EXEC.1 removes administrative TEST locks; all integrity guards remain."""
from alembic import op

revision = "exec1_independent_test"
down_revision = "cell_checkpoint_reuse_v2"
branch_labels = None
depends_on = None

SQL = r"""
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
   THEN RAISE EXCEPTION 'ASSESSMENT_INCOMPLETE'; END IF;
  END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.v2_evaluation_complete() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public', 'pg_catalog' AS $$
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
 END IF;
 SELECT count(*),sum(weight) INTO n,w FROM public.evaluation_ensemble_members WHERE evaluation_id=e.id;
 IF (e.subject_kind='single' AND n<>0) OR (e.subject_kind='ensemble' AND (n<2 OR w IS DISTINCT FROM 1::numeric)) THEN RAISE EXCEPTION 'ENSEMBLE_INVALID'; END IF;
 IF EXISTS(SELECT 1 FROM public.evaluation_ensemble_members m JOIN public.model_versions v ON v.id=m.model_version_id JOIN public.runs tr ON tr.id=v.training_run_id WHERE m.evaluation_id=e.id AND (v.checkpoint_artifact_id IS DISTINCT FROM m.checkpoint_artifact_id OR tr.dataset_version_id IS DISTINCT FROM r.dataset_version_id)) THEN RAISE EXCEPTION 'ENSEMBLE_LINEAGE_MISMATCH'; END IF;
 RETURN NULL;
END $$;
"""


def upgrade() -> None:
    op.execute(SQL)


def downgrade() -> None:
    raise RuntimeError("EXEC1_DOWNGRADE_REQUIRES_EXPLICIT_REVIEW")
