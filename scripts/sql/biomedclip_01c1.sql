-- BIOMEDCLIP-01C-1. Apply only to an explicitly authorized target after backup.
-- Current schema only. Existing PK/FK/CHECK and conventional TRAIN semantics remain.
BEGIN;

CREATE FUNCTION public.pretrained_origin_v1() RETURNS jsonb LANGUAGE sql IMMUTABLE
AS $$ SELECT '{"architecture":"biomedclip_zero_shot","kind":"pretrained_external","mode":"zero_shot","model_repository":"microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224","revision":"9f341de24bfb00180f1b847274256e9b65a3a32e","schema":"pretrained_origin_v1","training_performed":false}'::jsonb $$;
CREATE FUNCTION public.pretrained_protocol_v1() RETURNS jsonb LANGUAGE sql IMMUTABLE
AS $$ SELECT '{"architecture":"biomedclip_zero_shot","checkpoint":"open_clip_pytorch_model.bin","classes":["uninfected","parasitized"],"components":{"open_clip_config.json":{"bytes":707,"sha256":"9a41f334a8c444678772c0ebb9ab854c97ab350bced3a17b803e258d39c23dc0"},"open_clip_pytorch_model.bin":{"bytes":783705670,"sha256":"52cc993c5c5ff962bd0c60931874bc001e7e9b41666a385530f4a036294576be"},"text/config.json":{"bytes":385,"sha256":"56bab767c02bc792897638feb8addc06d483d9c73769a5f554bbabea1f5507a1"},"text/tokenizer_config.json":{"bytes":28,"sha256":"53b6f42b8b8daddbdc6d3532c324187a92b46c1602bd6e8d4ad5a413b4fc90e1"},"text/vocab.txt":{"bytes":225062,"sha256":"7b36651908a88bc38bda41b728b2a598191e0d3b553cbacf7b1e5f026d5b5b9f"}},"embedding":{"dimension":512,"normalization":"L2","space":"multimodal_projected"},"format":"open_clip_pytorch_state_dict","model_repository":"microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224","open_clip_configuration":"open_clip_config.json","positive_class":1,"prompt_ensemble":false,"prompt_language":"en","prompts":["a microscopy image of an uninfected red blood cell.","a microscopy image of a red blood cell infected with malaria parasites."],"revision":"9f341de24bfb00180f1b847274256e9b65a3a32e","schema":"biomedclip_zero_shot_inference_v1","score":{"clinically_calibrated":false,"exp_logit_scale":85.2322769165039,"formula":"softmax(exp(logit_scale) * cosine(image,text))[1]","logit_scale_source":"checkpoint.logit_scale","semantics":"relative_to_two_prompts"},"text_encoder":"microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract","text_pooling":"cls_last_hidden_state_pooler","text_projection":"mlp","text_revision":"d673b8835373c6fa116d6d8006b33d48734e305d","threshold":{"calibration":null,"comparison":">=","schema":"pretrained_fixed_threshold_v1","source":"protocol_before_test","value":0.5},"tokenizer":{"clean":"whitespace","context_length":256,"do_lower_case":true,"padding":"max_length","repository":"microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract","revision":"d673b8835373c6fa116d6d8006b33d48734e305d","strip_sep_token":false,"truncation":true},"transform":{"antialias":true,"center_crop":[224,224],"color":"RGB","dtype":"float32","interpolation":"bicubic","layout":"NCHW","mean":[0.48145466,0.4578275,0.40821073],"resize_shortest":224,"std":[0.26862954,0.26130258,0.27577711],"tensor_scale":"uint8_div_255"},"visual_encoder":"vit_base_patch16_224","visual_projection":"linear"}'::jsonb $$;

INSERT INTO public.models(name,model_type,framework,architecture,description,pretrained,pretrained_source,metadata)
VALUES ('biomedclip_zero_shot','classification','pytorch/open_clip','BiomedCLIP Zero-shot',
 'Origen preentrenado externo; no requiere entrenamiento local',true,
 'microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224','{"family":"biomedclip","trainable":false,"registration":"pretrained_origin_v1"}');

