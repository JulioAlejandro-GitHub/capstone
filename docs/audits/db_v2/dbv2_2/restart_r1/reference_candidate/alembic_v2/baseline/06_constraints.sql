-- E10.10.5A frozen Alembic resource. Execute only through the guarded v2 environment.
ALTER TABLE public.artifacts ADD CONSTRAINT chk_artifacts_governance_status CHECK (artifact_status = ANY(ARRAY[CAST('unknown' AS text), CAST('available' AS text), CAST('missing' AS text), CAST('mutated' AS text), CAST('archived' AS text)]));

ALTER TABLE public.assessment_artifacts ADD CONSTRAINT assessment_artifacts_payload_check CHECK (jsonb_typeof(payload) = CAST('object' AS text));

ALTER TABLE public.assessment_artifacts ADD CONSTRAINT assessment_artifacts_payload_check1 CHECK (payload ->> CAST('sha256' AS text) IS NOT NULL AND (payload ->> CAST('sha256' AS text)) ~ CAST('^[a-f0-9]{64}$' AS text));

ALTER TABLE public.assessment_artifacts ADD CONSTRAINT assessment_artifacts_payload_check2 CHECK (NOT jsonb_typeof(payload -> CAST('bytes' AS text)) IS DISTINCT FROM CAST('number' AS text) AND CAST(payload ->> CAST('bytes' AS text) AS bigint) > 0);

ALTER TABLE public.assessment_artifacts ADD CONSTRAINT assessment_artifacts_payload_check3 CHECK (NOT(payload ->> CAST('state' AS text)) IS DISTINCT FROM CAST('finalized' AS text));

ALTER TABLE public.assessment_attempts ADD CONSTRAINT assessment_attempts_check CHECK (state <> CAST('verified' AS text) OR verification IS NOT NULL);

ALTER TABLE public.assessment_attempts ADD CONSTRAINT assessment_attempts_ordinal_check CHECK (ordinal > 0);

ALTER TABLE public.assessment_attempts ADD CONSTRAINT assessment_attempts_pid_check CHECK (pid > 0);

ALTER TABLE public.assessment_attempts ADD CONSTRAINT assessment_attempts_state_check CHECK (state = ANY(ARRAY[CAST('active' AS text), CAST('verified' AS text), CAST('failed' AS text), CAST('interrupted' AS text)]));

ALTER TABLE public.assessment_final_locks ADD CONSTRAINT assessment_final_locks_check CHECK (NOT(evidence ->> CAST('identity_hash' AS text)) IS DISTINCT FROM identity_hash);

ALTER TABLE public.assessment_final_locks ADD CONSTRAINT assessment_final_locks_evidence_check CHECK (jsonb_typeof(evidence) = CAST('object' AS text));

ALTER TABLE public.assessment_final_locks ADD CONSTRAINT assessment_final_locks_evidence_check1 CHECK (NOT(evidence ->> CAST('status' AS text)) IS DISTINCT FROM CAST('locked' AS text));

ALTER TABLE public.assessment_final_locks ADD CONSTRAINT assessment_final_locks_evidence_check2 CHECK (NOT jsonb_typeof(evidence -> CAST('candidate' AS text)) IS DISTINCT FROM CAST('object' AS text));

ALTER TABLE public.assessment_final_locks ADD CONSTRAINT assessment_final_locks_evidence_check3 CHECK (NOT jsonb_typeof(evidence -> CAST('decision' AS text)) IS DISTINCT FROM CAST('object' AS text));

ALTER TABLE public.assessment_final_locks ADD CONSTRAINT assessment_final_locks_identity_hash_check CHECK (identity_hash ~ CAST('^[a-f0-9]{64}$' AS text));

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_check CHECK (NOT CAST(canonical_identity AS jsonb) IS DISTINCT FROM identity);

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_check1 CHECK (identity_hash = encode(sha256(convert_to(canonical_identity, CAST('UTF8' AS name))), CAST('hex' AS text)));

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_check2 CHECK (NOT(identity ->> CAST('kind' AS text)) IS DISTINCT FROM kind);

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_check3 CHECK (NOT((identity -> CAST('model' AS text)) ->> CAST('training_run_id' AS text)) IS DISTINCT FROM CAST(training_run_id AS text));

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check CHECK (jsonb_typeof(identity) = CAST('object' AS text));

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check1 CHECK (NOT(identity ->> CAST('schema' AS text)) IS DISTINCT FROM CAST('assessment_identity_v1' AS text));

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check10 CHECK (NOT jsonb_typeof((identity -> CAST('decision' AS text)) -> CAST('effective' AS text)) IS DISTINCT FROM CAST('number' AS text));

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check11 CHECK (CAST((identity -> CAST('decision' AS text)) ->> CAST('effective' AS text) AS numeric) >= CAST(0 AS numeric) AND CAST((identity -> CAST('decision' AS text)) ->> CAST('effective' AS text) AS numeric) <= CAST(1 AS numeric));

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check12 CHECK (NOT((identity -> CAST('decision' AS text)) ->> CAST('score_domain' AS text)) IS DISTINCT FROM CAST('raw' AS text));

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check13 CHECK (NOT((identity -> CAST('decision' AS text)) ->> CAST('comparison' AS text)) IS DISTINCT FROM CAST('>=' AS text));

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check14 CHECK (NOT jsonb_typeof(identity -> CAST('dataset' AS text)) IS DISTINCT FROM CAST('object' AS text));

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check2 CHECK (NOT jsonb_typeof(identity -> CAST('samples' AS text)) IS DISTINCT FROM CAST('array' AS text));

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check3 CHECK (jsonb_array_length(identity -> CAST('samples' AS text)) > 0);

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check4 CHECK (((identity ->> CAST('purpose' AS text)) = CAST('development' AS text) AND identity ->> CAST('split' AS text) = ANY(ARRAY[CAST('train' AS text), CAST('val' AS text)])) OR ((identity ->> CAST('purpose' AS text)) = CAST('final' AS text) AND (identity ->> CAST('split' AS text)) = CAST('test' AS text)));

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check5 CHECK (identity ->> CAST('purpose' AS text) IS NOT NULL AND identity ->> CAST('split' AS text) IS NOT NULL);

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check6 CHECK (NOT jsonb_typeof((identity -> CAST('model' AS text)) -> CAST('input_contract' AS text)) IS DISTINCT FROM CAST('object' AS text));

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check7 CHECK ((identity -> CAST('model' AS text)) ->> CAST('sha256' AS text) IS NOT NULL AND ((identity -> CAST('model' AS text)) ->> CAST('sha256' AS text)) ~ CAST('^[a-f0-9]{64}$' AS text));

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check8 CHECK ((identity -> CAST('model' AS text)) ->> CAST('model_version_id' AS text) IS NOT NULL AND CAST((identity -> CAST('model' AS text)) ->> CAST('model_version_id' AS text) AS uuid) IS NOT NULL);

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check9 CHECK ((identity -> CAST('model' AS text)) ->> CAST('checkpoint_artifact_id' AS text) IS NOT NULL AND CAST((identity -> CAST('model' AS text)) ->> CAST('checkpoint_artifact_id' AS text) AS uuid) IS NOT NULL);

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_hash_check CHECK (identity_hash ~ CAST('^[a-f0-9]{64}$' AS text));

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_kind_check CHECK (kind = ANY(ARRAY[CAST('evaluate' AS text), CAST('explain' AS text)]));

ALTER TABLE public.assessment_results ADD CONSTRAINT assessment_results_check CHECK (NOT(payload ->> CAST('sample_id' AS text)) IS DISTINCT FROM CAST(sample_id AS text));

ALTER TABLE public.assessment_results ADD CONSTRAINT assessment_results_payload_check CHECK (jsonb_typeof(payload) = CAST('object' AS text));

ALTER TABLE public.blood_samples ADD CONSTRAINT blood_samples_metadata_json_check CHECK (jsonb_typeof(metadata_json) = CAST('object' AS text));

ALTER TABLE public.blood_samples ADD CONSTRAINT blood_samples_sample_code_check CHECK (btrim(CAST(sample_code AS text)) <> CAST('' AS text));

ALTER TABLE public.blood_samples ADD CONSTRAINT blood_samples_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('registered' AS varchar) AS text), CAST(CAST('received' AS varchar) AS text), CAST(CAST('prepared' AS varchar) AS text), CAST(CAST('archived' AS varchar) AS text)]));

ALTER TABLE public.blood_samples ADD CONSTRAINT ck_blood_sample_archive_state CHECK ((CAST(status AS text) <> CAST('archived' AS text) AND archived_at IS NULL AND archived_by IS NULL) OR (CAST(status AS text) = CAST('archived' AS text) AND archived_at IS NOT NULL AND archived_by IS NOT NULL));

ALTER TABLE public.blood_samples ADD CONSTRAINT ck_blood_sample_chronology CHECK (collected_at IS NULL OR received_at IS NULL OR received_at >= collected_at);

ALTER TABLE public.blood_samples ADD CONSTRAINT ck_blood_samples_expected_count CHECK (expected_image_count IS NULL OR expected_image_count > 0);

ALTER TABLE public.blood_samples ADD CONSTRAINT ck_blood_samples_identity_origin CHECK (CAST(sample_identity_origin AS text) = ANY(ARRAY[CAST(CAST('external_system' AS varchar) AS text), CAST(CAST('generated_by_capstone' AS varchar) AS text), CAST(CAST('derived_import_profile' AS varchar) AS text)]));

ALTER TABLE public.blood_samples ADD CONSTRAINT ck_blood_samples_ingestion_status CHECK (ingestion_status IS NULL OR CAST(ingestion_status AS text) = ANY(ARRAY[CAST(CAST('pending' AS varchar) AS text), CAST(CAST('incomplete' AS varchar) AS text), CAST(CAST('complete' AS varchar) AS text), CAST(CAST('inconsistent' AS varchar) AS text), CAST(CAST('rejected' AS varchar) AS text)]));

ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_check CHECK ((state = CAST('active' AS text)) = (finished_at IS NULL));

ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_check1 CHECK (state <> ALL(ARRAY[CAST('failed' AS text), CAST('interrupted' AS text)]) OR (cause IS NOT NULL AND length(btrim(cause)) > 0));

ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_check2 CHECK (state <> ALL(ARRAY[CAST('completed' AS text), CAST('verified' AS text)]) OR training_run_id IS NOT NULL);

ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_ordinal_check CHECK (ordinal > 0);

ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_state_check CHECK (state = ANY(ARRAY[CAST('active' AS text), CAST('failed' AS text), CAST('interrupted' AS text), CAST('completed' AS text), CAST('verified' AS text)]));

ALTER TABLE public.campaign_configurations ADD CONSTRAINT campaign_configurations_configuration_check CHECK (jsonb_typeof(configuration) = CAST('object' AS text));

ALTER TABLE public.campaign_configurations ADD CONSTRAINT campaign_configurations_configuration_hash_check CHECK (configuration_hash ~ CAST('^[a-f0-9]{64}$' AS text));

ALTER TABLE public.campaign_configurations ADD CONSTRAINT campaign_configurations_requests_check CHECK (jsonb_typeof(requests) = CAST('array' AS text));

ALTER TABLE public.campaign_configurations ADD CONSTRAINT ck_campaign_configuration_required_v2 CHECK ((campaign_configuration_valid(configuration) AND jsonb_typeof(requests) = CAST('array' AS text) AND jsonb_array_length(requests) > 0) IS TRUE);

ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_reason_check CHECK (length(pg_catalog.btrim(reason)) > 0);

ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_check CHECK ((state = CAST('excluded' AS text)) = (exclusion_reason IS NOT NULL));

ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_check1 CHECK ((state = CAST('verified' AS text)) = (accepted_attempt_id IS NOT NULL));

ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_exclusion_reason_check CHECK (exclusion_reason IS NULL OR length(btrim(exclusion_reason)) > 0);

ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_position_check CHECK (position >= 0);

ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_seed_check CHECK (seed >= 0);

ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_state_check CHECK (state = ANY(ARRAY[CAST('pending' AS text), CAST('active' AS text), CAST('failed' AS text), CAST('interrupted' AS text), CAST('completed' AS text), CAST('verified' AS text), CAST('excluded' AS text)]));

ALTER TABLE public.campaign_technical_revisions ADD CONSTRAINT campaign_technical_revisions_check CHECK (CAST(canonical_payload AS jsonb) = payload);

ALTER TABLE public.campaign_technical_revisions ADD CONSTRAINT campaign_technical_revisions_check1 CHECK (encode(sha256(convert_to(canonical_payload, CAST('UTF8' AS name))), CAST('hex' AS text)) = payload_hash);

ALTER TABLE public.campaign_technical_revisions ADD CONSTRAINT campaign_technical_revisions_payload_hash_check CHECK (payload_hash ~ CAST('^[a-f0-9]{64}$' AS text));

ALTER TABLE public.cell_classification_events ADD CONSTRAINT cell_classification_events_event_type_check CHECK (btrim(CAST(event_type AS text)) <> CAST('' AS text));

ALTER TABLE public.cell_classification_events ADD CONSTRAINT cell_classification_events_metadata_json_check CHECK (jsonb_typeof(metadata_json) = CAST('object' AS text));

ALTER TABLE public.cell_classification_events ADD CONSTRAINT cell_classification_events_progress_current_check CHECK (progress_current IS NULL OR progress_current >= 0);

ALTER TABLE public.cell_classification_events ADD CONSTRAINT cell_classification_events_progress_total_check CHECK (progress_total IS NULL OR progress_total >= 0);

ALTER TABLE public.cell_classification_events ADD CONSTRAINT cell_classification_events_status_check CHECK (btrim(CAST(status AS text)) <> CAST('' AS text));

ALTER TABLE public.cell_classification_events ADD CONSTRAINT ck_cell_classification_event_progress CHECK (progress_current IS NULL OR progress_total IS NULL OR progress_current <= progress_total);

ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT cell_classification_inputs_cell_code_check CHECK (CAST(cell_code AS text) ~ CAST('^CELL-[A-F0-9]{12}$' AS text));

ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT cell_classification_inputs_cell_index_check CHECK (cell_index > 0);

ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT cell_classification_inputs_detector_algorithm_version_check CHECK (btrim(CAST(detector_algorithm_version AS text)) <> CAST('' AS text));

ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT cell_classification_inputs_detector_key_check CHECK (btrim(CAST(detector_key AS text)) <> CAST('' AS text));

ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT cell_classification_inputs_detector_version_check CHECK (btrim(CAST(detector_version AS text)) <> CAST('' AS text));

ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT cell_classification_inputs_image_sequence_number_check CHECK (image_sequence_number > 0);

ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT cell_classification_inputs_input_order_check CHECK (input_order > 0);

ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT ck_cell_classification_input_crop_metadata CHECK ((crop_id IS NULL AND NOT eligible AND crop_sha256 IS NULL AND crop_width_px IS NULL AND crop_height_px IS NULL) OR (crop_id IS NOT NULL AND crop_sha256 IS NOT NULL AND crop_sha256 ~ CAST('^[0-9a-f]{64}$' AS text) AND crop_width_px IS NOT NULL AND crop_width_px > 0 AND crop_height_px IS NOT NULL AND crop_height_px > 0));

ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT ck_cell_classification_input_eligibility CHECK ((eligible AND crop_id IS NOT NULL AND exclusion_reason IS NULL) OR (NOT eligible AND exclusion_reason IS NOT NULL AND btrim(CAST(exclusion_reason AS text)) <> CAST('' AS text)));

ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT ck_cell_classification_input_review CHECK (detection_review_status_at_creation IS NULL OR CAST(detection_review_status_at_creation AS text) = ANY(ARRAY[CAST(CAST('unreviewed' AS varchar) AS text), CAST(CAST('accepted' AS varchar) AS text), CAST(CAST('rejected' AS varchar) AS text), CAST(CAST('needs_attention' AS varchar) AS text)]));

ALTER TABLE public.cell_classification_reviews ADD CONSTRAINT cell_classification_reviews_decision_check CHECK (CAST(decision AS text) = ANY(ARRAY[CAST(CAST('confirmed' AS varchar) AS text), CAST(CAST('corrected' AS varchar) AS text), CAST(CAST('needs_attention' AS varchar) AS text), CAST(CAST('comment_only' AS varchar) AS text)]));

ALTER TABLE public.cell_classification_reviews ADD CONSTRAINT cell_classification_reviews_reviewed_label_check CHECK (reviewed_label IS NULL OR CAST(reviewed_label AS text) = ANY(ARRAY[CAST(CAST('parasitized' AS varchar) AS text), CAST(CAST('uninfected' AS varchar) AS text)]));

