-- E-04 approved overlay. No historical SQL or event is rewritten.
ALTER TABLE public.evaluations ADD CONSTRAINT ck_e04_selected_source CHECK (
 source_kind <> 'e10' OR evaluation_role <> 'calibration_selected'
 OR (threshold_source='validation_calibration' AND calibration_id IS NOT NULL));
ALTER TABLE public.evaluations ADD CONSTRAINT ck_e04_default_source CHECK (
 source_kind <> 'e10' OR evaluation_role <> 'calibration_default'
 OR (threshold_source='default' AND threshold_used=0.5 AND calibration_id IS NULL));
CREATE UNIQUE INDEX uq_e04_event_role ON public.evaluations(source_event_id,evaluation_role)
 WHERE source_kind='e10' AND evaluation_role IN ('calibration_default','calibration_selected');
-- NULL is an identity value, not permission to create another equivalent member.
-- Threshold and source_record_key deliberately do not participate.
CREATE UNIQUE INDEX uq_e04_contract_role ON public.evaluations
 (run_id,training_run_id,model_version_id,checkpoint_artifact_id,dataset_version_id,
 population_hash,protocol_version,protocol_hash,input_contract_hash,evaluation_role)
 NULLS NOT DISTINCT WHERE source_kind='e10'
 AND evaluation_role IN ('calibration_default','calibration_selected');

CREATE FUNCTION public.e04_legacy_admission() RETURNS trigger LANGUAGE plpgsql
 SET search_path=public,pg_catalog AS $$
BEGIN
 IF NEW.source_kind='legacy' AND current_user <> 'capstone_v2_migrator' THEN
   RAISE EXCEPTION 'E04_LEGACY_MIGRATOR_REQUIRED' USING ERRCODE='42501';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER e04_legacy_admission BEFORE INSERT ON public.evaluations
 FOR EACH ROW EXECUTE FUNCTION public.e04_legacy_admission();

CREATE FUNCTION public.e04_assert_calibration(member_id uuid) RETURNS void LANGUAGE plpgsql
 SET search_path=public,pg_catalog AS $$
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

CREATE FUNCTION public.e04_calibration_complete() RETURNS trigger LANGUAGE plpgsql
 SET search_path=public,pg_catalog AS $$
BEGIN
 IF TG_TABLE_NAME='evaluations' THEN
   PERFORM public.e04_assert_calibration(NEW.id);
 ELSE
   PERFORM public.e04_assert_calibration(NEW.default_evaluation_id);
   PERFORM public.e04_assert_calibration(NEW.selected_evaluation_id);
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER e04_evaluation_complete AFTER INSERT ON public.evaluations
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.e04_calibration_complete();
CREATE CONSTRAINT TRIGGER e04_calibration_complete AFTER INSERT OR UPDATE ON public.run_threshold_calibration
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.e04_calibration_complete();

CREATE FUNCTION public.e04_calibration_immutable() RETURNS trigger LANGUAGE plpgsql
 SET search_path=public,pg_catalog AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM public.evaluations WHERE source_kind='e10'
 AND id IN (OLD.default_evaluation_id,OLD.selected_evaluation_id)) THEN
   RAISE EXCEPTION 'E04_CALIBRATION_IMMUTABLE';
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER e04_calibration_immutable BEFORE UPDATE OR DELETE ON public.run_threshold_calibration
 FOR EACH ROW EXECUTE FUNCTION public.e04_calibration_immutable();
