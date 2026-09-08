# Fase 0 — Resolución "cell" vs. "microscopy" (bloqueante, solo lectura)

Fecha: 2026-09-08
Rama: `main` · HEAD `d71bded2` · Alembic head real y en BD: `20260901_01`
Base introspeccionada en vivo: `malaria_experiments` (contenedor `capstone_db`, PostgreSQL 17.9), usuario `julio`.
Método: introspección real de `pg_constraint` / `information_schema` + lectura de las 21 migraciones Alembic + `grep` sobre `backend_api/app`, `malaria_dl_local_project/src`, `malaria_dataset_split_project/src`, `frontend/src`. Ninguna sentencia mutante ejecutada.

> **Conclusión ejecutiva.** "microscopy" y "cell" **no son sistemas independientes ni una
> relación legacy/reemplazo**. Son **dos capas consecutivas de un único pipeline** — el
> análisis de frotis ("cell (análisis de frotis)" del enunciado):
> `microscopy_* = ingesta + control técnico de calidad de la imagen`; `cell_* = detección,
> clasificación y explicabilidad de células dentro de un análisis ya aprobado por el gate de
> calidad`. Ambas capas se introdujeron en la misma cadena continua de migraciones los días
> 2026-07-27/28, nunca fueron vaciadas, renombradas ni sustituidas, y **hoy reciben
> escritura en paralelo** (última fila 2026-09-04 13:55 en `microscopy_analysis_runs` y en
> `cell_classification_runs`). ⇒ El flag `--cell` debe purgar **ambas capas** (25 tablas).
> No hace falta un flag `--microscopy`. **Sí** hay una decisión abierta sobre las 6 tablas
> `scientific_validation_*` (ver §7).

---

## 1. Inventario de tablas con "cell" o "microscopy" en el nombre (introspección real)

14 tablas BASE TABLE en `public` contienen "cell" o "microscopy":

| Tabla | Capa | Migración que la creó | Fecha |
|---|---|---|---|
| `microscopy_images` | ingesta | `20260727_01_scientific_data_model` | 2026-07-27 |
| `microscopy_analysis_runs` | quality gate | `20260727_03_microscopy_quality_gate` | 2026-07-27 |
| `microscopy_analysis_run_images` | quality gate | `20260727_03_microscopy_quality_gate` | 2026-07-27 |
| `microscopy_analysis_events` | quality gate | `20260727_03_microscopy_quality_gate` | 2026-07-27 |
| `cell_detection_runs` | detección | `20260727_05_cell_detection_and_review` | 2026-07-28 |
| `cell_detections` | detección | `20260727_05_cell_detection_and_review` | 2026-07-28 |
| `cell_detection_events` | detección | `20260727_05_cell_detection_and_review` | 2026-07-28 |
| `cell_crops` | detección | `20260727_05_cell_detection_and_review` | 2026-07-28 |
| `cell_classification_runs` | clasificación | `20260728_01_cell_classification_and_explainability` | 2026-07-28 |
| `cell_classification_inputs` | clasificación | `20260728_01_cell_classification_and_explainability` | 2026-07-28 |
| `cell_classification_events` | clasificación | `20260728_01_cell_classification_and_explainability` | 2026-07-28 |
| `cell_classification_reviews` | clasificación | `20260728_01_cell_classification_and_explainability` | 2026-07-28 |
| `cell_predictions` | clasificación | `20260728_01_cell_classification_and_explainability` | 2026-07-28 |
| `cell_explanations` | clasificación | `20260728_01_cell_classification_and_explainability` | 2026-07-28 |

### Dependientes por FK cuyo nombre NO contiene "cell" ni "microscopy"

Recorriendo `pg_constraint contype='f'` hacia y desde las 14 anteriores:

| Tabla | Rol | Migración | Fecha | Relación con el pipeline |
|---|---|---|---|---|
| `research_subjects` | jerarquía de espécimen | `20260727_01` | 2026-07-27 | padre raíz: sujeto → caso → muestra → slide → imagen |
| `scientific_cases` | jerarquía de espécimen | `20260727_01` | 2026-07-27 | `subject_id → research_subjects` |
| `blood_samples` | jerarquía de espécimen | `20260727_01` | 2026-07-27 | `case_id → scientific_cases` |
| `smear_slides` | jerarquía de espécimen | `20260727_01` | 2026-07-27 | `sample_id → blood_samples`; `microscopy_images.slide_id → smear_slides` |
| `image_ingestion_batches` | ingesta | `20260727_02_secure_image_ingestion` | 2026-07-27 | agrupa imágenes por lote; `microscopy_analysis_runs.ingestion_batch_id → image_ingestion_batches` |
| `image_quality_assessments` | quality gate | `20260727_03` | 2026-07-27 | `analysis_run_id → microscopy_analysis_runs` |
| `quality_gate_decisions` | quality gate | `20260727_03` | 2026-07-27 | `analysis_run_id → microscopy_analysis_runs` |
| `quality_assessment_queue_items` | quality gate | `20260727_04_quality_assessment_queue` | 2026-07-28 | `analysis_run_id → microscopy_analysis_runs` |
| `image_connected_components` | detección | `20260727_05` | 2026-07-28 | `detection_run_id → cell_detection_runs` |
| `scientific_reviews` | detección | `20260727_05` | 2026-07-28 | `entity_id → cell_detections` (revisión humana append-only) |
| `smear_analysis_summaries` | clasificación | `20260728_01` | 2026-07-28 | `(classification_run_id, analysis_run_id, detection_run_id) → cell_classification_runs` (resultado agregado del frotis) |

**Total del subsistema: 25 tablas.** Coincide exactamente con `DELETE_ORDER` de
`scripts/storage/reset_smear_analysis.py:46-56` (herramienta previa ya revisada) y con las 25
tablas del inventario `docs/engineering/smear_storage_legacy_inventory.md`.

### Dependientes por FK de segundo nivel (capa de validación humana — decisión abierta, §7)

| Tabla | Migración | Fecha | FK hacia el pipeline |
|---|---|---|---|
| `scientific_validation_sessions` | `20260810_01_scientific_validation_sessions` | 2026-08-10 | (sólo `users`) — raíz de la capa |
| `scientific_validation_images` | `20260810_01` | 2026-08-10 | `microscopy_image_id → microscopy_images` |
| `scientific_validation_detection_runs` | `20260810_01` | 2026-08-10 | `detection_run_id → cell_detection_runs` |
| `scientific_validation_classification_runs` | `20260810_01` | 2026-08-10 | `classification_run_id → cell_classification_runs` |
| `scientific_validation_annotations` | `20260810_02_scientific_validation_annotations` | 2026-08-10 | `cell_detection_id → cell_detections`, `analysis_run_id → microscopy_analysis_runs`, `sample_id → blood_samples` |
| `scientific_validation_annotation_events` | `20260810_02` | 2026-08-10 | `annotation_id → scientific_validation_annotations` |

Todas las FK anteriores son `ON DELETE RESTRICT` (`confdeltype='r'`).

---

## 2. Datos activos hoy (conteo real + rango temporal)