ALTER TABLE public.cell_classification_reviews ADD CONSTRAINT ck_cell_classification_review_payload CHECK ((CAST(decision AS text) = CAST('confirmed' AS text) AND (comment IS NULL OR btrim(comment) <> CAST('' AS text))) OR (CAST(decision AS text) = CAST('corrected' AS text) AND reviewed_label IS NOT NULL AND (comment IS NULL OR btrim(comment) <> CAST('' AS text))) OR (CAST(decision AS text) = ANY(ARRAY[CAST(CAST('needs_attention' AS varchar) AS text), CAST(CAST('comment_only' AS varchar) AS text)]) AND reviewed_label IS NULL AND comment IS NOT NULL AND btrim(comment) <> CAST('' AS text)));

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_classification_run_code_check CHECK (CAST(classification_run_code AS text) ~ CAST('^CLS-[A-F0-9]{8}$' AS text));

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_eligible_count_check CHECK (eligible_count >= 0);

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_excluded_count_check CHECK (excluded_count >= 0);

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_failed_count_check CHECK (failed_count >= 0);

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_input_count_check CHECK (input_count >= 0);

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_input_manifest_sha256_check CHECK (input_manifest_sha256 ~ CAST('^[0-9a-f]{64}$' AS text));

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_model_name_check CHECK (btrim(CAST(model_name AS text)) <> CAST('' AS text));

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_model_snapshot_check CHECK (jsonb_typeof(model_snapshot) = CAST('object' AS text));

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_near_threshold_count_check CHECK (near_threshold_count >= 0);

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_parasitized_count_check CHECK (parasitized_count >= 0);

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_processed_count_check CHECK (processed_count >= 0);

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('created' AS varchar) AS text), CAST(CAST('processing' AS varchar) AS text), CAST(CAST('completed' AS varchar) AS text), CAST(CAST('completed_with_warnings' AS varchar) AS text), CAST(CAST('failed' AS varchar) AS text)]));

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_uninfected_count_check CHECK (uninfected_count >= 0);

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT ck_cell_classification_run_counts CHECK (input_count = (eligible_count + excluded_count) AND processed_count <= eligible_count AND processed_count = (parasitized_count + uninfected_count + failed_count) AND near_threshold_count <= (parasitized_count + uninfected_count));

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT ck_cell_classification_run_model_version CHECK (model_version IS NULL OR btrim(CAST(model_version AS text)) <> CAST('' AS text));

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT ck_cell_classification_run_retry CHECK (retry_of_run_id IS NULL OR retry_of_run_id <> id);

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT ck_cell_classification_run_terminal_state CHECK ((CAST(status AS text) = CAST('created' AS text) AND started_at IS NULL AND completed_at IS NULL AND failed_at IS NULL AND error_code IS NULL AND error_message IS NULL) OR (CAST(status AS text) = CAST('processing' AS text) AND started_at IS NOT NULL AND completed_at IS NULL AND failed_at IS NULL AND error_code IS NULL AND error_message IS NULL) OR (CAST(status AS text) = ANY(ARRAY[CAST(CAST('completed' AS varchar) AS text), CAST(CAST('completed_with_warnings' AS varchar) AS text)]) AND started_at IS NOT NULL AND completed_at IS NOT NULL AND failed_at IS NULL AND error_code IS NULL AND error_message IS NULL AND processed_count = eligible_count) OR (CAST(status AS text) = CAST('failed' AS text) AND started_at IS NOT NULL AND completed_at IS NULL AND failed_at IS NOT NULL AND error_code IS NOT NULL AND btrim(CAST(error_code AS text)) <> CAST('' AS text)));

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT ck_cell_classification_run_time_order CHECK (updated_at >= created_at AND (started_at IS NULL OR started_at >= created_at) AND (completed_at IS NULL OR completed_at >= started_at) AND (failed_at IS NULL OR failed_at >= started_at));

ALTER TABLE public.cell_crops ADD CONSTRAINT cell_crops_file_size_bytes_check CHECK (file_size_bytes > 0);

ALTER TABLE public.cell_crops ADD CONSTRAINT cell_crops_format_check CHECK (CAST(format AS text) = CAST('PNG' AS text));

ALTER TABLE public.cell_crops ADD CONSTRAINT cell_crops_height_px_check CHECK (height_px > 0);

ALTER TABLE public.cell_crops ADD CONSTRAINT cell_crops_padding_px_check CHECK (padding_px >= 0);

ALTER TABLE public.cell_crops ADD CONSTRAINT cell_crops_relative_storage_key_check CHECK (relative_storage_key ~ CAST('^cell-crops/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/crop[.]png$' AS text));

ALTER TABLE public.cell_crops ADD CONSTRAINT cell_crops_sha256_check CHECK (sha256 ~ CAST('^[0-9a-f]{64}$' AS text));

ALTER TABLE public.cell_crops ADD CONSTRAINT cell_crops_width_px_check CHECK (width_px > 0);

ALTER TABLE public.cell_detection_events ADD CONSTRAINT cell_detection_events_event_type_check CHECK (btrim(CAST(event_type AS text)) <> CAST('' AS text));

ALTER TABLE public.cell_detection_events ADD CONSTRAINT cell_detection_events_metadata_json_check CHECK (jsonb_typeof(metadata_json) = CAST('object' AS text));

ALTER TABLE public.cell_detection_events ADD CONSTRAINT cell_detection_events_progress_current_check CHECK (progress_current IS NULL OR progress_current >= 0);

ALTER TABLE public.cell_detection_events ADD CONSTRAINT cell_detection_events_progress_total_check CHECK (progress_total IS NULL OR progress_total >= 0);

ALTER TABLE public.cell_detection_events ADD CONSTRAINT cell_detection_events_stage_check CHECK (btrim(CAST(stage AS text)) <> CAST('' AS text));

ALTER TABLE public.cell_detection_events ADD CONSTRAINT cell_detection_events_status_check CHECK (btrim(CAST(status AS text)) <> CAST('' AS text));

ALTER TABLE public.cell_detection_events ADD CONSTRAINT ck_cell_detection_event_progress CHECK (progress_current IS NULL OR progress_total IS NULL OR progress_current <= progress_total);

ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_algorithm_version_check CHECK (btrim(CAST(algorithm_version AS text)) <> CAST('' AS text));

ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_check CHECK (processed_image_count >= 0 AND processed_image_count <= image_count);

ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_component_count_check CHECK (component_count >= 0);

ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_crop_count_check CHECK (crop_count >= 0);

ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_detection_count_check CHECK (detection_count >= 0);

ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_detection_run_code_check CHECK (CAST(detection_run_code AS text) ~ CAST('^DET-[A-F0-9]{8}$' AS text));

ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_detector_key_check CHECK (btrim(CAST(detector_key AS text)) <> CAST('' AS text));

ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_detector_version_check CHECK (btrim(CAST(detector_version AS text)) <> CAST('' AS text));

ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_image_count_check CHECK (image_count > 0);

ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_input_manifest_sha256_check CHECK (input_manifest_sha256 ~ CAST('^[0-9a-f]{64}$' AS text));

ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_profile_snapshot_check CHECK (jsonb_typeof(profile_snapshot) = CAST('object' AS text));

ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('created' AS varchar) AS text), CAST(CAST('processing' AS varchar) AS text), CAST(CAST('completed' AS varchar) AS text), CAST(CAST('completed_with_warnings' AS varchar) AS text), CAST(CAST('failed' AS varchar) AS text)]));

ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_warning_count_check CHECK (warning_count >= 0);

ALTER TABLE public.cell_detection_runs ADD CONSTRAINT ck_cell_detection_run_terminal_state CHECK ((CAST(status AS text) = CAST('created' AS text) AND started_at IS NULL AND completed_at IS NULL AND failed_at IS NULL AND error_code IS NULL AND error_message IS NULL) OR (CAST(status AS text) = CAST('processing' AS text) AND started_at IS NOT NULL AND completed_at IS NULL AND failed_at IS NULL AND error_code IS NULL AND error_message IS NULL) OR (CAST(status AS text) = ANY(ARRAY[CAST(CAST('completed' AS varchar) AS text), CAST(CAST('completed_with_warnings' AS varchar) AS text)]) AND started_at IS NOT NULL AND completed_at IS NOT NULL AND failed_at IS NULL AND error_code IS NULL AND error_message IS NULL) OR (CAST(status AS text) = CAST('failed' AS text) AND started_at IS NOT NULL AND completed_at IS NULL AND failed_at IS NOT NULL AND error_code IS NOT NULL));

ALTER TABLE public.cell_detections ADD CONSTRAINT cell_detections_automated_status_check CHECK (CAST(automated_status AS text) = CAST('candidate' AS text));

ALTER TABLE public.cell_detections ADD CONSTRAINT cell_detections_bbox_height_check CHECK (bbox_height > 0);

ALTER TABLE public.cell_detections ADD CONSTRAINT cell_detections_bbox_width_check CHECK (bbox_width > 0);

ALTER TABLE public.cell_detections ADD CONSTRAINT cell_detections_bbox_x_check CHECK (bbox_x >= 0);

ALTER TABLE public.cell_detections ADD CONSTRAINT cell_detections_bbox_y_check CHECK (bbox_y >= 0);

ALTER TABLE public.cell_detections ADD CONSTRAINT cell_detections_cell_code_check CHECK (CAST(cell_code AS text) ~ CAST('^CELL-[A-F0-9]{12}$' AS text));

ALTER TABLE public.cell_detections ADD CONSTRAINT cell_detections_cell_index_check CHECK (cell_index > 0);

ALTER TABLE public.cell_detections ADD CONSTRAINT cell_detections_coordinate_space_check CHECK (CAST(coordinate_space AS text) = CAST('original_image_pixels' AS text));

ALTER TABLE public.cell_detections ADD CONSTRAINT cell_detections_detector_score_check CHECK (detector_score IS NULL OR (detector_score >= CAST(0 AS double precision) AND detector_score <= CAST(1 AS double precision)));

ALTER TABLE public.cell_explanations ADD CONSTRAINT cell_explanations_method_check CHECK (CAST(method AS text) = CAST('gradcam' AS text));

ALTER TABLE public.cell_explanations ADD CONSTRAINT cell_explanations_method_version_check CHECK (btrim(CAST(method_version AS text)) <> CAST('' AS text));

ALTER TABLE public.cell_explanations ADD CONSTRAINT cell_explanations_parameters_json_check CHECK (jsonb_typeof(parameters_json) = CAST('object' AS text));

ALTER TABLE public.cell_explanations ADD CONSTRAINT cell_explanations_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('pending' AS varchar) AS text), CAST(CAST('generated' AS varchar) AS text), CAST(CAST('failed' AS varchar) AS text), CAST(CAST('unsupported' AS varchar) AS text), CAST(CAST('not_requested' AS varchar) AS text)]));

ALTER TABLE public.cell_explanations ADD CONSTRAINT ck_cell_explanation_dimensions CHECK ((width_px IS NULL OR width_px > 0) AND (height_px IS NULL OR height_px > 0) AND ((width_px IS NULL AND height_px IS NULL) OR (width_px IS NOT NULL AND height_px IS NOT NULL)));

ALTER TABLE public.cell_explanations ADD CONSTRAINT ck_cell_explanation_hashes CHECK ((heatmap_sha256 IS NULL OR heatmap_sha256 ~ CAST('^[0-9a-f]{64}$' AS text)) AND (overlay_sha256 IS NULL OR overlay_sha256 ~ CAST('^[0-9a-f]{64}$' AS text)));

ALTER TABLE public.cell_explanations ADD CONSTRAINT ck_cell_explanation_heatmap_key CHECK (heatmap_storage_key IS NULL OR heatmap_storage_key ~ CAST('^cell-explanations/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gradcam_heatmap[.]png$' AS text));

ALTER TABLE public.cell_explanations ADD CONSTRAINT ck_cell_explanation_overlay_key CHECK (overlay_storage_key IS NULL OR overlay_storage_key ~ CAST('^cell-explanations/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gradcam_overlay[.]png$' AS text));

ALTER TABLE public.cell_explanations ADD CONSTRAINT ck_cell_explanation_sizes CHECK ((heatmap_file_size_bytes IS NULL OR heatmap_file_size_bytes > 0) AND (overlay_file_size_bytes IS NULL OR overlay_file_size_bytes > 0));

ALTER TABLE public.cell_explanations ADD CONSTRAINT ck_cell_explanation_state CHECK ((CAST(status AS text) = CAST('not_requested' AS text) AND started_at IS NULL AND completed_at IS NULL AND error_code IS NULL AND error_message IS NULL AND heatmap_storage_key IS NULL AND heatmap_sha256 IS NULL AND heatmap_file_size_bytes IS NULL AND overlay_storage_key IS NULL AND overlay_sha256 IS NULL AND overlay_file_size_bytes IS NULL AND width_px IS NULL AND height_px IS NULL) OR (CAST(status AS text) = CAST('pending' AS text) AND started_at IS NOT NULL AND completed_at IS NULL AND error_code IS NULL AND error_message IS NULL AND heatmap_storage_key IS NULL AND heatmap_sha256 IS NULL AND heatmap_file_size_bytes IS NULL AND overlay_storage_key IS NULL AND overlay_sha256 IS NULL AND overlay_file_size_bytes IS NULL AND width_px IS NULL AND height_px IS NULL) OR (CAST(status AS text) = CAST('generated' AS text) AND started_at IS NOT NULL AND completed_at IS NOT NULL AND last_conv_layer IS NOT NULL AND btrim(CAST(last_conv_layer AS text)) <> CAST('' AS text) AND heatmap_storage_key IS NOT NULL AND heatmap_sha256 IS NOT NULL AND heatmap_file_size_bytes IS NOT NULL AND overlay_storage_key IS NOT NULL AND overlay_sha256 IS NOT NULL AND overlay_file_size_bytes IS NOT NULL AND width_px IS NOT NULL AND height_px IS NOT NULL AND error_code IS NULL AND error_message IS NULL) OR (CAST(status AS text) = ANY(ARRAY[CAST(CAST('failed' AS varchar) AS text), CAST(CAST('unsupported' AS varchar) AS text)]) AND started_at IS NOT NULL AND completed_at IS NOT NULL AND error_code IS NOT NULL AND btrim(CAST(error_code AS text)) <> CAST('' AS text) AND heatmap_storage_key IS NULL AND heatmap_sha256 IS NULL AND heatmap_file_size_bytes IS NULL AND overlay_storage_key IS NULL AND overlay_sha256 IS NULL AND overlay_file_size_bytes IS NULL AND width_px IS NULL AND height_px IS NULL));

ALTER TABLE public.cell_explanations ADD CONSTRAINT ck_cell_explanation_time_order CHECK ((started_at IS NULL OR started_at >= created_at) AND (completed_at IS NULL OR completed_at >= started_at));

ALTER TABLE public.cell_predictions ADD CONSTRAINT cell_predictions_prediction_status_check CHECK (CAST(prediction_status AS text) = ANY(ARRAY[CAST(CAST('completed' AS varchar) AS text), CAST(CAST('failed' AS varchar) AS text)]));

ALTER TABLE public.cell_predictions ADD CONSTRAINT cell_predictions_preprocessing_snapshot_check CHECK (jsonb_typeof(preprocessing_snapshot) = CAST('object' AS text));

ALTER TABLE public.cell_predictions ADD CONSTRAINT cell_predictions_raw_output_check CHECK (jsonb_typeof(raw_output) = ANY(ARRAY[CAST('object' AS text), CAST('array' AS text)]));

ALTER TABLE public.cell_predictions ADD CONSTRAINT cell_predictions_threshold_source_check CHECK (btrim(CAST(threshold_source AS text)) <> CAST('' AS text));

ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_class_index CHECK (predicted_class_index IS NULL OR predicted_class_index = ANY(ARRAY[0, 1]));

ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_completed_payload CHECK ((CAST(prediction_status AS text) = CAST('completed' AS text) AND probability_parasitized IS NOT NULL AND probability_uninfected IS NOT NULL AND CAST(predicted_label AS text) = ANY(ARRAY[CAST(CAST('parasitized' AS varchar) AS text), CAST(CAST('uninfected' AS varchar) AS text)]) AND predicted_class_index = ANY(ARRAY[0, 1]) AND decision_margin IS NOT NULL AND error_code IS NULL AND error_message IS NULL) OR (CAST(prediction_status AS text) = CAST('failed' AS text) AND probability_parasitized IS NULL AND probability_uninfected IS NULL AND predicted_label IS NULL AND predicted_class_index IS NULL AND decision_margin IS NULL AND NOT near_threshold AND error_code IS NOT NULL AND btrim(CAST(error_code AS text)) <> CAST('' AS text)));

ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_decision_margin CHECK (decision_margin IS NULL OR probability_parasitized IS NULL OR abs(decision_margin - abs(probability_parasitized - threshold_used)) <= CAST(0.000000001 AS double precision));

ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_duration CHECK (inference_duration_ms IS NULL OR (inference_duration_ms >= CAST(0 AS double precision) AND inference_duration_ms < CAST('Infinity' AS double precision)));

ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_label_index CHECK (CAST(prediction_status AS text) <> CAST('completed' AS text) OR (predicted_class_index = 1 AND CAST(predicted_label AS text) = CAST('parasitized' AS text) AND probability_parasitized >= threshold_used) OR (predicted_class_index = 0 AND CAST(predicted_label AS text) = CAST('uninfected' AS text) AND probability_parasitized < threshold_used));

ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_margin CHECK (decision_margin IS NULL OR (decision_margin >= CAST(0 AS double precision) AND decision_margin < CAST('Infinity' AS double precision)));

ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_positive_class CHECK (CAST(positive_label AS text) = CAST('parasitized' AS text) AND positive_class_index = 1);

ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_probability_parasitized CHECK (probability_parasitized IS NULL OR (probability_parasitized >= CAST(0 AS double precision) AND probability_parasitized <= CAST(1 AS double precision) AND probability_parasitized < CAST('Infinity' AS double precision)));

ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_probability_sum CHECK (probability_parasitized IS NULL OR probability_uninfected IS NULL OR abs((probability_parasitized + probability_uninfected) - CAST(1.0 AS double precision)) <= CAST(0.000000001 AS double precision));

ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_probability_uninfected CHECK (probability_uninfected IS NULL OR (probability_uninfected >= CAST(0 AS double precision) AND probability_uninfected <= CAST(1 AS double precision) AND probability_uninfected < CAST('Infinity' AS double precision)));

ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_threshold CHECK (threshold_used >= CAST(0 AS double precision) AND threshold_used <= CAST(1 AS double precision) AND threshold_used < CAST('Infinity' AS double precision));