CREATE FUNCTION public.pretrained_configuration_valid(r public.runs) RETURNS boolean
LANGUAGE plpgsql STABLE SET search_path TO public,pg_catalog AS $$
DECLARE c jsonb; d jsonb; f jsonb; m public.models; v public.dataset_versions; mat public.dataset_materializations;
BEGIN
 c:=r.execution_parameters->'pretrained_configuration'; d:=c->'target_dataset';
 SELECT * INTO m FROM models WHERE id=r.model_id;
 SELECT * INTO v FROM dataset_versions WHERE id=r.dataset_version_id;
 f:=v.methodology_json->'freeze_contract';
 SELECT * INTO mat FROM dataset_materializations WHERE id=(d->>'dataset_materialization_id')::uuid;
 RETURN coalesce(
 r.run_type='training' AND r.campaign_id IS NULL AND m.name='biomedclip_zero_shot'
 AND m.metadata->'trainable'='false'::jsonb AND m.framework='pytorch/open_clip'
 AND m.pretrained AND m.pretrained_source=pretrained_origin_v1()->>'model_repository'
 AND r.execution_parameters->'scientific_origin'=pretrained_origin_v1()
 AND campaign_json_object(r.execution_parameters,ARRAY['scientific_origin','pretrained_configuration','configuration_hash'])
 AND campaign_json_object(c,ARRAY['schema','scientific_origin','inference','target_dataset','framework','framework_versions'])
 AND c->>'schema'='pretrained_configuration_v1' AND c->'scientific_origin'=pretrained_origin_v1()
 AND c->'inference'=pretrained_protocol_v1() AND c->>'framework'='pytorch/open_clip'
 AND campaign_json_object(c->'framework_versions',ARRAY['torch','torchvision','open_clip_torch','transformers','timm','tokenizers','numpy'])
 AND NOT EXISTS(SELECT 1 FROM jsonb_each(c->'framework_versions') WHERE jsonb_typeof(value)<>'string' OR length(btrim(value#>>'{}'))=0)
 AND r.execution_parameters->>'configuration_hash'=encode(digest(convert_to(assessment_canonical(c),'UTF8'),'sha256'),'hex')
 AND campaign_json_object(d,ARRAY['dataset_version_id','dataset_materialization_id','dataset_root','patient_assignment_fingerprint','record_assignment_fingerprint','source_population_fingerprint','clinical_identity_fingerprint','counts','selection_unit'])
 AND d->>'dataset_version_id'=r.dataset_version_id::text AND d->>'selection_unit'='dataset_version_id'
 AND v.status='FROZEN' AND f->>'version'='malaria_patient_split_freeze_v1'
 AND f->>'dataset_version_id'=v.id::text AND f->>'dataset_materialization_id'=mat.id::text
 AND mat.dataset_version_id=v.id AND mat.status='READY' AND mat.reconciliation_status='PASS'
 AND NOT EXISTS(SELECT 1 FROM unnest(ARRAY['identity_coverage','identity_conflicts','patient_train_val_overlap',
  'patient_train_test_overlap','patient_val_test_overlap','duplicate_cross_split_overlap','assignment_count',
  'source_record_count','split_completeness','class_presence_train','class_presence_val','class_presence_test']) required(name)
  WHERE NOT EXISTS(SELECT 1 FROM (SELECT DISTINCT ON(check_name) check_name,status,blocking_for_validation
   FROM dataset_split_validation_checks WHERE dataset_version_id=v.id ORDER BY check_name,executed_at DESC,id DESC) checks
   WHERE checks.check_name=required.name AND checks.status='PASS' AND checks.blocking_for_validation))
 AND NOT EXISTS(SELECT 1 FROM (SELECT DISTINCT ON(check_name) status,blocking_for_validation
   FROM dataset_split_validation_checks WHERE dataset_version_id=v.id ORDER BY check_name,executed_at DESC,id DESC) checks
   WHERE checks.status='FAIL' AND checks.blocking_for_validation)
 AND d->>'patient_assignment_fingerprint'=f->'fingerprints'->>'patient_assignment_sha256'
 AND d->>'record_assignment_fingerprint'=f->'fingerprints'->>'record_assignment_sha256'
 AND d->>'source_population_fingerprint'=f->'fingerprints'->>'source_population_sha256'
 AND d->>'clinical_identity_fingerprint'=f->'fingerprints'->>'clinical_identity_sha256'
 AND d->>'dataset_root' LIKE '%/data/'||mat.relative_root
 AND NOT EXISTS(SELECT 1 FROM (VALUES ('train'),('val'),('test')) split(name)
   WHERE (d->'counts'->>split.name)::bigint IS DISTINCT FROM
   (SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=v.id AND split_name=split.name))
 AND NOT EXISTS(SELECT 1 FROM run_configurations WHERE run_id=r.id)
 AND r.max_epochs IS NULL AND r.total_epochs IS NULL AND r.completed_epochs=0
 AND r.best_epoch IS NULL AND r.stopped_epoch IS NULL AND r.fine_tuning_start_epoch IS NULL
 AND r.checkpoint_monitor IS NULL AND r.checkpoint_mode IS NULL AND r.best_validation_value IS NULL
 AND r.early_stopping_enabled IS NULL AND r.early_stopping_patience IS NULL
 AND r.early_stopping_min_delta IS NULL AND r.restore_best_weights IS NULL
 AND r.parameters='{}'::jsonb AND r.configuration IS NULL
 ,false);
END $$;

CREATE FUNCTION public.pretrained_completion_valid(rid uuid, completion jsonb) RETURNS boolean
LANGUAGE plpgsql STABLE SET search_path TO public,pg_catalog AS $$
DECLARE r public.runs; s public.train_execution_sessions; a public.artifacts; mv public.model_versions; c jsonb; spec jsonb;
BEGIN
 SELECT * INTO r FROM runs WHERE id=rid;
 SELECT * INTO s FROM train_execution_sessions WHERE run_id=rid;
 SELECT * INTO a FROM artifacts WHERE id=(completion->>'artifact_id')::uuid;
 SELECT * INTO mv FROM model_versions WHERE id=(completion->>'model_version_id')::uuid;
 c:=r.execution_parameters->'pretrained_configuration'; spec:=pretrained_protocol_v1();
 RETURN coalesce(pretrained_configuration_valid(r)
 AND s.configuration=c AND s.dataset=c->'target_dataset' AND s.attempt_id IS NULL
 AND s.environment->'packages'=c->'framework_versions' AND s.environment->>'operation'='register_pretrained'
 AND s.artifact_root LIKE '%/outputs/train_runs/'||rid::text
 AND s.artifact_root NOT LIKE '%/../%' AND s.artifact_root NOT LIKE '%/.cache/%'
 AND completion=jsonb_build_object('schema','pretrained_completion_v1','run_id',rid::text,
  'owner',s.owner::text,'model_id',r.model_id::text,'dataset_version_id',r.dataset_version_id::text,
  'artifact_id',a.id::text,'model_version_id',mv.id::text,
  'configuration_hash',r.execution_parameters->>'configuration_hash','components_hash','1d1ca160d9b7783ae033a05587f850949dc6a36307536c52fd3c51fe080c18c6')
 AND a.run_id=rid AND a.artifact_type='model_checkpoint'
 AND a.path=s.artifact_root||'/open_clip_pytorch_model.bin'
 AND a.checksum=spec->'components'->'open_clip_pytorch_model.bin'->>'sha256'
 AND a.file_size_bytes=(spec->'components'->'open_clip_pytorch_model.bin'->>'bytes')::bigint
 AND a.artifact_status='available'
 AND (SELECT count(*) FROM artifacts WHERE run_id=rid)=5
 AND NOT EXISTS(SELECT 1 FROM jsonb_each(spec->'components') x WHERE NOT EXISTS(
  SELECT 1 FROM artifacts ar WHERE ar.run_id=rid AND ar.path=s.artifact_root||'/'||x.key
  AND ar.checksum=x.value->>'sha256' AND ar.file_size_bytes=(x.value->>'bytes')::bigint
  AND ar.artifact_status='available'
  AND ar.artifact_type=CASE WHEN x.key='open_clip_pytorch_model.bin' THEN 'model_checkpoint' ELSE 'model_component' END
  AND ar.metadata=jsonb_build_object('scientific_origin',pretrained_origin_v1(),
      'configuration_hash',r.execution_parameters->>'configuration_hash','component',x.key)))
 AND mv.model_id=r.model_id AND mv.model_name='biomedclip_zero_shot' AND mv.training_run_id=rid
 AND mv.checkpoint_artifact_id=a.id AND mv.checkpoint_path=a.path AND mv.artifact_uri=a.path
 AND mv.artifact_sha256=a.checksum AND mv.artifact_size_bytes=a.file_size_bytes
 AND mv.status='candidate' AND mv.lineage_status='resolved' AND mv.framework='pytorch/open_clip'
 AND mv.framework_version=c->'framework_versions'->>'torch'
 AND mv.preprocessing_profile_snapshot=spec->'transform'
 AND mv.class_mapping='{"uninfected":0,"parasitized":1}'::jsonb
 AND mv.input_signature='{"shape":[null,3,224,224],"dtype":"float32","layout":"NCHW"}'::jsonb
 AND mv.output_signature='{"shape":[null,2],"positive_class":1,"semantics":"relative_to_two_prompts"}'::jsonb
 AND mv.metadata=jsonb_build_object('scientific_origin',pretrained_origin_v1(),'configuration_hash',r.execution_parameters->>'configuration_hash')
 AND NOT EXISTS(SELECT 1 FROM train_execution_records WHERE run_id=rid)
 AND NOT EXISTS(SELECT 1 FROM training_history WHERE run_id=rid)
 ,false);
END $$;

CREATE FUNCTION public.pretrained_run_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path TO public,pg_catalog AS $$
DECLARE relevant boolean;
BEGIN
 relevant:=EXISTS(SELECT 1 FROM models WHERE id=NEW.model_id AND name='biomedclip_zero_shot')
 OR NEW.execution_parameters ? 'scientific_origin' OR NEW.execution_parameters ? 'pretrained_configuration';
 IF TG_OP='UPDATE' AND (OLD.execution_parameters ? 'scientific_origin' OR relevant) THEN
  IF (to_jsonb(NEW)-ARRAY['status','finished_at','duration_seconds','updated_at']) IS DISTINCT FROM
     (to_jsonb(OLD)-ARRAY['status','finished_at','duration_seconds','updated_at'])
  THEN RAISE EXCEPTION 'PRETRAINED_ORIGIN_IMMUTABLE'; END IF;
  IF OLD.status='completed' THEN RAISE EXCEPTION 'PRETRAINED_ORIGIN_IMMUTABLE'; END IF;
 END IF;
 IF relevant AND NOT pretrained_configuration_valid(NEW) THEN RAISE EXCEPTION 'PRETRAINED_CONFIGURATION_INVALID'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER pretrained_run_guard BEFORE INSERT OR UPDATE ON public.runs
FOR EACH ROW EXECUTE FUNCTION public.pretrained_run_guard();
CREATE UNIQUE INDEX pretrained_scientific_identity ON public.runs ((execution_parameters->>'configuration_hash'))
WHERE execution_parameters ? 'scientific_origin';

CREATE FUNCTION public.pretrained_session_insert_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path TO public,pg_catalog AS $$
DECLARE r public.runs;
BEGIN
 SELECT * INTO r FROM runs WHERE id=NEW.run_id;
 IF r.execution_parameters ? 'scientific_origin' AND (
   NOT pretrained_configuration_valid(r) OR NEW.state<>'active'
   OR NEW.owner::text IS DISTINCT FROM current_setting('capstone.train_owner',true)
   OR NEW.configuration IS DISTINCT FROM r.execution_parameters->'pretrained_configuration'
   OR NEW.dataset IS DISTINCT FROM NEW.configuration->'target_dataset' OR NEW.attempt_id IS NOT NULL)
 THEN RAISE EXCEPTION 'PRETRAINED_SESSION_INVALID'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER pretrained_session_insert_guard BEFORE INSERT ON public.train_execution_sessions
FOR EACH ROW EXECUTE FUNCTION public.pretrained_session_insert_guard();

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
 IF EXISTS(SELECT 1 FROM runs WHERE id=NEW.run_id AND execution_parameters ? 'scientific_origin') THEN
   IF NEW.state IN ('completed','verified') AND NOT pretrained_completion_valid(NEW.run_id,NEW.completion)
   THEN RAISE EXCEPTION 'PRETRAINED_VERIFICATION_INCOMPLETE'; END IF;
   IF NEW.state='verified' AND NEW.verification IS DISTINCT FROM
      jsonb_build_object('status','verified','completion',NEW.completion,'components',pretrained_protocol_v1()->'components')
   THEN RAISE EXCEPTION 'PRETRAINED_VERIFICATION_INCOMPLETE'; END IF;
   RETURN NEW;
 END IF;
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
LANGUAGE plpgsql SET search_path TO public,pg_catalog AS $$
DECLARE r public.runs; s public.train_execution_sessions;
BEGIN
 SELECT * INTO r FROM runs WHERE id=NEW.id;
 IF r.execution_parameters ? 'scientific_origin' THEN
   SELECT * INTO s FROM train_execution_sessions WHERE run_id=r.id;
   IF NOT pretrained_completion_valid(r.id,s.completion) OR s.state IS DISTINCT FROM 'verified'
      OR r.status IS DISTINCT FROM 'completed'
   THEN RAISE EXCEPTION 'PRETRAINED_REGISTRATION_INCOMPLETE'; END IF;
 ELSIF NEW.run_type='training' AND NOT EXISTS(SELECT 1 FROM public.run_configurations WHERE run_id=NEW.id)
 THEN RAISE EXCEPTION 'TRAIN_CONFIGURATION_REQUIRED'; END IF;
 RETURN NULL;
END $$;

CREATE FUNCTION public.pretrained_no_learning_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path TO public,pg_catalog AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM runs WHERE id=NEW.run_id AND execution_parameters ? 'scientific_origin')
 THEN RAISE EXCEPTION 'PRETRAINED_LEARNING_EVIDENCE_FORBIDDEN'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER pretrained_no_learning_guard BEFORE INSERT OR UPDATE ON public.train_execution_records
FOR EACH ROW EXECUTE FUNCTION public.pretrained_no_learning_guard();
CREATE TRIGGER pretrained_no_learning_guard BEFORE INSERT OR UPDATE ON public.training_history
FOR EACH ROW EXECUTE FUNCTION public.pretrained_no_learning_guard();
CREATE TRIGGER pretrained_no_learning_guard BEFORE INSERT OR UPDATE ON public.run_configurations
FOR EACH ROW EXECUTE FUNCTION public.pretrained_no_learning_guard();

CREATE FUNCTION public.pretrained_artifact_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path TO public,pg_catalog AS $$
DECLARE rid uuid; spec jsonb; s public.train_execution_sessions; r public.runs;
BEGIN
 rid:=CASE WHEN TG_OP='INSERT' THEN NEW.run_id ELSE OLD.run_id END;
 SELECT * INTO r FROM runs WHERE id=rid;
 IF r.execution_parameters ? 'scientific_origin' THEN
   IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'PRETRAINED_ARTIFACT_IMMUTABLE'; END IF;
   SELECT * INTO s FROM train_execution_sessions WHERE run_id=rid;
   spec:=pretrained_protocol_v1()->'components'->(NEW.metadata->>'component');
   IF spec IS NULL OR s.state IS DISTINCT FROM 'active' OR s.owner::text IS DISTINCT FROM current_setting('capstone.train_owner',true)
    OR NEW.path IS DISTINCT FROM s.artifact_root||'/'||(NEW.metadata->>'component')
    OR NEW.checksum IS DISTINCT FROM spec->>'sha256' OR NEW.file_size_bytes IS DISTINCT FROM (spec->>'bytes')::bigint
    OR NEW.metadata IS DISTINCT FROM jsonb_build_object('scientific_origin',pretrained_origin_v1(),
       'configuration_hash',r.execution_parameters->>'configuration_hash','component',NEW.metadata->>'component')
   THEN RAISE EXCEPTION 'PRETRAINED_ARTIFACT_INVALID'; END IF;
 ELSIF TG_OP<>'DELETE' AND (NEW.metadata ? 'scientific_origin' OR EXISTS(SELECT 1 FROM runs WHERE id=NEW.run_id AND execution_parameters ? 'scientific_origin')) THEN
   RAISE EXCEPTION 'PRETRAINED_ARTIFACT_OWNER_INVALID';
 END IF;
 RETURN CASE WHEN TG_OP='DELETE' THEN OLD ELSE NEW END;
END $$;
CREATE TRIGGER pretrained_artifact_guard BEFORE INSERT OR UPDATE OR DELETE ON public.artifacts
FOR EACH ROW EXECUTE FUNCTION public.pretrained_artifact_guard();

CREATE FUNCTION public.pretrained_version_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path TO public,pg_catalog AS $$
DECLARE rid uuid; r public.runs; a public.artifacts; s public.train_execution_sessions;
BEGIN
 rid:=CASE WHEN TG_OP='INSERT' THEN NEW.training_run_id ELSE OLD.training_run_id END;
 SELECT * INTO r FROM runs WHERE id=rid;
 IF r.execution_parameters ? 'scientific_origin' THEN
   IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'PRETRAINED_VERSION_IMMUTABLE'; END IF;
   SELECT * INTO a FROM artifacts WHERE id=NEW.checkpoint_artifact_id;
   SELECT * INTO s FROM train_execution_sessions WHERE run_id=rid;
   IF NEW.model_id IS DISTINCT FROM r.model_id OR a.run_id IS DISTINCT FROM rid
      OR NEW.artifact_sha256 IS DISTINCT FROM a.checksum OR NEW.artifact_size_bytes IS DISTINCT FROM a.file_size_bytes
      OR NEW.checkpoint_path IS DISTINCT FROM a.path OR NEW.status IS DISTINCT FROM 'candidate'
      OR s.owner::text IS DISTINCT FROM current_setting('capstone.train_owner',true) OR s.state IS DISTINCT FROM 'active'
   THEN RAISE EXCEPTION 'PRETRAINED_VERSION_BINDING_INVALID'; END IF;
 ELSIF TG_OP<>'DELETE' AND (NEW.metadata ? 'scientific_origin' OR EXISTS(SELECT 1 FROM runs WHERE id=NEW.training_run_id AND execution_parameters ? 'scientific_origin') OR EXISTS(SELECT 1 FROM models WHERE id=NEW.model_id AND name='biomedclip_zero_shot')) THEN
   RAISE EXCEPTION 'PRETRAINED_VERSION_BINDING_INVALID';
 END IF;
 RETURN CASE WHEN TG_OP='DELETE' THEN OLD ELSE NEW END;
END $$;
CREATE TRIGGER pretrained_version_guard BEFORE INSERT OR UPDATE OR DELETE ON public.model_versions
FOR EACH ROW EXECUTE FUNCTION public.pretrained_version_guard();

CREATE FUNCTION public.pretrained_catalog_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path TO public,pg_catalog AS $$
BEGIN
 IF OLD.name='biomedclip_zero_shot' OR (TG_OP='UPDATE' AND NEW.name='biomedclip_zero_shot')
 THEN RAISE EXCEPTION 'PRETRAINED_CATALOG_IMMUTABLE'; END IF;
 RETURN CASE WHEN TG_OP='DELETE' THEN OLD ELSE NEW END;
END $$;
CREATE TRIGGER pretrained_catalog_guard BEFORE UPDATE OR DELETE ON public.models
FOR EACH ROW EXECUTE FUNCTION public.pretrained_catalog_guard();

CREATE FUNCTION public.pretrained_campaign_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path TO public,pg_catalog AS $$
BEGIN
 IF NEW.configuration->>'model_id'='biomedclip_zero_shot'
 THEN RAISE EXCEPTION 'MODEL_NOT_TRAINABLE'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER pretrained_campaign_guard BEFORE INSERT OR UPDATE ON public.campaign_configurations
FOR EACH ROW EXECUTE FUNCTION public.pretrained_campaign_guard();
COMMIT;