| Tabla | Filas | `min(created_at)` | `max(created_at)` |
|---|---:|---|---|
| `research_subjects` | 53 | | |
| `scientific_cases` | 53 | | |
| `blood_samples` | 53 | | |
| `smear_slides` | 53 | | |
| `image_ingestion_batches` | 53 | | |
| `microscopy_images` | 59 | 2026-07-27 17:47 | **2026-09-04 13:55** |
| `microscopy_analysis_runs` | 50 | 2026-07-28 17:39 | **2026-09-04 13:55** |
| `microscopy_analysis_run_images` | 52 | | |
| `image_quality_assessments` | 52 | | |
| `microscopy_analysis_events` | 258 | | |
| `quality_assessment_queue_items` | 50 | | |
| `quality_gate_decisions` | 4 | | |
| `cell_detection_runs` | 45 | 2026-07-28 19:12 | **2026-09-04 13:55** |
| `image_connected_components` | 3 718 | | |
| `cell_detections` | 2 505 | | |
| `cell_detection_events` | 182 | | |
| `cell_crops` | 2 505 | | |
| `scientific_reviews` | 11 | | |
| `cell_classification_runs` | 41 | 2026-07-28 22:10 | **2026-09-04 13:55** |
| `cell_classification_inputs` | 2 291 | | |
| `cell_predictions` | 1 901 | | |
| `smear_analysis_summaries` | 34 | | |
| `cell_classification_events` | 2 191 | | |
| `cell_classification_reviews` | 4 | | |
| `cell_explanations` | 13 | | |
| **`scientific_validation_*` (las 6)** | **0** | — | — |

**Lectura clave:** `microscopy_*` y `cell_*` tienen exactamente el mismo `max(created_at)`
(2026-09-04 13:55, mismo minuto). No es un subsistema "apagado" y otro "vivo": es un
pipeline único que se ejercita de punta a punta en cada corrida.

---

## 3. Código de backend/app que lee o escribe estas tablas (grep real)

| Módulo | Tablas que toca | Subsistema |
|---|---|---|
| `backend_api/app/repositories/scientific.py` | `research_subjects, scientific_cases, blood_samples, smear_slides, microscopy_images` | cell (ingesta) |
| `backend_api/app/services/image_ingestion.py` | `research_subjects … microscopy_images, image_ingestion_batches` | cell (ingesta) |
| `backend_api/app/services/microscopy_analysis.py`, `image_quality.py`, `quality_queue.py`, `quality_profiles.py` | `microscopy_analysis_runs, microscopy_analysis_run_images, image_quality_assessments, microscopy_analysis_events, quality_assessment_queue_items, quality_gate_decisions` | cell (quality gate) |
| `backend_api/app/repositories/cell_analysis.py` + `services/cell_analysis.py` + `services/detectors/*` | `cell_detection_runs, image_connected_components, cell_detections, cell_detection_events, cell_crops, scientific_reviews` (+ join a `microscopy_*`, `blood_samples`, `research_subjects`) | cell (detección) |
| `backend_api/app/repositories/cell_classification.py` + `services/cell_classification.py` + `services/smear_workflow.py` | `cell_classification_runs, cell_classification_inputs, cell_predictions, cell_classification_events, cell_classification_reviews, cell_explanations, smear_analysis_summaries` (+ join a `deployed_model_versions, stage2_model_publications, model_versions, runs, artifacts`) | cell (clasificación) |
| `backend_api/app/repositories/scientific_validation.py` + `services/scientific_validation.py` | `scientific_validation_*` (+ lectura de `cell_*`, `microscopy_*`, `blood_samples`) | validación (§7) |
| Rutas FastAPI: `routes/scientific.py`, `routes/analysis.py`, `routes/cell_analysis.py`, `routes/cell_classification.py`, `routes/scientific_validation.py` | — registran los servicios anteriores; prefijos `/api/v1/scientific`, `/api/v1/analysis`, `/api/v1/cell-analysis`, `/api/v1/cell-classification` | cell + validación |
| Frontend: `pages/SmearWorkflow.tsx`, `SmearUpload.tsx`, `SmearAnalysisHistory.tsx`, `CellReview.tsx` (rutas `/frotis/*`) | consumen esos endpoints; `/frotis/historial/{id}` usa `microscopy_analysis_runs.id` | cell |

Ningún servicio de `malaria_dl_local_project` (subsistema **run**) ni de
`malaria_dataset_split_project` (subsistema **dataset**) escribe en las 25 tablas del
pipeline de frotis.

---

## 4. ¿Alguna migración posterior vacía / renombra / reemplaza estas tablas?

Revisadas las 21 migraciones. `grep -E "RENAME|DROP TABLE|TRUNCATE|DELETE FROM"`:

- Ningún `DROP TABLE` / `TRUNCATE` / `DELETE FROM` de estas tablas en ninguna ruta
  `upgrade()`. Los `DROP TABLE` que aparecen están todos en `downgrade()`.
- **`20260728_01` línea 14:** `ALTER VIEW cell_predictions RENAME TO legacy_cell_predictions;`
  seguido de `CREATE TABLE cell_predictions (…)`. Es decir: en el baseline SQL histórico
  existía una **vista** `cell_predictions` (proyección sobre `predictions`, el subsistema
  run / inferencia subida). Los propios autores del esquema **desambiguaron el nombre a
  mano**: apartaron la vista legacy y le dieron el nombre `cell_predictions` a la tabla
  clínica real. Hoy `legacy_cell_predictions` sigue siendo una vista (0 filas) y **no es
  una tabla** — ningún flag de purga la toca.
- Migraciones posteriores a `20260728_03` que mencionan el dominio:
  `20260810_01/02` añaden la capa `scientific_validation_*` **encima** (aditivo, sin tocar
  filas de las 25); el resto (`20260811`, `20260812`, `20260829`, `20260901`) son de los
  subsistemas dataset y run.

⇒ **No hay reemplazo ni deprecación.** La única "sustitución" histórica fue vista→tabla
para `cell_predictions`, hace >1 año, y refuerza que el nombre "cell" pertenece
inequívocamente al dominio clínico de frotis.

---

## 5. Respuesta explícita a la pregunta de la Fase 0

**¿"cell" y "microscopy" son el mismo subsistema en dos momentos de su evolución, capas
distintas del mismo flujo, o sistemas independientes?**

