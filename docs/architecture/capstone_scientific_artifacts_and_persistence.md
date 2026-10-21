# Capstone — Mapa de persistencia y trazabilidad de artefactos científicos

Estado documental: `CURRENT_DOC`. Tipo: **referencia arquitectónica transversal**. Fecha de verificación: **2026-10-21**.
Código: `main` en `fa322be` (incluye la calibración de umbral seleccionable en campañas). Fuente de verdad: PostgreSQL operativo `malaria_experiments`, leído con
`default_transaction_read_only=on`.

Alcance: los cuatro comandos públicos `python -m src.train | src.evaluate | src.explain | src.test`
(`malaria_dl_local_project/`). Consumidores: campañas, «Aprendizaje del Modelo» y Comparación Científica.
Auditoría que lo valida: [SCC-CAMPAIGN.1A](../audits/scc_campaign_1a_preflight.md).

> Regla de lectura: una ruta documentada no garantiza que una ejecución concreta la usó. La ubicación efectiva es siempre
> la registrada en PostgreSQL (`train_execution_sessions.artifact_root`, `assessment_attempts.artifact_root`, rutas en
> payloads). Este documento indica dónde mirar y cómo verificar, no reemplaza esa lectura.

En las referencias, `M/` = `malaria_dl_local_project/src/malaria_dl/`.

## 1. Visión general

```text
Dataset gobernado (dataset_versions, dataset_split_assignments, dataset_materializations)
   │  data/malaria_dataset_versions/<dataset_version_id>/{train,val,test}/{clase}/<archivo>
   ▼
TRAIN  ── runs ── train_execution_sessions ── train_execution_records
   │        outputs/train_runs/<run_id>/epoch_N.keras        (python -m src.train)
   │        outputs/campaign_runs/<run_id>/epoch_N.keras     (worker de campaña, histórico)
   ▼  checkpoint seleccionado = train_execution_sessions.verification.artifact
EVALUATE / TEST / EXPLAIN ── assessment_identities ── assessment_attempts ── assessment_results
                                                                        └── assessment_artifacts (sólo EXPLAIN)
                             artifacts/assessments/<attempt_id>/<artifact_id>.{npy,png}
```

## 2. Raíces físicas y qué las determina

| Raíz | Quién la fija | Ruta relativa al proyecto | Observaciones verificadas |
|---|---|---|---|
| Dataset materializado | `dataset_materializations.relative_root` | `data/malaria_dataset_versions/<dataset_version_id>/` | Las identidades guardan la ruta Docker `/app/malaria_dl_local_project/data/...`; `M/data/governed_dataset.py:local_dataset_root` la traslada al montaje local |
| TRAIN por campaña (`src.train --campaign-id`, coordinador) | `M/execution/campaign.py:406` | `outputs/campaign_runs/<run_id>/` | Absoluta (`PROJECT_ROOT`). Desde SCC-EVIDENCE Fase 0 (sin commit) es la ruta de `--campaign-id` sin TRAIN de referencia; los 15 RUN de worker previos a `d3d42cf3` también viven aquí |
| TRAIN por referencia (`--source-training-run-id`) | `M/execution/operations.py` (`output_dir="outputs/train_runs"`) | `outputs/train_runs/<run_id>/` | `ExecutionRepository.standalone` resuelve con `Path(root).resolve()`: **depende del directorio actual**; ejecutar desde `malaria_dl_local_project/`. Sin E10 ni proyecciones SCC |
| EVALUATE / EXPLAIN / TEST | `M/assessment/cli.py:104` (`"artifacts/assessments"`) | `artifacts/assessments/<attempt_id>/` | `AssessmentRepository.reserve` añade `<attempt_id>` y resuelve contra el directorio actual. Ninguno de los cuatro comandos acepta `--artifact-root` (retirado en CLI-01); sólo lo conservan los ejecutores internos de worker (`execution/campaign.py`, `execution/controlled.py`). EVALUATE y TEST registran la raíz pero **no crean archivos** |

