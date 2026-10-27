-- Reviewable SQL shapes used by the EXISTING model/run/artifact/version repositories.
-- This file prepares and deallocates statements; it NEVER executes INSERT.
-- Operational writer: pretrained.registration.register_external_model(manifest).
-- Approval is required before invoking that writer against the real database.
-- Verify source hashes, copy exclusively to outputs/train_runs/<run_id>, verify
-- destination bytes and use their final paths. Resolve dependencies by role/id.
-- One transaction and pg_advisory_xact_lock(hashtextextended('model-registration:' || name,0)).
-- Check existing model/version/roles first; identical registration returns existing ids.
BEGIN READ ONLY;
PREPARE capstone_zs_model(text,text,text,text,jsonb) AS
 INSERT INTO public.models(name,model_type,framework,architecture,pretrained,pretrained_source,metadata)
 VALUES($1,'zero_shot',$2,$3,true,$4,$5) RETURNING id;
-- metadata: training_mode=logical; scientific_origin includes repository and pinned revision.
PREPARE capstone_zs_run(uuid,text,jsonb) AS
 INSERT INTO public.runs(model_id,run_name,run_type,status,total_epochs,completed_epochs,
   duration_seconds,dataset_version_id,started_at,finished_at,metadata,execution_parameters,execution_type)
 VALUES($1,$2,'training','completed',0,0,0,NULL,now(),now(),
   '{"training_performed":false}'::jsonb,$3,'local_python') RETURNING id;
-- $3 contains observed runtime and scientific_origin, never fabricated metrics/epochs.
PREPARE capstone_zs_artifact(uuid,text,text,text,bigint,text,jsonb) AS
 INSERT INTO public.artifacts(run_id,artifact_type,name,path,file_size_bytes,checksum,artifact_status,metadata)
 VALUES($1,$2,$3,$4,$5,$6,'available',$7) RETURNING id;
-- $2 = model_checkpoint or model_dependency; $7 contains the unique role and provenance.
PREPARE capstone_zs_version(uuid,text,integer,uuid,uuid,text,text,bigint,text,jsonb,jsonb,jsonb,jsonb,jsonb) AS
 INSERT INTO public.model_versions(model_id,model_name,version_number,training_run_id,
   checkpoint_artifact_id,checkpoint_path,artifact_sha256,artifact_size_bytes,framework,
   preprocessing_profile_snapshot,class_mapping,input_signature,output_signature,metadata,status,lineage_status)
 VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,'candidate','resolved') RETURNING id;
-- Ownership FK requires (checkpoint_artifact_id,training_run_id) to match artifacts.
-- Publication is a separate operation. Do not set productive_stage2 here.
DEALLOCATE capstone_zs_model;
DEALLOCATE capstone_zs_run;
DEALLOCATE capstone_zs_artifact;
DEALLOCATE capstone_zs_version;
ROLLBACK;