ALTER TABLE public.clinical_identities ADD CONSTRAINT chk_clinical_identities_metadata_object CHECK (jsonb_typeof(metadata) = CAST('object' AS text));

ALTER TABLE public.clinical_identities ADD CONSTRAINT chk_clinical_identities_status CHECK (status = ANY(ARRAY[CAST('VERIFIED' AS text), CAST('UNRESOLVED' AS text), CAST('CONFLICT' AS text)]));

ALTER TABLE public.clinical_identities ADD CONSTRAINT chk_clinical_identities_type CHECK (identity_type = CAST('PATIENT' AS text));

ALTER TABLE public.dataset_materialization_activations ADD CONSTRAINT chk_dataset_materialization_activations_interval CHECK (deactivated_at IS NULL OR deactivated_at >= activated_at);

ALTER TABLE public.dataset_materialization_activations ADD CONSTRAINT chk_dataset_materialization_activations_metadata_object CHECK (jsonb_typeof(metadata) = CAST('object' AS text));

ALTER TABLE public.dataset_materializations ADD CONSTRAINT chk_dataset_materializations_attempt CHECK (attempt_number > 0);

ALTER TABLE public.dataset_materializations ADD CONSTRAINT chk_dataset_materializations_manifest_object CHECK (jsonb_typeof(manifest_metadata) = CAST('object' AS text));

ALTER TABLE public.dataset_materializations ADD CONSTRAINT chk_dataset_materializations_metadata_object CHECK (jsonb_typeof(metadata) = CAST('object' AS text));

ALTER TABLE public.dataset_materializations ADD CONSTRAINT chk_dataset_materializations_reconciliation CHECK (reconciliation_status = ANY(ARRAY[CAST('PENDING' AS text), CAST('PASS' AS text), CAST('FAIL' AS text)]));

ALTER TABLE public.dataset_materializations ADD CONSTRAINT chk_dataset_materializations_record_count CHECK (record_count >= 0);

ALTER TABLE public.dataset_materializations ADD CONSTRAINT chk_dataset_materializations_relative_root CHECK (relative_root <> CAST('' AS text) AND relative_root !~ CAST('^/' AS text));

ALTER TABLE public.dataset_materializations ADD CONSTRAINT chk_dataset_materializations_status CHECK (status = ANY(ARRAY[CAST('NOT_MATERIALIZED' AS text), CAST('MATERIALIZING' AS text), CAST('READY' AS text), CAST('FAILED' AS text)]));

ALTER TABLE public.dataset_source_records ADD CONSTRAINT chk_dataset_source_records_dimensions CHECK ((image_width IS NULL OR image_width > 0) AND (image_height IS NULL OR image_height > 0) AND (file_size_bytes IS NULL OR file_size_bytes >= 0));

ALTER TABLE public.dataset_source_records ADD CONSTRAINT chk_dataset_source_records_identity_status CHECK (identity_status = ANY(ARRAY[CAST('VERIFIED' AS text), CAST('UNRESOLVED' AS text), CAST('CONFLICT' AS text)]));

ALTER TABLE public.dataset_source_records ADD CONSTRAINT chk_dataset_source_records_metadata_object CHECK (jsonb_typeof(metadata) = CAST('object' AS text));

ALTER TABLE public.dataset_source_records ADD CONSTRAINT chk_dataset_source_records_pixel_sha256 CHECK (decoded_pixel_sha256 IS NULL OR decoded_pixel_sha256 ~ CAST('^[0-9a-fA-F]{64}$' AS text));

ALTER TABLE public.dataset_source_records ADD CONSTRAINT chk_dataset_source_records_source_sha256 CHECK (source_file_sha256 IS NULL OR source_file_sha256 ~ CAST('^[0-9a-fA-F]{64}$' AS text));

ALTER TABLE public.dataset_split_assignments ADD CONSTRAINT chk_dataset_split_assignments_metadata_object CHECK (jsonb_typeof(metadata) = CAST('object' AS text));

ALTER TABLE public.dataset_split_assignments ADD CONSTRAINT chk_dataset_split_assignments_split CHECK (split_name = ANY(ARRAY[CAST('train' AS text), CAST('val' AS text), CAST('test' AS text), CAST('external_validation' AS text)]));

ALTER TABLE public.dataset_split_images ADD CONSTRAINT chk_dataset_split_images_class_index CHECK (class_index = ANY(ARRAY[0, 1]));

ALTER TABLE public.dataset_split_images ADD CONSTRAINT chk_dataset_split_images_class_name CHECK (class_name = ANY(ARRAY[CAST('uninfected' AS text), CAST('parasitized' AS text)]));

ALTER TABLE public.dataset_split_images ADD CONSTRAINT chk_dataset_split_images_split CHECK (split_name = ANY(ARRAY[CAST('train' AS text), CAST('val' AS text), CAST('validation' AS text), CAST('test' AS text)]));

ALTER TABLE public.dataset_split_statistics ADD CONSTRAINT chk_dataset_split_statistics_details_object CHECK (details_json IS NULL OR jsonb_typeof(details_json) = CAST('object' AS text));

ALTER TABLE public.dataset_split_statistics ADD CONSTRAINT chk_dataset_split_statistics_value CHECK (numeric_value IS NOT NULL OR text_value IS NOT NULL OR details_json IS NOT NULL);

ALTER TABLE public.dataset_split_validation_checks ADD CONSTRAINT chk_dataset_split_validation_checks_details_object CHECK (jsonb_typeof(details_json) = CAST('object' AS text));

ALTER TABLE public.dataset_split_validation_checks ADD CONSTRAINT chk_dataset_split_validation_checks_status CHECK (status = ANY(ARRAY[CAST('PASS' AS text), CAST('FAIL' AS text), CAST('WARNING' AS text)]));

ALTER TABLE public.dataset_version_sources ADD CONSTRAINT chk_dataset_version_sources_role CHECK (role = ANY(ARRAY[CAST('PRIMARY' AS text), CAST('EXTERNAL_VALIDATION' AS text), CAST('AUXILIARY' AS text)]));

ALTER TABLE public.dataset_versions ADD CONSTRAINT chk_dataset_versions_class_mapping_object CHECK (jsonb_typeof(class_mapping) = CAST('object' AS text));

ALTER TABLE public.dataset_versions ADD CONSTRAINT chk_dataset_versions_methodology_object CHECK (jsonb_typeof(methodology_json) = CAST('object' AS text));

ALTER TABLE public.dataset_versions ADD CONSTRAINT chk_dataset_versions_ratio_sum CHECK ((target_train_ratio + target_val_ratio + target_test_ratio) = 1.0);

ALTER TABLE public.dataset_versions ADD CONSTRAINT chk_dataset_versions_source_count CHECK (source_record_count >= 0);

ALTER TABLE public.dataset_versions ADD CONSTRAINT chk_dataset_versions_status CHECK (status = ANY(ARRAY[CAST('DRAFT' AS text), CAST('GENERATED' AS text), CAST('VALIDATED' AS text), CAST('FROZEN' AS text), CAST('ARCHIVED' AS text)]));

ALTER TABLE public.dataset_versions ADD CONSTRAINT chk_dataset_versions_test_ratio CHECK (target_test_ratio >= CAST(0 AS numeric) AND target_test_ratio <= CAST(1 AS numeric));

ALTER TABLE public.dataset_versions ADD CONSTRAINT chk_dataset_versions_train_ratio CHECK (target_train_ratio >= CAST(0 AS numeric) AND target_train_ratio <= CAST(1 AS numeric));

ALTER TABLE public.dataset_versions ADD CONSTRAINT chk_dataset_versions_val_ratio CHECK (target_val_ratio >= CAST(0 AS numeric) AND target_val_ratio <= CAST(1 AS numeric));

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_active_mapping CHECK (status <> CAST('active' AS text) OR label_mapping_snapshot @> CAST('{"0": "uninfected", "1": "parasitized"}' AS jsonb));

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_active_timestamps CHECK (status <> CAST('active' AS text) OR (deployed_at IS NOT NULL AND retired_at IS NULL AND NULLIF(btrim(deployed_by), CAST('' AS text)) IS NOT NULL));

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_artifact_size CHECK (artifact_size_bytes IS NULL OR artifact_size_bytes >= 0);

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_clinical_convention CHECK (positive_label = CAST('parasitized' AS text) AND score_name = CAST('probability_parasitized' AS text));

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_distinct_history CHECK ((supersedes_deployment_id IS NULL OR supersedes_deployment_id <> id) AND (rollback_of_deployment_id IS NULL OR rollback_of_deployment_id <> id));

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_names CHECK (btrim(deployment_name) <> CAST('' AS text) AND btrim(environment) <> CAST('' AS text) AND btrim(alias) <> CAST('' AS text));

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_retired_timestamp CHECK (status <> CAST('retired' AS text) OR retired_at IS NOT NULL);

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_sha256 CHECK (artifact_sha256 ~ CAST('^[0-9a-f]{64}$' AS text));

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_snapshots CHECK (jsonb_typeof(threshold_profile_snapshot) = CAST('object' AS text) AND jsonb_typeof(preprocessing_profile_snapshot) = CAST('object' AS text) AND jsonb_typeof(image_quality_policy_snapshot) = CAST('object' AS text) AND jsonb_typeof(label_mapping_snapshot) = CAST('object' AS text) AND jsonb_typeof(metadata) = CAST('object' AS text));

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_status CHECK (status = ANY(ARRAY[CAST('pending' AS text), CAST('active' AS text), CAST('inactive' AS text), CAST('retired' AS text), CAST('failed' AS text)]));

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_threshold CHECK (threshold_value >= CAST(0 AS numeric) AND threshold_value <= CAST(1 AS numeric));

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_timestamp_order CHECK (retired_at IS NULL OR deployed_at IS NULL OR retired_at >= deployed_at);

ALTER TABLE public.experiment_execution_gate ADD CONSTRAINT experiment_execution_gate_singleton_check CHECK (singleton);

ALTER TABLE public.experimental_campaigns ADD CONSTRAINT ck_campaign_frozen_required_v2 CHECK (state = CAST('draft' AS text) OR (contract IS NOT NULL AND canonical_contract IS NOT NULL AND contract_hash IS NOT NULL AND contract_hash ~ CAST('^[a-f0-9]{64}$' AS text) AND NOT contract_hash IS DISTINCT FROM encode(sha256(convert_to(canonical_contract, CAST('UTF8' AS name))), CAST('hex' AS text)) AND NOT CAST(canonical_contract AS jsonb) IS DISTINCT FROM contract AND campaign_contract_valid(contract)) IS TRUE);

ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_actor_check CHECK (length(btrim(actor)) > 0);

ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_check CHECK ((state = CAST('draft' AS text) AND contract IS NULL AND canonical_contract IS NULL AND contract_hash IS NULL AND frozen_at IS NULL) OR (state <> CAST('draft' AS text) AND contract IS NOT NULL AND canonical_contract IS NOT NULL AND contract_hash ~ CAST('^[a-f0-9]{64}$' AS text) AND registry_snapshot IS NOT NULL AND frozen_at IS NOT NULL AND expected_count > 0));

ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_check1 CHECK (NOT(dataset_snapshot ->> CAST('dataset_version_id' AS text)) IS DISTINCT FROM CAST(dataset_version_id AS text));

ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_dataset_snapshot_check CHECK (jsonb_typeof(dataset_snapshot) = CAST('object' AS text));

ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_environment_check CHECK (jsonb_typeof(environment) = CAST('object' AS text));

ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_expected_count_check CHECK (expected_count >= 0);

ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_name_check CHECK (length(btrim(name)) > 0);

ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_protocol_check CHECK (jsonb_typeof(protocol) = CAST('object' AS text));

ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_purpose_check CHECK (length(btrim(purpose)) > 0);

ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_requested_check CHECK (jsonb_typeof(requested) = CAST('object' AS text));

ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_state_check CHECK (state = ANY(ARRAY[CAST('draft' AS text), CAST('frozen' AS text), CAST('active' AS text), CAST('paused' AS text), CAST('finalized' AS text)]));

ALTER TABLE public.identity_evidence ADD CONSTRAINT chk_identity_evidence_json_object CHECK (jsonb_typeof(evidence_json) = CAST('object' AS text));

ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT chk_image_analysis_jobs_counts CHECK ((total_cells IS NULL OR total_cells >= 0) AND (positive_cells IS NULL OR positive_cells >= 0) AND (total_cells IS NULL OR positive_cells IS NULL OR positive_cells <= total_cells));

ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT chk_image_analysis_jobs_idempotency_key CHECK (idempotency_key IS NULL OR NULLIF(btrim(idempotency_key), CAST('' AS text)) IS NOT NULL);

ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT chk_image_analysis_jobs_payload_objects CHECK (jsonb_typeof(quality_metrics) = CAST('object' AS text) AND jsonb_typeof(summary) = CAST('object' AS text) AND jsonb_typeof(metadata) = CAST('object' AS text));

ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT chk_image_analysis_jobs_quality_status CHECK (quality_status = ANY(ARRAY[CAST('not_assessed' AS text), CAST('pending' AS text), CAST('passed' AS text), CAST('warning' AS text), CAST('rejected' AS text), CAST('failed' AS text), CAST('skipped' AS text)]));

ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT chk_image_analysis_jobs_source CHECK (input_artifact_id IS NOT NULL OR source_image_id IS NOT NULL);

ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT chk_image_analysis_jobs_status CHECK (status = ANY(ARRAY[CAST('pending' AS text), CAST('running' AS text), CAST('completed' AS text), CAST('failed' AS text), CAST('rejected' AS text), CAST('cancelled' AS text)]));

ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT chk_image_analysis_jobs_status_timestamps CHECK ((status <> ALL(ARRAY[CAST('running' AS text), CAST('completed' AS text)]) OR started_at IS NOT NULL) AND (status <> ALL(ARRAY[CAST('completed' AS text), CAST('failed' AS text), CAST('rejected' AS text), CAST('cancelled' AS text)]) OR completed_at IS NOT NULL));

ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT chk_image_analysis_jobs_threshold CHECK (threshold_used IS NULL OR (threshold_used >= CAST(0 AS numeric) AND threshold_used <= CAST(1 AS numeric)));

ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT chk_image_analysis_jobs_timestamp_order CHECK (completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at);

ALTER TABLE public.image_connected_components ADD CONSTRAINT ck_connected_component_rejection CHECK ((CAST(component_status AS text) = CAST('rejected_by_filter' AS text) AND rejection_code IS NOT NULL) OR (CAST(component_status AS text) <> CAST('rejected_by_filter' AS text) AND rejection_code IS NULL));

ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_area_px_check CHECK (area_px > 0);

ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_bbox_height_check CHECK (bbox_height > 0);

ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_bbox_width_check CHECK (bbox_width > 0);

ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_bbox_x_check CHECK (bbox_x >= 0);

ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_bbox_y_check CHECK (bbox_y >= 0);

ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_centroid_x_check CHECK (centroid_x >= CAST(0 AS double precision));

ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_centroid_y_check CHECK (centroid_y >= CAST(0 AS double precision));

ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_circularity_check CHECK (circularity IS NULL OR (circularity >= CAST(0 AS double precision) AND circularity <= CAST(1 AS double precision)));

ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_component_index_check CHECK (component_index > 0);

ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_component_status_check CHECK (CAST(component_status AS text) = ANY(ARRAY[CAST(CAST('candidate' AS varchar) AS text), CAST(CAST('accepted' AS varchar) AS text), CAST(CAST('rejected_by_filter' AS varchar) AS text)]));

ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_metrics_json_check CHECK (jsonb_typeof(metrics_json) = CAST('object' AS text));

ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_perimeter_px_check CHECK (perimeter_px IS NULL OR perimeter_px >= CAST(0 AS double precision));

ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_solidity_check CHECK (solidity IS NULL OR (solidity >= CAST(0 AS double precision) AND solidity <= CAST(1 AS double precision)));

ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_acquisition_origin_check CHECK (CAST(acquisition_origin AS text) = ANY(ARRAY[CAST(CAST('manual_upload' AS varchar) AS text), CAST(CAST('research_dataset_import' AS varchar) AS text), CAST(CAST('external_capture_system' AS varchar) AS text)]));

ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_expected_image_count_check CHECK (expected_image_count IS NULL OR expected_image_count > 0);

ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_metadata_json_check CHECK (jsonb_typeof(metadata_json) = CAST('object' AS text));

ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_received_image_count_check CHECK (received_image_count >= 0);

ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('pending' AS varchar) AS text), CAST(CAST('incomplete' AS varchar) AS text), CAST(CAST('complete' AS varchar) AS text), CAST(CAST('inconsistent' AS varchar) AS text), CAST(CAST('failed' AS varchar) AS text)]));

ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_analysis_scale_check CHECK (analysis_scale > CAST(0 AS double precision));

ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_analyzed_height_px_check CHECK (analyzed_height_px > 0);

ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_analyzed_width_px_check CHECK (analyzed_width_px > 0);

ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_assessment_status_check CHECK (CAST(assessment_status AS text) = ANY(ARRAY[CAST(CAST('pending' AS varchar) AS text), CAST(CAST('processing' AS varchar) AS text), CAST(CAST('completed' AS varchar) AS text), CAST(CAST('error' AS varchar) AS text)]));

ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_bright_pixel_ratio_check CHECK (bright_pixel_ratio >= CAST(0 AS double precision) AND bright_pixel_ratio <= CAST(1 AS double precision));

ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_dark_pixel_ratio_check CHECK (dark_pixel_ratio >= CAST(0 AS double precision) AND dark_pixel_ratio <= CAST(1 AS double precision));

ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_failure_codes_check CHECK (jsonb_typeof(failure_codes) = CAST('array' AS text));

ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_height_px_check CHECK (height_px > 0);

ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_metrics_json_check CHECK (jsonb_typeof(metrics_json) = CAST('object' AS text));

ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_near_black_border_ratio_check CHECK (near_black_border_ratio >= CAST(0 AS double precision) AND near_black_border_ratio <= CAST(1 AS double precision));

ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_pixel_count_check CHECK (pixel_count > 0);

ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_quality_verdict_check CHECK (CAST(quality_verdict AS text) = ANY(ARRAY[CAST(CAST('pending' AS varchar) AS text), CAST(CAST('pass' AS varchar) AS text), CAST(CAST('warning' AS varchar) AS text), CAST(CAST('fail' AS varchar) AS text), CAST(CAST('error' AS varchar) AS text)]));

ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_usable_field_ratio_check CHECK (usable_field_ratio >= CAST(0 AS double precision) AND usable_field_ratio <= CAST(1 AS double precision));

ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_warning_codes_check CHECK (jsonb_typeof(warning_codes) = CAST('array' AS text));

ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_width_px_check CHECK (width_px > 0);

