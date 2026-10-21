# SCC-CAMPAIGN.1A — Preflight científico integral de nueva campaña

Estado documental: `CURRENT_DOC`. Tipo: **auditoría de solo lectura**. Fecha: **2026-10-21**.
Código inspeccionado: `main`, HEAD `17244b93c9fb4dba0c119ba9905dd80b8fd7e14b`, árbol limpio.
Fuente de verdad: PostgreSQL operativo `malaria_experiments` (contenedor `capstone_db`, PostgreSQL 17.9),
consultado con `PGOPTIONS='-c default_transaction_read_only=on'` (verificado: `default_transaction_read_only = on`).

**Dictamen: `APROBADO CON ADVERTENCIAS`** — sin bloqueos para *ejecutar* la campaña con los cuatro
comandos y preservar la evidencia esencial; con una brecha de **consulta/visualización** en Comparación
Científica para RUN creados por `python -m src.train` (H-01), limitaciones científicas delimitadas
(representaciones internas no implementadas, criterio de checkpoint ambiguo, umbral sin calibración) y
condiciones que sólo pueden acreditarse operacionalmente durante la campaña (§9, §12).

---

## 1. Resumen ejecutivo

| Área | Resultado | Clase |
|---|---|---|
| Dataset gobernado v1 (`d8c0cab5-…`), FROZEN, materialización READY/PASS, 27.558 archivos físicos | PASS | — |
| SAME SPLIT / separación por paciente / fuga por SHA y píxeles | PASS (0 pacientes, 0 SHA, 0 hashes de píxel entre splits) | — |
| Contrato CLI de los cuatro comandos (`--help` real, código) | PASS | — |
| TRAIN preserva configuración, semilla, épocas, historial, selección, checkpoint + SHA-256 | PASS (código + 16 sesiones verificadas, 16/16 SHA-256 físicos coinciden) | — |
| RUN de `python -m src.train` sin proyecciones `artifacts`/`evaluations`/`run_clinical_metrics`/E10 | **FAIL** | Bloqueo de visualización SCC, no de evidencia (H-01) |
| Miembros de campaña no avanzan cuando TRAIN se lanza con `python -m src.train --campaign-id` | **FAIL** | Operativo/contable (H-02) |
| EVALUATE / TEST por muestra, intentos inmutables, repetibilidad | PASS (27 intentos, 22.889 resultados, sin sobrescritura) | — |
| TEST independiente de selección de modelo | PASS en código; disciplina de protocolo requerida (H-06) | Científica |
| Grad-CAM / LIME / SHAP sobre VAL | PASS implementado/persistido; validación científica SIN EVIDENCIA | Científica |
| EXPLAIN sobre TEST | No soportado (sólo `val`/`development`) | Científica, no bloqueante |
| Activaciones, embeddings, PCA, UMAP, CKA | **FAIL** (no implementados en el plano de ejecución) | Científica, derivable después (H-03) |
| Calibración de umbral en TRAIN | Deshabilitada en todas las configuraciones (`calibrate_threshold=false`) | Científica (H-05) |
| Criterio de checkpoint | Conflicto policy `auc_with_min_recall` vs monitor explícito `val_f2_parasitized`; ningún RUN alcanza `min_recall=0.98` | Científica (H-04) |
| Recorrido completo VGG16/DenseNet121 vía `python -m src.train` | SIN EVIDENCIA operacional (sólo Custom CNN probado por esta vía) | Operativo, se acredita en la campaña |

**Qué no se hizo:** no se ejecutó TRAIN, EVALUATE, EXPLAIN ni TEST; no se creó ni reservó campaña o
ejecución; no hubo DDL, migraciones ni SQL de escritura; no se modificó código, frontend, pesos, datasets ni
resultados; no se instalaron dependencias; no hubo commit ni push. La única escritura es este informe.

## 2. Alcance y fuentes inspeccionadas

**Documentos:** `docs/architecture/capstone_image_trace_lessons_learned.md`; `docs/audits/capstone_cli_01_parameter_certification.md`;
`docs/audits/capstone_data_01a_dataset_materialization_audit.md`; `docs/audits/capstone_data_01b1_new_single_cell_split_certification.md`;
`docs/audits/capstone_reports_01a_current_state.md`; `docs/engineering/scc_report_sci_1.md`, `scc_eligibility_1.md`, `scc_ui_preflight_2.md`;
`docs/contracts/scc_art_1.md`, `scc_xai_2.md`; `docs/engineering/campanas_creacion_ejecucion.md` (SUPERSEDED, sólo referencia del modelo de datos).

**Código** (`M/` = `malaria_dl_local_project/src/malaria_dl/`):

- Entradas: `malaria_dl_local_project/src/{train,evaluate,explain,test}.py`.
- TRAIN: `M/execution/operations.py`, `M/execution/selection.py`, `M/execution/train.py`, `M/execution/repository.py`, `M/execution/local_launch.py`.
- Assessment: `M/assessment/cli.py`, `service.py`, `lineage.py`, `runtime.py`, `contracts.py`.
- Backend SCC: `backend_api/app/repositories/scientific_results.py`, `services/scientific_preflight.py`,
  `services/comparison_eligibility.py`, `services/scientific_report.py`, `routes/campaigns.py`.
- Frontend: `frontend/src/components/reports/ScientificReport.tsx` (módulo de representaciones).

**PostgreSQL:** catálogo completo (`information_schema.tables`), `\d` de tablas operativas, funciones de trigger
(`pg_proc.prosrc`) y conteos reales por tabla (§11).

**Artefactos:** materialización física del dataset y checkpoints seleccionados de los 16 TRAIN (SHA-256 recomputado).

