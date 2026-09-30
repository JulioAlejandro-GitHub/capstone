# DBV2.1 — Fichas estructurales completas

Generadas del SQL propuesto. Complementan la definición estructural; no son una migración.

## artifacts

Registro de archivos de run/checkpoint, URI, hash y disponibilidad; no almacén de bytes.

Dominio: E. Model versions / checkpoints. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| run_id | uuid | YES |  |
| artifact_type | text | NO |  |
| name | text | YES |  |
| path | text | NO |  |
| mime_type | text | YES |  |
| file_size_bytes | bigint | YES |  |
| checksum | text | YES |  |
| created_at | timestamp with time zone | YES | now() |
| metadata | jsonb | YES | CAST('{}' AS jsonb) |
| artifact_uri | text | YES |  |
| artifact_status | text | NO | CAST('available' AS text) |
| archived_at | timestamp with time zone | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.artifacts ADD CONSTRAINT artifacts_pkey CONSTRAINT artifacts_pkey PRIMARY KEY (id);
ALTER TABLE public.artifacts ADD CONSTRAINT chk_artifacts_governance_status CONSTRAINT chk_artifacts_governance_status CHECK (artifact_status = ANY(ARRAY[CAST('unknown' AS text), CAST('available' AS text), CAST('missing' AS text), CAST('mutated' AS text), CAST('archived' AS text)]));
ALTER TABLE public.artifacts ADD CONSTRAINT artifacts_run_id_fkey CONSTRAINT artifacts_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;
```

Índices explícitos: `uq_artifacts_id_run_id`, `idx_artifacts_artifact_type`, `idx_artifacts_checksum`, `idx_artifacts_governance_status`, `idx_artifacts_metadata_source`, `idx_artifacts_run_id`, `idx_artifacts_type_path`, `idx_artifacts_uri`.
Auditoría: created_at, archived_at.
JSONB: metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## assessment_artifacts

Evidencia de archivos por intento/muestra/rol, con payload inmutable y artifact_id único.

Dominio: K. Evaluaciones. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| attempt_id | uuid | NO |  |
| artifact_id | uuid | NO |  |
| sample_id | uuid | NO |  |
| role | text | NO |  |
| payload | jsonb | NO |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.assessment_artifacts ADD CONSTRAINT assessment_artifacts_pkey CONSTRAINT assessment_artifacts_pkey PRIMARY KEY (attempt_id, sample_id, role);
ALTER TABLE public.assessment_artifacts ADD CONSTRAINT assessment_artifacts_artifact_id_key CONSTRAINT assessment_artifacts_artifact_id_key UNIQUE (artifact_id);
ALTER TABLE public.assessment_artifacts ADD CONSTRAINT assessment_artifacts_payload_check CONSTRAINT assessment_artifacts_payload_check CHECK (jsonb_typeof(payload) = CAST('object' AS text));
ALTER TABLE public.assessment_artifacts ADD CONSTRAINT assessment_artifacts_payload_check1 CONSTRAINT assessment_artifacts_payload_check1 CHECK (payload ->> CAST('sha256' AS text) IS NOT NULL AND (payload ->> CAST('sha256' AS text)) ~ CAST('^[a-f0-9]{64}$' AS text));
ALTER TABLE public.assessment_artifacts ADD CONSTRAINT assessment_artifacts_payload_check2 CONSTRAINT assessment_artifacts_payload_check2 CHECK (NOT jsonb_typeof(payload -> CAST('bytes' AS text)) IS DISTINCT FROM CAST('number' AS text) AND CAST(payload ->> CAST('bytes' AS text) AS bigint) > 0);
ALTER TABLE public.assessment_artifacts ADD CONSTRAINT assessment_artifacts_payload_check3 CONSTRAINT assessment_artifacts_payload_check3 CHECK (NOT(payload ->> CAST('state' AS text)) IS DISTINCT FROM CAST('finalized' AS text));
ALTER TABLE public.assessment_artifacts ADD CONSTRAINT assessment_artifacts_attempt_id_fkey CONSTRAINT assessment_artifacts_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES assessment_attempts (id);
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: heredada de su padre y registrada en la relación.
JSONB: payload. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## assessment_attempts

Intento autorizado evaluate/explain; owner, ordinal, estado y verificación final.

Dominio: K. Evaluaciones. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| identity_id | uuid | NO |  |
| owner | uuid | NO |  |
| host | text | NO |  |
| pid | integer | NO |  |
| ordinal | integer | NO |  |
| state | text | NO | CAST('active' AS text) |
| artifact_root | text | NO |  |
| cause | text | YES |  |
| verification | jsonb | YES |  |
| started_at | timestamp with time zone | NO | clock_timestamp() |
| finished_at | timestamp with time zone | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.assessment_attempts ADD CONSTRAINT assessment_attempts_pkey CONSTRAINT assessment_attempts_pkey PRIMARY KEY (id);
ALTER TABLE public.assessment_attempts ADD CONSTRAINT assessment_attempts_artifact_root_key CONSTRAINT assessment_attempts_artifact_root_key UNIQUE (artifact_root);
ALTER TABLE public.assessment_attempts ADD CONSTRAINT assessment_attempts_identity_id_ordinal_key CONSTRAINT assessment_attempts_identity_id_ordinal_key UNIQUE (identity_id, ordinal);
ALTER TABLE public.assessment_attempts ADD CONSTRAINT assessment_attempts_check CONSTRAINT assessment_attempts_check CHECK (state <> CAST('verified' AS text) OR verification IS NOT NULL);
ALTER TABLE public.assessment_attempts ADD CONSTRAINT assessment_attempts_ordinal_check CONSTRAINT assessment_attempts_ordinal_check CHECK (ordinal > 0);
ALTER TABLE public.assessment_attempts ADD CONSTRAINT assessment_attempts_pid_check CONSTRAINT assessment_attempts_pid_check CHECK (pid > 0);
ALTER TABLE public.assessment_attempts ADD CONSTRAINT assessment_attempts_state_check CONSTRAINT assessment_attempts_state_check CHECK (state = ANY(ARRAY[CAST('active' AS text), CAST('verified' AS text), CAST('failed' AS text), CAST('interrupted' AS text)]));
ALTER TABLE public.assessment_attempts ADD CONSTRAINT assessment_attempts_identity_id_fkey CONSTRAINT assessment_attempts_identity_id_fkey FOREIGN KEY (identity_id) REFERENCES assessment_identities (id);
```

Índices explícitos: `uq_assessment_live`, `uq_global_assessment_active`.
Auditoría: started_at, finished_at.
JSONB: verification. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## assessment_campaign_consumers

Consumo gobernado de identidad assessment por campaña/miembro, sin duplicar ejecución.

Dominio: K. Evaluaciones. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| campaign_id | uuid | NO |  |
| member_id | uuid | NO |  |
| identity_id | uuid | NO |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.assessment_campaign_consumers ADD CONSTRAINT assessment_campaign_consumers_pkey CONSTRAINT assessment_campaign_consumers_pkey PRIMARY KEY (campaign_id, member_id, identity_id);
ALTER TABLE public.assessment_campaign_consumers ADD CONSTRAINT assessment_campaign_consumers_campaign_id_fkey CONSTRAINT assessment_campaign_consumers_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns (id);
ALTER TABLE public.assessment_campaign_consumers ADD CONSTRAINT assessment_campaign_consumers_identity_id_fkey CONSTRAINT assessment_campaign_consumers_identity_id_fkey FOREIGN KEY (identity_id) REFERENCES assessment_identities (id);
ALTER TABLE public.assessment_campaign_consumers ADD CONSTRAINT assessment_campaign_consumers_member_id_fkey CONSTRAINT assessment_campaign_consumers_member_id_fkey FOREIGN KEY (member_id) REFERENCES campaign_members (id);
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: heredada de su padre y registrada en la relación.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## assessment_final_locks

Compromiso previo de candidato/decisión que habilita evaluación final TEST.

Dominio: K. Evaluaciones. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| identity_hash | text | NO |  |
| evidence | jsonb | NO |  |
| created_at | timestamp with time zone | NO | clock_timestamp() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.assessment_final_locks ADD CONSTRAINT assessment_final_locks_pkey CONSTRAINT assessment_final_locks_pkey PRIMARY KEY (id);
ALTER TABLE public.assessment_final_locks ADD CONSTRAINT assessment_final_locks_identity_hash_key CONSTRAINT assessment_final_locks_identity_hash_key UNIQUE (identity_hash);
ALTER TABLE public.assessment_final_locks ADD CONSTRAINT assessment_final_locks_check CONSTRAINT assessment_final_locks_check CHECK (NOT(evidence ->> CAST('identity_hash' AS text)) IS DISTINCT FROM identity_hash);
ALTER TABLE public.assessment_final_locks ADD CONSTRAINT assessment_final_locks_evidence_check CONSTRAINT assessment_final_locks_evidence_check CHECK (jsonb_typeof(evidence) = CAST('object' AS text));
ALTER TABLE public.assessment_final_locks ADD CONSTRAINT assessment_final_locks_evidence_check1 CONSTRAINT assessment_final_locks_evidence_check1 CHECK (NOT(evidence ->> CAST('status' AS text)) IS DISTINCT FROM CAST('locked' AS text));
ALTER TABLE public.assessment_final_locks ADD CONSTRAINT assessment_final_locks_evidence_check2 CONSTRAINT assessment_final_locks_evidence_check2 CHECK (NOT jsonb_typeof(evidence -> CAST('candidate' AS text)) IS DISTINCT FROM CAST('object' AS text));
ALTER TABLE public.assessment_final_locks ADD CONSTRAINT assessment_final_locks_evidence_check3 CONSTRAINT assessment_final_locks_evidence_check3 CHECK (NOT jsonb_typeof(evidence -> CAST('decision' AS text)) IS DISTINCT FROM CAST('object' AS text));
ALTER TABLE public.assessment_final_locks ADD CONSTRAINT assessment_final_locks_identity_hash_check CONSTRAINT assessment_final_locks_identity_hash_check CHECK (identity_hash ~ CAST('^[a-f0-9]{64}$' AS text));
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: evidence. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: identity_hash.

## assessment_identities

Identidad canónica y hashes de modelo/dataset/población/protocolo de assessment.

Dominio: K. Evaluaciones. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| identity_hash | text | NO |  |
| training_run_id | uuid | NO |  |
| kind | text | NO |  |
| identity | jsonb | NO |  |
| canonical_identity | text | NO |  |
| structural_hash | text | YES | GENERATED ALWAYS AS (assessment_structural_hash(identity)) STORED |
| created_at | timestamp with time zone | NO | clock_timestamp() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_pkey CONSTRAINT assessment_identities_pkey PRIMARY KEY (id);
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_hash_key CONSTRAINT assessment_identities_identity_hash_key UNIQUE (identity_hash);
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_structural_hash_key CONSTRAINT assessment_identities_structural_hash_key UNIQUE (structural_hash);
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_check CONSTRAINT assessment_identities_check CHECK (NOT CAST(canonical_identity AS jsonb) IS DISTINCT FROM identity);
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_check1 CONSTRAINT assessment_identities_check1 CHECK (identity_hash = encode(sha256(convert_to(canonical_identity, CAST('UTF8' AS name))), CAST('hex' AS text)));
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_check2 CONSTRAINT assessment_identities_check2 CHECK (NOT(identity ->> CAST('kind' AS text)) IS DISTINCT FROM kind);
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_check3 CONSTRAINT assessment_identities_check3 CHECK (NOT((identity -> CAST('model' AS text)) ->> CAST('training_run_id' AS text)) IS DISTINCT FROM CAST(training_run_id AS text));
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check CONSTRAINT assessment_identities_identity_check CHECK (jsonb_typeof(identity) = CAST('object' AS text));
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check1 CONSTRAINT assessment_identities_identity_check1 CHECK (NOT(identity ->> CAST('schema' AS text)) IS DISTINCT FROM CAST('assessment_identity_v1' AS text));
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check10 CONSTRAINT assessment_identities_identity_check10 CHECK (NOT jsonb_typeof((identity -> CAST('decision' AS text)) -> CAST('effective' AS text)) IS DISTINCT FROM CAST('number' AS text));
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check11 CONSTRAINT assessment_identities_identity_check11 CHECK (CAST((identity -> CAST('decision' AS text)) ->> CAST('effective' AS text) AS numeric) >= CAST(0 AS numeric) AND CAST((identity -> CAST('decision' AS text)) ->> CAST('effective' AS text) AS numeric) <= CAST(1 AS numeric));
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check12 CONSTRAINT assessment_identities_identity_check12 CHECK (NOT((identity -> CAST('decision' AS text)) ->> CAST('score_domain' AS text)) IS DISTINCT FROM CAST('raw' AS text));
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check13 CONSTRAINT assessment_identities_identity_check13 CHECK (NOT((identity -> CAST('decision' AS text)) ->> CAST('comparison' AS text)) IS DISTINCT FROM CAST('>=' AS text));
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check14 CONSTRAINT assessment_identities_identity_check14 CHECK (NOT jsonb_typeof(identity -> CAST('dataset' AS text)) IS DISTINCT FROM CAST('object' AS text));
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check2 CONSTRAINT assessment_identities_identity_check2 CHECK (NOT jsonb_typeof(identity -> CAST('samples' AS text)) IS DISTINCT FROM CAST('array' AS text));
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check3 CONSTRAINT assessment_identities_identity_check3 CHECK (jsonb_array_length(identity -> CAST('samples' AS text)) > 0);
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check4 CONSTRAINT assessment_identities_identity_check4 CHECK (((identity ->> CAST('purpose' AS text)) = CAST('development' AS text) AND identity ->> CAST('split' AS text) = ANY(ARRAY[CAST('train' AS text), CAST('val' AS text)])) OR ((identity ->> CAST('purpose' AS text)) = CAST('final' AS text) AND (identity ->> CAST('split' AS text)) = CAST('test' AS text)));
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check5 CONSTRAINT assessment_identities_identity_check5 CHECK (identity ->> CAST('purpose' AS text) IS NOT NULL AND identity ->> CAST('split' AS text) IS NOT NULL);
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check6 CONSTRAINT assessment_identities_identity_check6 CHECK (NOT jsonb_typeof((identity -> CAST('model' AS text)) -> CAST('input_contract' AS text)) IS DISTINCT FROM CAST('object' AS text));
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check7 CONSTRAINT assessment_identities_identity_check7 CHECK ((identity -> CAST('model' AS text)) ->> CAST('sha256' AS text) IS NOT NULL AND ((identity -> CAST('model' AS text)) ->> CAST('sha256' AS text)) ~ CAST('^[a-f0-9]{64}$' AS text));
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check8 CONSTRAINT assessment_identities_identity_check8 CHECK ((identity -> CAST('model' AS text)) ->> CAST('model_version_id' AS text) IS NOT NULL AND CAST((identity -> CAST('model' AS text)) ->> CAST('model_version_id' AS text) AS uuid) IS NOT NULL);
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_check9 CONSTRAINT assessment_identities_identity_check9 CHECK ((identity -> CAST('model' AS text)) ->> CAST('checkpoint_artifact_id' AS text) IS NOT NULL AND CAST((identity -> CAST('model' AS text)) ->> CAST('checkpoint_artifact_id' AS text) AS uuid) IS NOT NULL);
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_identity_hash_check CONSTRAINT assessment_identities_identity_hash_check CHECK (identity_hash ~ CAST('^[a-f0-9]{64}$' AS text));
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_kind_check CONSTRAINT assessment_identities_kind_check CHECK (kind = ANY(ARRAY[CAST('evaluate' AS text), CAST('explain' AS text)]));
ALTER TABLE public.assessment_identities ADD CONSTRAINT assessment_identities_training_run_id_fkey CONSTRAINT assessment_identities_training_run_id_fkey FOREIGN KEY (training_run_id) REFERENCES runs (id);
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: identity. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: identity_hash, canonical_identity, structural_hash.

## assessment_results

Evidencia por intento/muestra; scores o explicación, append-only, proyección tipada v2.

Dominio: K. Evaluaciones. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| attempt_id | uuid | NO |  |
| sample_id | uuid | NO |  |
| payload | jsonb | NO |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.assessment_results ADD CONSTRAINT assessment_results_pkey CONSTRAINT assessment_results_pkey PRIMARY KEY (attempt_id, sample_id);
ALTER TABLE public.assessment_results ADD CONSTRAINT assessment_results_check CONSTRAINT assessment_results_check CHECK (NOT(payload ->> CAST('sample_id' AS text)) IS DISTINCT FROM CAST(sample_id AS text));
ALTER TABLE public.assessment_results ADD CONSTRAINT assessment_results_payload_check CONSTRAINT assessment_results_payload_check CHECK (jsonb_typeof(payload) = CAST('object' AS text));
ALTER TABLE public.assessment_results ADD CONSTRAINT assessment_results_attempt_id_fkey CONSTRAINT assessment_results_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES assessment_attempts (id);
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: heredada de su padre y registrada en la relación.
JSONB: payload. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## audit_events

Auditoría de seguridad y operaciones; login no es ejecución experimental.

