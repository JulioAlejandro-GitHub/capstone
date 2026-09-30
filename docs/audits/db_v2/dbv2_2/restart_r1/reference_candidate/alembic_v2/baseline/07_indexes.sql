-- E10.10.5A frozen Alembic resource. Execute only through the guarded v2 environment.
CREATE INDEX idx_artifacts_artifact_type ON public.artifacts (artifact_type);

CREATE INDEX idx_artifacts_checksum ON public.artifacts (checksum);

CREATE INDEX idx_artifacts_governance_status ON public.artifacts (artifact_status);

CREATE INDEX idx_artifacts_metadata_source ON public.artifacts ((metadata ->> CAST('source' AS text)));

CREATE INDEX idx_artifacts_run_id ON public.artifacts (run_id);

CREATE INDEX idx_artifacts_type_path ON public.artifacts (artifact_type, path);

CREATE INDEX idx_artifacts_uri ON public.artifacts (artifact_uri) WHERE artifact_uri IS NOT NULL;

CREATE UNIQUE INDEX uq_assessment_live ON public.assessment_attempts (identity_id) WHERE state = ANY(ARRAY[CAST('active' AS text), CAST('verified' AS text)]);

CREATE UNIQUE INDEX uq_global_assessment_active ON public.assessment_attempts ((TRUE)) WHERE state = CAST('active' AS text);

CREATE INDEX ix_audit_events_actor ON public.audit_events (actor_user_id, created_at);

CREATE INDEX ix_audit_events_created_at ON public.audit_events (created_at);

CREATE INDEX ix_audit_events_resource ON public.audit_events (resource_type, resource_id, created_at);

CREATE INDEX ix_blood_samples_case ON public.blood_samples (case_id);

CREATE INDEX ix_blood_samples_status_created ON public.blood_samples (status, created_at DESC);

CREATE UNIQUE INDEX uq_blood_samples_external_identity ON public.blood_samples (case_id, source_system, external_sample_id) WHERE external_sample_id IS NOT NULL;

CREATE INDEX ix_campaign_attempt_state ON public.campaign_attempts (state);

CREATE UNIQUE INDEX uq_campaign_one_active_attempt ON public.campaign_attempts (member_id) WHERE state = CAST('active' AS text);

CREATE INDEX ix_campaign_member_state ON public.campaign_members (campaign_id, state);

CREATE INDEX ix_cell_classification_events_run_created ON public.cell_classification_events (classification_run_id, created_at, id);

CREATE INDEX ix_cell_classification_events_run_detection ON public.cell_classification_events (classification_run_id, cell_detection_id, created_at, id);

CREATE INDEX ix_cell_classification_events_run_prediction ON public.cell_classification_events (classification_run_id, cell_prediction_id, created_at, id);

CREATE INDEX ix_cell_classification_inputs_crop ON public.cell_classification_inputs (crop_id) WHERE crop_id IS NOT NULL;

CREATE INDEX ix_cell_classification_inputs_detection ON public.cell_classification_inputs (cell_detection_id);

CREATE INDEX ix_cell_classification_inputs_run_eligible_order ON public.cell_classification_inputs (classification_run_id, eligible, input_order);

CREATE INDEX ix_cell_classification_inputs_run_image_cell ON public.cell_classification_inputs (classification_run_id, image_sequence_number, cell_index, id);

CREATE INDEX ix_cell_classification_reviews_actor_created ON public.cell_classification_reviews (actor_user_id, created_at DESC, id DESC);

CREATE INDEX ix_cell_classification_reviews_prediction_created ON public.cell_classification_reviews (cell_prediction_id, created_at, id);

CREATE INDEX ix_cell_classification_runs_analysis_created ON public.cell_classification_runs (analysis_run_id, created_at DESC, id DESC);

CREATE INDEX ix_cell_classification_runs_detection_created ON public.cell_classification_runs (detection_run_id, created_at DESC, id DESC);

CREATE INDEX ix_cell_classification_runs_model_created ON public.cell_classification_runs (production_model_id, created_at DESC, id DESC);

CREATE INDEX ix_cell_classification_runs_status_created ON public.cell_classification_runs (status, created_at DESC, id DESC);

