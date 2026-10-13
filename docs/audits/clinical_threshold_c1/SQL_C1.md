# C1 — Esquema, procedencia y SQL de auditoría sin conexión

Estado documental: `HISTORICAL_AUDIT`. 2026-10-04.

**Metodología: auditoría estática, sin ejecución de código, pruebas ni consultas PostgreSQL.**

**Consultas ejecutadas en C1: ninguna.** Los resultados históricos citados pertenecen a B1; las consultas propuestas no tienen resultados obtenidos en C1. No se conectó a PostgreSQL, no se inició Docker y no se ejecutó el generador B1.

## Esquema verificado en archivos

Fuente: `alembic_v2/baseline/03_tables.sql`, líneas indicadas; relaciones complementadas por `05_keys.sql` y proyecciones `malaria_dl_local_project/src/malaria_dl/persistence/v2_projection.py:29–198`. Es un contrato estático; su presencia actual en la instancia es **NO VERIFICADO** por C1.

| Tabla / línea | Identidad y contenido pertinente | Relación de auditoría |
| --- | --- | --- |
| experimental_campaigns / 92 | id, requested, protocol, contract, dataset_snapshot, environment | runs.campaign_id; configuraciones y miembros |
| campaign_configurations / 22 | campaign_id, configuration_hash, configuration, requests, canonical_configuration | JOIN compuesto campaign_id + hash del miembro |
| runs / 152 | id, campaign_id, execution_parameters, configuration, parámetros/estado | RUN del entrenamiento |
| run_configurations / 136 | run_id, calibration_enabled, default_threshold, clinical_target_recall, extension_configuration, provenance_snapshot, canonical_configuration, configuration_hash | run_id=runs.id |
| train_execution_sessions / 184 | run_id, configuration, completion, verification, dataset, environment | Configuración realmente entregada y cierre |
| train_execution_records / 180 | run_id, kind, phase, record_key, payload, event_id, event_sequence | Registros legacy y eventos canónicos; no duplicar sus conteos |
| evaluations / 84 | id, training_run_id, run_id, split, evaluation_role, checkpoint_artifact_id, threshold_used, threshold_source, calibration_id y hashes | Métricas por evaluation_id; checkpoint exacto |
| run_clinical_metrics / 134 | evaluation_id, conteos, métricas, prediction_collapse, metadata | v2_binary_metric_guard deriva cocientes y threshold |
| run_threshold_calibration / 150 | run_threshold_calibration_id, run_id, default_evaluation_id, selected_evaluation_id, umbral y target; columnas resumen opcionales | Pareja de evaluaciones VAL del mismo checkpoint/población |
| artifacts / 2 | id, run_id, artifact_type, checksum, file_size_bytes, metadata | evaluations.checkpoint_artifact_id=id; metadata.epoch identifica época |

**Corrección al SQL inicial del encargo:** `rc.configuration` no existe en `run_configurations` v2. El JSON efectivo es `rc.extension_configuration` (resolved sin wrapper); el snapshot íntegro es `rc.provenance_snapshot`. En cambio, `campaign_configurations.configuration` y `train_execution_sessions.configuration` sí existen. No se sustituyen automáticamente hashes de configuración de RUN por los de miembro: B1 acredita que difieren por la semilla.

## Diccionario de procedencia

En esta tabla `M/` abrevia `malaria_dl_local_project/src/malaria_dl/`. Las operaciones son **PERSISTIDO** según código; no equivalen a valores obtenidos de una consulta C1.

