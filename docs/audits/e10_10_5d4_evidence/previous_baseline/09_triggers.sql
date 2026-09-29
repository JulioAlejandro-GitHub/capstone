-- E10.10.5A frozen Alembic resource. Execute only through the guarded v2 environment.
CREATE TRIGGER trg_artifacts_protect_governed_identity BEFORE UPDATE ON artifacts FOR EACH ROW EXECUTE PROCEDURE protect_governed_artifact_identity();

CREATE TRIGGER assessment_artifact_guard BEFORE INSERT OR DELETE OR UPDATE ON assessment_artifacts FOR EACH ROW EXECUTE PROCEDURE assessment_result_guard();

CREATE TRIGGER assessment_attempt_guard BEFORE INSERT OR DELETE OR UPDATE ON assessment_attempts FOR EACH ROW EXECUTE PROCEDURE assessment_attempt_guard();

CREATE TRIGGER global_assessment_reservation BEFORE INSERT OR UPDATE ON assessment_attempts FOR EACH ROW EXECUTE PROCEDURE experiment_reservation_guard();

CREATE TRIGGER assessment_consumer_guard BEFORE INSERT ON assessment_campaign_consumers FOR EACH ROW EXECUTE PROCEDURE assessment_consumer_guard();

CREATE TRIGGER assessment_consumer_immutable BEFORE DELETE OR UPDATE ON assessment_campaign_consumers FOR EACH ROW EXECUTE PROCEDURE assessment_immutable();

CREATE TRIGGER assessment_lock_immutable BEFORE DELETE OR UPDATE ON assessment_final_locks FOR EACH ROW EXECUTE PROCEDURE assessment_immutable();

CREATE TRIGGER assessment_identity_guard BEFORE INSERT ON assessment_identities FOR EACH ROW EXECUTE PROCEDURE assessment_identity_guard();

CREATE TRIGGER assessment_identity_immutable BEFORE DELETE OR UPDATE ON assessment_identities FOR EACH ROW EXECUTE PROCEDURE assessment_immutable();

CREATE TRIGGER assessment_result_guard BEFORE INSERT OR DELETE OR UPDATE ON assessment_results FOR EACH ROW EXECUTE PROCEDURE assessment_result_guard();

CREATE TRIGGER audit_events_append_only BEFORE DELETE OR UPDATE ON audit_events FOR EACH ROW EXECUTE PROCEDURE prevent_audit_event_mutation();

CREATE TRIGGER campaign_attempt_audit AFTER INSERT OR UPDATE ON campaign_attempts FOR EACH ROW EXECUTE PROCEDURE campaign_audit();

CREATE TRIGGER campaign_attempt_guard BEFORE INSERT OR DELETE OR UPDATE ON campaign_attempts FOR EACH ROW EXECUTE PROCEDURE campaign_attempt_guard();

CREATE TRIGGER campaign_attempt_state AFTER INSERT OR UPDATE ON campaign_attempts FOR EACH ROW EXECUTE PROCEDURE campaign_attempt_state();

CREATE TRIGGER global_attempt_reservation BEFORE INSERT ON campaign_attempts FOR EACH ROW EXECUTE PROCEDURE experiment_reservation_guard();

CREATE TRIGGER campaign_configuration_audit AFTER INSERT OR DELETE OR UPDATE ON campaign_configurations FOR EACH ROW EXECUTE PROCEDURE campaign_audit();

CREATE TRIGGER campaign_configuration_guard BEFORE INSERT OR DELETE OR UPDATE ON campaign_configurations FOR EACH ROW EXECUTE PROCEDURE campaign_configuration_guard();

CREATE CONSTRAINT TRIGGER controlled_binding_guard AFTER INSERT ON campaign_controlled_requests DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE PROCEDURE controlled_binding_guard();

CREATE TRIGGER controlled_request_guard BEFORE INSERT OR DELETE OR UPDATE ON campaign_controlled_requests FOR EACH ROW EXECUTE PROCEDURE campaign_technical_guard();

