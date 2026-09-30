-- DBV2.2 + approved R1. Install exclusively via guarded Alembic v2.
ALTER TABLE public.artifacts ADD CONSTRAINT artifacts_pkey PRIMARY KEY (id);

ALTER TABLE public.assessment_artifacts ADD CONSTRAINT assessment_artifacts_pkey PRIMARY KEY (attempt_id, sample_id, role);

ALTER TABLE public.assessment_attempts ADD CONSTRAINT assessment_attempts_pkey PRIMARY KEY (id);

ALTER TABLE public.assessment_campaign_consumers ADD CONSTRAINT assessment_campaign_consumers_pkey PRIMARY KEY (campaign_id, member_id, identity_id);

ALTER TABLE public.assessment_final_locks ADD CONSTRAINT assessment_final_locks_pkey PRIMARY KEY (id);

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_pkey PRIMARY KEY (id);

ALTER TABLE public.assessment_results ADD CONSTRAINT assessment_results_pkey PRIMARY KEY (attempt_id, sample_id);

ALTER TABLE public.audit_events ADD CONSTRAINT audit_events_pkey PRIMARY KEY (id);

ALTER TABLE public.blood_samples ADD CONSTRAINT blood_samples_pkey PRIMARY KEY (id);

ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_pkey PRIMARY KEY (id);

ALTER TABLE public.campaign_configurations ADD CONSTRAINT campaign_configurations_pkey PRIMARY KEY (campaign_id, configuration_hash);

ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_pkey PRIMARY KEY (id);

ALTER TABLE public.campaign_execution_events ADD CONSTRAINT campaign_execution_events_pkey PRIMARY KEY (id);

ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_pkey PRIMARY KEY (id);

ALTER TABLE public.campaign_technical_revisions ADD CONSTRAINT campaign_technical_revisions_pkey PRIMARY KEY (id);

ALTER TABLE public.cell_classification_events ADD CONSTRAINT cell_classification_events_pkey PRIMARY KEY (id);

ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT cell_classification_inputs_pkey PRIMARY KEY (id);

ALTER TABLE public.cell_classification_reviews ADD CONSTRAINT cell_classification_reviews_pkey PRIMARY KEY (id);

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_pkey PRIMARY KEY (id);

ALTER TABLE public.cell_crops ADD CONSTRAINT cell_crops_pkey PRIMARY KEY (id);

ALTER TABLE public.cell_detection_events ADD CONSTRAINT cell_detection_events_pkey PRIMARY KEY (id);

ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_pkey PRIMARY KEY (id);

ALTER TABLE public.cell_detections ADD CONSTRAINT cell_detections_pkey PRIMARY KEY (id);

ALTER TABLE public.cell_explanations ADD CONSTRAINT cell_explanations_pkey PRIMARY KEY (id);

ALTER TABLE public.cell_predictions ADD CONSTRAINT cell_predictions_pkey PRIMARY KEY (id);

ALTER TABLE public.clinical_identities ADD CONSTRAINT clinical_identities_pkey PRIMARY KEY (id);

ALTER TABLE public.dataset_materialization_activations ADD CONSTRAINT dataset_materialization_activations_pkey PRIMARY KEY (id);

ALTER TABLE public.dataset_materializations ADD CONSTRAINT dataset_materializations_pkey PRIMARY KEY (id);

ALTER TABLE public.dataset_source_records ADD CONSTRAINT dataset_source_records_pkey PRIMARY KEY (id);

ALTER TABLE public.dataset_split_assignments ADD CONSTRAINT dataset_split_assignments_pkey PRIMARY KEY (id);

ALTER TABLE public.dataset_split_images ADD CONSTRAINT dataset_split_images_pkey PRIMARY KEY (image_id);

ALTER TABLE public.dataset_split_statistics ADD CONSTRAINT dataset_split_statistics_pkey PRIMARY KEY (id);

