# SWV2.2 — Operación: preflight, dataset, demostración, postflight, git

## 1. Preflight (antes de modificar código)

| Campo | Valor |
|---|---|
| Rama / HEAD | `main` / `2ba0755e0035d21d2af5175fd0fb861fad89e8ee` (= cierre SWV2.1) |
| `git status` | limpio |
| PostgreSQL / base / OID / sysid | 17.9 / malaria_experiments / 16386 / 7691366089693499436 |
| Alembic | `pg_v2_baseline` (1 root, 1 head) |
| Structural manifest | `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb` |
| Backend | `capstone_v2_runtime`, no superuser; `require_e10_schema` PASS; `/health` 200, `/ready` 200 |
| Estado de entrada | 2 `USER_LOGIN_SUCCEEDED` (logins de aplicación posteriores a SWV2.1, no de SWV2.2) — `swv2_2_entry_state.json` |
| Evidencia | `swv2_2_check_preflight.json`, `swv2_2_runtime_preflight.json`, `swv2_2_smoke_preflight.json` (`scripts/db/swv22_campaigns.py`, READ ONLY) |

## 2. Restauración del estado sellado del dataset (autorizada por el usuario)

Al probar la persistencia real, `resolve_governed_dataset` (READ ONLY) devolvió `DATASET_CONTENT_SET_MISMATCH`. Diagnóstico READ ONLY como `capstone_v2_runtime` (`swv2_2_dataset_diag_before.json`): 27,558 archivos esperados, 27,562 presentes; extras = `.DS_Store`, `test/.DS_Store`, `train/.DS_Store`, `val/.DS_Store` (macOS Finder, creados 2026-09-28 21:56–21:57, antes de DB-V2); faltantes 0; **27,558/27,558 SHA-256 coinciden**.

Con autorización explícita del usuario se eliminaron sólo esos 4 archivos (rutas, tamaños y hashes en `swv2_2_ds_store_removed.txt`). No se tocaron imágenes, BD, split ni fingerprints. Después: 27,558 = 27,558, extras 0, hashes 27,558 OK, `resolve_governed_dataset` PASS (`swv2_2_dataset_diag_after.json`). Recomendación: no abrir ese directorio con Finder (lo recrea).

## 3. Escritura de la sonda HTTP (defecto encontrado y corregido)

La primera ejecución de `scripts/db/swv22_api_probe.py` envió `POST /api/campaigns` con nombre en blanco. `CampaignService.configure` ejecutaba la verificación de dataset (que persiste evidencia) antes de validar el nombre: quedó 1 fila `audit_events` `157491f3-0967-4a95-9be5-6cdcf7dd7e56` (`ml.dataset_verification`, éxito, `campaigns.configure`, sin campaña). `audit_events` es append-only (trigger), por lo que no se elimina; es evidencia verídica de una verificación, no un resultado científico. Corrección: nombre/propósito/actor se validan antes de cualquier escritura + test `test_configure_rejects_blank_identity_before_writing_dataset_evidence`. Re-ejecución: 0 escrituras (`swv2_2_api_probe.json`). El chequeo final atribuye esa fila campo por campo.

## 4. Campaña de demostración (configuración, NO ejecutada)

Creada desde la UI real (`http://localhost/modelo-ia/campana`) conducida por Chrome headless/CDP con un token emitido por el backend (sin login, sin contraseña; token eliminado al terminar). Capturas en `ui/`.

| Campo | Valor |
|---|---|
| campaign_id | `cfcd2c08-243e-4b52-b0c5-08c6f1bb287c` |
| Nombre | SWV2.2 demostración de configuración — NO EJECUTAR |
| Propósito | demostrar configurar → validar → guardar → campaign_id → comando |
| Dataset Version | `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2` |
| Modelos / optimizadores / semillas | custom_cnn, vgg16, densenet121 / adam / 11, 29 |
| Valores por modelo | custom_cnn max_epochs 50; vgg16 max_epochs 30; densenet121 fine_tune_epochs 10; resto defaults |
| Configuraciones / Total de Experimentos | 3 / **6** (UI antes de guardar = UI después = backend = BD) |
| Estado | `frozen`, 6 miembros `pending`, 0 intentos |
| Contract hash | `d8c7fe9087d77f63…` (completo en `swv2_2_cli_plan_container.json`) |
| Comando | `python run_train_all_models.py --campaign-id cfcd2c08-243e-4b52-b0c5-08c6f1bb287c` |

No se ejecutó: sin TRAIN, sin VALIDATION, sin TEST, sin EVALUATE/XAI, sin `campaign_attempts`/`runs`/sesiones/registros. No es evidencia de desempeño clínico. El trigger de BD impide borrarla (`CAMPAIGN_DELETE_FORBIDDEN`).

Escrituras persistentes atribuidas (chequeo final): 1 campaña, 3 configuraciones, 6 miembros, 14 `audit_events` = 1 evidencia de la sonda (§3) + 1 evidencia de dataset de la demo + 11 de triggers `campaign_audit` + 1 `ml.campaign.configured`.

## 5. Resolución CLI de `--campaign-id`

- Contenedor `capstone_backend` (entorno de creación): `run_train_all_models.py --campaign-id … --plan` → exit 0, 6 experimentos en orden, dataset = el de la campaña (`swv2_2_cli_plan_container.json`). Readiness: estado ejecutable, E10 schema, identidad de código, adapters, TEST prohibido, dataset sin cambios = PASS; `model_catalog_identity` = FAIL (`models` vacía en v2) → no listo para TRAIN hasta SWV2.3.
- Mac host (`swv2_2_cli_plan_mac.json`): argumentos aceptados; falla en cerrado en el primer acceso a BD por la regla preexistente `DATABASE_URL solo permite el hostname db`. Además el snapshot guarda `dataset_root` del contenedor y el entorno Python de creación; ejecutar fuera del contenedor requerirá el mecanismo existente (agente local / revisión técnica) — SWV2.3.

## 6. Postflight

`swv2_2_check_final.json` (READ ONLY): 17.9, OID 16386, sysid 7691366089693499436, `pg_v2_baseline`, manifest `15c95e0c…3eafb`, baseline diff 0, dataset FROZEN 22,180/2,693/2,685 = 27,558, 201 pacientes, overlap 0, 16 hashes de transferencia = DBV2.4, fingerprints iguales, usuario sin cambios (`last_login_at` = entrada), filas fuera del conjunto transferido sólo las atribuidas en §4, 0 filas de ejecución científica, XAI vacío. `swv2_2_runtime_final.json`: `capstone_v2_runtime`, sin superuser/migrator, `require_e10_schema` PASS. `swv2_2_smoke_final.json`: `/health` 200, `/ready` 200, `/api/v1/auth/me` sin token 401.

## 7. Git

Ningún cambio en `alembic_v2/`, `alembic_v2.ini`, `alembic/`, `docs/audits/db_v2/`, `malaria_dataset_split_project/`. Despliegue: el modo operativo (override) monta el código en `capstone_backend` (uvicorn `--reload`) y `capstone_frontend` (Vite); también se reconstruyó la imagen backend con el Dockerfile existente (sin cambios de Docker). Commit local único, sin push ni tag.
