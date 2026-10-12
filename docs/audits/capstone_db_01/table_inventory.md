# Anexo estructural por tabla

Estado documental: `HISTORICAL_AUDIT` — CAPSTONE-DB-01, 2026-10-12.

Fuente: catálogo operativo exportado; no derivado de Alembic. Definiciones completas de constraints e índices: CSV adjuntos.

## public.alembic_version

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| version_num | character varying(32) | True | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `alembic_version_pkc`: `PRIMARY KEY (version_num)`

## public.artifacts

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| run_id | uuid | False | ; identity=—; generated=— |
| artifact_type | text | True | ; identity=—; generated=— |
| name | text | False | ; identity=—; generated=— |
| path | text | True | ; identity=—; generated=— |
| mime_type | text | False | ; identity=—; generated=— |
| file_size_bytes | bigint | False | ; identity=—; generated=— |
| checksum | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | False | now(); identity=—; generated=— |
| metadata | jsonb | False | '{}'::jsonb; identity=—; generated=— |
| artifact_uri | text | False | ; identity=—; generated=— |
| artifact_status | text | True | 'available'::text; identity=—; generated=— |
| archived_at | timestamp with time zone | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `artifacts_pkey`: `PRIMARY KEY (id)`
- `artifacts_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE RESTRICT`

## public.assessment_artifacts

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| attempt_id | uuid | True | ; identity=—; generated=— |
| artifact_id | uuid | True | ; identity=—; generated=— |
| sample_id | uuid | True | ; identity=—; generated=— |
| role | text | True | ; identity=—; generated=— |
| payload | jsonb | True | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `assessment_artifacts_artifact_id_key`: `UNIQUE (artifact_id)`
- `assessment_artifacts_attempt_id_fkey`: `FOREIGN KEY (attempt_id) REFERENCES assessment_attempts(id)`
- `assessment_artifacts_pkey`: `PRIMARY KEY (attempt_id, sample_id, role)`

## public.assessment_attempts

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| identity_id | uuid | True | ; identity=—; generated=— |
| owner | uuid | True | ; identity=—; generated=— |
| host | text | True | ; identity=—; generated=— |
| pid | integer | True | ; identity=—; generated=— |
| ordinal | integer | True | ; identity=—; generated=— |
| state | text | True | 'active'::text; identity=—; generated=— |
| artifact_root | text | True | ; identity=—; generated=— |
| cause | text | False | ; identity=—; generated=— |
| verification | jsonb | False | ; identity=—; generated=— |
| started_at | timestamp with time zone | True | clock_timestamp(); identity=—; generated=— |
| finished_at | timestamp with time zone | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `assessment_attempts_artifact_root_key`: `UNIQUE (artifact_root)`
- `assessment_attempts_identity_id_fkey`: `FOREIGN KEY (identity_id) REFERENCES assessment_identities(id)`
- `assessment_attempts_identity_id_ordinal_key`: `UNIQUE (identity_id, ordinal)`
- `assessment_attempts_pkey`: `PRIMARY KEY (id)`

## public.assessment_campaign_consumers

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| campaign_id | uuid | True | ; identity=—; generated=— |
| member_id | uuid | True | ; identity=—; generated=— |
| identity_id | uuid | True | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `assessment_campaign_consumers_campaign_id_fkey`: `FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns(id)`
- `assessment_campaign_consumers_identity_id_fkey`: `FOREIGN KEY (identity_id) REFERENCES assessment_identities(id)`
- `assessment_campaign_consumers_member_id_fkey`: `FOREIGN KEY (member_id) REFERENCES campaign_members(id)`
- `assessment_campaign_consumers_pkey`: `PRIMARY KEY (campaign_id, member_id, identity_id)`

## public.assessment_final_locks

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| identity_hash | text | True | ; identity=—; generated=— |
| evidence | jsonb | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | clock_timestamp(); identity=—; generated=— |

PK/FK/UNIQUE:

- `assessment_final_locks_identity_hash_key`: `UNIQUE (identity_hash)`
- `assessment_final_locks_pkey`: `PRIMARY KEY (id)`

## public.assessment_identities

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| identity_hash | text | True | ; identity=—; generated=— |
| training_run_id | uuid | True | ; identity=—; generated=— |
| kind | text | True | ; identity=—; generated=— |
| identity | jsonb | True | ; identity=—; generated=— |
| canonical_identity | text | True | ; identity=—; generated=— |
| structural_hash | text | False | assessment_structural_hash(identity); identity=—; generated=s |
| created_at | timestamp with time zone | True | clock_timestamp(); identity=—; generated=— |

PK/FK/UNIQUE:

- `assessment_identities_identity_hash_key`: `UNIQUE (identity_hash)`
- `assessment_identities_pkey`: `PRIMARY KEY (id)`
- `assessment_identities_structural_hash_key`: `UNIQUE (structural_hash)`
- `assessment_identities_training_run_id_fkey`: `FOREIGN KEY (training_run_id) REFERENCES runs(id)`

## public.assessment_results

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| attempt_id | uuid | True | ; identity=—; generated=— |
| sample_id | uuid | True | ; identity=—; generated=— |
| payload | jsonb | True | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `assessment_results_attempt_id_fkey`: `FOREIGN KEY (attempt_id) REFERENCES assessment_attempts(id)`
- `assessment_results_pkey`: `PRIMARY KEY (attempt_id, sample_id)`

## public.audit_events

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| event_type | text | True | ; identity=—; generated=— |
| action | text | True | ; identity=—; generated=— |
| actor_user_id | uuid | False | ; identity=—; generated=— |
| actor_username_snapshot | text | False | ; identity=—; generated=— |
| resource_type | text | True | ; identity=—; generated=— |
| resource_id | text | False | ; identity=—; generated=— |
| request_method | text | True | ; identity=—; generated=— |
| request_path | text | True | ; identity=—; generated=— |
| correlation_id | text | True | ; identity=—; generated=— |
| before_state | jsonb | False | ; identity=—; generated=— |
| after_state | jsonb | False | ; identity=—; generated=— |
| metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| success | boolean | True | ; identity=—; generated=— |
| error_code | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `audit_events_actor_user_id_fkey`: `FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT`
- `audit_events_pkey`: `PRIMARY KEY (id)`

## public.blood_samples

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| case_id | uuid | True | ; identity=—; generated=— |
| sample_code | character varying(120) | True | ; identity=—; generated=— |
| specimen_type | character varying(80) | True | 'peripheral_blood'::character varying; identity=—; generated=— |
| collection_method | character varying(120) | False | ; identity=—; generated=— |
| anticoagulant | character varying(120) | False | ; identity=—; generated=— |
| collected_at | timestamp with time zone | False | ; identity=—; generated=— |
| received_at | timestamp with time zone | False | ; identity=—; generated=— |
| status | character varying(20) | True | 'registered'::character varying; identity=—; generated=— |
| notes | text | False | ; identity=—; generated=— |
| metadata_json | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| updated_at | timestamp with time zone | True | now(); identity=—; generated=— |
| created_by | uuid | True | ; identity=—; generated=— |
| updated_by | uuid | False | ; identity=—; generated=— |
| archived_at | timestamp with time zone | False | ; identity=—; generated=— |
| archived_by | uuid | False | ; identity=—; generated=— |
| source_system | character varying(120) | False | ; identity=—; generated=— |
| external_sample_id | character varying(240) | False | ; identity=—; generated=— |
| sample_identity_origin | character varying(40) | True | 'generated_by_capstone'::character varying; identity=—; generated=— |
| source_group_key | character varying(240) | False | ; identity=—; generated=— |
| ingestion_status | character varying(20) | False | ; identity=—; generated=— |
| expected_image_count | integer | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `blood_samples_archived_by_fkey`: `FOREIGN KEY (archived_by) REFERENCES users(id) ON DELETE RESTRICT`
- `blood_samples_case_id_fkey`: `FOREIGN KEY (case_id) REFERENCES scientific_cases(id) ON DELETE RESTRICT`
- `blood_samples_created_by_fkey`: `FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT`
- `blood_samples_pkey`: `PRIMARY KEY (id)`
- `blood_samples_updated_by_fkey`: `FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE RESTRICT`
- `uq_blood_samples_case_code`: `UNIQUE (case_id, sample_code)`

## public.campaign_attempts

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| member_id | uuid | True | ; identity=—; generated=— |
| ordinal | integer | True | ; identity=—; generated=— |
| state | text | True | ; identity=—; generated=— |
| training_run_id | uuid | False | ; identity=—; generated=— |
| cause | text | False | ; identity=—; generated=— |
| started_at | timestamp with time zone | True | now(); identity=—; generated=— |
| finished_at | timestamp with time zone | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `campaign_attempts_member_id_fkey`: `FOREIGN KEY (member_id) REFERENCES campaign_members(id) ON DELETE RESTRICT`
- `campaign_attempts_member_id_id_key`: `UNIQUE (member_id, id)`
- `campaign_attempts_member_id_ordinal_key`: `UNIQUE (member_id, ordinal)`
- `campaign_attempts_pkey`: `PRIMARY KEY (id)`
- `campaign_attempts_training_run_id_fkey`: `FOREIGN KEY (training_run_id) REFERENCES runs(id) ON DELETE RESTRICT`
- `campaign_attempts_training_run_id_key`: `UNIQUE (training_run_id)`

## public.campaign_configurations

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| campaign_id | uuid | True | ; identity=—; generated=— |
| configuration_hash | text | True | ; identity=—; generated=— |
| configuration | jsonb | True | ; identity=—; generated=— |
| canonical_configuration | text | True | ; identity=—; generated=— |
| requests | jsonb | True | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `campaign_configurations_campaign_id_fkey`: `FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns(id) ON DELETE RESTRICT`
- `campaign_configurations_pkey`: `PRIMARY KEY (campaign_id, configuration_hash)`

## public.campaign_controlled_requests

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| campaign_id | uuid | True | ; identity=—; generated=— |
| member_id | uuid | True | ; identity=—; generated=— |
| revision_id | uuid | True | ; identity=—; generated=— |
| previous_attempt_id | uuid | True | ; identity=—; generated=— |
| attempt_id | uuid | True | ; identity=—; generated=— |
| run_id | uuid | True | ; identity=—; generated=— |
| reason | text | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | clock_timestamp(); identity=—; generated=— |

PK/FK/UNIQUE:

- `campaign_controlled_requests_attempt_id_fkey`: `FOREIGN KEY (attempt_id) REFERENCES campaign_attempts(id) DEFERRABLE INITIALLY DEFERRED`
- `campaign_controlled_requests_attempt_id_key`: `UNIQUE (attempt_id)`
- `campaign_controlled_requests_campaign_id_fkey`: `FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns(id)`
- `campaign_controlled_requests_campaign_id_revision_id_fkey`: `FOREIGN KEY (campaign_id, revision_id) REFERENCES campaign_technical_revisions(campaign_id, id)`
- `campaign_controlled_requests_member_id_fkey`: `FOREIGN KEY (member_id) REFERENCES campaign_members(id)`
- `campaign_controlled_requests_pkey`: `PRIMARY KEY (id)`
- `campaign_controlled_requests_previous_attempt_id_fkey`: `FOREIGN KEY (previous_attempt_id) REFERENCES campaign_attempts(id)`
- `campaign_controlled_requests_previous_attempt_id_key`: `UNIQUE (previous_attempt_id)`
- `campaign_controlled_requests_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES runs(id) DEFERRABLE INITIALLY DEFERRED`
- `campaign_controlled_requests_run_id_key`: `UNIQUE (run_id)`

## public.campaign_execution_events

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| campaign_id | uuid | True | ; identity=—; generated=— |
| code | text | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | clock_timestamp(); identity=—; generated=— |

PK/FK/UNIQUE:

- `campaign_execution_events_campaign_id_fkey`: `FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns(id)`
- `campaign_execution_events_pkey`: `PRIMARY KEY (id)`

## public.campaign_members

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| campaign_id | uuid | True | ; identity=—; generated=— |
| configuration_hash | text | True | ; identity=—; generated=— |
| seed | integer | True | ; identity=—; generated=— |
| position | integer | True | ; identity=—; generated=— |
| exclusion_reason | text | False | ; identity=—; generated=— |
| state | text | True | 'pending'::text; identity=—; generated=— |
| accepted_attempt_id | uuid | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `campaign_members_campaign_id_configuration_hash_fkey`: `FOREIGN KEY (campaign_id, configuration_hash) REFERENCES campaign_configurations(campaign_id, configuration_hash) ON DELETE RESTRICT`
- `campaign_members_campaign_id_configuration_hash_seed_key`: `UNIQUE (campaign_id, configuration_hash, seed)`
- `campaign_members_campaign_id_fkey`: `FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns(id) ON DELETE RESTRICT`
- `campaign_members_campaign_id_position_key`: `UNIQUE (campaign_id, "position")`
- `campaign_members_pkey`: `PRIMARY KEY (id)`
- `fk_member_accepted_attempt`: `FOREIGN KEY (id, accepted_attempt_id) REFERENCES campaign_attempts(member_id, id) DEFERRABLE INITIALLY DEFERRED`

## public.campaign_technical_revisions

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| campaign_id | uuid | True | ; identity=—; generated=— |
| payload | jsonb | True | ; identity=—; generated=— |
| canonical_payload | text | True | ; identity=—; generated=— |
| payload_hash | text | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | clock_timestamp(); identity=—; generated=— |

PK/FK/UNIQUE:

- `campaign_technical_revisions_campaign_id_fkey`: `FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns(id)`
- `campaign_technical_revisions_campaign_id_id_key`: `UNIQUE (campaign_id, id)`
- `campaign_technical_revisions_pkey`: `PRIMARY KEY (id)`

## public.cell_classification_events

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| classification_run_id | uuid | True | ; identity=—; generated=— |
| cell_detection_id | uuid | False | ; identity=—; generated=— |
| cell_prediction_id | uuid | False | ; identity=—; generated=— |
| event_type | character varying(120) | True | ; identity=—; generated=— |
| status | character varying(40) | True | ; identity=—; generated=— |
| message_code | character varying(80) | False | ; identity=—; generated=— |
| message | text | False | ; identity=—; generated=— |
| progress_current | integer | False | ; identity=—; generated=— |
| progress_total | integer | False | ; identity=—; generated=— |
| metadata_json | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `cell_classification_events_cell_detection_id_fkey`: `FOREIGN KEY (cell_detection_id) REFERENCES cell_detections(id) ON DELETE RESTRICT`
- `cell_classification_events_classification_run_id_fkey`: `FOREIGN KEY (classification_run_id) REFERENCES cell_classification_runs(id) ON DELETE RESTRICT`
- `cell_classification_events_pkey`: `PRIMARY KEY (id)`
- `fk_cell_classification_event_prediction`: `FOREIGN KEY (cell_prediction_id, classification_run_id) REFERENCES cell_predictions(id, classification_run_id) ON DELETE RESTRICT`

## public.cell_classification_inputs

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| classification_run_id | uuid | True | ; identity=—; generated=— |
| detection_run_id | uuid | True | ; identity=—; generated=— |
| cell_detection_id | uuid | True | ; identity=—; generated=— |
| microscopy_image_id | uuid | True | ; identity=—; generated=— |
| crop_id | uuid | False | ; identity=—; generated=— |
| input_order | integer | True | ; identity=—; generated=— |
| image_sequence_number | integer | True | ; identity=—; generated=— |
| cell_index | integer | True | ; identity=—; generated=— |
| cell_code | character varying(40) | True | ; identity=—; generated=— |
| detector_key | character varying(80) | True | ; identity=—; generated=— |
| detector_version | character varying(40) | True | ; identity=—; generated=— |
| detector_algorithm_version | character varying(80) | True | ; identity=—; generated=— |
| crop_sha256 | character(64) | False | ; identity=—; generated=— |
| crop_width_px | integer | False | ; identity=—; generated=— |
| crop_height_px | integer | False | ; identity=—; generated=— |
| detection_review_status_at_creation | character varying(30) | False | ; identity=—; generated=— |
| eligible | boolean | True | ; identity=—; generated=— |
| exclusion_reason | character varying(120) | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `cell_classification_inputs_pkey`: `PRIMARY KEY (id)`
- `fk_cell_classification_input_crop`: `FOREIGN KEY (crop_id, cell_detection_id) REFERENCES cell_crops(id, cell_detection_id) ON DELETE RESTRICT`
- `fk_cell_classification_input_detection`: `FOREIGN KEY (cell_detection_id, detection_run_id, microscopy_image_id) REFERENCES cell_detections(id, detection_run_id, microscopy_image_id) ON DELETE RESTRICT`
- `fk_cell_classification_input_run_detection`: `FOREIGN KEY (classification_run_id, detection_run_id) REFERENCES cell_classification_runs(id, detection_run_id) ON DELETE RESTRICT`
- `uq_cell_classification_inputs_crop`: `UNIQUE (classification_run_id, crop_id)`
- `uq_cell_classification_inputs_detection`: `UNIQUE (classification_run_id, cell_detection_id)`
- `uq_cell_classification_inputs_order`: `UNIQUE (classification_run_id, input_order)`
- `uq_cell_classification_inputs_prediction_owner`: `UNIQUE (id, classification_run_id, cell_detection_id, crop_id)`