ALTER TABLE public.dataset_split_validation_checks ADD CONSTRAINT dataset_split_validation_checks_pkey PRIMARY KEY (id);

ALTER TABLE public.dataset_splits ADD CONSTRAINT dataset_splits_pkey PRIMARY KEY (id);

ALTER TABLE public.dataset_version_sources ADD CONSTRAINT dataset_version_sources_pkey PRIMARY KEY (dataset_version_id, dataset_id, role);

ALTER TABLE public.dataset_versions ADD CONSTRAINT dataset_versions_pkey PRIMARY KEY (id);

ALTER TABLE public.datasets ADD CONSTRAINT datasets_pkey PRIMARY KEY (id);

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT deployed_model_versions_pkey PRIMARY KEY (id);

ALTER TABLE public.environment_packages ADD CONSTRAINT environment_packages_pkey PRIMARY KEY (id);

ALTER TABLE public.errors ADD CONSTRAINT errors_pkey PRIMARY KEY (id);

ALTER TABLE public.execution_logs ADD CONSTRAINT execution_logs_pkey PRIMARY KEY (id);

ALTER TABLE public.experiment_execution_events ADD CONSTRAINT experiment_execution_events_pkey PRIMARY KEY (id);

ALTER TABLE public.experiment_execution_gate ADD CONSTRAINT experiment_execution_gate_pkey PRIMARY KEY (singleton);

ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_pkey PRIMARY KEY (id);

ALTER TABLE public.experiments ADD CONSTRAINT experiments_pkey PRIMARY KEY (id);

ALTER TABLE public.explainability_results ADD CONSTRAINT explainability_results_pkey PRIMARY KEY (id);

ALTER TABLE public.identity_evidence ADD CONSTRAINT identity_evidence_pkey PRIMARY KEY (id);

ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT image_analysis_jobs_pkey PRIMARY KEY (id);

ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_pkey PRIMARY KEY (id);

ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_pkey PRIMARY KEY (id);

ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_pkey PRIMARY KEY (id);

ALTER TABLE public.local_execution_jobs ADD CONSTRAINT local_execution_jobs_pkey PRIMARY KEY (id);

ALTER TABLE public.microscopy_analysis_events ADD CONSTRAINT microscopy_analysis_events_pkey PRIMARY KEY (id);

ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_images_pkey PRIMARY KEY (id);

ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_pkey PRIMARY KEY (id);

ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_pkey PRIMARY KEY (id);

ALTER TABLE public.model_versions ADD CONSTRAINT model_versions_pkey PRIMARY KEY (id);

ALTER TABLE public.models ADD CONSTRAINT models_pkey PRIMARY KEY (id);

ALTER TABLE public.predictions ADD CONSTRAINT predictions_pkey PRIMARY KEY (id);

ALTER TABLE public.quality_assessment_queue_items ADD CONSTRAINT quality_assessment_queue_items_pkey PRIMARY KEY (id);

ALTER TABLE public.quality_gate_decisions ADD CONSTRAINT quality_gate_decisions_pkey PRIMARY KEY (id);

ALTER TABLE public.research_subjects ADD CONSTRAINT research_subjects_pkey PRIMARY KEY (id);

ALTER TABLE public.roles ADD CONSTRAINT roles_pkey PRIMARY KEY (id);

ALTER TABLE public.run_checkpoint_policy ADD CONSTRAINT run_checkpoint_policy_pkey PRIMARY KEY (run_checkpoint_policy_id);

ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT run_clinical_metrics_pkey PRIMARY KEY (run_clinical_metric_id);

ALTER TABLE public.run_dataset_images ADD CONSTRAINT run_dataset_images_pkey PRIMARY KEY (run_dataset_image_id);

ALTER TABLE public.run_image_predictions ADD CONSTRAINT run_image_predictions_pkey PRIMARY KEY (run_image_prediction_id);

