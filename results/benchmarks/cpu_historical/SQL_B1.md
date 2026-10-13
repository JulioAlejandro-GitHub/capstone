# SQL B1 — Consultas verificadas y transformaciones

Estado documental: `HISTORICAL_AUDIT` — evidencia histórica B1; no autoriza entrenamientos ni comparación causal CPU/GPU.

Snapshot principal: `2026-10-04T12:56:54.183938+00:00`. Todas las consultas Q01–Q17 se ejecutaron exitosamente contra el esquema real; no hay DDL, DML, TEST ni EXPLAIN. Los nombres y columnas se verificaron con Q02. Los resultados se obtuvieron en una sola transacción de lectura repetible. Las proyecciones usan el estado existente: no se corrigió PostgreSQL.

## Ejecución y seguridad

Desde la raíz del repositorio, con PostgreSQL ya activo en Docker:

```sh
python3 scripts/benchmarks/b1_historical.py
```

Usa sólo la biblioteca estándar de Python y `docker compose exec -T db … psql`. No inicia servicios ni importa TensorFlow. Abre `BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY`, verifica `transaction_read_only=on` y termina con `ROLLBACK`. Las credenciales se resuelven dentro del contenedor; no se imprimen. El proceso escribe únicamente los entregables locales. Si cambia la evidencia, las aserciones detienen la generación ante cardinalidades o semántica inesperadas. `--snapshot /tmp/b1_snapshot.json` permite guardar temporalmente los resultados de SELECT y `--from-snapshot /tmp/b1_snapshot.json` regenerar desde esa captura (incluye identidades de muestras VAL; no se publica como entregable).


Cada bloque SELECT puede ejecutarse en psql dentro de esta envoltura de sesión (no modifica datos):

```sql
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL TIME ZONE 'UTC';
SET LOCAL statement_timeout='120s';
-- Ejecutar aquí los SELECT del catálogo.
ROLLBACK;
```

El exportador agrega cada resultado con json_agg y lo transporta en un objeto JSON que contiene su identificador literal y sus filas; usa coalesce con un array vacío para fuentes sin registros. Esta envoltura de transporte está implementada en b1_historical.py y no altera los JOIN ni los valores. Q16 verificó read_only=`on` e isolation=`repeatable read`. Las consultas diagnósticas previas se ejecutaron con `PGOPTIONS=-c default_transaction_read_only=on`; se registran al final por separado.

## Catálogo de extracción

### Q01 — Identificar campañas y universo de RUNS

- **Objetivo:** Identificar campañas y universo de RUNS.
- **Tablas:** experimental_campaigns, runs.
- **JOIN:** LEFT JOIN por runs.campaign_id; conserva campañas sin RUNS.
- **Campos recuperados:** `id`, `name`, `state`, `expected_count`, `dataset_version_id`, `created_at`, `run_type`, `status`, `run_count`
- **Resultado:** 1 filas.
- **Validaciones:** Una campaña, expected_count=12 y 12 RUNS training/completed.

```sql
SELECT c.id,c.name,c.state,c.expected_count,c.dataset_version_id,c.created_at,
       r.run_type,r.status,count(r.id) AS run_count
FROM experimental_campaigns c LEFT JOIN runs r ON r.campaign_id=c.id
GROUP BY c.id,r.run_type,r.status ORDER BY c.created_at,r.run_type,r.status;
```

### Q02 — Verificar esquema real

- **Objetivo:** Verificar esquema real.
- **Tablas:** information_schema.columns.
- **JOIN:** Sin JOIN.
- **Campos recuperados:** `table_name`, `column_name`, `data_type`
- **Resultado:** 388 filas.
- **Validaciones:** Columnas consultadas existen; tipos JSONB, numeric y timestamptz conservados.

```sql
SELECT table_name,column_name,data_type FROM information_schema.columns
WHERE table_schema='public' AND table_name IN (
'experimental_campaigns','campaign_members','campaign_attempts','campaign_configurations',
'run_configurations','runs','training_history','run_metrics','run_clinical_metrics',
'artifacts','run_checkpoint_policy','models','evaluations','environment_packages',
'execution_logs','datasets','dataset_versions','experiments','train_execution_records',
 'train_execution_sessions','train_execution_revisions','experiment_execution_events','campaign_execution_events')
ORDER BY table_name,ordinal_position;
```

### Q03 — Campaña, protocolo y dataset

- **Objetivo:** Campaña, protocolo y dataset.
- **Tablas:** experimental_campaigns, dataset_versions, datasets, runs.
- **JOIN:** Versión por dataset_version_id; dataset de origen mediante los RUNS seleccionados.
- **Campos recuperados:** `id`, `experiment_id`, `name`, `purpose`, `state`, `dataset_version_id`, `dataset_snapshot`, `dataset_evidence_id`, `requested`, `protocol`, `environment`, `registry_snapshot`, `contract`, `canonical_contract`, `contract_hash`, `expected_count`, `actor`, `created_at`, `updated_at`, `frozen_at`, `dataset_version`, `source_datasets`
- **Resultado:** 1 filas.
- **Validaciones:** Una versión; distribución y objetivo recuperados del protocolo, sin acceder a TEST.

```sql
SELECT c.*,row_to_json(dv) AS dataset_version,
       (SELECT json_agg(d ORDER BY d.id) FROM datasets d WHERE d.id IN
        (SELECT r.dataset_id FROM runs r WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid)) AS source_datasets
FROM experimental_campaigns c LEFT JOIN dataset_versions dv ON dv.id=c.dataset_version_id
WHERE c.id='b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid;
```

### Q04 — Trazabilidad campaña → miembro → intento → RUN y configuración

