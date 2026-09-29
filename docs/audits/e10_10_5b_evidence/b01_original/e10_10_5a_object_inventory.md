# E10.10.5A — Inventario implementado (estático)

**No es un catálogo obtenido de PostgreSQL.** Definiciones congeladas de `pg_v2_baseline`, después de A-01.

Fuente completa verificable: [catalog_manifest.json](../../alembic_v2/baseline/catalog_manifest.json). Cada entrada señala archivo, offsets en bytes y SHA-256; las tablas incluyen tipos, defaults, nulabilidad, expresiones generadas y colación. Los SQL contienen los cuerpos/firmas, predicados, opclasses, acciones FK y ACL completos.

| Objeto | Cantidad |
| --- | ---: |
| Tablas de aplicación | 102 |
| Tabla Alembic administrada por Alembic | 1 |
| Vistas | 33 |
| Funciones propias | 75 |
| Triggers de aplicación | 95 |
| PK aplicación | 102 |
| UNIQUE aplicación | 75 |
| CHECK aplicación | 524 |
| FK aplicación | 249 |
| Índices independientes | 229 |
| Secuencias | 1 |

Más PK e índice de `alembic_version`. Los índices implícitos de PK/UNIQUE no se recrean manualmente. Se conserva `pgcrypto`; `plpgsql` es prerrequisito incorporado. Los objetos internos de ambas extensiones y los triggers RI son responsabilidad de PostgreSQL.

## Tablas