## public.cell_classification_reviews

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| cell_prediction_id | uuid | True | ; identity=—; generated=— |
| decision | character varying(30) | True | ; identity=—; generated=— |
| reviewed_label | character varying(20) | False | ; identity=—; generated=— |
| comment | text | False | ; identity=—; generated=— |
| actor_user_id | uuid | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | clock_timestamp(); identity=—; generated=— |

PK/FK/UNIQUE:

- `cell_classification_reviews_actor_user_id_fkey`: `FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT`
- `cell_classification_reviews_cell_prediction_id_fkey`: `FOREIGN KEY (cell_prediction_id) REFERENCES cell_predictions(id) ON DELETE RESTRICT`
- `cell_classification_reviews_pkey`: `PRIMARY KEY (id)`

## public.cell_classification_runs

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| analysis_run_id | uuid | True | ; identity=—; generated=— |
| detection_run_id | uuid | True | ; identity=—; generated=— |
| classification_run_code | character varying(20) | True | ; identity=—; generated=— |
| production_model_id | uuid | True | ; identity=—; generated=— |
| stage2_publication_id | uuid | True | ; identity=—; generated=— |
| model_registry_id | uuid | True | ; identity=—; generated=— |
| model_name | character varying(160) | True | ; identity=—; generated=— |
| model_version | character varying(120) | False | ; identity=—; generated=— |
| model_snapshot | jsonb | True | ; identity=—; generated=— |
| input_manifest_sha256 | character(64) | True | ; identity=—; generated=— |
| status | character varying(30) | True | ; identity=—; generated=— |
| input_count | integer | True | ; identity=—; generated=— |
| eligible_count | integer | True | ; identity=—; generated=— |
| excluded_count | integer | True | ; identity=—; generated=— |
| processed_count | integer | True | 0; identity=—; generated=— |
| parasitized_count | integer | True | 0; identity=—; generated=— |
| uninfected_count | integer | True | 0; identity=—; generated=— |
| near_threshold_count | integer | True | 0; identity=—; generated=— |
| failed_count | integer | True | 0; identity=—; generated=— |
| requested_by | uuid | True | ; identity=—; generated=— |
| retry_of_run_id | uuid | False | ; identity=—; generated=— |
| started_at | timestamp with time zone | False | ; identity=—; generated=— |
| completed_at | timestamp with time zone | False | ; identity=—; generated=— |
| failed_at | timestamp with time zone | False | ; identity=—; generated=— |
| error_code | character varying(80) | False | ; identity=—; generated=— |
| error_message | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| updated_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `cell_classification_runs_classification_run_code_key`: `UNIQUE (classification_run_code)`
- `cell_classification_runs_pkey`: `PRIMARY KEY (id)`
- `cell_classification_runs_requested_by_fkey`: `FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE RESTRICT`
- `cell_classification_runs_retry_of_run_id_fkey`: `FOREIGN KEY (retry_of_run_id) REFERENCES cell_classification_runs(id) ON DELETE RESTRICT`
- `fk_cell_classification_run_deployment_version`: `FOREIGN KEY (production_model_id, model_registry_id) REFERENCES deployed_model_versions(id, model_version_id) ON DELETE RESTRICT`
- `fk_cell_classification_run_detection_analysis`: `FOREIGN KEY (detection_run_id, analysis_run_id) REFERENCES cell_detection_runs(id, analysis_run_id) ON DELETE RESTRICT`
- `fk_cell_classification_run_publication_version`: `FOREIGN KEY (stage2_publication_id, model_registry_id) REFERENCES stage2_model_publications(id, model_version_id) ON DELETE RESTRICT`
- `uq_cell_classification_runs_detection_identity`: `UNIQUE (id, detection_run_id)`
- `uq_cell_classification_runs_identity`: `UNIQUE (id, analysis_run_id, detection_run_id)`

## public.cell_crops

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| cell_detection_id | uuid | True | ; identity=—; generated=— |
| relative_storage_key | text | True | ; identity=—; generated=— |
| sha256 | character(64) | True | ; identity=—; generated=— |
| file_size_bytes | bigint | True | ; identity=—; generated=— |
| width_px | integer | True | ; identity=—; generated=— |
| height_px | integer | True | ; identity=—; generated=— |
| format | character varying(20) | True | ; identity=—; generated=— |
| padding_px | integer | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `cell_crops_pkey`: `PRIMARY KEY (id)`
- `fk_cell_crops_detection`: `FOREIGN KEY (cell_detection_id) REFERENCES cell_detections(id) ON DELETE RESTRICT`
- `uq_cell_crops_detection`: `UNIQUE (cell_detection_id)`
- `uq_cell_crops_storage_key`: `UNIQUE (relative_storage_key)`

## public.cell_detection_events

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| detection_run_id | uuid | True | ; identity=—; generated=— |
| microscopy_image_id | uuid | False | ; identity=—; generated=— |
| event_type | character varying(100) | True | ; identity=—; generated=— |
| stage | character varying(50) | True | ; identity=—; generated=— |
| status | character varying(30) | True | ; identity=—; generated=— |
| message_code | character varying(80) | False | ; identity=—; generated=— |
| message | text | False | ; identity=—; generated=— |
| progress_current | integer | False | ; identity=—; generated=— |
| progress_total | integer | False | ; identity=—; generated=— |
| metadata_json | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `cell_detection_events_detection_run_id_fkey`: `FOREIGN KEY (detection_run_id) REFERENCES cell_detection_runs(id) ON DELETE RESTRICT`
- `cell_detection_events_microscopy_image_id_fkey`: `FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images(id) ON DELETE RESTRICT`
- `cell_detection_events_pkey`: `PRIMARY KEY (id)`

## public.cell_detection_runs

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| analysis_run_id | uuid | True | ; identity=—; generated=— |
| detection_run_code | character varying(20) | True | ; identity=—; generated=— |
| detector_key | character varying(80) | True | ; identity=—; generated=— |
| detector_version | character varying(40) | True | ; identity=—; generated=— |
| algorithm_version | character varying(80) | True | ; identity=—; generated=— |
| profile_snapshot | jsonb | True | ; identity=—; generated=— |
| input_manifest_sha256 | character(64) | True | ; identity=—; generated=— |
| status | character varying(30) | True | ; identity=—; generated=— |
| image_count | integer | True | ; identity=—; generated=— |
| processed_image_count | integer | True | 0; identity=—; generated=— |
| component_count | integer | True | 0; identity=—; generated=— |
| detection_count | integer | True | 0; identity=—; generated=— |
| crop_count | integer | True | 0; identity=—; generated=— |
| warning_count | integer | True | 0; identity=—; generated=— |
| requested_by | uuid | True | ; identity=—; generated=— |
| started_at | timestamp with time zone | False | ; identity=—; generated=— |
| completed_at | timestamp with time zone | False | ; identity=—; generated=— |
| failed_at | timestamp with time zone | False | ; identity=—; generated=— |
| error_code | character varying(80) | False | ; identity=—; generated=— |
| error_message | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| updated_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `cell_detection_runs_analysis_run_id_fkey`: `FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT`
- `cell_detection_runs_detection_run_code_key`: `UNIQUE (detection_run_code)`
- `cell_detection_runs_pkey`: `PRIMARY KEY (id)`
- `cell_detection_runs_requested_by_fkey`: `FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE RESTRICT`
- `uq_cell_detection_runs_identity`: `UNIQUE (id, analysis_run_id)`

## public.cell_detections

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| detection_run_id | uuid | True | ; identity=—; generated=— |
| analysis_run_id | uuid | True | ; identity=—; generated=— |
| connected_component_id | uuid | True | ; identity=—; generated=— |
| analysis_run_image_id | uuid | True | ; identity=—; generated=— |
| microscopy_image_id | uuid | True | ; identity=—; generated=— |
| cell_index | integer | True | ; identity=—; generated=— |
| cell_code | character varying(40) | True | ; identity=—; generated=— |
| bbox_x | integer | True | ; identity=—; generated=— |
| bbox_y | integer | True | ; identity=—; generated=— |
| bbox_width | integer | True | ; identity=—; generated=— |
| bbox_height | integer | True | ; identity=—; generated=— |
| coordinate_space | character varying(40) | True | ; identity=—; generated=— |
| detector_score | double precision | False | ; identity=—; generated=— |
| automated_status | character varying(30) | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `cell_detections_pkey`: `PRIMARY KEY (id)`
- `fk_cell_detections_component`: `FOREIGN KEY (connected_component_id, detection_run_id, analysis_run_image_id, microscopy_image_id) REFERENCES image_connected_components(id, detection_run_id, analysis_run_image_id, microscopy_image_id) ON DELETE RESTRICT`
- `fk_cell_detections_run_analysis`: `FOREIGN KEY (detection_run_id, analysis_run_id) REFERENCES cell_detection_runs(id, analysis_run_id) ON DELETE RESTRICT`
- `uq_cell_detections_cell_code`: `UNIQUE (cell_code)`
- `uq_cell_detections_component`: `UNIQUE (connected_component_id)`
- `uq_cell_detections_identity`: `UNIQUE (id, detection_run_id, microscopy_image_id)`
- `uq_cell_detections_run_index`: `UNIQUE (detection_run_id, cell_index)`

## public.cell_explanations

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| cell_prediction_id | uuid | True | ; identity=—; generated=— |
| method | character varying(40) | True | ; identity=—; generated=— |
| method_version | character varying(80) | True | ; identity=—; generated=— |
| status | character varying(30) | True | ; identity=—; generated=— |
| last_conv_layer | character varying(255) | False | ; identity=—; generated=— |
| parameters_json | jsonb | True | ; identity=—; generated=— |
| heatmap_storage_key | text | False | ; identity=—; generated=— |
| heatmap_sha256 | character(64) | False | ; identity=—; generated=— |
| heatmap_file_size_bytes | bigint | False | ; identity=—; generated=— |
| overlay_storage_key | text | False | ; identity=—; generated=— |
| overlay_sha256 | character(64) | False | ; identity=—; generated=— |
| overlay_file_size_bytes | bigint | False | ; identity=—; generated=— |
| width_px | integer | False | ; identity=—; generated=— |
| height_px | integer | False | ; identity=—; generated=— |
| started_at | timestamp with time zone | False | ; identity=—; generated=— |
| completed_at | timestamp with time zone | False | ; identity=—; generated=— |
| error_code | character varying(80) | False | ; identity=—; generated=— |
| error_message | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `cell_explanations_cell_prediction_id_fkey`: `FOREIGN KEY (cell_prediction_id) REFERENCES cell_predictions(id) ON DELETE RESTRICT`
- `cell_explanations_cell_prediction_id_key`: `UNIQUE (cell_prediction_id)`
- `cell_explanations_pkey`: `PRIMARY KEY (id)`

## public.cell_predictions

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| classification_run_id | uuid | True | ; identity=—; generated=— |
| classification_input_id | uuid | True | ; identity=—; generated=— |
| cell_detection_id | uuid | True | ; identity=—; generated=— |
| crop_id | uuid | True | ; identity=—; generated=— |
| prediction_status | character varying(20) | True | ; identity=—; generated=— |
| raw_output | jsonb | True | ; identity=—; generated=— |
| probability_parasitized | double precision | False | ; identity=—; generated=— |
| probability_uninfected | double precision | False | ; identity=—; generated=— |
| predicted_label | character varying(20) | False | ; identity=—; generated=— |
| predicted_class_index | smallint | False | ; identity=—; generated=— |
| positive_label | character varying(20) | True | ; identity=—; generated=— |
| positive_class_index | smallint | True | ; identity=—; generated=— |
| threshold_used | double precision | True | ; identity=—; generated=— |
| threshold_source | character varying(120) | True | ; identity=—; generated=— |
| decision_margin | double precision | False | ; identity=—; generated=— |
| near_threshold | boolean | True | false; identity=—; generated=— |
| preprocessing_snapshot | jsonb | True | ; identity=—; generated=— |
| inference_duration_ms | double precision | False | ; identity=—; generated=— |
| error_code | character varying(80) | False | ; identity=—; generated=— |
| error_message | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `cell_predictions_classification_input_id_key`: `UNIQUE (classification_input_id)`
- `cell_predictions_pkey`: `PRIMARY KEY (id)`
- `fk_cell_prediction_input_owner`: `FOREIGN KEY (classification_input_id, classification_run_id, cell_detection_id, crop_id) REFERENCES cell_classification_inputs(id, classification_run_id, cell_detection_id, crop_id) ON DELETE RESTRICT`
- `uq_cell_predictions_run_identity`: `UNIQUE (id, classification_run_id)`

## public.clinical_identities

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| dataset_id | uuid | True | ; identity=—; generated=— |
| identity_type | text | True | ; identity=—; generated=— |
| source_identifier | text | True | ; identity=—; generated=— |
| status | text | True | ; identity=—; generated=— |
| metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| updated_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `clinical_identities_dataset_id_fkey`: `FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE RESTRICT`
- `clinical_identities_pkey`: `PRIMARY KEY (id)`
- `uq_clinical_identities_source`: `UNIQUE (dataset_id, identity_type, source_identifier)`

## public.dataset_materialization_activations

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| dataset_version_id | uuid | True | ; identity=—; generated=— |
| materialization_id | uuid | True | ; identity=—; generated=— |
| dataset_family | text | True | ; identity=—; generated=— |
| activated_at | timestamp with time zone | True | now(); identity=—; generated=— |
| deactivated_at | timestamp with time zone | False | ; identity=—; generated=— |
| metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |

PK/FK/UNIQUE:

- `dataset_materialization_activations_dataset_version_id_fkey`: `FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions(id) ON DELETE RESTRICT`
- `dataset_materialization_activations_materialization_id_fkey`: `FOREIGN KEY (materialization_id) REFERENCES dataset_materializations(id) ON DELETE RESTRICT`
- `dataset_materialization_activations_pkey`: `PRIMARY KEY (id)`

## public.dataset_materializations

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| dataset_version_id | uuid | True | ; identity=—; generated=— |
| attempt_number | integer | True | ; identity=—; generated=— |
| status | text | True | 'NOT_MATERIALIZED'::text; identity=—; generated=— |
| reconciliation_status | text | True | 'PENDING'::text; identity=—; generated=— |
| relative_root | text | True | ; identity=—; generated=— |
| record_count | bigint | True | 0; identity=—; generated=— |
| manifest_metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| started_at | timestamp with time zone | False | ; identity=—; generated=— |
| completed_at | timestamp with time zone | False | ; identity=—; generated=— |
| failure_reason | text | False | ; identity=—; generated=— |
| metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `dataset_materializations_dataset_version_id_fkey`: `FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions(id) ON DELETE RESTRICT`
- `dataset_materializations_pkey`: `PRIMARY KEY (id)`
- `uq_dataset_materializations_attempt`: `UNIQUE (dataset_version_id, attempt_number)`

## public.dataset_source_records

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| dataset_id | uuid | True | ; identity=—; generated=— |
| clinical_identity_id | uuid | False | ; identity=—; generated=— |
| source_record_key | text | True | ; identity=—; generated=— |
| tfds_index | bigint | False | ; identity=—; generated=— |
| source_filename | text | False | ; identity=—; generated=— |
| class_index | integer | True | ; identity=—; generated=— |
| class_name | text | True | ; identity=—; generated=— |
| original_label | integer | False | ; identity=—; generated=— |
| project_label | integer | False | ; identity=—; generated=— |
| relative_source_key | text | False | ; identity=—; generated=— |
| source_file_sha256 | text | False | ; identity=—; generated=— |
| decoded_pixel_sha256 | text | False | ; identity=—; generated=— |
| image_width | integer | False | ; identity=—; generated=— |
| image_height | integer | False | ; identity=—; generated=— |
| file_size_bytes | bigint | False | ; identity=—; generated=— |
| identity_status | text | True | ; identity=—; generated=— |
| metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| updated_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `dataset_source_records_clinical_identity_id_fkey`: `FOREIGN KEY (clinical_identity_id) REFERENCES clinical_identities(id) ON DELETE RESTRICT`
- `dataset_source_records_dataset_id_fkey`: `FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE RESTRICT`
- `dataset_source_records_pkey`: `PRIMARY KEY (id)`
- `uq_dataset_source_records_key`: `UNIQUE (dataset_id, source_record_key)`

## public.dataset_split_assignments

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| dataset_version_id | uuid | True | ; identity=—; generated=— |
| source_record_id | uuid | True | ; identity=—; generated=— |
| clinical_identity_id | uuid | True | ; identity=—; generated=— |
| split_name | text | True | ; identity=—; generated=— |
| class_index | integer | True | ; identity=—; generated=— |
| class_name | text | True | ; identity=—; generated=— |
| metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `dataset_split_assignments_clinical_identity_id_fkey`: `FOREIGN KEY (clinical_identity_id) REFERENCES clinical_identities(id) ON DELETE RESTRICT`
- `dataset_split_assignments_dataset_version_id_fkey`: `FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions(id) ON DELETE RESTRICT`
- `dataset_split_assignments_pkey`: `PRIMARY KEY (id)`
- `dataset_split_assignments_source_record_id_fkey`: `FOREIGN KEY (source_record_id) REFERENCES dataset_source_records(id) ON DELETE RESTRICT`
- `uq_dataset_split_assignments_record`: `UNIQUE (dataset_version_id, source_record_id)`