Dominio: Q. Auditoría y trazabilidad técnica. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| event_type | text | NO |  |
| action | text | NO |  |
| actor_user_id | uuid | YES |  |
| actor_username_snapshot | text | YES |  |
| resource_type | text | NO |  |
| resource_id | text | YES |  |
| request_method | text | NO |  |
| request_path | text | NO |  |
| correlation_id | text | NO |  |
| before_state | jsonb | YES |  |
| after_state | jsonb | YES |  |
| metadata | jsonb | NO | CAST('{}' AS jsonb) |
| success | boolean | NO |  |
| error_code | text | YES |  |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.audit_events ADD CONSTRAINT audit_events_pkey CONSTRAINT audit_events_pkey PRIMARY KEY (id);
ALTER TABLE public.audit_events ADD CONSTRAINT audit_events_actor_user_id_fkey CONSTRAINT audit_events_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES users (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_audit_events_actor`, `ix_audit_events_created_at`, `ix_audit_events_resource`.
Auditoría: actor_user_id, created_at.
JSONB: before_state, after_state, metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: resource_type, resource_id.

## blood_samples

Muestra biológica de un caso y su identidad de ingestión, archivo y procedencia.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| case_id | uuid | NO |  |
| sample_code | varchar(120) | NO |  |
| specimen_type | varchar(80) | NO | CAST('peripheral_blood' AS varchar) |
| collection_method | varchar(120) | YES |  |
| anticoagulant | varchar(120) | YES |  |
| collected_at | timestamp with time zone | YES |  |
| received_at | timestamp with time zone | YES |  |
| status | varchar(20) | NO | CAST('registered' AS varchar) |
| notes | text | YES |  |
| metadata_json | jsonb | NO | CAST('{}' AS jsonb) |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |
| created_by | uuid | NO |  |
| updated_by | uuid | YES |  |
| archived_at | timestamp with time zone | YES |  |
| archived_by | uuid | YES |  |
| source_system | varchar(120) | YES |  |
| external_sample_id | varchar(240) | YES |  |
| sample_identity_origin | varchar(40) | NO | CAST('generated_by_capstone' AS varchar) |
| source_group_key | varchar(240) | YES |  |
| ingestion_status | varchar(20) | YES |  |
| expected_image_count | integer | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.blood_samples ADD CONSTRAINT blood_samples_pkey CONSTRAINT blood_samples_pkey PRIMARY KEY (id);
ALTER TABLE public.blood_samples ADD CONSTRAINT uq_blood_samples_case_code CONSTRAINT uq_blood_samples_case_code UNIQUE (case_id, sample_code);
ALTER TABLE public.blood_samples ADD CONSTRAINT blood_samples_metadata_json_check CONSTRAINT blood_samples_metadata_json_check CHECK (jsonb_typeof(metadata_json) = CAST('object' AS text));
ALTER TABLE public.blood_samples ADD CONSTRAINT blood_samples_sample_code_check CONSTRAINT blood_samples_sample_code_check CHECK (btrim(CAST(sample_code AS text)) <> CAST('' AS text));
ALTER TABLE public.blood_samples ADD CONSTRAINT blood_samples_status_check CONSTRAINT blood_samples_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('registered' AS varchar) AS text), CAST(CAST('received' AS varchar) AS text), CAST(CAST('prepared' AS varchar) AS text), CAST(CAST('archived' AS varchar) AS text)]));
ALTER TABLE public.blood_samples ADD CONSTRAINT ck_blood_sample_archive_state CONSTRAINT ck_blood_sample_archive_state CHECK ((CAST(status AS text) <> CAST('archived' AS text) AND archived_at IS NULL AND archived_by IS NULL) OR (CAST(status AS text) = CAST('archived' AS text) AND archived_at IS NOT NULL AND archived_by IS NOT NULL));
ALTER TABLE public.blood_samples ADD CONSTRAINT ck_blood_sample_chronology CONSTRAINT ck_blood_sample_chronology CHECK (collected_at IS NULL OR received_at IS NULL OR received_at >= collected_at);
ALTER TABLE public.blood_samples ADD CONSTRAINT ck_blood_samples_expected_count CONSTRAINT ck_blood_samples_expected_count CHECK (expected_image_count IS NULL OR expected_image_count > 0);
ALTER TABLE public.blood_samples ADD CONSTRAINT ck_blood_samples_identity_origin CONSTRAINT ck_blood_samples_identity_origin CHECK (CAST(sample_identity_origin AS text) = ANY(ARRAY[CAST(CAST('external_system' AS varchar) AS text), CAST(CAST('generated_by_capstone' AS varchar) AS text), CAST(CAST('derived_import_profile' AS varchar) AS text)]));
ALTER TABLE public.blood_samples ADD CONSTRAINT ck_blood_samples_ingestion_status CONSTRAINT ck_blood_samples_ingestion_status CHECK (ingestion_status IS NULL OR CAST(ingestion_status AS text) = ANY(ARRAY[CAST(CAST('pending' AS varchar) AS text), CAST(CAST('incomplete' AS varchar) AS text), CAST(CAST('complete' AS varchar) AS text), CAST(CAST('inconsistent' AS varchar) AS text), CAST(CAST('rejected' AS varchar) AS text)]));
ALTER TABLE public.blood_samples ADD CONSTRAINT blood_samples_archived_by_fkey CONSTRAINT blood_samples_archived_by_fkey FOREIGN KEY (archived_by) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.blood_samples ADD CONSTRAINT blood_samples_case_id_fkey CONSTRAINT blood_samples_case_id_fkey FOREIGN KEY (case_id) REFERENCES scientific_cases (id) ON DELETE RESTRICT;
ALTER TABLE public.blood_samples ADD CONSTRAINT blood_samples_created_by_fkey CONSTRAINT blood_samples_created_by_fkey FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.blood_samples ADD CONSTRAINT blood_samples_updated_by_fkey CONSTRAINT blood_samples_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_blood_samples_case`, `ix_blood_samples_status_created`, `uq_blood_samples_external_identity`.
Auditoría: collected_at, received_at, created_at, updated_at, created_by, updated_by, archived_at.
JSONB: metadata_json. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: source_system, source_group_key.

## campaign_attempts

Ordinal e historial de intentos por miembro, TRAIN asociado, estado y aceptación.

Dominio: I. Campañas. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| member_id | uuid | NO |  |
| ordinal | integer | NO |  |
| state | text | NO |  |
| training_run_id | uuid | YES |  |
| cause | text | YES |  |
| started_at | timestamp with time zone | NO | now() |
| finished_at | timestamp with time zone | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_pkey CONSTRAINT campaign_attempts_pkey PRIMARY KEY (id);
ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_member_id_id_key CONSTRAINT campaign_attempts_member_id_id_key UNIQUE (member_id, id);
ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_member_id_ordinal_key CONSTRAINT campaign_attempts_member_id_ordinal_key UNIQUE (member_id, ordinal);
ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_training_run_id_key CONSTRAINT campaign_attempts_training_run_id_key UNIQUE (training_run_id);
ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_check CONSTRAINT campaign_attempts_check CHECK ((state = CAST('active' AS text)) = (finished_at IS NULL));
ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_check1 CONSTRAINT campaign_attempts_check1 CHECK (state <> ALL(ARRAY[CAST('failed' AS text), CAST('interrupted' AS text)]) OR (cause IS NOT NULL AND length(btrim(cause)) > 0));
ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_check2 CONSTRAINT campaign_attempts_check2 CHECK (state <> ALL(ARRAY[CAST('completed' AS text), CAST('verified' AS text)]) OR training_run_id IS NOT NULL);
ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_ordinal_check CONSTRAINT campaign_attempts_ordinal_check CHECK (ordinal > 0);
ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_state_check CONSTRAINT campaign_attempts_state_check CHECK (state = ANY(ARRAY[CAST('active' AS text), CAST('failed' AS text), CAST('interrupted' AS text), CAST('completed' AS text), CAST('verified' AS text)]));
ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_member_id_fkey CONSTRAINT campaign_attempts_member_id_fkey FOREIGN KEY (member_id) REFERENCES campaign_members (id) ON DELETE RESTRICT;
ALTER TABLE public.campaign_attempts ADD CONSTRAINT campaign_attempts_training_run_id_fkey CONSTRAINT campaign_attempts_training_run_id_fkey FOREIGN KEY (training_run_id) REFERENCES runs (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_campaign_attempt_state`, `uq_campaign_one_active_attempt`.
Auditoría: started_at, finished_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## campaign_configurations

Configuración y hash canónicos por campaña; snapshot/request para reserva, columnas por run en v2.

Dominio: I. Campañas. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| campaign_id | uuid | NO |  |
| configuration_hash | text | NO |  |
| configuration | jsonb | NO |  |
| canonical_configuration | text | NO |  |
| requests | jsonb | NO |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.campaign_configurations ADD CONSTRAINT campaign_configurations_pkey CONSTRAINT campaign_configurations_pkey PRIMARY KEY (campaign_id, configuration_hash);
ALTER TABLE public.campaign_configurations ADD CONSTRAINT campaign_configurations_configuration_check CONSTRAINT campaign_configurations_configuration_check CHECK (jsonb_typeof(configuration) = CAST('object' AS text));
ALTER TABLE public.campaign_configurations ADD CONSTRAINT campaign_configurations_configuration_hash_check CONSTRAINT campaign_configurations_configuration_hash_check CHECK (configuration_hash ~ CAST('^[a-f0-9]{64}$' AS text));
ALTER TABLE public.campaign_configurations ADD CONSTRAINT campaign_configurations_requests_check CONSTRAINT campaign_configurations_requests_check CHECK (jsonb_typeof(requests) = CAST('array' AS text));
ALTER TABLE public.campaign_configurations ADD CONSTRAINT ck_campaign_configuration_required_v2 CONSTRAINT ck_campaign_configuration_required_v2 CHECK ((campaign_configuration_valid(configuration) AND jsonb_typeof(requests) = CAST('array' AS text) AND jsonb_array_length(requests) > 0) IS TRUE);
ALTER TABLE public.campaign_configurations ADD CONSTRAINT campaign_configurations_campaign_id_fkey CONSTRAINT campaign_configurations_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns (id) ON DELETE RESTRICT;
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: heredada de su padre y registrada en la relación.
JSONB: configuration, requests. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: configuration_hash, canonical_configuration.

## campaign_controlled_requests

Request idempotente de un reintento autorizado sobre campaña pausada y revisión técnica.

Dominio: I. Campañas. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| campaign_id | uuid | NO |  |
| member_id | uuid | NO |  |
| revision_id | uuid | NO |  |
| previous_attempt_id | uuid | NO |  |
| attempt_id | uuid | NO |  |
| run_id | uuid | NO |  |
| reason | text | NO |  |
| created_at | timestamp with time zone | NO | clock_timestamp() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_pkey CONSTRAINT campaign_controlled_requests_pkey PRIMARY KEY (id);
ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_attempt_id_key CONSTRAINT campaign_controlled_requests_attempt_id_key UNIQUE (attempt_id);
ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_previous_attempt_id_key CONSTRAINT campaign_controlled_requests_previous_attempt_id_key UNIQUE (previous_attempt_id);
ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_run_id_key CONSTRAINT campaign_controlled_requests_run_id_key UNIQUE (run_id);
ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_reason_check CONSTRAINT campaign_controlled_requests_reason_check CHECK (length(pg_catalog.btrim(reason)) > 0);
ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_attempt_id_fkey CONSTRAINT campaign_controlled_requests_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES campaign_attempts (id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_campaign_id_fkey CONSTRAINT campaign_controlled_requests_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns (id);
ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_campaign_id_revision_id_fkey CONSTRAINT campaign_controlled_requests_campaign_id_revision_id_fkey FOREIGN KEY (campaign_id, revision_id) REFERENCES campaign_technical_revisions (campaign_id, id);
ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_member_id_fkey CONSTRAINT campaign_controlled_requests_member_id_fkey FOREIGN KEY (member_id) REFERENCES campaign_members (id);
ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_previous_attempt_id_fkey CONSTRAINT campaign_controlled_requests_previous_attempt_id_fkey FOREIGN KEY (previous_attempt_id) REFERENCES campaign_attempts (id);
ALTER TABLE public.campaign_controlled_requests ADD CONSTRAINT campaign_controlled_requests_run_id_fkey CONSTRAINT campaign_controlled_requests_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) DEFERRABLE INITIALLY DEFERRED;
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## campaign_execution_events

Historial append-only de coordinación de una campaña.

Dominio: I. Campañas. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| campaign_id | uuid | NO |  |
| code | text | NO |  |
| created_at | timestamp with time zone | NO | clock_timestamp() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.campaign_execution_events ADD CONSTRAINT campaign_execution_events_pkey CONSTRAINT campaign_execution_events_pkey PRIMARY KEY (id);
ALTER TABLE public.campaign_execution_events ADD CONSTRAINT campaign_execution_events_campaign_id_fkey CONSTRAINT campaign_execution_events_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns (id);
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## campaign_members

Posición, configuración/semilla y estado del candidato; referencia al intento aceptado.

Dominio: I. Campañas. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| campaign_id | uuid | NO |  |
| configuration_hash | text | NO |  |
| seed | integer | NO |  |
| position | integer | NO |  |
| exclusion_reason | text | YES |  |
| state | text | NO | CAST('pending' AS text) |
| accepted_attempt_id | uuid | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_pkey CONSTRAINT campaign_members_pkey PRIMARY KEY (id);
ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_campaign_id_configuration_hash_seed_key CONSTRAINT campaign_members_campaign_id_configuration_hash_seed_key UNIQUE (campaign_id, configuration_hash, seed);
ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_campaign_id_position_key CONSTRAINT campaign_members_campaign_id_position_key UNIQUE (campaign_id, position);
ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_check CONSTRAINT campaign_members_check CHECK ((state = CAST('excluded' AS text)) = (exclusion_reason IS NOT NULL));
ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_check1 CONSTRAINT campaign_members_check1 CHECK ((state = CAST('verified' AS text)) = (accepted_attempt_id IS NOT NULL));
ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_exclusion_reason_check CONSTRAINT campaign_members_exclusion_reason_check CHECK (exclusion_reason IS NULL OR length(btrim(exclusion_reason)) > 0);
ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_position_check CONSTRAINT campaign_members_position_check CHECK (position >= 0);
ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_seed_check CONSTRAINT campaign_members_seed_check CHECK (seed >= 0);
ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_state_check CONSTRAINT campaign_members_state_check CHECK (state = ANY(ARRAY[CAST('pending' AS text), CAST('active' AS text), CAST('failed' AS text), CAST('interrupted' AS text), CAST('completed' AS text), CAST('verified' AS text), CAST('excluded' AS text)]));
ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_campaign_id_configuration_hash_fkey CONSTRAINT campaign_members_campaign_id_configuration_hash_fkey FOREIGN KEY (campaign_id, configuration_hash) REFERENCES campaign_configurations (campaign_id, configuration_hash) ON DELETE RESTRICT;
ALTER TABLE public.campaign_members ADD CONSTRAINT campaign_members_campaign_id_fkey CONSTRAINT campaign_members_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns (id) ON DELETE RESTRICT;
ALTER TABLE public.campaign_members ADD CONSTRAINT fk_member_accepted_attempt CONSTRAINT fk_member_accepted_attempt FOREIGN KEY (id, accepted_attempt_id) REFERENCES campaign_attempts (member_id, id) DEFERRABLE INITIALLY DEFERRED;
```

Índices explícitos: `ix_campaign_member_state`.
Auditoría: heredada de su padre y registrada en la relación.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: configuration_hash.

## campaign_technical_revisions

Cambio técnico autorizado de entorno sin modificar contrato científico congelado.

Dominio: I. Campañas. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| campaign_id | uuid | NO |  |
| payload | jsonb | NO |  |
| canonical_payload | text | NO |  |
| payload_hash | text | NO |  |
| created_at | timestamp with time zone | NO | clock_timestamp() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.campaign_technical_revisions ADD CONSTRAINT campaign_technical_revisions_pkey CONSTRAINT campaign_technical_revisions_pkey PRIMARY KEY (id);
ALTER TABLE public.campaign_technical_revisions ADD CONSTRAINT campaign_technical_revisions_campaign_id_id_key CONSTRAINT campaign_technical_revisions_campaign_id_id_key UNIQUE (campaign_id, id);
ALTER TABLE public.campaign_technical_revisions ADD CONSTRAINT campaign_technical_revisions_check CONSTRAINT campaign_technical_revisions_check CHECK (CAST(canonical_payload AS jsonb) = payload);
ALTER TABLE public.campaign_technical_revisions ADD CONSTRAINT campaign_technical_revisions_check1 CONSTRAINT campaign_technical_revisions_check1 CHECK (encode(sha256(convert_to(canonical_payload, CAST('UTF8' AS name))), CAST('hex' AS text)) = payload_hash);
ALTER TABLE public.campaign_technical_revisions ADD CONSTRAINT campaign_technical_revisions_payload_hash_check CONSTRAINT campaign_technical_revisions_payload_hash_check CHECK (payload_hash ~ CAST('^[a-f0-9]{64}$' AS text));
ALTER TABLE public.campaign_technical_revisions ADD CONSTRAINT campaign_technical_revisions_campaign_id_fkey CONSTRAINT campaign_technical_revisions_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns (id);
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: payload. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: canonical_payload, payload_hash.

## cell_classification_events

Progreso, errores y resultados de clasificación celular por ejecución/entrada.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| classification_run_id | uuid | NO |  |
| cell_detection_id | uuid | YES |  |
| cell_prediction_id | uuid | YES |  |
| event_type | varchar(120) | NO |  |
| status | varchar(40) | NO |  |
| message_code | varchar(80) | YES |  |
| message | text | YES |  |
| progress_current | integer | YES |  |
| progress_total | integer | YES |  |
| metadata_json | jsonb | NO | CAST('{}' AS jsonb) |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.cell_classification_events ADD CONSTRAINT cell_classification_events_pkey CONSTRAINT cell_classification_events_pkey PRIMARY KEY (id);
ALTER TABLE public.cell_classification_events ADD CONSTRAINT cell_classification_events_event_type_check CONSTRAINT cell_classification_events_event_type_check CHECK (btrim(CAST(event_type AS text)) <> CAST('' AS text));
ALTER TABLE public.cell_classification_events ADD CONSTRAINT cell_classification_events_metadata_json_check CONSTRAINT cell_classification_events_metadata_json_check CHECK (jsonb_typeof(metadata_json) = CAST('object' AS text));
ALTER TABLE public.cell_classification_events ADD CONSTRAINT cell_classification_events_progress_current_check CONSTRAINT cell_classification_events_progress_current_check CHECK (progress_current IS NULL OR progress_current >= 0);
ALTER TABLE public.cell_classification_events ADD CONSTRAINT cell_classification_events_progress_total_check CONSTRAINT cell_classification_events_progress_total_check CHECK (progress_total IS NULL OR progress_total >= 0);
ALTER TABLE public.cell_classification_events ADD CONSTRAINT cell_classification_events_status_check CONSTRAINT cell_classification_events_status_check CHECK (btrim(CAST(status AS text)) <> CAST('' AS text));
ALTER TABLE public.cell_classification_events ADD CONSTRAINT ck_cell_classification_event_progress CONSTRAINT ck_cell_classification_event_progress CHECK (progress_current IS NULL OR progress_total IS NULL OR progress_current <= progress_total);
ALTER TABLE public.cell_classification_events ADD CONSTRAINT cell_classification_events_cell_detection_id_fkey CONSTRAINT cell_classification_events_cell_detection_id_fkey FOREIGN KEY (cell_detection_id) REFERENCES cell_detections (id) ON DELETE RESTRICT;
ALTER TABLE public.cell_classification_events ADD CONSTRAINT cell_classification_events_classification_run_id_fkey CONSTRAINT cell_classification_events_classification_run_id_fkey FOREIGN KEY (classification_run_id) REFERENCES cell_classification_runs (id) ON DELETE RESTRICT;
ALTER TABLE public.cell_classification_events ADD CONSTRAINT fk_cell_classification_event_prediction CONSTRAINT fk_cell_classification_event_prediction FOREIGN KEY (cell_prediction_id, classification_run_id) REFERENCES cell_predictions (id, classification_run_id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_cell_classification_events_run_created`, `ix_cell_classification_events_run_detection`, `ix_cell_classification_events_run_prediction`.
Auditoría: created_at.
JSONB: metadata_json. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## cell_classification_inputs

Conjunto ordenado congelado de crops/detecciones, elegibilidad y checksum del input.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| classification_run_id | uuid | NO |  |
| detection_run_id | uuid | NO |  |
| cell_detection_id | uuid | NO |  |
| microscopy_image_id | uuid | NO |  |
| crop_id | uuid | YES |  |
| input_order | integer | NO |  |
| image_sequence_number | integer | NO |  |
| cell_index | integer | NO |  |
| cell_code | varchar(40) | NO |  |
| detector_key | varchar(80) | NO |  |
| detector_version | varchar(40) | NO |  |
| detector_algorithm_version | varchar(80) | NO |  |
| crop_sha256 | char(64) | YES |  |
| crop_width_px | integer | YES |  |
| crop_height_px | integer | YES |  |
| detection_review_status_at_creation | varchar(30) | YES |  |
| eligible | boolean | NO |  |
| exclusion_reason | varchar(120) | YES |  |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT cell_classification_inputs_pkey CONSTRAINT cell_classification_inputs_pkey PRIMARY KEY (id);
ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT uq_cell_classification_inputs_crop CONSTRAINT uq_cell_classification_inputs_crop UNIQUE (classification_run_id, crop_id);
ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT uq_cell_classification_inputs_detection CONSTRAINT uq_cell_classification_inputs_detection UNIQUE (classification_run_id, cell_detection_id);
ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT uq_cell_classification_inputs_order CONSTRAINT uq_cell_classification_inputs_order UNIQUE (classification_run_id, input_order);
ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT uq_cell_classification_inputs_prediction_owner CONSTRAINT uq_cell_classification_inputs_prediction_owner UNIQUE (id, classification_run_id, cell_detection_id, crop_id);
ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT cell_classification_inputs_cell_code_check CONSTRAINT cell_classification_inputs_cell_code_check CHECK (CAST(cell_code AS text) ~ CAST('^CELL-[A-F0-9]{12}$' AS text));
ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT cell_classification_inputs_cell_index_check CONSTRAINT cell_classification_inputs_cell_index_check CHECK (cell_index > 0);
ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT cell_classification_inputs_detector_algorithm_version_check CONSTRAINT cell_classification_inputs_detector_algorithm_version_check CHECK (btrim(CAST(detector_algorithm_version AS text)) <> CAST('' AS text));
ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT cell_classification_inputs_detector_key_check CONSTRAINT cell_classification_inputs_detector_key_check CHECK (btrim(CAST(detector_key AS text)) <> CAST('' AS text));
ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT cell_classification_inputs_detector_version_check CONSTRAINT cell_classification_inputs_detector_version_check CHECK (btrim(CAST(detector_version AS text)) <> CAST('' AS text));
ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT cell_classification_inputs_image_sequence_number_check CONSTRAINT cell_classification_inputs_image_sequence_number_check CHECK (image_sequence_number > 0);
ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT cell_classification_inputs_input_order_check CONSTRAINT cell_classification_inputs_input_order_check CHECK (input_order > 0);
ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT ck_cell_classification_input_crop_metadata CONSTRAINT ck_cell_classification_input_crop_metadata CHECK ((crop_id IS NULL AND NOT eligible AND crop_sha256 IS NULL AND crop_width_px IS NULL AND crop_height_px IS NULL) OR (crop_id IS NOT NULL AND crop_sha256 IS NOT NULL AND crop_sha256 ~ CAST('^[0-9a-f]{64}$' AS text) AND crop_width_px IS NOT NULL AND crop_width_px > 0 AND crop_height_px IS NOT NULL AND crop_height_px > 0));
ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT ck_cell_classification_input_eligibility CONSTRAINT ck_cell_classification_input_eligibility CHECK ((eligible AND crop_id IS NOT NULL AND exclusion_reason IS NULL) OR (NOT eligible AND exclusion_reason IS NOT NULL AND btrim(CAST(exclusion_reason AS text)) <> CAST('' AS text)));
ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT ck_cell_classification_input_review CONSTRAINT ck_cell_classification_input_review CHECK (detection_review_status_at_creation IS NULL OR CAST(detection_review_status_at_creation AS text) = ANY(ARRAY[CAST(CAST('unreviewed' AS varchar) AS text), CAST(CAST('accepted' AS varchar) AS text), CAST(CAST('rejected' AS varchar) AS text), CAST(CAST('needs_attention' AS varchar) AS text)]));
ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT fk_cell_classification_input_crop CONSTRAINT fk_cell_classification_input_crop FOREIGN KEY (crop_id, cell_detection_id) REFERENCES cell_crops (id, cell_detection_id) ON DELETE RESTRICT;
ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT fk_cell_classification_input_detection CONSTRAINT fk_cell_classification_input_detection FOREIGN KEY (cell_detection_id, detection_run_id, microscopy_image_id) REFERENCES cell_detections (id, detection_run_id, microscopy_image_id) ON DELETE RESTRICT;
ALTER TABLE public.cell_classification_inputs ADD CONSTRAINT fk_cell_classification_input_run_detection CONSTRAINT fk_cell_classification_input_run_detection FOREIGN KEY (classification_run_id, detection_run_id) REFERENCES cell_classification_runs (id, detection_run_id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_cell_classification_inputs_crop`, `ix_cell_classification_inputs_detection`, `ix_cell_classification_inputs_run_eligible_order`, `ix_cell_classification_inputs_run_image_cell`.
Auditoría: created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: crop_sha256.

## cell_classification_reviews

Decisión humana sobre predicción celular; no altera la salida automática.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| cell_prediction_id | uuid | NO |  |
| decision | varchar(30) | NO |  |
| reviewed_label | varchar(20) | YES |  |
| comment | text | YES |  |
| actor_user_id | uuid | NO |  |
| created_at | timestamp with time zone | NO | clock_timestamp() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.cell_classification_reviews ADD CONSTRAINT cell_classification_reviews_pkey CONSTRAINT cell_classification_reviews_pkey PRIMARY KEY (id);
ALTER TABLE public.cell_classification_reviews ADD CONSTRAINT cell_classification_reviews_decision_check CONSTRAINT cell_classification_reviews_decision_check CHECK (CAST(decision AS text) = ANY(ARRAY[CAST(CAST('confirmed' AS varchar) AS text), CAST(CAST('corrected' AS varchar) AS text), CAST(CAST('needs_attention' AS varchar) AS text), CAST(CAST('comment_only' AS varchar) AS text)]));
ALTER TABLE public.cell_classification_reviews ADD CONSTRAINT cell_classification_reviews_reviewed_label_check CONSTRAINT cell_classification_reviews_reviewed_label_check CHECK (reviewed_label IS NULL OR CAST(reviewed_label AS text) = ANY(ARRAY[CAST(CAST('parasitized' AS varchar) AS text), CAST(CAST('uninfected' AS varchar) AS text)]));
ALTER TABLE public.cell_classification_reviews ADD CONSTRAINT ck_cell_classification_review_payload CONSTRAINT ck_cell_classification_review_payload CHECK ((CAST(decision AS text) = CAST('confirmed' AS text) AND (comment IS NULL OR btrim(comment) <> CAST('' AS text))) OR (CAST(decision AS text) = CAST('corrected' AS text) AND reviewed_label IS NOT NULL AND (comment IS NULL OR btrim(comment) <> CAST('' AS text))) OR (CAST(decision AS text) = ANY(ARRAY[CAST(CAST('needs_attention' AS varchar) AS text), CAST(CAST('comment_only' AS varchar) AS text)]) AND reviewed_label IS NULL AND comment IS NOT NULL AND btrim(comment) <> CAST('' AS text)));
ALTER TABLE public.cell_classification_reviews ADD CONSTRAINT cell_classification_reviews_actor_user_id_fkey CONSTRAINT cell_classification_reviews_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.cell_classification_reviews ADD CONSTRAINT cell_classification_reviews_cell_prediction_id_fkey CONSTRAINT cell_classification_reviews_cell_prediction_id_fkey FOREIGN KEY (cell_prediction_id) REFERENCES cell_predictions (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_cell_classification_reviews_actor_created`, `ix_cell_classification_reviews_prediction_created`.
Auditoría: actor_user_id, created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## cell_classification_runs

Ejecución clínica con snapshot de modelo/política, manifiesto de inputs y máquina de estado.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| analysis_run_id | uuid | NO |  |
| detection_run_id | uuid | NO |  |
| classification_run_code | varchar(20) | NO |  |
| production_model_id | uuid | NO |  |
| stage2_publication_id | uuid | NO |  |
| model_registry_id | uuid | NO |  |
| model_name | varchar(160) | NO |  |
| model_version | varchar(120) | YES |  |
| model_snapshot | jsonb | NO |  |
| input_manifest_sha256 | char(64) | NO |  |
| status | varchar(30) | NO |  |
| input_count | integer | NO |  |
| eligible_count | integer | NO |  |
| excluded_count | integer | NO |  |
| processed_count | integer | NO | 0 |
| parasitized_count | integer | NO | 0 |
| uninfected_count | integer | NO | 0 |
| near_threshold_count | integer | NO | 0 |
| failed_count | integer | NO | 0 |
| requested_by | uuid | NO |  |
| retry_of_run_id | uuid | YES |  |
| started_at | timestamp with time zone | YES |  |
| completed_at | timestamp with time zone | YES |  |
| failed_at | timestamp with time zone | YES |  |
| error_code | varchar(80) | YES |  |
| error_message | text | YES |  |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_pkey CONSTRAINT cell_classification_runs_pkey PRIMARY KEY (id);
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_classification_run_code_key CONSTRAINT cell_classification_runs_classification_run_code_key UNIQUE (classification_run_code);
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT uq_cell_classification_runs_detection_identity CONSTRAINT uq_cell_classification_runs_detection_identity UNIQUE (id, detection_run_id);
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT uq_cell_classification_runs_identity CONSTRAINT uq_cell_classification_runs_identity UNIQUE (id, analysis_run_id, detection_run_id);
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_classification_run_code_check CONSTRAINT cell_classification_runs_classification_run_code_check CHECK (CAST(classification_run_code AS text) ~ CAST('^CLS-[A-F0-9]{8}$' AS text));
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_eligible_count_check CONSTRAINT cell_classification_runs_eligible_count_check CHECK (eligible_count >= 0);
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_excluded_count_check CONSTRAINT cell_classification_runs_excluded_count_check CHECK (excluded_count >= 0);
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_failed_count_check CONSTRAINT cell_classification_runs_failed_count_check CHECK (failed_count >= 0);
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_input_count_check CONSTRAINT cell_classification_runs_input_count_check CHECK (input_count >= 0);
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_input_manifest_sha256_check CONSTRAINT cell_classification_runs_input_manifest_sha256_check CHECK (input_manifest_sha256 ~ CAST('^[0-9a-f]{64}$' AS text));
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_model_name_check CONSTRAINT cell_classification_runs_model_name_check CHECK (btrim(CAST(model_name AS text)) <> CAST('' AS text));
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_model_snapshot_check CONSTRAINT cell_classification_runs_model_snapshot_check CHECK (jsonb_typeof(model_snapshot) = CAST('object' AS text));
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_near_threshold_count_check CONSTRAINT cell_classification_runs_near_threshold_count_check CHECK (near_threshold_count >= 0);
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_parasitized_count_check CONSTRAINT cell_classification_runs_parasitized_count_check CHECK (parasitized_count >= 0);
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_processed_count_check CONSTRAINT cell_classification_runs_processed_count_check CHECK (processed_count >= 0);
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_status_check CONSTRAINT cell_classification_runs_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('created' AS varchar) AS text), CAST(CAST('processing' AS varchar) AS text), CAST(CAST('completed' AS varchar) AS text), CAST(CAST('completed_with_warnings' AS varchar) AS text), CAST(CAST('failed' AS varchar) AS text)]));
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_uninfected_count_check CONSTRAINT cell_classification_runs_uninfected_count_check CHECK (uninfected_count >= 0);
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT ck_cell_classification_run_counts CONSTRAINT ck_cell_classification_run_counts CHECK (input_count = (eligible_count + excluded_count) AND processed_count <= eligible_count AND processed_count = (parasitized_count + uninfected_count + failed_count) AND near_threshold_count <= (parasitized_count + uninfected_count));
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT ck_cell_classification_run_model_version CONSTRAINT ck_cell_classification_run_model_version CHECK (model_version IS NULL OR btrim(CAST(model_version AS text)) <> CAST('' AS text));
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT ck_cell_classification_run_retry CONSTRAINT ck_cell_classification_run_retry CHECK (retry_of_run_id IS NULL OR retry_of_run_id <> id);
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT ck_cell_classification_run_terminal_state CONSTRAINT ck_cell_classification_run_terminal_state CHECK ((CAST(status AS text) = CAST('created' AS text) AND started_at IS NULL AND completed_at IS NULL AND failed_at IS NULL AND error_code IS NULL AND error_message IS NULL) OR (CAST(status AS text) = CAST('processing' AS text) AND started_at IS NOT NULL AND completed_at IS NULL AND failed_at IS NULL AND error_code IS NULL AND error_message IS NULL) OR (CAST(status AS text) = ANY(ARRAY[CAST(CAST('completed' AS varchar) AS text), CAST(CAST('completed_with_warnings' AS varchar) AS text)]) AND started_at IS NOT NULL AND completed_at IS NOT NULL AND failed_at IS NULL AND error_code IS NULL AND error_message IS NULL AND processed_count = eligible_count) OR (CAST(status AS text) = CAST('failed' AS text) AND started_at IS NOT NULL AND completed_at IS NULL AND failed_at IS NOT NULL AND error_code IS NOT NULL AND btrim(CAST(error_code AS text)) <> CAST('' AS text)));
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT ck_cell_classification_run_time_order CONSTRAINT ck_cell_classification_run_time_order CHECK (updated_at >= created_at AND (started_at IS NULL OR started_at >= created_at) AND (completed_at IS NULL OR completed_at >= started_at) AND (failed_at IS NULL OR failed_at >= started_at));
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_requested_by_fkey CONSTRAINT cell_classification_runs_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT cell_classification_runs_retry_of_run_id_fkey CONSTRAINT cell_classification_runs_retry_of_run_id_fkey FOREIGN KEY (retry_of_run_id) REFERENCES cell_classification_runs (id) ON DELETE RESTRICT;
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT fk_cell_classification_run_deployment_version CONSTRAINT fk_cell_classification_run_deployment_version FOREIGN KEY (production_model_id, model_registry_id) REFERENCES deployed_model_versions (id, model_version_id) ON DELETE RESTRICT;
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT fk_cell_classification_run_detection_analysis CONSTRAINT fk_cell_classification_run_detection_analysis FOREIGN KEY (detection_run_id, analysis_run_id) REFERENCES cell_detection_runs (id, analysis_run_id) ON DELETE RESTRICT;
ALTER TABLE public.cell_classification_runs ADD CONSTRAINT fk_cell_classification_run_publication_version CONSTRAINT fk_cell_classification_run_publication_version FOREIGN KEY (stage2_publication_id, model_registry_id) REFERENCES stage2_model_publications (id, model_version_id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_cell_classification_runs_analysis_created`, `ix_cell_classification_runs_detection_created`, `ix_cell_classification_runs_model_created`, `ix_cell_classification_runs_status_created`, `uq_cell_classification_runs_equivalent_active`.
Auditoría: started_at, completed_at, failed_at, created_at, updated_at.
JSONB: model_snapshot. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: input_manifest_sha256.

## cell_crops

Artefacto de recorte y geometría por detección; entrada de clasificación/XAI.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| cell_detection_id | uuid | NO |  |
| relative_storage_key | text | NO |  |
| sha256 | char(64) | NO |  |
| file_size_bytes | bigint | NO |  |
| width_px | integer | NO |  |
| height_px | integer | NO |  |
| format | varchar(20) | NO |  |
| padding_px | integer | NO |  |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.cell_crops ADD CONSTRAINT cell_crops_pkey CONSTRAINT cell_crops_pkey PRIMARY KEY (id);
ALTER TABLE public.cell_crops ADD CONSTRAINT uq_cell_crops_detection CONSTRAINT uq_cell_crops_detection UNIQUE (cell_detection_id);
ALTER TABLE public.cell_crops ADD CONSTRAINT uq_cell_crops_storage_key CONSTRAINT uq_cell_crops_storage_key UNIQUE (relative_storage_key);
ALTER TABLE public.cell_crops ADD CONSTRAINT cell_crops_file_size_bytes_check CONSTRAINT cell_crops_file_size_bytes_check CHECK (file_size_bytes > 0);
ALTER TABLE public.cell_crops ADD CONSTRAINT cell_crops_format_check CONSTRAINT cell_crops_format_check CHECK (CAST(format AS text) = CAST('PNG' AS text));
ALTER TABLE public.cell_crops ADD CONSTRAINT cell_crops_height_px_check CONSTRAINT cell_crops_height_px_check CHECK (height_px > 0);
ALTER TABLE public.cell_crops ADD CONSTRAINT cell_crops_padding_px_check CONSTRAINT cell_crops_padding_px_check CHECK (padding_px >= 0);
ALTER TABLE public.cell_crops ADD CONSTRAINT cell_crops_relative_storage_key_check CONSTRAINT cell_crops_relative_storage_key_check CHECK (relative_storage_key ~ CAST('^cell-crops/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/crop[.]png$' AS text));
ALTER TABLE public.cell_crops ADD CONSTRAINT cell_crops_sha256_check CONSTRAINT cell_crops_sha256_check CHECK (sha256 ~ CAST('^[0-9a-f]{64}$' AS text));
ALTER TABLE public.cell_crops ADD CONSTRAINT cell_crops_width_px_check CONSTRAINT cell_crops_width_px_check CHECK (width_px > 0);
ALTER TABLE public.cell_crops ADD CONSTRAINT fk_cell_crops_detection CONSTRAINT fk_cell_crops_detection FOREIGN KEY (cell_detection_id) REFERENCES cell_detections (id) ON DELETE RESTRICT;
```

Índices explícitos: `uq_cell_crops_id_detection`.
Auditoría: created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: sha256.

## cell_detection_events

Progreso y eventos de detección sobre imágenes del análisis.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| detection_run_id | uuid | NO |  |
| microscopy_image_id | uuid | YES |  |
| event_type | varchar(100) | NO |  |
| stage | varchar(50) | NO |  |
| status | varchar(30) | NO |  |
| message_code | varchar(80) | YES |  |
| message | text | YES |  |
| progress_current | integer | YES |  |
| progress_total | integer | YES |  |
| metadata_json | jsonb | NO | CAST('{}' AS jsonb) |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.cell_detection_events ADD CONSTRAINT cell_detection_events_pkey CONSTRAINT cell_detection_events_pkey PRIMARY KEY (id);
ALTER TABLE public.cell_detection_events ADD CONSTRAINT cell_detection_events_event_type_check CONSTRAINT cell_detection_events_event_type_check CHECK (btrim(CAST(event_type AS text)) <> CAST('' AS text));
ALTER TABLE public.cell_detection_events ADD CONSTRAINT cell_detection_events_metadata_json_check CONSTRAINT cell_detection_events_metadata_json_check CHECK (jsonb_typeof(metadata_json) = CAST('object' AS text));
ALTER TABLE public.cell_detection_events ADD CONSTRAINT cell_detection_events_progress_current_check CONSTRAINT cell_detection_events_progress_current_check CHECK (progress_current IS NULL OR progress_current >= 0);
ALTER TABLE public.cell_detection_events ADD CONSTRAINT cell_detection_events_progress_total_check CONSTRAINT cell_detection_events_progress_total_check CHECK (progress_total IS NULL OR progress_total >= 0);
ALTER TABLE public.cell_detection_events ADD CONSTRAINT cell_detection_events_stage_check CONSTRAINT cell_detection_events_stage_check CHECK (btrim(CAST(stage AS text)) <> CAST('' AS text));
ALTER TABLE public.cell_detection_events ADD CONSTRAINT cell_detection_events_status_check CONSTRAINT cell_detection_events_status_check CHECK (btrim(CAST(status AS text)) <> CAST('' AS text));
ALTER TABLE public.cell_detection_events ADD CONSTRAINT ck_cell_detection_event_progress CONSTRAINT ck_cell_detection_event_progress CHECK (progress_current IS NULL OR progress_total IS NULL OR progress_current <= progress_total);
ALTER TABLE public.cell_detection_events ADD CONSTRAINT cell_detection_events_detection_run_id_fkey CONSTRAINT cell_detection_events_detection_run_id_fkey FOREIGN KEY (detection_run_id) REFERENCES cell_detection_runs (id) ON DELETE RESTRICT;
ALTER TABLE public.cell_detection_events ADD CONSTRAINT cell_detection_events_microscopy_image_id_fkey CONSTRAINT cell_detection_events_microscopy_image_id_fkey FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_cell_detection_events_run_created`, `ix_cell_detection_events_run_image`.
Auditoría: created_at.
JSONB: metadata_json. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## cell_detection_runs

Identidad/versiones del detector, perfil y estado sobre análisis de microscopía.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| analysis_run_id | uuid | NO |  |
| detection_run_code | varchar(20) | NO |  |
| detector_key | varchar(80) | NO |  |
| detector_version | varchar(40) | NO |  |
| algorithm_version | varchar(80) | NO |  |
| profile_snapshot | jsonb | NO |  |
| input_manifest_sha256 | char(64) | NO |  |
| status | varchar(30) | NO |  |
| image_count | integer | NO |  |
| processed_image_count | integer | NO | 0 |
| component_count | integer | NO | 0 |
| detection_count | integer | NO | 0 |
| crop_count | integer | NO | 0 |
| warning_count | integer | NO | 0 |
| requested_by | uuid | NO |  |
| started_at | timestamp with time zone | YES |  |
| completed_at | timestamp with time zone | YES |  |
| failed_at | timestamp with time zone | YES |  |
| error_code | varchar(80) | YES |  |
| error_message | text | YES |  |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_pkey CONSTRAINT cell_detection_runs_pkey PRIMARY KEY (id);
ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_detection_run_code_key CONSTRAINT cell_detection_runs_detection_run_code_key UNIQUE (detection_run_code);
ALTER TABLE public.cell_detection_runs ADD CONSTRAINT uq_cell_detection_runs_identity CONSTRAINT uq_cell_detection_runs_identity UNIQUE (id, analysis_run_id);
ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_algorithm_version_check CONSTRAINT cell_detection_runs_algorithm_version_check CHECK (btrim(CAST(algorithm_version AS text)) <> CAST('' AS text));
ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_check CONSTRAINT cell_detection_runs_check CHECK (processed_image_count >= 0 AND processed_image_count <= image_count);
ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_component_count_check CONSTRAINT cell_detection_runs_component_count_check CHECK (component_count >= 0);
ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_crop_count_check CONSTRAINT cell_detection_runs_crop_count_check CHECK (crop_count >= 0);
ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_detection_count_check CONSTRAINT cell_detection_runs_detection_count_check CHECK (detection_count >= 0);
ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_detection_run_code_check CONSTRAINT cell_detection_runs_detection_run_code_check CHECK (CAST(detection_run_code AS text) ~ CAST('^DET-[A-F0-9]{8}$' AS text));
ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_detector_key_check CONSTRAINT cell_detection_runs_detector_key_check CHECK (btrim(CAST(detector_key AS text)) <> CAST('' AS text));
ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_detector_version_check CONSTRAINT cell_detection_runs_detector_version_check CHECK (btrim(CAST(detector_version AS text)) <> CAST('' AS text));
ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_image_count_check CONSTRAINT cell_detection_runs_image_count_check CHECK (image_count > 0);
ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_input_manifest_sha256_check CONSTRAINT cell_detection_runs_input_manifest_sha256_check CHECK (input_manifest_sha256 ~ CAST('^[0-9a-f]{64}$' AS text));
ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_profile_snapshot_check CONSTRAINT cell_detection_runs_profile_snapshot_check CHECK (jsonb_typeof(profile_snapshot) = CAST('object' AS text));
ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_status_check CONSTRAINT cell_detection_runs_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('created' AS varchar) AS text), CAST(CAST('processing' AS varchar) AS text), CAST(CAST('completed' AS varchar) AS text), CAST(CAST('completed_with_warnings' AS varchar) AS text), CAST(CAST('failed' AS varchar) AS text)]));
ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_warning_count_check CONSTRAINT cell_detection_runs_warning_count_check CHECK (warning_count >= 0);
ALTER TABLE public.cell_detection_runs ADD CONSTRAINT ck_cell_detection_run_terminal_state CONSTRAINT ck_cell_detection_run_terminal_state CHECK ((CAST(status AS text) = CAST('created' AS text) AND started_at IS NULL AND completed_at IS NULL AND failed_at IS NULL AND error_code IS NULL AND error_message IS NULL) OR (CAST(status AS text) = CAST('processing' AS text) AND started_at IS NOT NULL AND completed_at IS NULL AND failed_at IS NULL AND error_code IS NULL AND error_message IS NULL) OR (CAST(status AS text) = ANY(ARRAY[CAST(CAST('completed' AS varchar) AS text), CAST(CAST('completed_with_warnings' AS varchar) AS text)]) AND started_at IS NOT NULL AND completed_at IS NOT NULL AND failed_at IS NULL AND error_code IS NULL AND error_message IS NULL) OR (CAST(status AS text) = CAST('failed' AS text) AND started_at IS NOT NULL AND completed_at IS NULL AND failed_at IS NOT NULL AND error_code IS NOT NULL));
ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_analysis_run_id_fkey CONSTRAINT cell_detection_runs_analysis_run_id_fkey FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs (id) ON DELETE RESTRICT;
ALTER TABLE public.cell_detection_runs ADD CONSTRAINT cell_detection_runs_requested_by_fkey CONSTRAINT cell_detection_runs_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES users (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_cell_detection_runs_analysis_created`, `ix_cell_detection_runs_status_created`, `uq_cell_detection_runs_equivalent_active`.
Auditoría: started_at, completed_at, failed_at, created_at, updated_at.
JSONB: profile_snapshot. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: input_manifest_sha256.

## cell_detections

Detecciones propuestas y revisadas a partir de componentes; geometría por célula.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| detection_run_id | uuid | NO |  |
| analysis_run_id | uuid | NO |  |
| connected_component_id | uuid | NO |  |
| analysis_run_image_id | uuid | NO |  |
| microscopy_image_id | uuid | NO |  |
| cell_index | integer | NO |  |
| cell_code | varchar(40) | NO |  |
| bbox_x | integer | NO |  |
| bbox_y | integer | NO |  |
| bbox_width | integer | NO |  |
| bbox_height | integer | NO |  |
| coordinate_space | varchar(40) | NO |  |
| detector_score | double precision | YES |  |
| automated_status | varchar(30) | NO |  |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.cell_detections ADD CONSTRAINT cell_detections_pkey CONSTRAINT cell_detections_pkey PRIMARY KEY (id);
ALTER TABLE public.cell_detections ADD CONSTRAINT uq_cell_detections_cell_code CONSTRAINT uq_cell_detections_cell_code UNIQUE (cell_code);
ALTER TABLE public.cell_detections ADD CONSTRAINT uq_cell_detections_component CONSTRAINT uq_cell_detections_component UNIQUE (connected_component_id);
ALTER TABLE public.cell_detections ADD CONSTRAINT uq_cell_detections_identity CONSTRAINT uq_cell_detections_identity UNIQUE (id, detection_run_id, microscopy_image_id);
ALTER TABLE public.cell_detections ADD CONSTRAINT uq_cell_detections_run_index CONSTRAINT uq_cell_detections_run_index UNIQUE (detection_run_id, cell_index);
ALTER TABLE public.cell_detections ADD CONSTRAINT cell_detections_automated_status_check CONSTRAINT cell_detections_automated_status_check CHECK (CAST(automated_status AS text) = CAST('candidate' AS text));
ALTER TABLE public.cell_detections ADD CONSTRAINT cell_detections_bbox_height_check CONSTRAINT cell_detections_bbox_height_check CHECK (bbox_height > 0);
ALTER TABLE public.cell_detections ADD CONSTRAINT cell_detections_bbox_width_check CONSTRAINT cell_detections_bbox_width_check CHECK (bbox_width > 0);
ALTER TABLE public.cell_detections ADD CONSTRAINT cell_detections_bbox_x_check CONSTRAINT cell_detections_bbox_x_check CHECK (bbox_x >= 0);
ALTER TABLE public.cell_detections ADD CONSTRAINT cell_detections_bbox_y_check CONSTRAINT cell_detections_bbox_y_check CHECK (bbox_y >= 0);
ALTER TABLE public.cell_detections ADD CONSTRAINT cell_detections_cell_code_check CONSTRAINT cell_detections_cell_code_check CHECK (CAST(cell_code AS text) ~ CAST('^CELL-[A-F0-9]{12}$' AS text));
ALTER TABLE public.cell_detections ADD CONSTRAINT cell_detections_cell_index_check CONSTRAINT cell_detections_cell_index_check CHECK (cell_index > 0);
ALTER TABLE public.cell_detections ADD CONSTRAINT cell_detections_coordinate_space_check CONSTRAINT cell_detections_coordinate_space_check CHECK (CAST(coordinate_space AS text) = CAST('original_image_pixels' AS text));
ALTER TABLE public.cell_detections ADD CONSTRAINT cell_detections_detector_score_check CONSTRAINT cell_detections_detector_score_check CHECK (detector_score IS NULL OR (detector_score >= CAST(0 AS double precision) AND detector_score <= CAST(1 AS double precision)));
ALTER TABLE public.cell_detections ADD CONSTRAINT fk_cell_detections_component CONSTRAINT fk_cell_detections_component FOREIGN KEY (connected_component_id, detection_run_id, analysis_run_image_id, microscopy_image_id) REFERENCES image_connected_components (id, detection_run_id, analysis_run_image_id, microscopy_image_id) ON DELETE RESTRICT;
ALTER TABLE public.cell_detections ADD CONSTRAINT fk_cell_detections_run_analysis CONSTRAINT fk_cell_detections_run_analysis FOREIGN KEY (detection_run_id, analysis_run_id) REFERENCES cell_detection_runs (id, analysis_run_id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_cell_detections_run_image`.
Auditoría: created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## cell_explanations

Ciclo de vida y artefactos Grad-CAM de una predicción celular; extensión reproducible xai_evidence.

Dominio: O. XAI. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| cell_prediction_id | uuid | NO |  |
| method | varchar(40) | NO |  |
| method_version | varchar(80) | NO |  |
| status | varchar(30) | NO |  |
| last_conv_layer | varchar(255) | YES |  |
| parameters_json | jsonb | NO |  |
| heatmap_storage_key | text | YES |  |
| heatmap_sha256 | char(64) | YES |  |
| heatmap_file_size_bytes | bigint | YES |  |
| overlay_storage_key | text | YES |  |
| overlay_sha256 | char(64) | YES |  |
| overlay_file_size_bytes | bigint | YES |  |
| width_px | integer | YES |  |
| height_px | integer | YES |  |
| started_at | timestamp with time zone | YES |  |
| completed_at | timestamp with time zone | YES |  |
| error_code | varchar(80) | YES |  |
| error_message | text | YES |  |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.cell_explanations ADD CONSTRAINT cell_explanations_pkey CONSTRAINT cell_explanations_pkey PRIMARY KEY (id);
ALTER TABLE public.cell_explanations ADD CONSTRAINT cell_explanations_cell_prediction_id_key CONSTRAINT cell_explanations_cell_prediction_id_key UNIQUE (cell_prediction_id);
ALTER TABLE public.cell_explanations ADD CONSTRAINT cell_explanations_method_check CONSTRAINT cell_explanations_method_check CHECK (CAST(method AS text) = CAST('gradcam' AS text));
ALTER TABLE public.cell_explanations ADD CONSTRAINT cell_explanations_method_version_check CONSTRAINT cell_explanations_method_version_check CHECK (btrim(CAST(method_version AS text)) <> CAST('' AS text));
ALTER TABLE public.cell_explanations ADD CONSTRAINT cell_explanations_parameters_json_check CONSTRAINT cell_explanations_parameters_json_check CHECK (jsonb_typeof(parameters_json) = CAST('object' AS text));
ALTER TABLE public.cell_explanations ADD CONSTRAINT cell_explanations_status_check CONSTRAINT cell_explanations_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('pending' AS varchar) AS text), CAST(CAST('generated' AS varchar) AS text), CAST(CAST('failed' AS varchar) AS text), CAST(CAST('unsupported' AS varchar) AS text), CAST(CAST('not_requested' AS varchar) AS text)]));
ALTER TABLE public.cell_explanations ADD CONSTRAINT ck_cell_explanation_dimensions CONSTRAINT ck_cell_explanation_dimensions CHECK ((width_px IS NULL OR width_px > 0) AND (height_px IS NULL OR height_px > 0) AND ((width_px IS NULL AND height_px IS NULL) OR (width_px IS NOT NULL AND height_px IS NOT NULL)));
ALTER TABLE public.cell_explanations ADD CONSTRAINT ck_cell_explanation_hashes CONSTRAINT ck_cell_explanation_hashes CHECK ((heatmap_sha256 IS NULL OR heatmap_sha256 ~ CAST('^[0-9a-f]{64}$' AS text)) AND (overlay_sha256 IS NULL OR overlay_sha256 ~ CAST('^[0-9a-f]{64}$' AS text)));
ALTER TABLE public.cell_explanations ADD CONSTRAINT ck_cell_explanation_heatmap_key CONSTRAINT ck_cell_explanation_heatmap_key CHECK (heatmap_storage_key IS NULL OR heatmap_storage_key ~ CAST('^cell-explanations/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gradcam_heatmap[.]png$' AS text));
ALTER TABLE public.cell_explanations ADD CONSTRAINT ck_cell_explanation_overlay_key CONSTRAINT ck_cell_explanation_overlay_key CHECK (overlay_storage_key IS NULL OR overlay_storage_key ~ CAST('^cell-explanations/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gradcam_overlay[.]png$' AS text));
ALTER TABLE public.cell_explanations ADD CONSTRAINT ck_cell_explanation_sizes CONSTRAINT ck_cell_explanation_sizes CHECK ((heatmap_file_size_bytes IS NULL OR heatmap_file_size_bytes > 0) AND (overlay_file_size_bytes IS NULL OR overlay_file_size_bytes > 0));
ALTER TABLE public.cell_explanations ADD CONSTRAINT ck_cell_explanation_state CONSTRAINT ck_cell_explanation_state CHECK ((CAST(status AS text) = CAST('not_requested' AS text) AND started_at IS NULL AND completed_at IS NULL AND error_code IS NULL AND error_message IS NULL AND heatmap_storage_key IS NULL AND heatmap_sha256 IS NULL AND heatmap_file_size_bytes IS NULL AND overlay_storage_key IS NULL AND overlay_sha256 IS NULL AND overlay_file_size_bytes IS NULL AND width_px IS NULL AND height_px IS NULL) OR (CAST(status AS text) = CAST('pending' AS text) AND started_at IS NOT NULL AND completed_at IS NULL AND error_code IS NULL AND error_message IS NULL AND heatmap_storage_key IS NULL AND heatmap_sha256 IS NULL AND heatmap_file_size_bytes IS NULL AND overlay_storage_key IS NULL AND overlay_sha256 IS NULL AND overlay_file_size_bytes IS NULL AND width_px IS NULL AND height_px IS NULL) OR (CAST(status AS text) = CAST('generated' AS text) AND started_at IS NOT NULL AND completed_at IS NOT NULL AND last_conv_layer IS NOT NULL AND btrim(CAST(last_conv_layer AS text)) <> CAST('' AS text) AND heatmap_storage_key IS NOT NULL AND heatmap_sha256 IS NOT NULL AND heatmap_file_size_bytes IS NOT NULL AND overlay_storage_key IS NOT NULL AND overlay_sha256 IS NOT NULL AND overlay_file_size_bytes IS NOT NULL AND width_px IS NOT NULL AND height_px IS NOT NULL AND error_code IS NULL AND error_message IS NULL) OR (CAST(status AS text) = ANY(ARRAY[CAST(CAST('failed' AS varchar) AS text), CAST(CAST('unsupported' AS varchar) AS text)]) AND started_at IS NOT NULL AND completed_at IS NOT NULL AND error_code IS NOT NULL AND btrim(CAST(error_code AS text)) <> CAST('' AS text) AND heatmap_storage_key IS NULL AND heatmap_sha256 IS NULL AND heatmap_file_size_bytes IS NULL AND overlay_storage_key IS NULL AND overlay_sha256 IS NULL AND overlay_file_size_bytes IS NULL AND width_px IS NULL AND height_px IS NULL));
ALTER TABLE public.cell_explanations ADD CONSTRAINT ck_cell_explanation_time_order CONSTRAINT ck_cell_explanation_time_order CHECK ((started_at IS NULL OR started_at >= created_at) AND (completed_at IS NULL OR completed_at >= started_at));
ALTER TABLE public.cell_explanations ADD CONSTRAINT cell_explanations_cell_prediction_id_fkey CONSTRAINT cell_explanations_cell_prediction_id_fkey FOREIGN KEY (cell_prediction_id) REFERENCES cell_predictions (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_cell_explanations_status_created`.
Auditoría: started_at, completed_at, created_at.
JSONB: parameters_json. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: heatmap_sha256, overlay_sha256.

## cell_predictions

Salida IA por input congelado, probabilidades, umbral, preprocessing y estado; no diagnóstico humano.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| classification_run_id | uuid | NO |  |
| classification_input_id | uuid | NO |  |
| cell_detection_id | uuid | NO |  |
| crop_id | uuid | NO |  |
| prediction_status | varchar(20) | NO |  |
| raw_output | jsonb | NO |  |
| probability_parasitized | double precision | YES |  |
| probability_uninfected | double precision | YES |  |
| predicted_label | varchar(20) | YES |  |
| predicted_class_index | smallint | YES |  |
| positive_label | varchar(20) | NO |  |
| positive_class_index | smallint | NO |  |
| threshold_used | double precision | NO |  |
| threshold_source | varchar(120) | NO |  |
| decision_margin | double precision | YES |  |
| near_threshold | boolean | NO | FALSE |
| preprocessing_snapshot | jsonb | NO |  |
| inference_duration_ms | double precision | YES |  |
| error_code | varchar(80) | YES |  |
| error_message | text | YES |  |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.cell_predictions ADD CONSTRAINT cell_predictions_pkey CONSTRAINT cell_predictions_pkey PRIMARY KEY (id);
ALTER TABLE public.cell_predictions ADD CONSTRAINT cell_predictions_classification_input_id_key CONSTRAINT cell_predictions_classification_input_id_key UNIQUE (classification_input_id);
ALTER TABLE public.cell_predictions ADD CONSTRAINT uq_cell_predictions_run_identity CONSTRAINT uq_cell_predictions_run_identity UNIQUE (id, classification_run_id);
ALTER TABLE public.cell_predictions ADD CONSTRAINT cell_predictions_prediction_status_check CONSTRAINT cell_predictions_prediction_status_check CHECK (CAST(prediction_status AS text) = ANY(ARRAY[CAST(CAST('completed' AS varchar) AS text), CAST(CAST('failed' AS varchar) AS text)]));
ALTER TABLE public.cell_predictions ADD CONSTRAINT cell_predictions_preprocessing_snapshot_check CONSTRAINT cell_predictions_preprocessing_snapshot_check CHECK (jsonb_typeof(preprocessing_snapshot) = CAST('object' AS text));
ALTER TABLE public.cell_predictions ADD CONSTRAINT cell_predictions_raw_output_check CONSTRAINT cell_predictions_raw_output_check CHECK (jsonb_typeof(raw_output) = ANY(ARRAY[CAST('object' AS text), CAST('array' AS text)]));
ALTER TABLE public.cell_predictions ADD CONSTRAINT cell_predictions_threshold_source_check CONSTRAINT cell_predictions_threshold_source_check CHECK (btrim(CAST(threshold_source AS text)) <> CAST('' AS text));
ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_class_index CONSTRAINT ck_cell_prediction_class_index CHECK (predicted_class_index IS NULL OR predicted_class_index = ANY(ARRAY[0, 1]));
ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_completed_payload CONSTRAINT ck_cell_prediction_completed_payload CHECK ((CAST(prediction_status AS text) = CAST('completed' AS text) AND probability_parasitized IS NOT NULL AND probability_uninfected IS NOT NULL AND CAST(predicted_label AS text) = ANY(ARRAY[CAST(CAST('parasitized' AS varchar) AS text), CAST(CAST('uninfected' AS varchar) AS text)]) AND predicted_class_index = ANY(ARRAY[0, 1]) AND decision_margin IS NOT NULL AND error_code IS NULL AND error_message IS NULL) OR (CAST(prediction_status AS text) = CAST('failed' AS text) AND probability_parasitized IS NULL AND probability_uninfected IS NULL AND predicted_label IS NULL AND predicted_class_index IS NULL AND decision_margin IS NULL AND NOT near_threshold AND error_code IS NOT NULL AND btrim(CAST(error_code AS text)) <> CAST('' AS text)));
ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_decision_margin CONSTRAINT ck_cell_prediction_decision_margin CHECK (decision_margin IS NULL OR probability_parasitized IS NULL OR abs(decision_margin - abs(probability_parasitized - threshold_used)) <= CAST(0.000000001 AS double precision));
ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_duration CONSTRAINT ck_cell_prediction_duration CHECK (inference_duration_ms IS NULL OR (inference_duration_ms >= CAST(0 AS double precision) AND inference_duration_ms < CAST('Infinity' AS double precision)));
ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_label_index CONSTRAINT ck_cell_prediction_label_index CHECK (CAST(prediction_status AS text) <> CAST('completed' AS text) OR (predicted_class_index = 1 AND CAST(predicted_label AS text) = CAST('parasitized' AS text) AND probability_parasitized >= threshold_used) OR (predicted_class_index = 0 AND CAST(predicted_label AS text) = CAST('uninfected' AS text) AND probability_parasitized < threshold_used));
ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_margin CONSTRAINT ck_cell_prediction_margin CHECK (decision_margin IS NULL OR (decision_margin >= CAST(0 AS double precision) AND decision_margin < CAST('Infinity' AS double precision)));
ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_positive_class CONSTRAINT ck_cell_prediction_positive_class CHECK (CAST(positive_label AS text) = CAST('parasitized' AS text) AND positive_class_index = 1);
ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_probability_parasitized CONSTRAINT ck_cell_prediction_probability_parasitized CHECK (probability_parasitized IS NULL OR (probability_parasitized >= CAST(0 AS double precision) AND probability_parasitized <= CAST(1 AS double precision) AND probability_parasitized < CAST('Infinity' AS double precision)));
ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_probability_sum CONSTRAINT ck_cell_prediction_probability_sum CHECK (probability_parasitized IS NULL OR probability_uninfected IS NULL OR abs((probability_parasitized + probability_uninfected) - CAST(1.0 AS double precision)) <= CAST(0.000000001 AS double precision));
ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_probability_uninfected CONSTRAINT ck_cell_prediction_probability_uninfected CHECK (probability_uninfected IS NULL OR (probability_uninfected >= CAST(0 AS double precision) AND probability_uninfected <= CAST(1 AS double precision) AND probability_uninfected < CAST('Infinity' AS double precision)));
ALTER TABLE public.cell_predictions ADD CONSTRAINT ck_cell_prediction_threshold CONSTRAINT ck_cell_prediction_threshold CHECK (threshold_used >= CAST(0 AS double precision) AND threshold_used <= CAST(1 AS double precision) AND threshold_used < CAST('Infinity' AS double precision));
ALTER TABLE public.cell_predictions ADD CONSTRAINT fk_cell_prediction_input_owner CONSTRAINT fk_cell_prediction_input_owner FOREIGN KEY (classification_input_id, classification_run_id, cell_detection_id, crop_id) REFERENCES cell_classification_inputs (id, classification_run_id, cell_detection_id, crop_id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_cell_predictions_crop`, `ix_cell_predictions_detection`, `ix_cell_predictions_run_label`, `ix_cell_predictions_run_near_threshold`, `ix_cell_predictions_run_status`.
Auditoría: created_at.
JSONB: raw_output, preprocessing_snapshot. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## clinical_identities

Identidad científica de paciente usada para agrupar el split; protegida.

Dominio: B. Dataset. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| dataset_id | uuid | NO |  |
| identity_type | text | NO |  |
| source_identifier | text | NO |  |
| status | text | NO |  |
| metadata | jsonb | NO | CAST('{}' AS jsonb) |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.clinical_identities ADD CONSTRAINT clinical_identities_pkey CONSTRAINT clinical_identities_pkey PRIMARY KEY (id);
ALTER TABLE public.clinical_identities ADD CONSTRAINT uq_clinical_identities_source CONSTRAINT uq_clinical_identities_source UNIQUE (dataset_id, identity_type, source_identifier);
ALTER TABLE public.clinical_identities ADD CONSTRAINT chk_clinical_identities_metadata_object CONSTRAINT chk_clinical_identities_metadata_object CHECK (jsonb_typeof(metadata) = CAST('object' AS text));
ALTER TABLE public.clinical_identities ADD CONSTRAINT chk_clinical_identities_status CONSTRAINT chk_clinical_identities_status CHECK (status = ANY(ARRAY[CAST('VERIFIED' AS text), CAST('UNRESOLVED' AS text), CAST('CONFLICT' AS text)]));
ALTER TABLE public.clinical_identities ADD CONSTRAINT chk_clinical_identities_type CONSTRAINT chk_clinical_identities_type CHECK (identity_type = CAST('PATIENT' AS text));
ALTER TABLE public.clinical_identities ADD CONSTRAINT clinical_identities_dataset_id_fkey CONSTRAINT clinical_identities_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE RESTRICT;
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at, updated_at.
JSONB: metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: source_identifier.

## dataset_materialization_activations

Historial de activación de una materialización científica sin alterar assignments.

Dominio: B. Dataset. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| dataset_version_id | uuid | NO |  |
| materialization_id | uuid | NO |  |
| dataset_family | text | NO |  |
| activated_at | timestamp with time zone | NO | now() |
| deactivated_at | timestamp with time zone | YES |  |
| metadata | jsonb | NO | CAST('{}' AS jsonb) |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.dataset_materialization_activations ADD CONSTRAINT dataset_materialization_activations_pkey CONSTRAINT dataset_materialization_activations_pkey PRIMARY KEY (id);
ALTER TABLE public.dataset_materialization_activations ADD CONSTRAINT chk_dataset_materialization_activations_interval CONSTRAINT chk_dataset_materialization_activations_interval CHECK (deactivated_at IS NULL OR deactivated_at >= activated_at);
ALTER TABLE public.dataset_materialization_activations ADD CONSTRAINT chk_dataset_materialization_activations_metadata_object CONSTRAINT chk_dataset_materialization_activations_metadata_object CHECK (jsonb_typeof(metadata) = CAST('object' AS text));
ALTER TABLE public.dataset_materialization_activations ADD CONSTRAINT dataset_materialization_activations_dataset_version_id_fkey CONSTRAINT dataset_materialization_activations_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;
ALTER TABLE public.dataset_materialization_activations ADD CONSTRAINT dataset_materialization_activations_materialization_id_fkey CONSTRAINT dataset_materialization_activations_materialization_id_fkey FOREIGN KEY (materialization_id) REFERENCES dataset_materializations (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_dataset_materialization_activations_dataset_version_id`, `ix_dataset_materialization_activations_materialization_id`, `uq_dataset_materialization_activations_current_family`.
Auditoría: activated_at, deactivated_at.
JSONB: metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## dataset_materializations

Materialización con ruta/estado/fingerprint y validación; protegida.

Dominio: B. Dataset. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| dataset_version_id | uuid | NO |  |
| attempt_number | integer | NO |  |
| status | text | NO | CAST('NOT_MATERIALIZED' AS text) |
| reconciliation_status | text | NO | CAST('PENDING' AS text) |
| relative_root | text | NO |  |
| record_count | bigint | NO | 0 |
| manifest_metadata | jsonb | NO | CAST('{}' AS jsonb) |
| started_at | timestamp with time zone | YES |  |
| completed_at | timestamp with time zone | YES |  |
| failure_reason | text | YES |  |
| metadata | jsonb | NO | CAST('{}' AS jsonb) |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.dataset_materializations ADD CONSTRAINT dataset_materializations_pkey CONSTRAINT dataset_materializations_pkey PRIMARY KEY (id);
ALTER TABLE public.dataset_materializations ADD CONSTRAINT uq_dataset_materializations_attempt CONSTRAINT uq_dataset_materializations_attempt UNIQUE (dataset_version_id, attempt_number);
ALTER TABLE public.dataset_materializations ADD CONSTRAINT chk_dataset_materializations_attempt CONSTRAINT chk_dataset_materializations_attempt CHECK (attempt_number > 0);
ALTER TABLE public.dataset_materializations ADD CONSTRAINT chk_dataset_materializations_manifest_object CONSTRAINT chk_dataset_materializations_manifest_object CHECK (jsonb_typeof(manifest_metadata) = CAST('object' AS text));
ALTER TABLE public.dataset_materializations ADD CONSTRAINT chk_dataset_materializations_metadata_object CONSTRAINT chk_dataset_materializations_metadata_object CHECK (jsonb_typeof(metadata) = CAST('object' AS text));
ALTER TABLE public.dataset_materializations ADD CONSTRAINT chk_dataset_materializations_reconciliation CONSTRAINT chk_dataset_materializations_reconciliation CHECK (reconciliation_status = ANY(ARRAY[CAST('PENDING' AS text), CAST('PASS' AS text), CAST('FAIL' AS text)]));
ALTER TABLE public.dataset_materializations ADD CONSTRAINT chk_dataset_materializations_record_count CONSTRAINT chk_dataset_materializations_record_count CHECK (record_count >= 0);
ALTER TABLE public.dataset_materializations ADD CONSTRAINT chk_dataset_materializations_relative_root CONSTRAINT chk_dataset_materializations_relative_root CHECK (relative_root <> CAST('' AS text) AND relative_root !~ CAST('^/' AS text));
ALTER TABLE public.dataset_materializations ADD CONSTRAINT chk_dataset_materializations_status CONSTRAINT chk_dataset_materializations_status CHECK (status = ANY(ARRAY[CAST('NOT_MATERIALIZED' AS text), CAST('MATERIALIZING' AS text), CAST('READY' AS text), CAST('FAILED' AS text)]));
ALTER TABLE public.dataset_materializations ADD CONSTRAINT dataset_materializations_dataset_version_id_fkey CONSTRAINT dataset_materializations_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_dataset_materializations_dataset_version_id`.
Auditoría: started_at, completed_at, created_at.
JSONB: manifest_metadata, metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## dataset_source_records

Registro fuente de cada imagen, identidad, etiqueta y hashes verificados.

Dominio: B. Dataset. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| dataset_id | uuid | NO |  |
| clinical_identity_id | uuid | YES |  |
| source_record_key | text | NO |  |
| tfds_index | bigint | YES |  |
| source_filename | text | YES |  |
| class_index | integer | NO |  |
| class_name | text | NO |  |
| original_label | integer | YES |  |
| project_label | integer | YES |  |
| relative_source_key | text | YES |  |
| source_file_sha256 | text | YES |  |
| decoded_pixel_sha256 | text | YES |  |
| image_width | integer | YES |  |
| image_height | integer | YES |  |
| file_size_bytes | bigint | YES |  |
| identity_status | text | NO |  |
| metadata | jsonb | NO | CAST('{}' AS jsonb) |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.dataset_source_records ADD CONSTRAINT dataset_source_records_pkey CONSTRAINT dataset_source_records_pkey PRIMARY KEY (id);
ALTER TABLE public.dataset_source_records ADD CONSTRAINT uq_dataset_source_records_key CONSTRAINT uq_dataset_source_records_key UNIQUE (dataset_id, source_record_key);
ALTER TABLE public.dataset_source_records ADD CONSTRAINT chk_dataset_source_records_dimensions CONSTRAINT chk_dataset_source_records_dimensions CHECK ((image_width IS NULL OR image_width > 0) AND (image_height IS NULL OR image_height > 0) AND (file_size_bytes IS NULL OR file_size_bytes >= 0));
ALTER TABLE public.dataset_source_records ADD CONSTRAINT chk_dataset_source_records_identity_status CONSTRAINT chk_dataset_source_records_identity_status CHECK (identity_status = ANY(ARRAY[CAST('VERIFIED' AS text), CAST('UNRESOLVED' AS text), CAST('CONFLICT' AS text)]));
ALTER TABLE public.dataset_source_records ADD CONSTRAINT chk_dataset_source_records_metadata_object CONSTRAINT chk_dataset_source_records_metadata_object CHECK (jsonb_typeof(metadata) = CAST('object' AS text));
ALTER TABLE public.dataset_source_records ADD CONSTRAINT chk_dataset_source_records_pixel_sha256 CONSTRAINT chk_dataset_source_records_pixel_sha256 CHECK (decoded_pixel_sha256 IS NULL OR decoded_pixel_sha256 ~ CAST('^[0-9a-fA-F]{64}$' AS text));
ALTER TABLE public.dataset_source_records ADD CONSTRAINT chk_dataset_source_records_source_sha256 CONSTRAINT chk_dataset_source_records_source_sha256 CHECK (source_file_sha256 IS NULL OR source_file_sha256 ~ CAST('^[0-9a-fA-F]{64}$' AS text));
ALTER TABLE public.dataset_source_records ADD CONSTRAINT dataset_source_records_clinical_identity_id_fkey CONSTRAINT dataset_source_records_clinical_identity_id_fkey FOREIGN KEY (clinical_identity_id) REFERENCES clinical_identities (id) ON DELETE RESTRICT;
ALTER TABLE public.dataset_source_records ADD CONSTRAINT dataset_source_records_dataset_id_fkey CONSTRAINT dataset_source_records_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_dataset_source_records_clinical_identity_id`, `ix_dataset_source_records_dataset_id`, `ix_dataset_source_records_decoded_pixel_sha256`, `ix_dataset_source_records_source_file_sha256`.
Auditoría: created_at, updated_at.
JSONB: metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: source_record_key, source_filename, relative_source_key, source_file_sha256, decoded_pixel_sha256.

## dataset_split_assignments

Asignación científica versionada por fuente/paciente; autoridad del universo oficial.

Dominio: B. Dataset. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| dataset_version_id | uuid | NO |  |
| source_record_id | uuid | NO |  |
| clinical_identity_id | uuid | NO |  |
| split_name | text | NO |  |
| class_index | integer | NO |  |
| class_name | text | NO |  |
| metadata | jsonb | NO | CAST('{}' AS jsonb) |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.dataset_split_assignments ADD CONSTRAINT dataset_split_assignments_pkey CONSTRAINT dataset_split_assignments_pkey PRIMARY KEY (id);
ALTER TABLE public.dataset_split_assignments ADD CONSTRAINT uq_dataset_split_assignments_record CONSTRAINT uq_dataset_split_assignments_record UNIQUE (dataset_version_id, source_record_id);
ALTER TABLE public.dataset_split_assignments ADD CONSTRAINT chk_dataset_split_assignments_metadata_object CONSTRAINT chk_dataset_split_assignments_metadata_object CHECK (jsonb_typeof(metadata) = CAST('object' AS text));
ALTER TABLE public.dataset_split_assignments ADD CONSTRAINT chk_dataset_split_assignments_split CONSTRAINT chk_dataset_split_assignments_split CHECK (split_name = ANY(ARRAY[CAST('train' AS text), CAST('val' AS text), CAST('test' AS text), CAST('external_validation' AS text)]));
ALTER TABLE public.dataset_split_assignments ADD CONSTRAINT dataset_split_assignments_clinical_identity_id_fkey CONSTRAINT dataset_split_assignments_clinical_identity_id_fkey FOREIGN KEY (clinical_identity_id) REFERENCES clinical_identities (id) ON DELETE RESTRICT;
ALTER TABLE public.dataset_split_assignments ADD CONSTRAINT dataset_split_assignments_dataset_version_id_fkey CONSTRAINT dataset_split_assignments_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;
ALTER TABLE public.dataset_split_assignments ADD CONSTRAINT dataset_split_assignments_source_record_id_fkey CONSTRAINT dataset_split_assignments_source_record_id_fkey FOREIGN KEY (source_record_id) REFERENCES dataset_source_records (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_dataset_split_assignments_clinical_identity_id`, `ix_dataset_split_assignments_dataset_version_id`.
Auditoría: created_at.
JSONB: metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: source_record_id.

## dataset_split_images

Inventario físico de imágenes por raíz; dos representaciones, no doble población.

Dominio: B. Dataset. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| image_id | uuid | NO | pg_catalog.gen_random_uuid() |
| dataset_id | uuid | YES |  |
| dataset_name | text | NO |  |
| dataset_source | text | NO |  |
| dataset_dir | text | NO |  |
| split_name | text | NO |  |
| class_index | integer | NO |  |
| class_name | text | NO |  |
| relative_path | text | NO |  |
| absolute_path | text | YES |  |
| filename | text | NO |  |
| original_tfds_label | integer | YES |  |
| project_label | integer | NO |  |
| label_mapping_version | text | NO |  |
| image_width | integer | YES |  |
| image_height | integer | YES |  |
| file_size_bytes | bigint | YES |  |
| checksum_sha256 | text | YES |  |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |
| metadata | jsonb | NO | CAST('{}' AS jsonb) |
| dataset_version_id | uuid | YES |  |
| dataset_materialization_id | uuid | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.dataset_split_images ADD CONSTRAINT dataset_split_images_pkey CONSTRAINT dataset_split_images_pkey PRIMARY KEY (image_id);
ALTER TABLE public.dataset_split_images ADD CONSTRAINT uq_dataset_split_images_path CONSTRAINT uq_dataset_split_images_path UNIQUE (dataset_dir, relative_path);
ALTER TABLE public.dataset_split_images ADD CONSTRAINT chk_dataset_split_images_class_index CONSTRAINT chk_dataset_split_images_class_index CHECK (class_index = ANY(ARRAY[0, 1]));
ALTER TABLE public.dataset_split_images ADD CONSTRAINT chk_dataset_split_images_class_name CONSTRAINT chk_dataset_split_images_class_name CHECK (class_name = ANY(ARRAY[CAST('uninfected' AS text), CAST('parasitized' AS text)]));
ALTER TABLE public.dataset_split_images ADD CONSTRAINT chk_dataset_split_images_split CONSTRAINT chk_dataset_split_images_split CHECK (split_name = ANY(ARRAY[CAST('train' AS text), CAST('val' AS text), CAST('validation' AS text), CAST('test' AS text)]));
ALTER TABLE public.dataset_split_images ADD CONSTRAINT dataset_split_images_dataset_id_fkey CONSTRAINT dataset_split_images_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE RESTRICT;
ALTER TABLE public.dataset_split_images ADD CONSTRAINT dataset_split_images_dataset_materialization_id_fkey CONSTRAINT dataset_split_images_dataset_materialization_id_fkey FOREIGN KEY (dataset_materialization_id) REFERENCES dataset_materializations (id) ON DELETE RESTRICT;
ALTER TABLE public.dataset_split_images ADD CONSTRAINT dataset_split_images_dataset_version_id_fkey CONSTRAINT dataset_split_images_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;
```

Índices explícitos: `idx_dataset_split_images_class`, `idx_dataset_split_images_dataset_dir`, `idx_dataset_split_images_dataset_id`, `idx_dataset_split_images_relative_path`, `idx_dataset_split_images_split`, `ix_dataset_split_images_dataset_materialization_id`, `ix_dataset_split_images_dataset_version_id`.
Auditoría: created_at, updated_at.
JSONB: metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: checksum_sha256.

## dataset_split_statistics

Estadísticas congeladas del split científico por versión.

Dominio: B. Dataset. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| dataset_version_id | uuid | NO |  |
| scope | text | NO |  |
| metric_name | text | NO |  |
| numeric_value | numeric | YES |  |
| text_value | text | YES |  |
| details_json | jsonb | YES |  |
| computed_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.dataset_split_statistics ADD CONSTRAINT dataset_split_statistics_pkey CONSTRAINT dataset_split_statistics_pkey PRIMARY KEY (id);
ALTER TABLE public.dataset_split_statistics ADD CONSTRAINT chk_dataset_split_statistics_details_object CONSTRAINT chk_dataset_split_statistics_details_object CHECK (details_json IS NULL OR jsonb_typeof(details_json) = CAST('object' AS text));
ALTER TABLE public.dataset_split_statistics ADD CONSTRAINT chk_dataset_split_statistics_value CONSTRAINT chk_dataset_split_statistics_value CHECK (numeric_value IS NOT NULL OR text_value IS NOT NULL OR details_json IS NOT NULL);
ALTER TABLE public.dataset_split_statistics ADD CONSTRAINT dataset_split_statistics_dataset_version_id_fkey CONSTRAINT dataset_split_statistics_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_dataset_split_statistics_version_metric`.
Auditoría: computed_at.
JSONB: details_json. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## dataset_split_validation_checks

Evidencia de validaciones PASS/FAIL del split por versión.

Dominio: B. Dataset. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| dataset_version_id | uuid | NO |  |
| check_name | text | NO |  |
| status | text | NO |  |
| observed_value | text | YES |  |
| expected_value | text | YES |  |
| details_json | jsonb | NO | CAST('{}' AS jsonb) |
| blocking_for_validation | boolean | NO | FALSE |
| blocking_for_freeze | boolean | NO | FALSE |
| executed_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.dataset_split_validation_checks ADD CONSTRAINT dataset_split_validation_checks_pkey CONSTRAINT dataset_split_validation_checks_pkey PRIMARY KEY (id);
ALTER TABLE public.dataset_split_validation_checks ADD CONSTRAINT chk_dataset_split_validation_checks_details_object CONSTRAINT chk_dataset_split_validation_checks_details_object CHECK (jsonb_typeof(details_json) = CAST('object' AS text));
ALTER TABLE public.dataset_split_validation_checks ADD CONSTRAINT chk_dataset_split_validation_checks_status CONSTRAINT chk_dataset_split_validation_checks_status CHECK (status = ANY(ARRAY[CAST('PASS' AS text), CAST('FAIL' AS text), CAST('WARNING' AS text)]));
ALTER TABLE public.dataset_split_validation_checks ADD CONSTRAINT dataset_split_validation_checks_dataset_version_id_fkey CONSTRAINT dataset_split_validation_checks_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_dataset_split_validation_checks_version_name`.
Auditoría: executed_at.
JSONB: details_json. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## dataset_splits

Distribuciones históricas por dataset requeridas por contratos de descubrimiento/features.

Dominio: B. Dataset. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| dataset_id | uuid | YES |  |
| split_name | text | NO |  |
| num_samples | integer | YES |  |
| class_distribution | jsonb | YES | CAST('{}' AS jsonb) |
| split_strategy | text | YES |  |
| random_seed | integer | YES |  |
| created_at | timestamp with time zone | YES | now() |
| metadata | jsonb | YES | CAST('{}' AS jsonb) |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.dataset_splits ADD CONSTRAINT dataset_splits_pkey CONSTRAINT dataset_splits_pkey PRIMARY KEY (id);
ALTER TABLE public.dataset_splits ADD CONSTRAINT dataset_splits_dataset_id_fkey CONSTRAINT dataset_splits_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE RESTRICT;
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: class_distribution, metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## dataset_version_sources

Fuentes vinculadas a la versión científica congelada.

Dominio: B. Dataset. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| dataset_version_id | uuid | NO |  |
| dataset_id | uuid | NO |  |
| role | text | NO |  |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.dataset_version_sources ADD CONSTRAINT dataset_version_sources_pkey CONSTRAINT dataset_version_sources_pkey PRIMARY KEY (dataset_version_id, dataset_id, role);
ALTER TABLE public.dataset_version_sources ADD CONSTRAINT chk_dataset_version_sources_role CONSTRAINT chk_dataset_version_sources_role CHECK (role = ANY(ARRAY[CAST('PRIMARY' AS text), CAST('EXTERNAL_VALIDATION' AS text), CAST('AUXILIARY' AS text)]));
ALTER TABLE public.dataset_version_sources ADD CONSTRAINT dataset_version_sources_dataset_id_fkey CONSTRAINT dataset_version_sources_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE RESTRICT;
ALTER TABLE public.dataset_version_sources ADD CONSTRAINT dataset_version_sources_dataset_version_id_fkey CONSTRAINT dataset_version_sources_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_dataset_version_sources_dataset_id`.
Auditoría: created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## dataset_versions

Versión FROZEN, protocolo/semilla/identidad científica del dataset.

Dominio: B. Dataset. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| name | text | NO |  |
| semantic_version | text | NO |  |
| status | text | NO | CAST('DRAFT' AS text) |
| grouping_strategy | text | NO |  |
| grouping_field | text | NO |  |
| stratification_strategy | text | NO |  |
| split_algorithm | text | NO |  |
| split_algorithm_version | text | NO |  |
| random_seed | integer | NO |  |
| target_train_ratio | numeric(8, 7) | NO |  |
| target_val_ratio | numeric(8, 7) | NO |  |
| target_test_ratio | numeric(8, 7) | NO |  |
| positive_class | text | NO |  |
| class_mapping | jsonb | NO | CAST('{}' AS jsonb) |
| source_record_count | bigint | NO | 0 |
| methodology_json | jsonb | NO | CAST('{}' AS jsonb) |
| created_at | timestamp with time zone | NO | now() |
| generated_at | timestamp with time zone | YES |  |
| validated_at | timestamp with time zone | YES |  |
| frozen_at | timestamp with time zone | YES |  |
| archived_at | timestamp with time zone | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.dataset_versions ADD CONSTRAINT dataset_versions_pkey CONSTRAINT dataset_versions_pkey PRIMARY KEY (id);
ALTER TABLE public.dataset_versions ADD CONSTRAINT uq_dataset_versions_name_semver CONSTRAINT uq_dataset_versions_name_semver UNIQUE (name, semantic_version);
ALTER TABLE public.dataset_versions ADD CONSTRAINT chk_dataset_versions_class_mapping_object CONSTRAINT chk_dataset_versions_class_mapping_object CHECK (jsonb_typeof(class_mapping) = CAST('object' AS text));
ALTER TABLE public.dataset_versions ADD CONSTRAINT chk_dataset_versions_methodology_object CONSTRAINT chk_dataset_versions_methodology_object CHECK (jsonb_typeof(methodology_json) = CAST('object' AS text));
ALTER TABLE public.dataset_versions ADD CONSTRAINT chk_dataset_versions_ratio_sum CONSTRAINT chk_dataset_versions_ratio_sum CHECK ((target_train_ratio + target_val_ratio + target_test_ratio) = 1.0);
ALTER TABLE public.dataset_versions ADD CONSTRAINT chk_dataset_versions_source_count CONSTRAINT chk_dataset_versions_source_count CHECK (source_record_count >= 0);
ALTER TABLE public.dataset_versions ADD CONSTRAINT chk_dataset_versions_status CONSTRAINT chk_dataset_versions_status CHECK (status = ANY(ARRAY[CAST('DRAFT' AS text), CAST('GENERATED' AS text), CAST('VALIDATED' AS text), CAST('FROZEN' AS text), CAST('ARCHIVED' AS text)]));
ALTER TABLE public.dataset_versions ADD CONSTRAINT chk_dataset_versions_test_ratio CONSTRAINT chk_dataset_versions_test_ratio CHECK (target_test_ratio >= CAST(0 AS numeric) AND target_test_ratio <= CAST(1 AS numeric));
ALTER TABLE public.dataset_versions ADD CONSTRAINT chk_dataset_versions_train_ratio CONSTRAINT chk_dataset_versions_train_ratio CHECK (target_train_ratio >= CAST(0 AS numeric) AND target_train_ratio <= CAST(1 AS numeric));
ALTER TABLE public.dataset_versions ADD CONSTRAINT chk_dataset_versions_val_ratio CONSTRAINT chk_dataset_versions_val_ratio CHECK (target_val_ratio >= CAST(0 AS numeric) AND target_val_ratio <= CAST(1 AS numeric));
```

Índices explícitos: `ix_dataset_versions_status`.
Auditoría: created_at, generated_at, validated_at, frozen_at, archived_at.
JSONB: class_mapping, methodology_json. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: source_record_count.

## datasets

Catálogo de datasets y origen; no confundir ID con dataset_version_id.

Dominio: B. Dataset. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| name | text | NO |  |
| source | text | YES |  |
| version | text | YES |  |
| description | text | YES |  |
| total_images | integer | YES |  |
| num_classes | integer | YES |  |
| class_names | text[] | YES |  |
| class_distribution | jsonb | YES | CAST('{}' AS jsonb) |
| license | text | YES |  |
| url | text | YES |  |
| local_path | text | YES |  |
| checksum | text | YES |  |
| created_at | timestamp with time zone | YES | now() |
| metadata | jsonb | YES | CAST('{}' AS jsonb) |
| provider | text | YES |  |
| source_type | text | YES |  |
| source_reference | text | YES |  |
| source_version | text | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.datasets ADD CONSTRAINT datasets_pkey CONSTRAINT datasets_pkey PRIMARY KEY (id);
```

Índices explícitos: `idx_datasets_metadata_gin`.
Auditoría: created_at.
JSONB: class_distribution, metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: source_type, source_reference, source_version.

## deployed_model_versions

Versión desplegada, ámbito y snapshots de umbral/preprocessing/contrato de entrada.

Dominio: P. Publicación / deployment. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| model_version_id | uuid | NO |  |
| checkpoint_artifact_id | uuid | NO |  |
| threshold_calibration_id | uuid | YES |  |
| deployment_name | text | NO |  |
| environment | text | NO |  |
| alias | text | NO |  |
| artifact_sha256 | text | NO |  |
| artifact_size_bytes | bigint | YES |  |
| threshold_value | numeric | NO |  |
| threshold_profile_snapshot | jsonb | NO | CAST('{}' AS jsonb) |
| preprocessing_profile_snapshot | jsonb | NO | CAST('{}' AS jsonb) |
| image_quality_policy_snapshot | jsonb | NO | CAST('{}' AS jsonb) |
| label_mapping_snapshot | jsonb | NO | CAST('{}' AS jsonb) |
| positive_label | text | NO | CAST('parasitized' AS text) |
| score_name | text | NO | CAST('probability_parasitized' AS text) |
| status | text | NO | CAST('pending' AS text) |
| supersedes_deployment_id | uuid | YES |  |
| rollback_of_deployment_id | uuid | YES |  |
| deployed_at | timestamp with time zone | YES |  |
| retired_at | timestamp with time zone | YES |  |
| deployed_by | text | YES |  |
| retired_by | text | YES |  |
| deployment_reason | text | YES |  |
| retirement_reason | text | YES |  |
| created_at | timestamp with time zone | NO | now() |
| metadata | jsonb | NO | CAST('{}' AS jsonb) |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.deployed_model_versions ADD CONSTRAINT deployed_model_versions_pkey CONSTRAINT deployed_model_versions_pkey PRIMARY KEY (id);
ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_active_mapping CONSTRAINT chk_deployed_model_versions_active_mapping CHECK (status <> CAST('active' AS text) OR label_mapping_snapshot @> CAST('{"0": "uninfected", "1": "parasitized"}' AS jsonb));
ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_active_timestamps CONSTRAINT chk_deployed_model_versions_active_timestamps CHECK (status <> CAST('active' AS text) OR (deployed_at IS NOT NULL AND retired_at IS NULL AND NULLIF(btrim(deployed_by), CAST('' AS text)) IS NOT NULL));
ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_artifact_size CONSTRAINT chk_deployed_model_versions_artifact_size CHECK (artifact_size_bytes IS NULL OR artifact_size_bytes >= 0);
ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_clinical_convention CONSTRAINT chk_deployed_model_versions_clinical_convention CHECK (positive_label = CAST('parasitized' AS text) AND score_name = CAST('probability_parasitized' AS text));
ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_distinct_history CONSTRAINT chk_deployed_model_versions_distinct_history CHECK ((supersedes_deployment_id IS NULL OR supersedes_deployment_id <> id) AND (rollback_of_deployment_id IS NULL OR rollback_of_deployment_id <> id));
ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_names CONSTRAINT chk_deployed_model_versions_names CHECK (btrim(deployment_name) <> CAST('' AS text) AND btrim(environment) <> CAST('' AS text) AND btrim(alias) <> CAST('' AS text));
ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_retired_timestamp CONSTRAINT chk_deployed_model_versions_retired_timestamp CHECK (status <> CAST('retired' AS text) OR retired_at IS NOT NULL);
ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_sha256 CONSTRAINT chk_deployed_model_versions_sha256 CHECK (artifact_sha256 ~ CAST('^[0-9a-f]{64}$' AS text));
ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_snapshots CONSTRAINT chk_deployed_model_versions_snapshots CHECK (jsonb_typeof(threshold_profile_snapshot) = CAST('object' AS text) AND jsonb_typeof(preprocessing_profile_snapshot) = CAST('object' AS text) AND jsonb_typeof(image_quality_policy_snapshot) = CAST('object' AS text) AND jsonb_typeof(label_mapping_snapshot) = CAST('object' AS text) AND jsonb_typeof(metadata) = CAST('object' AS text));
ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_status CONSTRAINT chk_deployed_model_versions_status CHECK (status = ANY(ARRAY[CAST('pending' AS text), CAST('active' AS text), CAST('inactive' AS text), CAST('retired' AS text), CAST('failed' AS text)]));
ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_threshold CONSTRAINT chk_deployed_model_versions_threshold CHECK (threshold_value >= CAST(0 AS numeric) AND threshold_value <= CAST(1 AS numeric));
ALTER TABLE public.deployed_model_versions ADD CONSTRAINT chk_deployed_model_versions_timestamp_order CONSTRAINT chk_deployed_model_versions_timestamp_order CHECK (retired_at IS NULL OR deployed_at IS NULL OR retired_at >= deployed_at);
ALTER TABLE public.deployed_model_versions ADD CONSTRAINT fk_deployed_model_versions_rollback CONSTRAINT fk_deployed_model_versions_rollback FOREIGN KEY (rollback_of_deployment_id) REFERENCES deployed_model_versions (id) ON DELETE RESTRICT;
ALTER TABLE public.deployed_model_versions ADD CONSTRAINT fk_deployed_model_versions_supersedes CONSTRAINT fk_deployed_model_versions_supersedes FOREIGN KEY (supersedes_deployment_id) REFERENCES deployed_model_versions (id) ON DELETE RESTRICT;
ALTER TABLE public.deployed_model_versions ADD CONSTRAINT fk_deployed_model_versions_threshold_version CONSTRAINT fk_deployed_model_versions_threshold_version FOREIGN KEY (threshold_calibration_id, model_version_id) REFERENCES run_threshold_calibration (run_threshold_calibration_id, model_version_id) ON DELETE RESTRICT;
ALTER TABLE public.deployed_model_versions ADD CONSTRAINT fk_deployed_model_versions_version_artifact CONSTRAINT fk_deployed_model_versions_version_artifact FOREIGN KEY (model_version_id, checkpoint_artifact_id) REFERENCES model_versions (id, checkpoint_artifact_id) ON DELETE RESTRICT;
```

Índices explícitos: `uq_deployed_model_versions_id_version`, `idx_deployed_model_versions_checkpoint_artifact`, `idx_deployed_model_versions_model_version`, `idx_deployed_model_versions_slot_history`, `idx_deployed_model_versions_status`, `idx_deployed_model_versions_threshold_calibration`, `uq_deployed_model_versions_active_slot`, `uq_deployed_model_versions_one_production_champion`.
Auditoría: deployed_at, retired_at, created_at.
JSONB: threshold_profile_snapshot, preprocessing_profile_snapshot, image_quality_policy_snapshot, label_mapping_snapshot, metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: artifact_sha256.

## environment_packages

Versiones de paquetes del entorno de ejecución por run.

Dominio: Q. Auditoría y trazabilidad técnica. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| run_id | uuid | YES |  |
| package_name | text | NO |  |
| package_version | text | YES |  |
| created_at | timestamp with time zone | YES | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.environment_packages ADD CONSTRAINT environment_packages_pkey CONSTRAINT environment_packages_pkey PRIMARY KEY (id);
ALTER TABLE public.environment_packages ADD CONSTRAINT environment_packages_run_id_fkey CONSTRAINT environment_packages_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;
```

Índices explícitos: `idx_environment_packages_run_id`.
Auditoría: created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## errors

Errores técnicos de run/script, distintos de métricas de modelo.

Dominio: Q. Auditoría y trazabilidad técnica. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| run_id | uuid | YES |  |
| error_type | text | YES |  |
| error_message | text | YES |  |
| stack_trace | text | YES |  |
| script_name | text | YES |  |
| created_at | timestamp with time zone | YES | now() |
| metadata | jsonb | YES | CAST('{}' AS jsonb) |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.errors ADD CONSTRAINT errors_pkey CONSTRAINT errors_pkey PRIMARY KEY (id);
ALTER TABLE public.errors ADD CONSTRAINT errors_run_id_fkey CONSTRAINT errors_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;
```

Índices explícitos: `idx_errors_run_id`.
Auditoría: created_at.
JSONB: metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## evaluation_ensemble_members

Componentes y pesos del ensemble de una evaluación.

Dominio: N. Ensembles. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| evaluation_id | uuid | NO |  |
| ordinal | integer | NO |  |
| model_version_id | uuid | NO |  |
| checkpoint_artifact_id | uuid | NO |  |
| weight | numeric | NO |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.evaluation_ensemble_members ADD CONSTRAINT v2_evaluation_ensemble_members_primary_0f6c3f155b09 CONSTRAINT v2_evaluation_ensemble_members_primary_0f6c3f155b09 PRIMARY KEY (evaluation_id, ordinal);
ALTER TABLE public.evaluation_ensemble_members ADD CONSTRAINT v2_evaluation_ensemble_members_unique_3a2092158e31 CONSTRAINT v2_evaluation_ensemble_members_unique_3a2092158e31 UNIQUE (evaluation_id, model_version_id);
ALTER TABLE public.evaluation_ensemble_members ADD CONSTRAINT v2_evaluation_ensemble_members_foreign_a402d28a70f6 CONSTRAINT v2_evaluation_ensemble_members_foreign_a402d28a70f6 FOREIGN KEY (evaluation_id) REFERENCES public.evaluations (id) ON DELETE RESTRICT;
ALTER TABLE public.evaluation_ensemble_members ADD CONSTRAINT v2_evaluation_ensemble_members_check_967aa2df2b88 CONSTRAINT v2_evaluation_ensemble_members_check_967aa2df2b88 CHECK (ordinal >= 0);
ALTER TABLE public.evaluation_ensemble_members ADD CONSTRAINT v2_evaluation_ensemble_members_foreign_b946b2b207f3 CONSTRAINT v2_evaluation_ensemble_members_foreign_b946b2b207f3 FOREIGN KEY (model_version_id) REFERENCES public.model_versions (id) ON DELETE RESTRICT;
ALTER TABLE public.evaluation_ensemble_members ADD CONSTRAINT v2_evaluation_ensemble_members_foreign_6aec504c7a2f CONSTRAINT v2_evaluation_ensemble_members_foreign_6aec504c7a2f FOREIGN KEY (checkpoint_artifact_id) REFERENCES public.artifacts (id) ON DELETE RESTRICT;
ALTER TABLE public.evaluation_ensemble_members ADD CONSTRAINT v2_evaluation_ensemble_members_check_32cd0f122db1 CONSTRAINT v2_evaluation_ensemble_members_check_32cd0f122db1 CHECK (weight > 0 AND weight < CAST('Infinity' AS numeric));
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: heredada de su padre y registrada en la relación.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## evaluations

Contexto científico, población, umbral y procedencia de una evaluación.

Dominio: K. Evaluaciones. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | gen_random_uuid() |
| run_id | uuid | NO |  |
| training_run_id | uuid | NO |  |
| model_version_id | uuid | YES |  |
| checkpoint_artifact_id | uuid | YES |  |
| dataset_version_id | uuid | NO |  |
| split | text | NO |  |
| evaluation_role | text | NO |  |
| purpose | text | NO |  |
| dataset_origin_id | uuid | YES |  |
| dataset_origin_role | text | YES |  |
| population_manifest_uri | text | YES |  |
| population_manifest_sha256 | text | YES |  |
| dataset_provenance_uri | text | YES |  |
| dataset_provenance_sha256 | text | YES |  |
| subject_kind | text | NO |  |
| protocol_version | text | NO |  |
| protocol_hash | text | NO |  |
| population_hash | text | NO |  |
| input_contract_hash | text | NO |  |
| comparison_contract_hash | text | NO |  |
| protocol_snapshot | jsonb | NO |  |
| source_kind | text | NO |  |
| source_record_key | text | NO |  |
| source_record_phase | text | NO |  |
| source_event_id | uuid | YES |  |
| event_kind | text | YES |  |
| event_phase | text | YES |  |
| event_key | text | YES |  |
| source_assessment_attempt_id | uuid | YES |  |
| threshold_used | numeric | NO |  |
| threshold_source | text | NO |  |
| calibration_id | uuid | YES |  |
| metric_definition | text | NO | 'binary_nullable_v2' |
| created_at | timestamptz | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_primary_8c8464f42472 CONSTRAINT v2_evaluations_primary_8c8464f42472 PRIMARY KEY (id);
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_unique_2b29f071653b CONSTRAINT v2_evaluations_unique_2b29f071653b UNIQUE (run_id, source_kind, source_record_phase, source_record_key);
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_unique_927a8d4fe69d CONSTRAINT v2_evaluations_unique_927a8d4fe69d UNIQUE (id, run_id);
ALTER TABLE public.evaluations ADD CONSTRAINT fk_evaluation_e10_record CONSTRAINT fk_evaluation_e10_record FOREIGN KEY (run_id, event_kind, event_phase, event_key) REFERENCES public.train_execution_records (run_id, kind, phase, record_key) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public.evaluations ADD CONSTRAINT ck_e04_selected_source CONSTRAINT ck_e04_selected_source CHECK (source_kind <> 'e10' OR evaluation_role <> 'calibration_selected' OR (threshold_source = 'validation_calibration' AND calibration_id IS NOT NULL));
ALTER TABLE public.evaluations ADD CONSTRAINT ck_e04_default_source CONSTRAINT ck_e04_default_source CHECK (source_kind <> 'e10' OR evaluation_role <> 'calibration_default' OR (threshold_source = 'default' AND threshold_used = 0.5 AND calibration_id IS NULL));
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_foreign_db5338c19de4 CONSTRAINT v2_evaluations_foreign_db5338c19de4 FOREIGN KEY (run_id) REFERENCES public.runs (id) ON DELETE RESTRICT;
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_foreign_4e6a43d876af CONSTRAINT v2_evaluations_foreign_4e6a43d876af FOREIGN KEY (training_run_id) REFERENCES public.runs (id) ON DELETE RESTRICT;
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_foreign_6aec504c7a2f CONSTRAINT v2_evaluations_foreign_6aec504c7a2f FOREIGN KEY (checkpoint_artifact_id) REFERENCES public.artifacts (id) ON DELETE RESTRICT;
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_foreign_14b20ff24e12 CONSTRAINT v2_evaluations_foreign_14b20ff24e12 FOREIGN KEY (dataset_version_id) REFERENCES public.dataset_versions (id) ON DELETE RESTRICT;
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_c2a936c0d6c6 CONSTRAINT v2_evaluations_check_c2a936c0d6c6 CHECK (split IN ('train', 'val', 'test', 'external'));
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_6d2ae4a2559c CONSTRAINT v2_evaluations_check_6d2ae4a2559c CHECK (evaluation_role IN ('training_validation_final', 'development', 'final_test', 'calibration_default', 'calibration_selected', 'external_complementary'));
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_114e1e7e39d4 CONSTRAINT v2_evaluations_check_114e1e7e39d4 CHECK (purpose IN ('development', 'final', 'complementary'));
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_b5ea10e3edba CONSTRAINT v2_evaluations_check_b5ea10e3edba CHECK (subject_kind IN ('single', 'ensemble'));
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_0652739ad678 CONSTRAINT v2_evaluations_check_0652739ad678 CHECK (protocol_hash ~ '^[0-9a-f]{64}$');
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_c13afae612b2 CONSTRAINT v2_evaluations_check_c13afae612b2 CHECK (population_hash ~ '^[0-9a-f]{64}$');
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_b93d47c84570 CONSTRAINT v2_evaluations_check_b93d47c84570 CHECK (input_contract_hash ~ '^[0-9a-f]{64}$');
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_f337b5a1c02f CONSTRAINT v2_evaluations_check_f337b5a1c02f CHECK (comparison_contract_hash ~ '^[0-9a-f]{64}$');
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_00fb2e80d9b2 CONSTRAINT v2_evaluations_check_00fb2e80d9b2 CHECK (jsonb_typeof(protocol_snapshot) = 'object');
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_f1db93b69ab7 CONSTRAINT v2_evaluations_check_f1db93b69ab7 CHECK (source_kind IN ('e10', 'assessment', 'legacy', 'external_record'));
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_foreign_c764adede219 CONSTRAINT v2_evaluations_foreign_c764adede219 FOREIGN KEY (source_assessment_attempt_id) REFERENCES public.assessment_attempts (id) ON DELETE RESTRICT;
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_05b75a389d97 CONSTRAINT v2_evaluations_check_05b75a389d97 CHECK (threshold_used >= 0 AND threshold_used <= 1);
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_f4818b1a9fd3 CONSTRAINT v2_evaluations_check_f4818b1a9fd3 CHECK (threshold_source IN ('default', 'validation_calibration', 'protocol_numeric'));
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_foreign_0baa7d166e2f CONSTRAINT v2_evaluations_foreign_0baa7d166e2f FOREIGN KEY (calibration_id) REFERENCES public.run_threshold_calibration (run_threshold_calibration_id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_4cbf36ebbe5e CONSTRAINT v2_evaluations_check_4cbf36ebbe5e CHECK (metric_definition = 'binary_nullable_v2');
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_foreign_6cfcdf2998f5 CONSTRAINT v2_evaluations_foreign_6cfcdf2998f5 FOREIGN KEY (model_version_id, training_run_id) REFERENCES public.model_versions (id, training_run_id) ON DELETE RESTRICT;
ALTER TABLE public.evaluations ADD CONSTRAINT ck_v2_evaluation_scope CONSTRAINT ck_v2_evaluation_scope CHECK ((split = 'test' AND purpose = 'final' AND evaluation_role = 'final_test') OR (split IN ('train', 'val') AND purpose = 'development' AND evaluation_role IN ('training_validation_final', 'development', 'calibration_default', 'calibration_selected')) OR (split = 'external' AND purpose = 'complementary' AND evaluation_role = 'external_complementary'));
ALTER TABLE public.evaluations ADD CONSTRAINT fk_v2_evaluation_dataset_origin CONSTRAINT fk_v2_evaluation_dataset_origin FOREIGN KEY (dataset_version_id, dataset_origin_id, dataset_origin_role) REFERENCES public.dataset_version_sources (dataset_version_id, dataset_id, role) ON DELETE RESTRICT;
ALTER TABLE public.evaluations ADD CONSTRAINT ck_v2_external_provenance CONSTRAINT ck_v2_external_provenance CHECK (split <> 'external' OR (dataset_origin_id IS NOT NULL AND dataset_origin_role IS NOT NULL AND population_manifest_uri IS NOT NULL AND length(btrim(population_manifest_uri)) > 0 AND population_manifest_sha256 IS NOT NULL AND population_manifest_sha256 ~ '^[0-9a-f]{64}$' AND dataset_provenance_uri IS NOT NULL AND length(btrim(dataset_provenance_uri)) > 0 AND dataset_provenance_sha256 IS NOT NULL AND dataset_provenance_sha256 ~ '^[0-9a-f]{64}$' AND source_kind IN ('legacy', 'external_record') AND length(btrim(source_record_key)) > 0 AND length(btrim(source_record_phase)) > 0));
ALTER TABLE public.evaluations ADD CONSTRAINT ck_v2_external_source CONSTRAINT ck_v2_external_source CHECK (source_kind <> 'external_record' OR split = 'external');
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_a359e10954fc CONSTRAINT v2_evaluations_check_a359e10954fc CHECK (evaluation_role NOT IN ('training_validation_final', 'calibration_default', 'calibration_selected') OR split = 'val');
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_d2a4e9ce706e CONSTRAINT v2_evaluations_check_d2a4e9ce706e CHECK ((threshold_source = 'default' AND threshold_used = 0.5 AND calibration_id IS NULL) OR (threshold_source = 'validation_calibration' AND calibration_id IS NOT NULL) OR (threshold_source = 'protocol_numeric' AND calibration_id IS NULL));
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_88394215eb49 CONSTRAINT v2_evaluations_check_88394215eb49 CHECK ((source_kind = 'e10' AND source_event_id IS NOT NULL AND source_assessment_attempt_id IS NULL) OR (source_kind = 'assessment' AND source_event_id IS NULL AND source_assessment_attempt_id IS NOT NULL) OR (source_kind IN ('legacy', 'external_record') AND source_event_id IS NULL AND source_assessment_attempt_id IS NULL));
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_3df12c5495af CONSTRAINT v2_evaluations_check_3df12c5495af CHECK (subject_kind = 'ensemble' OR checkpoint_artifact_id IS NOT NULL);
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_58c667b93f11 CONSTRAINT v2_evaluations_check_58c667b93f11 CHECK (split <> 'test' OR source_kind = 'assessment');
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_28938a6edbaa CONSTRAINT v2_evaluations_check_28938a6edbaa CHECK (source_kind <> 'e10' OR evaluation_role IN ('training_validation_final', 'calibration_default', 'calibration_selected'));
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_08204f883325 CONSTRAINT v2_evaluations_check_08204f883325 CHECK (evaluation_role <> 'training_validation_final' OR run_id = training_run_id);
ALTER TABLE public.evaluations ADD CONSTRAINT v2_evaluations_check_3b1acb9be108 CONSTRAINT v2_evaluations_check_3b1acb9be108 CHECK ((source_kind = 'e10' AND event_kind = 'e10_event' AND event_phase = 'run_event_v1' AND event_key = CAST(source_event_id AS text) AND event_kind IS NOT NULL AND event_phase IS NOT NULL AND event_key IS NOT NULL) OR (source_kind <> 'e10' AND event_kind IS NULL AND event_phase IS NULL AND event_key IS NULL));
```

Índices explícitos: `uq_evaluation_final_training`, `ix_evaluation_comparison`, `uq_e04_event_role`, `uq_e04_contract_role`.
Auditoría: created_at.
JSONB: protocol_snapshot. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: population_manifest_sha256, dataset_provenance_uri, dataset_provenance_sha256, protocol_hash, population_hash, input_contract_hash, comparison_contract_hash, source_kind, source_record_key, source_record_phase, source_event_id, source_assessment_attempt_id.

## execution_logs

Logs estructurados de ejecución, fuente/nivel/mensaje para observabilidad.

Dominio: Q. Auditoría y trazabilidad técnica. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| run_id | uuid | YES |  |
| log_level | text | YES |  |
| message | text | YES |  |
| source | text | YES |  |
| created_at | timestamp with time zone | YES | now() |
| metadata | jsonb | YES | CAST('{}' AS jsonb) |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.execution_logs ADD CONSTRAINT execution_logs_pkey CONSTRAINT execution_logs_pkey PRIMARY KEY (id);
ALTER TABLE public.execution_logs ADD CONSTRAINT execution_logs_run_id_fkey CONSTRAINT execution_logs_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;
```

Índices explícitos: `idx_execution_logs_run_id`.
Auditoría: created_at.
JSONB: metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## experiment_execution_events

Evidencia global append-only owner/event/payload, distinta del stream RunEvent.

Dominio: J. TRAIN / execution ledger. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | bigint | NO | GENERATED ALWAYS AS IDENTITY |
| owner | uuid | NO |  |
| event | text | NO |  |
| payload | jsonb | NO |  |
| created_at | timestamp with time zone | NO | clock_timestamp() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.experiment_execution_events ADD CONSTRAINT experiment_execution_events_pkey CONSTRAINT experiment_execution_events_pkey PRIMARY KEY (id);
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: payload. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## experiment_execution_gate

Singleton de exclusión global y fencing con owner/PID/evidencia de procesos.

Dominio: J. TRAIN / execution ledger. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| singleton | boolean | NO | TRUE |
| owner | uuid | YES |  |
| db_pid | integer | YES |  |
| process_evidence | jsonb | NO | CAST('{}' AS jsonb) |
| blocked_reason | text | YES |  |
| updated_at | timestamp with time zone | NO | clock_timestamp() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.experiment_execution_gate ADD CONSTRAINT experiment_execution_gate_pkey CONSTRAINT experiment_execution_gate_pkey PRIMARY KEY (singleton);
ALTER TABLE public.experiment_execution_gate ADD CONSTRAINT experiment_execution_gate_singleton_check CONSTRAINT experiment_execution_gate_singleton_check CHECK (singleton);
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: updated_at.
JSONB: process_evidence. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## experimental_campaigns

Contrato científico y presupuesto de campaña, dataset/entorno y máquina de estado.

Dominio: I. Campañas. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| experiment_id | uuid | YES |  |
| name | text | NO |  |
| purpose | text | NO |  |
| state | text | NO | CAST('draft' AS text) |
| dataset_version_id | uuid | NO |  |
| dataset_snapshot | jsonb | NO |  |
| dataset_evidence_id | uuid | NO |  |
| requested | jsonb | NO |  |
| protocol | jsonb | NO |  |
| environment | jsonb | NO |  |
| registry_snapshot | jsonb | YES |  |
| contract | jsonb | YES |  |
| canonical_contract | text | YES |  |
| contract_hash | text | YES |  |
| expected_count | integer | NO | 0 |
| actor | text | NO |  |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |
| frozen_at | timestamp with time zone | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_pkey CONSTRAINT experimental_campaigns_pkey PRIMARY KEY (id);
ALTER TABLE public.experimental_campaigns ADD CONSTRAINT ck_campaign_frozen_required_v2 CONSTRAINT ck_campaign_frozen_required_v2 CHECK (state = CAST('draft' AS text) OR (contract IS NOT NULL AND canonical_contract IS NOT NULL AND contract_hash IS NOT NULL AND contract_hash ~ CAST('^[a-f0-9]{64}$' AS text) AND NOT contract_hash IS DISTINCT FROM encode(sha256(convert_to(canonical_contract, CAST('UTF8' AS name))), CAST('hex' AS text)) AND NOT CAST(canonical_contract AS jsonb) IS DISTINCT FROM contract AND campaign_contract_valid(contract)) IS TRUE);
ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_actor_check CONSTRAINT experimental_campaigns_actor_check CHECK (length(btrim(actor)) > 0);
ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_check CONSTRAINT experimental_campaigns_check CHECK ((state = CAST('draft' AS text) AND contract IS NULL AND canonical_contract IS NULL AND contract_hash IS NULL AND frozen_at IS NULL) OR (state <> CAST('draft' AS text) AND contract IS NOT NULL AND canonical_contract IS NOT NULL AND contract_hash ~ CAST('^[a-f0-9]{64}$' AS text) AND registry_snapshot IS NOT NULL AND frozen_at IS NOT NULL AND expected_count > 0));
ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_check1 CONSTRAINT experimental_campaigns_check1 CHECK (NOT(dataset_snapshot ->> CAST('dataset_version_id' AS text)) IS DISTINCT FROM CAST(dataset_version_id AS text));
ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_dataset_snapshot_check CONSTRAINT experimental_campaigns_dataset_snapshot_check CHECK (jsonb_typeof(dataset_snapshot) = CAST('object' AS text));
ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_environment_check CONSTRAINT experimental_campaigns_environment_check CHECK (jsonb_typeof(environment) = CAST('object' AS text));
ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_expected_count_check CONSTRAINT experimental_campaigns_expected_count_check CHECK (expected_count >= 0);
ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_name_check CONSTRAINT experimental_campaigns_name_check CHECK (length(btrim(name)) > 0);
ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_protocol_check CONSTRAINT experimental_campaigns_protocol_check CHECK (jsonb_typeof(protocol) = CAST('object' AS text));
ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_purpose_check CONSTRAINT experimental_campaigns_purpose_check CHECK (length(btrim(purpose)) > 0);
ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_requested_check CONSTRAINT experimental_campaigns_requested_check CHECK (jsonb_typeof(requested) = CAST('object' AS text));
ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_state_check CONSTRAINT experimental_campaigns_state_check CHECK (state = ANY(ARRAY[CAST('draft' AS text), CAST('frozen' AS text), CAST('active' AS text), CAST('paused' AS text), CAST('finalized' AS text)]));
ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_dataset_evidence_id_fkey CONSTRAINT experimental_campaigns_dataset_evidence_id_fkey FOREIGN KEY (dataset_evidence_id) REFERENCES audit_events (id) ON DELETE RESTRICT;
ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_dataset_version_id_fkey CONSTRAINT experimental_campaigns_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;
ALTER TABLE public.experimental_campaigns ADD CONSTRAINT experimental_campaigns_experiment_id_fkey CONSTRAINT experimental_campaigns_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_campaign_dataset_state`.
Auditoría: created_at, updated_at, frozen_at.
JSONB: dataset_snapshot, requested, protocol, environment, registry_snapshot, contract. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: canonical_contract, contract_hash.

## experiments

Agrupación de runs por proyecto/experimento científico.

Dominio: F. Experimentos. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| name | text | NO |  |
| description | text | YES |  |
| project_name | text | YES |  |
| created_at | timestamp with time zone | YES | now() |
| updated_at | timestamp with time zone | YES | now() |
| metadata | jsonb | YES | CAST('{}' AS jsonb) |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.experiments ADD CONSTRAINT experiments_pkey CONSTRAINT experiments_pkey PRIMARY KEY (id);
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at, updated_at.
JSONB: metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## explainability_results

Resultado XAI ML ligado a run/predicción, caso y salida visual; padre de evidencia v2.

Dominio: O. XAI. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| run_id | uuid | YES |  |
| prediction_id | uuid | YES |  |
| method | text | NO |  |
| image_path | text | YES |  |
| output_path | text | YES |  |
| true_label | text | YES |  |
| predicted_label | text | YES |  |
| score | numeric | YES |  |
| case_type | text | YES |  |
| last_conv_layer | text | YES |  |
| explanation_parameters | jsonb | YES | CAST('{}' AS jsonb) |
| success | boolean | YES | TRUE |
| error_message | text | YES |  |
| created_at | timestamp with time zone | YES | now() |
| metadata | jsonb | YES | CAST('{}' AS jsonb) |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.explainability_results ADD CONSTRAINT explainability_results_pkey CONSTRAINT explainability_results_pkey PRIMARY KEY (id);
ALTER TABLE public.explainability_results ADD CONSTRAINT explainability_results_prediction_id_fkey CONSTRAINT explainability_results_prediction_id_fkey FOREIGN KEY (prediction_id) REFERENCES predictions (id) ON DELETE RESTRICT;
ALTER TABLE public.explainability_results ADD CONSTRAINT explainability_results_run_id_fkey CONSTRAINT explainability_results_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;
```

Índices explícitos: `idx_explainability_case_method`, `idx_explainability_method`, `idx_explainability_output_path`, `idx_explainability_run_id`, `idx_explainability_success`.
Auditoría: created_at.
JSONB: explanation_parameters, metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## identity_evidence

Procedencia/verificación de asociación imagen fuente–identidad clínica.

Dominio: B. Dataset. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| source_record_id | uuid | NO |  |
| clinical_identity_id | uuid | NO |  |
| evidence_type | text | NO |  |
| evidence_level | text | NO |  |
| mapping_method | text | NO |  |
| evidence_reference | text | YES |  |
| official_source_reference | text | YES |  |
| evidence_json | jsonb | NO | CAST('{}' AS jsonb) |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.identity_evidence ADD CONSTRAINT identity_evidence_pkey CONSTRAINT identity_evidence_pkey PRIMARY KEY (id);
ALTER TABLE public.identity_evidence ADD CONSTRAINT chk_identity_evidence_json_object CONSTRAINT chk_identity_evidence_json_object CHECK (jsonb_typeof(evidence_json) = CAST('object' AS text));
ALTER TABLE public.identity_evidence ADD CONSTRAINT identity_evidence_clinical_identity_id_fkey CONSTRAINT identity_evidence_clinical_identity_id_fkey FOREIGN KEY (clinical_identity_id) REFERENCES clinical_identities (id) ON DELETE RESTRICT;
ALTER TABLE public.identity_evidence ADD CONSTRAINT identity_evidence_source_record_id_fkey CONSTRAINT identity_evidence_source_record_id_fkey FOREIGN KEY (source_record_id) REFERENCES dataset_source_records (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_identity_evidence_clinical_identity_id`, `ix_identity_evidence_source_record_id`.
Auditoría: created_at.
JSONB: evidence_json. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: source_record_id, official_source_reference.

## image_analysis_jobs

Trabajo de inferencia trazable por imagen, input/checksum y despliegue.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| inference_run_id | uuid | NO |  |
| deployed_model_version_id | uuid | NO |  |
| model_version_id | uuid | NO |  |
| input_artifact_id | uuid | YES |  |
| source_image_id | uuid | YES |  |
| idempotency_key | text | YES |  |
| sample_id | text | YES |  |
| patient_id | text | YES |  |
| slide_id | text | YES |  |
| status | text | NO | CAST('pending' AS text) |
| quality_status | text | NO | CAST('not_assessed' AS text) |
| quality_metrics | jsonb | NO | CAST('{}' AS jsonb) |
| threshold_used | numeric | YES |  |
| threshold_source | text | YES |  |
| summary | jsonb | NO | CAST('{}' AS jsonb) |
| total_cells | integer | YES |  |
| positive_cells | integer | YES |  |
| started_at | timestamp with time zone | YES |  |
| completed_at | timestamp with time zone | YES |  |
| error_message | text | YES |  |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |
| metadata | jsonb | NO | CAST('{}' AS jsonb) |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT image_analysis_jobs_pkey CONSTRAINT image_analysis_jobs_pkey PRIMARY KEY (id);
ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT chk_image_analysis_jobs_counts CONSTRAINT chk_image_analysis_jobs_counts CHECK ((total_cells IS NULL OR total_cells >= 0) AND (positive_cells IS NULL OR positive_cells >= 0) AND (total_cells IS NULL OR positive_cells IS NULL OR positive_cells <= total_cells));
ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT chk_image_analysis_jobs_idempotency_key CONSTRAINT chk_image_analysis_jobs_idempotency_key CHECK (idempotency_key IS NULL OR NULLIF(btrim(idempotency_key), CAST('' AS text)) IS NOT NULL);
ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT chk_image_analysis_jobs_payload_objects CONSTRAINT chk_image_analysis_jobs_payload_objects CHECK (jsonb_typeof(quality_metrics) = CAST('object' AS text) AND jsonb_typeof(summary) = CAST('object' AS text) AND jsonb_typeof(metadata) = CAST('object' AS text));
ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT chk_image_analysis_jobs_quality_status CONSTRAINT chk_image_analysis_jobs_quality_status CHECK (quality_status = ANY(ARRAY[CAST('not_assessed' AS text), CAST('pending' AS text), CAST('passed' AS text), CAST('warning' AS text), CAST('rejected' AS text), CAST('failed' AS text), CAST('skipped' AS text)]));
ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT chk_image_analysis_jobs_source CONSTRAINT chk_image_analysis_jobs_source CHECK (input_artifact_id IS NOT NULL OR source_image_id IS NOT NULL);
ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT chk_image_analysis_jobs_status CONSTRAINT chk_image_analysis_jobs_status CHECK (status = ANY(ARRAY[CAST('pending' AS text), CAST('running' AS text), CAST('completed' AS text), CAST('failed' AS text), CAST('rejected' AS text), CAST('cancelled' AS text)]));
ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT chk_image_analysis_jobs_status_timestamps CONSTRAINT chk_image_analysis_jobs_status_timestamps CHECK ((status <> ALL(ARRAY[CAST('running' AS text), CAST('completed' AS text)]) OR started_at IS NOT NULL) AND (status <> ALL(ARRAY[CAST('completed' AS text), CAST('failed' AS text), CAST('rejected' AS text), CAST('cancelled' AS text)]) OR completed_at IS NOT NULL));
ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT chk_image_analysis_jobs_threshold CONSTRAINT chk_image_analysis_jobs_threshold CHECK (threshold_used IS NULL OR (threshold_used >= CAST(0 AS numeric) AND threshold_used <= CAST(1 AS numeric)));
ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT chk_image_analysis_jobs_timestamp_order CONSTRAINT chk_image_analysis_jobs_timestamp_order CHECK (completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at);
ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT fk_image_analysis_jobs_input_artifact CONSTRAINT fk_image_analysis_jobs_input_artifact FOREIGN KEY (input_artifact_id) REFERENCES artifacts (id) ON DELETE RESTRICT;
ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT fk_image_analysis_jobs_run_deployment_version CONSTRAINT fk_image_analysis_jobs_run_deployment_version FOREIGN KEY (inference_run_id, deployed_model_version_id, model_version_id) REFERENCES run_model_deployments (run_id, deployed_model_version_id, model_version_id) ON DELETE RESTRICT;
ALTER TABLE public.image_analysis_jobs ADD CONSTRAINT fk_image_analysis_jobs_source_image CONSTRAINT fk_image_analysis_jobs_source_image FOREIGN KEY (source_image_id) REFERENCES dataset_split_images (image_id) ON DELETE RESTRICT;
```

Índices explícitos: `uq_image_analysis_jobs_identity`, `idx_image_analysis_jobs_deployment`, `idx_image_analysis_jobs_input_artifact`, `idx_image_analysis_jobs_model_version`, `idx_image_analysis_jobs_run`, `idx_image_analysis_jobs_source_image`, `idx_image_analysis_jobs_status_created`, `uq_image_analysis_jobs_idempotency`.
Auditoría: started_at, completed_at, created_at, updated_at.
JSONB: quality_metrics, summary, metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: source_image_id.

## image_connected_components

Componentes numéricos/geometría extraídos por detector de imagen.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| detection_run_id | uuid | NO |  |
| analysis_run_id | uuid | NO |  |
| analysis_run_image_id | uuid | NO |  |
| microscopy_image_id | uuid | NO |  |
| component_index | integer | NO |  |
| bbox_x | integer | NO |  |
| bbox_y | integer | NO |  |
| bbox_width | integer | NO |  |
| bbox_height | integer | NO |  |
| centroid_x | double precision | NO |  |
| centroid_y | double precision | NO |  |
| area_px | integer | NO |  |
| perimeter_px | double precision | YES |  |
| circularity | double precision | YES |  |
| solidity | double precision | YES |  |
| touches_border | boolean | NO |  |
| component_status | varchar(30) | NO |  |
| rejection_code | varchar(80) | YES |  |
| metrics_json | jsonb | NO | CAST('{}' AS jsonb) |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_pkey CONSTRAINT image_connected_components_pkey PRIMARY KEY (id);
ALTER TABLE public.image_connected_components ADD CONSTRAINT uq_image_connected_components_identity CONSTRAINT uq_image_connected_components_identity UNIQUE (id, detection_run_id, analysis_run_image_id, microscopy_image_id);
ALTER TABLE public.image_connected_components ADD CONSTRAINT uq_image_connected_components_run_image_index CONSTRAINT uq_image_connected_components_run_image_index UNIQUE (detection_run_id, analysis_run_image_id, component_index);
ALTER TABLE public.image_connected_components ADD CONSTRAINT ck_connected_component_rejection CONSTRAINT ck_connected_component_rejection CHECK ((CAST(component_status AS text) = CAST('rejected_by_filter' AS text) AND rejection_code IS NOT NULL) OR (CAST(component_status AS text) <> CAST('rejected_by_filter' AS text) AND rejection_code IS NULL));
ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_area_px_check CONSTRAINT image_connected_components_area_px_check CHECK (area_px > 0);
ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_bbox_height_check CONSTRAINT image_connected_components_bbox_height_check CHECK (bbox_height > 0);
ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_bbox_width_check CONSTRAINT image_connected_components_bbox_width_check CHECK (bbox_width > 0);
ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_bbox_x_check CONSTRAINT image_connected_components_bbox_x_check CHECK (bbox_x >= 0);
ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_bbox_y_check CONSTRAINT image_connected_components_bbox_y_check CHECK (bbox_y >= 0);
ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_centroid_x_check CONSTRAINT image_connected_components_centroid_x_check CHECK (centroid_x >= CAST(0 AS double precision));
ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_centroid_y_check CONSTRAINT image_connected_components_centroid_y_check CHECK (centroid_y >= CAST(0 AS double precision));
ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_circularity_check CONSTRAINT image_connected_components_circularity_check CHECK (circularity IS NULL OR (circularity >= CAST(0 AS double precision) AND circularity <= CAST(1 AS double precision)));
ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_component_index_check CONSTRAINT image_connected_components_component_index_check CHECK (component_index > 0);
ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_component_status_check CONSTRAINT image_connected_components_component_status_check CHECK (CAST(component_status AS text) = ANY(ARRAY[CAST(CAST('candidate' AS varchar) AS text), CAST(CAST('accepted' AS varchar) AS text), CAST(CAST('rejected_by_filter' AS varchar) AS text)]));
ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_metrics_json_check CONSTRAINT image_connected_components_metrics_json_check CHECK (jsonb_typeof(metrics_json) = CAST('object' AS text));
ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_perimeter_px_check CONSTRAINT image_connected_components_perimeter_px_check CHECK (perimeter_px IS NULL OR perimeter_px >= CAST(0 AS double precision));
ALTER TABLE public.image_connected_components ADD CONSTRAINT image_connected_components_solidity_check CONSTRAINT image_connected_components_solidity_check CHECK (solidity IS NULL OR (solidity >= CAST(0 AS double precision) AND solidity <= CAST(1 AS double precision)));
ALTER TABLE public.image_connected_components ADD CONSTRAINT fk_components_detection_analysis CONSTRAINT fk_components_detection_analysis FOREIGN KEY (detection_run_id, analysis_run_id) REFERENCES cell_detection_runs (id, analysis_run_id) ON DELETE RESTRICT;
ALTER TABLE public.image_connected_components ADD CONSTRAINT fk_components_frozen_image CONSTRAINT fk_components_frozen_image FOREIGN KEY (analysis_run_image_id, analysis_run_id, microscopy_image_id) REFERENCES microscopy_analysis_run_images (id, analysis_run_id, microscopy_image_id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_image_connected_components_run_image`, `ix_image_connected_components_status`.
Auditoría: created_at.
JSONB: metrics_json. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## image_ingestion_batches

Lote de ingestión vinculado a caso/muestra/lámina e identidad de origen.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| subject_id | uuid | NO |  |
| case_id | uuid | NO |  |
| sample_id | uuid | NO |  |
| slide_id | uuid | NO |  |
| acquisition_origin | varchar(40) | NO |  |
| source_system | varchar(120) | YES |  |
| source_group_key | varchar(240) | YES |  |
| expected_image_count | integer | YES |  |
| received_image_count | integer | NO | 0 |
| status | varchar(20) | NO | CAST('pending' AS varchar) |
| created_by | uuid | NO |  |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |
| completed_at | timestamp with time zone | YES |  |
| metadata_json | jsonb | NO | CAST('{}' AS jsonb) |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_pkey CONSTRAINT image_ingestion_batches_pkey PRIMARY KEY (id);
ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_acquisition_origin_check CONSTRAINT image_ingestion_batches_acquisition_origin_check CHECK (CAST(acquisition_origin AS text) = ANY(ARRAY[CAST(CAST('manual_upload' AS varchar) AS text), CAST(CAST('research_dataset_import' AS varchar) AS text), CAST(CAST('external_capture_system' AS varchar) AS text)]));
ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_expected_image_count_check CONSTRAINT image_ingestion_batches_expected_image_count_check CHECK (expected_image_count IS NULL OR expected_image_count > 0);
ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_metadata_json_check CONSTRAINT image_ingestion_batches_metadata_json_check CHECK (jsonb_typeof(metadata_json) = CAST('object' AS text));
ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_received_image_count_check CONSTRAINT image_ingestion_batches_received_image_count_check CHECK (received_image_count >= 0);
ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_status_check CONSTRAINT image_ingestion_batches_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('pending' AS varchar) AS text), CAST(CAST('incomplete' AS varchar) AS text), CAST(CAST('complete' AS varchar) AS text), CAST(CAST('inconsistent' AS varchar) AS text), CAST(CAST('failed' AS varchar) AS text)]));
ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_case_id_fkey CONSTRAINT image_ingestion_batches_case_id_fkey FOREIGN KEY (case_id) REFERENCES scientific_cases (id) ON DELETE RESTRICT;
ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_created_by_fkey CONSTRAINT image_ingestion_batches_created_by_fkey FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_sample_id_fkey CONSTRAINT image_ingestion_batches_sample_id_fkey FOREIGN KEY (sample_id) REFERENCES blood_samples (id) ON DELETE RESTRICT;
ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_slide_id_fkey CONSTRAINT image_ingestion_batches_slide_id_fkey FOREIGN KEY (slide_id) REFERENCES smear_slides (id) ON DELETE RESTRICT;
ALTER TABLE public.image_ingestion_batches ADD CONSTRAINT image_ingestion_batches_subject_id_fkey CONSTRAINT image_ingestion_batches_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES research_subjects (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_ingestion_batches_sample`, `uq_ingestion_batches_source_group`.
Auditoría: created_by, created_at, updated_at, completed_at.
JSONB: metadata_json. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: source_system, source_group_key.

## image_quality_assessments

Control de calidad de imagen dentro de análisis, mediciones/decisión y explicación.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| analysis_run_id | uuid | NO |  |
| analysis_run_image_id | uuid | NO |  |
| microscopy_image_id | uuid | NO |  |
| assessment_status | varchar(20) | NO |  |
| quality_verdict | varchar(20) | NO |  |
| integrity_verified | boolean | NO | FALSE |
| checksum_verified | boolean | NO | FALSE |
| decoded_successfully | boolean | NO | FALSE |
| width_px | integer | NO |  |
| height_px | integer | NO |  |
| pixel_count | bigint | NO |  |
| channel_count | integer | YES |  |
| bit_depth | integer | YES |  |
| color_space | varchar(80) | YES |  |
| analyzed_width_px | integer | NO |  |
| analyzed_height_px | integer | NO |  |
| analysis_scale | double precision | NO |  |
| brightness_mean | double precision | YES |  |
| brightness_p05 | double precision | YES |  |
| brightness_p50 | double precision | YES |  |
| brightness_p95 | double precision | YES |  |
| contrast_p95_p05 | double precision | YES |  |
| luminance_stddev | double precision | YES |  |
| entropy_bits | double precision | YES |  |
| laplacian_variance | double precision | YES |  |
| tenengrad_mean | double precision | YES |  |
| dark_pixel_ratio | double precision | YES |  |
| bright_pixel_ratio | double precision | YES |  |
| near_black_border_ratio | double precision | YES |  |
| usable_field_ratio | double precision | YES |  |
| warning_codes | jsonb | NO | CAST('[]' AS jsonb) |
| failure_codes | jsonb | NO | CAST('[]' AS jsonb) |
| metrics_json | jsonb | NO | CAST('{}' AS jsonb) |
| started_at | timestamp with time zone | YES |  |
| completed_at | timestamp with time zone | YES |  |
| error_code | varchar(80) | YES |  |
| error_message | text | YES |  |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_pkey CONSTRAINT image_quality_assessments_pkey PRIMARY KEY (id);
ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_analysis_run_id_microscopy_image__key CONSTRAINT image_quality_assessments_analysis_run_id_microscopy_image__key UNIQUE (analysis_run_id, microscopy_image_id);
ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_analysis_scale_check CONSTRAINT image_quality_assessments_analysis_scale_check CHECK (analysis_scale > CAST(0 AS double precision));
ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_analyzed_height_px_check CONSTRAINT image_quality_assessments_analyzed_height_px_check CHECK (analyzed_height_px > 0);
ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_analyzed_width_px_check CONSTRAINT image_quality_assessments_analyzed_width_px_check CHECK (analyzed_width_px > 0);
ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_assessment_status_check CONSTRAINT image_quality_assessments_assessment_status_check CHECK (CAST(assessment_status AS text) = ANY(ARRAY[CAST(CAST('pending' AS varchar) AS text), CAST(CAST('processing' AS varchar) AS text), CAST(CAST('completed' AS varchar) AS text), CAST(CAST('error' AS varchar) AS text)]));
ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_bright_pixel_ratio_check CONSTRAINT image_quality_assessments_bright_pixel_ratio_check CHECK (bright_pixel_ratio >= CAST(0 AS double precision) AND bright_pixel_ratio <= CAST(1 AS double precision));
ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_dark_pixel_ratio_check CONSTRAINT image_quality_assessments_dark_pixel_ratio_check CHECK (dark_pixel_ratio >= CAST(0 AS double precision) AND dark_pixel_ratio <= CAST(1 AS double precision));
ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_failure_codes_check CONSTRAINT image_quality_assessments_failure_codes_check CHECK (jsonb_typeof(failure_codes) = CAST('array' AS text));
ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_height_px_check CONSTRAINT image_quality_assessments_height_px_check CHECK (height_px > 0);
ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_metrics_json_check CONSTRAINT image_quality_assessments_metrics_json_check CHECK (jsonb_typeof(metrics_json) = CAST('object' AS text));
ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_near_black_border_ratio_check CONSTRAINT image_quality_assessments_near_black_border_ratio_check CHECK (near_black_border_ratio >= CAST(0 AS double precision) AND near_black_border_ratio <= CAST(1 AS double precision));
ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_pixel_count_check CONSTRAINT image_quality_assessments_pixel_count_check CHECK (pixel_count > 0);
ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_quality_verdict_check CONSTRAINT image_quality_assessments_quality_verdict_check CHECK (CAST(quality_verdict AS text) = ANY(ARRAY[CAST(CAST('pending' AS varchar) AS text), CAST(CAST('pass' AS varchar) AS text), CAST(CAST('warning' AS varchar) AS text), CAST(CAST('fail' AS varchar) AS text), CAST(CAST('error' AS varchar) AS text)]));
ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_usable_field_ratio_check CONSTRAINT image_quality_assessments_usable_field_ratio_check CHECK (usable_field_ratio >= CAST(0 AS double precision) AND usable_field_ratio <= CAST(1 AS double precision));
ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_warning_codes_check CONSTRAINT image_quality_assessments_warning_codes_check CHECK (jsonb_typeof(warning_codes) = CAST('array' AS text));
ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_width_px_check CONSTRAINT image_quality_assessments_width_px_check CHECK (width_px > 0);
ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_analysis_run_id_fkey CONSTRAINT image_quality_assessments_analysis_run_id_fkey FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs (id) ON DELETE RESTRICT;
ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_analysis_run_image_id_analysis_r_fkey CONSTRAINT image_quality_assessments_analysis_run_image_id_analysis_r_fkey FOREIGN KEY (analysis_run_image_id, analysis_run_id, microscopy_image_id) REFERENCES microscopy_analysis_run_images (id, analysis_run_id, microscopy_image_id) ON DELETE RESTRICT;
ALTER TABLE public.image_quality_assessments ADD CONSTRAINT image_quality_assessments_microscopy_image_id_fkey CONSTRAINT image_quality_assessments_microscopy_image_id_fkey FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images (id) ON DELETE RESTRICT;
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: started_at, completed_at, created_at.
JSONB: warning_codes, failure_codes, metrics_json. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## local_execution_jobs

Reserva remota, identidad principal/agente, heartbeat/resultado/exit; retiene gate hasta salida.

Dominio: J. TRAIN / execution ledger. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| principal | text | NO |  |
| agent_id | uuid | NO |  |
| owner | uuid | NO |  |
| request_hash | text | NO |  |
| campaign_id | uuid | NO |  |
| run_id | uuid | YES |  |
| state | text | NO |  |
| session | jsonb | YES |  |
| heartbeat_at | timestamp with time zone | NO | clock_timestamp() |
| process | jsonb | YES |  |
| completion | jsonb | YES |  |
| exit_proof | jsonb | YES |  |
| result | jsonb | YES |  |
| created_at | timestamp with time zone | NO | clock_timestamp() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.local_execution_jobs ADD CONSTRAINT local_execution_jobs_pkey CONSTRAINT local_execution_jobs_pkey PRIMARY KEY (id);
ALTER TABLE public.local_execution_jobs ADD CONSTRAINT local_execution_jobs_owner_key CONSTRAINT local_execution_jobs_owner_key UNIQUE (owner);
ALTER TABLE public.local_execution_jobs ADD CONSTRAINT local_execution_jobs_run_id_key CONSTRAINT local_execution_jobs_run_id_key UNIQUE (run_id);
ALTER TABLE public.local_execution_jobs ADD CONSTRAINT local_execution_jobs_state_check CONSTRAINT local_execution_jobs_state_check CHECK (state = ANY(ARRAY[CAST('held' AS text), CAST('calculation_reported' AS text), CAST('released' AS text), CAST('failed' AS text)]));
ALTER TABLE public.local_execution_jobs ADD CONSTRAINT local_execution_jobs_campaign_id_fkey CONSTRAINT local_execution_jobs_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns (id);
ALTER TABLE public.local_execution_jobs ADD CONSTRAINT local_execution_jobs_run_id_fkey CONSTRAINT local_execution_jobs_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id);
```

Índices explícitos: `local_one_active`.
Auditoría: heartbeat_at, created_at.
JSONB: session, process, completion, exit_proof, result. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: request_hash.

## microscopy_analysis_events

Historial de cambios/progreso del análisis de microscopía.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| analysis_run_id | uuid | NO |  |
| microscopy_image_id | uuid | YES |  |
| event_type | varchar(80) | NO |  |
| stage | varchar(40) | NO |  |
| status | varchar(30) | NO |  |
| message_code | varchar(80) | YES |  |
| message | text | YES |  |
| progress_current | integer | YES |  |
| progress_total | integer | YES |  |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.microscopy_analysis_events ADD CONSTRAINT microscopy_analysis_events_pkey CONSTRAINT microscopy_analysis_events_pkey PRIMARY KEY (id);
ALTER TABLE public.microscopy_analysis_events ADD CONSTRAINT microscopy_analysis_events_progress_current_check CONSTRAINT microscopy_analysis_events_progress_current_check CHECK (progress_current IS NULL OR progress_current >= 0);
ALTER TABLE public.microscopy_analysis_events ADD CONSTRAINT microscopy_analysis_events_progress_total_check CONSTRAINT microscopy_analysis_events_progress_total_check CHECK (progress_total IS NULL OR progress_total >= 0);
ALTER TABLE public.microscopy_analysis_events ADD CONSTRAINT microscopy_analysis_events_analysis_run_id_fkey CONSTRAINT microscopy_analysis_events_analysis_run_id_fkey FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs (id) ON DELETE RESTRICT;
ALTER TABLE public.microscopy_analysis_events ADD CONSTRAINT microscopy_analysis_events_microscopy_image_id_fkey CONSTRAINT microscopy_analysis_events_microscopy_image_id_fkey FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_microscopy_analysis_events_run`.
Auditoría: created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## microscopy_analysis_run_images

Binding ordenado e inmutable análisis–imagen, entrada de QC y detección.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| analysis_run_id | uuid | NO |  |
| microscopy_image_id | uuid | NO |  |
| sequence_number | integer | NO |  |
| input_sha256 | char(64) | NO |  |
| input_file_size_bytes | bigint | NO |  |
| input_width_px | integer | NO |  |
| input_height_px | integer | NO |  |
| image_status_at_creation | varchar(30) | NO |  |
| quality_status | varchar(20) | NO | CAST('pending' AS varchar) |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_images_pkey CONSTRAINT microscopy_analysis_run_images_pkey PRIMARY KEY (id);
ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_image_analysis_run_id_microscopy_im_key CONSTRAINT microscopy_analysis_run_image_analysis_run_id_microscopy_im_key UNIQUE (analysis_run_id, microscopy_image_id);
ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_image_analysis_run_id_sequence_numb_key CONSTRAINT microscopy_analysis_run_image_analysis_run_id_sequence_numb_key UNIQUE (analysis_run_id, sequence_number);
ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_image_id_analysis_run_id_microscopy_key CONSTRAINT microscopy_analysis_run_image_id_analysis_run_id_microscopy_key UNIQUE (id, analysis_run_id, microscopy_image_id);
ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_images_input_file_size_bytes_check CONSTRAINT microscopy_analysis_run_images_input_file_size_bytes_check CHECK (input_file_size_bytes > 0);
ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_images_input_height_px_check CONSTRAINT microscopy_analysis_run_images_input_height_px_check CHECK (input_height_px > 0);
ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_images_input_width_px_check CONSTRAINT microscopy_analysis_run_images_input_width_px_check CHECK (input_width_px > 0);
ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_images_quality_status_check CONSTRAINT microscopy_analysis_run_images_quality_status_check CHECK (CAST(quality_status AS text) = ANY(ARRAY[CAST(CAST('pending' AS varchar) AS text), CAST(CAST('pass' AS varchar) AS text), CAST(CAST('warning' AS varchar) AS text), CAST(CAST('fail' AS varchar) AS text), CAST(CAST('error' AS varchar) AS text)]));
ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_images_sequence_number_check CONSTRAINT microscopy_analysis_run_images_sequence_number_check CHECK (sequence_number > 0);
ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_images_analysis_run_id_fkey CONSTRAINT microscopy_analysis_run_images_analysis_run_id_fkey FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs (id) ON DELETE RESTRICT;
ALTER TABLE public.microscopy_analysis_run_images ADD CONSTRAINT microscopy_analysis_run_images_microscopy_image_id_fkey CONSTRAINT microscopy_analysis_run_images_microscopy_image_id_fkey FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images (id) ON DELETE RESTRICT;
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: input_sha256.

## microscopy_analysis_runs

Proceso de análisis de frotis, caso/muestra/lámina y estado; no TRAIN.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| ingestion_batch_id | uuid | NO |  |
| subject_id | uuid | NO |  |
| case_id | uuid | NO |  |
| sample_id | uuid | NO |  |
| slide_id | uuid | NO |  |
| run_code | varchar(20) | NO |  |
| run_status | varchar(30) | NO |  |
| active_stage | varchar(30) | NO |  |
| quality_gate_status | varchar(20) | NO |  |
| ready_for_analysis | boolean | NO | FALSE |
| quality_profile_key | varchar(80) | NO |  |
| quality_profile_version | varchar(40) | NO |  |
| quality_algorithm_version | varchar(40) | NO |  |
| quality_profile_snapshot | jsonb | NO |  |
| input_manifest_sha256 | char(64) | NO |  |
| input_image_count | integer | NO |  |
| requested_by | uuid | NO |  |
| started_at | timestamp with time zone | YES |  |
| completed_at | timestamp with time zone | YES |  |
| failed_at | timestamp with time zone | YES |  |
| error_code | varchar(80) | YES |  |
| error_message | text | YES |  |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_pkey CONSTRAINT microscopy_analysis_runs_pkey PRIMARY KEY (id);
ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_run_code_key CONSTRAINT microscopy_analysis_runs_run_code_key UNIQUE (run_code);
ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_active_stage_check CONSTRAINT microscopy_analysis_runs_active_stage_check CHECK (CAST(active_stage AS text) = ANY(ARRAY[CAST(CAST('created' AS varchar) AS text), CAST(CAST('integrity_check' AS varchar) AS text), CAST(CAST('quality_assessment' AS varchar) AS text), CAST(CAST('quality_aggregation' AS varchar) AS text), CAST(CAST('technical_review' AS varchar) AS text), CAST(CAST('completed' AS varchar) AS text), CAST(CAST('failed' AS varchar) AS text)]));
ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_input_image_count_check CONSTRAINT microscopy_analysis_runs_input_image_count_check CHECK (input_image_count > 0);
ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_quality_gate_status_check CONSTRAINT microscopy_analysis_runs_quality_gate_status_check CHECK (CAST(quality_gate_status AS text) = ANY(ARRAY[CAST(CAST('pending' AS varchar) AS text), CAST(CAST('pass' AS varchar) AS text), CAST(CAST('warning' AS varchar) AS text), CAST(CAST('fail' AS varchar) AS text), CAST(CAST('error' AS varchar) AS text)]));
ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_quality_profile_snapshot_check CONSTRAINT microscopy_analysis_runs_quality_profile_snapshot_check CHECK (jsonb_typeof(quality_profile_snapshot) = CAST('object' AS text));
ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_run_status_check CONSTRAINT microscopy_analysis_runs_run_status_check CHECK (CAST(run_status AS text) = ANY(ARRAY[CAST(CAST('created' AS varchar) AS text), CAST(CAST('quality_pending' AS varchar) AS text), CAST(CAST('quality_processing' AS varchar) AS text), CAST(CAST('quality_completed' AS varchar) AS text), CAST(CAST('review_required' AS varchar) AS text), CAST(CAST('ready_for_analysis' AS varchar) AS text), CAST(CAST('blocked' AS varchar) AS text), CAST(CAST('failed' AS varchar) AS text), CAST(CAST('cancelled' AS varchar) AS text)]));
ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_case_id_fkey CONSTRAINT microscopy_analysis_runs_case_id_fkey FOREIGN KEY (case_id) REFERENCES scientific_cases (id) ON DELETE RESTRICT;
ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_ingestion_batch_id_fkey CONSTRAINT microscopy_analysis_runs_ingestion_batch_id_fkey FOREIGN KEY (ingestion_batch_id) REFERENCES image_ingestion_batches (id) ON DELETE RESTRICT;
ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_requested_by_fkey CONSTRAINT microscopy_analysis_runs_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_sample_id_fkey CONSTRAINT microscopy_analysis_runs_sample_id_fkey FOREIGN KEY (sample_id) REFERENCES blood_samples (id) ON DELETE RESTRICT;
ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_slide_id_fkey CONSTRAINT microscopy_analysis_runs_slide_id_fkey FOREIGN KEY (slide_id) REFERENCES smear_slides (id) ON DELETE RESTRICT;
ALTER TABLE public.microscopy_analysis_runs ADD CONSTRAINT microscopy_analysis_runs_subject_id_fkey CONSTRAINT microscopy_analysis_runs_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES research_subjects (id) ON DELETE RESTRICT;
```

Índices explícitos: `uq_microscopy_analysis_equivalent`, `ix_microscopy_analysis_runs_status`, `ix_microscopy_analysis_runs_subject`.
Auditoría: started_at, completed_at, failed_at, created_at, updated_at.
JSONB: quality_profile_snapshot. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: input_manifest_sha256.

## microscopy_images

Imagen clínica capturada, storage, orientación/dimensiones/procedencia y muestra.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| slide_id | uuid | NO |  |
| image_code | varchar(120) | NO |  |
| storage_provider | varchar(40) | NO | CAST('local' AS varchar) |
| storage_key | text | NO |  |
| original_filename | text | YES |  |
| mime_type | varchar(120) | NO |  |
| file_size_bytes | bigint | NO |  |
| sha256 | char(64) | NO |  |
| width_px | integer | NO |  |
| height_px | integer | NO |  |
| bit_depth | integer | YES |  |
| magnification | numeric | YES |  |
| objective_lens | varchar(120) | YES |  |
| microscope_reference | varchar(160) | YES |  |
| camera_reference | varchar(160) | YES |  |
| captured_at | timestamp with time zone | YES |  |
| status | varchar(20) | NO | CAST('registered' AS varchar) |
| metadata_json | jsonb | NO | CAST('{}' AS jsonb) |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |
| created_by | uuid | NO |  |
| updated_by | uuid | YES |  |
| archived_at | timestamp with time zone | YES |  |
| archived_by | uuid | YES |  |
| acquisition_origin | varchar(40) | NO | CAST('manual_upload' AS varchar) |
| source_system | varchar(120) | YES |  |
| source_component_id | varchar(240) | YES |  |
| source_image_name | varchar(500) | YES |  |
| source_relative_path | text | YES |  |
| image_sequence_number | integer | YES |  |
| detected_format | varchar(20) | YES |  |
| channel_count | integer | YES |  |
| color_space | varchar(80) | YES |  |
| orientation | varchar(80) | YES |  |
| ingestion_batch_id | uuid | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_pkey CONSTRAINT microscopy_images_pkey PRIMARY KEY (id);
ALTER TABLE public.microscopy_images ADD CONSTRAINT uq_microscopy_images_slide_code CONSTRAINT uq_microscopy_images_slide_code UNIQUE (slide_id, image_code);
ALTER TABLE public.microscopy_images ADD CONSTRAINT uq_microscopy_images_slide_sha256 CONSTRAINT uq_microscopy_images_slide_sha256 UNIQUE (slide_id, sha256);
ALTER TABLE public.microscopy_images ADD CONSTRAINT ck_microscopy_image_archive_state CONSTRAINT ck_microscopy_image_archive_state CHECK ((CAST(status AS text) <> CAST('archived' AS text) AND archived_at IS NULL AND archived_by IS NULL) OR (CAST(status AS text) = CAST('archived' AS text) AND archived_at IS NOT NULL AND archived_by IS NOT NULL));
ALTER TABLE public.microscopy_images ADD CONSTRAINT ck_microscopy_images_acquisition_origin CONSTRAINT ck_microscopy_images_acquisition_origin CHECK (CAST(acquisition_origin AS text) = ANY(ARRAY[CAST(CAST('manual_upload' AS varchar) AS text), CAST(CAST('research_dataset_import' AS varchar) AS text), CAST(CAST('external_capture_system' AS varchar) AS text)]));
ALTER TABLE public.microscopy_images ADD CONSTRAINT ck_microscopy_images_channels CONSTRAINT ck_microscopy_images_channels CHECK (channel_count IS NULL OR channel_count > 0);
ALTER TABLE public.microscopy_images ADD CONSTRAINT ck_microscopy_images_sequence CONSTRAINT ck_microscopy_images_sequence CHECK (image_sequence_number IS NULL OR image_sequence_number > 0);
ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_bit_depth_check CONSTRAINT microscopy_images_bit_depth_check CHECK (bit_depth IS NULL OR bit_depth > 0);
ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_file_size_bytes_check CONSTRAINT microscopy_images_file_size_bytes_check CHECK (file_size_bytes > 0);
ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_height_px_check CONSTRAINT microscopy_images_height_px_check CHECK (height_px > 0);
ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_image_code_check CONSTRAINT microscopy_images_image_code_check CHECK (btrim(CAST(image_code AS text)) <> CAST('' AS text));
ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_magnification_check CONSTRAINT microscopy_images_magnification_check CHECK (magnification IS NULL OR magnification > CAST(0 AS numeric));
ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_metadata_json_check CONSTRAINT microscopy_images_metadata_json_check CHECK (jsonb_typeof(metadata_json) = CAST('object' AS text));
ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_mime_type_check CONSTRAINT microscopy_images_mime_type_check CHECK (btrim(CAST(mime_type AS text)) <> CAST('' AS text));
ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_sha256_check CONSTRAINT microscopy_images_sha256_check CHECK (sha256 ~ CAST('^[0-9a-fA-F]{64}$' AS text));
ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_status_check CONSTRAINT microscopy_images_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('registered' AS varchar) AS text), CAST(CAST('available' AS varchar) AS text), CAST(CAST('unavailable' AS varchar) AS text), CAST(CAST('rejected' AS varchar) AS text), CAST(CAST('archived' AS varchar) AS text)]));
ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_storage_key_check CONSTRAINT microscopy_images_storage_key_check CHECK (btrim(storage_key) <> CAST('' AS text));
ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_width_px_check CONSTRAINT microscopy_images_width_px_check CHECK (width_px > 0);
ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_archived_by_fkey CONSTRAINT microscopy_images_archived_by_fkey FOREIGN KEY (archived_by) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_created_by_fkey CONSTRAINT microscopy_images_created_by_fkey FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_ingestion_batch_id_fkey CONSTRAINT microscopy_images_ingestion_batch_id_fkey FOREIGN KEY (ingestion_batch_id) REFERENCES image_ingestion_batches (id) ON DELETE RESTRICT;
ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_slide_id_fkey CONSTRAINT microscopy_images_slide_id_fkey FOREIGN KEY (slide_id) REFERENCES smear_slides (id) ON DELETE RESTRICT;
ALTER TABLE public.microscopy_images ADD CONSTRAINT microscopy_images_updated_by_fkey CONSTRAINT microscopy_images_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_microscopy_images_ingestion_batch`, `ix_microscopy_images_sha256`, `ix_microscopy_images_slide`, `ix_microscopy_images_status_created`, `uq_microscopy_images_external_path`.
Auditoría: captured_at, created_at, updated_at, created_by, updated_by, archived_at.
JSONB: metadata_json. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: sha256, source_system, source_component_id, source_image_name, source_relative_path.

## model_versions

Versión y checkpoint exactos ligados a TRAIN, signatures/snapshots y estado de gobernanza.

Dominio: E. Model versions / checkpoints. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| model_id | uuid | YES |  |
| version_name | text | YES |  |
| checkpoint_path | text | YES |  |
| final_model_path | text | YES |  |
| best_model_path | text | YES |  |
| training_run_id | uuid | YES |  |
| created_at | timestamp with time zone | YES | now() |
| metadata | jsonb | YES | CAST('{}' AS jsonb) |
| model_name | text | YES |  |
| version_number | integer | YES |  |
| checkpoint_artifact_id | uuid | YES |  |
| artifact_uri | text | YES |  |
| artifact_sha256 | text | YES |  |
| artifact_size_bytes | bigint | YES |  |
| artifact_hash_reuse_justification | text | YES |  |
| framework | text | YES |  |
| framework_version | text | YES |  |
| preprocessing_profile_snapshot | jsonb | NO | CAST('{}' AS jsonb) |
| class_mapping | jsonb | NO | CAST('{}' AS jsonb) |
| input_signature | jsonb | NO | CAST('{}' AS jsonb) |
| output_signature | jsonb | NO | CAST('{}' AS jsonb) |
| status | text | NO | CAST('discovered' AS text) |
| lineage_status | text | NO | CAST('unresolved' AS text) |
| validated_at | timestamp with time zone | YES |  |
| approved_at | timestamp with time zone | YES |  |
| retired_at | timestamp with time zone | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.model_versions ADD CONSTRAINT model_versions_pkey CONSTRAINT model_versions_pkey PRIMARY KEY (id);
ALTER TABLE public.model_versions ADD CONSTRAINT chk_model_versions_artifact_requires_training CONSTRAINT chk_model_versions_artifact_requires_training CHECK (checkpoint_artifact_id IS NULL OR training_run_id IS NOT NULL);
ALTER TABLE public.model_versions ADD CONSTRAINT chk_model_versions_artifact_size CONSTRAINT chk_model_versions_artifact_size CHECK (artifact_size_bytes IS NULL OR artifact_size_bytes >= 0);
ALTER TABLE public.model_versions ADD CONSTRAINT chk_model_versions_governed_hash CONSTRAINT chk_model_versions_governed_hash CHECK (status <> ALL(ARRAY[CAST('candidate' AS text), CAST('validated' AS text), CAST('approved' AS text), CAST('deployed' AS text), CAST('rejected' AS text), CAST('retired' AS text)]) OR (checkpoint_artifact_id IS NOT NULL AND artifact_sha256 IS NOT NULL));
ALTER TABLE public.model_versions ADD CONSTRAINT chk_model_versions_lineage_status CONSTRAINT chk_model_versions_lineage_status CHECK (lineage_status = ANY(ARRAY[CAST('unresolved' AS text), CAST('resolved' AS text), CAST('ambiguous' AS text), CAST('artifact_missing' AS text), CAST('checksum_mismatch' AS text), CAST('legacy_unresolved' AS text)]));
ALTER TABLE public.model_versions ADD CONSTRAINT chk_model_versions_profile_objects CONSTRAINT chk_model_versions_profile_objects CHECK (jsonb_typeof(preprocessing_profile_snapshot) = CAST('object' AS text) AND jsonb_typeof(class_mapping) = CAST('object' AS text) AND jsonb_typeof(input_signature) = CAST('object' AS text) AND jsonb_typeof(output_signature) = CAST('object' AS text));
ALTER TABLE public.model_versions ADD CONSTRAINT chk_model_versions_resolved_training CONSTRAINT chk_model_versions_resolved_training CHECK (lineage_status <> CAST('resolved' AS text) OR training_run_id IS NOT NULL);
ALTER TABLE public.model_versions ADD CONSTRAINT chk_model_versions_sha256 CONSTRAINT chk_model_versions_sha256 CHECK (artifact_sha256 IS NULL OR artifact_sha256 ~ CAST('^[0-9a-f]{64}$' AS text));
ALTER TABLE public.model_versions ADD CONSTRAINT chk_model_versions_status CONSTRAINT chk_model_versions_status CHECK (status = ANY(ARRAY[CAST('discovered' AS text), CAST('candidate' AS text), CAST('validated' AS text), CAST('approved' AS text), CAST('deployed' AS text), CAST('rejected' AS text), CAST('retired' AS text)]));
ALTER TABLE public.model_versions ADD CONSTRAINT chk_model_versions_version_number CONSTRAINT chk_model_versions_version_number CHECK (version_number IS NULL OR version_number > 0);
ALTER TABLE public.model_versions ADD CONSTRAINT fk_model_versions_checkpoint_artifact_owner CONSTRAINT fk_model_versions_checkpoint_artifact_owner FOREIGN KEY (checkpoint_artifact_id, training_run_id) REFERENCES artifacts (id, run_id) ON DELETE RESTRICT;
ALTER TABLE public.model_versions ADD CONSTRAINT model_versions_model_id_fkey CONSTRAINT model_versions_model_id_fkey FOREIGN KEY (model_id) REFERENCES models (id) ON DELETE RESTRICT;
ALTER TABLE public.model_versions ADD CONSTRAINT model_versions_training_run_id_fkey CONSTRAINT model_versions_training_run_id_fkey FOREIGN KEY (training_run_id) REFERENCES runs (id) ON DELETE RESTRICT;
```

