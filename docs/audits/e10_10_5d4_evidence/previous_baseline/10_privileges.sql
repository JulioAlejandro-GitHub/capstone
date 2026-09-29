-- E10.10.5A frozen Alembic resource. Execute only through the guarded v2 environment.
DO $v2_acl$ BEGIN
 EXECUTE format('REVOKE ALL ON DATABASE %I FROM PUBLIC', current_database());
 EXECUTE format('REVOKE ALL ON DATABASE %I FROM capstone_v2_runtime', current_database());
 EXECUTE format('GRANT CONNECT ON DATABASE %I TO capstone_v2_runtime', current_database());
END $v2_acl$;

REVOKE ALL ON SCHEMA public FROM capstone_v2_runtime;

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC, capstone_v2_runtime;

REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC, capstone_v2_runtime;

GRANT USAGE ON SCHEMA public TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.artifacts TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.assessment_artifacts TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.assessment_attempts TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.assessment_campaign_consumers TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.assessment_final_locks TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.assessment_identities TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.assessment_results TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.audit_events TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.blood_samples TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.campaign_attempts TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.campaign_configurations TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.campaign_controlled_requests TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.campaign_execution_events TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.campaign_members TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.campaign_technical_revisions TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.cell_classification_events TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.cell_classification_inputs TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.cell_classification_reviews TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.cell_classification_runs TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.cell_crops TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.cell_detection_events TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.cell_detection_runs TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.cell_detections TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.cell_explanations TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.cell_predictions TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.clinical_identities TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.dataset_materialization_activations TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.dataset_materializations TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.dataset_source_records TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.dataset_split_assignments TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.dataset_split_images TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.dataset_split_statistics TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.dataset_split_validation_checks TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.dataset_splits TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.dataset_version_sources TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.dataset_versions TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.datasets TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.deployed_model_versions TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.environment_packages TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.errors TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.evaluation_ensemble_members TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.evaluations TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.execution_logs TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.experiment_execution_events TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.experiment_execution_gate TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.experimental_campaigns TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.experiments TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.explainability_results TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.identity_evidence TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.image_analysis_jobs TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.image_connected_components TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.image_ingestion_batches TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.image_quality_assessments TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.local_execution_jobs TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.microscopy_analysis_events TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.microscopy_analysis_run_images TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.microscopy_analysis_runs TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.microscopy_images TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.model_governance_backfill_audit TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.model_versions TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.models TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.predictions TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.quality_assessment_queue_items TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.quality_gate_decisions TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.research_subjects TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.roles TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.run_checkpoint_policy TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.run_clinical_metrics TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.run_configurations TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.run_dataset_images TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.run_image_predictions TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.run_io_records TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.run_lineage TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.run_metrics TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.run_model_deployments TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.run_threshold_calibration TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.runs TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.schema_migrations TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.scientific_cases TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.scientific_reviews TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.scientific_validation_annotation_events TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.scientific_validation_annotations TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.scientific_validation_classification_runs TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.scientific_validation_detection_runs TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.scientific_validation_images TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.scientific_validation_sessions TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.smear_analysis_summaries TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.smear_slides TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.stage2_model_publication_events TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.stage2_model_publications TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.synthetic_data_runs TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.train_execution_records TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.train_execution_revisions TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.train_execution_sessions TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.training_history TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.user_roles TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.users TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.xai_artifacts TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.xai_evidence TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.xai_interpretations TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.xai_quantitative_evaluations TO capstone_v2_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.xai_specialist_reviews TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.classification_reports TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.confusion_matrices TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.inference_runs TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.legacy_cell_predictions TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_case_level_explainability TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_case_type_summary TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_checkpoint_policy_summary TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_clinical_inference_predictions TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_clinical_run_summary TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_dataset_browser_images TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_dataset_browser_summary TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_dataset_split_images_summary TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_evaluation_lineage TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_explainability_gallery TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_explainability_lineage TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_explainability_summary TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_false_negative_cases TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_false_positive_cases TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_low_confidence_cases TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_model_run_summary TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_run_artifacts_summary TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_run_dashboard TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_run_dataset_usage_summary TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_run_image_predictions_summary TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_run_io_summary TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_run_lineage TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_threshold_calibration_summary TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_uploaded_predictions TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_v2_external_evidence TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_v2_model_comparison TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_v2_run_metrics TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_v2_xai_comparison TO capstone_v2_runtime;

GRANT SELECT ON TABLE public.vw_visual_explainability_audit TO capstone_v2_runtime;