ALTER TABLE public.run_io_records ADD CONSTRAINT run_io_records_pkey PRIMARY KEY (run_io_id);

ALTER TABLE public.run_lineage ADD CONSTRAINT run_lineage_pkey PRIMARY KEY (id);

ALTER TABLE public.run_metrics ADD CONSTRAINT run_metrics_pkey PRIMARY KEY (id);

ALTER TABLE public.run_model_deployments ADD CONSTRAINT run_model_deployments_pkey PRIMARY KEY (id);

ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT run_threshold_calibration_pkey PRIMARY KEY (run_threshold_calibration_id);

ALTER TABLE public.runs ADD CONSTRAINT runs_pkey PRIMARY KEY (id);

ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_pkey PRIMARY KEY (id);

ALTER TABLE public.scientific_reviews ADD CONSTRAINT scientific_reviews_pkey PRIMARY KEY (id);

ALTER TABLE public.scientific_validation_annotation_events ADD CONSTRAINT scientific_validation_annotation_events_pkey PRIMARY KEY (id);

ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_pkey PRIMARY KEY (id);

ALTER TABLE public.scientific_validation_classification_runs ADD CONSTRAINT scientific_validation_classification_runs_pkey PRIMARY KEY (session_id, classification_run_id);

ALTER TABLE public.scientific_validation_detection_runs ADD CONSTRAINT scientific_validation_detection_runs_pkey PRIMARY KEY (session_id, detection_run_id);

ALTER TABLE public.scientific_validation_images ADD CONSTRAINT scientific_validation_images_pkey PRIMARY KEY (session_id, microscopy_image_id);

ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_pkey PRIMARY KEY (id);

ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_pkey PRIMARY KEY (id);

ALTER TABLE public.smear_slides ADD CONSTRAINT smear_slides_pkey PRIMARY KEY (id);

ALTER TABLE public.stage2_model_publication_events ADD CONSTRAINT stage2_model_publication_events_pkey PRIMARY KEY (id);

ALTER TABLE public.stage2_model_publications ADD CONSTRAINT stage2_model_publications_pkey PRIMARY KEY (id);

ALTER TABLE public.synthetic_data_runs ADD CONSTRAINT synthetic_data_runs_pkey PRIMARY KEY (id);

ALTER TABLE public.train_execution_records ADD CONSTRAINT train_execution_records_pkey PRIMARY KEY (run_id, kind, phase, record_key);

ALTER TABLE public.train_execution_revisions ADD CONSTRAINT train_execution_revisions_pkey PRIMARY KEY (attempt_id);

ALTER TABLE public.train_execution_sessions ADD CONSTRAINT train_execution_sessions_pkey PRIMARY KEY (run_id);

ALTER TABLE public.training_history ADD CONSTRAINT training_history_pkey PRIMARY KEY (id);

ALTER TABLE public.user_roles ADD CONSTRAINT user_roles_pkey PRIMARY KEY (user_id, role_id);

ALTER TABLE public.users ADD CONSTRAINT users_pkey PRIMARY KEY (id);

ALTER TABLE public.assessment_artifacts ADD CONSTRAINT assessment_artifacts_artifact_id_key UNIQUE (artifact_id);

ALTER TABLE public.assessment_attempts ADD CONSTRAINT assessment_attempts_artifact_root_key UNIQUE (artifact_root);

ALTER TABLE public.assessment_attempts ADD CONSTRAINT assessment_attempts_identity_id_ordinal_key UNIQUE (identity_id, ordinal);

ALTER TABLE public.assessment_final_locks ADD CONSTRAINT assessment_final_locks_identity_hash_key UNIQUE (identity_hash);

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_hash_key UNIQUE (identity_hash);

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_structural_hash_key UNIQUE (structural_hash);