## public.dataset_split_images

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| image_id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| dataset_id | uuid | False | ; identity=—; generated=— |
| dataset_name | text | True | ; identity=—; generated=— |
| dataset_source | text | True | ; identity=—; generated=— |
| dataset_dir | text | True | ; identity=—; generated=— |
| split_name | text | True | ; identity=—; generated=— |
| class_index | integer | True | ; identity=—; generated=— |
| class_name | text | True | ; identity=—; generated=— |
| relative_path | text | True | ; identity=—; generated=— |
| absolute_path | text | False | ; identity=—; generated=— |
| filename | text | True | ; identity=—; generated=— |
| original_tfds_label | integer | False | ; identity=—; generated=— |
| project_label | integer | True | ; identity=—; generated=— |
| label_mapping_version | text | True | ; identity=—; generated=— |
| image_width | integer | False | ; identity=—; generated=— |
| image_height | integer | False | ; identity=—; generated=— |
| file_size_bytes | bigint | False | ; identity=—; generated=— |
| checksum_sha256 | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| updated_at | timestamp with time zone | True | now(); identity=—; generated=— |
| metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| dataset_version_id | uuid | False | ; identity=—; generated=— |
| dataset_materialization_id | uuid | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `dataset_split_images_dataset_id_fkey`: `FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE RESTRICT`
- `dataset_split_images_dataset_materialization_id_fkey`: `FOREIGN KEY (dataset_materialization_id) REFERENCES dataset_materializations(id) ON DELETE RESTRICT`
- `dataset_split_images_dataset_version_id_fkey`: `FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions(id) ON DELETE RESTRICT`
- `dataset_split_images_pkey`: `PRIMARY KEY (image_id)`
- `uq_dataset_split_images_path`: `UNIQUE (dataset_dir, relative_path)`

## public.dataset_split_statistics

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| dataset_version_id | uuid | True | ; identity=—; generated=— |
| scope | text | True | ; identity=—; generated=— |
| metric_name | text | True | ; identity=—; generated=— |
| numeric_value | numeric | False | ; identity=—; generated=— |
| text_value | text | False | ; identity=—; generated=— |
| details_json | jsonb | False | ; identity=—; generated=— |
| computed_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `dataset_split_statistics_dataset_version_id_fkey`: `FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions(id) ON DELETE RESTRICT`
- `dataset_split_statistics_pkey`: `PRIMARY KEY (id)`

## public.dataset_split_validation_checks

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| dataset_version_id | uuid | True | ; identity=—; generated=— |
| check_name | text | True | ; identity=—; generated=— |
| status | text | True | ; identity=—; generated=— |
| observed_value | text | False | ; identity=—; generated=— |
| expected_value | text | False | ; identity=—; generated=— |
| details_json | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| blocking_for_validation | boolean | True | false; identity=—; generated=— |
| blocking_for_freeze | boolean | True | false; identity=—; generated=— |
| executed_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `dataset_split_validation_checks_dataset_version_id_fkey`: `FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions(id) ON DELETE RESTRICT`
- `dataset_split_validation_checks_pkey`: `PRIMARY KEY (id)`

## public.dataset_splits

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| dataset_id | uuid | False | ; identity=—; generated=— |
| split_name | text | True | ; identity=—; generated=— |
| num_samples | integer | False | ; identity=—; generated=— |
| class_distribution | jsonb | False | '{}'::jsonb; identity=—; generated=— |
| split_strategy | text | False | ; identity=—; generated=— |
| random_seed | integer | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | False | now(); identity=—; generated=— |
| metadata | jsonb | False | '{}'::jsonb; identity=—; generated=— |

PK/FK/UNIQUE:

- `dataset_splits_dataset_id_fkey`: `FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE RESTRICT`
- `dataset_splits_pkey`: `PRIMARY KEY (id)`

## public.dataset_version_sources

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| dataset_version_id | uuid | True | ; identity=—; generated=— |
| dataset_id | uuid | True | ; identity=—; generated=— |
| role | text | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `dataset_version_sources_dataset_id_fkey`: `FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE RESTRICT`
- `dataset_version_sources_dataset_version_id_fkey`: `FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions(id) ON DELETE RESTRICT`
- `dataset_version_sources_pkey`: `PRIMARY KEY (dataset_version_id, dataset_id, role)`

## public.dataset_versions

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| name | text | True | ; identity=—; generated=— |
| semantic_version | text | True | ; identity=—; generated=— |
| status | text | True | 'DRAFT'::text; identity=—; generated=— |
| grouping_strategy | text | True | ; identity=—; generated=— |
| grouping_field | text | True | ; identity=—; generated=— |
| stratification_strategy | text | True | ; identity=—; generated=— |
| split_algorithm | text | True | ; identity=—; generated=— |
| split_algorithm_version | text | True | ; identity=—; generated=— |
| random_seed | integer | True | ; identity=—; generated=— |
| target_train_ratio | numeric(8,7) | True | ; identity=—; generated=— |
| target_val_ratio | numeric(8,7) | True | ; identity=—; generated=— |
| target_test_ratio | numeric(8,7) | True | ; identity=—; generated=— |
| positive_class | text | True | ; identity=—; generated=— |
| class_mapping | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| source_record_count | bigint | True | 0; identity=—; generated=— |
| methodology_json | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| generated_at | timestamp with time zone | False | ; identity=—; generated=— |
| validated_at | timestamp with time zone | False | ; identity=—; generated=— |
| frozen_at | timestamp with time zone | False | ; identity=—; generated=— |
| archived_at | timestamp with time zone | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `dataset_versions_pkey`: `PRIMARY KEY (id)`
- `uq_dataset_versions_name_semver`: `UNIQUE (name, semantic_version)`

## public.datasets

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| name | text | True | ; identity=—; generated=— |
| source | text | False | ; identity=—; generated=— |
| version | text | False | ; identity=—; generated=— |
| description | text | False | ; identity=—; generated=— |
| total_images | integer | False | ; identity=—; generated=— |
| num_classes | integer | False | ; identity=—; generated=— |
| class_names | text[] | False | ; identity=—; generated=— |
| class_distribution | jsonb | False | '{}'::jsonb; identity=—; generated=— |
| license | text | False | ; identity=—; generated=— |
| url | text | False | ; identity=—; generated=— |
| local_path | text | False | ; identity=—; generated=— |
| checksum | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | False | now(); identity=—; generated=— |
| metadata | jsonb | False | '{}'::jsonb; identity=—; generated=— |
| provider | text | False | ; identity=—; generated=— |
| source_type | text | False | ; identity=—; generated=— |
| source_reference | text | False | ; identity=—; generated=— |
| source_version | text | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `datasets_pkey`: `PRIMARY KEY (id)`

## public.deployed_model_versions

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| model_version_id | uuid | True | ; identity=—; generated=— |
| checkpoint_artifact_id | uuid | True | ; identity=—; generated=— |
| threshold_calibration_id | uuid | False | ; identity=—; generated=— |
| deployment_name | text | True | ; identity=—; generated=— |
| environment | text | True | ; identity=—; generated=— |
| alias | text | True | ; identity=—; generated=— |
| artifact_sha256 | text | True | ; identity=—; generated=— |
| artifact_size_bytes | bigint | False | ; identity=—; generated=— |
| threshold_value | numeric | True | ; identity=—; generated=— |
| threshold_profile_snapshot | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| preprocessing_profile_snapshot | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| image_quality_policy_snapshot | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| label_mapping_snapshot | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| positive_label | text | True | 'parasitized'::text; identity=—; generated=— |
| score_name | text | True | 'probability_parasitized'::text; identity=—; generated=— |
| status | text | True | 'pending'::text; identity=—; generated=— |
| supersedes_deployment_id | uuid | False | ; identity=—; generated=— |
| rollback_of_deployment_id | uuid | False | ; identity=—; generated=— |
| deployed_at | timestamp with time zone | False | ; identity=—; generated=— |
| retired_at | timestamp with time zone | False | ; identity=—; generated=— |
| deployed_by | text | False | ; identity=—; generated=— |
| retired_by | text | False | ; identity=—; generated=— |
| deployment_reason | text | False | ; identity=—; generated=— |
| retirement_reason | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| threshold_assessment_attempt_id | uuid | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `deployed_model_versions_pkey`: `PRIMARY KEY (id)`
- `deployed_model_versions_threshold_assessment_attempt_id_fkey`: `FOREIGN KEY (threshold_assessment_attempt_id) REFERENCES assessment_attempts(id) ON DELETE RESTRICT`
- `fk_deployed_model_versions_rollback`: `FOREIGN KEY (rollback_of_deployment_id) REFERENCES deployed_model_versions(id) ON DELETE RESTRICT`
- `fk_deployed_model_versions_supersedes`: `FOREIGN KEY (supersedes_deployment_id) REFERENCES deployed_model_versions(id) ON DELETE RESTRICT`
- `fk_deployed_model_versions_threshold_version`: `FOREIGN KEY (threshold_calibration_id, model_version_id) REFERENCES run_threshold_calibration(run_threshold_calibration_id, model_version_id) ON DELETE RESTRICT`
- `fk_deployed_model_versions_version_artifact`: `FOREIGN KEY (model_version_id, checkpoint_artifact_id) REFERENCES model_versions(id, checkpoint_artifact_id) ON DELETE RESTRICT`

## public.environment_packages

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| run_id | uuid | False | ; identity=—; generated=— |
| package_name | text | True | ; identity=—; generated=— |
| package_version | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | False | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `environment_packages_pkey`: `PRIMARY KEY (id)`
- `environment_packages_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE RESTRICT`

## public.errors

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| run_id | uuid | False | ; identity=—; generated=— |
| error_type | text | False | ; identity=—; generated=— |
| error_message | text | False | ; identity=—; generated=— |
| stack_trace | text | False | ; identity=—; generated=— |
| script_name | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | False | now(); identity=—; generated=— |
| metadata | jsonb | False | '{}'::jsonb; identity=—; generated=— |

PK/FK/UNIQUE:

- `errors_pkey`: `PRIMARY KEY (id)`
- `errors_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE RESTRICT`

## public.evaluation_ensemble_members

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| evaluation_id | uuid | True | ; identity=—; generated=— |
| ordinal | integer | True | ; identity=—; generated=— |
| model_version_id | uuid | True | ; identity=—; generated=— |
| checkpoint_artifact_id | uuid | True | ; identity=—; generated=— |
| weight | numeric | True | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `v2_evaluation_ensemble_members_foreign_6aec504c7a2f`: `FOREIGN KEY (checkpoint_artifact_id) REFERENCES artifacts(id) ON DELETE RESTRICT`
- `v2_evaluation_ensemble_members_foreign_a402d28a70f6`: `FOREIGN KEY (evaluation_id) REFERENCES evaluations(id) ON DELETE RESTRICT`
- `v2_evaluation_ensemble_members_foreign_b946b2b207f3`: `FOREIGN KEY (model_version_id) REFERENCES model_versions(id) ON DELETE RESTRICT`
- `v2_evaluation_ensemble_members_primary_0f6c3f155b09`: `PRIMARY KEY (evaluation_id, ordinal)`
- `v2_evaluation_ensemble_members_unique_3a2092158e31`: `UNIQUE (evaluation_id, model_version_id)`

## public.evaluations

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | public.gen_random_uuid(); identity=—; generated=— |
| run_id | uuid | True | ; identity=—; generated=— |
| training_run_id | uuid | True | ; identity=—; generated=— |
| model_version_id | uuid | False | ; identity=—; generated=— |
| checkpoint_artifact_id | uuid | False | ; identity=—; generated=— |
| dataset_version_id | uuid | True | ; identity=—; generated=— |
| split | text | True | ; identity=—; generated=— |
| evaluation_role | text | True | ; identity=—; generated=— |
| purpose | text | True | ; identity=—; generated=— |
| dataset_origin_id | uuid | False | ; identity=—; generated=— |
| dataset_origin_role | text | False | ; identity=—; generated=— |
| population_manifest_uri | text | False | ; identity=—; generated=— |
| population_manifest_sha256 | text | False | ; identity=—; generated=— |
| dataset_provenance_uri | text | False | ; identity=—; generated=— |
| dataset_provenance_sha256 | text | False | ; identity=—; generated=— |
| subject_kind | text | True | ; identity=—; generated=— |
| protocol_version | text | True | ; identity=—; generated=— |
| protocol_hash | text | True | ; identity=—; generated=— |
| population_hash | text | True | ; identity=—; generated=— |
| input_contract_hash | text | True | ; identity=—; generated=— |
| comparison_contract_hash | text | True | ; identity=—; generated=— |
| protocol_snapshot | jsonb | True | ; identity=—; generated=— |
| source_kind | text | True | ; identity=—; generated=— |
| source_record_key | text | True | ; identity=—; generated=— |
| source_record_phase | text | True | ; identity=—; generated=— |
| source_event_id | uuid | False | ; identity=—; generated=— |
| event_kind | text | False | ; identity=—; generated=— |
| event_phase | text | False | ; identity=—; generated=— |
| event_key | text | False | ; identity=—; generated=— |
| source_assessment_attempt_id | uuid | False | ; identity=—; generated=— |
| threshold_used | numeric | True | ; identity=—; generated=— |
| threshold_source | text | True | ; identity=—; generated=— |
| calibration_id | uuid | False | ; identity=—; generated=— |
| metric_definition | text | True | 'binary_nullable_v2'::text; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `fk_evaluation_e10_record`: `FOREIGN KEY (run_id, event_kind, event_phase, event_key) REFERENCES train_execution_records(run_id, kind, phase, record_key) DEFERRABLE INITIALLY DEFERRED`
- `fk_v2_evaluation_dataset_origin`: `FOREIGN KEY (dataset_version_id, dataset_origin_id, dataset_origin_role) REFERENCES dataset_version_sources(dataset_version_id, dataset_id, role) ON DELETE RESTRICT`
- `v2_evaluations_foreign_0baa7d166e2f`: `FOREIGN KEY (calibration_id) REFERENCES run_threshold_calibration(run_threshold_calibration_id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED`
- `v2_evaluations_foreign_14b20ff24e12`: `FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions(id) ON DELETE RESTRICT`
- `v2_evaluations_foreign_4e6a43d876af`: `FOREIGN KEY (training_run_id) REFERENCES runs(id) ON DELETE RESTRICT`
- `v2_evaluations_foreign_6aec504c7a2f`: `FOREIGN KEY (checkpoint_artifact_id) REFERENCES artifacts(id) ON DELETE RESTRICT`
- `v2_evaluations_foreign_6cfcdf2998f5`: `FOREIGN KEY (model_version_id, training_run_id) REFERENCES model_versions(id, training_run_id) ON DELETE RESTRICT`
- `v2_evaluations_foreign_c764adede219`: `FOREIGN KEY (source_assessment_attempt_id) REFERENCES assessment_attempts(id) ON DELETE RESTRICT`
- `v2_evaluations_foreign_db5338c19de4`: `FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE RESTRICT`
- `v2_evaluations_primary_8c8464f42472`: `PRIMARY KEY (id)`
- `v2_evaluations_unique_2b29f071653b`: `UNIQUE (run_id, source_kind, source_record_phase, source_record_key)`
- `v2_evaluations_unique_927a8d4fe69d`: `UNIQUE (id, run_id)`

## public.execution_logs

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| run_id | uuid | False | ; identity=—; generated=— |
| log_level | text | False | ; identity=—; generated=— |
| message | text | False | ; identity=—; generated=— |
| source | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | False | now(); identity=—; generated=— |
| metadata | jsonb | False | '{}'::jsonb; identity=—; generated=— |

PK/FK/UNIQUE:

- `execution_logs_pkey`: `PRIMARY KEY (id)`
- `execution_logs_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE RESTRICT`

## public.experiment_execution_events

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | bigint | True | ; identity=a; generated=— |
| owner | uuid | True | ; identity=—; generated=— |
| event | text | True | ; identity=—; generated=— |
| payload | jsonb | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | clock_timestamp(); identity=—; generated=— |

PK/FK/UNIQUE:

- `experiment_execution_events_pkey`: `PRIMARY KEY (id)`

## public.experiment_execution_gate

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| singleton | boolean | True | true; identity=—; generated=— |
| owner | uuid | False | ; identity=—; generated=— |
| db_pid | integer | False | ; identity=—; generated=— |
| process_evidence | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| blocked_reason | text | False | ; identity=—; generated=— |
| updated_at | timestamp with time zone | True | clock_timestamp(); identity=—; generated=— |

PK/FK/UNIQUE:

- `experiment_execution_gate_pkey`: `PRIMARY KEY (singleton)`