Índices explícitos: `uq_model_versions_id_checkpoint_artifact`, `uq_model_versions_id_training_run`, `idx_model_versions_checkpoint_artifact`, `idx_model_versions_model`, `idx_model_versions_sha256`, `idx_model_versions_status_lineage`, `idx_model_versions_training_run`, `uq_model_versions_checkpoint_artifact`, `uq_model_versions_name_number`, `uq_model_versions_training_version_name`, `uq_model_versions_unjustified_sha256`.
Auditoría: created_at, validated_at, approved_at, retired_at.
JSONB: metadata, preprocessing_profile_snapshot, class_mapping, input_signature, output_signature. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: artifact_sha256, artifact_hash_reuse_justification.

## models

Catálogo protegido de arquitecturas, tres modelos vigentes.

Dominio: D. Modelos. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| name | text | NO |  |
| model_type | text | NO |  |
| framework | text | YES |  |
| architecture | text | YES |  |
| description | text | YES |  |
| input_shape | text | YES |  |
| output_shape | text | YES |  |
| num_parameters | bigint | YES |  |
| pretrained | boolean | YES | FALSE |
| pretrained_source | text | YES |  |
| created_at | timestamp with time zone | YES | now() |
| metadata | jsonb | YES | CAST('{}' AS jsonb) |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.models ADD CONSTRAINT models_pkey CONSTRAINT models_pkey PRIMARY KEY (id);
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## predictions