CREATE TRIGGER campaign_member_audit AFTER INSERT OR DELETE OR UPDATE ON campaign_members FOR EACH ROW EXECUTE PROCEDURE campaign_audit();

CREATE TRIGGER campaign_member_guard BEFORE INSERT OR DELETE OR UPDATE ON campaign_members FOR EACH ROW EXECUTE PROCEDURE campaign_member_guard();

CREATE TRIGGER technical_revision_guard BEFORE INSERT OR DELETE OR UPDATE ON campaign_technical_revisions FOR EACH ROW EXECUTE PROCEDURE campaign_technical_guard();

CREATE TRIGGER trg_cell_classification_events_append_only BEFORE DELETE OR UPDATE ON cell_classification_events FOR EACH ROW EXECUTE PROCEDURE reject_cell_classification_row_mutation();

CREATE TRIGGER trg_cell_classification_inputs_append_only BEFORE DELETE OR UPDATE ON cell_classification_inputs FOR EACH ROW EXECUTE PROCEDURE reject_cell_classification_row_mutation();

CREATE TRIGGER trg_cell_classification_inputs_insert_state BEFORE INSERT ON cell_classification_inputs FOR EACH ROW EXECUTE PROCEDURE validate_cell_classification_insert_state();

CREATE TRIGGER trg_cell_classification_inputs_snapshot BEFORE INSERT ON cell_classification_inputs FOR EACH ROW EXECUTE PROCEDURE validate_cell_classification_input_snapshot();

CREATE TRIGGER trg_cell_classification_reviews_append_only BEFORE DELETE OR UPDATE ON cell_classification_reviews FOR EACH ROW EXECUTE PROCEDURE reject_cell_classification_row_mutation();

CREATE TRIGGER trg_cell_classification_reviews_validate BEFORE INSERT ON cell_classification_reviews FOR EACH ROW EXECUTE PROCEDURE validate_cell_classification_review();

CREATE TRIGGER trg_cell_classification_runs_protected BEFORE DELETE OR UPDATE ON cell_classification_runs FOR EACH ROW EXECUTE PROCEDURE protect_cell_classification_run();

CREATE TRIGGER trg_cell_classification_runs_snapshot BEFORE INSERT ON cell_classification_runs FOR EACH ROW EXECUTE PROCEDURE validate_cell_classification_run_snapshot();

CREATE TRIGGER trg_cell_crops_append_only BEFORE DELETE OR UPDATE ON cell_crops FOR EACH ROW EXECUTE PROCEDURE reject_cell_analysis_row_mutation();

CREATE TRIGGER trg_cell_detection_events_append_only BEFORE DELETE OR UPDATE ON cell_detection_events FOR EACH ROW EXECUTE PROCEDURE reject_cell_analysis_row_mutation();

CREATE TRIGGER trg_cell_detection_runs_immutable_identity BEFORE DELETE OR UPDATE ON cell_detection_runs FOR EACH ROW EXECUTE PROCEDURE protect_cell_detection_run_identity();

CREATE TRIGGER trg_cell_detections_append_only BEFORE DELETE OR UPDATE ON cell_detections FOR EACH ROW EXECUTE PROCEDURE reject_cell_analysis_row_mutation();

CREATE TRIGGER trg_cell_explanations_contract BEFORE INSERT OR UPDATE ON cell_explanations FOR EACH ROW EXECUTE PROCEDURE validate_cell_explanation_contract();

CREATE TRIGGER trg_cell_explanations_protected BEFORE DELETE OR UPDATE ON cell_explanations FOR EACH ROW EXECUTE PROCEDURE protect_cell_explanation();

CREATE TRIGGER trg_cell_predictions_append_only BEFORE DELETE OR UPDATE ON cell_predictions FOR EACH ROW EXECUTE PROCEDURE reject_cell_classification_row_mutation();