CREATE UNIQUE INDEX uq_cell_classification_runs_equivalent_active ON public.cell_classification_runs (detection_run_id, production_model_id, (COALESCE(model_version, CAST('' AS varchar))), (COALESCE(model_snapshot ->> CAST('checkpoint_sha256' AS text), CAST('' AS text))), (COALESCE(model_snapshot ->> CAST('inference_version' AS text), CAST('' AS text))), input_manifest_sha256) WHERE CAST(status AS text) = ANY(ARRAY[CAST(CAST('created' AS varchar) AS text), CAST(CAST('processing' AS varchar) AS text), CAST(CAST('completed' AS varchar) AS text), CAST(CAST('completed_with_warnings' AS varchar) AS text)]);

CREATE INDEX ix_cell_detection_events_run_created ON public.cell_detection_events (detection_run_id, created_at, id);

CREATE INDEX ix_cell_detection_events_run_image ON public.cell_detection_events (detection_run_id, microscopy_image_id, created_at, id);

CREATE INDEX ix_cell_detection_runs_analysis_created ON public.cell_detection_runs (analysis_run_id, created_at DESC, id DESC);

CREATE INDEX ix_cell_detection_runs_status_created ON public.cell_detection_runs (status, created_at DESC, id DESC);

CREATE UNIQUE INDEX uq_cell_detection_runs_equivalent_active ON public.cell_detection_runs (analysis_run_id, detector_key, detector_version, algorithm_version, input_manifest_sha256) WHERE CAST(status AS text) = ANY(ARRAY[CAST(CAST('created' AS varchar) AS text), CAST(CAST('processing' AS varchar) AS text), CAST(CAST('completed' AS varchar) AS text), CAST(CAST('completed_with_warnings' AS varchar) AS text)]);

CREATE INDEX ix_cell_detections_run_image ON public.cell_detections (detection_run_id, microscopy_image_id, cell_index);

CREATE INDEX ix_cell_explanations_status_created ON public.cell_explanations (status, created_at DESC, id DESC);

CREATE INDEX ix_cell_predictions_crop ON public.cell_predictions (crop_id);

CREATE INDEX ix_cell_predictions_detection ON public.cell_predictions (cell_detection_id);

CREATE INDEX ix_cell_predictions_run_label ON public.cell_predictions (classification_run_id, predicted_label, created_at, id) WHERE CAST(prediction_status AS text) = CAST('completed' AS text);

CREATE INDEX ix_cell_predictions_run_near_threshold ON public.cell_predictions (classification_run_id, near_threshold, created_at, id);

CREATE INDEX ix_cell_predictions_run_status ON public.cell_predictions (classification_run_id, prediction_status, created_at, id);

CREATE INDEX ix_dataset_materialization_activations_dataset_version_id ON public.dataset_materialization_activations (dataset_version_id);

CREATE INDEX ix_dataset_materialization_activations_materialization_id ON public.dataset_materialization_activations (materialization_id);

CREATE UNIQUE INDEX uq_dataset_materialization_activations_current_family ON public.dataset_materialization_activations (dataset_family) WHERE deactivated_at IS NULL;

CREATE INDEX ix_dataset_materializations_dataset_version_id ON public.dataset_materializations (dataset_version_id);

CREATE INDEX ix_dataset_source_records_clinical_identity_id ON public.dataset_source_records (clinical_identity_id);

CREATE INDEX ix_dataset_source_records_dataset_id ON public.dataset_source_records (dataset_id);

CREATE INDEX ix_dataset_source_records_decoded_pixel_sha256 ON public.dataset_source_records (decoded_pixel_sha256) WHERE decoded_pixel_sha256 IS NOT NULL;

CREATE INDEX ix_dataset_source_records_source_file_sha256 ON public.dataset_source_records (source_file_sha256) WHERE source_file_sha256 IS NOT NULL;

CREATE INDEX ix_dataset_split_assignments_clinical_identity_id ON public.dataset_split_assignments (clinical_identity_id);

CREATE INDEX ix_dataset_split_assignments_dataset_version_id ON public.dataset_split_assignments (dataset_version_id);