Traslado Mac ↔ Docker: `M/execution/storage_paths.py:local_scientific_path` sólo reescribe rutas bajo
`outputs/train_runs` y `artifacts/assessments` (`ALLOWED_TREES`). Rutas `outputs/campaign_runs` se resuelven sólo si existen
tal cual. El backend Docker monta `malaria_dl_local_project` completo en `/app/malaria_dl_local_project`.

## 3. Mapa por operación

### 3.1 TRAIN

| Evidencia | Tabla / archivo | Identificador | Nota |
|---|---|---|---|
| Identidad, modelo, dataset, campaña, semilla, configuración resuelta | `runs` (`execution_parameters.model_configuration_e2.configuration`) | `runs.id` | `campaign_id` FK a `experimental_campaigns` |
| Sesión, owner, raíz de artefactos, cierre y verificación | `train_execution_sessions` | `run_id` (PK) | `verification.artifact` = checkpoint seleccionado con `path`, `sha256`, `bytes`, `epoch`, `version_id` |
| Configuración normalizada v2 | `run_configurations` | `run_id` | Incluye `calibration_enabled` (trigger `v2_configuration_guard`) |
| Historial por época (métricas TRAIN/VAL, LR, fase) | `train_execution_records` `kind='epoch'` | `(run_id, kind, phase, record_key)` | `training_history` y `run_metrics` son heredadas y están vacías |
| Checkpoint de **cada** época | `train_execution_records` `kind='artifact'` + `epoch_N.keras` | `payload.version_id` | Creación exclusiva (`.partial` → `rename`); nunca se sobrescribe |
| Selección de checkpoint | `kind='selection'` y `completion.selection` | `record_key` = época de fase | Incluye `warning` cuando el monitor explícito difiere de la política |
| Predicciones VAL por época | `kind='predictions'` (`payload.samples[]`: `sample` = ruta relativa, `label`, `score`) | ruta relativa | 2.693 por época; ruta ↔ `sample_id` derivable (Q8, §4) |
| Predicciones VAL del checkpoint elegido y umbral | `kind='calibration'`, `phase='val'`, `record_key='selected'` | — | `result.enabled=false` (auto 0,5) o `threshold_source='validation_calibration'` (clinical) |
| Eventos E10 | `kind='e10_event'` | `event_id` | **Sólo ruta coordinador** (worker o `--campaign-id` tras Fase 0) |
| Checkpoint registrado para SCC | `artifacts` (`artifact_type='model_checkpoint'`) y `runs.execution_parameters.e10_v2_evaluation_context_v1` | `artifacts.id` | **Sólo ruta coordinador**; ausente en RUN por referencia (H-01) |
| Evaluación VAL final y métricas clínicas | `evaluations`, `run_clinical_metrics` | `evaluation_id` | **Sólo ruta coordinador** (H-01) |
| Consumo individual en optimización | ninguna | — | **NO DEMOSTRADO** (TRACE-CLOSE-06/07); `run_dataset_images` = 0 filas y no es contador |

### 3.2 EVALUATE, TEST y EXPLAIN

| Evidencia | Tabla / archivo | Identificador | Nota |
|---|---|---|---|
| Qué se evalúa: TRAIN, checkpoint, dataset, split, propósito, protocolo, umbral, seed, batch, muestras | `assessment_identities.identity` | `identity_id`, `identity_hash` | `kind` ∈ {`evaluate`,`explain`}; TEST = `evaluate` + `split='test'` + `purpose='final'` |
| Intento, estado, owner, raíz, verificación | `assessment_attempts` | `attempt_id` | Cada invocación crea `execution_id` nuevo ⇒ identidad e intento nuevos |
| Resultado por muestra EVALUATE/TEST | `assessment_results.payload` (`label`, `raw_score`, `predicted`, `threshold`, `patient_id`) | `(attempt_id, sample_id)` | `sample_id` = `dataset_split_assignments.source_record_id` |
| Resultado por muestra EXPLAIN | `assessment_results.payload` (`specification`, `result.layer`, `artifacts[]`) | `(attempt_id, sample_id)` | No guarda el score; unir con EVALUATE por `sample_id` |
| Mapa y overlay EXPLAIN | `assessment_artifacts.payload` (`path`, `sha256`, `bytes`, `role`) + `artifacts/assessments/<attempt_id>/<artifact_id>.npy` / `.png` | `artifact_id` | Exactamente 2 por muestra (`map`, `overlay`), exigido por `assessment_attempt_guard` |
| Métricas y confusión | `assessment_attempts.verification.metrics` (`binary_counts_rates_v1`) | `attempt_id` | Reconstruibles desde `assessment_results` |