## public.experimental_campaigns

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| experiment_id | uuid | False | ; identity=—; generated=— |
| name | text | True | ; identity=—; generated=— |
| purpose | text | True | ; identity=—; generated=— |
| state | text | True | 'draft'::text; identity=—; generated=— |
| dataset_version_id | uuid | True | ; identity=—; generated=— |
| dataset_snapshot | jsonb | True | ; identity=—; generated=— |
| dataset_evidence_id | uuid | True | ; identity=—; generated=— |
| requested | jsonb | True | ; identity=—; generated=— |
| protocol | jsonb | True | ; identity=—; generated=— |
| environment | jsonb | True | ; identity=—; generated=— |
| registry_snapshot | jsonb | False | ; identity=—; generated=— |
| contract | jsonb | False | ; identity=—; generated=— |
| canonical_contract | text | False | ; identity=—; generated=— |
| contract_hash | text | False | ; identity=—; generated=— |
| expected_count | integer | True | 0; identity=—; generated=— |
| actor | text | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| updated_at | timestamp with time zone | True | now(); identity=—; generated=— |
| frozen_at | timestamp with time zone | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `experimental_campaigns_dataset_evidence_id_fkey`: `FOREIGN KEY (dataset_evidence_id) REFERENCES audit_events(id) ON DELETE RESTRICT`
- `experimental_campaigns_dataset_version_id_fkey`: `FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions(id) ON DELETE RESTRICT`
- `experimental_campaigns_experiment_id_fkey`: `FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE RESTRICT`
- `experimental_campaigns_pkey`: `PRIMARY KEY (id)`

## public.experiments

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| name | text | True | ; identity=—; generated=— |
| description | text | False | ; identity=—; generated=— |
| project_name | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | False | now(); identity=—; generated=— |
| updated_at | timestamp with time zone | False | now(); identity=—; generated=— |
| metadata | jsonb | False | '{}'::jsonb; identity=—; generated=— |

PK/FK/UNIQUE:

- `experiments_pkey`: `PRIMARY KEY (id)`

## public.explainability_results

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| run_id | uuid | False | ; identity=—; generated=— |
| prediction_id | uuid | False | ; identity=—; generated=— |
| method | text | True | ; identity=—; generated=— |
| image_path | text | False | ; identity=—; generated=— |
| output_path | text | False | ; identity=—; generated=— |
| true_label | text | False | ; identity=—; generated=— |
| predicted_label | text | False | ; identity=—; generated=— |
| score | numeric | False | ; identity=—; generated=— |
| case_type | text | False | ; identity=—; generated=— |
| last_conv_layer | text | False | ; identity=—; generated=— |
| explanation_parameters | jsonb | False | '{}'::jsonb; identity=—; generated=— |
| success | boolean | False | true; identity=—; generated=— |
| error_message | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | False | now(); identity=—; generated=— |
| metadata | jsonb | False | '{}'::jsonb; identity=—; generated=— |

PK/FK/UNIQUE:

- `explainability_results_pkey`: `PRIMARY KEY (id)`
- `explainability_results_prediction_id_fkey`: `FOREIGN KEY (prediction_id) REFERENCES predictions(id) ON DELETE RESTRICT`
- `explainability_results_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE RESTRICT`

## public.identity_evidence

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| source_record_id | uuid | True | ; identity=—; generated=— |
| clinical_identity_id | uuid | True | ; identity=—; generated=— |
| evidence_type | text | True | ; identity=—; generated=— |
| evidence_level | text | True | ; identity=—; generated=— |
| mapping_method | text | True | ; identity=—; generated=— |
| evidence_reference | text | False | ; identity=—; generated=— |
| official_source_reference | text | False | ; identity=—; generated=— |
| evidence_json | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `identity_evidence_clinical_identity_id_fkey`: `FOREIGN KEY (clinical_identity_id) REFERENCES clinical_identities(id) ON DELETE RESTRICT`
- `identity_evidence_pkey`: `PRIMARY KEY (id)`
- `identity_evidence_source_record_id_fkey`: `FOREIGN KEY (source_record_id) REFERENCES dataset_source_records(id) ON DELETE RESTRICT`

## public.image_analysis_jobs

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| inference_run_id | uuid | True | ; identity=—; generated=— |
| deployed_model_version_id | uuid | True | ; identity=—; generated=— |
| model_version_id | uuid | True | ; identity=—; generated=— |
| input_artifact_id | uuid | False | ; identity=—; generated=— |
| source_image_id | uuid | False | ; identity=—; generated=— |
| idempotency_key | text | False | ; identity=—; generated=— |
| sample_id | text | False | ; identity=—; generated=— |
| patient_id | text | False | ; identity=—; generated=— |
| slide_id | text | False | ; identity=—; generated=— |
| status | text | True | 'pending'::text; identity=—; generated=— |
| quality_status | text | True | 'not_assessed'::text; identity=—; generated=— |
| quality_metrics | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| threshold_used | numeric | False | ; identity=—; generated=— |
| threshold_source | text | False | ; identity=—; generated=— |
| summary | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| total_cells | integer | False | ; identity=—; generated=— |
| positive_cells | integer | False | ; identity=—; generated=— |
| started_at | timestamp with time zone | False | ; identity=—; generated=— |
| completed_at | timestamp with time zone | False | ; identity=—; generated=— |
| error_message | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| updated_at | timestamp with time zone | True | now(); identity=—; generated=— |
| metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |

PK/FK/UNIQUE:

- `fk_image_analysis_jobs_input_artifact`: `FOREIGN KEY (input_artifact_id) REFERENCES artifacts(id) ON DELETE RESTRICT`
- `fk_image_analysis_jobs_run_deployment_version`: `FOREIGN KEY (inference_run_id, deployed_model_version_id, model_version_id) REFERENCES run_model_deployments(run_id, deployed_model_version_id, model_version_id) ON DELETE RESTRICT`
- `fk_image_analysis_jobs_source_image`: `FOREIGN KEY (source_image_id) REFERENCES dataset_split_images(image_id) ON DELETE RESTRICT`
- `image_analysis_jobs_pkey`: `PRIMARY KEY (id)`

## public.image_connected_components

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| detection_run_id | uuid | True | ; identity=—; generated=— |
| analysis_run_id | uuid | True | ; identity=—; generated=— |
| analysis_run_image_id | uuid | True | ; identity=—; generated=— |
| microscopy_image_id | uuid | True | ; identity=—; generated=— |
| component_index | integer | True | ; identity=—; generated=— |
| bbox_x | integer | True | ; identity=—; generated=— |
| bbox_y | integer | True | ; identity=—; generated=— |
| bbox_width | integer | True | ; identity=—; generated=— |
| bbox_height | integer | True | ; identity=—; generated=— |
| centroid_x | double precision | True | ; identity=—; generated=— |
| centroid_y | double precision | True | ; identity=—; generated=— |
| area_px | integer | True | ; identity=—; generated=— |
| perimeter_px | double precision | False | ; identity=—; generated=— |
| circularity | double precision | False | ; identity=—; generated=— |
| solidity | double precision | False | ; identity=—; generated=— |
| touches_border | boolean | True | ; identity=—; generated=— |
| component_status | character varying(30) | True | ; identity=—; generated=— |
| rejection_code | character varying(80) | False | ; identity=—; generated=— |
| metrics_json | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `fk_components_detection_analysis`: `FOREIGN KEY (detection_run_id, analysis_run_id) REFERENCES cell_detection_runs(id, analysis_run_id) ON DELETE RESTRICT`
- `fk_components_frozen_image`: `FOREIGN KEY (analysis_run_image_id, analysis_run_id, microscopy_image_id) REFERENCES microscopy_analysis_run_images(id, analysis_run_id, microscopy_image_id) ON DELETE RESTRICT`
- `image_connected_components_pkey`: `PRIMARY KEY (id)`
- `uq_image_connected_components_identity`: `UNIQUE (id, detection_run_id, analysis_run_image_id, microscopy_image_id)`
- `uq_image_connected_components_run_image_index`: `UNIQUE (detection_run_id, analysis_run_image_id, component_index)`

## public.image_ingestion_batches

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| subject_id | uuid | True | ; identity=—; generated=— |
| case_id | uuid | True | ; identity=—; generated=— |
| sample_id | uuid | True | ; identity=—; generated=— |
| slide_id | uuid | True | ; identity=—; generated=— |
| acquisition_origin | character varying(40) | True | ; identity=—; generated=— |
| source_system | character varying(120) | False | ; identity=—; generated=— |
| source_group_key | character varying(240) | False | ; identity=—; generated=— |
| expected_image_count | integer | False | ; identity=—; generated=— |
| received_image_count | integer | True | 0; identity=—; generated=— |
| status | character varying(20) | True | 'pending'::character varying; identity=—; generated=— |
| created_by | uuid | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| updated_at | timestamp with time zone | True | now(); identity=—; generated=— |
| completed_at | timestamp with time zone | False | ; identity=—; generated=— |
| metadata_json | jsonb | True | '{}'::jsonb; identity=—; generated=— |

PK/FK/UNIQUE:

- `image_ingestion_batches_case_id_fkey`: `FOREIGN KEY (case_id) REFERENCES scientific_cases(id) ON DELETE RESTRICT`
- `image_ingestion_batches_created_by_fkey`: `FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT`
- `image_ingestion_batches_pkey`: `PRIMARY KEY (id)`
- `image_ingestion_batches_sample_id_fkey`: `FOREIGN KEY (sample_id) REFERENCES blood_samples(id) ON DELETE RESTRICT`
- `image_ingestion_batches_slide_id_fkey`: `FOREIGN KEY (slide_id) REFERENCES smear_slides(id) ON DELETE RESTRICT`
- `image_ingestion_batches_subject_id_fkey`: `FOREIGN KEY (subject_id) REFERENCES research_subjects(id) ON DELETE RESTRICT`

## public.image_quality_assessments

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| analysis_run_id | uuid | True | ; identity=—; generated=— |
| analysis_run_image_id | uuid | True | ; identity=—; generated=— |
| microscopy_image_id | uuid | True | ; identity=—; generated=— |
| assessment_status | character varying(20) | True | ; identity=—; generated=— |
| quality_verdict | character varying(20) | True | ; identity=—; generated=— |
| integrity_verified | boolean | True | false; identity=—; generated=— |
| checksum_verified | boolean | True | false; identity=—; generated=— |
| decoded_successfully | boolean | True | false; identity=—; generated=— |
| width_px | integer | True | ; identity=—; generated=— |
| height_px | integer | True | ; identity=—; generated=— |
| pixel_count | bigint | True | ; identity=—; generated=— |
| channel_count | integer | False | ; identity=—; generated=— |
| bit_depth | integer | False | ; identity=—; generated=— |
| color_space | character varying(80) | False | ; identity=—; generated=— |
| analyzed_width_px | integer | True | ; identity=—; generated=— |
| analyzed_height_px | integer | True | ; identity=—; generated=— |
| analysis_scale | double precision | True | ; identity=—; generated=— |
| brightness_mean | double precision | False | ; identity=—; generated=— |
| brightness_p05 | double precision | False | ; identity=—; generated=— |
| brightness_p50 | double precision | False | ; identity=—; generated=— |
| brightness_p95 | double precision | False | ; identity=—; generated=— |
| contrast_p95_p05 | double precision | False | ; identity=—; generated=— |
| luminance_stddev | double precision | False | ; identity=—; generated=— |
| entropy_bits | double precision | False | ; identity=—; generated=— |
| laplacian_variance | double precision | False | ; identity=—; generated=— |
| tenengrad_mean | double precision | False | ; identity=—; generated=— |
| dark_pixel_ratio | double precision | False | ; identity=—; generated=— |
| bright_pixel_ratio | double precision | False | ; identity=—; generated=— |
| near_black_border_ratio | double precision | False | ; identity=—; generated=— |
| usable_field_ratio | double precision | False | ; identity=—; generated=— |
| warning_codes | jsonb | True | '[]'::jsonb; identity=—; generated=— |
| failure_codes | jsonb | True | '[]'::jsonb; identity=—; generated=— |
| metrics_json | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| started_at | timestamp with time zone | False | ; identity=—; generated=— |
| completed_at | timestamp with time zone | False | ; identity=—; generated=— |
| error_code | character varying(80) | False | ; identity=—; generated=— |
| error_message | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `image_quality_assessments_analysis_run_id_fkey`: `FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT`
- `image_quality_assessments_analysis_run_id_microscopy_image__key`: `UNIQUE (analysis_run_id, microscopy_image_id)`
- `image_quality_assessments_analysis_run_image_id_analysis_r_fkey`: `FOREIGN KEY (analysis_run_image_id, analysis_run_id, microscopy_image_id) REFERENCES microscopy_analysis_run_images(id, analysis_run_id, microscopy_image_id) ON DELETE RESTRICT`
- `image_quality_assessments_microscopy_image_id_fkey`: `FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images(id) ON DELETE RESTRICT`
- `image_quality_assessments_pkey`: `PRIMARY KEY (id)`

## public.local_execution_jobs

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| principal | text | True | ; identity=—; generated=— |
| agent_id | uuid | True | ; identity=—; generated=— |
| owner | uuid | True | ; identity=—; generated=— |
| request_hash | text | True | ; identity=—; generated=— |
| campaign_id | uuid | True | ; identity=—; generated=— |
| run_id | uuid | False | ; identity=—; generated=— |
| state | text | True | ; identity=—; generated=— |
| session | jsonb | False | ; identity=—; generated=— |
| heartbeat_at | timestamp with time zone | True | clock_timestamp(); identity=—; generated=— |
| process | jsonb | False | ; identity=—; generated=— |
| completion | jsonb | False | ; identity=—; generated=— |
| exit_proof | jsonb | False | ; identity=—; generated=— |
| result | jsonb | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | clock_timestamp(); identity=—; generated=— |

PK/FK/UNIQUE:

- `local_execution_jobs_campaign_id_fkey`: `FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns(id)`
- `local_execution_jobs_owner_key`: `UNIQUE (owner)`
- `local_execution_jobs_pkey`: `PRIMARY KEY (id)`
- `local_execution_jobs_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES runs(id)`
- `local_execution_jobs_run_id_key`: `UNIQUE (run_id)`

## public.microscopy_analysis_events

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| analysis_run_id | uuid | True | ; identity=—; generated=— |
| microscopy_image_id | uuid | False | ; identity=—; generated=— |
| event_type | character varying(80) | True | ; identity=—; generated=— |
| stage | character varying(40) | True | ; identity=—; generated=— |
| status | character varying(30) | True | ; identity=—; generated=— |
| message_code | character varying(80) | False | ; identity=—; generated=— |
| message | text | False | ; identity=—; generated=— |
| progress_current | integer | False | ; identity=—; generated=— |
| progress_total | integer | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `microscopy_analysis_events_analysis_run_id_fkey`: `FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT`
- `microscopy_analysis_events_microscopy_image_id_fkey`: `FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images(id) ON DELETE RESTRICT`
- `microscopy_analysis_events_pkey`: `PRIMARY KEY (id)`

## public.microscopy_analysis_run_images

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| analysis_run_id | uuid | True | ; identity=—; generated=— |
| microscopy_image_id | uuid | True | ; identity=—; generated=— |
| sequence_number | integer | True | ; identity=—; generated=— |
| input_sha256 | character(64) | True | ; identity=—; generated=— |
| input_file_size_bytes | bigint | True | ; identity=—; generated=— |
| input_width_px | integer | True | ; identity=—; generated=— |
| input_height_px | integer | True | ; identity=—; generated=— |
| image_status_at_creation | character varying(30) | True | ; identity=—; generated=— |
| quality_status | character varying(20) | True | 'pending'::character varying; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `microscopy_analysis_run_image_analysis_run_id_microscopy_im_key`: `UNIQUE (analysis_run_id, microscopy_image_id)`
- `microscopy_analysis_run_image_analysis_run_id_sequence_numb_key`: `UNIQUE (analysis_run_id, sequence_number)`
- `microscopy_analysis_run_image_id_analysis_run_id_microscopy_key`: `UNIQUE (id, analysis_run_id, microscopy_image_id)`
- `microscopy_analysis_run_images_analysis_run_id_fkey`: `FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT`
- `microscopy_analysis_run_images_microscopy_image_id_fkey`: `FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images(id) ON DELETE RESTRICT`
- `microscopy_analysis_run_images_pkey`: `PRIMARY KEY (id)`

## public.microscopy_analysis_runs

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| ingestion_batch_id | uuid | True | ; identity=—; generated=— |
| subject_id | uuid | True | ; identity=—; generated=— |
| case_id | uuid | True | ; identity=—; generated=— |
| sample_id | uuid | True | ; identity=—; generated=— |
| slide_id | uuid | True | ; identity=—; generated=— |
| run_code | character varying(20) | True | ; identity=—; generated=— |
| run_status | character varying(30) | True | ; identity=—; generated=— |
| active_stage | character varying(30) | True | ; identity=—; generated=— |
| quality_gate_status | character varying(20) | True | ; identity=—; generated=— |
| ready_for_analysis | boolean | True | false; identity=—; generated=— |
| quality_profile_key | character varying(80) | True | ; identity=—; generated=— |
| quality_profile_version | character varying(40) | True | ; identity=—; generated=— |
| quality_algorithm_version | character varying(40) | True | ; identity=—; generated=— |
| quality_profile_snapshot | jsonb | True | ; identity=—; generated=— |
| input_manifest_sha256 | character(64) | True | ; identity=—; generated=— |
| input_image_count | integer | True | ; identity=—; generated=— |
| requested_by | uuid | True | ; identity=—; generated=— |
| started_at | timestamp with time zone | False | ; identity=—; generated=— |
| completed_at | timestamp with time zone | False | ; identity=—; generated=— |
| failed_at | timestamp with time zone | False | ; identity=—; generated=— |
| error_code | character varying(80) | False | ; identity=—; generated=— |
| error_message | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| updated_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `microscopy_analysis_runs_case_id_fkey`: `FOREIGN KEY (case_id) REFERENCES scientific_cases(id) ON DELETE RESTRICT`
- `microscopy_analysis_runs_ingestion_batch_id_fkey`: `FOREIGN KEY (ingestion_batch_id) REFERENCES image_ingestion_batches(id) ON DELETE RESTRICT`
- `microscopy_analysis_runs_pkey`: `PRIMARY KEY (id)`
- `microscopy_analysis_runs_requested_by_fkey`: `FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE RESTRICT`
- `microscopy_analysis_runs_run_code_key`: `UNIQUE (run_code)`
- `microscopy_analysis_runs_sample_id_fkey`: `FOREIGN KEY (sample_id) REFERENCES blood_samples(id) ON DELETE RESTRICT`
- `microscopy_analysis_runs_slide_id_fkey`: `FOREIGN KEY (slide_id) REFERENCES smear_slides(id) ON DELETE RESTRICT`
- `microscopy_analysis_runs_subject_id_fkey`: `FOREIGN KEY (subject_id) REFERENCES research_subjects(id) ON DELETE RESTRICT`