- **Objetivo:** Trazabilidad campaña → miembro → intento → RUN y configuración.
- **Tablas:** campaign_members, campaign_attempts, campaign_configurations, runs, run_configurations, models.
- **JOIN:** LEFT JOIN conserva ausencias: intento.member_id=miembro.id; RUN.id=training_run_id; configuración de campaña por clave compuesta (campaign_id,configuration_hash); configuración de RUN por run_id; models por model_id.
- **Campos recuperados:** `member_id`, `campaign_id`, `position`, `seed`, `member_state`, `exclusion_reason`, `accepted_attempt_id`, `member_configuration_hash`, `attempt_id`, `ordinal`, `attempt_state`, `cause`, `attempt_started_at`, `attempt_finished_at`, `run_id`, `run_campaign_id`, `run_type`, `status`, `architecture`, `optimizer`, `run_configuration_hash`, `campaign_architecture`, `campaign_optimizer`, `execution_architecture`, `execution_optimizer`, `run_configuration`, `campaign_configuration`, `configuration_requests`, `model_name`, `model_architecture`
- **Resultado:** 12 filas.
- **Validaciones:** 12 miembros, 12 intentos aceptados, 12 RUNS únicos; igualdad de arquitectura y optimizador en tres fuentes y de hashes miembro/configuración.

```sql
SELECT cm.id AS member_id,cm.campaign_id,cm.position,cm.seed,cm.state AS member_state,
 cm.exclusion_reason,cm.accepted_attempt_id,cm.configuration_hash AS member_configuration_hash,
 ca.id AS attempt_id,ca.ordinal,ca.state AS attempt_state,ca.cause,
 ca.started_at AS attempt_started_at,ca.finished_at AS attempt_finished_at,
 r.id AS run_id,r.campaign_id AS run_campaign_id,r.run_type,r.status,
 rc.architecture,rc.optimizer,rc.configuration_hash AS run_configuration_hash,
 cc.configuration->>'model_id' AS campaign_architecture,
 cc.configuration#>>'{resolved,optimizer,name}' AS campaign_optimizer,
 r.execution_parameters#>>'{model_configuration_e2,configuration,model_id}' AS execution_architecture,
 r.execution_parameters#>>'{model_configuration_e2,configuration,resolved,optimizer,name}' AS execution_optimizer,
 row_to_json(rc) AS run_configuration,cc.configuration AS campaign_configuration,
 cc.requests AS configuration_requests,m.name AS model_name,m.architecture AS model_architecture
FROM campaign_members cm LEFT JOIN campaign_attempts ca ON ca.member_id=cm.id
LEFT JOIN runs r ON r.id=ca.training_run_id
LEFT JOIN run_configurations rc ON rc.run_id=r.id
LEFT JOIN campaign_configurations cc ON cc.campaign_id=cm.campaign_id AND cc.configuration_hash=cm.configuration_hash
LEFT JOIN models m ON m.id=r.model_id
WHERE cm.campaign_id='b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid ORDER BY cm.position,ca.ordinal;
```

### Q05 — Entorno, inicio, término, duración y estado persistido

- **Objetivo:** Entorno, inicio, término, duración y estado persistido.
- **Tablas:** runs, train_execution_sessions.
- **JOIN:** LEFT JOIN sesión por run_id; mantiene RUNS sin sesión.
- **Campos recuperados:** `id`, `experiment_id`, `model_id`, `dataset_id`, `run_name`, `run_type`, `status`, `command`, `script_name`, `started_at`, `finished_at`, `duration_seconds`, `user_name`, `host_name`, `working_directory`, `git_commit`, `git_branch`, `python_version`, `tensorflow_version`, `keras_version`, `platform`, `machine`, `processor`, `gpu_available`, `gpu_devices`, `random_seed`, `parameters`, `notes`, `created_at`, `updated_at`, `metadata`, `execution_type`, `execution_parameters`, `fine_tuning_start_epoch`, `total_epochs`, `completed_epochs`, `max_epochs`, `stopped_epoch`, `best_epoch`, `checkpoint_monitor`, `checkpoint_mode`, `best_validation_value`, `early_stopping_enabled`, `early_stopping_patience`, `early_stopping_min_delta`, `restore_best_weights`, `backend_version`, `pipeline_version`, `configuration`, `error_message`, `dataset_version_id`, `release_status`, `release_updated_at`, `release_changed_by`, `release_reason`, `campaign_id`, `peak_cpu_memory_bytes`, `peak_gpu_memory_bytes`, `wall_seconds`, `duration_difference_seconds`, `session_attempt_id`, `session_state`, `session_host`, `session_started_at`, `session_updated_at`, `session_environment`, `completion`, `verification`
- **Resultado:** 12 filas.
- **Validaciones:** Duración positiva y coincidencia exacta con finished_at-started_at; separar entorno declarado del runtime.

```sql
SELECT r.*,extract(epoch FROM (r.finished_at-r.started_at)) AS wall_seconds,
 r.duration_seconds-extract(epoch FROM (r.finished_at-r.started_at)) AS duration_difference_seconds,
 s.attempt_id AS session_attempt_id,s.state AS session_state,s.host AS session_host,
 s.started_at AS session_started_at,s.updated_at AS session_updated_at,
 s.environment AS session_environment,s.completion,s.verification
FROM runs r LEFT JOIN train_execution_sessions s ON s.run_id=r.id
WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid ORDER BY r.started_at,r.id;
```

### Q06 — Épocas y métricas originales por fase

- **Objetivo:** Épocas y métricas originales por fase.
- **Tablas:** train_execution_records, runs.
- **JOIN:** JOIN RUN por run_id limita la campaña; sólo kind=epoch evita duplicar los eventos canónicos.
- **Campos recuperados:** `run_id`, `kind`, `phase`, `record_key`, `payload`, `created_at`, `event_id`, `event_sequence`
- **Resultado:** 396 filas.
- **Validaciones:** 396 filas, unicidad run/fase/clave y época global, secuencias contiguas; cotejo con phase y completion.