### 3.3 Requerimientos por pregunta científica

Estados: **PERSISTE** (fuente operativa con datos), **DERIVABLE** (se calcula desde lo persistido; no tiene almacén ni
linaje propio), **NO EXISTE** (sin productor), **NO DEMOSTRADO** (limitación aceptada). «Reporte A» = Aprendizaje del
Modelo (un RUN); «Reporte B» = Comparación Científica (varios RUN).

#### 3.3.1 Fuentes persistidas no listadas en §3.1–3.2

| Dato | Fuente | Contenido verificado | Uso |
|---|---|---|---|
| Entorno y compilación por fase | `train_execution_records` `kind='runtime'`, `record_key='configuration'` | `optimizer` (hiperparámetros efectivos), `optimizer_class`, `optimizer_state`, `loss`, `compile`, `callbacks`, `trainable_layers`, `input_contract`, `output_contract`, `runtime_environment`, `started_at` | Diferencias de aprendizaje entre fases y arquitecturas; capas congeladas en fine-tuning |
| Cierre de fase | `kind='phase'`, `record_key='completed'` | `epochs` ejecutadas, `early_stopping[].stopped_epoch/best_epoch` | Distinguir parada temprana de máximo de épocas |
| Contrato de campaña | `experimental_campaigns` (`contract`, `canonical_contract`, `contract_hash`, `protocol`, `dataset_snapshot`) | Matriz, protocolo congelado y hash | Probar que los RUN comparados comparten protocolo |
| Configuraciones y miembros | `campaign_configurations` (`configuration_hash`, `configuration`); `campaign_members` (`seed`, `position`, `state`) | Configuración por hash y semilla por miembro | Agrupar RUN por arquitectura/optimizador/semilla (miembros no avanzan con la CLI: H-02) |
| Configuración comparable | `run_configurations` | Columnas normalizadas (arquitectura, optimizador, LR, épocas, EarlyStopping, checkpoint, dropout, L2, entrada, pesos, `calibration_enabled`, `clinical_target_recall`) + `extension_configuration`, `provenance_snapshot` | Tabla de diferencias de configuración (dimensión A4) |
| Paciente y clase gobernados | `dataset_split_assignments` (`source_record_id`, `clinical_identity_id`, `split_name`, `class_name`) | 27.558 registros v1 | Análisis por paciente y bootstrap |
| Tablas XAI cuantitativas | `xai_evidence`, `xai_artifacts`, `xai_region_attributions`, `xai_quantitative_evaluations`, `xai_interpretations`, `xai_specialist_reviews`, `xai_method_configurations`, `xai_evaluation_protocols`, `xai_evaluation_members` | **0 filas**; ningún comando las llena | Almacén previsto para evaluación cuantitativa y revisión experta de explicaciones |

#### 3.3.2 Módulos de Comparación Científica y sus fuentes

`backend_api/app/services/scientific_report.py:read` y `scientific_preflight.py` (dimensiones A1–A6, ver
[SCC-REPORT-SCI.1](../engineering/scc_report_sci_1.md)).

