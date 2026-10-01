# SWV2.3 — Operación: preflight, cambios, verificación, git

## 1. Preflight (antes de modificar código)

| Campo | Valor |
|---|---|
| Rama / HEAD | `main` / `891b34c6f1d441f2708a3793c06cdba6f3751647` (= cierre SWV2.2) |
| `git status` | limpio al inicio (el árbol de trabajo se ensanchó con los cambios de SWV2.3 a lo largo de la sesión) |
| PostgreSQL / base | 17.9 / `malaria_experiments` |
| Alembic | `pg_v2_baseline` (sin cambio; SWV2.3 no toca el esquema) |
| Backend / Frontend | contenedores `capstone_backend` (uvicorn `--reload`) y `capstone_frontend` (Vite, puerto 80) con mounts de hot-reload |
| Campañas en BD | 2 `frozen`: `cfcd2c08-243e-4b52-b0c5-08c6f1bb287c` (demo SWV2.2, 6 experimentos) y `01f3f423-b5d3-42bf-b830-6f28ccd721e3` ("ejemplo", 1 experimento) |

## 2. Cambios aplicados (16 archivos modificados + 2 nuevos)

Diff total: **647 inserciones, 37 eliminaciones**. Detalle por capa en `swv2_3_audit.md` §2.

- **ML** (`malaria_dl_local_project`): `campaigns/repository.py` +`list_campaigns`; `campaigns/configuration.py` (reutiliza `document_from_request`); `tests/test_campaign_configuration_swv22.py` +2 tests.
- **Backend** (`backend_api`): `app/routes/campaigns.py` +`GET ""`; `app/services/campaign_configuration.py` +`list_campaigns`; `tests/test_campaigns_api_swv22.py` +3 tests.
- **Frontend** (`frontend`): `pages/CampaignsReport.tsx` (nuevo), `pages/CampaignConfiguration.tsx` (modo edición), `router.ts`, `types/campaign.ts`, `services/api.ts`, `components/navigation/{navigationConfig.ts,AppSidebar.tsx}`, `styles.css` (sección SWV2.3), `tests/campaigns-report.test.mjs` (nuevo) + `tests/campaign-configuration.test.mjs`.

## 3. Verificación de tests (registros crudos en `swv2_3_tests_*.txt`)

| Suite | Comando | Resultado |
|---|---|---|
| ML campañas | `cd malaria_dl_local_project && .venv/bin/python -m pytest tests/test_campaign_configuration_swv22.py -q` | **40 passed** |
| Backend API campañas | `docker compose exec -T backend python -m pytest tests/test_campaigns_api_swv22.py -q` | **11 passed** |
| Frontend (completa) | `cd frontend && npm test` | **219 passed, 0 fail** |
| Frontend build | `cd frontend && npm run build` | **OK** (tsc + vite; warning de chunk >500kB preexistente) |
| Contenedor (PostgreSQL real) | `docker compose exec -T -w /app/malaria_dl_local_project backend python -m pytest tests/test_campaign_configuration_postgres_swv22.py -q` | **7 passed** (crear/congelar atómico, idempotencia, 409, sin parciales, boundary, DELETE prohibido) |
| Makefile `test-ml` (canónico) | `docker compose exec -T -w /app/malaria_dl_local_project backend python -m pytest tests/test_label_mapping.py tests/test_decision.py tests/test_image_quality.py -q` | **17 passed** |

**SWV2.3 no rompe nada (verificado).** Suite backend completa en contenedor (con los 2 `--ignore` del §5): `21 failed, 325 passed, 1 skipped, 44 deselected`. Al comparar **HEAD vs HEAD+cambios** (vía `git stash` / `git stash pop`), los **21 fallos son idénticos** en ambos y los 3 tests nuevos de SWV2.3 pasan: los fallos son preexistentes, no de esta feature.

## 4. Verificación en vivo (datos reales)