```sql
SELECT t.* FROM train_execution_records t JOIN runs r ON r.id=t.run_id
WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid AND t.kind='epoch'
ORDER BY t.run_id,(t.payload->>'epoch')::integer;
```

### Q07 — Cierre por fase y EarlyStopping

- **Objetivo:** Cierre por fase y EarlyStopping.
- **Tablas:** train_execution_records, runs.
- **JOIN:** JOIN por run_id; kind=phase contiene los cierres.
- **Campos recuperados:** `run_id`, `kind`, `phase`, `record_key`, `payload`, `created_at`, `event_id`, `event_sequence`
- **Resultado:** 20 filas.
- **Validaciones:** 20 fases; comparar epochs con Q06 y stopped_epoch con índice local base cero.

```sql
SELECT t.* FROM train_execution_records t JOIN runs r ON r.id=t.run_id
WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid AND t.kind='phase' ORDER BY t.run_id,t.phase;
```

### Q08 — Métricas finales de VALIDATION y checkpoint evaluado

- **Objetivo:** Métricas finales de VALIDATION y checkpoint evaluado.
- **Tablas:** run_clinical_metrics, evaluations, runs, artifacts.
- **JOIN:** JOIN evaluación por evaluation_id, RUN por training_run_id; LEFT JOIN artefacto por checkpoint_artifact_id. No se une sólo por run_id, que podría multiplicar evaluaciones.
- **Campos recuperados:** `run_clinical_metric_id`, `run_id`, `model_id`, `model_name`, `split_name`, `threshold_used`, `threshold_source`, `accuracy`, `precision_parasitized`, `recall_parasitized`, `sensitivity_parasitized`, `specificity`, `f1_parasitized`, `f2_parasitized`, `roc_auc_parasitized`, `pr_auc_parasitized`, `balanced_accuracy`, `tn`, `fp`, `fn`, `tp`, `confusion_matrix`, `classification_report`, `prediction_distribution`, `prediction_collapse`, `label_mapping_version`, `raw_model_score_meaning`, `created_at`, `metadata`, `evaluation_id`, `sample_count`, `auc_unavailability_reason`, `training_run_id`, `evaluation_run_id`, `evaluation_split`, `evaluation_role`, `checkpoint_artifact_id`, `evaluation_dataset_version_id`, `source_event_id`, `metric_definition`, `protocol_hash`, `population_hash`, `comparison_contract_hash`, `evaluation_threshold`, `checkpoint_name`, `checkpoint_path`, `checkpoint_sha256`, `checkpoint_metadata`
- **Resultado:** 12 filas.
- **Validaciones:** 12 evaluaciones training_validation_final/val, misma versión y RUN, matrices de 2693; recalcular recall/specificity/F1/F2 y contrastar AUC con checkpoint.

```sql
SELECT m.*,e.training_run_id,e.run_id AS evaluation_run_id,e.split AS evaluation_split,
 e.evaluation_role,e.checkpoint_artifact_id,e.dataset_version_id AS evaluation_dataset_version_id,
 e.source_event_id,e.metric_definition,e.protocol_hash,e.population_hash,e.comparison_contract_hash,
 e.threshold_used AS evaluation_threshold,a.name AS checkpoint_name,a.path AS checkpoint_path,
 a.checksum AS checkpoint_sha256,a.metadata AS checkpoint_metadata
FROM run_clinical_metrics m JOIN evaluations e ON e.id=m.evaluation_id
JOIN runs r ON r.id=e.training_run_id LEFT JOIN artifacts a ON a.id=e.checkpoint_artifact_id
WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid AND e.split='val' AND e.evaluation_role='training_validation_final'
ORDER BY m.run_id,m.evaluation_id;
```

### Q09 — Catálogo de artefactos seleccionados

- **Objetivo:** Catálogo de artefactos seleccionados.
- **Tablas:** artifacts, runs.
- **JOIN:** JOIN por run_id.
- **Campos recuperados:** `id`, `run_id`, `artifact_type`, `name`, `path`, `mime_type`, `file_size_bytes`, `checksum`, `created_at`, `metadata`, `artifact_uri`, `artifact_status`, `archived_at`
- **Resultado:** 12 filas.
- **Validaciones:** 12 checkpoints; comprobar IDs, fase, época y checksum contra completion y evaluación. No se afirma existencia física actual.

```sql
SELECT a.* FROM artifacts a JOIN runs r ON r.id=a.run_id WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid ORDER BY a.run_id,a.id;
```

### Q10 — Checkpoint por época y selección histórica

- **Objetivo:** Checkpoint por época y selección histórica.
- **Tablas:** train_execution_records, runs.
- **JOIN:** JOIN por run_id; sólo artifact y selection.
- **Campos recuperados:** `run_id`, `kind`, `phase`, `record_key`, `payload`, `created_at`, `event_id`, `event_sequence`
- **Resultado:** 792 filas.
- **Validaciones:** 396 artefactos y 396 selecciones; cada época tiene evidencia, hash y tamaño.

```sql
SELECT t.* FROM train_execution_records t JOIN runs r ON r.id=t.run_id
WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid AND t.kind IN ('artifact','selection')
ORDER BY t.run_id,t.kind,(t.payload->>'epoch')::integer NULLS LAST,t.phase,t.record_key;
```

### Q11 — Tiempos de eventos canónicos y cobertura de instrumentación

