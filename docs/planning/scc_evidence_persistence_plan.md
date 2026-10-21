# SCC-EVIDENCE — Plan para persistir la evidencia «NO EXISTE» y «NO DEMOSTRADO»

Estado documental: `PROPOSAL`. Fecha: **2026-10-21**. Tipo: plan de implementación; **nada de este documento está
implementado ni autorizado**. Cada fase requiere aprobación explícita antes de empezar.

Origen: [mapa de persistencia §3.3](../architecture/capstone_scientific_artifacts_and_persistence.md#33-requerimientos-por-pregunta-científica)
y [SCC-CAMPAIGN.1A](../audits/scc_campaign_1a_preflight.md). Verificado contra `main` (`fa322be`) y el catálogo efectivo
de PostgreSQL (solo lectura). `M/` = `malaria_dl_local_project/src/malaria_dl/`.

## 1. Principios

1. **No reabrir TRACE.** TRACE-CLOSE-01/02 siguen vigentes: no instrumentar `train_step`/`test_step`, no parchear Keras,
   no recibos por batch. El consumo individual en optimización no se convierte en «demostrado» por este plan.
2. **Reutilizar antes de crear.** El esquema v2 ya tiene un modelo XAI completo (`xai_*`) enganchado a
   `assessment_results`/`assessment_artifacts`, hoy con 0 filas. Se llena antes de diseñar tablas nuevas.
3. **Toda evidencia nueva tiene identidad, insumos, hash e inmutabilidad**, como `assessment_*`. Nada se recalcula sobre
   un intento ya cerrado ni se reetiqueta un histórico.
4. **Separar operación científica de proyección.** Lo que requiere inferencia (representaciones, fidelidad XAI, EXPLAIN
   TEST) es una operación con intento propio. Lo que sólo reorganiza evidencia existente (checkpoint en `artifacts`,
   `xai_evidence`) es una proyección idempotente que nunca ejecuta ciencia.
5. **El esquema vigente es la fuente de verdad.** DDL sólo donde las restricciones actuales lo impiden, vía Alembic, en
   fase propia. Sin preflights de versión de esquema.

## 2. Brechas a cubrir

| ID | Brecha (§3.3) | Estado actual | Bloqueo real |
|---|---|---|---|
| G-01 | Checkpoint de RUN de `python -m src.train` registrado para SCC y XAI | NO EXISTE (H-01) | `train()` sin emitter ⇒ sin `artifacts`/`evaluations`; `v2_xai_lineage_guard` exige el checkpoint en `artifacts` o `model_versions` |
| G-02 | Condición de ejecución: dispositivo CPU/GPU, `tensorflow-metal`, hash de pesos iniciales | NO EXISTE (H-15) | `runtime_environment` no los recoge; `runs.gpu_available/gpu_devices` vacíos |
| G-03 | EXPLAIN sobre TEST (explicar errores de generalización) | NO EXISTE | `src.explain` fija `val/development`; el esquema sí lo admite |
| G-04 | Evidencia XAI estructurada (método, capa, clase, score explicado, artefactos) consultable | NO EXISTE | Nadie escribe `xai_method_configurations`/`xai_evidence`/`xai_artifacts` |
| G-05 | Fidelidad de las explicaciones y similitud entre mapas de arquitecturas | NO EXISTE | Sin cálculo; almacén `xai_evaluation_protocols`/`xai_quantitative_evaluations`/`xai_evaluation_members` vacío |
| G-06 | ¿Mira al parásito? Validación con anotación o revisión experta | NO EXISTE | Sin anotaciones de regiones en NIH; `xai_interpretations`/`xai_specialist_reviews` sin flujo |
| G-07 | Representaciones internas: activaciones/embeddings por capa | NO EXISTE | Sin productor; `assessment_identities.kind` ∈ {evaluate, explain} y el guard exige 2 artefactos/muestra para explain |
| G-08 | PCA / UMAP / CKA | NO EXISTE | Depende de G-07; `umap-learn` no instalado; sin entidad de análisis entre RUN |
| G-09 | Consumo de imágenes en optimización TRAIN | NO DEMOSTRADO | TRACE cerrado; `run_dataset_images` apunta a `dataset_split_images` sin hash ni versión |

## 3. Fases

### Fase 0 — Prerrequisito: proyecciones de TRAIN por CLI (G-01, además H-02/H-07)

**Qué:** que un RUN creado por `python -m src.train` deje las mismas proyecciones que el worker.

Restricciones verificadas que fijan el diseño:

- `ExecutionRepository.bind_evaluation_context` (registra el checkpoint en `artifacts` y el contexto de evaluación) exige
  sesión `active`, owner vigente **y** `attempt_id` de campaña (`CAMPAIGN_PROTOCOL_REQUIRED`); las sesiones standalone
  no tienen `attempt_id`.
- `evaluations` tiene FK `fk_evaluation_e10_record` a un registro E10 de `train_execution_records`: sin eventos E10 no
  puede existir la evaluación VAL histórica ni `run_clinical_metrics`.
- `train_record_guard` y `train_session_guard` impiden escribir registros tras el cierre de la sesión.

Diseño resultante:

- Con `--campaign-id`, TRAIN debe reservar como el worker: crear `campaign_attempts` y vincular la sesión (`attempt_id`),
  actualizar `campaign_members` (H-02), omitir miembros ya `verified` (H-07) y usar `RunEventEmitter` con el journal
  local existente, de modo que `bind_evaluation_context` y la proyección E10 → `evaluations`/`run_clinical_metrics`
  ocurran durante la sesión activa. Reutilizar `ExecutionRepository.claim` en lugar de duplicarlo.
- `--source-training-run-id` sin campaña sigue siendo standalone y sin protocolo de campaña: documentar que no alimenta
  la vista histórica de SCC (sólo intentos independientes) o exigir campaña para ese uso.
- **RUN CLI ya verificados (`d3d42cf3`): no reparables** sin violar los guards; su evidencia primaria queda intacta y
  se usan por sus intentos independientes, o se reentrenan en la campaña nueva.

**Esquema:** sin DDL. **Criterio de aceptación:** para un RUN CLI, `artifacts` (`model_checkpoint`), `evaluations` y
`run_clinical_metrics` existen, el miembro de campaña queda `verified` con su intento aceptado y el preflight SCC deja de
emitir `CHECKPOINT_UNREGISTERED`; relanzar la campaña no duplica miembros verificados.
**Pruebas:** unitarias con repositorio en memoria + integración en PostgreSQL desechable.

### Fase 1 — Sin DDL: condición de ejecución, XAI estructurada y EXPLAIN TEST

**1a. G-02 Condición de ejecución.**
- Añadir a `runtime_environment` una clave **nueva** `accelerator` con `tf.config.list_physical_devices('GPU')`,
  versión de `tensorflow-metal` (si está) y `TF_DETERMINISTIC_OPS`. No mezclarla en `packages`: `packages` forma parte
  de `IDENTITY_KEYS` (`M/execution/campaign.py:25`) y cambiaría la identidad de entorno de campañas congeladas.
- Llenar `runs.gpu_available` y `runs.gpu_devices` (columnas existentes).
- Pesos iniciales: SHA-256 del archivo de pesos Keras/ImageNet efectivamente cargado por el adapter (VGG16/DenseNet121)
  en `runtime` por fase; `"none"` para Custom CNN.
- Lo mismo en `inference_environment()` de assessments (`M/assessment/service.py:356`).

**1b. G-04 Proyección XAI.** Al verificar un intento EXPLAIN, proyectar (idempotente, sin nueva inferencia):
- `xai_method_configurations`: método, implementación, versión, parámetros (`num_samples`, background, capa) con hash.
- `xai_evidence` por muestra: `assessment_attempt_id`/`assessment_sample_id`, `dataset_source_record_id`, `run_id`,
  `checkpoint_artifact_id` (requiere Fase 0), `checkpoint_sha256`, `target_layer`, `target_class`,
  `explained_output`, `input_sha256`, `seed`, `environment_snapshot`, `prediction_score` (desde el EVALUATE del mismo
  checkpoint y muestra, si existe).
- `xai_artifacts`: mapa (`RAW_ATTRIBUTION`) y overlay (`OVERLAY`) referenciando `assessment_artifacts`, con
  `tensor_shape`, `numeric_dtype` y `availability`.
- Los guards `v2_xai_lineage_guard` y `v2_xai_artifact_source_guard` ya validan la coherencia.

**1c. G-03 EXPLAIN sobre TEST.**
- `assessment_identities_identity_check4` es independiente de `kind`: `explain` + `test` + `final` ya es válido en BD.
- Cambiar `src.explain` para aceptar una selección explícita de TEST (p. ej. `--split test`), sólo con umbral heredado
  (`auto`/`clinical`) y, por política, después del bloqueo de candidatos.
- Decidir si se exige registro previo de bloqueo (`assessment_final_locks`, hoy 0 filas) — ver D-01.

**Criterio de aceptación:** RUN con `accelerator` y pesos iniciales; intento EXPLAIN con `xai_evidence`/`xai_artifacts`
1:1 con sus resultados; EXPLAIN TEST verificado sobre un subconjunto. **Pruebas:** contratos y guards en PostgreSQL desechable.

### Fase 2 — Sin DDL: evaluación cuantitativa y revisión experta de XAI (G-05, G-06)

**2a. G-05 Fidelidad y similitud** — nueva operación científica (requiere inferencia; ver D-02 sobre su entrada CLI).
- Protocolos en `xai_evaluation_protocols` (nombre, versión, parámetros, estrategia de perturbación y normalización, hash):
  - *Deletion / insertion* (AUC al borrar/insertar píxeles por orden de atribución).
  - *Sanity check* de aleatorización de parámetros (correlación de rangos mapa original vs modelo aleatorizado).
  - *Similitud entre arquitecturas* sobre la misma muestra: correlación de Spearman e IoU del top-k %.
- Resultados en `xai_quantitative_evaluations` (`metric_value` o `undefined_reason`, `seed`, `sample_count`,
  `membership_hash`, `details_uri`/`details_sha256` para curvas por muestra) y miembros en `xai_evaluation_members`
  (`member_role` = `run_a`, `run_b`, `target`…).
- Población: subconjunto estratificado fijo (TP/TN/FP/FN por arquitectura, por paciente), seleccionado por `sample_id`
  en orden canónico y registrado en el manifiesto.

**2b. G-06 Validación biológica.**
- El dataset NIH no tiene anotaciones de región. Se requiere anotación experta de un subconjunto (máscara o punto del
  parásito) — es un proceso humano, no sólo software.
- Almacén candidato: `scientific_validation_annotations` (tiene `sample_id`, `content`, `version`; hoy 0 filas). Su
  semántica actual está orientada a sesiones de frotis: **verificar antes** si admite anotaciones de célula NIH o si hace
  falta otro contrato (D-03).
- Métricas con referencia: *pointing game* y IoU mapa↔máscara en `xai_quantitative_evaluations`
  (`reference_annotation_id`, `reference_annotation_version`, `reference_manifest_uri/sha256`).
- Revisión cualitativa: `xai_interpretations` (autor, interpretación, limitaciones) y `xai_specialist_reviews`
  (`supported`/`unsupported`/`inconclusive`, fundamento, competencia). Requiere pantalla en frontend.

**Criterio de aceptación:** protocolos sellados por hash; métricas reproducibles con la misma semilla; revisión experta
inmutable y atribuida. **Advertencia científica:** fidelidad alta no implica relevancia biológica; ambas se reportan por separado.

### Fase 3 — Con DDL: representaciones internas y análisis entre RUN (G-07, G-08)

**3a. G-07 Representaciones.** Nueva operación `represent` (decisión de entrada CLI: D-02).
- Identidad e intento en `assessment_identities`/`assessment_attempts` con `kind='represent'`: mismo checkpoint, split,
  muestras gobernadas, semilla, capas solicitadas.
- Salida: un `.npy` **por capa** (N × D, `float32`, filas en el orden canónico de `sample_id` registrado en la identidad),
  no un archivo por muestra. Estimación: VAL = 2.693 filas; D ≈ 128 (Custom CNN), 512 (VGG16 GAP), 1024 (DenseNet121
  GAP) ⇒ ~1,4–11 MB por capa y RUN.
- Capas por defecto: penúltima (embedding de la cabeza) y la salida espacial usada por Grad-CAM (agregada por GAP).
- Opcional: varias épocas (los checkpoints de todas las épocas existen) para dinámica de representaciones.
- **DDL necesario:** ampliar `assessment_identities_kind_check` a `represent` y la regla de verificación de
  `assessment_attempt_guard` (hoy: `explain` ⇒ 2 artefactos por muestra; `represent` ⇒ 1 artefacto por capa + manifiesto).

**3b. G-08 PCA / UMAP / CKA** y análisis derivados.
- Entidad de **análisis derivado** con identidad propia cuyos insumos son `attempt_id` verificados (uno o varios RUN):
  - PCA/UMAP por RUN y capa (componentes, varianza explicada, proyección 2D como artefacto).
  - CKA lineal entre pares de RUN/capas sobre la misma población y orden de `sample_id`.
  - Aprovechable para lo DERIVABLE de §3.3: ECE/Brier/fiabilidad, bootstrap por paciente, consenso/oracle, análisis por paciente.
- Opciones de almacenamiento (D-04): (a) `kind='analysis'` en `assessment_*` con identidad que lista insumos;
  (b) tablas nuevas `scientific_analysis_identities/attempts/outputs`. Ambas requieren DDL.
- Dependencia: `umap-learn` (no instalado en `.venv-local-train` ni `.venv-metal`); PCA y CKA sólo requieren
  `numpy`/`scikit-learn` (presentes). Instalación = D-05.
- Backend: el módulo `representations` ya consulta `artifacts` por tipo `embedding/pca/umap/cka`; redirigirlo a la
  entidad nueva y mostrar procedencia.

**Criterio de aceptación:** representaciones verificadas por hash y alineadas por `sample_id`; CKA de un modelo consigo
mismo = 1; PCA/UMAP reproducibles con semilla fija; análisis inmutables con insumos verificados.

### Fase 4 — G-09 Consumo TRAIN: subir de «ASIGNADA» a «ENUMERADA», sin reabrir TRACE

Lo máximo compatible con el cierre de TRACE:

- **Manifiesto de enumeración del loader:** antes de `fit`, persistir una vez por fase la lista de rutas que el loader
  TRAIN enumeró (`raw.file_paths`, igual que ya se hace para VAL), reconciliada contra `dataset_split_assignments`
  (ruta, clase, hash) en un registro `train_execution_records` `kind='loader_manifest'` con hash. Costo O(N) una vez,
  fuera del bucle de batches; no toca `train_step`, RNG ni orden.
- **Cobertura por época esperada por diseño:** registrar `steps_per_epoch` y tamaño del último batch derivados de la
  cardinalidad del dataset, junto con la época completada.
- **Rotulado obligatorio:** «Población ENUMERADA por el loader: 22.180 (reconciliada). Procesamiento por época:
  esperado por diseño, no observado. Consumo individual: NO DEMOSTRADO.» No escribir en `run_dataset_images` como uso
  (su FK apunta a `dataset_split_images`, sin hash ni versión para v1).
- Cualquier evidencia de consumo real requiere levantar TRACE-CLOSE-02 con nueva necesidad, mecanismo y presupuesto de
  interferencia. **No se propone.**

**Esquema:** sin DDL (`kind` libre en `train_execution_records`). Afecta `records_hash` sólo de RUN nuevos.

## 4. Secuencia recomendada

| Orden | Fase | DDL | Depende de | Habilita |
|---|---|---|---|---|
| 1 | Fase 0 (G-01, H-02, H-07) | No | — | SCC completo para RUN CLI; FK de `xai_evidence` |
| 2 | Fase 1a (G-02) | No | — | Comparabilidad por condición de ejecución |
| 3 | Fase 4 (G-09 enumeración) | No | — | Rotulado honesto de población TRAIN |
| 4 | Fase 1b (G-04) | No | Fase 0 | Base de Fase 2 |
| 5 | Fase 1c (G-03) | No | D-01 | XAI de errores TEST |
| 6 | Fase 2a (G-05) | No | Fase 1b | Fidelidad y similitud de mapas |
| 7 | Fase 3a (G-07) | **Sí** | D-02 | Representaciones |
| 8 | Fase 3b (G-08) | **Sí** | Fase 3a, D-04, D-05 | PCA/UMAP/CKA y derivados |
| 9 | Fase 2b (G-06) | No / por confirmar | D-03 y anotador experto | Validación biológica |

Antes de la campaña completa conviene tener las fases 0, 1a y 4 (sin DDL y de bajo riesgo). Las fases 1b–3 pueden
ejecutarse **después** de la campaña: los checkpoints de todas las épocas y los intentos quedan guardados, salvo
EXPLAIN TEST (1c), que sólo debe correr tras el bloqueo de candidatos.

## 5. Decisiones requeridas

| ID | Decisión | Opciones |
|---|---|---|
| D-01 | Política de acceso de EXPLAIN a TEST | Libre tras TEST / exigir bloqueo registrado en `assessment_final_locks` |
| D-02 | Entrada CLI de las operaciones nuevas | Ampliar `src.explain` (`--method embedding`, `--metric deletion`…) / nuevos módulos `src.represent`, `src.xai_eval`, `src.analyze` |
| D-03 | Almacén de anotaciones de célula | Reutilizar `scientific_validation_annotations` (verificar semántica) / contrato nuevo |
| D-04 | Entidad de análisis derivado | `kind='analysis'` en `assessment_*` / tablas `scientific_analysis_*` |
| D-05 | Dependencia UMAP | Instalar `umap-learn` en ambos venvs / limitarse a PCA y t-SNE de scikit-learn |
| D-06 | Uso de `--source-training-run-id` sin campaña | Aceptar que no alimenta la vista histórica SCC / exigir `--campaign-id` para RUN destinados a comparación |

## 6. Riesgos

| Riesgo | Mitigación |
|---|---|
| Proyectar evidencia que no corresponde (checkpoint, score) | Proyección sólo desde sesión `verified` y comparación de hashes; guards existentes |
| Cambiar la identidad de entorno de campañas congeladas | Clave `accelerator` separada de `IDENTITY_KEYS` |
| EXPLAIN TEST contamina la selección | Sólo tras bloqueo de candidatos; umbral heredado; sin tuning |
| Fidelidad confundida con validez biológica | Reportes separados; G-06 exige referencia humana |
| Coste de representaciones por época | Por defecto sólo checkpoint seleccionado; épocas extra opt-in |
| Archivos borrados (H-14) | Respaldo de `outputs/` y `artifacts/` y verificación física tras cada fase |
| Rotular enumeración como consumo | Texto fijado en Fase 4; TRACE-CLOSE-06/07 |

## 7. Fuera de alcance

Instrumentación por batch o por imagen de TRAIN; parches a APIs privadas de Keras; reescritura de intentos históricos;
recalibrar los 16 TRAIN existentes; afirmar reconocimiento biológico sin referencia experta.
