"""Reject NULL contracts and protect accredited relational TRAIN identity.

Forward correction: 20260911_01 is preserved even when its installed state is unknown.
"""

import sqlalchemy as sa

from alembic import op

revision = "20260911_02"
down_revision = "20260911_01"
branch_labels = None
depends_on = None

DDL = r"""
CREATE FUNCTION campaign_json_object(v jsonb, required_keys text[]) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE k text;
BEGIN
 IF jsonb_typeof(v) IS DISTINCT FROM 'object' THEN RETURN false; END IF;
 FOREACH k IN ARRAY required_keys LOOP
   IF NOT (v ? k) OR v->k='null'::jsonb THEN RETURN false; END IF;
 END LOOP;
 RETURN true;
END $$;
CREATE FUNCTION campaign_json_string(v jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
 SELECT coalesce(jsonb_typeof(v)='string' AND length(btrim(v #>> '{}'))>0,false)
$$;
CREATE FUNCTION campaign_json_integer(v jsonb,minimum_value numeric) RETURNS boolean LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE n numeric;
BEGIN
 IF jsonb_typeof(v) IS DISTINCT FROM 'number' THEN RETURN false; END IF;
 n=(v #>> '{}')::numeric;
 RETURN n=trunc(n) AND n>=minimum_value AND n<=2147483647;
END $$;
CREATE FUNCTION campaign_configuration_valid(v jsonb) RETURNS boolean LANGUAGE plpgsql IMMUTABLE AS $$
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
   OR NOT campaign_json_object(i,ARRAY['schema_version','architecture','adapter_version','shape','dtype','channels','source_order','source_scale','decode','resize','external','internal','label_mapping','output'])
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
END $$;
CREATE FUNCTION campaign_contract_valid(v jsonb) RETURNS boolean LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE p jsonb; b jsonb; matrix jsonb; seeds jsonb; configs jsonb; members jsonb;
 env jsonb; x jsonb; item record; seen_seeds jsonb='[]'; descriptor jsonb; k text;
 n integer; idx integer=0;
BEGIN
 -- experiment_id alone is intentionally nullable; its presence remains mandatory.
 IF NOT campaign_json_object(v,ARRAY['version','name','purpose','dataset','dataset_evidence_id','requested','protocol','environment','matrix'])
   OR NOT (v ? 'experiment_id') OR v->>'version' IS DISTINCT FROM 'campaign_contract_v1'
   OR NOT campaign_json_string(v->'name') OR NOT campaign_json_string(v->'purpose')
   OR NOT campaign_json_string(v->'dataset_evidence_id')
   OR NOT campaign_json_object(v->'dataset',ARRAY['dataset_version_id','dataset_materialization_id','dataset_root','patient_assignment_fingerprint','record_assignment_fingerprint','source_population_fingerprint','clinical_identity_fingerprint','counts','selection_unit'])
   OR jsonb_typeof(v->'requested') IS DISTINCT FROM 'object' THEN RETURN false; END IF;
 p=v->'protocol';
 IF NOT campaign_json_object(p,ARRAY['version','objective','metrics','sensitivity_target','specificity_minimum','roles','ranking','checkpoint','early_stopping','calibration','budget','missing','retries','fallback','test_access','aggregation','uncertainty','limitations','pending'])
   OR NOT campaign_json_string(p->'version') OR NOT campaign_json_string(p->'objective')
   OR p->'pending' IS DISTINCT FROM '[]'::jsonb
   OR p->'roles' IS DISTINCT FROM '{"train":"train","selection":"val","calibration":"val","final_test":"test"}'::jsonb
   OR p->>'test_access' IS DISTINCT FROM 'final_only_after_candidate_lock'
   OR p->>'retries' IS DISTINCT FROM 'first_verified_attempt'
   OR p->>'missing' IS DISTINCT FROM 'report_all_members' OR p->>'fallback' IS DISTINCT FROM 'diagnostic_only'
   OR jsonb_typeof(p->'sensitivity_target') IS DISTINCT FROM 'number'
   OR jsonb_typeof(p->'specificity_minimum') IS DISTINCT FROM 'number' THEN RETURN false; END IF;
 IF (p->>'sensitivity_target')::numeric NOT BETWEEN 0 AND 1 OR (p->>'specificity_minimum')::numeric NOT BETWEEN 0 AND 1 THEN RETURN false; END IF;
 b=p->'budget';
 IF NOT campaign_json_object(b,ARRAY['max_members','max_attempts_per_member'])
   OR NOT campaign_json_integer(b->'max_members',1) OR NOT campaign_json_integer(b->'max_attempts_per_member',1)
   OR NOT campaign_json_object(p->'metrics',ARRAY['primary','secondary','definitions_version','compliance'])
   OR jsonb_typeof(p->'metrics'->'primary') IS DISTINCT FROM 'array' OR jsonb_array_length(p->'metrics'->'primary')=0
   OR jsonb_typeof(p->'metrics'->'secondary') IS DISTINCT FROM 'array'
   OR NOT campaign_json_string(p->'metrics'->'definitions_version')
   OR p->'metrics'->>'compliance' NOT IN ('point_estimate','confidence_bound')
   OR NOT campaign_json_object(p->'ranking',ARRAY['partition','criteria','tie_breaks'])
   OR p->'ranking'->>'partition' IS DISTINCT FROM 'val'
   OR jsonb_typeof(p->'ranking'->'criteria') IS DISTINCT FROM 'array' OR jsonb_array_length(p->'ranking'->'criteria')=0
   OR jsonb_typeof(p->'ranking'->'tie_breaks') IS DISTINCT FROM 'array' OR jsonb_array_length(p->'ranking'->'tie_breaks')=0
   OR NOT campaign_json_object(p->'checkpoint',ARRAY['policy','monitor','mode','threshold'])
   OR p->'checkpoint'->'threshold' IS DISTINCT FROM '0.5'::jsonb
   OR NOT campaign_json_object(p->'early_stopping',ARRAY['enabled','monitor','mode','patience','min_delta','restore_best_weights'])
   OR jsonb_typeof(p->'early_stopping'->'enabled') IS DISTINCT FROM 'boolean'
   OR jsonb_typeof(p->'early_stopping'->'restore_best_weights') IS DISTINCT FROM 'boolean'
   OR NOT campaign_json_integer(p->'early_stopping'->'patience',0)
   OR jsonb_typeof(p->'early_stopping'->'min_delta') IS DISTINCT FROM 'number'
   OR NOT campaign_json_object(p->'calibration',ARRAY['algorithm','population','version'])
   OR p->'calibration'->>'population' IS DISTINCT FROM 'val'
   OR p->'calibration'->>'algorithm' NOT IN ('none','threshold_grid')
   OR NOT campaign_json_string(p->'calibration'->'version')
   OR NOT campaign_json_object(p->'limitations',ARRAY['shared_val','independent_calibration','test_exposure'])
   OR NOT campaign_json_string(p->'limitations'->'shared_val')
   OR p->'limitations'->'independent_calibration' IS DISTINCT FROM 'false'::jsonb
   OR p->'limitations'->>'test_exposure' NOT IN ('unknown','previously_accessed')
   OR NOT campaign_json_object(p->'aggregation',ARRAY['version','specification'])
   OR NOT campaign_json_string(p->'aggregation'->'version') OR NOT campaign_json_string(p->'aggregation'->'specification')
   OR NOT campaign_json_object(p->'uncertainty',ARRAY['version','specification'])
   OR NOT campaign_json_string(p->'uncertainty'->'version') OR NOT campaign_json_string(p->'uncertainty'->'specification')
   THEN RETURN false; END IF;
 FOREACH k IN ARRAY ARRAY['primary','secondary'] LOOP
   FOR x IN SELECT value FROM jsonb_array_elements(p->'metrics'->k) LOOP
     IF NOT campaign_json_string(x) THEN RETURN false; END IF;
   END LOOP;
 END LOOP;
 FOREACH k IN ARRAY ARRAY['criteria','tie_breaks'] LOOP
   FOR x IN SELECT value FROM jsonb_array_elements(p->'ranking'->k) LOOP
     IF NOT campaign_json_string(x) THEN RETURN false; END IF;
   END LOOP;
 END LOOP;
 FOREACH k IN ARRAY ARRAY['policy','monitor','mode'] LOOP
   IF NOT campaign_json_string(p->'checkpoint'->k) THEN RETURN false; END IF;
 END LOOP;
 IF NOT campaign_json_string(p->'early_stopping'->'monitor')
   OR NOT campaign_json_string(p->'early_stopping'->'mode') THEN RETURN false; END IF;
 env=v->'environment';
 IF NOT campaign_json_object(env,ARRAY['source_sha256','python','tensorflow','packages','determinism_environment'])
   OR NOT campaign_json_string(env->'python') OR NOT campaign_json_string(env->'tensorflow')
   OR (env->>'source_sha256') !~ '^[a-f0-9]{64}$'
   OR jsonb_typeof(env->'packages') IS DISTINCT FROM 'object' OR env->'packages'='{}'::jsonb
   OR jsonb_typeof(env->'determinism_environment') IS DISTINCT FROM 'object' THEN RETURN false; END IF;
 matrix=v->'matrix';
 IF NOT campaign_json_object(matrix,ARRAY['canonical_version','registry','registry_hash','configurations','members','expected_count','seeds'])
   OR matrix->>'canonical_version' IS DISTINCT FROM 'campaign_json_v1'
   OR NOT campaign_json_integer(matrix->'expected_count',1)
   OR (matrix->>'registry_hash') !~ '^[a-f0-9]{64}$'
   OR jsonb_typeof(matrix->'registry') IS DISTINCT FROM 'array' OR jsonb_array_length(matrix->'registry')=0
   OR jsonb_typeof(matrix->'seeds') IS DISTINCT FROM 'array' OR jsonb_array_length(matrix->'seeds')=0
   OR jsonb_typeof(matrix->'configurations') IS DISTINCT FROM 'object' OR matrix->'configurations'='{}'::jsonb
   OR jsonb_typeof(matrix->'members') IS DISTINCT FROM 'array' THEN RETURN false; END IF;
 n=(matrix->>'expected_count')::integer; seeds=matrix->'seeds';configs=matrix->'configurations';members=matrix->'members';
 IF n>(b->>'max_members')::integer OR n<>jsonb_array_length(members)
   OR n<>(SELECT count(*) FROM jsonb_each(configs))*jsonb_array_length(seeds) THEN RETURN false; END IF;
 FOR x IN SELECT value FROM jsonb_array_elements(seeds) LOOP
   IF NOT campaign_json_integer(x,0) OR seen_seeds @> jsonb_build_array(x) THEN RETURN false; END IF;
   seen_seeds=seen_seeds || jsonb_build_array(x);
 END LOOP;
 FOR descriptor IN SELECT value FROM jsonb_array_elements(matrix->'registry') LOOP
   IF NOT campaign_json_object(descriptor,ARRAY['id','aliases','enabled','trainable','version','adapter','input_contract','output_contract','strategies','optimizers','preprocessing_modes','default_preprocessing'])
      OR NOT campaign_json_string(descriptor->'id') OR NOT campaign_json_string(descriptor->'version')
      OR descriptor->'enabled' IS DISTINCT FROM 'true'::jsonb OR descriptor->'trainable' IS DISTINCT FROM 'true'::jsonb
      OR jsonb_typeof(descriptor->'aliases') IS DISTINCT FROM 'array'
      OR jsonb_typeof(descriptor->'optimizers') IS DISTINCT FROM 'array' THEN RETURN false; END IF;
   FOREACH k IN ARRAY ARRAY['adapter','input_contract','output_contract','default_preprocessing'] LOOP
     IF NOT campaign_json_string(descriptor->k) THEN RETURN false; END IF;
   END LOOP;
   FOREACH k IN ARRAY ARRAY['aliases','strategies','optimizers','preprocessing_modes'] LOOP
     IF jsonb_typeof(descriptor->k) IS DISTINCT FROM 'array' THEN RETURN false; END IF;
     FOR x IN SELECT value FROM jsonb_array_elements(descriptor->k) LOOP
       IF NOT campaign_json_string(x) THEN RETURN false; END IF;
     END LOOP;
   END LOOP;
 END LOOP;
 FOR item IN SELECT * FROM jsonb_each(configs) LOOP
   IF item.key !~ '^[a-f0-9]{64}$' OR NOT campaign_json_object(item.value,ARRAY['configuration','requests'])
      OR campaign_configuration_valid(item.value->'configuration') IS NOT TRUE
      OR jsonb_typeof(item.value->'requests') IS DISTINCT FROM 'array' OR jsonb_array_length(item.value->'requests')=0 THEN RETURN false; END IF;
 END LOOP;
 FOR x IN SELECT value FROM jsonb_array_elements(members) LOOP
   IF NOT campaign_json_object(x,ARRAY['configuration_hash','seed','position']) OR NOT (x ? 'exclusion_reason')
     OR NOT campaign_json_string(x->'configuration_hash') OR NOT (configs ? (x->>'configuration_hash'))
     OR NOT campaign_json_integer(x->'seed',0) OR NOT (seeds @> jsonb_build_array(x->'seed'))
     OR NOT campaign_json_integer(x->'position',0) OR (x->>'position')::int<>idx
     OR (x->'exclusion_reason'<>'null'::jsonb AND NOT campaign_json_string(x->'exclusion_reason')) THEN RETURN false; END IF;
   idx=idx+1;
 END LOOP;
 RETURN true;
END $$;
ALTER TABLE experimental_campaigns ADD CONSTRAINT ck_campaign_frozen_required_v2 CHECK (
 state='draft' OR (
 contract IS NOT NULL AND canonical_contract IS NOT NULL AND contract_hash IS NOT NULL
 AND contract_hash ~ '^[a-f0-9]{64}$'
 AND (contract_hash IS NOT DISTINCT FROM encode(sha256(convert_to(canonical_contract,'UTF8')),'hex'))
 AND (canonical_contract::jsonb IS NOT DISTINCT FROM contract)
 AND campaign_contract_valid(contract)
 ) IS TRUE
) NOT VALID;
ALTER TABLE experimental_campaigns VALIDATE CONSTRAINT ck_campaign_frozen_required_v2;
ALTER TABLE campaign_configurations ADD CONSTRAINT ck_campaign_configuration_required_v2 CHECK (
 (campaign_configuration_valid(configuration) AND jsonb_typeof(requests)='array' AND jsonb_array_length(requests)>0) IS TRUE
) NOT VALID;
ALTER TABLE campaign_configurations VALIDATE CONSTRAINT ck_campaign_configuration_required_v2;

CREATE FUNCTION campaign_environment_identity(v jsonb) RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$
 SELECT jsonb_build_object('source_sha256',v->'source_sha256','python',v->'python','tensorflow',v->'tensorflow',
                          'packages',v->'packages','determinism_environment',v->'determinism_environment')
$$;
CREATE FUNCTION campaign_model_matches(run_id uuid,member uuid) RETURNS boolean LANGUAGE plpgsql AS $$
DECLARE model_name text; cfg jsonb; registry jsonb; d jsonb; matches integer;
BEGIN
 SELECT mo.name,cf.configuration,c.registry_snapshot INTO model_name,cfg,registry
 FROM runs r JOIN models mo ON mo.id=r.model_id
 JOIN campaign_members m ON m.id=member
 JOIN campaign_configurations cf ON cf.campaign_id=m.campaign_id AND cf.configuration_hash=m.configuration_hash
 JOIN experimental_campaigns c ON c.id=m.campaign_id WHERE r.id=run_id;
 IF NOT FOUND THEN RETURN false; END IF;
 SELECT count(*) INTO matches FROM jsonb_array_elements(registry) item
 WHERE item->>'id'=cfg->>'model_id' AND item->>'version'=cfg->>'adapter_version'
   AND (item->>'id'=model_name OR item->'aliases' @> to_jsonb(ARRAY[model_name]));
 RETURN matches=1;
END $$;
CREATE OR REPLACE FUNCTION campaign_run_identity_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM campaign_attempts WHERE training_run_id=OLD.id) AND
   (NEW.model_id IS DISTINCT FROM OLD.model_id
    OR NEW.run_type IS DISTINCT FROM OLD.run_type OR NEW.dataset_version_id IS DISTINCT FROM OLD.dataset_version_id
    OR NEW.random_seed IS DISTINCT FROM OLD.random_seed OR NEW.experiment_id IS DISTINCT FROM OLD.experiment_id
    OR NEW.execution_parameters->'model_configuration_e2'->'configuration' IS DISTINCT FROM OLD.execution_parameters->'model_configuration_e2'->'configuration'
    OR NEW.execution_parameters->'model_configuration_e2'->'dataset' IS DISTINCT FROM OLD.execution_parameters->'model_configuration_e2'->'dataset'
    OR campaign_environment_identity(NEW.execution_parameters->'model_configuration_e2'->'environment') IS DISTINCT FROM
       campaign_environment_identity(OLD.execution_parameters->'model_configuration_e2'->'environment'))
 THEN RAISE EXCEPTION 'LINKED_TRAIN_IDENTITY_IMMUTABLE'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION campaign_catalog_identity_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.name IS DISTINCT FROM OLD.name AND EXISTS(
   SELECT 1 FROM runs r JOIN campaign_attempts a ON a.training_run_id=r.id WHERE r.model_id=OLD.id)
 THEN RAISE EXCEPTION 'LINKED_MODEL_NAME_IMMUTABLE'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER campaign_catalog_identity_guard BEFORE UPDATE ON models FOR EACH ROW EXECUTE FUNCTION campaign_catalog_identity_guard();
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM campaign_attempts WHERE training_run_id IS NOT NULL AND NOT campaign_model_matches(training_run_id,member_id))
 THEN RAISE EXCEPTION 'EXISTING_CAMPAIGN_MODEL_LINK_INVALID'; END IF;
END $$;
"""

