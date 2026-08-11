# Auditoría PostgreSQL y contratos TRAIN/EVALUATE — SPLIT 1C

## 1. Objetivo

Determinar cómo integrar posteriormente un dataset versionado y patient-disjoint con
PostgreSQL, TRAIN y EVALUATE, preservando el histórico y los contratos físicos actuales.
La etapa observa, documenta y propone; no migra ni ejecuta ML.

## 2. Evidencia previa de SPLIT 1A/1B

Se toma como base el split físico de 27.558 células bajo
`malaria_dl_local_project/data/malaria_physical_split`, layout `train/val/test`, seed 42,
y la identidad verificada de 201 pacientes. Los 201 aparecen en las tres particiones.

## 3. PostgreSQL actual

Se auditó `malaria_experiments.public` sobre PostgreSQL 17.9 usando una transacción con
`SET TRANSACTION READ ONLY`. Estado observado:

- `alembic_version`: `20260810_05`;
- 37 runs: 12 training, 12 evaluation, 12 explainability y 1 inference;
- fingerprint inicial del schema/conteos auditados:
  `be9c6c3fc5f5538b826eb86ab8454a6faf4f1caea702796290ab2f9056f6bd50`.

También existe `schema_migrations` con 23 filas. El repositorio contiene migrations SQL
incrementales en `db/init`, pero no se encontró configuración/directorio de revisiones
Alembic versionado pese a existir `alembic_version`; esto debe reconciliarse antes de
implementar SPLIT 2. No se ejecutó `upgrade`, `downgrade` ni `stamp`.

## 4. Tablas dataset

| Tabla | Propósito | PK | FK | Filas | Columnas importantes |
|---|---|---|---|---:|---|
| `datasets` | Catálogo lógico | `id` | ninguna | 2 | name, source, version, local_path, checksum, metadata |
| `dataset_splits` | Resumen/configuración por partición | `id` | dataset_id→datasets | 0 | split_name, num_samples, split_strategy, random_seed |
| `dataset_split_images` | Inventario de imágenes físicas | `image_id` | dataset_id→datasets | 27.558 | dataset_dir, split, clase, paths, dimensiones, checksum |
| `run_dataset_images` | Uso imagen↔run | `run_dataset_image_id` | run_id→runs; image_id→dataset_split_images | 396.840 | usage_context, flags train/val/test, relative_path |
| `run_io_records` | Snapshot de entradas/salidas del run | `run_io_id` | run_id→runs | 36 | input_parameters, dataset_metadata, artifacts |

Los dos registros de `datasets` son un dataset físico versionado nominalmente
`physical-split-clinical_v1_parasitized_positive`, con ruta absoluta, y el catálogo
genérico `tfds-malaria-clinical-v1` usado por tracking. Ninguno representa todavía una
entidad científica inmutable `dataset_version` con assignments y validaciones.

## 5. `dataset_split_images`

Columnas reales:

`image_id,dataset_id,dataset_name,dataset_source,dataset_dir,split_name,class_index,class_name,relative_path,absolute_path,filename,original_tfds_label,project_label,label_mapping_version,image_width,image_height,file_size_bytes,checksum_sha256,created_at,updated_at,metadata`.

- PK: `image_id`.
- FK: `dataset_id → datasets(id)` con `ON DELETE SET NULL`.
- Índices: split, class, dataset_dir, dataset_id, relative_path y unique
  `(dataset_dir, relative_path)`.
- Constraints: splits `train/val/validation/test`, índices 0/1 y clases clínicas.

Soporte de campos: split YES; clase YES; label YES; relative path YES; checksum YES
(sin poblar); width/height YES; `tfds_index` NO; `patient_id` NO;
`dataset_version_id` NO; source PARTIAL (`dataset_id`, nombre/source); sample/smear/slide
NO.

Semánticamente representa cada archivo materializado, no una observación científica
independiente de versión. `run_dataset_images` lo relaciona posteriormente con runs. La
fila no declara estado active/historical y su unique por path impide conservar dos
versiones simultáneas bajo la misma ruta/relative path. Puede coexistir con otra versión
si usa otro `dataset_dir`, pero no resuelve versionado estable: soporte **PARTIAL**.

## 6. Migrations y vistas

Migrations relevantes: `001_schema.sql` (datasets, dataset_splits, runs, artifacts),
`002_indexes.sql`, `003_views.sql`, `012_dataset_split_image_tracking.sql`,
`013_dataset_browser_views.sql`, `017_clinical_run_tracking.sql`,
`018_visual_audit_views.sql`, `019_model_execution_parameters.sql`,
`020_max_epochs_release.sql`, `022_run_lineage.sql`,
`023_schema_migrations_baseline.sql`, `024_model_version_artifact_governance.sql`,
`027_model_governance_backfill_constraints.sql`.