| Campo lógico | Solicitud/resolución | Ejecución y persistencia comprobables |
| --- | --- | --- |
| threshold_requested | Legacy: número o 'clinical' | `src/model_metadata.py:202–243` y `M/training/trainer.py:1430–1494`; no columna v2 dedicada ni clave emitida por TRAIN moderno con ese nombre. No inferirla de threshold_used. |
| threshold_selected | Resultado del calibrador | `payload.result.threshold_selected` del registro calibration; evento completo; `run_threshold_calibration.threshold_selected`. |
| threshold_used | ThresholdResult final | `evaluations.threshold_used`; trigger copia a métricas. En calibrador igual a selected. |
| threshold_source | validation_calibration o default en TRAIN moderno | `evaluations.threshold_source`, copia a métricas; default de fila de calibración validation_calibration. `fixed_cli` pertenece al resolver legacy. |
| threshold_mode | Legacy fixed/clinical | Metadata/inferencia legacy; no columna dedicada de TRAIN v2. No se acredita como campo persistido de B1. |
| target_recall | resolved.execution.target_recall | `run_configurations.clinical_target_recall`, JSON efectivo; `run_threshold_calibration.target_recall`; evento. |
| target_recall_satisfied | Booleano calculador | Evento/registro: result.target_recall_satisfied. Columna homónima existe, pero project_calibration no la rellena. No asumir false cuando sea null. |
| target_recall_satisfied_on_validation | Alias calculador | Evento/registro completo; metadata legacy. No columna homónima v2. |
| expected_specificity | selected_metrics.specificity en resolver legacy | Metadata/threshold_info; en v2 consultar métricas de selected_evaluation_id, sin atribuir capacidad predictiva externa. |
| min_specificity | Protocolo specificity_minimum → execution.min_specificity | JSON efectivo y resultado del evento; columna de calibración existe pero proyección moderna no la rellena. |
| min_specificity_satisfied | Resultado calculador | Evento/registro; no columna dedicada. No es equivalente a target_recall_satisfied. |
| calibrate_threshold | execution.calibrate_threshold | Snapshot RUN/sesión y `run_configurations.calibration_enabled`. |
| warning / candidate_count | Resultado calibrador | Registro/evento íntegro; columnas threshold_warning/candidate_count omitidas por project_calibration. |
| prediction_collapse | Callback/calculador | Logs de época y selected_metrics del evento; proyección final v2 omite dict, que tiene default `{}`. Ausencia no significa no colapso. |

`M/persistence/v2_projection.py:183–198` inserta sólo identidades de pareja, default_threshold, threshold_selected, target_recall, split, fecha y métricas por evaluación. `alembic_v2/baseline/04_functions.sql:1129–1150` deriva recall/especificidad/F2 y matriz, usando `NULLIF` para denominadores cero. El guard de pareja (1153–1165) verifica target contra configuración y compatibilidad de evaluaciones, pero no rellena las columnas resumen omitidas. `08_views.sql:38` lee directamente esas columnas; `backend_api/app/routes/runs.py:743–757` consume la vista.

La evaluación separada E6 usa nombres propios: `decision.requested`, `decision.effective`, `decision.source`, `decision.comparison`, no claves threshold_requested/threshold_mode. `M/assessment/contracts.py:28–64,118–127` construye esa identidad; `assessment/repository.py:22–35,123–151` define INSERT en assessment_identities y assessment_results. El modo clinical recupera el registro VAL del checkpoint exacto (`assessment/lineage.py:55–64`); no recalibra TEST. Esta ruta está implementada/conectada, sin consulta ni ejecución histórica TEST acreditada por C1.

## Consultas históricas recuperadas

Fuente completa: [SQL_B1.md](../../../results/benchmarks/cpu_historical/SQL_B1.md). Snapshot B1: **2026-10-04T12:56:54.183938+00:00**. Clasificación: **EJECUCIÓN HISTÓRICA ACREDITADA por documentación B1**, no nueva verificación.

| Consulta B1 | Qué acredita el archivo histórico | Resultado consignado |
| --- | --- | --- |
| Q04, líneas 85–113 | Miembro → intento → RUN y ambos snapshots | 12 configuraciones conciliadas |
| Q05, líneas 115–132 | RUN/sesión/completion | 12 RUNS, con estado y cierre |
| Q06/Q07, líneas 134–161 | Épocas y fases | 396 épocas; 20 fases |
| Q08, líneas 163–182 | Final VAL con checkpoint y métricas | 12 evaluaciones, 2693 muestras cada una |
| Q12, líneas 235–248 | Runtime compilado y callbacks | 20 fases; ES monitor normalizado |
| Q13, líneas 250–271; tabla 367–390 | Cobertura de registros | 12 calibration:val, 396 predictions, 396 selection; calibration no implica enabled |
| Q14, líneas 273–301 | Relaciones/identidades | Sin vínculos inválidos reportados; configuraciones/sesiones completas |
| Q17, líneas 332–350 | Scores de la época seleccionada | 12 conjuntos VAL de 2693; labels idénticas entre RUNS |