| Tabla | Acción de diseño | Columnas |
| --- | --- | ---: |
| `alembic_version` | Alembic | 1 |
| `artifacts` | KEEP | 13 |
| `assessment_artifacts` | KEEP | 5 |
| `assessment_attempts` | KEEP | 12 |
| `assessment_campaign_consumers` | KEEP | 3 |
| `assessment_final_locks` | KEEP | 4 |
| `assessment_identities` | KEEP | 8 |
| `assessment_results` | REFACTOR | 3 |
| `audit_events` | KEEP | 16 |
| `blood_samples` | KEEP | 23 |
| `campaign_attempts` | KEEP | 8 |
| `campaign_configurations` | REFACTOR | 5 |
| `campaign_controlled_requests` | KEEP | 9 |
| `campaign_execution_events` | KEEP | 4 |
| `campaign_members` | KEEP | 8 |
| `campaign_technical_revisions` | KEEP | 6 |
| `cell_classification_events` | KEEP | 12 |
| `cell_classification_inputs` | KEEP | 20 |
| `cell_classification_reviews` | KEEP | 7 |
| `cell_classification_runs` | KEEP | 29 |
| `cell_crops` | KEEP | 10 |
| `cell_detection_events` | KEEP | 12 |
| `cell_detection_runs` | KEEP | 23 |
| `cell_detections` | KEEP | 16 |
| `cell_explanations` | REFACTOR | 20 |
| `cell_predictions` | KEEP | 22 |
| `clinical_identities` | PROTECTED | 8 |
| `dataset_materialization_activations` | PROTECTED | 7 |
| `dataset_materializations` | PROTECTED | 13 |
| `dataset_source_records` | PROTECTED | 20 |
| `dataset_split_assignments` | PROTECTED | 9 |
| `dataset_split_images` | PROTECTED | 23 |
| `dataset_split_statistics` | PROTECTED | 8 |
| `dataset_split_validation_checks` | PROTECTED | 10 |
| `dataset_splits` | PROTECTED | 9 |
| `dataset_version_sources` | PROTECTED | 4 |
| `dataset_versions` | PROTECTED | 22 |
| `datasets` | PROTECTED | 19 |
| `deployed_model_versions` | KEEP | 27 |
| `environment_packages` | KEEP | 5 |
| `errors` | KEEP | 8 |
| `evaluation_ensemble_members` | NEW | 5 |
| `evaluations` | NEW | 35 |
| `execution_logs` | KEEP | 7 |
| `experiment_execution_events` | KEEP | 5 |
| `experiment_execution_gate` | KEEP | 6 |
| `experimental_campaigns` | KEEP | 20 |
| `experiments` | KEEP | 7 |
| `explainability_results` | REFACTOR | 16 |
| `identity_evidence` | PROTECTED | 10 |
| `image_analysis_jobs` | KEEP | 24 |
| `image_connected_components` | KEEP | 21 |
| `image_ingestion_batches` | KEEP | 16 |
| `image_quality_assessments` | KEEP | 39 |
| `local_execution_jobs` | KEEP | 15 |
| `microscopy_analysis_events` | KEEP | 11 |
| `microscopy_analysis_run_images` | KEEP | 11 |
| `microscopy_analysis_runs` | KEEP | 25 |
| `microscopy_images` | KEEP | 36 |
| `model_governance_backfill_audit` | KEEP | 14 |
| `model_versions` | KEEP | 27 |
| `models` | PROTECTED | 13 |
| `predictions` | REFACTOR | 42 |
| `quality_assessment_queue_items` | KEEP | 14 |
| `quality_gate_decisions` | KEEP | 6 |
| `research_subjects` | KEEP | 15 |
| `roles` | PROTECTED | 3 |
| `run_checkpoint_policy` | KEEP | 26 |
| `run_clinical_metrics` | REFACTOR | 32 |
| `run_configurations` | NEW | 37 |
| `run_dataset_images` | KEEP | 16 |
| `run_image_predictions` | KEEP | 21 |
| `run_io_records` | KEEP | 18 |
| `run_lineage` | KEEP | 10 |
| `run_metrics` | REFACTOR | 11 |
| `run_model_deployments` | KEEP | 9 |
| `run_threshold_calibration` | REFACTOR | 35 |
| `runs` | REFACTOR | 58 |
| `schema_migrations` | KEEP | 4 |
| `scientific_cases` | KEEP | 15 |
| `scientific_reviews` | KEEP | 7 |
| `scientific_validation_annotation_events` | KEEP | 9 |
| `scientific_validation_annotations` | KEEP | 13 |
| `scientific_validation_classification_runs` | KEEP | 3 |
| `scientific_validation_detection_runs` | KEEP | 3 |
| `scientific_validation_images` | KEEP | 5 |
| `scientific_validation_sessions` | KEEP | 16 |
| `smear_analysis_summaries` | KEEP | 18 |
| `smear_slides` | KEEP | 16 |
| `stage2_model_publication_events` | KEEP | 14 |
| `stage2_model_publications` | REFACTOR | 16 |
| `synthetic_data_runs` | KEEP | 10 |
| `train_execution_records` | KEEP | 8 |
| `train_execution_revisions` | KEEP | 4 |
| `train_execution_sessions` | KEEP | 16 |
| `training_history` | REFACTOR | 25 |
| `user_roles` | PROTECTED | 3 |
| `users` | PROTECTED | 9 |
| `xai_artifacts` | NEW | 16 |
| `xai_evidence` | NEW | 33 |
| `xai_interpretations` | NEW | 7 |
| `xai_quantitative_evaluations` | NEW | 19 |
| `xai_specialist_reviews` | NEW | 7 |

## Vistas

- `classification_reports`
- `confusion_matrices`
- `inference_runs`
- `legacy_cell_predictions`
- `vw_case_level_explainability`
- `vw_checkpoint_policy_summary`
- `vw_clinical_run_summary`
- `vw_dataset_browser_images`
- `vw_dataset_browser_summary`
- `vw_dataset_split_images_summary`
- `vw_explainability_summary`
- `vw_model_run_summary`
- `vw_run_artifacts_summary`
- `vw_run_dashboard`
- `vw_run_dataset_usage_summary`
- `vw_run_image_predictions_summary`
- `vw_run_io_summary`
- `vw_run_lineage`
- `vw_threshold_calibration_summary`
- `vw_uploaded_predictions`
- `vw_v2_external_evidence`
- `vw_v2_model_comparison`
- `vw_v2_run_metrics`
- `vw_v2_xai_comparison`
- `vw_visual_explainability_audit`
- `vw_case_type_summary`
- `vw_clinical_inference_predictions`
- `vw_evaluation_lineage`
- `vw_explainability_gallery`
- `vw_explainability_lineage`
- `vw_false_negative_cases`
- `vw_false_positive_cases`
- `vw_low_confidence_cases`