CREATE TRIGGER trg_cell_predictions_insert_state BEFORE INSERT ON cell_predictions FOR EACH ROW EXECUTE PROCEDURE validate_cell_classification_insert_state();

CREATE TRIGGER trg_cell_predictions_validate_input BEFORE INSERT ON cell_predictions FOR EACH ROW EXECUTE PROCEDURE validate_cell_prediction_input();

CREATE TRIGGER trg_activation_materialization_consistency BEFORE INSERT OR UPDATE ON dataset_materialization_activations FOR EACH ROW EXECUTE PROCEDURE enforce_activation_materialization_consistency();

CREATE TRIGGER trg_dataset_assignment_consistency BEFORE INSERT OR UPDATE ON dataset_split_assignments FOR EACH ROW EXECUTE PROCEDURE enforce_dataset_assignment_consistency();

CREATE TRIGGER trg_protect_frozen_dataset_assignment_updates BEFORE UPDATE ON dataset_split_assignments FOR EACH ROW EXECUTE PROCEDURE protect_frozen_dataset_assignment_updates();

CREATE TRIGGER trg_protect_frozen_dataset_assignments_delete BEFORE DELETE ON dataset_split_assignments FOR EACH ROW EXECUTE PROCEDURE protect_frozen_dataset_assignments();

CREATE TRIGGER trg_protect_frozen_dataset_version_sources BEFORE INSERT OR DELETE OR UPDATE ON dataset_version_sources FOR EACH ROW EXECUTE PROCEDURE protect_frozen_dataset_version_sources();

CREATE TRIGGER trg_dataset_version_lifecycle BEFORE UPDATE ON dataset_versions FOR EACH ROW EXECUTE PROCEDURE enforce_dataset_version_lifecycle();

CREATE TRIGGER trg_deployed_model_versions_10_immutable BEFORE UPDATE ON deployed_model_versions FOR EACH ROW EXECUTE PROCEDURE protect_deployed_model_version_payload();

CREATE TRIGGER trg_deployed_model_versions_20_validate BEFORE INSERT OR UPDATE ON deployed_model_versions FOR EACH ROW EXECUTE PROCEDURE validate_deployed_model_version();

CREATE TRIGGER global_execution_event_immutable BEFORE DELETE OR UPDATE ON experiment_execution_events FOR EACH ROW EXECUTE PROCEDURE execution_event_immutable();

CREATE TRIGGER campaign_audit AFTER INSERT OR UPDATE ON experimental_campaigns FOR EACH ROW EXECUTE PROCEDURE campaign_audit();

CREATE TRIGGER campaign_guard BEFORE INSERT OR DELETE OR UPDATE ON experimental_campaigns FOR EACH ROW EXECUTE PROCEDURE campaign_guard();

CREATE TRIGGER controlled_pause_guard BEFORE UPDATE ON experimental_campaigns FOR EACH ROW EXECUTE PROCEDURE controlled_pause_guard();

CREATE TRIGGER trg_image_analysis_jobs_validate BEFORE INSERT OR UPDATE ON image_analysis_jobs FOR EACH ROW EXECUTE PROCEDURE validate_image_analysis_job();

CREATE TRIGGER trg_image_connected_components_append_only BEFORE DELETE OR UPDATE ON image_connected_components FOR EACH ROW EXECUTE PROCEDURE reject_cell_analysis_row_mutation();

CREATE TRIGGER trg_model_governance_audit_append_only BEFORE DELETE OR UPDATE ON model_governance_backfill_audit FOR EACH ROW EXECUTE PROCEDURE prevent_model_governance_audit_mutation();

CREATE TRIGGER trg_model_versions_governance BEFORE INSERT OR UPDATE ON model_versions FOR EACH ROW EXECUTE PROCEDURE enforce_model_version_governance();

CREATE TRIGGER campaign_catalog_identity_guard BEFORE UPDATE ON models FOR EACH ROW EXECUTE PROCEDURE campaign_catalog_identity_guard();