CREATE INDEX idx_dataset_split_images_class ON public.dataset_split_images (class_name);

CREATE INDEX idx_dataset_split_images_dataset_dir ON public.dataset_split_images (dataset_dir);

CREATE INDEX idx_dataset_split_images_dataset_id ON public.dataset_split_images (dataset_id);

CREATE INDEX idx_dataset_split_images_relative_path ON public.dataset_split_images (relative_path);

CREATE INDEX idx_dataset_split_images_split ON public.dataset_split_images (split_name);

CREATE INDEX ix_dataset_split_images_dataset_materialization_id ON public.dataset_split_images (dataset_materialization_id);

CREATE INDEX ix_dataset_split_images_dataset_version_id ON public.dataset_split_images (dataset_version_id);

CREATE INDEX ix_dataset_split_statistics_version_metric ON public.dataset_split_statistics (dataset_version_id, scope, metric_name);

CREATE INDEX ix_dataset_split_validation_checks_version_name ON public.dataset_split_validation_checks (dataset_version_id, check_name, executed_at);

CREATE INDEX ix_dataset_version_sources_dataset_id ON public.dataset_version_sources (dataset_id);

CREATE INDEX ix_dataset_versions_status ON public.dataset_versions (status);

CREATE INDEX idx_datasets_metadata_gin ON public.datasets USING gin (metadata);

CREATE INDEX idx_deployed_model_versions_checkpoint_artifact ON public.deployed_model_versions (checkpoint_artifact_id);

CREATE INDEX idx_deployed_model_versions_model_version ON public.deployed_model_versions (model_version_id);

CREATE INDEX idx_deployed_model_versions_slot_history ON public.deployed_model_versions (deployment_name, environment, alias, created_at DESC);

CREATE INDEX idx_deployed_model_versions_status ON public.deployed_model_versions (status, created_at DESC);

CREATE INDEX idx_deployed_model_versions_threshold_calibration ON public.deployed_model_versions (threshold_calibration_id) WHERE threshold_calibration_id IS NOT NULL;

CREATE UNIQUE INDEX uq_deployed_model_versions_active_slot ON public.deployed_model_versions (deployment_name, environment, alias) WHERE status = CAST('active' AS text);

CREATE UNIQUE INDEX uq_deployed_model_versions_one_production_champion ON public.deployed_model_versions (environment, alias) WHERE status = CAST('active' AS text) AND environment = CAST('production' AS text) AND alias = CAST('champion' AS text);

CREATE INDEX idx_environment_packages_run_id ON public.environment_packages (run_id);

CREATE INDEX idx_errors_run_id ON public.errors (run_id);

CREATE INDEX idx_execution_logs_run_id ON public.execution_logs (run_id);

CREATE INDEX ix_campaign_dataset_state ON public.experimental_campaigns (dataset_version_id, state);

CREATE INDEX idx_explainability_case_method ON public.explainability_results (case_type, method);

CREATE INDEX idx_explainability_method ON public.explainability_results (method);

CREATE INDEX idx_explainability_output_path ON public.explainability_results (output_path);

CREATE INDEX idx_explainability_run_id ON public.explainability_results (run_id);

CREATE INDEX idx_explainability_success ON public.explainability_results (success);

CREATE INDEX ix_identity_evidence_clinical_identity_id ON public.identity_evidence (clinical_identity_id);

CREATE INDEX ix_identity_evidence_source_record_id ON public.identity_evidence (source_record_id);

CREATE INDEX idx_image_analysis_jobs_deployment ON public.image_analysis_jobs (deployed_model_version_id);

CREATE INDEX idx_image_analysis_jobs_input_artifact ON public.image_analysis_jobs (input_artifact_id) WHERE input_artifact_id IS NOT NULL;

CREATE INDEX idx_image_analysis_jobs_model_version ON public.image_analysis_jobs (model_version_id);

CREATE INDEX idx_image_analysis_jobs_run ON public.image_analysis_jobs (inference_run_id);

CREATE INDEX idx_image_analysis_jobs_source_image ON public.image_analysis_jobs (source_image_id) WHERE source_image_id IS NOT NULL;