- **Objetivo:** Tiempos de eventos canónicos y cobertura de instrumentación.
- **Tablas:** train_execution_records, runs.
- **JOIN:** JOIN por run_id; LATERAL convierte canonical_event (cadena JSON dentro de JSONB) a objeto.
- **Campos recuperados:** `run_id`, `record_key`, `event_id`, `event_sequence`, `created_at`, `canonical_event_id`, `event_type`, `occurred_at`, `sequence`, `legacy_kind`, `legacy_phase`, `legacy_key`, `payload_context`
- **Resultado:** 2044 filas.
- **Validaciones:** 2044 eventos; identidad y secuencia; marcas occurred_at de emisión, no cronómetros de cómputo.

```sql
SELECT t.run_id,t.record_key,t.event_id,t.event_sequence,t.created_at,
 ev.j->>'event_id' AS canonical_event_id,ev.j->>'event_type' AS event_type,
 ev.j->>'occurred_at' AS occurred_at,ev.j->>'sequence' AS sequence,
 ev.j#>>'{payload,legacy_record,kind}' AS legacy_kind,
 ev.j#>>'{payload,legacy_record,phase}' AS legacy_phase,
 ev.j#>>'{payload,legacy_record,record_key}' AS legacy_key,
 (ev.j->'payload') - 'result' AS payload_context
FROM train_execution_records t JOIN runs r ON r.id=t.run_id
CROSS JOIN LATERAL (SELECT (t.payload->>'canonical_event')::jsonb AS j) ev
WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid AND t.kind='e10_event'
ORDER BY t.run_id,(ev.j->>'sequence')::numeric;
```

### Q12 — Configuración realmente compilada y callbacks por fase

- **Objetivo:** Configuración realmente compilada y callbacks por fase.
- **Tablas:** train_execution_records, runs.
- **JOIN:** JOIN por run_id; excluye model_json y architecture (grafo serializado), conserva configuración operativa.
- **Campos recuperados:** `run_id`, `phase`, `record_key`, `created_at`, `payload`
- **Resultado:** 20 filas.
- **Validaciones:** 20 runtimes; identificar arquitectura por input_contract y optimizador por optimizer_class/config.

```sql
SELECT t.run_id,t.phase,t.record_key,t.created_at,t.payload-'model_json'-'architecture' AS payload
FROM train_execution_records t JOIN runs r ON r.id=t.run_id
WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid AND t.kind='runtime' ORDER BY t.run_id,t.phase;
```

### Q13 — Cobertura de fuentes alternativas y tipos de registros

- **Objetivo:** Cobertura de fuentes alternativas y tipos de registros.
- **Tablas:** runs y tablas de evidencia.
- **JOIN:** Cada subconsulta hace JOIN por run_id; UNION ALL etiqueta fuentes, sin mezclar métricas.
- **Campos recuperados:** `source`, `rows`
- **Resultado:** 21 filas.
- **Validaciones:** Explicitar fuentes vacías; no sustituir ausencias por ceros de entrenamiento.

```sql
SELECT 'training_history' AS source,count(*) AS rows FROM training_history t JOIN runs r ON r.id=t.run_id WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid
UNION ALL
SELECT 'run_metrics' AS source,count(*) AS rows FROM run_metrics t JOIN runs r ON r.id=t.run_id WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid
UNION ALL
SELECT 'run_checkpoint_policy' AS source,count(*) AS rows FROM run_checkpoint_policy t JOIN runs r ON r.id=t.run_id WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid
UNION ALL
SELECT 'execution_logs' AS source,count(*) AS rows FROM execution_logs t JOIN runs r ON r.id=t.run_id WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid
UNION ALL
SELECT 'environment_packages' AS source,count(*) AS rows FROM environment_packages t JOIN runs r ON r.id=t.run_id WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid
UNION ALL
SELECT 'records:'||t.kind||':'||t.phase,count(*) FROM train_execution_records t JOIN runs r ON r.id=t.run_id WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid GROUP BY t.kind,t.phase ORDER BY source;
```

### Q14 — Integridad relacional y cardinalidades

- **Objetivo:** Integridad relacional y cardinalidades.
- **Tablas:** campaign_members, campaign_attempts, runs, run_configurations, campaign_configurations, train_execution_sessions, evaluations, artifacts, run_clinical_metrics.
- **JOIN:** Subconsultas correlacionadas conservan cardinalidad; LEFT JOIN detecta huérfanos.
- **Campos recuperados:** `members`, `runs`, `unique_pairs`, `invalid_accepted_attempts`, `invalid_run_links`, `missing_run_configurations`, `missing_campaign_configurations`, `missing_sessions`, `unlinked_runs`, `invalid_evaluation_links`, `invalid_metric_links`
- **Resultado:** 1 filas.
- **Validaciones:** Contadores de anomalías deben ser cero; 12 pares arquitectura/optimizador.