CREATE TRIGGER trg_run_lineage_governance BEFORE INSERT OR UPDATE ON run_lineage FOR EACH ROW EXECUTE PROCEDURE enforce_run_lineage_governance();

CREATE TRIGGER trg_run_model_deployments_validate BEFORE INSERT OR UPDATE ON run_model_deployments FOR EACH ROW EXECUTE PROCEDURE validate_run_model_deployment();

CREATE TRIGGER campaign_run_identity_guard BEFORE UPDATE ON runs FOR EACH ROW EXECUTE PROCEDURE campaign_run_identity_guard();

CREATE TRIGGER controlled_run_guard BEFORE INSERT OR UPDATE ON runs FOR EACH ROW EXECUTE PROCEDURE controlled_run_guard();

CREATE TRIGGER trg_scientific_reviews_append_only BEFORE DELETE OR UPDATE ON scientific_reviews FOR EACH ROW EXECUTE PROCEDURE reject_cell_analysis_row_mutation();

CREATE TRIGGER trg_validation_annotation_events_append_only BEFORE DELETE OR UPDATE ON scientific_validation_annotation_events FOR EACH ROW EXECUTE PROCEDURE prevent_validation_annotation_event_mutation();

CREATE TRIGGER trg_validation_annotation_protected BEFORE DELETE OR UPDATE ON scientific_validation_annotations FOR EACH ROW EXECUTE PROCEDURE protect_validation_annotation();

CREATE TRIGGER trg_validation_classification_runs_immutable BEFORE DELETE OR UPDATE ON scientific_validation_classification_runs FOR EACH ROW EXECUTE PROCEDURE prevent_validation_membership_mutation();

CREATE TRIGGER trg_validation_detection_runs_immutable BEFORE DELETE OR UPDATE ON scientific_validation_detection_runs FOR EACH ROW EXECUTE PROCEDURE prevent_validation_membership_mutation();

CREATE TRIGGER trg_validation_images_immutable BEFORE DELETE OR UPDATE ON scientific_validation_images FOR EACH ROW EXECUTE PROCEDURE prevent_validation_membership_mutation();

CREATE TRIGGER trg_validation_snapshot_protected BEFORE DELETE OR UPDATE ON scientific_validation_sessions FOR EACH ROW EXECUTE PROCEDURE protect_validation_snapshot();

CREATE TRIGGER trg_smear_analysis_summaries_append_only BEFORE DELETE OR UPDATE ON smear_analysis_summaries FOR EACH ROW EXECUTE PROCEDURE reject_cell_classification_row_mutation();

CREATE TRIGGER trg_smear_analysis_summaries_insert_state BEFORE INSERT ON smear_analysis_summaries FOR EACH ROW EXECUTE PROCEDURE validate_cell_classification_insert_state();

CREATE TRIGGER trg_smear_analysis_summaries_validate BEFORE INSERT ON smear_analysis_summaries FOR EACH ROW EXECUTE PROCEDURE validate_smear_analysis_summary();

CREATE TRIGGER trg_stage2_publication_events_append_only BEFORE DELETE OR UPDATE ON stage2_model_publication_events FOR EACH ROW EXECUTE PROCEDURE prevent_stage2_publication_event_mutation();

CREATE TRIGGER a_train_event_guard BEFORE INSERT ON train_execution_records FOR EACH ROW EXECUTE PROCEDURE train_event_guard();

CREATE TRIGGER train_record_guard BEFORE INSERT OR DELETE OR UPDATE ON train_execution_records FOR EACH ROW EXECUTE PROCEDURE train_record_guard();

CREATE TRIGGER train_execution_revision_immutable BEFORE DELETE OR UPDATE ON train_execution_revisions FOR EACH ROW EXECUTE PROCEDURE execution_event_immutable();

CREATE CONSTRAINT TRIGGER train_revision_binding_guard AFTER INSERT ON train_execution_revisions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE PROCEDURE train_revision_binding_guard();

