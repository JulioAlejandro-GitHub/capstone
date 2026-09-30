# SWV2.0 — Dataset y usuario de aplicación

Verificado por el endpoint final `127.0.0.1:5432/malaria_experiments` (checkpoints `integrated` y `after_restart`) y en preflight/post_rename. Sin recalcular imágenes ni fingerprints: se leen los valores almacenados y se comparan con DBV2.4/DBV2.5.

| Campo | Esperado | Observado |
|---|---|---|
| dataset_version_id | d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 | idem |
| Estado | FROZEN | FROZEN (`frozen_at` = DBV2.5) |
| TRAIN / VALIDATION / TEST | 22,180 / 2,693 / 2,685 | 22,180 / 2,693 / 2,685 |
| TOTAL | 27,558 | 27,558 |
| Patients | 201 | 201 |
| Overlap T/V, T/T, V/T | 0 / 0 / 0 | 0 / 0 / 0 |
| dataset_split_images | 55,116 | 55,116 (2 raíces × 27,558) |
| Snapshot científico | = DBV2.5 | idéntico |
| record_assignment_sha256 | 9709ce48…196ea2 | idéntico |
| patient_assignment_sha256 | cbe7a7b8…20ea7f | idéntico |
| clinical_identity_sha256 | d4bd79cb…3e8a59 | idéntico |
| source_population_sha256 | eef647ce…1f35f0 | idéntico |

## Contenido fila a fila

Para las 16 tablas transferidas en DBV2.4 (13 dataset + `roles`, `users`, `user_roles`) se recalculó el mismo transfer hash de DBV2.4 (JSONB por fila, ordenado por PK, prefijado por longitud; `users` sin `password_hash`) y el `pk_hash`: **16/16 idénticos** al `dbv2_4_transfer_manifest.json` (`295ad373…3cf9`). Detalle en `data.tables` de cada `swv2_0_check_*.json`.

## Usuario de aplicación

| Campo | Valor |
|---|---|
| users / roles / user_roles | 1 / 1 / 1 |
| Usuario activo | 1 |
| password_hash sin cambios | YES — digest SHA-256 del valor almacenado tomado en preflight y comparado en cada checkpoint; el digest sólo existe en `var/maintenance/swv20/` (ignorado por Git); el hash nunca se imprimió ni se almacenó |

## Otros invariantes

Filas fuera de las tablas transferidas: sólo `alembic_version` (1) y `experiment_execution_gate` (1). XAI, E10 y audit = 0 filas. FK/CHECK/UNIQUE/PK: 0 violaciones.

Dataset retransferido: **NO**. Dataset reconstruido: **NO**.