## public.microscopy_images

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| slide_id | uuid | True | ; identity=—; generated=— |
| image_code | character varying(120) | True | ; identity=—; generated=— |
| storage_provider | character varying(40) | True | 'local'::character varying; identity=—; generated=— |
| storage_key | text | True | ; identity=—; generated=— |
| original_filename | text | False | ; identity=—; generated=— |
| mime_type | character varying(120) | True | ; identity=—; generated=— |
| file_size_bytes | bigint | True | ; identity=—; generated=— |
| sha256 | character(64) | True | ; identity=—; generated=— |
| width_px | integer | True | ; identity=—; generated=— |
| height_px | integer | True | ; identity=—; generated=— |
| bit_depth | integer | False | ; identity=—; generated=— |
| magnification | numeric | False | ; identity=—; generated=— |
| objective_lens | character varying(120) | False | ; identity=—; generated=— |
| microscope_reference | character varying(160) | False | ; identity=—; generated=— |
| camera_reference | character varying(160) | False | ; identity=—; generated=— |
| captured_at | timestamp with time zone | False | ; identity=—; generated=— |
| status | character varying(20) | True | 'registered'::character varying; identity=—; generated=— |
| metadata_json | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| updated_at | timestamp with time zone | True | now(); identity=—; generated=— |
| created_by | uuid | True | ; identity=—; generated=— |
| updated_by | uuid | False | ; identity=—; generated=— |
| archived_at | timestamp with time zone | False | ; identity=—; generated=— |
| archived_by | uuid | False | ; identity=—; generated=— |
| acquisition_origin | character varying(40) | True | 'manual_upload'::character varying; identity=—; generated=— |
| source_system | character varying(120) | False | ; identity=—; generated=— |
| source_component_id | character varying(240) | False | ; identity=—; generated=— |
| source_image_name | character varying(500) | False | ; identity=—; generated=— |
| source_relative_path | text | False | ; identity=—; generated=— |
| image_sequence_number | integer | False | ; identity=—; generated=— |
| detected_format | character varying(20) | False | ; identity=—; generated=— |
| channel_count | integer | False | ; identity=—; generated=— |
| color_space | character varying(80) | False | ; identity=—; generated=— |
| orientation | character varying(80) | False | ; identity=—; generated=— |
| ingestion_batch_id | uuid | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `microscopy_images_archived_by_fkey`: `FOREIGN KEY (archived_by) REFERENCES users(id) ON DELETE RESTRICT`
- `microscopy_images_created_by_fkey`: `FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT`
- `microscopy_images_ingestion_batch_id_fkey`: `FOREIGN KEY (ingestion_batch_id) REFERENCES image_ingestion_batches(id) ON DELETE RESTRICT`
- `microscopy_images_pkey`: `PRIMARY KEY (id)`
- `microscopy_images_slide_id_fkey`: `FOREIGN KEY (slide_id) REFERENCES smear_slides(id) ON DELETE RESTRICT`
- `microscopy_images_updated_by_fkey`: `FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE RESTRICT`
- `uq_microscopy_images_slide_code`: `UNIQUE (slide_id, image_code)`
- `uq_microscopy_images_slide_sha256`: `UNIQUE (slide_id, sha256)`

## public.model_versions

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| model_id | uuid | False | ; identity=—; generated=— |
| version_name | text | False | ; identity=—; generated=— |
| checkpoint_path | text | False | ; identity=—; generated=— |
| final_model_path | text | False | ; identity=—; generated=— |
| best_model_path | text | False | ; identity=—; generated=— |
| training_run_id | uuid | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | False | now(); identity=—; generated=— |
| metadata | jsonb | False | '{}'::jsonb; identity=—; generated=— |
| model_name | text | False | ; identity=—; generated=— |
| version_number | integer | False | ; identity=—; generated=— |
| checkpoint_artifact_id | uuid | False | ; identity=—; generated=— |
| artifact_uri | text | False | ; identity=—; generated=— |
| artifact_sha256 | text | False | ; identity=—; generated=— |
| artifact_size_bytes | bigint | False | ; identity=—; generated=— |
| artifact_hash_reuse_justification | text | False | ; identity=—; generated=— |
| framework | text | False | ; identity=—; generated=— |
| framework_version | text | False | ; identity=—; generated=— |
| preprocessing_profile_snapshot | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| class_mapping | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| input_signature | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| output_signature | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| status | text | True | 'discovered'::text; identity=—; generated=— |
| lineage_status | text | True | 'unresolved'::text; identity=—; generated=— |
| validated_at | timestamp with time zone | False | ; identity=—; generated=— |
| approved_at | timestamp with time zone | False | ; identity=—; generated=— |
| retired_at | timestamp with time zone | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `fk_model_versions_checkpoint_artifact_owner`: `FOREIGN KEY (checkpoint_artifact_id, training_run_id) REFERENCES artifacts(id, run_id) ON DELETE RESTRICT`
- `model_versions_model_id_fkey`: `FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE RESTRICT`
- `model_versions_pkey`: `PRIMARY KEY (id)`
- `model_versions_training_run_id_fkey`: `FOREIGN KEY (training_run_id) REFERENCES runs(id) ON DELETE RESTRICT`

## public.models

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| name | text | True | ; identity=—; generated=— |
| model_type | text | True | ; identity=—; generated=— |
| framework | text | False | ; identity=—; generated=— |
| architecture | text | False | ; identity=—; generated=— |
| description | text | False | ; identity=—; generated=— |
| input_shape | text | False | ; identity=—; generated=— |
| output_shape | text | False | ; identity=—; generated=— |
| num_parameters | bigint | False | ; identity=—; generated=— |
| pretrained | boolean | False | false; identity=—; generated=— |
| pretrained_source | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | False | now(); identity=—; generated=— |
| metadata | jsonb | False | '{}'::jsonb; identity=—; generated=— |

PK/FK/UNIQUE:

- `models_pkey`: `PRIMARY KEY (id)`

## public.predictions

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| run_id | uuid | False | ; identity=—; generated=— |
| dataset_id | uuid | False | ; identity=—; generated=— |
| image_id | text | False | ; identity=—; generated=— |
| image_path | text | False | ; identity=—; generated=— |
| true_label | text | False | ; identity=—; generated=— |
| predicted_label | text | False | ; identity=—; generated=— |
| score | numeric | False | ; identity=—; generated=— |
| score_positive_label | numeric | False | ; identity=—; generated=— |
| threshold | numeric | False | ; identity=—; generated=— |
| is_correct | boolean | False | ; identity=—; generated=— |
| case_type | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | False | now(); identity=—; generated=— |
| metadata | jsonb | False | '{}'::jsonb; identity=—; generated=— |
| image_analysis_job_id | uuid | False | ; identity=—; generated=— |
| model_version_id | uuid | False | ; identity=—; generated=— |
| deployed_model_version_id | uuid | False | ; identity=—; generated=— |
| inference_run_id | uuid | False | ; identity=—; generated=— |
| classifier_model_version_id | uuid | False | ; identity=—; generated=— |
| detector_model_version_id | uuid | False | ; identity=—; generated=— |
| prediction_scope | text | True | 'legacy_image'::text; identity=—; generated=— |
| cell_index | integer | False | ; identity=—; generated=— |
| source_image_id | uuid | False | ; identity=—; generated=— |
| bbox_x | numeric | False | ; identity=—; generated=— |
| bbox_y | numeric | False | ; identity=—; generated=— |
| bbox_width | numeric | False | ; identity=—; generated=— |
| bbox_height | numeric | False | ; identity=—; generated=— |
| crop_artifact_id | uuid | False | ; identity=—; generated=— |
| explanation_artifact_id | uuid | False | ; identity=—; generated=— |
| probability_parasitized | numeric | False | ; identity=—; generated=— |
| probability_uninfected | numeric | False | ; identity=—; generated=— |
| threshold_used | numeric | False | ; identity=—; generated=— |
| predicted_class | smallint | False | ; identity=—; generated=— |
| confidence_level | text | False | ; identity=—; generated=— |
| quality_status | text | False | ; identity=—; generated=— |
| review_status | text | True | 'unreviewed'::text; identity=—; generated=— |
| reviewed_label | text | False | ; identity=—; generated=— |
| reviewed_by | text | False | ; identity=—; generated=— |
| reviewed_at | timestamp with time zone | False | ; identity=—; generated=— |
| evaluation_id | uuid | False | ; identity=—; generated=— |
| dataset_source_record_id | uuid | False | ; identity=—; generated=— |
| true_class | smallint | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `fk_predictions_analysis_job`: `FOREIGN KEY (image_analysis_job_id) REFERENCES image_analysis_jobs(id) ON DELETE RESTRICT`
- `fk_predictions_classifier_model_version`: `FOREIGN KEY (classifier_model_version_id) REFERENCES model_versions(id) ON DELETE RESTRICT`
- `fk_predictions_crop_artifact`: `FOREIGN KEY (crop_artifact_id) REFERENCES artifacts(id) ON DELETE RESTRICT`
- `fk_predictions_deployed_model_version`: `FOREIGN KEY (deployed_model_version_id) REFERENCES deployed_model_versions(id) ON DELETE RESTRICT`
- `fk_predictions_detector_model_version`: `FOREIGN KEY (detector_model_version_id) REFERENCES model_versions(id) ON DELETE RESTRICT`
- `fk_predictions_explanation_artifact`: `FOREIGN KEY (explanation_artifact_id) REFERENCES artifacts(id) ON DELETE RESTRICT`
- `fk_predictions_inference_run`: `FOREIGN KEY (inference_run_id) REFERENCES runs(id) ON DELETE RESTRICT`
- `fk_predictions_job_provenance`: `FOREIGN KEY (image_analysis_job_id, inference_run_id, deployed_model_version_id, model_version_id) REFERENCES image_analysis_jobs(id, inference_run_id, deployed_model_version_id, model_version_id) ON DELETE RESTRICT`
- `fk_predictions_model_version`: `FOREIGN KEY (model_version_id) REFERENCES model_versions(id) ON DELETE RESTRICT`
- `fk_predictions_source_image`: `FOREIGN KEY (source_image_id) REFERENCES dataset_split_images(image_id) ON DELETE RESTRICT`
- `fk_v2_prediction_evaluation_run`: `FOREIGN KEY (evaluation_id, run_id) REFERENCES evaluations(id, run_id) ON DELETE RESTRICT`
- `predictions_dataset_id_fkey`: `FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE RESTRICT`
- `predictions_pkey`: `PRIMARY KEY (id)`
- `predictions_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE RESTRICT`
- `uq_v2_evaluation_sample`: `UNIQUE (evaluation_id, dataset_source_record_id)`
- `v2_predictions_foreign_a402d28a70f6`: `FOREIGN KEY (evaluation_id) REFERENCES evaluations(id) ON DELETE RESTRICT`
- `v2_predictions_foreign_e8d9af78807c`: `FOREIGN KEY (dataset_source_record_id) REFERENCES dataset_source_records(id) ON DELETE RESTRICT`

## public.quality_assessment_queue_items

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| analysis_run_id | uuid | True | ; identity=—; generated=— |
| priority | smallint | True | 50; identity=—; generated=— |
| status | character varying(20) | True | 'queued'::character varying; identity=—; generated=— |
| requested_by | uuid | True | ; identity=—; generated=— |
| requested_at | timestamp with time zone | True | now(); identity=—; generated=— |
| started_at | timestamp with time zone | False | ; identity=—; generated=— |
| completed_at | timestamp with time zone | False | ; identity=—; generated=— |
| failed_at | timestamp with time zone | False | ; identity=—; generated=— |
| attempt_count | integer | True | 0; identity=—; generated=— |
| last_error_code | character varying(80) | False | ; identity=—; generated=— |
| last_error_message | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| updated_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `quality_assessment_queue_items_analysis_run_id_fkey`: `FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT`
- `quality_assessment_queue_items_pkey`: `PRIMARY KEY (id)`
- `quality_assessment_queue_items_requested_by_fkey`: `FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE RESTRICT`

## public.quality_gate_decisions

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| analysis_run_id | uuid | True | ; identity=—; generated=— |
| decision | character varying(30) | True | ; identity=—; generated=— |
| comment | text | True | ; identity=—; generated=— |
| actor_user_id | uuid | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `quality_gate_decisions_actor_user_id_fkey`: `FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT`
- `quality_gate_decisions_analysis_run_id_fkey`: `FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT`
- `quality_gate_decisions_pkey`: `PRIMARY KEY (id)`

## public.research_subjects

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| subject_code | character varying(120) | True | ; identity=—; generated=— |
| study_reference | character varying(200) | False | ; identity=—; generated=— |
| age_group | character varying(80) | False | ; identity=—; generated=— |
| biological_sex | character varying(80) | False | ; identity=—; generated=— |
| metadata_json | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| status | character varying(20) | True | 'active'::character varying; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| updated_at | timestamp with time zone | True | now(); identity=—; generated=— |
| created_by | uuid | False | ; identity=—; generated=— |
| updated_by | uuid | False | ; identity=—; generated=— |
| archived_at | timestamp with time zone | False | ; identity=—; generated=— |
| archived_by | uuid | False | ; identity=—; generated=— |
| source_system | character varying(120) | False | ; identity=—; generated=— |
| external_patient_id | character varying(240) | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `research_subjects_archived_by_fkey`: `FOREIGN KEY (archived_by) REFERENCES users(id) ON DELETE RESTRICT`
- `research_subjects_created_by_fkey`: `FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT`
- `research_subjects_pkey`: `PRIMARY KEY (id)`
- `research_subjects_subject_code_key`: `UNIQUE (subject_code)`
- `research_subjects_updated_by_fkey`: `FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE RESTRICT`

## public.roles

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| name | text | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `roles_name_key`: `UNIQUE (name)`
- `roles_pkey`: `PRIMARY KEY (id)`

## public.run_checkpoint_policy

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| run_checkpoint_policy_id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| run_id | uuid | True | ; identity=—; generated=— |
| model_name | text | False | ; identity=—; generated=— |
| checkpoint_policy | text | True | ; identity=—; generated=— |
| checkpoint_policy_config | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| selected_epoch | integer | False | ; identity=—; generated=— |
| policy_satisfied | boolean | False | ; identity=—; generated=— |
| selected_metric | text | False | ; identity=—; generated=— |
| selected_metric_value | numeric | False | ; identity=—; generated=— |
| min_recall_required | numeric | False | ; identity=—; generated=— |
| val_recall_parasitized_selected | numeric | False | ; identity=—; generated=— |
| val_f2_parasitized_selected | numeric | False | ; identity=—; generated=— |
| val_specificity_selected | numeric | False | ; identity=—; generated=— |
| val_auc_selected | numeric | False | ; identity=—; generated=— |
| val_pr_auc_selected | numeric | False | ; identity=—; generated=— |
| val_balanced_accuracy_selected | numeric | False | ; identity=—; generated=— |
| prediction_collapse_detected | boolean | False | ; identity=—; generated=— |
| all_epochs_collapsed | boolean | False | ; identity=—; generated=— |
| checkpoint_warning | text | False | ; identity=—; generated=— |
| checkpoint_path | text | False | ; identity=—; generated=— |
| checkpoint_policy_summary_path | text | False | ; identity=—; generated=— |
| model_metadata_path | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| model_version_id | uuid | False | ; identity=—; generated=— |
| checkpoint_artifact_id | uuid | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `fk_run_checkpoint_policy_artifact_owner`: `FOREIGN KEY (checkpoint_artifact_id, run_id) REFERENCES artifacts(id, run_id) ON DELETE RESTRICT`
- `fk_run_checkpoint_policy_model_version_owner`: `FOREIGN KEY (model_version_id, run_id) REFERENCES model_versions(id, training_run_id) ON DELETE RESTRICT`
- `fk_run_checkpoint_policy_version_artifact`: `FOREIGN KEY (model_version_id, checkpoint_artifact_id) REFERENCES model_versions(id, checkpoint_artifact_id) ON DELETE RESTRICT`
- `run_checkpoint_policy_pkey`: `PRIMARY KEY (run_checkpoint_policy_id)`
- `run_checkpoint_policy_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE RESTRICT`