Q17 se recuperó literalmente del documento B1; **no ejecutada en C1**:

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

La consulta recupera muestras: en una fase futura autorizada deben permanecer en un entorno controlado; este documento no publica identificadores de células/pacientes. Q17 demuestra disponibilidad en el snapshot B1, no disponibilidad actual. `report.md` explica que los scores individuales no se publicaron en los cuatro CSV; sólo un snapshot opcional de extracción los conserva. No se buscó ni procesó ese snapshot.

## Consultas propuestas para C2 — no ejecutadas

Todos los campos siguientes se confirmaron en esquema/código. Las rutas JSON se confirman por el productor; valores actuales y cardinalidades son **NO VERIFICADO**. Estas consultas no autorizan acceso: son material reproducible para C2 bajo aprobación independiente.

### C2-Q1: configuración y evaluación clínica final

Corrige `rc.configuration`, conserva ausencias y no mezcla los roles de calibración con final VAL. Mostraría solicitud, snapshot efectivo, threshold aplicado y métricas publicadas.

```sql
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT r.id AS run_id, r.run_name,
       r.execution_parameters #> '{model_configuration_e2,configuration,requested}' AS requested,
       rc.extension_configuration AS resolved,
       rc.calibration_enabled, rc.default_threshold, rc.clinical_target_recall,
       e.id AS evaluation_id, e.split, e.evaluation_role,
       e.threshold_used, e.threshold_source,
       m.recall_parasitized, m.specificity, m.f2_parasitized,
       m.prediction_collapse, m.metadata
FROM runs r
LEFT JOIN run_configurations rc ON rc.run_id=r.id
LEFT JOIN evaluations e ON e.training_run_id=r.id
 AND e.split='val' AND e.evaluation_role='training_validation_final'
LEFT JOIN run_clinical_metrics m ON m.evaluation_id=e.id
WHERE r.campaign_id='b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid
ORDER BY r.started_at,r.id;
ROLLBACK;
```

No se predice una fila calibrada en B1: la evidencia disponible dice false/0.5. LEFT JOIN permite detectar evaluaciones/configuraciones ausentes; una duplicación debe investigarse, no ocultarse con LIMIT 1.

### C2-Q2: campaña y configuración entregada a cada sesión

```sql
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT c.id AS campaign_id,c.requested,c.protocol,
       cm.id AS member_id,cm.configuration_hash AS member_configuration_hash,
       cc.configuration AS campaign_configuration,cc.requests,
       r.id AS run_id,rc.configuration_hash AS run_configuration_hash,
       rc.provenance_snapshot,ts.configuration AS session_configuration,
       ts.completion->'selection' AS selected,
       ts.completion->'clinical_objective_met' AS clinical_objective_met
FROM experimental_campaigns c
JOIN campaign_members cm ON cm.campaign_id=c.id
LEFT JOIN campaign_configurations cc ON cc.campaign_id=cm.campaign_id
 AND cc.configuration_hash=cm.configuration_hash
LEFT JOIN campaign_attempts ca ON ca.id=cm.accepted_attempt_id AND ca.member_id=cm.id
LEFT JOIN runs r ON r.id=ca.training_run_id
LEFT JOIN run_configurations rc ON rc.run_id=r.id
LEFT JOIN train_execution_sessions ts ON ts.run_id=r.id
WHERE c.id='b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid
ORDER BY cm.position;
ROLLBACK;
```

Demostraría el protocolo congelado, su transformación en resolved y el indicador de cierre. No debe confundir `completion.selection.val_recall_parasitized` con recall recalibrado.

### C2-Q3: registros de calibración, selección, runtime y predicciones, sin muestras