Predicción ML/evaluación/inferencia trazable; v2 agrega evaluación y fuente científica tipadas.

Dominio: C. Imágenes / pacientes / splits. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| run_id | uuid | YES |  |
| dataset_id | uuid | YES |  |
| image_id | text | YES |  |
| image_path | text | YES |  |
| true_label | text | YES |  |
| predicted_label | text | YES |  |
| score | numeric | YES |  |
| score_positive_label | numeric | YES |  |
| threshold | numeric | YES |  |
| is_correct | boolean | YES |  |
| case_type | text | YES |  |
| created_at | timestamp with time zone | YES | now() |
| metadata | jsonb | YES | CAST('{}' AS jsonb) |
| image_analysis_job_id | uuid | YES |  |
| model_version_id | uuid | YES |  |
| deployed_model_version_id | uuid | YES |  |
| inference_run_id | uuid | YES |  |
| classifier_model_version_id | uuid | YES |  |
| detector_model_version_id | uuid | YES |  |
| prediction_scope | text | NO | CAST('legacy_image' AS text) |
| cell_index | integer | YES |  |
| source_image_id | uuid | YES |  |
| bbox_x | numeric | YES |  |
| bbox_y | numeric | YES |  |
| bbox_width | numeric | YES |  |
| bbox_height | numeric | YES |  |
| crop_artifact_id | uuid | YES |  |
| explanation_artifact_id | uuid | YES |  |
| probability_parasitized | numeric | YES |  |
| probability_uninfected | numeric | YES |  |
| threshold_used | numeric | YES |  |
| predicted_class | smallint | YES |  |
| confidence_level | text | YES |  |
| quality_status | text | YES |  |
| review_status | text | NO | CAST('unreviewed' AS text) |
| reviewed_label | text | YES |  |
| reviewed_by | text | YES |  |
| reviewed_at | timestamp with time zone | YES |  |
| evaluation_id | uuid | YES |  |
| dataset_source_record_id | uuid | YES |  |
| true_class | smallint | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.predictions ADD CONSTRAINT predictions_pkey CONSTRAINT predictions_pkey PRIMARY KEY (id);
ALTER TABLE public.predictions ADD CONSTRAINT uq_v2_evaluation_sample CONSTRAINT uq_v2_evaluation_sample UNIQUE (evaluation_id, dataset_source_record_id);
ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_bbox CONSTRAINT chk_predictions_bbox CHECK ((bbox_x IS NULL OR bbox_x >= CAST(0 AS numeric)) AND (bbox_y IS NULL OR bbox_y >= CAST(0 AS numeric)) AND (bbox_width IS NULL OR bbox_width > CAST(0 AS numeric)) AND (bbox_height IS NULL OR bbox_height > CAST(0 AS numeric)));
ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_cell_requirements CONSTRAINT chk_predictions_cell_requirements CHECK (prediction_scope <> CAST('cell' AS text) OR (image_analysis_job_id IS NOT NULL AND inference_run_id IS NOT NULL AND deployed_model_version_id IS NOT NULL AND model_version_id IS NOT NULL AND classifier_model_version_id IS NOT NULL AND model_version_id = classifier_model_version_id AND run_id IS NOT NULL AND run_id = inference_run_id AND cell_index IS NOT NULL AND cell_index >= 0 AND bbox_x IS NOT NULL AND bbox_y IS NOT NULL AND bbox_width IS NOT NULL AND bbox_height IS NOT NULL AND probability_parasitized IS NOT NULL AND probability_uninfected IS NOT NULL AND threshold_used IS NOT NULL AND predicted_class IS NOT NULL AND predicted_label IS NOT NULL));
ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_class_label CONSTRAINT chk_predictions_class_label CHECK (predicted_class IS NULL OR (predicted_class = 0 AND predicted_label = CAST('uninfected' AS text)) OR (predicted_class = 1 AND predicted_label = CAST('parasitized' AS text)));
ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_confidence_level CONSTRAINT chk_predictions_confidence_level CHECK (confidence_level IS NULL OR confidence_level = ANY(ARRAY[CAST('low' AS text), CAST('medium' AS text), CAST('high' AS text), CAST('uncertain' AS text), CAST('not_assessed' AS text)]));
ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_predicted_class CONSTRAINT chk_predictions_predicted_class CHECK (predicted_class IS NULL OR predicted_class = ANY(ARRAY[0, 1]));
ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_probability_parasitized CONSTRAINT chk_predictions_probability_parasitized CHECK (probability_parasitized IS NULL OR (probability_parasitized >= CAST(0 AS numeric) AND probability_parasitized <= CAST(1 AS numeric)));
ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_probability_uninfected CONSTRAINT chk_predictions_probability_uninfected CHECK (probability_uninfected IS NULL OR (probability_uninfected >= CAST(0 AS numeric) AND probability_uninfected <= CAST(1 AS numeric)));
ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_quality_status CONSTRAINT chk_predictions_quality_status CHECK (quality_status IS NULL OR quality_status = ANY(ARRAY[CAST('not_assessed' AS text), CAST('pending' AS text), CAST('passed' AS text), CAST('warning' AS text), CAST('rejected' AS text), CAST('failed' AS text), CAST('skipped' AS text)]));
ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_review_status CONSTRAINT chk_predictions_review_status CHECK (review_status = ANY(ARRAY[CAST('unreviewed' AS text), CAST('pending' AS text), CAST('confirmed' AS text), CAST('corrected' AS text), CAST('rejected' AS text)]));
ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_reviewed_label CONSTRAINT chk_predictions_reviewed_label CHECK (reviewed_label IS NULL OR reviewed_label = ANY(ARRAY[CAST('uninfected' AS text), CAST('parasitized' AS text)]));
ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_scope CONSTRAINT chk_predictions_scope CHECK (prediction_scope = ANY(ARRAY[CAST('legacy_image' AS text), CAST('image' AS text), CAST('cell' AS text)]));
ALTER TABLE public.predictions ADD CONSTRAINT chk_predictions_threshold_used CONSTRAINT chk_predictions_threshold_used CHECK (threshold_used IS NULL OR (threshold_used >= CAST(0 AS numeric) AND threshold_used <= CAST(1 AS numeric)));
ALTER TABLE public.predictions ADD CONSTRAINT fk_predictions_analysis_job CONSTRAINT fk_predictions_analysis_job FOREIGN KEY (image_analysis_job_id) REFERENCES image_analysis_jobs (id) ON DELETE RESTRICT;
ALTER TABLE public.predictions ADD CONSTRAINT fk_predictions_classifier_model_version CONSTRAINT fk_predictions_classifier_model_version FOREIGN KEY (classifier_model_version_id) REFERENCES model_versions (id) ON DELETE RESTRICT;
ALTER TABLE public.predictions ADD CONSTRAINT fk_predictions_crop_artifact CONSTRAINT fk_predictions_crop_artifact FOREIGN KEY (crop_artifact_id) REFERENCES artifacts (id) ON DELETE RESTRICT;
ALTER TABLE public.predictions ADD CONSTRAINT fk_predictions_deployed_model_version CONSTRAINT fk_predictions_deployed_model_version FOREIGN KEY (deployed_model_version_id) REFERENCES deployed_model_versions (id) ON DELETE RESTRICT;
ALTER TABLE public.predictions ADD CONSTRAINT fk_predictions_detector_model_version CONSTRAINT fk_predictions_detector_model_version FOREIGN KEY (detector_model_version_id) REFERENCES model_versions (id) ON DELETE RESTRICT;
ALTER TABLE public.predictions ADD CONSTRAINT fk_predictions_explanation_artifact CONSTRAINT fk_predictions_explanation_artifact FOREIGN KEY (explanation_artifact_id) REFERENCES artifacts (id) ON DELETE RESTRICT;
ALTER TABLE public.predictions ADD CONSTRAINT fk_predictions_inference_run CONSTRAINT fk_predictions_inference_run FOREIGN KEY (inference_run_id) REFERENCES runs (id) ON DELETE RESTRICT;
ALTER TABLE public.predictions ADD CONSTRAINT fk_predictions_job_provenance CONSTRAINT fk_predictions_job_provenance FOREIGN KEY (image_analysis_job_id, inference_run_id, deployed_model_version_id, model_version_id) REFERENCES image_analysis_jobs (id, inference_run_id, deployed_model_version_id, model_version_id) ON DELETE RESTRICT;
ALTER TABLE public.predictions ADD CONSTRAINT fk_predictions_model_version CONSTRAINT fk_predictions_model_version FOREIGN KEY (model_version_id) REFERENCES model_versions (id) ON DELETE RESTRICT;
ALTER TABLE public.predictions ADD CONSTRAINT fk_predictions_source_image CONSTRAINT fk_predictions_source_image FOREIGN KEY (source_image_id) REFERENCES dataset_split_images (image_id) ON DELETE RESTRICT;
ALTER TABLE public.predictions ADD CONSTRAINT predictions_dataset_id_fkey CONSTRAINT predictions_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE RESTRICT;
ALTER TABLE public.predictions ADD CONSTRAINT predictions_run_id_fkey CONSTRAINT predictions_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;
ALTER TABLE public.predictions ADD CONSTRAINT fk_v2_prediction_evaluation_run CONSTRAINT fk_v2_prediction_evaluation_run FOREIGN KEY (evaluation_id, run_id) REFERENCES public.evaluations (id, run_id) ON DELETE RESTRICT;
ALTER TABLE public.predictions ADD CONSTRAINT ck_v2_prediction_sample CONSTRAINT ck_v2_prediction_sample CHECK (evaluation_id IS NULL OR (run_id IS NOT NULL AND dataset_source_record_id IS NOT NULL AND true_class IS NOT NULL));
ALTER TABLE public.predictions ADD CONSTRAINT v2_predictions_foreign_a402d28a70f6 CONSTRAINT v2_predictions_foreign_a402d28a70f6 FOREIGN KEY (evaluation_id) REFERENCES public.evaluations (id) ON DELETE RESTRICT;
ALTER TABLE public.predictions ADD CONSTRAINT v2_predictions_foreign_e8d9af78807c CONSTRAINT v2_predictions_foreign_e8d9af78807c FOREIGN KEY (dataset_source_record_id) REFERENCES public.dataset_source_records (id) ON DELETE RESTRICT;
ALTER TABLE public.predictions ADD CONSTRAINT v2_predictions_check_bcedf284d6cb CONSTRAINT v2_predictions_check_bcedf284d6cb CHECK (true_class IN (0, 1));
```

Índices explícitos: `idx_predictions_analysis_job`, `idx_predictions_case_type`, `idx_predictions_case_type_run`, `idx_predictions_classifier_model_version`, `idx_predictions_created_at`, `idx_predictions_deployed_model_version`, `idx_predictions_detector_model_version`, `idx_predictions_inference_run`, `idx_predictions_metadata_source`, `idx_predictions_metadata_workflow`, `idx_predictions_model_version`, `idx_predictions_predicted_label`, `idx_predictions_review_status`, `idx_predictions_run_id`, `idx_predictions_true_pred`, `uq_predictions_job_cell_index`.
Auditoría: created_at, reviewed_at.
JSONB: metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: source_image_id, dataset_source_record_id.

## quality_assessment_queue_items

Cola e identidad del trabajo QC, reintentos y estado técnico.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| analysis_run_id | uuid | NO |  |
| priority | smallint | NO | 50 |
| status | varchar(20) | NO | CAST('queued' AS varchar) |
| requested_by | uuid | NO |  |
| requested_at | timestamp with time zone | NO | now() |
| started_at | timestamp with time zone | YES |  |
| completed_at | timestamp with time zone | YES |  |
| failed_at | timestamp with time zone | YES |  |
| attempt_count | integer | NO | 0 |
| last_error_code | varchar(80) | YES |  |
| last_error_message | text | YES |  |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.quality_assessment_queue_items ADD CONSTRAINT quality_assessment_queue_items_pkey CONSTRAINT quality_assessment_queue_items_pkey PRIMARY KEY (id);
ALTER TABLE public.quality_assessment_queue_items ADD CONSTRAINT quality_assessment_queue_items_attempt_count_check CONSTRAINT quality_assessment_queue_items_attempt_count_check CHECK (attempt_count >= 0);
ALTER TABLE public.quality_assessment_queue_items ADD CONSTRAINT quality_assessment_queue_items_priority_check CONSTRAINT quality_assessment_queue_items_priority_check CHECK (priority = ANY(ARRAY[1, 50, 100]));
ALTER TABLE public.quality_assessment_queue_items ADD CONSTRAINT quality_assessment_queue_items_status_check CONSTRAINT quality_assessment_queue_items_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('queued' AS varchar) AS text), CAST(CAST('running' AS varchar) AS text), CAST(CAST('completed' AS varchar) AS text), CAST(CAST('failed' AS varchar) AS text)]));
ALTER TABLE public.quality_assessment_queue_items ADD CONSTRAINT quality_assessment_queue_items_analysis_run_id_fkey CONSTRAINT quality_assessment_queue_items_analysis_run_id_fkey FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs (id) ON DELETE RESTRICT;
ALTER TABLE public.quality_assessment_queue_items ADD CONSTRAINT quality_assessment_queue_items_requested_by_fkey CONSTRAINT quality_assessment_queue_items_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES users (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_quality_queue_order`, `ix_quality_queue_priority_requested`, `uq_quality_queue_active_run`.
Auditoría: requested_at, started_at, completed_at, failed_at, created_at, updated_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## quality_gate_decisions

