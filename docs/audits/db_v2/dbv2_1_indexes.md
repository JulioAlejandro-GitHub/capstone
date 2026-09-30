# DBV2.1 — Índices

PK y UNIQUE crean índices implícitos; se enumeran separadamente de CREATE INDEX. No duplicar índices exactos. Un prefijo más corto no se elimina sin evidencia de consultas; tampoco se añaden índices a todas las FK por defecto. Índices XAI nuevos cubren recorrido inverso de miembros, método, protocolo y anotación. E-04 conserva NULLS NOT DISTINCT y predicados de roles.

## Implícitos por integridad

- `artifacts_pkey` en `artifacts(id)`: identidad primaria.
- `assessment_artifacts_pkey` en `assessment_artifacts(attempt_id, sample_id, role)`: identidad primaria.
- `assessment_attempts_pkey` en `assessment_attempts(id)`: identidad primaria.
- `assessment_campaign_consumers_pkey` en `assessment_campaign_consumers(campaign_id, member_id, identity_id)`: identidad primaria.
- `assessment_final_locks_pkey` en `assessment_final_locks(id)`: identidad primaria.
- `assessment_identities_pkey` en `assessment_identities(id)`: identidad primaria.
- `assessment_results_pkey` en `assessment_results(attempt_id, sample_id)`: identidad primaria.
- `audit_events_pkey` en `audit_events(id)`: identidad primaria.
- `blood_samples_pkey` en `blood_samples(id)`: identidad primaria.
- `campaign_attempts_pkey` en `campaign_attempts(id)`: identidad primaria.
- `campaign_configurations_pkey` en `campaign_configurations(campaign_id, configuration_hash)`: identidad primaria.
- `campaign_controlled_requests_pkey` en `campaign_controlled_requests(id)`: identidad primaria.
- `campaign_execution_events_pkey` en `campaign_execution_events(id)`: identidad primaria.
- `campaign_members_pkey` en `campaign_members(id)`: identidad primaria.
- `campaign_technical_revisions_pkey` en `campaign_technical_revisions(id)`: identidad primaria.
- `cell_classification_events_pkey` en `cell_classification_events(id)`: identidad primaria.
- `cell_classification_inputs_pkey` en `cell_classification_inputs(id)`: identidad primaria.
- `cell_classification_reviews_pkey` en `cell_classification_reviews(id)`: identidad primaria.
- `cell_classification_runs_pkey` en `cell_classification_runs(id)`: identidad primaria.
- `cell_crops_pkey` en `cell_crops(id)`: identidad primaria.
- `cell_detection_events_pkey` en `cell_detection_events(id)`: identidad primaria.
- `cell_detection_runs_pkey` en `cell_detection_runs(id)`: identidad primaria.
- `cell_detections_pkey` en `cell_detections(id)`: identidad primaria.
- `cell_explanations_pkey` en `cell_explanations(id)`: identidad primaria.
- `cell_predictions_pkey` en `cell_predictions(id)`: identidad primaria.
- `clinical_identities_pkey` en `clinical_identities(id)`: identidad primaria.
- `dataset_materialization_activations_pkey` en `dataset_materialization_activations(id)`: identidad primaria.
- `dataset_materializations_pkey` en `dataset_materializations(id)`: identidad primaria.
- `dataset_source_records_pkey` en `dataset_source_records(id)`: identidad primaria.
- `dataset_split_assignments_pkey` en `dataset_split_assignments(id)`: identidad primaria.
- `dataset_split_images_pkey` en `dataset_split_images(image_id)`: identidad primaria.
- `dataset_split_statistics_pkey` en `dataset_split_statistics(id)`: identidad primaria.
- `dataset_split_validation_checks_pkey` en `dataset_split_validation_checks(id)`: identidad primaria.
- `dataset_splits_pkey` en `dataset_splits(id)`: identidad primaria.
- `dataset_version_sources_pkey` en `dataset_version_sources(dataset_version_id, dataset_id, role)`: identidad primaria.
- `dataset_versions_pkey` en `dataset_versions(id)`: identidad primaria.
- `datasets_pkey` en `datasets(id)`: identidad primaria.
- `deployed_model_versions_pkey` en `deployed_model_versions(id)`: identidad primaria.
- `environment_packages_pkey` en `environment_packages(id)`: identidad primaria.
- `errors_pkey` en `errors(id)`: identidad primaria.
- `execution_logs_pkey` en `execution_logs(id)`: identidad primaria.
- `experiment_execution_events_pkey` en `experiment_execution_events(id)`: identidad primaria.
- `experiment_execution_gate_pkey` en `experiment_execution_gate(singleton)`: identidad primaria.
- `experimental_campaigns_pkey` en `experimental_campaigns(id)`: identidad primaria.
- `experiments_pkey` en `experiments(id)`: identidad primaria.
- `explainability_results_pkey` en `explainability_results(id)`: identidad primaria.
- `identity_evidence_pkey` en `identity_evidence(id)`: identidad primaria.
- `image_analysis_jobs_pkey` en `image_analysis_jobs(id)`: identidad primaria.
- `image_connected_components_pkey` en `image_connected_components(id)`: identidad primaria.
- `image_ingestion_batches_pkey` en `image_ingestion_batches(id)`: identidad primaria.
- `image_quality_assessments_pkey` en `image_quality_assessments(id)`: identidad primaria.
- `local_execution_jobs_pkey` en `local_execution_jobs(id)`: identidad primaria.
- `microscopy_analysis_events_pkey` en `microscopy_analysis_events(id)`: identidad primaria.
- `microscopy_analysis_run_images_pkey` en `microscopy_analysis_run_images(id)`: identidad primaria.
- `microscopy_analysis_runs_pkey` en `microscopy_analysis_runs(id)`: identidad primaria.
- `microscopy_images_pkey` en `microscopy_images(id)`: identidad primaria.
- `model_versions_pkey` en `model_versions(id)`: identidad primaria.
- `models_pkey` en `models(id)`: identidad primaria.
- `predictions_pkey` en `predictions(id)`: identidad primaria.
- `quality_assessment_queue_items_pkey` en `quality_assessment_queue_items(id)`: identidad primaria.
- `quality_gate_decisions_pkey` en `quality_gate_decisions(id)`: identidad primaria.
- `research_subjects_pkey` en `research_subjects(id)`: identidad primaria.
- `roles_pkey` en `roles(id)`: identidad primaria.
- `run_checkpoint_policy_pkey` en `run_checkpoint_policy(run_checkpoint_policy_id)`: identidad primaria.
- `run_clinical_metrics_pkey` en `run_clinical_metrics(run_clinical_metric_id)`: identidad primaria.
- `run_dataset_images_pkey` en `run_dataset_images(run_dataset_image_id)`: identidad primaria.
- `run_image_predictions_pkey` en `run_image_predictions(run_image_prediction_id)`: identidad primaria.
- `run_io_records_pkey` en `run_io_records(run_io_id)`: identidad primaria.
- `run_lineage_pkey` en `run_lineage(id)`: identidad primaria.
- `run_metrics_pkey` en `run_metrics(id)`: identidad primaria.
- `run_model_deployments_pkey` en `run_model_deployments(id)`: identidad primaria.
- `run_threshold_calibration_pkey` en `run_threshold_calibration(run_threshold_calibration_id)`: identidad primaria.
- `runs_pkey` en `runs(id)`: identidad primaria.
- `scientific_cases_pkey` en `scientific_cases(id)`: identidad primaria.
- `scientific_reviews_pkey` en `scientific_reviews(id)`: identidad primaria.
- `scientific_validation_annotation_events_pkey` en `scientific_validation_annotation_events(id)`: identidad primaria.
- `scientific_validation_annotations_pkey` en `scientific_validation_annotations(id)`: identidad primaria.
- `scientific_validation_classification_runs_pkey` en `scientific_validation_classification_runs(session_id, classification_run_id)`: identidad primaria.
- `scientific_validation_detection_runs_pkey` en `scientific_validation_detection_runs(session_id, detection_run_id)`: identidad primaria.
- `scientific_validation_images_pkey` en `scientific_validation_images(session_id, microscopy_image_id)`: identidad primaria.
- `scientific_validation_sessions_pkey` en `scientific_validation_sessions(id)`: identidad primaria.
- `smear_analysis_summaries_pkey` en `smear_analysis_summaries(id)`: identidad primaria.
- `smear_slides_pkey` en `smear_slides(id)`: identidad primaria.
- `stage2_model_publication_events_pkey` en `stage2_model_publication_events(id)`: identidad primaria.
- `stage2_model_publications_pkey` en `stage2_model_publications(id)`: identidad primaria.
- `synthetic_data_runs_pkey` en `synthetic_data_runs(id)`: identidad primaria.
- `train_execution_records_pkey` en `train_execution_records(run_id, kind, phase, record_key)`: identidad primaria.
- `train_execution_revisions_pkey` en `train_execution_revisions(attempt_id)`: identidad primaria.
- `train_execution_sessions_pkey` en `train_execution_sessions(run_id)`: identidad primaria.
- `training_history_pkey` en `training_history(id)`: identidad primaria.
- `user_roles_pkey` en `user_roles(user_id, role_id)`: identidad primaria.
- `users_pkey` en `users(id)`: identidad primaria.
- `assessment_artifacts_artifact_id_key` en `assessment_artifacts(artifact_id)`: unicidad contractual / destino FK; CONSTRAINT assessment_artifacts_artifact_id_key UNIQUE (artifact_id).
- `assessment_attempts_artifact_root_key` en `assessment_attempts(artifact_root)`: unicidad contractual / destino FK; CONSTRAINT assessment_attempts_artifact_root_key UNIQUE (artifact_root).
- `assessment_attempts_identity_id_ordinal_key` en `assessment_attempts(identity_id, ordinal)`: unicidad contractual / destino FK; CONSTRAINT assessment_attempts_identity_id_ordinal_key UNIQUE (identity_id, ordinal).
- `assessment_final_locks_identity_hash_key` en `assessment_final_locks(identity_hash)`: unicidad contractual / destino FK; CONSTRAINT assessment_final_locks_identity_hash_key UNIQUE (identity_hash).
- `assessment_identities_identity_hash_key` en `assessment_identities(identity_hash)`: unicidad contractual / destino FK; CONSTRAINT assessment_identities_identity_hash_key UNIQUE (identity_hash).
- `assessment_identities_structural_hash_key` en `assessment_identities(structural_hash)`: unicidad contractual / destino FK; CONSTRAINT assessment_identities_structural_hash_key UNIQUE (structural_hash).
- `uq_blood_samples_case_code` en `blood_samples(case_id, sample_code)`: unicidad contractual / destino FK; CONSTRAINT uq_blood_samples_case_code UNIQUE (case_id, sample_code).
- `campaign_attempts_member_id_id_key` en `campaign_attempts(member_id, id)`: unicidad contractual / destino FK; CONSTRAINT campaign_attempts_member_id_id_key UNIQUE (member_id, id).
- `campaign_attempts_member_id_ordinal_key` en `campaign_attempts(member_id, ordinal)`: unicidad contractual / destino FK; CONSTRAINT campaign_attempts_member_id_ordinal_key UNIQUE (member_id, ordinal).
- `campaign_attempts_training_run_id_key` en `campaign_attempts(training_run_id)`: unicidad contractual / destino FK; CONSTRAINT campaign_attempts_training_run_id_key UNIQUE (training_run_id).
- `campaign_controlled_requests_attempt_id_key` en `campaign_controlled_requests(attempt_id)`: unicidad contractual / destino FK; CONSTRAINT campaign_controlled_requests_attempt_id_key UNIQUE (attempt_id).
- `campaign_controlled_requests_previous_attempt_id_key` en `campaign_controlled_requests(previous_attempt_id)`: unicidad contractual / destino FK; CONSTRAINT campaign_controlled_requests_previous_attempt_id_key UNIQUE (previous_attempt_id).
- `campaign_controlled_requests_run_id_key` en `campaign_controlled_requests(run_id)`: unicidad contractual / destino FK; CONSTRAINT campaign_controlled_requests_run_id_key UNIQUE (run_id).
- `campaign_members_campaign_id_configuration_hash_seed_key` en `campaign_members(campaign_id, configuration_hash, seed)`: unicidad contractual / destino FK; CONSTRAINT campaign_members_campaign_id_configuration_hash_seed_key UNIQUE (campaign_id, configuration_hash, seed).
- `campaign_members_campaign_id_position_key` en `campaign_members(campaign_id, position)`: unicidad contractual / destino FK; CONSTRAINT campaign_members_campaign_id_position_key UNIQUE (campaign_id, position).
- `campaign_technical_revisions_campaign_id_id_key` en `campaign_technical_revisions(campaign_id, id)`: unicidad contractual / destino FK; CONSTRAINT campaign_technical_revisions_campaign_id_id_key UNIQUE (campaign_id, id).
- `uq_cell_classification_inputs_crop` en `cell_classification_inputs(classification_run_id, crop_id)`: unicidad contractual / destino FK; CONSTRAINT uq_cell_classification_inputs_crop UNIQUE (classification_run_id, crop_id).
- `uq_cell_classification_inputs_detection` en `cell_classification_inputs(classification_run_id, cell_detection_id)`: unicidad contractual / destino FK; CONSTRAINT uq_cell_classification_inputs_detection UNIQUE (classification_run_id, cell_detection_id).
- `uq_cell_classification_inputs_order` en `cell_classification_inputs(classification_run_id, input_order)`: unicidad contractual / destino FK; CONSTRAINT uq_cell_classification_inputs_order UNIQUE (classification_run_id, input_order).
- `uq_cell_classification_inputs_prediction_owner` en `cell_classification_inputs(id, classification_run_id, cell_detection_id, crop_id)`: unicidad contractual / destino FK; CONSTRAINT uq_cell_classification_inputs_prediction_owner UNIQUE (id, classification_run_id, cell_detection_id, crop_id).
- `cell_classification_runs_classification_run_code_key` en `cell_classification_runs(classification_run_code)`: unicidad contractual / destino FK; CONSTRAINT cell_classification_runs_classification_run_code_key UNIQUE (classification_run_code).
- `uq_cell_classification_runs_detection_identity` en `cell_classification_runs(id, detection_run_id)`: unicidad contractual / destino FK; CONSTRAINT uq_cell_classification_runs_detection_identity UNIQUE (id, detection_run_id).
- `uq_cell_classification_runs_identity` en `cell_classification_runs(id, analysis_run_id, detection_run_id)`: unicidad contractual / destino FK; CONSTRAINT uq_cell_classification_runs_identity UNIQUE (id, analysis_run_id, detection_run_id).
- `uq_cell_crops_detection` en `cell_crops(cell_detection_id)`: unicidad contractual / destino FK; CONSTRAINT uq_cell_crops_detection UNIQUE (cell_detection_id).
- `uq_cell_crops_storage_key` en `cell_crops(relative_storage_key)`: unicidad contractual / destino FK; CONSTRAINT uq_cell_crops_storage_key UNIQUE (relative_storage_key).
- `cell_detection_runs_detection_run_code_key` en `cell_detection_runs(detection_run_code)`: unicidad contractual / destino FK; CONSTRAINT cell_detection_runs_detection_run_code_key UNIQUE (detection_run_code).
- `uq_cell_detection_runs_identity` en `cell_detection_runs(id, analysis_run_id)`: unicidad contractual / destino FK; CONSTRAINT uq_cell_detection_runs_identity UNIQUE (id, analysis_run_id).
- `uq_cell_detections_cell_code` en `cell_detections(cell_code)`: unicidad contractual / destino FK; CONSTRAINT uq_cell_detections_cell_code UNIQUE (cell_code).
- `uq_cell_detections_component` en `cell_detections(connected_component_id)`: unicidad contractual / destino FK; CONSTRAINT uq_cell_detections_component UNIQUE (connected_component_id).
- `uq_cell_detections_identity` en `cell_detections(id, detection_run_id, microscopy_image_id)`: unicidad contractual / destino FK; CONSTRAINT uq_cell_detections_identity UNIQUE (id, detection_run_id, microscopy_image_id).
- `uq_cell_detections_run_index` en `cell_detections(detection_run_id, cell_index)`: unicidad contractual / destino FK; CONSTRAINT uq_cell_detections_run_index UNIQUE (detection_run_id, cell_index).
- `cell_explanations_cell_prediction_id_key` en `cell_explanations(cell_prediction_id)`: unicidad contractual / destino FK; CONSTRAINT cell_explanations_cell_prediction_id_key UNIQUE (cell_prediction_id).
- `cell_predictions_classification_input_id_key` en `cell_predictions(classification_input_id)`: unicidad contractual / destino FK; CONSTRAINT cell_predictions_classification_input_id_key UNIQUE (classification_input_id).
- `uq_cell_predictions_run_identity` en `cell_predictions(id, classification_run_id)`: unicidad contractual / destino FK; CONSTRAINT uq_cell_predictions_run_identity UNIQUE (id, classification_run_id).
- `uq_clinical_identities_source` en `clinical_identities(dataset_id, identity_type, source_identifier)`: unicidad contractual / destino FK; CONSTRAINT uq_clinical_identities_source UNIQUE (dataset_id, identity_type, source_identifier).
- `uq_dataset_materializations_attempt` en `dataset_materializations(dataset_version_id, attempt_number)`: unicidad contractual / destino FK; CONSTRAINT uq_dataset_materializations_attempt UNIQUE (dataset_version_id, attempt_number).
- `uq_dataset_source_records_key` en `dataset_source_records(dataset_id, source_record_key)`: unicidad contractual / destino FK; CONSTRAINT uq_dataset_source_records_key UNIQUE (dataset_id, source_record_key).
- `uq_dataset_split_assignments_record` en `dataset_split_assignments(dataset_version_id, source_record_id)`: unicidad contractual / destino FK; CONSTRAINT uq_dataset_split_assignments_record UNIQUE (dataset_version_id, source_record_id).
- `uq_dataset_split_images_path` en `dataset_split_images(dataset_dir, relative_path)`: unicidad contractual / destino FK; CONSTRAINT uq_dataset_split_images_path UNIQUE (dataset_dir, relative_path).
- `uq_dataset_versions_name_semver` en `dataset_versions(name, semantic_version)`: unicidad contractual / destino FK; CONSTRAINT uq_dataset_versions_name_semver UNIQUE (name, semantic_version).
- `uq_image_connected_components_identity` en `image_connected_components(id, detection_run_id, analysis_run_image_id, microscopy_image_id)`: unicidad contractual / destino FK; CONSTRAINT uq_image_connected_components_identity UNIQUE (id, detection_run_id, analysis_run_image_id, microscopy_image_id).
- `uq_image_connected_components_run_image_index` en `image_connected_components(detection_run_id, analysis_run_image_id, component_index)`: unicidad contractual / destino FK; CONSTRAINT uq_image_connected_components_run_image_index UNIQUE (detection_run_id, analysis_run_image_id, component_index).
- `image_quality_assessments_analysis_run_id_microscopy_image__key` en `image_quality_assessments(analysis_run_id, microscopy_image_id)`: unicidad contractual / destino FK; CONSTRAINT image_quality_assessments_analysis_run_id_microscopy_image__key UNIQUE (analysis_run_id, microscopy_image_id).
- `local_execution_jobs_owner_key` en `local_execution_jobs(owner)`: unicidad contractual / destino FK; CONSTRAINT local_execution_jobs_owner_key UNIQUE (owner).
- `local_execution_jobs_run_id_key` en `local_execution_jobs(run_id)`: unicidad contractual / destino FK; CONSTRAINT local_execution_jobs_run_id_key UNIQUE (run_id).
- `microscopy_analysis_run_image_analysis_run_id_microscopy_im_key` en `microscopy_analysis_run_images(analysis_run_id, microscopy_image_id)`: unicidad contractual / destino FK; CONSTRAINT microscopy_analysis_run_image_analysis_run_id_microscopy_im_key UNIQUE (analysis_run_id, microscopy_image_id).
- `microscopy_analysis_run_image_analysis_run_id_sequence_numb_key` en `microscopy_analysis_run_images(analysis_run_id, sequence_number)`: unicidad contractual / destino FK; CONSTRAINT microscopy_analysis_run_image_analysis_run_id_sequence_numb_key UNIQUE (analysis_run_id, sequence_number).
- `microscopy_analysis_run_image_id_analysis_run_id_microscopy_key` en `microscopy_analysis_run_images(id, analysis_run_id, microscopy_image_id)`: unicidad contractual / destino FK; CONSTRAINT microscopy_analysis_run_image_id_analysis_run_id_microscopy_key UNIQUE (id, analysis_run_id, microscopy_image_id).
- `microscopy_analysis_runs_run_code_key` en `microscopy_analysis_runs(run_code)`: unicidad contractual / destino FK; CONSTRAINT microscopy_analysis_runs_run_code_key UNIQUE (run_code).
- `uq_microscopy_images_slide_code` en `microscopy_images(slide_id, image_code)`: unicidad contractual / destino FK; CONSTRAINT uq_microscopy_images_slide_code UNIQUE (slide_id, image_code).
- `uq_microscopy_images_slide_sha256` en `microscopy_images(slide_id, sha256)`: unicidad contractual / destino FK; CONSTRAINT uq_microscopy_images_slide_sha256 UNIQUE (slide_id, sha256).
- `research_subjects_subject_code_key` en `research_subjects(subject_code)`: unicidad contractual / destino FK; CONSTRAINT research_subjects_subject_code_key UNIQUE (subject_code).
- `roles_name_key` en `roles(name)`: unicidad contractual / destino FK; CONSTRAINT roles_name_key UNIQUE (name).
- `uq_run_dataset_images_usage` en `run_dataset_images(run_id, image_id, usage_context)`: unicidad contractual / destino FK; CONSTRAINT uq_run_dataset_images_usage UNIQUE (run_id, image_id, usage_context).
- `uq_run_lineage_parent_child_type` en `run_lineage(parent_run_id, child_run_id, relationship_type)`: unicidad contractual / destino FK; CONSTRAINT uq_run_lineage_parent_child_type UNIQUE (parent_run_id, child_run_id, relationship_type).
- `scientific_cases_case_code_key` en `scientific_cases(case_code)`: unicidad contractual / destino FK; CONSTRAINT scientific_cases_case_code_key UNIQUE (case_code).
- `scientific_validation_annotat_annotation_id_annotation_vers_key` en `scientific_validation_annotation_events(annotation_id, annotation_version)`: unicidad contractual / destino FK; CONSTRAINT scientific_validation_annotat_annotation_id_annotation_vers_key UNIQUE (annotation_id, annotation_version).
- `scientific_validation_images_session_id_sequence_number_key` en `scientific_validation_images(session_id, sequence_number)`: unicidad contractual / destino FK; CONSTRAINT scientific_validation_images_session_id_sequence_number_key UNIQUE (session_id, sequence_number).
- `smear_analysis_summaries_classification_run_id_key` en `smear_analysis_summaries(classification_run_id)`: unicidad contractual / destino FK; CONSTRAINT smear_analysis_summaries_classification_run_id_key UNIQUE (classification_run_id).
- `uq_smear_slides_sample_code` en `smear_slides(sample_id, slide_code)`: unicidad contractual / destino FK; CONSTRAINT uq_smear_slides_sample_code UNIQUE (sample_id, slide_code).
- `train_execution_sessions_artifact_root_key` en `train_execution_sessions(artifact_root)`: unicidad contractual / destino FK; CONSTRAINT train_execution_sessions_artifact_root_key UNIQUE (artifact_root).
- `train_execution_sessions_attempt_id_key` en `train_execution_sessions(attempt_id)`: unicidad contractual / destino FK; CONSTRAINT train_execution_sessions_attempt_id_key UNIQUE (attempt_id).
- `users_email_key` en `users(email)`: unicidad contractual / destino FK; CONSTRAINT users_email_key UNIQUE (email).
- `users_username_key` en `users(username)`: unicidad contractual / destino FK; CONSTRAINT users_username_key UNIQUE (username).
- `uq_v2_epoch` en `training_history(run_id, phase, epoch)`: unicidad contractual / destino FK; CONSTRAINT uq_v2_epoch UNIQUE (run_id, phase, epoch).
- `uq_v2_evaluation_sample` en `predictions(evaluation_id, dataset_source_record_id)`: unicidad contractual / destino FK; CONSTRAINT uq_v2_evaluation_sample UNIQUE (evaluation_id, dataset_source_record_id).
- `v2_run_clinical_metrics_unique_f9437c271ff6` en `run_clinical_metrics(evaluation_id)`: unicidad contractual / destino FK; CONSTRAINT v2_run_clinical_metrics_unique_f9437c271ff6 UNIQUE (evaluation_id).
- `v2_run_configurations_primary_360aa242ca7c` en `run_configurations(run_id)`: identidad primaria.
- `v2_evaluations_primary_8c8464f42472` en `evaluations(id)`: identidad primaria.
- `v2_evaluations_unique_2b29f071653b` en `evaluations(run_id, source_kind, source_record_phase, source_record_key)`: unicidad contractual / destino FK; CONSTRAINT v2_evaluations_unique_2b29f071653b UNIQUE (run_id, source_kind, source_record_phase, source_record_key).
- `v2_evaluations_unique_927a8d4fe69d` en `evaluations(id, run_id)`: unicidad contractual / destino FK; CONSTRAINT v2_evaluations_unique_927a8d4fe69d UNIQUE (id, run_id).
- `v2_evaluation_ensemble_members_primary_0f6c3f155b09` en `evaluation_ensemble_members(evaluation_id, ordinal)`: identidad primaria.
- `v2_evaluation_ensemble_members_unique_3a2092158e31` en `evaluation_ensemble_members(evaluation_id, model_version_id)`: unicidad contractual / destino FK; CONSTRAINT v2_evaluation_ensemble_members_unique_3a2092158e31 UNIQUE (evaluation_id, model_version_id).
- `v2_xai_evidence_primary_8c8464f42472` en `xai_evidence(id)`: identidad primaria.
- `v2_xai_evidence_unique_d9477cb1fece` en `xai_evidence(ml_explanation_id)`: unicidad contractual / destino FK; CONSTRAINT v2_xai_evidence_unique_d9477cb1fece UNIQUE (ml_explanation_id).
- `v2_xai_evidence_unique_d4bf0f195fcf` en `xai_evidence(cell_explanation_id)`: unicidad contractual / destino FK; CONSTRAINT v2_xai_evidence_unique_d4bf0f195fcf UNIQUE (cell_explanation_id).
- `v2_xai_evidence_unique_0be310eeb2b7` en `xai_evidence(assessment_attempt_id, assessment_sample_id)`: unicidad contractual / destino FK; CONSTRAINT v2_xai_evidence_unique_0be310eeb2b7 UNIQUE (assessment_attempt_id, assessment_sample_id).
- `v2_xai_artifacts_primary_8c8464f42472` en `xai_artifacts(id)`: identidad primaria.
- `v2_xai_artifacts_unique_ee15a9513a9e` en `xai_artifacts(evidence_id, role, ordinal)`: unicidad contractual / destino FK; CONSTRAINT v2_xai_artifacts_unique_ee15a9513a9e UNIQUE (evidence_id, role, ordinal).
- `v2_xai_quantitative_evaluations_primary_8c8464f42472` en `xai_quantitative_evaluations(id)`: identidad primaria.
- `v2_xai_interpretations_primary_8c8464f42472` en `xai_interpretations(id)`: identidad primaria.
- `v2_xai_specialist_reviews_primary_8c8464f42472` en `xai_specialist_reviews(id)`: identidad primaria.
- `xai_method_configurations_pkey` en `xai_method_configurations(id)`: identidad primaria.
- `xai_region_attributions_pkey` en `xai_region_attributions(xai_evidence_id, region_type, region_index)`: identidad primaria.
- `xai_evaluation_protocols_pkey` en `xai_evaluation_protocols(id)`: identidad primaria.
- `xai_evaluation_members_pkey` en `xai_evaluation_members(evaluation_id, xai_evidence_id)`: identidad primaria.
- `uq_xai_method_configuration_hash` en `xai_method_configurations(configuration_hash)`: unicidad contractual / destino FK; CONSTRAINT uq_xai_method_configuration_hash UNIQUE (configuration_hash).
- `uq_xai_protocol_hash` en `xai_evaluation_protocols(protocol_hash)`: unicidad contractual / destino FK; CONSTRAINT uq_xai_protocol_hash UNIQUE (protocol_hash).
- `uq_xai_protocol_metric` en `xai_evaluation_protocols(id, metric_name)`: unicidad contractual / destino FK; CONSTRAINT uq_xai_protocol_metric UNIQUE (id, metric_name).