## Funciones propias

- `public.assessment_attempt_guard`
- `public.assessment_canonical`
- `public.assessment_consumer_guard`
- `public.assessment_identity_guard`
- `public.assessment_immutable`
- `public.assessment_result_guard`
- `public.campaign_attempt_state`
- `public.campaign_audit`
- `public.campaign_catalog_identity_guard`
- `public.campaign_configuration_guard`
- `public.campaign_environment_identity`
- `public.campaign_guard`
- `public.campaign_json_integer`
- `public.campaign_json_object`
- `public.campaign_json_string`
- `public.campaign_member_guard`
- `public.campaign_model_matches`
- `public.controlled_binding_guard`
- `public.controlled_pause_guard`
- `public.controlled_run_guard`
- `public.enforce_activation_materialization_consistency`
- `public.enforce_dataset_assignment_consistency`
- `public.enforce_dataset_version_lifecycle`
- `public.enforce_model_version_governance`
- `public.enforce_run_lineage_governance`
- `public.execution_event_immutable`
- `public.experiment_require_owner`
- `public.prevent_audit_event_mutation`
- `public.prevent_model_governance_audit_mutation`
- `public.prevent_stage2_publication_event_mutation`
- `public.prevent_validation_annotation_event_mutation`
- `public.prevent_validation_membership_mutation`
- `public.protect_cell_classification_run`
- `public.protect_cell_detection_run_identity`
- `public.protect_cell_explanation`
- `public.protect_deployed_model_version_payload`
- `public.protect_frozen_dataset_assignment_updates`
- `public.protect_frozen_dataset_assignments`
- `public.protect_frozen_dataset_version_sources`
- `public.protect_governed_artifact_identity`
- `public.protect_validation_annotation`
- `public.protect_validation_snapshot`
- `public.reject_cell_analysis_row_mutation`
- `public.reject_cell_classification_row_mutation`
- `public.train_record_guard`
- `public.train_revision_binding_guard`
- `public.train_session_guard`
- `public.v2_binary_metric_guard`
- `public.v2_calibration_pair_guard`
- `public.v2_configuration_guard`
- `public.v2_evaluation_complete`
- `public.v2_immutable`
- `public.v2_run_configuration_required`
- `public.v2_xai_artifact_guard`
- `public.v2_xai_artifact_source_guard`
- `public.v2_xai_comparison_guard`
- `public.v2_xai_lineage_guard`
- `public.validate_cell_classification_input_snapshot`
- `public.validate_cell_classification_insert_state`
- `public.validate_cell_classification_review`
- `public.validate_cell_classification_run_snapshot`
- `public.validate_cell_explanation_contract`
- `public.validate_cell_prediction_input`
- `public.validate_deployed_model_version`
- `public.validate_image_analysis_job`
- `public.validate_run_model_deployment`
- `public.validate_smear_analysis_summary`
- `public.assessment_structural_hash`
- `public.campaign_attempt_guard`
- `public.campaign_configuration_valid`
- `public.campaign_run_identity_guard`
- `public.campaign_technical_guard`
- `public.experiment_reservation_guard`
- `public.train_event_guard`
- `public.campaign_contract_valid`

## Triggers de aplicación

