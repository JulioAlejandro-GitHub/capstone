-- lineage
SELECT m.id model_id,m.name,m.framework,m.metadata model_metadata,
 r.id training_run_id,r.run_type,r.status,r.total_epochs,r.completed_epochs,r.metadata run_metadata,
 r.execution_parameters->'runtime_environment' runtime_environment,
 a.id artifact_id,a.run_id artifact_owner,a.path,a.checksum,a.file_size_bytes,a.artifact_status,
 mv.id model_version_id,mv.checkpoint_artifact_id,mv.framework version_framework,mv.output_signature,
 (SELECT count(*) FROM run_configurations rc WHERE rc.run_id=r.id) configurations,
 (SELECT count(*) FROM training_history th WHERE th.run_id=r.id) training_history_rows,
 (SELECT count(*) FROM run_metrics rm WHERE rm.run_id=r.id) metrics_rows
 FROM models m JOIN runs r ON r.model_id=m.id AND r.run_type='training'
 JOIN model_versions mv ON mv.training_run_id=r.id
 JOIN artifacts a ON a.id=mv.checkpoint_artifact_id AND a.run_id=r.id
 WHERE m.name='biomedclip_zero_shot';

-- invariants
SELECT to_regclass('public.run_configurations')::text run_configurations,
 NOT EXISTS(SELECT 1 FROM pg_trigger WHERE tgrelid='public.runs'::regclass AND tgname='v2_run_configuration_required') trigger_absent,
 NOT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='runs' AND column_name IN ('tensorflow_version','keras_version')) retired_columns_absent;

-- selection
SELECT p.id publication_id,p.evaluation_run_id,p.evaluation_attempt_id,p.is_active,
 d.id deployment_id,d.status,d.threshold_value,d.threshold_profile_snapshot,d.metadata
 FROM stage2_model_publications p JOIN deployed_model_versions d ON d.model_version_id=p.model_version_id
 WHERE p.model_version_id='3fd16a84-b5c7-442b-916b-e0438bb0f3e5';

-- cell_predictions
SELECT p.id,p.classification_run_id,p.classification_input_id,p.cell_detection_id,p.crop_id,
 p.prediction_status,p.raw_output,p.probability_parasitized,p.probability_uninfected,p.predicted_label,
 p.threshold_used,p.threshold_source,r.model_snapshot->'output_signature' score_semantics
 FROM cell_predictions p JOIN cell_classification_runs r ON r.id=p.classification_run_id
 WHERE p.classification_run_id='bae280c9-0b10-4cf5-80ff-694a80c947fa';