Decisión del gate QC y política aplicada para permitir etapas posteriores.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| analysis_run_id | uuid | NO |  |
| decision | varchar(30) | NO |  |
| comment | text | NO |  |
| actor_user_id | uuid | NO |  |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.quality_gate_decisions ADD CONSTRAINT quality_gate_decisions_pkey CONSTRAINT quality_gate_decisions_pkey PRIMARY KEY (id);
ALTER TABLE public.quality_gate_decisions ADD CONSTRAINT quality_gate_decisions_comment_check CONSTRAINT quality_gate_decisions_comment_check CHECK (length(btrim(comment)) > 0);
ALTER TABLE public.quality_gate_decisions ADD CONSTRAINT quality_gate_decisions_decision_check CONSTRAINT quality_gate_decisions_decision_check CHECK (CAST(decision AS text) = ANY(ARRAY[CAST(CAST('approve_with_warnings' AS varchar) AS text), CAST(CAST('reject' AS varchar) AS text)]));
ALTER TABLE public.quality_gate_decisions ADD CONSTRAINT quality_gate_decisions_actor_user_id_fkey CONSTRAINT quality_gate_decisions_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.quality_gate_decisions ADD CONSTRAINT quality_gate_decisions_analysis_run_id_fkey CONSTRAINT quality_gate_decisions_analysis_run_id_fkey FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_quality_gate_decisions_run`.
Auditoría: actor_user_id, created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## research_subjects

Sujeto del dominio clínico/investigación; no recrear identidades científicas del split.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| subject_code | varchar(120) | NO |  |
| study_reference | varchar(200) | YES |  |
| age_group | varchar(80) | YES |  |
| biological_sex | varchar(80) | YES |  |
| metadata_json | jsonb | NO | CAST('{}' AS jsonb) |
| status | varchar(20) | NO | CAST('active' AS varchar) |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |
| created_by | uuid | YES |  |
| updated_by | uuid | YES |  |
| archived_at | timestamp with time zone | YES |  |
| archived_by | uuid | YES |  |
| source_system | varchar(120) | YES |  |
| external_patient_id | varchar(240) | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.research_subjects ADD CONSTRAINT research_subjects_pkey CONSTRAINT research_subjects_pkey PRIMARY KEY (id);
ALTER TABLE public.research_subjects ADD CONSTRAINT research_subjects_subject_code_key CONSTRAINT research_subjects_subject_code_key UNIQUE (subject_code);
ALTER TABLE public.research_subjects ADD CONSTRAINT ck_research_subject_archive_state CONSTRAINT ck_research_subject_archive_state CHECK ((CAST(status AS text) = CAST('active' AS text) AND archived_at IS NULL AND archived_by IS NULL) OR (CAST(status AS text) = CAST('archived' AS text) AND archived_at IS NOT NULL));
ALTER TABLE public.research_subjects ADD CONSTRAINT research_subjects_metadata_json_check CONSTRAINT research_subjects_metadata_json_check CHECK (jsonb_typeof(metadata_json) = CAST('object' AS text));
ALTER TABLE public.research_subjects ADD CONSTRAINT research_subjects_status_check CONSTRAINT research_subjects_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('active' AS varchar) AS text), CAST(CAST('archived' AS varchar) AS text)]));
ALTER TABLE public.research_subjects ADD CONSTRAINT research_subjects_subject_code_check CONSTRAINT research_subjects_subject_code_check CHECK (btrim(CAST(subject_code AS text)) <> CAST('' AS text));
ALTER TABLE public.research_subjects ADD CONSTRAINT research_subjects_archived_by_fkey CONSTRAINT research_subjects_archived_by_fkey FOREIGN KEY (archived_by) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.research_subjects ADD CONSTRAINT research_subjects_created_by_fkey CONSTRAINT research_subjects_created_by_fkey FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.research_subjects ADD CONSTRAINT research_subjects_updated_by_fkey CONSTRAINT research_subjects_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_research_subjects_status_created`, `uq_research_subjects_external_identity`.
Auditoría: created_at, updated_at, created_by, updated_by, archived_at.
JSONB: metadata_json. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: source_system.