- `artifacts.trg_artifacts_protect_governed_identity`
- `assessment_artifacts.assessment_artifact_guard`
- `assessment_attempts.assessment_attempt_guard`
- `assessment_attempts.global_assessment_reservation`
- `assessment_campaign_consumers.assessment_consumer_guard`
- `assessment_campaign_consumers.assessment_consumer_immutable`
- `assessment_final_locks.assessment_lock_immutable`
- `assessment_identities.assessment_identity_guard`
- `assessment_identities.assessment_identity_immutable`
- `assessment_results.assessment_result_guard`
- `audit_events.audit_events_append_only`
- `campaign_attempts.campaign_attempt_audit`
- `campaign_attempts.campaign_attempt_guard`
- `campaign_attempts.campaign_attempt_state`
- `campaign_attempts.global_attempt_reservation`
- `campaign_configurations.campaign_configuration_audit`
- `campaign_configurations.campaign_configuration_guard`
- `campaign_controlled_requests.controlled_binding_guard` — constraint trigger; diferible=True, inicialmente diferido=True
- `campaign_controlled_requests.controlled_request_guard`
- `campaign_members.campaign_member_audit`
- `campaign_members.campaign_member_guard`
- `campaign_technical_revisions.technical_revision_guard`
- `cell_classification_events.trg_cell_classification_events_append_only`
- `cell_classification_inputs.trg_cell_classification_inputs_append_only`
- `cell_classification_inputs.trg_cell_classification_inputs_insert_state`
- `cell_classification_inputs.trg_cell_classification_inputs_snapshot`
- `cell_classification_reviews.trg_cell_classification_reviews_append_only`
- `cell_classification_reviews.trg_cell_classification_reviews_validate`
- `cell_classification_runs.trg_cell_classification_runs_protected`
- `cell_classification_runs.trg_cell_classification_runs_snapshot`
- `cell_crops.trg_cell_crops_append_only`
- `cell_detection_events.trg_cell_detection_events_append_only`
- `cell_detection_runs.trg_cell_detection_runs_immutable_identity`
- `cell_detections.trg_cell_detections_append_only`
- `cell_explanations.trg_cell_explanations_contract`
- `cell_explanations.trg_cell_explanations_protected`
- `cell_predictions.trg_cell_predictions_append_only`
- `cell_predictions.trg_cell_predictions_insert_state`
- `cell_predictions.trg_cell_predictions_validate_input`
- `dataset_materialization_activations.trg_activation_materialization_consistency`
- `dataset_split_assignments.trg_dataset_assignment_consistency`
- `dataset_split_assignments.trg_protect_frozen_dataset_assignment_updates`
- `dataset_split_assignments.trg_protect_frozen_dataset_assignments_delete`
- `dataset_version_sources.trg_protect_frozen_dataset_version_sources`
- `dataset_versions.trg_dataset_version_lifecycle`
- `deployed_model_versions.trg_deployed_model_versions_10_immutable`
- `deployed_model_versions.trg_deployed_model_versions_20_validate`
- `experiment_execution_events.global_execution_event_immutable`
- `experimental_campaigns.campaign_audit`
- `experimental_campaigns.campaign_guard`
- `experimental_campaigns.controlled_pause_guard`
- `image_analysis_jobs.trg_image_analysis_jobs_validate`
- `image_connected_components.trg_image_connected_components_append_only`
- `model_governance_backfill_audit.trg_model_governance_audit_append_only`
- `model_versions.trg_model_versions_governance`
- `models.campaign_catalog_identity_guard`
- `run_lineage.trg_run_lineage_governance`
- `run_model_deployments.trg_run_model_deployments_validate`
- `runs.campaign_run_identity_guard`
- `runs.controlled_run_guard`
- `scientific_reviews.trg_scientific_reviews_append_only`
- `scientific_validation_annotation_events.trg_validation_annotation_events_append_only`
- `scientific_validation_annotations.trg_validation_annotation_protected`
- `scientific_validation_classification_runs.trg_validation_classification_runs_immutable`
- `scientific_validation_detection_runs.trg_validation_detection_runs_immutable`
- `scientific_validation_images.trg_validation_images_immutable`
- `scientific_validation_sessions.trg_validation_snapshot_protected`
- `smear_analysis_summaries.trg_smear_analysis_summaries_append_only`
- `smear_analysis_summaries.trg_smear_analysis_summaries_insert_state`
- `smear_analysis_summaries.trg_smear_analysis_summaries_validate`
- `stage2_model_publication_events.trg_stage2_publication_events_append_only`
- `train_execution_records.a_train_event_guard`
- `train_execution_records.train_record_guard`
- `train_execution_revisions.train_execution_revision_immutable`
- `train_execution_revisions.train_revision_binding_guard` — constraint trigger; diferible=True, inicialmente diferido=True
- `train_execution_sessions.global_train_reservation`
- `train_execution_sessions.train_session_guard`
- `run_clinical_metrics.v2_binary_metric_guard`
- `run_configurations.v2_config_immutable`
- `evaluations.v2_evaluation_immutable`
- `run_clinical_metrics.v2_metric_immutable`
- `evaluation_ensemble_members.v2_ensemble_immutable`
- `evaluations.v2_evaluation_complete` — constraint trigger; diferible=True, inicialmente diferido=True
- `evaluation_ensemble_members.v2_ensemble_complete` — constraint trigger; diferible=True, inicialmente diferido=True
- `xai_evidence.v2_xai_immutable`
- `xai_quantitative_evaluations.v2_xai_quantitative_immutable`
- `xai_interpretations.v2_xai_interpretation_immutable`
- `xai_specialist_reviews.v2_xai_review_immutable`
- `xai_artifacts.v2_xai_artifact_guard`
- `xai_evidence.v2_xai_lineage_guard`
- `run_configurations.v2_configuration_guard`
- `xai_quantitative_evaluations.v2_xai_comparison_guard`
- `run_threshold_calibration.v2_calibration_pair_guard` — constraint trigger; diferible=True, inicialmente diferido=True
- `runs.v2_run_configuration_required` — constraint trigger; diferible=True, inicialmente diferido=True
- `xai_artifacts.v2_xai_artifact_source_guard`