CREATE TRIGGER global_train_reservation BEFORE INSERT OR UPDATE ON train_execution_sessions FOR EACH ROW EXECUTE PROCEDURE experiment_reservation_guard();

CREATE TRIGGER train_session_guard BEFORE DELETE OR UPDATE ON train_execution_sessions FOR EACH ROW EXECUTE PROCEDURE train_session_guard();

CREATE TRIGGER v2_binary_metric_guard BEFORE INSERT ON public.run_clinical_metrics FOR EACH ROW EXECUTE PROCEDURE public.v2_binary_metric_guard();

CREATE TRIGGER v2_config_immutable BEFORE DELETE OR UPDATE ON public.run_configurations FOR EACH ROW EXECUTE PROCEDURE public.v2_immutable();

CREATE TRIGGER v2_evaluation_immutable BEFORE DELETE OR UPDATE ON public.evaluations FOR EACH ROW EXECUTE PROCEDURE public.v2_immutable();

CREATE TRIGGER v2_metric_immutable BEFORE DELETE OR UPDATE ON public.run_clinical_metrics FOR EACH ROW EXECUTE PROCEDURE public.v2_immutable();

CREATE TRIGGER v2_ensemble_immutable BEFORE DELETE OR UPDATE ON public.evaluation_ensemble_members FOR EACH ROW EXECUTE PROCEDURE public.v2_immutable();

CREATE CONSTRAINT TRIGGER v2_evaluation_complete AFTER INSERT ON public.evaluations DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE PROCEDURE public.v2_evaluation_complete();

CREATE CONSTRAINT TRIGGER v2_ensemble_complete AFTER INSERT ON public.evaluation_ensemble_members DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE PROCEDURE public.v2_evaluation_complete();

CREATE TRIGGER v2_xai_immutable BEFORE DELETE OR UPDATE ON public.xai_evidence FOR EACH ROW EXECUTE PROCEDURE public.v2_immutable();

CREATE TRIGGER v2_xai_quantitative_immutable BEFORE DELETE OR UPDATE ON public.xai_quantitative_evaluations FOR EACH ROW EXECUTE PROCEDURE public.v2_immutable();

CREATE TRIGGER v2_xai_interpretation_immutable BEFORE DELETE OR UPDATE ON public.xai_interpretations FOR EACH ROW EXECUTE PROCEDURE public.v2_immutable();

CREATE TRIGGER v2_xai_review_immutable BEFORE DELETE OR UPDATE ON public.xai_specialist_reviews FOR EACH ROW EXECUTE PROCEDURE public.v2_immutable();

CREATE TRIGGER v2_xai_artifact_guard BEFORE DELETE OR UPDATE ON public.xai_artifacts FOR EACH ROW EXECUTE PROCEDURE public.v2_xai_artifact_guard();

CREATE TRIGGER v2_xai_lineage_guard BEFORE INSERT ON public.xai_evidence FOR EACH ROW EXECUTE PROCEDURE public.v2_xai_lineage_guard();

CREATE TRIGGER v2_configuration_guard BEFORE INSERT ON public.run_configurations FOR EACH ROW EXECUTE PROCEDURE public.v2_configuration_guard();

CREATE TRIGGER v2_xai_comparison_guard BEFORE INSERT ON public.xai_quantitative_evaluations FOR EACH ROW EXECUTE PROCEDURE public.v2_xai_comparison_guard();

CREATE CONSTRAINT TRIGGER v2_calibration_pair_guard AFTER INSERT OR UPDATE ON public.run_threshold_calibration DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE PROCEDURE public.v2_calibration_pair_guard();

CREATE CONSTRAINT TRIGGER v2_run_configuration_required AFTER INSERT ON public.runs DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE PROCEDURE public.v2_run_configuration_required();

CREATE TRIGGER v2_xai_artifact_source_guard BEFORE INSERT ON public.xai_artifacts FOR EACH ROW EXECUTE PROCEDURE public.v2_xai_artifact_source_guard();