ALTER TABLE public.local_execution_jobs ADD CONSTRAINT local_execution_jobs_state_check CHECK (state = ANY(ARRAY[CAST('held' AS text), CAST('calculation_reported' AS text), CAST('released' AS text), CAST('failed' AS text)]));

ALTER TABLE public.microscopy_analysis_events ADD CONSTRAINT microscopy_analysis_events_progress_current_check CHECK (progress_current IS NULL OR progress_current >= 0);

ALTER TABLE public.microscopy_analysis_events ADD CONSTRAINT microscopy_analysis_events_progress_total_check CHECK (progress_total IS NULL OR progress_total >= 0);

ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_images_input_file_size_bytes_check CHECK (input_file_size_bytes > 0);

ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_images_input_height_px_check CHECK (input_height_px > 0);

ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_images_input_width_px_check CHECK (input_width_px > 0);

ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_images_quality_status_check CHECK (CAST(quality_status AS text) = ANY(ARRAY[CAST(CAST('pending' AS varchar) AS text), CAST(CAST('pass' AS varchar) AS text), CAST(CAST('warning' AS varchar) AS text), CAST(CAST('fail' AS varchar) AS text), CAST(CAST('error' AS varchar) AS text)]));

ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_images_sequence_number_check CHECK (sequence_number > 0);

ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_active_stage_check CHECK (CAST(active_stage AS text) = ANY(ARRAY[CAST(CAST('created' AS varchar) AS text), CAST(CAST('integrity_check' AS varchar) AS text), CAST(CAST('quality_assessment' AS varchar) AS text), CAST(CAST('quality_aggregation' AS varchar) AS text), CAST(CAST('technical_review' AS varchar) AS text), CAST(CAST('completed' AS varchar) AS text), CAST(CAST('failed' AS varchar) AS text)]));

ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_input_image_count_check CHECK (input_image_count > 0);

ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_quality_gate_status_check CHECK (CAST(quality_gate_status AS text) = ANY(ARRAY[CAST(CAST('pending' AS varchar) AS text), CAST(CAST('pass' AS varchar) AS text), CAST(CAST('warning' AS varchar) AS text), CAST(CAST('fail' AS varchar) AS text), CAST(CAST('error' AS varchar) AS text)]));

ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_quality_profile_snapshot_check CHECK (jsonb_typeof(quality_profile_snapshot) = CAST('object' AS text));

ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_run_status_check CHECK (CAST(run_status AS text) = ANY(ARRAY[CAST(CAST('created' AS varchar) AS text), CAST(CAST('quality_pending' AS varchar) AS text), CAST(CAST('quality_processing' AS varchar) AS text), CAST(CAST('quality_completed' AS varchar) AS text), CAST(CAST('review_required' AS varchar) AS text), CAST(CAST('ready_for_analysis' AS varchar) AS text), CAST(CAST('blocked' AS varchar) AS text), CAST(CAST('failed' AS varchar) AS text), CAST(CAST('cancelled' AS varchar) AS text)]));

ALTER TABLE public.microscopy_images ADD CONSTRAINT ck_microscopy_image_archive_state CHECK ((CAST(status AS text) <> CAST('archived' AS text) AND archived_at IS NULL AND archived_by IS NULL) OR (CAST(status AS text) = CAST('archived' AS text) AND archived_at IS NOT NULL AND archived_by IS NOT NULL));

ALTER TABLE public.microscopy_images ADD CONSTRAINT ck_microscopy_images_acquisition_origin CHECK (CAST(acquisition_origin AS text) = ANY(ARRAY[CAST(CAST('manual_upload' AS varchar) AS text), CAST(CAST('research_dataset_import' AS varchar) AS text), CAST(CAST('external_capture_system' AS varchar) AS text)]));

ALTER TABLE public.microscopy_images ADD CONSTRAINT ck_microscopy_images_channels CHECK (channel_count IS NULL OR channel_count > 0);

ALTER TABLE public.microscopy_images ADD CONSTRAINT ck_microscopy_images_sequence CHECK (image_sequence_number IS NULL OR image_sequence_number > 0);

ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_bit_depth_check CHECK (bit_depth IS NULL OR bit_depth > 0);

ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_file_size_bytes_check CHECK (file_size_bytes > 0);

ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_height_px_check CHECK (height_px > 0);

ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_image_code_check CHECK (btrim(CAST(image_code AS text)) <> CAST('' AS text));

ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_magnification_check CHECK (magnification IS NULL OR magnification > CAST(0 AS numeric));

ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_metadata_json_check CHECK (jsonb_typeof(metadata_json) = CAST('object' AS text));

ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_mime_type_check CHECK (btrim(CAST(mime_type AS text)) <> CAST('' AS text));

ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_sha256_check CHECK (sha256 ~ CAST('^[0-9a-fA-F]{64}$' AS text));

ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('registered' AS varchar) AS text), CAST(CAST('available' AS varchar) AS text), CAST(CAST('unavailable' AS varchar) AS text), CAST(CAST('rejected' AS varchar) AS text), CAST(CAST('archived' AS varchar) AS text)]));

ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_storage_key_check CHECK (btrim(storage_key) <> CAST('' AS text));

ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_width_px_check CHECK (width_px > 0);

ALTER TABLE public.model_governance_backfill_audit ADD CONSTRAINT chk_model_governance_audit_after_object CHECK (jsonb_typeof(after_values) = CAST('object' AS text));

ALTER TABLE public.model_governance_backfill_audit ADD CONSTRAINT chk_model_governance_audit_before_object CHECK (jsonb_typeof(before_values) = CAST('object' AS text));

ALTER TABLE public.model_governance_backfill_audit ADD CONSTRAINT chk_model_governance_audit_event_type CHECK (event_type = ANY(ARRAY[CAST('apply' AS text), CAST('revert' AS text)]));

ALTER TABLE public.model_governance_backfill_audit ADD CONSTRAINT chk_model_governance_audit_metadata_object CHECK (jsonb_typeof(metadata) = CAST('object' AS text));

ALTER TABLE public.model_governance_backfill_audit ADD CONSTRAINT chk_model_governance_audit_result_status CHECK (result_status = ANY(ARRAY[CAST('applied' AS text), CAST('reverted' AS text), CAST('exact' AS text), CAST('ambiguous' AS text), CAST('missing' AS text), CAST('checksum_mismatch' AS text), CAST('skipped' AS text)]));

ALTER TABLE public.model_governance_backfill_audit ADD CONSTRAINT chk_model_governance_audit_reversal CHECK ((event_type = CAST('apply' AS text) AND reversal_of_audit_id IS NULL) OR (event_type = CAST('revert' AS text) AND reversal_of_audit_id IS NOT NULL));

ALTER TABLE public.model_versions ADD CONSTRAINT chk_model_versions_artifact_requires_training CHECK (checkpoint_artifact_id IS NULL OR training_run_id IS NOT NULL);

ALTER TABLE public.model_versions ADD CONSTRAINT chk_model_versions_artifact_size CHECK (artifact_size_bytes IS NULL OR artifact_size_bytes >= 0);

ALTER TABLE public.model_versions ADD CONSTRAINT chk_model_versions_governed_hash CHECK (status <> ALL(ARRAY[CAST('candidate' AS text), CAST('validated' AS text), CAST('approved' AS text), CAST('deployed' AS text), CAST('rejected' AS text), CAST('retired' AS text)]) OR (checkpoint_artifact_id IS NOT NULL AND artifact_sha256 IS NOT NULL));

ALTER TABLE public.model_versions ADD CONSTRAINT chk_model_versions_lineage_status CHECK (lineage_status = ANY(ARRAY[CAST('unresolved' AS text), CAST('resolved' AS text), CAST('ambiguous' AS text), CAST('artifact_missing' AS text), CAST('checksum_mismatch' AS text), CAST('legacy_unresolved' AS text)]));

ALTER TABLE public.model_versions ADD CONSTRAINT chk_model_versions_profile_objects CHECK (jsonb_typeof(preprocessing_profile_snapshot) = CAST('object' AS text) AND jsonb_typeof(class_mapping) = CAST('object' AS text) AND jsonb_typeof(input_signature) = CAST('object' AS text) AND jsonb_typeof(output_signature) = CAST('object' AS text));

ALTER TABLE public.model_versions ADD CONSTRAINT chk_model_versions_resolved_training CHECK (lineage_status <> CAST('resolved' AS text) OR training_run_id IS NOT NULL);

ALTER TABLE public.model_versions ADD CONSTRAINT chk_model_versions_sha256 CHECK (artifact_sha256 IS NULL OR artifact_sha256 ~ CAST('^[0-9a-f]{64}$' AS text));

ALTER TABLE public.model_versions ADD CONSTRAINT chk_model_versions_status CHECK (status = ANY(ARRAY[CAST('discovered' AS text), CAST('candidate' AS text), CAST('validated' AS text), CAST('approved' AS text), CAST('deployed' AS text), CAST('rejected' AS text), CAST('retired' AS text)]));

ALTER TABLE public.model_versions ADD CONSTRAINT chk_model_versions_version_number CHECK (version_number IS NULL OR version_number > 0);

ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_bbox CHECK ((bbox_x IS NULL OR bbox_x >= CAST(0 AS numeric)) AND (bbox_y IS NULL OR bbox_y >= CAST(0 AS numeric)) AND (bbox_width IS NULL OR bbox_width > CAST(0 AS numeric)) AND (bbox_height IS NULL OR bbox_height > CAST(0 AS numeric)));

ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_cell_requirements CHECK (prediction_scope <> CAST('cell' AS text) OR (image_analysis_job_id IS NOT NULL AND inference_run_id IS NOT NULL AND deployed_model_version_id IS NOT NULL AND model_version_id IS NOT NULL AND classifier_model_version_id IS NOT NULL AND model_version_id = classifier_model_version_id AND run_id IS NOT NULL AND run_id = inference_run_id AND cell_index IS NOT NULL AND cell_index >= 0 AND bbox_x IS NOT NULL AND bbox_y IS NOT NULL AND bbox_width IS NOT NULL AND bbox_height IS NOT NULL AND probability_parasitized IS NOT NULL AND probability_uninfected IS NOT NULL AND threshold_used IS NOT NULL AND predicted_class IS NOT NULL AND predicted_label IS NOT NULL));

ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_class_label CHECK (predicted_class IS NULL OR (predicted_class = 0 AND predicted_label = CAST('uninfected' AS text)) OR (predicted_class = 1 AND predicted_label = CAST('parasitized' AS text)));

ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_confidence_level CHECK (confidence_level IS NULL OR confidence_level = ANY(ARRAY[CAST('low' AS text), CAST('medium' AS text), CAST('high' AS text), CAST('uncertain' AS text), CAST('not_assessed' AS text)]));

ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_predicted_class CHECK (predicted_class IS NULL OR predicted_class = ANY(ARRAY[0, 1]));

ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_probability_parasitized CHECK (probability_parasitized IS NULL OR (probability_parasitized >= CAST(0 AS numeric) AND probability_parasitized <= CAST(1 AS numeric)));

ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_probability_uninfected CHECK (probability_uninfected IS NULL OR (probability_uninfected >= CAST(0 AS numeric) AND probability_uninfected <= CAST(1 AS numeric)));

ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_quality_status CHECK (quality_status IS NULL OR quality_status = ANY(ARRAY[CAST('not_assessed' AS text), CAST('pending' AS text), CAST('passed' AS text), CAST('warning' AS text), CAST('rejected' AS text), CAST('failed' AS text), CAST('skipped' AS text)]));

ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_review_status CHECK (review_status = ANY(ARRAY[CAST('unreviewed' AS text), CAST('pending' AS text), CAST('confirmed' AS text), CAST('corrected' AS text), CAST('rejected' AS text)]));

ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_reviewed_label CHECK (reviewed_label IS NULL OR reviewed_label = ANY(ARRAY[CAST('uninfected' AS text), CAST('parasitized' AS text)]));

ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_scope CHECK (prediction_scope = ANY(ARRAY[CAST('legacy_image' AS text), CAST('image' AS text), CAST('cell' AS text)]));

ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_threshold_used CHECK (threshold_used IS NULL OR (threshold_used >= CAST(0 AS numeric) AND threshold_used <= CAST(1 AS numeric)));

ALTER TABLE public.quality_assessment_queue_items ADD CONSTRAINT quality_assessment_queue_items_attempt_count_check CHECK (attempt_count >= 0);

ALTER TABLE public.quality_assessment_queue_items ADD CONSTRAINT quality_assessment_queue_items_priority_check CHECK (priority = ANY(ARRAY[1, 50, 100]));

ALTER TABLE public.quality_assessment_queue_items ADD CONSTRAINT quality_assessment_queue_items_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('queued' AS varchar) AS text), CAST(CAST('running' AS varchar) AS text), CAST(CAST('completed' AS varchar) AS text), CAST(CAST('failed' AS varchar) AS text)]));

ALTER TABLE public.quality_gate_decisions ADD CONSTRAINT quality_gate_decisions_comment_check CHECK (length(btrim(comment)) > 0);

ALTER TABLE public.quality_gate_decisions ADD CONSTRAINT quality_gate_decisions_decision_check CHECK (CAST(decision AS text) = ANY(ARRAY[CAST(CAST('approve_with_warnings' AS varchar) AS text), CAST(CAST('reject' AS varchar) AS text)]));

ALTER TABLE public.research_subjects ADD CONSTRAINT ck_research_subject_archive_state CHECK ((CAST(status AS text) = CAST('active' AS text) AND archived_at IS NULL AND archived_by IS NULL) OR (CAST(status AS text) = CAST('archived' AS text) AND archived_at IS NOT NULL));

ALTER TABLE public.research_subjects ADD CONSTRAINT research_subjects_metadata_json_check CHECK (jsonb_typeof(metadata_json) = CAST('object' AS text));

ALTER TABLE public.research_subjects ADD CONSTRAINT research_subjects_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('active' AS varchar) AS text), CAST(CAST('archived' AS varchar) AS text)]));

ALTER TABLE public.research_subjects ADD CONSTRAINT research_subjects_subject_code_check CHECK (btrim(CAST(subject_code AS text)) <> CAST('' AS text));

ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT chk_run_clinical_metrics_split CHECK (split_name = ANY(ARRAY[CAST('train' AS text), CAST('val' AS text), CAST('validation' AS text), CAST('test' AS text), CAST('external' AS text)]));

ALTER TABLE public.run_dataset_images ADD CONSTRAINT chk_run_dataset_images_class_index CHECK (class_index = ANY(ARRAY[0, 1]));

ALTER TABLE public.run_dataset_images ADD CONSTRAINT chk_run_dataset_images_class_name CHECK (class_name = ANY(ARRAY[CAST('uninfected' AS text), CAST('parasitized' AS text)]));

ALTER TABLE public.run_dataset_images ADD CONSTRAINT chk_run_dataset_images_split CHECK (split_name = ANY(ARRAY[CAST('train' AS text), CAST('val' AS text), CAST('validation' AS text), CAST('test' AS text)]));

ALTER TABLE public.run_dataset_images ADD CONSTRAINT chk_run_dataset_images_usage_context CHECK (usage_context = ANY(ARRAY[CAST('train' AS text), CAST('validation' AS text), CAST('evaluation' AS text), CAST('explainability' AS text), CAST('tta' AS text), CAST('ensemble' AS text), CAST('svm_features' AS text), CAST('inference' AS text)]));