## roles

Roles de autenticación protegidos, no modificar por añadir XAI.

Dominio: A. Usuarios / seguridad. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| name | text | NO |  |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.roles ADD CONSTRAINT roles_pkey CONSTRAINT roles_pkey PRIMARY KEY (id);
ALTER TABLE public.roles ADD CONSTRAINT roles_name_key CONSTRAINT roles_name_key UNIQUE (name);
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## run_checkpoint_policy

Selección de checkpoint, monitor/criterios/warnings y binding a versión/artefacto.

Dominio: E. Model versions / checkpoints. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| run_checkpoint_policy_id | uuid | NO | pg_catalog.gen_random_uuid() |
| run_id | uuid | NO |  |
| model_name | text | YES |  |
| checkpoint_policy | text | NO |  |
| checkpoint_policy_config | jsonb | NO | CAST('{}' AS jsonb) |
| selected_epoch | integer | YES |  |
| policy_satisfied | boolean | YES |  |
| selected_metric | text | YES |  |
| selected_metric_value | numeric | YES |  |
| min_recall_required | numeric | YES |  |
| val_recall_parasitized_selected | numeric | YES |  |
| val_f2_parasitized_selected | numeric | YES |  |
| val_specificity_selected | numeric | YES |  |
| val_auc_selected | numeric | YES |  |
| val_pr_auc_selected | numeric | YES |  |
| val_balanced_accuracy_selected | numeric | YES |  |
| prediction_collapse_detected | boolean | YES |  |
| all_epochs_collapsed | boolean | YES |  |
| checkpoint_warning | text | YES |  |
| checkpoint_path | text | YES |  |
| checkpoint_policy_summary_path | text | YES |  |
| model_metadata_path | text | YES |  |
| created_at | timestamp with time zone | NO | now() |
| metadata | jsonb | NO | CAST('{}' AS jsonb) |
| model_version_id | uuid | YES |  |
| checkpoint_artifact_id | uuid | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.run_checkpoint_policy ADD CONSTRAINT run_checkpoint_policy_pkey CONSTRAINT run_checkpoint_policy_pkey PRIMARY KEY (run_checkpoint_policy_id);
ALTER TABLE public.run_checkpoint_policy ADD CONSTRAINT fk_run_checkpoint_policy_artifact_owner CONSTRAINT fk_run_checkpoint_policy_artifact_owner FOREIGN KEY (checkpoint_artifact_id, run_id) REFERENCES artifacts (id, run_id) ON DELETE RESTRICT;
ALTER TABLE public.run_checkpoint_policy ADD CONSTRAINT fk_run_checkpoint_policy_model_version_owner CONSTRAINT fk_run_checkpoint_policy_model_version_owner FOREIGN KEY (model_version_id, run_id) REFERENCES model_versions (id, training_run_id) ON DELETE RESTRICT;
ALTER TABLE public.run_checkpoint_policy ADD CONSTRAINT fk_run_checkpoint_policy_version_artifact CONSTRAINT fk_run_checkpoint_policy_version_artifact FOREIGN KEY (model_version_id, checkpoint_artifact_id) REFERENCES model_versions (id, checkpoint_artifact_id) ON DELETE RESTRICT;
ALTER TABLE public.run_checkpoint_policy ADD CONSTRAINT run_checkpoint_policy_run_id_fkey CONSTRAINT run_checkpoint_policy_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;
```

Índices explícitos: `idx_run_checkpoint_policy_artifact`, `idx_run_checkpoint_policy_model_version`, `idx_run_checkpoint_policy_run_id`.
Auditoría: created_at.
JSONB: checkpoint_policy_config, metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## run_clinical_metrics

Única medición binaria por evaluación: conteos, tasas, AUC, aliases controlados y razones NULL.

Dominio: L. Métricas clínicas. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| run_clinical_metric_id | uuid | NO | pg_catalog.gen_random_uuid() |
| run_id | uuid | NO |  |
| model_id | uuid | YES |  |
| model_name | text | YES |  |
| split_name | text | NO |  |
| threshold_used | numeric | YES |  |
| threshold_source | text | YES |  |
| accuracy | numeric | YES |  |
| precision_parasitized | numeric | YES |  |
| recall_parasitized | numeric | YES |  |
| sensitivity_parasitized | numeric | YES |  |
| specificity | numeric | YES |  |
| f1_parasitized | numeric | YES |  |
| f2_parasitized | numeric | YES |  |
| roc_auc_parasitized | numeric | YES |  |
| pr_auc_parasitized | numeric | YES |  |
| balanced_accuracy | numeric | YES |  |
| tn | bigint | NO |  |
| fp | bigint | NO |  |
| fn | bigint | NO |  |
| tp | bigint | NO |  |
| confusion_matrix | jsonb | NO | CAST('[]' AS jsonb) |
| classification_report | jsonb | NO | CAST('{}' AS jsonb) |
| prediction_distribution | jsonb | NO | CAST('{}' AS jsonb) |
| prediction_collapse | jsonb | NO | CAST('{}' AS jsonb) |
| label_mapping_version | text | NO | CAST('clinical_v1_parasitized_positive' AS text) |
| raw_model_score_meaning | text | NO | CAST('probability_parasitized' AS text) |
| created_at | timestamp with time zone | NO | now() |
| metadata | jsonb | NO | CAST('{}' AS jsonb) |
| evaluation_id | uuid | NO |  |
| sample_count | numeric | YES | GENERATED ALWAYS AS (CAST(tn AS numeric) + fp + fn + tp) STORED |
| auc_unavailability_reason | text | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT run_clinical_metrics_pkey CONSTRAINT run_clinical_metrics_pkey PRIMARY KEY (run_clinical_metric_id);
ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT v2_run_clinical_metrics_unique_f9437c271ff6 CONSTRAINT v2_run_clinical_metrics_unique_f9437c271ff6 UNIQUE (evaluation_id);
ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT chk_run_clinical_metrics_split CONSTRAINT chk_run_clinical_metrics_split CHECK (split_name = ANY(ARRAY[CAST('train' AS text), CAST('val' AS text), CAST('validation' AS text), CAST('test' AS text), CAST('external' AS text)]));
ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT run_clinical_metrics_model_id_fkey CONSTRAINT run_clinical_metrics_model_id_fkey FOREIGN KEY (model_id) REFERENCES models (id) ON DELETE RESTRICT;
ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT run_clinical_metrics_run_id_fkey CONSTRAINT run_clinical_metrics_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;
ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT fk_metric_evaluation_run CONSTRAINT fk_metric_evaluation_run FOREIGN KEY (evaluation_id, run_id) REFERENCES public.evaluations (id, run_id) ON DELETE RESTRICT;
ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT ck_v2_binary_counts CONSTRAINT ck_v2_binary_counts CHECK (tn >= 0 AND fp >= 0 AND fn >= 0 AND tp >= 0 AND (CAST(tn AS numeric) + fp + fn + tp) > 0);
ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT ck_v2_auc_domain CONSTRAINT ck_v2_auc_domain CHECK ((roc_auc_parasitized IS NULL OR (roc_auc_parasitized >= 0 AND roc_auc_parasitized <= 1)) AND (pr_auc_parasitized IS NULL OR (pr_auc_parasitized >= 0 AND pr_auc_parasitized <= 1)));
ALTER TABLE public.run_clinical_metrics ADD CONSTRAINT ck_v2_auc_reason CONSTRAINT ck_v2_auc_reason CHECK ((roc_auc_parasitized IS NOT NULL AND pr_auc_parasitized IS NOT NULL AND auc_unavailability_reason IS NULL) OR ((roc_auc_parasitized IS NULL OR pr_auc_parasitized IS NULL) AND auc_unavailability_reason IS NOT NULL AND auc_unavailability_reason IN ('single_class', 'scores_unavailable', 'not_computed')));
```

Índices explícitos: `idx_run_clinical_metrics_model_name`, `idx_run_clinical_metrics_run_id`, `idx_run_clinical_metrics_split_name`.
Auditoría: created_at.
JSONB: confusion_matrix, classification_report, prediction_distribution, prediction_collapse, metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## run_configurations

Configuración científica efectiva, tipada e inmutable de cada TRAIN.

Dominio: H. Run configurations. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| run_id | uuid | NO |  |
| architecture | text | NO |  |
| adapter_version | text | NO |  |
| optimizer | text | NO |  |
| learning_rate | double precision | NO |  |
| fine_tune_learning_rate | double precision | NO |  |
| batch_size | integer | NO |  |
| random_seed | bigint | NO |  |
| max_epochs | integer | NO |  |
| fine_tune_epochs | integer | NO |  |
| early_stopping | boolean | NO |  |
| early_stopping_patience | integer | NO |  |
| early_stopping_min_delta | double precision | NO |  |
| early_stopping_monitor | text | NO |  |
| early_stopping_mode | text | NO |  |
| restore_best_weights | boolean | NO |  |
| checkpoint_monitor | text | NO |  |
| checkpoint_mode | text | NO |  |
| dropout | double precision | NO |  |
| l2 | double precision | NO |  |
| input_height | integer | NO |  |
| input_width | integer | NO |  |
| input_channels | integer | NO |  |
| weights | text | NO |  |
| fine_tune_layers | integer | NO |  |
| normalization | text | NO |  |
| internal_preprocessing | text | YES |  |
| loss_function | text | NO |  |
| calibration_enabled | boolean | NO | FALSE |
| default_threshold | numeric | NO | 0.5 |
| clinical_target_recall | numeric | NO |  |
| configuration_hash | text | NO |  |
| canonical_configuration | text | NO |  |
| optimizer_extensions | jsonb | NO | '{}' |
| extension_configuration | jsonb | NO | '{}' |
| provenance_snapshot | jsonb | NO |  |
| created_at | timestamptz | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_primary_360aa242ca7c CONSTRAINT v2_run_configurations_primary_360aa242ca7c PRIMARY KEY (run_id);
ALTER TABLE public.run_configurations ADD CONSTRAINT ck_v2_config_hash CONSTRAINT ck_v2_config_hash CHECK (configuration_hash = encode(digest(canonical_configuration, 'sha256'), 'hex'));
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_foreign_db5338c19de4 CONSTRAINT v2_run_configurations_foreign_db5338c19de4 FOREIGN KEY (run_id) REFERENCES public.runs (id) ON DELETE RESTRICT;
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_cf7585e198d6 CONSTRAINT v2_run_configurations_check_cf7585e198d6 CHECK (architecture IN ('custom_cnn', 'vgg16', 'densenet121'));
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_580e3e6c54f3 CONSTRAINT v2_run_configurations_check_580e3e6c54f3 CHECK (optimizer IN ('adam', 'adamw', 'sgd', 'adadelta'));
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_ced6e7c6097c CONSTRAINT v2_run_configurations_check_ced6e7c6097c CHECK (learning_rate > 0 AND learning_rate < CAST('Infinity' AS float8));
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_ddd84a2faca3 CONSTRAINT v2_run_configurations_check_ddd84a2faca3 CHECK (fine_tune_learning_rate > 0 AND fine_tune_learning_rate < CAST('Infinity' AS float8));
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_a447b286c925 CONSTRAINT v2_run_configurations_check_a447b286c925 CHECK (batch_size > 0);
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_b4ca1fd48d76 CONSTRAINT v2_run_configurations_check_b4ca1fd48d76 CHECK (random_seed >= 0);
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_2df57f7a8f77 CONSTRAINT v2_run_configurations_check_2df57f7a8f77 CHECK (max_epochs > 0);
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_7bcf16f32f16 CONSTRAINT v2_run_configurations_check_7bcf16f32f16 CHECK (fine_tune_epochs >= 0);
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_998aa974aff8 CONSTRAINT v2_run_configurations_check_998aa974aff8 CHECK (early_stopping_patience >= 0);
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_ab6239fe6a31 CONSTRAINT v2_run_configurations_check_ab6239fe6a31 CHECK (early_stopping_min_delta >= 0 AND early_stopping_min_delta < CAST('Infinity' AS float8));
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_f121e8cce088 CONSTRAINT v2_run_configurations_check_f121e8cce088 CHECK (early_stopping_mode IN ('min', 'max'));
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_2131e4191e29 CONSTRAINT v2_run_configurations_check_2131e4191e29 CHECK (checkpoint_mode IN ('min', 'max'));
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_eee102ab78dd CONSTRAINT v2_run_configurations_check_eee102ab78dd CHECK (dropout >= 0 AND dropout < 1);
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_ea943e1f4322 CONSTRAINT v2_run_configurations_check_ea943e1f4322 CHECK (l2 >= 0 AND l2 < 1);
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_46e293269ce9 CONSTRAINT v2_run_configurations_check_46e293269ce9 CHECK (input_height >= 32);
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_f91cdd45746e CONSTRAINT v2_run_configurations_check_f91cdd45746e CHECK (input_width = input_height);
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_25a4140a88de CONSTRAINT v2_run_configurations_check_25a4140a88de CHECK (input_channels = 3);
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_4face7ed3946 CONSTRAINT v2_run_configurations_check_4face7ed3946 CHECK (weights IN ('none', 'imagenet'));
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_80bf078e8ac1 CONSTRAINT v2_run_configurations_check_80bf078e8ac1 CHECK (fine_tune_layers >= 0);
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_278a5e3294ac CONSTRAINT v2_run_configurations_check_278a5e3294ac CHECK (default_threshold = 0.5);
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_d6094850fee4 CONSTRAINT v2_run_configurations_check_d6094850fee4 CHECK (clinical_target_recall > 0 AND clinical_target_recall <= 1);
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_3321a4aaab96 CONSTRAINT v2_run_configurations_check_3321a4aaab96 CHECK (configuration_hash ~ '^[0-9a-f]{64}$');
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_3f8c4617855a CONSTRAINT v2_run_configurations_check_3f8c4617855a CHECK (jsonb_typeof(optimizer_extensions) = 'object');
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_f31c0727c3ef CONSTRAINT v2_run_configurations_check_f31c0727c3ef CHECK (jsonb_typeof(extension_configuration) = 'object');
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_eb0d0af834a3 CONSTRAINT v2_run_configurations_check_eb0d0af834a3 CHECK (jsonb_typeof(provenance_snapshot) = 'object');
ALTER TABLE public.run_configurations ADD CONSTRAINT v2_run_configurations_check_63e4a55e1de0 CONSTRAINT v2_run_configurations_check_63e4a55e1de0 CHECK ((architecture = 'vgg16' AND normalization = 'vgg16_imagenet' AND internal_preprocessing IS NULL) OR (architecture = 'custom_cnn' AND normalization = 'rescale_0_1' AND internal_preprocessing IS NULL) OR (architecture = 'densenet121' AND normalization = 'rescale_0_1' AND internal_preprocessing = 'densenet_imagenet_channel_mean_std'));
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: optimizer_extensions, extension_configuration, provenance_snapshot. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: configuration_hash, canonical_configuration, provenance_snapshot.

## run_dataset_images

Uso efectivo de imagen física por run y contexto TRAIN/val/evaluate/inference.

Dominio: C. Imágenes / pacientes / splits. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| run_dataset_image_id | uuid | NO | pg_catalog.gen_random_uuid() |
| run_id | uuid | NO |  |
| image_id | uuid | NO |  |
| split_name | text | NO |  |
| usage_context | text | NO |  |
| class_index | integer | NO |  |
| class_name | text | NO |  |
| relative_path | text | NO |  |
| filename | text | NO |  |
| batch_index | integer | YES |  |
| sample_index | integer | YES |  |
| used_for_training | boolean | NO | FALSE |
| used_for_validation | boolean | NO | FALSE |
| used_for_test | boolean | NO | FALSE |
| created_at | timestamp with time zone | NO | now() |
| metadata | jsonb | NO | CAST('{}' AS jsonb) |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.run_dataset_images ADD CONSTRAINT run_dataset_images_pkey CONSTRAINT run_dataset_images_pkey PRIMARY KEY (run_dataset_image_id);
ALTER TABLE public.run_dataset_images ADD CONSTRAINT uq_run_dataset_images_usage CONSTRAINT uq_run_dataset_images_usage UNIQUE (run_id, image_id, usage_context);
ALTER TABLE public.run_dataset_images ADD CONSTRAINT chk_run_dataset_images_class_index CONSTRAINT chk_run_dataset_images_class_index CHECK (class_index = ANY(ARRAY[0, 1]));
ALTER TABLE public.run_dataset_images ADD CONSTRAINT chk_run_dataset_images_class_name CONSTRAINT chk_run_dataset_images_class_name CHECK (class_name = ANY(ARRAY[CAST('uninfected' AS text), CAST('parasitized' AS text)]));
ALTER TABLE public.run_dataset_images ADD CONSTRAINT chk_run_dataset_images_split CONSTRAINT chk_run_dataset_images_split CHECK (split_name = ANY(ARRAY[CAST('train' AS text), CAST('val' AS text), CAST('validation' AS text), CAST('test' AS text)]));
ALTER TABLE public.run_dataset_images ADD CONSTRAINT chk_run_dataset_images_usage_context CONSTRAINT chk_run_dataset_images_usage_context CHECK (usage_context = ANY(ARRAY[CAST('train' AS text), CAST('validation' AS text), CAST('evaluation' AS text), CAST('explainability' AS text), CAST('tta' AS text), CAST('ensemble' AS text), CAST('svm_features' AS text), CAST('inference' AS text)]));
ALTER TABLE public.run_dataset_images ADD CONSTRAINT run_dataset_images_image_id_fkey CONSTRAINT run_dataset_images_image_id_fkey FOREIGN KEY (image_id) REFERENCES dataset_split_images (image_id) ON DELETE RESTRICT;
ALTER TABLE public.run_dataset_images ADD CONSTRAINT run_dataset_images_run_id_fkey CONSTRAINT run_dataset_images_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;
```

Índices explícitos: `idx_run_dataset_images_image_id`, `idx_run_dataset_images_run_id`, `idx_run_dataset_images_split`, `idx_run_dataset_images_usage_context`.
Auditoría: created_at.
JSONB: metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## run_image_predictions

Trazabilidad de imagen/predicción específica del contrato clínico de tracking histórico.

Dominio: C. Imágenes / pacientes / splits. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| run_image_prediction_id | uuid | NO | pg_catalog.gen_random_uuid() |
| run_id | uuid | NO |  |
| image_id | uuid | YES |  |
| split_name | text | YES |  |
| usage_context | text | YES |  |
| filename | text | YES |  |
| relative_path | text | YES |  |
| true_label | integer | YES |  |
| true_label_name | text | YES |  |
| predicted_label | integer | YES |  |
| predicted_label_name | text | YES |  |
| probability_parasitized | numeric | YES |  |
| probability_uninfected | numeric | YES |  |
| raw_model_score | numeric | YES |  |
| raw_model_score_meaning | text | NO | CAST('probability_parasitized' AS text) |
| threshold_used | numeric | YES |  |
| threshold_source | text | YES |  |
| is_correct | boolean | YES |  |
| case_type | text | YES |  |
| metadata | jsonb | NO | CAST('{}' AS jsonb) |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.run_image_predictions ADD CONSTRAINT run_image_predictions_pkey CONSTRAINT run_image_predictions_pkey PRIMARY KEY (run_image_prediction_id);
ALTER TABLE public.run_image_predictions ADD CONSTRAINT chk_run_image_predictions_case_type CONSTRAINT chk_run_image_predictions_case_type CHECK (case_type IS NULL OR case_type = ANY(ARRAY[CAST('true_positive' AS text), CAST('true_negative' AS text), CAST('false_positive' AS text), CAST('false_negative' AS text), CAST('low_confidence' AS text), CAST('unknown' AS text)]));
ALTER TABLE public.run_image_predictions ADD CONSTRAINT chk_run_image_predictions_split CONSTRAINT chk_run_image_predictions_split CHECK (split_name IS NULL OR split_name = ANY(ARRAY[CAST('train' AS text), CAST('val' AS text), CAST('validation' AS text), CAST('test' AS text), CAST('external' AS text)]));
ALTER TABLE public.run_image_predictions ADD CONSTRAINT chk_run_image_predictions_usage_context CONSTRAINT chk_run_image_predictions_usage_context CHECK (usage_context IS NULL OR usage_context = ANY(ARRAY[CAST('train' AS text), CAST('validation' AS text), CAST('evaluation' AS text), CAST('explainability' AS text), CAST('tta' AS text), CAST('ensemble' AS text), CAST('svm_features' AS text), CAST('inference' AS text)]));
ALTER TABLE public.run_image_predictions ADD CONSTRAINT run_image_predictions_image_id_fkey CONSTRAINT run_image_predictions_image_id_fkey FOREIGN KEY (image_id) REFERENCES dataset_split_images (image_id) ON DELETE RESTRICT;
ALTER TABLE public.run_image_predictions ADD CONSTRAINT run_image_predictions_run_id_fkey CONSTRAINT run_image_predictions_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;
```

Índices explícitos: `idx_run_image_predictions_case_type`, `idx_run_image_predictions_run_id`, `idx_run_image_predictions_split`.
Auditoría: created_at.
JSONB: metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## run_io_records

Manifiestos de entradas/salidas de run y evidencia de dataset/modelo/preprocessing.

Dominio: Q. Auditoría y trazabilidad técnica. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| run_io_id | uuid | NO | pg_catalog.gen_random_uuid() |
| run_id | uuid | NO |  |
| script_name | text | NO |  |
| command | text | YES |  |
| input_parameters | jsonb | NO | CAST('{}' AS jsonb) |
| output_results | jsonb | NO | CAST('{}' AS jsonb) |
| output_artifacts | jsonb | NO | CAST('[]' AS jsonb) |
| dataset_metadata | jsonb | NO | CAST('{}' AS jsonb) |
| label_mapping_version | text | NO | CAST('clinical_v1_parasitized_positive' AS text) |
| raw_model_score_meaning | text | YES | CAST('probability_parasitized' AS text) |
| created_at | timestamp with time zone | NO | now() |
| metadata | jsonb | NO | CAST('{}' AS jsonb) |
| run_type | text | YES |  |
| model_name | text | YES |  |
| model_metadata | jsonb | NO | CAST('{}' AS jsonb) |
| clinical_metadata | jsonb | NO | CAST('{}' AS jsonb) |
| dataset_version_id | uuid | YES |  |
| dataset_materialization_id | uuid | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.run_io_records ADD CONSTRAINT run_io_records_pkey CONSTRAINT run_io_records_pkey PRIMARY KEY (run_io_id);
ALTER TABLE public.run_io_records ADD CONSTRAINT run_io_records_dataset_materialization_id_fkey CONSTRAINT run_io_records_dataset_materialization_id_fkey FOREIGN KEY (dataset_materialization_id) REFERENCES dataset_materializations (id) ON DELETE RESTRICT;
ALTER TABLE public.run_io_records ADD CONSTRAINT run_io_records_dataset_version_id_fkey CONSTRAINT run_io_records_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;
ALTER TABLE public.run_io_records ADD CONSTRAINT run_io_records_run_id_fkey CONSTRAINT run_io_records_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;
```

Índices explícitos: `idx_run_io_records_clinical_metadata_gin`, `idx_run_io_records_created_at`, `idx_run_io_records_model_metadata_gin`, `idx_run_io_records_model_name`, `idx_run_io_records_run_id`, `idx_run_io_records_run_type`, `idx_run_io_records_script_name`, `ix_run_io_records_dataset_materialization_id`, `ix_run_io_records_dataset_version_id`.
Auditoría: created_at.
JSONB: input_parameters, output_results, output_artifacts, dataset_metadata, metadata, model_metadata, clinical_metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## run_lineage

Linaje TRAIN/EVALUATE/EXPLAIN con checkpoint/versión, claves compuestas.

Dominio: Q. Auditoría y trazabilidad técnica. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| parent_run_id | uuid | NO |  |
| child_run_id | uuid | NO |  |
| relationship_type | text | NO |  |
| checkpoint_path | text | YES |  |
| checkpoint_artifact_id | uuid | YES |  |
| model_version_id | uuid | YES |  |
| confidence | text | NO | CAST('explicit' AS text) |
| metadata | jsonb | NO | CAST('{}' AS jsonb) |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.run_lineage ADD CONSTRAINT run_lineage_pkey CONSTRAINT run_lineage_pkey PRIMARY KEY (id);
ALTER TABLE public.run_lineage ADD CONSTRAINT uq_run_lineage_parent_child_type CONSTRAINT uq_run_lineage_parent_child_type UNIQUE (parent_run_id, child_run_id, relationship_type);
ALTER TABLE public.run_lineage ADD CONSTRAINT chk_run_lineage_confidence CONSTRAINT chk_run_lineage_confidence CHECK (confidence = ANY(ARRAY[CAST('explicit' AS text), CAST('inferred_exact_checkpoint' AS text), CAST('inferred_model_version' AS text), CAST('inferred_heuristic' AS text), CAST('unknown' AS text)]));
ALTER TABLE public.run_lineage ADD CONSTRAINT chk_run_lineage_distinct_runs CONSTRAINT chk_run_lineage_distinct_runs CHECK (parent_run_id <> child_run_id);
ALTER TABLE public.run_lineage ADD CONSTRAINT chk_run_lineage_relationship_type CONSTRAINT chk_run_lineage_relationship_type CHECK (relationship_type = ANY(ARRAY[CAST('evaluates_checkpoint_from' AS text), CAST('explains_checkpoint_from' AS text), CAST('derived_from' AS text)]));
ALTER TABLE public.run_lineage ADD CONSTRAINT fk_run_lineage_checkpoint_artifact_owner CONSTRAINT fk_run_lineage_checkpoint_artifact_owner FOREIGN KEY (checkpoint_artifact_id, parent_run_id) REFERENCES artifacts (id, run_id) ON DELETE RESTRICT;
ALTER TABLE public.run_lineage ADD CONSTRAINT fk_run_lineage_model_version_owner CONSTRAINT fk_run_lineage_model_version_owner FOREIGN KEY (model_version_id, parent_run_id) REFERENCES model_versions (id, training_run_id) ON DELETE RESTRICT;
ALTER TABLE public.run_lineage ADD CONSTRAINT fk_run_lineage_version_artifact CONSTRAINT fk_run_lineage_version_artifact FOREIGN KEY (model_version_id, checkpoint_artifact_id) REFERENCES model_versions (id, checkpoint_artifact_id) ON DELETE RESTRICT;
ALTER TABLE public.run_lineage ADD CONSTRAINT run_lineage_child_run_id_fkey CONSTRAINT run_lineage_child_run_id_fkey FOREIGN KEY (child_run_id) REFERENCES runs (id) ON DELETE RESTRICT;
ALTER TABLE public.run_lineage ADD CONSTRAINT run_lineage_parent_run_id_fkey CONSTRAINT run_lineage_parent_run_id_fkey FOREIGN KEY (parent_run_id) REFERENCES runs (id) ON DELETE RESTRICT;
```

Índices explícitos: `idx_run_lineage_checkpoint_artifact`, `idx_run_lineage_checkpoint_path`, `idx_run_lineage_child_run_id`, `idx_run_lineage_model_version`, `idx_run_lineage_parent_run_id`, `idx_run_lineage_relationship_type`, `uq_run_lineage_single_evaluation_training_parent`.
Auditoría: created_at.
JSONB: metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## run_metrics

Métricas extensibles EAV; v2 reserva las métricas binarias estables al registro tipado.

Dominio: L. Métricas clínicas. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| run_id | uuid | YES |  |
| metric_name | text | NO |  |
| metric_value | numeric | YES |  |
| metric_unit | text | YES |  |
| split_name | text | YES |  |
| class_name | text | YES |  |
| step | integer | YES |  |
| epoch | integer | YES |  |
| created_at | timestamp with time zone | YES | now() |
| metadata | jsonb | YES | CAST('{}' AS jsonb) |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.run_metrics ADD CONSTRAINT run_metrics_pkey CONSTRAINT run_metrics_pkey PRIMARY KEY (id);
ALTER TABLE public.run_metrics ADD CONSTRAINT run_metrics_run_id_fkey CONSTRAINT run_metrics_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;
ALTER TABLE public.run_metrics ADD CONSTRAINT ck_v2_extension_only CONSTRAINT ck_v2_extension_only CHECK (lower(metric_name) NOT IN ('recall', 'sensitivity', 'specificity', 'precision', 'f1', 'f2', 'balanced_accuracy', 'roc_auc', 'pr_auc', 'tp', 'fp', 'fn', 'tn', 'recall_parasitized', 'sensitivity_parasitized', 'precision_parasitized', 'f1_parasitized', 'f2_parasitized', 'roc_auc_parasitized', 'pr_auc_parasitized'));
```

Índices explícitos: `idx_run_metrics_name`, `idx_run_metrics_run_id`.
Auditoría: created_at.
JSONB: metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## run_model_deployments

Versiones/despliegues consumidos por run, rol/ordinal/peso (incluidos ensembles).

Dominio: P. Publicación / deployment. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| run_id | uuid | NO |  |
| deployed_model_version_id | uuid | NO |  |
| model_version_id | uuid | NO |  |
| role | text | NO | CAST('primary' AS text) |
| ordinal | integer | NO | 0 |
| weight | numeric | YES |  |
| metadata | jsonb | NO | CAST('{}' AS jsonb) |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.run_model_deployments ADD CONSTRAINT run_model_deployments_pkey CONSTRAINT run_model_deployments_pkey PRIMARY KEY (id);
ALTER TABLE public.run_model_deployments ADD CONSTRAINT chk_run_model_deployments_metadata CONSTRAINT chk_run_model_deployments_metadata CHECK (jsonb_typeof(metadata) = CAST('object' AS text));
ALTER TABLE public.run_model_deployments ADD CONSTRAINT chk_run_model_deployments_ordinal CONSTRAINT chk_run_model_deployments_ordinal CHECK (ordinal >= 0);
ALTER TABLE public.run_model_deployments ADD CONSTRAINT chk_run_model_deployments_role CONSTRAINT chk_run_model_deployments_role CHECK (role = ANY(ARRAY[CAST('primary' AS text), CAST('classifier' AS text), CAST('detector' AS text), CAST('ensemble_member' AS text), CAST('explainer' AS text)]));
ALTER TABLE public.run_model_deployments ADD CONSTRAINT chk_run_model_deployments_weight CONSTRAINT chk_run_model_deployments_weight CHECK (weight IS NULL OR (weight >= CAST(0 AS numeric) AND weight <= CAST(1 AS numeric)));
ALTER TABLE public.run_model_deployments ADD CONSTRAINT fk_run_model_deployments_deployment_version CONSTRAINT fk_run_model_deployments_deployment_version FOREIGN KEY (deployed_model_version_id, model_version_id) REFERENCES deployed_model_versions (id, model_version_id) ON DELETE RESTRICT;
ALTER TABLE public.run_model_deployments ADD CONSTRAINT fk_run_model_deployments_run CONSTRAINT fk_run_model_deployments_run FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;
```

Índices explícitos: `uq_run_model_deployments_binding`, `uq_run_model_deployments_run_deployment_version`, `idx_run_model_deployments_deployment`, `idx_run_model_deployments_model_version`, `uq_run_model_deployments_primary`.
Auditoría: created_at.
JSONB: metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## run_threshold_calibration

Evidencia de calibración val y umbral elegido; v2 enlaza evaluaciones default/seleccionada.