GRANT USAGE, SELECT ON SEQUENCE public.experiment_execution_events_id_seq TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.assessment_attempt_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.assessment_attempt_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.assessment_canonical(jsonb) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.assessment_canonical(jsonb) TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.assessment_consumer_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.assessment_consumer_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.assessment_identity_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.assessment_identity_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.assessment_immutable() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.assessment_immutable() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.assessment_result_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.assessment_result_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.assessment_structural_hash(jsonb) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.assessment_structural_hash(jsonb) TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.campaign_attempt_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.campaign_attempt_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.campaign_attempt_state() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.campaign_attempt_state() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.campaign_audit() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.campaign_audit() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.campaign_catalog_identity_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.campaign_catalog_identity_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.campaign_configuration_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.campaign_configuration_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.campaign_configuration_valid(jsonb) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.campaign_configuration_valid(jsonb) TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.campaign_contract_valid(jsonb) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.campaign_contract_valid(jsonb) TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.campaign_environment_identity(jsonb) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.campaign_environment_identity(jsonb) TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.campaign_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.campaign_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.campaign_json_integer(jsonb, numeric) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.campaign_json_integer(jsonb, numeric) TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.campaign_json_object(jsonb, text[]) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.campaign_json_object(jsonb, text[]) TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.campaign_json_string(jsonb) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.campaign_json_string(jsonb) TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.campaign_member_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.campaign_member_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.campaign_model_matches(uuid, uuid) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.campaign_model_matches(uuid, uuid) TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.campaign_run_identity_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.campaign_run_identity_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.campaign_technical_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.campaign_technical_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.controlled_binding_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.controlled_binding_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.controlled_pause_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.controlled_pause_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.controlled_run_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.controlled_run_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.enforce_activation_materialization_consistency() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.enforce_activation_materialization_consistency() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.enforce_dataset_assignment_consistency() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.enforce_dataset_assignment_consistency() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.enforce_dataset_version_lifecycle() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.enforce_dataset_version_lifecycle() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.enforce_model_version_governance() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.enforce_model_version_governance() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.enforce_run_lineage_governance() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.enforce_run_lineage_governance() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.execution_event_immutable() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.execution_event_immutable() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.experiment_require_owner() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.experiment_require_owner() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.experiment_reservation_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.experiment_reservation_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.prevent_audit_event_mutation() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.prevent_audit_event_mutation() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.prevent_model_governance_audit_mutation() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.prevent_model_governance_audit_mutation() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.prevent_stage2_publication_event_mutation() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.prevent_stage2_publication_event_mutation() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.prevent_validation_annotation_event_mutation() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.prevent_validation_annotation_event_mutation() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.prevent_validation_membership_mutation() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.prevent_validation_membership_mutation() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.protect_cell_classification_run() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.protect_cell_classification_run() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.protect_cell_detection_run_identity() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.protect_cell_detection_run_identity() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.protect_cell_explanation() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.protect_cell_explanation() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.protect_deployed_model_version_payload() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.protect_deployed_model_version_payload() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.protect_frozen_dataset_assignment_updates() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.protect_frozen_dataset_assignment_updates() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.protect_frozen_dataset_assignments() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.protect_frozen_dataset_assignments() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.protect_frozen_dataset_version_sources() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.protect_frozen_dataset_version_sources() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.protect_governed_artifact_identity() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.protect_governed_artifact_identity() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.protect_validation_annotation() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.protect_validation_annotation() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.protect_validation_snapshot() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.protect_validation_snapshot() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.reject_cell_analysis_row_mutation() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.reject_cell_analysis_row_mutation() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.reject_cell_classification_row_mutation() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.reject_cell_classification_row_mutation() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.train_event_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.train_event_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.train_record_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.train_record_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.train_revision_binding_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.train_revision_binding_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.train_session_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.train_session_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.validate_cell_classification_input_snapshot() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.validate_cell_classification_input_snapshot() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.validate_cell_classification_insert_state() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.validate_cell_classification_insert_state() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.validate_cell_classification_review() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.validate_cell_classification_review() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.validate_cell_classification_run_snapshot() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.validate_cell_classification_run_snapshot() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.validate_cell_explanation_contract() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.validate_cell_explanation_contract() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.validate_cell_prediction_input() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.validate_cell_prediction_input() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.validate_deployed_model_version() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.validate_deployed_model_version() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.validate_image_analysis_job() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.validate_image_analysis_job() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.validate_run_model_deployment() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.validate_run_model_deployment() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.validate_smear_analysis_summary() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.validate_smear_analysis_summary() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.v2_binary_metric_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.v2_binary_metric_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.v2_immutable() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.v2_immutable() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.v2_evaluation_complete() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.v2_evaluation_complete() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.v2_xai_artifact_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.v2_xai_artifact_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.v2_xai_lineage_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.v2_xai_lineage_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.v2_configuration_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.v2_configuration_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.v2_xai_comparison_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.v2_xai_comparison_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.v2_calibration_pair_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.v2_calibration_pair_guard() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.v2_run_configuration_required() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.v2_run_configuration_required() TO capstone_v2_runtime;

REVOKE ALL ON FUNCTION public.v2_xai_artifact_source_guard() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.v2_xai_artifact_source_guard() TO capstone_v2_runtime;

REVOKE ALL ON TABLE public.alembic_version FROM PUBLIC, capstone_v2_runtime;