ALTER TABLE public.run_image_predictions ADD CONSTRAINT chk_run_image_predictions_case_type CHECK (case_type IS NULL OR case_type = ANY(ARRAY[CAST('true_positive' AS text), CAST('true_negative' AS text), CAST('false_positive' AS text), CAST('false_negative' AS text), CAST('low_confidence' AS text), CAST('unknown' AS text)]));

ALTER TABLE public.run_image_predictions ADD CONSTRAINT chk_run_image_predictions_split CHECK (split_name IS NULL OR split_name = ANY(ARRAY[CAST('train' AS text), CAST('val' AS text), CAST('validation' AS text), CAST('test' AS text), CAST('external' AS text)]));

ALTER TABLE public.run_image_predictions ADD CONSTRAINT chk_run_image_predictions_usage_context CHECK (usage_context IS NULL OR usage_context = ANY(ARRAY[CAST('train' AS text), CAST('validation' AS text), CAST('evaluation' AS text), CAST('explainability' AS text), CAST('tta' AS text), CAST('ensemble' AS text), CAST('svm_features' AS text), CAST('inference' AS text)]));

ALTER TABLE public.run_lineage ADD CONSTRAINT chk_run_lineage_confidence CHECK (confidence = ANY(ARRAY[CAST('explicit' AS text), CAST('inferred_exact_checkpoint' AS text), CAST('inferred_model_version' AS text), CAST('inferred_heuristic' AS text), CAST('unknown' AS text)]));

ALTER TABLE public.run_lineage ADD CONSTRAINT chk_run_lineage_distinct_runs CHECK (parent_run_id <> child_run_id);

ALTER TABLE public.run_lineage ADD CONSTRAINT chk_run_lineage_relationship_type CHECK (relationship_type = ANY(ARRAY[CAST('evaluates_checkpoint_from' AS text), CAST('explains_checkpoint_from' AS text), CAST('derived_from' AS text)]));

ALTER TABLE public.run_model_deployments ADD CONSTRAINT chk_run_model_deployments_metadata CHECK (jsonb_typeof(metadata) = CAST('object' AS text));

ALTER TABLE public.run_model_deployments ADD CONSTRAINT chk_run_model_deployments_ordinal CHECK (ordinal >= 0);

ALTER TABLE public.run_model_deployments ADD CONSTRAINT chk_run_model_deployments_role CHECK (role = ANY(ARRAY[CAST('primary' AS text), CAST('classifier' AS text), CAST('detector' AS text), CAST('ensemble_member' AS text), CAST('explainer' AS text)]));

ALTER TABLE public.run_model_deployments ADD CONSTRAINT chk_run_model_deployments_weight CHECK (weight IS NULL OR (weight >= CAST(0 AS numeric) AND weight <= CAST(1 AS numeric)));

ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT chk_run_threshold_calibration_positive_label CHECK (positive_label = CAST('parasitized' AS text));

ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT chk_run_threshold_calibration_score_name CHECK (score_name = CAST('probability_parasitized' AS text));

ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT chk_run_threshold_calibration_split CHECK (calibration_split = ANY(ARRAY[CAST('val' AS text), CAST('validation' AS text)]));

ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT chk_run_threshold_calibration_status CHECK (calibration_status = ANY(ARRAY[CAST('recorded' AS text), CAST('validated' AS text), CAST('rejected' AS text), CAST('retired' AS text)]));

ALTER TABLE public.runs ADD CONSTRAINT chk_runs_configuration_object CHECK (configuration IS NULL OR jsonb_typeof(configuration) = CAST('object' AS text));

ALTER TABLE public.runs ADD CONSTRAINT ck_runs_release_status_requires_timestamp CHECK (release_status IS NULL OR release_updated_at IS NOT NULL);

ALTER TABLE public.runs ADD CONSTRAINT ck_runs_release_status_training_vocabulary CHECK (release_status IS NULL OR (run_type = CAST('training' AS text) AND release_status = ANY(ARRAY[CAST('not_available' AS text), CAST('available_to_publish' AS text), CAST('productive_stage2' AS text)])));

ALTER TABLE public.schema_migrations ADD CONSTRAINT chk_schema_migrations_checksum_sha256 CHECK (checksum ~ CAST('^[0-9a-f]{64}$' AS text));

ALTER TABLE public.scientific_cases ADD CONSTRAINT ck_scientific_case_archive_state CHECK ((CAST(status AS text) <> CAST('archived' AS text) AND archived_at IS NULL AND archived_by IS NULL) OR (CAST(status AS text) = CAST('archived' AS text) AND archived_at IS NOT NULL AND archived_by IS NOT NULL));

ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_case_code_check CHECK (btrim(CAST(case_code AS text)) <> CAST('' AS text));

ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_metadata_json_check CHECK (jsonb_typeof(metadata_json) = CAST('object' AS text));

ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_priority_check CHECK (CAST(priority AS text) = ANY(ARRAY[CAST(CAST('low' AS varchar) AS text), CAST(CAST('normal' AS varchar) AS text), CAST(CAST('high' AS varchar) AS text)]));

ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_source_type_check CHECK (CAST(source_type AS text) = ANY(ARRAY[CAST(CAST('physical_microscope' AS varchar) AS text), CAST(CAST('imported_image' AS varchar) AS text), CAST(CAST('research_dataset' AS varchar) AS text), CAST(CAST('synthetic' AS varchar) AS text)]));

ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('draft' AS varchar) AS text), CAST(CAST('registered' AS varchar) AS text), CAST(CAST('ready' AS varchar) AS text), CAST(CAST('archived' AS varchar) AS text)]));

ALTER TABLE public.scientific_reviews ADD CONSTRAINT ck_scientific_review_comment CHECK ((CAST(decision AS text) = CAST('accepted' AS text) AND (comment IS NULL OR btrim(comment) <> CAST('' AS text))) OR (CAST(decision AS text) = ANY(ARRAY[CAST(CAST('rejected' AS varchar) AS text), CAST(CAST('needs_attention' AS varchar) AS text), CAST(CAST('comment_only' AS varchar) AS text)]) AND comment IS NOT NULL AND btrim(comment) <> CAST('' AS text)));

ALTER TABLE public.scientific_reviews ADD CONSTRAINT scientific_reviews_decision_check CHECK (CAST(decision AS text) = ANY(ARRAY[CAST(CAST('accepted' AS varchar) AS text), CAST(CAST('rejected' AS varchar) AS text), CAST(CAST('needs_attention' AS varchar) AS text), CAST(CAST('comment_only' AS varchar) AS text)]));

ALTER TABLE public.scientific_reviews ADD CONSTRAINT scientific_reviews_entity_type_check CHECK (CAST(entity_type AS text) = CAST('cell_detection' AS text));

ALTER TABLE public.scientific_validation_annotation_events ADD CONSTRAINT ck_validation_annotation_event_before CHECK ((CAST(event_type AS text) = CAST('created' AS text) AND before_state IS NULL AND annotation_version = 1) OR (CAST(event_type AS text) = CAST('updated' AS text) AND jsonb_typeof(before_state) = CAST('object' AS text) AND annotation_version > 1));

ALTER TABLE public.scientific_validation_annotation_events ADD CONSTRAINT scientific_validation_annotation_event_annotation_version_check CHECK (annotation_version > 0);

ALTER TABLE public.scientific_validation_annotation_events ADD CONSTRAINT scientific_validation_annotation_events_after_state_check CHECK (jsonb_typeof(after_state) = CAST('object' AS text));

ALTER TABLE public.scientific_validation_annotation_events ADD CONSTRAINT scientific_validation_annotation_events_event_type_check CHECK (CAST(event_type AS text) = ANY(ARRAY[CAST(CAST('created' AS varchar) AS text), CAST(CAST('updated' AS varchar) AS text)]));

ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT ck_validation_annotation_exact_target CHECK ((CAST(target_type AS text) = CAST('cell' AS text) AND cell_detection_id IS NOT NULL AND analysis_run_id IS NULL AND sample_id IS NULL) OR (CAST(target_type AS text) = CAST('analysis' AS text) AND analysis_run_id IS NOT NULL AND cell_detection_id IS NULL AND sample_id IS NULL) OR (CAST(target_type AS text) = CAST('sample' AS text) AND sample_id IS NOT NULL AND cell_detection_id IS NULL AND analysis_run_id IS NULL));

ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_category_check CHECK (btrim(CAST(category AS text)) <> CAST('' AS text));

ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_content_check CHECK (btrim(content) <> CAST('' AS text));

ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_target_type_check CHECK (CAST(target_type AS text) = ANY(ARRAY[CAST(CAST('cell' AS varchar) AS text), CAST(CAST('analysis' AS varchar) AS text), CAST(CAST('sample' AS varchar) AS text)]));

ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_version_check CHECK (version > 0);

ALTER TABLE public.scientific_validation_images ADD CONSTRAINT scientific_validation_images_image_sha256_check CHECK (image_sha256 ~ CAST('^[0-9a-f]{64}$' AS text));

ALTER TABLE public.scientific_validation_images ADD CONSTRAINT scientific_validation_images_sequence_number_check CHECK (sequence_number > 0);

ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT ck_validation_session_archive CHECK ((CAST(status AS text) <> CAST('archived' AS text) AND archived_at IS NULL AND archived_by IS NULL) OR (CAST(status AS text) = CAST('archived' AS text) AND archived_at IS NOT NULL AND archived_by IS NOT NULL));

ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_datasource_check CHECK (btrim(CAST(datasource AS text)) <> CAST('' AS text));

ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_initial_snapshot_check CHECK (jsonb_typeof(initial_snapshot) = CAST('object' AS text));

ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_matching_iou_threshold_check CHECK (matching_iou_threshold > CAST(0 AS double precision) AND matching_iou_threshold <= CAST(1 AS double precision));

ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_name_check CHECK (btrim(CAST(name AS text)) <> CAST('' AS text));

ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_protocol_key_check CHECK (btrim(CAST(protocol_key AS text)) <> CAST('' AS text));

ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_protocol_version_check CHECK (btrim(CAST(protocol_version AS text)) <> CAST('' AS text));

ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_snapshot_sha256_check CHECK (snapshot_sha256 ~ CAST('^[0-9a-f]{64}$' AS text));

ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('draft' AS varchar) AS text), CAST(CAST('annotation_in_progress' AS varchar) AS text), CAST(CAST('ready_for_analysis' AS varchar) AS text), CAST(CAST('completed' AS varchar) AS text), CAST(CAST('archived' AS varchar) AS text)]));

ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT ck_smear_summary_counts CHECK (classified_cell_count = (parasitized_candidate_count + uninfected_candidate_count) AND (classified_cell_count + failed_prediction_count) = eligible_cell_count AND near_threshold_count <= classified_cell_count);

ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT ck_smear_summary_fraction CHECK ((classified_cell_count = 0 AND parasitized_candidate_fraction IS NULL) OR (classified_cell_count > 0 AND parasitized_candidate_fraction >= CAST(0 AS double precision) AND parasitized_candidate_fraction <= CAST(1 AS double precision) AND abs(parasitized_candidate_fraction - (CAST(parasitized_candidate_count AS double precision) / CAST(classified_cell_count AS double precision))) <= CAST(0.000000001 AS double precision)));

ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT ck_smear_summary_probabilities CHECK ((classified_cell_count = 0 AND maximum_probability_parasitized IS NULL AND mean_probability_parasitized IS NULL AND median_probability_parasitized IS NULL) OR (classified_cell_count > 0 AND maximum_probability_parasitized >= CAST(0 AS double precision) AND maximum_probability_parasitized <= CAST(1 AS double precision) AND mean_probability_parasitized >= CAST(0 AS double precision) AND mean_probability_parasitized <= CAST(1 AS double precision) AND median_probability_parasitized >= CAST(0 AS double precision) AND median_probability_parasitized <= CAST(1 AS double precision)));

ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_aggregation_policy_snapshot_check CHECK (jsonb_typeof(aggregation_policy_snapshot) = CAST('object' AS text));

ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_classified_cell_count_check CHECK (classified_cell_count >= 0);

ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_eligible_cell_count_check CHECK (eligible_cell_count >= 0);

ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_failed_prediction_count_check CHECK (failed_prediction_count >= 0);

ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_near_threshold_count_check CHECK (near_threshold_count >= 0);

ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_outcome_check CHECK (CAST(outcome AS text) = ANY(ARRAY[CAST(CAST('suspicious_cells_detected' AS varchar) AS text), CAST(CAST('no_suspicious_cells_detected' AS varchar) AS text), CAST(CAST('inconclusive' AS varchar) AS text)]));

ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_parasitized_candidate_count_check CHECK (parasitized_candidate_count >= 0);

ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_per_image_summary_check CHECK (jsonb_typeof(per_image_summary) = CAST('object' AS text));

ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_uninfected_candidate_count_check CHECK (uninfected_candidate_count >= 0);

ALTER TABLE public.smear_slides ADD CONSTRAINT ck_smear_slide_archive_state CHECK ((CAST(status AS text) <> CAST('archived' AS text) AND archived_at IS NULL AND archived_by IS NULL) OR (CAST(status AS text) = CAST('archived' AS text) AND archived_at IS NOT NULL AND archived_by IS NOT NULL));

ALTER TABLE public.smear_slides ADD CONSTRAINT smear_slides_metadata_json_check CHECK (jsonb_typeof(metadata_json) = CAST('object' AS text));

ALTER TABLE public.smear_slides ADD CONSTRAINT smear_slides_slide_code_check CHECK (btrim(CAST(slide_code AS text)) <> CAST('' AS text));

ALTER TABLE public.smear_slides ADD CONSTRAINT smear_slides_smear_type_check CHECK (CAST(smear_type AS text) = ANY(ARRAY[CAST(CAST('thin' AS varchar) AS text), CAST(CAST('thick' AS varchar) AS text), CAST(CAST('combined' AS varchar) AS text), CAST(CAST('unknown' AS varchar) AS text)]));

ALTER TABLE public.smear_slides ADD CONSTRAINT smear_slides_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('registered' AS varchar) AS text), CAST(CAST('prepared' AS varchar) AS text), CAST(CAST('ready_for_capture' AS varchar) AS text), CAST(CAST('archived' AS varchar) AS text)]));

ALTER TABLE public.stage2_model_publication_events ADD CONSTRAINT chk_stage2_publication_event_metadata CHECK (jsonb_typeof(metadata) = CAST('object' AS text));

ALTER TABLE public.stage2_model_publication_events ADD CONSTRAINT chk_stage2_publication_event_status CHECK (new_status = ANY(ARRAY[CAST('active' AS text), CAST('inactive' AS text)]) AND (previous_status IS NULL OR previous_status = ANY(ARRAY[CAST('active' AS text), CAST('inactive' AS text)])));

ALTER TABLE public.stage2_model_publication_events ADD CONSTRAINT chk_stage2_publication_event_type CHECK (event_type = ANY(ARRAY[CAST('MODEL_STAGE2_PUBLISHED' AS text), CAST('MODEL_STAGE2_DEACTIVATED' AS text), CAST('MODEL_STAGE2_REACTIVATED' AS text)]));

ALTER TABLE public.stage2_model_publications ADD CONSTRAINT chk_stage2_publication_metadata CHECK (jsonb_typeof(metadata) = CAST('object' AS text));

ALTER TABLE public.stage2_model_publications ADD CONSTRAINT chk_stage2_publication_scope CHECK (scope = CAST('stage2' AS text));

ALTER TABLE public.stage2_model_publications ADD CONSTRAINT chk_stage2_publication_state CHECK ((status = CAST('active' AS text) AND is_active AND deactivated_at IS NULL) OR (status = CAST('inactive' AS text) AND NOT is_active AND deactivated_at IS NOT NULL));

ALTER TABLE public.stage2_model_publications ADD CONSTRAINT chk_stage2_publication_status CHECK (status = ANY(ARRAY[CAST('active' AS text), CAST('inactive' AS text)]));

ALTER TABLE public.train_execution_records ADD CONSTRAINT train_event_metadata CHECK ((event_id IS NULL AND event_sequence IS NULL AND kind <> CAST('e10_event' AS text)) OR (event_id IS NOT NULL AND event_sequence IS NOT NULL AND event_sequence >= CAST(1 AS numeric) AND event_sequence = trunc(event_sequence) AND event_sequence <> ALL(ARRAY[CAST('NaN' AS numeric), CAST('Infinity' AS numeric), CAST('-Infinity' AS numeric)]) AND kind = CAST('e10_event' AS text) AND phase = CAST('run_event_v1' AS text) AND record_key = CAST(event_id AS text) AND NOT jsonb_typeof(payload -> CAST('canonical_event' AS text)) IS DISTINCT FROM CAST('string' AS text) AND (payload - CAST('canonical_event' AS text)) = CAST('{}' AS jsonb)));

ALTER TABLE public.train_execution_records ADD CONSTRAINT train_execution_records_payload_check CHECK (jsonb_typeof(payload) = CAST('object' AS text));

ALTER TABLE public.train_execution_sessions ADD CONSTRAINT train_execution_sessions_check CHECK (state <> ALL(ARRAY[CAST('completed' AS text), CAST('verified' AS text)]) OR completion IS NOT NULL);

ALTER TABLE public.train_execution_sessions ADD CONSTRAINT train_execution_sessions_check1 CHECK (state <> CAST('verified' AS text) OR verification IS NOT NULL);

ALTER TABLE public.train_execution_sessions ADD CONSTRAINT train_execution_sessions_parent_pid_check CHECK (parent_pid > 0);