## 3. Estado actual de las investigaciones

| Investigación | Conclusión | Vigencia tras este preflight |
|---|---|---|
| TRACE.1A–1B.2-R2 (cierre 2026-10-21) | Sin evidencia individual exhaustiva de consumo en optimización; instrumentación por batch abandonada | **Vigente; no reabierta.** `run_dataset_images` = 0 filas, confirmado; no se interpreta como cero consumo |
| CAPSTONE-CLI-01 (2026-10-13) | Cuatro módulos públicos; `run_*` retirados; selección por `campaign-id`/`source-training-run-id` | **Vigente.** `run_*` ausentes; parsers coinciden con `--help` real |
| CAPSTONE-DATA-01B.1 (2026-10-14) | El flujo público no crea un segundo split; v1 intacto | **Vigente.** Sólo existe v1 Cell; la campaña debe usar v1 |
| SCC-REPORT-SCI.1 (2026-10-16) | Sólo `model_checkpoint` en `artifacts`; sin embeddings/PCA/UMAP/CKA; no alinea rutas históricas con `sample_id` sin correspondencia probada | **Vigente**; este preflight aporta prueba de correspondencia 1:1 para un RUN (§5.4) |
| SCC-ART.1 / CAPSTONE-REPORTS-01A | Acceso HTTP a artefactos implementado; aceptación autenticada pendiente | **Pendiente**, no revalidado aquí (requiere sesión autenticada) |
| CLI-01 §12 EXPLAIN-UI-01/02 | Visualización de artefactos y «Explicabilidad por caso» pendientes | **SIN EVIDENCIA** de cierre |

No se repitieron auditorías cuya evidencia sigue vigente (DATA-01B.1, TRACE, pruebas CLI-01).

## 4. Contrato verificado de los cuatro comandos

### 4.1 Entorno y directorio

- Directorio: `malaria_dl_local_project/`. Entorno: `.venv-local-train` o `.venv-metal`, Python **3.12.13** (ambos verificados).
  `local_launch.bootstrap` exige uno de esos venvs y Python 3.12; fija `DATABASE_URL` hacia `127.0.0.1:5432` con rol `capstone_v2_runtime` leído de `../.env`.
- `--help` ejecutado realmente para los cuatro módulos (no requiere BD): salida coincide con la matriz de CLI-01.

### 4.2 Matriz efectiva

| Comando | Selección | Opciones | Split / propósito | Identidad creada |
|---|---|---|---|---|
| `python -m src.train` | `--campaign-id` y/o `--source-training-run-id` (≥1 obligatorio) | `--dry-run`/`--plan`/`--inspect` | TRAIN+VAL; `evaluate_best_on_test` debe ser `false` (`TEST_FORBIDDEN`) | `runs.id` + `train_execution_sessions` nuevos por miembro |
| `python -m src.evaluate` | ídem | `--inspect --threshold --seed --batch-size` | `val` / `development` | `assessment_identities` (kind `evaluate`) + `assessment_attempts` |
| `python -m src.explain` | ídem | + `--method {gradcam,lime,shap} --layer --class-id --num-samples --max-images\|--sample-id --background-sample-id` | `val` / `development` | kind `explain` + `assessment_artifacts` (map `.npy` + overlay `.png`) |
| `python -m src.test` | ídem | `--inspect --threshold --seed --batch-size` | `test` / `final` | kind `evaluate`, `split=test`, `purpose=final` |

`--dataset-version-id` **no existe** como argumento: el dataset proviene de la campaña (`experimental_campaigns.dataset_version_id`)
o del TRAIN de origen (`M/execution/operations.py:training_plan`). Para EVALUATE/EXPLAIN/TEST el dataset se hereda del TRAIN
(`M/assessment/lineage.py:resolve` → `training_dataset_metadata`) y se re-verifica física y criptográficamente (`dataset_samples`).

### 4.3 Resolución del checkpoint

`lineage.resolve` exige `train_execution_sessions.state='verified'`, re-verifica registros y binario (`verify_session`),
toma `verification.artifact` (ruta, SHA-256, bytes, época) y exige un único registro `calibration/val/selected` cuya
`checkpoint_epoch` coincida. Antes de inferir, `service.execute_reserved` comprueba de nuevo SHA-256 y tamaño
(`CHECKPOINT_CONTENT_CHANGED`). **PASS.**

### 4.4 Selección multi-TRAIN y dependencias

- `selection.select_trainings`: `runs.campaign_id=:campaign` **o** vínculo `campaign_attempts→campaign_members`; `ORDER BY r.started_at, r.id`. Sin «latest».
- TRAIN por campaña (`operations.training_plan`) itera **todos** los miembros de la campaña en cada invocación (no omite miembros ya entrenados). Ver H-07.
- Dependencias reales: EVALUATE/EXPLAIN/TEST requieren `runs.status='completed'` (`TRAIN_NOT_COMPLETED`) y sesión `verified`. TEST no requiere EVALUATE ni EXPLAIN. EXPLAIN no requiere EVALUATE.
- Exclusión global: índice `uq_global_train_active` (sesión `active` **o** `completed`), `uq_global_assessment_active` y trigger `experiment_reservation_guard` impiden TRAIN y assessment simultáneos. Gate `experiment_execution_gate` liberado (`release_confirmed=true`, sin owner). Hoy: 16 sesiones `verified`, 0 intentos `active`.

### 4.5 Errores y reintentos

