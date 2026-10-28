-- campaign_configurations: accept the input contract of trained BiomedCLIP heads.
--
-- campaign_configuration_valid only knew the Keras contract (malaria_input_v1). This adds one
-- branch for openclip_supervised_input_v1, checked with the same rigor (architecture and adapter
-- bound to the configuration, canonical label mapping, sigmoid output, input shape equal to
-- model.input_shape, external mode equal to model.preprocessing). The Keras branch is unchanged.
-- The Keras branch below is the previous definition, unchanged.
BEGIN;
CREATE OR REPLACE FUNCTION public.campaign_configuration_valid(v jsonb)
 RETURNS boolean
 LANGUAGE plpgsql
 IMMUTABLE
 SET search_path TO 'public', 'pg_catalog'
AS $function$
DECLARE r jsonb; m jsonb; e jsonb; i jsonb; o jsonb; x jsonb; k text;
BEGIN
 IF NOT campaign_json_object(v,ARRAY['schema_version','model_id','adapter_version','resolved'])
   OR v->>'schema_version' IS DISTINCT FROM 'model_config_v1'
   OR NOT campaign_json_string(v->'model_id') OR NOT campaign_json_string(v->'adapter_version') THEN RETURN false; END IF;
 r=v->'resolved';
 IF NOT campaign_json_object(r,ARRAY['model','optimizer','execution','recipe','selection','input_contract']) THEN RETURN false; END IF;
 m=r->'model';e=r->'execution';i=r->'input_contract';o=r->'optimizer';
 IF NOT campaign_json_object(m,ARRAY['input_shape','preprocessing','weights','dropout','l2','head_units','batch_normalization','fine_tune_layers'])
   OR NOT campaign_json_object(o,ARRAY['name','parameters','fine_tune_learning_rate'])
   OR NOT campaign_json_string(o->'name') OR jsonb_typeof(o->'parameters') IS DISTINCT FROM 'object'
   OR jsonb_typeof(o->'fine_tune_learning_rate') IS DISTINCT FROM 'number'
   OR NOT campaign_json_object(e,ARRAY['max_epochs','fine_tune_epochs','batch_size','deterministic_ops','no_augment','checkpoint_policy','checkpoint_mode','min_recall','beta','reject_prediction_collapse','min_class_fraction','calibrate_threshold','target_recall','min_specificity','early_stopping','early_stopping_mode','early_stopping_patience','early_stopping_min_delta','restore_best_weights','evaluate_best_on_test'])
   OR e ? 'seed' OR e->'evaluate_best_on_test' IS DISTINCT FROM 'false'::jsonb
   OR NOT campaign_json_integer(e->'max_epochs',1) OR NOT campaign_json_integer(e->'fine_tune_epochs',0)
   OR NOT campaign_json_integer(e->'batch_size',1) OR NOT campaign_json_integer(e->'early_stopping_patience',0)
   OR NOT campaign_json_object(r->'recipe',ARRAY['loss','metrics','augmentation','reduce_lr','selection_threshold','fallback','clinical_success_independent_of_technical_completion'])
   OR NOT campaign_json_object(r->'selection',ARRAY['monitor','mode','explicit','early_stopping_monitor','early_stopping_mode','threshold','beta','clinical_objective','fallback'])
   THEN RETURN false; END IF;
 FOREACH k IN ARRAY ARRAY['preprocessing','weights','batch_normalization'] LOOP
   IF NOT campaign_json_string(m->k) THEN RETURN false; END IF;
 END LOOP;
 IF jsonb_typeof(m->'dropout') IS DISTINCT FROM 'number' OR jsonb_typeof(m->'l2') IS DISTINCT FROM 'number'
   OR NOT campaign_json_integer(m->'head_units',0) OR NOT campaign_json_integer(m->'fine_tune_layers',0)
   THEN RETURN false; END IF;
 FOREACH k IN ARRAY ARRAY['deterministic_ops','no_augment','reject_prediction_collapse','calibrate_threshold','early_stopping','restore_best_weights'] LOOP
   IF jsonb_typeof(e->k) IS DISTINCT FROM 'boolean' THEN RETURN false; END IF;
 END LOOP;
 FOREACH k IN ARRAY ARRAY['min_recall','beta','min_class_fraction','target_recall','min_specificity','early_stopping_min_delta'] LOOP
   IF jsonb_typeof(e->k) IS DISTINCT FROM 'number' THEN RETURN false; END IF;
 END LOOP;
 FOREACH k IN ARRAY ARRAY['checkpoint_policy','checkpoint_mode','early_stopping_mode'] LOOP
   IF NOT campaign_json_string(e->k) THEN RETURN false; END IF;
 END LOOP;
 -- Monitor values are optional in E2; presence is mandatory, JSON null is allowed.
 FOREACH k IN ARRAY ARRAY['checkpoint_monitor','early_stopping_monitor'] LOOP
   IF NOT (e ? k) OR (e->k<>'null'::jsonb AND NOT campaign_json_string(e->k)) THEN RETURN false; END IF;
 END LOOP;
 IF NOT campaign_json_string(r->'recipe'->'loss') OR NOT campaign_json_string(r->'recipe'->'metrics')
   OR jsonb_typeof(r->'recipe'->'augmentation') IS DISTINCT FROM 'object'
   OR jsonb_typeof(r->'recipe'->'reduce_lr') IS DISTINCT FROM 'object'
   OR jsonb_typeof(r->'recipe'->'selection_threshold') IS DISTINCT FROM 'number'
   OR NOT campaign_json_string(r->'recipe'->'fallback')
   OR r->'recipe'->'clinical_success_independent_of_technical_completion' IS DISTINCT FROM 'true'::jsonb
   OR jsonb_typeof(r->'selection'->'explicit') IS DISTINCT FROM 'boolean'
   OR jsonb_typeof(r->'selection'->'threshold') IS DISTINCT FROM 'number'
   OR jsonb_typeof(r->'selection'->'beta') IS DISTINCT FROM 'number' THEN RETURN false; END IF;
 FOREACH k IN ARRAY ARRAY['monitor','mode','early_stopping_monitor','early_stopping_mode','clinical_objective','fallback'] LOOP
   IF NOT campaign_json_string(r->'selection'->k) THEN RETURN false; END IF;
 END LOOP;
 IF i->>'schema_version'='openclip_supervised_input_v1' THEN
   -- Trained BiomedCLIP head: the registered base fixes transform and encoder (see models.biomedclip_training).
   IF NOT campaign_json_object(i,ARRAY['schema_version','architecture','adapter_version','framework','external','head','label_mapping','input','output'])
     OR i->>'architecture' IS DISTINCT FROM v->>'model_id' OR i->>'adapter_version' IS DISTINCT FROM v->>'adapter_version'
     OR i->>'framework' IS DISTINCT FROM 'pytorch_openclip'
     OR NOT campaign_json_object(i->'external',ARRAY['mode','embedding','base_model'])
     OR i->'label_mapping' IS DISTINCT FROM '{"0":"uninfected","1":"parasitized","positive_class": 1,"positive_label":"parasitized"}'::jsonb
     OR i->'output' IS DISTINCT FROM '{"shape":[null,1],"activation":"sigmoid","meaning":"probability_parasitized"}'::jsonb
     OR jsonb_typeof(m->'input_shape') IS DISTINCT FROM 'array' OR jsonb_array_length(m->'input_shape')<>3
     OR jsonb_typeof(i->'input'->'shape') IS DISTINCT FROM 'array' OR jsonb_array_length(i->'input'->'shape')<>4
     OR i->'input'->'shape'->0 IS DISTINCT FROM 'null'::jsonb
     THEN RETURN false; END IF;
   FOR x IN SELECT value FROM jsonb_array_elements(m->'input_shape') LOOP
     IF NOT campaign_json_integer(x,1) THEN RETURN false; END IF;
   END LOOP;
   RETURN ((i->'input'->'shape') - 0) = m->'input_shape' AND (m->'input_shape'->2)='3'::jsonb
     AND i->'external'->>'mode'=m->>'preprocessing';
 END IF;
 IF NOT campaign_json_object(i,ARRAY['schema_version','architecture','adapter_version','shape','dtype','channels','source_order','source_scale','decode','resize','external','internal','label_mapping','output'])
   THEN RETURN false; END IF;
 IF i->>'schema_version' IS DISTINCT FROM 'malaria_input_v1'
   OR i->>'architecture' IS DISTINCT FROM v->>'model_id' OR i->>'adapter_version' IS DISTINCT FROM v->>'adapter_version'
   OR i->>'dtype' IS DISTINCT FROM 'float32' OR i->'channels' IS DISTINCT FROM '3'::jsonb
   OR i->>'source_order' IS DISTINCT FROM 'RGB' OR i->>'source_scale' IS DISTINCT FROM '0_255'
   OR i->>'decode' IS DISTINCT FROM 'tf_decode_image_rgb_v1'
   OR i->'resize' IS DISTINCT FROM '{"method":"bilinear","antialias": false,"location":"loader"}'::jsonb
   OR NOT campaign_json_object(i->'external',ARRAY['mode','version','location','output_order'])
   OR jsonb_typeof(i->'internal') IS DISTINCT FROM 'object'
   OR NOT ((i->'internal') ?& ARRAY['mode','location'])
   OR NOT campaign_json_object(i->'output',ARRAY['shape','dtype','meaning','activation'])
   OR i->'label_mapping' IS DISTINCT FROM '{"0":"uninfected","1":"parasitized","positive_class": 1,"positive_label":"parasitized"}'::jsonb
   OR jsonb_typeof(m->'input_shape') IS DISTINCT FROM 'array' OR jsonb_array_length(m->'input_shape')<>3
   OR jsonb_typeof(i->'shape') IS DISTINCT FROM 'array' OR jsonb_array_length(i->'shape')<>4
   OR i->'shape'->0 IS DISTINCT FROM 'null'::jsonb
   THEN RETURN false; END IF;
 FOR x IN SELECT value FROM jsonb_array_elements(m->'input_shape') LOOP
   IF NOT campaign_json_integer(x,1) THEN RETURN false; END IF;
 END LOOP;
 RETURN ((i->'shape') - 0) = m->'input_shape' AND (m->'input_shape'->2)='3'::jsonb
   AND i->'external'->>'mode'=m->>'preprocessing';
END $function$;
COMMIT;