ALTER TABLE public.train_execution_sessions ADD CONSTRAINT train_execution_sessions_state_check CHECK (state = ANY(ARRAY[CAST('active' AS text), CAST('completed' AS text), CAST('verified' AS text), CAST('failed' AS text), CAST('interrupted' AS text)]));

ALTER TABLE public.users ADD CONSTRAINT users_status_check CHECK (status = ANY(ARRAY[CAST('active' AS text), CAST('disabled' AS text)]));

ALTER TABLE public.artifacts ADD CONSTRAINT artifacts_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE;

ALTER TABLE public.assessment_artifacts ADD CONSTRAINT assessment_artifacts_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES assessment_attempts (id);

ALTER TABLE public.assessment_attempts ADD CONSTRAINT assessment_attempts_identity_id_fkey FOREIGN KEY (identity_id) REFERENCES assessment_identities (id);

ALTER TABLE public.assessment_campaign_consumers ADD CONSTRAINT assessment_campaign_consumers_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns (id);

ALTER TABLE public.assessment_campaign_consumers ADD CONSTRAINT assessment_campaign_consumers_identity_id_fkey FOREIGN KEY (identity_id) REFERENCES assessment_identities (id);

ALTER TABLE public.assessment_campaign_consumers ADD CONSTRAINT assessment_campaign_consumers_member_id_fkey FOREIGN KEY (member_id) REFERENCES campaign_members (id);

ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_training_run_id_fkey FOREIGN KEY (training_run_id) REFERENCES runs (id);

ALTER TABLE public.assessment_results ADD CONSTRAINT assessment_results_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES assessment_attempts (id);