- `GET /api/campaigns?limit=5` (sin token) → `401 AUTHENTICATION_REQUIRED` (la ruta **existe**; sin token no 404). Con sesión del navegador, el reporte lista las 2 campañas.
- Servicio `list_campaigns` contra la BD real (rol runtime): `01f3f423` "ejemplo" frozen 1 modelo/1 experimento; `cfcd2c08` demo frozen 3 modelos/6 experimentos, `members_by_state {pending:6}`.
- Detalle `GET /api/campaigns/{cfcd2c08}` devuelve `configuration` completa (modelos, optimizador, semillas, variante, protocolo) → el prefill de edición funciona.
- Vite sirve el código nuevo: `CampaignsReport.tsx` transformado, `router.ts` con `campaigns: "/modelo-ia/campanas"`, `App.tsx` con ambas rutas.
- Página `http://localhost/modelo-ia/campanas?datasource=malaria` → 200 (SPA). Menú "Campaña" → reporte; **Nueva Campaña** → form vacío; **Editar** → form prellenado + banner.

## 5. Hallazgo preexistente: rotura de la suite backend canónica (NO de SWV2.3)

`make test-backend` = `docker compose exec -T backend python -m pytest tests -m "not requires_docker_postgres"` **se aborta** en contenedor:

```
ERROR tests/test_docker_postgres_contract_guard.py - FileNotFoundError: [Errno 2] ... '/scripts/check_docker_postgres_contract.py'
ERROR tests/test_smear_reset_tool.py - FileNotFoundError: [Errno 2] ... '/scripts/storage/reset_smear_analysis.py'
346/390 tests collected (44 deselected), 2 errors
```

**Causa raíz.** Ambos calculan `ROOT = Path(__file__).resolve().parents[2]`. En host (`backend_api/tests/…`) `parents[2]` = raíz del repo (correcto). En contenedor los tests se montan en `/app/tests`, por lo que `parents[2]` = `/` → buscan en `/scripts/…` (no existe). El Dockerfile hornea `scripts/storage/reset_smear_analysis.{py,sh}` en `/app/scripts/…` (no el guard). Con los 2 `--ignore`, la suite completa da **21 fallos**: los 2 que ya fallaban en el baseline host de SWV2.2 (`test_mutation_security_policy`, `test_scientific_storage_docker_contract`) + 19 adicionales específicos de contenedor (guardas de contrato que resuelven rutas vía `__file__`).

**Verificación de que es preexistente.** `git stash` (cambios de SWV2.3) → suite en contenedor → `21 failed, 322 passed, 1 skipped, 44 deselected`; `git stash pop` → `21 failed, 325 passed, …`. **Mismos 21 fallos** con y sin SWV2.3 (la diferencia de +3 passed son los tests nuevos de SWV2.3). Los 2 archivos de colección preexisten (commits `792f123`, `d71bded`).

**No se corrigió** (fuera de alcance de la feature; cultura de auditoría). Corrección sugerida (cambio separado, con aprobación):
1. Resolver la raíz desde un punto estable: `parents[1]` + montar `scripts/` en el override, **o** usar `CAPSTONE_ROOT` (patrón ya usado por `scripts/db/verify_alembic_adoption.py`).
2. Hornear `scripts/check_docker_postgres_contract.py` en el Dockerfile (hoy no está).

## 6. Git

- Ningún cambio en `alembic_v2/`, `alembic_v2.ini`, `alembic/`, `docs/audits/db_v2/`, `malaria_dataset_split_project/`, ni en los guards de `alembic_v2/baseline`.
- **No se revertió** el badge DeepWiki en `README.md` (artefacto externo, mtime Oct 1; ajeno a la feature).
- `ej.html` (raíz, 415 KB, sin rastrear): copia HTML guardada de una página del usuario; ajena a la feature, no se toca.
- `.agents/` (sin rastrear): carpeta de trabajo del agente; no es parte de la feature.
- Despliegue: el modo operativo (override) monta el código en `capstone_backend`/`capstone_frontend` (hot-reload); no se cambió Docker.
- **Sin commit** (los cambios de SWV2.3 permanecen en el árbol de trabajo, como al inicio de la sesión).