```sql
SELECT
 (SELECT count(*) FROM campaign_members WHERE campaign_id='b54ea684-1b0c-421d-a4b2-9f12667bd619') AS members,
 (SELECT count(*) FROM runs r WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid) AS runs,
 (SELECT count(DISTINCT (rc.architecture,rc.optimizer)) FROM runs r JOIN run_configurations rc ON rc.run_id=r.id WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid) AS unique_pairs,
 (SELECT count(*) FROM campaign_members cm LEFT JOIN campaign_attempts ca ON ca.id=cm.accepted_attempt_id
  WHERE cm.campaign_id='b54ea684-1b0c-421d-a4b2-9f12667bd619' AND (ca.id IS NULL OR ca.member_id<>cm.id)) AS invalid_accepted_attempts,
 (SELECT count(*) FROM campaign_attempts ca JOIN campaign_members cm ON cm.id=ca.member_id LEFT JOIN runs r ON r.id=ca.training_run_id
  WHERE cm.campaign_id='b54ea684-1b0c-421d-a4b2-9f12667bd619' AND (r.id IS NULL OR r.campaign_id<>cm.campaign_id)) AS invalid_run_links,
 (SELECT count(*) FROM runs r LEFT JOIN run_configurations rc ON rc.run_id=r.id WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid AND rc.run_id IS NULL) AS missing_run_configurations,
 (SELECT count(*) FROM campaign_members cm LEFT JOIN campaign_configurations cc ON cc.campaign_id=cm.campaign_id AND cc.configuration_hash=cm.configuration_hash
  WHERE cm.campaign_id='b54ea684-1b0c-421d-a4b2-9f12667bd619' AND cc.campaign_id IS NULL) AS missing_campaign_configurations,
 (SELECT count(*) FROM runs r LEFT JOIN train_execution_sessions s ON s.run_id=r.id WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid AND s.run_id IS NULL) AS missing_sessions,
 (SELECT count(*) FROM runs r WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid AND NOT EXISTS
   (SELECT 1 FROM campaign_attempts ca JOIN campaign_members cm ON cm.id=ca.member_id WHERE ca.training_run_id=r.id AND cm.campaign_id=r.campaign_id)) AS unlinked_runs,
 (SELECT count(*) FROM evaluations e JOIN runs r ON r.id=e.training_run_id LEFT JOIN artifacts a ON a.id=e.checkpoint_artifact_id
  WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid AND e.split='val' AND (a.id IS NULL OR a.run_id<>r.id OR e.dataset_version_id<>r.dataset_version_id)) AS invalid_evaluation_links,
 (SELECT count(*) FROM run_clinical_metrics m JOIN runs r ON r.id=m.run_id LEFT JOIN evaluations e ON e.id=m.evaluation_id
  WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid AND (e.id IS NULL OR e.training_run_id<>r.id OR e.split<>m.split_name)) AS invalid_metric_links;
```

### Q15 — Inventario de evaluaciones existentes sin ejecutar ninguna

- **Objetivo:** Inventario de evaluaciones existentes sin ejecutar ninguna.
- **Tablas:** evaluations, runs.
- **JOIN:** JOIN por training_run_id.
- **Campos recuperados:** `split`, `evaluation_role`, `rows`
- **Resultado:** 1 filas.
- **Validaciones:** Sólo VALIDATION histórica; esta consulta no ejecuta TEST ni EXPLAIN.

```sql
SELECT e.split,e.evaluation_role,count(*) AS rows FROM evaluations e JOIN runs r ON r.id=e.training_run_id
WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid GROUP BY e.split,e.evaluation_role ORDER BY e.split,e.evaluation_role;
```

### Q16 — Metadatos del snapshot de lectura

- **Objetivo:** Metadatos del snapshot de lectura.
- **Tablas:** PostgreSQL.
- **JOIN:** Sin JOIN.
- **Campos recuperados:** `database`, `server_version`, `read_only`, `isolation`, `snapshot_at`
- **Resultado:** 1 filas.
- **Validaciones:** Transacción REPEATABLE READ READ ONLY; versión de servidor y timestamp explícitos.

```sql
SELECT current_database() AS database,version() AS server_version,
 current_setting('transaction_read_only') AS read_only,
 current_setting('transaction_isolation') AS isolation,transaction_timestamp() AS snapshot_at;
```

### Q17 — Validar métricas usando scores VALIDATION históricos del checkpoint

- **Objetivo:** Validar métricas usando scores VALIDATION históricos del checkpoint.
- **Tablas:** train_execution_records, runs, evaluations, artifacts.
- **JOIN:** JOIN evaluación final y su artefacto; predictions.payload.epoch=artifacts.metadata.epoch. Sólo scores ya persistidos de val.
- **Campos recuperados:** `run_id`, `phase`, `record_key`, `created_at`, `evaluation_id`, `artifact_id`, `epoch`, `role`, `samples`
- **Resultado:** 12 filas.
- **Validaciones:** 12 poblaciones de 2693; reconstruir matriz, ROC-AUC por rangos y AP por umbrales; sin cargar modelos ni ejecutar inferencia.

```sql
SELECT t.run_id,t.phase,t.record_key,t.created_at,e.id AS evaluation_id,
 a.id AS artifact_id,t.payload->>'epoch' AS epoch,t.payload->>'role' AS role,
 t.payload->'samples' AS samples
FROM train_execution_records t JOIN runs r ON r.id=t.run_id
JOIN evaluations e ON e.training_run_id=r.id AND e.split='val' AND e.evaluation_role='training_validation_final'
JOIN artifacts a ON a.id=e.checkpoint_artifact_id
WHERE r.campaign_id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid AND t.kind='predictions' AND t.payload->>'role'='val'
AND (t.payload->>'epoch')::integer=(a.metadata->>'epoch')::integer ORDER BY t.run_id;
```

## Transformaciones Python y fórmulas

Se ejecutan en `scripts/benchmarks/b1_report.py`; no entrenan ni infieren. Las fuentes temporales y métricas originales se conservan en los CSV.

