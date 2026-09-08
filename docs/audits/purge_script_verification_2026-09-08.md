# Fase 2 — Verificación de scripts/db/purge.py

Fecha: 2026-09-08 · Alembic head `20260901_01` · base `malaria_experiments` (contenedor `capstone_db`).
Entorno: `docker compose exec backend python /app/scripts/db/purge.py` (imagen reconstruida
con la línea `COPY scripts/db/purge.py` del Dockerfile).

**No se ejecutó ninguna purga real.** Todo lo de abajo es `--dry-run` (modo por defecto sin
`--yes`) + tests. La ejecución real se autoriza por separado tras revisar la Fase 0.

---

## 1. Dry-run por flag individual

### `--cell` (31 tablas, 16 231 filas)

| # | Tabla | Filas |
|---:|---|---:|
| 1 | cell_classification_events | 2191 |
| 2 | cell_classification_reviews | 4 |
| 3 | cell_detection_events | 182 |
| 4 | cell_explanations | 13 |
| 5 | cell_predictions | 1901 |
| 6 | cell_classification_inputs | 2291 |
| 7 | cell_crops | 2505 |
| 8 | image_quality_assessments | 52 |
| 9 | microscopy_analysis_events | 258 |
| 10 | quality_assessment_queue_items | 50 |
| 11 | quality_gate_decisions | 4 |
| 12 | scientific_reviews | 11 |
| 13 | scientific_validation_annotation_events | 0 |
| 14 | scientific_validation_annotations | 0 |
| 15 | cell_detections | 2505 |
| 16 | image_connected_components | 3718 |
| 17 | microscopy_analysis_run_images | 52 |
| 18 | scientific_validation_classification_runs | 0 |
| 19 | scientific_validation_detection_runs | 0 |
| 20 | scientific_validation_images | 0 |
| 21 | microscopy_images | 59 |
| 22 | scientific_validation_sessions | 0 |
| 23 | smear_analysis_summaries | 34 |
| 24 | cell_classification_runs | 41 |
| 25 | cell_detection_runs | 45 |
| 26 | microscopy_analysis_runs | 50 |
| 27 | image_ingestion_batches | 53 |
| 28 | smear_slides | 53 |
| 29 | blood_samples | 53 |
| 30 | scientific_cases | 53 |
| 31 | research_subjects | 53 |
| | **total_rows_in_scope** | **16 231** |

Orden hijo→padre verificado: hojas (`*_events`, `*_reviews`, `cell_explanations`,
`cell_predictions`) primero; raíces de espécimen (`research_subjects`, `scientific_cases`)
al final. Coincide con `smear_storage_legacy_inventory.md` (16 231 IDs clínicos).

### `--run` — **RECHAZADO en solitario** (comportamiento esperado)

```
PURGE_REFUSED: el subsistema 'cell' tiene filas que dependen del conjunto solicitado;
añada el flag --cell o no será posible purgar sin romper integridad.
```

Causa: `cell_classification_runs` (41 filas, subsistema cell) referencia
`deployed_model_versions` / `stage2_model_publications` (subsistema run) con FK `RESTRICT`.
El chequeo previo lo detecta antes de abrir ninguna transacción. ✔️ Requisito Fase 1 §2.

### `--dataset` — **RECHAZADO en solitario** (comportamiento esperado)

```
PURGE_REFUSED: el subsistema 'run' tiene filas que dependen del conjunto solicitado;
añada el flag --run o no será posible purgar sin romper integridad.
```

Causa: `runs`, `predictions`, `image_analysis_jobs` (subsistema run) referencian
`dataset_versions` / `dataset_split_images` (subsistema dataset) con FK `RESTRICT`. ✔️

---

## 2. Dry-run por combinación

| Invocación | Resultado | Filas en alcance |
|---|---|---:|
| `--run --cell` | OK · orden `cell → run` | 1 051 124 |
| `--run --dataset` | RECHAZADO → falta `--cell` (cell_classification_runs → run) | — |
| `--cell --dataset` (sin run) | RECHAZADO → falta `--run` (run → dataset) | — |
| `--dataset --run --cell` | OK · orden `cell → run → dataset` | **1 189 133** |
| *(sin flags)* | RECHAZADO → "Debe indicar al menos un flag" | — |

### Desglose de `--dataset --run --cell`

- **cell**: 31 tablas · 16 231 filas (igual que §1).
- **run**: 28 tablas · 1 034 893 filas. Mayores: `run_dataset_images` 825 048 ·
  `predictions` 99 567 · `run_image_predictions` 98 364 · `artifacts` 4 007 ·
  `explainability_results` 3 600 · `run_metrics` 2 796 · `training_history` 926.
  Orden: hojas (`classification_reports`, `confusion_matrices`, `run_metrics`, …) →
  `predictions` → `image_analysis_jobs` → `run_model_deployments` → `deployed_model_versions`
  → `run_threshold_calibration` → `stage2_model_publications` → `model_versions` →
  `artifacts` → `runs` → `experiments` → `models`.
- **dataset**: 13 tablas · 138 009 filas. Mayores: `dataset_split_images` 55 116 ·
  `dataset_split_assignments` 27 558 · `identity_evidence` 27 558 ·
  `dataset_source_records` 27 558 · `clinical_identities` 201.
  Orden: `identity_evidence` / `dataset_split_assignments` / `dataset_split_images` →
  `dataset_materializations` → `dataset_version_sources` → `dataset_source_records` →
  `clinical_identities` → `dataset_versions` → `datasets`.

`users`, `roles`, `user_roles`, `audit_events` (1 097 filas), `alembic_version`,
`schema_migrations` (23 filas): **fuera de alcance en todas las combinaciones**.