ALTER TABLE public.audit_events ADD CONSTRAINT audit_events_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.blood_samples ADD CONSTRAINT blood_samples_archived_by_fkey FOREIGN KEY (archived_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.blood_samples ADD CONSTRAINT blood_samples_case_id_fkey FOREIGN KEY (case_id) REFERENCES scientific_cases (id) ON DELETE RESTRICT;

ALTER TABLE public.blood_samples ADD CONSTRAINT blood_samples_created_by_fkey FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.blood_samples ADD CONSTRAINT blood_samples_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_member_id_fkey FOREIGN KEY (member_id) REFERENCES campaign_members (id) ON DELETE RESTRICT;

ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_training_run_id_fkey FOREIGN KEY (training_run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.campaign_configurations ADD CONSTRAINT campaign_configurations_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns (id) ON DELETE RESTRICT;

ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES campaign_attempts (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns (id);

ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_campaign_id_revision_id_fkey FOREIGN KEY (campaign_id, revision_id) REFERENCES campaign_technical_revisions (campaign_id, id);

ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_member_id_fkey FOREIGN KEY (member_id) REFERENCES campaign_members (id);

ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_previous_attempt_id_fkey FOREIGN KEY (previous_attempt_id) REFERENCES campaign_attempts (id);

ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.campaign_execution_events ADD CONSTRAINT campaign_execution_events_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns (id);

ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_campaign_id_configuration_hash_fkey FOREIGN KEY (campaign_id, configuration_hash) REFERENCES campaign_configurations (campaign_id, configuration_hash) ON DELETE RESTRICT;

ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns (id) ON DELETE RESTRICT;

ALTER TABLE public.campaign_members ADD CONSTRAINT fk_member_accepted_attempt FOREIGN KEY (id, accepted_attempt_id) REFERENCES campaign_attempts (member_id, id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.campaign_technical_revisions ADD CONSTRAINT campaign_technical_revisions_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns (id);

ALTER TABLE public.cell_classification_events ADD CONSTRAINT cell_classification_events_cell_detection_id_fkey FOREIGN KEY (cell_detection_id) REFERENCES cell_detections (id) ON DELETE RESTRICT;

ALTER TABLE public.cell_classification_events ADD CONSTRAINT cell_classification_events_classification_run_id_fkey FOREIGN KEY (classification_run_id) REFERENCES cell_classification_runs (id) ON DELETE RESTRICT;

ALTER TABLE public.cell_classification_events ADD CONSTRAINT fk_cell_classification_event_prediction FOREIGN KEY (cell_prediction_id, classification_run_id) REFERENCES cell_predictions (id, classification_run_id) ON DELETE RESTRICT;

ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT fk_cell_classification_input_crop FOREIGN KEY (crop_id, cell_detection_id) REFERENCES cell_crops (id, cell_detection_id) ON DELETE RESTRICT;

ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT fk_cell_classification_input_detection FOREIGN KEY (cell_detection_id, detection_run_id, microscopy_image_id) REFERENCES cell_detections (id, detection_run_id, microscopy_image_id) ON DELETE RESTRICT;

ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT fk_cell_classification_input_run_detection FOREIGN KEY (classification_run_id, detection_run_id) REFERENCES cell_classification_runs (id, detection_run_id) ON DELETE RESTRICT;

ALTER TABLE public.cell_classification_reviews ADD CONSTRAINT cell_classification_reviews_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.cell_classification_reviews ADD CONSTRAINT cell_classification_reviews_cell_prediction_id_fkey FOREIGN KEY (cell_prediction_id) REFERENCES cell_predictions (id) ON DELETE RESTRICT;

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_retry_of_run_id_fkey FOREIGN KEY (retry_of_run_id) REFERENCES cell_classification_runs (id) ON DELETE RESTRICT;

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT fk_cell_classification_run_deployment_version FOREIGN KEY (production_model_id, model_registry_id) REFERENCES deployed_model_versions (id, model_version_id) ON DELETE RESTRICT;

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT fk_cell_classification_run_detection_analysis FOREIGN KEY (detection_run_id, analysis_run_id) REFERENCES cell_detection_runs (id, analysis_run_id) ON DELETE RESTRICT;

ALTER TABLE public.cell_classification_runs ADD CONSTRAINT fk_cell_classification_run_publication_version FOREIGN KEY (stage2_publication_id, model_registry_id) REFERENCES stage2_model_publications (id, model_version_id) ON DELETE RESTRICT;

ALTER TABLE public.cell_crops ADD CONSTRAINT fk_cell_crops_detection FOREIGN KEY (cell_detection_id) REFERENCES cell_detections (id) ON DELETE RESTRICT;

ALTER TABLE public.cell_detection_events ADD CONSTRAINT cell_detection_events_detection_run_id_fkey FOREIGN KEY (detection_run_id) REFERENCES cell_detection_runs (id) ON DELETE RESTRICT;

ALTER TABLE public.cell_detection_events ADD CONSTRAINT cell_detection_events_microscopy_image_id_fkey FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images (id) ON DELETE RESTRICT;

ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_analysis_run_id_fkey FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs (id) ON DELETE RESTRICT;

ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.cell_detections ADD CONSTRAINT fk_cell_detections_component FOREIGN KEY (connected_component_id, detection_run_id, analysis_run_image_id, microscopy_image_id) REFERENCES image_connected_components (id, detection_run_id, analysis_run_image_id, microscopy_image_id) ON DELETE RESTRICT;

ALTER TABLE public.cell_detections ADD CONSTRAINT fk_cell_detections_run_analysis FOREIGN KEY (detection_run_id, analysis_run_id) REFERENCES cell_detection_runs (id, analysis_run_id) ON DELETE RESTRICT;

ALTER TABLE public.cell_explanations ADD CONSTRAINT cell_explanations_cell_prediction_id_fkey FOREIGN KEY (cell_prediction_id) REFERENCES cell_predictions (id) ON DELETE RESTRICT;

ALTER TABLE public.cell_predictions ADD CONSTRAINT fk_cell_prediction_input_owner FOREIGN KEY (classification_input_id, classification_run_id, cell_detection_id, crop_id) REFERENCES cell_classification_inputs (id, classification_run_id, cell_detection_id, crop_id) ON DELETE RESTRICT;

ALTER TABLE public.clinical_identities ADD CONSTRAINT clinical_identities_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_materialization_activations ADD CONSTRAINT dataset_materialization_activations_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_materialization_activations ADD CONSTRAINT dataset_materialization_activations_materialization_id_fkey FOREIGN KEY (materialization_id) REFERENCES dataset_materializations (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_materializations ADD CONSTRAINT dataset_materializations_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_source_records ADD CONSTRAINT dataset_source_records_clinical_identity_id_fkey FOREIGN KEY (clinical_identity_id) REFERENCES clinical_identities (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_source_records ADD CONSTRAINT dataset_source_records_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_split_assignments ADD CONSTRAINT dataset_split_assignments_clinical_identity_id_fkey FOREIGN KEY (clinical_identity_id) REFERENCES clinical_identities (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_split_assignments ADD CONSTRAINT dataset_split_assignments_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_split_assignments ADD CONSTRAINT dataset_split_assignments_source_record_id_fkey FOREIGN KEY (source_record_id) REFERENCES dataset_source_records (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_split_images ADD CONSTRAINT dataset_split_images_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE SET NULL;

ALTER TABLE public.dataset_split_images ADD CONSTRAINT dataset_split_images_dataset_materialization_id_fkey FOREIGN KEY (dataset_materialization_id) REFERENCES dataset_materializations (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_split_images ADD CONSTRAINT dataset_split_images_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_split_statistics ADD CONSTRAINT dataset_split_statistics_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_split_validation_checks ADD CONSTRAINT dataset_split_validation_checks_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_splits ADD CONSTRAINT dataset_splits_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE CASCADE;

ALTER TABLE public.dataset_version_sources ADD CONSTRAINT dataset_version_sources_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_version_sources ADD CONSTRAINT dataset_version_sources_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT fk_deployed_model_versions_rollback FOREIGN KEY (rollback_of_deployment_id) REFERENCES deployed_model_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT fk_deployed_model_versions_supersedes FOREIGN KEY (supersedes_deployment_id) REFERENCES deployed_model_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT fk_deployed_model_versions_threshold_version FOREIGN KEY (threshold_calibration_id, model_version_id) REFERENCES run_threshold_calibration (run_threshold_calibration_id, model_version_id) ON DELETE RESTRICT;

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT fk_deployed_model_versions_version_artifact FOREIGN KEY (model_version_id, checkpoint_artifact_id) REFERENCES model_versions (id, checkpoint_artifact_id) ON DELETE RESTRICT;

ALTER TABLE public.environment_packages ADD CONSTRAINT environment_packages_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE;

ALTER TABLE public.errors ADD CONSTRAINT errors_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE;

ALTER TABLE public.execution_logs ADD CONSTRAINT execution_logs_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE;

ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_dataset_evidence_id_fkey FOREIGN KEY (dataset_evidence_id) REFERENCES audit_events (id) ON DELETE RESTRICT;

ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE RESTRICT;

ALTER TABLE public.explainability_results ADD CONSTRAINT explainability_results_prediction_id_fkey FOREIGN KEY (prediction_id) REFERENCES predictions (id) ON DELETE SET NULL;

ALTER TABLE public.explainability_results ADD CONSTRAINT explainability_results_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE;

ALTER TABLE public.identity_evidence ADD CONSTRAINT identity_evidence_clinical_identity_id_fkey FOREIGN KEY (clinical_identity_id) REFERENCES clinical_identities (id) ON DELETE RESTRICT;

ALTER TABLE public.identity_evidence ADD CONSTRAINT identity_evidence_source_record_id_fkey FOREIGN KEY (source_record_id) REFERENCES dataset_source_records (id) ON DELETE RESTRICT;

ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT fk_image_analysis_jobs_input_artifact FOREIGN KEY (input_artifact_id) REFERENCES artifacts (id) ON DELETE RESTRICT;

ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT fk_image_analysis_jobs_run_deployment_version FOREIGN KEY (inference_run_id, deployed_model_version_id, model_version_id) REFERENCES run_model_deployments (run_id, deployed_model_version_id, model_version_id) ON DELETE RESTRICT;

ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT fk_image_analysis_jobs_source_image FOREIGN KEY (source_image_id) REFERENCES dataset_split_images (image_id) ON DELETE RESTRICT;

ALTER TABLE public.image_connected_components ADD CONSTRAINT fk_components_detection_analysis FOREIGN KEY (detection_run_id, analysis_run_id) REFERENCES cell_detection_runs (id, analysis_run_id) ON DELETE RESTRICT;

ALTER TABLE public.image_connected_components ADD CONSTRAINT fk_components_frozen_image FOREIGN KEY (analysis_run_image_id, analysis_run_id, microscopy_image_id) REFERENCES microscopy_analysis_run_images (id, analysis_run_id, microscopy_image_id) ON DELETE RESTRICT;

ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_case_id_fkey FOREIGN KEY (case_id) REFERENCES scientific_cases (id) ON DELETE RESTRICT;

ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_created_by_fkey FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_sample_id_fkey FOREIGN KEY (sample_id) REFERENCES blood_samples (id) ON DELETE RESTRICT;

ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_slide_id_fkey FOREIGN KEY (slide_id) REFERENCES smear_slides (id) ON DELETE RESTRICT;

ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES research_subjects (id) ON DELETE RESTRICT;

ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_analysis_run_id_fkey FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs (id) ON DELETE RESTRICT;

ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_analysis_run_image_id_analysis_r_fkey FOREIGN KEY (analysis_run_image_id, analysis_run_id, microscopy_image_id) REFERENCES microscopy_analysis_run_images (id, analysis_run_id, microscopy_image_id) ON DELETE RESTRICT;

ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_microscopy_image_id_fkey FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images (id) ON DELETE RESTRICT;

ALTER TABLE public.local_execution_jobs ADD CONSTRAINT local_execution_jobs_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns (id);

ALTER TABLE public.local_execution_jobs ADD CONSTRAINT local_execution_jobs_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id);

ALTER TABLE public.microscopy_analysis_events ADD CONSTRAINT microscopy_analysis_events_analysis_run_id_fkey FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs (id) ON DELETE RESTRICT;

ALTER TABLE public.microscopy_analysis_events ADD CONSTRAINT microscopy_analysis_events_microscopy_image_id_fkey FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images (id) ON DELETE RESTRICT;

ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_images_analysis_run_id_fkey FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs (id) ON DELETE RESTRICT;

ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_images_microscopy_image_id_fkey FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images (id) ON DELETE RESTRICT;

ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_case_id_fkey FOREIGN KEY (case_id) REFERENCES scientific_cases (id) ON DELETE RESTRICT;

ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_ingestion_batch_id_fkey FOREIGN KEY (ingestion_batch_id) REFERENCES image_ingestion_batches (id) ON DELETE RESTRICT;

ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_sample_id_fkey FOREIGN KEY (sample_id) REFERENCES blood_samples (id) ON DELETE RESTRICT;

ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_slide_id_fkey FOREIGN KEY (slide_id) REFERENCES smear_slides (id) ON DELETE RESTRICT;

ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES research_subjects (id) ON DELETE RESTRICT;

ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_archived_by_fkey FOREIGN KEY (archived_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_created_by_fkey FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_ingestion_batch_id_fkey FOREIGN KEY (ingestion_batch_id) REFERENCES image_ingestion_batches (id) ON DELETE RESTRICT;

ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_slide_id_fkey FOREIGN KEY (slide_id) REFERENCES smear_slides (id) ON DELETE RESTRICT;

ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.model_governance_backfill_audit ADD CONSTRAINT fk_model_governance_audit_reversal FOREIGN KEY (reversal_of_audit_id) REFERENCES model_governance_backfill_audit (id) ON DELETE RESTRICT;

ALTER TABLE public.model_versions ADD CONSTRAINT fk_model_versions_checkpoint_artifact_owner FOREIGN KEY (checkpoint_artifact_id, training_run_id) REFERENCES artifacts (id, run_id) ON DELETE RESTRICT;

ALTER TABLE public.model_versions ADD CONSTRAINT model_versions_model_id_fkey FOREIGN KEY (model_id) REFERENCES models (id) ON DELETE RESTRICT;

ALTER TABLE public.model_versions ADD CONSTRAINT model_versions_training_run_id_fkey FOREIGN KEY (training_run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.predictions ADD CONSTRAINT fk_predictions_analysis_job FOREIGN KEY (image_analysis_job_id) REFERENCES image_analysis_jobs (id) ON DELETE RESTRICT;

ALTER TABLE public.predictions ADD CONSTRAINT fk_predictions_classifier_model_version FOREIGN KEY (classifier_model_version_id) REFERENCES model_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.predictions ADD CONSTRAINT fk_predictions_crop_artifact FOREIGN KEY (crop_artifact_id) REFERENCES artifacts (id) ON DELETE RESTRICT;

ALTER TABLE public.predictions ADD CONSTRAINT fk_predictions_deployed_model_version FOREIGN KEY (deployed_model_version_id) REFERENCES deployed_model_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.predictions ADD CONSTRAINT fk_predictions_detector_model_version FOREIGN KEY (detector_model_version_id) REFERENCES model_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.predictions ADD CONSTRAINT fk_predictions_explanation_artifact FOREIGN KEY (explanation_artifact_id) REFERENCES artifacts (id) ON DELETE RESTRICT;

ALTER TABLE public.predictions ADD CONSTRAINT fk_predictions_inference_run FOREIGN KEY (inference_run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.predictions ADD CONSTRAINT fk_predictions_job_provenance FOREIGN KEY (image_analysis_job_id, inference_run_id, deployed_model_version_id, model_version_id) REFERENCES image_analysis_jobs (id, inference_run_id, deployed_model_version_id, model_version_id) ON DELETE RESTRICT;

ALTER TABLE public.predictions ADD CONSTRAINT fk_predictions_model_version FOREIGN KEY (model_version_id) REFERENCES model_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.predictions ADD CONSTRAINT fk_predictions_source_image FOREIGN KEY (source_image_id) REFERENCES dataset_split_images (image_id) ON DELETE RESTRICT;

ALTER TABLE public.predictions ADD CONSTRAINT predictions_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE SET NULL;

ALTER TABLE public.predictions ADD CONSTRAINT predictions_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE;

ALTER TABLE public.quality_assessment_queue_items ADD CONSTRAINT quality_assessment_queue_items_analysis_run_id_fkey FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs (id) ON DELETE RESTRICT;

ALTER TABLE public.quality_assessment_queue_items ADD CONSTRAINT quality_assessment_queue_items_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.quality_gate_decisions ADD CONSTRAINT quality_gate_decisions_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.quality_gate_decisions ADD CONSTRAINT quality_gate_decisions_analysis_run_id_fkey FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs (id) ON DELETE RESTRICT;

ALTER TABLE public.research_subjects ADD CONSTRAINT research_subjects_archived_by_fkey FOREIGN KEY (archived_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.research_subjects ADD CONSTRAINT research_subjects_created_by_fkey FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.research_subjects ADD CONSTRAINT research_subjects_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.run_checkpoint_policy ADD CONSTRAINT fk_run_checkpoint_policy_artifact_owner FOREIGN KEY (checkpoint_artifact_id, run_id) REFERENCES artifacts (id, run_id) ON DELETE RESTRICT;

ALTER TABLE public.run_checkpoint_policy ADD CONSTRAINT fk_run_checkpoint_policy_model_version_owner FOREIGN KEY (model_version_id, run_id) REFERENCES model_versions (id, training_run_id) ON DELETE RESTRICT;

ALTER TABLE public.run_checkpoint_policy ADD CONSTRAINT fk_run_checkpoint_policy_version_artifact FOREIGN KEY (model_version_id, checkpoint_artifact_id) REFERENCES model_versions (id, checkpoint_artifact_id) ON DELETE RESTRICT;

ALTER TABLE public.run_checkpoint_policy ADD CONSTRAINT run_checkpoint_policy_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE;

ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT run_clinical_metrics_model_id_fkey FOREIGN KEY (model_id) REFERENCES models (id) ON DELETE SET NULL;

ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT run_clinical_metrics_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE;

ALTER TABLE public.run_dataset_images ADD CONSTRAINT run_dataset_images_image_id_fkey FOREIGN KEY (image_id) REFERENCES dataset_split_images (image_id) ON DELETE CASCADE;

ALTER TABLE public.run_dataset_images ADD CONSTRAINT run_dataset_images_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE;

ALTER TABLE public.run_image_predictions ADD CONSTRAINT run_image_predictions_image_id_fkey FOREIGN KEY (image_id) REFERENCES dataset_split_images (image_id) ON DELETE SET NULL;

ALTER TABLE public.run_image_predictions ADD CONSTRAINT run_image_predictions_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE;

ALTER TABLE public.run_io_records ADD CONSTRAINT run_io_records_dataset_materialization_id_fkey FOREIGN KEY (dataset_materialization_id) REFERENCES dataset_materializations (id) ON DELETE RESTRICT;

ALTER TABLE public.run_io_records ADD CONSTRAINT run_io_records_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.run_io_records ADD CONSTRAINT run_io_records_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE;

ALTER TABLE public.run_lineage ADD CONSTRAINT fk_run_lineage_checkpoint_artifact_owner FOREIGN KEY (checkpoint_artifact_id, parent_run_id) REFERENCES artifacts (id, run_id) ON DELETE RESTRICT;

ALTER TABLE public.run_lineage ADD CONSTRAINT fk_run_lineage_model_version_owner FOREIGN KEY (model_version_id, parent_run_id) REFERENCES model_versions (id, training_run_id) ON DELETE RESTRICT;

ALTER TABLE public.run_lineage ADD CONSTRAINT fk_run_lineage_version_artifact FOREIGN KEY (model_version_id, checkpoint_artifact_id) REFERENCES model_versions (id, checkpoint_artifact_id) ON DELETE RESTRICT;

ALTER TABLE public.run_lineage ADD CONSTRAINT run_lineage_child_run_id_fkey FOREIGN KEY (child_run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.run_lineage ADD CONSTRAINT run_lineage_parent_run_id_fkey FOREIGN KEY (parent_run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.run_metrics ADD CONSTRAINT run_metrics_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE;

ALTER TABLE public.run_model_deployments ADD CONSTRAINT fk_run_model_deployments_deployment_version FOREIGN KEY (deployed_model_version_id, model_version_id) REFERENCES deployed_model_versions (id, model_version_id) ON DELETE RESTRICT;

ALTER TABLE public.run_model_deployments ADD CONSTRAINT fk_run_model_deployments_run FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT fk_run_threshold_calibration_artifact_owner FOREIGN KEY (calibration_artifact_id, run_id) REFERENCES artifacts (id, run_id) ON DELETE RESTRICT;

ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT fk_run_threshold_calibration_model_version FOREIGN KEY (model_version_id) REFERENCES model_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT run_threshold_calibration_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE;

ALTER TABLE public.runs ADD CONSTRAINT runs_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns (id);

ALTER TABLE public.runs ADD CONSTRAINT runs_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE SET NULL;

ALTER TABLE public.runs ADD CONSTRAINT runs_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.runs ADD CONSTRAINT runs_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE SET NULL;

ALTER TABLE public.runs ADD CONSTRAINT runs_model_id_fkey FOREIGN KEY (model_id) REFERENCES models (id) ON DELETE SET NULL;

ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_archived_by_fkey FOREIGN KEY (archived_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_created_by_fkey FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES research_subjects (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_reviews ADD CONSTRAINT scientific_reviews_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_reviews ADD CONSTRAINT scientific_reviews_entity_id_fkey FOREIGN KEY (entity_id) REFERENCES cell_detections (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_validation_annotation_events ADD CONSTRAINT scientific_validation_annotation_eve_validation_session_id_fkey FOREIGN KEY (validation_session_id) REFERENCES scientific_validation_sessions (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_validation_annotation_events ADD CONSTRAINT scientific_validation_annotation_events_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_validation_annotation_events ADD CONSTRAINT scientific_validation_annotation_events_annotation_id_fkey FOREIGN KEY (annotation_id) REFERENCES scientific_validation_annotations (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_analysis_run_id_fkey FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_cell_detection_id_fkey FOREIGN KEY (cell_detection_id) REFERENCES cell_detections (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_created_by_fkey FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_sample_id_fkey FOREIGN KEY (sample_id) REFERENCES blood_samples (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_validation_session_id_fkey FOREIGN KEY (validation_session_id) REFERENCES scientific_validation_sessions (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_validation_classification_runs ADD CONSTRAINT scientific_validation_classification_classification_run_id_fkey FOREIGN KEY (classification_run_id) REFERENCES cell_classification_runs (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_validation_classification_runs ADD CONSTRAINT scientific_validation_classification_runs_session_id_fkey FOREIGN KEY (session_id) REFERENCES scientific_validation_sessions (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_validation_detection_runs ADD CONSTRAINT scientific_validation_detection_runs_detection_run_id_fkey FOREIGN KEY (detection_run_id) REFERENCES cell_detection_runs (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_validation_detection_runs ADD CONSTRAINT scientific_validation_detection_runs_session_id_fkey FOREIGN KEY (session_id) REFERENCES scientific_validation_sessions (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_validation_images ADD CONSTRAINT scientific_validation_images_microscopy_image_id_fkey FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_validation_images ADD CONSTRAINT scientific_validation_images_session_id_fkey FOREIGN KEY (session_id) REFERENCES scientific_validation_sessions (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_archived_by_fkey FOREIGN KEY (archived_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_created_by_fkey FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT fk_smear_summary_classification_lineage FOREIGN KEY (classification_run_id, analysis_run_id, detection_run_id) REFERENCES cell_classification_runs (id, analysis_run_id, detection_run_id) ON DELETE RESTRICT;

ALTER TABLE public.smear_slides ADD CONSTRAINT smear_slides_archived_by_fkey FOREIGN KEY (archived_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.smear_slides ADD CONSTRAINT smear_slides_created_by_fkey FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.smear_slides ADD CONSTRAINT smear_slides_sample_id_fkey FOREIGN KEY (sample_id) REFERENCES blood_samples (id) ON DELETE RESTRICT;

ALTER TABLE public.smear_slides ADD CONSTRAINT smear_slides_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE RESTRICT;

ALTER TABLE public.stage2_model_publication_events ADD CONSTRAINT stage2_model_publication_events_publication_id_fkey FOREIGN KEY (publication_id) REFERENCES stage2_model_publications (id) ON DELETE RESTRICT;

ALTER TABLE public.stage2_model_publications ADD CONSTRAINT fk_stage2_publication_evaluation FOREIGN KEY (evaluation_run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.stage2_model_publications ADD CONSTRAINT fk_stage2_publication_training FOREIGN KEY (training_run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.stage2_model_publications ADD CONSTRAINT fk_stage2_publication_version_artifact FOREIGN KEY (model_version_id, checkpoint_artifact_id) REFERENCES model_versions (id, checkpoint_artifact_id) ON DELETE RESTRICT;

ALTER TABLE public.synthetic_data_runs ADD CONSTRAINT synthetic_data_runs_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE;

ALTER TABLE public.synthetic_data_runs ADD CONSTRAINT synthetic_data_runs_source_dataset_id_fkey FOREIGN KEY (source_dataset_id) REFERENCES datasets (id) ON DELETE SET NULL;

ALTER TABLE public.train_execution_records ADD CONSTRAINT train_execution_records_run_id_fkey FOREIGN KEY (run_id) REFERENCES train_execution_sessions (run_id);

ALTER TABLE public.train_execution_revisions ADD CONSTRAINT train_execution_revisions_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES campaign_attempts (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.train_execution_revisions ADD CONSTRAINT train_execution_revisions_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns (id);

ALTER TABLE public.train_execution_revisions ADD CONSTRAINT train_execution_revisions_campaign_id_revision_id_fkey FOREIGN KEY (campaign_id, revision_id) REFERENCES campaign_technical_revisions (campaign_id, id);

ALTER TABLE public.train_execution_sessions ADD CONSTRAINT train_execution_sessions_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES campaign_attempts (id);

ALTER TABLE public.train_execution_sessions ADD CONSTRAINT train_execution_sessions_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id);

ALTER TABLE public.training_history ADD CONSTRAINT training_history_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE;

ALTER TABLE public.user_roles ADD CONSTRAINT user_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE RESTRICT;

ALTER TABLE public.user_roles ADD CONSTRAINT user_roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE;

ALTER TABLE public.evaluations ADD CONSTRAINT fk_evaluation_e10_record FOREIGN KEY (run_id, event_kind, event_phase, event_key) REFERENCES public.train_execution_records (run_id, kind, phase, record_key) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT fk_metric_evaluation_run FOREIGN KEY (evaluation_id, run_id) REFERENCES public.evaluations (id, run_id) ON DELETE RESTRICT;

ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT ck_v2_binary_counts CHECK (tn >= 0 AND fp >= 0 AND fn >= 0 AND tp >= 0 AND (CAST(tn AS numeric) + fp + fn + tp) > 0);

ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT ck_v2_auc_domain CHECK ((roc_auc_parasitized IS NULL OR (roc_auc_parasitized >= 0 AND roc_auc_parasitized <= 1)) AND (pr_auc_parasitized IS NULL OR (pr_auc_parasitized >= 0 AND pr_auc_parasitized <= 1)));

ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT ck_v2_auc_reason CHECK ((roc_auc_parasitized IS NOT NULL AND pr_auc_parasitized IS NOT NULL AND auc_unavailability_reason IS NULL) OR ((roc_auc_parasitized IS NULL OR pr_auc_parasitized IS NULL) AND auc_unavailability_reason IS NOT NULL AND auc_unavailability_reason IN ('single_class', 'scores_unavailable', 'not_computed')));

ALTER TABLE public.training_history ADD CONSTRAINT ck_v2_epoch CHECK (epoch >= 0);

ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT ck_v2_calibration_val CHECK (calibration_split = 'val' AND default_threshold = 0.5 AND target_recall = 0.98);

ALTER TABLE public.run_metrics ADD CONSTRAINT ck_v2_extension_only CHECK (lower(metric_name) NOT IN ('recall', 'sensitivity', 'specificity', 'precision', 'f1', 'f2', 'balanced_accuracy', 'roc_auc', 'pr_auc', 'tp', 'fp', 'fn', 'tn', 'recall_parasitized', 'sensitivity_parasitized', 'precision_parasitized', 'f1_parasitized', 'f2_parasitized', 'roc_auc_parasitized', 'pr_auc_parasitized'));

ALTER TABLE public.stage2_model_publications ADD CONSTRAINT fk_stage2_publication_model_training FOREIGN KEY (model_version_id, training_run_id) REFERENCES public.model_versions (id, training_run_id) ON DELETE RESTRICT;

ALTER TABLE public.runs ADD CONSTRAINT ck_v2_no_result_json CHECK (NOT parameters ? 'training_results');

ALTER TABLE public.run_configurations ADD CONSTRAINT ck_v2_config_hash CHECK (configuration_hash = encode(digest(canonical_configuration, 'sha256'), 'hex'));

ALTER TABLE public.predictions ADD CONSTRAINT fk_v2_prediction_evaluation_run FOREIGN KEY (evaluation_id, run_id) REFERENCES public.evaluations (id, run_id) ON DELETE RESTRICT;

ALTER TABLE public.predictions ADD CONSTRAINT ck_v2_prediction_sample CHECK (evaluation_id IS NULL OR (run_id IS NOT NULL AND dataset_source_record_id IS NOT NULL AND true_class IS NOT NULL));

ALTER TABLE public.evaluations ADD CONSTRAINT ck_e04_selected_source CHECK (source_kind <> 'e10' OR evaluation_role <> 'calibration_selected' OR (threshold_source = 'validation_calibration' AND calibration_id IS NOT NULL));

ALTER TABLE public.evaluations ADD CONSTRAINT ck_e04_default_source CHECK (source_kind <> 'e10' OR evaluation_role <> 'calibration_default' OR (threshold_source = 'default' AND threshold_used = 0.5 AND calibration_id IS NULL));

ALTER TABLE public.predictions ADD CONSTRAINT v2_predictions_foreign_a402d28a70f6 FOREIGN KEY (evaluation_id) REFERENCES public.evaluations (id) ON DELETE RESTRICT;

ALTER TABLE public.predictions ADD CONSTRAINT v2_predictions_foreign_e8d9af78807c FOREIGN KEY (dataset_source_record_id) REFERENCES public.dataset_source_records (id) ON DELETE RESTRICT;

ALTER TABLE public.predictions ADD CONSTRAINT v2_predictions_check_bcedf284d6cb CHECK (true_class IN (0, 1));

ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT v2_run_threshold_calibration_foreign_014acc59cdbd FOREIGN KEY (default_evaluation_id) REFERENCES public.evaluations (id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT v2_run_threshold_calibration_foreign_0ba3287c0955 FOREIGN KEY (selected_evaluation_id) REFERENCES public.evaluations (id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.runs ADD CONSTRAINT v2_runs_check_275ea92559ec CHECK (peak_cpu_memory_bytes >= 0);

ALTER TABLE public.runs ADD CONSTRAINT v2_runs_check_080968ed1984 CHECK (peak_gpu_memory_bytes >= 0);

ALTER TABLE public.training_history ADD CONSTRAINT v2_training_history_check_51b772d5ee79 CHECK (train_specificity BETWEEN 0 AND 1);

ALTER TABLE public.training_history ADD CONSTRAINT v2_training_history_check_3eea954e3a67 CHECK (val_specificity BETWEEN 0 AND 1);

ALTER TABLE public.training_history ADD CONSTRAINT v2_training_history_check_68190383a722 CHECK (train_f2 BETWEEN 0 AND 1);

ALTER TABLE public.training_history ADD CONSTRAINT v2_training_history_check_03efeda77886 CHECK (val_f2 BETWEEN 0 AND 1);

ALTER TABLE public.training_history ADD CONSTRAINT v2_training_history_check_5cb83011b377 CHECK (train_balanced_accuracy BETWEEN 0 AND 1);

ALTER TABLE public.training_history ADD CONSTRAINT v2_training_history_check_edfadf7cb46b CHECK (val_balanced_accuracy BETWEEN 0 AND 1);

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_foreign_db5338c19de4 FOREIGN KEY (run_id) REFERENCES public.runs (id) ON DELETE RESTRICT;

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_cf7585e198d6 CHECK (architecture IN ('custom_cnn', 'vgg16', 'densenet121'));

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_580e3e6c54f3 CHECK (optimizer IN ('adam', 'adamw', 'sgd', 'adadelta'));

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_ced6e7c6097c CHECK (learning_rate > 0 AND learning_rate < CAST('Infinity' AS float8));

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_ddd84a2faca3 CHECK (fine_tune_learning_rate > 0 AND fine_tune_learning_rate < CAST('Infinity' AS float8));

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_a447b286c925 CHECK (batch_size > 0);

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_b4ca1fd48d76 CHECK (random_seed >= 0);

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_2df57f7a8f77 CHECK (max_epochs > 0);

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_7bcf16f32f16 CHECK (fine_tune_epochs >= 0);

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_998aa974aff8 CHECK (early_stopping_patience >= 0);

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_ab6239fe6a31 CHECK (early_stopping_min_delta >= 0 AND early_stopping_min_delta < CAST('Infinity' AS float8));

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_f121e8cce088 CHECK (early_stopping_mode IN ('min', 'max'));

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_2131e4191e29 CHECK (checkpoint_mode IN ('min', 'max'));

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_eee102ab78dd CHECK (dropout >= 0 AND dropout < 1);

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_ea943e1f4322 CHECK (l2 >= 0 AND l2 < 1);

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_46e293269ce9 CHECK (input_height >= 32);

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_f91cdd45746e CHECK (input_width = input_height);

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_25a4140a88de CHECK (input_channels = 3);

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_4face7ed3946 CHECK (weights IN ('none', 'imagenet'));

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_80bf078e8ac1 CHECK (fine_tune_layers >= 0);

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_278a5e3294ac CHECK (default_threshold = 0.5);

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_d6094850fee4 CHECK (clinical_target_recall = 0.98);

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_3321a4aaab96 CHECK (configuration_hash ~ '^[0-9a-f]{64}$');

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_3f8c4617855a CHECK (jsonb_typeof(optimizer_extensions) = 'object');

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_f31c0727c3ef CHECK (jsonb_typeof(extension_configuration) = 'object');

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_eb0d0af834a3 CHECK (jsonb_typeof(provenance_snapshot) = 'object');

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_63e4a55e1de0 CHECK ((architecture = 'vgg16' AND normalization = 'vgg16_imagenet' AND internal_preprocessing IS NULL) OR (architecture = 'custom_cnn' AND normalization = 'rescale_0_1' AND internal_preprocessing IS NULL) OR (architecture = 'densenet121' AND normalization = 'rescale_0_1' AND internal_preprocessing = 'densenet_imagenet_channel_mean_std'));

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_foreign_db5338c19de4 FOREIGN KEY (run_id) REFERENCES public.runs (id) ON DELETE RESTRICT;

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_foreign_4e6a43d876af FOREIGN KEY (training_run_id) REFERENCES public.runs (id) ON DELETE RESTRICT;

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_foreign_6aec504c7a2f FOREIGN KEY (checkpoint_artifact_id) REFERENCES public.artifacts (id) ON DELETE RESTRICT;

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_foreign_14b20ff24e12 FOREIGN KEY (dataset_version_id) REFERENCES public.dataset_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_c2a936c0d6c6 CHECK (split IN ('train', 'val', 'test', 'external'));

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_6d2ae4a2559c CHECK (evaluation_role IN ('training_validation_final', 'development', 'final_test', 'calibration_default', 'calibration_selected', 'external_complementary'));

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_114e1e7e39d4 CHECK (purpose IN ('development', 'final', 'complementary'));

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_b5ea10e3edba CHECK (subject_kind IN ('single', 'ensemble'));

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_0652739ad678 CHECK (protocol_hash ~ '^[0-9a-f]{64}$');

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_c13afae612b2 CHECK (population_hash ~ '^[0-9a-f]{64}$');

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_b93d47c84570 CHECK (input_contract_hash ~ '^[0-9a-f]{64}$');

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_f337b5a1c02f CHECK (comparison_contract_hash ~ '^[0-9a-f]{64}$');

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_00fb2e80d9b2 CHECK (jsonb_typeof(protocol_snapshot) = 'object');

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_f1db93b69ab7 CHECK (source_kind IN ('e10', 'assessment', 'legacy', 'external_record'));

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_foreign_c764adede219 FOREIGN KEY (source_assessment_attempt_id) REFERENCES public.assessment_attempts (id) ON DELETE RESTRICT;

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_05b75a389d97 CHECK (threshold_used >= 0 AND threshold_used <= 1);

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_f4818b1a9fd3 CHECK (threshold_source IN ('default', 'validation_calibration', 'protocol_numeric'));

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_foreign_0baa7d166e2f FOREIGN KEY (calibration_id) REFERENCES public.run_threshold_calibration (run_threshold_calibration_id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_4cbf36ebbe5e CHECK (metric_definition = 'binary_nullable_v2');

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_foreign_6cfcdf2998f5 FOREIGN KEY (model_version_id, training_run_id) REFERENCES public.model_versions (id, training_run_id) ON DELETE RESTRICT;

ALTER TABLE public.evaluations ADD CONSTRAINT ck_v2_evaluation_scope CHECK ((split = 'test' AND purpose = 'final' AND evaluation_role = 'final_test') OR (split IN ('train', 'val') AND purpose = 'development' AND evaluation_role IN ('training_validation_final', 'development', 'calibration_default', 'calibration_selected')) OR (split = 'external' AND purpose = 'complementary' AND evaluation_role = 'external_complementary'));

ALTER TABLE public.evaluations ADD CONSTRAINT fk_v2_evaluation_dataset_origin FOREIGN KEY (dataset_version_id, dataset_origin_id, dataset_origin_role) REFERENCES public.dataset_version_sources (dataset_version_id, dataset_id, role) ON DELETE RESTRICT;

ALTER TABLE public.evaluations ADD CONSTRAINT ck_v2_external_provenance CHECK (split <> 'external' OR (dataset_origin_id IS NOT NULL AND dataset_origin_role IS NOT NULL AND population_manifest_uri IS NOT NULL AND length(btrim(population_manifest_uri)) > 0 AND population_manifest_sha256 IS NOT NULL AND population_manifest_sha256 ~ '^[0-9a-f]{64}$' AND dataset_provenance_uri IS NOT NULL AND length(btrim(dataset_provenance_uri)) > 0 AND dataset_provenance_sha256 IS NOT NULL AND dataset_provenance_sha256 ~ '^[0-9a-f]{64}$' AND source_kind IN ('legacy', 'external_record') AND length(btrim(source_record_key)) > 0 AND length(btrim(source_record_phase)) > 0));

ALTER TABLE public.evaluations ADD CONSTRAINT ck_v2_external_source CHECK (source_kind <> 'external_record' OR split = 'external');

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_a359e10954fc CHECK (evaluation_role NOT IN ('training_validation_final', 'calibration_default', 'calibration_selected') OR split = 'val');

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_d2a4e9ce706e CHECK ((threshold_source = 'default' AND threshold_used = 0.5 AND calibration_id IS NULL) OR (threshold_source = 'validation_calibration' AND calibration_id IS NOT NULL) OR (threshold_source = 'protocol_numeric' AND calibration_id IS NULL));

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_88394215eb49 CHECK ((source_kind = 'e10' AND source_event_id IS NOT NULL AND source_assessment_attempt_id IS NULL) OR (source_kind = 'assessment' AND source_event_id IS NULL AND source_assessment_attempt_id IS NOT NULL) OR (source_kind IN ('legacy', 'external_record') AND source_event_id IS NULL AND source_assessment_attempt_id IS NULL));

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_3df12c5495af CHECK (subject_kind = 'ensemble' OR checkpoint_artifact_id IS NOT NULL);

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_58c667b93f11 CHECK (split <> 'test' OR source_kind = 'assessment');

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_28938a6edbaa CHECK (source_kind <> 'e10' OR evaluation_role IN ('training_validation_final', 'calibration_default', 'calibration_selected'));

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_08204f883325 CHECK (evaluation_role <> 'training_validation_final' OR run_id = training_run_id);

ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_3b1acb9be108 CHECK ((source_kind = 'e10' AND event_kind = 'e10_event' AND event_phase = 'run_event_v1' AND event_key = CAST(source_event_id AS text) AND event_kind IS NOT NULL AND event_phase IS NOT NULL AND event_key IS NOT NULL) OR (source_kind <> 'e10' AND event_kind IS NULL AND event_phase IS NULL AND event_key IS NULL));

ALTER TABLE public.evaluation_ensemble_members ADD CONSTRAINT v2_evaluation_ensemble_members_foreign_a402d28a70f6 FOREIGN KEY (evaluation_id) REFERENCES public.evaluations (id) ON DELETE RESTRICT;

ALTER TABLE public.evaluation_ensemble_members ADD CONSTRAINT v2_evaluation_ensemble_members_check_967aa2df2b88 CHECK (ordinal >= 0);

ALTER TABLE public.evaluation_ensemble_members ADD CONSTRAINT v2_evaluation_ensemble_members_foreign_b946b2b207f3 FOREIGN KEY (model_version_id) REFERENCES public.model_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.evaluation_ensemble_members ADD CONSTRAINT v2_evaluation_ensemble_members_foreign_6aec504c7a2f FOREIGN KEY (checkpoint_artifact_id) REFERENCES public.artifacts (id) ON DELETE RESTRICT;

ALTER TABLE public.evaluation_ensemble_members ADD CONSTRAINT v2_evaluation_ensemble_members_check_32cd0f122db1 CHECK (weight > 0 AND weight < CAST('Infinity' AS numeric));

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_9851edbb8079 FOREIGN KEY (ml_explanation_id) REFERENCES public.explainability_results (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_3fe88bd35854 FOREIGN KEY (cell_explanation_id) REFERENCES public.cell_explanations (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_4b04405ab069 FOREIGN KEY (prediction_id) REFERENCES public.predictions (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_029e07f1d6db FOREIGN KEY (cell_prediction_id) REFERENCES public.cell_predictions (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_a402d28a70f6 FOREIGN KEY (evaluation_id) REFERENCES public.evaluations (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_e8d9af78807c FOREIGN KEY (dataset_source_record_id) REFERENCES public.dataset_source_records (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_a1c9b824423e FOREIGN KEY (input_artifact_id) REFERENCES public.artifacts (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_ad1ea3f78d92 FOREIGN KEY (microscopy_image_id) REFERENCES public.microscopy_images (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_db5338c19de4 FOREIGN KEY (run_id) REFERENCES public.runs (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_b946b2b207f3 FOREIGN KEY (model_version_id) REFERENCES public.model_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_6aec504c7a2f FOREIGN KEY (checkpoint_artifact_id) REFERENCES public.artifacts (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_5e31bead5512 CHECK (method IN ('gradcam', 'shap', 'lime'));

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_94a05a1bd653 CHECK (jsonb_typeof(method_configuration) = 'object');

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_3321a4aaab96 CHECK (configuration_hash ~ '^[0-9a-f]{64}$');

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_71beacad95d0 CHECK (jsonb_typeof(input_contract) = 'object');

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_b93d47c84570 CHECK (input_contract_hash ~ '^[0-9a-f]{64}$');

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_93787689f516 CHECK (input_sha256 ~ '^[0-9a-f]{64}$');

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_6bf21e8ba9a2 CHECK (checkpoint_sha256 ~ '^[0-9a-f]{64}$');

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_185d894424d0 CHECK (target_class IN (0, 1));

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_26e9e3a0278b CHECK (explained_output IN ('probability_parasitized', 'probability_uninfected', 'raw_output'));

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_5027e188ea2a CHECK (processing_stage IN ('model_input', 'cell_crop', 'evaluation_sample'));

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_3e7a5ed7ffee CHECK (background_manifest_sha256 ~ '^[0-9a-f]{64}$');

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_9d77320c4af9 CHECK (jsonb_typeof(environment_snapshot) = 'object');

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_52bd313b1c15 FOREIGN KEY (assessment_attempt_id, assessment_sample_id) REFERENCES public.assessment_results (attempt_id, sample_id) MATCH FULL ON DELETE RESTRICT;

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_0b0c8b6b4dc8 CHECK (num_nonnulls(ml_explanation_id, cell_explanation_id, assessment_attempt_id) = 1);

ALTER TABLE public.xai_evidence ADD CONSTRAINT ck_xai_input_origin CHECK (num_nonnulls(dataset_source_record_id, microscopy_image_id, input_artifact_id) = 1);

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_bfbb62e97a91 CHECK (num_nonnulls(prediction_id, cell_prediction_id) <= 1);

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_f1eec802dae7 CHECK ((method = 'shap' AND background_manifest_uri IS NOT NULL AND background_manifest_sha256 IS NOT NULL) OR method <> 'shap');

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_foreign_4b080b42e888 FOREIGN KEY (evidence_id) REFERENCES public.xai_evidence (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_foreign_e3d2eb574718 FOREIGN KEY (artifact_id) REFERENCES public.artifacts (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_foreign_f9c5548be835 FOREIGN KEY (assessment_artifact_id) REFERENCES public.assessment_artifacts (artifact_id) ON DELETE RESTRICT;

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_70ab6797c0c6 CHECK (num_nonnulls(artifact_id, assessment_artifact_id) <= 1);

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_eb359eee6311 CHECK (role IN ('raw_attribution', 'spatial_map', 'segments', 'segment_weights', 'overlay', 'render', 'background_manifest', 'input_manifest'));

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_967aa2df2b88 CHECK (ordinal >= 0);

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_20426a1e7fe3 CHECK (sha256 ~ '^[0-9a-f]{64}$');

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_a81626200b02 CHECK (byte_size >= 0);

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_4b7ae3b26ca5 CHECK (availability IN ('available', 'missing', 'quarantined', 'archived'));

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_a68006e838dc CHECK (tensor_shape IS NULL OR (cardinality(tensor_shape) > 0 AND 0 < ALL(tensor_shape)));

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT v2_xai_quantitative_evaluations_foreign_4b080b42e888 FOREIGN KEY (evidence_id) REFERENCES public.xai_evidence (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT v2_xai_quantitative_evaluations_foreign_851f5820eb59 FOREIGN KEY (comparison_evidence_id) REFERENCES public.xai_evidence (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT v2_xai_quantitative_evaluations_check_91eb3dc34528 CHECK (family IN ('stability', 'faithfulness', 'localization', 'concordance'));

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT v2_xai_quantitative_evaluations_check_0652739ad678 CHECK (protocol_hash ~ '^[0-9a-f]{64}$');

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT v2_xai_quantitative_evaluations_check_00fb2e80d9b2 CHECK (jsonb_typeof(protocol_snapshot) = 'object');

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT v2_xai_quantitative_evaluations_check_bcd82843d42a CHECK (sample_count > 0);

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT v2_xai_quantitative_evaluations_check_887951a61b99 CHECK (value > CAST('-Infinity' AS float8) AND value < CAST('Infinity' AS float8));

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT v2_xai_quantitative_evaluations_foreign_159f07174869 FOREIGN KEY (reference_annotation_id) REFERENCES public.scientific_validation_annotations (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT v2_xai_quantitative_evaluations_check_ffe78f63e439 CHECK (reference_manifest_sha256 ~ '^[0-9a-f]{64}$');

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT v2_xai_quantitative_evaluations_check_599c4acec50d CHECK (details_sha256 ~ '^[0-9a-f]{64}$');

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT v2_xai_quantitative_evaluations_check_4778c641fdd8 CHECK ((value IS NULL) = (null_reason IS NOT NULL));

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT v2_xai_quantitative_evaluations_check_21cdf11ae847 CHECK (comparison_evidence_id IS NULL OR comparison_evidence_id <> evidence_id);

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT v2_xai_quantitative_evaluations_check_655d0810bc12 CHECK (family <> 'concordance' OR comparison_evidence_id IS NOT NULL);

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT v2_xai_quantitative_evaluations_check_4d27ef172e06 CHECK (family <> 'localization' OR (reference_annotation_id IS NOT NULL AND reference_annotation_version IS NOT NULL AND reference_manifest_sha256 IS NOT NULL AND reference_manifest_uri IS NOT NULL));

ALTER TABLE public.xai_interpretations ADD CONSTRAINT v2_xai_interpretations_foreign_4b080b42e888 FOREIGN KEY (evidence_id) REFERENCES public.xai_evidence (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_interpretations ADD CONSTRAINT v2_xai_interpretations_foreign_6b09f9926d4f FOREIGN KEY (author_user_id) REFERENCES public.users (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_interpretations ADD CONSTRAINT v2_xai_interpretations_check_c7c3afcde9f7 CHECK (length(pg_catalog.btrim(interpretation)) > 0);

ALTER TABLE public.xai_interpretations ADD CONSTRAINT v2_xai_interpretations_foreign_af451d74af77 FOREIGN KEY (supersedes_id) REFERENCES public.xai_interpretations (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_specialist_reviews ADD CONSTRAINT v2_xai_specialist_reviews_foreign_4735bf604cb2 FOREIGN KEY (interpretation_id) REFERENCES public.xai_interpretations (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_specialist_reviews ADD CONSTRAINT v2_xai_specialist_reviews_foreign_7ca01df9e490 FOREIGN KEY (reviewer_user_id) REFERENCES public.users (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_specialist_reviews ADD CONSTRAINT v2_xai_specialist_reviews_check_920877b7b5d1 CHECK (decision IN ('supported', 'unsupported', 'inconclusive'));

ALTER TABLE public.xai_specialist_reviews ADD CONSTRAINT v2_xai_specialist_reviews_check_d8ae577b1870 CHECK (length(pg_catalog.btrim(rationale)) > 0);

ALTER TABLE public.xai_specialist_reviews ADD CONSTRAINT v2_xai_specialist_reviews_check_07baf4b694f5 CHECK (jsonb_typeof(competence_snapshot) = 'object');