→ **Capas distintas y consecutivas del mismo flujo.** Un único subsistema ("análisis de
frotis") con un pipeline de cuatro etapas sobre la misma jerarquía de espécimen:

```
research_subjects → scientific_cases → blood_samples → smear_slides
        │
        ▼
[ingesta]      image_ingestion_batches → microscopy_images
        │
        ▼
[quality gate] microscopy_analysis_runs → microscopy_analysis_run_images
               → image_quality_assessments / microscopy_analysis_events
               → quality_gate_decisions / quality_assessment_queue_items
        │
        ▼
[detección]    cell_detection_runs → image_connected_components → cell_detections
               → cell_crops / cell_detection_events / scientific_reviews
        │
        ▼
[clasificación] cell_classification_runs → cell_classification_inputs → cell_predictions
               → cell_explanations / cell_classification_events / cell_classification_reviews
               → smear_analysis_summaries   (resultado agregado del frotis)
```

Cadena de FK que lo demuestra:
`microscopy_images → microscopy_analysis_runs → cell_detection_runs → cell_classification_runs → smear_analysis_summaries`.

**¿Hay un legacy del otro?** No. Evidencia:
1. Cadena de migraciones **continua y sin bifurcaciones** `20260727_01 → 20260727_02 →
   20260727_03 → 20260727_04 → 20260727_05 → 20260728_01`, todas del mismo autor, en 48 h.
2. Cero `DROP`/`TRUNCATE`/`RENAME` de estas tablas en `upgrade()` de ninguna migración.
3. Escritura activa **simultánea** en ambas capas (mismo `max(created_at)` al minuto).
4. El backend usa las dos capas en el mismo servicio (`smear_workflow.py`,
   `cell_classification.py` hace `JOIN` de `cell_*` con `microscopy_*`).
5. "microscopy" **no** es un sinónimo desafortunado de "cell": nombra una capa real y
   necesaria (la imagen y su control de calidad). Pero pertenece a la misma unidad de
   purga porque purgar la clasificación de células sin su capa de imagen/calidad — o al
   revés — deja huérfanos sin sentido clínico y viola las FK `RESTRICT` internas.

---

## 6. Lista definitiva de tablas para `--cell` (25) y orden de borrado

Orden hijo→padre (idéntico a `reset_smear_analysis.py:DELETE_ORDER`, ya revisado; se
reutiliza el **orden**, no su lógica de storage):

```
 1. cell_explanations
 2. cell_classification_reviews
 3. cell_classification_events
 4. smear_analysis_summaries
 5. cell_predictions
 6. cell_classification_inputs
 7. cell_classification_runs          (autorreferencia retry_of_run_id → borrado por conjunto completo, OK)
 8. scientific_reviews
 9. cell_crops
10. cell_detection_events
11. cell_detections
12. image_connected_components
13. cell_detection_runs
14. quality_gate_decisions
15. quality_assessment_queue_items
16. microscopy_analysis_events
17. image_quality_assessments
18. microscopy_analysis_run_images
19. microscopy_analysis_runs
20. microscopy_images
21. image_ingestion_batches
22. smear_slides
23. blood_samples
24. scientific_cases
25. research_subjects
```

**Justificación por bloque:**
- 1–7 (clasificación): dependen de `cell_classification_runs`, que depende de
  `cell_detection_runs`. `smear_analysis_summaries` y `cell_predictions` antes que sus
  padres.
- 8–13 (detección): `scientific_reviews`, `cell_crops`, `cell_detections`,
  `image_connected_components` cuelgan de `cell_detection_runs` (directa o vía claves
  compuestas). `cell_detection_runs` depende de `microscopy_analysis_runs`.
- 14–19 (quality gate): todo cuelga de `microscopy_analysis_runs`;
  `image_quality_assessments` referencia además `microscopy_analysis_run_images` (FK
  compuesta) → va antes.
- 20–21 (ingesta): `microscopy_images` y `image_ingestion_batches` se referencian
  mutuamente de forma parcial; `microscopy_images.ingestion_batch_id → image_ingestion_batches`
  ⇒ imágenes antes que lotes.
- 22–25 (espécimen): slide → muestra → caso → sujeto.

**Disparadores que bloquean el DELETE** (14 en las tablas objetivo + `audit_events`):
`reject_cell_analysis_row_mutation`, `reject_cell_classification_row_mutation`,
`protect_cell_detection_run_identity`, `protect_cell_classification_run`,
`protect_cell_explanation`. Se neutralizan **dentro de la transacción** con
`ALTER TABLE … DISABLE TRIGGER USER` / `ENABLE TRIGGER USER` (requiere ser owner de la
tabla; `current_user = julio` lo es), tal como hace `reset_smear_analysis.py:966-977`.

**`audit_events` NO se purga bajo `--cell`** (ni bajo ningún flag). Es la traza de
auditoría de seguridad/clínica; su borrado selectivo pertenece a una herramienta de
mandato distinto (el `reset_smear_analysis.py` sólo borra filas de auditoría de recursos
clínicos concretos bajo su mandato estrecho, preservando los eventos de seguridad). Para
`purge.py` la recomendación es **no tocar `audit_events`**.

---

> **DECISIONES CONFIRMADAS (2026-09-08, tras la Fase 0):**
> 1. `scientific_validation_*` → **Opción A**: se purgan DENTRO de `--cell`. No hay cuarto
>    flag. `--cell` = 31 tablas.
> 2. Modelo transaccional → **una transacción por subsistema** (no una sola global). El
>    orden global sigue siendo cell → run → dataset y el chequeo FK cruzado es previo a
>    cualquier transacción.
> Estas decisiones ya están implementadas en `scripts/db/purge.py`. El resto de esta
> sección documenta el análisis que llevó a ellas.

## 7. ¿Hace falta un flag adicional? — `scientific_validation_*` (resuelto: Opción A)

Las 6 tablas `scientific_validation_*`:

- **No** son dataset, **no** son run, y **no** nacieron con la familia de migraciones de
  frotis: son una **capa de validación por experto humano** añadida 2 semanas después
  (`20260810_01/02`, 2026-08-10).
- Son **dependientes duros por FK `RESTRICT`** de `--cell` (`microscopy_images`,
  `cell_detection_runs`, `cell_classification_runs`, `cell_detections`,
  `microscopy_analysis_runs`, `blood_samples`).
- **Hoy están vacías (0 filas)** → para la primera purga real es indiferente, pero el
  script debe decidir su tratamiento de forma explícita para no romperse en el futuro.

**Opción A (recomendada): incluirlas dentro de `--cell`.**
Una anotación de validación sobre una detección que ya no existe no tiene sentido. El flag
`--cell` purgaría primero las 6 (hijas) y luego las 25. Orden:
`scientific_validation_annotation_events → scientific_validation_annotations →
scientific_validation_classification_runs → scientific_validation_detection_runs →
scientific_validation_images → scientific_validation_sessions →` (luego las 25).
Disparadores a neutralizar: `protect_validation_snapshot`, `protect_validation_annotation`,
`prevent_validation_membership_mutation`, `prevent_validation_annotation_event_mutation`.

**Opción B: cuarto flag `--validation`.**
Sólo si el equipo considera la validación por experto un activo independiente que debe
sobrevivir a una purga de frotis. En ese caso `--cell` **sin** `--validation` debe
**fallar con mensaje claro** ("hay N filas en scientific_validation_* que referencian
tablas de --cell; añada --validation") en vez de borrar en cascada — exactamente el patrón
de `reset_smear_analysis.py:846-871`, que preserva estas tablas y **rechaza** el reset si
enlazan datos clínicos.

`reset_smear_analysis.py` eligió preservar+rechazar porque su mandato es explícitamente
"narrowly-scoped smear-analysis". Un flag `--cell` de propósito general tiene otro mandato,
por eso la recomendación por defecto es **A**.

> **Confirmado: Opción A.** `scientific_validation_*` se purga dentro de `--cell`. Sin
> cuarto flag. Implementado en `scripts/db/purge.py` (`CELL_TABLES`).

---

## 8. Mapa de los otros dos subsistemas (para el diseño de `--dataset` y `--run`)

### `--dataset` — descargas de `tensorflow_datasets` + versionado/registro (13 tablas)
Código dueño: `malaria_dataset_split_project/src` (splitting, materialization, freeze) +
`backend_api/app/services/governed_datasets.py`, `dataset_browser.py`, rutas `dataset.py`,
`dataset_versions.py`.

| Tabla | Origen | Filas |
|---|---|---:|
| `datasets` | baseline SQL 001 (stamp `20260726_00`) | 2 |
| `dataset_splits` | baseline SQL 001 | 0 (modelo de split legacy, superado) |
| `dataset_split_images` | baseline SQL 012 · **PK = `image_id`** | 55 116 |
| `dataset_versions` | `20260811_01` | 1 |
| `dataset_version_sources` | `20260811_01` | 1 |
| `clinical_identities` | `20260811_01` (`dataset_id → datasets`) | 201 |
| `dataset_source_records` | `20260811_01` | 27 558 |
| `identity_evidence` | `20260811_01` | 27 558 |
| `dataset_split_assignments` | `20260811_01` | 27 558 |
| `dataset_split_statistics` | `20260811_01` | 1 |
| `dataset_split_validation_checks` | `20260811_01` | 12 |
| `dataset_materializations` | `20260811_01` | 1 |
| `dataset_materialization_activations` | `20260811_01` | 0 |

Disparadores de borrado: `protect_frozen_dataset_assignments` (DELETE),
`protect_frozen_dataset_version_sources` (DELETE).

### `--run` — ejecuciones de modelos (entrenamiento/evaluación/explicabilidad/lineage) (~28 tablas)
Código dueño: `malaria_dl_local_project/src` + `backend_api/app/routes/runs.py`,
`governance.py`, `predictions.py`, `explainability.py`, `analysis.py`, servicios
`run_lineage.py`, `lineage_children.py`, `productive_model.py`.

`experiments, runs, models, model_versions, run_metrics, training_history,
confusion_matrices, classification_reports, predictions, artifacts, explainability_results,
execution_logs, errors, environment_packages, synthetic_data_runs, run_dataset_images,
run_io_records, run_clinical_metrics, run_checkpoint_policy, run_threshold_calibration,
run_image_predictions, run_lineage, model_governance_backfill_audit,
deployed_model_versions, run_model_deployments, stage2_model_publications,
stage2_model_publication_events, image_analysis_jobs`.

Filas destacadas: `predictions` 99 567 · `run_image_predictions` 98 364 ·
`run_dataset_images` **825 048** · `artifacts` 4 007 · `explainability_results` 3 600.
Disparadores append-only: `model_governance_backfill_audit`, `stage2_model_publication_events`.

Fuera de todo flag (bookkeeping de sistema): `alembic_version`, `schema_migrations`
(ledger pre-Alembic, 23 filas), `legacy_cell_predictions` (vista).

---

## 9. Dependencias FK cruzadas entre subsistemas (crítico para la Fase 1)

Todas `ON DELETE RESTRICT` salvo lo indicado. Sentido: **hijo → padre**.

### 9.1 run → dataset (tablas de run que apuntan a tablas de dataset)
| Hijo (run) | Padre (dataset) | `ON DELETE` |
|---|---|---|
| `runs.dataset_version_id` | `dataset_versions` | RESTRICT |
| `run_io_records.dataset_version_id` | `dataset_versions` | RESTRICT |
| `run_io_records.dataset_materialization_id` | `dataset_materializations` | RESTRICT |
| `predictions.source_image_id` | `dataset_split_images` | RESTRICT |
| `image_analysis_jobs.source_image_id` | `dataset_split_images` | RESTRICT |
| `run_dataset_images.image_id` | `dataset_split_images` | **CASCADE** |
| `runs.dataset_id` | `datasets` | SET NULL |
| `predictions.dataset_id` | `datasets` | SET NULL |
| `run_image_predictions.image_id` | `dataset_split_images` | SET NULL |
| `synthetic_data_runs.source_dataset_id` | `datasets` | SET NULL |

⇒ **`--dataset` sin `--run`**: el `DELETE` de `dataset_versions` / `dataset_materializations`
/ `dataset_split_images` **fallará** por las FK `RESTRICT` desde filas de run. El script
debe detectar filas de run que referencian el conjunto dataset y **abortar con
"se requiere también --run"**, nunca cascadear.
⇒ **`--run` sin `--dataset`**: OK.

### 9.2 cell → run (tablas de cell que apuntan a tablas de run/modelo)
| Hijo (cell) | Padre (run) | `ON DELETE` |
|---|---|---|
| `cell_classification_runs.(production_model_id, model_registry_id)` | `deployed_model_versions` | RESTRICT |
| `cell_classification_runs.(stage2_publication_id, model_registry_id)` | `stage2_model_publications` | RESTRICT |

⇒ **`--run` sin `--cell`**: el `DELETE` de `deployed_model_versions` /
`stage2_model_publications` **fallará** por FK `RESTRICT` desde `cell_classification_runs`.
El script debe detectar y **abortar con "se requiere también --cell"**.
⇒ **`--cell` sin `--run`**: OK (se borra el hijo `cell_classification_runs`, no el padre).

### 9.3 cell ↔ dataset
**Ninguna FK directa.** Subsistemas independientes entre sí.

### 9.4 users
`users` es padre (`RESTRICT`) de decenas de tablas de los tres subsistemas
(`created_by`, `requested_by`, `actor_user_id`, …). Como **nunca** se borran filas de
`users`, estas FK no imponen ninguna restricción sobre la purga. `users`, `roles`,
`user_roles` **no aparecen como flag y no se tocan bajo ninguna combinación**.

### 9.5 Matriz de combinaciones

| Invocación | ¿Válida? | Orden de purga | Falla si… |
|---|---|---|---|
| `--cell` | siempre | (val.§7 →) 25 tablas cell | — |
| `--run` | condicional | 28 tablas run | existen `cell_classification_runs` con `production_model_id`/`stage2_publication_id` ⇒ pide `--cell` |
| `--dataset` | condicional | 13 tablas dataset | existen filas run apuntando al conjunto dataset ⇒ pide `--run` |
| `--run --cell` | siempre | cell → run | — |
| `--run --dataset` | siempre | run → dataset | — |
| `--cell --dataset` (sin run) | condicional | cell → dataset | filas run apuntando a dataset ⇒ pide `--run` |
| `--cell --run --dataset` | siempre | cell → run → dataset | — |

---

## 10. Recomendación de diseño para la Fase 1 (sujeto a confirmación del §7)

1. **Flags:** `--dataset`, `--run`, `--cell` (+ `--validation` **sólo** si se elige Opción B).
   `users` nunca es flag.
2. **Chequeo previo (pre-flight, fuera de transacción):** para cada flag pedido, verificar
   que no haya FK entrantes `RESTRICT` desde un subsistema **no** pedido; si las hay,
   abortar con el flag exacto que falta. Nunca cascada entre subsistemas.
3. **Transacción:** **una por subsistema** (decisión confirmada), con orden global
   `cell → run → dataset`. Cada subsistema confirma por separado; si uno posterior falla,
   los anteriores quedan confirmados y el script lo informa explícitamente
   (`subsistemas ya confirmados y NO revertidos: …`). Dentro de cada transacción:
   `SET LOCAL session_replication_role = replica` (desactiva RI + triggers append-only;
   requiere superusuario — el owner canónico lo es) → `DELETE FROM` explícito por tabla en
   orden hijo→padre (los `ON DELETE CASCADE` tampoco disparan bajo replica, por eso el
   borrado es explícito y contado) → verificación de conteo cero → `COMMIT`.
4. **`--dry-run` por defecto de facto:** sin `--yes` explícito, sólo se reportan conteos por
   tabla; ningún `DELETE`.
5. **Log** (igual que `scripts/db/status.sh` / `reset_smear_analysis.py`): timestamp, flags
   usados, identidad de BD (`current_database`, `current_user`), Alembic `version_num`,
   conteo por tabla eliminado, antes del `COMMIT`.
6. **Guardas reutilizadas del repo:** verificación de identidad de BD contra `DATABASE_URL`
   canónico (`db:5432`), Alembic head == `20260901_01`, esquema `public`, rechazo si hay
   trabajo activo (`runs.status IN ('running','queued',…)`, `*_analysis_runs` en estados no
   terminales, `dataset_versions.status IN ('DRAFT','GENERATED','VALIDATED')`), confirmación
   explícita `--yes` **más** `PURGE_DB_ALLOW_EXECUTION=1` **más** un backup PostgreSQL
   custom-format verificado (`CAPSTONE_VERIFIED_BACKUP` / `--backup`, magic `PGDMP`), igual
   que `reset_smear_analysis.py`. Sin defaults inseguros. **No toca `var/storage/` ni ningún
   archivo:** sólo `DELETE FROM` en PostgreSQL.
7. **`audit_events`, `alembic_version`, `schema_migrations`: intactos** bajo cualquier flag.

---

## 11. Archivos y comandos de evidencia

- Introspección FK: `SELECT … FROM pg_constraint WHERE contype='f'` (175 FK en el esquema).
- Conteos: `query_to_xml` por tabla sobre la lista de las 76 tablas relevantes.
- Disparadores: `information_schema.triggers` (44 disparadores; 14 de DELETE en el conjunto cell).
- Migraciones: `alembic/versions/*.py` (21 revisiones, head `20260901_01`).
- Inventario previo concordante: `docs/engineering/smear_storage_legacy_inventory.md`,
  `scripts/storage/reset_smear_analysis.py:46-56` (`DELETE_ORDER`).