- TRAIN: cada miembro captura su excepción; la sesión `active` pasa a `failed` (`INDIVIDUAL_TRAIN_FAILED`); salida 2 si alguno no queda `verified`.
- Assessment: un fallo deja el intento `failed` con los resultados ya escritos (p. ej. LIME `failed` con 1.344 resultados parciales, conservados). Repetir genera nuevo `execution_id` → nueva identidad (`structural_hash` incluye `execution_id`) y nuevo `artifact_root`.
- Equivalencia `python -m src.*` ↔ `run_*`: **no aplica**; los `run_*` fueron retirados (verificado: no existen en `malaria_dl_local_project/`).

## 5. Dataset y SAME SPLIT

### 5.1 Versión y materialización

| Campo | Valor observado |
|---|---|
| `dataset_versions.id` | `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2` — «Malaria Patient Split v1» 1.0.0, **FROZEN** (2026-08-18), seed 42 |
| Clases | `{"0":"uninfected","1":"parasitized"}`, clase positiva `parasitized` |
| Materialización | intento 1, **READY / PASS**, `relative_root=malaria_dataset_versions/d8c0cab5-…`, 27.558 registros |
| Reconciliación (`manifest_metadata`) | `files_found=27558`, `sha_match=27558`, `sha_mismatch=0`, `missing=0`, `unexpected=0`, `filename_collisions=0` |
| Digests | `record_assignment=9709ce48…6ea2`, `patient_assignment=cbe7a7b8…ea7f` |
| Otra versión | `f0c1f636-…` Thin Blood Smear (965 frotis), **no aplicable** a clasificación celular |

### 5.2 Particiones

| Split | uninfected | parasitized | Total | Pacientes (únicos) | Archivos físicos |
|---|---:|---:|---:|---:|---:|
| TRAIN | 11.043 | 11.137 | 22.180 | 161 | 11.043 / 11.137 |
| VAL | 1.368 | 1.325 | 2.693 | 20 | 1.368 / 1.325 |
| TEST | 1.368 | 1.317 | 2.685 | 20 | 1.368 / 1.317 |

Pacientes con imágenes parasitadas: 121 / 15 / 15. Archivos físicos contados bajo
`malaria_dl_local_project/data/malaria_dataset_versions/d8c0cab5-…/{split}/{clase}`.

### 5.3 Controles de fuga e identidad — PASS

- Pacientes en más de un split: **0**. SHA-256 de archivo compartido entre splits: **0**. SHA de píxeles decodificados entre splits: **0**.
- Discrepancias clase/paciente entre `dataset_split_assignments` y `dataset_source_records`: **0**. `identity_status=VERIFIED`: 27.558/27.558.
- Identidad de muestra: `sample_id = dataset_split_assignments.source_record_id` (UUID), `patient_id = clinical_identity_id`.
- `dataset_split_images` (55.116 filas, `dataset_version_id` NULL, «malaria_physical_split») es **heredada**, no fuente operativa.

### 5.4 Asignada ≠ procesada; correspondencia ruta ↔ `sample_id`

- TRAIN asignado = 22.180 imágenes. **Consumo efectivo en optimización: NO DEMOSTRADO** (TRACE-CLOSE-06/07). `run_dataset_images` = 0 filas y no se usa como contador.
- Predicciones VAL de TRAIN se identifican por **ruta relativa** (`train.py:205`, `{"sample": path}`); assessment por `sample_id` UUID.
  Prueba de lectura para `d3d42cf3`: 2.693 rutas de `calibration/val/selected`, 2.693 distintas, **2.693/2.693** coinciden con `relative_path` de la identidad EVALUATE VAL. Con `filename_collisions=0`, la proyección ruta→`sample_id` es derivable sin ambigüedad. **No implementada** en SCC (scc_report_sci_1 §52).

### 5.5 TEST no utilizado en TRAIN/selección — PASS (código)

TRAIN carga sólo `train` y `val` (`train.py:79`); `TEST_FORBIDDEN` y `E5_TRAIN_TEST_OR_SIDECAR_FORBIDDEN`; selección de checkpoint y
`calibration` sólo sobre VAL. TEST se lee únicamente en `src.test` (`split=test`, `purpose=final`; constraint `assessment_identities_identity_check4`).

## 6. Matriz de persistencia por operación

| Evidencia | Fuente operativa | RUN de worker (15) | RUN de `python -m src.train` (`d3d42cf3`) | Estado |
|---|---|---|---|---|
| RUN, modelo, dataset, campaña, semilla | `runs` (+FK `campaign_id`, `dataset_version_id`, `model_id`) | Sí | Sí | PASS |
| Configuración completa (modelo, optimizador+LR, recipe/augmentation, selección, input contract) | `runs.execution_parameters.model_configuration_e2.configuration` y `train_execution_sessions.configuration`; `run_configurations` | Sí | Sí (`run_configurations`=1) | PASS |
| Pesos iniciales | `resolved.model.weights` (`none` Custom CNN; ImageNet según adapter VGG/DenseNet) | Sí | Sí | PASS (declarado; hash de pesos ImageNet SIN EVIDENCIA) |
| Fases y épocas | `train_execution_records` `phase`, `epoch` (`base`, `fine_tuning`) | Sí | Sí | PASS |
| Historial TRAIN/VAL por época (+ LR) | `train_execution_records.kind='epoch'` | Sí | Sí | PASS (`training_history`=0 es heredada) |
| Selección y mejor época | `kind='selection'`, `train_execution_sessions.completion.selection` | Sí | Sí | PASS |
| Checkpoint por época + SHA-256 | `kind='artifact'` (ruta, `sha256`, `bytes`, `version_id`) | Sí | Sí | PASS |
| Checkpoint seleccionado verificado | `train_execution_sessions.verification.artifact` | Sí | Sí | PASS (16/16 SHA-256 físicos coinciden) |
| Predicciones VAL por época y del checkpoint elegido | `kind='predictions'` / `kind='calibration'` (`payload.samples`) | Sí | Sí | PASS (por ruta) |
| Estado y duración | `runs.status`, `duration_seconds`; `train_execution_sessions.state` | Sí | Sí | PASS (`runs.completed_epochs=0` y `best_epoch` NULL en 12 RUN de Campaña 1: proyección histórica incompleta, la sesión sí lo tiene) |
| Eventos E10 | `kind='e10_event'` | Sí | **No** | FAIL (H-01) |
| Checkpoint registrado para SCC | `artifacts` (`model_checkpoint`) + `execution_parameters.e10_v2_evaluation_context_v1` | Sí | **No** | FAIL (H-01) |
| Evaluación VAL final de TRAIN | `evaluations` + `run_clinical_metrics` | Sí | **No** | FAIL (H-01) |
| EVALUATE / TEST por muestra | `assessment_results(attempt_id, sample_id)`: label, raw_score, predicted, threshold, patient_id | — | Sí | PASS |
| Métricas y confusión | `assessment_attempts.verification.metrics` (`binary_counts_rates_v1`) | — | Sí | PASS |
| EXPLAIN | `assessment_results` (spec, capa, clase) + `assessment_artifacts` (map/overlay, SHA-256) | — | Sí | PASS |
| Representaciones internas | ninguna | No | No | FAIL (H-03) |