Dominio: M. Calibración. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| run_threshold_calibration_id | uuid | NO | pg_catalog.gen_random_uuid() |
| run_id | uuid | NO |  |
| model_name | text | YES |  |
| threshold_policy | text | NO | CAST('target_recall' AS text) |
| threshold_source | text | NO | CAST('validation_calibration' AS text) |
| threshold_selected | numeric | NO |  |
| default_threshold | numeric | NO | 0.5 |
| target_recall | numeric | NO |  |
| target_recall_satisfied | boolean | YES |  |
| min_specificity | numeric | YES |  |
| validation_recall_at_threshold | numeric | YES |  |
| validation_specificity_at_threshold | numeric | YES |  |
| validation_precision_at_threshold | numeric | YES |  |
| validation_f1_at_threshold | numeric | YES |  |
| validation_f2_at_threshold | numeric | YES |  |
| validation_balanced_accuracy_at_threshold | numeric | YES |  |
| validation_pr_auc | numeric | YES |  |
| validation_roc_auc | numeric | YES |  |
| default_threshold_metrics | jsonb | NO | CAST('{}' AS jsonb) |
| selected_threshold_metrics | jsonb | NO | CAST('{}' AS jsonb) |
| candidate_count | integer | YES |  |
| threshold_warning | text | YES |  |
| calibration_split | text | NO | CAST('val' AS text) |
| threshold_calibration_path | text | YES |  |
| model_metadata_path | text | YES |  |
| created_at | timestamp with time zone | NO | now() |
| metadata | jsonb | NO | CAST('{}' AS jsonb) |
| model_version_id | uuid | YES |  |
| calibration_artifact_id | uuid | YES |  |
| score_name | text | NO | CAST('probability_parasitized' AS text) |
| label_mapping_version | text | NO | CAST('clinical_v1_parasitized_positive' AS text) |
| positive_label | text | NO | CAST('parasitized' AS text) |
| calibration_status | text | NO | CAST('recorded' AS text) |
| default_evaluation_id | uuid | NO |  |
| selected_evaluation_id | uuid | NO |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT run_threshold_calibration_pkey CONSTRAINT run_threshold_calibration_pkey PRIMARY KEY (run_threshold_calibration_id);
ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT chk_run_threshold_calibration_positive_label CONSTRAINT chk_run_threshold_calibration_positive_label CHECK (positive_label = CAST('parasitized' AS text));
ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT chk_run_threshold_calibration_score_name CONSTRAINT chk_run_threshold_calibration_score_name CHECK (score_name = CAST('probability_parasitized' AS text));
ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT chk_run_threshold_calibration_split CONSTRAINT chk_run_threshold_calibration_split CHECK (calibration_split = ANY(ARRAY[CAST('val' AS text), CAST('validation' AS text)]));
ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT chk_run_threshold_calibration_status CONSTRAINT chk_run_threshold_calibration_status CHECK (calibration_status = ANY(ARRAY[CAST('recorded' AS text), CAST('validated' AS text), CAST('rejected' AS text), CAST('retired' AS text)]));
ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT fk_run_threshold_calibration_artifact_owner CONSTRAINT fk_run_threshold_calibration_artifact_owner FOREIGN KEY (calibration_artifact_id, run_id) REFERENCES artifacts (id, run_id) ON DELETE RESTRICT;
ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT fk_run_threshold_calibration_model_version CONSTRAINT fk_run_threshold_calibration_model_version FOREIGN KEY (model_version_id) REFERENCES model_versions (id) ON DELETE RESTRICT;
ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT run_threshold_calibration_run_id_fkey CONSTRAINT run_threshold_calibration_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;
ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT ck_v2_calibration_val CONSTRAINT ck_v2_calibration_val CHECK (calibration_split = 'val' AND default_threshold = 0.5 AND target_recall > 0 AND target_recall <= 1);
ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT v2_run_threshold_calibration_foreign_014acc59cdbd CONSTRAINT v2_run_threshold_calibration_foreign_014acc59cdbd FOREIGN KEY (default_evaluation_id) REFERENCES public.evaluations (id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public.run_threshold_calibration ADD CONSTRAINT v2_run_threshold_calibration_foreign_0ba3287c0955 CONSTRAINT v2_run_threshold_calibration_foreign_0ba3287c0955 FOREIGN KEY (selected_evaluation_id) REFERENCES public.evaluations (id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
```

Índices explícitos: `uq_run_threshold_calibration_id_version`, `idx_run_threshold_calibration_artifact`, `idx_run_threshold_calibration_model_version`, `idx_run_threshold_calibration_run_id`.
Auditoría: created_at.
JSONB: default_threshold_metrics, selected_threshold_metrics, metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## runs

Identidad/ciclo de vida, entorno y resumen técnico; resultados/config consultables fuera del JSON.

Dominio: G. Runs. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| experiment_id | uuid | YES |  |
| model_id | uuid | YES |  |
| dataset_id | uuid | YES |  |
| run_name | text | YES |  |
| run_type | text | NO |  |
| status | text | NO |  |
| command | text | YES |  |
| script_name | text | YES |  |
| started_at | timestamp with time zone | YES |  |
| finished_at | timestamp with time zone | YES |  |
| duration_seconds | numeric | YES |  |
| user_name | text | YES |  |
| host_name | text | YES |  |
| working_directory | text | YES |  |
| git_commit | text | YES |  |
| git_branch | text | YES |  |
| python_version | text | YES |  |
| tensorflow_version | text | YES |  |
| keras_version | text | YES |  |
| platform | text | YES |  |
| machine | text | YES |  |
| processor | text | YES |  |
| gpu_available | boolean | YES |  |
| gpu_devices | jsonb | YES | CAST('[]' AS jsonb) |
| random_seed | integer | YES |  |
| parameters | jsonb | YES | CAST('{}' AS jsonb) |
| notes | text | YES |  |
| created_at | timestamp with time zone | YES | now() |
| updated_at | timestamp with time zone | YES | now() |
| metadata | jsonb | YES | CAST('{}' AS jsonb) |
| execution_type | text | YES |  |
| execution_parameters | jsonb | NO | CAST('{}' AS jsonb) |
| fine_tuning_start_epoch | integer | YES |  |
| total_epochs | integer | YES |  |
| completed_epochs | integer | NO | 0 |
| max_epochs | integer | YES |  |
| stopped_epoch | integer | YES |  |
| best_epoch | integer | YES |  |
| checkpoint_monitor | text | YES |  |
| checkpoint_mode | text | YES |  |
| best_validation_value | double precision | YES |  |
| early_stopping_enabled | boolean | YES |  |
| early_stopping_patience | integer | YES |  |
| early_stopping_min_delta | double precision | YES |  |
| restore_best_weights | boolean | YES |  |
| backend_version | text | YES |  |
| pipeline_version | text | YES |  |
| configuration | jsonb | YES |  |
| error_message | text | YES |  |
| dataset_version_id | uuid | YES |  |
| release_status | text | YES |  |
| release_updated_at | timestamp with time zone | YES |  |
| release_changed_by | text | YES |  |
| release_reason | text | YES |  |
| campaign_id | uuid | YES |  |
| peak_cpu_memory_bytes | bigint | YES |  |
| peak_gpu_memory_bytes | bigint | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.runs ADD CONSTRAINT runs_pkey CONSTRAINT runs_pkey PRIMARY KEY (id);
ALTER TABLE public.runs ADD CONSTRAINT chk_runs_configuration_object CONSTRAINT chk_runs_configuration_object CHECK (configuration IS NULL OR jsonb_typeof(configuration) = CAST('object' AS text));
ALTER TABLE public.runs ADD CONSTRAINT ck_runs_release_status_requires_timestamp CONSTRAINT ck_runs_release_status_requires_timestamp CHECK (release_status IS NULL OR release_updated_at IS NOT NULL);
ALTER TABLE public.runs ADD CONSTRAINT ck_runs_release_status_training_vocabulary CONSTRAINT ck_runs_release_status_training_vocabulary CHECK (release_status IS NULL OR (run_type = CAST('training' AS text) AND release_status = ANY(ARRAY[CAST('not_available' AS text), CAST('available_to_publish' AS text), CAST('productive_stage2' AS text)])));
ALTER TABLE public.runs ADD CONSTRAINT runs_campaign_id_fkey CONSTRAINT runs_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns (id);
ALTER TABLE public.runs ADD CONSTRAINT runs_dataset_id_fkey CONSTRAINT runs_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE RESTRICT;
ALTER TABLE public.runs ADD CONSTRAINT runs_dataset_version_id_fkey CONSTRAINT runs_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT;
ALTER TABLE public.runs ADD CONSTRAINT runs_experiment_id_fkey CONSTRAINT runs_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE RESTRICT;
ALTER TABLE public.runs ADD CONSTRAINT runs_model_id_fkey CONSTRAINT runs_model_id_fkey FOREIGN KEY (model_id) REFERENCES models (id) ON DELETE RESTRICT;
ALTER TABLE public.runs ADD CONSTRAINT ck_v2_no_result_json CONSTRAINT ck_v2_no_result_json CHECK (NOT parameters ? 'training_results');
ALTER TABLE public.runs ADD CONSTRAINT v2_runs_check_275ea92559ec CONSTRAINT v2_runs_check_275ea92559ec CHECK (peak_cpu_memory_bytes >= 0);
ALTER TABLE public.runs ADD CONSTRAINT v2_runs_check_080968ed1984 CONSTRAINT v2_runs_check_080968ed1984 CHECK (peak_gpu_memory_bytes >= 0);
```

Índices explícitos: `idx_runs_dataset_id`, `idx_runs_execution_parameters_gin`, `idx_runs_execution_type`, `idx_runs_inference_script`, `idx_runs_metadata_gin`, `idx_runs_model_id`, `idx_runs_parameters_gin`, `idx_runs_run_type`, `idx_runs_started_at`, `idx_runs_status`, `idx_runs_training_release_status`, `ix_runs_dataset_version_id`, `uq_runs_single_productive_stage2`.
Auditoría: started_at, finished_at, created_at, updated_at, release_updated_at.
JSONB: gpu_devices, parameters, metadata, execution_parameters, configuration. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## scientific_cases

Caso/solicitud clínica científica, sujeto, prioridad, procedencia y archivo.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| case_code | varchar(120) | NO |  |
| subject_id | uuid | YES |  |
| title | varchar(240) | YES |  |
| description | text | YES |  |
| source_type | varchar(30) | NO |  |
| status | varchar(20) | NO | CAST('draft' AS varchar) |
| priority | varchar(10) | NO | CAST('normal' AS varchar) |
| metadata_json | jsonb | NO | CAST('{}' AS jsonb) |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |
| created_by | uuid | NO |  |
| updated_by | uuid | YES |  |
| archived_at | timestamp with time zone | YES |  |
| archived_by | uuid | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_pkey CONSTRAINT scientific_cases_pkey PRIMARY KEY (id);
ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_case_code_key CONSTRAINT scientific_cases_case_code_key UNIQUE (case_code);
ALTER TABLE public.scientific_cases ADD CONSTRAINT ck_scientific_case_archive_state CONSTRAINT ck_scientific_case_archive_state CHECK ((CAST(status AS text) <> CAST('archived' AS text) AND archived_at IS NULL AND archived_by IS NULL) OR (CAST(status AS text) = CAST('archived' AS text) AND archived_at IS NOT NULL AND archived_by IS NOT NULL));
ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_case_code_check CONSTRAINT scientific_cases_case_code_check CHECK (btrim(CAST(case_code AS text)) <> CAST('' AS text));
ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_metadata_json_check CONSTRAINT scientific_cases_metadata_json_check CHECK (jsonb_typeof(metadata_json) = CAST('object' AS text));
ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_priority_check CONSTRAINT scientific_cases_priority_check CHECK (CAST(priority AS text) = ANY(ARRAY[CAST(CAST('low' AS varchar) AS text), CAST(CAST('normal' AS varchar) AS text), CAST(CAST('high' AS varchar) AS text)]));
ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_source_type_check CONSTRAINT scientific_cases_source_type_check CHECK (CAST(source_type AS text) = ANY(ARRAY[CAST(CAST('physical_microscope' AS varchar) AS text), CAST(CAST('imported_image' AS varchar) AS text), CAST(CAST('research_dataset' AS varchar) AS text), CAST(CAST('synthetic' AS varchar) AS text)]));
ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_status_check CONSTRAINT scientific_cases_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('draft' AS varchar) AS text), CAST(CAST('registered' AS varchar) AS text), CAST(CAST('ready' AS varchar) AS text), CAST(CAST('archived' AS varchar) AS text)]));
ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_archived_by_fkey CONSTRAINT scientific_cases_archived_by_fkey FOREIGN KEY (archived_by) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_created_by_fkey CONSTRAINT scientific_cases_created_by_fkey FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_subject_id_fkey CONSTRAINT scientific_cases_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES research_subjects (id) ON DELETE RESTRICT;
ALTER TABLE public.scientific_cases ADD CONSTRAINT scientific_cases_updated_by_fkey CONSTRAINT scientific_cases_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_scientific_cases_status_created`, `ix_scientific_cases_subject`.
Auditoría: created_at, updated_at, created_by, updated_by, archived_at.
JSONB: metadata_json. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: source_type.

## scientific_reviews

Revisión científica de entidad existente, autor/decisión/razón y trazabilidad.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| entity_type | varchar(40) | NO |  |
| entity_id | uuid | NO |  |
| decision | varchar(30) | NO |  |
| comment | text | YES |  |
| actor_user_id | uuid | NO |  |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.scientific_reviews ADD CONSTRAINT scientific_reviews_pkey CONSTRAINT scientific_reviews_pkey PRIMARY KEY (id);
ALTER TABLE public.scientific_reviews ADD CONSTRAINT ck_scientific_review_comment CONSTRAINT ck_scientific_review_comment CHECK ((CAST(decision AS text) = CAST('accepted' AS text) AND (comment IS NULL OR btrim(comment) <> CAST('' AS text))) OR (CAST(decision AS text) = ANY(ARRAY[CAST(CAST('rejected' AS varchar) AS text), CAST(CAST('needs_attention' AS varchar) AS text), CAST(CAST('comment_only' AS varchar) AS text)]) AND comment IS NOT NULL AND btrim(comment) <> CAST('' AS text)));
ALTER TABLE public.scientific_reviews ADD CONSTRAINT scientific_reviews_decision_check CONSTRAINT scientific_reviews_decision_check CHECK (CAST(decision AS text) = ANY(ARRAY[CAST(CAST('accepted' AS varchar) AS text), CAST(CAST('rejected' AS varchar) AS text), CAST(CAST('needs_attention' AS varchar) AS text), CAST(CAST('comment_only' AS varchar) AS text)]));
ALTER TABLE public.scientific_reviews ADD CONSTRAINT scientific_reviews_entity_type_check CONSTRAINT scientific_reviews_entity_type_check CHECK (CAST(entity_type AS text) = CAST('cell_detection' AS text));
ALTER TABLE public.scientific_reviews ADD CONSTRAINT scientific_reviews_actor_user_id_fkey CONSTRAINT scientific_reviews_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.scientific_reviews ADD CONSTRAINT scientific_reviews_entity_id_fkey CONSTRAINT scientific_reviews_entity_id_fkey FOREIGN KEY (entity_id) REFERENCES cell_detections (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_scientific_reviews_actor_created`, `ix_scientific_reviews_entity_created`.
Auditoría: actor_user_id, created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## scientific_validation_annotation_events

Historial de versiones/estado antes-después de anotación por usuario.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| annotation_id | uuid | NO |  |
| validation_session_id | uuid | YES |  |
| event_type | varchar(20) | NO |  |
| annotation_version | integer | NO |  |
| actor_user_id | uuid | NO |  |
| before_state | jsonb | YES |  |
| after_state | jsonb | NO |  |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.scientific_validation_annotation_events ADD CONSTRAINT scientific_validation_annotation_events_pkey CONSTRAINT scientific_validation_annotation_events_pkey PRIMARY KEY (id);
ALTER TABLE public.scientific_validation_annotation_events ADD CONSTRAINT scientific_validation_annotat_annotation_id_annotation_vers_key CONSTRAINT scientific_validation_annotat_annotation_id_annotation_vers_key UNIQUE (annotation_id, annotation_version);
ALTER TABLE public.scientific_validation_annotation_events ADD CONSTRAINT ck_validation_annotation_event_before CONSTRAINT ck_validation_annotation_event_before CHECK ((CAST(event_type AS text) = CAST('created' AS text) AND before_state IS NULL AND annotation_version = 1) OR (CAST(event_type AS text) = CAST('updated' AS text) AND jsonb_typeof(before_state) = CAST('object' AS text) AND annotation_version > 1));
ALTER TABLE public.scientific_validation_annotation_events ADD CONSTRAINT scientific_validation_annotation_event_annotation_version_check CONSTRAINT scientific_validation_annotation_event_annotation_version_check CHECK (annotation_version > 0);
ALTER TABLE public.scientific_validation_annotation_events ADD CONSTRAINT scientific_validation_annotation_events_after_state_check CONSTRAINT scientific_validation_annotation_events_after_state_check CHECK (jsonb_typeof(after_state) = CAST('object' AS text));
ALTER TABLE public.scientific_validation_annotation_events ADD CONSTRAINT scientific_validation_annotation_events_event_type_check CONSTRAINT scientific_validation_annotation_events_event_type_check CHECK (CAST(event_type AS text) = ANY(ARRAY[CAST(CAST('created' AS varchar) AS text), CAST(CAST('updated' AS varchar) AS text)]));
ALTER TABLE public.scientific_validation_annotation_events ADD CONSTRAINT scientific_validation_annotation_eve_validation_session_id_fkey CONSTRAINT scientific_validation_annotation_eve_validation_session_id_fkey FOREIGN KEY (validation_session_id) REFERENCES scientific_validation_sessions (id) ON DELETE RESTRICT;
ALTER TABLE public.scientific_validation_annotation_events ADD CONSTRAINT scientific_validation_annotation_events_actor_user_id_fkey CONSTRAINT scientific_validation_annotation_events_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.scientific_validation_annotation_events ADD CONSTRAINT scientific_validation_annotation_events_annotation_id_fkey CONSTRAINT scientific_validation_annotation_events_annotation_id_fkey FOREIGN KEY (annotation_id) REFERENCES scientific_validation_annotations (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_validation_annotation_events_actor_created`, `ix_validation_annotation_events_annotation_created`.
Auditoría: actor_user_id, created_at.
JSONB: before_state, after_state. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## scientific_validation_annotations

Anotación humana de referencia por sesión/target, versionada para validación.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| validation_session_id | uuid | YES |  |
| target_type | varchar(20) | NO |  |
| cell_detection_id | uuid | YES |  |
| analysis_run_id | uuid | YES |  |
| category | varchar(120) | NO |  |
| content | text | NO |  |
| version | integer | NO | 1 |
| created_by | uuid | NO |  |
| created_at | timestamp with time zone | NO | now() |
| updated_by | uuid | NO |  |
| updated_at | timestamp with time zone | NO | now() |
| sample_id | uuid | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_pkey CONSTRAINT scientific_validation_annotations_pkey PRIMARY KEY (id);
ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT ck_validation_annotation_exact_target CONSTRAINT ck_validation_annotation_exact_target CHECK ((CAST(target_type AS text) = CAST('cell' AS text) AND cell_detection_id IS NOT NULL AND analysis_run_id IS NULL AND sample_id IS NULL) OR (CAST(target_type AS text) = CAST('analysis' AS text) AND analysis_run_id IS NOT NULL AND cell_detection_id IS NULL AND sample_id IS NULL) OR (CAST(target_type AS text) = CAST('sample' AS text) AND sample_id IS NOT NULL AND cell_detection_id IS NULL AND analysis_run_id IS NULL));
ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_category_check CONSTRAINT scientific_validation_annotations_category_check CHECK (btrim(CAST(category AS text)) <> CAST('' AS text));
ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_content_check CONSTRAINT scientific_validation_annotations_content_check CHECK (btrim(content) <> CAST('' AS text));
ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_target_type_check CONSTRAINT scientific_validation_annotations_target_type_check CHECK (CAST(target_type AS text) = ANY(ARRAY[CAST(CAST('cell' AS varchar) AS text), CAST(CAST('analysis' AS varchar) AS text), CAST(CAST('sample' AS varchar) AS text)]));
ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_version_check CONSTRAINT scientific_validation_annotations_version_check CHECK (version > 0);
ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_analysis_run_id_fkey CONSTRAINT scientific_validation_annotations_analysis_run_id_fkey FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs (id) ON DELETE RESTRICT;
ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_cell_detection_id_fkey CONSTRAINT scientific_validation_annotations_cell_detection_id_fkey FOREIGN KEY (cell_detection_id) REFERENCES cell_detections (id) ON DELETE RESTRICT;
ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_created_by_fkey CONSTRAINT scientific_validation_annotations_created_by_fkey FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_sample_id_fkey CONSTRAINT scientific_validation_annotations_sample_id_fkey FOREIGN KEY (sample_id) REFERENCES blood_samples (id) ON DELETE RESTRICT;
ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_updated_by_fkey CONSTRAINT scientific_validation_annotations_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.scientific_validation_annotations ADD CONSTRAINT scientific_validation_annotations_validation_session_id_fkey CONSTRAINT scientific_validation_annotations_validation_session_id_fkey FOREIGN KEY (validation_session_id) REFERENCES scientific_validation_sessions (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_validation_annotations_general_target`, `ix_validation_annotations_session_analysis`, `ix_validation_annotations_session_category`, `ix_validation_annotations_session_cell`, `ix_validation_annotations_session_created`, `ix_validation_annotations_session_sample`.
Auditoría: created_by, created_at, updated_by, updated_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## scientific_validation_classification_runs

Binding sesión de validación–ejecución de clasificación, sin copiar outputs.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| session_id | uuid | NO |  |
| classification_run_id | uuid | NO |  |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.scientific_validation_classification_runs ADD CONSTRAINT scientific_validation_classification_runs_pkey CONSTRAINT scientific_validation_classification_runs_pkey PRIMARY KEY (session_id, classification_run_id);
ALTER TABLE public.scientific_validation_classification_runs ADD CONSTRAINT scientific_validation_classification_classification_run_id_fkey CONSTRAINT scientific_validation_classification_classification_run_id_fkey FOREIGN KEY (classification_run_id) REFERENCES cell_classification_runs (id) ON DELETE RESTRICT;
ALTER TABLE public.scientific_validation_classification_runs ADD CONSTRAINT scientific_validation_classification_runs_session_id_fkey CONSTRAINT scientific_validation_classification_runs_session_id_fkey FOREIGN KEY (session_id) REFERENCES scientific_validation_sessions (id) ON DELETE RESTRICT;
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## scientific_validation_detection_runs

Binding sesión de validación–detección con configuración exacta.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| session_id | uuid | NO |  |
| detection_run_id | uuid | NO |  |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.scientific_validation_detection_runs ADD CONSTRAINT scientific_validation_detection_runs_pkey CONSTRAINT scientific_validation_detection_runs_pkey PRIMARY KEY (session_id, detection_run_id);
ALTER TABLE public.scientific_validation_detection_runs ADD CONSTRAINT scientific_validation_detection_runs_detection_run_id_fkey CONSTRAINT scientific_validation_detection_runs_detection_run_id_fkey FOREIGN KEY (detection_run_id) REFERENCES cell_detection_runs (id) ON DELETE RESTRICT;
ALTER TABLE public.scientific_validation_detection_runs ADD CONSTRAINT scientific_validation_detection_runs_session_id_fkey CONSTRAINT scientific_validation_detection_runs_session_id_fkey FOREIGN KEY (session_id) REFERENCES scientific_validation_sessions (id) ON DELETE RESTRICT;
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## scientific_validation_images

Conjunto de imágenes de referencia de sesión con secuencia y hash congelados.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| session_id | uuid | NO |  |
| microscopy_image_id | uuid | NO |  |
| image_sha256 | char(64) | NO |  |
| sequence_number | integer | NO |  |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.scientific_validation_images ADD CONSTRAINT scientific_validation_images_pkey CONSTRAINT scientific_validation_images_pkey PRIMARY KEY (session_id, microscopy_image_id);
ALTER TABLE public.scientific_validation_images ADD CONSTRAINT scientific_validation_images_session_id_sequence_number_key CONSTRAINT scientific_validation_images_session_id_sequence_number_key UNIQUE (session_id, sequence_number);
ALTER TABLE public.scientific_validation_images ADD CONSTRAINT scientific_validation_images_image_sha256_check CONSTRAINT scientific_validation_images_image_sha256_check CHECK (image_sha256 ~ CAST('^[0-9a-f]{64}$' AS text));
ALTER TABLE public.scientific_validation_images ADD CONSTRAINT scientific_validation_images_sequence_number_check CONSTRAINT scientific_validation_images_sequence_number_check CHECK (sequence_number > 0);
ALTER TABLE public.scientific_validation_images ADD CONSTRAINT scientific_validation_images_microscopy_image_id_fkey CONSTRAINT scientific_validation_images_microscopy_image_id_fkey FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images (id) ON DELETE RESTRICT;
ALTER TABLE public.scientific_validation_images ADD CONSTRAINT scientific_validation_images_session_id_fkey CONSTRAINT scientific_validation_images_session_id_fkey FOREIGN KEY (session_id) REFERENCES scientific_validation_sessions (id) ON DELETE RESTRICT;
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: image_sha256.

## scientific_validation_sessions

Protocolo/snapshot inicial y estado de sesión de validación científica de microscopía.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| name | varchar(200) | NO |  |
| description | text | YES |  |
| datasource | varchar(80) | NO |  |
| protocol_key | varchar(120) | NO |  |
| protocol_version | varchar(80) | NO |  |
| matching_iou_threshold | double precision | NO |  |
| status | varchar(30) | NO | CAST('draft' AS varchar) |
| initial_snapshot | jsonb | NO |  |
| snapshot_sha256 | char(64) | NO |  |
| created_by | uuid | NO |  |
| updated_by | uuid | NO |  |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |
| archived_at | timestamp with time zone | YES |  |
| archived_by | uuid | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_pkey CONSTRAINT scientific_validation_sessions_pkey PRIMARY KEY (id);
ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT ck_validation_session_archive CONSTRAINT ck_validation_session_archive CHECK ((CAST(status AS text) <> CAST('archived' AS text) AND archived_at IS NULL AND archived_by IS NULL) OR (CAST(status AS text) = CAST('archived' AS text) AND archived_at IS NOT NULL AND archived_by IS NOT NULL));
ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_datasource_check CONSTRAINT scientific_validation_sessions_datasource_check CHECK (btrim(CAST(datasource AS text)) <> CAST('' AS text));
ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_initial_snapshot_check CONSTRAINT scientific_validation_sessions_initial_snapshot_check CHECK (jsonb_typeof(initial_snapshot) = CAST('object' AS text));
ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_matching_iou_threshold_check CONSTRAINT scientific_validation_sessions_matching_iou_threshold_check CHECK (matching_iou_threshold > CAST(0 AS double precision) AND matching_iou_threshold <= CAST(1 AS double precision));
ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_name_check CONSTRAINT scientific_validation_sessions_name_check CHECK (btrim(CAST(name AS text)) <> CAST('' AS text));
ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_protocol_key_check CONSTRAINT scientific_validation_sessions_protocol_key_check CHECK (btrim(CAST(protocol_key AS text)) <> CAST('' AS text));
ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_protocol_version_check CONSTRAINT scientific_validation_sessions_protocol_version_check CHECK (btrim(CAST(protocol_version AS text)) <> CAST('' AS text));
ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_snapshot_sha256_check CONSTRAINT scientific_validation_sessions_snapshot_sha256_check CHECK (snapshot_sha256 ~ CAST('^[0-9a-f]{64}$' AS text));
ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_status_check CONSTRAINT scientific_validation_sessions_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('draft' AS varchar) AS text), CAST(CAST('annotation_in_progress' AS varchar) AS text), CAST(CAST('ready_for_analysis' AS varchar) AS text), CAST(CAST('completed' AS varchar) AS text), CAST(CAST('archived' AS varchar) AS text)]));
ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_archived_by_fkey CONSTRAINT scientific_validation_sessions_archived_by_fkey FOREIGN KEY (archived_by) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_created_by_fkey CONSTRAINT scientific_validation_sessions_created_by_fkey FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.scientific_validation_sessions ADD CONSTRAINT scientific_validation_sessions_updated_by_fkey CONSTRAINT scientific_validation_sessions_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_validation_sessions_creator_created`, `ix_validation_sessions_status_created`.
Auditoría: created_by, updated_by, created_at, updated_at, archived_at.
JSONB: initial_snapshot. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: snapshot_sha256.

## smear_analysis_summaries

Resumen automático/revisado de frotis según política de agregación; no diagnóstico confirmado.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| classification_run_id | uuid | NO |  |
| analysis_run_id | uuid | NO |  |
| detection_run_id | uuid | NO |  |
| outcome | varchar(40) | NO |  |
| eligible_cell_count | integer | NO |  |
| classified_cell_count | integer | NO |  |
| parasitized_candidate_count | integer | NO |  |
| uninfected_candidate_count | integer | NO |  |
| near_threshold_count | integer | NO |  |
| failed_prediction_count | integer | NO |  |
| parasitized_candidate_fraction | double precision | YES |  |
| maximum_probability_parasitized | double precision | YES |  |
| mean_probability_parasitized | double precision | YES |  |
| median_probability_parasitized | double precision | YES |  |
| per_image_summary | jsonb | NO |  |
| aggregation_policy_snapshot | jsonb | NO |  |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_pkey CONSTRAINT smear_analysis_summaries_pkey PRIMARY KEY (id);
ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_classification_run_id_key CONSTRAINT smear_analysis_summaries_classification_run_id_key UNIQUE (classification_run_id);
ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT ck_smear_summary_counts CONSTRAINT ck_smear_summary_counts CHECK (classified_cell_count = (parasitized_candidate_count + uninfected_candidate_count) AND (classified_cell_count + failed_prediction_count) = eligible_cell_count AND near_threshold_count <= classified_cell_count);
ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT ck_smear_summary_fraction CONSTRAINT ck_smear_summary_fraction CHECK ((classified_cell_count = 0 AND parasitized_candidate_fraction IS NULL) OR (classified_cell_count > 0 AND parasitized_candidate_fraction >= CAST(0 AS double precision) AND parasitized_candidate_fraction <= CAST(1 AS double precision) AND abs(parasitized_candidate_fraction - (CAST(parasitized_candidate_count AS double precision) / CAST(classified_cell_count AS double precision))) <= CAST(0.000000001 AS double precision)));
ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT ck_smear_summary_probabilities CONSTRAINT ck_smear_summary_probabilities CHECK ((classified_cell_count = 0 AND maximum_probability_parasitized IS NULL AND mean_probability_parasitized IS NULL AND median_probability_parasitized IS NULL) OR (classified_cell_count > 0 AND maximum_probability_parasitized >= CAST(0 AS double precision) AND maximum_probability_parasitized <= CAST(1 AS double precision) AND mean_probability_parasitized >= CAST(0 AS double precision) AND mean_probability_parasitized <= CAST(1 AS double precision) AND median_probability_parasitized >= CAST(0 AS double precision) AND median_probability_parasitized <= CAST(1 AS double precision)));
ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_aggregation_policy_snapshot_check CONSTRAINT smear_analysis_summaries_aggregation_policy_snapshot_check CHECK (jsonb_typeof(aggregation_policy_snapshot) = CAST('object' AS text));
ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_classified_cell_count_check CONSTRAINT smear_analysis_summaries_classified_cell_count_check CHECK (classified_cell_count >= 0);
ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_eligible_cell_count_check CONSTRAINT smear_analysis_summaries_eligible_cell_count_check CHECK (eligible_cell_count >= 0);
ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_failed_prediction_count_check CONSTRAINT smear_analysis_summaries_failed_prediction_count_check CHECK (failed_prediction_count >= 0);
ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_near_threshold_count_check CONSTRAINT smear_analysis_summaries_near_threshold_count_check CHECK (near_threshold_count >= 0);
ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_outcome_check CONSTRAINT smear_analysis_summaries_outcome_check CHECK (CAST(outcome AS text) = ANY(ARRAY[CAST(CAST('suspicious_cells_detected' AS varchar) AS text), CAST(CAST('no_suspicious_cells_detected' AS varchar) AS text), CAST(CAST('inconclusive' AS varchar) AS text)]));
ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_parasitized_candidate_count_check CONSTRAINT smear_analysis_summaries_parasitized_candidate_count_check CHECK (parasitized_candidate_count >= 0);
ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_per_image_summary_check CONSTRAINT smear_analysis_summaries_per_image_summary_check CHECK (jsonb_typeof(per_image_summary) = CAST('object' AS text));
ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT smear_analysis_summaries_uninfected_candidate_count_check CONSTRAINT smear_analysis_summaries_uninfected_candidate_count_check CHECK (uninfected_candidate_count >= 0);
ALTER TABLE public.smear_analysis_summaries ADD CONSTRAINT fk_smear_summary_classification_lineage CONSTRAINT fk_smear_summary_classification_lineage FOREIGN KEY (classification_run_id, analysis_run_id, detection_run_id) REFERENCES cell_classification_runs (id, analysis_run_id, detection_run_id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_smear_analysis_summaries_analysis_created`, `ix_smear_analysis_summaries_detection_created`, `ix_smear_analysis_summaries_outcome_created`.
Auditoría: created_at.
JSONB: per_image_summary, aggregation_policy_snapshot. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## smear_slides

Lámina/portaobjetos de la muestra, tipo de frotis y procedencia.

Dominio: C. Imágenes / pacientes / splits. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| sample_id | uuid | NO |  |
| slide_code | varchar(120) | NO |  |
| smear_type | varchar(20) | NO |  |
| stain_type | varchar(120) | YES |  |
| preparation_method | varchar(160) | YES |  |
| prepared_at | timestamp with time zone | YES |  |
| status | varchar(30) | NO | CAST('registered' AS varchar) |
| notes | text | YES |  |
| metadata_json | jsonb | NO | CAST('{}' AS jsonb) |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |
| created_by | uuid | NO |  |
| updated_by | uuid | YES |  |
| archived_at | timestamp with time zone | YES |  |
| archived_by | uuid | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.smear_slides ADD CONSTRAINT smear_slides_pkey CONSTRAINT smear_slides_pkey PRIMARY KEY (id);
ALTER TABLE public.smear_slides ADD CONSTRAINT uq_smear_slides_sample_code CONSTRAINT uq_smear_slides_sample_code UNIQUE (sample_id, slide_code);
ALTER TABLE public.smear_slides ADD CONSTRAINT ck_smear_slide_archive_state CONSTRAINT ck_smear_slide_archive_state CHECK ((CAST(status AS text) <> CAST('archived' AS text) AND archived_at IS NULL AND archived_by IS NULL) OR (CAST(status AS text) = CAST('archived' AS text) AND archived_at IS NOT NULL AND archived_by IS NOT NULL));
ALTER TABLE public.smear_slides ADD CONSTRAINT smear_slides_metadata_json_check CONSTRAINT smear_slides_metadata_json_check CHECK (jsonb_typeof(metadata_json) = CAST('object' AS text));
ALTER TABLE public.smear_slides ADD CONSTRAINT smear_slides_slide_code_check CONSTRAINT smear_slides_slide_code_check CHECK (btrim(CAST(slide_code AS text)) <> CAST('' AS text));
ALTER TABLE public.smear_slides ADD CONSTRAINT smear_slides_smear_type_check CONSTRAINT smear_slides_smear_type_check CHECK (CAST(smear_type AS text) = ANY(ARRAY[CAST(CAST('thin' AS varchar) AS text), CAST(CAST('thick' AS varchar) AS text), CAST(CAST('combined' AS varchar) AS text), CAST(CAST('unknown' AS varchar) AS text)]));
ALTER TABLE public.smear_slides ADD CONSTRAINT smear_slides_status_check CONSTRAINT smear_slides_status_check CHECK (CAST(status AS text) = ANY(ARRAY[CAST(CAST('registered' AS varchar) AS text), CAST(CAST('prepared' AS varchar) AS text), CAST(CAST('ready_for_capture' AS varchar) AS text), CAST(CAST('archived' AS varchar) AS text)]));
ALTER TABLE public.smear_slides ADD CONSTRAINT smear_slides_archived_by_fkey CONSTRAINT smear_slides_archived_by_fkey FOREIGN KEY (archived_by) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.smear_slides ADD CONSTRAINT smear_slides_created_by_fkey CONSTRAINT smear_slides_created_by_fkey FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT;
ALTER TABLE public.smear_slides ADD CONSTRAINT smear_slides_sample_id_fkey CONSTRAINT smear_slides_sample_id_fkey FOREIGN KEY (sample_id) REFERENCES blood_samples (id) ON DELETE RESTRICT;
ALTER TABLE public.smear_slides ADD CONSTRAINT smear_slides_updated_by_fkey CONSTRAINT smear_slides_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE RESTRICT;
```

Índices explícitos: `ix_smear_slides_sample`, `ix_smear_slides_status_created`.
Auditoría: prepared_at, created_at, updated_at, created_by, updated_by, archived_at.
JSONB: metadata_json. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## stage2_model_publication_events

Historial de publicar/desactivar/reactivar modelo para Etapa 2.

Dominio: P. Publicación / deployment. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| publication_id | uuid | NO |  |
| event_type | text | NO |  |
| actor | text | YES |  |
| event_at | timestamp with time zone | NO | now() |
| model_version_id | uuid | NO |  |
| training_run_id | uuid | NO |  |
| evaluation_run_id | uuid | NO |  |
| datasource | text | NO |  |
| previous_status | text | YES |  |
| new_status | text | NO |  |
| reason | text | YES |  |
| correlation_id | text | YES |  |
| metadata | jsonb | NO | CAST('{}' AS jsonb) |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.stage2_model_publication_events ADD CONSTRAINT stage2_model_publication_events_pkey CONSTRAINT stage2_model_publication_events_pkey PRIMARY KEY (id);
ALTER TABLE public.stage2_model_publication_events ADD CONSTRAINT chk_stage2_publication_event_metadata CONSTRAINT chk_stage2_publication_event_metadata CHECK (jsonb_typeof(metadata) = CAST('object' AS text));
ALTER TABLE public.stage2_model_publication_events ADD CONSTRAINT chk_stage2_publication_event_status CONSTRAINT chk_stage2_publication_event_status CHECK (new_status = ANY(ARRAY[CAST('active' AS text), CAST('inactive' AS text)]) AND (previous_status IS NULL OR previous_status = ANY(ARRAY[CAST('active' AS text), CAST('inactive' AS text)])));
ALTER TABLE public.stage2_model_publication_events ADD CONSTRAINT chk_stage2_publication_event_type CONSTRAINT chk_stage2_publication_event_type CHECK (event_type = ANY(ARRAY[CAST('MODEL_STAGE2_PUBLISHED' AS text), CAST('MODEL_STAGE2_DEACTIVATED' AS text), CAST('MODEL_STAGE2_REACTIVATED' AS text)]));
ALTER TABLE public.stage2_model_publication_events ADD CONSTRAINT stage2_model_publication_events_publication_id_fkey CONSTRAINT stage2_model_publication_events_publication_id_fkey FOREIGN KEY (publication_id) REFERENCES stage2_model_publications (id) ON DELETE RESTRICT;
```

Índices explícitos: `idx_stage2_publication_events_publication`.
Auditoría: event_at.
JSONB: metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## stage2_model_publications

Versión/artefacto/TRAIN/EVALUATE publicados; v2 refuerza TRAIN propio de versión.