## Índices independientes

- `uq_artifacts_id_run_id`
- `uq_cell_crops_id_detection`
- `uq_deployed_model_versions_id_version`
- `uq_image_analysis_jobs_identity`
- `uq_microscopy_analysis_equivalent`
- `uq_model_versions_id_checkpoint_artifact`
- `uq_model_versions_id_training_run`
- `uq_run_model_deployments_binding`
- `uq_run_model_deployments_run_deployment_version`
- `uq_run_threshold_calibration_id_version`
- `uq_stage2_model_publications_id_version`
- `idx_artifacts_artifact_type`
- `idx_artifacts_checksum`
- `idx_artifacts_governance_status`
- `idx_artifacts_metadata_source`
- `idx_artifacts_run_id`
- `idx_artifacts_type_path`
- `idx_artifacts_uri`
- `uq_assessment_live`
- `uq_global_assessment_active`
- `ix_audit_events_actor`
- `ix_audit_events_created_at`
- `ix_audit_events_resource`
- `ix_blood_samples_case`
- `ix_blood_samples_status_created`
- `uq_blood_samples_external_identity`
- `ix_campaign_attempt_state`
- `uq_campaign_one_active_attempt`
- `ix_campaign_member_state`
- `ix_cell_classification_events_run_created`
- `ix_cell_classification_events_run_detection`
- `ix_cell_classification_events_run_prediction`
- `ix_cell_classification_inputs_crop`
- `ix_cell_classification_inputs_detection`
- `ix_cell_classification_inputs_run_eligible_order`
- `ix_cell_classification_inputs_run_image_cell`
- `ix_cell_classification_reviews_actor_created`
- `ix_cell_classification_reviews_prediction_created`
- `ix_cell_classification_runs_analysis_created`
- `ix_cell_classification_runs_detection_created`
- `ix_cell_classification_runs_model_created`
- `ix_cell_classification_runs_status_created`
- `uq_cell_classification_runs_equivalent_active`
- `ix_cell_detection_events_run_created`
- `ix_cell_detection_events_run_image`
- `ix_cell_detection_runs_analysis_created`
- `ix_cell_detection_runs_status_created`
- `uq_cell_detection_runs_equivalent_active`
- `ix_cell_detections_run_image`
- `ix_cell_explanations_status_created`
- `ix_cell_predictions_crop`
- `ix_cell_predictions_detection`
- `ix_cell_predictions_run_label`
- `ix_cell_predictions_run_near_threshold`
- `ix_cell_predictions_run_status`
- `ix_dataset_materialization_activations_dataset_version_id`
- `ix_dataset_materialization_activations_materialization_id`
- `uq_dataset_materialization_activations_current_family`
- `ix_dataset_materializations_dataset_version_id`
- `ix_dataset_source_records_clinical_identity_id`
- `ix_dataset_source_records_dataset_id`
- `ix_dataset_source_records_decoded_pixel_sha256`
- `ix_dataset_source_records_source_file_sha256`
- `ix_dataset_split_assignments_clinical_identity_id`
- `ix_dataset_split_assignments_dataset_version_id`
- `idx_dataset_split_images_class`
- `idx_dataset_split_images_dataset_dir`
- `idx_dataset_split_images_dataset_id`
- `idx_dataset_split_images_relative_path`
- `idx_dataset_split_images_split`
- `ix_dataset_split_images_dataset_materialization_id`
- `ix_dataset_split_images_dataset_version_id`
- `ix_dataset_split_statistics_version_metric`
- `ix_dataset_split_validation_checks_version_name`
- `ix_dataset_version_sources_dataset_id`
- `ix_dataset_versions_status`
- `idx_datasets_metadata_gin`
- `idx_deployed_model_versions_checkpoint_artifact`
- `idx_deployed_model_versions_model_version`
- `idx_deployed_model_versions_slot_history`
- `idx_deployed_model_versions_status`
- `idx_deployed_model_versions_threshold_calibration`
- `uq_deployed_model_versions_active_slot`
- `uq_deployed_model_versions_one_production_champion`
- `idx_environment_packages_run_id`
- `idx_errors_run_id`
- `idx_execution_logs_run_id`
- `ix_campaign_dataset_state`
- `idx_explainability_case_method`
- `idx_explainability_method`
- `idx_explainability_output_path`
- `idx_explainability_run_id`
- `idx_explainability_success`
- `ix_identity_evidence_clinical_identity_id`
- `ix_identity_evidence_source_record_id`
- `idx_image_analysis_jobs_deployment`
- `idx_image_analysis_jobs_input_artifact`
- `idx_image_analysis_jobs_model_version`
- `idx_image_analysis_jobs_run`
- `idx_image_analysis_jobs_source_image`
- `idx_image_analysis_jobs_status_created`
- `uq_image_analysis_jobs_idempotency`
- `ix_image_connected_components_run_image`
- `ix_image_connected_components_status`
- `ix_ingestion_batches_sample`
- `uq_ingestion_batches_source_group`
- `local_one_active`
- `ix_microscopy_analysis_events_run`
- `ix_microscopy_analysis_runs_status`
- `ix_microscopy_analysis_runs_subject`
- `ix_microscopy_images_ingestion_batch`
- `ix_microscopy_images_sha256`
- `ix_microscopy_images_slide`
- `ix_microscopy_images_status_created`
- `uq_microscopy_images_external_path`
- `idx_model_governance_audit_batch`
- `idx_model_governance_audit_record`
- `idx_model_governance_audit_reversal`
- `idx_model_versions_checkpoint_artifact`
- `idx_model_versions_model`
- `idx_model_versions_sha256`
- `idx_model_versions_status_lineage`
- `idx_model_versions_training_run`
- `uq_model_versions_checkpoint_artifact`
- `uq_model_versions_name_number`
- `uq_model_versions_training_version_name`
- `uq_model_versions_unjustified_sha256`
- `idx_predictions_analysis_job`
- `idx_predictions_case_type`
- `idx_predictions_case_type_run`
- `idx_predictions_classifier_model_version`
- `idx_predictions_created_at`
- `idx_predictions_deployed_model_version`
- `idx_predictions_detector_model_version`
- `idx_predictions_inference_run`
- `idx_predictions_metadata_source`
- `idx_predictions_metadata_workflow`
- `idx_predictions_model_version`
- `idx_predictions_predicted_label`
- `idx_predictions_review_status`
- `idx_predictions_run_id`
- `idx_predictions_true_pred`
- `uq_predictions_job_cell_index`
- `ix_quality_queue_order`
- `ix_quality_queue_priority_requested`
- `uq_quality_queue_active_run`
- `ix_quality_gate_decisions_run`
- `ix_research_subjects_status_created`
- `uq_research_subjects_external_identity`
- `idx_run_checkpoint_policy_artifact`
- `idx_run_checkpoint_policy_model_version`
- `idx_run_checkpoint_policy_run_id`
- `idx_run_clinical_metrics_model_name`
- `idx_run_clinical_metrics_run_id`
- `idx_run_clinical_metrics_split_name`
- `idx_run_dataset_images_image_id`
- `idx_run_dataset_images_run_id`
- `idx_run_dataset_images_split`
- `idx_run_dataset_images_usage_context`
- `idx_run_image_predictions_case_type`
- `idx_run_image_predictions_run_id`
- `idx_run_image_predictions_split`
- `idx_run_io_records_clinical_metadata_gin`
- `idx_run_io_records_created_at`
- `idx_run_io_records_model_metadata_gin`
- `idx_run_io_records_model_name`
- `idx_run_io_records_run_id`
- `idx_run_io_records_run_type`
- `idx_run_io_records_script_name`
- `ix_run_io_records_dataset_materialization_id`
- `ix_run_io_records_dataset_version_id`
- `idx_run_lineage_checkpoint_artifact`
- `idx_run_lineage_checkpoint_path`
- `idx_run_lineage_child_run_id`
- `idx_run_lineage_model_version`
- `idx_run_lineage_parent_run_id`
- `idx_run_lineage_relationship_type`
- `uq_run_lineage_single_evaluation_training_parent`
- `idx_run_metrics_name`
- `idx_run_metrics_run_id`
- `idx_run_model_deployments_deployment`
- `idx_run_model_deployments_model_version`
- `uq_run_model_deployments_primary`
- `idx_run_threshold_calibration_artifact`
- `idx_run_threshold_calibration_model_version`
- `idx_run_threshold_calibration_run_id`
- `idx_runs_dataset_id`
- `idx_runs_execution_parameters_gin`
- `idx_runs_execution_type`
- `idx_runs_inference_script`
- `idx_runs_metadata_gin`
- `idx_runs_model_id`
- `idx_runs_parameters_gin`
- `idx_runs_run_type`
- `idx_runs_started_at`
- `idx_runs_status`
- `idx_runs_training_release_status`
- `ix_runs_dataset_version_id`
- `uq_runs_single_productive_stage2`
- `ix_scientific_cases_status_created`
- `ix_scientific_cases_subject`
- `ix_scientific_reviews_actor_created`
- `ix_scientific_reviews_entity_created`
- `ix_validation_annotation_events_actor_created`
- `ix_validation_annotation_events_annotation_created`
- `ix_validation_annotations_general_target`
- `ix_validation_annotations_session_analysis`
- `ix_validation_annotations_session_category`
- `ix_validation_annotations_session_cell`
- `ix_validation_annotations_session_created`
- `ix_validation_annotations_session_sample`
- `ix_validation_sessions_creator_created`
- `ix_validation_sessions_status_created`
- `ix_smear_analysis_summaries_analysis_created`
- `ix_smear_analysis_summaries_detection_created`
- `ix_smear_analysis_summaries_outcome_created`
- `ix_smear_slides_sample`
- `ix_smear_slides_status_created`
- `idx_stage2_publication_events_publication`
- `idx_stage2_publication_candidates`
- `uq_stage2_publication_active_version`
- `train_event_id_unique`
- `train_event_sequence_unique`
- `uq_global_train_active`
- `idx_training_history_run_id`
- `uq_evaluation_final_training`
- `ix_evaluation_comparison`
- `ix_xai_same_image`
- `ix_xai_evaluation`

## Roles y estado inicial

- Owner de objetos: `pg_v2_migrator`, owner de la base aislada, sin superuser/CREATEROLE/CREATEDB/REPLICATION/BYPASSRLS ni memberships.
- Runtime: `pg_v2_runtime`, distinto, sin esos privilegios ni memberships. USAGE de public; DML de tablas de aplicación bajo sus guards; sólo SELECT de schema_migrations y vistas; USAGE/SELECT de la secuencia. Sin DDL, TEMP, TRUNCATE ni escritura de alembic_version.
- EXECUTE de funciones propias sólo para runtime y owner; se retira PUBLIC. Los permisos de funciones incorporadas de pgcrypto conservan la política de la extensión confiable; no se intenta reasignar su ownership administrativo.
- Único seed: fila libre de experiment_execution_gate. No se crean usuarios, roles de aplicación, modelos, datasets ni filas ficticias de schema_migrations.
- Los roles administrativos se provisionarán exclusivamente en la futura instancia aislada después de Gate A. La revisión no ejecuta CREATE ROLE ni cambia roles operativos.