### 6.1 Mapa de persistencia y trazabilidad de artefactos científicos

El mapa permanente está en [capstone_scientific_artifacts_and_persistence.md](../architecture/capstone_scientific_artifacts_and_persistence.md):
raíces físicas y qué las determina, tabla e identificador por evidencia, consultas SQL reproducibles, verificación de
SHA-256 y política de conservación. Su §3.3 relaciona cada pregunta de «Aprendizaje del Modelo» y «Comparación
Científica» con su evidencia, fuente y estado (PERSISTE / DERIVABLE / NO EXISTE / NO DEMOSTRADO), y cada módulo de
Comparación Científica con la fuente que consulta. Este preflight lo valida con estas observaciones:

| Control | Resultado | Estado |
|---|---|---|
| Raíz TRAIN de `python -m src.train` | `outputs/train_runs/<run_id>/`, relativa al directorio actual (`operations.py:64`) | PASS; ejecutar desde `malaria_dl_local_project/` |
| Raíz TRAIN de la Campaña 1 | `outputs/campaign_runs/<run_id>/` (worker, `campaign.py:406`) | PASS, histórico |
| Raíz assessments | `artifacts/assessments/<attempt_id>/` (`assessment/cli.py:104`); sin `--artifact-root` público | PASS |
| Consulta `artifacts WHERE artifact_type='model_checkpoint'` | 15 de 16 RUN; omite RUN de CLI | FAIL como fuente única (H-01); usar `train_execution_sessions.verification.artifact` |
| Checkpoints seleccionados, SHA-256 + bytes | 16 / 16 | PASS |
| Checkpoints de todas las épocas, existencia + bytes | 432 / 432 | PASS |
| Artefactos EXPLAIN, SHA-256 + bytes | 13.578 / 18.964; 5.386 ausentes, todos del intento `ceaa29af-…` | FAIL histórico (H-14) |
| Inmutabilidad de filas PostgreSQL | Guards sólo-INSERT / sin DELETE en `train_execution_*` y `assessment_*` | PASS |
| Protección de archivos en disco | Ninguna | FAIL (H-14) |

## 7. Cobertura de preguntas científicas

### 7.1 Fase F — técnicas de explicación y representación

| Técnica | 1. Código | 2. Ejecutable con checkpoint actual | 3. Persistida | 4. API | 5. Comparación Científica | 6. Validación científica |
|---|---|---|---|---|---|---|
| Grad-CAM | PASS (`runtime.explain`, `compute_gradcam_artifacts`) | PASS (VAL completo verificado, 2.693) | PASS | PASS (SCC-ART.1; aceptación autenticada pendiente) | Parcial (módulo XAI) | SIN EVIDENCIA |
| LIME | PASS (1000–5000) | PASS (1 muestra verificada; VAL completo `failed` parcial) | PASS | ídem | Parcial | SIN EVIDENCIA |
| SHAP (GradientExplainer) | PASS (background explícito VAL) | PASS (1 muestra) | PASS | ídem | Parcial | SIN EVIDENCIA |
| Activaciones intermedias | FAIL | — | FAIL | FAIL | FAIL | — |
| Embeddings | FAIL | — | FAIL | Sólo inventario de `artifacts` | Mensaje «no disponible» | — |
| PCA / UMAP | FAIL | — | FAIL | ídem | ídem | — |
| CKA | FAIL | — | FAIL | ídem | «sin análisis acreditado» | — |

EXPLAIN asociable a las mismas muestras que las predicciones: **PASS** por `sample_id` (misma población VAL ordenada por `source_record_id`;
`--max-images N` selecciona los N primeros UUID, idéntico entre arquitecturas). EXPLAIN **no** cubre TEST ni guarda el score del modelo
(se une con EVALUATE por `sample_id`). Una visualización Grad-CAM no prueba reconocimiento biológico del parásito.

### 7.2 Fase G — comparabilidad entre arquitecturas