Vistas con impacto futuro incluyen `vw_dataset_split_images_summary`,
`vw_dataset_browser_*`, `vw_run_dataset_usage_summary`, `vw_run_io_summary`,
`vw_run_lineage`, `vw_evaluation_lineage`, `vw_model_run_summary` y
`vw_run_dashboard`. Una extensión futura debe conservar columnas actuales y añadir
versionado de forma aditiva.

## 7. Training run persistence

La entidad principal es `runs` filtrada por `run_type='training'`: 12 filas, PK `id`.
Se relaciona con `experiments`, `models` y `datasets`; guarda estado, comando, script,
seed, parameters/execution_parameters JSONB, checkpoint policy y metadata. Complementan
`training_history` (478), `run_metrics` (1.128 globales), `run_clinical_metrics` (24),
`artifacts` (1.886), `model_versions` (24), `run_dataset_images` y `run_io_records`.

Los 12 training tienen `dataset_id` y `dataset_dir` en JSON. No tienen
`dataset_version_id`, metodología de split o grouping. La ruta es demostrable de forma
**INDIRECTA**, no mediante una FK inmutable a materialización/version.

## 8. Evaluation run persistence

La entidad principal también es `runs`, filtrada por `run_type='evaluation'`: 12 filas,
PK `id`. Las 12 tienen `dataset_id` y `dataset_dir`; las 12 están enlazadas a un training
en `run_lineage` mediante `evaluates_checkpoint_from`. `model_versions` y el checkpoint
conectan el modelo evaluado con el training. Métricas, predicciones, artefactos y uso de
imágenes se almacenan en tablas compartidas.

No existe `dataset_version_id` ni un `test_dataset_id` específico; `dataset_id` es
genérico. Tampoco se registra metodología/grouping en los 12 runs actuales.

## 9. Dataset lineage actual

PostgreSQL cataloga dataset, inventario físico y uso por run, pero TRAIN/EVALUATE no
resuelven sus inputs desde la BD. La FK `runs.dataset_id` apunta al catálogo genérico
TFDS y los JSON conservan `dataset_dir`; el inventario físico está en otro registro
`datasets`. Por tanto, la demostración exacta de una versión científica requiere
reconciliación y un futuro vínculo explícito.

## 10. Contrato TRAIN

- Entry point: `python -m src.train` → `malaria_dl.training.trainer.main`.
- Orquestador: `run_train_all_models.py`.
- Loader: `malaria_dl/data/loaders.py::{load_malaria_splits,load_physical_split}`.
- Argumentos: `--data-source` default `physical`; `--dataset-dir` default
  `data/malaria_physical_split`.
- Resolución: **FILESYSTEM**. PostgreSQL sólo recibe tracking opcional posterior.
- Fit: `ds_train`; validation: `ds_val`.
- Test no participa en fit, checkpoint selection, early stopping ni threshold selection.
  El comando de orquestación puede solicitar una evaluación final única de `ds_test`
  después de seleccionar el checkpoint mediante validation.
- Checkpoint/early stopping: métricas `val_*`, incluyendo F2, recall/sensitivity y
  specificity calculadas sobre `val`.
- Threshold calibration: `val`; `test` está explícitamente bloqueado.
- Probability calibration (temperature scaling): `val`; el CLI valida/bloquea `test`.

## 11. Contrato EVALUATE

- Entry point: `python -m src.evaluate` → `malaria_dl.evaluation.evaluator.main`.
- Orquestador: `run_evaluate_all_trainings.py`.
- Loader compartido: `load_malaria_splits`; consume únicamente el tercer retorno,
  `ds_test`.
- Argumentos compartidos: `--data-source physical` y `--dataset-dir` default
  `data/malaria_physical_split`.
- Resolución: **FILESYSTEM**; la BD aporta tracking/lineage, no selección de imágenes.
- Test: `<dataset_root>/test` del mismo root usado por TRAIN.

## 12. Loader y layout

`resolve_physical_dataset_dir` resuelve rutas relativas contra
`malaria_dl_local_project`. `validate_physical_split` exige `metadata.json`, conteos
consistentes y exactamente:

```text
train/{uninfected,parasitized}
val/{uninfected,parasitized}
test/{uninfected,parasitized}
```

`image_dataset_from_directory` obtiene etiquetas de `CLASS_NAMES =
[uninfected, parasitized]`. TRAIN y EVALUATE comparten root y loader.

## 13. Contrato de ruta física

La ruta activa puede conservarse exactamente. Referencias relevantes están concentradas
en settings/loaders, ambos orquestadores, scripts create/register, tracking/registry,
tests de arquitectura/carga/registry y el browser backend. El layout también debe
preservarse; cambiar `val` a `validation` rompería el loader.

## 14. Estado BD ↔ filesystem

BD: 27.558 filas bajo el mismo `dataset_dir`, distribuidas 22.046/2.756/2.756.
Filesystem: 27.558 imágenes. `CURRENT_DB_FILESYSTEM_COUNT_MATCH=YES` por conteos y
particiones; esto no reemplaza una reconciliación futura por versión/checksum.