## Explícitos

### idx_artifacts_artifact_type

Acceso por artifact_type en artifacts.
```sql
CREATE INDEX idx_artifacts_artifact_type ON public.artifacts (artifact_type);
```

### idx_artifacts_checksum

Acceso por checksum en artifacts.
```sql
CREATE INDEX idx_artifacts_checksum ON public.artifacts (checksum);
```

### idx_artifacts_governance_status

Acceso por artifact_status en artifacts.
```sql
CREATE INDEX idx_artifacts_governance_status ON public.artifacts (artifact_status);
```

### idx_artifacts_metadata_source

Acceso por metadata ->> CAST('source' AS text) en artifacts.
```sql
CREATE INDEX idx_artifacts_metadata_source ON public.artifacts ((metadata ->> CAST('source' AS text)));
```

### idx_artifacts_run_id

Acceso por run_id en artifacts.
```sql
CREATE INDEX idx_artifacts_run_id ON public.artifacts (run_id);
```

### idx_artifacts_type_path

Acceso por artifact_type, path en artifacts.
```sql
CREATE INDEX idx_artifacts_type_path ON public.artifacts (artifact_type, path);
```

### idx_artifacts_uri

Acceso por artifact_uri en artifacts.
```sql
CREATE INDEX idx_artifacts_uri ON public.artifacts (artifact_uri) WHERE artifact_uri IS NOT NULL;
```