| Dimensión | Estado | Comentario |
|---|---|---|
| Dataset y población común | Listo | Misma versión, fingerprints en `identity.dataset`; VAL 2.693 / TEST 2.685 |
| Etiquetas alineadas | Listo | `label` por `sample_id` en cada intento |
| Checkpoints verificables | Listo en datos / FAIL en SCC para RUN CLI | H-01 |
| Protocolo y umbral documentados | Listo | `identity.decision` (`effective`, `source`, `>=`, raw) |
| Predicciones individuales VAL/TEST | Listo | `assessment_results` |
| FN/FP compartidos, consenso, oracle | Listo (VAL); TEST SIN EVIDENCIA operacional en SCC | `scientific_report.consensus` por intersección de `sample_id` |
| Confianza y calibración | Derivado | `raw_score` persistido; ECE/Brier existen en `evaluation/probability_calibration.py`, no integrados a SCC |
| Representaciones / CKA | Requiere implementación | H-03 |
| Explicaciones espaciales | Listo (VAL) | Comparación cuantitativa entre mapas no implementada |
| TEST independiente | Listo (código) | H-06 |
| Incertidumbre estadística | Derivado / implementación | Bootstrap por paciente especificado en `science/protocol.py:229`, no conectado a assessment/SCC |
| Análisis por paciente | Derivado | `patient_id` en cada resultado; TEST = 20 pacientes (15 parasitados): IC amplios |
| Variabilidad por semilla | Depende del diseño | Campaña 1 usó una sola semilla (47) |

### 7.3 Fase I — matriz de cobertura

| Pregunta científica | Evidencia requerida | Fuente actual | Estado | Brecha | Acción propuesta |
|---|---|---|---|---|---|
| Evolución del aprendizaje | Métricas TRAIN/VAL y LR por época y fase | `train_execution_records` `epoch` | PASS | — | Durante campaña |
| Selección de checkpoint | Criterio, monitor, época, métrica, checkpoint+SHA | `selection`, `completion`, `verification.artifact` | PASS con advertencia | Conflicto policy/monitor; `min_recall` no alcanzado (H-04) | **Antes**: fijar criterio en protocolo |
| Desempeño VAL | Predicciones por muestra, umbral, métricas | `assessment_results` (EVALUATE VAL); `calibration/val/selected` | PASS | `evaluations` ausente en RUN CLI (H-01) | Durante: `src.evaluate` |
| Generalización TEST | Predicciones TEST por muestra con checkpoint/umbral congelados | `assessment_results` (`test/final`) | PASS (código + 2 TEST previos verificados) | Independencia depende de bloqueo de candidatos (H-06) | **Antes**: documentar candidatos y umbral; después: `src.test` |
| Errores por muestra | label, score, predicho, paciente | `assessment_results` | PASS | — | Derivado |
| Errores compartidos | Intersección de `sample_id` entre RUN | `scientific_report.consensus` | PASS VAL / SIN EVIDENCIA TEST en UI | — | Derivado |
| Confianza y calibración | raw scores; curvas de fiabilidad, ECE, Brier | `raw_score`; módulo de calibración no integrado | Parcial | `calibrate_threshold=false` (H-05) | Derivado post-campaña |
| Evidencia espacial | Grad-CAM/LIME/SHAP por muestra | `assessment_artifacts` | PASS (VAL) | Sin TEST; sin métrica cuantitativa de localización | Durante (Grad-CAM); futuro: evaluación cuantitativa |
| Representaciones internas | Activaciones/embeddings por capa y muestra | — | FAIL | No implementado (H-03) | Derivado desde checkpoints (implementación nueva) |
| Similitud representacional | CKA entre arquitecturas/capas/épocas | — | FAIL | No implementado (H-03) | Investigación posterior |
| Robustez | Perturbaciones controladas, variación por semilla | — | SIN EVIDENCIA | Sin protocolo; semilla única en campaña previa | Diseño: ≥3 semillas; robustez = futuro |
| Comparabilidad entre arquitecturas | Misma población, protocolo, umbral y checkpoint verificable | Identidades assessment + dataset | PASS en datos | Visualización checkpoint SCC (H-01) | Corregir H-01 |

**Clasificación:**

- *Indispensable antes de ejecutar:* campaña creada y congelada sobre v1; protocolo con criterio de checkpoint, política de umbral, semillas y regla de acceso a TEST (§9).
- *Se obtiene durante la campaña:* historial, checkpoints+SHA, selección, predicciones VAL/TEST por muestra, Grad-CAM VAL.
- *Derivada después:* proyección ruta→`sample_id`, consenso/FN/FP compartidos, calibración (ECE/Brier/fiabilidad), bootstrap por paciente, análisis por paciente, embeddings/PCA/UMAP/CKA calculados desde checkpoints ya guardados (todas las épocas se conservan).
- *Investigación futura no bloqueante:* validación biológica de mapas, robustez, EXPLAIN sobre TEST, instrumentación de consumo (cerrada por TRACE).

## 8. Brechas y riesgos