## public.run_clinical_metrics

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| run_clinical_metric_id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| run_id | uuid | True | ; identity=—; generated=— |
| model_id | uuid | False | ; identity=—; generated=— |
| model_name | text | False | ; identity=—; generated=— |
| split_name | text | True | ; identity=—; generated=— |
| threshold_used | numeric | False | ; identity=—; generated=— |
| threshold_source | text | False | ; identity=—; generated=— |
| accuracy | numeric | False | ; identity=—; generated=— |
| precision_parasitized | numeric | False | ; identity=—; generated=— |
| recall_parasitized | numeric | False | ; identity=—; generated=— |
| sensitivity_parasitized | numeric | False | ; identity=—; generated=— |
| specificity | numeric | False | ; identity=—; generated=— |
| f1_parasitized | numeric | False | ; identity=—; generated=— |
| f2_parasitized | numeric | False | ; identity=—; generated=— |
| roc_auc_parasitized | numeric | False | ; identity=—; generated=— |
| pr_auc_parasitized | numeric | False | ; identity=—; generated=— |
| balanced_accuracy | numeric | False | ; identity=—; generated=— |
| tn | bigint | True | ; identity=—; generated=— |
| fp | bigint | True | ; identity=—; generated=— |
| fn | bigint | True | ; identity=—; generated=— |
| tp | bigint | True | ; identity=—; generated=— |
| confusion_matrix | jsonb | True | '[]'::jsonb; identity=—; generated=— |
| classification_report | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| prediction_distribution | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| prediction_collapse | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| label_mapping_version | text | True | 'clinical_v1_parasitized_positive'::text; identity=—; generated=— |
| raw_model_score_meaning | text | True | 'probability_parasitized'::text; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| evaluation_id | uuid | True | ; identity=—; generated=— |
| sample_count | numeric | False | ((((tn)::numeric + (fp)::numeric) + (fn)::numeric) + (tp)::numeric); identity=—; generated=s |
| auc_unavailability_reason | text | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `fk_metric_evaluation_run`: `FOREIGN KEY (evaluation_id, run_id) REFERENCES evaluations(id, run_id) ON DELETE RESTRICT`
- `run_clinical_metrics_model_id_fkey`: `FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE RESTRICT`
- `run_clinical_metrics_pkey`: `PRIMARY KEY (run_clinical_metric_id)`
- `run_clinical_metrics_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE RESTRICT`
- `v2_run_clinical_metrics_unique_f9437c271ff6`: `UNIQUE (evaluation_id)`

## public.run_configurations

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| run_id | uuid | True | ; identity=—; generated=— |
| architecture | text | True | ; identity=—; generated=— |
| adapter_version | text | True | ; identity=—; generated=— |
| optimizer | text | True | ; identity=—; generated=— |
| learning_rate | double precision | True | ; identity=—; generated=— |
| fine_tune_learning_rate | double precision | True | ; identity=—; generated=— |
| batch_size | integer | True | ; identity=—; generated=— |
| random_seed | bigint | True | ; identity=—; generated=— |
| max_epochs | integer | True | ; identity=—; generated=— |
| fine_tune_epochs | integer | True | ; identity=—; generated=— |
| early_stopping | boolean | True | ; identity=—; generated=— |
| early_stopping_patience | integer | True | ; identity=—; generated=— |
| early_stopping_min_delta | double precision | True | ; identity=—; generated=— |
| early_stopping_monitor | text | True | ; identity=—; generated=— |
| early_stopping_mode | text | True | ; identity=—; generated=— |
| restore_best_weights | boolean | True | ; identity=—; generated=— |
| checkpoint_monitor | text | True | ; identity=—; generated=— |
| checkpoint_mode | text | True | ; identity=—; generated=— |
| dropout | double precision | True | ; identity=—; generated=— |
| l2 | double precision | True | ; identity=—; generated=— |
| input_height | integer | True | ; identity=—; generated=— |
| input_width | integer | True | ; identity=—; generated=— |
| input_channels | integer | True | ; identity=—; generated=— |
| weights | text | True | ; identity=—; generated=— |
| fine_tune_layers | integer | True | ; identity=—; generated=— |
| normalization | text | True | ; identity=—; generated=— |
| internal_preprocessing | text | False | ; identity=—; generated=— |
| loss_function | text | True | ; identity=—; generated=— |
| calibration_enabled | boolean | True | false; identity=—; generated=— |
| default_threshold | numeric | True | 0.5; identity=—; generated=— |
| clinical_target_recall | numeric | True | ; identity=—; generated=— |
| configuration_hash | text | True | ; identity=—; generated=— |
| canonical_configuration | text | True | ; identity=—; generated=— |
| optimizer_extensions | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| extension_configuration | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| provenance_snapshot | jsonb | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `v2_run_configurations_foreign_db5338c19de4`: `FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE RESTRICT`
- `v2_run_configurations_primary_360aa242ca7c`: `PRIMARY KEY (run_id)`

## public.run_dataset_images

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| run_dataset_image_id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| run_id | uuid | True | ; identity=—; generated=— |
| image_id | uuid | True | ; identity=—; generated=— |
| split_name | text | True | ; identity=—; generated=— |
| usage_context | text | True | ; identity=—; generated=— |
| class_index | integer | True | ; identity=—; generated=— |
| class_name | text | True | ; identity=—; generated=— |
| relative_path | text | True | ; identity=—; generated=— |
| filename | text | True | ; identity=—; generated=— |
| batch_index | integer | False | ; identity=—; generated=— |
| sample_index | integer | False | ; identity=—; generated=— |
| used_for_training | boolean | True | false; identity=—; generated=— |
| used_for_validation | boolean | True | false; identity=—; generated=— |
| used_for_test | boolean | True | false; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |

PK/FK/UNIQUE:

- `run_dataset_images_image_id_fkey`: `FOREIGN KEY (image_id) REFERENCES dataset_split_images(image_id) ON DELETE RESTRICT`
- `run_dataset_images_pkey`: `PRIMARY KEY (run_dataset_image_id)`
- `run_dataset_images_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE RESTRICT`
- `uq_run_dataset_images_usage`: `UNIQUE (run_id, image_id, usage_context)`

## public.run_image_predictions

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| run_image_prediction_id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| run_id | uuid | True | ; identity=—; generated=— |
| image_id | uuid | False | ; identity=—; generated=— |
| split_name | text | False | ; identity=—; generated=— |
| usage_context | text | False | ; identity=—; generated=— |
| filename | text | False | ; identity=—; generated=— |
| relative_path | text | False | ; identity=—; generated=— |
| true_label | integer | False | ; identity=—; generated=— |
| true_label_name | text | False | ; identity=—; generated=— |
| predicted_label | integer | False | ; identity=—; generated=— |
| predicted_label_name | text | False | ; identity=—; generated=— |
| probability_parasitized | numeric | False | ; identity=—; generated=— |
| probability_uninfected | numeric | False | ; identity=—; generated=— |
| raw_model_score | numeric | False | ; identity=—; generated=— |
| raw_model_score_meaning | text | True | 'probability_parasitized'::text; identity=—; generated=— |
| threshold_used | numeric | False | ; identity=—; generated=— |
| threshold_source | text | False | ; identity=—; generated=— |
| is_correct | boolean | False | ; identity=—; generated=— |
| case_type | text | False | ; identity=—; generated=— |
| metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `run_image_predictions_image_id_fkey`: `FOREIGN KEY (image_id) REFERENCES dataset_split_images(image_id) ON DELETE RESTRICT`
- `run_image_predictions_pkey`: `PRIMARY KEY (run_image_prediction_id)`
- `run_image_predictions_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE RESTRICT`

## public.run_io_records

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| run_io_id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| run_id | uuid | True | ; identity=—; generated=— |
| script_name | text | True | ; identity=—; generated=— |
| command | text | False | ; identity=—; generated=— |
| input_parameters | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| output_results | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| output_artifacts | jsonb | True | '[]'::jsonb; identity=—; generated=— |
| dataset_metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| label_mapping_version | text | True | 'clinical_v1_parasitized_positive'::text; identity=—; generated=— |
| raw_model_score_meaning | text | False | 'probability_parasitized'::text; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| run_type | text | False | ; identity=—; generated=— |
| model_name | text | False | ; identity=—; generated=— |
| model_metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| clinical_metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| dataset_version_id | uuid | False | ; identity=—; generated=— |
| dataset_materialization_id | uuid | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `run_io_records_dataset_materialization_id_fkey`: `FOREIGN KEY (dataset_materialization_id) REFERENCES dataset_materializations(id) ON DELETE RESTRICT`
- `run_io_records_dataset_version_id_fkey`: `FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions(id) ON DELETE RESTRICT`
- `run_io_records_pkey`: `PRIMARY KEY (run_io_id)`
- `run_io_records_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE RESTRICT`

## public.run_lineage

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| parent_run_id | uuid | True | ; identity=—; generated=— |
| child_run_id | uuid | True | ; identity=—; generated=— |
| relationship_type | text | True | ; identity=—; generated=— |
| checkpoint_path | text | False | ; identity=—; generated=— |
| checkpoint_artifact_id | uuid | False | ; identity=—; generated=— |
| model_version_id | uuid | False | ; identity=—; generated=— |
| confidence | text | True | 'explicit'::text; identity=—; generated=— |
| metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `fk_run_lineage_checkpoint_artifact_owner`: `FOREIGN KEY (checkpoint_artifact_id, parent_run_id) REFERENCES artifacts(id, run_id) ON DELETE RESTRICT`
- `fk_run_lineage_model_version_owner`: `FOREIGN KEY (model_version_id, parent_run_id) REFERENCES model_versions(id, training_run_id) ON DELETE RESTRICT`
- `fk_run_lineage_version_artifact`: `FOREIGN KEY (model_version_id, checkpoint_artifact_id) REFERENCES model_versions(id, checkpoint_artifact_id) ON DELETE RESTRICT`
- `run_lineage_child_run_id_fkey`: `FOREIGN KEY (child_run_id) REFERENCES runs(id) ON DELETE RESTRICT`
- `run_lineage_parent_run_id_fkey`: `FOREIGN KEY (parent_run_id) REFERENCES runs(id) ON DELETE RESTRICT`
- `run_lineage_pkey`: `PRIMARY KEY (id)`
- `uq_run_lineage_parent_child_type`: `UNIQUE (parent_run_id, child_run_id, relationship_type)`

## public.run_metrics

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| run_id | uuid | False | ; identity=—; generated=— |
| metric_name | text | True | ; identity=—; generated=— |
| metric_value | numeric | False | ; identity=—; generated=— |
| metric_unit | text | False | ; identity=—; generated=— |
| split_name | text | False | ; identity=—; generated=— |
| class_name | text | False | ; identity=—; generated=— |
| step | integer | False | ; identity=—; generated=— |
| epoch | integer | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | False | now(); identity=—; generated=— |
| metadata | jsonb | False | '{}'::jsonb; identity=—; generated=— |

PK/FK/UNIQUE:

- `run_metrics_pkey`: `PRIMARY KEY (id)`
- `run_metrics_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE RESTRICT`

## public.run_model_deployments

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| run_id | uuid | True | ; identity=—; generated=— |
| deployed_model_version_id | uuid | True | ; identity=—; generated=— |
| model_version_id | uuid | True | ; identity=—; generated=— |
| role | text | True | 'primary'::text; identity=—; generated=— |
| ordinal | integer | True | 0; identity=—; generated=— |
| weight | numeric | False | ; identity=—; generated=— |
| metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `fk_run_model_deployments_deployment_version`: `FOREIGN KEY (deployed_model_version_id, model_version_id) REFERENCES deployed_model_versions(id, model_version_id) ON DELETE RESTRICT`
- `fk_run_model_deployments_run`: `FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE RESTRICT`
- `run_model_deployments_pkey`: `PRIMARY KEY (id)`

## public.run_threshold_calibration

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| run_threshold_calibration_id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| run_id | uuid | True | ; identity=—; generated=— |
| model_name | text | False | ; identity=—; generated=— |
| threshold_policy | text | True | 'target_recall'::text; identity=—; generated=— |
| threshold_source | text | True | 'validation_calibration'::text; identity=—; generated=— |
| threshold_selected | numeric | True | ; identity=—; generated=— |
| default_threshold | numeric | True | 0.5; identity=—; generated=— |
| target_recall | numeric | True | ; identity=—; generated=— |
| target_recall_satisfied | boolean | False | ; identity=—; generated=— |
| min_specificity | numeric | False | ; identity=—; generated=— |
| validation_recall_at_threshold | numeric | False | ; identity=—; generated=— |
| validation_specificity_at_threshold | numeric | False | ; identity=—; generated=— |
| validation_precision_at_threshold | numeric | False | ; identity=—; generated=— |
| validation_f1_at_threshold | numeric | False | ; identity=—; generated=— |
| validation_f2_at_threshold | numeric | False | ; identity=—; generated=— |
| validation_balanced_accuracy_at_threshold | numeric | False | ; identity=—; generated=— |
| validation_pr_auc | numeric | False | ; identity=—; generated=— |
| validation_roc_auc | numeric | False | ; identity=—; generated=— |
| default_threshold_metrics | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| selected_threshold_metrics | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| candidate_count | integer | False | ; identity=—; generated=— |
| threshold_warning | text | False | ; identity=—; generated=— |
| calibration_split | text | True | 'val'::text; identity=—; generated=— |
| threshold_calibration_path | text | False | ; identity=—; generated=— |
| model_metadata_path | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| model_version_id | uuid | False | ; identity=—; generated=— |
| calibration_artifact_id | uuid | False | ; identity=—; generated=— |
| score_name | text | True | 'probability_parasitized'::text; identity=—; generated=— |
| label_mapping_version | text | True | 'clinical_v1_parasitized_positive'::text; identity=—; generated=— |
| positive_label | text | True | 'parasitized'::text; identity=—; generated=— |
| calibration_status | text | True | 'recorded'::text; identity=—; generated=— |
| default_evaluation_id | uuid | True | ; identity=—; generated=— |
| selected_evaluation_id | uuid | True | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `fk_run_threshold_calibration_artifact_owner`: `FOREIGN KEY (calibration_artifact_id, run_id) REFERENCES artifacts(id, run_id) ON DELETE RESTRICT`
- `fk_run_threshold_calibration_model_version`: `FOREIGN KEY (model_version_id) REFERENCES model_versions(id) ON DELETE RESTRICT`
- `run_threshold_calibration_pkey`: `PRIMARY KEY (run_threshold_calibration_id)`
- `run_threshold_calibration_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE RESTRICT`
- `v2_run_threshold_calibration_foreign_014acc59cdbd`: `FOREIGN KEY (default_evaluation_id) REFERENCES evaluations(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED`
- `v2_run_threshold_calibration_foreign_0ba3287c0955`: `FOREIGN KEY (selected_evaluation_id) REFERENCES evaluations(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED`

## public.runs

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| experiment_id | uuid | False | ; identity=—; generated=— |
| model_id | uuid | False | ; identity=—; generated=— |
| dataset_id | uuid | False | ; identity=—; generated=— |
| run_name | text | False | ; identity=—; generated=— |
| run_type | text | True | ; identity=—; generated=— |
| status | text | True | ; identity=—; generated=— |
| command | text | False | ; identity=—; generated=— |
| script_name | text | False | ; identity=—; generated=— |
| started_at | timestamp with time zone | False | ; identity=—; generated=— |
| finished_at | timestamp with time zone | False | ; identity=—; generated=— |
| duration_seconds | numeric | False | ; identity=—; generated=— |
| user_name | text | False | ; identity=—; generated=— |
| host_name | text | False | ; identity=—; generated=— |
| working_directory | text | False | ; identity=—; generated=— |
| git_commit | text | False | ; identity=—; generated=— |
| git_branch | text | False | ; identity=—; generated=— |
| python_version | text | False | ; identity=—; generated=— |
| tensorflow_version | text | False | ; identity=—; generated=— |
| keras_version | text | False | ; identity=—; generated=— |
| platform | text | False | ; identity=—; generated=— |
| machine | text | False | ; identity=—; generated=— |
| processor | text | False | ; identity=—; generated=— |
| gpu_available | boolean | False | ; identity=—; generated=— |
| gpu_devices | jsonb | False | '[]'::jsonb; identity=—; generated=— |
| random_seed | integer | False | ; identity=—; generated=— |
| parameters | jsonb | False | '{}'::jsonb; identity=—; generated=— |
| notes | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | False | now(); identity=—; generated=— |
| updated_at | timestamp with time zone | False | now(); identity=—; generated=— |
| metadata | jsonb | False | '{}'::jsonb; identity=—; generated=— |
| execution_type | text | False | ; identity=—; generated=— |
| execution_parameters | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| fine_tuning_start_epoch | integer | False | ; identity=—; generated=— |
| total_epochs | integer | False | ; identity=—; generated=— |
| completed_epochs | integer | True | 0; identity=—; generated=— |
| max_epochs | integer | False | ; identity=—; generated=— |
| stopped_epoch | integer | False | ; identity=—; generated=— |
| best_epoch | integer | False | ; identity=—; generated=— |
| checkpoint_monitor | text | False | ; identity=—; generated=— |
| checkpoint_mode | text | False | ; identity=—; generated=— |
| best_validation_value | double precision | False | ; identity=—; generated=— |
| early_stopping_enabled | boolean | False | ; identity=—; generated=— |
| early_stopping_patience | integer | False | ; identity=—; generated=— |
| early_stopping_min_delta | double precision | False | ; identity=—; generated=— |
| restore_best_weights | boolean | False | ; identity=—; generated=— |
| backend_version | text | False | ; identity=—; generated=— |
| pipeline_version | text | False | ; identity=—; generated=— |
| configuration | jsonb | False | ; identity=—; generated=— |
| error_message | text | False | ; identity=—; generated=— |
| dataset_version_id | uuid | False | ; identity=—; generated=— |
| release_status | text | False | ; identity=—; generated=— |
| release_updated_at | timestamp with time zone | False | ; identity=—; generated=— |
| release_changed_by | text | False | ; identity=—; generated=— |
| release_reason | text | False | ; identity=—; generated=— |
| campaign_id | uuid | False | ; identity=—; generated=— |
| peak_cpu_memory_bytes | bigint | False | ; identity=—; generated=— |
| peak_gpu_memory_bytes | bigint | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `runs_campaign_id_fkey`: `FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns(id)`
- `runs_dataset_id_fkey`: `FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE RESTRICT`
- `runs_dataset_version_id_fkey`: `FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions(id) ON DELETE RESTRICT`
- `runs_experiment_id_fkey`: `FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE RESTRICT`
- `runs_model_id_fkey`: `FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE RESTRICT`
- `runs_pkey`: `PRIMARY KEY (id)`