ALTER TABLE public.blood_samples ADD CONSTRAINT uq_blood_samples_case_code UNIQUE (case_id, sample_code);

ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_member_id_id_key UNIQUE (member_id, id);

ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_member_id_ordinal_key UNIQUE (member_id, ordinal);

ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_training_run_id_key UNIQUE (training_run_id);

ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_attempt_id_key UNIQUE (attempt_id);

ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_previous_attempt_id_key UNIQUE (previous_attempt_id);

ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_run_id_key UNIQUE (run_id);

ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_campaign_id_configuration_hash_seed_key UNIQUE (campaign_id, configuration_hash, seed);

ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_campaign_id_position_key UNIQUE (campaign_id, position);

ALTER TABLE public.campaign_technical_revisions ADD CONSTRAINT campaign_technical_revisions_campaign_id_id_key UNIQUE (campaign_id, id);

ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT uq_cell_classification_inputs_crop UNIQUE (classification_run_id, crop_id);

ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT uq_cell_classification_inputs_detection UNIQUE (classification_run_id, cell_detection_id);

ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT uq_cell_classification_inputs_order UNIQUE (classification_run_id, input_order);

ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT uq_cell_classification_inputs_prediction_owner UNIQUE (id, classification_run_id, cell_detection_id, crop_id);

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_classification_run_code_key UNIQUE (classification_run_code);

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT uq_cell_classification_runs_detection_identity UNIQUE (id, detection_run_id);

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT uq_cell_classification_runs_identity UNIQUE (id, analysis_run_id, detection_run_id);

ALTER TABLE public.cell_crops ADD CONSTRAINT uq_cell_crops_detection UNIQUE (cell_detection_id);

ALTER TABLE public.cell_crops ADD CONSTRAINT uq_cell_crops_storage_key UNIQUE (relative_storage_key);

ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_detection_run_code_key UNIQUE (detection_run_code);

ALTER TABLE public.cell_detection_runs ADD CONSTRAINT uq_cell_detection_runs_identity UNIQUE (id, analysis_run_id);

ALTER TABLE public.cell_detections ADD CONSTRAINT uq_cell_detections_cell_code UNIQUE (cell_code);

ALTER TABLE public.cell_detections ADD CONSTRAINT uq_cell_detections_component UNIQUE (connected_component_id);

ALTER TABLE public.cell_detections ADD CONSTRAINT uq_cell_detections_identity UNIQUE (id, detection_run_id, microscopy_image_id);

ALTER TABLE public.cell_detections ADD CONSTRAINT uq_cell_detections_run_index UNIQUE (detection_run_id, cell_index);

ALTER TABLE public.cell_explanations ADD CONSTRAINT cell_explanations_cell_prediction_id_key UNIQUE (cell_prediction_id);

ALTER TABLE public.cell_predictions ADD CONSTRAINT cell_predictions_classification_input_id_key UNIQUE (classification_input_id);

ALTER TABLE public.cell_predictions ADD CONSTRAINT uq_cell_predictions_run_identity UNIQUE (id, classification_run_id);

ALTER TABLE public.clinical_identities ADD CONSTRAINT uq_clinical_identities_source UNIQUE (dataset_id, identity_type, source_identifier);

ALTER TABLE public.dataset_materializations ADD CONSTRAINT uq_dataset_materializations_attempt UNIQUE (dataset_version_id, attempt_number);

ALTER TABLE public.dataset_source_records ADD CONSTRAINT uq_dataset_source_records_key UNIQUE (dataset_id, source_record_key);

ALTER TABLE public.dataset_split_assignments ADD CONSTRAINT uq_dataset_split_assignments_record UNIQUE (dataset_version_id, source_record_id);

ALTER TABLE public.dataset_split_images ADD CONSTRAINT uq_dataset_split_images_path UNIQUE (dataset_dir, relative_path);

ALTER TABLE public.dataset_versions ADD CONSTRAINT uq_dataset_versions_name_semver UNIQUE (name, semantic_version);

ALTER TABLE public.image_connected_components ADD CONSTRAINT uq_image_connected_components_identity UNIQUE (id, detection_run_id, analysis_run_image_id, microscopy_image_id);