| Módulo | Fuente | RUN de worker | RUN de `python -m src.train` |
|---|---|---|---|
| `catalog` | `evaluations` ∪ `assessment_identities`/`attempts` (`comparison_catalog`); gobernanza (`dataset_versions`, `dataset_split_validation_checks`); checkpoint (`comparison_checkpoint`) | Completo | Intentos sí; checkpoint `CHECKPOINT_UNREGISTERED` (H-01) |
| `curves` | `train_execution_records` `epoch` (`comparison_epochs`) + `run_configurations` | Completo | Curvas sí; checkpoint marcado no atribuido (H-01) |
| `metrics` | Histórico: `evaluations` + `run_clinical_metrics`; independiente: `assessment_attempts.verification` | Ambos | Sólo intentos independientes |
| `consensus` / `questions` | Histórico: `train_execution_records` `predictions` (por ruta); independiente: `assessment_results` (por `sample_id`) | Ambos; no mezcla espacios de identidad | Sólo `assessment_results` |
| `representations` | `artifacts` con tipo/método `embedding`, `pca`, `umap`, `cka` (`comparison_representations`) | Vacío | Vacío |
| Preflight A5 (checkpoint) | `artifacts` + `train_execution_sessions.verification` (`checkpoint_binding`) | PASS | Previsiblemente `CHECKPOINT_UNREGISTERED` (H-01) |

#### 3.3.3 Reporte A — ¿Qué aprendió el modelo?

| Pregunta | Evidencia requerida | Fuente | Estado |
|---|---|---|---|
| ¿Cómo evolucionó el aprendizaje? | Métricas TRAIN/VAL, LR y fase por época | `epoch`, `runtime`, `phase` | PERSISTE |
| ¿Cuándo dejó de mejorar y por qué paró? | Épocas ejecutadas, `stopped_epoch`, `best_epoch`, EarlyStopping | `phase`, `selection` | PERSISTE |
| ¿Qué checkpoint se eligió y con qué criterio? | Época, métrica, política, advertencia, SHA-256 | `selection`, `completion.selection`, `verification.artifact` | PERSISTE (conflicto política/monitor: H-04 de SCC-CAMPAIGN.1A) |
| ¿Cómo cambiaron sus predicciones entre épocas? | Score VAL por muestra y época | `predictions` + Q8 | PERSISTE (por ruta; proyección a `sample_id` DERIVABLE) |
| ¿Con qué umbral decide? | Evidencia de calibración VAL | `calibration/val/selected` | PERSISTE |
| ¿Cómo rinde en VAL y TEST? | Resultados por muestra, métricas, confusión | `assessment_results`, `verification.metrics` | PERSISTE |
| ¿Qué tan segura es y está calibrada? | `raw_score` + ECE, Brier, curva de fiabilidad | `assessment_results.raw_score` | DERIVABLE (`evaluation/probability_calibration.py` existe, sin almacén) |
| ¿Dónde se equivoca y en qué pacientes? | Errores por muestra unidos a paciente | `assessment_results.patient_id`, `dataset_split_assignments` | DERIVABLE |
| ¿Qué regiones influyen en la decisión? | Mapas por muestra, método, capa, checkpoint | `assessment_results` + `assessment_artifacts` (VAL) | PERSISTE (verificar integridad física, §5) |
| ¿Por qué falla en TEST? | Explicaciones de errores TEST | — | NO EXISTE (EXPLAIN sólo VAL) |
| ¿Mira al parásito? | Anotación de regiones o revisión experta contrastada con los mapas | `xai_region_attributions`, `xai_specialist_reviews` | NO EXISTE (tablas vacías, sin flujo) |
| ¿Qué representaciones internas construyó? | Activaciones/embeddings por capa y muestra; PCA/UMAP | Checkpoints de todas las épocas + muestras gobernadas | NO EXISTE; DERIVABLE con implementación nueva |
| ¿Qué imágenes procesó al optimizar? | Recibos de consumo | — | NO DEMOSTRADO |

#### 3.3.4 Reporte B — Comparación Científica

