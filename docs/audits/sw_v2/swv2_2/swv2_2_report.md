# SWV2.2 — Configuración de campañas sobre PostgreSQL v2

Estado: **PASS — pendiente GATE SWV2.2** (la aprobación corresponde al usuario). TRAIN, VALIDATION y TEST no ejecutados. U-Net no implementado.

## Cambios

Backend/ML (`malaria_dl_local_project`):
- `src/malaria_dl/campaigns/configuration.py` (nuevo): catálogo desde registry + defaults versionados + protocolo aprobado; validación por campo; traducción única a request/protocolo E4; total = `expand_matrix`.
- `src/malaria_dl/campaigns/plan.py` (nuevo): `campaign_id` → plan (sólo lectura) + readiness del ejecutor + comando.
- `campaigns/repository.py`: `create_frozen` (draft+configuraciones+miembros+freeze en una transacción, idempotente por `campaign_id`), `_materialize` extraído de `freeze` (mismo SQL), `same_configuration`.
- `campaigns/service.py`: `configure`, `frozen_contract` (compartido con `freeze`); validación de identidad antes de cualquier escritura.
- `execution/campaign.py`: `--plan`; dataset tomado de la campaña (aserción opcional). `run_train_all_models.py`: docstring de uso.

API (`backend_api`): `schemas/campaigns.py` (DTO estrictos), `services/campaign_configuration.py`, `routes/campaigns.py` (`GET catalog`, `GET preview`, `POST` crear, `GET {id}`; sin endpoint de ejecución), permiso `campaigns.configure` (administrator, researcher), router registrado.

Frontend: `pages/CampaignConfiguration.tsx` (página única: datos generales, dataset, modelos/optimizadores/semillas, configuración por modelo y variantes, EarlyStopping/presupuesto, resumen sticky, validación, guardar, panel con comando y Copiar), `types/campaign.ts`, métodos en `services/api.ts`, ruta `/modelo-ia/campana`, menú Modelo IA → Campaña bajo Ejecuciones, estilos.

Evidencia/herramientas: `scripts/db/swv22_campaigns.py`, `scripts/db/swv22_api_probe.py`, `docs/audits/sw_v2/swv2_2/*`.

## Pruebas

| Suite | Antes (HEAD) | Después | Nuevos fallos |
|---|---|---|---|
| ML campañas/registry/CLI (host) | 172 ✓ / 6 ✗ | 222 ✓ / 6 ✗ (mismos) | 0 |
| Backend CI (`not requires_docker_postgres`) | 539 ✓ / 2 ✗ | 547 ✓ / 2 ✗ (mismos) | 0 |
| Frontend `node --test` | 201 ✓ | 211 ✓ | 0 |
| SWV2.2 en `capstone_backend` (PostgreSQL v2 real, rollback) | — | 57 ✓ | 0 |
| `tsc` + `vite build` | OK | OK | — |

Nuevos: 50 ML (38 configuración, 12 CLI/plan), 7 PostgreSQL v2 con rollback (crear/recargar/plan, idempotencia/conflicto, atomicidad ante fallo del freeze, `--plan` real sin TRAIN, DELETE prohibido, rol runtime), 8 API, 10 frontend. Fallos preexistentes: `test_model_registry_e2::test_matrix_invalid_combination_rejected_before_preflight` (modo directo retirado en Etapa 5), 2 `test_input_contract_e3` (fixture sin `architecture`), 3 `test_campaign_exit_diagnostics` (fake repo sin `preflight_e10_schema`), 2 backend (política E9.3 local_execution; bloque TEMPORAL del override). Detalle: `swv2_2_tests_*.txt`.

Cobertura de la lista obligatoria: PostgreSQL v2/runtime/health/ready (check, runtime, smoke); dataset versions y asociación (API, BD); discovery de modelos y defaults (catálogo); válidos/inválidos/optimizer/EarlyStopping (parametrizados + sonda HTTP); configuración por modelo preservada (unit + BD); total y coincidencia frontend/backend (preview = resolve = BD = UI recargada); guardar atómico, campaign_id, recarga exacta, plan, comando (BD + UI); CLI `--campaign-id`/`--plan`/exclusión/aserción de dataset; ningún TRAIN/TEST/resultado (fakes que fallan si se cruza el boundary; conteos antes/después).

## No regresión

/health 200, /ready 200, `require_e10_schema` PASS, `pg_v2_baseline`, manifest `15c95e0c…3eafb`, sysid/OID sin cambio, dataset y fingerprints intactos, split sin cambios, XAI y TRAIN history vacíos, ejecución Mac/Docker no rediseñada. Ver `swv2_2_operations.md`.

## Problemas encontrados

1. 4 `.DS_Store` en la raíz del dataset (preexistente) — eliminados con autorización; integridad restaurada.
2. Orden de validación en `configure` — corregido; dejó 1 evidencia append-only atribuida.
3. Modo directo `--dataset-version-id` no existe desde Etapa 5 — documentado, no recreado.

## Pendientes para SWV2.3

- Tabla `models` vacía: `_create_run` exige identidad única por modelo (`CANONICAL_MODEL_CATALOG_IDENTITY_REQUIRED`).
- El CLI ML sólo conecta a hostname `db`; el `.env` local del Mac apunta a `julio` (SUPERUSER). Ejecutar fuera del contenedor requiere además el mecanismo de revisión técnica (entorno y `dataset_root` congelados en la campaña).
- Hiperparámetros internos por optimizador no editables en campañas multi-optimizador (contrato E4).
- `run_configurations.architecture` CHECK limita a las 3 arquitecturas actuales (evolución de esquema futura para U-Net).