ALTER TABLE public.image_connected_components ADD CONSTRAINT uq_image_connected_components_run_image_index UNIQUE (detection_run_id, analysis_run_image_id, component_index);

ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_analysis_run_id_microscopy_image__key UNIQUE (analysis_run_id, microscopy_image_id);

ALTER TABLE public.local_execution_jobs ADD CONSTRAINT local_execution_jobs_owner_key UNIQUE (owner);

ALTER TABLE public.local_execution_jobs ADD CONSTRAINT local_execution_jobs_run_id_key UNIQUE (run_id);

ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_image_analysis_run_id_microscopy_im_key UNIQUE (analysis_run_id, microscopy_image_id);

ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_image_analysis_run_id_sequence_numb_key UNIQUE (analysis_run_id, sequence_number);

ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_image_id_analysis_run_id_microscopy_key UNIQUE (id, analysis_run_id, microscopy_image_id);

ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_run_code_key UNIQUE (run_code);

ALTER TABLE public.microscopy_images ADD CONSTRAINT uq_microscopy_images_slide_code UNIQUE (slide_id, image_code);

ALTER TABLE public.microscopy_images ADD CONSTRAINT uq_microscopy_images_slide_sha256 UNIQUE (slide_id, sha256);

ALTER TABLE public.research_subjects ADD CONSTRAINT research_subjects_subject_code_key UNIQUE (subject_code);

ALTER TABLE public.roles ADD CONSTRAINT roles_name_key UNIQUE (name);

ALTER TABLE public.run_dataset_images ADD CONSTRAINT uq_run_dataset_images_usage UNIQUE (run_id, image_id, usage_context);

ALTER TABLE public.run_lineage ADD CONSTRAINT uq_run_lineage_parent_child_type UNIQUE (parent_run_id, child_run_id, relationship_type);

ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_case_code_key UNIQUE (case_code);

ALTER TABLE public.scientific_validation_annotation_events ADD CONSTRAINT scientific_validation_annotat_annotation_id_annotation_vers_key UNIQUE (annotation_id, annotation_version);

ALTER TABLE public.scientific_validation_images ADD CONSTRAINT scientific_validation_images_session_id_sequence_number_key UNIQUE (session_id, sequence_number);

ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_classification_run_id_key UNIQUE (classification_run_id);

ALTER TABLE public.smear_slides ADD CONSTRAINT uq_smear_slides_sample_code UNIQUE (sample_id, slide_code);

ALTER TABLE public.train_execution_sessions ADD CONSTRAINT train_execution_sessions_artifact_root_key UNIQUE (artifact_root);

ALTER TABLE public.train_execution_sessions ADD CONSTRAINT train_execution_sessions_attempt_id_key UNIQUE (attempt_id);

ALTER TABLE public.users ADD CONSTRAINT users_email_key UNIQUE (email);

ALTER TABLE public.users ADD CONSTRAINT users_username_key UNIQUE (username);

ALTER TABLE public.training_history ADD CONSTRAINT uq_v2_epoch UNIQUE (run_id, phase, epoch);

ALTER TABLE public.predictions ADD CONSTRAINT uq_v2_evaluation_sample UNIQUE (evaluation_id, dataset_source_record_id);

ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT v2_run_clinical_metrics_unique_f9437c271ff6 UNIQUE (evaluation_id);

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_primary_360aa242ca7c PRIMARY KEY (run_id);

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_primary_8c8464f42472 PRIMARY KEY (id);

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_unique_2b29f071653b UNIQUE (run_id, source_kind, source_record_phase, source_record_key);

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_unique_927a8d4fe69d UNIQUE (id, run_id);

ALTER TABLE public.evaluation_ensemble_members ADD CONSTRAINT v2_evaluation_ensemble_members_primary_0f6c3f155b09 PRIMARY KEY (evaluation_id, ordinal);