| ID | Hallazgo | Estado | Tipo | Evidencia |
|---|---|---|---|---|
| H-01 | `python -m src.train` llama `train(repo, session, …)` **sin** `event_emitter` (`M/execution/train.py:362`); por ello no ejecuta `bind_evaluation_context` (`train.py:274-276`) ni emite eventos E10. Resultado: sin fila `artifacts` (`model_checkpoint`), sin `e10_v2_evaluation_context_v1`, sin `evaluations` ni `run_clinical_metrics`. `comparison_checkpoint` depende de esa fila (`scientific_results.py:193-205`) y `checkpoint_evidence` exige `record.id` (`scientific_report.py:33`) → previsiblemente `CHECKPOINT_UNREGISTERED` en Comparación Científica | **FAIL** (estático); respuesta HTTP SIN EVIDENCIA | Visualización/consulta; la evidencia primaria sí persiste | §11 Q7 |
| H-02 | La ruta `standalone` inserta `runs.campaign_id` pero no crea `campaign_attempts` ni actualiza `campaign_members`; tampoco valida el estado de la campaña. C02 `4d041560` conserva su miembro `pending` pese al TRAIN verificado `d3d42cf3` | **FAIL** | Operativo/contable | §11 Q6 |
| H-03 | No existe extracción de activaciones/embeddings ni PCA/UMAP/CKA; backend sólo inventaría `artifacts` por tipo | **FAIL** | Científica | `scientific_results.py:219-226`; búsqueda en `malaria_dl_local_project/src` |
| H-04 | Configuración: `checkpoint_policy=auc_with_min_recall` y `selection.explicit=true` con `monitor=val_f2_parasitized`; la selección registra «Selected by explicit monitor … not by configured policy». Ningún TRAIN (16) cumple `min_recall=0.98` (`clinical_objective_met=false`) | Advertencia | Científica | §11 Q9 |
| H-05 | `calibrate_threshold=false` en los 16 TRAIN; `calibration.result={"enabled":false,"threshold":0.5}`. `--threshold auto` ⇒ 0,5 fijo (`training_fixed_threshold_v1`); `--threshold clinical` fallará (`CLINICAL_THRESHOLD_EVIDENCE_REQUIRED`) | Advertencia | Científica | §11 Q9 |
| H-06 | El protocolo de campaña declara `test_access: final_only_after_candidate_lock` (`science/protocol.py`), pero `src.test` no exige bloqueo (`assessment_final_locks`=0); la independencia de TEST depende de disciplina de protocolo | Advertencia | Científica | `M/assessment/cli.py:_execute` |
| H-07 | `python -m src.train --campaign-id` entrena **todos** los miembros en cada invocación; repetir tras un fallo duplica RUN, y EVALUATE/TEST `--campaign-id` seleccionará también duplicados y fallidos | Riesgo | Operativo | `operations.py:training_plan` |
| H-08 | `uq_global_train_active` cubre `completed`; una caída entre `completed` y `verified` bloquearía todo TRAIN/assessment posterior | Riesgo | Operativo | `\d train_execution_sessions` |
| H-09 | `deterministic_ops=false` en TRAIN: reproducibilidad bit a bit no garantizada (assessment sí activa determinismo) | Advertencia | Científica | config resuelta |
| H-10 | VGG16/DenseNet121 nunca recorridos por `python -m src.train` (sólo por worker en Campaña 1) | SIN EVIDENCIA | Operativo | §11 Q6 |
| H-11 | Duración: VGG16 5,5–6,3 h, DenseNet121 2,2–3,5 h, Custom CNN 0,7–1,6 h por miembro (Campaña 1). Disco libre 363 GiB; `outputs/campaign_runs` = 15 GB (todas las épocas se guardan) | Riesgo de capacidad, no bloqueante | Operativo | `runs.duration_seconds`; `du`/`df` |
| H-12 | EXPLAIN-UI-01/02 y certificación HTTP autenticada de artefactos (SCC-ART.1) siguen pendientes | SIN EVIDENCIA | Visualización | docs citados |
| H-13 | `--threshold clinical` exigía `calibrate_threshold=true`, imposible de configurar en una campaña (`science/protocol.py:214`). **Corregido en `fa322be`:** el protocolo de campaña ofrece «Calibración del umbral (VAL)» con «auto 0,5» (`none`, por defecto) o «clinical» (`threshold_grid`). Los 16 TRAIN previos no se pueden recalibrar | PASS en pruebas; SIN EVIDENCIA operacional | Científica | `campaigns/configuration.py`; pruebas §11 |
| H-14 | Los archivos `.keras`/`.npy`/`.png` no tienen protección contra borrado. 5.386 artefactos del intento verificado `ceaa29af-…` faltan en disco (ya observado en REPORTS-01A) | FAIL | Conservación | §6.1 |
| H-15 | El dispositivo de ejecución (CPU / GPU Metal) no se persiste; con la misma configuración, CPU y GPU dieron curvas distintas (`e9eb63f4` vs `bbbd5b60`) | Advertencia | Científica | `runs.gpu_devices=[]`; `train_execution_records` `epoch` |

