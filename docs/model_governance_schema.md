# Esquema de gobernanza y linaje de modelos

**Compatibilidad objetivo:** PostgreSQL 17  
**Convención de identidad:** UUID y claves foráneas  
**Convención clínica:** `0 = uninfected`, `1 = parasitized`  
**Estado del documento:** contrato del esquema preparado en el repositorio; no acredita aplicación sobre una base viva

## Alcance

Este documento especifica el modelo físico que representa el linaje:

~~~text
training run
└── model version
    ├── evaluation run
    ├── explainability run
    └── deployed model version
        └── inference run
            └── image analysis job
                └── cell predictions
~~~

La implementación es aditiva. Reutiliza las tablas históricas cuando ya representan correctamente una entidad y crea tablas nuevas solo para deployments y trabajos de análisis. Los paths se conservan por compatibilidad, pero una ruta nunca es la única identidad de un modelo gobernado.

## Decisiones físicas

| Entidad lógica | Objeto físico canónico | Decisión |
|---|---|---|
| Training run | `runs` con `run_type = 'training'` | Reutilizado |
| Model version | `model_versions` | Reutilizado y extendido |
| Evaluation run | `runs` + `run_lineage` | Reutilizado; no existe tabla duplicada |
| Explainability run | `runs` + `run_lineage` | Reutilizado; no existe tabla duplicada |
| Deployed model version | `deployed_model_versions` | Tabla nueva |
| Relación inference/deployment | `run_model_deployments` | Tabla puente nueva, apta para ensembles |
| Inference run | `runs` con `run_type = 'inference'` | Reutilizado; `inference_runs` es una vista |
| Image analysis job | `image_analysis_jobs` | Tabla nueva |
| Cell prediction | `predictions` con alcance celular | Reutilizado; `cell_predictions` es una vista |
| Bytes del modelo/inputs/outputs | `artifacts` | Reutilizado |
| Threshold calibrado | `run_threshold_calibration` | Reutilizado y relacionado |
| Política de checkpoint | `run_checkpoint_policy` | Reutilizado y relacionado |
| Evaluation/explainability lineage | `run_lineage` | Reutilizado y fortalecido |
| Historial de migración | `schema_migrations` | Ledger administrativo |
| Evidencia de backfill | `model_governance_backfill_audit` | Registro append-only de aplicación/reversión |

`inference_runs` y `cell_predictions` son read models. Los escritores insertan en `runs` y `predictions`, respectivamente; escribir en tablas paralelas produciría dos fuentes de verdad y no está soportado.

## Capa Python

El paquete público `malaria_dl_local_project/src/model_governance` separa dominio y persistencia:

- `entities.py`: dataclasses `frozen` `ModelVersion`, `DeployedModelVersion`, `InferenceRun`, `ImageAnalysisJob`, `CellPrediction` y `LineageRecord`, además de enums y validaciones clínicas.
- `repository.py`: operaciones keyword-only `create_model_version`, `create_deployed_model_version`, `create_inference_run`, `create_image_analysis_job`, `create_cell_prediction` y `get_lineage`.
- `errors.py`: `ModelGovernanceError` y errores tipados de validación, not found, ownership, state, conflict e infraestructura.
- `__init__.py`: superficie pública estable del paquete.

Todas las operaciones aceptan `connection_or_session=None`. Si se entrega una conexión/sesión, la reutilizan sin abrir otra transacción; en caso contrario usan `src.db.get_connection()`. Esto permite incluir varias escrituras en una sola transacción y hace atómica la creación de `runs + run_model_deployments` para inferencia.

Comportamiento relevante:

- `create_model_version` comprueba que el run sea training, que el artifact le pertenezca y que path/hash/tamaño coincidan. El argumento API `artifact_path` se persiste en `checkpoint_path`; `artifact_uri` queda separado.
- `create_deployed_model_version` resuelve el artifact/snapshots desde una versión gobernada. Su default es `pending`, nunca `active`.
- `create_inference_run` exige un deployment activo y crea el run más su vínculo `primary` de forma atómica.
- `create_image_analysis_job` exige run `started`, conserva el threshold del deployment y usa `(inference_run_id, idempotency_key)` para devolver el mismo job solo si el payload de identidad coincide.
- `create_cell_prediction` escribe en `predictions`, completa también campos legacy de score/threshold y exige que classifier, job, run, deployment y threshold coincidan.
- `get_lineage` exige exactamente un anchor entre training/version/deployment/run/job/prediction y devuelve rutas aplanadas que incluyen evaluation/explainability mediante `run_lineage`.

La capa Python valida antes del INSERT, pero no sustituye checks, FKs, índices ni triggers PostgreSQL; ambas defensas son deliberadas.

## Diagrama de relaciones