ALTER TABLE public.evaluation_ensemble_members ADD CONSTRAINT v2_evaluation_ensemble_members_unique_3a2092158e31 UNIQUE (evaluation_id, model_version_id);

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_primary_8c8464f42472 PRIMARY KEY (id);

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_unique_d9477cb1fece UNIQUE (ml_explanation_id);

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_unique_d4bf0f195fcf UNIQUE (cell_explanation_id);

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_unique_0be310eeb2b7 UNIQUE (assessment_attempt_id, assessment_sample_id);

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_primary_8c8464f42472 PRIMARY KEY (id);

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_unique_ee15a9513a9e UNIQUE (evidence_id, role, ordinal);

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT v2_xai_quantitative_evaluations_primary_8c8464f42472 PRIMARY KEY (id);

ALTER TABLE public.xai_interpretations ADD CONSTRAINT v2_xai_interpretations_primary_8c8464f42472 PRIMARY KEY (id);

ALTER TABLE public.xai_specialist_reviews ADD CONSTRAINT v2_xai_specialist_reviews_primary_8c8464f42472 PRIMARY KEY (id);

ALTER TABLE public.xai_method_configurations ADD CONSTRAINT xai_method_configurations_pkey PRIMARY KEY (id);

ALTER TABLE public.xai_region_attributions ADD CONSTRAINT xai_region_attributions_pkey PRIMARY KEY (xai_evidence_id, region_type, region_index);

ALTER TABLE public.xai_evaluation_protocols ADD CONSTRAINT xai_evaluation_protocols_pkey PRIMARY KEY (id);

ALTER TABLE public.xai_evaluation_members ADD CONSTRAINT xai_evaluation_members_pkey PRIMARY KEY (evaluation_id, xai_evidence_id);

ALTER TABLE public.xai_method_configurations ADD CONSTRAINT uq_xai_method_configuration_hash UNIQUE (configuration_hash);

ALTER TABLE public.xai_evaluation_protocols ADD CONSTRAINT uq_xai_protocol_hash UNIQUE (protocol_hash);

ALTER TABLE public.xai_evaluation_protocols ADD CONSTRAINT uq_xai_protocol_metric UNIQUE (id, metric_name);

CREATE UNIQUE INDEX uq_artifacts_id_run_id ON public.artifacts (id, run_id);

CREATE UNIQUE INDEX uq_cell_crops_id_detection ON public.cell_crops (id, cell_detection_id);

CREATE UNIQUE INDEX uq_deployed_model_versions_id_version ON public.deployed_model_versions (id, model_version_id);

CREATE UNIQUE INDEX uq_image_analysis_jobs_identity ON public.image_analysis_jobs (id, inference_run_id, deployed_model_version_id, model_version_id);

CREATE UNIQUE INDEX uq_microscopy_analysis_equivalent ON public.microscopy_analysis_runs (ingestion_batch_id, quality_profile_key, quality_profile_version, quality_algorithm_version, input_manifest_sha256);

CREATE UNIQUE INDEX uq_model_versions_id_checkpoint_artifact ON public.model_versions (id, checkpoint_artifact_id);

CREATE UNIQUE INDEX uq_model_versions_id_training_run ON public.model_versions (id, training_run_id);

CREATE UNIQUE INDEX uq_run_model_deployments_binding ON public.run_model_deployments (run_id, deployed_model_version_id, role, ordinal);

CREATE UNIQUE INDEX uq_run_model_deployments_run_deployment_version ON public.run_model_deployments (run_id, deployed_model_version_id, model_version_id);

CREATE UNIQUE INDEX uq_run_threshold_calibration_id_version ON public.run_threshold_calibration (run_threshold_calibration_id, model_version_id);

CREATE UNIQUE INDEX uq_stage2_model_publications_id_version ON public.stage2_model_publications (id, model_version_id);