1. **Identificación:** arquitectura/optimizador normalizados se contrastan con campaign_configuration, execution_parameters y runtime. No se extraen de run_name ni se interpreta models.architecture como código de arquitectura. Se conserva el JOIN compuesto campaña/hash. El hash de RUN corresponde al JSON resolved con seed; se valida SHA-256 del texto canónico y equivalencia estructural, sin igualarlo al hash del miembro.
2. **Épocas:** N = número de filas Q06 por run; N_base/N_FT por phase. Se exige `(run_id,phase,record_key)` único y epoch global 1…N; `phase_epoch` 1…N_fase. Se coteja Q07 y completion de Q05. No se utiliza `runs.completed_epochs` como fuente principal. No se suman legacy y e10_event.
3. **Duración:** `wall_seconds = finished_at-started_at` en segundos UTC; Q05 calcula EXTRACT(EPOCH). Python convierte timedelta exactamente con días×86400 + segundos + microsegundos/1e6. `seconds_per_epoch = wall_seconds/N`. `sum_run_seconds=Σ wall_seconds`; `run_span_seconds=max(finished_at)-min(started_at)`. Las pausas son Σ(inicio siguiente−fin anterior), sólo tras comprobar ausencia de solapamientos; sum_run_seconds+pausas=span. Desde creación se usa último fin−campaign.created_at y se etiqueta espera incluida.
4. **Fases:** inicio/fin por occurred_at de `phase_started` y `phase_completed` en Q11, con referencia legacy runtime/phase. `phase_event_seconds_per_epoch=(fin-inicio)/N_fase`; no incluye todo el RUN. EarlyStopping se identifica por stopped_epoch>0, verificando stopped_epoch+1=N_fase; best/stopped son locales 0-based. Cuando stopped_epoch=0 y se alcanza máximo no se declara parada anticipada. No se identifica el checkpoint con ese índice local.
5. **Intervalos por época:** `event_interval_seconds=occurred_at(epoch actual)−occurred_at(epoch anterior de misma fase)`; para primera época se usa phase_started. Incluye guardado y callbacks de la época anterior y trabajo previo al evento actual; no representa duración pura de esa época. `checkpoint_event_interval_seconds=artifact_created−artifact_prepared`. `postselection_prediction_interval_seconds=predictions_completed−selection_completed`. Se unen por run/fase/record_key, se conservan endpoints y se exige diferencia no negativa. Estos intervalos no aíslan todo el overhead y no se restan del RUN para inventar tiempo de cómputo.
6. **Métricas finales:** se mantienen los valores originales Q08. Para validar Q17, clase positiva parasitized=1, predicción positiva score≥0,5. Matriz filas reales [0,1], columnas predichas [0,1]: [[TN,FP],[FN,TP]]. Recall=TP/(TP+FN), specificity=TN/(TN+FP), F1=2TP/(2TP+FP+FN), F2=5TP/(5TP+4FN+FP). Ambos soportes son positivos (1325/1368); no se reemplazan denominadores nulos por cero. ROC-AUC: Σ_por_score(pos_en_grupo×(neg_de_score_inferior+0,5×neg_en_grupo))/(P×N), equivalente a comparación por pares con empate a mitad. AP=Σ_por_score_descendente[(pos_en_grupo/P)×(TP_acumulado/n_acumulado)], agrupando empates; no se integra trapecio de PR. Error absoluto=|recalculado−publicado|, tolerancia 1e-12. Se conserva el detalle en `runs.metric_validation`. No se confunden AUC aproximadas de Keras con AUC clínica final.
7. **Objetivo:** recall>0,98, sin redondear; umbral fijo 0,5. Se compara con completion.clinical_objective_met y no con selection.policy_satisfied. Los resultados corresponden al checkpoint enlazado en evaluations, no a la última época.
8. **Agregados:** horas=segundos/3600; promedio ponderado por arquitectura=Σsegundos/Σépocas; rangos=min/max entre sus cuatro recetas, no IC. Porcentaje de intervalo=100×Σintervalos/Σsegundos_RUN. Bytes=Σtamaños declarados por epoch artifact; seleccionado si su época global coincide con el artefacto evaluado. No se inventa artifact_id donde no existe proyección.
9. **Precisión:** json.loads(parse_float=Decimal), Decimal con precisión 50; numeric fuente conservado sin redondeo de presentación. JSON estructurado se serializa manteniendo números, no cadenas para decimales. Divisiones no terminantes están necesariamente limitadas a 50 cifras y los datos base permiten recalcularlas. Markdown redondea; CSV no usa ese formateo. Vacíos son ausencia, no cero.
10. **Controles:** aserciones de cardinalidad, integridad, población VAL compartida, checksum/configuración, secuencia y reconciliación. Los datos faltantes conocidos generan advertencias y se preservan; inconsistencias nuevas de identidad, duración, métricas o conteos abortan. No se excluyen RUNS por bajo recall, EarlyStopping o costo. `training_history` vacío no implica cero épocas.

## Cobertura de fuentes observada

| Fuente | Filas |
| --- | --- |
| environment_packages | 0 |
| execution_logs | 0 |
| records:artifact:base | 263 |
| records:artifact:fine_tuning | 133 |
| records:artifact_prepared:base | 263 |
| records:artifact_prepared:fine_tuning | 133 |
| records:calibration:val | 12 |
| records:e10_event:run_event_v1 | 2044 |
| records:epoch:base | 263 |
| records:epoch:fine_tuning | 133 |
| records:phase:base | 12 |
| records:phase:fine_tuning | 8 |
| records:predictions:base | 263 |
| records:predictions:fine_tuning | 133 |
| records:runtime:base | 12 |
| records:runtime:fine_tuning | 8 |
| records:selection:base | 263 |
| records:selection:fine_tuning | 133 |
| run_checkpoint_policy | 0 |
| run_metrics | 0 |
| training_history | 0 |

## Consultas diagnósticas previas (trazabilidad de exploración)

Estos SELECT se ejecutaron durante el descubrimiento del esquema y datos. Los conteos de filas se volvieron a comprobar en la transacción final mediante SELECT count(*) FROM (consulta) q; son conteos del resultado, no necesariamente de la tabla. Las muestras LIMIT sin ORDER BY no fijan una identidad reproducible: sólo se usaron para inspeccionar estructura. Los resultados publicados provienen del catálogo Q, con selección explícita.

### D01 — Inventario inicial de tablas y vistas

