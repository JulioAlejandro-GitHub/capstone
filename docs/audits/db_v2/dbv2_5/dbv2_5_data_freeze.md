# DBV2.5 — Freeze de datos

Todas las lecturas: BD-v2 y legacy en `REPEATABLE READ READ ONLY`. Los fingerprints se **leen** de PostgreSQL (`dataset_versions.methodology_json → freeze_contract.fingerprints`); no se recalculan ni se reprocesan imágenes.

## Dataset

| Campo | Esperado | Observado |
|---|---|---|
| dataset_version_id | `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2` | idem (única fila en `dataset_versions`) |
| Estado | FROZEN | FROZEN |
| frozen_at | preservado | `2026-08-18 18:06:25.263208+00` = valor legacy (comparación exacta) |
| TRAIN / VALIDATION / TEST | 22,180 / 2,693 / 2,685 | 22,180 / 2,693 / 2,685 |
| TOTAL | 27,558 | 27,558 |
| Pacientes | 201 | 201 |
| Overlap TRAIN/VAL, TRAIN/TEST, VAL/TEST | 0 / 0 / 0 | 0 / 0 / 0 |
| dataset_split_images | 55,116 = 2 raíces × 27,558 | 55,116: `malaria_dataset_versions/d8c0…` 27,558 + `malaria_physical_split` 27,558 (sin deduplicar) |

Snapshot científico BD-v2 == snapshot científico legacy (misma función `science()` de DBV2.4 sobre ambos).

## Fingerprints almacenados

| Fingerprint | Valor almacenado | Resultado |
|---|---|---|
| record_assignment_sha256 | `9709ce48b9b41bcacca49ccfb53ec62b48c4822c2fb8e227643bf26aed196ea2` | PASS |
| patient_assignment_sha256 | `cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f` | PASS |
| clinical_identity_sha256 | `d4bd79cb2327ca7aa1eeff19e14a9104af157984cccd9418c75b0f62ae3e8a59` | PASS |
| source_population_sha256 | `eef647ce1f3040468a84cbad73ffb1b50b86d685313f1291693b16f4f1f635f0` | PASS |

## Tablas transferidas (re-verificación contra legacy)

Para cada tabla autorizada: conteo, hash de transferencia (JSONB length-prefixed ordenado por PK), hash de PK e igualdad exacta fila a fila frente a legacy (`compare()` de DBV2.4).

| Tabla | Filas | Resultado |
|---|---|---|
| datasets | 2 | PASS |
| dataset_versions | 1 | PASS |
| clinical_identities | 201 | PASS |
| dataset_source_records | 27,558 | PASS |
| identity_evidence | 27,558 | PASS |
| dataset_version_sources | 1 | PASS |
| dataset_split_assignments | 27,558 | PASS |
| dataset_split_statistics | 1 | PASS |
| dataset_split_validation_checks | 12 | PASS |
| dataset_splits | 0 | PRESERVED_EMPTY |
| dataset_materializations | 1 | PASS |
| dataset_materialization_activations | 0 | PRESERVED_EMPTY |
| dataset_split_images | 55,116 | PASS |
| roles | 1 | PASS |
| users | 1 | PASS |
| user_roles | 1 | PASS |

## Usuario mínimo preservado

| Campo | Resultado |
|---|---|
| preserved user | YES (1) |
| user ID preserved | YES |
| identity preserved | YES |
| role preserved | YES (1 de 5 roles legacy; el único referenciado, según el plan aprobado) |
| user_role preserved | YES (1) |
| password_hash_match | **true** (comparación en memoria; el valor no se imprime ni se persiste) |

## Ausencias

| Categoría | Filas |
|---|---|
| Filas no autorizadas | 0 (sólo filas técnicas de baseline: `alembic_version` 1, `experiment_execution_gate` 1) |
| audit_events | 0 |
| Historia XAI (9 tablas) | 0 |
| Historia E10 (experiments, runs, campaigns, evaluations, predictions, calibrations, deployments, publication, smear, training…; 26 tablas) | 0 |

## Integridad (post-restart y chequeo final)

FK huérfanas 0 · PK duplicadas 0 · violaciones UNIQUE 0 · violaciones CHECK 0 (992 consultas explícitas).

Evidencia: `dbv2_5_verification.json` → `data`; `dbv2_5_final_check.json`.
