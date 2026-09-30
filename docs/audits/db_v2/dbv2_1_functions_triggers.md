# DBV2.1 — Funciones y triggers

Inventario exhaustivo de candidatas y objetivo; cuerpos completos en el SQL. No hay algoritmos científicos nuevos. REQUIRED_DB_INVARIANT protege identidad, completitud, atomicidad o inmutabilidad; TECHNICAL implementa canonización/hash o soporte. SOFTWARE_RESPONSIBILITY comprende selección de configuración, ejecución de procesos, cálculo de métricas y gestión física de archivos: ninguna función candidata de este inventario ejecuta esos algoritmos.

E-04 conserva admisión SECURITY INVOKER, comparación NULL-safe, índices parciales y triggers diferidos. `v2_calibration_pair_guard` agrega concordancia con el objetivo de run_configurations. `v2_xai_comparison_guard` se reemplaza por completitud N:M. Las funciones de pgcrypto pertenecen a la extensión; no se copian como funciones propias.

| Función | Clasificación | Decisión | Garantía observable / motivo |
|---|---|---|---|
| assessment_attempt_guard | REQUIRED_DB_INVARIANT | KEEP | ASSESSMENT_HISTORY_IMMUTABLE; ASSESSMENT_INVALID_START; TEST_FINAL_LOCK_REQUIRED; ASSESSMENT_OWNER_FENCED; ASSESSMENT_INCOMPLETE |
| assessment_canonical | TECHNICAL | KEEP | Función auxiliar de identidad, consulta o transición atómica; definición completa en SQL. |
| assessment_consumer_guard | REQUIRED_DB_INVARIANT | KEEP | ASSESSMENT_CAMPAIGN_CONFLICT |
| assessment_identity_guard | REQUIRED_DB_INVARIANT | KEEP | ASSESSMENT_TRAIN_REQUIRED; ASSESSMENT_PROTOCOL_OR_SAMPLES_INVALID; ASSESSMENT_SAMPLE_INVALID |
| assessment_immutable | REQUIRED_DB_INVARIANT | KEEP | ASSESSMENT_HISTORY_IMMUTABLE |
| assessment_result_guard | REQUIRED_DB_INVARIANT | KEEP | ASSESSMENT_RESULT_IMMUTABLE; ASSESSMENT_OWNER_FENCED; ASSESSMENT_SAMPLE_CONFLICT; ASSESSMENT_PATIENT_CONFLICT; ASSESSMENT_PREDICTION_CONFLICT; ASSESSMENT_EXPLANATION_CONFLICT |
| assessment_structural_hash | TECHNICAL | KEEP | Función auxiliar de identidad, consulta o transición atómica; definición completa en SQL. |
| campaign_attempt_guard | REQUIRED_DB_INVARIANT | KEEP | ATTEMPT_HISTORY_IMMUTABLE; ATTEMPT_REQUIRES_FROZEN_CAMPAIGN; INVALID_NEW_ATTEMPT; ATTEMPT_IDENTITY_IMMUTABLE; INVALID_ATTEMPT_TRANSITION; TRAIN_EVIDENCE_REQUIRED; TRAIN_RELATIONAL_MODEL_CONFLICT; TRAIN_CAMPAIGN_CONTRACT_CONFLICT |
| campaign_attempt_state | REQUIRED_DB_INVARIANT | KEEP | Función auxiliar de identidad, consulta o transición atómica; definición completa en SQL. |
| campaign_audit | REQUIRED_DB_INVARIANT | KEEP | Función auxiliar de identidad, consulta o transición atómica; definición completa en SQL. |
| campaign_catalog_identity_guard | REQUIRED_DB_INVARIANT | KEEP | LINKED_MODEL_NAME_IMMUTABLE |
| campaign_configuration_guard | REQUIRED_DB_INVARIANT | KEEP | FROZEN_CONFIGURATION_IMMUTABLE; CONFIGURATION_IDENTITY_IMMUTABLE; CONFIGURATION_HASH_CONFLICT |
| campaign_configuration_valid | REQUIRED_DB_INVARIANT | KEEP | Función auxiliar de identidad, consulta o transición atómica; definición completa en SQL. |
| campaign_contract_valid | REQUIRED_DB_INVARIANT | KEEP | Función auxiliar de identidad, consulta o transición atómica; definición completa en SQL. |
| campaign_environment_identity | TECHNICAL | KEEP | Función auxiliar de identidad, consulta o transición atómica; definición completa en SQL. |
| campaign_guard | REQUIRED_DB_INVARIANT | KEEP | CAMPAIGN_DELETE_FORBIDDEN; CAMPAIGN_IDENTITY_IMMUTABLE; FROZEN_CAMPAIGN_IMMUTABLE; INVALID_CAMPAIGN_TRANSITION; CAMPAIGN_NOT_TERMINAL; CAMPAIGN_STARTS_DRAFT; CAMPAIGN_DATASET_EVIDENCE_CONFLICT; CAMPAIGN_HASH_CONFLICT; INCOMPLETE_FROZEN_MATRIX; INCOMPLETE_CONFIGURATION_SEED_GRID; INVALID_FROZEN_PROTOCOL; INCOMPLETE_SCIENTIFIC_PROTOCOL; INVALID_INITIAL_MEMBERS |
| campaign_json_integer | TECHNICAL | KEEP | Función auxiliar de identidad, consulta o transición atómica; definición completa en SQL. |
| campaign_json_object | TECHNICAL | KEEP | Función auxiliar de identidad, consulta o transición atómica; definición completa en SQL. |
| campaign_json_string | TECHNICAL | KEEP | Función auxiliar de identidad, consulta o transición atómica; definición completa en SQL. |
| campaign_member_guard | REQUIRED_DB_INVARIANT | KEEP | FROZEN_MEMBER_IMMUTABLE; MEMBERS_REQUIRE_DRAFT; MEMBER_IDENTITY_IMMUTABLE; FROZEN_MEMBER_IMMUTABLE; FIRST_VERIFIED_ATTEMPT_REQUIRED; MEMBER_STATE_MUST_FOLLOW_ATTEMPT |
| campaign_model_matches | REQUIRED_DB_INVARIANT | KEEP | Función auxiliar de identidad, consulta o transición atómica; definición completa en SQL. |
| campaign_run_identity_guard | REQUIRED_DB_INVARIANT | KEEP | LINKED_TRAIN_IDENTITY_IMMUTABLE |
| campaign_technical_guard | REQUIRED_DB_INVARIANT | KEEP | TECHNICAL_HISTORY_IMMUTABLE; PAUSED_CAMPAIGN_REQUIRED; TECHNICAL_REVISION_INVALID; TECHNICAL_ENVIRONMENT_CONFLICT; CONTROLLED_ATTEMPT_INELIGIBLE |
| controlled_binding_guard | REQUIRED_DB_INVARIANT | KEEP | CONTROLLED_BINDING_INVALID |
| controlled_pause_guard | REQUIRED_DB_INVARIANT | KEEP | CONTROLLED_TRAIN_REQUIRES_PAUSED |
| controlled_run_guard | REQUIRED_DB_INVARIANT | KEEP | CONTROLLED_CAMPAIGN_ID_REQUIRED; RUN_CAMPAIGN_IMMUTABLE |
| dbv21_xai_configuration_guard | TECHNICAL | NEW | XAI_CONFIGURATION_HASH_MISMATCH; XAI_PROTOCOL_HASH_MISMATCH |
| dbv21_xai_evaluation_complete | REQUIRED_DB_INVARIANT | NEW | dbv21_xai_evaluation_complete invoked from unsupported table: %; XAI_MEMBERSHIP_HASH_MISMATCH; XAI_EVALUATION_MEMBERS_REQUIRED; XAI_AGREEMENT_INCOMPATIBLE; XAI_LOCALIZATION_REFERENCE_REQUIRED; XAI_REFERENCE_VERSION_MISMATCH |
| e04_assert_calibration | REQUIRED_DB_INVARIANT | KEEP | E04_PAIR_REQUIRED; E04_PAIR_REQUIRED; E04_PAIR_IDENTITY_MISMATCH; E04_THRESHOLD_PROVENANCE; E04_EVENT_PROVENANCE; E04_CONTEXT_PROVENANCE; E04_METRIC_PROVENANCE; E04_METRIC_PROVENANCE; E04_PAIR_METRICS_REQUIRED |
| e04_calibration_complete | REQUIRED_DB_INVARIANT | KEEP | Función auxiliar de identidad, consulta o transición atómica; definición completa en SQL. |
| e04_calibration_immutable | REQUIRED_DB_INVARIANT | KEEP | E04_CALIBRATION_IMMUTABLE |
| e04_legacy_admission | REQUIRED_DB_INVARIANT | KEEP | E04_LEGACY_MIGRATOR_REQUIRED |
| enforce_activation_materialization_consistency | REQUIRED_DB_INVARIANT | KEEP | activation version differs from materialization version |
| enforce_dataset_assignment_consistency | REQUIRED_DB_INVARIANT | KEEP | assignments of a FROZEN dataset version are immutable; assignment clinical identity differs from source record identity; assignment class differs from source record class; patient is already assigned to split % in this dataset version |
| enforce_dataset_version_lifecycle | REQUIRED_DB_INVARIANT | KEEP | scientific fields of a FROZEN dataset version are immutable; invalid dataset version lifecycle transition: % -> % |
| enforce_model_version_governance | REQUIRED_DB_INVARIANT | KEEP | model_versions.training_run_id debe referenciar un run training; recibió % (%); El payload de una model_version gobernada es inmutable (%) |
| enforce_run_lineage_governance | REQUIRED_DB_INVARIANT | KEEP | evaluates_checkpoint_from exige parent training y child evaluation; recibió % -> %; explains_checkpoint_from exige parent training y child explainability; recibió % -> %; El linaje gobernado % exige model_version_id y checkpoint_artifact_id; Cambiar la identidad de linaje % exige model_version_id y checkpoint_artifact_id |
| execution_event_immutable | REQUIRED_DB_INVARIANT | KEEP | EXECUTION_HISTORY_IMMUTABLE |
| experiment_require_owner | REQUIRED_DB_INVARIANT | KEEP | GLOBAL_EXECUTION_OWNER_REQUIRED |
| experiment_reservation_guard | REQUIRED_DB_INVARIANT | KEEP | GLOBAL_TRAIN_ALREADY_ACTIVE; GLOBAL_ASSESSMENT_ALREADY_ACTIVE |
| prevent_audit_event_mutation | REQUIRED_DB_INVARIANT | KEEP | audit_events is append-only |
| prevent_model_governance_audit_mutation | LEGACY_REDUNDANT | REMOVE | La tabla de backfill histórico queda fuera de una instalación vacía. |
| prevent_stage2_publication_event_mutation | REQUIRED_DB_INVARIANT | KEEP | stage2_model_publication_events es append-only |
| prevent_validation_annotation_event_mutation | REQUIRED_DB_INVARIANT | KEEP | scientific validation annotation events are append-only |
| prevent_validation_membership_mutation | REQUIRED_DB_INVARIANT | KEEP | scientific validation membership is append-only |
| protect_cell_classification_run | REQUIRED_DB_INVARIANT | KEEP | cell_classification_runs cannot be deleted; terminal cell_classification_runs are immutable; invalid cell classification run transition; frozen classification inputs do not match run counters; invalid cell classification run transition; persisted predictions do not match run counters; completed classification run requires one immutable summary; classification run time cannot move backwards; classification run started_at is immutable once set; cell_classification_runs identity, model and inputs are immutable |
| protect_cell_detection_run_identity | REQUIRED_DB_INVARIANT | KEEP | cell_detection_runs cannot be deleted; terminal cell_detection_runs are immutable; invalid cell detection run transition; invalid cell detection run transition; cell_detection_runs identity and profile are immutable |
| protect_cell_explanation | REQUIRED_DB_INVARIANT | KEEP | cell_explanations cannot be deleted; cell explanation identity and parameters are immutable; terminal cell explanations are immutable; invalid cell explanation transition |
| protect_deployed_model_version_payload | REQUIRED_DB_INVARIANT | KEEP | El payload de deployed_model_versions es inmutable; cree una nueva revisión (%) |
| protect_frozen_dataset_assignment_updates | REQUIRED_DB_INVARIANT | KEEP | assignments of a FROZEN dataset version are immutable |
| protect_frozen_dataset_assignments | REQUIRED_DB_INVARIANT | KEEP | assignments of a FROZEN dataset version are immutable |
| protect_frozen_dataset_version_sources | REQUIRED_DB_INVARIANT | KEEP | source composition of a FROZEN dataset version is immutable |
| protect_governed_artifact_identity | REQUIRED_DB_INVARIANT | KEEP | No se puede mutar path/checksum/tamaño de un artifact ligado a model_version (%) |
| protect_validation_annotation | REQUIRED_DB_INVARIANT | KEEP | scientific validation annotations cannot be deleted; scientific validation annotation identity is immutable; scientific validation annotation version must advance once |
| protect_validation_snapshot | REQUIRED_DB_INVARIANT | KEEP | scientific validation snapshots cannot be deleted; scientific validation snapshot identity is immutable |
| reject_cell_analysis_row_mutation | REQUIRED_DB_INVARIANT | KEEP | cell analysis result and review rows are append-only |
| reject_cell_classification_row_mutation | REQUIRED_DB_INVARIANT | KEEP | cell classification inputs, predictions, summaries, events and reviews are append-only |
| train_event_guard | REQUIRED_DB_INVARIANT | KEEP | TRAIN_OWNER_FENCED; RESULT_EVENT_SEQUENCE_INVALID |
| train_record_guard | REQUIRED_DB_INVARIANT | KEEP | TRAIN_RECORD_IMMUTABLE; TRAIN_OWNER_FENCED |
| train_revision_binding_guard | REQUIRED_DB_INVARIANT | KEEP | TRAIN_REVISION_BINDING_INVALID |
| train_session_guard | REQUIRED_DB_INVARIANT | KEEP | TRAIN_HISTORY_IMMUTABLE; TRAIN_IDENTITY_IMMUTABLE; TRAIN_OWNER_FENCED; TRAIN_TRANSITION_INVALID; TRAIN_VERIFICATION_INCOMPLETE |
| v2_binary_metric_guard | REQUIRED_DB_INVARIANT | KEEP | METRIC_RUN_MISMATCH; SINGLE_CLASS_AUC |
| v2_calibration_pair_guard | REQUIRED_DB_INVARIANT | MODIFY | CALIBRATION_CONFIGURATION_TARGET_MISMATCH; CALIBRATION_PAIR_INVALID |
| v2_configuration_guard | REQUIRED_DB_INVARIANT | MODIFY | FROZEN_CONFIGURATION_MISMATCH |
| v2_evaluation_complete | REQUIRED_DB_INVARIANT | KEEP | EVALUATION_TRAIN_DATASET_MISMATCH; EVALUATION_METRICS_MISSING; CHECKPOINT_TRAIN_MISMATCH; CHECKPOINT_VERSION_MISMATCH; CALIBRATION_LINEAGE_MISMATCH; EVENT_LINEAGE_MISMATCH; ASSESSMENT_PROJECTION_MISMATCH; TEST_FINAL_LOCK_REQUIRED; ENSEMBLE_INVALID; ENSEMBLE_LINEAGE_MISMATCH |
| v2_immutable | REQUIRED_DB_INVARIANT | KEEP | V2_SCIENTIFIC_EVIDENCE_IMMUTABLE |
| v2_run_configuration_required | REQUIRED_DB_INVARIANT | KEEP | TRAIN_CONFIGURATION_REQUIRED |
| v2_xai_artifact_guard | REQUIRED_DB_INVARIANT | KEEP | XAI_ARTIFACT_IMMUTABLE |
| v2_xai_artifact_source_guard | REQUIRED_DB_INVARIANT | KEEP | XAI_ARTIFACT_REFERENCE_MISMATCH; XAI_ASSESSMENT_ARTIFACT_MISMATCH |
| v2_xai_comparison_guard | REQUIRED_DB_INVARIANT | REMOVE | Sustituida por dbv21_xai_evaluation_complete para N:M; conserva compatibilidad entre explicaciones. |
| v2_xai_lineage_guard | REQUIRED_DB_INVARIANT | MODIFY | XAI_SHAP_BACKGROUND_REQUIRED; XAI_MODEL_CHECKPOINT_MISMATCH; XAI_PROVISIONAL_CHECKPOINT_MISMATCH; XAI_ML_LINEAGE_MISMATCH; XAI_CELL_LINEAGE_MISMATCH; XAI_PREDICTION_MODEL_MISMATCH; XAI_SOURCE_IMAGE_MISMATCH; XAI_ASSESSMENT_SAMPLE_MISMATCH; XAI_ASSESSMENT_MODEL_MISMATCH; XAI_CROP_MISMATCH; XAI_EVALUATION_MISMATCH |
| validate_cell_classification_input_snapshot | REQUIRED_DB_INVARIANT | KEEP | classification input does not match immutable detection/crop metadata |
| validate_cell_classification_insert_state | REQUIRED_DB_INVARIANT | KEEP | cell classification inputs require a created run; cell predictions require a processing run; smear analysis summary requires a processing run; unsupported guarded classification table; classification run does not exist; classification child rows exceed the frozen run count |
| validate_cell_classification_review | REQUIRED_DB_INVARIANT | KEEP | cell prediction does not exist; failed cell predictions cannot be reviewed; confirmed label must match the immutable automatic prediction |
| validate_cell_classification_run_snapshot | REQUIRED_DB_INVARIANT | KEEP | model snapshot identity or required contract is invalid; model snapshot numeric policy is invalid; model snapshot numeric policy is outside allowed bounds |
| validate_cell_explanation_contract | REQUIRED_DB_INVARIANT | KEEP | cell explanation does not match the immutable prediction contract; generated explanation artifact lineage is inconsistent |
| validate_cell_prediction_input | REQUIRED_DB_INVARIANT | KEEP | cell prediction requires an eligible frozen input; cell prediction does not match the frozen model policy |
| validate_deployed_model_version | REQUIRED_DB_INVARIANT | KEEP | Deployment sin par version/artifact gobernado: version %, artifact %; SHA-256 de deployment, model_version y artifact no coincide; Tamaño de deployment, model_version y artifact no coincide; threshold_value (%) no coincide con calibración % (%); Model version % no apta para Etapa 2; Etapa 2 exige elegibilidad técnica y smoke PASS; Solo una model_version approved/deployed puede activarse; estado actual %; El artifact debe estar available para activar; estado actual % |
| validate_image_analysis_job | REQUIRED_DB_INVARIANT | KEEP | image_analysis_jobs.inference_run_id debe ser inference; recibió %; Un image_analysis_job nuevo exige deployment active; recibió %; threshold_used del job debe coincidir con threshold_value del deployment (%) |
| validate_run_model_deployment | REQUIRED_DB_INVARIANT | KEEP | run_model_deployments.run_id debe ser inference; recibió %; Un inference run solo puede vincular un deployment active; recibió % |
| validate_smear_analysis_summary | REQUIRED_DB_INVARIANT | KEEP | smear analysis summary does not match immutable predictions |