- **Objetivo:** Inventario inicial de tablas y vistas.
- **Tablas:** information_schema.tables.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** table_name.
- **Resultado:** 138 filas.
- **Validaciones:** Nombres contrastados con Q02.

```sql
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;
```

### D02 — Esquema inicial de entidades científicas

- **Objetivo:** Esquema inicial de entidades científicas.
- **Tablas:** information_schema.columns.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** table_name, column_name, data_type.
- **Resultado:** 351 filas.
- **Validaciones:** Columnas reales; ampliación en Q02.

```sql
SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema='public' AND table_name IN ('experimental_campaigns','campaign_members','campaign_attempts','campaign_configurations','run_configurations','runs','training_history','run_metrics','run_clinical_metrics','artifacts','run_checkpoint_policy','models','evaluations','environment_packages','execution_logs','datasets','dataset_versions','experiments') ORDER BY table_name,ordinal_position;
```

### D03 — Identificar campaña y entorno declarado

- **Objetivo:** Identificar campaña y entorno declarado.
- **Tablas:** experimental_campaigns.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** id,name,state,expected_count,dataset_version_id,created_at,environment.
- **Resultado:** 1 filas.
- **Validaciones:** Una campaña de 12 miembros esperados.

```sql
SELECT id,name,state,expected_count,dataset_version_id,created_at,environment FROM experimental_campaigns ORDER BY created_at;
```

### D04 — Inventario inicial de RUNS

- **Objetivo:** Inventario inicial de RUNS.
- **Tablas:** runs.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** run_type,status,count.
- **Resultado:** 1 filas.
- **Validaciones:** 12 training/completed; sin filtros de rendimiento.

```sql
SELECT run_type,status,count(*) FROM runs GROUP BY run_type,status;
```

### D05 — Inspección inicial de identidades de configuración

- **Objetivo:** Inspección inicial de identidades de configuración.
- **Tablas:** runs,run_configurations,campaign_attempts,campaign_members,campaign_configurations.
- **JOIN:** RUN→configuración por run_id; RUN→intento por training_run_id; intento→miembro por member_id; configuración por campaign_id y configuration_hash. LEFT JOIN preserva ausencias.
- **Campos:** id,run_name,architecture,optimizer,configuration,execution_parameters.
- **Resultado:** 2 filas.
- **Validaciones:** Muestra LIMIT 2, posteriormente validada para 12/12 por Q04/Q12.

```sql
SELECT r.id,r.run_name,rc.architecture,rc.optimizer,cc.configuration,r.execution_parameters FROM runs r LEFT JOIN run_configurations rc ON rc.run_id=r.id LEFT JOIN campaign_attempts ca ON ca.training_run_id=r.id LEFT JOIN campaign_members cm ON cm.id=ca.member_id LEFT JOIN campaign_configurations cc ON cc.campaign_id=cm.campaign_id AND cc.configuration_hash=cm.configuration_hash ORDER BY cm.position LIMIT 2;
```

### D06 — Muestra completa del primer RUN

- **Objetivo:** Muestra completa del primer RUN.
- **Tablas:** runs.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** row_to_json(r), todos los campos de runs.
- **Resultado:** 1 filas.
- **Validaciones:** Detectó campos planos nulos y completed_epochs=0; auditoría completa Q05.

```sql
SELECT row_to_json(r) FROM runs r ORDER BY started_at LIMIT 1;
```

### D07 — Inspección de historia de entrenamiento

- **Objetivo:** Inspección de historia de entrenamiento.
- **Tablas:** training_history.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** row_to_json(h), todos los campos.
- **Resultado:** 0 filas.
- **Validaciones:** Resultado vacío, no se interpreta como cero épocas.

```sql
SELECT row_to_json(h) FROM training_history h ORDER BY created_at LIMIT 2;
```

### D08 — Inspección inicial de métricas clínicas

- **Objetivo:** Inspección inicial de métricas clínicas.
- **Tablas:** run_clinical_metrics.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** row_to_json(m), todos los campos.
- **Resultado:** 1 filas.
- **Validaciones:** Muestra LIMIT 1 sin orden; no se usa para seleccionar ganador. Q08 recupera todas.

```sql
SELECT row_to_json(m) FROM run_clinical_metrics m LIMIT 1;
```

### D09 — Inspección de proyección de políticas

- **Objetivo:** Inspección de proyección de políticas.
- **Tablas:** run_checkpoint_policy.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** row_to_json(p), todos los campos.
- **Resultado:** 0 filas.
- **Validaciones:** Vacía; selección recuperada de sesiones/artefactos.

```sql
SELECT row_to_json(p) FROM run_checkpoint_policy p LIMIT 1;
```

### D10 — Inspección inicial de evaluación

- **Objetivo:** Inspección inicial de evaluación.
- **Tablas:** evaluations.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** row_to_json(e), todos los campos.
- **Resultado:** 1 filas.
- **Validaciones:** Muestra LIMIT 1 sin orden; Q08 restringe rol y split explícitamente.

```sql
SELECT row_to_json(e) FROM evaluations e LIMIT 1;
```

### D11 — Tipos de artefactos catalogados

- **Objetivo:** Tipos de artefactos catalogados.
- **Tablas:** artifacts.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** artifact_type,count.
- **Resultado:** 1 filas.
- **Validaciones:** model_checkpoint: 12.

```sql
SELECT artifact_type,count(*) FROM artifacts GROUP BY artifact_type;
```

### D12 — Localizar tablas de eventos y sesiones

- **Objetivo:** Localizar tablas de eventos y sesiones.
- **Tablas:** information_schema.columns.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** table_name,column_name,data_type.
- **Resultado:** 37 filas.
- **Validaciones:** Confirmó JSONB payload y campos de claves de registros.