| Pregunta | Evidencia requerida | Fuente | Estado |
|---|---|---|---|
| ¿Son comparables los RUN? | Mismo dataset, fingerprints, split, protocolo, umbral, checkpoint verificable | `assessment_identities.identity`, contrato de campaña, `run_configurations` | PERSISTE; checkpoint en UI afectado por H-01 |
| ¿Qué configuración difiere? | Configuración normalizada | `run_configurations` | PERSISTE |
| ¿Cuál generaliza mejor? | TEST por muestra con umbral congelado antes de TEST | `assessment_results` (`test/final`) | PERSISTE |
| ¿Cómo se comparan en VAL? | EVALUATE VAL por muestra | `assessment_results` (`val/development`) | PERSISTE (optimista: VAL selecciona checkpoint y umbral) |
| ¿Qué errores comparten o complementan? | Intersección por `sample_id`, consenso, oracle | `assessment_results`; módulo `consensus` | PERSISTE; cálculo en consulta, sin almacén |
| ¿Cuál es más confiable en su confianza? | ECE, Brier, fiabilidad por RUN | `raw_score` | DERIVABLE, sin almacén |
| ¿Es la diferencia estadísticamente real? | Bootstrap por paciente, IC 95 % | `assessment_results` + paciente | DERIVABLE (especificado en `science/protocol.py`; TEST = 20 pacientes) |
| ¿Varía con la semilla? | ≥3 semillas por configuración | `campaign_members.seed` | Depende del diseño de campaña |
| ¿Miran regiones similares? | Mapas por muestra común; métrica de similitud entre mapas | `assessment_artifacts` | PERSISTE (mapas); métrica cuantitativa NO EXISTE (`xai_quantitative_evaluations` vacía) |
| ¿Construyen representaciones similares? | CKA entre capas/arquitecturas | — | NO EXISTE |
| ¿Corrieron en la misma condición? | Dispositivo CPU/GPU, `tensorflow-metal`, hash de pesos iniciales | — | NO EXISTE (H-15) |

#### 3.3.5 Evidencia derivada sin almacén ni linaje

Se puede calcular hoy fuera del sistema, pero el resultado no queda registrado con identidad, insumos ni hash:
proyección ruta→`sample_id` de predicciones TRAIN-VAL; ECE/Brier/fiabilidad; bootstrap por paciente; consenso/oracle
(el módulo lo calcula en cada consulta); análisis por paciente; métricas de similitud entre mapas; embeddings, PCA,
UMAP y CKA. Hasta definir su contrato, un reporte que los use debe citar las consultas de origen (§4), los
`attempt_id`/`run_id` de entrada y declararlos **derivados no persistidos**.

## 4. Consultas reproducibles (solo lectura)