Las 27.558 filas contienen `relative_path` y `absolute_path`, y `dataset_dir` es absoluto.
La estrategia actual es **MIXED_ABSOLUTE_AND_RELATIVE**, con baja portabilidad.

## 15. Checksums

Columna `checksum_sha256`; 0 filas pobladas y 27.558 NULL. El código usa SHA-256 cuando
se ejecuta registro con `compute_checksum=True`, pero no se calcularon hashes en 1C.

## 16. Historicidad/versionado actual

`datasets.version` y `dataset_splits` ofrecen una base reutilizable, pero
`dataset_splits` está vacío y no hay identidad, assignments, freeze, estado activo,
validaciones o FK estable desde runs/imágenes a una versión. El soporte de múltiples
versiones es **PARTIAL**. El unique path impide legacy+v1 bajo el mismo root en paralelo.

## 17. Matriz REUSE / EXTEND / NEW

| Componente | Estado actual | Decisión | Motivo |
|---|---|---|---|
| `dataset_split_images` | Inventario físico útil | EXTEND | Vincular versión/observación; conservar compatibilidad |
| `runs` training | Tracking maduro | EXTEND | FK explícita a dataset_version |
| `runs` evaluation | Tracking + lineage | EXTEND | FK a versión/test assignment |
| artifact tracking | Checksums/paths existentes | REUSE | Ya enlaza artefactos con runs |
| dataset path config | CLI + constant | EXTEND | Resolver activación sin hardcode nuevo |
| physical split loader | Contrato estable | REUSE | Ya consume layout requerido |
| dataset source | `datasets` parcial | EXTEND | Provenance/version/fingerprint fuertes |
| dataset version | Sólo string nominal | NEW ENTITY REQUIRED | Inmutabilidad, freeze y método |
| clinical identity | Ausente | NEW ENTITY REQUIRED | Patient/source/sample evidence |
| split assignments | Ausente | NEW ENTITY REQUIRED | Assignment versionado por paciente |
| validation checks | Ausente | NEW ENTITY REQUIRED | Gates anti-leakage/integridad |
| split statistics | JSON parcial | NEW ENTITY REQUIRED | Estadísticas reproducibles por versión |
| physical materialization | Sólo paths | EXTEND | Estado, manifest y activación trazables |

Se recomienda evolución aditiva, no reemplazar tablas históricas.

## 18. Integraciones futuras necesarias

Targets mínimos de `dataset_version_id`: `runs` (training/evaluation/calibration),
`dataset_split_images` o su entidad de assignment/materialización, `run_io_records` y
la relación de test evaluado. `run_dataset_images` puede heredar la versión por
`image_id`, pero conviene una constraint verificable.

El loader debe seguir recibiendo `dataset_dir`; antes de iniciar un run, SPLIT 2 deberá
resolver una versión activa, validar/fijar su manifest y persistir la FK. Después se
mantiene el flujo TensorFlow por filesystem.

Activación recomendada: materializar en directorio versionado de staging, validar,
promover mediante reemplazo atómico/controlado del root activo conservando
`malaria_physical_split`, y registrar la materialización activa. No se implementó.

## 19. Riesgos de compatibilidad

- Dos catálogos `datasets` describen aspectos distintos del mismo material.
- Paths absolutos persistidos reducen portabilidad.
- Unique `(dataset_dir,relative_path)` no conserva generaciones sucesivas en el root.
- Vistas y backend asumen el inventario/ruta legacy.
- `tfds_index` y Patient-ID no están en BD.
- Estado Alembic presente sin revisions locales visibles.
- El loader carga los tres datasets incluso cuando EVALUATE sólo usa test.

Tests existentes relevantes: `test_physical_dataset_split`, `test_data_loading`,
`test_canonical_architecture`, `test_dataset_registry`, `test_tracking_integration`,
`test_run_evaluate_all_trainings`, `test_threshold_calibration`,
`test_run_lineage_migration`, `test_dataset_browser_*`. Protegen estructura, mapping,
conteos, rutas, registro, calibration sobre val y lineage evaluation→training.

## 20. Conclusiones y requisitos para SPLIT 1D

- Reutilizar loader/layout, runs, artifacts, model versions, run lineage e inventario.
- Extender catálogo source, runs, imágenes, configuración y materialización.
- Crear entidades explícitas de dataset version, identidad/evidencia, assignments,
  validaciones y estadísticas.
- Preservar histórico enlazándolo aditivamente a una versión legacy; nunca reescribirlo.
- Mantener root activo y nombres `train/val/test` + clases actuales.
- Resolver en 1D cardinalidades, estados FROZEN/ACTIVE, estrategia exacta de activación,
  política de backfill legacy y reconciliación de los dos registros `datasets`.