ATTEMPT_GUARD = r"""
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
   IF OLD.state<>'active' OR NEW.state NOT IN ('active','failed','interrupted','completed') THEN RAISE EXCEPTION 'INVALID_ATTEMPT_TRANSITION'; END IF;
 END IF;
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
"""


def upgrade():
    op.execute(DDL)
    op.execute(ATTEMPT_GUARD)
    context = op.get_context()
    schema = (
        "public"
        if context.as_sql
        else op.get_bind().execute(sa.text("SELECT current_schema()")).scalar_one()
    )
    quoted = context.dialect.identifier_preparer.quote(schema)
    signatures = (
        "campaign_json_object(jsonb,text[])",
        "campaign_json_string(jsonb)",
        "campaign_json_integer(jsonb,numeric)",
        "campaign_configuration_valid(jsonb)",
        "campaign_contract_valid(jsonb)",
        "campaign_environment_identity(jsonb)",
        "campaign_model_matches(uuid,uuid)",
        "campaign_run_identity_guard()",
        "campaign_catalog_identity_guard()",
        "campaign_attempt_guard()",
    )
    for signature in signatures:
        op.execute(f"ALTER FUNCTION {signature} SET search_path = {quoted}, pg_catalog")


def downgrade():
    raise RuntimeError("Operational downgrade forbidden; use a forward migration")