| Trigger / tabla | Función | Clasificación | Decisión | Diferido |
|---|---|---|---|---|
| trg_artifacts_protect_governed_identity / artifacts | protect_governed_artifact_identity | REQUIRED_DB_INVARIANT | KEEP | False/False |
| assessment_artifact_guard / assessment_artifacts | assessment_result_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| assessment_attempt_guard / assessment_attempts | assessment_attempt_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| global_assessment_reservation / assessment_attempts | experiment_reservation_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| assessment_consumer_guard / assessment_campaign_consumers | assessment_consumer_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| assessment_consumer_immutable / assessment_campaign_consumers | assessment_immutable | REQUIRED_DB_INVARIANT | KEEP | False/False |
| assessment_lock_immutable / assessment_final_locks | assessment_immutable | REQUIRED_DB_INVARIANT | KEEP | False/False |
| assessment_identity_guard / assessment_identities | assessment_identity_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| assessment_identity_immutable / assessment_identities | assessment_immutable | REQUIRED_DB_INVARIANT | KEEP | False/False |
| assessment_result_guard / assessment_results | assessment_result_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| audit_events_append_only / audit_events | prevent_audit_event_mutation | REQUIRED_DB_INVARIANT | KEEP | False/False |
| campaign_attempt_audit / campaign_attempts | campaign_audit | REQUIRED_DB_INVARIANT | KEEP | False/False |
| campaign_attempt_guard / campaign_attempts | campaign_attempt_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| campaign_attempt_state / campaign_attempts | campaign_attempt_state | REQUIRED_DB_INVARIANT | KEEP | False/False |
| global_attempt_reservation / campaign_attempts | experiment_reservation_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| campaign_configuration_audit / campaign_configurations | campaign_audit | REQUIRED_DB_INVARIANT | KEEP | False/False |
| campaign_configuration_guard / campaign_configurations | campaign_configuration_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| controlled_binding_guard / campaign_controlled_requests | controlled_binding_guard | REQUIRED_DB_INVARIANT | KEEP | True/True |
| controlled_request_guard / campaign_controlled_requests | campaign_technical_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| campaign_member_audit / campaign_members | campaign_audit | REQUIRED_DB_INVARIANT | KEEP | False/False |
| campaign_member_guard / campaign_members | campaign_member_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| technical_revision_guard / campaign_technical_revisions | campaign_technical_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_cell_classification_events_append_only / cell_classification_events | reject_cell_classification_row_mutation | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_cell_classification_inputs_append_only / cell_classification_inputs | reject_cell_classification_row_mutation | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_cell_classification_inputs_insert_state / cell_classification_inputs | validate_cell_classification_insert_state | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_cell_classification_inputs_snapshot / cell_classification_inputs | validate_cell_classification_input_snapshot | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_cell_classification_reviews_append_only / cell_classification_reviews | reject_cell_classification_row_mutation | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_cell_classification_reviews_validate / cell_classification_reviews | validate_cell_classification_review | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_cell_classification_runs_protected / cell_classification_runs | protect_cell_classification_run | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_cell_classification_runs_snapshot / cell_classification_runs | validate_cell_classification_run_snapshot | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_cell_crops_append_only / cell_crops | reject_cell_analysis_row_mutation | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_cell_detection_events_append_only / cell_detection_events | reject_cell_analysis_row_mutation | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_cell_detection_runs_immutable_identity / cell_detection_runs | protect_cell_detection_run_identity | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_cell_detections_append_only / cell_detections | reject_cell_analysis_row_mutation | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_cell_explanations_contract / cell_explanations | validate_cell_explanation_contract | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_cell_explanations_protected / cell_explanations | protect_cell_explanation | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_cell_predictions_append_only / cell_predictions | reject_cell_classification_row_mutation | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_cell_predictions_insert_state / cell_predictions | validate_cell_classification_insert_state | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_cell_predictions_validate_input / cell_predictions | validate_cell_prediction_input | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_activation_materialization_consistency / dataset_materialization_activations | enforce_activation_materialization_consistency | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_dataset_assignment_consistency / dataset_split_assignments | enforce_dataset_assignment_consistency | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_protect_frozen_dataset_assignment_updates / dataset_split_assignments | protect_frozen_dataset_assignment_updates | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_protect_frozen_dataset_assignments_delete / dataset_split_assignments | protect_frozen_dataset_assignments | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_protect_frozen_dataset_version_sources / dataset_version_sources | protect_frozen_dataset_version_sources | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_dataset_version_lifecycle / dataset_versions | enforce_dataset_version_lifecycle | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_deployed_model_versions_10_immutable / deployed_model_versions | protect_deployed_model_version_payload | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_deployed_model_versions_20_validate / deployed_model_versions | validate_deployed_model_version | REQUIRED_DB_INVARIANT | KEEP | False/False |
| v2_ensemble_complete / evaluation_ensemble_members | v2_evaluation_complete | REQUIRED_DB_INVARIANT | KEEP | True/True |
| v2_ensemble_immutable / evaluation_ensemble_members | v2_immutable | REQUIRED_DB_INVARIANT | KEEP | False/False |
| e04_evaluation_complete / evaluations | e04_calibration_complete | REQUIRED_DB_INVARIANT | KEEP | True/True |
| e04_legacy_admission / evaluations | e04_legacy_admission | REQUIRED_DB_INVARIANT | KEEP | False/False |
| v2_evaluation_complete / evaluations | v2_evaluation_complete | REQUIRED_DB_INVARIANT | KEEP | True/True |
| v2_evaluation_immutable / evaluations | v2_immutable | REQUIRED_DB_INVARIANT | KEEP | False/False |
| global_execution_event_immutable / experiment_execution_events | execution_event_immutable | REQUIRED_DB_INVARIANT | KEEP | False/False |
| campaign_audit / experimental_campaigns | campaign_audit | REQUIRED_DB_INVARIANT | KEEP | False/False |
| campaign_guard / experimental_campaigns | campaign_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| controlled_pause_guard / experimental_campaigns | controlled_pause_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_image_analysis_jobs_validate / image_analysis_jobs | validate_image_analysis_job | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_image_connected_components_append_only / image_connected_components | reject_cell_analysis_row_mutation | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_model_governance_audit_append_only / model_governance_backfill_audit | prevent_model_governance_audit_mutation | LEGACY_REDUNDANT | REMOVE | False/False |
| trg_model_versions_governance / model_versions | enforce_model_version_governance | REQUIRED_DB_INVARIANT | KEEP | False/False |
| campaign_catalog_identity_guard / models | campaign_catalog_identity_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| v2_binary_metric_guard / run_clinical_metrics | v2_binary_metric_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| v2_metric_immutable / run_clinical_metrics | v2_immutable | REQUIRED_DB_INVARIANT | KEEP | False/False |
| v2_config_immutable / run_configurations | v2_immutable | REQUIRED_DB_INVARIANT | KEEP | False/False |
| v2_configuration_guard / run_configurations | v2_configuration_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_run_lineage_governance / run_lineage | enforce_run_lineage_governance | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_run_model_deployments_validate / run_model_deployments | validate_run_model_deployment | REQUIRED_DB_INVARIANT | KEEP | False/False |
| e04_calibration_complete / run_threshold_calibration | e04_calibration_complete | REQUIRED_DB_INVARIANT | KEEP | True/True |
| e04_calibration_immutable / run_threshold_calibration | e04_calibration_immutable | REQUIRED_DB_INVARIANT | KEEP | False/False |
| v2_calibration_pair_guard / run_threshold_calibration | v2_calibration_pair_guard | REQUIRED_DB_INVARIANT | KEEP | True/True |
| campaign_run_identity_guard / runs | campaign_run_identity_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| controlled_run_guard / runs | controlled_run_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| v2_run_configuration_required / runs | v2_run_configuration_required | REQUIRED_DB_INVARIANT | KEEP | True/True |
| trg_scientific_reviews_append_only / scientific_reviews | reject_cell_analysis_row_mutation | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_validation_annotation_events_append_only / scientific_validation_annotation_events | prevent_validation_annotation_event_mutation | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_validation_annotation_protected / scientific_validation_annotations | protect_validation_annotation | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_validation_classification_runs_immutable / scientific_validation_classification_runs | prevent_validation_membership_mutation | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_validation_detection_runs_immutable / scientific_validation_detection_runs | prevent_validation_membership_mutation | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_validation_images_immutable / scientific_validation_images | prevent_validation_membership_mutation | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_validation_snapshot_protected / scientific_validation_sessions | protect_validation_snapshot | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_smear_analysis_summaries_append_only / smear_analysis_summaries | reject_cell_classification_row_mutation | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_smear_analysis_summaries_insert_state / smear_analysis_summaries | validate_cell_classification_insert_state | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_smear_analysis_summaries_validate / smear_analysis_summaries | validate_smear_analysis_summary | REQUIRED_DB_INVARIANT | KEEP | False/False |
| trg_stage2_publication_events_append_only / stage2_model_publication_events | prevent_stage2_publication_event_mutation | REQUIRED_DB_INVARIANT | KEEP | False/False |
| a_train_event_guard / train_execution_records | train_event_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| train_record_guard / train_execution_records | train_record_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| train_execution_revision_immutable / train_execution_revisions | execution_event_immutable | REQUIRED_DB_INVARIANT | KEEP | False/False |
| train_revision_binding_guard / train_execution_revisions | train_revision_binding_guard | REQUIRED_DB_INVARIANT | KEEP | True/True |
| global_train_reservation / train_execution_sessions | experiment_reservation_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| train_session_guard / train_execution_sessions | train_session_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| v2_xai_artifact_guard / xai_artifacts | v2_xai_artifact_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| v2_xai_artifact_source_guard / xai_artifacts | v2_xai_artifact_source_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| dbv21_immutable / xai_evaluation_members | v2_immutable | REQUIRED_DB_INVARIANT | NEW | False/False |
| dbv21_xai_evaluation_complete / xai_evaluation_members | dbv21_xai_evaluation_complete | REQUIRED_DB_INVARIANT | NEW | True/True |
| dbv21_configuration_guard / xai_evaluation_protocols | dbv21_xai_configuration_guard | TECHNICAL | NEW | False/False |
| dbv21_immutable / xai_evaluation_protocols | v2_immutable | REQUIRED_DB_INVARIANT | NEW | False/False |
| v2_xai_immutable / xai_evidence | v2_immutable | REQUIRED_DB_INVARIANT | KEEP | False/False |
| v2_xai_lineage_guard / xai_evidence | v2_xai_lineage_guard | REQUIRED_DB_INVARIANT | KEEP | False/False |
| v2_xai_interpretation_immutable / xai_interpretations | v2_immutable | REQUIRED_DB_INVARIANT | KEEP | False/False |
| dbv21_configuration_guard / xai_method_configurations | dbv21_xai_configuration_guard | TECHNICAL | NEW | False/False |
| dbv21_immutable / xai_method_configurations | v2_immutable | REQUIRED_DB_INVARIANT | NEW | False/False |
| dbv21_xai_evaluation_complete / xai_quantitative_evaluations | dbv21_xai_evaluation_complete | REQUIRED_DB_INVARIANT | NEW | True/True |
| v2_xai_comparison_guard / xai_quantitative_evaluations | v2_xai_comparison_guard | REQUIRED_DB_INVARIANT | REMOVE | False/False |
| v2_xai_quantitative_immutable / xai_quantitative_evaluations | v2_immutable | REQUIRED_DB_INVARIANT | KEEP | False/False |
| dbv21_immutable / xai_region_attributions | v2_immutable | REQUIRED_DB_INVARIANT | NEW | False/False |
| v2_xai_review_immutable / xai_specialist_reviews | v2_immutable | REQUIRED_DB_INVARIANT | KEEP | False/False |

No se conservan funciones sólo por compatibilidad histórica: la tabla de auditoría backfill y su trigger desaparecen. Las guardas de campañas y TRAIN permanecen porque la exclusión entre sesiones concurrentes y la inmutabilidad de contratos requieren atomicidad en DB; planificar o ejecutar campañas pertenece a SW-v2.