CREATE INDEX idx_image_analysis_jobs_status_created ON public.image_analysis_jobs (status, created_at DESC);

CREATE UNIQUE INDEX uq_image_analysis_jobs_idempotency ON public.image_analysis_jobs (inference_run_id, idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE INDEX ix_image_connected_components_run_image ON public.image_connected_components (detection_run_id, microscopy_image_id, component_index);

CREATE INDEX ix_image_connected_components_status ON public.image_connected_components (detection_run_id, component_status, component_index);

CREATE INDEX ix_ingestion_batches_sample ON public.image_ingestion_batches (sample_id, created_at DESC);

CREATE UNIQUE INDEX uq_ingestion_batches_source_group ON public.image_ingestion_batches (source_system, source_group_key) WHERE source_system IS NOT NULL AND source_group_key IS NOT NULL;

CREATE UNIQUE INDEX local_one_active ON public.local_execution_jobs ((TRUE)) WHERE state = ANY(ARRAY[CAST('held' AS text), CAST('calculation_reported' AS text)]);

CREATE INDEX ix_microscopy_analysis_events_run ON public.microscopy_analysis_events (analysis_run_id, created_at, id);

CREATE INDEX ix_microscopy_analysis_runs_status ON public.microscopy_analysis_runs (run_status, created_at DESC);

CREATE INDEX ix_microscopy_analysis_runs_subject ON public.microscopy_analysis_runs (subject_id, created_at DESC);

CREATE INDEX ix_microscopy_images_ingestion_batch ON public.microscopy_images (ingestion_batch_id);

CREATE INDEX ix_microscopy_images_sha256 ON public.microscopy_images (sha256);

CREATE INDEX ix_microscopy_images_slide ON public.microscopy_images (slide_id);

CREATE INDEX ix_microscopy_images_status_created ON public.microscopy_images (status, created_at DESC);

CREATE UNIQUE INDEX uq_microscopy_images_external_path ON public.microscopy_images (source_system, source_relative_path) WHERE source_system IS NOT NULL AND source_relative_path IS NOT NULL;

CREATE INDEX idx_model_governance_audit_batch ON public.model_governance_backfill_audit (batch_id, event_at);

CREATE INDEX idx_model_governance_audit_record ON public.model_governance_backfill_audit (table_name, record_id, event_at);

CREATE INDEX idx_model_governance_audit_reversal ON public.model_governance_backfill_audit (reversal_of_audit_id) WHERE reversal_of_audit_id IS NOT NULL;

CREATE INDEX idx_model_versions_checkpoint_artifact ON public.model_versions (checkpoint_artifact_id);

CREATE INDEX idx_model_versions_model ON public.model_versions (model_id);

CREATE INDEX idx_model_versions_sha256 ON public.model_versions (artifact_sha256);

CREATE INDEX idx_model_versions_status_lineage ON public.model_versions (status, lineage_status);

CREATE INDEX idx_model_versions_training_run ON public.model_versions (training_run_id);

CREATE UNIQUE INDEX uq_model_versions_checkpoint_artifact ON public.model_versions (checkpoint_artifact_id) WHERE checkpoint_artifact_id IS NOT NULL;

CREATE UNIQUE INDEX uq_model_versions_name_number ON public.model_versions (model_name, version_number) WHERE model_name IS NOT NULL AND version_number IS NOT NULL;

CREATE UNIQUE INDEX uq_model_versions_training_version_name ON public.model_versions (training_run_id, version_name) WHERE training_run_id IS NOT NULL AND version_name IS NOT NULL;

CREATE UNIQUE INDEX uq_model_versions_unjustified_sha256 ON public.model_versions (artifact_sha256) WHERE artifact_sha256 IS NOT NULL AND NULLIF(btrim(artifact_hash_reuse_justification), CAST('' AS text)) IS NULL;

CREATE INDEX idx_predictions_analysis_job ON public.predictions (image_analysis_job_id);

CREATE INDEX idx_predictions_case_type ON public.predictions (case_type);

CREATE INDEX idx_predictions_case_type_run ON public.predictions (case_type, run_id);

CREATE INDEX idx_predictions_classifier_model_version ON public.predictions (classifier_model_version_id);

CREATE INDEX idx_predictions_created_at ON public.predictions (created_at);

CREATE INDEX idx_predictions_deployed_model_version ON public.predictions (deployed_model_version_id);

CREATE INDEX idx_predictions_detector_model_version ON public.predictions (detector_model_version_id) WHERE detector_model_version_id IS NOT NULL;

CREATE INDEX idx_predictions_inference_run ON public.predictions (inference_run_id);

CREATE INDEX idx_predictions_metadata_source ON public.predictions ((metadata ->> CAST('source' AS text)));

CREATE INDEX idx_predictions_metadata_workflow ON public.predictions ((metadata ->> CAST('workflow' AS text)));

CREATE INDEX idx_predictions_model_version ON public.predictions (model_version_id);

CREATE INDEX idx_predictions_predicted_label ON public.predictions (predicted_label);

CREATE INDEX idx_predictions_review_status ON public.predictions (review_status, created_at DESC);

CREATE INDEX idx_predictions_run_id ON public.predictions (run_id);

CREATE INDEX idx_predictions_true_pred ON public.predictions (true_label, predicted_label);

CREATE UNIQUE INDEX uq_predictions_job_cell_index ON public.predictions (image_analysis_job_id, cell_index) WHERE prediction_scope = CAST('cell' AS text);

CREATE INDEX ix_quality_queue_order ON public.quality_assessment_queue_items (status, priority DESC, requested_at);

CREATE INDEX ix_quality_queue_priority_requested ON public.quality_assessment_queue_items (priority DESC, requested_at);

CREATE UNIQUE INDEX uq_quality_queue_active_run ON public.quality_assessment_queue_items (analysis_run_id) WHERE CAST(status AS text) = ANY(ARRAY[CAST(CAST('queued' AS varchar) AS text), CAST(CAST('running' AS varchar) AS text)]);

CREATE INDEX ix_quality_gate_decisions_run ON public.quality_gate_decisions (analysis_run_id, created_at, id);

CREATE INDEX ix_research_subjects_status_created ON public.research_subjects (status, created_at DESC);

CREATE UNIQUE INDEX uq_research_subjects_external_identity ON public.research_subjects (source_system, external_patient_id) WHERE external_patient_id IS NOT NULL;

CREATE INDEX idx_run_checkpoint_policy_artifact ON public.run_checkpoint_policy (checkpoint_artifact_id);

CREATE INDEX idx_run_checkpoint_policy_model_version ON public.run_checkpoint_policy (model_version_id);

CREATE INDEX idx_run_checkpoint_policy_run_id ON public.run_checkpoint_policy (run_id);

CREATE INDEX idx_run_clinical_metrics_model_name ON public.run_clinical_metrics (model_name);

CREATE INDEX idx_run_clinical_metrics_run_id ON public.run_clinical_metrics (run_id);

CREATE INDEX idx_run_clinical_metrics_split_name ON public.run_clinical_metrics (split_name);

CREATE INDEX idx_run_dataset_images_image_id ON public.run_dataset_images (image_id);

CREATE INDEX idx_run_dataset_images_run_id ON public.run_dataset_images (run_id);

CREATE INDEX idx_run_dataset_images_split ON public.run_dataset_images (split_name);

CREATE INDEX idx_run_dataset_images_usage_context ON public.run_dataset_images (usage_context);

CREATE INDEX idx_run_image_predictions_case_type ON public.run_image_predictions (case_type);

CREATE INDEX idx_run_image_predictions_run_id ON public.run_image_predictions (run_id);

CREATE INDEX idx_run_image_predictions_split ON public.run_image_predictions (split_name);

CREATE INDEX idx_run_io_records_clinical_metadata_gin ON public.run_io_records USING gin (clinical_metadata);

CREATE INDEX idx_run_io_records_created_at ON public.run_io_records (created_at);

CREATE INDEX idx_run_io_records_model_metadata_gin ON public.run_io_records USING gin (model_metadata);

CREATE INDEX idx_run_io_records_model_name ON public.run_io_records (model_name);

CREATE INDEX idx_run_io_records_run_id ON public.run_io_records (run_id);

CREATE INDEX idx_run_io_records_run_type ON public.run_io_records (run_type);

CREATE INDEX idx_run_io_records_script_name ON public.run_io_records (script_name);

CREATE INDEX ix_run_io_records_dataset_materialization_id ON public.run_io_records (dataset_materialization_id);

CREATE INDEX ix_run_io_records_dataset_version_id ON public.run_io_records (dataset_version_id);

CREATE INDEX idx_run_lineage_checkpoint_artifact ON public.run_lineage (checkpoint_artifact_id);

CREATE INDEX idx_run_lineage_checkpoint_path ON public.run_lineage (checkpoint_path);

CREATE INDEX idx_run_lineage_child_run_id ON public.run_lineage (child_run_id);

CREATE INDEX idx_run_lineage_model_version ON public.run_lineage (model_version_id);

CREATE INDEX idx_run_lineage_parent_run_id ON public.run_lineage (parent_run_id);

CREATE INDEX idx_run_lineage_relationship_type ON public.run_lineage (relationship_type);

CREATE UNIQUE INDEX uq_run_lineage_single_evaluation_training_parent ON public.run_lineage (child_run_id) WHERE relationship_type = CAST('evaluates_checkpoint_from' AS text);

CREATE INDEX idx_run_metrics_name ON public.run_metrics (metric_name);

CREATE INDEX idx_run_metrics_run_id ON public.run_metrics (run_id);

CREATE INDEX idx_run_model_deployments_deployment ON public.run_model_deployments (deployed_model_version_id);

CREATE INDEX idx_run_model_deployments_model_version ON public.run_model_deployments (model_version_id);

CREATE UNIQUE INDEX uq_run_model_deployments_primary ON public.run_model_deployments (run_id) WHERE role = CAST('primary' AS text);

CREATE INDEX idx_run_threshold_calibration_artifact ON public.run_threshold_calibration (calibration_artifact_id);

CREATE INDEX idx_run_threshold_calibration_model_version ON public.run_threshold_calibration (model_version_id);

CREATE INDEX idx_run_threshold_calibration_run_id ON public.run_threshold_calibration (run_id);

CREATE INDEX idx_runs_dataset_id ON public.runs (dataset_id);

CREATE INDEX idx_runs_execution_parameters_gin ON public.runs USING gin (execution_parameters);

CREATE INDEX idx_runs_execution_type ON public.runs (execution_type);

CREATE INDEX idx_runs_inference_script ON public.runs (run_type, script_name);

CREATE INDEX idx_runs_metadata_gin ON public.runs USING gin (metadata);

CREATE INDEX idx_runs_model_id ON public.runs (model_id);

CREATE INDEX idx_runs_parameters_gin ON public.runs USING gin (parameters);

CREATE INDEX idx_runs_run_type ON public.runs (run_type);

CREATE INDEX idx_runs_started_at ON public.runs (started_at);

CREATE INDEX idx_runs_status ON public.runs (status);

CREATE INDEX idx_runs_training_release_status ON public.runs (release_status) WHERE run_type = CAST('training' AS text);

CREATE INDEX ix_runs_dataset_version_id ON public.runs (dataset_version_id);

CREATE UNIQUE INDEX uq_runs_single_productive_stage2 ON public.runs (release_status) WHERE run_type = CAST('training' AS text) AND release_status = CAST('productive_stage2' AS text);

CREATE INDEX ix_scientific_cases_status_created ON public.scientific_cases (status, created_at DESC);

CREATE INDEX ix_scientific_cases_subject ON public.scientific_cases (subject_id);

CREATE INDEX ix_scientific_reviews_actor_created ON public.scientific_reviews (actor_user_id, created_at DESC, id DESC);

CREATE INDEX ix_scientific_reviews_entity_created ON public.scientific_reviews (entity_type, entity_id, created_at, id);

CREATE INDEX ix_validation_annotation_events_actor_created ON public.scientific_validation_annotation_events (actor_user_id, created_at DESC, id DESC);

CREATE INDEX ix_validation_annotation_events_annotation_created ON public.scientific_validation_annotation_events (annotation_id, created_at, id);

CREATE INDEX ix_validation_annotations_general_target ON public.scientific_validation_annotations (target_type, cell_detection_id, sample_id, created_at, id) WHERE validation_session_id IS NULL;

CREATE INDEX ix_validation_annotations_session_analysis ON public.scientific_validation_annotations (validation_session_id, analysis_run_id, created_at, id) WHERE CAST(target_type AS text) = CAST('analysis' AS text);

CREATE INDEX ix_validation_annotations_session_category ON public.scientific_validation_annotations (validation_session_id, category, created_at, id);

CREATE INDEX ix_validation_annotations_session_cell ON public.scientific_validation_annotations (validation_session_id, cell_detection_id, created_at, id) WHERE CAST(target_type AS text) = CAST('cell' AS text);

CREATE INDEX ix_validation_annotations_session_created ON public.scientific_validation_annotations (validation_session_id, created_at, id);

CREATE INDEX ix_validation_annotations_session_sample ON public.scientific_validation_annotations (validation_session_id, sample_id, created_at, id) WHERE CAST(target_type AS text) = CAST('sample' AS text);

CREATE INDEX ix_validation_sessions_creator_created ON public.scientific_validation_sessions (created_by, created_at DESC, id DESC);

CREATE INDEX ix_validation_sessions_status_created ON public.scientific_validation_sessions (status, created_at DESC, id DESC);

CREATE INDEX ix_smear_analysis_summaries_analysis_created ON public.smear_analysis_summaries (analysis_run_id, created_at DESC, id DESC);

CREATE INDEX ix_smear_analysis_summaries_detection_created ON public.smear_analysis_summaries (detection_run_id, created_at DESC, id DESC);

CREATE INDEX ix_smear_analysis_summaries_outcome_created ON public.smear_analysis_summaries (outcome, created_at DESC, id DESC);

CREATE INDEX ix_smear_slides_sample ON public.smear_slides (sample_id);

CREATE INDEX ix_smear_slides_status_created ON public.smear_slides (status, created_at DESC);

CREATE INDEX idx_stage2_publication_events_publication ON public.stage2_model_publication_events (publication_id, event_at);

CREATE INDEX idx_stage2_publication_candidates ON public.stage2_model_publications (datasource, scope, is_active, published_at DESC);

CREATE UNIQUE INDEX uq_stage2_publication_active_version ON public.stage2_model_publications (model_version_id, scope) WHERE is_active;

CREATE UNIQUE INDEX train_event_id_unique ON public.train_execution_records (event_id) WHERE event_id IS NOT NULL;

CREATE UNIQUE INDEX train_event_sequence_unique ON public.train_execution_records (run_id, event_sequence) WHERE event_sequence IS NOT NULL;

CREATE UNIQUE INDEX uq_global_train_active ON public.train_execution_sessions ((TRUE)) WHERE state = ANY(ARRAY[CAST('active' AS text), CAST('completed' AS text)]);

CREATE INDEX idx_training_history_run_id ON public.training_history (run_id);

CREATE UNIQUE INDEX uq_evaluation_final_training ON public.evaluations (run_id) WHERE evaluation_role = 'training_validation_final';

CREATE INDEX ix_evaluation_comparison ON public.evaluations (dataset_version_id, comparison_contract_hash, split, created_at, id);

CREATE INDEX ix_xai_same_image ON public.xai_evidence (input_sha256, input_contract_hash, model_version_id, method, generated_at, id);

CREATE INDEX ix_xai_evaluation ON public.xai_evidence (evaluation_id, method);

CREATE UNIQUE INDEX uq_e04_event_role ON public.evaluations (source_event_id, evaluation_role) WHERE source_kind = 'e10' AND evaluation_role IN ('calibration_default', 'calibration_selected');

CREATE UNIQUE INDEX uq_e04_contract_role ON public.evaluations (run_id, training_run_id, model_version_id, checkpoint_artifact_id, dataset_version_id, population_hash, protocol_version, protocol_hash, input_contract_hash, evaluation_role) NULLS NOT DISTINCT WHERE source_kind = 'e10' AND evaluation_role IN ('calibration_default', 'calibration_selected');