```sql
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT t.run_id,t.kind,t.phase,t.record_key,t.created_at,
       CASE WHEN t.kind IN ('calibration','predictions')
            THEN t.payload - 'samples'
            WHEN t.kind='runtime'
            THEN jsonb_build_object('callbacks',t.payload->'callbacks')
            ELSE t.payload END AS audit_payload,
       CASE WHEN jsonb_typeof(t.payload->'samples')='array'
            THEN jsonb_array_length(t.payload->'samples') END AS sample_count
FROM train_execution_records t
JOIN runs r ON r.id=t.run_id
WHERE r.campaign_id='b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid
 AND t.kind IN ('calibration','selection','runtime','predictions')
ORDER BY t.run_id,t.created_at,t.kind,t.record_key;
ROLLBACK;
```

Demostraría si calibration contiene `enabled=false` o un resultado real, qué callbacks se declararon y población por época. Se eligen tipos legacy explícitos para no sumar también `e10_event`.

### C2-Q4: calibración relacional frente a las métricas de su pareja

```sql
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT c.run_id,c.run_threshold_calibration_id,
       c.default_evaluation_id,c.selected_evaluation_id,
       c.threshold_selected,c.target_recall,c.target_recall_satisfied,
       c.min_specificity,c.threshold_warning,c.candidate_count,
       s.threshold_used,s.threshold_source,s.population_hash,s.checkpoint_artifact_id,
       m.recall_parasitized,m.specificity,m.f2_parasitized,
       (m.recall_parasitized >= c.target_recall) AS recall_ge_target_derived,
       (m.recall_parasitized > c.target_recall) AS recall_gt_target_derived
FROM run_threshold_calibration c
JOIN runs r ON r.id=c.run_id
LEFT JOIN evaluations s ON s.id=c.selected_evaluation_id
LEFT JOIN run_clinical_metrics m ON m.evaluation_id=s.id
WHERE r.campaign_id='b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid
ORDER BY c.run_id,c.created_at;
ROLLBACK;
```

Demostraría omisiones de columnas resumen frente a conteos/evaluación. Los booleanos `*_derived` son cálculos de auditoría expresamente nombrados, no campos existentes ni resultados obtenidos. Sin filas de calibración no se concluye pérdida: en B1 está desactivada. Para validar C2 habilitado se usaría el ID de la nueva campaña, conservando este filtro histórico como referencia.

### C2-Q5: linaje y cardinalidad de scores del checkpoint elegido

```sql
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT r.id AS run_id,e.id AS evaluation_id,e.dataset_version_id,
       e.population_hash,e.checkpoint_artifact_id,a.checksum,
       a.metadata->>'epoch' AS checkpoint_epoch,t.phase,t.record_key,
       t.payload->>'role' AS prediction_role,
       jsonb_array_length(t.payload->'samples') AS n_scores
FROM runs r
JOIN evaluations e ON e.training_run_id=r.id AND e.split='val'
 AND e.evaluation_role='training_validation_final'
JOIN artifacts a ON a.id=e.checkpoint_artifact_id
JOIN train_execution_records t ON t.run_id=r.id AND t.kind='predictions'
 AND t.payload->>'role'='val'
 AND (t.payload->>'epoch')::integer=(a.metadata->>'epoch')::integer
WHERE r.campaign_id='b54ea684-1b0c-421d-a4b2-9f12667bd619'::uuid
ORDER BY r.id;
ROLLBACK;
```

Demostraría disponibilidad actual y asociación exacta sin divulgar samples. Requeriría después, sólo en C2 autorizado, validar unicidad, etiquetas {0,1}, finitez/rango, ambas clases, población y hashes antes de llamar al algoritmo existente. No basta con contar 2693 entradas: la identidad y correspondencia labels/scores deben ser íntegras.

## Limitaciones y resultado de C1

No hay resultados SQL nuevos, filas nuevas ni modificación de históricos. Los archivos B1 acreditan que los scores fueron suficientes para reconstruir matrices y AUC/AP en ese snapshot. Las métricas agregadas de `runs.csv` o `epochs.csv` por sí solas no permiten reconstruir el orden de scores ni calibrar retrospectivamente. Se requiere recuperar la evidencia por muestra ya existente, sin volver a inferir. El SQL legacy de `run_repository.log_threshold_calibration` no debe reutilizarse directamente para v2: faltan en él las referencias de pareja obligatorias.