**Actualización 2026-10-21 — SCC-EVIDENCE Fase 0 (sin commit):** `python -m src.train --campaign-id` sin
`--source-training-run-id` delega ahora en el coordinador de campaña (`claim` → worker con `RunEventEmitter`).
Corrige en código **H-01** (proyecciones `artifacts`/`evaluations`/`run_clinical_metrics`/E10), **H-02** (intentos y
miembros) y **H-07** (no reentrena miembros `verified`; reintenta fallidos dentro del presupuesto). Estado: PASS en
pruebas sin PostgreSQL; **SIN EVIDENCIA operacional** hasta el piloto. Detalle en
[scc_evidence_persistence_plan.md](../planning/scc_evidence_persistence_plan.md#fase-0--prerrequisito-proyecciones-de-train-por-cli-g-01-además-h-02h-07).
Los RUN CLI ya verificados (`d3d42cf3`) no se pueden reparar.

## 9. Acciones mínimas antes de ejecutar

1. **Decisión de protocolo (documental, obligatoria):** semillas por arquitectura (recomendado ≥3), un optimizador por arquitectura o matriz explícita, criterio de checkpoint único (resolver H-04), política de umbral (0,5 fijo o calibración VAL habilitada; H-05), y regla escrita: candidatos y umbral congelados antes de TEST (H-06).
2. **Crear y congelar la campaña** sobre `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2` mediante el flujo autorizado (`POST /api/campaigns` + freeze). Requiere autorización explícita; no se hizo aquí.
3. **Decidir H-01** antes de la campaña: (a) corregir `src.train` para producir las mismas proyecciones que el worker (recomendado), o (b) aceptar que Comparación Científica no mostrará checkpoint/VAL histórica para estos RUN hasta una proyección posterior desde la evidencia persistida (sin reejecutar ciencia).
4. **Inspección sin escritura** con los IDs reales: `src.train --campaign-id <C> --plan`; tras TRAIN, `--inspect` de los otros tres.
5. Confirmar ausencia de sesiones `active`/`completed` y de intentos `active` inmediatamente antes de iniciar (Q8).
6. Fijar un único entorno (`.venv-metal` recomendado) y registrar fuera del sistema `tf.config.list_physical_devices('GPU')` y la versión de `tensorflow-metal` (H-15).
7. Respaldar `outputs/`, `artifacts/assessments/` y la BD al terminar, y ejecutar la verificación física del mapa de persistencia (§6.1) antes de cualquier reporte (H-14).

## 10. Plan de ejecución posterior (no ejecutado)

Desde `malaria_dl_local_project/`, con `source .venv-metal/bin/activate` (o `.venv-local-train`):

```bash
python -m src.train --campaign-id "$CAMPAIGN_ID" --plan
python -m src.train --campaign-id "$CAMPAIGN_ID"
python -m src.evaluate --campaign-id "$CAMPAIGN_ID" --inspect
python -m src.evaluate --campaign-id "$CAMPAIGN_ID" --threshold auto --seed auto
python -m src.explain --campaign-id "$CAMPAIGN_ID" --method gradcam --class-id 1 --max-images all
python -m src.explain --campaign-id "$CAMPAIGN_ID" --method lime --num-samples 1000 --max-images "$N"
python -m src.explain --campaign-id "$CAMPAIGN_ID" --method shap --num-samples 1000 --max-images "$N" --background-sample-id "$BG_ID"
python -m src.test --campaign-id "$CAMPAIGN_ID" --inspect
python -m src.test --campaign-id "$CAMPAIGN_ID" --threshold "$THRESHOLD_CONGELADO" --seed auto
```

Secuencia: TRAIN (todos los miembros) → verificar 100 % `verified` → EVALUATE VAL → EXPLAIN VAL (Grad-CAM completo; LIME/SHAP subconjunto `N` común) → **congelar candidatos y umbral por escrito** → TEST una vez por candidato.
Si un miembro falla, reintentarlo con `--campaign-id "$CAMPAIGN_ID" --source-training-run-id "$RUN_FALLIDO"` (no repetir la campaña completa, H-07) y evaluar por `--source-training-run-id` para no incluir fallidos.
`$N`, `$BG_ID` y `$THRESHOLD_CONGELADO` no se fijan aquí: dependen del protocolo del paso 9.1.

## 11. Evidencia verificable

Todas las consultas se ejecutaron con `docker exec -e PGOPTIONS='-c default_transaction_read_only=on' capstone_db psql …`.

**Q1 — Conteos reales (selección):** `runs` 16 (todos `training`), `train_execution_sessions` 16, `train_execution_records` 4.390,
`experimental_campaigns` 7, `campaign_members` 18, `campaign_attempts` 15, `assessment_identities` 27, `assessment_attempts` 27,
`assessment_results` 22.889, `assessment_artifacts` 18.964, `artifacts` 15, `evaluations` 15, `run_clinical_metrics` 15,
`run_configurations` 16, `dataset_split_assignments` 28.523, `dataset_source_records` 28.523.
Vacías: `training_history`, `run_metrics`, `predictions`, `explainability_results`, `xai_*`, `run_dataset_images`, `run_lineage`, `assessment_final_locks`, `local_execution_jobs`.
(`pg_stat_user_tables.n_live_tup` estaba desactualizado; se usaron `count(*)`.)

**Q2 — Splits:**
```sql
SELECT dataset_version_id, split_name, class_index, class_name, count(*), count(DISTINCT clinical_identity_id)
FROM dataset_split_assignments GROUP BY 1,2,3,4 ORDER BY 1,2,3;
```

**Q3 — Fuga por paciente / SHA / píxeles:** resultado 0 / 0 / 0.
```sql
SELECT dataset_version_id, count(*) FROM (SELECT dataset_version_id, clinical_identity_id FROM dataset_split_assignments
  GROUP BY 1,2 HAVING count(DISTINCT split_name)>1) x GROUP BY 1;
SELECT count(*) FROM (SELECT r.source_file_sha256 FROM dataset_split_assignments a JOIN dataset_source_records r ON r.id=a.source_record_id
  WHERE a.dataset_version_id='d8c0cab5-09dd-597f-9de7-7ca01aee2ec2' GROUP BY 1 HAVING count(DISTINCT a.split_name)>1) x;
-- idem con r.decoded_pixel_sha256
```

**Q4 — Consistencia etiqueta/paciente:** 0 discrepancias.
```sql
SELECT count(*) FROM dataset_split_assignments a JOIN dataset_source_records r ON r.id=a.source_record_id
WHERE a.class_index<>r.class_index OR a.clinical_identity_id<>r.clinical_identity_id;
```

**Q5 — Campañas:** Campaña 1 `b54ea684` finalized (12 miembros verified: 3 arquitecturas × adadelta/adam/adamw/sgd, seed 47);
`900bbe8f`, `2ffeca5d`, `4b5a9626` finalized; `2c1e1229` paused; `2fb7a7a8` y `4d041560` («C02») frozen, todas sobre `d8c0cab5-…`.

**Q6 — Linaje por RUN:**
```sql
SELECT r.id, r.status, s.state, r.campaign_id,
  EXISTS(SELECT 1 FROM campaign_attempts a WHERE a.training_run_id=r.id) AS via_attempt
FROM runs r LEFT JOIN train_execution_sessions s ON s.run_id=r.id WHERE r.run_type='training' ORDER BY r.started_at;
```
15 RUN con `via_attempt=true` (worker); `d3d42cf3-0800-468c-b3ed-995860967da1` con `campaign_id=4d041560-…` y `via_attempt=false`.
Miembro de `4d041560`: `pending`.

**Q7 — Proyecciones por RUN:**
```sql
SELECT r.id, r.execution_parameters ? 'e10_v2_evaluation_context_v1',
  (SELECT count(*) FROM artifacts a WHERE a.run_id=r.id),
  (SELECT count(*) FROM evaluations e WHERE e.training_run_id=r.id),
  (SELECT count(*) FROM run_clinical_metrics m WHERE m.run_id=r.id),
  (SELECT count(*) FROM train_execution_records t WHERE t.run_id=r.id AND kind='e10_event')
FROM runs r ORDER BY r.started_at;
```
15 RUN de worker: `t / 1 / 1 / 1 / >0`. `d3d42cf3`: `f / 0 / 0 / 0 / 0`. `artifacts` sólo contiene `model_checkpoint` (15).

**Q8 — Exclusión global:** `train_execution_sessions`: 16 `verified`; `assessment_attempts`: 25 `verified`, 2 `failed`, 0 `active`;
`experiment_execution_gate`: sin owner, `release_confirmed=true`, `blocked_reason` NULL (actualizado 2026-10-19).

**Q9 — Selección y calibración:** `completion.clinical_objective_met=false` en 16/16; F2 VAL seleccionado 0,81–0,95;
`calibration.result` de `d3d42cf3` = `{"enabled": false, "threshold": 0.5}`; `selection.warning` presente en 4 RUN recientes.

**Q10 — Assessments:** 27 intentos sobre 3 TRAIN (`bbbd5b60`, `338136db`, `d3d42cf3`): EVALUATE VAL 2.693, TEST 2.685 (2 intentos, `verified`),
Grad-CAM VAL completo (3), LIME/SHAP de 1 muestra, 1 LIME VAL completo `failed` (1.344 resultados parciales), 1 SHAP `failed` (0).
Payload TEST: `{label, predicted, raw_score, sample_id, threshold, patient_id, calibrated_score:null}`.

**Q11 — Correspondencia ruta ↔ `sample_id` (`d3d42cf3`, VAL):** 2.693 / 2.693 distintas / 2.693 en identidad / **2.693 coincidencias**.

**Q12 — Guardas relevantes (`pg_proc`):** `assessment_attempt_guard` (inmutabilidad, `ASSESSMENT_INCOMPLETE` si `count` ≠ población o explain ≠ 2 artefactos por muestra);
`assessment_identity_guard` (TRAIN requerido, split/propósito ∈ protocolo, muestras únicas con paciente, etiqueta y SHA);
`experiment_reservation_guard` (TRAIN y assessment excluyentes); `controlled_run_guard` (campaña inmutable en UPDATE, sin validar estado de campaña en INSERT);
`assessment_identities_kind_check` (`evaluate`,`explain`): TEST se persiste como `evaluate` + `test/final`.

**Artefactos físicos:** checkpoint seleccionado de los 16 TRAIN (`train_execution_sessions.verification.artifact`) recomputado con
`shasum -a 256` y `stat`: **16/16 PASS** (ruta, SHA-256 y bytes). Ejemplo: `outputs/train_runs/d3d42cf3-…/epoch_2.keras`.
Dataset: conteos físicos por carpeta iguales a Q2.

**CLI:** `.venv-local-train/bin/python -m src.{train,evaluate,explain,test} --help` → rc 0, opciones de §4.2.

## 12. Dictamen final

**`APROBADO CON ADVERTENCIAS`.**

- **Bloqueos operativos para ejecutar:** ninguno verificado. Dataset, CLI, exclusión global, resolución de checkpoint e integridad están en PASS.
- **Brecha que compromete la visualización, no la evidencia:** H-01. La evidencia primaria (sesión verificada, registros por época,
  checkpoint+SHA, predicciones por muestra) se conserva, pero Comparación Científica no podrá acreditar el checkpoint de los nuevos RUN.
  Corregirla antes de ejecutar evita una proyección posterior.
- **Limitaciones científicas delimitadas:** H-03 (representaciones internas y CKA no implementadas, derivables desde checkpoints), H-04, H-05, H-06, H-09.
- **No acreditable estáticamente:** recorrido VGG16/DenseNet121 vía `python -m src.train` (H-10), presentación SCC/HTTP de los nuevos RUN (H-01, H-12).
  Se acreditan durante la campaña; por eso el dictamen no es `APROBADO`.

**Qué falta implementar o corregir (por prioridad):**
1. H-01: proyecciones `artifacts`/`evaluations`/contexto E10 para RUN de `python -m src.train` (o consulta SCC desde `train_execution_sessions.verification`).
2. H-02/H-07: vincular TRAIN de CLI a `campaign_attempts`/miembros y omitir miembros ya verificados.
3. H-03: extracción de embeddings por capa desde checkpoints y `sample_id` gobernados; PCA/UMAP/CKA como evidencia derivada con contrato propio.
4. Proyección ruta→`sample_id` de predicciones TRAIN-VAL (Q11), calibración (ECE/Brier) y bootstrap por paciente integrados a SCC.
5. Opcional: EXPLAIN sobre TEST y bloqueo de candidatos antes de TEST (H-06).

**Confirmaciones:** no se ejecutaron operaciones científicas; no se modificaron datos operativos, código, esquema, pesos ni datasets;
no se realizó commit ni push. SCC-CAMPAIGN.1B no se inicia sin autorización explícita.
