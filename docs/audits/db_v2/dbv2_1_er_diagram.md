# DBV2.1 — ER completo

104 tablas de aplicación. Alembic administrará su ledger técnico por separado. Cada arista es una FK; relaciones N:M se detallan en el CSV.

```mermaid
erDiagram
    artifacts {
        uuid id PK
    }
    runs o|..o{ artifacts : "artifacts_run_id_fkey"
    assessment_artifacts {
        uuid attempt_id PK
        uuid sample_id PK
        text role PK
    }
    assessment_attempts ||..o{ assessment_artifacts : "assessment_artifacts_attempt_id_fkey"
    assessment_attempts {
        uuid id PK
    }
    assessment_identities ||..o{ assessment_attempts : "assessment_attempts_identity_id_fkey"
    assessment_campaign_consumers {
        uuid campaign_id PK
        uuid member_id PK
        uuid identity_id PK
    }
    experimental_campaigns ||..o{ assessment_campaign_consumers : "assessment_campaign_consumers_campaign_id_fkey"
    assessment_identities ||..o{ assessment_campaign_consumers : "assessment_campaign_consumers_identity_id_fkey"
    campaign_members ||..o{ assessment_campaign_consumers : "assessment_campaign_consumers_member_id_fkey"
    assessment_final_locks {
        uuid id PK
    }
    assessment_identities {
        uuid id PK
    }
    runs ||..o{ assessment_identities : "assessment_identities_training_run_id_fkey"
    assessment_results {
        uuid attempt_id PK
        uuid sample_id PK
    }
    assessment_attempts ||..o{ assessment_results : "assessment_results_attempt_id_fkey"
    audit_events {
        uuid id PK
    }
    users o|..o{ audit_events : "audit_events_actor_user_id_fkey"
    blood_samples {
        uuid id PK
    }
    users o|..o{ blood_samples : "blood_samples_archived_by_fkey"
    scientific_cases ||..o{ blood_samples : "blood_samples_case_id_fkey"
    users ||..o{ blood_samples : "blood_samples_created_by_fkey"
    users o|..o{ blood_samples : "blood_samples_updated_by_fkey"
    campaign_attempts {
        uuid id PK
    }
    campaign_members ||..o{ campaign_attempts : "campaign_attempts_member_id_fkey"
    runs o|..o| campaign_attempts : "campaign_attempts_training_run_id_fkey"
    campaign_configurations {
        uuid campaign_id PK
        text configuration_hash PK
    }
    experimental_campaigns ||..o{ campaign_configurations : "campaign_configurations_campaign_id_fkey"
    campaign_controlled_requests {
        uuid id PK
    }
    campaign_attempts ||..o| campaign_controlled_requests : "campaign_controlled_requests_attempt_id_fkey"
    experimental_campaigns ||..o{ campaign_controlled_requests : "campaign_controlled_requests_campaign_id_fkey"
    campaign_technical_revisions ||..o{ campaign_controlled_requests : "campaign_controlled_requests_campaign_id_revision_id_fkey"
    campaign_members ||..o{ campaign_controlled_requests : "campaign_controlled_requests_member_id_fkey"
    campaign_attempts ||..o| campaign_controlled_requests : "campaign_controlled_requests_previous_attempt_id_fkey"
    runs ||..o| campaign_controlled_requests : "campaign_controlled_requests_run_id_fkey"
    campaign_execution_events {
        uuid id PK
    }
    experimental_campaigns ||..o{ campaign_execution_events : "campaign_execution_events_campaign_id_fkey"
    campaign_members {
        uuid id PK
    }
    campaign_configurations ||..o{ campaign_members : "campaign_members_campaign_id_configuration_hash_fkey"
    experimental_campaigns ||..o{ campaign_members : "campaign_members_campaign_id_fkey"
    campaign_attempts o|..o| campaign_members : "fk_member_accepted_attempt"
    campaign_technical_revisions {
        uuid id PK
    }
    experimental_campaigns ||..o{ campaign_technical_revisions : "campaign_technical_revisions_campaign_id_fkey"
    cell_classification_events {
        uuid id PK
    }
    cell_detections o|..o{ cell_classification_events : "cell_classification_events_cell_detection_id_fkey"
    cell_classification_runs ||..o{ cell_classification_events : "cell_classification_events_classification_run_id_fkey"
    cell_predictions o|..o{ cell_classification_events : "fk_cell_classification_event_prediction"
    cell_classification_inputs {
        uuid id PK
    }
    cell_crops o|..o{ cell_classification_inputs : "fk_cell_classification_input_crop"
    cell_detections ||..o{ cell_classification_inputs : "fk_cell_classification_input_detection"
    cell_classification_runs ||..o{ cell_classification_inputs : "fk_cell_classification_input_run_detection"
    cell_classification_reviews {
        uuid id PK
    }
    users ||..o{ cell_classification_reviews : "cell_classification_reviews_actor_user_id_fkey"
    cell_predictions ||..o{ cell_classification_reviews : "cell_classification_reviews_cell_prediction_id_fkey"
    cell_classification_runs {
        uuid id PK
    }
    users ||..o{ cell_classification_runs : "cell_classification_runs_requested_by_fkey"
    cell_classification_runs o|..o{ cell_classification_runs : "cell_classification_runs_retry_of_run_id_fkey"
    deployed_model_versions ||..o{ cell_classification_runs : "fk_cell_classification_run_deployment_version"
    cell_detection_runs ||..o{ cell_classification_runs : "fk_cell_classification_run_detection_analysis"
    stage2_model_publications ||..o{ cell_classification_runs : "fk_cell_classification_run_publication_version"
    cell_crops {
        uuid id PK
    }
    cell_detections ||..o| cell_crops : "fk_cell_crops_detection"
    cell_detection_events {
        uuid id PK
    }
    cell_detection_runs ||..o{ cell_detection_events : "cell_detection_events_detection_run_id_fkey"
    microscopy_images o|..o{ cell_detection_events : "cell_detection_events_microscopy_image_id_fkey"
    cell_detection_runs {
        uuid id PK
    }
    microscopy_analysis_runs ||..o{ cell_detection_runs : "cell_detection_runs_analysis_run_id_fkey"
    users ||..o{ cell_detection_runs : "cell_detection_runs_requested_by_fkey"
    cell_detections {
        uuid id PK
    }
    image_connected_components ||..o| cell_detections : "fk_cell_detections_component"
    cell_detection_runs ||..o{ cell_detections : "fk_cell_detections_run_analysis"
    cell_explanations {
        uuid id PK
    }
    cell_predictions ||..o| cell_explanations : "cell_explanations_cell_prediction_id_fkey"
    cell_predictions {
        uuid id PK
    }
    cell_classification_inputs ||..o| cell_predictions : "fk_cell_prediction_input_owner"
    clinical_identities {
        uuid id PK
    }
    datasets ||..o{ clinical_identities : "clinical_identities_dataset_id_fkey"
    dataset_materialization_activations {
        uuid id PK
    }
    dataset_versions ||..o{ dataset_materialization_activations : "dataset_materialization_activations_dataset_version_id_fkey"
    dataset_materializations ||..o{ dataset_materialization_activations : "dataset_materialization_activations_materialization_id_fkey"
    dataset_materializations {
        uuid id PK
    }
    dataset_versions ||..o{ dataset_materializations : "dataset_materializations_dataset_version_id_fkey"
    dataset_source_records {
        uuid id PK
    }
    clinical_identities o|..o{ dataset_source_records : "dataset_source_records_clinical_identity_id_fkey"
    datasets ||..o{ dataset_source_records : "dataset_source_records_dataset_id_fkey"
    dataset_split_assignments {
        uuid id PK
    }
    clinical_identities ||..o{ dataset_split_assignments : "dataset_split_assignments_clinical_identity_id_fkey"
    dataset_versions ||..o{ dataset_split_assignments : "dataset_split_assignments_dataset_version_id_fkey"
    dataset_source_records ||..o{ dataset_split_assignments : "dataset_split_assignments_source_record_id_fkey"
    dataset_split_images {
        uuid image_id PK
    }
    datasets o|..o{ dataset_split_images : "dataset_split_images_dataset_id_fkey"
    dataset_materializations o|..o{ dataset_split_images : "dataset_split_images_dataset_materialization_id_fkey"
    dataset_versions o|..o{ dataset_split_images : "dataset_split_images_dataset_version_id_fkey"
    dataset_split_statistics {
        uuid id PK
    }
    dataset_versions ||..o{ dataset_split_statistics : "dataset_split_statistics_dataset_version_id_fkey"
    dataset_split_validation_checks {
        uuid id PK
    }
    dataset_versions ||..o{ dataset_split_validation_checks : "dataset_split_validation_checks_dataset_version_id_fkey"
    dataset_splits {
        uuid id PK
    }
    datasets o|..o{ dataset_splits : "dataset_splits_dataset_id_fkey"
    dataset_version_sources {
        uuid dataset_version_id PK
        uuid dataset_id PK
        text role PK
    }
    datasets ||..o{ dataset_version_sources : "dataset_version_sources_dataset_id_fkey"
    dataset_versions ||..o{ dataset_version_sources : "dataset_version_sources_dataset_version_id_fkey"
    dataset_versions {
        uuid id PK
    }
    datasets {
        uuid id PK
    }
    deployed_model_versions {
        uuid id PK
    }
    deployed_model_versions o|..o{ deployed_model_versions : "fk_deployed_model_versions_rollback"
    deployed_model_versions o|..o{ deployed_model_versions : "fk_deployed_model_versions_supersedes"
    run_threshold_calibration o|..o{ deployed_model_versions : "fk_deployed_model_versions_threshold_version"
    model_versions ||..o{ deployed_model_versions : "fk_deployed_model_versions_version_artifact"
    environment_packages {
        uuid id PK
    }
    runs o|..o{ environment_packages : "environment_packages_run_id_fkey"
    errors {
        uuid id PK
    }
    runs o|..o{ errors : "errors_run_id_fkey"
    evaluation_ensemble_members {
        uuid evaluation_id PK
        integer ordinal PK
    }
    evaluations ||..o{ evaluation_ensemble_members : "v2_evaluation_ensemble_members_foreign_a402d28a70f6"
    model_versions ||..o{ evaluation_ensemble_members : "v2_evaluation_ensemble_members_foreign_b946b2b207f3"
    artifacts ||..o{ evaluation_ensemble_members : "v2_evaluation_ensemble_members_foreign_6aec504c7a2f"
    evaluations {
        uuid id PK
    }
    train_execution_records o|..o{ evaluations : "fk_evaluation_e10_record"
    runs ||..o{ evaluations : "v2_evaluations_foreign_db5338c19de4"
    runs ||..o{ evaluations : "v2_evaluations_foreign_4e6a43d876af"
    artifacts o|..o{ evaluations : "v2_evaluations_foreign_6aec504c7a2f"
    dataset_versions ||..o{ evaluations : "v2_evaluations_foreign_14b20ff24e12"
    assessment_attempts o|..o{ evaluations : "v2_evaluations_foreign_c764adede219"
    run_threshold_calibration o|..o{ evaluations : "v2_evaluations_foreign_0baa7d166e2f"
    model_versions o|..o{ evaluations : "v2_evaluations_foreign_6cfcdf2998f5"
    dataset_version_sources o|..o{ evaluations : "fk_v2_evaluation_dataset_origin"
    execution_logs {
        uuid id PK
    }
    runs o|..o{ execution_logs : "execution_logs_run_id_fkey"
    experiment_execution_events {
        bigint id PK
    }
    experiment_execution_gate {
        boolean singleton PK
    }
    experimental_campaigns {
        uuid id PK
    }
    audit_events ||..o{ experimental_campaigns : "experimental_campaigns_dataset_evidence_id_fkey"
    dataset_versions ||..o{ experimental_campaigns : "experimental_campaigns_dataset_version_id_fkey"
    experiments o|..o{ experimental_campaigns : "experimental_campaigns_experiment_id_fkey"
    experiments {
        uuid id PK
    }
    explainability_results {
        uuid id PK
    }
    predictions o|..o{ explainability_results : "explainability_results_prediction_id_fkey"
    runs o|..o{ explainability_results : "explainability_results_run_id_fkey"
    identity_evidence {
        uuid id PK
    }
    clinical_identities ||..o{ identity_evidence : "identity_evidence_clinical_identity_id_fkey"
    dataset_source_records ||..o{ identity_evidence : "identity_evidence_source_record_id_fkey"
    image_analysis_jobs {
        uuid id PK
    }
    artifacts o|..o{ image_analysis_jobs : "fk_image_analysis_jobs_input_artifact"
    run_model_deployments ||..o{ image_analysis_jobs : "fk_image_analysis_jobs_run_deployment_version"
    dataset_split_images o|..o{ image_analysis_jobs : "fk_image_analysis_jobs_source_image"
    image_connected_components {
        uuid id PK
    }
    cell_detection_runs ||..o{ image_connected_components : "fk_components_detection_analysis"
    microscopy_analysis_run_images ||..o{ image_connected_components : "fk_components_frozen_image"
    image_ingestion_batches {
        uuid id PK
    }
    scientific_cases ||..o{ image_ingestion_batches : "image_ingestion_batches_case_id_fkey"
    users ||..o{ image_ingestion_batches : "image_ingestion_batches_created_by_fkey"
    blood_samples ||..o{ image_ingestion_batches : "image_ingestion_batches_sample_id_fkey"
    smear_slides ||..o{ image_ingestion_batches : "image_ingestion_batches_slide_id_fkey"
    research_subjects ||..o{ image_ingestion_batches : "image_ingestion_batches_subject_id_fkey"
    image_quality_assessments {
        uuid id PK
    }
    microscopy_analysis_runs ||..o{ image_quality_assessments : "image_quality_assessments_analysis_run_id_fkey"
    microscopy_analysis_run_images ||..o| image_quality_assessments : "image_quality_assessments_analysis_run_image_id_analysis_r_fkey"
    microscopy_images ||..o{ image_quality_assessments : "image_quality_assessments_microscopy_image_id_fkey"
    local_execution_jobs {
        uuid id PK
    }
    experimental_campaigns ||..o{ local_execution_jobs : "local_execution_jobs_campaign_id_fkey"
    runs o|..o| local_execution_jobs : "local_execution_jobs_run_id_fkey"
    microscopy_analysis_events {
        uuid id PK
    }
    microscopy_analysis_runs ||..o{ microscopy_analysis_events : "microscopy_analysis_events_analysis_run_id_fkey"
    microscopy_images o|..o{ microscopy_analysis_events : "microscopy_analysis_events_microscopy_image_id_fkey"
    microscopy_analysis_run_images {
        uuid id PK
    }
    microscopy_analysis_runs ||..o{ microscopy_analysis_run_images : "microscopy_analysis_run_images_analysis_run_id_fkey"
    microscopy_images ||..o{ microscopy_analysis_run_images : "microscopy_analysis_run_images_microscopy_image_id_fkey"
    microscopy_analysis_runs {
        uuid id PK
    }
    scientific_cases ||..o{ microscopy_analysis_runs : "microscopy_analysis_runs_case_id_fkey"
    image_ingestion_batches ||..o{ microscopy_analysis_runs : "microscopy_analysis_runs_ingestion_batch_id_fkey"
    users ||..o{ microscopy_analysis_runs : "microscopy_analysis_runs_requested_by_fkey"
    blood_samples ||..o{ microscopy_analysis_runs : "microscopy_analysis_runs_sample_id_fkey"
    smear_slides ||..o{ microscopy_analysis_runs : "microscopy_analysis_runs_slide_id_fkey"
    research_subjects ||..o{ microscopy_analysis_runs : "microscopy_analysis_runs_subject_id_fkey"
    microscopy_images {
        uuid id PK
    }
    users o|..o{ microscopy_images : "microscopy_images_archived_by_fkey"
    users ||..o{ microscopy_images : "microscopy_images_created_by_fkey"
    image_ingestion_batches o|..o{ microscopy_images : "microscopy_images_ingestion_batch_id_fkey"
    smear_slides ||..o{ microscopy_images : "microscopy_images_slide_id_fkey"
    users o|..o{ microscopy_images : "microscopy_images_updated_by_fkey"
    model_versions {
        uuid id PK
    }
    artifacts o|..o{ model_versions : "fk_model_versions_checkpoint_artifact_owner"
    models o|..o{ model_versions : "model_versions_model_id_fkey"
    runs o|..o{ model_versions : "model_versions_training_run_id_fkey"
    models {
        uuid id PK
    }
    predictions {
        uuid id PK
    }
    image_analysis_jobs o|..o{ predictions : "fk_predictions_analysis_job"
    model_versions o|..o{ predictions : "fk_predictions_classifier_model_version"
    artifacts o|..o{ predictions : "fk_predictions_crop_artifact"
    deployed_model_versions o|..o{ predictions : "fk_predictions_deployed_model_version"
    model_versions o|..o{ predictions : "fk_predictions_detector_model_version"
    artifacts o|..o{ predictions : "fk_predictions_explanation_artifact"
    runs o|..o{ predictions : "fk_predictions_inference_run"
    image_analysis_jobs o|..o{ predictions : "fk_predictions_job_provenance"
    model_versions o|..o{ predictions : "fk_predictions_model_version"
    dataset_split_images o|..o{ predictions : "fk_predictions_source_image"
    datasets o|..o{ predictions : "predictions_dataset_id_fkey"
    runs o|..o{ predictions : "predictions_run_id_fkey"
    evaluations o|..o{ predictions : "fk_v2_prediction_evaluation_run"
    evaluations o|..o{ predictions : "v2_predictions_foreign_a402d28a70f6"
    dataset_source_records o|..o{ predictions : "v2_predictions_foreign_e8d9af78807c"
    quality_assessment_queue_items {
        uuid id PK
    }
    microscopy_analysis_runs ||..o{ quality_assessment_queue_items : "quality_assessment_queue_items_analysis_run_id_fkey"
    users ||..o{ quality_assessment_queue_items : "quality_assessment_queue_items_requested_by_fkey"
    quality_gate_decisions {
        uuid id PK
    }
    users ||..o{ quality_gate_decisions : "quality_gate_decisions_actor_user_id_fkey"
    microscopy_analysis_runs ||..o{ quality_gate_decisions : "quality_gate_decisions_analysis_run_id_fkey"
    research_subjects {
        uuid id PK
    }
    users o|..o{ research_subjects : "research_subjects_archived_by_fkey"
    users o|..o{ research_subjects : "research_subjects_created_by_fkey"
    users o|..o{ research_subjects : "research_subjects_updated_by_fkey"
    roles {
        uuid id PK
    }
    run_checkpoint_policy {
        uuid run_checkpoint_policy_id PK
    }
    artifacts o|..o{ run_checkpoint_policy : "fk_run_checkpoint_policy_artifact_owner"
    model_versions o|..o{ run_checkpoint_policy : "fk_run_checkpoint_policy_model_version_owner"
    model_versions o|..o{ run_checkpoint_policy : "fk_run_checkpoint_policy_version_artifact"
    runs ||..o{ run_checkpoint_policy : "run_checkpoint_policy_run_id_fkey"
    run_clinical_metrics {
        uuid run_clinical_metric_id PK
    }
    models o|..o{ run_clinical_metrics : "run_clinical_metrics_model_id_fkey"
    runs ||..o{ run_clinical_metrics : "run_clinical_metrics_run_id_fkey"
    evaluations ||..o| run_clinical_metrics : "fk_metric_evaluation_run"
    run_configurations {
        uuid run_id PK
    }
    runs ||..o| run_configurations : "v2_run_configurations_foreign_db5338c19de4"
    run_dataset_images {
        uuid run_dataset_image_id PK
    }
    dataset_split_images ||..o{ run_dataset_images : "run_dataset_images_image_id_fkey"
    runs ||..o{ run_dataset_images : "run_dataset_images_run_id_fkey"
    run_image_predictions {
        uuid run_image_prediction_id PK
    }
    dataset_split_images o|..o{ run_image_predictions : "run_image_predictions_image_id_fkey"
    runs ||..o{ run_image_predictions : "run_image_predictions_run_id_fkey"
    run_io_records {
        uuid run_io_id PK
    }
    dataset_materializations o|..o{ run_io_records : "run_io_records_dataset_materialization_id_fkey"
    dataset_versions o|..o{ run_io_records : "run_io_records_dataset_version_id_fkey"
    runs ||..o{ run_io_records : "run_io_records_run_id_fkey"
    run_lineage {
        uuid id PK
    }
    artifacts o|..o{ run_lineage : "fk_run_lineage_checkpoint_artifact_owner"
    model_versions o|..o{ run_lineage : "fk_run_lineage_model_version_owner"
    model_versions o|..o{ run_lineage : "fk_run_lineage_version_artifact"
    runs ||..o{ run_lineage : "run_lineage_child_run_id_fkey"
    runs ||..o{ run_lineage : "run_lineage_parent_run_id_fkey"
    run_metrics {
        uuid id PK
    }
    runs o|..o{ run_metrics : "run_metrics_run_id_fkey"
    run_model_deployments {
        uuid id PK
    }
    deployed_model_versions ||..o{ run_model_deployments : "fk_run_model_deployments_deployment_version"
    runs ||..o{ run_model_deployments : "fk_run_model_deployments_run"
    run_threshold_calibration {
        uuid run_threshold_calibration_id PK
    }
    artifacts o|..o{ run_threshold_calibration : "fk_run_threshold_calibration_artifact_owner"
    model_versions o|..o{ run_threshold_calibration : "fk_run_threshold_calibration_model_version"
    runs ||..o{ run_threshold_calibration : "run_threshold_calibration_run_id_fkey"
    evaluations ||..o{ run_threshold_calibration : "v2_run_threshold_calibration_foreign_014acc59cdbd"
    evaluations ||..o{ run_threshold_calibration : "v2_run_threshold_calibration_foreign_0ba3287c0955"
    runs {
        uuid id PK
    }
    experimental_campaigns o|..o{ runs : "runs_campaign_id_fkey"
    datasets o|..o{ runs : "runs_dataset_id_fkey"
    dataset_versions o|..o{ runs : "runs_dataset_version_id_fkey"
    experiments o|..o{ runs : "runs_experiment_id_fkey"
    models o|..o{ runs : "runs_model_id_fkey"
    scientific_cases {
        uuid id PK
    }
    users o|..o{ scientific_cases : "scientific_cases_archived_by_fkey"
    users ||..o{ scientific_cases : "scientific_cases_created_by_fkey"
    research_subjects o|..o{ scientific_cases : "scientific_cases_subject_id_fkey"
    users o|..o{ scientific_cases : "scientific_cases_updated_by_fkey"
    scientific_reviews {
        uuid id PK
    }
    users ||..o{ scientific_reviews : "scientific_reviews_actor_user_id_fkey"
    cell_detections ||..o{ scientific_reviews : "scientific_reviews_entity_id_fkey"
    scientific_validation_annotation_events {
        uuid id PK
    }
    scientific_validation_sessions o|..o{ scientific_validation_annotation_events : "scientific_validation_annotation_eve_validation_session_id_fkey"
    users ||..o{ scientific_validation_annotation_events : "scientific_validation_annotation_events_actor_user_id_fkey"
    scientific_validation_annotations ||..o{ scientific_validation_annotation_events : "scientific_validation_annotation_events_annotation_id_fkey"
    scientific_validation_annotations {
        uuid id PK
    }
    microscopy_analysis_runs o|..o{ scientific_validation_annotations : "scientific_validation_annotations_analysis_run_id_fkey"
    cell_detections o|..o{ scientific_validation_annotations : "scientific_validation_annotations_cell_detection_id_fkey"
    users ||..o{ scientific_validation_annotations : "scientific_validation_annotations_created_by_fkey"
    blood_samples o|..o{ scientific_validation_annotations : "scientific_validation_annotations_sample_id_fkey"
    users ||..o{ scientific_validation_annotations : "scientific_validation_annotations_updated_by_fkey"
    scientific_validation_sessions o|..o{ scientific_validation_annotations : "scientific_validation_annotations_validation_session_id_fkey"
    scientific_validation_classification_runs {
        uuid session_id PK
        uuid classification_run_id PK
    }
    cell_classification_runs ||..o{ scientific_validation_classification_runs : "scientific_validation_classification_classification_run_id_fkey"
    scientific_validation_sessions ||..o{ scientific_validation_classification_runs : "scientific_validation_classification_runs_session_id_fkey"
    scientific_validation_detection_runs {
        uuid session_id PK
        uuid detection_run_id PK
    }
    cell_detection_runs ||..o{ scientific_validation_detection_runs : "scientific_validation_detection_runs_detection_run_id_fkey"
    scientific_validation_sessions ||..o{ scientific_validation_detection_runs : "scientific_validation_detection_runs_session_id_fkey"
    scientific_validation_images {
        uuid session_id PK
        uuid microscopy_image_id PK
    }
    microscopy_images ||..o{ scientific_validation_images : "scientific_validation_images_microscopy_image_id_fkey"
    scientific_validation_sessions ||..o{ scientific_validation_images : "scientific_validation_images_session_id_fkey"
    scientific_validation_sessions {
        uuid id PK
    }
    users o|..o{ scientific_validation_sessions : "scientific_validation_sessions_archived_by_fkey"
    users ||..o{ scientific_validation_sessions : "scientific_validation_sessions_created_by_fkey"
    users ||..o{ scientific_validation_sessions : "scientific_validation_sessions_updated_by_fkey"
    smear_analysis_summaries {
        uuid id PK
    }
    cell_classification_runs ||..o| smear_analysis_summaries : "fk_smear_summary_classification_lineage"
    smear_slides {
        uuid id PK
    }
    users o|..o{ smear_slides : "smear_slides_archived_by_fkey"
    users ||..o{ smear_slides : "smear_slides_created_by_fkey"
    blood_samples ||..o{ smear_slides : "smear_slides_sample_id_fkey"
    users o|..o{ smear_slides : "smear_slides_updated_by_fkey"
    stage2_model_publication_events {
        uuid id PK
    }
    stage2_model_publications ||..o{ stage2_model_publication_events : "stage2_model_publication_events_publication_id_fkey"
    stage2_model_publications {
        uuid id PK
    }
    runs ||..o{ stage2_model_publications : "fk_stage2_publication_evaluation"
    runs ||..o{ stage2_model_publications : "fk_stage2_publication_training"
    model_versions ||..o{ stage2_model_publications : "fk_stage2_publication_version_artifact"
    model_versions ||..o{ stage2_model_publications : "fk_stage2_publication_model_training"
    synthetic_data_runs {
        uuid id PK
    }
    runs o|..o{ synthetic_data_runs : "synthetic_data_runs_run_id_fkey"
    datasets o|..o{ synthetic_data_runs : "synthetic_data_runs_source_dataset_id_fkey"
    train_execution_records {
        uuid run_id PK
        text kind PK
        text phase PK
        text record_key PK
    }
    train_execution_sessions ||..o{ train_execution_records : "train_execution_records_run_id_fkey"
    train_execution_revisions {
        uuid attempt_id PK
    }
    campaign_attempts ||..o| train_execution_revisions : "train_execution_revisions_attempt_id_fkey"
    experimental_campaigns ||..o{ train_execution_revisions : "train_execution_revisions_campaign_id_fkey"
    campaign_technical_revisions ||..o{ train_execution_revisions : "train_execution_revisions_campaign_id_revision_id_fkey"
    train_execution_sessions {
        uuid run_id PK
    }
    campaign_attempts o|..o| train_execution_sessions : "train_execution_sessions_attempt_id_fkey"
    runs ||..o| train_execution_sessions : "train_execution_sessions_run_id_fkey"
    training_history {
        uuid id PK
    }
    runs ||..o{ training_history : "training_history_run_id_fkey"
    user_roles {
        uuid user_id PK
        uuid role_id PK
    }
    roles ||..o{ user_roles : "user_roles_role_id_fkey"
    users ||..o{ user_roles : "user_roles_user_id_fkey"
    users {
        uuid id PK
    }
    xai_artifacts {
        uuid id PK
    }
    xai_evidence ||..o{ xai_artifacts : "v2_xai_artifacts_foreign_4b080b42e888"
    artifacts o|..o{ xai_artifacts : "v2_xai_artifacts_foreign_e3d2eb574718"
    assessment_artifacts o|..o{ xai_artifacts : "v2_xai_artifacts_foreign_f9c5548be835"
    xai_evaluation_members {
        uuid evaluation_id PK
        uuid xai_evidence_id PK
    }
    xai_quantitative_evaluations ||..o{ xai_evaluation_members : "fk_xai_member_evaluation"
    xai_evidence ||..o{ xai_evaluation_members : "fk_xai_member_evidence"
    xai_evaluation_protocols {
        uuid id PK
    }
    xai_evidence {
        uuid id PK
    }
    explainability_results o|..o| xai_evidence : "v2_xai_evidence_foreign_9851edbb8079"
    cell_explanations o|..o| xai_evidence : "v2_xai_evidence_foreign_3fe88bd35854"
    predictions o|..o{ xai_evidence : "v2_xai_evidence_foreign_4b04405ab069"
    cell_predictions o|..o{ xai_evidence : "v2_xai_evidence_foreign_029e07f1d6db"
    evaluations o|..o{ xai_evidence : "v2_xai_evidence_foreign_a402d28a70f6"
    dataset_source_records o|..o{ xai_evidence : "v2_xai_evidence_foreign_e8d9af78807c"
    artifacts o|..o{ xai_evidence : "v2_xai_evidence_foreign_a1c9b824423e"
    microscopy_images o|..o{ xai_evidence : "v2_xai_evidence_foreign_ad1ea3f78d92"
    runs o|..o{ xai_evidence : "v2_xai_evidence_foreign_db5338c19de4"
    model_versions o|..o{ xai_evidence : "v2_xai_evidence_foreign_b946b2b207f3"
    artifacts ||..o{ xai_evidence : "v2_xai_evidence_foreign_6aec504c7a2f"
    assessment_results o|..o| xai_evidence : "v2_xai_evidence_foreign_52bd313b1c15"
    xai_method_configurations ||..o{ xai_evidence : "fk_xai_method_configuration"
    xai_interpretations {
        uuid id PK
    }
    xai_evidence ||..o{ xai_interpretations : "v2_xai_interpretations_foreign_4b080b42e888"
    users ||..o{ xai_interpretations : "v2_xai_interpretations_foreign_6b09f9926d4f"
    xai_interpretations o|..o{ xai_interpretations : "v2_xai_interpretations_foreign_af451d74af77"
    xai_method_configurations {
        uuid id PK
    }
    xai_quantitative_evaluations {
        uuid id PK
    }
    xai_evaluation_protocols ||..o{ xai_quantitative_evaluations : "fk_xai_metric_protocol"
    scientific_validation_annotations o|..o{ xai_quantitative_evaluations : "fk_xai_reference_annotation"
    xai_region_attributions {
        uuid xai_evidence_id PK
        text region_type PK
        integer region_index PK
    }
    xai_evidence ||..o{ xai_region_attributions : "fk_xai_region_evidence"
    xai_specialist_reviews {
        uuid id PK
    }
    xai_interpretations ||..o{ xai_specialist_reviews : "v2_xai_specialist_reviews_foreign_4735bf604cb2"
    users ||..o{ xai_specialist_reviews : "v2_xai_specialist_reviews_foreign_7ca01df9e490"
```

La FK describe cardinalidad máxima: 1:1 no impone por sí sola existencia de un hijo. Los triggers diferidos imponen completitud donde corresponde (E-04, evaluación, XAI).
N:M explícitas:
- `users` ↔ `roles` por `user_roles`.
- `dataset_versions` ↔ `datasets` por `dataset_version_sources`.
- `dataset_versions` ↔ `dataset_source_records` por `dataset_split_assignments`.
- `evaluations` ↔ `model_versions` por `evaluation_ensemble_members`.
- `xai_quantitative_evaluations` ↔ `xai_evidence` por `xai_evaluation_members`.
- `runs` ↔ `dataset_split_images` por `run_dataset_images`.
- `runs` ↔ `deployed_model_versions` por `run_model_deployments`.
- `scientific_validation_sessions` ↔ `microscopy_images` por `scientific_validation_images`.
- `scientific_validation_sessions` ↔ `cell_detection_runs` por `scientific_validation_detection_runs`.
- `scientific_validation_sessions` ↔ `cell_classification_runs` por `scientific_validation_classification_runs`.
- `experimental_campaigns` ↔ `assessment_identities` por `assessment_campaign_consumers`.