~~~mermaid
erDiagram
    RUNS ||--o{ MODEL_VERSIONS : "training_run_id"
    MODELS ||--o{ MODEL_VERSIONS : "model_id"
    ARTIFACTS ||--o{ MODEL_VERSIONS : "checkpoint_artifact_id"
    RUNS ||--o{ RUN_LINEAGE : "parent_run_id"
    RUNS ||--o{ RUN_LINEAGE : "child_run_id"
    MODEL_VERSIONS ||--o{ RUN_LINEAGE : "model_version_id"
    ARTIFACTS ||--o{ RUN_LINEAGE : "checkpoint_artifact_id"
    MODEL_VERSIONS ||--o{ DEPLOYED_MODEL_VERSIONS : authorizes
    RUN_THRESHOLD_CALIBRATION ||--o{ DEPLOYED_MODEL_VERSIONS : freezes
    DEPLOYED_MODEL_VERSIONS ||--o{ RUN_MODEL_DEPLOYMENTS : used_by
    RUNS ||--o{ RUN_MODEL_DEPLOYMENTS : inference
    RUNS ||--o{ IMAGE_ANALYSIS_JOBS : inference_run_id
    DEPLOYED_MODEL_VERSIONS ||--o{ IMAGE_ANALYSIS_JOBS : deployment
    ARTIFACTS ||--o{ IMAGE_ANALYSIS_JOBS : input_artifact
    DATASET_SPLIT_IMAGES ||--o{ IMAGE_ANALYSIS_JOBS : source_image
    IMAGE_ANALYSIS_JOBS ||--o{ PREDICTIONS : contains
    MODEL_VERSIONS ||--o{ PREDICTIONS : classifier
    MODEL_VERSIONS ||--o{ PREDICTIONS : detector
    ARTIFACTS ||--o{ PREDICTIONS : crop
    ARTIFACTS ||--o{ PREDICTIONS : explanation
    DATASET_SPLIT_IMAGES ||--o{ PREDICTIONS : source_image
~~~

La flecha conceptual `model_versions → evaluation/explainability` se materializa mediante `run_lineage`: el run de training es `parent_run_id`, el run derivado es `child_run_id` y la versión/artifact exactos quedan en `model_version_id` y `checkpoint_artifact_id`.

## Identidad y equivalencias legacy

| Contrato gobernado | Equivalente histórico conservado | Regla de uso |
|---|---|---|
| `model_version_id` | `checkpoint_path`, `best_model_path`, `final_model_path` | El UUID es identidad; los paths son atributos legacy |
| Artifact y SHA-256 de la versión | `artifacts.id`, `artifacts.checksum`, `artifacts.file_size_bytes` | Los bytes se demuestran mediante FK y checksum, no por basename |
| Número/nombre de versión | `model_versions.version_name` | Se conserva para consumidores existentes y se normaliza en el contrato nuevo |
| Configuración del inference run | `runs.parameters`, `runs.execution_parameters`, `runs.metadata` | Los campos gobernados son explícitos; los JSONB preservan payloads previos |
| Finalización del inference run | `runs.finished_at` | Se expone como `completed_at` en el read model cuando corresponda |
| Probabilidad parasitized | `predictions.score_positive_label` o metadata legacy | Para filas celulares se usa el campo gobernado explícito |
| Threshold | `predictions.threshold` o metadata legacy | Para filas celulares se usa `threshold_used` y su fuente queda trazable en job/deployment |
| Label predicha textual | `predictions.predicted_label` | El contrato celular agrega clase binaria explícita y valida su concordancia |
| Imagen de origen | `predictions.image_id`, `image_path`, `dataset_id` | El job y el artifact/source UUID son la identidad gobernada |

Los datos históricos no se reescriben para aparentar que siempre tuvieron IDs gobernados. Las columnas nuevas que aceptan `NULL` durante la transición distinguen legado no resuelto de escritura nueva; un backfill solo puede completar relaciones exactas y auditables.

## Catálogo de tablas y vistas

### `schema_migrations`

Ledger administrativo creado por el runner y declarado también en `023_schema_migrations_baseline.sql` para ejecución SQL directa.

| Campo | Tipo/regla | Propósito |
|---|---|---|
| `migration_id` | `TEXT PRIMARY KEY` | Nombre inmutable del archivo de migración |
| `checksum` | `TEXT NOT NULL` | SHA-256 hexadecimal; `chk_schema_migrations_checksum_sha256` exige 64 caracteres lowercase |
| `applied_at` | `TIMESTAMPTZ NOT NULL DEFAULT NOW()` | Momento de registro |
| `execution_metadata` | `JSONB NOT NULL DEFAULT '{}'` | Path, runner, número de sentencias y señal de baseline |

### `model_governance_backfill_audit`

Bitácora append-only de atribuciones y reversiones. El trigger `trg_model_governance_audit_append_only`, respaldado por `prevent_model_governance_audit_mutation()`, rechaza `UPDATE` y `DELETE`; una reversión siempre es otro evento.

| Campo | Tipo/regla | Propósito |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | Identidad del evento |
| `batch_id` | `UUID NOT NULL` | Agrupa una ejecución de backfill/reversión |
| `event_type` | `TEXT NOT NULL` | `apply` o `revert` |
| `reversal_of_audit_id` | UUID nullable, FK autorreferente `ON DELETE RESTRICT` | Evento aplicado que se revierte |
| `table_name`, `record_id` | `TEXT`, `UUID`, ambos `NOT NULL` | Fila de dominio atribuida |
| `before_values`, `after_values` | `JSONB NOT NULL` | Snapshot antes/después; ambos deben ser objetos JSON |
| `resolution_rule` | `TEXT NOT NULL` | Regla exacta utilizada |
| `candidate_ids` | `UUID[] NOT NULL` | Candidatos considerados, incluso en ambigüedad |
| `result_status` | `TEXT NOT NULL` | `applied`, `reverted`, `exact`, `ambiguous`, `missing`, `checksum_mismatch` o `skipped` |
| `event_at`, `actor` | timestamp y actor, ambos `NOT NULL` | Momento y responsable |
| `metadata` | `JSONB NOT NULL` | Evidencia adicional; debe ser objeto JSON |

Los checks `chk_model_governance_audit_event_type`, `chk_model_governance_audit_result_status`, `chk_model_governance_audit_before_object`, `chk_model_governance_audit_after_object`, `chk_model_governance_audit_metadata_object` y `chk_model_governance_audit_reversal` validan el tipo de evento, resultado, snapshots y semántica de reversión. La FK autorreferente se denomina `fk_model_governance_audit_reversal` y usa `ON DELETE RESTRICT`.

Índices:

- `idx_model_governance_audit_batch (batch_id, event_at)`.
- `idx_model_governance_audit_record (table_name, record_id, event_at)`.
- `idx_model_governance_audit_reversal (reversal_of_audit_id)` parcial para valores no nulos.

### `model_versions`

Tabla histórica extendida por `024_model_version_artifact_governance.sql`. Conserva `id`, `model_id`, `version_name`, `checkpoint_path`, `final_model_path`, `best_model_path`, `training_run_id`, `created_at` y `metadata`.

| Campo gobernado | Tipo/default | Regla |
|---|---|---|
| `model_name` | `TEXT` nullable para legado | Participa en la identidad lógica nueva |
| `version_number` | `INTEGER` nullable para legado | Positivo cuando está informado |
| `checkpoint_artifact_id` | `UUID` nullable durante transición | Artifact canónico; debe pertenecer al mismo training run |
| `artifact_uri` | `TEXT` | URI/storage key portable; el path histórico no se borra |
| `artifact_sha256` | `TEXT` | 64 caracteres hexadecimales lowercase |
| `artifact_size_bytes` | `BIGINT` | Cero o positivo |
| `artifact_hash_reuse_justification` | `TEXT` | Justificación explícita para reutilizar un hash existente |
| `framework`, `framework_version` | `TEXT` | Framework y versión efectiva |
| `preprocessing_profile_snapshot` | `JSONB NOT NULL DEFAULT '{}'` | Snapshot inmutable de preprocessing |
| `class_mapping` | `JSONB NOT NULL DEFAULT '{}'` | Mapeo de clases efectivo |
| `input_signature`, `output_signature` | `JSONB NOT NULL DEFAULT '{}'` | Contratos de entrada/salida |
| `status` | `TEXT NOT NULL DEFAULT 'discovered'` | Estado funcional |
| `lineage_status` | `TEXT NOT NULL DEFAULT 'unresolved'` | Resolución de procedencia, separada del estado funcional |
| `validated_at`, `approved_at`, `retired_at` | `TIMESTAMPTZ` | Hitos del lifecycle |

Estados funcionales admitidos por `chk_model_versions_status`: `discovered`, `candidate`, `validated`, `approved`, `deployed`, `rejected`, `retired`.

Estados de procedencia admitidos por `chk_model_versions_lineage_status`: `unresolved`, `resolved`, `ambiguous`, `artifact_missing`, `checksum_mismatch`, `legacy_unresolved`.

Reglas principales:

- `chk_model_versions_resolved_training`: una fila `lineage_status = 'resolved'` debe tener `training_run_id`.
- `chk_model_versions_governed_hash`: desde `candidate` —incluidos `validated`, `approved`, `deployed`, `rejected` y `retired`— exige `checkpoint_artifact_id` y `artifact_sha256`.
- `chk_model_versions_sha256`, `chk_model_versions_artifact_size` y `chk_model_versions_version_number` validan hash, tamaño y número.
- `chk_model_versions_profile_objects` exige objetos JSON en los cuatro snapshots/signatures.
- `chk_model_versions_artifact_requires_training` impide informar artifact sin training run.
- `uq_model_versions_name_number` impone unicidad parcial de `(model_name, version_number)`.
- `uq_model_versions_training_version_name` conserva la idempotencia legacy por training/name.
- `uq_model_versions_checkpoint_artifact` impide atribuir el mismo artifact a versiones diferentes.
- `uq_model_versions_unjustified_sha256` impide hashes duplicados cuando no existe `artifact_hash_reuse_justification`.

Índices de identidad/consulta: `uq_model_versions_id_training_run`, `uq_model_versions_id_checkpoint_artifact`, `idx_model_versions_training_run`, `idx_model_versions_model`, `idx_model_versions_checkpoint_artifact`, `idx_model_versions_sha256` e `idx_model_versions_status_lineage`.

La FK compuesta `fk_model_versions_checkpoint_artifact_owner` enlaza `(checkpoint_artifact_id, training_run_id)` con `artifacts(id, run_id)` usando `ON DELETE RESTRICT`.

### Extensiones de `artifacts`

`artifacts` conserva `path`, `checksum` y `file_size_bytes`. Se agregan:

| Campo | Tipo/default | Propósito |
|---|---|---|
| `artifact_uri` | `TEXT` | Identificador portable adicional al path absoluto legacy |
| `artifact_status` | `TEXT NOT NULL DEFAULT 'available'` | `unknown` para legado no verificado; `available`, `missing`, `mutated` o `archived` para estados gobernados |
| `archived_at` | `TIMESTAMPTZ` | Momento de archivado |

`chk_artifacts_governance_status` controla el estado. `uq_artifacts_id_run_id` habilita ownership compuesto; `idx_artifacts_checksum`, `idx_artifacts_governance_status` e `idx_artifacts_uri` soportan reconciliación y búsqueda.

### Extensiones de linaje, checkpoint y threshold

`run_lineage` ya poseía `model_version_id` y `checkpoint_artifact_id`; 024 agrega índices y FKs compuestas que demuestran simultáneamente versión, artifact y training propietario:

- `fk_run_lineage_model_version_owner`.
- `fk_run_lineage_checkpoint_artifact_owner`.
- `fk_run_lineage_version_artifact`.
- `idx_run_lineage_model_version` e `idx_run_lineage_checkpoint_artifact`.

`run_checkpoint_policy` agrega `model_version_id` y `checkpoint_artifact_id`, protegidos por:

- `fk_run_checkpoint_policy_model_version_owner`.
- `fk_run_checkpoint_policy_artifact_owner`.
- `fk_run_checkpoint_policy_version_artifact`.
- `idx_run_checkpoint_policy_model_version` e `idx_run_checkpoint_policy_artifact`.

`run_threshold_calibration` agrega:

| Campo | Tipo/default | Propósito |
|---|---|---|
| `model_version_id` | `UUID` | Versión calibrada |
| `calibration_artifact_id` | `UUID` | Artifact de calibración perteneciente al run |
| `score_name` | `TEXT DEFAULT 'probability_parasitized'` | Score clínico fijo |
| `label_mapping_version` | `TEXT DEFAULT 'clinical_v1_parasitized_positive'` | Versión del mapeo |
| `positive_label` | `TEXT DEFAULT 'parasitized'` | Clase positiva fija |
| `calibration_status` | `TEXT DEFAULT 'recorded'` | `recorded`, `validated`, `rejected` o `retired` |

`chk_run_threshold_calibration_score_name`, `chk_run_threshold_calibration_positive_label` y `chk_run_threshold_calibration_status` cierran el contrato clínico. Las FKs `fk_run_threshold_calibration_model_version` y `fk_run_threshold_calibration_artifact_owner` usan `ON DELETE RESTRICT`; los índices son `uq_run_threshold_calibration_id_version`, `idx_run_threshold_calibration_model_version` e `idx_run_threshold_calibration_artifact`.

Las nuevas FKs y checks de 024 se crean `NOT VALID`: protegen escrituras posteriores sin inventar valores para filas legacy y quedan sujetas a backfill/validación en 027.

### `deployed_model_versions`

Cada fila es una revisión auditable e inmutable de autorización. La migración no inserta filas ni usa `active` como default; el estado inicial predeterminado es `pending`.

| Campo | Tipo/default | Propósito/regla |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | Identidad del deployment revision |
| `model_version_id` | `UUID NOT NULL` | Versión autorizada |
| `checkpoint_artifact_id` | `UUID NOT NULL` | Bytes exactos de esa versión |
| `threshold_calibration_id` | `UUID` nullable | Calibración elegida, si existe registro normalizado |
| `deployment_name`, `environment`, `alias` | `TEXT NOT NULL` | Slot lógico; ninguno puede quedar vacío |
| `artifact_sha256` | `TEXT NOT NULL` | Hash congelado, 64 caracteres lowercase |
| `artifact_size_bytes` | `BIGINT` nullable | Tamaño congelado, no negativo |
| `threshold_value` | `NUMERIC NOT NULL` | Umbral congelado en `[0,1]` |
| `threshold_profile_snapshot` | `JSONB NOT NULL` | Configuración completa del threshold |
| `preprocessing_profile_snapshot` | `JSONB NOT NULL` | Preprocessing efectivo |
| `image_quality_policy_snapshot` | `JSONB NOT NULL` | Política de calidad efectiva |
| `label_mapping_snapshot` | `JSONB NOT NULL` | Mapeo de clases congelado |
| `positive_label` | `TEXT DEFAULT 'parasitized'` | Clase positiva fija |
| `score_name` | `TEXT DEFAULT 'probability_parasitized'` | Score clínico fijo |
| `status` | `TEXT DEFAULT 'pending'` | `pending`, `active`, `inactive`, `retired` o `failed` |
| `supersedes_deployment_id` | UUID nullable, FK autorreferente | Revisión sustituida |
| `rollback_of_deployment_id` | UUID nullable, FK autorreferente | Revisión histórica cuyo payload origina un rollback |
| `deployed_at`, `retired_at` | `TIMESTAMPTZ` | Intervalo de vigencia |
| `deployed_by`, `retired_by` | `TEXT` | Actores |
| `deployment_reason`, `retirement_reason` | `TEXT` | Justificación operacional |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT NOW()` | Creación de la revisión |
| `metadata` | `JSONB NOT NULL DEFAULT '{}'` | Evidencia adicional, objeto JSON |

Integridad:

- `fk_deployed_model_versions_version_artifact` impide combinar una versión con el artifact de otra.
- `fk_deployed_model_versions_threshold_version` impide combinar una calibración con otra versión.
- `fk_deployed_model_versions_supersedes` y `fk_deployed_model_versions_rollback` conservan historia con `ON DELETE RESTRICT`.
- `chk_deployed_model_versions_status`, `chk_deployed_model_versions_names`, `chk_deployed_model_versions_sha256`, `chk_deployed_model_versions_artifact_size`, `chk_deployed_model_versions_threshold`, `chk_deployed_model_versions_clinical_convention` y `chk_deployed_model_versions_snapshots` validan el payload.
- `chk_deployed_model_versions_active_timestamps` exige `deployed_at`, `deployed_by` no vacío y ausencia de `retired_at` para `active`.
- `chk_deployed_model_versions_active_mapping` exige que un deployment activo contenga `{"0":"uninfected","1":"parasitized"}` en su snapshot.
- `chk_deployed_model_versions_retired_timestamp` exige `retired_at` para `retired`.
- `chk_deployed_model_versions_timestamp_order` impide un retiro anterior al deployment.
- `chk_deployed_model_versions_distinct_history` impide que una fila se sustituya o revierta a sí misma.
- `uq_deployed_model_versions_active_slot` garantiza como máximo una fila `active` por `(deployment_name, environment, alias)`.

Índices: `uq_deployed_model_versions_id_version`, `idx_deployed_model_versions_model_version`, `idx_deployed_model_versions_checkpoint_artifact`, `idx_deployed_model_versions_threshold_calibration`, `idx_deployed_model_versions_slot_history` e `idx_deployed_model_versions_status`.

Los aliases admitidos por la API Python son `candidate`, `challenger`, `champion` y `experimental`; el DDL conserva compatibilidad aceptando cualquier alias no vacío.

### `run_model_deployments`

Puente entre un inference run y uno o más deployments. La repetición explícita de `model_version_id` permite una FK compuesta que prueba que la versión coincide con el deployment.

| Campo | Tipo/default | Propósito/regla |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | Identidad del vínculo |
| `run_id` | `UUID NOT NULL` | Run físico en `runs` |
| `deployed_model_version_id` | `UUID NOT NULL` | Deployment utilizado |
| `model_version_id` | `UUID NOT NULL` | Versión corroborada por FK compuesta |
| `role` | `TEXT NOT NULL DEFAULT 'primary'` | `primary`, `classifier`, `detector`, `ensemble_member` o `explainer` |
| `ordinal` | `INTEGER NOT NULL DEFAULT 0` | Orden no negativo dentro del rol |
| `weight` | `NUMERIC` nullable | Peso opcional en `[0,1]` |
| `metadata` | `JSONB NOT NULL DEFAULT '{}'` | Snapshot adicional, objeto JSON |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT NOW()` | Registro del uso |

`fk_run_model_deployments_run` y `fk_run_model_deployments_deployment_version` usan `ON DELETE RESTRICT`. Los checks `chk_run_model_deployments_role`, `chk_run_model_deployments_ordinal`, `chk_run_model_deployments_weight` y `chk_run_model_deployments_metadata` validan rol, orden, peso y payload JSON. `uq_run_model_deployments_binding` evita repetir rol/ordinal, `uq_run_model_deployments_run_deployment_version` evita vínculos redundantes y `uq_run_model_deployments_primary` limita a un deployment `primary` por run. Los índices de búsqueda son `idx_run_model_deployments_deployment` e `idx_run_model_deployments_model_version`.

### `runs` e `inference_runs`

`runs` sigue siendo la única tabla de ejecuciones. `026_inference_jobs.sql` agrega cuatro columnas reutilizables:

| Campo en `runs` | Tipo | Uso en inferencia |
|---|---|---|
| `backend_version` | `TEXT` | Versión del servicio/backend que ejecutó el modelo |
| `pipeline_version` | `TEXT` | Versión del pipeline de preprocessing/inferencia |
| `configuration` | `JSONB` | Configuración efectiva; `chk_runs_configuration_object` exige objeto cuando no es nula |
| `error_message` | `TEXT` | Error terminal resumido |

La vista `inference_runs` selecciona únicamente `runs.run_type = 'inference'` y expone:

- `id`/`run_id`.
- `deployed_model_version_id` y `model_version_id` tomados del vínculo `primary` o, si no existe, del primer vínculo ordenado.
- `backend_version`, `pipeline_version`, `started_at`, `finished_at AS completed_at`, `status`, `metadata` y `error_message`.
- `configuration`, con fallback no destructivo `runs.configuration → execution_parameters → parameters → {}`.
- `deployment_bindings`, arreglo JSON con todos los deployments, roles, ordinales y pesos; este campo conserva ensembles sin duplicar el run.

La vista es de lectura. Para crear inferencia se inserta un `runs` con tipo `inference` y se registra al menos un vínculo en `run_model_deployments` dentro de la misma operación lógica.

### `image_analysis_jobs`

Representa una imagen/caso procesado dentro de un inference run y comprueba por FK compuesta el deployment y model version efectivos.

| Campo | Tipo/default | Propósito/regla |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | Identidad del job |
| `inference_run_id` | `UUID NOT NULL` | Run de inferencia |
| `deployed_model_version_id` | `UUID NOT NULL` | Deployment utilizado |
| `model_version_id` | `UUID NOT NULL` | Versión corroborada contra el vínculo del run |
| `input_artifact_id` | `UUID` nullable | Artifact de entrada |
| `source_image_id` | `UUID` nullable | Imagen registrada en `dataset_split_images` |
| `idempotency_key` | `TEXT` nullable | Clave no vacía, única dentro del inference run |
| `sample_id`, `patient_id`, `slide_id` | `TEXT` nullable | Referencias de dominio; deben tratarse según privacidad |
| `status` | `TEXT DEFAULT 'pending'` | `pending`, `running`, `completed`, `failed`, `rejected` o `cancelled` |
| `quality_status` | `TEXT DEFAULT 'not_assessed'` | `not_assessed`, `pending`, `passed`, `warning`, `rejected`, `failed` o `skipped` |
| `quality_metrics` | `JSONB NOT NULL DEFAULT '{}'` | Métricas de calidad, objeto JSON |
| `threshold_used`, `threshold_source` | `NUMERIC`, `TEXT` | Umbral opcional en `[0,1]` y procedencia |
| `summary` | `JSONB NOT NULL DEFAULT '{}'` | Resumen, objeto JSON |
| `total_cells`, `positive_cells` | `INTEGER` nullable | Conteos no negativos; positivos no pueden exceder total |
| `started_at`, `completed_at` | `TIMESTAMPTZ` | Intervalo; completion no puede anteceder inicio |
| `error_message` | `TEXT` | Error terminal |
| `created_at`, `updated_at` | `TIMESTAMPTZ NOT NULL DEFAULT NOW()` | Auditoría temporal |
| `metadata` | `JSONB NOT NULL DEFAULT '{}'` | Evidencia adicional, objeto JSON |

`chk_image_analysis_jobs_source` exige `input_artifact_id` o `source_image_id`. `chk_image_analysis_jobs_idempotency_key`, `chk_image_analysis_jobs_quality_status`, `chk_image_analysis_jobs_threshold`, `chk_image_analysis_jobs_counts` y `chk_image_analysis_jobs_payload_objects` validan la clave, taxonomía de calidad, umbral, conteos y objetos JSON. Las FKs `fk_image_analysis_jobs_run_deployment_version`, `fk_image_analysis_jobs_input_artifact` y `fk_image_analysis_jobs_source_image` usan `ON DELETE RESTRICT`.

`chk_image_analysis_jobs_status_timestamps` exige `started_at` para `running`/`completed` y `completed_at` para cualquier estado terminal (`completed`, `failed`, `rejected`, `cancelled`); `chk_image_analysis_jobs_timestamp_order` conserva el orden temporal.

Índices:

- `uq_image_analysis_jobs_identity` sustenta la procedencia compuesta de predicciones.
- `uq_image_analysis_jobs_idempotency` es parcial para claves no nulas.
- `idx_image_analysis_jobs_run`, `idx_image_analysis_jobs_deployment`, `idx_image_analysis_jobs_model_version`, `idx_image_analysis_jobs_input_artifact`, `idx_image_analysis_jobs_source_image` e `idx_image_analysis_jobs_status_created` soportan joins y colas de trabajo.

### `predictions` y `cell_predictions`

`predictions` continúa siendo la tabla canónica. Las columnas históricas (`run_id`, `dataset_id`, `image_id`, `image_path`, labels/scores/threshold legacy, `case_type`, `created_at`, `metadata`) no se eliminan.

Campos gobernados agregados:

| Campo | Tipo/default | Propósito/regla |
|---|---|---|
| `image_analysis_job_id` | `UUID` | Job propietario |
| `model_version_id` | `UUID` | Versión principal; en alcance cell coincide con classifier |
| `deployed_model_version_id` | `UUID` | Deployment efectivo |
| `inference_run_id` | `UUID` | Run efectivo; en alcance cell coincide con `run_id` |
| `classifier_model_version_id` | `UUID` | Clasificador obligatorio para cell |
| `detector_model_version_id` | `UUID` nullable | Detector opcional |
| `prediction_scope` | `TEXT NOT NULL DEFAULT 'legacy_image'` | `legacy_image`, `image` o `cell` |
| `cell_index` | `INTEGER` | Índice no negativo y único dentro del job |
| `source_image_id` | `UUID` nullable | Imagen registrada |
| `bbox_x`, `bbox_y` | `NUMERIC` | Coordenadas no negativas |
| `bbox_width`, `bbox_height` | `NUMERIC` | Dimensiones positivas |
| `crop_artifact_id` | `UUID` nullable | Crop registrado |
| `explanation_artifact_id` | `UUID` nullable | Explicación registrada |
| `probability_parasitized`, `probability_uninfected` | `NUMERIC` | Ambas en `[0,1]` |
| `threshold_used` | `NUMERIC` | Threshold en `[0,1]` |
| `predicted_class` | `SMALLINT` | `0` o `1` |
| `confidence_level` | `TEXT` nullable | `low`, `medium`, `high`, `uncertain` o `not_assessed` |
| `quality_status` | `TEXT` nullable | Misma taxonomía de calidad del job |
| `review_status` | `TEXT NOT NULL DEFAULT 'unreviewed'` | `unreviewed`, `pending`, `confirmed`, `corrected` o `rejected` |
| `reviewed_label`, `reviewed_by`, `reviewed_at` | texto/actor/timestamp | Resultado de revisión humana |

Checks relevantes:

- `chk_predictions_probability_parasitized` y `chk_predictions_probability_uninfected`.
- `chk_predictions_predicted_class` y `chk_predictions_class_label`.
- `chk_predictions_threshold_used`, `chk_predictions_scope` y `chk_predictions_bbox`.
- `chk_predictions_quality_status`, `chk_predictions_confidence_level`, `chk_predictions_review_status` y `chk_predictions_reviewed_label`.
- `chk_predictions_cell_requirements`: una fila `cell` exige job, run, deployment, versión/clasificador coincidentes, `cell_index`, bbox completa, probabilidades, threshold, clase y label.

`uq_predictions_job_cell_index` garantiza unicidad de `(image_analysis_job_id, cell_index)` solo para filas celulares. Los índices de consulta son `idx_predictions_analysis_job`, `idx_predictions_model_version`, `idx_predictions_deployed_model_version`, `idx_predictions_inference_run`, `idx_predictions_classifier_model_version`, `idx_predictions_detector_model_version` e `idx_predictions_review_status`.

Las FKs simples `fk_predictions_analysis_job`, `fk_predictions_model_version`, `fk_predictions_deployed_model_version`, `fk_predictions_inference_run`, `fk_predictions_classifier_model_version`, `fk_predictions_detector_model_version`, `fk_predictions_source_image`, `fk_predictions_crop_artifact` y `fk_predictions_explanation_artifact` usan `ON DELETE RESTRICT`. `fk_predictions_job_provenance` agrega defensa compuesta: job, run, deployment y versión deben ser el mismo cuarteto registrado en `image_analysis_jobs`.

La vista `cell_predictions` filtra `prediction_scope = 'cell'` y expone `id AS cell_prediction_id` junto con todos los IDs, bbox, probabilities, threshold, resultado, calidad, explicación, revisión, timestamps y metadata. Es de lectura; no debe convertirse en una segunda tabla.

### Backfill e integridad final de 027

`027_model_governance_backfill_constraints.sql` aplica un backfill conservador y luego cierra las reglas cruzadas. No selecciona la versión más reciente, no compara por basename y no reemplaza checksums históricos.

Reglas exactas:

- Para `model_versions`, `same_training_run_exact_checkpoint_path_valid_sha256_unique`: mismo `training_run_id`, `checkpoint_path` exacto, artifact con SHA-256 válido y un único candidato. Completa artifact/hash/tamaño y datos de catálogo faltantes, marca `lineage_status = 'resolved'` y registra before/after.
- Para `run_lineage`, `parent_training_run_exact_checkpoint_path_version_artifact_sha256_unique`: mismo parent training, path exacto, model version resuelta, mismo artifact y mismo SHA-256, también con candidato único.
- El batch usa un UUID y escribe eventos `apply` en `model_governance_backfill_audit`. Las filas ambiguas o incompatibles no se fuerzan ni se sustituyen por un candidato heurístico.

Después del backfill, 027 ejecuta `VALIDATE CONSTRAINT` para los checks/FKs de 024 y 026. Una aplicación exitosa deja esas constraints validadas; si una fila histórica las incumple, la migración transaccional falla y debe investigarse antes de reintentar.

#### Triggers de defensa

| Trigger / función | Defensa |
|---|---|
| `trg_model_versions_governance` / `enforce_model_version_governance()` | `training_run_id` debe ser training; desde `candidate` el payload de identidad/version/artifact/perfiles es inmutable |
| `trg_run_lineage_governance` / `enforce_run_lineage_governance()` | Exige tipos parent/child correctos y version/artifact para evaluación/explicabilidad gobernadas |
| `trg_deployed_model_versions_10_immutable` / `protect_deployed_model_version_payload()` | Impide modificar el payload congelado; promoción/rollback crean otra fila |
| `trg_deployed_model_versions_20_validate` / `validate_deployed_model_version()` | Verifica par version/artifact, hash, tamaño y threshold; `active` exige versión `approved`/`deployed` y artifact `available` |
| `trg_run_model_deployments_validate` / `validate_run_model_deployment()` | El run debe ser `inference` y un vínculo nuevo solo admite deployment `active` |
| `trg_image_analysis_jobs_validate` / `validate_image_analysis_job()` | Valida run, deployment/version y que jobs `running`/`completed` usen exactamente el threshold congelado |
| `trg_artifacts_protect_governed_identity` / `protect_governed_artifact_identity()` | Impide cambiar owner, path, checksum o tamaño de un artifact ligado a una model version |

#### Políticas `ON DELETE`

Toda FK introducida en 023–026 usa `ON DELETE RESTRICT`. Además, 027 reemplaza las políticas históricas peligrosas siguientes:

| FK | Política anterior | Política final |
|---|---|---|
| `model_versions_training_run_id_fkey` | `SET NULL` | `RESTRICT` |
| `model_versions_model_id_fkey` | `CASCADE` | `RESTRICT` |
| `run_lineage_parent_run_id_fkey` | `CASCADE` | `RESTRICT` |
| `run_lineage_child_run_id_fkey` | `CASCADE` | `RESTRICT` |

Así, borrar un training run no desvincula la versión ni elimina silenciosamente el linaje. Los FKs históricos de otras tablas no se reescriben globalmente: un run/artifact que ya participa en la cadena gobernada queda protegido por las relaciones `RESTRICT` específicas. Los procedimientos de purge/reset/clean todavía deben realizar preflight referencial y no deben usarse como mecanismo de rollback.

## Convención clínica obligatoria

La convención única es:

| Clase | Label | Score clínico |
|---:|---|---|
| `0` | `uninfected` | `1 - probability_parasitized` cuando el clasificador binario es complementario |
| `1` | `parasitized` | `probability_parasitized` |

Además:

- `positive_label = 'parasitized'`.
- `score_name = 'probability_parasitized'`.
- `probability_parasitized`, `probability_uninfected` y `threshold_used` pertenecen al intervalo cerrado `[0, 1]`.
- `predicted_class` solo admite `0` o `1`.
- `predicted_class = 0` exige `predicted_label = 'uninfected'`.
- `predicted_class = 1` exige `predicted_label = 'parasitized'`.
- Un deployment congela threshold, mapeo de clases, positive label, score y perfiles efectivos; cambiar cualquiera de ellos requiere otra revisión auditable.

## Estados

| Ámbito | Valores |
|---|---|
| `model_versions.status` | `discovered`, `candidate`, `validated`, `approved`, `deployed`, `rejected`, `retired` |
| `model_versions.lineage_status` | `unresolved`, `resolved`, `ambiguous`, `artifact_missing`, `checksum_mismatch`, `legacy_unresolved` |
| `artifacts.artifact_status` | `unknown`, `available`, `missing`, `mutated`, `archived` |
| `run_threshold_calibration.calibration_status` | `recorded`, `validated`, `rejected`, `retired` |
| `deployed_model_versions.status` | `pending`, `active`, `inactive`, `retired`, `failed` |
| Inference run creado por la API | `started`, `completed`, `failed`, `cancelled` |
| `image_analysis_jobs.status` | `pending`, `running`, `completed`, `failed`, `rejected`, `cancelled` |
| Calidad de job/cell | `not_assessed`, `pending`, `passed`, `warning`, `rejected`, `failed`, `skipped` |
| `predictions.prediction_scope` | `legacy_image`, `image`, `cell` |
| `predictions.confidence_level` | `low`, `medium`, `high`, `uncertain`, `not_assessed` |
| `predictions.review_status` | `unreviewed`, `pending`, `confirmed`, `corrected`, `rejected` |

El recorrido funcional esperado de una versión es `discovered → candidate → validated → approved → deployed → retired`; `rejected` es una salida terminal de evaluación. El lineage se resuelve de forma independiente y puede quedar `unresolved`, `ambiguous`, `artifact_missing` o `checksum_mismatch` sin falsificar procedencia.

Un deployment normalmente recorre `pending → active → inactive/retired`; un fallo de activación usa `failed`. Promoción y rollback crean una fila nueva. Las constraints controlan estados y coherencia temporal, pero la autorización de cada transición también corresponde a la capa de servicio/transacción.

## Migraciones

Las migraciones se encuentran en `malaria_dl_local_project/db/init` y se ejecutan en orden lexicográfico:

| Archivo | Responsabilidad |
|---|---|
| `023_schema_migrations_baseline.sql` | Baseline administrativo, ledger y auditoría durable de backfill |
| `024_model_version_artifact_governance.sql` | Identidad de `model_versions`, artifacts y relaciones históricas |
| `025_deployed_model_versions.sql` | `deployed_model_versions` y `run_model_deployments` |
| `026_inference_jobs.sql` | Inferencia, `image_analysis_jobs`, extensión de `predictions` y vistas gobernadas |
| `027_model_governance_backfill_constraints.sql` | Integridad cruzada, políticas de borrado, backfill/constraints finales y compatibilidad |

`001_schema.sql` permanece como baseline histórico y no se reescribe para simular que el esquema nuevo siempre existió.

### Ledger y checksum

`scripts/init_db.py` crea o utiliza `schema_migrations` antes de recorrer los archivos `NNN_*.sql`:

- `migration_id`: nombre del archivo SQL, clave primaria.
- `checksum`: SHA-256 hexadecimal del archivo.
- `applied_at`: timestamp de registro.
- `execution_metadata`: path, runner y cantidad de sentencias ejecutadas.

Una migración sin registro se ejecuta dentro de la transacción del runner y luego se registra. Una migración registrada con el mismo checksum se omite. Si el mismo `migration_id` aparece con bytes distintos, el runner falla: una migración aplicada es inmutable y cualquier cambio posterior debe usar un número nuevo.

Para instalaciones anteriores al ledger, `baseline_legacy_migrations()` solo registra 001–022 sin reejecutarlas cuando el ledger está vacío y `legacy_schema_is_complete()` comprueba las tablas, vistas y columnas representativas del baseline. Cada registro queda marcado con `execution_metadata.baseline = true`. En una base nueva o no reconocida como completa, los archivos se ejecutan normalmente en orden.

El ledger demuestra lo ejecutado o reconocido explícitamente por este runner desde su adopción. En una instalación anterior no reemplaza el inventario de tablas, columnas, constraints y datos necesario para confirmar que el baseline detectado corresponde al estado real. Una instalación parcial debe revisarse antes de migrar.

### Preparación y backup

Antes de migrar una instalación existente:

```bash
pg_dump --format=custom --file=malaria_experiments_pre_governance.dump malaria_experiments
pg_restore --list malaria_experiments_pre_governance.dump >/dev/null
```

También se debe generar un manifiesto de artifacts con tamaño y SHA-256, registrar el commit desplegado, comprobar espacio disponible y pausar temporalmente escritores de training, evaluación, explicación e inferencia.

### Inicialización o migración

Desde la raíz del repositorio:

```bash
cd malaria_dl_local_project
DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE' \
  .venv/bin/python scripts/init_db.py
```

El mismo comando sirve para una instalación nueva y para una existente: el runner aplica únicamente migraciones no registradas. No se debe ejecutar contra producción sin backup, revisión de checksums y ventana operacional.

### Verificación posterior

```bash
psql 'postgresql://USER:PASSWORD@HOST:5432/DATABASE' -v ON_ERROR_STOP=1
```

Dentro de `psql`:

```sql
SELECT migration_id, checksum, applied_at, execution_metadata
FROM schema_migrations
ORDER BY migration_id;

SELECT to_regclass('public.model_versions'),
       to_regclass('public.deployed_model_versions'),
       to_regclass('public.run_model_deployments'),
       to_regclass('public.image_analysis_jobs'),
       to_regclass('public.inference_runs'),
       to_regclass('public.cell_predictions');

SELECT conrelid::regclass AS object_name,
       conname,
       contype,
       convalidated
FROM pg_constraint
WHERE conrelid IN (
    'model_versions'::regclass,
    'deployed_model_versions'::regclass,
    'run_model_deployments'::regclass,
    'image_analysis_jobs'::regclass,
    'predictions'::regclass
)
ORDER BY object_name::text, conname;

SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE tablename IN (
    'model_versions',
    'deployed_model_versions',
    'run_model_deployments',
    'image_analysis_jobs',
    'predictions'
)
ORDER BY tablename, indexname;
```

La verificación funcional debe incluir inserts válidos, rechazo de probabilidades/clases/labels inválidos, rechazo de un segundo deployment activo para la misma clave, recorrido completo del linaje y prueba de que borrar un training run no destruye su evidencia.

### Pruebas versionadas

Las pruebas de entidades, contrato de migraciones y repositorio se ejecutan con:

```bash
PYTHONDONTWRITEBYTECODE=1 \
malaria_dl_local_project/.venv/bin/python -B -m unittest \
  malaria_dl_local_project.tests.test_model_governance_entities \
  malaria_dl_local_project.tests.test_model_governance_migration \
  malaria_dl_local_project.tests.test_model_governance_repository
```

La verificación local de esta implementación reportó 25 pruebas aprobadas. Estas suites validan entidades, parser/checksums, control de reejecución, contrato SQL, transacción externa, recuperación del linaje y atomicidad del repositorio mediante dobles de conexión; no equivalen a aplicar 023–027 sobre PostgreSQL real.

La integración real está versionada como una prueba opt-in que se niega a usar
`malaria_experiments` y exige un nombre de base que contenga `test` o `codex`:

```bash
cd malaria_dl_local_project
MODEL_GOVERNANCE_TEST_DATABASE_URL='postgresql://USER:PASSWORD@HOST:5432/malaria_governance_test' \
MODEL_GOVERNANCE_TEST_ALLOW_SCHEMA_CHANGES=1 \
  .venv/bin/python -m unittest tests.test_model_governance_postgres
```

Esa prueba aplica el historial numerado, verifica una segunda pasada no-op del
ledger, recorre el linaje completo, prueba los checks clínicos, la unicidad del
deployment activo y el bloqueo al borrar el training run. No se ejecutó durante
esta implementación porque no estuvo disponible una base PostgreSQL 17
desechable autorizada; sin las dos variables la prueba queda omitida.

## Estrategia de rollback

El rollback principal es **forward-compatible**:

1. Detener escritores nuevos.
2. Desactivar en la aplicación las rutas gobernadas de deployment/job si se habilitaron.
3. Volver al binario anterior; las columnas y tablas aditivas permanecen y el código previo las ignora.
4. Conservar aliases y contratos GET históricos durante la ventana de compatibilidad.
5. Corregir cualquier defecto con una migración nueva; no editar el archivo ya registrado ni falsificar su checksum.

No se entrega un downgrade destructivo automático. Eliminar tablas, columnas o filas nuevas puede destruir linaje clínico/experimental y no forma parte del procedimiento normal.

### Reversión de datos o backfill

- Cada backfill debe conservar `before`/`after`, regla de resolución, candidatos, batch y actor en evidencia durable.
- Una atribución defectuosa se revierte solo para las filas del batch comprobado y mediante un nuevo evento de reversión.
- No se borran runs, model versions, artifacts, deployments, jobs, predicciones, métricas ni relaciones históricas.
- Una relación ambigua vuelve a `unresolved`; no se reemplaza por la versión “más reciente”.

### Rollback clínico de deployment

Rollback no significa reactivar ni mutar una fila histórica. Se crea una revisión nueva de `deployed_model_versions` con el snapshot clínico de una revisión previa compatible, se registra el vínculo de rollback/sustitución y se retira la revisión activa dentro de la misma transacción. No se copian archivos sobre `best_model.keras` ni se modifica la model version histórica.

### Restauración de desastre

Restaurar el `pg_dump` completo es el último recurso cuando una migración no puede corregirse de forma aditiva. Debe ensayarse en otra base, acompañarse del manifiesto de artifacts y realizarse con una ventana explícita de pérdida de datos. Nunca se restaura un archivo sobre una ruta histórica sin verificar primero su SHA-256.

## Compatibilidad histórica

- No se eliminan ni renombran columnas existentes.
- `models`, `runs`, `model_versions`, `artifacts`, `run_lineage`, `predictions`, `run_checkpoint_policy`, `run_threshold_calibration`, `run_clinical_metrics`, `run_image_predictions` y `explainability_results` se preservan.
- Los endpoints y vistas legacy pueden continuar leyendo paths y metadata durante la transición.
- `run_image_predictions` permanece como proyección clínica histórica; `predictions` es la fuente canónica para nueva persistencia celular.
- Las filas legacy pueden conservar IDs gobernados nulos hasta que exista una resolución exacta.
- No se crea ningún deployment activo ni se habilita inferencia automáticamente.
- No se reorganiza el frontend como parte de estas migraciones.

## Riesgos pendientes

1. El DDL versionado no demuestra que PostgreSQL vivo lo haya recibido; se requiere aplicar y verificar por ambiente.
2. 027 intenta validar todos los checks/FKs transicionales; cualquier fallo de `VALIDATE CONSTRAINT` bloquea el despliegue y exige resolver la anomalía, no omitir la validación.
3. Los artifacts faltantes o mutados requieren reconciliación contra checksum; no deben “corregirse” reescribiendo evidencia histórica.
4. Las rutas absolutas legacy siguen siendo poco portables y deben retirarse gradualmente de contratos nuevos.
5. La promoción concurrente debe probarse sobre PostgreSQL real para confirmar la unicidad del deployment activo.
6. Debe verificarse que los scripts de purge/reset/clean bloqueen evidencia ligada a versiones o deployments gobernados.
7. La adopción de IDs por evaluation, explainability e inference writers debe medirse; el fallback por path solo puede resolver coincidencias exactas.
8. TTA, ensembles, SVM y explicaciones durante inferencia deben incorporarse explícitamente al mismo contrato antes de considerarlos gobernados.
9. La suite de repositorio cubre transacción externa, atomicidad, jobs y predicciones mediante dobles; sigue pendiente ejecutar constraints, backfill, reejecución y concurrencia sobre una base PostgreSQL 17 desechable.