---

## 3. Guardas verificadas (dry-run / rechazo)

| Guarda | Comprobación | Resultado |
|---|---|---|
| Flag obligatorio | `purge.py` sin flags | `PURGE_REFUSED: Debe indicar al menos un flag…` |
| Identidad de BD | `current_database/user/schema` vs `DATABASE_URL` + Alembic head | validado en cada transacción |
| Toda tabla clasificada | 78/78 tablas mapeadas a cell/run/dataset/users/system | sin `PURGE_REFUSED: tablas sin clasificar` |
| FK cruzada | ver §1–§2 | rechazo con el flag exacto que falta |
| `--yes` sin `PURGE_DB_ALLOW_EXECUTION=1` | `purge.py --cell --yes` | `PURGE_REFUSED: PURGE_DB_ALLOW_EXECUTION=1 es obligatorio…` |
| `--yes` sin backup | `PURGE_DB_ALLOW_EXECUTION=1 purge.py --cell --yes` | `PURGE_REFUSED: --yes requiere un backup verificado…` |
| `--yes` con backup falso | `--backup /tmp/x.dump` (5 bytes) | `PURGE_REFUSED: backup demasiado pequeño…` |
| No toca storage | `grep -n "var/storage\|open(\|Path(" scripts/db/purge.py` | sólo `Path` para validar el backup; ningún archivo científico |

---

## 4. Suite de tests — `backend_api/tests/test_db_purge_tool.py`

`docker compose exec -T backend python -m pytest tests/test_db_purge_tool.py -q`
→ **29 passed** (idéntico resultado ejecutado desde el host con
`~/Library/Python/3.9/bin/pytest`).

Cobertura:

- **Flags aislados y combinados** (`test_single_flag`, `test_combined_flags_are_ordered_cell_run_dataset`):
  cada permutación de `--dataset/--run/--cell` resuelve al orden global `cell, run, dataset`.
- **`--cell` nunca purga tablas ajenas** (`test_cell_flag_never_reaches_dataset_or_run_tables`):
  `CELL_TABLES ∩ DATASET_TABLES = ∅`, `CELL_TABLES ∩ RUN_TABLES = ∅`; `microscopy_*` y
  `scientific_validation_*` clasifican como `cell`.
- **Ninguna combinación toca users/system** (`test_no_flag_combination_touches_users_or_system_tables`):
  para los 7 subconjuntos no vacíos de flags, `target_tables ∩ (USERS_TABLES ∪ SYSTEM_TABLES) = ∅`.
- **Buckets disjuntos** (`test_every_known_table_maps_to_exactly_one_bucket`).
- **Orden topológico** (`test_toposort_puts_children_before_parents`,
  `…_is_deterministic_alpha_tiebreak`, `…_survives_a_cycle`, `…_ignores_edges_outside_the_set`,
  `test_real_cell_order_keeps_specimen_roots_last`).
- **FK cruzadas** (`test_run_alone_is_refused_when_cell_rows_reference_it`,
  `…_allowed_when_no_cell_rows…`, `test_dataset_alone_is_refused_when_run_rows_reference_it`,
  `test_all_three_flags_have_no_cross_subsystem_conflict`,
  `test_unknown_dependent_table_fails_closed`,
  `test_child_in_target_parent_outside_is_not_a_conflict`).
- **Backup obligatorio para ejecutar** (`test_execution_needs_a_verified_backup`).
- **URL canónica** (`test_build_engine_rejects_non_canonical_urls`): rechaza `localhost`,
  puerto ≠ 5432, driver ≠ postgresql, URL sin usuario.
- **Aislamiento transaccional por subsistema** (motor falso en memoria):
  `test_purge_one_subsystem_disables_triggers_and_commits_once` (emite
  `SET LOCAL session_replication_role = replica`, un único `COMMIT`, DELETE en el orden
  recibido), `test_purge_one_subsystem_rolls_back_if_table_not_emptied` (si una tabla no
  queda vacía → `PurgeRefused` + `ROLLBACK`, sin `COMMIT`).

`test_docker_postgres_tooling.py` (7/7 desde host) valida además que `scripts/db/purge.sh`
crea el backup con `scripts/db/backup.sh` y ejecuta dentro del contenedor.

> Nota de entorno: dentro del contenedor, los tests que resuelven la raíz del repo con
> `Path(__file__).parents[2]` fallan (`test_docker_postgres_tooling.py`,
> `test_smear_reset_tool.py`, `test_scientific_storage_docker_contract.py`, …) porque
> `/app/tests` deja esa expresión en `/`. Es una condición **preexistente** del repo (ver
> `docs/audits/architecture_audit_2026-09-08.md` §6.1); no la introduce este trabajo.
> `test_db_purge_tool.py` la evita con un fallback a `/app/scripts/db/purge.py`.

---

## 5. Verificación pendiente (fuera de este prompt)

Punto 3 de la Fase 2 (purga real de prueba + login + vistas vacías sin 500) requiere
ejecutar una purga real y por tanto **se autoriza por separado**, tras revisar la Fase 0.
Procedimiento recomendado:

1. `make db-backup` (o dejar que `scripts/db/purge.sh --yes` lo haga).
2. `PURGE_DB_ALLOW_EXECUTION=1 scripts/db/purge.sh --cell --yes` en un entorno con backup
   restaurable.
3. Confirmar en el frontend: `/login` sigue funcionando (subsistema `users` intacto);
   `/frotis/historial`, `/frotis` y `/revision-celulas` muestran estado vacío sin error 500.
4. `pg_restore` del backup si se quería sólo validar.