## public.scientific_cases

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| case_code | character varying(120) | True | ; identity=—; generated=— |
| subject_id | uuid | False | ; identity=—; generated=— |
| title | character varying(240) | False | ; identity=—; generated=— |
| description | text | False | ; identity=—; generated=— |
| source_type | character varying(30) | True | ; identity=—; generated=— |
| status | character varying(20) | True | 'draft'::character varying; identity=—; generated=— |
| priority | character varying(10) | True | 'normal'::character varying; identity=—; generated=— |
| metadata_json | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| updated_at | timestamp with time zone | True | now(); identity=—; generated=— |
| created_by | uuid | True | ; identity=—; generated=— |
| updated_by | uuid | False | ; identity=—; generated=— |
| archived_at | timestamp with time zone | False | ; identity=—; generated=— |
| archived_by | uuid | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `scientific_cases_archived_by_fkey`: `FOREIGN KEY (archived_by) REFERENCES users(id) ON DELETE RESTRICT`
- `scientific_cases_case_code_key`: `UNIQUE (case_code)`
- `scientific_cases_created_by_fkey`: `FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT`
- `scientific_cases_pkey`: `PRIMARY KEY (id)`
- `scientific_cases_subject_id_fkey`: `FOREIGN KEY (subject_id) REFERENCES research_subjects(id) ON DELETE RESTRICT`
- `scientific_cases_updated_by_fkey`: `FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE RESTRICT`

## public.scientific_reviews

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| entity_type | character varying(40) | True | ; identity=—; generated=— |
| entity_id | uuid | True | ; identity=—; generated=— |
| decision | character varying(30) | True | ; identity=—; generated=— |
| comment | text | False | ; identity=—; generated=— |
| actor_user_id | uuid | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `scientific_reviews_actor_user_id_fkey`: `FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT`
- `scientific_reviews_entity_id_fkey`: `FOREIGN KEY (entity_id) REFERENCES cell_detections(id) ON DELETE RESTRICT`
- `scientific_reviews_pkey`: `PRIMARY KEY (id)`

## public.scientific_validation_annotation_events

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| annotation_id | uuid | True | ; identity=—; generated=— |
| validation_session_id | uuid | False | ; identity=—; generated=— |
| event_type | character varying(20) | True | ; identity=—; generated=— |
| annotation_version | integer | True | ; identity=—; generated=— |
| actor_user_id | uuid | True | ; identity=—; generated=— |
| before_state | jsonb | False | ; identity=—; generated=— |
| after_state | jsonb | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `scientific_validation_annotat_annotation_id_annotation_vers_key`: `UNIQUE (annotation_id, annotation_version)`
- `scientific_validation_annotation_eve_validation_session_id_fkey`: `FOREIGN KEY (validation_session_id) REFERENCES scientific_validation_sessions(id) ON DELETE RESTRICT`
- `scientific_validation_annotation_events_actor_user_id_fkey`: `FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT`
- `scientific_validation_annotation_events_annotation_id_fkey`: `FOREIGN KEY (annotation_id) REFERENCES scientific_validation_annotations(id) ON DELETE RESTRICT`
- `scientific_validation_annotation_events_pkey`: `PRIMARY KEY (id)`

## public.scientific_validation_annotations

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| validation_session_id | uuid | False | ; identity=—; generated=— |
| target_type | character varying(20) | True | ; identity=—; generated=— |
| cell_detection_id | uuid | False | ; identity=—; generated=— |
| analysis_run_id | uuid | False | ; identity=—; generated=— |
| category | character varying(120) | True | ; identity=—; generated=— |
| content | text | True | ; identity=—; generated=— |
| version | integer | True | 1; identity=—; generated=— |
| created_by | uuid | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| updated_by | uuid | True | ; identity=—; generated=— |
| updated_at | timestamp with time zone | True | now(); identity=—; generated=— |
| sample_id | uuid | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `scientific_validation_annotations_analysis_run_id_fkey`: `FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT`
- `scientific_validation_annotations_cell_detection_id_fkey`: `FOREIGN KEY (cell_detection_id) REFERENCES cell_detections(id) ON DELETE RESTRICT`
- `scientific_validation_annotations_created_by_fkey`: `FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT`
- `scientific_validation_annotations_pkey`: `PRIMARY KEY (id)`
- `scientific_validation_annotations_sample_id_fkey`: `FOREIGN KEY (sample_id) REFERENCES blood_samples(id) ON DELETE RESTRICT`
- `scientific_validation_annotations_updated_by_fkey`: `FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE RESTRICT`
- `scientific_validation_annotations_validation_session_id_fkey`: `FOREIGN KEY (validation_session_id) REFERENCES scientific_validation_sessions(id) ON DELETE RESTRICT`

## public.scientific_validation_classification_runs

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| session_id | uuid | True | ; identity=—; generated=— |
| classification_run_id | uuid | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `scientific_validation_classification_classification_run_id_fkey`: `FOREIGN KEY (classification_run_id) REFERENCES cell_classification_runs(id) ON DELETE RESTRICT`
- `scientific_validation_classification_runs_pkey`: `PRIMARY KEY (session_id, classification_run_id)`
- `scientific_validation_classification_runs_session_id_fkey`: `FOREIGN KEY (session_id) REFERENCES scientific_validation_sessions(id) ON DELETE RESTRICT`

## public.scientific_validation_detection_runs

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| session_id | uuid | True | ; identity=—; generated=— |
| detection_run_id | uuid | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `scientific_validation_detection_runs_detection_run_id_fkey`: `FOREIGN KEY (detection_run_id) REFERENCES cell_detection_runs(id) ON DELETE RESTRICT`
- `scientific_validation_detection_runs_pkey`: `PRIMARY KEY (session_id, detection_run_id)`
- `scientific_validation_detection_runs_session_id_fkey`: `FOREIGN KEY (session_id) REFERENCES scientific_validation_sessions(id) ON DELETE RESTRICT`

## public.scientific_validation_images

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| session_id | uuid | True | ; identity=—; generated=— |
| microscopy_image_id | uuid | True | ; identity=—; generated=— |
| image_sha256 | character(64) | True | ; identity=—; generated=— |
| sequence_number | integer | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `scientific_validation_images_microscopy_image_id_fkey`: `FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images(id) ON DELETE RESTRICT`
- `scientific_validation_images_pkey`: `PRIMARY KEY (session_id, microscopy_image_id)`
- `scientific_validation_images_session_id_fkey`: `FOREIGN KEY (session_id) REFERENCES scientific_validation_sessions(id) ON DELETE RESTRICT`
- `scientific_validation_images_session_id_sequence_number_key`: `UNIQUE (session_id, sequence_number)`

## public.scientific_validation_sessions

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| name | character varying(200) | True | ; identity=—; generated=— |
| description | text | False | ; identity=—; generated=— |
| datasource | character varying(80) | True | ; identity=—; generated=— |
| protocol_key | character varying(120) | True | ; identity=—; generated=— |
| protocol_version | character varying(80) | True | ; identity=—; generated=— |
| matching_iou_threshold | double precision | True | ; identity=—; generated=— |
| status | character varying(30) | True | 'draft'::character varying; identity=—; generated=— |
| initial_snapshot | jsonb | True | ; identity=—; generated=— |
| snapshot_sha256 | character(64) | True | ; identity=—; generated=— |
| created_by | uuid | True | ; identity=—; generated=— |
| updated_by | uuid | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| updated_at | timestamp with time zone | True | now(); identity=—; generated=— |
| archived_at | timestamp with time zone | False | ; identity=—; generated=— |
| archived_by | uuid | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `scientific_validation_sessions_archived_by_fkey`: `FOREIGN KEY (archived_by) REFERENCES users(id) ON DELETE RESTRICT`
- `scientific_validation_sessions_created_by_fkey`: `FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT`
- `scientific_validation_sessions_pkey`: `PRIMARY KEY (id)`
- `scientific_validation_sessions_updated_by_fkey`: `FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE RESTRICT`

## public.smear_analysis_summaries

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| classification_run_id | uuid | True | ; identity=—; generated=— |
| analysis_run_id | uuid | True | ; identity=—; generated=— |
| detection_run_id | uuid | True | ; identity=—; generated=— |
| outcome | character varying(40) | True | ; identity=—; generated=— |
| eligible_cell_count | integer | True | ; identity=—; generated=— |
| classified_cell_count | integer | True | ; identity=—; generated=— |
| parasitized_candidate_count | integer | True | ; identity=—; generated=— |
| uninfected_candidate_count | integer | True | ; identity=—; generated=— |
| near_threshold_count | integer | True | ; identity=—; generated=— |
| failed_prediction_count | integer | True | ; identity=—; generated=— |
| parasitized_candidate_fraction | double precision | False | ; identity=—; generated=— |
| maximum_probability_parasitized | double precision | False | ; identity=—; generated=— |
| mean_probability_parasitized | double precision | False | ; identity=—; generated=— |
| median_probability_parasitized | double precision | False | ; identity=—; generated=— |
| per_image_summary | jsonb | True | ; identity=—; generated=— |
| aggregation_policy_snapshot | jsonb | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `fk_smear_summary_classification_lineage`: `FOREIGN KEY (classification_run_id, analysis_run_id, detection_run_id) REFERENCES cell_classification_runs(id, analysis_run_id, detection_run_id) ON DELETE RESTRICT`
- `smear_analysis_summaries_classification_run_id_key`: `UNIQUE (classification_run_id)`
- `smear_analysis_summaries_pkey`: `PRIMARY KEY (id)`

## public.smear_slides

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| sample_id | uuid | True | ; identity=—; generated=— |
| slide_code | character varying(120) | True | ; identity=—; generated=— |
| smear_type | character varying(20) | True | ; identity=—; generated=— |
| stain_type | character varying(120) | False | ; identity=—; generated=— |
| preparation_method | character varying(160) | False | ; identity=—; generated=— |
| prepared_at | timestamp with time zone | False | ; identity=—; generated=— |
| status | character varying(30) | True | 'registered'::character varying; identity=—; generated=— |
| notes | text | False | ; identity=—; generated=— |
| metadata_json | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| updated_at | timestamp with time zone | True | now(); identity=—; generated=— |
| created_by | uuid | True | ; identity=—; generated=— |
| updated_by | uuid | False | ; identity=—; generated=— |
| archived_at | timestamp with time zone | False | ; identity=—; generated=— |
| archived_by | uuid | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `smear_slides_archived_by_fkey`: `FOREIGN KEY (archived_by) REFERENCES users(id) ON DELETE RESTRICT`
- `smear_slides_created_by_fkey`: `FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT`
- `smear_slides_pkey`: `PRIMARY KEY (id)`
- `smear_slides_sample_id_fkey`: `FOREIGN KEY (sample_id) REFERENCES blood_samples(id) ON DELETE RESTRICT`
- `smear_slides_updated_by_fkey`: `FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE RESTRICT`
- `uq_smear_slides_sample_code`: `UNIQUE (sample_id, slide_code)`

## public.stage2_model_publication_events

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| publication_id | uuid | True | ; identity=—; generated=— |
| event_type | text | True | ; identity=—; generated=— |
| actor | text | False | ; identity=—; generated=— |
| event_at | timestamp with time zone | True | now(); identity=—; generated=— |
| model_version_id | uuid | True | ; identity=—; generated=— |
| training_run_id | uuid | True | ; identity=—; generated=— |
| evaluation_run_id | uuid | False | ; identity=—; generated=— |
| datasource | text | True | ; identity=—; generated=— |
| previous_status | text | False | ; identity=—; generated=— |
| new_status | text | True | ; identity=—; generated=— |
| reason | text | False | ; identity=—; generated=— |
| correlation_id | text | False | ; identity=—; generated=— |
| metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| evaluation_attempt_id | uuid | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `stage2_model_publication_events_evaluation_attempt_id_fkey`: `FOREIGN KEY (evaluation_attempt_id) REFERENCES assessment_attempts(id) ON DELETE RESTRICT`
- `stage2_model_publication_events_pkey`: `PRIMARY KEY (id)`
- `stage2_model_publication_events_publication_id_fkey`: `FOREIGN KEY (publication_id) REFERENCES stage2_model_publications(id) ON DELETE RESTRICT`

## public.stage2_model_publications

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| datasource | text | True | ; identity=—; generated=— |
| model_version_id | uuid | True | ; identity=—; generated=— |
| training_run_id | uuid | True | ; identity=—; generated=— |
| evaluation_run_id | uuid | False | ; identity=—; generated=— |
| checkpoint_artifact_id | uuid | True | ; identity=—; generated=— |
| scope | text | True | 'stage2'::text; identity=—; generated=— |
| status | text | True | 'active'::text; identity=—; generated=— |
| is_active | boolean | True | true; identity=—; generated=— |
| published_at | timestamp with time zone | True | now(); identity=—; generated=— |
| published_by | text | False | ; identity=—; generated=— |
| deactivated_at | timestamp with time zone | False | ; identity=—; generated=— |
| deactivated_by | text | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| updated_at | timestamp with time zone | True | now(); identity=—; generated=— |
| metadata | jsonb | True | '{}'::jsonb; identity=—; generated=— |
| evaluation_attempt_id | uuid | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `fk_stage2_publication_evaluation`: `FOREIGN KEY (evaluation_run_id) REFERENCES runs(id) ON DELETE RESTRICT`
- `fk_stage2_publication_model_training`: `FOREIGN KEY (model_version_id, training_run_id) REFERENCES model_versions(id, training_run_id) ON DELETE RESTRICT`
- `fk_stage2_publication_training`: `FOREIGN KEY (training_run_id) REFERENCES runs(id) ON DELETE RESTRICT`
- `fk_stage2_publication_version_artifact`: `FOREIGN KEY (model_version_id, checkpoint_artifact_id) REFERENCES model_versions(id, checkpoint_artifact_id) ON DELETE RESTRICT`
- `stage2_model_publications_evaluation_attempt_id_fkey`: `FOREIGN KEY (evaluation_attempt_id) REFERENCES assessment_attempts(id) ON DELETE RESTRICT`
- `stage2_model_publications_pkey`: `PRIMARY KEY (id)`

## public.synthetic_data_runs

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| run_id | uuid | False | ; identity=—; generated=— |
| method | text | False | ; identity=—; generated=— |
| num_images_generated | integer | False | ; identity=—; generated=— |
| source_dataset_id | uuid | False | ; identity=—; generated=— |
| output_path | text | False | ; identity=—; generated=— |
| generation_parameters | jsonb | False | '{}'::jsonb; identity=—; generated=— |
| quality_checks | jsonb | False | '{}'::jsonb; identity=—; generated=— |
| created_at | timestamp with time zone | False | now(); identity=—; generated=— |
| metadata | jsonb | False | '{}'::jsonb; identity=—; generated=— |

PK/FK/UNIQUE:

- `synthetic_data_runs_pkey`: `PRIMARY KEY (id)`
- `synthetic_data_runs_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE RESTRICT`
- `synthetic_data_runs_source_dataset_id_fkey`: `FOREIGN KEY (source_dataset_id) REFERENCES datasets(id) ON DELETE RESTRICT`

## public.train_execution_records

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| run_id | uuid | True | ; identity=—; generated=— |
| kind | text | True | ; identity=—; generated=— |
| phase | text | True | ; identity=—; generated=— |
| record_key | text | True | ; identity=—; generated=— |
| payload | jsonb | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | clock_timestamp(); identity=—; generated=— |
| event_id | uuid | False | ; identity=—; generated=— |
| event_sequence | numeric | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `train_execution_records_pkey`: `PRIMARY KEY (run_id, kind, phase, record_key)`
- `train_execution_records_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES train_execution_sessions(run_id)`

## public.train_execution_revisions

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| attempt_id | uuid | True | ; identity=—; generated=— |
| campaign_id | uuid | True | ; identity=—; generated=— |
| revision_id | uuid | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | clock_timestamp(); identity=—; generated=— |

PK/FK/UNIQUE:

- `train_execution_revisions_attempt_id_fkey`: `FOREIGN KEY (attempt_id) REFERENCES campaign_attempts(id) DEFERRABLE INITIALLY DEFERRED`
- `train_execution_revisions_campaign_id_fkey`: `FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns(id)`
- `train_execution_revisions_campaign_id_revision_id_fkey`: `FOREIGN KEY (campaign_id, revision_id) REFERENCES campaign_technical_revisions(campaign_id, id)`
- `train_execution_revisions_pkey`: `PRIMARY KEY (attempt_id)`

## public.train_execution_sessions

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| run_id | uuid | True | ; identity=—; generated=— |
| attempt_id | uuid | False | ; identity=—; generated=— |
| owner | uuid | True | ; identity=—; generated=— |
| host | text | True | ; identity=—; generated=— |
| parent_pid | integer | True | ; identity=—; generated=— |
| child_pid | integer | False | ; identity=—; generated=— |
| state | text | True | 'active'::text; identity=—; generated=— |
| configuration | jsonb | True | ; identity=—; generated=— |
| dataset | jsonb | True | ; identity=—; generated=— |
| environment | jsonb | True | ; identity=—; generated=— |
| artifact_root | text | True | ; identity=—; generated=— |
| cause | text | False | ; identity=—; generated=— |
| started_at | timestamp with time zone | True | clock_timestamp(); identity=—; generated=— |
| updated_at | timestamp with time zone | True | clock_timestamp(); identity=—; generated=— |
| completion | jsonb | False | ; identity=—; generated=— |
| verification | jsonb | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `train_execution_sessions_artifact_root_key`: `UNIQUE (artifact_root)`
- `train_execution_sessions_attempt_id_fkey`: `FOREIGN KEY (attempt_id) REFERENCES campaign_attempts(id)`
- `train_execution_sessions_attempt_id_key`: `UNIQUE (attempt_id)`
- `train_execution_sessions_pkey`: `PRIMARY KEY (run_id)`
- `train_execution_sessions_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES runs(id)`

## public.training_history

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | gen_random_uuid(); identity=—; generated=— |
| run_id | uuid | True | ; identity=—; generated=— |
| epoch | integer | True | ; identity=—; generated=— |
| loss | numeric | False | ; identity=—; generated=— |
| accuracy | numeric | False | ; identity=—; generated=— |
| precision_value | numeric | False | ; identity=—; generated=— |
| recall_value | numeric | False | ; identity=—; generated=— |
| auc | numeric | False | ; identity=—; generated=— |
| val_loss | numeric | False | ; identity=—; generated=— |
| val_accuracy | numeric | False | ; identity=—; generated=— |
| val_precision | numeric | False | ; identity=—; generated=— |
| val_recall | numeric | False | ; identity=—; generated=— |
| val_auc | numeric | False | ; identity=—; generated=— |
| learning_rate | numeric | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | False | now(); identity=—; generated=— |
| metadata | jsonb | False | '{}'::jsonb; identity=—; generated=— |
| phase | text | True | 'training'::text; identity=—; generated=— |
| train_loss | numeric | False | ; identity=—; generated=— |
| train_accuracy | numeric | False | ; identity=—; generated=— |
| train_specificity | numeric | False | ; identity=—; generated=— |
| val_specificity | numeric | False | ; identity=—; generated=— |
| train_f2 | numeric | False | ; identity=—; generated=— |
| val_f2 | numeric | False | ; identity=—; generated=— |
| train_balanced_accuracy | numeric | False | ; identity=—; generated=— |
| val_balanced_accuracy | numeric | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `training_history_pkey`: `PRIMARY KEY (id)`
- `training_history_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE RESTRICT`
- `uq_v2_epoch`: `UNIQUE (run_id, phase, epoch)`

## public.user_roles

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| user_id | uuid | True | ; identity=—; generated=— |
| role_id | uuid | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `user_roles_pkey`: `PRIMARY KEY (user_id, role_id)`
- `user_roles_role_id_fkey`: `FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE RESTRICT`
- `user_roles_user_id_fkey`: `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE`

## public.users

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | ; identity=—; generated=— |
| username | text | True | ; identity=—; generated=— |
| email | text | False | ; identity=—; generated=— |
| password_hash | text | True | ; identity=—; generated=— |
| status | text | True | 'active'::text; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| updated_at | timestamp with time zone | True | now(); identity=—; generated=— |
| last_login_at | timestamp with time zone | False | ; identity=—; generated=— |
| disabled_at | timestamp with time zone | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `users_email_key`: `UNIQUE (email)`
- `users_pkey`: `PRIMARY KEY (id)`
- `users_username_key`: `UNIQUE (username)`

## public.xai_artifacts

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | public.gen_random_uuid(); identity=—; generated=— |
| evidence_id | uuid | True | ; identity=—; generated=— |
| artifact_id | uuid | False | ; identity=—; generated=— |
| assessment_artifact_id | uuid | False | ; identity=—; generated=— |
| role | text | True | ; identity=—; generated=— |
| ordinal | integer | True | 0; identity=—; generated=— |
| storage_uri | text | True | ; identity=—; generated=— |
| sha256 | text | True | ; identity=—; generated=— |
| byte_size | bigint | True | ; identity=—; generated=— |
| mime_type | text | True | ; identity=—; generated=— |
| numeric_dtype | text | False | ; identity=—; generated=— |
| tensor_shape | integer[] | False | ; identity=—; generated=— |
| axis_order | text | False | ; identity=—; generated=— |
| coordinate_space | text | False | ; identity=—; generated=— |
| availability | text | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `v2_xai_artifacts_foreign_4b080b42e888`: `FOREIGN KEY (evidence_id) REFERENCES xai_evidence(id) ON DELETE RESTRICT`
- `v2_xai_artifacts_foreign_e3d2eb574718`: `FOREIGN KEY (artifact_id) REFERENCES artifacts(id) ON DELETE RESTRICT`
- `v2_xai_artifacts_foreign_f9c5548be835`: `FOREIGN KEY (assessment_artifact_id) REFERENCES assessment_artifacts(artifact_id) ON DELETE RESTRICT`
- `v2_xai_artifacts_primary_8c8464f42472`: `PRIMARY KEY (id)`
- `v2_xai_artifacts_unique_ee15a9513a9e`: `UNIQUE (evidence_id, role, ordinal)`

## public.xai_evaluation_members

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| evaluation_id | uuid | True | ; identity=—; generated=— |
| xai_evidence_id | uuid | True | ; identity=—; generated=— |
| member_role | text | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `fk_xai_member_evaluation`: `FOREIGN KEY (evaluation_id) REFERENCES xai_quantitative_evaluations(id) ON DELETE RESTRICT`
- `fk_xai_member_evidence`: `FOREIGN KEY (xai_evidence_id) REFERENCES xai_evidence(id) ON DELETE RESTRICT`
- `xai_evaluation_members_pkey`: `PRIMARY KEY (evaluation_id, xai_evidence_id)`

## public.xai_evaluation_protocols

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | public.gen_random_uuid(); identity=—; generated=— |
| metric_name | text | True | ; identity=—; generated=— |
| metric_family | text | True | ; identity=—; generated=— |
| protocol_name | text | True | ; identity=—; generated=— |
| protocol_version | text | True | ; identity=—; generated=— |
| parameters | jsonb | True | ; identity=—; generated=— |
| normalization_strategy | text | True | ; identity=—; generated=— |
| perturbation_strategy | text | False | ; identity=—; generated=— |
| reference_definition | jsonb | False | ; identity=—; generated=— |
| canonical_protocol | text | True | ; identity=—; generated=— |
| protocol_hash | text | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `uq_xai_protocol_hash`: `UNIQUE (protocol_hash)`
- `uq_xai_protocol_metric`: `UNIQUE (id, metric_name)`
- `xai_evaluation_protocols_pkey`: `PRIMARY KEY (id)`

## public.xai_evidence

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | public.gen_random_uuid(); identity=—; generated=— |
| ml_explanation_id | uuid | False | ; identity=—; generated=— |
| cell_explanation_id | uuid | False | ; identity=—; generated=— |
| assessment_attempt_id | uuid | False | ; identity=—; generated=— |
| assessment_sample_id | uuid | False | ; identity=—; generated=— |
| prediction_id | uuid | False | ; identity=—; generated=— |
| cell_prediction_id | uuid | False | ; identity=—; generated=— |
| evaluation_id | uuid | False | ; identity=—; generated=— |
| dataset_source_record_id | uuid | False | ; identity=—; generated=— |
| input_artifact_id | uuid | False | ; identity=—; generated=— |
| microscopy_image_id | uuid | False | ; identity=—; generated=— |
| run_id | uuid | False | ; identity=—; generated=— |
| model_version_id | uuid | False | ; identity=—; generated=— |
| checkpoint_artifact_id | uuid | True | ; identity=—; generated=— |
| method_configuration_id | uuid | True | ; identity=—; generated=— |
| target_layer | text | False | ; identity=—; generated=— |
| prediction_score | numeric | False | ; identity=—; generated=— |
| source_commit | text | True | ; identity=—; generated=— |
| input_contract | jsonb | True | ; identity=—; generated=— |
| input_contract_hash | text | True | ; identity=—; generated=— |
| input_storage_uri | text | True | ; identity=—; generated=— |
| input_sha256 | text | True | ; identity=—; generated=— |
| checkpoint_sha256 | text | True | ; identity=—; generated=— |
| target_class | smallint | True | ; identity=—; generated=— |
| explained_output | text | True | ; identity=—; generated=— |
| processing_stage | text | True | ; identity=—; generated=— |
| seed | bigint | False | ; identity=—; generated=— |
| background_manifest_uri | text | False | ; identity=—; generated=— |
| background_manifest_sha256 | text | False | ; identity=—; generated=— |
| environment_snapshot | jsonb | True | ; identity=—; generated=— |
| generated_at | timestamp with time zone | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `fk_xai_method_configuration`: `FOREIGN KEY (method_configuration_id) REFERENCES xai_method_configurations(id) ON DELETE RESTRICT`
- `v2_xai_evidence_foreign_029e07f1d6db`: `FOREIGN KEY (cell_prediction_id) REFERENCES cell_predictions(id) ON DELETE RESTRICT`
- `v2_xai_evidence_foreign_3fe88bd35854`: `FOREIGN KEY (cell_explanation_id) REFERENCES cell_explanations(id) ON DELETE RESTRICT`
- `v2_xai_evidence_foreign_4b04405ab069`: `FOREIGN KEY (prediction_id) REFERENCES predictions(id) ON DELETE RESTRICT`
- `v2_xai_evidence_foreign_52bd313b1c15`: `FOREIGN KEY (assessment_attempt_id, assessment_sample_id) REFERENCES assessment_results(attempt_id, sample_id) MATCH FULL ON DELETE RESTRICT`
- `v2_xai_evidence_foreign_6aec504c7a2f`: `FOREIGN KEY (checkpoint_artifact_id) REFERENCES artifacts(id) ON DELETE RESTRICT`
- `v2_xai_evidence_foreign_9851edbb8079`: `FOREIGN KEY (ml_explanation_id) REFERENCES explainability_results(id) ON DELETE RESTRICT`
- `v2_xai_evidence_foreign_a1c9b824423e`: `FOREIGN KEY (input_artifact_id) REFERENCES artifacts(id) ON DELETE RESTRICT`
- `v2_xai_evidence_foreign_a402d28a70f6`: `FOREIGN KEY (evaluation_id) REFERENCES evaluations(id) ON DELETE RESTRICT`
- `v2_xai_evidence_foreign_ad1ea3f78d92`: `FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images(id) ON DELETE RESTRICT`
- `v2_xai_evidence_foreign_b946b2b207f3`: `FOREIGN KEY (model_version_id) REFERENCES model_versions(id) ON DELETE RESTRICT`
- `v2_xai_evidence_foreign_db5338c19de4`: `FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE RESTRICT`
- `v2_xai_evidence_foreign_e8d9af78807c`: `FOREIGN KEY (dataset_source_record_id) REFERENCES dataset_source_records(id) ON DELETE RESTRICT`
- `v2_xai_evidence_primary_8c8464f42472`: `PRIMARY KEY (id)`
- `v2_xai_evidence_unique_0be310eeb2b7`: `UNIQUE (assessment_attempt_id, assessment_sample_id)`
- `v2_xai_evidence_unique_d4bf0f195fcf`: `UNIQUE (cell_explanation_id)`
- `v2_xai_evidence_unique_d9477cb1fece`: `UNIQUE (ml_explanation_id)`

## public.xai_interpretations

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | public.gen_random_uuid(); identity=—; generated=— |
| evidence_id | uuid | True | ; identity=—; generated=— |
| author_user_id | uuid | True | ; identity=—; generated=— |
| interpretation | text | True | ; identity=—; generated=— |
| limitations | text | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |
| supersedes_id | uuid | False | ; identity=—; generated=— |

PK/FK/UNIQUE:

- `v2_xai_interpretations_foreign_4b080b42e888`: `FOREIGN KEY (evidence_id) REFERENCES xai_evidence(id) ON DELETE RESTRICT`
- `v2_xai_interpretations_foreign_6b09f9926d4f`: `FOREIGN KEY (author_user_id) REFERENCES users(id) ON DELETE RESTRICT`
- `v2_xai_interpretations_foreign_af451d74af77`: `FOREIGN KEY (supersedes_id) REFERENCES xai_interpretations(id) ON DELETE RESTRICT`
- `v2_xai_interpretations_primary_8c8464f42472`: `PRIMARY KEY (id)`

## public.xai_method_configurations

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | public.gen_random_uuid(); identity=—; generated=— |
| method | text | True | ; identity=—; generated=— |
| implementation | text | True | ; identity=—; generated=— |
| implementation_version | text | True | ; identity=—; generated=— |
| parameters | jsonb | True | ; identity=—; generated=— |
| canonical_configuration | text | True | ; identity=—; generated=— |
| configuration_hash | text | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `uq_xai_method_configuration_hash`: `UNIQUE (configuration_hash)`
- `xai_method_configurations_pkey`: `PRIMARY KEY (id)`

## public.xai_quantitative_evaluations

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | public.gen_random_uuid(); identity=—; generated=— |
| protocol_id | uuid | True | ; identity=—; generated=— |
| metric_name | text | True | ; identity=—; generated=— |
| membership_hash | text | True | ; identity=—; generated=— |
| metric_value | double precision | False | ; identity=—; generated=— |
| undefined_reason | text | False | ; identity=—; generated=— |
| seed | bigint | False | ; identity=—; generated=— |
| sample_count | bigint | True | ; identity=—; generated=— |
| reference_annotation_id | uuid | False | ; identity=—; generated=— |
| reference_annotation_version | integer | False | ; identity=—; generated=— |
| reference_manifest_uri | text | False | ; identity=—; generated=— |
| reference_manifest_sha256 | text | False | ; identity=—; generated=— |
| details_uri | text | False | ; identity=—; generated=— |
| details_sha256 | text | False | ; identity=—; generated=— |
| evaluated_at | timestamp with time zone | True | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `fk_xai_metric_protocol`: `FOREIGN KEY (protocol_id, metric_name) REFERENCES xai_evaluation_protocols(id, metric_name) ON DELETE RESTRICT`
- `fk_xai_reference_annotation`: `FOREIGN KEY (reference_annotation_id) REFERENCES scientific_validation_annotations(id) ON DELETE RESTRICT`
- `v2_xai_quantitative_evaluations_primary_8c8464f42472`: `PRIMARY KEY (id)`

## public.xai_region_attributions

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| xai_evidence_id | uuid | True | ; identity=—; generated=— |
| region_type | text | True | ; identity=—; generated=— |
| region_index | integer | True | ; identity=—; generated=— |
| attribution_value | double precision | True | ; identity=—; generated=— |
| rank | integer | False | ; identity=—; generated=— |
| region_definition | jsonb | False | ; identity=—; generated=— |
| created_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `fk_xai_region_evidence`: `FOREIGN KEY (xai_evidence_id) REFERENCES xai_evidence(id) ON DELETE RESTRICT`
- `xai_region_attributions_pkey`: `PRIMARY KEY (xai_evidence_id, region_type, region_index)`

## public.xai_specialist_reviews

Propietario: `capstone_v2_migrator`. RLS: `False`.

| Columna | Tipo | NOT NULL | Default / identity / generated |
|---|---|---|---|
| id | uuid | True | public.gen_random_uuid(); identity=—; generated=— |
| interpretation_id | uuid | True | ; identity=—; generated=— |
| reviewer_user_id | uuid | True | ; identity=—; generated=— |
| decision | text | True | ; identity=—; generated=— |
| rationale | text | True | ; identity=—; generated=— |
| competence_snapshot | jsonb | True | ; identity=—; generated=— |
| reviewed_at | timestamp with time zone | True | now(); identity=—; generated=— |

PK/FK/UNIQUE:

- `v2_xai_specialist_reviews_foreign_4735bf604cb2`: `FOREIGN KEY (interpretation_id) REFERENCES xai_interpretations(id) ON DELETE RESTRICT`
- `v2_xai_specialist_reviews_foreign_7ca01df9e490`: `FOREIGN KEY (reviewer_user_id) REFERENCES users(id) ON DELETE RESTRICT`
- `v2_xai_specialist_reviews_primary_8c8464f42472`: `PRIMARY KEY (id)`

