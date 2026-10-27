-- Backup of the two replaced current functions; restore only before any registered origin exists.
CREATE OR REPLACE FUNCTION public.train_session_guard() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO 'public', 'pg_catalog'
    AS $_$
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
END $_$;
CREATE OR REPLACE FUNCTION public.v2_run_configuration_required() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO 'public', 'pg_catalog'
    AS $$ BEGIN
 IF NEW.run_type='training' AND NOT EXISTS(SELECT 1 FROM public.run_configurations WHERE run_id=NEW.id) THEN RAISE EXCEPTION 'TRAIN_CONFIGURATION_REQUIRED'; END IF;
 RETURN NULL;
END $$;