### idx_dataset_split_images_class

Acceso por class_name en dataset_split_images.
```sql
CREATE INDEX idx_dataset_split_images_class ON public.dataset_split_images (class_name);
```

### idx_dataset_split_images_dataset_dir

Acceso por dataset_dir en dataset_split_images.
```sql
CREATE INDEX idx_dataset_split_images_dataset_dir ON public.dataset_split_images (dataset_dir);
```

### idx_dataset_split_images_dataset_id

Acceso por dataset_id en dataset_split_images.
```sql
CREATE INDEX idx_dataset_split_images_dataset_id ON public.dataset_split_images (dataset_id);
```

### idx_dataset_split_images_relative_path

Acceso por relative_path en dataset_split_images.
```sql
CREATE INDEX idx_dataset_split_images_relative_path ON public.dataset_split_images (relative_path);
```

### idx_dataset_split_images_split

Acceso por split_name en dataset_split_images.
```sql
CREATE INDEX idx_dataset_split_images_split ON public.dataset_split_images (split_name);
```

### idx_datasets_metadata_gin

Acceso por metadata en datasets.
```sql
CREATE INDEX idx_datasets_metadata_gin ON public.datasets USING gin (metadata);
```

### idx_deployed_model_versions_checkpoint_artifact

Acceso por checkpoint_artifact_id en deployed_model_versions.
```sql
CREATE INDEX idx_deployed_model_versions_checkpoint_artifact ON public.deployed_model_versions (checkpoint_artifact_id);
```

### idx_deployed_model_versions_model_version

Acceso por model_version_id en deployed_model_versions.
```sql
CREATE INDEX idx_deployed_model_versions_model_version ON public.deployed_model_versions (model_version_id);
```

### idx_deployed_model_versions_slot_history

Acceso por deployment_name, environment, alias, created_at en deployed_model_versions.
```sql
CREATE INDEX idx_deployed_model_versions_slot_history ON public.deployed_model_versions (deployment_name, environment, alias, created_at DESC);
```

### idx_deployed_model_versions_status

Acceso por status, created_at en deployed_model_versions.
```sql
CREATE INDEX idx_deployed_model_versions_status ON public.deployed_model_versions (status, created_at DESC);
```

### idx_deployed_model_versions_threshold_calibration

Acceso por threshold_calibration_id en deployed_model_versions.
```sql
CREATE INDEX idx_deployed_model_versions_threshold_calibration ON public.deployed_model_versions (threshold_calibration_id) WHERE threshold_calibration_id IS NOT NULL;
```

### idx_environment_packages_run_id

Acceso por run_id en environment_packages.
```sql
CREATE INDEX idx_environment_packages_run_id ON public.environment_packages (run_id);
```

### idx_errors_run_id

Acceso por run_id en errors.
```sql
CREATE INDEX idx_errors_run_id ON public.errors (run_id);
```

### idx_execution_logs_run_id

Acceso por run_id en execution_logs.
```sql
CREATE INDEX idx_execution_logs_run_id ON public.execution_logs (run_id);
```

### idx_explainability_case_method

Acceso por case_type, method en explainability_results.
```sql
CREATE INDEX idx_explainability_case_method ON public.explainability_results (case_type, method);
```

### idx_explainability_method

Acceso por method en explainability_results.
```sql
CREATE INDEX idx_explainability_method ON public.explainability_results (method);
```

### idx_explainability_output_path

Acceso por output_path en explainability_results.
```sql
CREATE INDEX idx_explainability_output_path ON public.explainability_results (output_path);
```

### idx_explainability_run_id

Acceso por run_id en explainability_results.
```sql
CREATE INDEX idx_explainability_run_id ON public.explainability_results (run_id);
```

### idx_explainability_success

Acceso por success en explainability_results.
```sql
CREATE INDEX idx_explainability_success ON public.explainability_results (success);
```

### idx_image_analysis_jobs_deployment

Acceso por deployed_model_version_id en image_analysis_jobs.
```sql
CREATE INDEX idx_image_analysis_jobs_deployment ON public.image_analysis_jobs (deployed_model_version_id);
```

### idx_image_analysis_jobs_input_artifact

Acceso por input_artifact_id en image_analysis_jobs.
```sql
CREATE INDEX idx_image_analysis_jobs_input_artifact ON public.image_analysis_jobs (input_artifact_id) WHERE input_artifact_id IS NOT NULL;
```

### idx_image_analysis_jobs_model_version

Acceso por model_version_id en image_analysis_jobs.
```sql
CREATE INDEX idx_image_analysis_jobs_model_version ON public.image_analysis_jobs (model_version_id);
```

### idx_image_analysis_jobs_run

Acceso por inference_run_id en image_analysis_jobs.
```sql
CREATE INDEX idx_image_analysis_jobs_run ON public.image_analysis_jobs (inference_run_id);
```

### idx_image_analysis_jobs_source_image

Acceso por source_image_id en image_analysis_jobs.
```sql
CREATE INDEX idx_image_analysis_jobs_source_image ON public.image_analysis_jobs (source_image_id) WHERE source_image_id IS NOT NULL;
```

### idx_image_analysis_jobs_status_created

Acceso por status, created_at en image_analysis_jobs.
```sql
CREATE INDEX idx_image_analysis_jobs_status_created ON public.image_analysis_jobs (status, created_at DESC);
```

### idx_model_versions_checkpoint_artifact

Acceso por checkpoint_artifact_id en model_versions.
```sql
CREATE INDEX idx_model_versions_checkpoint_artifact ON public.model_versions (checkpoint_artifact_id);
```

### idx_model_versions_model

Acceso por model_id en model_versions.
```sql
CREATE INDEX idx_model_versions_model ON public.model_versions (model_id);
```

### idx_model_versions_sha256

Acceso por artifact_sha256 en model_versions.
```sql
CREATE INDEX idx_model_versions_sha256 ON public.model_versions (artifact_sha256);
```

### idx_model_versions_status_lineage

Acceso por status, lineage_status en model_versions.
```sql
CREATE INDEX idx_model_versions_status_lineage ON public.model_versions (status, lineage_status);
```

### idx_model_versions_training_run

Acceso por training_run_id en model_versions.
```sql
CREATE INDEX idx_model_versions_training_run ON public.model_versions (training_run_id);
```

### idx_predictions_analysis_job

Acceso por image_analysis_job_id en predictions.
```sql
CREATE INDEX idx_predictions_analysis_job ON public.predictions (image_analysis_job_id);
```

### idx_predictions_case_type

Acceso por case_type en predictions.
```sql
CREATE INDEX idx_predictions_case_type ON public.predictions (case_type);
```

### idx_predictions_case_type_run

Acceso por case_type, run_id en predictions.
```sql
CREATE INDEX idx_predictions_case_type_run ON public.predictions (case_type, run_id);
```

### idx_predictions_classifier_model_version

Acceso por classifier_model_version_id en predictions.
```sql
CREATE INDEX idx_predictions_classifier_model_version ON public.predictions (classifier_model_version_id);
```

### idx_predictions_created_at

Acceso por created_at en predictions.
```sql
CREATE INDEX idx_predictions_created_at ON public.predictions (created_at);
```

### idx_predictions_deployed_model_version

Acceso por deployed_model_version_id en predictions.
```sql
CREATE INDEX idx_predictions_deployed_model_version ON public.predictions (deployed_model_version_id);
```

### idx_predictions_detector_model_version

Acceso por detector_model_version_id en predictions.
```sql
CREATE INDEX idx_predictions_detector_model_version ON public.predictions (detector_model_version_id) WHERE detector_model_version_id IS NOT NULL;
```

### idx_predictions_inference_run

Acceso por inference_run_id en predictions.
```sql
CREATE INDEX idx_predictions_inference_run ON public.predictions (inference_run_id);
```

### idx_predictions_metadata_source

Acceso por metadata ->> CAST('source' AS text) en predictions.
```sql
CREATE INDEX idx_predictions_metadata_source ON public.predictions ((metadata ->> CAST('source' AS text)));
```

### idx_predictions_metadata_workflow

Acceso por metadata ->> CAST('workflow' AS text) en predictions.
```sql
CREATE INDEX idx_predictions_metadata_workflow ON public.predictions ((metadata ->> CAST('workflow' AS text)));
```

### idx_predictions_model_version

Acceso por model_version_id en predictions.
```sql
CREATE INDEX idx_predictions_model_version ON public.predictions (model_version_id);
```

### idx_predictions_predicted_label

Acceso por predicted_label en predictions.
```sql
CREATE INDEX idx_predictions_predicted_label ON public.predictions (predicted_label);
```

### idx_predictions_review_status

Acceso por review_status, created_at en predictions.
```sql
CREATE INDEX idx_predictions_review_status ON public.predictions (review_status, created_at DESC);
```

### idx_predictions_run_id

Acceso por run_id en predictions.
```sql
CREATE INDEX idx_predictions_run_id ON public.predictions (run_id);
```

### idx_predictions_true_pred

Acceso por true_label, predicted_label en predictions.
```sql
CREATE INDEX idx_predictions_true_pred ON public.predictions (true_label, predicted_label);
```

### idx_run_checkpoint_policy_artifact

Acceso por checkpoint_artifact_id en run_checkpoint_policy.
```sql
CREATE INDEX idx_run_checkpoint_policy_artifact ON public.run_checkpoint_policy (checkpoint_artifact_id);
```

### idx_run_checkpoint_policy_model_version

Acceso por model_version_id en run_checkpoint_policy.
```sql
CREATE INDEX idx_run_checkpoint_policy_model_version ON public.run_checkpoint_policy (model_version_id);
```

### idx_run_checkpoint_policy_run_id

Acceso por run_id en run_checkpoint_policy.
```sql
CREATE INDEX idx_run_checkpoint_policy_run_id ON public.run_checkpoint_policy (run_id);
```

### idx_run_clinical_metrics_model_name

Acceso por model_name en run_clinical_metrics.
```sql
CREATE INDEX idx_run_clinical_metrics_model_name ON public.run_clinical_metrics (model_name);
```

### idx_run_clinical_metrics_run_id

Acceso por run_id en run_clinical_metrics.
```sql
CREATE INDEX idx_run_clinical_metrics_run_id ON public.run_clinical_metrics (run_id);
```

### idx_run_clinical_metrics_split_name