Dominio: P. Publicación / deployment. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| datasource | text | NO |  |
| model_version_id | uuid | NO |  |
| training_run_id | uuid | NO |  |
| evaluation_run_id | uuid | NO |  |
| checkpoint_artifact_id | uuid | NO |  |
| scope | text | NO | CAST('stage2' AS text) |
| status | text | NO | CAST('active' AS text) |
| is_active | boolean | NO | TRUE |
| published_at | timestamp with time zone | NO | now() |
| published_by | text | YES |  |
| deactivated_at | timestamp with time zone | YES |  |
| deactivated_by | text | YES |  |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |
| metadata | jsonb | NO | CAST('{}' AS jsonb) |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.stage2_model_publications ADD CONSTRAINT stage2_model_publications_pkey CONSTRAINT stage2_model_publications_pkey PRIMARY KEY (id);
ALTER TABLE public.stage2_model_publications ADD CONSTRAINT chk_stage2_publication_metadata CONSTRAINT chk_stage2_publication_metadata CHECK (jsonb_typeof(metadata) = CAST('object' AS text));
ALTER TABLE public.stage2_model_publications ADD CONSTRAINT chk_stage2_publication_scope CONSTRAINT chk_stage2_publication_scope CHECK (scope = CAST('stage2' AS text));
ALTER TABLE public.stage2_model_publications ADD CONSTRAINT chk_stage2_publication_state CONSTRAINT chk_stage2_publication_state CHECK ((status = CAST('active' AS text) AND is_active AND deactivated_at IS NULL) OR (status = CAST('inactive' AS text) AND NOT is_active AND deactivated_at IS NOT NULL));
ALTER TABLE public.stage2_model_publications ADD CONSTRAINT chk_stage2_publication_status CONSTRAINT chk_stage2_publication_status CHECK (status = ANY(ARRAY[CAST('active' AS text), CAST('inactive' AS text)]));
ALTER TABLE public.stage2_model_publications ADD CONSTRAINT fk_stage2_publication_evaluation CONSTRAINT fk_stage2_publication_evaluation FOREIGN KEY (evaluation_run_id) REFERENCES runs (id) ON DELETE RESTRICT;
ALTER TABLE public.stage2_model_publications ADD CONSTRAINT fk_stage2_publication_training CONSTRAINT fk_stage2_publication_training FOREIGN KEY (training_run_id) REFERENCES runs (id) ON DELETE RESTRICT;
ALTER TABLE public.stage2_model_publications ADD CONSTRAINT fk_stage2_publication_version_artifact CONSTRAINT fk_stage2_publication_version_artifact FOREIGN KEY (model_version_id, checkpoint_artifact_id) REFERENCES model_versions (id, checkpoint_artifact_id) ON DELETE RESTRICT;
ALTER TABLE public.stage2_model_publications ADD CONSTRAINT fk_stage2_publication_model_training CONSTRAINT fk_stage2_publication_model_training FOREIGN KEY (model_version_id, training_run_id) REFERENCES public.model_versions (id, training_run_id) ON DELETE RESTRICT;
```

Índices explícitos: `uq_stage2_model_publications_id_version`, `idx_stage2_publication_candidates`, `uq_stage2_publication_active_version`.
Auditoría: published_at, deactivated_at, created_at, updated_at.
JSONB: metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## synthetic_data_runs

Procedencia de generación sintética y dataset fuente por run; no duplica dataset oficial.

Dominio: C. Imágenes / pacientes / splits. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| run_id | uuid | YES |  |
| method | text | YES |  |
| num_images_generated | integer | YES |  |
| source_dataset_id | uuid | YES |  |
| output_path | text | YES |  |
| generation_parameters | jsonb | YES | CAST('{}' AS jsonb) |
| quality_checks | jsonb | YES | CAST('{}' AS jsonb) |
| created_at | timestamp with time zone | YES | now() |
| metadata | jsonb | YES | CAST('{}' AS jsonb) |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.synthetic_data_runs ADD CONSTRAINT synthetic_data_runs_pkey CONSTRAINT synthetic_data_runs_pkey PRIMARY KEY (id);
ALTER TABLE public.synthetic_data_runs ADD CONSTRAINT synthetic_data_runs_run_id_fkey CONSTRAINT synthetic_data_runs_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;
ALTER TABLE public.synthetic_data_runs ADD CONSTRAINT synthetic_data_runs_source_dataset_id_fkey CONSTRAINT synthetic_data_runs_source_dataset_id_fkey FOREIGN KEY (source_dataset_id) REFERENCES datasets (id) ON DELETE RESTRICT;
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: generation_parameters, quality_checks, metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: source_dataset_id.

## train_execution_records

Ledger mixto legacy/E10: PK run-kind-phase-key, event_id global y sequence por run.

Dominio: J. TRAIN / execution ledger. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| run_id | uuid | NO |  |
| kind | text | NO |  |
| phase | text | NO |  |
| record_key | text | NO |  |
| payload | jsonb | NO |  |
| created_at | timestamp with time zone | NO | clock_timestamp() |
| event_id | uuid | YES |  |
| event_sequence | numeric | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.train_execution_records ADD CONSTRAINT train_execution_records_pkey CONSTRAINT train_execution_records_pkey PRIMARY KEY (run_id, kind, phase, record_key);
ALTER TABLE public.train_execution_records ADD CONSTRAINT train_event_metadata CONSTRAINT train_event_metadata CHECK ((event_id IS NULL AND event_sequence IS NULL AND kind <> CAST('e10_event' AS text)) OR (event_id IS NOT NULL AND event_sequence IS NOT NULL AND event_sequence >= CAST(1 AS numeric) AND event_sequence = trunc(event_sequence) AND event_sequence <> ALL(ARRAY[CAST('NaN' AS numeric), CAST('Infinity' AS numeric), CAST('-Infinity' AS numeric)]) AND kind = CAST('e10_event' AS text) AND phase = CAST('run_event_v1' AS text) AND record_key = CAST(event_id AS text) AND NOT jsonb_typeof(payload -> CAST('canonical_event' AS text)) IS DISTINCT FROM CAST('string' AS text) AND (payload - CAST('canonical_event' AS text)) = CAST('{}' AS jsonb)));
ALTER TABLE public.train_execution_records ADD CONSTRAINT train_execution_records_payload_check CONSTRAINT train_execution_records_payload_check CHECK (jsonb_typeof(payload) = CAST('object' AS text));
ALTER TABLE public.train_execution_records ADD CONSTRAINT train_execution_records_run_id_fkey CONSTRAINT train_execution_records_run_id_fkey FOREIGN KEY (run_id) REFERENCES train_execution_sessions (run_id);
```

Índices explícitos: `train_event_id_unique`, `train_event_sequence_unique`.
Auditoría: created_at.
JSONB: payload. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## train_execution_revisions

Binding inmutable intento/campaña/revisión técnica de ejecución secuencial.

Dominio: J. TRAIN / execution ledger. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| attempt_id | uuid | NO |  |
| campaign_id | uuid | NO |  |
| revision_id | uuid | NO |  |
| created_at | timestamp with time zone | NO | clock_timestamp() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.train_execution_revisions ADD CONSTRAINT train_execution_revisions_pkey CONSTRAINT train_execution_revisions_pkey PRIMARY KEY (attempt_id);
ALTER TABLE public.train_execution_revisions ADD CONSTRAINT train_execution_revisions_attempt_id_fkey CONSTRAINT train_execution_revisions_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES campaign_attempts (id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public.train_execution_revisions ADD CONSTRAINT train_execution_revisions_campaign_id_fkey CONSTRAINT train_execution_revisions_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns (id);
ALTER TABLE public.train_execution_revisions ADD CONSTRAINT train_execution_revisions_campaign_id_revision_id_fkey CONSTRAINT train_execution_revisions_campaign_id_revision_id_fkey FOREIGN KEY (campaign_id, revision_id) REFERENCES campaign_technical_revisions (campaign_id, id);
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## train_execution_sessions

Sesión TRAIN autorizada, owner/runtime/config/dataset/estado; padre de records.

Dominio: J. TRAIN / execution ledger. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| run_id | uuid | NO |  |
| attempt_id | uuid | YES |  |
| owner | uuid | NO |  |
| host | text | NO |  |
| parent_pid | integer | NO |  |
| child_pid | integer | YES |  |
| state | text | NO | CAST('active' AS text) |
| configuration | jsonb | NO |  |
| dataset | jsonb | NO |  |
| environment | jsonb | NO |  |
| artifact_root | text | NO |  |
| cause | text | YES |  |
| started_at | timestamp with time zone | NO | clock_timestamp() |
| updated_at | timestamp with time zone | NO | clock_timestamp() |
| completion | jsonb | YES |  |
| verification | jsonb | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.train_execution_sessions ADD CONSTRAINT train_execution_sessions_pkey CONSTRAINT train_execution_sessions_pkey PRIMARY KEY (run_id);
ALTER TABLE public.train_execution_sessions ADD CONSTRAINT train_execution_sessions_artifact_root_key CONSTRAINT train_execution_sessions_artifact_root_key UNIQUE (artifact_root);
ALTER TABLE public.train_execution_sessions ADD CONSTRAINT train_execution_sessions_attempt_id_key CONSTRAINT train_execution_sessions_attempt_id_key UNIQUE (attempt_id);
ALTER TABLE public.train_execution_sessions ADD CONSTRAINT train_execution_sessions_check CONSTRAINT train_execution_sessions_check CHECK (state <> ALL(ARRAY[CAST('completed' AS text), CAST('verified' AS text)]) OR completion IS NOT NULL);
ALTER TABLE public.train_execution_sessions ADD CONSTRAINT train_execution_sessions_check1 CONSTRAINT train_execution_sessions_check1 CHECK (state <> CAST('verified' AS text) OR verification IS NOT NULL);
ALTER TABLE public.train_execution_sessions ADD CONSTRAINT train_execution_sessions_parent_pid_check CONSTRAINT train_execution_sessions_parent_pid_check CHECK (parent_pid > 0);
ALTER TABLE public.train_execution_sessions ADD CONSTRAINT train_execution_sessions_state_check CONSTRAINT train_execution_sessions_state_check CHECK (state = ANY(ARRAY[CAST('active' AS text), CAST('completed' AS text), CAST('verified' AS text), CAST('failed' AS text), CAST('interrupted' AS text)]));
ALTER TABLE public.train_execution_sessions ADD CONSTRAINT train_execution_sessions_attempt_id_fkey CONSTRAINT train_execution_sessions_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES campaign_attempts (id);
ALTER TABLE public.train_execution_sessions ADD CONSTRAINT train_execution_sessions_run_id_fkey CONSTRAINT train_execution_sessions_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id);
```

Índices explícitos: `uq_global_train_active`.
Auditoría: started_at, updated_at.
JSONB: configuration, dataset, environment, completion, verification. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## training_history

Curvas TRAIN/val por run-fase-epoch; v2 unicidad y métricas clínicas por época.

Dominio: J. TRAIN / execution ledger. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | pg_catalog.gen_random_uuid() |
| run_id | uuid | NO |  |
| epoch | integer | NO |  |
| loss | numeric | YES |  |
| accuracy | numeric | YES |  |
| precision_value | numeric | YES |  |
| recall_value | numeric | YES |  |
| auc | numeric | YES |  |
| val_loss | numeric | YES |  |
| val_accuracy | numeric | YES |  |
| val_precision | numeric | YES |  |
| val_recall | numeric | YES |  |
| val_auc | numeric | YES |  |
| learning_rate | numeric | YES |  |
| created_at | timestamp with time zone | YES | now() |
| metadata | jsonb | YES | CAST('{}' AS jsonb) |
| phase | text | NO | CAST('training' AS text) |
| train_loss | numeric | YES |  |
| train_accuracy | numeric | YES |  |
| train_specificity | numeric | YES |  |
| val_specificity | numeric | YES |  |
| train_f2 | numeric | YES |  |
| val_f2 | numeric | YES |  |
| train_balanced_accuracy | numeric | YES |  |
| val_balanced_accuracy | numeric | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.training_history ADD CONSTRAINT training_history_pkey CONSTRAINT training_history_pkey PRIMARY KEY (id);
ALTER TABLE public.training_history ADD CONSTRAINT uq_v2_epoch CONSTRAINT uq_v2_epoch UNIQUE (run_id, phase, epoch);
ALTER TABLE public.training_history ADD CONSTRAINT training_history_run_id_fkey CONSTRAINT training_history_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE RESTRICT;
ALTER TABLE public.training_history ADD CONSTRAINT ck_v2_epoch CONSTRAINT ck_v2_epoch CHECK (epoch >= 0);
ALTER TABLE public.training_history ADD CONSTRAINT v2_training_history_check_51b772d5ee79 CONSTRAINT v2_training_history_check_51b772d5ee79 CHECK (train_specificity BETWEEN 0 AND 1);
ALTER TABLE public.training_history ADD CONSTRAINT v2_training_history_check_3eea954e3a67 CONSTRAINT v2_training_history_check_3eea954e3a67 CHECK (val_specificity BETWEEN 0 AND 1);
ALTER TABLE public.training_history ADD CONSTRAINT v2_training_history_check_68190383a722 CONSTRAINT v2_training_history_check_68190383a722 CHECK (train_f2 BETWEEN 0 AND 1);
ALTER TABLE public.training_history ADD CONSTRAINT v2_training_history_check_03efeda77886 CONSTRAINT v2_training_history_check_03efeda77886 CHECK (val_f2 BETWEEN 0 AND 1);
ALTER TABLE public.training_history ADD CONSTRAINT v2_training_history_check_5cb83011b377 CONSTRAINT v2_training_history_check_5cb83011b377 CHECK (train_balanced_accuracy BETWEEN 0 AND 1);
ALTER TABLE public.training_history ADD CONSTRAINT v2_training_history_check_edfadf7cb46b CONSTRAINT v2_training_history_check_edfadf7cb46b CHECK (val_balanced_accuracy BETWEEN 0 AND 1);
```

Índices explícitos: `idx_training_history_run_id`.
Auditoría: created_at.
JSONB: metadata. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## user_roles

Asociación protegida usuario–rol.

Dominio: A. Usuarios / seguridad. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| user_id | uuid | NO |  |
| role_id | uuid | NO |  |
| created_at | timestamp with time zone | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.user_roles ADD CONSTRAINT user_roles_pkey CONSTRAINT user_roles_pkey PRIMARY KEY (user_id, role_id);
ALTER TABLE public.user_roles ADD CONSTRAINT user_roles_role_id_fkey CONSTRAINT user_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE RESTRICT;
ALTER TABLE public.user_roles ADD CONSTRAINT user_roles_user_id_fkey CONSTRAINT user_roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE;
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## users

Identidad/autenticación y hashes de contraseña protegidos; nunca fixtures de diseño.

Dominio: A. Usuarios / seguridad. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO |  |
| username | text | NO |  |
| email | text | YES |  |
| password_hash | text | NO |  |
| status | text | NO | CAST('active' AS text) |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |
| last_login_at | timestamp with time zone | YES |  |
| disabled_at | timestamp with time zone | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.users ADD CONSTRAINT users_pkey CONSTRAINT users_pkey PRIMARY KEY (id);
ALTER TABLE public.users ADD CONSTRAINT users_email_key CONSTRAINT users_email_key UNIQUE (email);
ALTER TABLE public.users ADD CONSTRAINT users_username_key CONSTRAINT users_username_key UNIQUE (username);
ALTER TABLE public.users ADD CONSTRAINT users_status_check CONSTRAINT users_status_check CHECK (status = ANY(ARRAY[CAST('active' AS text), CAST('disabled' AS text)]));
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at, updated_at, last_login_at, disabled_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: password_hash.

## xai_artifacts

Manifiesto de archivos numéricos y visuales externos de una explicación.

Dominio: O. XAI. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | gen_random_uuid() |
| evidence_id | uuid | NO |  |
| artifact_id | uuid | YES |  |
| assessment_artifact_id | uuid | YES |  |
| role | text | NO |  |
| ordinal | integer | NO | 0 |
| storage_uri | text | NO |  |
| sha256 | text | NO |  |
| byte_size | bigint | NO |  |
| mime_type | text | NO |  |
| numeric_dtype | text | YES |  |
| tensor_shape | integer[] | YES |  |
| axis_order | text | YES |  |
| coordinate_space | text | YES |  |
| availability | text | NO |  |
| created_at | timestamptz | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_primary_8c8464f42472 CONSTRAINT v2_xai_artifacts_primary_8c8464f42472 PRIMARY KEY (id);
ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_unique_ee15a9513a9e CONSTRAINT v2_xai_artifacts_unique_ee15a9513a9e UNIQUE (evidence_id, role, ordinal);
ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_foreign_4b080b42e888 CONSTRAINT v2_xai_artifacts_foreign_4b080b42e888 FOREIGN KEY (evidence_id) REFERENCES public.xai_evidence (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_foreign_e3d2eb574718 CONSTRAINT v2_xai_artifacts_foreign_e3d2eb574718 FOREIGN KEY (artifact_id) REFERENCES public.artifacts (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_foreign_f9c5548be835 CONSTRAINT v2_xai_artifacts_foreign_f9c5548be835 FOREIGN KEY (assessment_artifact_id) REFERENCES public.assessment_artifacts (artifact_id) ON DELETE RESTRICT;
ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_70ab6797c0c6 CONSTRAINT v2_xai_artifacts_check_70ab6797c0c6 CHECK (num_nonnulls(artifact_id, assessment_artifact_id) <= 1);
ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_eb359eee6311 CONSTRAINT v2_xai_artifacts_check_eb359eee6311 CHECK (role IN ('RAW_ATTRIBUTION', 'SPATIAL_MAP', 'SEGMENTATION', 'REGION_WEIGHTS', 'OVERLAY', 'HEATMAP_RENDER', 'BACKGROUND_MANIFEST', 'INPUT_MANIFEST'));
ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_967aa2df2b88 CONSTRAINT v2_xai_artifacts_check_967aa2df2b88 CHECK (ordinal >= 0);
ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_20426a1e7fe3 CONSTRAINT v2_xai_artifacts_check_20426a1e7fe3 CHECK (sha256 ~ '^[0-9a-f]{64}$');
ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_a81626200b02 CONSTRAINT v2_xai_artifacts_check_a81626200b02 CHECK (byte_size >= 0);
ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_4b7ae3b26ca5 CONSTRAINT v2_xai_artifacts_check_4b7ae3b26ca5 CHECK (availability IN ('available', 'missing', 'quarantined', 'archived'));
ALTER TABLE public.xai_artifacts ADD CONSTRAINT v2_xai_artifacts_check_a68006e838dc CONSTRAINT v2_xai_artifacts_check_a68006e838dc CHECK (tensor_shape IS NULL OR (cardinality(tensor_shape) > 0 AND 0 < ALL(tensor_shape)));
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: sha256.

## xai_evaluation_members

Miembros N:M de cada medición XAI, con rol y membresía congelada.

Dominio: O. XAI. Acción: NEW.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| evaluation_id | uuid | NO |  |
| xai_evidence_id | uuid | NO |  |
| member_role | text | NO |  |
| created_at | timestamptz | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.xai_evaluation_members ADD CONSTRAINT xai_evaluation_members_pkey CONSTRAINT xai_evaluation_members_pkey PRIMARY KEY (evaluation_id, xai_evidence_id);
ALTER TABLE public.xai_evaluation_members ADD CONSTRAINT fk_xai_member_evaluation CONSTRAINT fk_xai_member_evaluation FOREIGN KEY (evaluation_id) REFERENCES public.xai_quantitative_evaluations (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_evaluation_members ADD CONSTRAINT fk_xai_member_evidence CONSTRAINT fk_xai_member_evidence FOREIGN KEY (xai_evidence_id) REFERENCES public.xai_evidence (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_evaluation_members ADD CONSTRAINT ck_xai_member_role CONSTRAINT ck_xai_member_role CHECK (member_role ~ '^[a-z][a-z0-9_]*$');
```

Índices explícitos: `ix_xai_member_evidence`.
Auditoría: created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## xai_evaluation_protocols

Identidad reproducible del protocolo de una métrica XAI extensible.

Dominio: O. XAI. Acción: NEW.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | gen_random_uuid() |
| metric_name | text | NO |  |
| metric_family | text | NO |  |
| protocol_name | text | NO |  |
| protocol_version | text | NO |  |
| parameters | jsonb | NO |  |
| normalization_strategy | text | NO |  |
| perturbation_strategy | text | YES |  |
| reference_definition | jsonb | YES |  |
| canonical_protocol | text | NO |  |
| protocol_hash | text | NO |  |
| created_at | timestamptz | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.xai_evaluation_protocols ADD CONSTRAINT xai_evaluation_protocols_pkey CONSTRAINT xai_evaluation_protocols_pkey PRIMARY KEY (id);
ALTER TABLE public.xai_evaluation_protocols ADD CONSTRAINT uq_xai_protocol_hash CONSTRAINT uq_xai_protocol_hash UNIQUE (protocol_hash);
ALTER TABLE public.xai_evaluation_protocols ADD CONSTRAINT uq_xai_protocol_metric CONSTRAINT uq_xai_protocol_metric UNIQUE (id, metric_name);
ALTER TABLE public.xai_evaluation_protocols ADD CONSTRAINT ck_protocol_hash_xai_protocol CONSTRAINT ck_protocol_hash_xai_protocol CHECK (protocol_hash ~ '^[0-9a-f]{64}$');
ALTER TABLE public.xai_evaluation_protocols ADD CONSTRAINT ck_xai_evaluation_protocols_parameters CONSTRAINT ck_xai_evaluation_protocols_parameters CHECK (jsonb_typeof(parameters) = 'object');
ALTER TABLE public.xai_evaluation_protocols ADD CONSTRAINT ck_xai_protocol_identity CONSTRAINT ck_xai_protocol_identity CHECK (length(btrim(metric_name)) > 0 AND length(btrim(metric_family)) > 0 AND metric_family = lower(metric_family) AND length(btrim(protocol_name)) > 0 AND length(btrim(protocol_version)) > 0 AND length(btrim(normalization_strategy)) > 0);
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: parameters, reference_definition. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: canonical_protocol, protocol_hash.

## xai_evidence

Explicación individual reproducible con contexto experimental o celular y checkpoint.

Dominio: O. XAI. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | gen_random_uuid() |
| ml_explanation_id | uuid | YES |  |
| cell_explanation_id | uuid | YES |  |
| assessment_attempt_id | uuid | YES |  |
| assessment_sample_id | uuid | YES |  |
| prediction_id | uuid | YES |  |
| cell_prediction_id | uuid | YES |  |
| evaluation_id | uuid | YES |  |
| dataset_source_record_id | uuid | YES |  |
| input_artifact_id | uuid | YES |  |
| microscopy_image_id | uuid | YES |  |
| run_id | uuid | YES |  |
| model_version_id | uuid | YES |  |
| checkpoint_artifact_id | uuid | NO |  |
| method_configuration_id | uuid | NO |  |
| target_layer | text | YES |  |
| prediction_score | numeric | YES |  |
| source_commit | text | NO |  |
| input_contract | jsonb | NO |  |
| input_contract_hash | text | NO |  |
| input_storage_uri | text | NO |  |
| input_sha256 | text | NO |  |
| checkpoint_sha256 | text | NO |  |
| target_class | smallint | NO |  |
| explained_output | text | NO |  |
| processing_stage | text | NO |  |
| seed | bigint | YES |  |
| background_manifest_uri | text | YES |  |
| background_manifest_sha256 | text | YES |  |
| environment_snapshot | jsonb | NO |  |
| generated_at | timestamptz | NO |  |
| created_at | timestamptz | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_primary_8c8464f42472 CONSTRAINT v2_xai_evidence_primary_8c8464f42472 PRIMARY KEY (id);
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_unique_d9477cb1fece CONSTRAINT v2_xai_evidence_unique_d9477cb1fece UNIQUE (ml_explanation_id);
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_unique_d4bf0f195fcf CONSTRAINT v2_xai_evidence_unique_d4bf0f195fcf UNIQUE (cell_explanation_id);
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_unique_0be310eeb2b7 CONSTRAINT v2_xai_evidence_unique_0be310eeb2b7 UNIQUE (assessment_attempt_id, assessment_sample_id);
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_9851edbb8079 CONSTRAINT v2_xai_evidence_foreign_9851edbb8079 FOREIGN KEY (ml_explanation_id) REFERENCES public.explainability_results (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_3fe88bd35854 CONSTRAINT v2_xai_evidence_foreign_3fe88bd35854 FOREIGN KEY (cell_explanation_id) REFERENCES public.cell_explanations (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_4b04405ab069 CONSTRAINT v2_xai_evidence_foreign_4b04405ab069 FOREIGN KEY (prediction_id) REFERENCES public.predictions (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_029e07f1d6db CONSTRAINT v2_xai_evidence_foreign_029e07f1d6db FOREIGN KEY (cell_prediction_id) REFERENCES public.cell_predictions (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_a402d28a70f6 CONSTRAINT v2_xai_evidence_foreign_a402d28a70f6 FOREIGN KEY (evaluation_id) REFERENCES public.evaluations (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_e8d9af78807c CONSTRAINT v2_xai_evidence_foreign_e8d9af78807c FOREIGN KEY (dataset_source_record_id) REFERENCES public.dataset_source_records (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_a1c9b824423e CONSTRAINT v2_xai_evidence_foreign_a1c9b824423e FOREIGN KEY (input_artifact_id) REFERENCES public.artifacts (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_ad1ea3f78d92 CONSTRAINT v2_xai_evidence_foreign_ad1ea3f78d92 FOREIGN KEY (microscopy_image_id) REFERENCES public.microscopy_images (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_db5338c19de4 CONSTRAINT v2_xai_evidence_foreign_db5338c19de4 FOREIGN KEY (run_id) REFERENCES public.runs (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_b946b2b207f3 CONSTRAINT v2_xai_evidence_foreign_b946b2b207f3 FOREIGN KEY (model_version_id) REFERENCES public.model_versions (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_6aec504c7a2f CONSTRAINT v2_xai_evidence_foreign_6aec504c7a2f FOREIGN KEY (checkpoint_artifact_id) REFERENCES public.artifacts (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_71beacad95d0 CONSTRAINT v2_xai_evidence_check_71beacad95d0 CHECK (jsonb_typeof(input_contract) = 'object');
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_b93d47c84570 CONSTRAINT v2_xai_evidence_check_b93d47c84570 CHECK (input_contract_hash ~ '^[0-9a-f]{64}$');
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_93787689f516 CONSTRAINT v2_xai_evidence_check_93787689f516 CHECK (input_sha256 ~ '^[0-9a-f]{64}$');
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_6bf21e8ba9a2 CONSTRAINT v2_xai_evidence_check_6bf21e8ba9a2 CHECK (checkpoint_sha256 ~ '^[0-9a-f]{64}$');
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_185d894424d0 CONSTRAINT v2_xai_evidence_check_185d894424d0 CHECK (target_class IN (0, 1));
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_26e9e3a0278b CONSTRAINT v2_xai_evidence_check_26e9e3a0278b CHECK (explained_output IN ('probability_parasitized', 'probability_uninfected', 'raw_output'));
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_5027e188ea2a CONSTRAINT v2_xai_evidence_check_5027e188ea2a CHECK (processing_stage IN ('model_input', 'cell_crop', 'evaluation_sample'));
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_3e7a5ed7ffee CONSTRAINT v2_xai_evidence_check_3e7a5ed7ffee CHECK (background_manifest_sha256 ~ '^[0-9a-f]{64}$');
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_9d77320c4af9 CONSTRAINT v2_xai_evidence_check_9d77320c4af9 CHECK (jsonb_typeof(environment_snapshot) = 'object');
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_foreign_52bd313b1c15 CONSTRAINT v2_xai_evidence_foreign_52bd313b1c15 FOREIGN KEY (assessment_attempt_id, assessment_sample_id) REFERENCES public.assessment_results (attempt_id, sample_id) MATCH FULL ON DELETE RESTRICT;
ALTER TABLE public.xai_evidence ADD CONSTRAINT ck_xai_input_origin CONSTRAINT ck_xai_input_origin CHECK (num_nonnulls(dataset_source_record_id, microscopy_image_id, input_artifact_id) = 1);
ALTER TABLE public.xai_evidence ADD CONSTRAINT v2_xai_evidence_check_bfbb62e97a91 CONSTRAINT v2_xai_evidence_check_bfbb62e97a91 CHECK (num_nonnulls(prediction_id, cell_prediction_id) <= 1);
ALTER TABLE public.xai_evidence ADD CONSTRAINT fk_xai_method_configuration CONSTRAINT fk_xai_method_configuration FOREIGN KEY (method_configuration_id) REFERENCES public.xai_method_configurations (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_evidence ADD CONSTRAINT ck_xai_provisional_checkpoint CONSTRAINT ck_xai_provisional_checkpoint CHECK (model_version_id IS NOT NULL OR run_id IS NOT NULL);
ALTER TABLE public.xai_evidence ADD CONSTRAINT ck_xai_prediction_score CONSTRAINT ck_xai_prediction_score CHECK (prediction_score >= 0 AND prediction_score <= 1);
```

Índices explícitos: `ix_xai_same_image`, `ix_xai_evaluation`, `ix_xai_method_configuration`.
Auditoría: generated_at, created_at.
JSONB: input_contract, environment_snapshot. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: dataset_source_record_id, source_commit, input_contract_hash, input_sha256, checkpoint_sha256, background_manifest_sha256.

## xai_interpretations

Interpretación escrita y versionada de la explicación por un autor.

Dominio: O. XAI. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | gen_random_uuid() |
| evidence_id | uuid | NO |  |
| author_user_id | uuid | NO |  |
| interpretation | text | NO |  |
| limitations | text | NO |  |
| created_at | timestamptz | NO | now() |
| supersedes_id | uuid | YES |  |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.xai_interpretations ADD CONSTRAINT v2_xai_interpretations_primary_8c8464f42472 CONSTRAINT v2_xai_interpretations_primary_8c8464f42472 PRIMARY KEY (id);
ALTER TABLE public.xai_interpretations ADD CONSTRAINT v2_xai_interpretations_foreign_4b080b42e888 CONSTRAINT v2_xai_interpretations_foreign_4b080b42e888 FOREIGN KEY (evidence_id) REFERENCES public.xai_evidence (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_interpretations ADD CONSTRAINT v2_xai_interpretations_foreign_6b09f9926d4f CONSTRAINT v2_xai_interpretations_foreign_6b09f9926d4f FOREIGN KEY (author_user_id) REFERENCES public.users (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_interpretations ADD CONSTRAINT v2_xai_interpretations_check_c7c3afcde9f7 CONSTRAINT v2_xai_interpretations_check_c7c3afcde9f7 CHECK (length(pg_catalog.btrim(interpretation)) > 0);
ALTER TABLE public.xai_interpretations ADD CONSTRAINT v2_xai_interpretations_foreign_af451d74af77 CONSTRAINT v2_xai_interpretations_foreign_af451d74af77 FOREIGN KEY (supersedes_id) REFERENCES public.xai_interpretations (id) ON DELETE RESTRICT;
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## xai_method_configurations

Identidad reutilizable de método, implementación, versión y parámetros XAI.

Dominio: O. XAI. Acción: NEW.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | gen_random_uuid() |
| method | text | NO |  |
| implementation | text | NO |  |
| implementation_version | text | NO |  |
| parameters | jsonb | NO |  |
| canonical_configuration | text | NO |  |
| configuration_hash | text | NO |  |
| created_at | timestamptz | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.xai_method_configurations ADD CONSTRAINT xai_method_configurations_pkey CONSTRAINT xai_method_configurations_pkey PRIMARY KEY (id);
ALTER TABLE public.xai_method_configurations ADD CONSTRAINT uq_xai_method_configuration_hash CONSTRAINT uq_xai_method_configuration_hash UNIQUE (configuration_hash);
ALTER TABLE public.xai_method_configurations ADD CONSTRAINT ck_configuration_hash_xai_method CONSTRAINT ck_configuration_hash_xai_method CHECK (configuration_hash ~ '^[0-9a-f]{64}$');
ALTER TABLE public.xai_method_configurations ADD CONSTRAINT ck_xai_method_configurations_parameters CONSTRAINT ck_xai_method_configurations_parameters CHECK (jsonb_typeof(parameters) = 'object');
ALTER TABLE public.xai_method_configurations ADD CONSTRAINT ck_xai_method_identity CONSTRAINT ck_xai_method_identity CHECK (length(btrim(method)) > 0 AND method = lower(method) AND length(btrim(implementation)) > 0 AND length(btrim(implementation_version)) > 0);
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: parameters. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: canonical_configuration, configuration_hash.

## xai_quantitative_evaluations

Una medición vertical por protocolo y conjunto de explicaciones; NULL con razón.

Dominio: O. XAI. Acción: MODIFY.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | gen_random_uuid() |
| protocol_id | uuid | NO |  |
| metric_name | text | NO |  |
| membership_hash | text | NO |  |
| metric_value | double precision | YES |  |
| undefined_reason | text | YES |  |
| seed | bigint | YES |  |
| sample_count | bigint | NO |  |
| reference_annotation_id | uuid | YES |  |
| reference_annotation_version | integer | YES |  |
| reference_manifest_uri | text | YES |  |
| reference_manifest_sha256 | text | YES |  |
| details_uri | text | YES |  |
| details_sha256 | text | YES |  |
| evaluated_at | timestamptz | NO |  |
| created_at | timestamptz | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT v2_xai_quantitative_evaluations_primary_8c8464f42472 CONSTRAINT v2_xai_quantitative_evaluations_primary_8c8464f42472 PRIMARY KEY (id);
ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT fk_xai_metric_protocol CONSTRAINT fk_xai_metric_protocol FOREIGN KEY (protocol_id, metric_name) REFERENCES public.xai_evaluation_protocols (id, metric_name) ON DELETE RESTRICT;
ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT fk_xai_reference_annotation CONSTRAINT fk_xai_reference_annotation FOREIGN KEY (reference_annotation_id) REFERENCES public.scientific_validation_annotations (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT ck_xai_metric_defined CONSTRAINT ck_xai_metric_defined CHECK ((metric_value IS NULL AND undefined_reason IS NOT NULL AND length(btrim(undefined_reason)) > 0) OR (metric_value IS NOT NULL AND undefined_reason IS NULL AND metric_value > CAST('-Infinity' AS float8) AND metric_value < CAST('Infinity' AS float8)));
ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT ck_xai_sample_count CONSTRAINT ck_xai_sample_count CHECK (sample_count > 0);
ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT ck_xai_reference_tuple CONSTRAINT ck_xai_reference_tuple CHECK (num_nonnulls(reference_annotation_id, reference_annotation_version, reference_manifest_uri, reference_manifest_sha256) IN (0, 4) AND (reference_annotation_version IS NULL OR reference_annotation_version > 0) AND (reference_manifest_sha256 IS NULL OR reference_manifest_sha256 ~ '^[0-9a-f]{64}$'));
ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT ck_xai_details_tuple CONSTRAINT ck_xai_details_tuple CHECK (num_nonnulls(details_uri, details_sha256) IN (0, 2) AND (details_sha256 IS NULL OR details_sha256 ~ '^[0-9a-f]{64}$'));
ALTER TABLE public.xai_quantitative_evaluations ADD CONSTRAINT ck_xai_membership_hash CONSTRAINT ck_xai_membership_hash CHECK (membership_hash ~ '^[0-9a-f]{64}$');
```

Índices explícitos: `ix_xai_metric_protocol`, `ix_xai_reference_annotation`.
Auditoría: evaluated_at, created_at.
JSONB: no utiliza. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: membership_hash, reference_manifest_sha256, details_sha256.

## xai_region_attributions

Atribución por región discreta; los mapas densos permanecen en archivos externos.

Dominio: O. XAI. Acción: NEW.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| xai_evidence_id | uuid | NO |  |
| region_type | text | NO |  |
| region_index | integer | NO |  |
| attribution_value | double precision | NO |  |
| rank | integer | YES |  |
| region_definition | jsonb | YES |  |
| created_at | timestamptz | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.xai_region_attributions ADD CONSTRAINT xai_region_attributions_pkey CONSTRAINT xai_region_attributions_pkey PRIMARY KEY (xai_evidence_id, region_type, region_index);
ALTER TABLE public.xai_region_attributions ADD CONSTRAINT fk_xai_region_evidence CONSTRAINT fk_xai_region_evidence FOREIGN KEY (xai_evidence_id) REFERENCES public.xai_evidence (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_region_attributions ADD CONSTRAINT ck_xai_region_domain CONSTRAINT ck_xai_region_domain CHECK (region_index >= 0 AND length(btrim(region_type)) > 0 AND (rank IS NULL OR rank > 0) AND attribution_value > CAST('-Infinity' AS float8) AND attribution_value < CAST('Infinity' AS float8) AND (region_definition IS NULL OR jsonb_typeof(region_definition) = 'object'));
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: created_at.
JSONB: region_definition. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.

## xai_specialist_reviews

Revisión clínica de la interpretación, independiente de Agreement.

Dominio: O. XAI. Acción: KEEP.

Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):

| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |
|---|---|---|---|
| id | uuid | NO | gen_random_uuid() |
| interpretation_id | uuid | NO |  |
| reviewer_user_id | uuid | NO |  |
| decision | text | NO |  |
| rationale | text | NO |  |
| competence_snapshot | jsonb | NO |  |
| reviewed_at | timestamptz | NO | now() |

Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):

```sql
ALTER TABLE public.xai_specialist_reviews ADD CONSTRAINT v2_xai_specialist_reviews_primary_8c8464f42472 CONSTRAINT v2_xai_specialist_reviews_primary_8c8464f42472 PRIMARY KEY (id);
ALTER TABLE public.xai_specialist_reviews ADD CONSTRAINT v2_xai_specialist_reviews_foreign_4735bf604cb2 CONSTRAINT v2_xai_specialist_reviews_foreign_4735bf604cb2 FOREIGN KEY (interpretation_id) REFERENCES public.xai_interpretations (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_specialist_reviews ADD CONSTRAINT v2_xai_specialist_reviews_foreign_7ca01df9e490 CONSTRAINT v2_xai_specialist_reviews_foreign_7ca01df9e490 FOREIGN KEY (reviewer_user_id) REFERENCES public.users (id) ON DELETE RESTRICT;
ALTER TABLE public.xai_specialist_reviews ADD CONSTRAINT v2_xai_specialist_reviews_check_920877b7b5d1 CONSTRAINT v2_xai_specialist_reviews_check_920877b7b5d1 CHECK (decision IN ('supported', 'unsupported', 'inconclusive'));
ALTER TABLE public.xai_specialist_reviews ADD CONSTRAINT v2_xai_specialist_reviews_check_d8ae577b1870 CONSTRAINT v2_xai_specialist_reviews_check_d8ae577b1870 CHECK (length(pg_catalog.btrim(rationale)) > 0);
ALTER TABLE public.xai_specialist_reviews ADD CONSTRAINT v2_xai_specialist_reviews_check_07baf4b694f5 CONSTRAINT v2_xai_specialist_reviews_check_07baf4b694f5 CHECK (jsonb_typeof(competence_snapshot) = 'object');
```

Índices explícitos: ninguno adicional a PK/UNIQUE.
Auditoría: reviewed_at.
JSONB: competence_snapshot. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.
Provenance/hash: por FK a las entidades de origen.
