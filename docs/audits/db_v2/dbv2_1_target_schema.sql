-- DBV2.1 STRUCTURAL SPECIFICATION
-- DESIGN ARTIFACT ONLY
-- DO NOT EXECUTE
-- NOT AN ALEMBIC MIGRATION
-- PostgreSQL 17.9 target; standalone definitions; no historical imports.
-- Pending GATE DBV2.1. Roles/ACL and Alembic-owned ledger specified in documentation.
-- 01_prerequisites
SET LOCAL search_path = public, pg_catalog;

SET LOCAL check_function_bodies = true;

CREATE EXTENSION pgcrypto WITH SCHEMA public;

REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- 02_generated_functions
CREATE OR REPLACE FUNCTION public.assessment_canonical(v jsonb)
 RETURNS text
 LANGUAGE plpgsql
 IMMUTABLE STRICT
 SET search_path TO 'public', 'pg_catalog'
AS $function$
DECLARE result text;
BEGIN
 CASE jsonb_typeof(v)
 WHEN 'object' THEN
   SELECT '{'||coalesce(string_agg(to_jsonb(key)::text||':'||assessment_canonical(value),',' ORDER BY key COLLATE "C"),'')||'}' INTO result FROM jsonb_each(v);
 WHEN 'array' THEN
   SELECT '['||coalesce(string_agg(assessment_canonical(value),',' ORDER BY ord),'')||']' INTO result FROM jsonb_array_elements(v) WITH ORDINALITY a(value,ord);
 WHEN 'number' THEN result=trim_scale((v::text)::numeric)::text;
 ELSE result=v::text;
 END CASE;
 RETURN result;
END $function$;

CREATE OR REPLACE FUNCTION public.assessment_structural_hash(v jsonb)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE STRICT
 SET search_path TO 'public', 'pg_catalog'
AS $function$
 SELECT encode(sha256(convert_to(assessment_canonical(v),'UTF8')),'hex')
$function$;

-- 03_tables
CREATE TABLE public.artifacts (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, run_id uuid, artifact_type text NOT NULL, name text, path text NOT NULL, mime_type text, file_size_bytes bigint, checksum text, created_at timestamp with time zone DEFAULT now(), metadata jsonb DEFAULT CAST('{}' AS jsonb), artifact_uri text, artifact_status text DEFAULT CAST('available' AS text) NOT NULL, archived_at timestamp with time zone);

CREATE TABLE public.assessment_artifacts (attempt_id uuid NOT NULL, artifact_id uuid NOT NULL, sample_id uuid NOT NULL, role text NOT NULL, payload jsonb NOT NULL);

CREATE TABLE public.assessment_attempts (id uuid NOT NULL, identity_id uuid NOT NULL, owner uuid NOT NULL, host text NOT NULL, pid integer NOT NULL, ordinal integer NOT NULL, state text DEFAULT CAST('active' AS text) NOT NULL, artifact_root text NOT NULL, cause text, verification jsonb, started_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL, finished_at timestamp with time zone);

CREATE TABLE public.assessment_campaign_consumers (campaign_id uuid NOT NULL, member_id uuid NOT NULL, identity_id uuid NOT NULL);

CREATE TABLE public.assessment_final_locks (id uuid NOT NULL, identity_hash text NOT NULL, evidence jsonb NOT NULL, created_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL);

CREATE TABLE public.assessment_identities (id uuid NOT NULL, identity_hash text NOT NULL, training_run_id uuid NOT NULL, kind text NOT NULL, identity jsonb NOT NULL, canonical_identity text NOT NULL, structural_hash text GENERATED ALWAYS AS (assessment_structural_hash(identity)) STORED, created_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL);

CREATE TABLE public.assessment_results (attempt_id uuid NOT NULL, sample_id uuid NOT NULL, payload jsonb NOT NULL);