Acceso por split_name en run_clinical_metrics.
```sql
CREATE INDEX idx_run_clinical_metrics_split_name ON public.run_clinical_metrics (split_name);
```

### idx_run_dataset_images_image_id

Acceso por image_id en run_dataset_images.
```sql
CREATE INDEX idx_run_dataset_images_image_id ON public.run_dataset_images (image_id);
```

### idx_run_dataset_images_run_id

Acceso por run_id en run_dataset_images.
```sql
CREATE INDEX idx_run_dataset_images_run_id ON public.run_dataset_images (run_id);
```

### idx_run_dataset_images_split

Acceso por split_name en run_dataset_images.
```sql
CREATE INDEX idx_run_dataset_images_split ON public.run_dataset_images (split_name);
```

### idx_run_dataset_images_usage_context

Acceso por usage_context en run_dataset_images.
```sql
CREATE INDEX idx_run_dataset_images_usage_context ON public.run_dataset_images (usage_context);
```

### idx_run_image_predictions_case_type

Acceso por case_type en run_image_predictions.
```sql
CREATE INDEX idx_run_image_predictions_case_type ON public.run_image_predictions (case_type);
```

### idx_run_image_predictions_run_id

Acceso por run_id en run_image_predictions.
```sql
CREATE INDEX idx_run_image_predictions_run_id ON public.run_image_predictions (run_id);
```

### idx_run_image_predictions_split

Acceso por split_name en run_image_predictions.
```sql
CREATE INDEX idx_run_image_predictions_split ON public.run_image_predictions (split_name);
```

### idx_run_io_records_clinical_metadata_gin

Acceso por clinical_metadata en run_io_records.
```sql
CREATE INDEX idx_run_io_records_clinical_metadata_gin ON public.run_io_records USING gin (clinical_metadata);
```

### idx_run_io_records_created_at

Acceso por created_at en run_io_records.
```sql
CREATE INDEX idx_run_io_records_created_at ON public.run_io_records (created_at);
```

### idx_run_io_records_model_metadata_gin

Acceso por model_metadata en run_io_records.
```sql
CREATE INDEX idx_run_io_records_model_metadata_gin ON public.run_io_records USING gin (model_metadata);
```

### idx_run_io_records_model_name

Acceso por model_name en run_io_records.
```sql
CREATE INDEX idx_run_io_records_model_name ON public.run_io_records (model_name);
```

### idx_run_io_records_run_id

Acceso por run_id en run_io_records.
```sql
CREATE INDEX idx_run_io_records_run_id ON public.run_io_records (run_id);
```

### idx_run_io_records_run_type

Acceso por run_type en run_io_records.
```sql
CREATE INDEX idx_run_io_records_run_type ON public.run_io_records (run_type);
```

### idx_run_io_records_script_name

Acceso por script_name en run_io_records.
```sql
CREATE INDEX idx_run_io_records_script_name ON public.run_io_records (script_name);
```

### idx_run_lineage_checkpoint_artifact

Acceso por checkpoint_artifact_id en run_lineage.
```sql
CREATE INDEX idx_run_lineage_checkpoint_artifact ON public.run_lineage (checkpoint_artifact_id);
```

### idx_run_lineage_checkpoint_path

Acceso por checkpoint_path en run_lineage.
```sql
CREATE INDEX idx_run_lineage_checkpoint_path ON public.run_lineage (checkpoint_path);
```

### idx_run_lineage_child_run_id

Acceso por child_run_id en run_lineage.
```sql
CREATE INDEX idx_run_lineage_child_run_id ON public.run_lineage (child_run_id);
```

### idx_run_lineage_model_version

Acceso por model_version_id en run_lineage.
```sql
CREATE INDEX idx_run_lineage_model_version ON public.run_lineage (model_version_id);
```

### idx_run_lineage_parent_run_id

Acceso por parent_run_id en run_lineage.
```sql
CREATE INDEX idx_run_lineage_parent_run_id ON public.run_lineage (parent_run_id);
```

### idx_run_lineage_relationship_type

Acceso por relationship_type en run_lineage.
```sql
CREATE INDEX idx_run_lineage_relationship_type ON public.run_lineage (relationship_type);
```

### idx_run_metrics_name

Acceso por metric_name en run_metrics.
```sql
CREATE INDEX idx_run_metrics_name ON public.run_metrics (metric_name);
```

### idx_run_metrics_run_id

Acceso por run_id en run_metrics.
```sql
CREATE INDEX idx_run_metrics_run_id ON public.run_metrics (run_id);
```

### idx_run_model_deployments_deployment

Acceso por deployed_model_version_id en run_model_deployments.
```sql
CREATE INDEX idx_run_model_deployments_deployment ON public.run_model_deployments (deployed_model_version_id);
```

### idx_run_model_deployments_model_version

Acceso por model_version_id en run_model_deployments.
```sql
CREATE INDEX idx_run_model_deployments_model_version ON public.run_model_deployments (model_version_id);
```

### idx_run_threshold_calibration_artifact

Acceso por calibration_artifact_id en run_threshold_calibration.
```sql
CREATE INDEX idx_run_threshold_calibration_artifact ON public.run_threshold_calibration (calibration_artifact_id);
```

### idx_run_threshold_calibration_model_version

Acceso por model_version_id en run_threshold_calibration.
```sql
CREATE INDEX idx_run_threshold_calibration_model_version ON public.run_threshold_calibration (model_version_id);
```

### idx_run_threshold_calibration_run_id

Acceso por run_id en run_threshold_calibration.
```sql
CREATE INDEX idx_run_threshold_calibration_run_id ON public.run_threshold_calibration (run_id);
```

### idx_runs_dataset_id

Acceso por dataset_id en runs.
```sql
CREATE INDEX idx_runs_dataset_id ON public.runs (dataset_id);
```

### idx_runs_execution_parameters_gin

Acceso por execution_parameters en runs.
```sql
CREATE INDEX idx_runs_execution_parameters_gin ON public.runs USING gin (execution_parameters);
```

### idx_runs_execution_type

Acceso por execution_type en runs.
```sql
CREATE INDEX idx_runs_execution_type ON public.runs (execution_type);
```

### idx_runs_inference_script

Acceso por run_type, script_name en runs.
```sql
CREATE INDEX idx_runs_inference_script ON public.runs (run_type, script_name);
```

### idx_runs_metadata_gin

Acceso por metadata en runs.
```sql
CREATE INDEX idx_runs_metadata_gin ON public.runs USING gin (metadata);
```

### idx_runs_model_id

Acceso por model_id en runs.
```sql
CREATE INDEX idx_runs_model_id ON public.runs (model_id);
```

### idx_runs_parameters_gin

Acceso por parameters en runs.
```sql
CREATE INDEX idx_runs_parameters_gin ON public.runs USING gin (parameters);
```

### idx_runs_run_type

Acceso por run_type en runs.
```sql
CREATE INDEX idx_runs_run_type ON public.runs (run_type);
```

### idx_runs_started_at

Acceso por started_at en runs.
```sql
CREATE INDEX idx_runs_started_at ON public.runs (started_at);
```

### idx_runs_status

Acceso por status en runs.
```sql
CREATE INDEX idx_runs_status ON public.runs (status);
```

### idx_runs_training_release_status

Acceso por release_status en runs.
```sql
CREATE INDEX idx_runs_training_release_status ON public.runs (release_status) WHERE run_type = CAST('training' AS text);
```

### idx_stage2_publication_candidates

Acceso por datasource, scope, is_active, published_at en stage2_model_publications.
```sql
CREATE INDEX idx_stage2_publication_candidates ON public.stage2_model_publications (datasource, scope, is_active, published_at DESC);
```

### idx_stage2_publication_events_publication

Acceso por publication_id, event_at en stage2_model_publication_events.
```sql
CREATE INDEX idx_stage2_publication_events_publication ON public.stage2_model_publication_events (publication_id, event_at);
```

### idx_training_history_run_id

Acceso por run_id en training_history.
```sql
CREATE INDEX idx_training_history_run_id ON public.training_history (run_id);
```

### ix_audit_events_actor

Acceso por actor_user_id, created_at en audit_events.
```sql
CREATE INDEX ix_audit_events_actor ON public.audit_events (actor_user_id, created_at);
```

### ix_audit_events_created_at

Acceso por created_at en audit_events.
```sql
CREATE INDEX ix_audit_events_created_at ON public.audit_events (created_at);
```

### ix_audit_events_resource

Acceso por resource_type, resource_id, created_at en audit_events.
```sql
CREATE INDEX ix_audit_events_resource ON public.audit_events (resource_type, resource_id, created_at);
```

### ix_blood_samples_case

Acceso por case_id en blood_samples.
```sql
CREATE INDEX ix_blood_samples_case ON public.blood_samples (case_id);
```

### ix_blood_samples_status_created

Acceso por status, created_at en blood_samples.
```sql
CREATE INDEX ix_blood_samples_status_created ON public.blood_samples (status, created_at DESC);
```

### ix_campaign_attempt_state

Acceso por state en campaign_attempts.
```sql
CREATE INDEX ix_campaign_attempt_state ON public.campaign_attempts (state);
```

### ix_campaign_dataset_state

Acceso por dataset_version_id, state en experimental_campaigns.
```sql
CREATE INDEX ix_campaign_dataset_state ON public.experimental_campaigns (dataset_version_id, state);
```

### ix_campaign_member_state

Acceso por campaign_id, state en campaign_members.
```sql
CREATE INDEX ix_campaign_member_state ON public.campaign_members (campaign_id, state);
```

### ix_cell_classification_events_run_created

Acceso por classification_run_id, created_at, id en cell_classification_events.
```sql
CREATE INDEX ix_cell_classification_events_run_created ON public.cell_classification_events (classification_run_id, created_at, id);
```

### ix_cell_classification_events_run_detection

Acceso por classification_run_id, cell_detection_id, created_at, id en cell_classification_events.
```sql
CREATE INDEX ix_cell_classification_events_run_detection ON public.cell_classification_events (classification_run_id, cell_detection_id, created_at, id);
```

### ix_cell_classification_events_run_prediction

Acceso por classification_run_id, cell_prediction_id, created_at, id en cell_classification_events.
```sql
CREATE INDEX ix_cell_classification_events_run_prediction ON public.cell_classification_events (classification_run_id, cell_prediction_id, created_at, id);
```

### ix_cell_classification_inputs_crop

Acceso por crop_id en cell_classification_inputs.
```sql
CREATE INDEX ix_cell_classification_inputs_crop ON public.cell_classification_inputs (crop_id) WHERE crop_id IS NOT NULL;
```

### ix_cell_classification_inputs_detection

Acceso por cell_detection_id en cell_classification_inputs.
```sql
CREATE INDEX ix_cell_classification_inputs_detection ON public.cell_classification_inputs (cell_detection_id);
```

### ix_cell_classification_inputs_run_eligible_order

Acceso por classification_run_id, eligible, input_order en cell_classification_inputs.
```sql
CREATE INDEX ix_cell_classification_inputs_run_eligible_order ON public.cell_classification_inputs (classification_run_id, eligible, input_order);
```

### ix_cell_classification_inputs_run_image_cell

Acceso por classification_run_id, image_sequence_number, cell_index, id en cell_classification_inputs.
```sql
CREATE INDEX ix_cell_classification_inputs_run_image_cell ON public.cell_classification_inputs (classification_run_id, image_sequence_number, cell_index, id);
```

### ix_cell_classification_reviews_actor_created

Acceso por actor_user_id, created_at, id en cell_classification_reviews.
```sql
CREATE INDEX ix_cell_classification_reviews_actor_created ON public.cell_classification_reviews (actor_user_id, created_at DESC, id DESC);
```

### ix_cell_classification_reviews_prediction_created

Acceso por cell_prediction_id, created_at, id en cell_classification_reviews.
```sql
CREATE INDEX ix_cell_classification_reviews_prediction_created ON public.cell_classification_reviews (cell_prediction_id, created_at, id);
```

### ix_cell_classification_runs_analysis_created

Acceso por analysis_run_id, created_at, id en cell_classification_runs.
```sql
CREATE INDEX ix_cell_classification_runs_analysis_created ON public.cell_classification_runs (analysis_run_id, created_at DESC, id DESC);
```

### ix_cell_classification_runs_detection_created

Acceso por detection_run_id, created_at, id en cell_classification_runs.
```sql
CREATE INDEX ix_cell_classification_runs_detection_created ON public.cell_classification_runs (detection_run_id, created_at DESC, id DESC);
```

### ix_cell_classification_runs_model_created

Acceso por production_model_id, created_at, id en cell_classification_runs.
```sql
CREATE INDEX ix_cell_classification_runs_model_created ON public.cell_classification_runs (production_model_id, created_at DESC, id DESC);
```

### ix_cell_classification_runs_status_created

Acceso por status, created_at, id en cell_classification_runs.
```sql
CREATE INDEX ix_cell_classification_runs_status_created ON public.cell_classification_runs (status, created_at DESC, id DESC);
```

### ix_cell_detection_events_run_created

Acceso por detection_run_id, created_at, id en cell_detection_events.
```sql
CREATE INDEX ix_cell_detection_events_run_created ON public.cell_detection_events (detection_run_id, created_at, id);
```

### ix_cell_detection_events_run_image

Acceso por detection_run_id, microscopy_image_id, created_at, id en cell_detection_events.
```sql
CREATE INDEX ix_cell_detection_events_run_image ON public.cell_detection_events (detection_run_id, microscopy_image_id, created_at, id);
```