```sql
-- Q1. Checkpoint seleccionado por TRAIN (válido para ambas rutas; NO usar sólo `artifacts`)
SELECT s.run_id, s.state, s.artifact_root,
       s.verification #>> '{artifact,path}'   AS checkpoint_path,
       s.verification #>> '{artifact,sha256}' AS sha256,
       (s.verification #>> '{artifact,bytes}')::bigint AS bytes,
       (s.verification #>> '{artifact,epoch}')::int    AS selected_epoch
FROM train_execution_sessions s ORDER BY s.started_at;

-- Q2. Checkpoints de todas las épocas de un RUN
SELECT phase, record_key, payload->>'epoch' AS epoch, payload->>'path' AS path,
       payload->>'sha256' AS sha256, payload->>'bytes' AS bytes
FROM train_execution_records WHERE run_id = :run AND kind = 'artifact' ORDER BY (payload->>'epoch')::int;

-- Q3. Historial por época
SELECT phase, record_key, payload FROM train_execution_records
WHERE run_id = :run AND kind = 'epoch' ORDER BY (payload->>'epoch')::int;

-- Q4. Umbral y predicciones VAL del checkpoint elegido
SELECT payload->'result' AS threshold_evidence, payload->'checkpoint_epoch' AS checkpoint_epoch,
       jsonb_array_length(payload->'samples') AS n
FROM train_execution_records WHERE run_id = :run AND kind = 'calibration' AND phase = 'val' AND record_key = 'selected';

-- Q5. Intentos de una campaña (EVALUATE/TEST/EXPLAIN)
SELECT i.training_run_id, i.kind, i.identity->>'split' AS split, i.identity->>'purpose' AS purpose,
       i.identity#>>'{explanation,method}' AS method, i.identity#>>'{decision,effective}' AS threshold,
       i.identity#>>'{decision,source,version}' AS threshold_source,
       jsonb_array_length(i.identity->'samples') AS expected, a.id AS attempt_id, a.state,
       a.verification->>'count' AS verified_count, a.artifact_root
FROM assessment_identities i JOIN assessment_attempts a ON a.identity_id = i.id
JOIN runs r ON r.id = i.training_run_id
WHERE r.campaign_id = :campaign ORDER BY i.training_run_id, a.started_at;

-- Q6. Resultados por muestra de un intento
SELECT sample_id, payload FROM assessment_results WHERE attempt_id = :attempt ORDER BY sample_id;

-- Q7. Artefactos EXPLAIN de un intento
SELECT sample_id, role, artifact_id, payload->>'path' AS path, payload->>'sha256' AS sha256, payload->>'bytes' AS bytes
FROM assessment_artifacts WHERE attempt_id = :attempt ORDER BY sample_id, role;

-- Q8. Correspondencia ruta TRAIN-VAL ↔ sample_id (debe dar n = distintos = coincidencias)
WITH t AS (SELECT s->>'sample' p FROM train_execution_records r, jsonb_array_elements(r.payload->'samples') s
           WHERE r.run_id = :run AND kind = 'calibration'),
     a AS (SELECT s->>'relative_path' p, s->>'sample_id' id FROM assessment_identities i,
           jsonb_array_elements(i.identity->'samples') s
           WHERE i.training_run_id = :run AND i.kind = 'evaluate' AND i.identity->>'split' = 'val')
SELECT (SELECT count(*) FROM t), (SELECT count(DISTINCT p) FROM t), (SELECT count(*) FROM t JOIN a USING (p));
```

La consulta sobre `artifacts` (`artifact_type='model_checkpoint'`) es válida (columnas `run_id`, `name`, `path`,
`file_size_bytes`, `checksum` existen) pero **sólo devuelve RUN del worker**: 15 de 16 hoy; omite `d3d42cf3` y omitirá
todo RUN creado por `python -m src.train` mientras persista H-01. Usar Q1.

## 5. Verificación de integridad física

1. Obtener la ruta registrada (Q1, Q2, Q7). Si empieza por `/app/`, trasladarla a la raíz del repositorio
   (`/app/malaria_dl_local_project/...` → `<repo>/malaria_dl_local_project/...`).
2. Comprobar existencia, que no sea symlink y tamaño = `bytes`.
3. Recalcular SHA-256 y comparar con el valor registrado. En macOS: `shasum -a 256 <ruta>`.
4. Dataset: `dataset_materializations.manifest_metadata.reconciliation` (`sha_match`, `missing_files`, `unexpected_files`)
   y, para revalidar, `verify_dataset_for_execution` (lo hace cada operación al iniciar).

Los propios comandos repiten parte de esto: `lineage.resolve` revalida el checkpoint seleccionado; `service.verify` revalida
checkpoint, filas y cada artefacto EXPLAIN dentro de su `artifact_root`.

**Estado observado (2026-10-21):**

| Conjunto | Total | PASS | Fallo |
|---|---:|---:|---:|
| Checkpoints seleccionados (SHA-256 + bytes) | 16 | 16 | 0 |
| Checkpoints de todas las épocas (existencia + bytes) | 432 | 432 | 0 |
| Artefactos EXPLAIN (SHA-256 + bytes, rutas `/app/` trasladadas) | 18.964 | 13.578 | **5.386 ausentes** |