```sql
SELECT table_name,column_name,data_type FROM information_schema.columns WHERE table_schema='public' AND table_name IN ('experiment_execution_events','campaign_execution_events','train_execution_records','train_execution_sessions','train_execution_revisions') ORDER BY table_name,ordinal_position;
```

### D13 — Cobertura de run_metrics

- **Objetivo:** Cobertura de run_metrics.
- **Tablas:** run_metrics.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** count.
- **Resultado:** 1 filas.
- **Validaciones:** Valor count=0; la consulta devuelve una fila agregada.

```sql
SELECT count(*) FROM run_metrics;
```

### D14 — Cobertura de logs

- **Objetivo:** Cobertura de logs.
- **Tablas:** execution_logs.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** count.
- **Resultado:** 1 filas.
- **Validaciones:** Valor count=0; la consulta devuelve una fila agregada.

```sql
SELECT count(*) FROM execution_logs;
```

### D15 — Inspección de checkpoint catalogado

- **Objetivo:** Inspección de checkpoint catalogado.
- **Tablas:** artifacts.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** row_to_json(a), todos los campos.
- **Resultado:** 1 filas.
- **Validaciones:** Muestra LIMIT 1 sin orden; Q09 verifica todo el catálogo de campaña.

```sql
SELECT row_to_json(a) FROM artifacts a LIMIT 1;
```

### D16 — Inventario de tipos/fases de evidencia

- **Objetivo:** Inventario de tipos/fases de evidencia.
- **Tablas:** train_execution_records.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** kind,phase,count.
- **Resultado:** 16 filas.
- **Validaciones:** Localizó 263 épocas base y 133 fine_tuning; Q13 verifica cobertura.

```sql
SELECT kind,phase,count(*) FROM train_execution_records GROUP BY kind,phase ORDER BY kind,phase;
```

### D17 — Inspección de payload por tipo/fase

- **Objetivo:** Inspección de payload por tipo/fase.
- **Tablas:** train_execution_records.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** kind,phase,record_key,payload.
- **Resultado:** 16 filas.
- **Validaciones:** DISTINCT ON: sólo muestra inicial por tipo/fase. Incluía payloads voluminosos; se acotaron proyecciones posteriores.

```sql
SELECT DISTINCT ON (kind,phase) kind,phase,record_key,payload FROM train_execution_records ORDER BY kind,phase,created_at;
```

### D18 — Inspección de completion y verificación

- **Objetivo:** Inspección de completion y verificación.
- **Tablas:** train_execution_sessions.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** run_id,state,completion,verification,environment.
- **Resultado:** 1 filas.
- **Validaciones:** Primera sesión por started_at; cotejo completo Q05.

```sql
SELECT run_id,state,completion,verification,environment FROM train_execution_sessions ORDER BY started_at LIMIT 1;
```

### D19 — Inspección acotada de épocas y cierres

- **Objetivo:** Inspección acotada de épocas y cierres.
- **Tablas:** train_execution_records.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** kind,phase,record_key,payload.
- **Resultado:** 4 filas.
- **Validaciones:** Identificó epochs y early_stopping por fase; muestra inicial, ampliada en Q06/Q07.

```sql
SELECT DISTINCT ON (kind,phase) kind,phase,record_key,payload FROM train_execution_records WHERE kind IN ('epoch','phase') ORDER BY kind,phase,created_at;
```

### D20 — Inspección de claves del contenedor de eventos

- **Objetivo:** Inspección de claves del contenedor de eventos.
- **Tablas:** train_execution_records.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** event_type,key.
- **Resultado:** 25 filas.
- **Validaciones:** event_type nulo en este nivel: el evento está en la cadena canonical_event; no se interpreta como tipo desconocido.

```sql
SELECT payload->>'event_type' AS event_type, jsonb_object_keys(payload) AS key FROM train_execution_records WHERE kind='e10_event' LIMIT 25;
```

### D21 — Inspección de runtime compilado

- **Objetivo:** Inspección de runtime compilado.
- **Tablas:** train_execution_records.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** run_id,phase,runtime.
- **Resultado:** 1 filas.
- **Validaciones:** Muestra LIMIT 1 sin orden; Q12 recupera las 20 fases.

```sql
SELECT run_id,phase,payload - 'model_json' - 'model_configuration' - 'architecture' AS runtime FROM train_execution_records WHERE kind='runtime' LIMIT 1;
```

### D22 — Verificar representación de canonical_event

- **Objetivo:** Verificar representación de canonical_event.
- **Tablas:** train_execution_records.
- **JOIN:** Sin JOIN; lectura directa de la fuente indicada.
- **Campos:** payload.
- **Resultado:** 1 filas.
- **Validaciones:** Confirma que canonical_event es texto JSON; Q11 usa ->> y cast a jsonb.

```sql
SELECT payload FROM train_execution_records WHERE kind='e10_event' ORDER BY created_at LIMIT 1;
```

### Incidencia diagnóstica descartada

Una llamada preliminar a `jsonb_object_keys(payload->'canonical_event')` (sobre train_execution_records, kind='e10_event', LIMIT 20, alias key) falló con `cannot call jsonb_object_keys on a scalar`. No produjo datos ni se usó para calcular resultados. D22 comprobó que el campo es una cadena JSON; Q11 utiliza `(payload->>'canonical_event')::jsonb` y fue ejecutada satisfactoriamente para 2.044 eventos. La expresión fallida se conserva sólo como incidente, no como consulta ejecutable del experimento.

La primera lectura local de los resultados JSON del catálogo también falló al asumir una línea por resultado: json_agg puede incluir saltos de línea. Se corrigió el lector con JSONDecoder.raw_decode y se repitió la extracción. No hubo cambios en PostgreSQL y sólo la captura íntegra verificada generó los entregables.