CREATE TABLE public.audit_events (id uuid NOT NULL, event_type text NOT NULL, action text NOT NULL, actor_user_id uuid, actor_username_snapshot text, resource_type text NOT NULL, resource_id text, request_method text NOT NULL, request_path text NOT NULL, correlation_id text NOT NULL, before_state jsonb, after_state jsonb, metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, success boolean NOT NULL, error_code text, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.blood_samples (id uuid NOT NULL, case_id uuid NOT NULL, sample_code varchar(120) NOT NULL, specimen_type varchar(80) DEFAULT CAST('peripheral_blood' AS varchar) NOT NULL, collection_method varchar(120), anticoagulant varchar(120), collected_at timestamp with time zone, received_at timestamp with time zone, status varchar(20) DEFAULT CAST('registered' AS varchar) NOT NULL, notes text, metadata_json jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL, updated_at timestamp with time zone DEFAULT now() NOT NULL, created_by uuid NOT NULL, updated_by uuid, archived_at timestamp with time zone, archived_by uuid, source_system varchar(120), external_sample_id varchar(240), sample_identity_origin varchar(40) DEFAULT CAST('generated_by_capstone' AS varchar) NOT NULL, source_group_key varchar(240), ingestion_status varchar(20), expected_image_count integer);

CREATE TABLE public.campaign_attempts (id uuid NOT NULL, member_id uuid NOT NULL, ordinal integer NOT NULL, state text NOT NULL, training_run_id uuid, cause text, started_at timestamp with time zone DEFAULT now() NOT NULL, finished_at timestamp with time zone);

CREATE TABLE public.campaign_configurations (campaign_id uuid NOT NULL, configuration_hash text NOT NULL, configuration jsonb NOT NULL, canonical_configuration text NOT NULL, requests jsonb NOT NULL);

CREATE TABLE public.campaign_controlled_requests (id uuid NOT NULL, campaign_id uuid NOT NULL, member_id uuid NOT NULL, revision_id uuid NOT NULL, previous_attempt_id uuid NOT NULL, attempt_id uuid NOT NULL, run_id uuid NOT NULL, reason text NOT NULL, created_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL);

CREATE TABLE public.campaign_execution_events (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, campaign_id uuid NOT NULL, code text NOT NULL, created_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL);

CREATE TABLE public.campaign_members (id uuid NOT NULL, campaign_id uuid NOT NULL, configuration_hash text NOT NULL, seed integer NOT NULL, position integer NOT NULL, exclusion_reason text, state text DEFAULT CAST('pending' AS text) NOT NULL, accepted_attempt_id uuid);

CREATE TABLE public.campaign_technical_revisions (id uuid NOT NULL, campaign_id uuid NOT NULL, payload jsonb NOT NULL, canonical_payload text NOT NULL, payload_hash text NOT NULL, created_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL);

CREATE TABLE public.cell_classification_events (id uuid NOT NULL, classification_run_id uuid NOT NULL, cell_detection_id uuid, cell_prediction_id uuid, event_type varchar(120) NOT NULL, status varchar(40) NOT NULL, message_code varchar(80), message text, progress_current integer, progress_total integer, metadata_json jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.cell_classification_inputs (id uuid NOT NULL, classification_run_id uuid NOT NULL, detection_run_id uuid NOT NULL, cell_detection_id uuid NOT NULL, microscopy_image_id uuid NOT NULL, crop_id uuid, input_order integer NOT NULL, image_sequence_number integer NOT NULL, cell_index integer NOT NULL, cell_code varchar(40) NOT NULL, detector_key varchar(80) NOT NULL, detector_version varchar(40) NOT NULL, detector_algorithm_version varchar(80) NOT NULL, crop_sha256 char(64), crop_width_px integer, crop_height_px integer, detection_review_status_at_creation varchar(30), eligible boolean NOT NULL, exclusion_reason varchar(120), created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.cell_classification_reviews (id uuid NOT NULL, cell_prediction_id uuid NOT NULL, decision varchar(30) NOT NULL, reviewed_label varchar(20), comment text, actor_user_id uuid NOT NULL, created_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL);

CREATE TABLE public.cell_classification_runs (id uuid NOT NULL, analysis_run_id uuid NOT NULL, detection_run_id uuid NOT NULL, classification_run_code varchar(20) NOT NULL, production_model_id uuid NOT NULL, stage2_publication_id uuid NOT NULL, model_registry_id uuid NOT NULL, model_name varchar(160) NOT NULL, model_version varchar(120), model_snapshot jsonb NOT NULL, input_manifest_sha256 char(64) NOT NULL, status varchar(30) NOT NULL, input_count integer NOT NULL, eligible_count integer NOT NULL, excluded_count integer NOT NULL, processed_count integer DEFAULT 0 NOT NULL, parasitized_count integer DEFAULT 0 NOT NULL, uninfected_count integer DEFAULT 0 NOT NULL, near_threshold_count integer DEFAULT 0 NOT NULL, failed_count integer DEFAULT 0 NOT NULL, requested_by uuid NOT NULL, retry_of_run_id uuid, started_at timestamp with time zone, completed_at timestamp with time zone, failed_at timestamp with time zone, error_code varchar(80), error_message text, created_at timestamp with time zone DEFAULT now() NOT NULL, updated_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.cell_crops (id uuid NOT NULL, cell_detection_id uuid NOT NULL, relative_storage_key text NOT NULL, sha256 char(64) NOT NULL, file_size_bytes bigint NOT NULL, width_px integer NOT NULL, height_px integer NOT NULL, format varchar(20) NOT NULL, padding_px integer NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.cell_detection_events (id uuid NOT NULL, detection_run_id uuid NOT NULL, microscopy_image_id uuid, event_type varchar(100) NOT NULL, stage varchar(50) NOT NULL, status varchar(30) NOT NULL, message_code varchar(80), message text, progress_current integer, progress_total integer, metadata_json jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.cell_detection_runs (id uuid NOT NULL, analysis_run_id uuid NOT NULL, detection_run_code varchar(20) NOT NULL, detector_key varchar(80) NOT NULL, detector_version varchar(40) NOT NULL, algorithm_version varchar(80) NOT NULL, profile_snapshot jsonb NOT NULL, input_manifest_sha256 char(64) NOT NULL, status varchar(30) NOT NULL, image_count integer NOT NULL, processed_image_count integer DEFAULT 0 NOT NULL, component_count integer DEFAULT 0 NOT NULL, detection_count integer DEFAULT 0 NOT NULL, crop_count integer DEFAULT 0 NOT NULL, warning_count integer DEFAULT 0 NOT NULL, requested_by uuid NOT NULL, started_at timestamp with time zone, completed_at timestamp with time zone, failed_at timestamp with time zone, error_code varchar(80), error_message text, created_at timestamp with time zone DEFAULT now() NOT NULL, updated_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.cell_detections (id uuid NOT NULL, detection_run_id uuid NOT NULL, analysis_run_id uuid NOT NULL, connected_component_id uuid NOT NULL, analysis_run_image_id uuid NOT NULL, microscopy_image_id uuid NOT NULL, cell_index integer NOT NULL, cell_code varchar(40) NOT NULL, bbox_x integer NOT NULL, bbox_y integer NOT NULL, bbox_width integer NOT NULL, bbox_height integer NOT NULL, coordinate_space varchar(40) NOT NULL, detector_score double precision, automated_status varchar(30) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.cell_explanations (id uuid NOT NULL, cell_prediction_id uuid NOT NULL, method varchar(40) NOT NULL, method_version varchar(80) NOT NULL, status varchar(30) NOT NULL, last_conv_layer varchar(255), parameters_json jsonb NOT NULL, heatmap_storage_key text, heatmap_sha256 char(64), heatmap_file_size_bytes bigint, overlay_storage_key text, overlay_sha256 char(64), overlay_file_size_bytes bigint, width_px integer, height_px integer, started_at timestamp with time zone, completed_at timestamp with time zone, error_code varchar(80), error_message text, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.cell_predictions (id uuid NOT NULL, classification_run_id uuid NOT NULL, classification_input_id uuid NOT NULL, cell_detection_id uuid NOT NULL, crop_id uuid NOT NULL, prediction_status varchar(20) NOT NULL, raw_output jsonb NOT NULL, probability_parasitized double precision, probability_uninfected double precision, predicted_label varchar(20), predicted_class_index smallint, positive_label varchar(20) NOT NULL, positive_class_index smallint NOT NULL, threshold_used double precision NOT NULL, threshold_source varchar(120) NOT NULL, decision_margin double precision, near_threshold boolean DEFAULT FALSE NOT NULL, preprocessing_snapshot jsonb NOT NULL, inference_duration_ms double precision, error_code varchar(80), error_message text, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.clinical_identities (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, dataset_id uuid NOT NULL, identity_type text NOT NULL, source_identifier text NOT NULL, status text NOT NULL, metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL, updated_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.dataset_materialization_activations (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, dataset_version_id uuid NOT NULL, materialization_id uuid NOT NULL, dataset_family text NOT NULL, activated_at timestamp with time zone DEFAULT now() NOT NULL, deactivated_at timestamp with time zone, metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL);

CREATE TABLE public.dataset_materializations (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, dataset_version_id uuid NOT NULL, attempt_number integer NOT NULL, status text DEFAULT CAST('NOT_MATERIALIZED' AS text) NOT NULL, reconciliation_status text DEFAULT CAST('PENDING' AS text) NOT NULL, relative_root text NOT NULL, record_count bigint DEFAULT 0 NOT NULL, manifest_metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, started_at timestamp with time zone, completed_at timestamp with time zone, failure_reason text, metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.dataset_source_records (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, dataset_id uuid NOT NULL, clinical_identity_id uuid, source_record_key text NOT NULL, tfds_index bigint, source_filename text, class_index integer NOT NULL, class_name text NOT NULL, original_label integer, project_label integer, relative_source_key text, source_file_sha256 text, decoded_pixel_sha256 text, image_width integer, image_height integer, file_size_bytes bigint, identity_status text NOT NULL, metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL, updated_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.dataset_split_assignments (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, dataset_version_id uuid NOT NULL, source_record_id uuid NOT NULL, clinical_identity_id uuid NOT NULL, split_name text NOT NULL, class_index integer NOT NULL, class_name text NOT NULL, metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.dataset_split_images (image_id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, dataset_id uuid, dataset_name text NOT NULL, dataset_source text NOT NULL, dataset_dir text NOT NULL, split_name text NOT NULL, class_index integer NOT NULL, class_name text NOT NULL, relative_path text NOT NULL, absolute_path text, filename text NOT NULL, original_tfds_label integer, project_label integer NOT NULL, label_mapping_version text NOT NULL, image_width integer, image_height integer, file_size_bytes bigint, checksum_sha256 text, created_at timestamp with time zone DEFAULT now() NOT NULL, updated_at timestamp with time zone DEFAULT now() NOT NULL, metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, dataset_version_id uuid, dataset_materialization_id uuid);

CREATE TABLE public.dataset_split_statistics (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, dataset_version_id uuid NOT NULL, scope text NOT NULL, metric_name text NOT NULL, numeric_value numeric, text_value text, details_json jsonb, computed_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.dataset_split_validation_checks (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, dataset_version_id uuid NOT NULL, check_name text NOT NULL, status text NOT NULL, observed_value text, expected_value text, details_json jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, blocking_for_validation boolean DEFAULT FALSE NOT NULL, blocking_for_freeze boolean DEFAULT FALSE NOT NULL, executed_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.dataset_splits (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, dataset_id uuid, split_name text NOT NULL, num_samples integer, class_distribution jsonb DEFAULT CAST('{}' AS jsonb), split_strategy text, random_seed integer, created_at timestamp with time zone DEFAULT now(), metadata jsonb DEFAULT CAST('{}' AS jsonb));

CREATE TABLE public.dataset_version_sources (dataset_version_id uuid NOT NULL, dataset_id uuid NOT NULL, role text NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.dataset_versions (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, name text NOT NULL, semantic_version text NOT NULL, status text DEFAULT CAST('DRAFT' AS text) NOT NULL, grouping_strategy text NOT NULL, grouping_field text NOT NULL, stratification_strategy text NOT NULL, split_algorithm text NOT NULL, split_algorithm_version text NOT NULL, random_seed integer NOT NULL, target_train_ratio numeric(8, 7) NOT NULL, target_val_ratio numeric(8, 7) NOT NULL, target_test_ratio numeric(8, 7) NOT NULL, positive_class text NOT NULL, class_mapping jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, source_record_count bigint DEFAULT 0 NOT NULL, methodology_json jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL, generated_at timestamp with time zone, validated_at timestamp with time zone, frozen_at timestamp with time zone, archived_at timestamp with time zone);

CREATE TABLE public.datasets (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, name text NOT NULL, source text, version text, description text, total_images integer, num_classes integer, class_names text[], class_distribution jsonb DEFAULT CAST('{}' AS jsonb), license text, url text, local_path text, checksum text, created_at timestamp with time zone DEFAULT now(), metadata jsonb DEFAULT CAST('{}' AS jsonb), provider text, source_type text, source_reference text, source_version text);

CREATE TABLE public.deployed_model_versions (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, model_version_id uuid NOT NULL, checkpoint_artifact_id uuid NOT NULL, threshold_calibration_id uuid, deployment_name text NOT NULL, environment text NOT NULL, alias text NOT NULL, artifact_sha256 text NOT NULL, artifact_size_bytes bigint, threshold_value numeric NOT NULL, threshold_profile_snapshot jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, preprocessing_profile_snapshot jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, image_quality_policy_snapshot jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, label_mapping_snapshot jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, positive_label text DEFAULT CAST('parasitized' AS text) NOT NULL, score_name text DEFAULT CAST('probability_parasitized' AS text) NOT NULL, status text DEFAULT CAST('pending' AS text) NOT NULL, supersedes_deployment_id uuid, rollback_of_deployment_id uuid, deployed_at timestamp with time zone, retired_at timestamp with time zone, deployed_by text, retired_by text, deployment_reason text, retirement_reason text, created_at timestamp with time zone DEFAULT now() NOT NULL, metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL);

CREATE TABLE public.environment_packages (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, run_id uuid, package_name text NOT NULL, package_version text, created_at timestamp with time zone DEFAULT now());

CREATE TABLE public.errors (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, run_id uuid, error_type text, error_message text, stack_trace text, script_name text, created_at timestamp with time zone DEFAULT now(), metadata jsonb DEFAULT CAST('{}' AS jsonb));

CREATE TABLE public.evaluation_ensemble_members (evaluation_id uuid NOT NULL, ordinal integer NOT NULL, model_version_id uuid NOT NULL, checkpoint_artifact_id uuid NOT NULL, weight numeric NOT NULL);

CREATE TABLE public.evaluations (id uuid DEFAULT gen_random_uuid(), run_id uuid NOT NULL, training_run_id uuid NOT NULL, model_version_id uuid, checkpoint_artifact_id uuid, dataset_version_id uuid NOT NULL, split text NOT NULL, evaluation_role text NOT NULL, purpose text NOT NULL, dataset_origin_id uuid, dataset_origin_role text, population_manifest_uri text, population_manifest_sha256 text, dataset_provenance_uri text, dataset_provenance_sha256 text, subject_kind text NOT NULL, protocol_version text NOT NULL, protocol_hash text NOT NULL, population_hash text NOT NULL, input_contract_hash text NOT NULL, comparison_contract_hash text NOT NULL, protocol_snapshot jsonb NOT NULL, source_kind text NOT NULL, source_record_key text NOT NULL, source_record_phase text NOT NULL, source_event_id uuid, event_kind text, event_phase text, event_key text, source_assessment_attempt_id uuid, threshold_used numeric NOT NULL, threshold_source text NOT NULL, calibration_id uuid, metric_definition text NOT NULL DEFAULT 'binary_nullable_v2', created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE public.execution_logs (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, run_id uuid, log_level text, message text, source text, created_at timestamp with time zone DEFAULT now(), metadata jsonb DEFAULT CAST('{}' AS jsonb));

CREATE TABLE public.experiment_execution_events (id bigint GENERATED ALWAYS AS IDENTITY NOT NULL, owner uuid NOT NULL, event text NOT NULL, payload jsonb NOT NULL, created_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL);

CREATE TABLE public.experiment_execution_gate (singleton boolean DEFAULT TRUE NOT NULL, owner uuid, db_pid integer, process_evidence jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, blocked_reason text, updated_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL);

CREATE TABLE public.experimental_campaigns (id uuid NOT NULL, experiment_id uuid, name text NOT NULL, purpose text NOT NULL, state text DEFAULT CAST('draft' AS text) NOT NULL, dataset_version_id uuid NOT NULL, dataset_snapshot jsonb NOT NULL, dataset_evidence_id uuid NOT NULL, requested jsonb NOT NULL, protocol jsonb NOT NULL, environment jsonb NOT NULL, registry_snapshot jsonb, contract jsonb, canonical_contract text, contract_hash text, expected_count integer DEFAULT 0 NOT NULL, actor text NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL, updated_at timestamp with time zone DEFAULT now() NOT NULL, frozen_at timestamp with time zone);

CREATE TABLE public.experiments (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, name text NOT NULL, description text, project_name text, created_at timestamp with time zone DEFAULT now(), updated_at timestamp with time zone DEFAULT now(), metadata jsonb DEFAULT CAST('{}' AS jsonb));

CREATE TABLE public.explainability_results (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, run_id uuid, prediction_id uuid, method text NOT NULL, image_path text, output_path text, true_label text, predicted_label text, score numeric, case_type text, last_conv_layer text, explanation_parameters jsonb DEFAULT CAST('{}' AS jsonb), success boolean DEFAULT TRUE, error_message text, created_at timestamp with time zone DEFAULT now(), metadata jsonb DEFAULT CAST('{}' AS jsonb));

CREATE TABLE public.identity_evidence (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, source_record_id uuid NOT NULL, clinical_identity_id uuid NOT NULL, evidence_type text NOT NULL, evidence_level text NOT NULL, mapping_method text NOT NULL, evidence_reference text, official_source_reference text, evidence_json jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.image_analysis_jobs (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, inference_run_id uuid NOT NULL, deployed_model_version_id uuid NOT NULL, model_version_id uuid NOT NULL, input_artifact_id uuid, source_image_id uuid, idempotency_key text, sample_id text, patient_id text, slide_id text, status text DEFAULT CAST('pending' AS text) NOT NULL, quality_status text DEFAULT CAST('not_assessed' AS text) NOT NULL, quality_metrics jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, threshold_used numeric, threshold_source text, summary jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, total_cells integer, positive_cells integer, started_at timestamp with time zone, completed_at timestamp with time zone, error_message text, created_at timestamp with time zone DEFAULT now() NOT NULL, updated_at timestamp with time zone DEFAULT now() NOT NULL, metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL);

CREATE TABLE public.image_connected_components (id uuid NOT NULL, detection_run_id uuid NOT NULL, analysis_run_id uuid NOT NULL, analysis_run_image_id uuid NOT NULL, microscopy_image_id uuid NOT NULL, component_index integer NOT NULL, bbox_x integer NOT NULL, bbox_y integer NOT NULL, bbox_width integer NOT NULL, bbox_height integer NOT NULL, centroid_x double precision NOT NULL, centroid_y double precision NOT NULL, area_px integer NOT NULL, perimeter_px double precision, circularity double precision, solidity double precision, touches_border boolean NOT NULL, component_status varchar(30) NOT NULL, rejection_code varchar(80), metrics_json jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.image_ingestion_batches (id uuid NOT NULL, subject_id uuid NOT NULL, case_id uuid NOT NULL, sample_id uuid NOT NULL, slide_id uuid NOT NULL, acquisition_origin varchar(40) NOT NULL, source_system varchar(120), source_group_key varchar(240), expected_image_count integer, received_image_count integer DEFAULT 0 NOT NULL, status varchar(20) DEFAULT CAST('pending' AS varchar) NOT NULL, created_by uuid NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL, updated_at timestamp with time zone DEFAULT now() NOT NULL, completed_at timestamp with time zone, metadata_json jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL);

CREATE TABLE public.image_quality_assessments (id uuid NOT NULL, analysis_run_id uuid NOT NULL, analysis_run_image_id uuid NOT NULL, microscopy_image_id uuid NOT NULL, assessment_status varchar(20) NOT NULL, quality_verdict varchar(20) NOT NULL, integrity_verified boolean DEFAULT FALSE NOT NULL, checksum_verified boolean DEFAULT FALSE NOT NULL, decoded_successfully boolean DEFAULT FALSE NOT NULL, width_px integer NOT NULL, height_px integer NOT NULL, pixel_count bigint NOT NULL, channel_count integer, bit_depth integer, color_space varchar(80), analyzed_width_px integer NOT NULL, analyzed_height_px integer NOT NULL, analysis_scale double precision NOT NULL, brightness_mean double precision, brightness_p05 double precision, brightness_p50 double precision, brightness_p95 double precision, contrast_p95_p05 double precision, luminance_stddev double precision, entropy_bits double precision, laplacian_variance double precision, tenengrad_mean double precision, dark_pixel_ratio double precision, bright_pixel_ratio double precision, near_black_border_ratio double precision, usable_field_ratio double precision, warning_codes jsonb DEFAULT CAST('[]' AS jsonb) NOT NULL, failure_codes jsonb DEFAULT CAST('[]' AS jsonb) NOT NULL, metrics_json jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, started_at timestamp with time zone, completed_at timestamp with time zone, error_code varchar(80), error_message text, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.local_execution_jobs (id uuid NOT NULL, principal text NOT NULL, agent_id uuid NOT NULL, owner uuid NOT NULL, request_hash text NOT NULL, campaign_id uuid NOT NULL, run_id uuid, state text NOT NULL, session jsonb, heartbeat_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL, process jsonb, completion jsonb, exit_proof jsonb, result jsonb, created_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL);

CREATE TABLE public.microscopy_analysis_events (id uuid NOT NULL, analysis_run_id uuid NOT NULL, microscopy_image_id uuid, event_type varchar(80) NOT NULL, stage varchar(40) NOT NULL, status varchar(30) NOT NULL, message_code varchar(80), message text, progress_current integer, progress_total integer, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.microscopy_analysis_run_images (id uuid NOT NULL, analysis_run_id uuid NOT NULL, microscopy_image_id uuid NOT NULL, sequence_number integer NOT NULL, input_sha256 char(64) NOT NULL, input_file_size_bytes bigint NOT NULL, input_width_px integer NOT NULL, input_height_px integer NOT NULL, image_status_at_creation varchar(30) NOT NULL, quality_status varchar(20) DEFAULT CAST('pending' AS varchar) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.microscopy_analysis_runs (id uuid NOT NULL, ingestion_batch_id uuid NOT NULL, subject_id uuid NOT NULL, case_id uuid NOT NULL, sample_id uuid NOT NULL, slide_id uuid NOT NULL, run_code varchar(20) NOT NULL, run_status varchar(30) NOT NULL, active_stage varchar(30) NOT NULL, quality_gate_status varchar(20) NOT NULL, ready_for_analysis boolean DEFAULT FALSE NOT NULL, quality_profile_key varchar(80) NOT NULL, quality_profile_version varchar(40) NOT NULL, quality_algorithm_version varchar(40) NOT NULL, quality_profile_snapshot jsonb NOT NULL, input_manifest_sha256 char(64) NOT NULL, input_image_count integer NOT NULL, requested_by uuid NOT NULL, started_at timestamp with time zone, completed_at timestamp with time zone, failed_at timestamp with time zone, error_code varchar(80), error_message text, created_at timestamp with time zone DEFAULT now() NOT NULL, updated_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.microscopy_images (id uuid NOT NULL, slide_id uuid NOT NULL, image_code varchar(120) NOT NULL, storage_provider varchar(40) DEFAULT CAST('local' AS varchar) NOT NULL, storage_key text NOT NULL, original_filename text, mime_type varchar(120) NOT NULL, file_size_bytes bigint NOT NULL, sha256 char(64) NOT NULL, width_px integer NOT NULL, height_px integer NOT NULL, bit_depth integer, magnification numeric, objective_lens varchar(120), microscope_reference varchar(160), camera_reference varchar(160), captured_at timestamp with time zone, status varchar(20) DEFAULT CAST('registered' AS varchar) NOT NULL, metadata_json jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL, updated_at timestamp with time zone DEFAULT now() NOT NULL, created_by uuid NOT NULL, updated_by uuid, archived_at timestamp with time zone, archived_by uuid, acquisition_origin varchar(40) DEFAULT CAST('manual_upload' AS varchar) NOT NULL, source_system varchar(120), source_component_id varchar(240), source_image_name varchar(500), source_relative_path text, image_sequence_number integer, detected_format varchar(20), channel_count integer, color_space varchar(80), orientation varchar(80), ingestion_batch_id uuid);

CREATE TABLE public.model_versions (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, model_id uuid, version_name text, checkpoint_path text, final_model_path text, best_model_path text, training_run_id uuid, created_at timestamp with time zone DEFAULT now(), metadata jsonb DEFAULT CAST('{}' AS jsonb), model_name text, version_number integer, checkpoint_artifact_id uuid, artifact_uri text, artifact_sha256 text, artifact_size_bytes bigint, artifact_hash_reuse_justification text, framework text, framework_version text, preprocessing_profile_snapshot jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, class_mapping jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, input_signature jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, output_signature jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, status text DEFAULT CAST('discovered' AS text) NOT NULL, lineage_status text DEFAULT CAST('unresolved' AS text) NOT NULL, validated_at timestamp with time zone, approved_at timestamp with time zone, retired_at timestamp with time zone);

CREATE TABLE public.models (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, name text NOT NULL, model_type text NOT NULL, framework text, architecture text, description text, input_shape text, output_shape text, num_parameters bigint, pretrained boolean DEFAULT FALSE, pretrained_source text, created_at timestamp with time zone DEFAULT now(), metadata jsonb DEFAULT CAST('{}' AS jsonb));

CREATE TABLE public.predictions (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, run_id uuid, dataset_id uuid, image_id text, image_path text, true_label text, predicted_label text, score numeric, score_positive_label numeric, threshold numeric, is_correct boolean, case_type text, created_at timestamp with time zone DEFAULT now(), metadata jsonb DEFAULT CAST('{}' AS jsonb), image_analysis_job_id uuid, model_version_id uuid, deployed_model_version_id uuid, inference_run_id uuid, classifier_model_version_id uuid, detector_model_version_id uuid, prediction_scope text DEFAULT CAST('legacy_image' AS text) NOT NULL, cell_index integer, source_image_id uuid, bbox_x numeric, bbox_y numeric, bbox_width numeric, bbox_height numeric, crop_artifact_id uuid, explanation_artifact_id uuid, probability_parasitized numeric, probability_uninfected numeric, threshold_used numeric, predicted_class smallint, confidence_level text, quality_status text, review_status text DEFAULT CAST('unreviewed' AS text) NOT NULL, reviewed_label text, reviewed_by text, reviewed_at timestamp with time zone, evaluation_id uuid, dataset_source_record_id uuid, true_class smallint);

CREATE TABLE public.quality_assessment_queue_items (id uuid NOT NULL, analysis_run_id uuid NOT NULL, priority smallint DEFAULT 50 NOT NULL, status varchar(20) DEFAULT CAST('queued' AS varchar) NOT NULL, requested_by uuid NOT NULL, requested_at timestamp with time zone DEFAULT now() NOT NULL, started_at timestamp with time zone, completed_at timestamp with time zone, failed_at timestamp with time zone, attempt_count integer DEFAULT 0 NOT NULL, last_error_code varchar(80), last_error_message text, created_at timestamp with time zone DEFAULT now() NOT NULL, updated_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.quality_gate_decisions (id uuid NOT NULL, analysis_run_id uuid NOT NULL, decision varchar(30) NOT NULL, comment text NOT NULL, actor_user_id uuid NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.research_subjects (id uuid NOT NULL, subject_code varchar(120) NOT NULL, study_reference varchar(200), age_group varchar(80), biological_sex varchar(80), metadata_json jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, status varchar(20) DEFAULT CAST('active' AS varchar) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL, updated_at timestamp with time zone DEFAULT now() NOT NULL, created_by uuid, updated_by uuid, archived_at timestamp with time zone, archived_by uuid, source_system varchar(120), external_patient_id varchar(240));

CREATE TABLE public.roles (id uuid NOT NULL, name text NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.run_checkpoint_policy (run_checkpoint_policy_id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, run_id uuid NOT NULL, model_name text, checkpoint_policy text NOT NULL, checkpoint_policy_config jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, selected_epoch integer, policy_satisfied boolean, selected_metric text, selected_metric_value numeric, min_recall_required numeric, val_recall_parasitized_selected numeric, val_f2_parasitized_selected numeric, val_specificity_selected numeric, val_auc_selected numeric, val_pr_auc_selected numeric, val_balanced_accuracy_selected numeric, prediction_collapse_detected boolean, all_epochs_collapsed boolean, checkpoint_warning text, checkpoint_path text, checkpoint_policy_summary_path text, model_metadata_path text, created_at timestamp with time zone DEFAULT now() NOT NULL, metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, model_version_id uuid, checkpoint_artifact_id uuid);

CREATE TABLE public.run_clinical_metrics (run_clinical_metric_id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, run_id uuid NOT NULL, model_id uuid, model_name text, split_name text NOT NULL, threshold_used numeric, threshold_source text, accuracy numeric, precision_parasitized numeric, recall_parasitized numeric, sensitivity_parasitized numeric, specificity numeric, f1_parasitized numeric, f2_parasitized numeric, roc_auc_parasitized numeric, pr_auc_parasitized numeric, balanced_accuracy numeric, tn bigint NOT NULL, fp bigint NOT NULL, fn bigint NOT NULL, tp bigint NOT NULL, confusion_matrix jsonb DEFAULT CAST('[]' AS jsonb) NOT NULL, classification_report jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, prediction_distribution jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, prediction_collapse jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, label_mapping_version text DEFAULT CAST('clinical_v1_parasitized_positive' AS text) NOT NULL, raw_model_score_meaning text DEFAULT CAST('probability_parasitized' AS text) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL, metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, evaluation_id uuid NOT NULL, sample_count numeric GENERATED ALWAYS AS (CAST(tn AS numeric) + fp + fn + tp) STORED, auc_unavailability_reason text);

CREATE TABLE public.run_configurations (run_id uuid, architecture text NOT NULL, adapter_version text NOT NULL, optimizer text NOT NULL, learning_rate double precision NOT NULL, fine_tune_learning_rate double precision NOT NULL, batch_size integer NOT NULL, random_seed bigint NOT NULL, max_epochs integer NOT NULL, fine_tune_epochs integer NOT NULL, early_stopping boolean NOT NULL, early_stopping_patience integer NOT NULL, early_stopping_min_delta double precision NOT NULL, early_stopping_monitor text NOT NULL, early_stopping_mode text NOT NULL, restore_best_weights boolean NOT NULL, checkpoint_monitor text NOT NULL, checkpoint_mode text NOT NULL, dropout double precision NOT NULL, l2 double precision NOT NULL, input_height integer NOT NULL, input_width integer NOT NULL, input_channels integer NOT NULL, weights text NOT NULL, fine_tune_layers integer NOT NULL, normalization text NOT NULL, internal_preprocessing text, loss_function text NOT NULL, calibration_enabled boolean NOT NULL DEFAULT FALSE, default_threshold numeric NOT NULL DEFAULT 0.5, clinical_target_recall numeric NOT NULL, configuration_hash text NOT NULL, canonical_configuration text NOT NULL, optimizer_extensions jsonb NOT NULL DEFAULT '{}', extension_configuration jsonb NOT NULL DEFAULT '{}', provenance_snapshot jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE public.run_dataset_images (run_dataset_image_id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, run_id uuid NOT NULL, image_id uuid NOT NULL, split_name text NOT NULL, usage_context text NOT NULL, class_index integer NOT NULL, class_name text NOT NULL, relative_path text NOT NULL, filename text NOT NULL, batch_index integer, sample_index integer, used_for_training boolean DEFAULT FALSE NOT NULL, used_for_validation boolean DEFAULT FALSE NOT NULL, used_for_test boolean DEFAULT FALSE NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL, metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL);

CREATE TABLE public.run_image_predictions (run_image_prediction_id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, run_id uuid NOT NULL, image_id uuid, split_name text, usage_context text, filename text, relative_path text, true_label integer, true_label_name text, predicted_label integer, predicted_label_name text, probability_parasitized numeric, probability_uninfected numeric, raw_model_score numeric, raw_model_score_meaning text DEFAULT CAST('probability_parasitized' AS text) NOT NULL, threshold_used numeric, threshold_source text, is_correct boolean, case_type text, metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.run_io_records (run_io_id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, run_id uuid NOT NULL, script_name text NOT NULL, command text, input_parameters jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, output_results jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, output_artifacts jsonb DEFAULT CAST('[]' AS jsonb) NOT NULL, dataset_metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, label_mapping_version text DEFAULT CAST('clinical_v1_parasitized_positive' AS text) NOT NULL, raw_model_score_meaning text DEFAULT CAST('probability_parasitized' AS text), created_at timestamp with time zone DEFAULT now() NOT NULL, metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, run_type text, model_name text, model_metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, clinical_metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, dataset_version_id uuid, dataset_materialization_id uuid);

CREATE TABLE public.run_lineage (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, parent_run_id uuid NOT NULL, child_run_id uuid NOT NULL, relationship_type text NOT NULL, checkpoint_path text, checkpoint_artifact_id uuid, model_version_id uuid, confidence text DEFAULT CAST('explicit' AS text) NOT NULL, metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.run_metrics (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, run_id uuid, metric_name text NOT NULL, metric_value numeric, metric_unit text, split_name text, class_name text, step integer, epoch integer, created_at timestamp with time zone DEFAULT now(), metadata jsonb DEFAULT CAST('{}' AS jsonb));

CREATE TABLE public.run_model_deployments (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, run_id uuid NOT NULL, deployed_model_version_id uuid NOT NULL, model_version_id uuid NOT NULL, role text DEFAULT CAST('primary' AS text) NOT NULL, ordinal integer DEFAULT 0 NOT NULL, weight numeric, metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.run_threshold_calibration (run_threshold_calibration_id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, run_id uuid NOT NULL, model_name text, threshold_policy text DEFAULT CAST('target_recall' AS text) NOT NULL, threshold_source text DEFAULT CAST('validation_calibration' AS text) NOT NULL, threshold_selected numeric NOT NULL, default_threshold numeric DEFAULT 0.5 NOT NULL, target_recall numeric NOT NULL, target_recall_satisfied boolean, min_specificity numeric, validation_recall_at_threshold numeric, validation_specificity_at_threshold numeric, validation_precision_at_threshold numeric, validation_f1_at_threshold numeric, validation_f2_at_threshold numeric, validation_balanced_accuracy_at_threshold numeric, validation_pr_auc numeric, validation_roc_auc numeric, default_threshold_metrics jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, selected_threshold_metrics jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, candidate_count integer, threshold_warning text, calibration_split text DEFAULT CAST('val' AS text) NOT NULL, threshold_calibration_path text, model_metadata_path text, created_at timestamp with time zone DEFAULT now() NOT NULL, metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, model_version_id uuid, calibration_artifact_id uuid, score_name text DEFAULT CAST('probability_parasitized' AS text) NOT NULL, label_mapping_version text DEFAULT CAST('clinical_v1_parasitized_positive' AS text) NOT NULL, positive_label text DEFAULT CAST('parasitized' AS text) NOT NULL, calibration_status text DEFAULT CAST('recorded' AS text) NOT NULL, default_evaluation_id uuid NOT NULL, selected_evaluation_id uuid NOT NULL);

CREATE TABLE public.runs (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, experiment_id uuid, model_id uuid, dataset_id uuid, run_name text, run_type text NOT NULL, status text NOT NULL, command text, script_name text, started_at timestamp with time zone, finished_at timestamp with time zone, duration_seconds numeric, user_name text, host_name text, working_directory text, git_commit text, git_branch text, python_version text, tensorflow_version text, keras_version text, platform text, machine text, processor text, gpu_available boolean, gpu_devices jsonb DEFAULT CAST('[]' AS jsonb), random_seed integer, parameters jsonb DEFAULT CAST('{}' AS jsonb), notes text, created_at timestamp with time zone DEFAULT now(), updated_at timestamp with time zone DEFAULT now(), metadata jsonb DEFAULT CAST('{}' AS jsonb), execution_type text, execution_parameters jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, fine_tuning_start_epoch integer, total_epochs integer, completed_epochs integer DEFAULT 0 NOT NULL, max_epochs integer, stopped_epoch integer, best_epoch integer, checkpoint_monitor text, checkpoint_mode text, best_validation_value double precision, early_stopping_enabled boolean, early_stopping_patience integer, early_stopping_min_delta double precision, restore_best_weights boolean, backend_version text, pipeline_version text, configuration jsonb, error_message text, dataset_version_id uuid, release_status text, release_updated_at timestamp with time zone, release_changed_by text, release_reason text, campaign_id uuid, peak_cpu_memory_bytes bigint, peak_gpu_memory_bytes bigint);

CREATE TABLE public.scientific_cases (id uuid NOT NULL, case_code varchar(120) NOT NULL, subject_id uuid, title varchar(240), description text, source_type varchar(30) NOT NULL, status varchar(20) DEFAULT CAST('draft' AS varchar) NOT NULL, priority varchar(10) DEFAULT CAST('normal' AS varchar) NOT NULL, metadata_json jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL, updated_at timestamp with time zone DEFAULT now() NOT NULL, created_by uuid NOT NULL, updated_by uuid, archived_at timestamp with time zone, archived_by uuid);

CREATE TABLE public.scientific_reviews (id uuid NOT NULL, entity_type varchar(40) NOT NULL, entity_id uuid NOT NULL, decision varchar(30) NOT NULL, comment text, actor_user_id uuid NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.scientific_validation_annotation_events (id uuid NOT NULL, annotation_id uuid NOT NULL, validation_session_id uuid, event_type varchar(20) NOT NULL, annotation_version integer NOT NULL, actor_user_id uuid NOT NULL, before_state jsonb, after_state jsonb NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.scientific_validation_annotations (id uuid NOT NULL, validation_session_id uuid, target_type varchar(20) NOT NULL, cell_detection_id uuid, analysis_run_id uuid, category varchar(120) NOT NULL, content text NOT NULL, version integer DEFAULT 1 NOT NULL, created_by uuid NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL, updated_by uuid NOT NULL, updated_at timestamp with time zone DEFAULT now() NOT NULL, sample_id uuid);

CREATE TABLE public.scientific_validation_classification_runs (session_id uuid NOT NULL, classification_run_id uuid NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.scientific_validation_detection_runs (session_id uuid NOT NULL, detection_run_id uuid NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.scientific_validation_images (session_id uuid NOT NULL, microscopy_image_id uuid NOT NULL, image_sha256 char(64) NOT NULL, sequence_number integer NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.scientific_validation_sessions (id uuid NOT NULL, name varchar(200) NOT NULL, description text, datasource varchar(80) NOT NULL, protocol_key varchar(120) NOT NULL, protocol_version varchar(80) NOT NULL, matching_iou_threshold double precision NOT NULL, status varchar(30) DEFAULT CAST('draft' AS varchar) NOT NULL, initial_snapshot jsonb NOT NULL, snapshot_sha256 char(64) NOT NULL, created_by uuid NOT NULL, updated_by uuid NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL, updated_at timestamp with time zone DEFAULT now() NOT NULL, archived_at timestamp with time zone, archived_by uuid);

CREATE TABLE public.smear_analysis_summaries (id uuid NOT NULL, classification_run_id uuid NOT NULL, analysis_run_id uuid NOT NULL, detection_run_id uuid NOT NULL, outcome varchar(40) NOT NULL, eligible_cell_count integer NOT NULL, classified_cell_count integer NOT NULL, parasitized_candidate_count integer NOT NULL, uninfected_candidate_count integer NOT NULL, near_threshold_count integer NOT NULL, failed_prediction_count integer NOT NULL, parasitized_candidate_fraction double precision, maximum_probability_parasitized double precision, mean_probability_parasitized double precision, median_probability_parasitized double precision, per_image_summary jsonb NOT NULL, aggregation_policy_snapshot jsonb NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.smear_slides (id uuid NOT NULL, sample_id uuid NOT NULL, slide_code varchar(120) NOT NULL, smear_type varchar(20) NOT NULL, stain_type varchar(120), preparation_method varchar(160), prepared_at timestamp with time zone, status varchar(30) DEFAULT CAST('registered' AS varchar) NOT NULL, notes text, metadata_json jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL, updated_at timestamp with time zone DEFAULT now() NOT NULL, created_by uuid NOT NULL, updated_by uuid, archived_at timestamp with time zone, archived_by uuid);

CREATE TABLE public.stage2_model_publication_events (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, publication_id uuid NOT NULL, event_type text NOT NULL, actor text, event_at timestamp with time zone DEFAULT now() NOT NULL, model_version_id uuid NOT NULL, training_run_id uuid NOT NULL, evaluation_run_id uuid NOT NULL, datasource text NOT NULL, previous_status text, new_status text NOT NULL, reason text, correlation_id text, metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL);

CREATE TABLE public.stage2_model_publications (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, datasource text NOT NULL, model_version_id uuid NOT NULL, training_run_id uuid NOT NULL, evaluation_run_id uuid NOT NULL, checkpoint_artifact_id uuid NOT NULL, scope text DEFAULT CAST('stage2' AS text) NOT NULL, status text DEFAULT CAST('active' AS text) NOT NULL, is_active boolean DEFAULT TRUE NOT NULL, published_at timestamp with time zone DEFAULT now() NOT NULL, published_by text, deactivated_at timestamp with time zone, deactivated_by text, created_at timestamp with time zone DEFAULT now() NOT NULL, updated_at timestamp with time zone DEFAULT now() NOT NULL, metadata jsonb DEFAULT CAST('{}' AS jsonb) NOT NULL);

CREATE TABLE public.synthetic_data_runs (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, run_id uuid, method text, num_images_generated integer, source_dataset_id uuid, output_path text, generation_parameters jsonb DEFAULT CAST('{}' AS jsonb), quality_checks jsonb DEFAULT CAST('{}' AS jsonb), created_at timestamp with time zone DEFAULT now(), metadata jsonb DEFAULT CAST('{}' AS jsonb));

CREATE TABLE public.train_execution_records (run_id uuid NOT NULL, kind text NOT NULL, phase text NOT NULL, record_key text NOT NULL, payload jsonb NOT NULL, created_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL, event_id uuid, event_sequence numeric);

CREATE TABLE public.train_execution_revisions (attempt_id uuid NOT NULL, campaign_id uuid NOT NULL, revision_id uuid NOT NULL, created_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL);

CREATE TABLE public.train_execution_sessions (run_id uuid NOT NULL, attempt_id uuid, owner uuid NOT NULL, host text NOT NULL, parent_pid integer NOT NULL, child_pid integer, state text DEFAULT CAST('active' AS text) NOT NULL, configuration jsonb NOT NULL, dataset jsonb NOT NULL, environment jsonb NOT NULL, artifact_root text NOT NULL, cause text, started_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL, updated_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL, completion jsonb, verification jsonb);

CREATE TABLE public.training_history (id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL, run_id uuid NOT NULL, epoch integer NOT NULL, loss numeric, accuracy numeric, precision_value numeric, recall_value numeric, auc numeric, val_loss numeric, val_accuracy numeric, val_precision numeric, val_recall numeric, val_auc numeric, learning_rate numeric, created_at timestamp with time zone DEFAULT now(), metadata jsonb DEFAULT CAST('{}' AS jsonb), phase text DEFAULT CAST('training' AS text) NOT NULL, train_loss numeric, train_accuracy numeric, train_specificity numeric, val_specificity numeric, train_f2 numeric, val_f2 numeric, train_balanced_accuracy numeric, val_balanced_accuracy numeric);

CREATE TABLE public.user_roles (user_id uuid NOT NULL, role_id uuid NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public.users (id uuid NOT NULL, username text NOT NULL, email text, password_hash text NOT NULL, status text DEFAULT CAST('active' AS text) NOT NULL, created_at timestamp with time zone DEFAULT now() NOT NULL, updated_at timestamp with time zone DEFAULT now() NOT NULL, last_login_at timestamp with time zone, disabled_at timestamp with time zone);

CREATE TABLE public.xai_artifacts (id uuid DEFAULT gen_random_uuid(), evidence_id uuid NOT NULL, artifact_id uuid, assessment_artifact_id uuid, role text NOT NULL, ordinal integer NOT NULL DEFAULT 0, storage_uri text NOT NULL, sha256 text NOT NULL, byte_size bigint NOT NULL, mime_type text NOT NULL, numeric_dtype text, tensor_shape integer[], axis_order text, coordinate_space text, availability text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE public.xai_evidence (id uuid DEFAULT gen_random_uuid(), ml_explanation_id uuid, cell_explanation_id uuid, assessment_attempt_id uuid, assessment_sample_id uuid, prediction_id uuid, cell_prediction_id uuid, evaluation_id uuid, dataset_source_record_id uuid, input_artifact_id uuid, microscopy_image_id uuid, run_id uuid, model_version_id uuid, checkpoint_artifact_id uuid NOT NULL, method_configuration_id uuid NOT NULL, target_layer text, prediction_score numeric, source_commit text NOT NULL, input_contract jsonb NOT NULL, input_contract_hash text NOT NULL, input_storage_uri text NOT NULL, input_sha256 text NOT NULL, checkpoint_sha256 text NOT NULL, target_class smallint NOT NULL, explained_output text NOT NULL, processing_stage text NOT NULL, seed bigint, background_manifest_uri text, background_manifest_sha256 text, environment_snapshot jsonb NOT NULL, generated_at timestamptz NOT NULL, created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE public.xai_interpretations (id uuid DEFAULT gen_random_uuid(), evidence_id uuid NOT NULL, author_user_id uuid NOT NULL, interpretation text NOT NULL, limitations text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), supersedes_id uuid);

CREATE TABLE public.xai_quantitative_evaluations (id uuid DEFAULT gen_random_uuid(), protocol_id uuid NOT NULL, metric_name text NOT NULL, membership_hash text NOT NULL, metric_value double precision, undefined_reason text, seed bigint, sample_count bigint NOT NULL, reference_annotation_id uuid, reference_annotation_version integer, reference_manifest_uri text, reference_manifest_sha256 text, details_uri text, details_sha256 text, evaluated_at timestamptz NOT NULL, created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE public.xai_specialist_reviews (id uuid DEFAULT gen_random_uuid(), interpretation_id uuid NOT NULL, reviewer_user_id uuid NOT NULL, decision text NOT NULL, rationale text NOT NULL, competence_snapshot jsonb NOT NULL, reviewed_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE public.xai_method_configurations (id uuid DEFAULT gen_random_uuid(), method text NOT NULL, implementation text NOT NULL, implementation_version text NOT NULL, parameters jsonb NOT NULL, canonical_configuration text NOT NULL, configuration_hash text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE public.xai_region_attributions (xai_evidence_id uuid NOT NULL, region_type text NOT NULL, region_index integer NOT NULL, attribution_value double precision NOT NULL, rank integer, region_definition jsonb, created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE public.xai_evaluation_protocols (id uuid DEFAULT gen_random_uuid(), metric_name text NOT NULL, metric_family text NOT NULL, protocol_name text NOT NULL, protocol_version text NOT NULL, parameters jsonb NOT NULL, normalization_strategy text NOT NULL, perturbation_strategy text, reference_definition jsonb, canonical_protocol text NOT NULL, protocol_hash text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE public.xai_evaluation_members (evaluation_id uuid NOT NULL, xai_evidence_id uuid NOT NULL, member_role text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());

-- 04_functions
CREATE OR REPLACE FUNCTION public.assessment_attempt_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
DECLARE i record; n integer;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'ASSESSMENT_HISTORY_IMMUTABLE'; END IF;
 SELECT * INTO i FROM assessment_identities WHERE id=NEW.identity_id FOR UPDATE;
 IF TG_OP='INSERT' THEN
  IF NEW.state<>'active' OR NEW.verification IS NOT NULL THEN RAISE EXCEPTION 'ASSESSMENT_INVALID_START'; END IF;
  IF i.identity->>'purpose'='final' AND NOT EXISTS(SELECT 1 FROM assessment_final_locks l WHERE l.identity_hash=i.identity_hash
    AND l.evidence->'candidate'=i.identity->'model' AND l.evidence->'decision'=i.identity->'decision')
  THEN RAISE EXCEPTION 'TEST_FINAL_LOCK_REQUIRED'; END IF;
 ELSE
  IF OLD.state<>'active' OR OLD.owner::text IS DISTINCT FROM current_setting('capstone.assessment_owner',true)
    OR (to_jsonb(NEW)-ARRAY['state','cause','verification','finished_at']) IS DISTINCT FROM
       (to_jsonb(OLD)-ARRAY['state','cause','verification','finished_at'])
    OR NEW.state NOT IN ('verified','failed','interrupted') THEN RAISE EXCEPTION 'ASSESSMENT_OWNER_FENCED'; END IF;
  IF NEW.state='verified' THEN
   SELECT count(*) INTO n FROM assessment_results WHERE attempt_id=NEW.id;
   IF n IS DISTINCT FROM jsonb_array_length(i.identity->'samples')
     OR (NEW.verification->>'count')::integer IS DISTINCT FROM n
     OR coalesce(NEW.verification->>'sha256','') !~ '^[a-f0-9]{64}$'
     OR (i.kind='explain' AND (SELECT count(*) FROM assessment_artifacts WHERE attempt_id=NEW.id)<>2*n)
   THEN RAISE EXCEPTION 'ASSESSMENT_INCOMPLETE'; END IF;
  END IF;
 END IF;
 RETURN NEW;
END $function$;

CREATE OR REPLACE FUNCTION public.assessment_consumer_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM campaign_members m JOIN campaign_attempts a ON a.id=m.accepted_attempt_id
 JOIN train_execution_sessions s ON s.run_id=a.training_run_id JOIN assessment_identities i ON i.id=NEW.identity_id
 WHERE m.id=NEW.member_id AND m.campaign_id=NEW.campaign_id AND a.member_id=m.id AND a.state='verified'
 AND s.state='verified' AND i.training_run_id=a.training_run_id AND i.identity->'dataset'=s.dataset
 AND i.identity->'model'->>'model_version_id'=s.verification->'artifact'->>'version_id'
 AND i.identity->'model'->>'sha256'=s.verification->'artifact'->>'sha256'
 AND i.identity->'model'->'bytes'=s.verification->'artifact'->'bytes'
 AND i.identity->'model'->>'path'=s.verification->'artifact'->>'path'
 AND i.identity->'model'->'input_contract'=s.configuration->'resolved'->'input_contract')
 THEN RAISE EXCEPTION 'ASSESSMENT_CAMPAIGN_CONFLICT'; END IF;
 RETURN NEW;
END $function$;

CREATE OR REPLACE FUNCTION public.assessment_identity_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM runs WHERE id=NEW.training_run_id AND run_type='training')
 THEN RAISE EXCEPTION 'ASSESSMENT_TRAIN_REQUIRED'; END IF;
 IF jsonb_typeof(NEW.identity->'protocol') IS DISTINCT FROM 'object'
  OR NEW.identity->'protocol'->>'version' IS NULL
  OR NOT coalesce((NEW.identity->'protocol'->'splits') ? (NEW.identity->>'split'),false)
  OR NOT coalesce((NEW.identity->'protocol'->'purposes') ? (NEW.identity->>'purpose'),false)
  OR (SELECT count(*) FROM jsonb_array_elements(NEW.identity->'samples')) IS DISTINCT FROM
     (SELECT count(DISTINCT s->>'sample_id') FROM jsonb_array_elements(NEW.identity->'samples') s)
 THEN RAISE EXCEPTION 'ASSESSMENT_PROTOCOL_OR_SAMPLES_INVALID'; END IF;
 IF EXISTS(SELECT 1 FROM jsonb_array_elements(NEW.identity->'samples') s
   WHERE s->>'split' IS DISTINCT FROM NEW.identity->>'split'
      OR s->>'patient_id' IS NULL OR s->>'label' IS NULL OR s->>'label' NOT IN ('0','1')
      OR s->>'sha256' IS NULL OR s->>'sha256' !~ '^[a-f0-9]{64}$')
 THEN RAISE EXCEPTION 'ASSESSMENT_SAMPLE_INVALID'; END IF;
 RETURN NEW;
END $function$;

CREATE OR REPLACE FUNCTION public.assessment_immutable()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
BEGIN RAISE EXCEPTION 'ASSESSMENT_HISTORY_IMMUTABLE'; END $function$;

CREATE OR REPLACE FUNCTION public.assessment_result_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
DECLARE a record; i jsonb; sample jsonb;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'ASSESSMENT_RESULT_IMMUTABLE'; END IF;
 SELECT * INTO a FROM assessment_attempts WHERE id=NEW.attempt_id FOR UPDATE;
 IF a.state IS DISTINCT FROM 'active' OR a.owner::text IS DISTINCT FROM current_setting('capstone.assessment_owner',true)
 THEN RAISE EXCEPTION 'ASSESSMENT_OWNER_FENCED'; END IF;
 IF NOT EXISTS (SELECT 1 FROM assessment_identities i, jsonb_array_elements(i.identity->'samples') s
 WHERE i.id=a.identity_id AND s->>'sample_id'=NEW.sample_id::text) THEN RAISE EXCEPTION 'ASSESSMENT_SAMPLE_CONFLICT'; END IF;
 SELECT identity INTO i FROM assessment_identities WHERE id=a.identity_id;
 SELECT s INTO sample FROM jsonb_array_elements(i->'samples') s WHERE s->>'sample_id'=NEW.sample_id::text;
 IF TG_TABLE_NAME='assessment_results' THEN
   IF NEW.payload->>'patient_id' IS DISTINCT FROM sample->>'patient_id' THEN RAISE EXCEPTION 'ASSESSMENT_PATIENT_CONFLICT'; END IF;
   IF i->>'kind'='evaluate' THEN
    IF NEW.payload->'label' IS DISTINCT FROM sample->'label'
      OR jsonb_typeof(NEW.payload->'raw_score') IS DISTINCT FROM 'number'
      OR NOT ((NEW.payload->>'raw_score')::numeric BETWEEN 0 AND 1)
      OR NEW.payload->'calibrated_score' IS DISTINCT FROM 'null'::jsonb
      OR NEW.payload->'threshold' IS DISTINCT FROM i->'decision'->'effective'
      OR NEW.payload->'predicted' IS DISTINCT FROM to_jsonb(CASE WHEN (NEW.payload->>'raw_score')::numeric >= (i->'decision'->>'effective')::numeric THEN 1 ELSE 0 END)
    THEN RAISE EXCEPTION 'ASSESSMENT_PREDICTION_CONFLICT'; END IF;
   ELSE
    IF NEW.payload->'specification' IS DISTINCT FROM i->'explanation'
      OR NEW.payload->'result'->>'score_explained' IS DISTINCT FROM 'raw'
    THEN RAISE EXCEPTION 'ASSESSMENT_EXPLANATION_CONFLICT'; END IF;
   END IF;
 END IF;
 RETURN NEW;
END $function$;

CREATE OR REPLACE FUNCTION public.campaign_attempt_state()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
BEGIN
 UPDATE campaign_members SET state=NEW.state,
 accepted_attempt_id=CASE WHEN NEW.state='verified' THEN
   (SELECT id FROM campaign_attempts WHERE member_id=NEW.member_id AND state='verified' ORDER BY ordinal LIMIT 1)
   ELSE NULL END WHERE id=NEW.member_id;
 RETURN NEW;
END $function$;

CREATE OR REPLACE FUNCTION public.campaign_audit()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
DECLARE before_value jsonb; after_value jsonb; event_id uuid;
BEGIN
 event_id=gen_random_uuid();
 IF TG_OP<>'INSERT' THEN before_value=to_jsonb(OLD); END IF;
 IF TG_OP<>'DELETE' THEN after_value=to_jsonb(NEW); END IF;
 INSERT INTO audit_events(id,event_type,action,resource_type,resource_id,request_method,request_path,correlation_id,
   actor_username_snapshot,before_state,after_state,metadata,success)
 VALUES(event_id,'ml.campaign.'||TG_TABLE_NAME,lower(TG_OP),TG_TABLE_NAME,
   coalesce(after_value->>'id',before_value->>'id',after_value->>'campaign_id',before_value->>'campaign_id'),
   'DB','campaigns.e4',event_id::text,current_user,before_value,after_value,'{}'::jsonb,true);
 RETURN coalesce(NEW,OLD);
END $function$;

CREATE OR REPLACE FUNCTION public.campaign_catalog_identity_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
BEGIN
 IF NEW.name IS DISTINCT FROM OLD.name AND EXISTS(
   SELECT 1 FROM runs r JOIN campaign_attempts a ON a.training_run_id=r.id WHERE r.model_id=OLD.id)
 THEN RAISE EXCEPTION 'LINKED_MODEL_NAME_IMMUTABLE'; END IF;
 RETURN NEW;
END $function$;

CREATE OR REPLACE FUNCTION public.campaign_configuration_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
DECLARE state_value text;
BEGIN
 SELECT state INTO state_value FROM experimental_campaigns WHERE id=coalesce(NEW.campaign_id,OLD.campaign_id) FOR UPDATE;
 IF state_value IS DISTINCT FROM 'draft' THEN RAISE EXCEPTION 'FROZEN_CONFIGURATION_IMMUTABLE'; END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 IF TG_OP='UPDATE' AND (NEW.campaign_id<>OLD.campaign_id OR NEW.configuration_hash<>OLD.configuration_hash) THEN RAISE EXCEPTION 'CONFIGURATION_IDENTITY_IMMUTABLE'; END IF;
 IF NEW.canonical_configuration::jsonb IS DISTINCT FROM NEW.configuration
    OR encode(sha256(convert_to(NEW.canonical_configuration,'UTF8')),'hex')<>NEW.configuration_hash
    THEN RAISE EXCEPTION 'CONFIGURATION_HASH_CONFLICT'; END IF;
 RETURN NEW;
END $function$;

CREATE OR REPLACE FUNCTION public.campaign_environment_identity(v jsonb)
 RETURNS jsonb
 LANGUAGE sql
 IMMUTABLE
 SET search_path TO 'public', 'pg_catalog'
AS $function$
 SELECT jsonb_build_object('source_sha256',v->'source_sha256','python',v->'python','tensorflow',v->'tensorflow',
                          'packages',v->'packages','determinism_environment',v->'determinism_environment')
$function$;

CREATE OR REPLACE FUNCTION public.campaign_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
DECLARE ev record; configs jsonb; members jsonb; p jsonb;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'CAMPAIGN_DELETE_FORBIDDEN'; END IF;
 IF TG_OP='UPDATE' THEN
   IF NEW.id<>OLD.id OR NEW.created_at<>OLD.created_at OR NEW.actor<>OLD.actor THEN RAISE EXCEPTION 'CAMPAIGN_IDENTITY_IMMUTABLE'; END IF;
   IF OLD.state<>'draft' AND (to_jsonb(NEW)-ARRAY['state','updated_at']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['state','updated_at'])
     THEN RAISE EXCEPTION 'FROZEN_CAMPAIGN_IMMUTABLE'; END IF;
   IF NEW.state<>OLD.state AND NOT (
     (OLD.state='draft' AND NEW.state='frozen') OR
     (OLD.state='frozen' AND NEW.state IN ('active','paused')) OR
     (OLD.state='active' AND NEW.state IN ('paused','finalized')) OR
     (OLD.state='paused' AND NEW.state IN ('active','finalized')))
     THEN RAISE EXCEPTION 'INVALID_CAMPAIGN_TRANSITION'; END IF;
   IF NEW.state='finalized' AND EXISTS(SELECT 1 FROM campaign_members WHERE campaign_id=NEW.id AND state IN ('pending','active'))
     THEN RAISE EXCEPTION 'CAMPAIGN_NOT_TERMINAL'; END IF;
 END IF;
 IF TG_OP='INSERT' AND NEW.state<>'draft' THEN RAISE EXCEPTION 'CAMPAIGN_STARTS_DRAFT'; END IF;
 IF TG_OP='INSERT' OR OLD.state='draft' THEN
   SELECT * INTO ev FROM audit_events WHERE id=NEW.dataset_evidence_id;
   IF NOT FOUND OR ev.event_type<>'ml.dataset_verification' OR NOT ev.success OR ev.error_code IS NOT NULL
      OR (ev.after_state->>'integrity_status') IS DISTINCT FROM 'verified'
      OR (ev.after_state->'snapshot') IS DISTINCT FROM NEW.dataset_snapshot
      OR (ev.after_state->>'dataset_version_id') IS DISTINCT FROM NEW.dataset_version_id::text
      THEN RAISE EXCEPTION 'CAMPAIGN_DATASET_EVIDENCE_CONFLICT'; END IF;
 END IF;
 IF TG_OP='UPDATE' AND OLD.state='draft' AND NEW.state='frozen' THEN
   IF NEW.canonical_contract::jsonb IS DISTINCT FROM NEW.contract
      OR encode(sha256(convert_to(NEW.canonical_contract,'UTF8')),'hex')<>NEW.contract_hash THEN RAISE EXCEPTION 'CAMPAIGN_HASH_CONFLICT'; END IF;
   SELECT coalesce(jsonb_object_agg(configuration_hash,jsonb_build_object('configuration',configuration,'requests',requests)),'{}'::jsonb)
      INTO configs FROM campaign_configurations WHERE campaign_id=NEW.id;
   SELECT coalesce(jsonb_agg(jsonb_build_object('configuration_hash',configuration_hash,'seed',seed,'position',position,'exclusion_reason',exclusion_reason) ORDER BY position),'[]'::jsonb)
      INTO members FROM campaign_members WHERE campaign_id=NEW.id;
   IF jsonb_array_length(members)<>NEW.expected_count OR NEW.expected_count=0
      OR (NEW.contract->'matrix'->'configurations') IS DISTINCT FROM configs
      OR (NEW.contract->'matrix'->'members') IS DISTINCT FROM members
      OR (NEW.contract->'matrix'->>'expected_count') IS DISTINCT FROM NEW.expected_count::text
      OR (NEW.contract->'dataset') IS DISTINCT FROM NEW.dataset_snapshot
      OR (NEW.contract->>'dataset_evidence_id') IS DISTINCT FROM NEW.dataset_evidence_id::text
      OR (NEW.contract->'protocol') IS DISTINCT FROM NEW.protocol
      OR (NEW.contract->'requested') IS DISTINCT FROM NEW.requested
      OR (NEW.contract->'environment') IS DISTINCT FROM NEW.environment
      OR (NEW.contract->'matrix'->'registry') IS DISTINCT FROM NEW.registry_snapshot
      OR (NEW.contract->>'name') IS DISTINCT FROM NEW.name
      OR (NEW.contract->>'purpose') IS DISTINCT FROM NEW.purpose
      OR (NEW.contract->>'experiment_id') IS DISTINCT FROM NEW.experiment_id::text
      THEN RAISE EXCEPTION 'INCOMPLETE_FROZEN_MATRIX'; END IF;
   IF NEW.expected_count<>(SELECT count(*) FROM campaign_configurations WHERE campaign_id=NEW.id)*jsonb_array_length(NEW.contract->'matrix'->'seeds')
      OR EXISTS(SELECT 1 FROM campaign_members WHERE campaign_id=NEW.id AND NOT ((NEW.contract->'matrix'->'seeds') @> jsonb_build_array(seed)))
      OR jsonb_array_length(NEW.contract->'matrix'->'seeds')<>(SELECT count(DISTINCT value) FROM jsonb_array_elements(NEW.contract->'matrix'->'seeds'))
      THEN RAISE EXCEPTION 'INCOMPLETE_CONFIGURATION_SEED_GRID'; END IF;
   p=NEW.protocol;
   IF NOT (p ?& ARRAY['version','objective','metrics','sensitivity_target','specificity_minimum','roles','ranking','checkpoint','early_stopping','calibration','budget','missing','retries','fallback','test_access','aggregation','uncertainty','limitations','pending'])
      OR p->'pending' IS DISTINCT FROM '[]'::jsonb
      OR p->'roles' IS DISTINCT FROM '{"train":"train","selection":"val","calibration":"val","final_test":"test"}'::jsonb
      OR p->>'test_access' IS DISTINCT FROM 'final_only_after_candidate_lock'
      OR p->'ranking'->>'partition' IS DISTINCT FROM 'val'
      OR p->'calibration'->>'population' IS DISTINCT FROM 'val'
      OR p->'limitations'->'independent_calibration' IS DISTINCT FROM 'false'::jsonb
      OR p->>'retries' IS DISTINCT FROM 'first_verified_attempt'
      OR p->>'missing' IS DISTINCT FROM 'report_all_members'
      OR p->>'fallback' IS DISTINCT FROM 'diagnostic_only'
      THEN RAISE EXCEPTION 'INVALID_FROZEN_PROTOCOL'; END IF;
   IF jsonb_typeof(p->'sensitivity_target') IS DISTINCT FROM 'number'
      OR jsonb_typeof(p->'specificity_minimum') IS DISTINCT FROM 'number'
      OR (p->>'sensitivity_target')::numeric NOT BETWEEN 0 AND 1
      OR (p->>'specificity_minimum')::numeric NOT BETWEEN 0 AND 1
      OR (p->'budget'->>'max_members')::integer < NEW.expected_count
      OR coalesce((p->'budget'->>'max_attempts_per_member')::integer,0)<1
      OR coalesce(length(btrim(p->>'version')),0)=0
      OR coalesce(length(btrim(p->>'objective')),0)=0
      OR coalesce(length(btrim(p->'limitations'->>'shared_val')),0)=0
      OR p->'limitations'->>'test_exposure' IS NULL
      OR p->'limitations'->>'test_exposure' NOT IN ('unknown','previously_accessed')
      OR p->'checkpoint'->'threshold' IS DISTINCT FROM '0.5'::jsonb
      THEN RAISE EXCEPTION 'INCOMPLETE_SCIENTIFIC_PROTOCOL'; END IF;
   IF EXISTS(SELECT 1 FROM campaign_members WHERE campaign_id=NEW.id AND state NOT IN ('pending','excluded'))
      OR NOT EXISTS(SELECT 1 FROM campaign_members WHERE campaign_id=NEW.id AND state='pending')
      THEN RAISE EXCEPTION 'INVALID_INITIAL_MEMBERS'; END IF;
 END IF;
 NEW.updated_at=now(); RETURN NEW;
END $function$;

CREATE OR REPLACE FUNCTION public.campaign_json_integer(v jsonb, minimum_value numeric)
 RETURNS boolean
 LANGUAGE plpgsql
 IMMUTABLE
 SET search_path TO 'public', 'pg_catalog'
AS $function$
DECLARE n numeric;
BEGIN
 IF jsonb_typeof(v) IS DISTINCT FROM 'number' THEN RETURN false; END IF;
 n=(v #>> '{}')::numeric;
 RETURN n=trunc(n) AND n>=minimum_value AND n<=2147483647;
END $function$;

CREATE OR REPLACE FUNCTION public.campaign_json_object(v jsonb, required_keys text[])
 RETURNS boolean
 LANGUAGE plpgsql
 IMMUTABLE
 SET search_path TO 'public', 'pg_catalog'
AS $function$
DECLARE k text;
BEGIN
 IF jsonb_typeof(v) IS DISTINCT FROM 'object' THEN RETURN false; END IF;
 FOREACH k IN ARRAY required_keys LOOP
   IF NOT (v ? k) OR v->k='null'::jsonb THEN RETURN false; END IF;
 END LOOP;
 RETURN true;
END $function$;

CREATE OR REPLACE FUNCTION public.campaign_json_string(v jsonb)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
 SET search_path TO 'public', 'pg_catalog'
AS $function$
 SELECT coalesce(jsonb_typeof(v)='string' AND length(btrim(v #>> '{}'))>0,false)
$function$;

CREATE OR REPLACE FUNCTION public.campaign_member_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
DECLARE parent_state text; current_attempt text;
BEGIN
 SELECT state INTO parent_state FROM experimental_campaigns WHERE id=coalesce(NEW.campaign_id,OLD.campaign_id) FOR UPDATE;
 IF TG_OP='DELETE' THEN
   IF parent_state<>'draft' THEN RAISE EXCEPTION 'FROZEN_MEMBER_IMMUTABLE'; END IF; RETURN OLD;
 END IF;
 IF TG_OP='INSERT' AND (parent_state IS DISTINCT FROM 'draft' OR NEW.state NOT IN ('pending','excluded')) THEN RAISE EXCEPTION 'MEMBERS_REQUIRE_DRAFT'; END IF;
 IF TG_OP='UPDATE' THEN
   IF NEW.id<>OLD.id OR NEW.campaign_id<>OLD.campaign_id THEN RAISE EXCEPTION 'MEMBER_IDENTITY_IMMUTABLE'; END IF;
   IF parent_state<>'draft' AND (to_jsonb(NEW)-ARRAY['state','accepted_attempt_id']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['state','accepted_attempt_id']) THEN RAISE EXCEPTION 'FROZEN_MEMBER_IMMUTABLE'; END IF;
   IF NEW.state='verified' OR NEW.accepted_attempt_id IS NOT NULL THEN
     IF NEW.state IS DISTINCT FROM 'verified' OR NEW.accepted_attempt_id IS DISTINCT FROM
       (SELECT id FROM campaign_attempts WHERE member_id=NEW.id AND state='verified' ORDER BY ordinal LIMIT 1)
       OR NEW.accepted_attempt_id IS NULL THEN RAISE EXCEPTION 'FIRST_VERIFIED_ATTEMPT_REQUIRED'; END IF;
   END IF;
   IF NEW.state<>OLD.state THEN
     SELECT state INTO current_attempt FROM campaign_attempts WHERE member_id=NEW.id ORDER BY ordinal DESC LIMIT 1;
     IF NEW.state IS DISTINCT FROM current_attempt THEN RAISE EXCEPTION 'MEMBER_STATE_MUST_FOLLOW_ATTEMPT'; END IF;
   END IF;
 END IF;
 RETURN NEW;
END $function$;

CREATE OR REPLACE FUNCTION public.campaign_model_matches(run_id uuid, member uuid)
 RETURNS boolean
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
DECLARE model_name text; cfg jsonb; registry jsonb; d jsonb; matches integer;
BEGIN
 SELECT mo.name,cf.configuration,c.registry_snapshot INTO model_name,cfg,registry
 FROM runs r JOIN models mo ON mo.id=r.model_id
 JOIN campaign_members m ON m.id=member
 JOIN campaign_configurations cf ON cf.campaign_id=m.campaign_id AND cf.configuration_hash=m.configuration_hash
 JOIN experimental_campaigns c ON c.id=m.campaign_id WHERE r.id=run_id;
 IF NOT FOUND THEN RETURN false; END IF;
 SELECT count(*) INTO matches FROM jsonb_array_elements(registry) item
 WHERE item->>'id'=cfg->>'model_id' AND item->>'version'=cfg->>'adapter_version'
   AND (item->>'id'=model_name OR item->'aliases' @> to_jsonb(ARRAY[model_name]));
 RETURN matches=1;
END $function$;

CREATE OR REPLACE FUNCTION public.controlled_binding_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM campaign_attempts a JOIN train_execution_sessions s ON s.attempt_id=a.id
 JOIN campaign_technical_revisions v ON v.id=NEW.revision_id JOIN runs r ON r.id=NEW.run_id
 WHERE a.id=NEW.attempt_id AND a.member_id=NEW.member_id AND a.training_run_id=NEW.run_id
 AND s.run_id=NEW.run_id AND r.campaign_id=NEW.campaign_id AND s.environment=v.payload->'environment'
 AND s.configuration IS NOT DISTINCT FROM r.execution_parameters->'model_configuration_e2'->'configuration'
 AND s.dataset IS NOT DISTINCT FROM r.execution_parameters->'model_configuration_e2'->'dataset')
 THEN RAISE EXCEPTION 'CONTROLLED_BINDING_INVALID'; END IF;
 RETURN NEW;
END $function$;

CREATE OR REPLACE FUNCTION public.controlled_pause_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
BEGIN
 IF NEW.state IS DISTINCT FROM 'paused' AND EXISTS(
  SELECT 1 FROM campaign_controlled_requests q JOIN campaign_attempts a ON a.id=q.attempt_id
  WHERE q.campaign_id=NEW.id AND a.state IN ('active','completed'))
 THEN RAISE EXCEPTION 'CONTROLLED_TRAIN_REQUIRES_PAUSED'; END IF;
 RETURN NEW;
END $function$;

CREATE OR REPLACE FUNCTION public.controlled_run_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
DECLARE q record;
BEGIN
 SELECT * INTO q FROM campaign_controlled_requests WHERE run_id=NEW.id;
 IF FOUND AND NEW.campaign_id IS DISTINCT FROM q.campaign_id THEN RAISE EXCEPTION 'CONTROLLED_CAMPAIGN_ID_REQUIRED'; END IF;
 IF TG_OP='UPDATE' AND NEW.campaign_id IS DISTINCT FROM OLD.campaign_id THEN RAISE EXCEPTION 'RUN_CAMPAIGN_IMMUTABLE'; END IF;
 RETURN NEW;
END $function$;

CREATE FUNCTION public.e04_assert_calibration(member_id uuid) RETURNS void LANGUAGE plpgsql
 SET search_path=public,pg_catalog AS $$
DECLARE e public.evaluations%ROWTYPE; d public.evaluations%ROWTYPE; s public.evaluations%ROWTYPE;
 c public.run_threshold_calibration%ROWTYPE; ev jsonb; result jsonb; context jsonb;
 n integer; m public.run_clinical_metrics%ROWTYPE; expected jsonb; k text;
BEGIN
 SELECT * INTO e FROM public.evaluations WHERE id=member_id;
 IF NOT FOUND OR e.source_kind<>'e10'
 OR e.evaluation_role NOT IN ('calibration_default','calibration_selected') THEN RETURN; END IF;
 SELECT count(*) INTO n FROM public.run_threshold_calibration
 WHERE default_evaluation_id=e.id OR selected_evaluation_id=e.id;
 IF n<>1 THEN RAISE EXCEPTION 'E04_PAIR_REQUIRED'; END IF;
 SELECT * INTO STRICT c FROM public.run_threshold_calibration
 WHERE default_evaluation_id=e.id OR selected_evaluation_id=e.id;
 SELECT * INTO d FROM public.evaluations WHERE id=c.default_evaluation_id;
 SELECT * INTO s FROM public.evaluations WHERE id=c.selected_evaluation_id;
 IF d.id IS NULL OR s.id IS NULL THEN RAISE EXCEPTION 'E04_PAIR_REQUIRED'; END IF;
 IF d.id=s.id OR d.evaluation_role IS DISTINCT FROM 'calibration_default'
 OR s.evaluation_role IS DISTINCT FROM 'calibration_selected'
 OR d.source_kind IS DISTINCT FROM 'e10' OR s.source_kind IS DISTINCT FROM 'e10'
 OR d.split IS DISTINCT FROM 'val' OR s.split IS DISTINCT FROM 'val'
 OR c.calibration_split IS DISTINCT FROM 'val'
 OR d.run_id IS DISTINCT FROM s.run_id OR d.training_run_id IS DISTINCT FROM s.training_run_id
 OR d.run_id IS DISTINCT FROM d.training_run_id OR d.training_run_id IS DISTINCT FROM c.run_id
 OR d.model_version_id IS DISTINCT FROM s.model_version_id
 OR c.model_version_id IS DISTINCT FROM d.model_version_id
 OR d.checkpoint_artifact_id IS DISTINCT FROM s.checkpoint_artifact_id
 OR d.dataset_version_id IS DISTINCT FROM s.dataset_version_id
 OR d.population_hash IS DISTINCT FROM s.population_hash
 OR d.protocol_version IS DISTINCT FROM s.protocol_version
 OR d.protocol_hash IS DISTINCT FROM s.protocol_hash
 OR d.protocol_snapshot IS DISTINCT FROM s.protocol_snapshot
 OR d.input_contract_hash IS DISTINCT FROM s.input_contract_hash
 OR d.comparison_contract_hash IS DISTINCT FROM s.comparison_contract_hash
 OR d.subject_kind IS DISTINCT FROM s.subject_kind
 OR d.source_event_id IS DISTINCT FROM s.source_event_id
 THEN RAISE EXCEPTION 'E04_PAIR_IDENTITY_MISMATCH'; END IF;
 IF d.threshold_source IS DISTINCT FROM 'default' OR d.calibration_id IS NOT NULL
 OR d.threshold_used IS DISTINCT FROM c.default_threshold
 OR s.threshold_source IS DISTINCT FROM 'validation_calibration'
 OR s.calibration_id IS DISTINCT FROM c.run_threshold_calibration_id
 OR s.threshold_used IS DISTINCT FROM c.threshold_selected
 THEN RAISE EXCEPTION 'E04_THRESHOLD_PROVENANCE'; END IF;
 SELECT (payload->>'canonical_event')::jsonb INTO ev FROM public.train_execution_records
 WHERE run_id=d.run_id AND event_id=d.source_event_id AND kind='e10_event'
 AND phase='run_event_v1' AND record_key=d.source_event_id::text;
 result:=ev#>'{payload,result,result}';
 IF ev->>'event_type' IS DISTINCT FROM 'calibration_completed'
 OR ev->>'event_id' IS DISTINCT FROM d.source_event_id::text
 OR ev->>'run_id' IS DISTINCT FROM d.run_id::text
 OR ev->>'schema_version' IS DISTINCT FROM 'run_event_v1'
 OR ev#>>'{payload,result,split}' IS DISTINCT FROM 'val'
 OR result->>'calibration_split' IS DISTINCT FROM 'val'
 OR result->>'threshold_source' IS DISTINCT FROM 'validation_calibration'
 OR (result->>'threshold_selected')::numeric IS DISTINCT FROM c.threshold_selected
 OR (result->>'threshold_used')::numeric IS DISTINCT FROM c.threshold_selected
 OR (result->>'default_threshold')::numeric IS DISTINCT FROM c.default_threshold
 OR (result->>'target_recall')::numeric IS DISTINCT FROM c.target_recall
 THEN RAISE EXCEPTION 'E04_EVENT_PROVENANCE'; END IF;
 SELECT execution_parameters->'e10_v2_evaluation_context_v1' INTO context
 FROM public.runs WHERE id=d.run_id;
 IF context IS NULL OR context->>'checkpoint_artifact_id' IS DISTINCT FROM d.checkpoint_artifact_id::text
 OR context->>'model_version_id' IS DISTINCT FROM d.model_version_id::text
 OR context->>'protocol_version' IS DISTINCT FROM d.protocol_version
 OR context->>'protocol_hash' IS DISTINCT FROM d.protocol_hash
 OR context->'protocol_snapshot' IS DISTINCT FROM d.protocol_snapshot
 OR context->>'population_hash' IS DISTINCT FROM d.population_hash
 OR context->>'input_contract_hash' IS DISTINCT FROM d.input_contract_hash
 OR context->>'comparison_contract_hash' IS DISTINCT FROM d.comparison_contract_hash
 THEN RAISE EXCEPTION 'E04_CONTEXT_PROVENANCE'; END IF;
 FOR m IN SELECT * FROM public.run_clinical_metrics WHERE evaluation_id IN (d.id,s.id) LOOP
   expected:=CASE WHEN m.evaluation_id=d.id THEN result->'default_threshold_metrics' ELSE result->'selected_metrics' END;
   IF expected IS NULL OR jsonb_typeof(expected) IS DISTINCT FROM 'object' THEN
     RAISE EXCEPTION 'E04_METRIC_PROVENANCE';
   END IF;
   FOREACH k IN ARRAY ARRAY['tn','fp','fn','tp','roc_auc_parasitized','pr_auc_parasitized'] LOOP
     IF NOT (expected ? k) OR (to_jsonb(m)->k) IS DISTINCT FROM expected->k THEN
       RAISE EXCEPTION 'E04_METRIC_PROVENANCE';
     END IF;
   END LOOP;
 END LOOP;
 IF (SELECT count(*) FROM public.run_clinical_metrics WHERE evaluation_id IN (d.id,s.id))<>2 THEN
   RAISE EXCEPTION 'E04_PAIR_METRICS_REQUIRED';
 END IF;
END $$;

CREATE FUNCTION public.e04_calibration_immutable() RETURNS trigger LANGUAGE plpgsql
 SET search_path=public,pg_catalog AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM public.evaluations WHERE source_kind='e10'
 AND id IN (OLD.default_evaluation_id,OLD.selected_evaluation_id)) THEN
   RAISE EXCEPTION 'E04_CALIBRATION_IMMUTABLE';
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.e04_legacy_admission() RETURNS trigger LANGUAGE plpgsql
 SET search_path=public,pg_catalog AS $$
BEGIN
 IF NEW.source_kind='legacy' AND current_user <> 'capstone_v2_migrator' THEN
   RAISE EXCEPTION 'E04_LEGACY_MIGRATOR_REQUIRED' USING ERRCODE='42501';
 END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.enforce_activation_materialization_consistency()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        DECLARE materialization_version UUID;
        BEGIN
          SELECT dataset_version_id INTO materialization_version
          FROM dataset_materializations WHERE id = NEW.materialization_id;
          IF materialization_version IS DISTINCT FROM NEW.dataset_version_id THEN
            RAISE EXCEPTION 'activation version differs from materialization version'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END;
        $function$;

CREATE OR REPLACE FUNCTION public.enforce_dataset_assignment_consistency()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        DECLARE
          source_identity UUID;
          source_class_index INTEGER;
          source_class_name TEXT;
          conflicting_split TEXT;
          version_status TEXT;
        BEGIN
          SELECT status INTO version_status
          FROM dataset_versions WHERE id = NEW.dataset_version_id;
          IF version_status = 'FROZEN' THEN
            RAISE EXCEPTION 'assignments of a FROZEN dataset version are immutable'
              USING ERRCODE = '23514';
          END IF;

          SELECT clinical_identity_id, class_index, class_name
            INTO source_identity, source_class_index, source_class_name
          FROM dataset_source_records WHERE id = NEW.source_record_id;
          IF source_identity IS NULL OR source_identity IS DISTINCT FROM NEW.clinical_identity_id THEN
            RAISE EXCEPTION 'assignment clinical identity differs from source record identity'
              USING ERRCODE = '23514';
          END IF;
          IF source_class_index IS DISTINCT FROM NEW.class_index
             OR source_class_name IS DISTINCT FROM NEW.class_name THEN
            RAISE EXCEPTION 'assignment class differs from source record class'
              USING ERRCODE = '23514';
          END IF;

          PERFORM pg_advisory_xact_lock(
            hashtextextended(NEW.dataset_version_id::text || ':' || NEW.clinical_identity_id::text, 0)
          );
          SELECT split_name INTO conflicting_split
          FROM dataset_split_assignments
          WHERE dataset_version_id = NEW.dataset_version_id
            AND clinical_identity_id = NEW.clinical_identity_id
            AND id IS DISTINCT FROM NEW.id
            AND split_name <> NEW.split_name
          LIMIT 1;
          IF conflicting_split IS NOT NULL THEN
            RAISE EXCEPTION 'patient is already assigned to split % in this dataset version', conflicting_split
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END;
        $function$;

CREATE OR REPLACE FUNCTION public.enforce_dataset_version_lifecycle()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        BEGIN
          IF OLD.status = 'FROZEN' AND (
            NEW.name IS DISTINCT FROM OLD.name OR
            NEW.semantic_version IS DISTINCT FROM OLD.semantic_version OR
            NEW.grouping_strategy IS DISTINCT FROM OLD.grouping_strategy OR
            NEW.grouping_field IS DISTINCT FROM OLD.grouping_field OR
            NEW.stratification_strategy IS DISTINCT FROM OLD.stratification_strategy OR
            NEW.split_algorithm IS DISTINCT FROM OLD.split_algorithm OR
            NEW.split_algorithm_version IS DISTINCT FROM OLD.split_algorithm_version OR
            NEW.random_seed IS DISTINCT FROM OLD.random_seed OR
            NEW.target_train_ratio IS DISTINCT FROM OLD.target_train_ratio OR
            NEW.target_val_ratio IS DISTINCT FROM OLD.target_val_ratio OR
            NEW.target_test_ratio IS DISTINCT FROM OLD.target_test_ratio OR
            NEW.positive_class IS DISTINCT FROM OLD.positive_class OR
            NEW.class_mapping IS DISTINCT FROM OLD.class_mapping OR
            NEW.source_record_count IS DISTINCT FROM OLD.source_record_count OR
            NEW.methodology_json IS DISTINCT FROM OLD.methodology_json
          ) THEN
            RAISE EXCEPTION 'scientific fields of a FROZEN dataset version are immutable'
              USING ERRCODE = '23514';
          END IF;

          IF NEW.status IS DISTINCT FROM OLD.status THEN
            IF NOT (
              (OLD.status = 'DRAFT' AND NEW.status IN ('GENERATED','ARCHIVED')) OR
              (OLD.status = 'GENERATED' AND NEW.status IN ('VALIDATED','ARCHIVED')) OR
              (OLD.status = 'VALIDATED' AND NEW.status IN ('FROZEN','ARCHIVED')) OR
              (OLD.status = 'FROZEN' AND NEW.status = 'ARCHIVED')
            ) THEN
              RAISE EXCEPTION 'invalid dataset version lifecycle transition: % -> %', OLD.status, NEW.status
                USING ERRCODE = '23514';
            END IF;
            IF NEW.status = 'GENERATED' THEN NEW.generated_at := COALESCE(NEW.generated_at, now()); END IF;
            IF NEW.status = 'VALIDATED' THEN NEW.validated_at := COALESCE(NEW.validated_at, now()); END IF;
            IF NEW.status = 'FROZEN' THEN NEW.frozen_at := COALESCE(NEW.frozen_at, now()); END IF;
            IF NEW.status = 'ARCHIVED' THEN NEW.archived_at := COALESCE(NEW.archived_at, now()); END IF;
          END IF;
          RETURN NEW;
        END;
        $function$;

CREATE OR REPLACE FUNCTION public.enforce_model_version_governance()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    owner_run_type TEXT;
BEGIN
    IF NEW.training_run_id IS NOT NULL THEN
        SELECT run_type
        INTO owner_run_type
        FROM runs
        WHERE id = NEW.training_run_id;

        IF owner_run_type IS DISTINCT FROM 'training' THEN
            RAISE EXCEPTION
                'model_versions.training_run_id debe referenciar un run training; recibió % (%)',
                NEW.training_run_id,
                owner_run_type
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF TG_OP = 'UPDATE'
       AND (
           OLD.status IN (
               'candidate', 'validated', 'approved', 'deployed', 'rejected', 'retired'
           )
           OR NEW.status IN (
               'candidate', 'validated', 'approved', 'deployed', 'rejected', 'retired'
           )
       )
       AND ROW(
           NEW.model_id,
           NEW.model_name,
           NEW.version_number,
           NEW.checkpoint_path,
           NEW.final_model_path,
           NEW.best_model_path,
           NEW.training_run_id,
           NEW.checkpoint_artifact_id,
           NEW.artifact_uri,
           NEW.artifact_sha256,
           NEW.artifact_size_bytes,
           NEW.artifact_hash_reuse_justification,
           NEW.framework,
           NEW.framework_version,
           NEW.preprocessing_profile_snapshot,
           NEW.class_mapping,
           NEW.input_signature,
           NEW.output_signature
       ) IS DISTINCT FROM ROW(
           OLD.model_id,
           OLD.model_name,
           OLD.version_number,
           OLD.checkpoint_path,
           OLD.final_model_path,
           OLD.best_model_path,
           OLD.training_run_id,
           OLD.checkpoint_artifact_id,
           OLD.artifact_uri,
           OLD.artifact_sha256,
           OLD.artifact_size_bytes,
           OLD.artifact_hash_reuse_justification,
           OLD.framework,
           OLD.framework_version,
           OLD.preprocessing_profile_snapshot,
           OLD.class_mapping,
           OLD.input_signature,
           OLD.output_signature
       ) THEN
        RAISE EXCEPTION
            'El payload de una model_version gobernada es inmutable (%)',
            OLD.id
            USING ERRCODE = '55000';
    END IF;

    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION public.enforce_run_lineage_governance()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    parent_type TEXT;
    child_type TEXT;
BEGIN
    SELECT run_type INTO parent_type FROM runs WHERE id = NEW.parent_run_id;
    SELECT run_type INTO child_type FROM runs WHERE id = NEW.child_run_id;

    IF NEW.relationship_type = 'evaluates_checkpoint_from'
       AND (parent_type IS DISTINCT FROM 'training' OR child_type IS DISTINCT FROM 'evaluation') THEN
        RAISE EXCEPTION
            'evaluates_checkpoint_from exige parent training y child evaluation; recibió % -> %',
            parent_type,
            child_type
            USING ERRCODE = '23514';
    END IF;

    IF NEW.relationship_type = 'explains_checkpoint_from'
       AND (parent_type IS DISTINCT FROM 'training' OR child_type IS DISTINCT FROM 'explainability') THEN
        RAISE EXCEPTION
            'explains_checkpoint_from exige parent training y child explainability; recibió % -> %',
            parent_type,
            child_type
            USING ERRCODE = '23514';
    END IF;

    IF NEW.relationship_type IN (
           'evaluates_checkpoint_from', 'explains_checkpoint_from'
       )
       AND (
           NEW.model_version_id IS NULL
           OR NEW.checkpoint_artifact_id IS NULL
       ) THEN
        IF TG_OP = 'INSERT' THEN
            RAISE EXCEPTION
                'El linaje gobernado % exige model_version_id y checkpoint_artifact_id',
                NEW.relationship_type
                USING ERRCODE = '23514';
        ELSIF ROW(
            NEW.relationship_type,
            NEW.parent_run_id,
            NEW.child_run_id,
            NEW.model_version_id,
            NEW.checkpoint_artifact_id
        ) IS DISTINCT FROM ROW(
            OLD.relationship_type,
            OLD.parent_run_id,
            OLD.child_run_id,
            OLD.model_version_id,
            OLD.checkpoint_artifact_id
        ) THEN
            RAISE EXCEPTION
                'Cambiar la identidad de linaje % exige model_version_id y checkpoint_artifact_id',
                NEW.relationship_type
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION public.execution_event_immutable()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
BEGIN RAISE EXCEPTION 'EXECUTION_HISTORY_IMMUTABLE'; END $function$;

CREATE OR REPLACE FUNCTION public.experiment_require_owner()
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
DECLARE g record;
BEGIN
 SELECT * INTO g FROM experiment_execution_gate WHERE singleton FOR UPDATE;
 IF g.owner IS NULL OR g.owner::text IS DISTINCT FROM current_setting('capstone.execution_token',true)
 OR NOT (EXISTS(SELECT 1 FROM pg_locks WHERE locktype='advisory' AND classid=120994 AND objid=1 AND objsubid=2 AND pid=g.db_pid AND granted)
 OR EXISTS(SELECT 1 FROM local_execution_jobs WHERE owner=g.owner AND state IN ('held','calculation_reported')))
 THEN RAISE EXCEPTION 'GLOBAL_EXECUTION_OWNER_REQUIRED'; END IF;
END $function$;

CREATE OR REPLACE FUNCTION public.prevent_audit_event_mutation()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
      BEGIN
        RAISE EXCEPTION 'audit_events is append-only';
      END $function$;

CREATE OR REPLACE FUNCTION public.prevent_stage2_publication_event_mutation()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    RAISE EXCEPTION 'stage2_model_publication_events es append-only';
END;
$function$;

CREATE OR REPLACE FUNCTION public.prevent_validation_annotation_event_mutation()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    BEGIN
      RAISE EXCEPTION 'scientific validation annotation events are append-only'
        USING ERRCODE='55000';
    END $function$;

CREATE OR REPLACE FUNCTION public.prevent_validation_membership_mutation()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    BEGIN
      RAISE EXCEPTION 'scientific validation membership is append-only';
    END $function$;

CREATE OR REPLACE FUNCTION public.protect_cell_classification_run()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    DECLARE
      actual_input_count INTEGER;
      actual_eligible_count INTEGER;
      actual_excluded_count INTEGER;
      actual_processed_count INTEGER;
      actual_parasitized_count INTEGER;
      actual_uninfected_count INTEGER;
      actual_near_threshold_count INTEGER;
      actual_failed_count INTEGER;
      actual_summary_count INTEGER;
    BEGIN
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'cell_classification_runs cannot be deleted'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status IN ('completed','completed_with_warnings','failed') THEN
        RAISE EXCEPTION 'terminal cell_classification_runs are immutable'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status = 'created' AND NEW.status NOT IN ('processing','failed') THEN
        RAISE EXCEPTION 'invalid cell classification run transition'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status = 'created' AND NEW.status = 'processing' THEN
        SELECT
          count(*),
          count(*) FILTER (WHERE eligible),
          count(*) FILTER (WHERE NOT eligible)
        INTO
          actual_input_count,
          actual_eligible_count,
          actual_excluded_count
        FROM cell_classification_inputs
        WHERE classification_run_id=OLD.id;
        IF actual_input_count <> OLD.input_count
          OR actual_eligible_count <> OLD.eligible_count
          OR actual_excluded_count <> OLD.excluded_count
        THEN
          RAISE EXCEPTION
            'frozen classification inputs do not match run counters'
            USING ERRCODE = '23514';
        END IF;
      END IF;
      IF OLD.status = 'processing'
        AND NEW.status NOT IN (
          'processing','completed','completed_with_warnings','failed'
        )
      THEN
        RAISE EXCEPTION 'invalid cell classification run transition'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status IN ('created','processing') THEN
        SELECT
          count(*),
          count(*) FILTER (
            WHERE prediction_status='completed'
              AND predicted_label='parasitized'
          ),
          count(*) FILTER (
            WHERE prediction_status='completed'
              AND predicted_label='uninfected'
          ),
          count(*) FILTER (
            WHERE prediction_status='completed' AND near_threshold
          ),
          count(*) FILTER (WHERE prediction_status='failed')
        INTO
          actual_processed_count,
          actual_parasitized_count,
          actual_uninfected_count,
          actual_near_threshold_count,
          actual_failed_count
        FROM cell_predictions
        WHERE classification_run_id=OLD.id;
        IF actual_processed_count <> NEW.processed_count
          OR actual_parasitized_count <> NEW.parasitized_count
          OR actual_uninfected_count <> NEW.uninfected_count
          OR actual_near_threshold_count <> NEW.near_threshold_count
          OR actual_failed_count <> NEW.failed_count
        THEN
          RAISE EXCEPTION
            'persisted predictions do not match run counters'
            USING ERRCODE = '23514';
        END IF;
      END IF;
      IF NEW.status IN ('completed','completed_with_warnings') THEN
        SELECT count(*)
        INTO actual_summary_count
        FROM smear_analysis_summaries
        WHERE classification_run_id=OLD.id;
        IF actual_summary_count <> 1 THEN
          RAISE EXCEPTION
            'completed classification run requires one immutable summary'
            USING ERRCODE = '23514';
        END IF;
      END IF;
      IF NEW.updated_at < OLD.updated_at THEN
        RAISE EXCEPTION 'classification run time cannot move backwards'
          USING ERRCODE = '23514';
      END IF;
      IF OLD.started_at IS NOT NULL
        AND NEW.started_at IS DISTINCT FROM OLD.started_at
      THEN
        RAISE EXCEPTION 'classification run started_at is immutable once set'
          USING ERRCODE = '55000';
      END IF;
      IF NEW.analysis_run_id IS DISTINCT FROM OLD.analysis_run_id
        OR NEW.detection_run_id IS DISTINCT FROM OLD.detection_run_id
        OR NEW.classification_run_code
          IS DISTINCT FROM OLD.classification_run_code
        OR NEW.production_model_id IS DISTINCT FROM OLD.production_model_id
        OR NEW.stage2_publication_id
          IS DISTINCT FROM OLD.stage2_publication_id
        OR NEW.model_registry_id IS DISTINCT FROM OLD.model_registry_id
        OR NEW.model_name IS DISTINCT FROM OLD.model_name
        OR NEW.model_version IS DISTINCT FROM OLD.model_version
        OR NEW.model_snapshot IS DISTINCT FROM OLD.model_snapshot
        OR NEW.input_manifest_sha256
          IS DISTINCT FROM OLD.input_manifest_sha256
        OR NEW.input_count IS DISTINCT FROM OLD.input_count
        OR NEW.eligible_count IS DISTINCT FROM OLD.eligible_count
        OR NEW.excluded_count IS DISTINCT FROM OLD.excluded_count
        OR NEW.requested_by IS DISTINCT FROM OLD.requested_by
        OR NEW.retry_of_run_id IS DISTINCT FROM OLD.retry_of_run_id
        OR NEW.created_at IS DISTINCT FROM OLD.created_at
      THEN
        RAISE EXCEPTION
          'cell_classification_runs identity, model and inputs are immutable'
          USING ERRCODE = '55000';
      END IF;
      RETURN NEW;
    END;
    $function$;

CREATE OR REPLACE FUNCTION public.protect_cell_detection_run_identity()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    BEGIN
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'cell_detection_runs cannot be deleted'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status IN ('completed','completed_with_warnings','failed') THEN
        RAISE EXCEPTION 'terminal cell_detection_runs are immutable'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status = 'created' AND NEW.status NOT IN ('processing','failed') THEN
        RAISE EXCEPTION 'invalid cell detection run transition'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status = 'processing'
        AND NEW.status NOT IN (
          'processing','completed','completed_with_warnings','failed'
        )
      THEN
        RAISE EXCEPTION 'invalid cell detection run transition'
          USING ERRCODE = '55000';
      END IF;
      IF NEW.analysis_run_id IS DISTINCT FROM OLD.analysis_run_id
        OR NEW.detection_run_code IS DISTINCT FROM OLD.detection_run_code
        OR NEW.detector_key IS DISTINCT FROM OLD.detector_key
        OR NEW.detector_version IS DISTINCT FROM OLD.detector_version
        OR NEW.algorithm_version IS DISTINCT FROM OLD.algorithm_version
        OR NEW.profile_snapshot IS DISTINCT FROM OLD.profile_snapshot
        OR NEW.input_manifest_sha256 IS DISTINCT FROM OLD.input_manifest_sha256
        OR NEW.image_count IS DISTINCT FROM OLD.image_count
        OR NEW.requested_by IS DISTINCT FROM OLD.requested_by
        OR NEW.created_at IS DISTINCT FROM OLD.created_at
      THEN
        RAISE EXCEPTION 'cell_detection_runs identity and profile are immutable'
          USING ERRCODE = '55000';
      END IF;
      RETURN NEW;
    END;
    $function$;

CREATE OR REPLACE FUNCTION public.protect_cell_explanation()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    BEGIN
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'cell_explanations cannot be deleted'
          USING ERRCODE = '55000';
      END IF;
      IF NEW.cell_prediction_id IS DISTINCT FROM OLD.cell_prediction_id
        OR NEW.method IS DISTINCT FROM OLD.method
        OR NEW.method_version IS DISTINCT FROM OLD.method_version
        OR NEW.parameters_json IS DISTINCT FROM OLD.parameters_json
        OR NEW.created_at IS DISTINCT FROM OLD.created_at
      THEN
        RAISE EXCEPTION 'cell explanation identity and parameters are immutable'
          USING ERRCODE = '55000';
      END IF;
      IF OLD.status IN ('generated','unsupported') THEN
        RAISE EXCEPTION 'terminal cell explanations are immutable'
          USING ERRCODE = '55000';
      END IF;
      IF NOT (
        (OLD.status = 'not_requested' AND NEW.status = 'pending')
        OR
        (
          OLD.status = 'pending'
          AND NEW.status IN ('generated','failed','unsupported')
        )
        OR
        (OLD.status = 'failed' AND NEW.status = 'pending')
      ) THEN
        RAISE EXCEPTION 'invalid cell explanation transition'
          USING ERRCODE = '55000';
      END IF;
      RETURN NEW;
    END;
    $function$;

CREATE OR REPLACE FUNCTION public.protect_deployed_model_version_payload()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF TG_OP = 'UPDATE'
       AND ROW(
           NEW.model_version_id,
           NEW.checkpoint_artifact_id,
           NEW.threshold_calibration_id,
           NEW.deployment_name,
           NEW.environment,
           NEW.alias,
           NEW.artifact_sha256,
           NEW.artifact_size_bytes,
           NEW.threshold_value,
           NEW.threshold_profile_snapshot,
           NEW.preprocessing_profile_snapshot,
           NEW.image_quality_policy_snapshot,
           NEW.label_mapping_snapshot,
           NEW.positive_label,
           NEW.score_name,
           NEW.supersedes_deployment_id,
           NEW.rollback_of_deployment_id,
           NEW.created_at
       ) IS DISTINCT FROM ROW(
           OLD.model_version_id,
           OLD.checkpoint_artifact_id,
           OLD.threshold_calibration_id,
           OLD.deployment_name,
           OLD.environment,
           OLD.alias,
           OLD.artifact_sha256,
           OLD.artifact_size_bytes,
           OLD.threshold_value,
           OLD.threshold_profile_snapshot,
           OLD.preprocessing_profile_snapshot,
           OLD.image_quality_policy_snapshot,
           OLD.label_mapping_snapshot,
           OLD.positive_label,
           OLD.score_name,
           OLD.supersedes_deployment_id,
           OLD.rollback_of_deployment_id,
           OLD.created_at
       ) THEN
        RAISE EXCEPTION
            'El payload de deployed_model_versions es inmutable; cree una nueva revisión (%)',
            OLD.id
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION public.protect_frozen_dataset_assignment_updates()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        DECLARE old_status TEXT; new_status TEXT;
        BEGIN
          SELECT status INTO old_status
          FROM dataset_versions WHERE id = OLD.dataset_version_id;
          SELECT status INTO new_status
          FROM dataset_versions WHERE id = NEW.dataset_version_id;
          IF old_status = 'FROZEN' OR new_status = 'FROZEN' THEN
            RAISE EXCEPTION 'assignments of a FROZEN dataset version are immutable'
              USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END;
        $function$;

CREATE OR REPLACE FUNCTION public.protect_frozen_dataset_assignments()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        DECLARE version_id UUID; version_status TEXT;
        BEGIN
          version_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.dataset_version_id ELSE NEW.dataset_version_id END;
          SELECT status INTO version_status FROM dataset_versions WHERE id = version_id;
          IF version_status = 'FROZEN' THEN
            RAISE EXCEPTION 'assignments of a FROZEN dataset version are immutable'
              USING ERRCODE = '23514';
          END IF;
          RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END;
        $function$;

CREATE OR REPLACE FUNCTION public.protect_frozen_dataset_version_sources()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        DECLARE old_status TEXT; new_status TEXT;
        BEGIN
          IF TG_OP <> 'INSERT' THEN
            SELECT status INTO old_status FROM dataset_versions WHERE id = OLD.dataset_version_id;
          END IF;
          IF TG_OP <> 'DELETE' THEN
            SELECT status INTO new_status FROM dataset_versions WHERE id = NEW.dataset_version_id;
          END IF;
          IF old_status = 'FROZEN' OR new_status = 'FROZEN' THEN
            RAISE EXCEPTION 'source composition of a FROZEN dataset version is immutable'
              USING ERRCODE = '23514';
          END IF;
          RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END;
        $function$;

CREATE OR REPLACE FUNCTION public.protect_governed_artifact_identity()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM model_versions
        WHERE checkpoint_artifact_id = OLD.id
    )
       AND ROW(
           NEW.run_id,
           NEW.path,
           NEW.checksum,
           NEW.file_size_bytes
       ) IS DISTINCT FROM ROW(
           OLD.run_id,
           OLD.path,
           OLD.checksum,
           OLD.file_size_bytes
       ) THEN
        RAISE EXCEPTION
            'No se puede mutar path/checksum/tamaño de un artifact ligado a model_version (%)',
            OLD.id
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION public.protect_validation_annotation()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    BEGIN
      IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'scientific validation annotations cannot be deleted'
          USING ERRCODE='55000';
      END IF;
      IF OLD.validation_session_id IS DISTINCT FROM NEW.validation_session_id
        OR OLD.target_type IS DISTINCT FROM NEW.target_type
        OR OLD.cell_detection_id IS DISTINCT FROM NEW.cell_detection_id
        OR OLD.analysis_run_id IS DISTINCT FROM NEW.analysis_run_id
        OR OLD.sample_id IS DISTINCT FROM NEW.sample_id
        OR OLD.created_by IS DISTINCT FROM NEW.created_by
        OR OLD.created_at IS DISTINCT FROM NEW.created_at THEN
        RAISE EXCEPTION 'scientific validation annotation identity is immutable'
          USING ERRCODE='55000';
      END IF;
      IF NEW.version <> OLD.version + 1 OR NEW.updated_at <= OLD.updated_at THEN
        RAISE EXCEPTION 'scientific validation annotation version must advance once'
          USING ERRCODE='40001';
      END IF;
      RETURN NEW;
    END $function$;

CREATE OR REPLACE FUNCTION public.protect_validation_snapshot()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    BEGIN
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'scientific validation snapshots cannot be deleted';
      END IF;
      IF OLD.datasource IS DISTINCT FROM NEW.datasource
        OR OLD.protocol_key IS DISTINCT FROM NEW.protocol_key
        OR OLD.protocol_version IS DISTINCT FROM NEW.protocol_version
        OR OLD.matching_iou_threshold IS DISTINCT FROM NEW.matching_iou_threshold
        OR OLD.initial_snapshot IS DISTINCT FROM NEW.initial_snapshot
        OR OLD.snapshot_sha256 IS DISTINCT FROM NEW.snapshot_sha256
        OR OLD.created_by IS DISTINCT FROM NEW.created_by
        OR OLD.created_at IS DISTINCT FROM NEW.created_at THEN
        RAISE EXCEPTION 'scientific validation snapshot identity is immutable';
      END IF;
      RETURN NEW;
    END $function$;

CREATE OR REPLACE FUNCTION public.reject_cell_analysis_row_mutation()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    BEGIN
      RAISE EXCEPTION 'cell analysis result and review rows are append-only'
        USING ERRCODE = '55000';
    END;
    $function$;

CREATE OR REPLACE FUNCTION public.reject_cell_classification_row_mutation()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    BEGIN
      RAISE EXCEPTION
        'cell classification inputs, predictions, summaries, events and reviews are append-only'
        USING ERRCODE = '55000';
    END;
    $function$;

CREATE OR REPLACE FUNCTION public.train_record_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
DECLARE s record;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'TRAIN_RECORD_IMMUTABLE'; END IF;
 SELECT * INTO s FROM train_execution_sessions WHERE run_id=NEW.run_id FOR UPDATE;
 IF s.state IS DISTINCT FROM 'active' OR s.owner::text IS DISTINCT FROM current_setting('capstone.train_owner',true)
 THEN RAISE EXCEPTION 'TRAIN_OWNER_FENCED'; END IF;
 RETURN NEW;
END $function$;

CREATE OR REPLACE FUNCTION public.train_revision_binding_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM campaign_attempts a JOIN campaign_members m ON m.id=a.member_id
 JOIN train_execution_sessions s ON s.attempt_id=a.id JOIN campaign_technical_revisions v ON v.id=NEW.revision_id
 WHERE a.id=NEW.attempt_id AND m.campaign_id=NEW.campaign_id AND v.campaign_id=NEW.campaign_id
 AND s.environment IS NOT DISTINCT FROM v.payload->'environment')
 THEN RAISE EXCEPTION 'TRAIN_REVISION_BINDING_INVALID'; END IF;
 RETURN NEW;
END $function$;

CREATE OR REPLACE FUNCTION public.train_session_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'TRAIN_HISTORY_IMMUTABLE'; END IF;
 IF NEW.run_id<>OLD.run_id OR NEW.owner<>OLD.owner OR NEW.attempt_id IS DISTINCT FROM OLD.attempt_id
 OR NEW.configuration IS DISTINCT FROM OLD.configuration OR NEW.dataset IS DISTINCT FROM OLD.dataset
 OR NEW.environment IS DISTINCT FROM OLD.environment OR NEW.artifact_root<>OLD.artifact_root
 THEN RAISE EXCEPTION 'TRAIN_IDENTITY_IMMUTABLE'; END IF;
 IF OLD.state IN ('verified','failed','interrupted') OR OLD.owner::text IS DISTINCT FROM current_setting('capstone.train_owner',true)
 THEN RAISE EXCEPTION 'TRAIN_OWNER_FENCED'; END IF;
 IF NOT ((OLD.state='active' AND NEW.state IN ('active','completed','failed','interrupted')) OR (OLD.state='completed' AND NEW.state='verified'))
 THEN RAISE EXCEPTION 'TRAIN_TRANSITION_INVALID'; END IF;
 IF NEW.state='verified' AND (
   NEW.verification->>'status' IS DISTINCT FROM 'verified'
   OR coalesce(NEW.completion->>'records_hash','') !~ '^[a-f0-9]{64}$'
   OR (NEW.completion->>'epochs')::integer IS DISTINCT FROM (SELECT count(*)::integer FROM train_execution_records WHERE run_id=NEW.run_id AND kind='epoch')
   OR NEW.completion->>'records_hash' IS DISTINCT FROM NEW.verification->>'records_hash'
   OR NOT EXISTS(SELECT 1 FROM train_execution_records WHERE run_id=NEW.run_id AND kind='epoch')
   OR NOT EXISTS(SELECT 1 FROM train_execution_records WHERE run_id=NEW.run_id AND kind='artifact')
 ) THEN RAISE EXCEPTION 'TRAIN_VERIFICATION_INCOMPLETE'; END IF;
 RETURN NEW;
END $function$;

CREATE FUNCTION public.v2_binary_metric_guard() RETURNS trigger LANGUAGE plpgsql
 SET search_path = public, pg_catalog AS $$
DECLARE e public.evaluations%ROWTYPE;
BEGIN
 SELECT * INTO STRICT e FROM public.evaluations WHERE id=NEW.evaluation_id;
 IF NEW.run_id IS DISTINCT FROM e.run_id THEN RAISE EXCEPTION 'METRIC_RUN_MISMATCH'; END IF;
 IF e.subject_kind='single' THEN
 SELECT r.model_id,m.name INTO NEW.model_id,NEW.model_name FROM public.runs r JOIN public.models m ON m.id=r.model_id WHERE r.id=e.training_run_id;
 ELSE NEW.model_id:=NULL; NEW.model_name:='ensemble'; END IF;
 NEW.split_name:=e.split; NEW.threshold_used:=e.threshold_used; NEW.threshold_source:=e.threshold_source;
 NEW.recall_parasitized:=NEW.tp::numeric/nullif(NEW.tp::numeric+NEW.fn,0);
 NEW.sensitivity_parasitized:=NEW.recall_parasitized;
 NEW.specificity:=NEW.tn::numeric/nullif(NEW.tn::numeric+NEW.fp,0);
 NEW.precision_parasitized:=NEW.tp::numeric/nullif(NEW.tp::numeric+NEW.fp,0);
 NEW.f1_parasitized:=2*NEW.tp::numeric/nullif(2*NEW.tp::numeric+NEW.fp+NEW.fn,0);
 NEW.f2_parasitized:=5*NEW.tp::numeric/nullif(5*NEW.tp::numeric+NEW.fp+4*NEW.fn::numeric,0);
 NEW.balanced_accuracy:=(NEW.recall_parasitized+NEW.specificity)/2;
 NEW.accuracy:=(NEW.tp::numeric+NEW.tn)/nullif(NEW.tp::numeric+NEW.tn+NEW.fp+NEW.fn,0);
 NEW.confusion_matrix:=jsonb_build_array(jsonb_build_array(NEW.tn,NEW.fp),jsonb_build_array(NEW.fn,NEW.tp));
 IF NEW.tp::numeric+NEW.fn=0 OR NEW.tn::numeric+NEW.fp=0 THEN
   IF NEW.roc_auc_parasitized IS NOT NULL OR NEW.pr_auc_parasitized IS NOT NULL THEN RAISE EXCEPTION 'SINGLE_CLASS_AUC'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.v2_calibration_pair_guard() RETURNS trigger LANGUAGE plpgsql
 SET search_path = public, pg_catalog AS $$
DECLARE d public.evaluations%ROWTYPE; s public.evaluations%ROWTYPE;
BEGIN
 IF NOT EXISTS (SELECT 1 FROM public.run_configurations rc WHERE rc.run_id=NEW.run_id AND rc.clinical_target_recall=NEW.target_recall) THEN RAISE EXCEPTION 'CALIBRATION_CONFIGURATION_TARGET_MISMATCH'; END IF;
 SELECT * INTO STRICT d FROM public.evaluations WHERE id=NEW.default_evaluation_id;
 SELECT * INTO STRICT s FROM public.evaluations WHERE id=NEW.selected_evaluation_id;
 IF d.id=s.id OR d.split<>'val' OR s.split<>'val'
 OR d.training_run_id IS DISTINCT FROM NEW.run_id OR s.training_run_id IS DISTINCT FROM NEW.run_id
 OR d.dataset_version_id IS DISTINCT FROM s.dataset_version_id OR d.population_hash IS DISTINCT FROM s.population_hash
 OR d.checkpoint_artifact_id IS DISTINCT FROM s.checkpoint_artifact_id
 OR d.threshold_used<>0.5 OR s.threshold_used IS DISTINCT FROM NEW.threshold_selected
 OR d.evaluation_role<>'calibration_default' OR s.evaluation_role<>'calibration_selected' THEN RAISE EXCEPTION 'CALIBRATION_PAIR_INVALID'; END IF;
 RETURN NULL;
END $$;

CREATE FUNCTION public.v2_configuration_guard() RETURNS trigger LANGUAGE plpgsql
 SET search_path = public, pg_catalog AS $$
DECLARE r public.runs%ROWTYPE; j jsonb; cfg jsonb;
BEGIN
 SELECT * INTO STRICT r FROM public.runs WHERE id=NEW.run_id;
 j:=NEW.canonical_configuration::jsonb;
 cfg:=r.execution_parameters->'model_configuration_e2'->'configuration';
 IF r.run_type<>'training' OR r.random_seed IS DISTINCT FROM NEW.random_seed
 OR cfg->'resolved' IS DISTINCT FROM j OR cfg->>'model_id' IS DISTINCT FROM NEW.architecture
 OR cfg->>'adapter_version' IS DISTINCT FROM NEW.adapter_version
 OR j#>>'{optimizer,name}' IS DISTINCT FROM NEW.optimizer
 OR (j#>>'{optimizer,parameters,learning_rate}')::float8 IS DISTINCT FROM NEW.learning_rate
 OR (j#>>'{optimizer,fine_tune_learning_rate}')::float8 IS DISTINCT FROM NEW.fine_tune_learning_rate
 OR (j#>>'{execution,batch_size}')::integer IS DISTINCT FROM NEW.batch_size
 OR (j#>>'{execution,seed}')::bigint IS DISTINCT FROM NEW.random_seed
 OR (j#>>'{execution,max_epochs}')::integer IS DISTINCT FROM NEW.max_epochs
 OR (j#>>'{execution,fine_tune_epochs}')::integer IS DISTINCT FROM NEW.fine_tune_epochs
 OR (j#>>'{model,dropout}')::float8 IS DISTINCT FROM NEW.dropout
 OR (j#>>'{model,l2}')::float8 IS DISTINCT FROM NEW.l2
 OR j#>>'{model,preprocessing}' IS DISTINCT FROM NEW.normalization
 OR j#>>'{recipe,loss}' IS DISTINCT FROM NEW.loss_function
 OR (j#>>'{execution,calibrate_threshold}')::boolean IS DISTINCT FROM NEW.calibration_enabled
 OR (j#>>'{execution,target_recall}')::numeric IS DISTINCT FROM NEW.clinical_target_recall
 THEN RAISE EXCEPTION 'FROZEN_CONFIGURATION_MISMATCH'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.v2_evaluation_complete() RETURNS trigger LANGUAGE plpgsql
 SET search_path = public, pg_catalog AS $$
DECLARE e public.evaluations%ROWTYPE; n integer; w numeric; r public.runs%ROWTYPE; ai public.assessment_identities%ROWTYPE; ast text;
BEGIN
 IF TG_TABLE_NAME='evaluations' THEN e:=NEW; ELSE SELECT * INTO STRICT e FROM public.evaluations WHERE id=NEW.evaluation_id; END IF;
 SELECT * INTO STRICT r FROM public.runs WHERE id=e.training_run_id;
 IF r.run_type<>'training' OR (e.split<>'external' AND r.dataset_version_id IS DISTINCT FROM e.dataset_version_id) THEN RAISE EXCEPTION 'EVALUATION_TRAIN_DATASET_MISMATCH'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.run_clinical_metrics WHERE evaluation_id=e.id) THEN RAISE EXCEPTION 'EVALUATION_METRICS_MISSING'; END IF;
 IF e.checkpoint_artifact_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.artifacts WHERE id=e.checkpoint_artifact_id AND run_id=e.training_run_id) THEN RAISE EXCEPTION 'CHECKPOINT_TRAIN_MISMATCH'; END IF;
 IF e.model_version_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.model_versions WHERE id=e.model_version_id AND checkpoint_artifact_id=e.checkpoint_artifact_id) THEN RAISE EXCEPTION 'CHECKPOINT_VERSION_MISMATCH'; END IF;
 IF e.threshold_source='validation_calibration' AND NOT EXISTS(SELECT 1 FROM public.run_threshold_calibration WHERE run_threshold_calibration_id=e.calibration_id AND calibration_split='val' AND threshold_selected=e.threshold_used AND run_id=e.training_run_id) THEN RAISE EXCEPTION 'CALIBRATION_LINEAGE_MISMATCH'; END IF;
 IF e.source_kind='e10' AND NOT EXISTS(SELECT 1 FROM public.train_execution_records WHERE run_id=e.run_id AND event_id=e.source_event_id AND kind=e.event_kind AND phase=e.event_phase AND record_key=e.event_key) THEN RAISE EXCEPTION 'EVENT_LINEAGE_MISMATCH'; END IF;
 IF e.source_kind='assessment' THEN
 SELECT i.* INTO ai FROM public.assessment_attempts a JOIN public.assessment_identities i ON i.id=a.identity_id WHERE a.id=e.source_assessment_attempt_id;
 SELECT state INTO ast FROM public.assessment_attempts WHERE id=e.source_assessment_attempt_id;
 IF ai.id IS NULL OR ast IS DISTINCT FROM 'verified' OR ai.kind<>'evaluate' OR ai.training_run_id IS DISTINCT FROM e.training_run_id OR ai.identity->>'split' IS DISTINCT FROM e.split OR ai.identity->>'purpose' IS DISTINCT FROM e.purpose THEN RAISE EXCEPTION 'ASSESSMENT_PROJECTION_MISMATCH'; END IF;
 IF e.split='test' AND NOT EXISTS(SELECT 1 FROM public.assessment_final_locks l WHERE l.identity_hash=ai.identity_hash AND l.evidence->'candidate'=ai.identity->'model' AND l.evidence->'decision'=ai.identity->'decision') THEN RAISE EXCEPTION 'TEST_FINAL_LOCK_REQUIRED'; END IF;
 END IF;
 SELECT count(*),sum(weight) INTO n,w FROM public.evaluation_ensemble_members WHERE evaluation_id=e.id;
 IF (e.subject_kind='single' AND n<>0) OR (e.subject_kind='ensemble' AND (n<2 OR w IS DISTINCT FROM 1::numeric)) THEN RAISE EXCEPTION 'ENSEMBLE_INVALID'; END IF;
 IF EXISTS(SELECT 1 FROM public.evaluation_ensemble_members m JOIN public.model_versions v ON v.id=m.model_version_id JOIN public.runs tr ON tr.id=v.training_run_id WHERE m.evaluation_id=e.id AND (v.checkpoint_artifact_id IS DISTINCT FROM m.checkpoint_artifact_id OR tr.dataset_version_id IS DISTINCT FROM r.dataset_version_id)) THEN RAISE EXCEPTION 'ENSEMBLE_LINEAGE_MISMATCH'; END IF;
 RETURN NULL;
END $$;

CREATE FUNCTION public.v2_immutable() RETURNS trigger LANGUAGE plpgsql
 SET search_path = public, pg_catalog AS $$ BEGIN RAISE EXCEPTION 'V2_SCIENTIFIC_EVIDENCE_IMMUTABLE'; END $$;

CREATE FUNCTION public.v2_run_configuration_required() RETURNS trigger LANGUAGE plpgsql
 SET search_path = public, pg_catalog AS $$ BEGIN
 IF NEW.run_type='training' AND NOT EXISTS(SELECT 1 FROM public.run_configurations WHERE run_id=NEW.id) THEN RAISE EXCEPTION 'TRAIN_CONFIGURATION_REQUIRED'; END IF;
 RETURN NULL;
END $$;

CREATE FUNCTION public.v2_xai_artifact_guard() RETURNS trigger LANGUAGE plpgsql
 SET search_path = public, pg_catalog AS $$ BEGIN
 IF TG_OP='DELETE' OR (to_jsonb(NEW)-'availability') IS DISTINCT FROM (to_jsonb(OLD)-'availability') THEN RAISE EXCEPTION 'XAI_ARTIFACT_IMMUTABLE'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.v2_xai_artifact_source_guard() RETURNS trigger LANGUAGE plpgsql
 SET search_path = public, pg_catalog AS $$
DECLARE e public.xai_evidence%ROWTYPE; p jsonb;
BEGIN
 SELECT * INTO STRICT e FROM public.xai_evidence WHERE id=NEW.evidence_id;
 IF NEW.artifact_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.artifacts a WHERE a.id=NEW.artifact_id AND a.checksum=NEW.sha256 AND a.file_size_bytes=NEW.byte_size AND (a.path=NEW.storage_uri OR a.artifact_uri=NEW.storage_uri)) THEN RAISE EXCEPTION 'XAI_ARTIFACT_REFERENCE_MISMATCH'; END IF;
 IF NEW.assessment_artifact_id IS NOT NULL THEN
 SELECT a.payload INTO p FROM public.assessment_artifacts a WHERE a.artifact_id=NEW.assessment_artifact_id AND a.attempt_id=e.assessment_attempt_id AND a.sample_id=e.assessment_sample_id;
 IF p IS NULL OR p->>'sha256' IS DISTINCT FROM NEW.sha256 OR (p->>'bytes')::bigint IS DISTINCT FROM NEW.byte_size OR p->>'path' IS DISTINCT FROM NEW.storage_uri THEN RAISE EXCEPTION 'XAI_ASSESSMENT_ARTIFACT_MISMATCH'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION public.v2_xai_lineage_guard() RETURNS trigger LANGUAGE plpgsql
 SET search_path = public, pg_catalog AS $$
DECLARE v public.model_versions%ROWTYPE; method_key text; training_id uuid;
BEGIN
 SELECT method INTO STRICT method_key FROM public.xai_method_configurations WHERE id=NEW.method_configuration_id;
 IF method_key='shap' AND (NEW.background_manifest_uri IS NULL OR NEW.background_manifest_sha256 IS NULL) THEN RAISE EXCEPTION 'XAI_SHAP_BACKGROUND_REQUIRED'; END IF;
 IF NEW.model_version_id IS NOT NULL THEN
 SELECT * INTO STRICT v FROM public.model_versions WHERE id=NEW.model_version_id;
 IF v.checkpoint_artifact_id IS DISTINCT FROM NEW.checkpoint_artifact_id OR v.artifact_sha256 IS DISTINCT FROM NEW.checkpoint_sha256 THEN RAISE EXCEPTION 'XAI_MODEL_CHECKPOINT_MISMATCH'; END IF;
 training_id:=v.training_run_id;
 ELSE
 SELECT a.run_id INTO training_id FROM public.artifacts a JOIN public.runs r ON r.id=a.run_id WHERE a.id=NEW.checkpoint_artifact_id AND a.checksum=NEW.checkpoint_sha256 AND r.run_type='training';
 IF training_id IS NULL OR training_id IS DISTINCT FROM NEW.run_id THEN RAISE EXCEPTION 'XAI_PROVISIONAL_CHECKPOINT_MISMATCH'; END IF;
 END IF;
 IF NEW.ml_explanation_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.explainability_results x WHERE x.id=NEW.ml_explanation_id AND x.run_id IS NOT DISTINCT FROM NEW.run_id AND x.prediction_id IS NOT DISTINCT FROM NEW.prediction_id AND lower(x.method)=method_key) THEN RAISE EXCEPTION 'XAI_ML_LINEAGE_MISMATCH'; END IF;
 IF NEW.cell_explanation_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.cell_explanations x WHERE x.id=NEW.cell_explanation_id AND x.cell_prediction_id=NEW.cell_prediction_id AND lower(x.method)=method_key) THEN RAISE EXCEPTION 'XAI_CELL_LINEAGE_MISMATCH'; END IF;
 IF NEW.prediction_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.predictions p WHERE p.id=NEW.prediction_id AND coalesce(p.model_version_id,p.classifier_model_version_id)=NEW.model_version_id) THEN RAISE EXCEPTION 'XAI_PREDICTION_MODEL_MISMATCH'; END IF;
 IF NEW.dataset_source_record_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.dataset_source_records d WHERE d.id=NEW.dataset_source_record_id AND d.source_file_sha256=NEW.input_sha256) THEN RAISE EXCEPTION 'XAI_SOURCE_IMAGE_MISMATCH'; END IF;
 IF NEW.assessment_attempt_id IS NOT NULL AND NEW.assessment_sample_id IS DISTINCT FROM NEW.dataset_source_record_id THEN RAISE EXCEPTION 'XAI_ASSESSMENT_SAMPLE_MISMATCH'; END IF;
 IF NEW.assessment_attempt_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.assessment_attempts aa JOIN public.assessment_identities ai ON ai.id=aa.identity_id WHERE aa.id=NEW.assessment_attempt_id AND ai.kind='explain' AND ai.training_run_id=training_id AND ai.identity#>>'{explanation,method}'=method_key AND (ai.identity#>>'{explanation,class}')::smallint=NEW.target_class AND ai.identity#>>'{model,sha256}'=NEW.checkpoint_sha256) THEN RAISE EXCEPTION 'XAI_ASSESSMENT_MODEL_MISMATCH'; END IF;
 IF NEW.cell_prediction_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.cell_predictions p JOIN public.cell_classification_inputs i ON i.id=p.classification_input_id JOIN public.cell_classification_runs cr ON cr.id=p.classification_run_id WHERE p.id=NEW.cell_prediction_id AND cr.model_registry_id=NEW.model_version_id AND i.microscopy_image_id=NEW.microscopy_image_id AND i.crop_sha256=NEW.input_sha256) THEN RAISE EXCEPTION 'XAI_CROP_MISMATCH'; END IF;
 IF NEW.evaluation_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.evaluations e WHERE e.id=NEW.evaluation_id AND (((e.model_version_id=NEW.model_version_id OR (e.model_version_id IS NULL AND e.training_run_id=training_id)) AND e.checkpoint_artifact_id=NEW.checkpoint_artifact_id) OR (e.subject_kind='ensemble' AND EXISTS(SELECT 1 FROM public.evaluation_ensemble_members em WHERE em.evaluation_id=e.id AND em.model_version_id=NEW.model_version_id AND em.checkpoint_artifact_id=NEW.checkpoint_artifact_id)))) THEN RAISE EXCEPTION 'XAI_EVALUATION_MISMATCH'; END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.validate_cell_classification_input_snapshot()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    DECLARE
      source_cell_index INTEGER;
      source_cell_code VARCHAR(40);
      source_image_sequence INTEGER;
      source_detector_key VARCHAR(80);
      source_detector_version VARCHAR(40);
      source_algorithm_version VARCHAR(80);
      source_crop_id UUID;
      source_crop_sha256 CHAR(64);
      source_crop_width INTEGER;
      source_crop_height INTEGER;
    BEGIN
      SELECT
        detection.cell_index,
        detection.cell_code,
        image.sequence_number,
        run.detector_key,
        run.detector_version,
        run.algorithm_version,
        crop.id,
        crop.sha256,
        crop.width_px,
        crop.height_px
      INTO
        source_cell_index,
        source_cell_code,
        source_image_sequence,
        source_detector_key,
        source_detector_version,
        source_algorithm_version,
        source_crop_id,
        source_crop_sha256,
        source_crop_width,
        source_crop_height
      FROM cell_detections detection
      JOIN cell_detection_runs run
        ON run.id=detection.detection_run_id
      JOIN microscopy_analysis_run_images image
        ON image.id=detection.analysis_run_image_id
      LEFT JOIN cell_crops crop
        ON crop.cell_detection_id=detection.id
      WHERE detection.id=NEW.cell_detection_id
        AND detection.detection_run_id=NEW.detection_run_id
        AND detection.microscopy_image_id=NEW.microscopy_image_id
      FOR SHARE OF detection,run,image;

      IF source_cell_index IS NULL
        OR NEW.cell_index IS DISTINCT FROM source_cell_index
        OR NEW.cell_code IS DISTINCT FROM source_cell_code
        OR NEW.image_sequence_number IS DISTINCT FROM source_image_sequence
        OR NEW.detector_key IS DISTINCT FROM source_detector_key
        OR NEW.detector_version IS DISTINCT FROM source_detector_version
        OR NEW.detector_algorithm_version
          IS DISTINCT FROM source_algorithm_version
        OR NEW.crop_id IS DISTINCT FROM source_crop_id
        OR NEW.crop_sha256 IS DISTINCT FROM source_crop_sha256
        OR NEW.crop_width_px IS DISTINCT FROM source_crop_width
        OR NEW.crop_height_px IS DISTINCT FROM source_crop_height
      THEN
        RAISE EXCEPTION
          'classification input does not match immutable detection/crop metadata'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $function$;

CREATE OR REPLACE FUNCTION public.validate_cell_classification_insert_state()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    DECLARE
      run_status VARCHAR(30);
      declared_count INTEGER;
      existing_count INTEGER;
    BEGIN
      IF TG_TABLE_NAME = 'cell_classification_inputs' THEN
        SELECT status,input_count
        INTO run_status,declared_count
        FROM cell_classification_runs
        WHERE id=NEW.classification_run_id
        FOR SHARE;
        IF run_status IS DISTINCT FROM 'created' THEN
          RAISE EXCEPTION
            'cell classification inputs require a created run'
            USING ERRCODE = '55000';
        END IF;
        SELECT count(*)
        INTO existing_count
        FROM cell_classification_inputs
        WHERE classification_run_id=NEW.classification_run_id;
      ELSIF TG_TABLE_NAME = 'cell_predictions' THEN
        SELECT status,eligible_count
        INTO run_status,declared_count
        FROM cell_classification_runs
        WHERE id=NEW.classification_run_id
        FOR SHARE;
        IF run_status IS DISTINCT FROM 'processing' THEN
          RAISE EXCEPTION
            'cell predictions require a processing run'
            USING ERRCODE = '55000';
        END IF;
        SELECT count(*)
        INTO existing_count
        FROM cell_predictions
        WHERE classification_run_id=NEW.classification_run_id;
      ELSIF TG_TABLE_NAME = 'smear_analysis_summaries' THEN
        SELECT status,1
        INTO run_status,declared_count
        FROM cell_classification_runs
        WHERE id=NEW.classification_run_id
        FOR SHARE;
        IF run_status IS DISTINCT FROM 'processing' THEN
          RAISE EXCEPTION
            'smear analysis summary requires a processing run'
            USING ERRCODE = '55000';
        END IF;
        SELECT count(*)
        INTO existing_count
        FROM smear_analysis_summaries
        WHERE classification_run_id=NEW.classification_run_id;
      ELSE
        RAISE EXCEPTION 'unsupported guarded classification table'
          USING ERRCODE = '55000';
      END IF;

      IF run_status IS NULL THEN
        RAISE EXCEPTION 'classification run does not exist'
          USING ERRCODE = '23503';
      END IF;
      IF existing_count >= declared_count THEN
        RAISE EXCEPTION
          'classification child rows exceed the frozen run count'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $function$;

CREATE OR REPLACE FUNCTION public.validate_cell_classification_review()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    DECLARE
      automatic_status VARCHAR(20);
      automatic_label VARCHAR(20);
    BEGIN
      SELECT prediction_status,predicted_label
      INTO automatic_status,automatic_label
      FROM cell_predictions
      WHERE id=NEW.cell_prediction_id
      FOR SHARE;
      IF automatic_status IS NULL THEN
        RAISE EXCEPTION 'cell prediction does not exist'
          USING ERRCODE = '23503';
      END IF;
      IF automatic_status <> 'completed' THEN
        RAISE EXCEPTION
          'failed cell predictions cannot be reviewed'
          USING ERRCODE = '23514';
      END IF;
      IF NEW.decision = 'confirmed'
        AND NEW.reviewed_label IS NOT NULL
        AND NEW.reviewed_label IS DISTINCT FROM automatic_label
      THEN
        RAISE EXCEPTION
          'confirmed label must match the immutable automatic prediction'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $function$;

CREATE OR REPLACE FUNCTION public.validate_cell_classification_run_snapshot()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    DECLARE
      snapshot JSONB := NEW.model_snapshot;
      published_threshold DOUBLE PRECISION;
      published_review_margin DOUBLE PRECISION;
    BEGIN
      IF jsonb_typeof(snapshot) IS DISTINCT FROM 'object'
        OR snapshot->>'schema_version' IS DISTINCT FROM '1'
        OR snapshot->>'production_model_id'
          IS DISTINCT FROM NEW.production_model_id::text
        OR snapshot->>'stage2_publication_id'
          IS DISTINCT FROM NEW.stage2_publication_id::text
        OR snapshot->>'model_registry_id'
          IS DISTINCT FROM NEW.model_registry_id::text
        OR snapshot->>'model_name' IS DISTINCT FROM NEW.model_name
        OR snapshot->>'model_version' IS DISTINCT FROM NEW.model_version
        OR snapshot->>'positive_label' IS DISTINCT FROM 'parasitized'
        OR snapshot->>'positive_class_index' IS DISTINCT FROM '1'
        OR snapshot->>'production_status' IS DISTINCT FROM 'active'
        OR snapshot->>'checkpoint_sha256' IS NULL
        OR snapshot->>'checkpoint_sha256' !~ '^[0-9a-f]{64}$'
        OR COALESCE(snapshot->>'checkpoint_size_bytes','')
          !~ '^[1-9][0-9]*$'
        OR snapshot->>'loader_version' IS NULL
        OR btrim(snapshot->>'loader_version') = ''
        OR snapshot->>'inference_version' IS NULL
        OR btrim(snapshot->>'inference_version') = ''
        OR snapshot->>'threshold_source' IS NULL
        OR btrim(snapshot->>'threshold_source') = ''
        OR jsonb_typeof(snapshot->'preprocessing') IS DISTINCT FROM 'object'
        OR jsonb_typeof(snapshot->'input_signature') IS DISTINCT FROM 'object'
        OR jsonb_typeof(snapshot->'output_signature') IS DISTINCT FROM 'object'
        OR jsonb_typeof(snapshot->'calibration_metadata')
          IS DISTINCT FROM 'object'
        OR jsonb_typeof(snapshot->'stage2_default') IS DISTINCT FROM 'object'
        OR jsonb_typeof(snapshot->'explainability_policy')
          IS DISTINCT FROM 'object'
        OR jsonb_typeof(snapshot->'label_mapping') IS DISTINCT FROM 'object'
        OR NOT (
          snapshot->'label_mapping' @>
            '{
              "0":"uninfected",
              "1":"parasitized",
              "positive_class": 1,
              "positive_label":"parasitized"
            }'::jsonb
        )
        OR snapshot#>>'{stage2_default,environment}' IS DISTINCT FROM 'stage2'
        OR snapshot#>>'{stage2_default,alias}' IS DISTINCT FROM 'default'
        OR snapshot#>>'{stage2_default,deployment_id}'
          IS DISTINCT FROM NEW.production_model_id::text
        OR snapshot#>>'{explainability_policy,version}'
          IS DISTINCT FROM 'cell-gradcam-manual-v1'
        OR snapshot#>>'{explainability_policy,method}'
          IS DISTINCT FROM 'gradcam'
        OR snapshot#>>'{explainability_policy,scope}'
          IS DISTINCT FROM 'single_cell_on_demand'
        OR snapshot#>>'{explainability_policy,automatic_generation}'
          IS DISTINCT FROM 'false'
        OR snapshot#>>'{explainability_policy,manual_retry_required}'
          IS DISTINCT FROM 'true'
        OR snapshot#>>'{explainability_policy,bulk_generation}'
          IS DISTINCT FROM 'false'
        OR COALESCE(snapshot->>'source_training_run_id','')
          !~ '^[0-9a-f-]{36}$'
        OR COALESCE(snapshot->>'source_evaluation_run_id','')
          !~ '^[0-9a-f-]{36}$'
        OR COALESCE(snapshot->>'checkpoint_artifact_id','')
          !~ '^[0-9a-f-]{36}$'
        OR COALESCE(snapshot->>'batch_size','') !~ '^[1-9][0-9]*$'
        OR COALESCE(snapshot->>'input_width','') !~ '^[1-9][0-9]*$'
        OR COALESCE(snapshot->>'input_height','') !~ '^[1-9][0-9]*$'
        OR COALESCE(snapshot->>'input_channels','') !~ '^[1-9][0-9]*$'
      THEN
        RAISE EXCEPTION
          'model snapshot identity or required contract is invalid'
          USING ERRCODE = '23514';
      END IF;

      IF jsonb_typeof(snapshot->'threshold') IS DISTINCT FROM 'number'
        OR jsonb_typeof(snapshot->'review_margin') IS DISTINCT FROM 'number'
      THEN
        RAISE EXCEPTION
          'model snapshot numeric policy is invalid'
          USING ERRCODE = '23514';
      END IF;
      published_threshold := (snapshot->>'threshold')::DOUBLE PRECISION;
      published_review_margin :=
        (snapshot->>'review_margin')::DOUBLE PRECISION;
      IF published_threshold < 0 OR published_threshold > 1
        OR published_review_margin < 0 OR published_review_margin > 1
      THEN
        RAISE EXCEPTION
          'model snapshot numeric policy is outside allowed bounds'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $function$;

CREATE OR REPLACE FUNCTION public.validate_cell_explanation_contract()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    DECLARE
      prediction_status VARCHAR(20);
      prediction_class SMALLINT;
      prediction_preprocessing JSONB;
      source_analysis_run_id UUID;
      source_classification_run_id UUID;
      source_cell_detection_id UUID;
      source_input_width INTEGER;
      source_input_height INTEGER;
      expected_heatmap_key TEXT;
      expected_overlay_key TEXT;
    BEGIN
      SELECT
        prediction.prediction_status,
        prediction.predicted_class_index,
        prediction.preprocessing_snapshot,
        run.analysis_run_id,
        prediction.classification_run_id,
        prediction.cell_detection_id,
        (run.model_snapshot->>'input_width')::INTEGER,
        (run.model_snapshot->>'input_height')::INTEGER
      INTO
        prediction_status,
        prediction_class,
        prediction_preprocessing,
        source_analysis_run_id,
        source_classification_run_id,
        source_cell_detection_id,
        source_input_width,
        source_input_height
      FROM cell_predictions prediction
      JOIN cell_classification_runs run
        ON run.id=prediction.classification_run_id
      WHERE prediction.id=NEW.cell_prediction_id
      FOR SHARE OF prediction,run;

      IF prediction_status IS DISTINCT FROM 'completed'
        OR NEW.parameters_json->>'method' IS DISTINCT FROM 'gradcam'
        OR NEW.parameters_json->>'method_version'
          IS DISTINCT FROM NEW.method_version
        OR NEW.parameters_json->>'target_class_index'
          IS DISTINCT FROM prediction_class::text
        OR NEW.parameters_json->>'positive_class_index'
          IS DISTINCT FROM '1'
        OR NEW.parameters_json->'preprocessing'
          IS DISTINCT FROM prediction_preprocessing
      THEN
        RAISE EXCEPTION
          'cell explanation does not match the immutable prediction contract'
          USING ERRCODE = '23514';
      END IF;

      IF NEW.status='generated' THEN
        expected_heatmap_key := format(
          'cell-explanations/%s/%s/%s/gradcam_heatmap.png',
          source_analysis_run_id,
          source_classification_run_id,
          source_cell_detection_id
        );
        expected_overlay_key := format(
          'cell-explanations/%s/%s/%s/gradcam_overlay.png',
          source_analysis_run_id,
          source_classification_run_id,
          source_cell_detection_id
        );
        IF NEW.heatmap_storage_key IS DISTINCT FROM expected_heatmap_key
          OR NEW.overlay_storage_key IS DISTINCT FROM expected_overlay_key
          OR NEW.width_px IS DISTINCT FROM source_input_width
          OR NEW.height_px IS DISTINCT FROM source_input_height
        THEN
          RAISE EXCEPTION
            'generated explanation artifact lineage is inconsistent'
            USING ERRCODE = '23514';
        END IF;
      END IF;
      RETURN NEW;
    END;
    $function$;

CREATE OR REPLACE FUNCTION public.validate_cell_prediction_input()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    DECLARE
      input_eligible BOOLEAN;
      run_snapshot JSONB;
      snapshot_threshold DOUBLE PRECISION;
      snapshot_review_margin DOUBLE PRECISION;
    BEGIN
      SELECT input.eligible,run.model_snapshot
      INTO input_eligible,run_snapshot
      FROM cell_classification_inputs input
      JOIN cell_classification_runs run
        ON run.id=input.classification_run_id
      WHERE input.id = NEW.classification_input_id
        AND input.classification_run_id = NEW.classification_run_id
        AND input.cell_detection_id = NEW.cell_detection_id
        AND input.crop_id = NEW.crop_id
      FOR SHARE OF input,run;
      IF input_eligible IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION
          'cell prediction requires an eligible frozen input'
          USING ERRCODE = '23514';
      END IF;
      snapshot_threshold :=
        (run_snapshot->>'threshold')::DOUBLE PRECISION;
      snapshot_review_margin :=
        (run_snapshot->>'review_margin')::DOUBLE PRECISION;
      IF abs(NEW.threshold_used - snapshot_threshold) > 1e-12
        OR NEW.threshold_source
          IS DISTINCT FROM run_snapshot->>'threshold_source'
        OR NEW.preprocessing_snapshot
          IS DISTINCT FROM run_snapshot->'preprocessing'
        OR NEW.positive_label
          IS DISTINCT FROM run_snapshot->>'positive_label'
        OR NEW.positive_class_index::text
          IS DISTINCT FROM run_snapshot->>'positive_class_index'
        OR (
          NEW.prediction_status='completed'
          AND NEW.near_threshold IS DISTINCT FROM
            (NEW.decision_margin <= snapshot_review_margin)
        )
      THEN
        RAISE EXCEPTION
          'cell prediction does not match the frozen model policy'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $function$;

CREATE OR REPLACE FUNCTION public.validate_deployed_model_version()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    version_status TEXT;
    version_sha256 TEXT;
    version_size BIGINT;
    artifact_checksum TEXT;
    artifact_size BIGINT;
    physical_status TEXT;
    calibrated_threshold NUMERIC;
    is_stage2 BOOLEAN;
    is_technical_production BOOLEAN;
BEGIN
    SELECT mv.status,mv.artifact_sha256,mv.artifact_size_bytes,LOWER(a.checksum),
           a.file_size_bytes,a.artifact_status
      INTO version_status,version_sha256,version_size,artifact_checksum,
           artifact_size,physical_status
      FROM model_versions mv
      JOIN artifacts a ON a.id=mv.checkpoint_artifact_id
                      AND a.run_id=mv.training_run_id
     WHERE mv.id=NEW.model_version_id
       AND mv.checkpoint_artifact_id=NEW.checkpoint_artifact_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Deployment sin par version/artifact gobernado: version %, artifact %',
            NEW.model_version_id,NEW.checkpoint_artifact_id USING ERRCODE='23503';
    END IF;

    IF NEW.artifact_size_bytes IS NULL THEN NEW.artifact_size_bytes:=version_size; END IF;
    IF LOWER(NEW.artifact_sha256) IS DISTINCT FROM version_sha256
       OR version_sha256 IS DISTINCT FROM artifact_checksum THEN
        RAISE EXCEPTION 'SHA-256 de deployment, model_version y artifact no coincide'
            USING ERRCODE='23514';
    END IF;
    IF NEW.artifact_size_bytes IS DISTINCT FROM version_size
       OR version_size IS DISTINCT FROM artifact_size THEN
        RAISE EXCEPTION 'Tamaño de deployment, model_version y artifact no coincide'
            USING ERRCODE='23514';
    END IF;

    IF NEW.threshold_calibration_id IS NOT NULL THEN
        SELECT threshold_selected INTO calibrated_threshold
          FROM run_threshold_calibration
         WHERE run_threshold_calibration_id=NEW.threshold_calibration_id
           AND model_version_id=NEW.model_version_id;
        IF calibrated_threshold IS DISTINCT FROM NEW.threshold_value THEN
            RAISE EXCEPTION 'threshold_value (%) no coincide con calibración % (%)',
                NEW.threshold_value,NEW.threshold_calibration_id,calibrated_threshold
                USING ERRCODE='23514';
        END IF;
    END IF;

    IF NEW.status='active' THEN
        is_stage2:=NEW.environment='stage2' AND NEW.alias='default';
        is_technical_production:=NEW.environment='production' AND NEW.alias='champion'
          AND COALESCE(NEW.metadata->>'production_scope','')='stage2_technical';
        IF is_stage2 OR is_technical_production THEN
            IF version_status NOT IN ('candidate','validated','approved','deployed') THEN
                RAISE EXCEPTION 'Model version % no apta para Etapa 2',version_status
                    USING ERRCODE='23514';
            END IF;
            IF COALESCE(NEW.metadata#>>'{stage2,eligible}','false')<>'true'
               OR COALESCE(NEW.metadata#>>'{technical_smoke_test,status}',
                           NEW.metadata#>>'{stage2_smoke_test,status}','')<>'PASS' THEN
                RAISE EXCEPTION 'Etapa 2 exige elegibilidad técnica y smoke PASS'
                    USING ERRCODE='23514';
            END IF;
        ELSIF version_status NOT IN ('approved','deployed') THEN
            RAISE EXCEPTION 'Solo una model_version approved/deployed puede activarse; estado actual %',
                version_status USING ERRCODE='23514';
        END IF;
        IF physical_status IS DISTINCT FROM 'available' THEN
            RAISE EXCEPTION 'El artifact debe estar available para activar; estado actual %',
                physical_status USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION public.validate_image_analysis_job()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    inference_type TEXT;
    deployment_status TEXT;
    deployment_threshold NUMERIC;
BEGIN
    SELECT run_type
    INTO inference_type
    FROM runs
    WHERE id = NEW.inference_run_id;

    IF inference_type IS DISTINCT FROM 'inference' THEN
        RAISE EXCEPTION
            'image_analysis_jobs.inference_run_id debe ser inference; recibió %',
            inference_type
            USING ERRCODE = '23514';
    END IF;

    SELECT status, threshold_value
    INTO deployment_status, deployment_threshold
    FROM deployed_model_versions
    WHERE id = NEW.deployed_model_version_id
      AND model_version_id = NEW.model_version_id;

    IF TG_OP = 'INSERT'
       OR NEW.inference_run_id IS DISTINCT FROM OLD.inference_run_id
       OR NEW.deployed_model_version_id IS DISTINCT FROM OLD.deployed_model_version_id
       OR NEW.model_version_id IS DISTINCT FROM OLD.model_version_id THEN
        IF deployment_status IS DISTINCT FROM 'active' THEN
            RAISE EXCEPTION
                'Un image_analysis_job nuevo exige deployment active; recibió %',
                deployment_status
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.status IN ('running', 'completed') THEN
        IF NEW.threshold_used IS NULL
           OR NEW.threshold_used IS DISTINCT FROM deployment_threshold THEN
            RAISE EXCEPTION
                'threshold_used del job debe coincidir con threshold_value del deployment (%)',
                deployment_threshold
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION public.validate_run_model_deployment()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    inference_type TEXT;
    deployment_status TEXT;
BEGIN
    SELECT run_type INTO inference_type FROM runs WHERE id = NEW.run_id;
    IF inference_type IS DISTINCT FROM 'inference' THEN
        RAISE EXCEPTION
            'run_model_deployments.run_id debe ser inference; recibió %',
            inference_type
            USING ERRCODE = '23514';
    END IF;

    IF TG_OP = 'INSERT'
       OR NEW.run_id IS DISTINCT FROM OLD.run_id
       OR NEW.deployed_model_version_id IS DISTINCT FROM OLD.deployed_model_version_id
       OR NEW.model_version_id IS DISTINCT FROM OLD.model_version_id THEN
        SELECT status
        INTO deployment_status
        FROM deployed_model_versions
        WHERE id = NEW.deployed_model_version_id
          AND model_version_id = NEW.model_version_id;

        IF deployment_status IS DISTINCT FROM 'active' THEN
            RAISE EXCEPTION
                'Un inference run solo puede vincular un deployment active; recibió %',
                deployment_status
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION public.validate_smear_analysis_summary()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    DECLARE
      source_analysis_run_id UUID;
      source_detection_run_id UUID;
      source_eligible_count INTEGER;
      actual_classified_count INTEGER;
      actual_parasitized_count INTEGER;
      actual_uninfected_count INTEGER;
      actual_near_count INTEGER;
      actual_failed_count INTEGER;
      actual_maximum DOUBLE PRECISION;
      actual_mean DOUBLE PRECISION;
      actual_median DOUBLE PRECISION;
      expected_outcome VARCHAR(40);
      actual_per_image JSONB;
      expected_policy CONSTANT JSONB := '{
        "version":"cell-candidate-aggregation-v1",
        "scope":"candidate_cells",
        "suspicious_when_any_parasitized": true,
        "near_threshold_makes_negative_inconclusive": true,
        "partial_failure_makes_negative_inconclusive": true,
        "terminology":"experimental_screening_not_diagnosis"
      }'::jsonb;
    BEGIN
      SELECT analysis_run_id,detection_run_id,eligible_count
      INTO
        source_analysis_run_id,
        source_detection_run_id,
        source_eligible_count
      FROM cell_classification_runs
      WHERE id=NEW.classification_run_id
      FOR SHARE;

      SELECT
        count(*) FILTER (WHERE prediction_status='completed'),
        count(*) FILTER (
          WHERE prediction_status='completed'
            AND predicted_label='parasitized'
        ),
        count(*) FILTER (
          WHERE prediction_status='completed'
            AND predicted_label='uninfected'
        ),
        count(*) FILTER (
          WHERE prediction_status='completed' AND near_threshold
        ),
        count(*) FILTER (WHERE prediction_status='failed'),
        max(probability_parasitized) FILTER (
          WHERE prediction_status='completed'
        ),
        avg(probability_parasitized) FILTER (
          WHERE prediction_status='completed'
        ),
        percentile_cont(0.5) WITHIN GROUP (
          ORDER BY probability_parasitized
        ) FILTER (WHERE prediction_status='completed')
      INTO
        actual_classified_count,
        actual_parasitized_count,
        actual_uninfected_count,
        actual_near_count,
        actual_failed_count,
        actual_maximum,
        actual_mean,
        actual_median
      FROM cell_predictions
      WHERE classification_run_id=NEW.classification_run_id;

      SELECT jsonb_build_object(
        'images',
        COALESCE(
          jsonb_agg(
            jsonb_build_object(
              'microscopy_image_id',per_image.microscopy_image_id::text,
              'image_sequence_number',per_image.image_sequence_number,
              'eligible_cell_count',per_image.eligible_cell_count,
              'classified_cell_count',per_image.classified_cell_count,
              'parasitized_candidate_count',
                per_image.parasitized_candidate_count,
              'uninfected_candidate_count',
                per_image.uninfected_candidate_count,
              'near_threshold_count',per_image.near_threshold_count,
              'failed_prediction_count',per_image.failed_prediction_count
            )
            ORDER BY
              per_image.image_sequence_number,
              per_image.microscopy_image_id
          ),
          '[]'::jsonb
        )
      )
      INTO actual_per_image
      FROM (
        SELECT
          input.microscopy_image_id,
          min(input.image_sequence_number) image_sequence_number,
          count(*)::INTEGER eligible_cell_count,
          count(prediction.id) FILTER (
            WHERE prediction.prediction_status='completed'
          )::INTEGER classified_cell_count,
          count(prediction.id) FILTER (
            WHERE prediction.prediction_status='completed'
              AND prediction.predicted_label='parasitized'
          )::INTEGER parasitized_candidate_count,
          count(prediction.id) FILTER (
            WHERE prediction.prediction_status='completed'
              AND prediction.predicted_label='uninfected'
          )::INTEGER uninfected_candidate_count,
          count(prediction.id) FILTER (
            WHERE prediction.prediction_status='completed'
              AND prediction.near_threshold
          )::INTEGER near_threshold_count,
          count(prediction.id) FILTER (
            WHERE prediction.prediction_status='failed'
          )::INTEGER failed_prediction_count
        FROM cell_classification_inputs input
        LEFT JOIN cell_predictions prediction
          ON prediction.classification_input_id=input.id
        WHERE input.classification_run_id=NEW.classification_run_id
          AND input.eligible
        GROUP BY input.microscopy_image_id
      ) per_image;

      IF actual_parasitized_count > 0 THEN
        expected_outcome := 'suspicious_cells_detected';
      ELSIF source_eligible_count > 0
        AND actual_classified_count=source_eligible_count
        AND actual_failed_count=0
        AND actual_near_count=0
      THEN
        expected_outcome := 'no_suspicious_cells_detected';
      ELSE
        expected_outcome := 'inconclusive';
      END IF;

      IF NEW.analysis_run_id IS DISTINCT FROM source_analysis_run_id
        OR NEW.detection_run_id IS DISTINCT FROM source_detection_run_id
        OR NEW.eligible_cell_count IS DISTINCT FROM source_eligible_count
        OR NEW.classified_cell_count IS DISTINCT FROM actual_classified_count
        OR NEW.parasitized_candidate_count
          IS DISTINCT FROM actual_parasitized_count
        OR NEW.uninfected_candidate_count
          IS DISTINCT FROM actual_uninfected_count
        OR NEW.near_threshold_count IS DISTINCT FROM actual_near_count
        OR NEW.failed_prediction_count IS DISTINCT FROM actual_failed_count
        OR NEW.outcome IS DISTINCT FROM expected_outcome
        OR NEW.per_image_summary IS DISTINCT FROM actual_per_image
        OR NEW.aggregation_policy_snapshot IS DISTINCT FROM expected_policy
        OR (
          actual_classified_count > 0
          AND (
            NEW.maximum_probability_parasitized IS NULL
            OR NEW.mean_probability_parasitized IS NULL
            OR NEW.median_probability_parasitized IS NULL
            OR abs(
              NEW.maximum_probability_parasitized - actual_maximum
            ) > 1e-12
            OR abs(NEW.mean_probability_parasitized - actual_mean) > 1e-12
            OR abs(NEW.median_probability_parasitized - actual_median) > 1e-12
          )
        )
      THEN
        RAISE EXCEPTION
          'smear analysis summary does not match immutable predictions'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END;
    $function$;

CREATE OR REPLACE FUNCTION public.campaign_attempt_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
DECLARE m record; c record; r record; cfg jsonb; rcfg jsonb; maximum integer; technical jsonb;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'ATTEMPT_HISTORY_IMMUTABLE'; END IF;
 -- Campaign lock first, shared with planning and members; then member serialization.
 SELECT c0.* INTO c FROM experimental_campaigns c0 JOIN campaign_members m0 ON m0.campaign_id=c0.id WHERE m0.id=NEW.member_id FOR UPDATE OF c0;
 SELECT * INTO m FROM campaign_members WHERE id=NEW.member_id FOR UPDATE;
 IF m.id IS NULL OR c.state NOT IN ('frozen','active','paused') THEN RAISE EXCEPTION 'ATTEMPT_REQUIRES_FROZEN_CAMPAIGN'; END IF;
 SELECT v.payload->'environment' INTO technical FROM campaign_technical_revisions v WHERE v.id=coalesce((SELECT revision_id FROM campaign_controlled_requests WHERE attempt_id=NEW.id AND campaign_id=c.id AND member_id=NEW.member_id),(SELECT revision_id FROM train_execution_revisions WHERE attempt_id=NEW.id AND campaign_id=c.id));
 IF TG_OP='INSERT' THEN
   SELECT coalesce(max(ordinal),0)+1 INTO maximum FROM campaign_attempts WHERE member_id=NEW.member_id;
   IF (c.state='paused' AND NOT EXISTS(SELECT 1 FROM campaign_controlled_requests WHERE attempt_id=NEW.id AND campaign_id=c.id AND member_id=NEW.member_id)) OR NEW.state<>'active' OR m.state NOT IN ('pending','failed','interrupted')
      OR NEW.ordinal<>maximum OR NEW.ordinal>(c.protocol->'budget'->>'max_attempts_per_member')::int
      THEN RAISE EXCEPTION 'INVALID_NEW_ATTEMPT'; END IF;
 ELSE
   IF NEW.id<>OLD.id OR NEW.member_id<>OLD.member_id OR NEW.ordinal<>OLD.ordinal OR NEW.started_at<>OLD.started_at
     OR (OLD.training_run_id IS NOT NULL AND NEW.training_run_id IS DISTINCT FROM OLD.training_run_id)
     THEN RAISE EXCEPTION 'ATTEMPT_IDENTITY_IMMUTABLE'; END IF;
   IF NOT ((OLD.state='active' AND NEW.state IN ('active','failed','interrupted','completed')) OR (OLD.state='completed' AND NEW.state='verified')) THEN RAISE EXCEPTION 'INVALID_ATTEMPT_TRANSITION'; END IF;
 END IF;
 IF NEW.state='verified' AND NOT EXISTS(SELECT 1 FROM train_execution_sessions WHERE run_id=NEW.training_run_id AND state='verified') THEN RAISE EXCEPTION 'TRAIN_EVIDENCE_REQUIRED'; END IF;
 IF NEW.training_run_id IS NOT NULL THEN
   SELECT * INTO r FROM runs WHERE id=NEW.training_run_id FOR UPDATE;
   PERFORM 1 FROM models WHERE id=r.model_id FOR SHARE;
   IF NOT campaign_model_matches(NEW.training_run_id,NEW.member_id) THEN RAISE EXCEPTION 'TRAIN_RELATIONAL_MODEL_CONFLICT'; END IF;
   SELECT configuration INTO cfg FROM campaign_configurations WHERE campaign_id=m.campaign_id AND configuration_hash=m.configuration_hash;
   rcfg=r.execution_parameters->'model_configuration_e2'->'configuration';
   IF r.id IS NULL OR r.run_type<>'training' OR r.dataset_version_id IS DISTINCT FROM c.dataset_version_id
     OR (c.experiment_id IS NOT NULL AND r.experiment_id IS DISTINCT FROM c.experiment_id)
     OR r.random_seed IS DISTINCT FROM m.seed
     OR (rcfg->'resolved'->'execution'->>'seed') IS DISTINCT FROM m.seed::text
     OR (rcfg->>'model_id') IS DISTINCT FROM (cfg->>'model_id')
     OR (rcfg->>'adapter_version') IS DISTINCT FROM (cfg->>'adapter_version')
     OR (rcfg->>'schema_version') IS DISTINCT FROM (cfg->>'schema_version')
     OR (rcfg->'resolved' #- '{execution,seed}') IS DISTINCT FROM (cfg->'resolved')
     OR r.execution_parameters->'model_configuration_e2'->'dataset' IS DISTINCT FROM c.dataset_snapshot
     OR r.execution_parameters->'model_configuration_e2'->'environment'->>'source_sha256' IS DISTINCT FROM coalesce(technical,c.environment)->>'source_sha256'
     OR r.execution_parameters->'model_configuration_e2'->'environment'->'packages' IS DISTINCT FROM coalesce(technical,c.environment)->'packages'
     OR r.execution_parameters->'model_configuration_e2'->'environment'->>'python' IS DISTINCT FROM coalesce(technical,c.environment)->>'python'
     OR r.execution_parameters->'model_configuration_e2'->'environment'->>'tensorflow' IS DISTINCT FROM coalesce(technical,c.environment)->>'tensorflow'
     OR r.execution_parameters->'model_configuration_e2'->'environment'->'determinism_environment' IS DISTINCT FROM coalesce(technical,c.environment)->'determinism_environment'
     THEN RAISE EXCEPTION 'TRAIN_CAMPAIGN_CONTRACT_CONFLICT'; END IF;
 END IF;
 RETURN NEW;
END $function$;

CREATE OR REPLACE FUNCTION public.campaign_configuration_valid(v jsonb)
 RETURNS boolean
 LANGUAGE plpgsql
 IMMUTABLE
 SET search_path TO 'public', 'pg_catalog'
AS $function$
DECLARE r jsonb; m jsonb; e jsonb; i jsonb; o jsonb; x jsonb; k text;
BEGIN
 IF NOT campaign_json_object(v,ARRAY['schema_version','model_id','adapter_version','resolved'])
   OR v->>'schema_version' IS DISTINCT FROM 'model_config_v1'
   OR NOT campaign_json_string(v->'model_id') OR NOT campaign_json_string(v->'adapter_version') THEN RETURN false; END IF;
 r=v->'resolved';
 IF NOT campaign_json_object(r,ARRAY['model','optimizer','execution','recipe','selection','input_contract']) THEN RETURN false; END IF;
 m=r->'model';e=r->'execution';i=r->'input_contract';o=r->'optimizer';
 IF NOT campaign_json_object(m,ARRAY['input_shape','preprocessing','weights','dropout','l2','head_units','batch_normalization','fine_tune_layers'])
   OR NOT campaign_json_object(o,ARRAY['name','parameters','fine_tune_learning_rate'])
   OR NOT campaign_json_string(o->'name') OR jsonb_typeof(o->'parameters') IS DISTINCT FROM 'object'
   OR jsonb_typeof(o->'fine_tune_learning_rate') IS DISTINCT FROM 'number'
   OR NOT campaign_json_object(e,ARRAY['max_epochs','fine_tune_epochs','batch_size','deterministic_ops','no_augment','checkpoint_policy','checkpoint_mode','min_recall','beta','reject_prediction_collapse','min_class_fraction','calibrate_threshold','target_recall','min_specificity','early_stopping','early_stopping_mode','early_stopping_patience','early_stopping_min_delta','restore_best_weights','evaluate_best_on_test'])
   OR e ? 'seed' OR e->'evaluate_best_on_test' IS DISTINCT FROM 'false'::jsonb
   OR NOT campaign_json_integer(e->'max_epochs',1) OR NOT campaign_json_integer(e->'fine_tune_epochs',0)
   OR NOT campaign_json_integer(e->'batch_size',1) OR NOT campaign_json_integer(e->'early_stopping_patience',0)
   OR NOT campaign_json_object(r->'recipe',ARRAY['loss','metrics','augmentation','reduce_lr','selection_threshold','fallback','clinical_success_independent_of_technical_completion'])
   OR NOT campaign_json_object(r->'selection',ARRAY['monitor','mode','explicit','early_stopping_monitor','early_stopping_mode','threshold','beta','clinical_objective','fallback'])
   OR NOT campaign_json_object(i,ARRAY['schema_version','architecture','adapter_version','shape','dtype','channels','source_order','source_scale','decode','resize','external','internal','label_mapping','output'])
   THEN RETURN false; END IF;
 FOREACH k IN ARRAY ARRAY['preprocessing','weights','batch_normalization'] LOOP
   IF NOT campaign_json_string(m->k) THEN RETURN false; END IF;
 END LOOP;
 IF jsonb_typeof(m->'dropout') IS DISTINCT FROM 'number' OR jsonb_typeof(m->'l2') IS DISTINCT FROM 'number'
   OR NOT campaign_json_integer(m->'head_units',0) OR NOT campaign_json_integer(m->'fine_tune_layers',0)
   THEN RETURN false; END IF;
 FOREACH k IN ARRAY ARRAY['deterministic_ops','no_augment','reject_prediction_collapse','calibrate_threshold','early_stopping','restore_best_weights'] LOOP
   IF jsonb_typeof(e->k) IS DISTINCT FROM 'boolean' THEN RETURN false; END IF;
 END LOOP;
 FOREACH k IN ARRAY ARRAY['min_recall','beta','min_class_fraction','target_recall','min_specificity','early_stopping_min_delta'] LOOP
   IF jsonb_typeof(e->k) IS DISTINCT FROM 'number' THEN RETURN false; END IF;
 END LOOP;
 FOREACH k IN ARRAY ARRAY['checkpoint_policy','checkpoint_mode','early_stopping_mode'] LOOP
   IF NOT campaign_json_string(e->k) THEN RETURN false; END IF;
 END LOOP;
 -- Monitor values are optional in E2; presence is mandatory, JSON null is allowed.
 FOREACH k IN ARRAY ARRAY['checkpoint_monitor','early_stopping_monitor'] LOOP
   IF NOT (e ? k) OR (e->k<>'null'::jsonb AND NOT campaign_json_string(e->k)) THEN RETURN false; END IF;
 END LOOP;
 IF NOT campaign_json_string(r->'recipe'->'loss') OR NOT campaign_json_string(r->'recipe'->'metrics')
   OR jsonb_typeof(r->'recipe'->'augmentation') IS DISTINCT FROM 'object'
   OR jsonb_typeof(r->'recipe'->'reduce_lr') IS DISTINCT FROM 'object'
   OR jsonb_typeof(r->'recipe'->'selection_threshold') IS DISTINCT FROM 'number'
   OR NOT campaign_json_string(r->'recipe'->'fallback')
   OR r->'recipe'->'clinical_success_independent_of_technical_completion' IS DISTINCT FROM 'true'::jsonb
   OR jsonb_typeof(r->'selection'->'explicit') IS DISTINCT FROM 'boolean'
   OR jsonb_typeof(r->'selection'->'threshold') IS DISTINCT FROM 'number'
   OR jsonb_typeof(r->'selection'->'beta') IS DISTINCT FROM 'number' THEN RETURN false; END IF;
 FOREACH k IN ARRAY ARRAY['monitor','mode','early_stopping_monitor','early_stopping_mode','clinical_objective','fallback'] LOOP
   IF NOT campaign_json_string(r->'selection'->k) THEN RETURN false; END IF;
 END LOOP;
 IF i->>'schema_version' IS DISTINCT FROM 'malaria_input_v1'
   OR i->>'architecture' IS DISTINCT FROM v->>'model_id' OR i->>'adapter_version' IS DISTINCT FROM v->>'adapter_version'
   OR i->>'dtype' IS DISTINCT FROM 'float32' OR i->'channels' IS DISTINCT FROM '3'::jsonb
   OR i->>'source_order' IS DISTINCT FROM 'RGB' OR i->>'source_scale' IS DISTINCT FROM '0_255'
   OR i->>'decode' IS DISTINCT FROM 'tf_decode_image_rgb_v1'
   OR i->'resize' IS DISTINCT FROM '{"method":"bilinear","antialias": false,"location":"loader"}'::jsonb
   OR NOT campaign_json_object(i->'external',ARRAY['mode','version','location','output_order'])
   OR jsonb_typeof(i->'internal') IS DISTINCT FROM 'object'
   OR NOT ((i->'internal') ?& ARRAY['mode','location'])
   OR NOT campaign_json_object(i->'output',ARRAY['shape','dtype','meaning','activation'])
   OR i->'label_mapping' IS DISTINCT FROM '{"0":"uninfected","1":"parasitized","positive_class": 1,"positive_label":"parasitized"}'::jsonb
   OR jsonb_typeof(m->'input_shape') IS DISTINCT FROM 'array' OR jsonb_array_length(m->'input_shape')<>3
   OR jsonb_typeof(i->'shape') IS DISTINCT FROM 'array' OR jsonb_array_length(i->'shape')<>4
   OR i->'shape'->0 IS DISTINCT FROM 'null'::jsonb
   THEN RETURN false; END IF;
 FOR x IN SELECT value FROM jsonb_array_elements(m->'input_shape') LOOP
   IF NOT campaign_json_integer(x,1) THEN RETURN false; END IF;
 END LOOP;
 RETURN ((i->'shape') - 0) = m->'input_shape' AND (m->'input_shape'->2)='3'::jsonb
   AND i->'external'->>'mode'=m->>'preprocessing';
END $function$;

CREATE OR REPLACE FUNCTION public.campaign_run_identity_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
BEGIN
 IF EXISTS(SELECT 1 FROM campaign_attempts WHERE training_run_id=OLD.id) AND
   (NEW.model_id IS DISTINCT FROM OLD.model_id
    OR NEW.run_type IS DISTINCT FROM OLD.run_type OR NEW.dataset_version_id IS DISTINCT FROM OLD.dataset_version_id
    OR NEW.random_seed IS DISTINCT FROM OLD.random_seed OR NEW.experiment_id IS DISTINCT FROM OLD.experiment_id
    OR NEW.execution_parameters->'model_configuration_e2'->'configuration' IS DISTINCT FROM OLD.execution_parameters->'model_configuration_e2'->'configuration'
    OR NEW.execution_parameters->'model_configuration_e2'->'dataset' IS DISTINCT FROM OLD.execution_parameters->'model_configuration_e2'->'dataset'
    OR campaign_environment_identity(NEW.execution_parameters->'model_configuration_e2'->'environment') IS DISTINCT FROM
       campaign_environment_identity(OLD.execution_parameters->'model_configuration_e2'->'environment'))
 THEN RAISE EXCEPTION 'LINKED_TRAIN_IDENTITY_IMMUTABLE'; END IF;
 RETURN NEW;
END $function$;

CREATE OR REPLACE FUNCTION public.campaign_technical_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
DECLARE c record; m record; a record; e jsonb;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'TECHNICAL_HISTORY_IMMUTABLE'; END IF;
 SELECT * INTO c FROM experimental_campaigns WHERE id=NEW.campaign_id FOR UPDATE;
 IF c.state IS DISTINCT FROM 'paused' THEN RAISE EXCEPTION 'PAUSED_CAMPAIGN_REQUIRED'; END IF;
 IF TG_TABLE_NAME='campaign_technical_revisions' THEN
  IF (NEW.payload-ARRAY['original_environment','environment','contract_hash','reason','files','tests','authorization'])<>'{}'::jsonb OR NOT campaign_json_object(NEW.payload,ARRAY['original_environment','environment','contract_hash','reason','files','tests','authorization'])
   OR NEW.payload->'original_environment' IS DISTINCT FROM c.environment
   OR NEW.payload->>'contract_hash' IS DISTINCT FROM c.contract_hash
   OR jsonb_typeof(NEW.payload->'files') IS DISTINCT FROM 'object'
   OR NEW.payload->'files'='{}'::jsonb
   OR EXISTS(SELECT 1 FROM jsonb_each(NEW.payload->'files') f WHERE jsonb_typeof(f.value) IS DISTINCT FROM 'string' OR (f.value#>>'{}') !~ '^[a-f0-9]{64}$')
   OR jsonb_typeof(NEW.payload->'tests') IS DISTINCT FROM 'array'
   OR jsonb_array_length(NEW.payload->'tests')=0
   OR coalesce(length(trim(NEW.payload->>'reason')),0)=0
   OR coalesce(length(trim(NEW.payload->>'authorization')),0)=0
  THEN RAISE EXCEPTION 'TECHNICAL_REVISION_INVALID'; END IF;
  e=NEW.payload->'environment';
  IF jsonb_typeof(e) IS DISTINCT FROM 'object' OR coalesce(e->>'source_sha256','') !~ '^[a-f0-9]{64}$'
    OR ((e-ARRAY['source_sha256','git_commit']) IS DISTINCT FROM (c.environment-ARRAY['source_sha256','git_commit']) AND NOT (e->>'execution_mode'='local_python' AND e->>'platform'='Darwin' AND e->>'machine'='arm64' AND e->>'device'='CPU' AND e->>'precision'='float32' AND jsonb_typeof(e->'packages')='object' AND e->'packages'<>'{}'::jsonb AND jsonb_typeof(e->'determinism_environment')='object') IS TRUE)
  THEN RAISE EXCEPTION 'TECHNICAL_ENVIRONMENT_CONFLICT'; END IF;
 ELSE
  SELECT * INTO m FROM campaign_members WHERE id=NEW.member_id FOR UPDATE;
  SELECT * INTO a FROM campaign_attempts WHERE id=NEW.previous_attempt_id;
  IF m.campaign_id IS DISTINCT FROM c.id OR a.member_id IS DISTINCT FROM m.id
   OR a.state NOT IN ('failed','interrupted') OR m.state NOT IN ('failed','interrupted')
   OR EXISTS(SELECT 1 FROM campaign_attempts a0 JOIN campaign_members m0 ON m0.id=a0.member_id
             WHERE m0.campaign_id=c.id AND a0.state IN ('active','completed'))
  THEN RAISE EXCEPTION 'CONTROLLED_ATTEMPT_INELIGIBLE'; END IF;
 END IF;
 RETURN NEW;
END $function$;

CREATE FUNCTION public.e04_calibration_complete() RETURNS trigger LANGUAGE plpgsql
 SET search_path=public,pg_catalog AS $$
BEGIN
 IF TG_TABLE_NAME='evaluations' THEN
   PERFORM public.e04_assert_calibration(NEW.id);
 ELSE
   PERFORM public.e04_assert_calibration(NEW.default_evaluation_id);
   PERFORM public.e04_assert_calibration(NEW.selected_evaluation_id);
 END IF;
 RETURN NULL;
END $$;

CREATE OR REPLACE FUNCTION public.experiment_reservation_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
BEGIN
 PERFORM experiment_require_owner();
 IF TG_OP='INSERT' THEN
  IF TG_TABLE_NAME='assessment_attempts' AND EXISTS(SELECT 1 FROM train_execution_sessions WHERE state IN ('active','completed'))
  THEN RAISE EXCEPTION 'GLOBAL_TRAIN_ALREADY_ACTIVE'; END IF;
  IF TG_TABLE_NAME IN ('train_execution_sessions','campaign_attempts') AND EXISTS(SELECT 1 FROM assessment_attempts WHERE state='active')
  THEN RAISE EXCEPTION 'GLOBAL_ASSESSMENT_ALREADY_ACTIVE'; END IF;
 END IF;
 RETURN NEW;
END $function$;

CREATE OR REPLACE FUNCTION public.train_event_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_catalog'
AS $function$
DECLARE s record; previous numeric;
BEGIN
 IF NEW.event_id IS NULL THEN RETURN NEW; END IF;
 -- Same global ownership guard as reservations. Acquired before the session lock.
 PERFORM experiment_require_owner();
 SELECT * INTO s FROM train_execution_sessions WHERE run_id=NEW.run_id FOR UPDATE NOWAIT;
 IF s.run_id IS NULL OR s.state IS DISTINCT FROM 'active'
 OR s.owner::text IS DISTINCT FROM current_setting('capstone.train_owner',true)
 THEN RAISE EXCEPTION 'TRAIN_OWNER_FENCED'; END IF;
 SELECT coalesce(max(event_sequence),0) INTO previous FROM train_execution_records WHERE run_id=NEW.run_id;
 IF NEW.event_sequence IS DISTINCT FROM previous+1
 THEN RAISE EXCEPTION 'RESULT_EVENT_SEQUENCE_INVALID'; END IF;
 RETURN NEW;
END $function$;

CREATE OR REPLACE FUNCTION public.campaign_contract_valid(v jsonb)
 RETURNS boolean
 LANGUAGE plpgsql
 IMMUTABLE
 SET search_path TO 'public', 'pg_catalog'
AS $function$
DECLARE p jsonb; b jsonb; matrix jsonb; seeds jsonb; configs jsonb; members jsonb;
 env jsonb; x jsonb; item record; seen_seeds jsonb='[]'; descriptor jsonb; k text;
 n integer; idx integer=0;
BEGIN
 -- experiment_id alone is intentionally nullable; its presence remains mandatory.
 IF NOT campaign_json_object(v,ARRAY['version','name','purpose','dataset','dataset_evidence_id','requested','protocol','environment','matrix'])
   OR NOT (v ? 'experiment_id') OR v->>'version' IS DISTINCT FROM 'campaign_contract_v1'
   OR NOT campaign_json_string(v->'name') OR NOT campaign_json_string(v->'purpose')
   OR NOT campaign_json_string(v->'dataset_evidence_id')
   OR NOT campaign_json_object(v->'dataset',ARRAY['dataset_version_id','dataset_materialization_id','dataset_root','patient_assignment_fingerprint','record_assignment_fingerprint','source_population_fingerprint','clinical_identity_fingerprint','counts','selection_unit'])
   OR jsonb_typeof(v->'requested') IS DISTINCT FROM 'object' THEN RETURN false; END IF;
 p=v->'protocol';
 IF NOT campaign_json_object(p,ARRAY['version','objective','metrics','sensitivity_target','specificity_minimum','roles','ranking','checkpoint','early_stopping','calibration','budget','missing','retries','fallback','test_access','aggregation','uncertainty','limitations','pending'])
   OR NOT campaign_json_string(p->'version') OR NOT campaign_json_string(p->'objective')
   OR p->'pending' IS DISTINCT FROM '[]'::jsonb
   OR p->'roles' IS DISTINCT FROM '{"train":"train","selection":"val","calibration":"val","final_test":"test"}'::jsonb
   OR p->>'test_access' IS DISTINCT FROM 'final_only_after_candidate_lock'
   OR p->>'retries' IS DISTINCT FROM 'first_verified_attempt'
   OR p->>'missing' IS DISTINCT FROM 'report_all_members' OR p->>'fallback' IS DISTINCT FROM 'diagnostic_only'
   OR jsonb_typeof(p->'sensitivity_target') IS DISTINCT FROM 'number'
   OR jsonb_typeof(p->'specificity_minimum') IS DISTINCT FROM 'number' THEN RETURN false; END IF;
 IF (p->>'sensitivity_target')::numeric NOT BETWEEN 0 AND 1 OR (p->>'specificity_minimum')::numeric NOT BETWEEN 0 AND 1 THEN RETURN false; END IF;
 b=p->'budget';
 IF NOT campaign_json_object(b,ARRAY['max_members','max_attempts_per_member'])
   OR NOT campaign_json_integer(b->'max_members',1) OR NOT campaign_json_integer(b->'max_attempts_per_member',1)
   OR NOT campaign_json_object(p->'metrics',ARRAY['primary','secondary','definitions_version','compliance'])
   OR jsonb_typeof(p->'metrics'->'primary') IS DISTINCT FROM 'array' OR jsonb_array_length(p->'metrics'->'primary')=0
   OR jsonb_typeof(p->'metrics'->'secondary') IS DISTINCT FROM 'array'
   OR NOT campaign_json_string(p->'metrics'->'definitions_version')
   OR p->'metrics'->>'compliance' NOT IN ('point_estimate','confidence_bound')
   OR NOT campaign_json_object(p->'ranking',ARRAY['partition','criteria','tie_breaks'])
   OR p->'ranking'->>'partition' IS DISTINCT FROM 'val'
   OR jsonb_typeof(p->'ranking'->'criteria') IS DISTINCT FROM 'array' OR jsonb_array_length(p->'ranking'->'criteria')=0
   OR jsonb_typeof(p->'ranking'->'tie_breaks') IS DISTINCT FROM 'array' OR jsonb_array_length(p->'ranking'->'tie_breaks')=0
   OR NOT campaign_json_object(p->'checkpoint',ARRAY['policy','monitor','mode','threshold'])
   OR p->'checkpoint'->'threshold' IS DISTINCT FROM '0.5'::jsonb
   OR NOT campaign_json_object(p->'early_stopping',ARRAY['enabled','monitor','mode','patience','min_delta','restore_best_weights'])
   OR jsonb_typeof(p->'early_stopping'->'enabled') IS DISTINCT FROM 'boolean'
   OR jsonb_typeof(p->'early_stopping'->'restore_best_weights') IS DISTINCT FROM 'boolean'
   OR NOT campaign_json_integer(p->'early_stopping'->'patience',0)
   OR jsonb_typeof(p->'early_stopping'->'min_delta') IS DISTINCT FROM 'number'
   OR NOT campaign_json_object(p->'calibration',ARRAY['algorithm','population','version'])
   OR p->'calibration'->>'population' IS DISTINCT FROM 'val'
   OR p->'calibration'->>'algorithm' NOT IN ('none','threshold_grid')
   OR NOT campaign_json_string(p->'calibration'->'version')
   OR NOT campaign_json_object(p->'limitations',ARRAY['shared_val','independent_calibration','test_exposure'])
   OR NOT campaign_json_string(p->'limitations'->'shared_val')
   OR p->'limitations'->'independent_calibration' IS DISTINCT FROM 'false'::jsonb
   OR p->'limitations'->>'test_exposure' NOT IN ('unknown','previously_accessed')
   OR NOT campaign_json_object(p->'aggregation',ARRAY['version','specification'])
   OR NOT campaign_json_string(p->'aggregation'->'version') OR NOT campaign_json_string(p->'aggregation'->'specification')
   OR NOT campaign_json_object(p->'uncertainty',ARRAY['version','specification'])
   OR NOT campaign_json_string(p->'uncertainty'->'version') OR NOT campaign_json_string(p->'uncertainty'->'specification')
   THEN RETURN false; END IF;
 FOREACH k IN ARRAY ARRAY['primary','secondary'] LOOP
   FOR x IN SELECT value FROM jsonb_array_elements(p->'metrics'->k) LOOP
     IF NOT campaign_json_string(x) THEN RETURN false; END IF;
   END LOOP;
 END LOOP;
 FOREACH k IN ARRAY ARRAY['criteria','tie_breaks'] LOOP
   FOR x IN SELECT value FROM jsonb_array_elements(p->'ranking'->k) LOOP
     IF NOT campaign_json_string(x) THEN RETURN false; END IF;
   END LOOP;
 END LOOP;
 FOREACH k IN ARRAY ARRAY['policy','monitor','mode'] LOOP
   IF NOT campaign_json_string(p->'checkpoint'->k) THEN RETURN false; END IF;
 END LOOP;
 IF NOT campaign_json_string(p->'early_stopping'->'monitor')
   OR NOT campaign_json_string(p->'early_stopping'->'mode') THEN RETURN false; END IF;
 env=v->'environment';
 IF NOT campaign_json_object(env,ARRAY['source_sha256','python','tensorflow','packages','determinism_environment'])
   OR NOT campaign_json_string(env->'python') OR NOT campaign_json_string(env->'tensorflow')
   OR (env->>'source_sha256') !~ '^[a-f0-9]{64}$'
   OR jsonb_typeof(env->'packages') IS DISTINCT FROM 'object' OR env->'packages'='{}'::jsonb
   OR jsonb_typeof(env->'determinism_environment') IS DISTINCT FROM 'object' THEN RETURN false; END IF;
 matrix=v->'matrix';
 IF NOT campaign_json_object(matrix,ARRAY['canonical_version','registry','registry_hash','configurations','members','expected_count','seeds'])
   OR matrix->>'canonical_version' IS DISTINCT FROM 'campaign_json_v1'
   OR NOT campaign_json_integer(matrix->'expected_count',1)
   OR (matrix->>'registry_hash') !~ '^[a-f0-9]{64}$'
   OR jsonb_typeof(matrix->'registry') IS DISTINCT FROM 'array' OR jsonb_array_length(matrix->'registry')=0
   OR jsonb_typeof(matrix->'seeds') IS DISTINCT FROM 'array' OR jsonb_array_length(matrix->'seeds')=0
   OR jsonb_typeof(matrix->'configurations') IS DISTINCT FROM 'object' OR matrix->'configurations'='{}'::jsonb
   OR jsonb_typeof(matrix->'members') IS DISTINCT FROM 'array' THEN RETURN false; END IF;
 n=(matrix->>'expected_count')::integer; seeds=matrix->'seeds';configs=matrix->'configurations';members=matrix->'members';
 IF n>(b->>'max_members')::integer OR n<>jsonb_array_length(members)
   OR n<>(SELECT count(*) FROM jsonb_each(configs))*jsonb_array_length(seeds) THEN RETURN false; END IF;
 FOR x IN SELECT value FROM jsonb_array_elements(seeds) LOOP
   IF NOT campaign_json_integer(x,0) OR seen_seeds @> jsonb_build_array(x) THEN RETURN false; END IF;
   seen_seeds=seen_seeds || jsonb_build_array(x);
 END LOOP;
 FOR descriptor IN SELECT value FROM jsonb_array_elements(matrix->'registry') LOOP
   IF NOT campaign_json_object(descriptor,ARRAY['id','aliases','enabled','trainable','version','adapter','input_contract','output_contract','strategies','optimizers','preprocessing_modes','default_preprocessing'])
      OR NOT campaign_json_string(descriptor->'id') OR NOT campaign_json_string(descriptor->'version')
      OR descriptor->'enabled' IS DISTINCT FROM 'true'::jsonb OR descriptor->'trainable' IS DISTINCT FROM 'true'::jsonb
      OR jsonb_typeof(descriptor->'aliases') IS DISTINCT FROM 'array'
      OR jsonb_typeof(descriptor->'optimizers') IS DISTINCT FROM 'array' THEN RETURN false; END IF;
   FOREACH k IN ARRAY ARRAY['adapter','input_contract','output_contract','default_preprocessing'] LOOP
     IF NOT campaign_json_string(descriptor->k) THEN RETURN false; END IF;
   END LOOP;
   FOREACH k IN ARRAY ARRAY['aliases','strategies','optimizers','preprocessing_modes'] LOOP
     IF jsonb_typeof(descriptor->k) IS DISTINCT FROM 'array' THEN RETURN false; END IF;
     FOR x IN SELECT value FROM jsonb_array_elements(descriptor->k) LOOP
       IF NOT campaign_json_string(x) THEN RETURN false; END IF;
     END LOOP;
   END LOOP;
 END LOOP;
 FOR item IN SELECT * FROM jsonb_each(configs) LOOP
   IF item.key !~ '^[a-f0-9]{64}$' OR NOT campaign_json_object(item.value,ARRAY['configuration','requests'])
      OR campaign_configuration_valid(item.value->'configuration') IS NOT TRUE
      OR jsonb_typeof(item.value->'requests') IS DISTINCT FROM 'array' OR jsonb_array_length(item.value->'requests')=0 THEN RETURN false; END IF;
 END LOOP;
 FOR x IN SELECT value FROM jsonb_array_elements(members) LOOP
   IF NOT campaign_json_object(x,ARRAY['configuration_hash','seed','position']) OR NOT (x ? 'exclusion_reason')
     OR NOT campaign_json_string(x->'configuration_hash') OR NOT (configs ? (x->>'configuration_hash'))
     OR NOT campaign_json_integer(x->'seed',0) OR NOT (seeds @> jsonb_build_array(x->'seed'))
     OR NOT campaign_json_integer(x->'position',0) OR (x->>'position')::int<>idx
     OR (x->'exclusion_reason'<>'null'::jsonb AND NOT campaign_json_string(x->'exclusion_reason')) THEN RETURN false; END IF;
   idx=idx+1;
 END LOOP;
 RETURN true;
END $function$;


CREATE FUNCTION public.dbv21_xai_configuration_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_catalog AS $$
DECLARE c jsonb; h text;
BEGIN
 IF TG_TABLE_NAME='xai_method_configurations' THEN
 c:=jsonb_build_object('method',NEW.method,'implementation',NEW.implementation,'implementation_version',NEW.implementation_version,'parameters',NEW.parameters);
 h:=encode(digest(convert_to(NEW.canonical_configuration,'UTF8'),'sha256'),'hex');
 IF NEW.canonical_configuration::jsonb IS DISTINCT FROM c OR h IS DISTINCT FROM NEW.configuration_hash THEN RAISE EXCEPTION 'XAI_CONFIGURATION_HASH_MISMATCH'; END IF;
 ELSE
 c:=jsonb_build_object('metric_name',NEW.metric_name,'metric_family',NEW.metric_family,'protocol_name',NEW.protocol_name,'protocol_version',NEW.protocol_version,'parameters',NEW.parameters,'normalization_strategy',NEW.normalization_strategy,'perturbation_strategy',NEW.perturbation_strategy,'reference_definition',NEW.reference_definition);
 h:=encode(digest(convert_to(NEW.canonical_protocol,'UTF8'),'sha256'),'hex');
 IF NEW.canonical_protocol::jsonb IS DISTINCT FROM c OR h IS DISTINCT FROM NEW.protocol_hash THEN RAISE EXCEPTION 'XAI_PROTOCOL_HASH_MISMATCH'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION public.dbv21_xai_evaluation_complete() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_catalog AS $$
DECLARE eid uuid; q public.xai_quantitative_evaluations%ROWTYPE; p public.xai_evaluation_protocols%ROWTYPE; n integer;
BEGIN
 IF TG_TABLE_NAME = 'xai_quantitative_evaluations' THEN
     eid := NEW.id;
 ELSIF TG_TABLE_NAME = 'xai_evaluation_members' THEN
     eid := NEW.evaluation_id;
 ELSE
     RAISE EXCEPTION
         'dbv21_xai_evaluation_complete invoked from unsupported table: %',
         TG_TABLE_NAME;
 END IF;
 SELECT * INTO STRICT q FROM public.xai_quantitative_evaluations WHERE id=eid;
 SELECT * INTO STRICT p FROM public.xai_evaluation_protocols WHERE id=q.protocol_id;
 SELECT count(*) INTO n FROM public.xai_evaluation_members WHERE evaluation_id=eid;
 IF q.membership_hash IS DISTINCT FROM (SELECT encode(digest(convert_to(coalesce(string_agg(xai_evidence_id::text || ':' || member_role, E'\n' ORDER BY xai_evidence_id::text COLLATE "C"),''),'UTF8'),'sha256'),'hex') FROM public.xai_evaluation_members WHERE evaluation_id=eid) THEN RAISE EXCEPTION 'XAI_MEMBERSHIP_HASH_MISMATCH'; END IF;
 IF n<1 OR (p.metric_family='agreement' AND n<2) THEN RAISE EXCEPTION 'XAI_EVALUATION_MEMBERS_REQUIRED'; END IF;
 IF p.metric_family='agreement' AND EXISTS (
 SELECT 1 FROM public.xai_evaluation_members ma JOIN public.xai_evidence a ON a.id=ma.xai_evidence_id
 JOIN public.xai_evaluation_members mb ON mb.evaluation_id=ma.evaluation_id JOIN public.xai_evidence b ON b.id=mb.xai_evidence_id
 WHERE ma.evaluation_id=eid AND (a.input_sha256 IS DISTINCT FROM b.input_sha256 OR a.input_contract_hash IS DISTINCT FROM b.input_contract_hash OR a.target_class IS DISTINCT FROM b.target_class OR a.explained_output IS DISTINCT FROM b.explained_output OR a.processing_stage IS DISTINCT FROM b.processing_stage OR a.checkpoint_sha256 IS DISTINCT FROM b.checkpoint_sha256)) THEN RAISE EXCEPTION 'XAI_AGREEMENT_INCOMPATIBLE'; END IF;
 IF p.metric_family='localization' AND q.metric_value IS NOT NULL AND q.reference_annotation_id IS NULL THEN RAISE EXCEPTION 'XAI_LOCALIZATION_REFERENCE_REQUIRED'; END IF;
 IF q.reference_annotation_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.scientific_validation_annotations WHERE id=q.reference_annotation_id AND version=q.reference_annotation_version) THEN RAISE EXCEPTION 'XAI_REFERENCE_VERSION_MISMATCH'; END IF;
 RETURN NULL;
END $$;


-- 05_keys
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

ALTER TABLE public.xai_method_configurations ADD CONSTRAINT xai_method_configurations_pkey PRIMARY KEY (id);

ALTER TABLE public.xai_region_attributions ADD CONSTRAINT xai_region_attributions_pkey PRIMARY KEY (xai_evidence_id, region_type, region_index);

ALTER TABLE public.xai_evaluation_protocols ADD CONSTRAINT xai_evaluation_protocols_pkey PRIMARY KEY (id);

ALTER TABLE public.xai_evaluation_members ADD CONSTRAINT xai_evaluation_members_pkey PRIMARY KEY (evaluation_id, xai_evidence_id);

ALTER TABLE public.xai_method_configurations ADD CONSTRAINT uq_xai_method_configuration_hash UNIQUE (configuration_hash);

ALTER TABLE public.xai_evaluation_protocols ADD CONSTRAINT uq_xai_protocol_hash UNIQUE (protocol_hash);

ALTER TABLE public.xai_evaluation_protocols ADD CONSTRAINT uq_xai_protocol_metric UNIQUE (id, metric_name);

-- 06_constraints
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

ALTER TABLE public.artifacts ADD CONSTRAINT artifacts_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;

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

ALTER TABLE public.dataset_split_images ADD CONSTRAINT dataset_split_images_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_split_images ADD CONSTRAINT dataset_split_images_dataset_materialization_id_fkey FOREIGN KEY (dataset_materialization_id) REFERENCES dataset_materializations (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_split_images ADD CONSTRAINT dataset_split_images_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_split_statistics ADD CONSTRAINT dataset_split_statistics_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_split_validation_checks ADD CONSTRAINT dataset_split_validation_checks_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_splits ADD CONSTRAINT dataset_splits_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_version_sources ADD CONSTRAINT dataset_version_sources_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE RESTRICT;

ALTER TABLE public.dataset_version_sources ADD CONSTRAINT dataset_version_sources_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT fk_deployed_model_versions_rollback FOREIGN KEY (rollback_of_deployment_id) REFERENCES deployed_model_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT fk_deployed_model_versions_supersedes FOREIGN KEY (supersedes_deployment_id) REFERENCES deployed_model_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT fk_deployed_model_versions_threshold_version FOREIGN KEY (threshold_calibration_id, model_version_id) REFERENCES run_threshold_calibration (run_threshold_calibration_id, model_version_id) ON DELETE RESTRICT;

ALTER TABLE public.deployed_model_versions ADD CONSTRAINT fk_deployed_model_versions_version_artifact FOREIGN KEY (model_version_id, checkpoint_artifact_id) REFERENCES model_versions (id, checkpoint_artifact_id) ON DELETE RESTRICT;

ALTER TABLE public.environment_packages ADD CONSTRAINT environment_packages_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.errors ADD CONSTRAINT errors_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.execution_logs ADD CONSTRAINT execution_logs_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_dataset_evidence_id_fkey FOREIGN KEY (dataset_evidence_id) REFERENCES audit_events (id) ON DELETE RESTRICT;

ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE RESTRICT;

ALTER TABLE public.explainability_results ADD CONSTRAINT explainability_results_prediction_id_fkey FOREIGN KEY (prediction_id) REFERENCES predictions (id) ON DELETE RESTRICT;

ALTER TABLE public.explainability_results ADD CONSTRAINT explainability_results_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;

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

ALTER TABLE public.predictions ADD CONSTRAINT predictions_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE RESTRICT;

ALTER TABLE public.predictions ADD CONSTRAINT predictions_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;

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

ALTER TABLE public.run_checkpoint_policy ADD CONSTRAINT run_checkpoint_policy_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT run_clinical_metrics_model_id_fkey FOREIGN KEY (model_id) REFERENCES models (id) ON DELETE RESTRICT;

ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT run_clinical_metrics_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.run_dataset_images ADD CONSTRAINT run_dataset_images_image_id_fkey FOREIGN KEY (image_id) REFERENCES dataset_split_images (image_id) ON DELETE RESTRICT;

ALTER TABLE public.run_dataset_images ADD CONSTRAINT run_dataset_images_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.run_image_predictions ADD CONSTRAINT run_image_predictions_image_id_fkey FOREIGN KEY (image_id) REFERENCES dataset_split_images (image_id) ON DELETE RESTRICT;

ALTER TABLE public.run_image_predictions ADD CONSTRAINT run_image_predictions_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.run_io_records ADD CONSTRAINT run_io_records_dataset_materialization_id_fkey FOREIGN KEY (dataset_materialization_id) REFERENCES dataset_materializations (id) ON DELETE RESTRICT;

ALTER TABLE public.run_io_records ADD CONSTRAINT run_io_records_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.run_io_records ADD CONSTRAINT run_io_records_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.run_lineage ADD CONSTRAINT fk_run_lineage_checkpoint_artifact_owner FOREIGN KEY (checkpoint_artifact_id, parent_run_id) REFERENCES artifacts (id, run_id) ON DELETE RESTRICT;

ALTER TABLE public.run_lineage ADD CONSTRAINT fk_run_lineage_model_version_owner FOREIGN KEY (model_version_id, parent_run_id) REFERENCES model_versions (id, training_run_id) ON DELETE RESTRICT;

ALTER TABLE public.run_lineage ADD CONSTRAINT fk_run_lineage_version_artifact FOREIGN KEY (model_version_id, checkpoint_artifact_id) REFERENCES model_versions (id, checkpoint_artifact_id) ON DELETE RESTRICT;

ALTER TABLE public.run_lineage ADD CONSTRAINT run_lineage_child_run_id_fkey FOREIGN KEY (child_run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.run_lineage ADD CONSTRAINT run_lineage_parent_run_id_fkey FOREIGN KEY (parent_run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.run_metrics ADD CONSTRAINT run_metrics_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.run_model_deployments ADD CONSTRAINT fk_run_model_deployments_deployment_version FOREIGN KEY (deployed_model_version_id, model_version_id) REFERENCES deployed_model_versions (id, model_version_id) ON DELETE RESTRICT;

ALTER TABLE public.run_model_deployments ADD CONSTRAINT fk_run_model_deployments_run FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT fk_run_threshold_calibration_artifact_owner FOREIGN KEY (calibration_artifact_id, run_id) REFERENCES artifacts (id, run_id) ON DELETE RESTRICT;

ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT fk_run_threshold_calibration_model_version FOREIGN KEY (model_version_id) REFERENCES model_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT run_threshold_calibration_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.runs ADD CONSTRAINT runs_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns (id);

ALTER TABLE public.runs ADD CONSTRAINT runs_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE RESTRICT;

ALTER TABLE public.runs ADD CONSTRAINT runs_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;

ALTER TABLE public.runs ADD CONSTRAINT runs_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE RESTRICT;

ALTER TABLE public.runs ADD CONSTRAINT runs_model_id_fkey FOREIGN KEY (model_id) REFERENCES models (id) ON DELETE RESTRICT;

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

ALTER TABLE public.synthetic_data_runs ADD CONSTRAINT synthetic_data_runs_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.synthetic_data_runs ADD CONSTRAINT synthetic_data_runs_source_dataset_id_fkey FOREIGN KEY (source_dataset_id) REFERENCES datasets (id) ON DELETE RESTRICT;

ALTER TABLE public.train_execution_records ADD CONSTRAINT train_execution_records_run_id_fkey FOREIGN KEY (run_id) REFERENCES train_execution_sessions (run_id);

ALTER TABLE public.train_execution_revisions ADD CONSTRAINT train_execution_revisions_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES campaign_attempts (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.train_execution_revisions ADD CONSTRAINT train_execution_revisions_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns (id);

ALTER TABLE public.train_execution_revisions ADD CONSTRAINT train_execution_revisions_campaign_id_revision_id_fkey FOREIGN KEY (campaign_id, revision_id) REFERENCES campaign_technical_revisions (campaign_id, id);

ALTER TABLE public.train_execution_sessions ADD CONSTRAINT train_execution_sessions_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES campaign_attempts (id);

ALTER TABLE public.train_execution_sessions ADD CONSTRAINT train_execution_sessions_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id);

ALTER TABLE public.training_history ADD CONSTRAINT training_history_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;

ALTER TABLE public.user_roles ADD CONSTRAINT user_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE RESTRICT;

ALTER TABLE public.user_roles ADD CONSTRAINT user_roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE;

ALTER TABLE public.evaluations ADD CONSTRAINT fk_evaluation_e10_record FOREIGN KEY (run_id, event_kind, event_phase, event_key) REFERENCES public.train_execution_records (run_id, kind, phase, record_key) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT fk_metric_evaluation_run FOREIGN KEY (evaluation_id, run_id) REFERENCES public.evaluations (id, run_id) ON DELETE RESTRICT;

ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT ck_v2_binary_counts CHECK (tn >= 0 AND fp >= 0 AND fn >= 0 AND tp >= 0 AND (CAST(tn AS numeric) + fp + fn + tp) > 0);

ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT ck_v2_auc_domain CHECK ((roc_auc_parasitized IS NULL OR (roc_auc_parasitized >= 0 AND roc_auc_parasitized <= 1)) AND (pr_auc_parasitized IS NULL OR (pr_auc_parasitized >= 0 AND pr_auc_parasitized <= 1)));

ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT ck_v2_auc_reason CHECK ((roc_auc_parasitized IS NOT NULL AND pr_auc_parasitized IS NOT NULL AND auc_unavailability_reason IS NULL) OR ((roc_auc_parasitized IS NULL OR pr_auc_parasitized IS NULL) AND auc_unavailability_reason IS NOT NULL AND auc_unavailability_reason IN ('single_class', 'scores_unavailable', 'not_computed')));

ALTER TABLE public.training_history ADD CONSTRAINT ck_v2_epoch CHECK (epoch >= 0);

ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT ck_v2_calibration_val CHECK (calibration_split = 'val' AND default_threshold = 0.5 AND target_recall > 0 AND target_recall <= 1);

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

ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_d6094850fee4 CHECK (clinical_target_recall > 0 AND clinical_target_recall <= 1);

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

ALTER TABLE public.xai_evidence ADD CONSTRAINT ck_xai_input_origin CHECK (num_nonnulls(dataset_source_record_id, microscopy_image_id, input_artifact_id) = 1);

ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_bfbb62e97a91 CHECK (num_nonnulls(prediction_id, cell_prediction_id) <= 1);

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_foreign_4b080b42e888 FOREIGN KEY (evidence_id) REFERENCES public.xai_evidence (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_foreign_e3d2eb574718 FOREIGN KEY (artifact_id) REFERENCES public.artifacts (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_foreign_f9c5548be835 FOREIGN KEY (assessment_artifact_id) REFERENCES public.assessment_artifacts (artifact_id) ON DELETE RESTRICT;

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_70ab6797c0c6 CHECK (num_nonnulls(artifact_id, assessment_artifact_id) <= 1);

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_eb359eee6311 CHECK (role IN ('RAW_ATTRIBUTION', 'SPATIAL_MAP', 'SEGMENTATION', 'REGION_WEIGHTS', 'OVERLAY', 'HEATMAP_RENDER', 'BACKGROUND_MANIFEST', 'INPUT_MANIFEST'));

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_967aa2df2b88 CHECK (ordinal >= 0);

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_20426a1e7fe3 CHECK (sha256 ~ '^[0-9a-f]{64}$');

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_a81626200b02 CHECK (byte_size >= 0);

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_4b7ae3b26ca5 CHECK (availability IN ('available', 'missing', 'quarantined', 'archived'));

ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_a68006e838dc CHECK (tensor_shape IS NULL OR (cardinality(tensor_shape) > 0 AND 0 < ALL(tensor_shape)));

ALTER TABLE public.xai_interpretations ADD CONSTRAINT v2_xai_interpretations_foreign_4b080b42e888 FOREIGN KEY (evidence_id) REFERENCES public.xai_evidence (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_interpretations ADD CONSTRAINT v2_xai_interpretations_foreign_6b09f9926d4f FOREIGN KEY (author_user_id) REFERENCES public.users (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_interpretations ADD CONSTRAINT v2_xai_interpretations_check_c7c3afcde9f7 CHECK (length(pg_catalog.btrim(interpretation)) > 0);

ALTER TABLE public.xai_interpretations ADD CONSTRAINT v2_xai_interpretations_foreign_af451d74af77 FOREIGN KEY (supersedes_id) REFERENCES public.xai_interpretations (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_specialist_reviews ADD CONSTRAINT v2_xai_specialist_reviews_foreign_4735bf604cb2 FOREIGN KEY (interpretation_id) REFERENCES public.xai_interpretations (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_specialist_reviews ADD CONSTRAINT v2_xai_specialist_reviews_foreign_7ca01df9e490 FOREIGN KEY (reviewer_user_id) REFERENCES public.users (id) ON DELETE RESTRICT;

ALTER TABLE public.xai_specialist_reviews ADD CONSTRAINT v2_xai_specialist_reviews_check_920877b7b5d1 CHECK (decision IN ('supported', 'unsupported', 'inconclusive'));

ALTER TABLE public.xai_specialist_reviews ADD CONSTRAINT v2_xai_specialist_reviews_check_d8ae577b1870 CHECK (length(pg_catalog.btrim(rationale)) > 0);

ALTER TABLE public.xai_specialist_reviews ADD CONSTRAINT v2_xai_specialist_reviews_check_07baf4b694f5 CHECK (jsonb_typeof(competence_snapshot) = 'object');

ALTER TABLE public.xai_evidence ADD CONSTRAINT fk_xai_method_configuration FOREIGN KEY (method_configuration_id) REFERENCES public.xai_method_configurations (id) ON DELETE RESTRICT ON UPDATE NO ACTION;

ALTER TABLE public.xai_region_attributions ADD CONSTRAINT fk_xai_region_evidence FOREIGN KEY (xai_evidence_id) REFERENCES public.xai_evidence (id) ON DELETE RESTRICT ON UPDATE NO ACTION;

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT fk_xai_metric_protocol FOREIGN KEY (protocol_id, metric_name) REFERENCES public.xai_evaluation_protocols (id, metric_name) ON DELETE RESTRICT ON UPDATE NO ACTION;

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT fk_xai_reference_annotation FOREIGN KEY (reference_annotation_id) REFERENCES public.scientific_validation_annotations (id) ON DELETE RESTRICT ON UPDATE NO ACTION;

ALTER TABLE public.xai_evaluation_members ADD CONSTRAINT fk_xai_member_evaluation FOREIGN KEY (evaluation_id) REFERENCES public.xai_quantitative_evaluations (id) ON DELETE RESTRICT ON UPDATE NO ACTION;

ALTER TABLE public.xai_evaluation_members ADD CONSTRAINT fk_xai_member_evidence FOREIGN KEY (xai_evidence_id) REFERENCES public.xai_evidence (id) ON DELETE RESTRICT ON UPDATE NO ACTION;

ALTER TABLE public.xai_method_configurations ADD CONSTRAINT ck_configuration_hash_xai_method CHECK (configuration_hash ~ '^[0-9a-f]{64}$');

ALTER TABLE public.xai_method_configurations ADD CONSTRAINT ck_xai_method_configurations_parameters CHECK (jsonb_typeof(parameters) = 'object');

ALTER TABLE public.xai_evaluation_protocols ADD CONSTRAINT ck_protocol_hash_xai_protocol CHECK (protocol_hash ~ '^[0-9a-f]{64}$');

ALTER TABLE public.xai_evaluation_protocols ADD CONSTRAINT ck_xai_evaluation_protocols_parameters CHECK (jsonb_typeof(parameters) = 'object');

ALTER TABLE public.xai_method_configurations ADD CONSTRAINT ck_xai_method_identity CHECK (length(btrim(method)) > 0 AND method = lower(method) AND length(btrim(implementation)) > 0 AND length(btrim(implementation_version)) > 0);

ALTER TABLE public.xai_evaluation_protocols ADD CONSTRAINT ck_xai_protocol_identity CHECK (length(btrim(metric_name)) > 0 AND length(btrim(metric_family)) > 0 AND metric_family = lower(metric_family) AND length(btrim(protocol_name)) > 0 AND length(btrim(protocol_version)) > 0 AND length(btrim(normalization_strategy)) > 0);

ALTER TABLE public.xai_evidence ADD CONSTRAINT ck_xai_provisional_checkpoint CHECK (model_version_id IS NOT NULL OR run_id IS NOT NULL);

ALTER TABLE public.xai_evidence ADD CONSTRAINT ck_xai_prediction_score CHECK (prediction_score >= 0 AND prediction_score <= 1);

ALTER TABLE public.xai_region_attributions ADD CONSTRAINT ck_xai_region_domain CHECK (region_index >= 0 AND length(btrim(region_type)) > 0 AND (rank IS NULL OR rank > 0) AND attribution_value > '-Infinity'::float8 AND attribution_value < 'Infinity'::float8 AND (region_definition IS NULL OR jsonb_typeof(region_definition) = 'object'));

ALTER TABLE public.xai_evaluation_members ADD CONSTRAINT ck_xai_member_role CHECK (member_role ~ '^[a-z][a-z0-9_]*$');

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT ck_xai_metric_defined CHECK ((metric_value IS NULL AND undefined_reason IS NOT NULL AND length(btrim(undefined_reason)) > 0) OR (metric_value IS NOT NULL AND undefined_reason IS NULL AND metric_value > '-Infinity'::float8 AND metric_value < 'Infinity'::float8));

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT ck_xai_sample_count CHECK (sample_count > 0);

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT ck_xai_reference_tuple CHECK (num_nonnulls(reference_annotation_id, reference_annotation_version, reference_manifest_uri, reference_manifest_sha256) IN (0,4) AND (reference_annotation_version IS NULL OR reference_annotation_version > 0) AND (reference_manifest_sha256 IS NULL OR reference_manifest_sha256 ~ '^[0-9a-f]{64}$'));

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT ck_xai_details_tuple CHECK (num_nonnulls(details_uri, details_sha256) IN (0,2) AND (details_sha256 IS NULL OR details_sha256 ~ '^[0-9a-f]{64}$'));

-- 07_indexes
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

CREATE INDEX ix_xai_same_image ON public.xai_evidence (input_sha256, input_contract_hash, model_version_id, method_configuration_id, generated_at, id);

CREATE INDEX ix_xai_evaluation ON public.xai_evidence (evaluation_id, method_configuration_id);

CREATE UNIQUE INDEX uq_e04_event_role ON public.evaluations (source_event_id, evaluation_role) WHERE source_kind = 'e10' AND evaluation_role IN ('calibration_default', 'calibration_selected');

CREATE UNIQUE INDEX uq_e04_contract_role ON public.evaluations (run_id, training_run_id, model_version_id, checkpoint_artifact_id, dataset_version_id, population_hash, protocol_version, protocol_hash, input_contract_hash, evaluation_role) NULLS NOT DISTINCT WHERE source_kind = 'e10' AND evaluation_role IN ('calibration_default', 'calibration_selected');

CREATE INDEX ix_xai_member_evidence ON public.xai_evaluation_members (xai_evidence_id, evaluation_id);

CREATE INDEX ix_xai_method_configuration ON public.xai_evidence (method_configuration_id);

CREATE INDEX ix_xai_metric_protocol ON public.xai_quantitative_evaluations (protocol_id, metric_name, evaluated_at);

CREATE INDEX ix_xai_reference_annotation ON public.xai_quantitative_evaluations (reference_annotation_id);

-- 08_views
CREATE VIEW public.classification_reports AS SELECT m.run_clinical_metric_id AS id, m.run_id, m.split_name, c.class_name, c.precision_value, c.recall_value, c.f1_score, c.support, m.created_at, m.metadata FROM public.run_clinical_metrics AS m CROSS JOIN LATERAL ((VALUES (CAST('parasitized' AS text), m.precision_parasitized, m.recall_parasitized, m.f1_parasitized, CAST(m.tp AS numeric) + m.fn), (CAST('uninfected' AS text), CAST(m.tn AS numeric) / (NULLIF(CAST(m.tn AS numeric) + m.fn, 0)), m.specificity, (2 * CAST(m.tn AS numeric)) / (NULLIF((2 * CAST(m.tn AS numeric)) + m.fn + m.fp, 0)), CAST(m.tn AS numeric) + m.fp))) AS c (class_name, precision_value, recall_value, f1_score, support);

CREATE VIEW public.confusion_matrices AS SELECT run_clinical_metric_id AS id, run_id, split_name, CAST(ARRAY['uninfected', 'parasitized'] AS text[]) AS labels, confusion_matrix AS matrix, tp AS true_positive, tn AS true_negative, fp AS false_positive, fn AS false_negative, created_at, metadata FROM public.run_clinical_metrics;

CREATE VIEW public.inference_runs AS SELECT r.id, r.id AS run_id, primary_binding.deployed_model_version_id, primary_binding.model_version_id, r.backend_version, r.pipeline_version, r.started_at, r.finished_at AS completed_at, r.status, COALESCE(r.configuration, r.execution_parameters, r.parameters, CAST('{}' AS jsonb)) AS configuration, r.metadata, r.error_message, COALESCE(all_bindings.bindings, CAST('[]' AS jsonb)) AS deployment_bindings FROM runs AS r LEFT JOIN LATERAL (SELECT rmd.deployed_model_version_id, rmd.model_version_id FROM run_model_deployments AS rmd WHERE rmd.run_id = r.id ORDER BY rmd.role = CAST('primary' AS text) DESC, rmd.ordinal, rmd.created_at, rmd.id LIMIT 1) AS primary_binding ON TRUE LEFT JOIN LATERAL (SELECT jsonb_agg(jsonb_build_object('deployed_model_version_id', rmd.deployed_model_version_id, 'model_version_id', rmd.model_version_id, 'role', rmd.role, 'ordinal', rmd.ordinal, 'weight', rmd.weight) ORDER BY rmd.ordinal, rmd.created_at, rmd.id) AS bindings FROM run_model_deployments AS rmd WHERE rmd.run_id = r.id) AS all_bindings ON TRUE WHERE r.run_type = CAST('inference' AS text);

CREATE VIEW public.legacy_cell_predictions AS SELECT id, id AS cell_prediction_id, image_analysis_job_id, cell_index, inference_run_id, deployed_model_version_id, model_version_id, classifier_model_version_id, detector_model_version_id, source_image_id, bbox_x, bbox_y, bbox_width, bbox_height, crop_artifact_id, probability_parasitized, probability_uninfected, threshold_used, predicted_class, predicted_label, confidence_level, quality_status, explanation_artifact_id, review_status, reviewed_label, reviewed_by, reviewed_at, created_at, metadata FROM predictions AS p WHERE prediction_scope = CAST('cell' AS text);

CREATE VIEW public.vw_case_level_explainability AS SELECT er.id AS explainability_id, er.run_id, er.prediction_id, r.experiment_id, r.model_id, m.name AS model_name, m.model_type, COALESCE(p.dataset_id, r.dataset_id) AS dataset_id, d.name AS dataset_name, r.run_name, r.run_type, r.status AS run_status, r.script_name, r.command, r.started_at, r.finished_at, r.duration_seconds, er.method, CASE WHEN COALESCE(er.case_type, p.case_type) = CAST('low_confidence' AS text) THEN CAST('low_confidence' AS text) WHEN COALESCE(er.true_label, p.true_label) IS NULL OR COALESCE(er.predicted_label, p.predicted_label) IS NULL THEN COALESCE(er.case_type, p.case_type, CAST('unknown' AS text)) WHEN COALESCE(er.true_label, p.true_label) = COALESCE(NULLIF(r.parameters ->> CAST('positive_label' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('positive_label' AS text), CAST('' AS text)), CAST('parasitized' AS text)) AND COALESCE(er.predicted_label, p.predicted_label) = COALESCE(NULLIF(r.parameters ->> CAST('positive_label' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('positive_label' AS text), CAST('' AS text)), CAST('parasitized' AS text)) THEN CAST('true_positive' AS text) WHEN COALESCE(er.true_label, p.true_label) <> COALESCE(NULLIF(r.parameters ->> CAST('positive_label' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('positive_label' AS text), CAST('' AS text)), CAST('parasitized' AS text)) AND COALESCE(er.predicted_label, p.predicted_label) <> COALESCE(NULLIF(r.parameters ->> CAST('positive_label' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('positive_label' AS text), CAST('' AS text)), CAST('parasitized' AS text)) THEN CAST('true_negative' AS text) WHEN COALESCE(er.true_label, p.true_label) <> COALESCE(NULLIF(r.parameters ->> CAST('positive_label' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('positive_label' AS text), CAST('' AS text)), CAST('parasitized' AS text)) AND COALESCE(er.predicted_label, p.predicted_label) = COALESCE(NULLIF(r.parameters ->> CAST('positive_label' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('positive_label' AS text), CAST('' AS text)), CAST('parasitized' AS text)) THEN CAST('false_positive' AS text) WHEN COALESCE(er.true_label, p.true_label) = COALESCE(NULLIF(r.parameters ->> CAST('positive_label' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('positive_label' AS text), CAST('' AS text)), CAST('parasitized' AS text)) AND COALESCE(er.predicted_label, p.predicted_label) <> COALESCE(NULLIF(r.parameters ->> CAST('positive_label' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('positive_label' AS text), CAST('' AS text)), CAST('parasitized' AS text)) THEN CAST('false_negative' AS text) ELSE COALESCE(er.case_type, p.case_type, CAST('unknown' AS text)) END AS case_type, COALESCE(er.true_label, p.true_label) AS true_label, COALESCE(er.predicted_label, p.predicted_label) AS predicted_label, COALESCE(NULLIF(r.parameters ->> CAST('positive_label' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('positive_label' AS text), CAST('' AS text)), CAST('parasitized' AS text)) AS positive_label, COALESCE(p.score, er.score) AS score, COALESCE(p.score_positive_label, er.score) AS score_positive_label, COALESCE(p.score_positive_label, er.score) AS probability_parasitized, COALESCE(p.threshold, CASE WHEN (er.explanation_parameters ->> CAST('threshold' AS text)) ~ CAST('^-?[0-9]+([.][0-9]+)?$' AS text) THEN CAST(er.explanation_parameters ->> CAST('threshold' AS text) AS numeric) ELSE CAST(NULL AS numeric) END, CASE WHEN (r.parameters ->> CAST('threshold' AS text)) ~ CAST('^-?[0-9]+([.][0-9]+)?$' AS text) THEN CAST(r.parameters ->> CAST('threshold' AS text) AS numeric) ELSE CAST(NULL AS numeric) END, 0.5) AS threshold, COALESCE(p.threshold, CASE WHEN (er.explanation_parameters ->> CAST('threshold' AS text)) ~ CAST('^-?[0-9]+([.][0-9]+)?$' AS text) THEN CAST(er.explanation_parameters ->> CAST('threshold' AS text) AS numeric) ELSE CAST(NULL AS numeric) END, CASE WHEN (r.parameters ->> CAST('threshold' AS text)) ~ CAST('^-?[0-9]+([.][0-9]+)?$' AS text) THEN CAST(r.parameters ->> CAST('threshold' AS text) AS numeric) ELSE CAST(NULL AS numeric) END, 0.5) AS threshold_used, COALESCE(p.metadata ->> CAST('threshold_source' AS text), er.explanation_parameters ->> CAST('threshold_source' AS text), r.parameters ->> CAST('threshold_source' AS text), r.metadata ->> CAST('threshold_source' AS text), CAST('fixed_cli' AS text)) AS threshold_source, COALESCE(p.is_correct, COALESCE(er.true_label, p.true_label) = COALESCE(er.predicted_label, p.predicted_label)) AS is_correct, p.image_id, COALESCE(NULLIF(er.image_path, CAST('' AS text)), NULLIF(p.image_path, CAST('' AS text))) AS image_path, NULLIF(er.output_path, CAST('' AS text)) AS explanation_output_path, a.path AS artifact_path, a.artifact_type, er.last_conv_layer, er.success, er.error_message, er.explanation_parameters, p.metadata AS prediction_metadata, er.metadata AS explainability_metadata, r.parameters AS run_parameters, r.metadata AS run_metadata, a.id AS artifact_id FROM explainability_results AS er LEFT JOIN predictions AS p ON p.id = er.prediction_id LEFT JOIN runs AS r ON r.id = er.run_id LEFT JOIN models AS m ON m.id = r.model_id LEFT JOIN datasets AS d ON d.id = COALESCE(p.dataset_id, r.dataset_id) LEFT JOIN LATERAL (SELECT artifacts.id, artifacts.path, artifacts.artifact_type FROM artifacts WHERE artifacts.run_id = er.run_id AND ((er.output_path IS NOT NULL AND artifacts.path = er.output_path) OR (er.image_path IS NOT NULL AND artifacts.path = er.image_path) OR (p.image_path IS NOT NULL AND artifacts.path = p.image_path)) ORDER BY CASE WHEN er.output_path IS NOT NULL AND artifacts.path = er.output_path THEN 1 WHEN er.image_path IS NOT NULL AND artifacts.path = er.image_path THEN 2 ELSE 3 END, artifacts.created_at DESC LIMIT 1) AS a ON TRUE;

CREATE VIEW public.vw_checkpoint_policy_summary AS SELECT run_id, model_name, checkpoint_policy, min_recall_required, selected_epoch, policy_satisfied, selected_metric, selected_metric_value, val_recall_parasitized_selected, val_f2_parasitized_selected, val_specificity_selected, val_auc_selected, prediction_collapse_detected, all_epochs_collapsed, checkpoint_warning, checkpoint_path, created_at FROM run_checkpoint_policy AS rcp;

CREATE VIEW public.vw_clinical_run_summary AS WITH latest_io AS (SELECT DISTINCT ON (run_io_records.run_id) run_io_records.run_id, run_io_records.model_name, run_io_records.clinical_metadata, run_io_records.output_results FROM run_io_records ORDER BY run_io_records.run_id, run_io_records.created_at DESC), latest_metrics AS (SELECT DISTINCT ON (run_clinical_metrics.run_id) run_clinical_metrics.run_clinical_metric_id, run_clinical_metrics.run_id, run_clinical_metrics.model_id, run_clinical_metrics.model_name, run_clinical_metrics.split_name, run_clinical_metrics.threshold_used, run_clinical_metrics.threshold_source, run_clinical_metrics.accuracy, run_clinical_metrics.precision_parasitized, run_clinical_metrics.recall_parasitized, run_clinical_metrics.sensitivity_parasitized, run_clinical_metrics.specificity, run_clinical_metrics.f1_parasitized, run_clinical_metrics.f2_parasitized, run_clinical_metrics.roc_auc_parasitized, run_clinical_metrics.pr_auc_parasitized, run_clinical_metrics.balanced_accuracy, run_clinical_metrics.tn, run_clinical_metrics.fp, run_clinical_metrics.fn, run_clinical_metrics.tp, run_clinical_metrics.confusion_matrix, run_clinical_metrics.classification_report, run_clinical_metrics.prediction_distribution, run_clinical_metrics.prediction_collapse, run_clinical_metrics.label_mapping_version, run_clinical_metrics.raw_model_score_meaning, run_clinical_metrics.created_at, run_clinical_metrics.metadata FROM run_clinical_metrics WHERE run_clinical_metrics.split_name = ANY(ARRAY[CAST('test' AS text), CAST('external' AS text)]) ORDER BY run_clinical_metrics.run_id, run_clinical_metrics.created_at DESC), latest_checkpoint AS (SELECT DISTINCT ON (run_checkpoint_policy.run_id) run_checkpoint_policy.run_checkpoint_policy_id, run_checkpoint_policy.run_id, run_checkpoint_policy.model_name, run_checkpoint_policy.checkpoint_policy, run_checkpoint_policy.checkpoint_policy_config, run_checkpoint_policy.selected_epoch, run_checkpoint_policy.policy_satisfied, run_checkpoint_policy.selected_metric, run_checkpoint_policy.selected_metric_value, run_checkpoint_policy.min_recall_required, run_checkpoint_policy.val_recall_parasitized_selected, run_checkpoint_policy.val_f2_parasitized_selected, run_checkpoint_policy.val_specificity_selected, run_checkpoint_policy.val_auc_selected, run_checkpoint_policy.val_pr_auc_selected, run_checkpoint_policy.val_balanced_accuracy_selected, run_checkpoint_policy.prediction_collapse_detected, run_checkpoint_policy.all_epochs_collapsed, run_checkpoint_policy.checkpoint_warning, run_checkpoint_policy.checkpoint_path, run_checkpoint_policy.checkpoint_policy_summary_path, run_checkpoint_policy.model_metadata_path, run_checkpoint_policy.created_at, run_checkpoint_policy.metadata FROM run_checkpoint_policy ORDER BY run_checkpoint_policy.run_id, run_checkpoint_policy.created_at DESC), latest_threshold AS (SELECT DISTINCT ON (run_threshold_calibration.run_id) run_threshold_calibration.run_threshold_calibration_id, run_threshold_calibration.run_id, run_threshold_calibration.model_name, run_threshold_calibration.threshold_policy, run_threshold_calibration.threshold_source, run_threshold_calibration.threshold_selected, run_threshold_calibration.default_threshold, run_threshold_calibration.target_recall, run_threshold_calibration.target_recall_satisfied, run_threshold_calibration.min_specificity, run_threshold_calibration.validation_recall_at_threshold, run_threshold_calibration.validation_specificity_at_threshold, run_threshold_calibration.validation_precision_at_threshold, run_threshold_calibration.validation_f1_at_threshold, run_threshold_calibration.validation_f2_at_threshold, run_threshold_calibration.validation_balanced_accuracy_at_threshold, run_threshold_calibration.validation_pr_auc, run_threshold_calibration.validation_roc_auc, run_threshold_calibration.default_threshold_metrics, run_threshold_calibration.selected_threshold_metrics, run_threshold_calibration.candidate_count, run_threshold_calibration.threshold_warning, run_threshold_calibration.calibration_split, run_threshold_calibration.threshold_calibration_path, run_threshold_calibration.model_metadata_path, run_threshold_calibration.created_at, run_threshold_calibration.metadata FROM run_threshold_calibration ORDER BY run_threshold_calibration.run_id, run_threshold_calibration.created_at DESC) SELECT r.id AS run_id, r.run_name, r.run_type, r.script_name, COALESCE(lm.model_name, lc.model_name, lt.model_name, lio.model_name, m.name) AS model_name, r.started_at, r.finished_at, r.status, lc.checkpoint_policy, COALESCE(lm.threshold_source, lt.threshold_source) AS threshold_source, COALESCE(lm.threshold_used, lt.threshold_selected) AS threshold_used, lt.target_recall, lm.accuracy, lm.recall_parasitized, lm.specificity, lm.f2_parasitized, lm.pr_auc_parasitized, lm.roc_auc_parasitized, lm.balanced_accuracy, CASE lower(COALESCE(lm.prediction_collapse ->> CAST('collapsed' AS text), lm.metadata ->> CAST('prediction_collapse_detected' AS text))) WHEN CAST('true' AS text) THEN TRUE WHEN CAST('t' AS text) THEN TRUE WHEN CAST('1' AS text) THEN TRUE WHEN CAST('false' AS text) THEN FALSE WHEN CAST('f' AS text) THEN FALSE WHEN CAST('0' AS text) THEN FALSE ELSE CAST(NULL AS boolean) END AS prediction_collapse_detected, lc.checkpoint_warning, lt.threshold_warning, lio.clinical_metadata, lio.output_results FROM runs AS r LEFT JOIN models AS m ON m.id = r.model_id LEFT JOIN latest_io AS lio ON lio.run_id = r.id LEFT JOIN latest_metrics AS lm ON lm.run_id = r.id LEFT JOIN latest_checkpoint AS lc ON lc.run_id = r.id LEFT JOIN latest_threshold AS lt ON lt.run_id = r.id;

CREATE VIEW public.vw_dataset_browser_images AS SELECT dsi.image_id, dsi.dataset_id, dsi.dataset_name, dsi.dataset_source, COALESCE(d.url, d.metadata ->> CAST('source_url' AS text)) AS source_url, dsi.dataset_dir, dsi.split_name, CASE WHEN dsi.split_name = CAST('val' AS text) THEN CAST('validation' AS text) ELSE dsi.split_name END AS display_split_name, dsi.class_name, dsi.class_index, dsi.relative_path, dsi.absolute_path, dsi.filename, dsi.original_tfds_label, dsi.project_label, dsi.image_width, dsi.image_height, dsi.file_size_bytes, dsi.checksum_sha256, dsi.label_mapping_version, dsi.created_at, dsi.updated_at, dsi.metadata FROM dataset_split_images AS dsi LEFT JOIN datasets AS d ON d.id = dsi.dataset_id;

CREATE VIEW public.vw_dataset_browser_summary AS SELECT dsi.dataset_id, dsi.dataset_name, dsi.dataset_source, COALESCE(d.url, d.metadata ->> CAST('source_url' AS text)) AS source_url, COALESCE(d.description, d.metadata ->> CAST('description' AS text)) AS description, dsi.dataset_dir, COALESCE(d.metadata ->> CAST('split_type' AS text), dsi.metadata ->> CAST('split_type' AS text), CAST('physical_stratified_split' AS text)) AS split_type, CAST(NULLIF(COALESCE(d.metadata ->> CAST('train_ratio' AS text), dsi.metadata ->> CAST('train_ratio' AS text)), CAST('' AS text)) AS numeric) AS train_ratio, CAST(NULLIF(COALESCE(d.metadata ->> CAST('val_ratio' AS text), dsi.metadata ->> CAST('val_ratio' AS text)), CAST('' AS text)) AS numeric) AS val_ratio, CAST(NULLIF(COALESCE(d.metadata ->> CAST('test_ratio' AS text), dsi.metadata ->> CAST('test_ratio' AS text)), CAST('' AS text)) AS numeric) AS test_ratio, CAST(NULLIF(COALESCE(d.metadata ->> CAST('seed' AS text), dsi.metadata ->> CAST('seed' AS text)), CAST('' AS text)) AS integer) AS seed, dsi.label_mapping_version, dsi.split_name, CASE WHEN dsi.split_name = CAST('val' AS text) THEN CAST('validation' AS text) ELSE dsi.split_name END AS display_split_name, dsi.class_name, dsi.class_index, count(*) AS image_count, min(dsi.created_at) AS first_registered_at, max(dsi.updated_at) AS last_updated_at, COALESCE(d.metadata, CAST('{}' AS jsonb)) AS dataset_metadata FROM dataset_split_images AS dsi LEFT JOIN datasets AS d ON d.id = dsi.dataset_id GROUP BY dsi.dataset_id, dsi.dataset_name, dsi.dataset_source, COALESCE(d.url, d.metadata ->> CAST('source_url' AS text)), COALESCE(d.description, d.metadata ->> CAST('description' AS text)), dsi.dataset_dir, COALESCE(d.metadata ->> CAST('split_type' AS text), dsi.metadata ->> CAST('split_type' AS text), CAST('physical_stratified_split' AS text)), CAST(NULLIF(COALESCE(d.metadata ->> CAST('train_ratio' AS text), dsi.metadata ->> CAST('train_ratio' AS text)), CAST('' AS text)) AS numeric), CAST(NULLIF(COALESCE(d.metadata ->> CAST('val_ratio' AS text), dsi.metadata ->> CAST('val_ratio' AS text)), CAST('' AS text)) AS numeric), CAST(NULLIF(COALESCE(d.metadata ->> CAST('test_ratio' AS text), dsi.metadata ->> CAST('test_ratio' AS text)), CAST('' AS text)) AS numeric), CAST(NULLIF(COALESCE(d.metadata ->> CAST('seed' AS text), dsi.metadata ->> CAST('seed' AS text)), CAST('' AS text)) AS integer), dsi.label_mapping_version, dsi.split_name, dsi.class_name, dsi.class_index, COALESCE(d.metadata, CAST('{}' AS jsonb));

CREATE VIEW public.vw_dataset_split_images_summary AS SELECT dataset_name, dataset_source, dataset_dir, CASE WHEN split_name = CAST('val' AS text) THEN CAST('validation' AS text) ELSE split_name END AS display_split_name, split_name, class_name, class_index, count(*) AS image_count, sum(file_size_bytes) AS total_file_size_bytes, min(created_at) AS first_registered_at, max(updated_at) AS last_updated_at FROM dataset_split_images GROUP BY dataset_name, dataset_source, dataset_dir, split_name, class_name, class_index;

CREATE VIEW public.vw_explainability_summary AS SELECT run_id, method, count(*) AS total_explanations, count(*) FILTER (WHERE success IS TRUE) AS successful_explanations, count(*) FILTER (WHERE success IS FALSE) AS failed_explanations, count(*) FILTER (WHERE case_type = CAST('true_positive' AS text)) AS true_positive_count, count(*) FILTER (WHERE case_type = CAST('true_negative' AS text)) AS true_negative_count, count(*) FILTER (WHERE case_type = CAST('false_positive' AS text)) AS false_positive_count, count(*) FILTER (WHERE case_type = CAST('false_negative' AS text)) AS false_negative_count, count(*) FILTER (WHERE case_type = CAST('low_confidence' AS text)) AS low_confidence_count FROM explainability_results GROUP BY run_id, method;

CREATE VIEW public.vw_model_run_summary AS SELECT m.id AS model_id, m.name AS model_name, m.model_type, count(DISTINCT r.id) AS total_runs, count(DISTINCT r.id) FILTER (WHERE r.status = CAST('completed' AS text)) AS completed_runs, count(DISTINCT r.id) FILTER (WHERE r.status = CAST('failed' AS text)) AS failed_runs, max(r.started_at) AS last_run_at, max(rm.metric_value) FILTER (WHERE rm.metric_name = ANY(ARRAY[CAST('accuracy' AS text), CAST('test_accuracy' AS text), CAST('val_accuracy' AS text)])) AS best_accuracy, max(rm.metric_value) FILTER (WHERE rm.metric_name = ANY(ARRAY[CAST('recall' AS text), CAST('recall_macro' AS text), CAST('sensitivity' AS text), CAST('test_recall' AS text)])) AS best_recall, max(rm.metric_value) FILTER (WHERE rm.metric_name = ANY(ARRAY[CAST('f1_score' AS text), CAST('f1_macro' AS text), CAST('test_f1' AS text)])) AS best_f1_score, max(rm.metric_value) FILTER (WHERE rm.metric_name = ANY(ARRAY[CAST('auc' AS text), CAST('test_auc' AS text), CAST('val_auc' AS text)])) AS best_auc FROM models AS m LEFT JOIN runs AS r ON r.model_id = m.id LEFT JOIN run_metrics AS rm ON rm.run_id = r.id GROUP BY m.id, m.name, m.model_type;

CREATE VIEW public.vw_run_artifacts_summary AS SELECT run_id, artifact_type, path AS artifact_path, CASE lower(COALESCE(metadata ->> CAST('exists' AS text), CAST('true' AS text))) WHEN CAST('true' AS text) THEN TRUE WHEN CAST('t' AS text) THEN TRUE WHEN CAST('1' AS text) THEN TRUE WHEN CAST('false' AS text) THEN FALSE WHEN CAST('f' AS text) THEN FALSE WHEN CAST('0' AS text) THEN FALSE ELSE TRUE END AS exists, created_at, name, mime_type, file_size_bytes, metadata FROM artifacts AS a;

CREATE VIEW public.vw_run_dashboard AS SELECT r.id AS run_id, r.run_name, r.run_type, r.status, m.name AS model_name, d.name AS dataset_name, r.started_at, r.finished_at, r.duration_seconds, max(rm.metric_value) FILTER (WHERE rm.metric_name = ANY(ARRAY[CAST('accuracy' AS text), CAST('test_accuracy' AS text), CAST('val_accuracy' AS text)])) AS accuracy, max(rm.metric_value) FILTER (WHERE rm.metric_name = ANY(ARRAY[CAST('precision' AS text), CAST('precision_macro' AS text), CAST('test_precision' AS text)])) AS precision, max(rm.metric_value) FILTER (WHERE rm.metric_name = ANY(ARRAY[CAST('recall' AS text), CAST('recall_macro' AS text), CAST('sensitivity' AS text), CAST('test_recall' AS text)])) AS recall, max(rm.metric_value) FILTER (WHERE rm.metric_name = ANY(ARRAY[CAST('f1_score' AS text), CAST('f1_macro' AS text), CAST('test_f1' AS text)])) AS f1_score, max(rm.metric_value) FILTER (WHERE rm.metric_name = ANY(ARRAY[CAST('auc' AS text), CAST('test_auc' AS text), CAST('val_auc' AS text)])) AS auc, substring(r.command, CAST('--optimizer(?:[[:space:]]+|=)([^[:space:]]+)' AS text)) AS optimizer FROM runs AS r LEFT JOIN models AS m ON m.id = r.model_id LEFT JOIN datasets AS d ON d.id = r.dataset_id LEFT JOIN run_metrics AS rm ON rm.run_id = r.id GROUP BY r.id, r.run_name, r.run_type, r.status, m.name, d.name, r.started_at, r.finished_at, r.duration_seconds;

CREATE VIEW public.vw_run_dataset_usage_summary AS SELECT rdi.run_id, r.script_name, m.name AS model_name, r.run_type, dsi.dataset_name, dsi.dataset_source, dsi.dataset_dir, count(*) FILTER (WHERE rdi.split_name = CAST('train' AS text)) AS train_images_count, count(*) FILTER (WHERE rdi.split_name = ANY(ARRAY[CAST('val' AS text), CAST('validation' AS text)])) AS val_images_count, count(*) FILTER (WHERE rdi.split_name = CAST('test' AS text)) AS test_images_count, count(*) FILTER (WHERE rdi.class_name = CAST('uninfected' AS text)) AS uninfected_count, count(*) FILTER (WHERE rdi.class_name = CAST('parasitized' AS text)) AS parasitized_count, count(*) FILTER (WHERE rdi.usage_context = CAST('explainability' AS text)) AS explained_images_count, min(rdi.created_at) AS created_at, max(rdi.created_at) AS last_recorded_at FROM run_dataset_images AS rdi INNER JOIN runs AS r ON r.id = rdi.run_id LEFT JOIN models AS m ON m.id = r.model_id INNER JOIN dataset_split_images AS dsi ON dsi.image_id = rdi.image_id GROUP BY rdi.run_id, r.script_name, m.name, r.run_type, dsi.dataset_name, dsi.dataset_source, dsi.dataset_dir;

CREATE VIEW public.vw_run_image_predictions_summary AS SELECT run_id, split_name, usage_context, filename, relative_path, true_label_name, predicted_label_name, probability_parasitized, threshold_used, threshold_source, case_type, is_correct, created_at FROM run_image_predictions AS rip;

CREATE VIEW public.vw_run_io_summary AS SELECT rio.run_io_id, rio.run_id, r.run_name, r.run_type, r.status AS run_status, m.name AS model_name, rio.script_name, COALESCE(rio.command, r.command) AS command, rio.input_parameters, rio.output_results, rio.output_artifacts, rio.dataset_metadata, rio.label_mapping_version, rio.raw_model_score_meaning, rio.created_at, rio.metadata FROM run_io_records AS rio LEFT JOIN runs AS r ON r.id = rio.run_id LEFT JOIN models AS m ON m.id = r.model_id;

CREATE VIEW public.vw_run_lineage AS SELECT child_run.id AS child_run_id, child_run.run_name AS child_run_name, child_run.run_type AS child_run_type, child_run.status AS child_status, child_run.started_at AS child_started_at, parent_run.id AS parent_run_id, parent_run.run_name AS parent_run_name, parent_run.run_type AS parent_run_type, parent_run.status AS parent_status, parent_run.started_at AS parent_started_at, lineage.relationship_type, lineage.confidence, lineage.checkpoint_path, COALESCE(parent_model.name, NULLIF(parent_run.execution_parameters ->> CAST('model_name' AS text), CAST('' AS text)), NULLIF(parent_run.execution_parameters ->> CAST('model' AS text), CAST('' AS text)), NULLIF(parent_run.parameters ->> CAST('model_name' AS text), CAST('' AS text)), NULLIF(parent_run.parameters ->> CAST('model' AS text), CAST('' AS text)), NULLIF(parent_run.metadata ->> CAST('model_name' AS text), CAST('' AS text))) AS parent_model_name, COALESCE(NULLIF(parent_run.execution_parameters ->> CAST('optimizer' AS text), CAST('' AS text)), NULLIF(parent_run.execution_parameters #>> CAST('{cli_arguments,optimizer}' AS text[]), CAST('' AS text)), NULLIF(parent_run.parameters ->> CAST('optimizer' AS text), CAST('' AS text)), NULLIF(parent_run.parameters #>> CAST('{execution_parameters,optimizer}' AS text[]), CAST('' AS text)), NULLIF(parent_run.parameters #>> CAST('{cli_arguments,optimizer}' AS text[]), CAST('' AS text)), NULLIF(parent_run.metadata ->> CAST('optimizer' AS text), CAST('' AS text)), substring(parent_run.command, CAST('--optimizer[[:space:]=]+([^[:space:]]+)' AS text))) AS parent_optimizer, parent_run.command AS parent_command, child_run.command AS child_command FROM run_lineage AS lineage INNER JOIN runs AS child_run ON child_run.id = lineage.child_run_id INNER JOIN runs AS parent_run ON parent_run.id = lineage.parent_run_id LEFT JOIN models AS parent_model ON parent_model.id = parent_run.model_id;

CREATE VIEW public.vw_threshold_calibration_summary AS SELECT run_id, model_name, threshold_policy, threshold_source, threshold_selected, default_threshold, target_recall, target_recall_satisfied, validation_recall_at_threshold, validation_specificity_at_threshold, validation_f2_at_threshold, validation_pr_auc, validation_roc_auc, threshold_warning, calibration_split, created_at FROM run_threshold_calibration AS rtc;

CREATE VIEW public.vw_uploaded_predictions AS SELECT p.id AS prediction_id, p.run_id, r.experiment_id, r.model_id, m.name AS model_name, m.model_type, r.run_name, r.run_type, r.status AS run_status, r.script_name, r.command, r.started_at, r.finished_at, r.duration_seconds, p.dataset_id, d.name AS dataset_name, p.image_id, p.image_path, a.id AS artifact_id, a.path AS artifact_path, a.name AS artifact_name, a.mime_type, a.file_size_bytes, a.checksum, p.true_label, p.predicted_label, p.score, p.score_positive_label, p.threshold, p.is_correct, p.case_type, p.created_at, p.metadata AS prediction_metadata, a.metadata AS artifact_metadata, r.parameters, r.metadata AS run_metadata, COALESCE(p.metadata ->> CAST('source' AS text), a.metadata ->> CAST('source' AS text)) AS source, COALESCE(p.metadata ->> CAST('original_image_path' AS text), a.metadata ->> CAST('original_image_path' AS text)) AS original_image_path, COALESCE(p.metadata ->> CAST('original_filename' AS text), a.metadata ->> CAST('original_filename' AS text)) AS original_filename, COALESCE(p.metadata ->> CAST('stored_filename' AS text), a.metadata ->> CAST('stored_filename' AS text), a.name) AS stored_filename, COALESCE(CAST(NULLIF(p.metadata ->> CAST('probability_parasitized' AS text), CAST('' AS text)) AS numeric), p.score_positive_label) AS probability_parasitized, CAST(NULLIF(p.metadata ->> CAST('probability_uninfected' AS text), CAST('' AS text)) AS numeric) AS probability_uninfected, p.metadata ->> CAST('confidence_level' AS text) AS confidence_level, p.metadata ->> CAST('decision' AS text) AS decision, COALESCE(CAST(NULLIF(p.metadata ->> CAST('tta' AS text), CAST('' AS text)) AS boolean), CAST(NULLIF(r.parameters ->> CAST('tta' AS text), CAST('' AS text)) AS boolean), FALSE) AS tta, CAST(NULLIF(COALESCE(p.metadata ->> CAST('n_aug' AS text), r.parameters ->> CAST('n_aug' AS text)), CAST('' AS text)) AS integer) AS n_aug, er.method AS explainability_method, er.output_path AS explainability_path, er.success AS explainability_success FROM predictions AS p LEFT JOIN runs AS r ON r.id = p.run_id LEFT JOIN models AS m ON m.id = r.model_id LEFT JOIN datasets AS d ON d.id = p.dataset_id LEFT JOIN LATERAL (SELECT art.id, art.run_id, art.artifact_type, art.name, art.path, art.mime_type, art.file_size_bytes, art.checksum, art.created_at, art.metadata FROM artifacts AS art WHERE art.run_id = p.run_id AND (art.path = p.image_path OR art.artifact_type = CAST('uploaded_input_image' AS text) OR (art.metadata ->> CAST('source' AS text)) = CAST('uploaded_for_prediction' AS text)) ORDER BY art.path = p.image_path DESC, art.artifact_type = CAST('uploaded_input_image' AS text) DESC, art.created_at DESC LIMIT 1) AS a ON TRUE LEFT JOIN LATERAL (SELECT exp.id, exp.run_id, exp.prediction_id, exp.method, exp.image_path, exp.output_path, exp.true_label, exp.predicted_label, exp.score, exp.case_type, exp.last_conv_layer, exp.explanation_parameters, exp.success, exp.error_message, exp.created_at, exp.metadata FROM explainability_results AS exp WHERE exp.run_id = p.run_id AND (exp.prediction_id = p.id OR exp.image_path = p.image_path) ORDER BY exp.created_at DESC LIMIT 1) AS er ON TRUE WHERE (p.metadata ->> CAST('source' AS text)) = CAST('uploaded_for_prediction' AS text) OR (a.metadata ->> CAST('source' AS text)) = CAST('uploaded_for_prediction' AS text) OR a.artifact_type = CAST('uploaded_input_image' AS text);

CREATE VIEW public.vw_v2_external_evidence AS SELECT e.id AS evaluation_id, e.run_id, e.training_run_id, e.model_version_id, e.checkpoint_artifact_id, e.split, e.purpose, e.evaluation_role, e.dataset_version_id, e.dataset_origin_id, e.dataset_origin_role, e.population_hash, e.population_manifest_uri, e.population_manifest_sha256, e.dataset_provenance_uri, e.dataset_provenance_sha256, e.protocol_version, e.protocol_hash, e.protocol_snapshot, e.comparison_contract_hash, e.input_contract_hash, e.source_kind, e.source_record_phase, e.source_record_key, e.threshold_used, e.threshold_source, e.metric_definition, m.tp, m.fp, m.fn, m.tn, m.sample_count, m.accuracy, m.recall_parasitized, m.specificity, m.precision_parasitized, m.f1_parasitized, m.f2_parasitized, m.balanced_accuracy, m.roc_auc_parasitized, m.pr_auc_parasitized, m.auc_unavailability_reason, e.created_at FROM public.evaluations AS e INNER JOIN public.run_clinical_metrics AS m ON m.evaluation_id = e.id WHERE e.split = 'external';

CREATE VIEW public.vw_v2_model_comparison AS SELECT e.id AS evaluation_id, e.dataset_version_id, e.split, e.evaluation_role, e.purpose, e.subject_kind, e.protocol_version, e.protocol_hash, e.population_hash, e.comparison_contract_hash, e.input_contract_hash, CASE WHEN e.subject_kind = 'single' THEN COALESCE(e.model_version_id, mv.id) END AS model_version_id, e.training_run_id, e.run_id, e.threshold_used, e.threshold_source, CASE WHEN e.subject_kind = 'single' THEN c.architecture END AS architecture, CASE WHEN e.subject_kind = 'single' THEN c.optimizer END AS optimizer, CASE WHEN e.subject_kind = 'single' THEN c.learning_rate END AS learning_rate, CASE WHEN e.subject_kind = 'single' THEN c.batch_size END AS batch_size, CASE WHEN e.subject_kind = 'single' THEN c.random_seed END AS random_seed, CASE WHEN e.subject_kind = 'single' THEN c.configuration_hash END AS configuration_hash, m.recall_parasitized AS recall, m.specificity, m.precision_parasitized AS precision, m.f1_parasitized AS f1, m.f2_parasitized AS f2, m.balanced_accuracy, m.roc_auc_parasitized AS roc_auc, m.pr_auc_parasitized AS pr_auc, m.tp, m.fp, m.fn, m.tn, m.sample_count, r.duration_seconds, r.status, r.campaign_id, e.created_at FROM public.evaluations AS e INNER JOIN public.run_clinical_metrics AS m ON m.evaluation_id = e.id INNER JOIN public.runs AS r ON r.id = e.training_run_id INNER JOIN public.run_configurations AS c ON c.run_id = r.id LEFT JOIN public.model_versions AS mv ON mv.training_run_id = e.training_run_id AND mv.checkpoint_artifact_id = e.checkpoint_artifact_id WHERE e.split IN ('train', 'val', 'test');

CREATE VIEW public.vw_v2_run_metrics AS SELECT id, run_id, metric_name, metric_value, metric_unit, split_name, class_name, step, epoch, created_at, metadata FROM public.run_metrics UNION ALL SELECT m.run_clinical_metric_id, m.run_id, k.name, k.value, CAST('ratio' AS text), m.split_name, CAST('parasitized' AS text), CAST(NULL AS integer), CAST(NULL AS integer), m.created_at, jsonb_build_object('evaluation_id', m.evaluation_id, 'metric_definition', 'binary_nullable_v2') FROM public.run_clinical_metrics AS m CROSS JOIN LATERAL ((VALUES ('recall', m.recall_parasitized), ('specificity', m.specificity), ('precision', m.precision_parasitized), ('f1', m.f1_parasitized), ('f2', m.f2_parasitized), ('balanced_accuracy', m.balanced_accuracy), ('roc_auc', m.roc_auc_parasitized), ('pr_auc', m.pr_auc_parasitized))) AS k (name, value);

CREATE VIEW public.vw_v2_xai_comparison AS SELECT x.id, mc.method, mc.implementation_version AS method_version, mc.implementation AS implementation_path, x.model_version_id, x.checkpoint_artifact_id, x.evaluation_id, x.input_sha256, x.input_contract_hash, x.target_class, x.explained_output, mc.configuration_hash, x.generated_at, a.id AS artifact_id, a.role, a.storage_uri, a.sha256, a.availability FROM public.xai_evidence AS x JOIN public.xai_method_configurations mc ON mc.id=x.method_configuration_id LEFT JOIN public.xai_artifacts AS a ON a.evidence_id = x.id;

CREATE VIEW public.vw_visual_explainability_audit AS WITH audit_source AS (SELECT er.id AS explainability_id, er.prediction_id, er.run_id, r.experiment_id, r.model_id, m.name AS model_name, m.model_type, COALESCE(dsi.dataset_id, p.dataset_id, r.dataset_id) AS dataset_id, COALESCE(dsi.dataset_name, d.name) AS dataset_name, COALESCE(dsi.dataset_source, d.source, NULLIF(p.metadata ->> CAST('source' AS text), CAST('' AS text)), NULLIF(r.parameters ->> CAST('dataset_source' AS text), CAST('' AS text))) AS dataset_source, COALESCE(NULLIF(p.metadata ->> CAST('dataset_split' AS text), CAST('' AS text)), NULLIF(p.metadata ->> CAST('split_name' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('dataset_split' AS text), CAST('' AS text)), rdi.split_name, NULLIF(r.parameters ->> CAST('dataset_split' AS text), CAST('' AS text)), NULLIF(r.parameters ->> CAST('split_name' AS text), CAST('' AS text))) AS dataset_split, CASE WHEN COALESCE(NULLIF(p.metadata ->> CAST('dataset_index' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('dataset_index' AS text), CAST('' AS text))) ~ CAST('^[0-9]+$' AS text) THEN CAST(COALESCE(NULLIF(p.metadata ->> CAST('dataset_index' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('dataset_index' AS text), CAST('' AS text))) AS bigint) ELSE CAST(rdi.sample_index AS bigint) END AS dataset_index, COALESCE(NULLIF(p.metadata ->> CAST('manifest_id' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('manifest_id' AS text), CAST('' AS text)), NULLIF(rdi.metadata ->> CAST('manifest_id' AS text), CAST('' AS text)), NULLIF(dsi.metadata ->> CAST('manifest_id' AS text), CAST('' AS text)), CAST(dsi.image_id AS text)) AS manifest_id, dsi.image_id AS dataset_image_id, COALESCE(CASE WHEN COALESCE(NULLIF(p.metadata ->> CAST('original_tfds_label' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('original_tfds_label' AS text), CAST('' AS text))) ~ CAST('^[+-]?[0-9]+$' AS text) THEN CAST(COALESCE(NULLIF(p.metadata ->> CAST('original_tfds_label' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('original_tfds_label' AS text), CAST('' AS text))) AS integer) ELSE CAST(NULL AS integer) END, dsi.original_tfds_label) AS original_tfds_label, COALESCE(CASE WHEN COALESCE(NULLIF(p.metadata ->> CAST('project_label' AS text), CAST('' AS text)), NULLIF(p.metadata ->> CAST('remapped_label' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('project_label' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('remapped_label' AS text), CAST('' AS text))) ~ CAST('^[+-]?[0-9]+$' AS text) THEN CAST(COALESCE(NULLIF(p.metadata ->> CAST('project_label' AS text), CAST('' AS text)), NULLIF(p.metadata ->> CAST('remapped_label' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('project_label' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('remapped_label' AS text), CAST('' AS text))) AS integer) ELSE CAST(NULL AS integer) END, dsi.project_label) AS project_label, COALESCE(CASE WHEN COALESCE(NULLIF(p.metadata ->> CAST('remapped_label' AS text), CAST('' AS text)), NULLIF(p.metadata ->> CAST('project_label' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('remapped_label' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('project_label' AS text), CAST('' AS text))) ~ CAST('^[+-]?[0-9]+$' AS text) THEN CAST(COALESCE(NULLIF(p.metadata ->> CAST('remapped_label' AS text), CAST('' AS text)), NULLIF(p.metadata ->> CAST('project_label' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('remapped_label' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('project_label' AS text), CAST('' AS text))) AS integer) ELSE CAST(NULL AS integer) END, dsi.project_label) AS remapped_label, COALESCE(NULLIF(dsi.label_mapping_version, CAST('' AS text)), NULLIF(p.metadata ->> CAST('label_mapping_version' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('label_mapping_version' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('label_mapping_version' AS text), CAST('' AS text)), NULLIF(r.parameters ->> CAST('label_mapping_version' AS text), CAST('' AS text))) AS label_mapping_version, r.run_name, r.run_type, r.status AS run_status, r.script_name, r.command, r.started_at, r.finished_at, er.created_at, p.created_at AS prediction_created_at, er.method, COALESCE(er.true_label, p.true_label) AS true_label, COALESCE(er.predicted_label, p.predicted_label) AS predicted_label, COALESCE(NULLIF(p.metadata ->> CAST('positive_label' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('positive_label' AS text), CAST('' AS text)), NULLIF(r.parameters ->> CAST('positive_label' AS text), CAST('' AS text)), NULLIF(r.parameters ->> CAST('positive_class_name' AS text), CAST('' AS text)), CAST('parasitized' AS text)) AS positive_label, COALESCE(NULLIF(er.case_type, CAST('' AS text)), NULLIF(p.case_type, CAST('' AS text)), CAST('unknown' AS text)) AS recorded_case_type, COALESCE(p.score, er.score) AS score, COALESCE(CASE WHEN (NULLIF(p.metadata ->> CAST('probability_parasitized' AS text), CAST('' AS text))) ~ CAST('^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$' AS text) THEN CAST(p.metadata ->> CAST('probability_parasitized' AS text) AS numeric) ELSE CAST(NULL AS numeric) END, p.score_positive_label, CASE WHEN (NULLIF(er.metadata ->> CAST('probability_parasitized' AS text), CAST('' AS text))) ~ CAST('^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$' AS text) THEN CAST(er.metadata ->> CAST('probability_parasitized' AS text) AS numeric) ELSE CAST(NULL AS numeric) END, er.score) AS probability_parasitized, COALESCE(CASE WHEN (NULLIF(p.metadata ->> CAST('probability_uninfected' AS text), CAST('' AS text))) ~ CAST('^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$' AS text) THEN CAST(p.metadata ->> CAST('probability_uninfected' AS text) AS numeric) ELSE CAST(NULL AS numeric) END, CASE WHEN (NULLIF(er.metadata ->> CAST('probability_uninfected' AS text), CAST('' AS text))) ~ CAST('^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$' AS text) THEN CAST(er.metadata ->> CAST('probability_uninfected' AS text) AS numeric) ELSE CAST(NULL AS numeric) END, CASE WHEN (NULLIF(r.parameters ->> CAST('probability_uninfected' AS text), CAST('' AS text))) ~ CAST('^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$' AS text) THEN CAST(r.parameters ->> CAST('probability_uninfected' AS text) AS numeric) ELSE CAST(NULL AS numeric) END) AS recorded_probability_uninfected, COALESCE(p.threshold, CASE WHEN (NULLIF(er.explanation_parameters ->> CAST('threshold_used' AS text), CAST('' AS text))) ~ CAST('^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$' AS text) THEN CAST(er.explanation_parameters ->> CAST('threshold_used' AS text) AS numeric) ELSE CAST(NULL AS numeric) END, CASE WHEN (NULLIF(er.explanation_parameters ->> CAST('threshold' AS text), CAST('' AS text))) ~ CAST('^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$' AS text) THEN CAST(er.explanation_parameters ->> CAST('threshold' AS text) AS numeric) ELSE CAST(NULL AS numeric) END, CASE WHEN (NULLIF(r.parameters ->> CAST('threshold_used' AS text), CAST('' AS text))) ~ CAST('^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$' AS text) THEN CAST(r.parameters ->> CAST('threshold_used' AS text) AS numeric) ELSE CAST(NULL AS numeric) END, CASE WHEN (NULLIF(r.parameters ->> CAST('threshold' AS text), CAST('' AS text))) ~ CAST('^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$' AS text) THEN CAST(r.parameters ->> CAST('threshold' AS text) AS numeric) ELSE CAST(NULL AS numeric) END, rtc.threshold_selected, 0.5) AS threshold_used, COALESCE(NULLIF(p.metadata ->> CAST('threshold_source' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('threshold_source' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('threshold_source' AS text), CAST('' AS text)), NULLIF(r.parameters ->> CAST('threshold_source' AS text), CAST('' AS text)), NULLIF(r.metadata ->> CAST('threshold_source' AS text), CAST('' AS text)), rtc.threshold_source, CAST('fixed_cli' AS text)) AS threshold_source, p.is_correct, p.image_id, COALESCE(NULLIF(er.image_path, CAST('' AS text)), NULLIF(p.image_path, CAST('' AS text)), NULLIF(p.metadata ->> CAST('crop_path' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('crop_path' AS text), CAST('' AS text)), NULLIF(dsi.absolute_path, CAST('' AS text)), CASE WHEN dsi.dataset_dir IS NOT NULL AND dsi.relative_path IS NOT NULL THEN concat(rtrim(dsi.dataset_dir, CAST('/' AS text)), '/', ltrim(dsi.relative_path, CAST('/' AS text))) ELSE CAST(NULL AS text) END) AS image_path, COALESCE(NULLIF(p.metadata ->> CAST('source_image_path' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('source_image_path' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('source_image_path' AS text), CAST('' AS text)), NULLIF(dsi.absolute_path, CAST('' AS text)), CASE WHEN dsi.dataset_dir IS NOT NULL AND dsi.relative_path IS NOT NULL THEN concat(rtrim(dsi.dataset_dir, CAST('/' AS text)), '/', ltrim(dsi.relative_path, CAST('/' AS text))) ELSE CAST(NULL AS text) END, NULLIF(p.image_path, CAST('' AS text)), NULLIF(er.image_path, CAST('' AS text)), NULLIF(sa.path, CAST('' AS text)), NULLIF(p.metadata ->> CAST('original_image_path' AS text), CAST('' AS text)), NULLIF(sa.metadata ->> CAST('original_image_path' AS text), CAST('' AS text))) AS source_image_path, COALESCE(NULLIF(p.metadata ->> CAST('original_image_path' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('original_image_path' AS text), CAST('' AS text)), NULLIF(sa.metadata ->> CAST('original_image_path' AS text), CAST('' AS text)), NULLIF(dsi.absolute_path, CAST('' AS text))) AS original_image_path, COALESCE(NULLIF(p.metadata ->> CAST('original_filename' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('original_filename' AS text), CAST('' AS text)), NULLIF(sa.metadata ->> CAST('original_filename' AS text), CAST('' AS text)), dsi.filename, sa.name) AS original_filename, COALESCE(NULLIF(p.metadata ->> CAST('image_stored_path' AS text), CAST('' AS text)), NULLIF(p.metadata ->> CAST('stored_image_path' AS text), CAST('' AS text)), NULLIF(p.image_path, CAST('' AS text)), NULLIF(sa.path, CAST('' AS text))) AS image_stored_path, COALESCE(NULLIF(p.metadata ->> CAST('crop_path' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('crop_path' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('crop_path' AS text), CAST('' AS text)), NULLIF(p.image_path, CAST('' AS text)), NULLIF(er.image_path, CAST('' AS text)), NULLIF(dsi.absolute_path, CAST('' AS text)), CASE WHEN dsi.dataset_dir IS NOT NULL AND dsi.relative_path IS NOT NULL THEN concat(rtrim(dsi.dataset_dir, CAST('/' AS text)), '/', ltrim(dsi.relative_path, CAST('/' AS text))) ELSE CAST(NULL AS text) END) AS crop_path, COALESCE(NULLIF(p.metadata ->> CAST('source_image_id' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('source_image_id' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('source_image_id' AS text), CAST('' AS text)), CAST(dsi.image_id AS text), CASE WHEN COALESCE(p.metadata ->> CAST('source' AS text), sa.metadata ->> CAST('source' AS text)) = CAST('uploaded_for_prediction' AS text) THEN NULLIF(p.image_id, CAST('' AS text)) ELSE CAST(NULL AS text) END) AS source_image_id, COALESCE(NULLIF(p.metadata ->> CAST('patient_id' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('patient_id' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('patient_id' AS text), CAST('' AS text))) AS patient_id, COALESCE(NULLIF(p.metadata ->> CAST('slide_id' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('slide_id' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('slide_id' AS text), CAST('' AS text))) AS slide_id, CASE WHEN COALESCE(NULLIF(p.metadata ->> CAST('bbox_x' AS text), CAST('' AS text)), NULLIF(p.metadata #>> CAST('{bbox,x}' AS text[]), CAST('' AS text)), NULLIF(er.metadata ->> CAST('bbox_x' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('bbox_x' AS text), CAST('' AS text))) ~ CAST('^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$' AS text) THEN CAST(COALESCE(NULLIF(p.metadata ->> CAST('bbox_x' AS text), CAST('' AS text)), NULLIF(p.metadata #>> CAST('{bbox,x}' AS text[]), CAST('' AS text)), NULLIF(er.metadata ->> CAST('bbox_x' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('bbox_x' AS text), CAST('' AS text))) AS numeric) ELSE CAST(NULL AS numeric) END AS bbox_x, CASE WHEN COALESCE(NULLIF(p.metadata ->> CAST('bbox_y' AS text), CAST('' AS text)), NULLIF(p.metadata #>> CAST('{bbox,y}' AS text[]), CAST('' AS text)), NULLIF(er.metadata ->> CAST('bbox_y' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('bbox_y' AS text), CAST('' AS text))) ~ CAST('^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$' AS text) THEN CAST(COALESCE(NULLIF(p.metadata ->> CAST('bbox_y' AS text), CAST('' AS text)), NULLIF(p.metadata #>> CAST('{bbox,y}' AS text[]), CAST('' AS text)), NULLIF(er.metadata ->> CAST('bbox_y' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('bbox_y' AS text), CAST('' AS text))) AS numeric) ELSE CAST(NULL AS numeric) END AS bbox_y, CASE WHEN COALESCE(NULLIF(p.metadata ->> CAST('bbox_width' AS text), CAST('' AS text)), NULLIF(p.metadata #>> CAST('{bbox,width}' AS text[]), CAST('' AS text)), NULLIF(er.metadata ->> CAST('bbox_width' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('bbox_width' AS text), CAST('' AS text))) ~ CAST('^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$' AS text) THEN CAST(COALESCE(NULLIF(p.metadata ->> CAST('bbox_width' AS text), CAST('' AS text)), NULLIF(p.metadata #>> CAST('{bbox,width}' AS text[]), CAST('' AS text)), NULLIF(er.metadata ->> CAST('bbox_width' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('bbox_width' AS text), CAST('' AS text))) AS numeric) ELSE CAST(NULL AS numeric) END AS bbox_width, CASE WHEN COALESCE(NULLIF(p.metadata ->> CAST('bbox_height' AS text), CAST('' AS text)), NULLIF(p.metadata #>> CAST('{bbox,height}' AS text[]), CAST('' AS text)), NULLIF(er.metadata ->> CAST('bbox_height' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('bbox_height' AS text), CAST('' AS text))) ~ CAST('^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$' AS text) THEN CAST(COALESCE(NULLIF(p.metadata ->> CAST('bbox_height' AS text), CAST('' AS text)), NULLIF(p.metadata #>> CAST('{bbox,height}' AS text[]), CAST('' AS text)), NULLIF(er.metadata ->> CAST('bbox_height' AS text), CAST('' AS text)), NULLIF(er.explanation_parameters ->> CAST('bbox_height' AS text), CAST('' AS text))) AS numeric) ELSE CAST(NULL AS numeric) END AS bbox_height, COALESCE(NULLIF(p.metadata ->> CAST('prediction_upload_id' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('prediction_upload_id' AS text), CAST('' AS text)), NULLIF(sa.metadata ->> CAST('prediction_upload_id' AS text), CAST('' AS text)), NULLIF(sa.metadata ->> CAST('image_id' AS text), CAST('' AS text)), CASE WHEN COALESCE(p.metadata ->> CAST('source' AS text), sa.metadata ->> CAST('source' AS text)) = CAST('uploaded_for_prediction' AS text) THEN CAST(p.id AS text) ELSE CAST(NULL AS text) END) AS prediction_upload_id, CASE WHEN COALESCE(p.metadata ->> CAST('source' AS text), sa.metadata ->> CAST('source' AS text)) = CAST('uploaded_for_prediction' AS text) THEN COALESCE(sa.created_at, p.created_at) ELSE CAST(NULL AS timestamp with time zone) END AS uploaded_at, COALESCE(NULLIF(er.output_path, CAST('' AS text)), NULLIF(ea.path, CAST('' AS text))) AS explanation_output_path, er.last_conv_layer, er.success, er.error_message, COALESCE(er.explanation_parameters, CAST('{}' AS jsonb)) AS explanation_parameters, COALESCE(p.metadata, CAST('{}' AS jsonb)) AS prediction_metadata, COALESCE(er.metadata, CAST('{}' AS jsonb)) AS explainability_metadata, COALESCE(rdi.metadata, CAST('{}' AS jsonb)) AS source_usage_metadata, COALESCE(dsi.metadata, CAST('{}' AS jsonb)) AS source_dataset_metadata, COALESCE(r.parameters, CAST('{}' AS jsonb)) AS run_parameters, COALESCE(r.metadata, CAST('{}' AS jsonb)) AS run_metadata, COALESCE(NULLIF(p.metadata ->> CAST('confidence_level' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('confidence_level' AS text), CAST('' AS text)), NULLIF(r.parameters ->> CAST('confidence_level' AS text), CAST('' AS text))) AS confidence_level, sa.id AS source_artifact_id, sa.path AS source_artifact_path, sa.artifact_type AS source_artifact_type, ea.id AS explanation_artifact_id, ea.path AS explanation_artifact_path, ea.artifact_type AS explanation_artifact_type FROM explainability_results AS er LEFT JOIN predictions AS p ON p.id = er.prediction_id LEFT JOIN runs AS r ON r.id = er.run_id LEFT JOIN models AS m ON m.id = r.model_id LEFT JOIN LATERAL (SELECT linked_rdi.run_dataset_image_id, linked_rdi.run_id, linked_rdi.image_id, linked_rdi.split_name, linked_rdi.usage_context, linked_rdi.class_index, linked_rdi.class_name, linked_rdi.relative_path, linked_rdi.filename, linked_rdi.batch_index, linked_rdi.sample_index, linked_rdi.used_for_training, linked_rdi.used_for_validation, linked_rdi.used_for_test, linked_rdi.created_at, linked_rdi.metadata, linked_dsi.dataset_id, linked_dsi.dataset_name, linked_dsi.dataset_source, linked_dsi.dataset_dir, linked_dsi.absolute_path, linked_dsi.filename AS dataset_filename, linked_dsi.original_tfds_label, linked_dsi.project_label, linked_dsi.label_mapping_version, linked_dsi.metadata AS dataset_metadata FROM run_dataset_images AS linked_rdi INNER JOIN dataset_split_images AS linked_dsi ON linked_dsi.image_id = linked_rdi.image_id WHERE linked_rdi.run_id = er.run_id AND (CAST(linked_rdi.image_id AS text) = COALESCE(NULLIF(p.metadata ->> CAST('dataset_image_id' AS text), CAST('' AS text)), NULLIF(p.metadata ->> CAST('registered_image_id' AS text), CAST('' AS text))) OR linked_rdi.sample_index = CASE WHEN COALESCE(NULLIF(p.metadata ->> CAST('dataset_index' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('dataset_index' AS text), CAST('' AS text))) ~ CAST('^[0-9]+$' AS text) THEN CAST(COALESCE(NULLIF(p.metadata ->> CAST('dataset_index' AS text), CAST('' AS text)), NULLIF(er.metadata ->> CAST('dataset_index' AS text), CAST('' AS text))) AS integer) ELSE CAST(NULL AS integer) END OR (NULLIF(p.image_path, CAST('' AS text))) = linked_dsi.absolute_path OR (NULLIF(p.image_path, CAST('' AS text))) = linked_dsi.relative_path OR (NULLIF(p.image_path, CAST('' AS text))) = concat(rtrim(linked_dsi.dataset_dir, CAST('/' AS text)), '/', ltrim(linked_dsi.relative_path, CAST('/' AS text))) OR (NULLIF(er.image_path, CAST('' AS text))) = linked_dsi.absolute_path OR (NULLIF(er.image_path, CAST('' AS text))) = linked_dsi.relative_path OR (NULLIF(er.image_path, CAST('' AS text))) = concat(rtrim(linked_dsi.dataset_dir, CAST('/' AS text)), '/', ltrim(linked_dsi.relative_path, CAST('/' AS text)))) ORDER BY linked_rdi.usage_context = CAST('explainability' AS text) DESC, linked_rdi.created_at DESC LIMIT 1) AS source_link ON TRUE LEFT JOIN run_dataset_images AS rdi ON rdi.run_dataset_image_id = source_link.run_dataset_image_id LEFT JOIN dataset_split_images AS dsi ON dsi.image_id = source_link.image_id LEFT JOIN datasets AS d ON d.id = COALESCE(dsi.dataset_id, p.dataset_id, r.dataset_id) LEFT JOIN LATERAL (SELECT calibration.threshold_selected, calibration.threshold_source FROM run_threshold_calibration AS calibration WHERE calibration.run_id = er.run_id ORDER BY calibration.created_at DESC LIMIT 1) AS rtc ON TRUE LEFT JOIN LATERAL (SELECT source_artifact.id, source_artifact.run_id, source_artifact.artifact_type, source_artifact.name, source_artifact.path, source_artifact.mime_type, source_artifact.file_size_bytes, source_artifact.checksum, source_artifact.created_at, source_artifact.metadata FROM artifacts AS source_artifact WHERE source_artifact.run_id = er.run_id AND (source_artifact.path = p.image_path OR source_artifact.path = er.image_path OR source_artifact.path = (p.metadata ->> CAST('source_image_path' AS text)) OR source_artifact.path = (p.metadata ->> CAST('crop_path' AS text)) OR source_artifact.artifact_type = CAST('uploaded_input_image' AS text)) ORDER BY source_artifact.path = p.image_path DESC, source_artifact.path = er.image_path DESC, source_artifact.artifact_type = CAST('uploaded_input_image' AS text) DESC, source_artifact.created_at DESC LIMIT 1) AS sa ON TRUE LEFT JOIN LATERAL (SELECT explanation_artifact.id, explanation_artifact.run_id, explanation_artifact.artifact_type, explanation_artifact.name, explanation_artifact.path, explanation_artifact.mime_type, explanation_artifact.file_size_bytes, explanation_artifact.checksum, explanation_artifact.created_at, explanation_artifact.metadata FROM artifacts AS explanation_artifact WHERE explanation_artifact.run_id = er.run_id AND (explanation_artifact.path = er.output_path OR (er.output_path IS NULL AND explanation_artifact.artifact_type = ANY(ARRAY[CAST('gradcam_image' AS text), CAST('lime_image' AS text), CAST('shap_image' AS text)]) AND explanation_artifact.artifact_type = concat(lower(er.method), '_image'))) ORDER BY explanation_artifact.path = er.output_path DESC, explanation_artifact.created_at DESC LIMIT 1) AS ea ON TRUE), classified AS (SELECT audit_source.explainability_id, audit_source.prediction_id, audit_source.run_id, audit_source.experiment_id, audit_source.model_id, audit_source.model_name, audit_source.model_type, audit_source.dataset_id, audit_source.dataset_name, audit_source.dataset_source, audit_source.dataset_split, audit_source.dataset_index, audit_source.manifest_id, audit_source.dataset_image_id, audit_source.original_tfds_label, audit_source.project_label, audit_source.remapped_label, audit_source.label_mapping_version, audit_source.run_name, audit_source.run_type, audit_source.run_status, audit_source.script_name, audit_source.command, audit_source.started_at, audit_source.finished_at, audit_source.created_at, audit_source.prediction_created_at, audit_source.method, audit_source.true_label, audit_source.predicted_label, audit_source.positive_label, audit_source.recorded_case_type, audit_source.score, audit_source.probability_parasitized, audit_source.recorded_probability_uninfected, audit_source.threshold_used, audit_source.threshold_source, audit_source.is_correct, audit_source.image_id, audit_source.image_path, audit_source.source_image_path, audit_source.original_image_path, audit_source.original_filename, audit_source.image_stored_path, audit_source.crop_path, audit_source.source_image_id, audit_source.patient_id, audit_source.slide_id, audit_source.bbox_x, audit_source.bbox_y, audit_source.bbox_width, audit_source.bbox_height, audit_source.prediction_upload_id, audit_source.uploaded_at, audit_source.explanation_output_path, audit_source.last_conv_layer, audit_source.success, audit_source.error_message, audit_source.explanation_parameters, audit_source.prediction_metadata, audit_source.explainability_metadata, audit_source.source_usage_metadata, audit_source.source_dataset_metadata, audit_source.run_parameters, audit_source.run_metadata, audit_source.confidence_level, audit_source.source_artifact_id, audit_source.source_artifact_path, audit_source.source_artifact_type, audit_source.explanation_artifact_id, audit_source.explanation_artifact_path, audit_source.explanation_artifact_type, COALESCE(audit_source.recorded_probability_uninfected, CASE WHEN audit_source.probability_parasitized >= CAST(0 AS numeric) AND audit_source.probability_parasitized <= CAST(1 AS numeric) THEN CAST(1 AS numeric) - audit_source.probability_parasitized ELSE CAST(NULL AS numeric) END) AS probability_uninfected, CASE WHEN audit_source.recorded_case_type = CAST('low_confidence' AS text) THEN CAST('low_confidence' AS text) WHEN audit_source.true_label IS NULL OR audit_source.predicted_label IS NULL THEN audit_source.recorded_case_type WHEN audit_source.true_label = audit_source.positive_label AND audit_source.predicted_label = audit_source.positive_label THEN CAST('true_positive' AS text) WHEN audit_source.true_label <> audit_source.positive_label AND audit_source.predicted_label <> audit_source.positive_label THEN CAST('true_negative' AS text) WHEN audit_source.true_label <> audit_source.positive_label AND audit_source.predicted_label = audit_source.positive_label THEN CAST('false_positive' AS text) WHEN audit_source.true_label = audit_source.positive_label AND audit_source.predicted_label <> audit_source.positive_label THEN CAST('false_negative' AS text) ELSE audit_source.recorded_case_type END AS case_type FROM audit_source), confidence AS (SELECT classified.explainability_id, classified.prediction_id, classified.run_id, classified.experiment_id, classified.model_id, classified.model_name, classified.model_type, classified.dataset_id, classified.dataset_name, classified.dataset_source, classified.dataset_split, classified.dataset_index, classified.manifest_id, classified.dataset_image_id, classified.original_tfds_label, classified.project_label, classified.remapped_label, classified.label_mapping_version, classified.run_name, classified.run_type, classified.run_status, classified.script_name, classified.command, classified.started_at, classified.finished_at, classified.created_at, classified.prediction_created_at, classified.method, classified.true_label, classified.predicted_label, classified.positive_label, classified.recorded_case_type, classified.score, classified.probability_parasitized, classified.recorded_probability_uninfected, classified.threshold_used, classified.threshold_source, classified.is_correct, classified.image_id, classified.image_path, classified.source_image_path, classified.original_image_path, classified.original_filename, classified.image_stored_path, classified.crop_path, classified.source_image_id, classified.patient_id, classified.slide_id, classified.bbox_x, classified.bbox_y, classified.bbox_width, classified.bbox_height, classified.prediction_upload_id, classified.uploaded_at, classified.explanation_output_path, classified.last_conv_layer, classified.success, classified.error_message, classified.explanation_parameters, classified.prediction_metadata, classified.explainability_metadata, classified.source_usage_metadata, classified.source_dataset_metadata, classified.run_parameters, classified.run_metadata, classified.confidence_level, classified.source_artifact_id, classified.source_artifact_path, classified.source_artifact_type, classified.explanation_artifact_id, classified.explanation_artifact_path, classified.explanation_artifact_type, classified.probability_uninfected, classified.case_type, CASE WHEN classified.probability_parasitized IS NOT NULL AND classified.threshold_used IS NOT NULL THEN abs(classified.probability_parasitized - classified.threshold_used) ELSE CAST(NULL AS numeric) END AS confidence_distance FROM classified) SELECT explainability_id, prediction_id, run_id, experiment_id, model_id, model_name, model_type, dataset_id, dataset_name, dataset_source, dataset_split, dataset_index, manifest_id, dataset_image_id, original_tfds_label, project_label, remapped_label, label_mapping_version, run_name, run_type, run_status, script_name, command, method, case_type, recorded_case_type, true_label, predicted_label, positive_label, score, probability_parasitized AS score_positive_label, probability_parasitized, probability_uninfected, threshold_used AS threshold, threshold_used, threshold_source, confidence_distance, confidence_level, CASE WHEN probability_parasitized IS NULL OR threshold_used IS NULL THEN CAST('unknown' AS text) WHEN case_type = CAST('low_confidence' AS text) OR confidence_distance <= 0.10 THEN CAST('low_confidence' AS text) ELSE CAST('confident' AS text) END AS confidence_status, COALESCE(is_correct, CASE WHEN true_label IS NOT NULL AND predicted_label IS NOT NULL THEN true_label = predicted_label ELSE CAST(NULL AS boolean) END) AS is_correct, image_id, image_path, source_image_path, original_image_path, original_filename, image_stored_path, crop_path, source_image_id, patient_id, slide_id, bbox_x, bbox_y, bbox_width, bbox_height, prediction_upload_id, uploaded_at, explanation_output_path, explanation_output_path AS output_path, last_conv_layer, success, error_message, explanation_parameters, CASE case_type WHEN CAST('false_positive' AS text) THEN CAST('La imagen estaba etiquetada como no parasitada, pero el modelo la clasificó como parasitada. Este caso debe revisarse como posible confusión visual, artefacto o umbral demasiado sensible.' AS text) WHEN CAST('false_negative' AS text) THEN CAST('La imagen estaba etiquetada como parasitada, pero el modelo la clasificó como no parasitada. Este caso es crítico porque representa una célula parasitada no detectada por el modelo.' AS text) WHEN CAST('true_positive' AS text) THEN CAST('La imagen estaba etiquetada como parasitada y el modelo también la clasificó como parasitada. La explicación visual permite revisar si la decisión se apoya en una región microscópica plausible.' AS text) WHEN CAST('true_negative' AS text) THEN CAST('La imagen estaba etiquetada como no parasitada y el modelo también la clasificó como no parasitada.' AS text) WHEN CAST('low_confidence' AS text) THEN CAST('La predicción está cercana al umbral de decisión. Este caso debe priorizarse para revisión humana.' AS text) ELSE CAST('No hay información suficiente para generar una interpretación automática del caso.' AS text) END AS interpretation, CAST('Uso experimental; no sustituye la revisión de un profesional de salud.' AS text) AS disclaimer, source_artifact_id, source_artifact_path, source_artifact_type, explanation_artifact_id AS artifact_id, COALESCE(explanation_artifact_path, explanation_output_path) AS artifact_path, explanation_artifact_type AS artifact_type, explanation_artifact_id, explanation_artifact_path, explanation_artifact_type, prediction_metadata, explainability_metadata, source_usage_metadata, source_dataset_metadata, run_parameters, run_metadata, started_at, finished_at, prediction_created_at, created_at FROM confidence;

CREATE VIEW public.vw_case_type_summary AS SELECT model_name, dataset_name, method, case_type, count(*) AS total_cases, avg(score_positive_label) AS avg_score, min(score_positive_label) AS min_score, max(score_positive_label) AS max_score, max(started_at) AS latest_run_at FROM vw_case_level_explainability GROUP BY model_name, dataset_name, method, case_type;

CREATE VIEW public.vw_clinical_inference_predictions AS SELECT prediction_id, run_id, experiment_id, model_id, model_name, model_type, run_name, run_type, run_status, script_name, command, started_at, finished_at, created_at, COALESCE(prediction_metadata ->> CAST('workflow' AS text), parameters ->> CAST('workflow' AS text), CAST('clinical_inference_experimental' AS text)) AS workflow, image_id, image_path, artifact_id, COALESCE(artifact_path, image_path) AS image_stored_path, original_image_path AS image_original_path, original_filename, stored_filename, mime_type, file_size_bytes, checksum, true_label, predicted_label, probability_parasitized, probability_uninfected, score, score_positive_label, threshold, is_correct, case_type, confidence_level, decision AS decision_code, COALESCE(prediction_metadata ->> CAST('human_readable_response' AS text), parameters ->> CAST('human_readable_response' AS text)) AS human_readable_response, CAST(NULLIF(COALESCE(prediction_metadata #>> CAST('{quality,passed}' AS text[]), parameters #>> CAST('{quality,passed}' AS text[])), CAST('' AS text)) AS boolean) AS quality_passed, COALESCE(prediction_metadata #> CAST('{quality,warnings}' AS text[]), parameters #> CAST('{quality,warnings}' AS text[]), CAST('[]' AS jsonb)) AS quality_warnings, COALESCE(prediction_metadata #> CAST('{quality,metrics}' AS text[]), parameters #> CAST('{quality,metrics}' AS text[]), CAST('{}' AS jsonb)) AS quality_metrics, CAST(NULLIF(COALESCE(prediction_metadata ->> CAST('raw_model_score' AS text), parameters ->> CAST('raw_model_score' AS text)), CAST('' AS text)) AS numeric) AS raw_model_score, COALESCE(prediction_metadata #>> CAST('{calibration,method}' AS text[]), parameters #>> CAST('{calibration,method}' AS text[]), CAST('none' AS text)) AS calibration_method, CAST(NULLIF(COALESCE(prediction_metadata #>> CAST('{calibration,applied}' AS text[]), parameters #>> CAST('{calibration,applied}' AS text[])), CAST('' AS text)) AS boolean) AS calibration_applied, tta AS tta_applied, n_aug, CAST(NULLIF(COALESCE(prediction_metadata ->> CAST('ensemble_applied' AS text), parameters ->> CAST('ensemble_applied' AS text)), CAST('' AS text)) AS boolean) AS ensemble_applied, COALESCE(prediction_metadata #> CAST('{ensemble_models}' AS text[]), parameters #> CAST('{ensemble_models}' AS text[]), CAST('[]' AS jsonb)) AS ensemble_models, COALESCE(prediction_metadata #> CAST('{ensemble_weights}' AS text[]), parameters #> CAST('{ensemble_weights}' AS text[]), CAST('[]' AS jsonb)) AS ensemble_weights, explainability_method, explainability_path, explainability_success, prediction_metadata, artifact_metadata, parameters AS run_parameters, run_metadata, COALESCE(prediction_metadata ->> CAST('raw_model_score_meaning' AS text), parameters ->> CAST('raw_model_score_meaning' AS text), run_metadata ->> CAST('raw_model_score_meaning' AS text), CAST('probability_parasitized' AS text)) AS raw_model_score_meaning, COALESCE(prediction_metadata ->> CAST('label_mapping_version' AS text), parameters ->> CAST('label_mapping_version' AS text), run_metadata ->> CAST('label_mapping_version' AS text), CAST('clinical_v1_parasitized_positive' AS text)) AS label_mapping_version, COALESCE(prediction_metadata #> CAST('{label_mapping}' AS text[]), parameters #> CAST('{label_mapping}' AS text[]), run_metadata #> CAST('{label_mapping}' AS text[]), jsonb_build_object('version', 'clinical_v1_parasitized_positive', 'negative_class_index', 0, 'negative_class_name', 'uninfected', 'positive_class_index', 1, 'positive_class_name', 'parasitized', 'raw_model_score_meaning', 'probability_parasitized')) AS label_mapping, COALESCE(prediction_metadata ->> CAST('positive_class_name' AS text), parameters ->> CAST('positive_class_name' AS text), CAST('parasitized' AS text)) AS positive_class_name, CAST(NULLIF(COALESCE(prediction_metadata ->> CAST('positive_class_index' AS text), parameters ->> CAST('positive_class_index' AS text), CAST('1' AS text)), CAST('' AS text)) AS integer) AS positive_class_index, COALESCE(prediction_metadata ->> CAST('negative_class_name' AS text), parameters ->> CAST('negative_class_name' AS text), CAST('uninfected' AS text)) AS negative_class_name, CAST(NULLIF(COALESCE(prediction_metadata ->> CAST('negative_class_index' AS text), parameters ->> CAST('negative_class_index' AS text), CAST('0' AS text)), CAST('' AS text)) AS integer) AS negative_class_index FROM vw_uploaded_predictions AS up WHERE run_type = CAST('inference' AS text) AND script_name = CAST('src.predict_image' AS text) AND COALESCE(prediction_metadata ->> CAST('source' AS text), artifact_metadata ->> CAST('source' AS text), source) = CAST('uploaded_for_prediction' AS text);

CREATE VIEW public.vw_evaluation_lineage AS WITH generic_metrics AS (SELECT run_metrics.run_id, max(run_metrics.metric_value) FILTER (WHERE lower(run_metrics.metric_name) = ANY(ARRAY[CAST('accuracy' AS text), CAST('test_accuracy' AS text), CAST('val_accuracy' AS text)])) AS accuracy, max(run_metrics.metric_value) FILTER (WHERE lower(run_metrics.metric_name) = ANY(ARRAY[CAST('recall' AS text), CAST('recall_macro' AS text), CAST('recall_parasitized' AS text), CAST('sensitivity' AS text), CAST('sensitivity_parasitized' AS text), CAST('test_recall' AS text)])) AS recall, max(run_metrics.metric_value) FILTER (WHERE lower(run_metrics.metric_name) = ANY(ARRAY[CAST('specificity' AS text), CAST('test_specificity' AS text)])) AS specificity, max(run_metrics.metric_value) FILTER (WHERE lower(run_metrics.metric_name) = ANY(ARRAY[CAST('f2' AS text), CAST('f2_score' AS text), CAST('f2_parasitized' AS text), CAST('test_f2' AS text)])) AS f2_score, max(run_metrics.metric_value) FILTER (WHERE lower(run_metrics.metric_name) = ANY(ARRAY[CAST('auc' AS text), CAST('auc_parasitized' AS text), CAST('roc_auc' AS text), CAST('roc_auc_parasitized' AS text), CAST('test_auc' AS text)])) AS auc FROM run_metrics GROUP BY run_metrics.run_id), latest_clinical_metrics AS (SELECT DISTINCT ON (run_clinical_metrics.run_id) run_clinical_metrics.run_id, run_clinical_metrics.accuracy, COALESCE(run_clinical_metrics.recall_parasitized, run_clinical_metrics.sensitivity_parasitized) AS recall, run_clinical_metrics.specificity, run_clinical_metrics.f2_parasitized AS f2_score, run_clinical_metrics.roc_auc_parasitized AS auc FROM run_clinical_metrics WHERE run_clinical_metrics.split_name = ANY(ARRAY[CAST('test' AS text), CAST('external' AS text)]) ORDER BY run_clinical_metrics.run_id, CASE run_clinical_metrics.split_name WHEN CAST('test' AS text) THEN 0 WHEN CAST('external' AS text) THEN 1 ELSE 2 END, run_clinical_metrics.created_at DESC) SELECT lineage.child_run_id AS evaluation_run_id, lineage.child_run_name AS evaluation_run_name, lineage.child_started_at AS evaluation_started_at, lineage.parent_run_id AS training_run_id, lineage.parent_run_name AS training_run_name, lineage.parent_model_name AS model_name, lineage.parent_optimizer AS optimizer, lineage.checkpoint_path, lineage.relationship_type, lineage.confidence, COALESCE(clinical.accuracy, metrics.accuracy) AS accuracy, COALESCE(clinical.recall, metrics.recall) AS recall, COALESCE(clinical.specificity, metrics.specificity) AS specificity, COALESCE(clinical.f2_score, metrics.f2_score) AS f2_score, COALESCE(clinical.auc, metrics.auc) AS auc FROM vw_run_lineage AS lineage LEFT JOIN generic_metrics AS metrics ON metrics.run_id = lineage.child_run_id LEFT JOIN latest_clinical_metrics AS clinical ON clinical.run_id = lineage.child_run_id WHERE lineage.child_run_type = CAST('evaluation' AS text) AND lineage.parent_run_type = CAST('training' AS text) AND lineage.relationship_type = CAST('evaluates_checkpoint_from' AS text);

CREATE VIEW public.vw_explainability_gallery AS SELECT explainability_id AS gallery_id, run_id, model_name, dataset_name, method, case_type, true_label, predicted_label, positive_label, score_positive_label, threshold, image_id, image_path, explanation_output_path, artifact_path, artifact_type, last_conv_layer, success, error_message, started_at, artifact_id FROM vw_case_level_explainability WHERE explanation_output_path IS NOT NULL;

CREATE VIEW public.vw_explainability_lineage AS WITH explanation_summary AS (SELECT explainability_results.run_id, explainability_results.method, count(*) AS total_explanations, count(*) FILTER (WHERE explainability_results.success IS TRUE) AS success_count, count(*) FILTER (WHERE explainability_results.success IS FALSE) AS failed_count FROM explainability_results GROUP BY explainability_results.run_id, explainability_results.method) SELECT lineage.child_run_id AS explain_run_id, lineage.child_run_name AS explain_run_name, lineage.child_started_at AS explain_started_at, lineage.parent_run_id AS training_run_id, lineage.parent_run_name AS training_run_name, lineage.parent_model_name AS model_name, lineage.parent_optimizer AS optimizer, lineage.checkpoint_path, lineage.relationship_type, lineage.confidence, COALESCE(summary.method, NULLIF(explain_run.parameters ->> CAST('method' AS text), CAST('' AS text)), NULLIF(explain_run.metadata ->> CAST('method' AS text), CAST('' AS text))) AS method, COALESCE(summary.total_explanations, CAST(0 AS bigint)) AS total_explanations, COALESCE(summary.success_count, CAST(0 AS bigint)) AS success_count, COALESCE(summary.failed_count, CAST(0 AS bigint)) AS failed_count FROM vw_run_lineage AS lineage INNER JOIN runs AS explain_run ON explain_run.id = lineage.child_run_id LEFT JOIN explanation_summary AS summary ON summary.run_id = lineage.child_run_id WHERE lineage.child_run_type = CAST('explainability' AS text) AND lineage.parent_run_type = CAST('training' AS text) AND lineage.relationship_type = CAST('explains_checkpoint_from' AS text);

CREATE VIEW public.vw_false_negative_cases AS SELECT explainability_id, prediction_id, run_id, model_name, dataset_name, method, case_type, true_label, predicted_label, positive_label, score_positive_label, probability_parasitized, threshold, threshold_used, threshold_source, image_id, image_path, explanation_output_path, artifact_path, artifact_type, last_conv_layer, success, error_message, started_at, command, artifact_id FROM vw_case_level_explainability WHERE case_type = CAST('false_negative' AS text) OR (true_label IS NOT NULL AND predicted_label IS NOT NULL AND true_label = positive_label AND predicted_label <> positive_label);

CREATE VIEW public.vw_false_positive_cases AS SELECT explainability_id, prediction_id, run_id, model_name, dataset_name, method, case_type, true_label, predicted_label, positive_label, score_positive_label, probability_parasitized, threshold, threshold_used, threshold_source, image_id, image_path, explanation_output_path, artifact_path, artifact_type, last_conv_layer, success, error_message, started_at, command, artifact_id FROM vw_case_level_explainability WHERE case_type = CAST('false_positive' AS text) OR (true_label IS NOT NULL AND predicted_label IS NOT NULL AND true_label <> positive_label AND predicted_label = positive_label);

CREATE VIEW public.vw_low_confidence_cases AS SELECT explainability_id, prediction_id, run_id, model_name, dataset_name, method, case_type, true_label, predicted_label, positive_label, score_positive_label, probability_parasitized, threshold, threshold_used, threshold_source, abs(score_positive_label - threshold) AS confidence_distance, image_id, image_path, explanation_output_path, artifact_path, artifact_type, last_conv_layer, success, error_message, started_at, artifact_id FROM vw_case_level_explainability WHERE case_type = CAST('low_confidence' AS text) OR (score_positive_label IS NOT NULL AND threshold IS NOT NULL AND abs(score_positive_label - threshold) <= 0.10);

-- 09_triggers
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

CREATE CONSTRAINT TRIGGER v2_calibration_pair_guard AFTER INSERT OR UPDATE ON public.run_threshold_calibration DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE PROCEDURE public.v2_calibration_pair_guard();

CREATE CONSTRAINT TRIGGER v2_run_configuration_required AFTER INSERT ON public.runs DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE PROCEDURE public.v2_run_configuration_required();

CREATE TRIGGER v2_xai_artifact_source_guard BEFORE INSERT ON public.xai_artifacts FOR EACH ROW EXECUTE PROCEDURE public.v2_xai_artifact_source_guard();

CREATE TRIGGER e04_legacy_admission BEFORE INSERT ON public.evaluations FOR EACH ROW EXECUTE PROCEDURE public.e04_legacy_admission();

CREATE CONSTRAINT TRIGGER e04_evaluation_complete AFTER INSERT ON public.evaluations DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE PROCEDURE public.e04_calibration_complete();

CREATE CONSTRAINT TRIGGER e04_calibration_complete AFTER INSERT OR UPDATE ON public.run_threshold_calibration DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE PROCEDURE public.e04_calibration_complete();

CREATE TRIGGER e04_calibration_immutable BEFORE DELETE OR UPDATE ON public.run_threshold_calibration FOR EACH ROW EXECUTE PROCEDURE public.e04_calibration_immutable();

CREATE TRIGGER dbv21_immutable BEFORE UPDATE OR DELETE ON public.xai_method_configurations FOR EACH ROW EXECUTE FUNCTION public.v2_immutable();

CREATE TRIGGER dbv21_immutable BEFORE UPDATE OR DELETE ON public.xai_region_attributions FOR EACH ROW EXECUTE FUNCTION public.v2_immutable();

CREATE TRIGGER dbv21_immutable BEFORE UPDATE OR DELETE ON public.xai_evaluation_protocols FOR EACH ROW EXECUTE FUNCTION public.v2_immutable();

CREATE TRIGGER dbv21_immutable BEFORE UPDATE OR DELETE ON public.xai_evaluation_members FOR EACH ROW EXECUTE FUNCTION public.v2_immutable();

CREATE TRIGGER dbv21_configuration_guard BEFORE INSERT ON public.xai_method_configurations FOR EACH ROW EXECUTE FUNCTION public.dbv21_xai_configuration_guard();

CREATE TRIGGER dbv21_configuration_guard BEFORE INSERT ON public.xai_evaluation_protocols FOR EACH ROW EXECUTE FUNCTION public.dbv21_xai_configuration_guard();

CREATE CONSTRAINT TRIGGER dbv21_xai_evaluation_complete AFTER INSERT ON public.xai_quantitative_evaluations DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.dbv21_xai_evaluation_complete();

CREATE CONSTRAINT TRIGGER dbv21_xai_evaluation_complete AFTER INSERT ON public.xai_evaluation_members DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.dbv21_xai_evaluation_complete();

ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT ck_xai_membership_hash CHECK (membership_hash ~ '^[0-9a-f]{64}$');