Los 5.386 ausentes son exactamente los del intento Grad-CAM `ceaa29af-cb60-4be2-8a67-01b9c9382cda` (TRAIN `bbbd5b60`,
2026-10-08), cuya carpeta falta en el host y en Docker; ya registrado en CAPSTONE-REPORTS-01A. Su fila sigue `verified`
en PostgreSQL. Esto demuestra indisponibilidad física, no su causa.

## 6. Conservación y recuperación histórica

| Capa | Protección efectiva | Límite |
|---|---|---|
| `train_execution_records` | `train_record_guard`: sólo INSERT (`TRAIN_RECORD_IMMUTABLE`), owner y sesión activa | — |
| `train_execution_sessions` | `train_session_guard`: sin DELETE, identidad inmutable, transiciones válidas | — |
| `runs` vinculados | `campaign_run_identity_guard`, `controlled_run_guard` | Columnas operativas (estado, release) sí cambian |
| `assessment_identities` | `assessment_immutable`: sin UPDATE/DELETE | — |
| `assessment_attempts` | `assessment_attempt_guard`: sin DELETE; sólo `active` → terminal por el owner | — |
| `assessment_results` / `assessment_artifacts` | `assessment_result_guard`: sólo INSERT, coherencia muestra/paciente/predicción | — |
| Archivos `.keras`, `.npy`, `.png` | Escritura exclusiva (`rename`/`os.link` sin sobrescritura) | **Ningún guard impide borrarlos o moverlos** (caso `ceaa29af`) |

Política operativa derivada:

- No borrar ni mover `outputs/train_runs`, `outputs/campaign_runs`, `artifacts/assessments` ni `data/malaria_dataset_versions`.
  Toda limpieza debe seguir un manifiesto congelado como [STORAGE.CLEAN.1](../maintenance/storage_clean_1_execution.md)
  y excluir rutas referenciadas por PostgreSQL.
- Respaldar esas raíces junto con el backup PostgreSQL; un backup sólo de la BD conserva referencias sin binarios.
- Ejecutar la verificación física de §5 antes de cada reporte científico y después de cada campaña.
- Recuperación: un intento con archivos ausentes no se repara ni se reetiqueta. Se ejecuta una nueva identidad/intento
  con el mismo checkpoint y protocolo; el histórico queda como evidencia de resultados con binarios no disponibles.
- Espacio: Campaña 1 ocupa 15 GB en `outputs/campaign_runs` (se guardan todas las épocas); `artifacts/assessments` 1,2 GB.

## 7. Limitaciones vigentes

- H-01: RUN de `python -m src.train` sin `artifacts`, `evaluations`, `run_clinical_metrics` ni E10.
- El dispositivo de ejecución (CPU / GPU Metal) no se persiste (`runs.gpu_devices=[]`; `tensorflow-metal` no figura en
  el entorno registrado).
- Consumo individual de TRAIN: NO DEMOSTRADO.
- Representaciones internas (embeddings, PCA, UMAP, CKA): sin productor ni tabla.

## 8. Fuentes

`M/execution/operations.py`, `M/execution/train.py`, `M/execution/repository.py`, `M/execution/storage_paths.py`,
`M/assessment/{cli,service,lineage,runtime,repository}.py`, `M/data/governed_dataset.py`,
`backend_api/app/repositories/scientific_results.py`; catálogo y funciones `pg_proc` de PostgreSQL;
[TRACE.1A](../audits/capstone_image_trace_1a.md), [CAPSTONE-REPORTS-01A](../audits/capstone_reports_01a_current_state.md),
[CAPSTONE-CLI-01](../audits/capstone_cli_01_parameter_certification.md),
[Auditoría SQL SCC](../Capstone_SCC_Auditoria_SQL_Evidencia_Cientifica.md).

Complementario para parámetros y umbrales: [Scientific Parameter Registry](../scientific_parameters.md) (generado;
cadena `experimental_campaigns` → `campaign_configurations` → `runs` → `run_configurations` y destino de
`threshold_selected`/`threshold_used`). Su frase «el catálogo público sigue fijando none» es anterior a `fa322be`.