### ix_cell_detection_runs_analysis_created

Acceso por analysis_run_id, created_at, id en cell_detection_runs.
```sql
CREATE INDEX ix_cell_detection_runs_analysis_created ON public.cell_detection_runs (analysis_run_id, created_at DESC, id DESC);
```

### ix_cell_detection_runs_status_created

Acceso por status, created_at, id en cell_detection_runs.
```sql
CREATE INDEX ix_cell_detection_runs_status_created ON public.cell_detection_runs (status, created_at DESC, id DESC);
```

### ix_cell_detections_run_image

Acceso por detection_run_id, microscopy_image_id, cell_index en cell_detections.
```sql
CREATE INDEX ix_cell_detections_run_image ON public.cell_detections (detection_run_id, microscopy_image_id, cell_index);
```

### ix_cell_explanations_status_created

Acceso por status, created_at, id en cell_explanations.
```sql
CREATE INDEX ix_cell_explanations_status_created ON public.cell_explanations (status, created_at DESC, id DESC);
```

### ix_cell_predictions_crop

Acceso por crop_id en cell_predictions.
```sql
CREATE INDEX ix_cell_predictions_crop ON public.cell_predictions (crop_id);
```

### ix_cell_predictions_detection

Acceso por cell_detection_id en cell_predictions.
```sql
CREATE INDEX ix_cell_predictions_detection ON public.cell_predictions (cell_detection_id);
```

### ix_cell_predictions_run_label

Acceso por classification_run_id, predicted_label, created_at, id en cell_predictions.
```sql
CREATE INDEX ix_cell_predictions_run_label ON public.cell_predictions (classification_run_id, predicted_label, created_at, id) WHERE CAST(prediction_status AS text) = CAST('completed' AS text);
```

### ix_cell_predictions_run_near_threshold

Acceso por classification_run_id, near_threshold, created_at, id en cell_predictions.
```sql
CREATE INDEX ix_cell_predictions_run_near_threshold ON public.cell_predictions (classification_run_id, near_threshold, created_at, id);
```

### ix_cell_predictions_run_status

Acceso por classification_run_id, prediction_status, created_at, id en cell_predictions.
```sql
CREATE INDEX ix_cell_predictions_run_status ON public.cell_predictions (classification_run_id, prediction_status, created_at, id);
```

### ix_dataset_materialization_activations_dataset_version_id

Acceso por dataset_version_id en dataset_materialization_activations.
```sql
CREATE INDEX ix_dataset_materialization_activations_dataset_version_id ON public.dataset_materialization_activations (dataset_version_id);
```

### ix_dataset_materialization_activations_materialization_id

Acceso por materialization_id en dataset_materialization_activations.
```sql
CREATE INDEX ix_dataset_materialization_activations_materialization_id ON public.dataset_materialization_activations (materialization_id);
```

### ix_dataset_materializations_dataset_version_id

Acceso por dataset_version_id en dataset_materializations.
```sql
CREATE INDEX ix_dataset_materializations_dataset_version_id ON public.dataset_materializations (dataset_version_id);
```

### ix_dataset_source_records_clinical_identity_id

Acceso por clinical_identity_id en dataset_source_records.
```sql
CREATE INDEX ix_dataset_source_records_clinical_identity_id ON public.dataset_source_records (clinical_identity_id);
```

### ix_dataset_source_records_dataset_id

Acceso por dataset_id en dataset_source_records.
```sql
CREATE INDEX ix_dataset_source_records_dataset_id ON public.dataset_source_records (dataset_id);
```

### ix_dataset_source_records_decoded_pixel_sha256

Acceso por decoded_pixel_sha256 en dataset_source_records.
```sql
CREATE INDEX ix_dataset_source_records_decoded_pixel_sha256 ON public.dataset_source_records (decoded_pixel_sha256) WHERE decoded_pixel_sha256 IS NOT NULL;
```

### ix_dataset_source_records_source_file_sha256

Acceso por source_file_sha256 en dataset_source_records.
```sql
CREATE INDEX ix_dataset_source_records_source_file_sha256 ON public.dataset_source_records (source_file_sha256) WHERE source_file_sha256 IS NOT NULL;
```

### ix_dataset_split_assignments_clinical_identity_id

Acceso por clinical_identity_id en dataset_split_assignments.
```sql
CREATE INDEX ix_dataset_split_assignments_clinical_identity_id ON public.dataset_split_assignments (clinical_identity_id);
```

### ix_dataset_split_assignments_dataset_version_id

Acceso por dataset_version_id en dataset_split_assignments.
```sql
CREATE INDEX ix_dataset_split_assignments_dataset_version_id ON public.dataset_split_assignments (dataset_version_id);
```

### ix_dataset_split_images_dataset_materialization_id

Acceso por dataset_materialization_id en dataset_split_images.
```sql
CREATE INDEX ix_dataset_split_images_dataset_materialization_id ON public.dataset_split_images (dataset_materialization_id);
```

### ix_dataset_split_images_dataset_version_id

Acceso por dataset_version_id en dataset_split_images.
```sql
CREATE INDEX ix_dataset_split_images_dataset_version_id ON public.dataset_split_images (dataset_version_id);
```

### ix_dataset_split_statistics_version_metric

Acceso por dataset_version_id, scope, metric_name en dataset_split_statistics.
```sql
CREATE INDEX ix_dataset_split_statistics_version_metric ON public.dataset_split_statistics (dataset_version_id, scope, metric_name);
```

### ix_dataset_split_validation_checks_version_name

Acceso por dataset_version_id, check_name, executed_at en dataset_split_validation_checks.
```sql
CREATE INDEX ix_dataset_split_validation_checks_version_name ON public.dataset_split_validation_checks (dataset_version_id, check_name, executed_at);
```

### ix_dataset_version_sources_dataset_id

Acceso por dataset_id en dataset_version_sources.
```sql
CREATE INDEX ix_dataset_version_sources_dataset_id ON public.dataset_version_sources (dataset_id);
```

### ix_dataset_versions_status

Acceso por status en dataset_versions.
```sql
CREATE INDEX ix_dataset_versions_status ON public.dataset_versions (status);
```

### ix_evaluation_comparison

Acceso por dataset_version_id, comparison_contract_hash, split, created_at, id en evaluations.
```sql
CREATE INDEX ix_evaluation_comparison ON public.evaluations (dataset_version_id, comparison_contract_hash, split, created_at, id);
```

### ix_identity_evidence_clinical_identity_id

Acceso por clinical_identity_id en identity_evidence.
```sql
CREATE INDEX ix_identity_evidence_clinical_identity_id ON public.identity_evidence (clinical_identity_id);
```

### ix_identity_evidence_source_record_id

Acceso por source_record_id en identity_evidence.
```sql
CREATE INDEX ix_identity_evidence_source_record_id ON public.identity_evidence (source_record_id);
```

### ix_image_connected_components_run_image

Acceso por detection_run_id, microscopy_image_id, component_index en image_connected_components.
```sql
CREATE INDEX ix_image_connected_components_run_image ON public.image_connected_components (detection_run_id, microscopy_image_id, component_index);
```

### ix_image_connected_components_status

Acceso por detection_run_id, component_status, component_index en image_connected_components.
```sql
CREATE INDEX ix_image_connected_components_status ON public.image_connected_components (detection_run_id, component_status, component_index);
```

### ix_ingestion_batches_sample

Acceso por sample_id, created_at en image_ingestion_batches.
```sql
CREATE INDEX ix_ingestion_batches_sample ON public.image_ingestion_batches (sample_id, created_at DESC);
```

### ix_microscopy_analysis_events_run

Acceso por analysis_run_id, created_at, id en microscopy_analysis_events.
```sql
CREATE INDEX ix_microscopy_analysis_events_run ON public.microscopy_analysis_events (analysis_run_id, created_at, id);
```

### ix_microscopy_analysis_runs_status

Acceso por run_status, created_at en microscopy_analysis_runs.
```sql
CREATE INDEX ix_microscopy_analysis_runs_status ON public.microscopy_analysis_runs (run_status, created_at DESC);
```

### ix_microscopy_analysis_runs_subject

Acceso por subject_id, created_at en microscopy_analysis_runs.
```sql
CREATE INDEX ix_microscopy_analysis_runs_subject ON public.microscopy_analysis_runs (subject_id, created_at DESC);
```

### ix_microscopy_images_ingestion_batch

Acceso por ingestion_batch_id en microscopy_images.
```sql
CREATE INDEX ix_microscopy_images_ingestion_batch ON public.microscopy_images (ingestion_batch_id);
```

### ix_microscopy_images_sha256

Acceso por sha256 en microscopy_images.
```sql
CREATE INDEX ix_microscopy_images_sha256 ON public.microscopy_images (sha256);
```

### ix_microscopy_images_slide

Acceso por slide_id en microscopy_images.
```sql
CREATE INDEX ix_microscopy_images_slide ON public.microscopy_images (slide_id);
```

### ix_microscopy_images_status_created

Acceso por status, created_at en microscopy_images.
```sql
CREATE INDEX ix_microscopy_images_status_created ON public.microscopy_images (status, created_at DESC);
```

### ix_quality_gate_decisions_run

Acceso por analysis_run_id, created_at, id en quality_gate_decisions.
```sql
CREATE INDEX ix_quality_gate_decisions_run ON public.quality_gate_decisions (analysis_run_id, created_at, id);
```

### ix_quality_queue_order

Acceso por status, priority, requested_at en quality_assessment_queue_items.
```sql
CREATE INDEX ix_quality_queue_order ON public.quality_assessment_queue_items (status, priority DESC, requested_at);
```

### ix_quality_queue_priority_requested

Acceso por priority, requested_at en quality_assessment_queue_items.
```sql
CREATE INDEX ix_quality_queue_priority_requested ON public.quality_assessment_queue_items (priority DESC, requested_at);
```

### ix_research_subjects_status_created

Acceso por status, created_at en research_subjects.
```sql
CREATE INDEX ix_research_subjects_status_created ON public.research_subjects (status, created_at DESC);
```

### ix_run_io_records_dataset_materialization_id

Acceso por dataset_materialization_id en run_io_records.
```sql
CREATE INDEX ix_run_io_records_dataset_materialization_id ON public.run_io_records (dataset_materialization_id);
```

### ix_run_io_records_dataset_version_id

Acceso por dataset_version_id en run_io_records.
```sql
CREATE INDEX ix_run_io_records_dataset_version_id ON public.run_io_records (dataset_version_id);
```

### ix_runs_dataset_version_id

Acceso por dataset_version_id en runs.
```sql
CREATE INDEX ix_runs_dataset_version_id ON public.runs (dataset_version_id);
```

### ix_scientific_cases_status_created

Acceso por status, created_at en scientific_cases.
```sql
CREATE INDEX ix_scientific_cases_status_created ON public.scientific_cases (status, created_at DESC);
```

### ix_scientific_cases_subject

Acceso por subject_id en scientific_cases.
```sql
CREATE INDEX ix_scientific_cases_subject ON public.scientific_cases (subject_id);
```

### ix_scientific_reviews_actor_created

Acceso por actor_user_id, created_at, id en scientific_reviews.
```sql
CREATE INDEX ix_scientific_reviews_actor_created ON public.scientific_reviews (actor_user_id, created_at DESC, id DESC);
```

### ix_scientific_reviews_entity_created

Acceso por entity_type, entity_id, created_at, id en scientific_reviews.
```sql
CREATE INDEX ix_scientific_reviews_entity_created ON public.scientific_reviews (entity_type, entity_id, created_at, id);
```

### ix_smear_analysis_summaries_analysis_created

Acceso por analysis_run_id, created_at, id en smear_analysis_summaries.
```sql
CREATE INDEX ix_smear_analysis_summaries_analysis_created ON public.smear_analysis_summaries (analysis_run_id, created_at DESC, id DESC);
```

### ix_smear_analysis_summaries_detection_created

Acceso por detection_run_id, created_at, id en smear_analysis_summaries.
```sql
CREATE INDEX ix_smear_analysis_summaries_detection_created ON public.smear_analysis_summaries (detection_run_id, created_at DESC, id DESC);
```

### ix_smear_analysis_summaries_outcome_created

Acceso por outcome, created_at, id en smear_analysis_summaries.
```sql
CREATE INDEX ix_smear_analysis_summaries_outcome_created ON public.smear_analysis_summaries (outcome, created_at DESC, id DESC);
```

### ix_smear_slides_sample

Acceso por sample_id en smear_slides.
```sql
CREATE INDEX ix_smear_slides_sample ON public.smear_slides (sample_id);
```

### ix_smear_slides_status_created

Acceso por status, created_at en smear_slides.
```sql
CREATE INDEX ix_smear_slides_status_created ON public.smear_slides (status, created_at DESC);
```

### ix_validation_annotation_events_actor_created

Acceso por actor_user_id, created_at, id en scientific_validation_annotation_events.
```sql
CREATE INDEX ix_validation_annotation_events_actor_created ON public.scientific_validation_annotation_events (actor_user_id, created_at DESC, id DESC);
```

### ix_validation_annotation_events_annotation_created

Acceso por annotation_id, created_at, id en scientific_validation_annotation_events.
```sql
CREATE INDEX ix_validation_annotation_events_annotation_created ON public.scientific_validation_annotation_events (annotation_id, created_at, id);
```

### ix_validation_annotations_general_target

Acceso por target_type, cell_detection_id, sample_id, created_at, id en scientific_validation_annotations.
```sql
CREATE INDEX ix_validation_annotations_general_target ON public.scientific_validation_annotations (target_type, cell_detection_id, sample_id, created_at, id) WHERE validation_session_id IS NULL;
```

### ix_validation_annotations_session_analysis

Acceso por validation_session_id, analysis_run_id, created_at, id en scientific_validation_annotations.
```sql
CREATE INDEX ix_validation_annotations_session_analysis ON public.scientific_validation_annotations (validation_session_id, analysis_run_id, created_at, id) WHERE CAST(target_type AS text) = CAST('analysis' AS text);
```

### ix_validation_annotations_session_category

Acceso por validation_session_id, category, created_at, id en scientific_validation_annotations.
```sql
CREATE INDEX ix_validation_annotations_session_category ON public.scientific_validation_annotations (validation_session_id, category, created_at, id);
```

### ix_validation_annotations_session_cell

Acceso por validation_session_id, cell_detection_id, created_at, id en scientific_validation_annotations.
```sql
CREATE INDEX ix_validation_annotations_session_cell ON public.scientific_validation_annotations (validation_session_id, cell_detection_id, created_at, id) WHERE CAST(target_type AS text) = CAST('cell' AS text);
```

### ix_validation_annotations_session_created

Acceso por validation_session_id, created_at, id en scientific_validation_annotations.
```sql
CREATE INDEX ix_validation_annotations_session_created ON public.scientific_validation_annotations (validation_session_id, created_at, id);
```

### ix_validation_annotations_session_sample

Acceso por validation_session_id, sample_id, created_at, id en scientific_validation_annotations.
```sql
CREATE INDEX ix_validation_annotations_session_sample ON public.scientific_validation_annotations (validation_session_id, sample_id, created_at, id) WHERE CAST(target_type AS text) = CAST('sample' AS text);
```

### ix_validation_sessions_creator_created

Acceso por created_by, created_at, id en scientific_validation_sessions.
```sql
CREATE INDEX ix_validation_sessions_creator_created ON public.scientific_validation_sessions (created_by, created_at DESC, id DESC);
```

### ix_validation_sessions_status_created

Acceso por status, created_at, id en scientific_validation_sessions.
```sql
CREATE INDEX ix_validation_sessions_status_created ON public.scientific_validation_sessions (status, created_at DESC, id DESC);
```

### ix_xai_evaluation

Acceso por evaluation_id, method_configuration_id en xai_evidence.
```sql
CREATE INDEX ix_xai_evaluation ON public.xai_evidence (evaluation_id, method_configuration_id);
```

### ix_xai_member_evidence

Acceso por xai_evidence_id, evaluation_id en xai_evaluation_members.
```sql
CREATE INDEX ix_xai_member_evidence ON public.xai_evaluation_members (xai_evidence_id, evaluation_id);
```

### ix_xai_method_configuration

Acceso por method_configuration_id en xai_evidence.
```sql
CREATE INDEX ix_xai_method_configuration ON public.xai_evidence (method_configuration_id);
```

### ix_xai_metric_protocol

Acceso por protocol_id, metric_name, evaluated_at en xai_quantitative_evaluations.
```sql
CREATE INDEX ix_xai_metric_protocol ON public.xai_quantitative_evaluations (protocol_id, metric_name, evaluated_at);
```

### ix_xai_reference_annotation

Acceso por reference_annotation_id en xai_quantitative_evaluations.
```sql
CREATE INDEX ix_xai_reference_annotation ON public.xai_quantitative_evaluations (reference_annotation_id);
```

### ix_xai_same_image

Acceso por input_sha256, input_contract_hash, model_version_id, method_configuration_id, generated_at, id en xai_evidence.
```sql
CREATE INDEX ix_xai_same_image ON public.xai_evidence (input_sha256, input_contract_hash, model_version_id, method_configuration_id, generated_at, id);
```

### local_one_active

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX local_one_active ON public.local_execution_jobs ((TRUE)) WHERE state = ANY(ARRAY[CAST('held' AS text), CAST('calculation_reported' AS text)]);
```

### train_event_id_unique

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX train_event_id_unique ON public.train_execution_records (event_id) WHERE event_id IS NOT NULL;
```

### train_event_sequence_unique

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX train_event_sequence_unique ON public.train_execution_records (run_id, event_sequence) WHERE event_sequence IS NOT NULL;
```

### uq_artifacts_id_run_id

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_artifacts_id_run_id ON public.artifacts (id, run_id);
```

### uq_assessment_live

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_assessment_live ON public.assessment_attempts (identity_id) WHERE state = ANY(ARRAY[CAST('active' AS text), CAST('verified' AS text)]);
```

### uq_blood_samples_external_identity

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_blood_samples_external_identity ON public.blood_samples (case_id, source_system, external_sample_id) WHERE external_sample_id IS NOT NULL;
```

### uq_campaign_one_active_attempt

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_campaign_one_active_attempt ON public.campaign_attempts (member_id) WHERE state = CAST('active' AS text);
```

### uq_cell_classification_runs_equivalent_active

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_cell_classification_runs_equivalent_active ON public.cell_classification_runs (detection_run_id, production_model_id, (COALESCE(model_version, CAST('' AS varchar))), (COALESCE(model_snapshot ->> CAST('checkpoint_sha256' AS text), CAST('' AS text))), (COALESCE(model_snapshot ->> CAST('inference_version' AS text), CAST('' AS text))), input_manifest_sha256) WHERE CAST(status AS text) = ANY(ARRAY[CAST(CAST('created' AS varchar) AS text), CAST(CAST('processing' AS varchar) AS text), CAST(CAST('completed' AS varchar) AS text), CAST(CAST('completed_with_warnings' AS varchar) AS text)]);
```

### uq_cell_crops_id_detection

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_cell_crops_id_detection ON public.cell_crops (id, cell_detection_id);
```

### uq_cell_detection_runs_equivalent_active

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_cell_detection_runs_equivalent_active ON public.cell_detection_runs (analysis_run_id, detector_key, detector_version, algorithm_version, input_manifest_sha256) WHERE CAST(status AS text) = ANY(ARRAY[CAST(CAST('created' AS varchar) AS text), CAST(CAST('processing' AS varchar) AS text), CAST(CAST('completed' AS varchar) AS text), CAST(CAST('completed_with_warnings' AS varchar) AS text)]);
```

### uq_dataset_materialization_activations_current_family

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_dataset_materialization_activations_current_family ON public.dataset_materialization_activations (dataset_family) WHERE deactivated_at IS NULL;
```

### uq_deployed_model_versions_active_slot

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_deployed_model_versions_active_slot ON public.deployed_model_versions (deployment_name, environment, alias) WHERE status = CAST('active' AS text);
```

### uq_deployed_model_versions_id_version

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_deployed_model_versions_id_version ON public.deployed_model_versions (id, model_version_id);
```

### uq_deployed_model_versions_one_production_champion

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_deployed_model_versions_one_production_champion ON public.deployed_model_versions (environment, alias) WHERE status = CAST('active' AS text) AND environment = CAST('production' AS text) AND alias = CAST('champion' AS text);
```

### uq_e04_contract_role

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_e04_contract_role ON public.evaluations (run_id, training_run_id, model_version_id, checkpoint_artifact_id, dataset_version_id, population_hash, protocol_version, protocol_hash, input_contract_hash, evaluation_role) WHERE source_kind = 'e10' AND evaluation_role IN ('calibration_default', 'calibration_selected') NULLS NOT DISTINCT;
```

### uq_e04_event_role

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_e04_event_role ON public.evaluations (source_event_id, evaluation_role) WHERE source_kind = 'e10' AND evaluation_role IN ('calibration_default', 'calibration_selected');
```

### uq_evaluation_final_training

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_evaluation_final_training ON public.evaluations (run_id) WHERE evaluation_role = 'training_validation_final';
```

### uq_global_assessment_active

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_global_assessment_active ON public.assessment_attempts ((TRUE)) WHERE state = CAST('active' AS text);
```

### uq_global_train_active

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_global_train_active ON public.train_execution_sessions ((TRUE)) WHERE state = ANY(ARRAY[CAST('active' AS text), CAST('completed' AS text)]);
```

### uq_image_analysis_jobs_idempotency

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_image_analysis_jobs_idempotency ON public.image_analysis_jobs (inference_run_id, idempotency_key) WHERE idempotency_key IS NOT NULL;
```

### uq_image_analysis_jobs_identity

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_image_analysis_jobs_identity ON public.image_analysis_jobs (id, inference_run_id, deployed_model_version_id, model_version_id);
```

### uq_ingestion_batches_source_group

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_ingestion_batches_source_group ON public.image_ingestion_batches (source_system, source_group_key) WHERE source_system IS NOT NULL AND source_group_key IS NOT NULL;
```

### uq_microscopy_analysis_equivalent

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_microscopy_analysis_equivalent ON public.microscopy_analysis_runs (ingestion_batch_id, quality_profile_key, quality_profile_version, quality_algorithm_version, input_manifest_sha256);
```

### uq_microscopy_images_external_path

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_microscopy_images_external_path ON public.microscopy_images (source_system, source_relative_path) WHERE source_system IS NOT NULL AND source_relative_path IS NOT NULL;
```

### uq_model_versions_checkpoint_artifact

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_model_versions_checkpoint_artifact ON public.model_versions (checkpoint_artifact_id) WHERE checkpoint_artifact_id IS NOT NULL;
```

### uq_model_versions_id_checkpoint_artifact

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_model_versions_id_checkpoint_artifact ON public.model_versions (id, checkpoint_artifact_id);
```

### uq_model_versions_id_training_run

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_model_versions_id_training_run ON public.model_versions (id, training_run_id);
```

### uq_model_versions_name_number

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_model_versions_name_number ON public.model_versions (model_name, version_number) WHERE model_name IS NOT NULL AND version_number IS NOT NULL;
```

### uq_model_versions_training_version_name

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_model_versions_training_version_name ON public.model_versions (training_run_id, version_name) WHERE training_run_id IS NOT NULL AND version_name IS NOT NULL;
```

### uq_model_versions_unjustified_sha256

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_model_versions_unjustified_sha256 ON public.model_versions (artifact_sha256) WHERE artifact_sha256 IS NOT NULL AND NULLIF(btrim(artifact_hash_reuse_justification), CAST('' AS text)) IS NULL;
```

### uq_predictions_job_cell_index

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_predictions_job_cell_index ON public.predictions (image_analysis_job_id, cell_index) WHERE prediction_scope = CAST('cell' AS text);
```

### uq_quality_queue_active_run

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_quality_queue_active_run ON public.quality_assessment_queue_items (analysis_run_id) WHERE CAST(status AS text) = ANY(ARRAY[CAST(CAST('queued' AS varchar) AS text), CAST(CAST('running' AS varchar) AS text)]);
```

### uq_research_subjects_external_identity

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_research_subjects_external_identity ON public.research_subjects (source_system, external_patient_id) WHERE external_patient_id IS NOT NULL;
```

### uq_run_lineage_single_evaluation_training_parent

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_run_lineage_single_evaluation_training_parent ON public.run_lineage (child_run_id) WHERE relationship_type = CAST('evaluates_checkpoint_from' AS text);
```

### uq_run_model_deployments_binding

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_run_model_deployments_binding ON public.run_model_deployments (run_id, deployed_model_version_id, role, ordinal);
```

### uq_run_model_deployments_primary

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_run_model_deployments_primary ON public.run_model_deployments (run_id) WHERE role = CAST('primary' AS text);
```

### uq_run_model_deployments_run_deployment_version

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_run_model_deployments_run_deployment_version ON public.run_model_deployments (run_id, deployed_model_version_id, model_version_id);
```

### uq_run_threshold_calibration_id_version

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_run_threshold_calibration_id_version ON public.run_threshold_calibration (run_threshold_calibration_id, model_version_id);
```

### uq_runs_single_productive_stage2

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_runs_single_productive_stage2 ON public.runs (release_status) WHERE run_type = CAST('training' AS text) AND release_status = CAST('productive_stage2' AS text);
```

### uq_stage2_model_publications_id_version

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_stage2_model_publications_id_version ON public.stage2_model_publications (id, model_version_id);
```

### uq_stage2_publication_active_version

Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.
```sql
CREATE UNIQUE INDEX uq_stage2_publication_active_version ON public.stage2_model_publications (model_version_id, scope) WHERE is_active;
```

## Cobertura de FK por prefijo

Sin cobertura no significa FK inválida: su validación usa el índice UNIQUE del padre. Esta lista permite revisar coste de joins y borrados en DBV2.2; no presupone cargas medidas.

| FK | Tabla hija | Prefijo cubierto |
|---|---|---|
| artifacts_run_id_fkey | artifacts | idx_artifacts_run_id |
| assessment_artifacts_attempt_id_fkey | assessment_artifacts | assessment_artifacts_pkey |
| assessment_attempts_identity_id_fkey | assessment_attempts | assessment_attempts_identity_id_ordinal_key |
| assessment_campaign_consumers_campaign_id_fkey | assessment_campaign_consumers | assessment_campaign_consumers_pkey |
| assessment_campaign_consumers_identity_id_fkey | assessment_campaign_consumers | No; conservar sin índice adicional hasta justificar consulta/coste |
| assessment_campaign_consumers_member_id_fkey | assessment_campaign_consumers | No; conservar sin índice adicional hasta justificar consulta/coste |
| assessment_identities_training_run_id_fkey | assessment_identities | No; conservar sin índice adicional hasta justificar consulta/coste |
| assessment_results_attempt_id_fkey | assessment_results | assessment_results_pkey |
| audit_events_actor_user_id_fkey | audit_events | ix_audit_events_actor |
| blood_samples_archived_by_fkey | blood_samples | No; conservar sin índice adicional hasta justificar consulta/coste |
| blood_samples_case_id_fkey | blood_samples | uq_blood_samples_case_code, ix_blood_samples_case |
| blood_samples_created_by_fkey | blood_samples | No; conservar sin índice adicional hasta justificar consulta/coste |
| blood_samples_updated_by_fkey | blood_samples | No; conservar sin índice adicional hasta justificar consulta/coste |
| campaign_attempts_member_id_fkey | campaign_attempts | campaign_attempts_member_id_id_key, campaign_attempts_member_id_ordinal_key |
| campaign_attempts_training_run_id_fkey | campaign_attempts | campaign_attempts_training_run_id_key |
| campaign_configurations_campaign_id_fkey | campaign_configurations | campaign_configurations_pkey |
| campaign_controlled_requests_attempt_id_fkey | campaign_controlled_requests | campaign_controlled_requests_attempt_id_key |
| campaign_controlled_requests_campaign_id_fkey | campaign_controlled_requests | No; conservar sin índice adicional hasta justificar consulta/coste |
| campaign_controlled_requests_campaign_id_revision_id_fkey | campaign_controlled_requests | No; conservar sin índice adicional hasta justificar consulta/coste |
| campaign_controlled_requests_member_id_fkey | campaign_controlled_requests | No; conservar sin índice adicional hasta justificar consulta/coste |
| campaign_controlled_requests_previous_attempt_id_fkey | campaign_controlled_requests | campaign_controlled_requests_previous_attempt_id_key |
| campaign_controlled_requests_run_id_fkey | campaign_controlled_requests | campaign_controlled_requests_run_id_key |
| campaign_execution_events_campaign_id_fkey | campaign_execution_events | No; conservar sin índice adicional hasta justificar consulta/coste |
| campaign_members_campaign_id_configuration_hash_fkey | campaign_members | campaign_members_campaign_id_configuration_hash_seed_key |
| campaign_members_campaign_id_fkey | campaign_members | campaign_members_campaign_id_configuration_hash_seed_key, campaign_members_campaign_id_position_key, ix_campaign_member_state |
| fk_member_accepted_attempt | campaign_members | No; conservar sin índice adicional hasta justificar consulta/coste |
| campaign_technical_revisions_campaign_id_fkey | campaign_technical_revisions | campaign_technical_revisions_campaign_id_id_key |
| cell_classification_events_cell_detection_id_fkey | cell_classification_events | No; conservar sin índice adicional hasta justificar consulta/coste |
| cell_classification_events_classification_run_id_fkey | cell_classification_events | ix_cell_classification_events_run_created, ix_cell_classification_events_run_detection, ix_cell_classification_events_run_prediction |
| fk_cell_classification_event_prediction | cell_classification_events | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_cell_classification_input_crop | cell_classification_inputs | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_cell_classification_input_detection | cell_classification_inputs | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_cell_classification_input_run_detection | cell_classification_inputs | No; conservar sin índice adicional hasta justificar consulta/coste |
| cell_classification_reviews_actor_user_id_fkey | cell_classification_reviews | ix_cell_classification_reviews_actor_created |
| cell_classification_reviews_cell_prediction_id_fkey | cell_classification_reviews | ix_cell_classification_reviews_prediction_created |
| cell_classification_runs_requested_by_fkey | cell_classification_runs | No; conservar sin índice adicional hasta justificar consulta/coste |
| cell_classification_runs_retry_of_run_id_fkey | cell_classification_runs | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_cell_classification_run_deployment_version | cell_classification_runs | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_cell_classification_run_detection_analysis | cell_classification_runs | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_cell_classification_run_publication_version | cell_classification_runs | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_cell_crops_detection | cell_crops | uq_cell_crops_detection |
| cell_detection_events_detection_run_id_fkey | cell_detection_events | ix_cell_detection_events_run_created, ix_cell_detection_events_run_image |
| cell_detection_events_microscopy_image_id_fkey | cell_detection_events | No; conservar sin índice adicional hasta justificar consulta/coste |
| cell_detection_runs_analysis_run_id_fkey | cell_detection_runs | ix_cell_detection_runs_analysis_created |
| cell_detection_runs_requested_by_fkey | cell_detection_runs | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_cell_detections_component | cell_detections | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_cell_detections_run_analysis | cell_detections | No; conservar sin índice adicional hasta justificar consulta/coste |
| cell_explanations_cell_prediction_id_fkey | cell_explanations | cell_explanations_cell_prediction_id_key |
| fk_cell_prediction_input_owner | cell_predictions | No; conservar sin índice adicional hasta justificar consulta/coste |
| clinical_identities_dataset_id_fkey | clinical_identities | uq_clinical_identities_source |
| dataset_materialization_activations_dataset_version_id_fkey | dataset_materialization_activations | ix_dataset_materialization_activations_dataset_version_id |
| dataset_materialization_activations_materialization_id_fkey | dataset_materialization_activations | ix_dataset_materialization_activations_materialization_id |
| dataset_materializations_dataset_version_id_fkey | dataset_materializations | uq_dataset_materializations_attempt, ix_dataset_materializations_dataset_version_id |
| dataset_source_records_clinical_identity_id_fkey | dataset_source_records | ix_dataset_source_records_clinical_identity_id |
| dataset_source_records_dataset_id_fkey | dataset_source_records | uq_dataset_source_records_key, ix_dataset_source_records_dataset_id |
| dataset_split_assignments_clinical_identity_id_fkey | dataset_split_assignments | ix_dataset_split_assignments_clinical_identity_id |
| dataset_split_assignments_dataset_version_id_fkey | dataset_split_assignments | uq_dataset_split_assignments_record, ix_dataset_split_assignments_dataset_version_id |
| dataset_split_assignments_source_record_id_fkey | dataset_split_assignments | No; conservar sin índice adicional hasta justificar consulta/coste |
| dataset_split_images_dataset_id_fkey | dataset_split_images | idx_dataset_split_images_dataset_id |
| dataset_split_images_dataset_materialization_id_fkey | dataset_split_images | ix_dataset_split_images_dataset_materialization_id |
| dataset_split_images_dataset_version_id_fkey | dataset_split_images | ix_dataset_split_images_dataset_version_id |
| dataset_split_statistics_dataset_version_id_fkey | dataset_split_statistics | ix_dataset_split_statistics_version_metric |
| dataset_split_validation_checks_dataset_version_id_fkey | dataset_split_validation_checks | ix_dataset_split_validation_checks_version_name |
| dataset_splits_dataset_id_fkey | dataset_splits | No; conservar sin índice adicional hasta justificar consulta/coste |
| dataset_version_sources_dataset_id_fkey | dataset_version_sources | ix_dataset_version_sources_dataset_id |
| dataset_version_sources_dataset_version_id_fkey | dataset_version_sources | dataset_version_sources_pkey |
| fk_deployed_model_versions_rollback | deployed_model_versions | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_deployed_model_versions_supersedes | deployed_model_versions | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_deployed_model_versions_threshold_version | deployed_model_versions | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_deployed_model_versions_version_artifact | deployed_model_versions | No; conservar sin índice adicional hasta justificar consulta/coste |
| environment_packages_run_id_fkey | environment_packages | idx_environment_packages_run_id |
| errors_run_id_fkey | errors | idx_errors_run_id |
| v2_evaluation_ensemble_members_foreign_a402d28a70f6 | evaluation_ensemble_members | v2_evaluation_ensemble_members_primary_0f6c3f155b09, v2_evaluation_ensemble_members_unique_3a2092158e31 |
| v2_evaluation_ensemble_members_foreign_b946b2b207f3 | evaluation_ensemble_members | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_evaluation_ensemble_members_foreign_6aec504c7a2f | evaluation_ensemble_members | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_evaluation_e10_record | evaluations | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_evaluations_foreign_db5338c19de4 | evaluations | v2_evaluations_unique_2b29f071653b |
| v2_evaluations_foreign_4e6a43d876af | evaluations | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_evaluations_foreign_6aec504c7a2f | evaluations | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_evaluations_foreign_14b20ff24e12 | evaluations | ix_evaluation_comparison |
| v2_evaluations_foreign_c764adede219 | evaluations | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_evaluations_foreign_0baa7d166e2f | evaluations | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_evaluations_foreign_6cfcdf2998f5 | evaluations | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_v2_evaluation_dataset_origin | evaluations | No; conservar sin índice adicional hasta justificar consulta/coste |
| execution_logs_run_id_fkey | execution_logs | idx_execution_logs_run_id |
| experimental_campaigns_dataset_evidence_id_fkey | experimental_campaigns | No; conservar sin índice adicional hasta justificar consulta/coste |
| experimental_campaigns_dataset_version_id_fkey | experimental_campaigns | ix_campaign_dataset_state |
| experimental_campaigns_experiment_id_fkey | experimental_campaigns | No; conservar sin índice adicional hasta justificar consulta/coste |
| explainability_results_prediction_id_fkey | explainability_results | No; conservar sin índice adicional hasta justificar consulta/coste |
| explainability_results_run_id_fkey | explainability_results | idx_explainability_run_id |
| identity_evidence_clinical_identity_id_fkey | identity_evidence | ix_identity_evidence_clinical_identity_id |
| identity_evidence_source_record_id_fkey | identity_evidence | ix_identity_evidence_source_record_id |
| fk_image_analysis_jobs_input_artifact | image_analysis_jobs | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_image_analysis_jobs_run_deployment_version | image_analysis_jobs | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_image_analysis_jobs_source_image | image_analysis_jobs | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_components_detection_analysis | image_connected_components | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_components_frozen_image | image_connected_components | No; conservar sin índice adicional hasta justificar consulta/coste |
| image_ingestion_batches_case_id_fkey | image_ingestion_batches | No; conservar sin índice adicional hasta justificar consulta/coste |
| image_ingestion_batches_created_by_fkey | image_ingestion_batches | No; conservar sin índice adicional hasta justificar consulta/coste |
| image_ingestion_batches_sample_id_fkey | image_ingestion_batches | ix_ingestion_batches_sample |
| image_ingestion_batches_slide_id_fkey | image_ingestion_batches | No; conservar sin índice adicional hasta justificar consulta/coste |
| image_ingestion_batches_subject_id_fkey | image_ingestion_batches | No; conservar sin índice adicional hasta justificar consulta/coste |
| image_quality_assessments_analysis_run_id_fkey | image_quality_assessments | image_quality_assessments_analysis_run_id_microscopy_image__key |
| image_quality_assessments_analysis_run_image_id_analysis_r_fkey | image_quality_assessments | No; conservar sin índice adicional hasta justificar consulta/coste |
| image_quality_assessments_microscopy_image_id_fkey | image_quality_assessments | No; conservar sin índice adicional hasta justificar consulta/coste |
| local_execution_jobs_campaign_id_fkey | local_execution_jobs | No; conservar sin índice adicional hasta justificar consulta/coste |
| local_execution_jobs_run_id_fkey | local_execution_jobs | local_execution_jobs_run_id_key |
| microscopy_analysis_events_analysis_run_id_fkey | microscopy_analysis_events | ix_microscopy_analysis_events_run |
| microscopy_analysis_events_microscopy_image_id_fkey | microscopy_analysis_events | No; conservar sin índice adicional hasta justificar consulta/coste |
| microscopy_analysis_run_images_analysis_run_id_fkey | microscopy_analysis_run_images | microscopy_analysis_run_image_analysis_run_id_microscopy_im_key, microscopy_analysis_run_image_analysis_run_id_sequence_numb_key |
| microscopy_analysis_run_images_microscopy_image_id_fkey | microscopy_analysis_run_images | No; conservar sin índice adicional hasta justificar consulta/coste |
| microscopy_analysis_runs_case_id_fkey | microscopy_analysis_runs | No; conservar sin índice adicional hasta justificar consulta/coste |
| microscopy_analysis_runs_ingestion_batch_id_fkey | microscopy_analysis_runs | uq_microscopy_analysis_equivalent |
| microscopy_analysis_runs_requested_by_fkey | microscopy_analysis_runs | No; conservar sin índice adicional hasta justificar consulta/coste |
| microscopy_analysis_runs_sample_id_fkey | microscopy_analysis_runs | No; conservar sin índice adicional hasta justificar consulta/coste |
| microscopy_analysis_runs_slide_id_fkey | microscopy_analysis_runs | No; conservar sin índice adicional hasta justificar consulta/coste |
| microscopy_analysis_runs_subject_id_fkey | microscopy_analysis_runs | ix_microscopy_analysis_runs_subject |
| microscopy_images_archived_by_fkey | microscopy_images | No; conservar sin índice adicional hasta justificar consulta/coste |
| microscopy_images_created_by_fkey | microscopy_images | No; conservar sin índice adicional hasta justificar consulta/coste |
| microscopy_images_ingestion_batch_id_fkey | microscopy_images | ix_microscopy_images_ingestion_batch |
| microscopy_images_slide_id_fkey | microscopy_images | uq_microscopy_images_slide_code, uq_microscopy_images_slide_sha256, ix_microscopy_images_slide |
| microscopy_images_updated_by_fkey | microscopy_images | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_model_versions_checkpoint_artifact_owner | model_versions | No; conservar sin índice adicional hasta justificar consulta/coste |
| model_versions_model_id_fkey | model_versions | idx_model_versions_model |
| model_versions_training_run_id_fkey | model_versions | idx_model_versions_training_run |
| fk_predictions_analysis_job | predictions | idx_predictions_analysis_job |
| fk_predictions_classifier_model_version | predictions | idx_predictions_classifier_model_version |
| fk_predictions_crop_artifact | predictions | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_predictions_deployed_model_version | predictions | idx_predictions_deployed_model_version |
| fk_predictions_detector_model_version | predictions | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_predictions_explanation_artifact | predictions | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_predictions_inference_run | predictions | idx_predictions_inference_run |
| fk_predictions_job_provenance | predictions | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_predictions_model_version | predictions | idx_predictions_model_version |
| fk_predictions_source_image | predictions | No; conservar sin índice adicional hasta justificar consulta/coste |
| predictions_dataset_id_fkey | predictions | No; conservar sin índice adicional hasta justificar consulta/coste |
| predictions_run_id_fkey | predictions | idx_predictions_run_id |
| fk_v2_prediction_evaluation_run | predictions | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_predictions_foreign_a402d28a70f6 | predictions | uq_v2_evaluation_sample |
| v2_predictions_foreign_e8d9af78807c | predictions | No; conservar sin índice adicional hasta justificar consulta/coste |
| quality_assessment_queue_items_analysis_run_id_fkey | quality_assessment_queue_items | No; conservar sin índice adicional hasta justificar consulta/coste |
| quality_assessment_queue_items_requested_by_fkey | quality_assessment_queue_items | No; conservar sin índice adicional hasta justificar consulta/coste |
| quality_gate_decisions_actor_user_id_fkey | quality_gate_decisions | No; conservar sin índice adicional hasta justificar consulta/coste |
| quality_gate_decisions_analysis_run_id_fkey | quality_gate_decisions | ix_quality_gate_decisions_run |
| research_subjects_archived_by_fkey | research_subjects | No; conservar sin índice adicional hasta justificar consulta/coste |
| research_subjects_created_by_fkey | research_subjects | No; conservar sin índice adicional hasta justificar consulta/coste |
| research_subjects_updated_by_fkey | research_subjects | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_run_checkpoint_policy_artifact_owner | run_checkpoint_policy | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_run_checkpoint_policy_model_version_owner | run_checkpoint_policy | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_run_checkpoint_policy_version_artifact | run_checkpoint_policy | No; conservar sin índice adicional hasta justificar consulta/coste |
| run_checkpoint_policy_run_id_fkey | run_checkpoint_policy | idx_run_checkpoint_policy_run_id |
| run_clinical_metrics_model_id_fkey | run_clinical_metrics | No; conservar sin índice adicional hasta justificar consulta/coste |
| run_clinical_metrics_run_id_fkey | run_clinical_metrics | idx_run_clinical_metrics_run_id |
| fk_metric_evaluation_run | run_clinical_metrics | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_run_configurations_foreign_db5338c19de4 | run_configurations | v2_run_configurations_primary_360aa242ca7c |
| run_dataset_images_image_id_fkey | run_dataset_images | idx_run_dataset_images_image_id |
| run_dataset_images_run_id_fkey | run_dataset_images | uq_run_dataset_images_usage, idx_run_dataset_images_run_id |
| run_image_predictions_image_id_fkey | run_image_predictions | No; conservar sin índice adicional hasta justificar consulta/coste |
| run_image_predictions_run_id_fkey | run_image_predictions | idx_run_image_predictions_run_id |
| run_io_records_dataset_materialization_id_fkey | run_io_records | ix_run_io_records_dataset_materialization_id |
| run_io_records_dataset_version_id_fkey | run_io_records | ix_run_io_records_dataset_version_id |
| run_io_records_run_id_fkey | run_io_records | idx_run_io_records_run_id |
| fk_run_lineage_checkpoint_artifact_owner | run_lineage | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_run_lineage_model_version_owner | run_lineage | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_run_lineage_version_artifact | run_lineage | No; conservar sin índice adicional hasta justificar consulta/coste |
| run_lineage_child_run_id_fkey | run_lineage | idx_run_lineage_child_run_id |
| run_lineage_parent_run_id_fkey | run_lineage | uq_run_lineage_parent_child_type, idx_run_lineage_parent_run_id |
| run_metrics_run_id_fkey | run_metrics | idx_run_metrics_run_id |
| fk_run_model_deployments_deployment_version | run_model_deployments | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_run_model_deployments_run | run_model_deployments | uq_run_model_deployments_binding, uq_run_model_deployments_run_deployment_version |
| fk_run_threshold_calibration_artifact_owner | run_threshold_calibration | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_run_threshold_calibration_model_version | run_threshold_calibration | idx_run_threshold_calibration_model_version |
| run_threshold_calibration_run_id_fkey | run_threshold_calibration | idx_run_threshold_calibration_run_id |
| v2_run_threshold_calibration_foreign_014acc59cdbd | run_threshold_calibration | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_run_threshold_calibration_foreign_0ba3287c0955 | run_threshold_calibration | No; conservar sin índice adicional hasta justificar consulta/coste |
| runs_campaign_id_fkey | runs | No; conservar sin índice adicional hasta justificar consulta/coste |
| runs_dataset_id_fkey | runs | idx_runs_dataset_id |
| runs_dataset_version_id_fkey | runs | ix_runs_dataset_version_id |
| runs_experiment_id_fkey | runs | No; conservar sin índice adicional hasta justificar consulta/coste |
| runs_model_id_fkey | runs | idx_runs_model_id |
| scientific_cases_archived_by_fkey | scientific_cases | No; conservar sin índice adicional hasta justificar consulta/coste |
| scientific_cases_created_by_fkey | scientific_cases | No; conservar sin índice adicional hasta justificar consulta/coste |
| scientific_cases_subject_id_fkey | scientific_cases | ix_scientific_cases_subject |
| scientific_cases_updated_by_fkey | scientific_cases | No; conservar sin índice adicional hasta justificar consulta/coste |
| scientific_reviews_actor_user_id_fkey | scientific_reviews | ix_scientific_reviews_actor_created |
| scientific_reviews_entity_id_fkey | scientific_reviews | No; conservar sin índice adicional hasta justificar consulta/coste |
| scientific_validation_annotation_eve_validation_session_id_fkey | scientific_validation_annotation_events | No; conservar sin índice adicional hasta justificar consulta/coste |
| scientific_validation_annotation_events_actor_user_id_fkey | scientific_validation_annotation_events | ix_validation_annotation_events_actor_created |
| scientific_validation_annotation_events_annotation_id_fkey | scientific_validation_annotation_events | scientific_validation_annotat_annotation_id_annotation_vers_key, ix_validation_annotation_events_annotation_created |
| scientific_validation_annotations_analysis_run_id_fkey | scientific_validation_annotations | No; conservar sin índice adicional hasta justificar consulta/coste |
| scientific_validation_annotations_cell_detection_id_fkey | scientific_validation_annotations | No; conservar sin índice adicional hasta justificar consulta/coste |
| scientific_validation_annotations_created_by_fkey | scientific_validation_annotations | No; conservar sin índice adicional hasta justificar consulta/coste |
| scientific_validation_annotations_sample_id_fkey | scientific_validation_annotations | No; conservar sin índice adicional hasta justificar consulta/coste |
| scientific_validation_annotations_updated_by_fkey | scientific_validation_annotations | No; conservar sin índice adicional hasta justificar consulta/coste |
| scientific_validation_annotations_validation_session_id_fkey | scientific_validation_annotations | ix_validation_annotations_session_category, ix_validation_annotations_session_created |
| scientific_validation_classification_classification_run_id_fkey | scientific_validation_classification_runs | No; conservar sin índice adicional hasta justificar consulta/coste |
| scientific_validation_classification_runs_session_id_fkey | scientific_validation_classification_runs | scientific_validation_classification_runs_pkey |
| scientific_validation_detection_runs_detection_run_id_fkey | scientific_validation_detection_runs | No; conservar sin índice adicional hasta justificar consulta/coste |
| scientific_validation_detection_runs_session_id_fkey | scientific_validation_detection_runs | scientific_validation_detection_runs_pkey |
| scientific_validation_images_microscopy_image_id_fkey | scientific_validation_images | No; conservar sin índice adicional hasta justificar consulta/coste |
| scientific_validation_images_session_id_fkey | scientific_validation_images | scientific_validation_images_pkey, scientific_validation_images_session_id_sequence_number_key |
| scientific_validation_sessions_archived_by_fkey | scientific_validation_sessions | No; conservar sin índice adicional hasta justificar consulta/coste |
| scientific_validation_sessions_created_by_fkey | scientific_validation_sessions | ix_validation_sessions_creator_created |
| scientific_validation_sessions_updated_by_fkey | scientific_validation_sessions | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_smear_summary_classification_lineage | smear_analysis_summaries | No; conservar sin índice adicional hasta justificar consulta/coste |
| smear_slides_archived_by_fkey | smear_slides | No; conservar sin índice adicional hasta justificar consulta/coste |
| smear_slides_created_by_fkey | smear_slides | No; conservar sin índice adicional hasta justificar consulta/coste |
| smear_slides_sample_id_fkey | smear_slides | uq_smear_slides_sample_code, ix_smear_slides_sample |
| smear_slides_updated_by_fkey | smear_slides | No; conservar sin índice adicional hasta justificar consulta/coste |
| stage2_model_publication_events_publication_id_fkey | stage2_model_publication_events | idx_stage2_publication_events_publication |
| fk_stage2_publication_evaluation | stage2_model_publications | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_stage2_publication_training | stage2_model_publications | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_stage2_publication_version_artifact | stage2_model_publications | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_stage2_publication_model_training | stage2_model_publications | No; conservar sin índice adicional hasta justificar consulta/coste |
| synthetic_data_runs_run_id_fkey | synthetic_data_runs | No; conservar sin índice adicional hasta justificar consulta/coste |
| synthetic_data_runs_source_dataset_id_fkey | synthetic_data_runs | No; conservar sin índice adicional hasta justificar consulta/coste |
| train_execution_records_run_id_fkey | train_execution_records | train_execution_records_pkey |
| train_execution_revisions_attempt_id_fkey | train_execution_revisions | train_execution_revisions_pkey |
| train_execution_revisions_campaign_id_fkey | train_execution_revisions | No; conservar sin índice adicional hasta justificar consulta/coste |
| train_execution_revisions_campaign_id_revision_id_fkey | train_execution_revisions | No; conservar sin índice adicional hasta justificar consulta/coste |
| train_execution_sessions_attempt_id_fkey | train_execution_sessions | train_execution_sessions_attempt_id_key |
| train_execution_sessions_run_id_fkey | train_execution_sessions | train_execution_sessions_pkey |
| training_history_run_id_fkey | training_history | uq_v2_epoch, idx_training_history_run_id |
| user_roles_role_id_fkey | user_roles | No; conservar sin índice adicional hasta justificar consulta/coste |
| user_roles_user_id_fkey | user_roles | user_roles_pkey |
| v2_xai_artifacts_foreign_4b080b42e888 | xai_artifacts | v2_xai_artifacts_unique_ee15a9513a9e |
| v2_xai_artifacts_foreign_e3d2eb574718 | xai_artifacts | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_xai_artifacts_foreign_f9c5548be835 | xai_artifacts | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_xai_member_evaluation | xai_evaluation_members | xai_evaluation_members_pkey |
| fk_xai_member_evidence | xai_evaluation_members | ix_xai_member_evidence |
| v2_xai_evidence_foreign_9851edbb8079 | xai_evidence | v2_xai_evidence_unique_d9477cb1fece |
| v2_xai_evidence_foreign_3fe88bd35854 | xai_evidence | v2_xai_evidence_unique_d4bf0f195fcf |
| v2_xai_evidence_foreign_4b04405ab069 | xai_evidence | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_xai_evidence_foreign_029e07f1d6db | xai_evidence | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_xai_evidence_foreign_a402d28a70f6 | xai_evidence | ix_xai_evaluation |
| v2_xai_evidence_foreign_e8d9af78807c | xai_evidence | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_xai_evidence_foreign_a1c9b824423e | xai_evidence | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_xai_evidence_foreign_ad1ea3f78d92 | xai_evidence | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_xai_evidence_foreign_db5338c19de4 | xai_evidence | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_xai_evidence_foreign_b946b2b207f3 | xai_evidence | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_xai_evidence_foreign_6aec504c7a2f | xai_evidence | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_xai_evidence_foreign_52bd313b1c15 | xai_evidence | v2_xai_evidence_unique_0be310eeb2b7 |
| fk_xai_method_configuration | xai_evidence | ix_xai_method_configuration |
| v2_xai_interpretations_foreign_4b080b42e888 | xai_interpretations | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_xai_interpretations_foreign_6b09f9926d4f | xai_interpretations | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_xai_interpretations_foreign_af451d74af77 | xai_interpretations | No; conservar sin índice adicional hasta justificar consulta/coste |
| fk_xai_metric_protocol | xai_quantitative_evaluations | ix_xai_metric_protocol |
| fk_xai_reference_annotation | xai_quantitative_evaluations | ix_xai_reference_annotation |
| fk_xai_region_evidence | xai_region_attributions | xai_region_attributions_pkey |
| v2_xai_specialist_reviews_foreign_4735bf604cb2 | xai_specialist_reviews | No; conservar sin índice adicional hasta justificar consulta/coste |
| v2_xai_specialist_reviews_foreign_7ca01df9e490 | xai_specialist_reviews | No; conservar sin índice adicional hasta justificar consulta/coste |
