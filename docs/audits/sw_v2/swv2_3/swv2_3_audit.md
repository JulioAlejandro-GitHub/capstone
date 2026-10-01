# SWV2.3 — Auditoría del reporte de campañas

Realizada sobre el código real (HEAD `891b34c` = cierre SWV2.2) **antes** de modificar código. `S/` = `malaria_dl_local_project/src/malaria_dl/`. SWV2.3 no toca el esquema (`alembic_v2/baseline` intacto): es una capa de **lectura y navegación** sobre el contrato SWV2.2 ya congelado.

## 1. Estado real encontrado (brecha que cierra SWV2.3)

| Componente | Hallazgo |
|---|---|
| Resultado tras guardar | `SavedCampaignPanel` dentro de `frontend/src/pages/CampaignConfiguration.tsx`: panel **en memoria** que aparece al guardar. **No tiene ruta propia** — al navegar se pierde. Era la única "visualización de la campaña creada" y no era accesible desde el menú. **Esta es la razón de ser del reporte.** |
| Menú "Campaña" | Apuntaba a `/modelo-ia/campana` (la página de configuración, form vacío). No había forma de ver las campañas ya creadas. |
| Backend | Existían `GET /catalog`, `GET /preview`, `POST ""`, `GET /{campaign_id}`. **No había listado** de campañas creadas. `GET /{campaign_id}` ya devolvía el detalle completo (incl. `configuration` reconstruida por SWV2.2 vía `document_from_request`). |
| ML | `S/campaigns/repository.py` tenía `get` (una campaña) pero **no `list_campaigns`**. `S/campaigns/configuration.py` ya tenía `document_from_request` (SWV2.2, inversa de `build_request`/`build_protocol`). |
| Frontend | `router.ts` tenía `campaign` pero no `campaigns`. `types/campaign.ts` tenía `SavedCampaign` pero no `CampaignListItem`. No existía página de reporte. |
| PostgreSQL v2 | 2 campañas `frozen` en `experimental_campaigns`: `cfcd2c08-…` (demo SWV2.2, 6 experimentos) y `01f3f423-…` ("ejemplo", 1 experimento). Guardas `campaign_guard` intactas (DELETE prohibido, FROZEN inmutable). |

## 2. Lo que agrega SWV2.3 (por capa)

| Capa | Archivo | Cambio |
|---|---|---|
| ML | `S/campaigns/repository.py` | Nuevo `list_campaigns(limit, offset)`: join con `dataset_versions` (nombre + `semantic_version`), agrega estados de `campaign_members`, `ORDER BY created_at DESC`. Solo lectura. |
| ML | `S/campaigns/configuration.py` | (SWV2.2) `document_from_request` ya existía; SWV2.3 la reutiliza en el detalle para el prefill de edición. |
| Backend | `app/services/campaign_configuration.py` | Nuevo `list_campaigns(limit, offset)` (proyecta `CampaignListItem`: dataset, modelos/optimizadores/semillas desde `requested`, `total_experiments` = `expected_count`, `members_by_state`, `command`). `_saved()` ya incluye `configuration` (SWV2.2). |
| Backend | `app/routes/campaigns.py` | Nuevo `GET ""` (permiso `RUNS_READ`, `limit` 1..500, `offset` ≥0) **antes** de `/{campaign_id}`. Sin palabras de ejecución en rutas (contrato SWV2.2 intacto). |
| Frontend | `src/pages/CampaignsReport.tsx` (nuevo, 153) | Página principal de campañas: tabla 8 columnas, badges de estado, botón **Nueva Campaña** → `/modelo-ia/campana`, **Editar** por fila → `/modelo-ia/campana?campaignId=<id>`. |
| Frontend | `src/pages/CampaignConfiguration.tsx` | Modo edición: `?campaignId` prefill desde `GET /{id}` + `existing.configuration`; banner de edición; 409 `CAMPAIGN_ID_CONFLICT` → reintenta con nuevo id + nota "derivada"; botones Ver/Volver al reporte. |
| Frontend | `src/router.ts` | Nuevo `campaigns: '/modelo-ia/campanas'`; `isValidPublicId` acepta `string \| null \| undefined`. |
| Frontend | `src/types/campaign.ts` | Nuevos `CampaignListItem` + `CampaignListResponse`; `SavedCampaign.configuration`. |
| Frontend | `src/services/api.ts` | Nuevo `getCampaigns({limit, offset})`. |
| Frontend | `src/components/navigation/{navigationConfig.ts,AppSidebar.tsx}` | Menú "Campaña" → `routes.campaigns`; `sectionForPath` y resaltado cubren ambas rutas. |
| Frontend | `src/styles.css` | Sección `/* SWV2.3 */`: grid responsive 8 col, 5 colores de estado, `.is-highlight`, banner, nota `.api-note` (antes sin estilo). |
| Tests | ML `test_campaign_configuration_swv22.py` (+2), backend `test_campaigns_api_swv22.py` (+3), frontend `campaigns-report.test.mjs` (nuevo, 8) + `campaign-configuration.test.mjs` (actualizado) | |

## 3. Contratos

**Listado (`GET /api/campaigns`).** Solo lectura, más recientes primero. Cada ítem: identidad, estado, `contract_hash`, `frozen_at`, dataset (nombre + versión semántica + UUID), modelos/optimizadores/semillas (desde `requested`), `total_experiments` (autoridad = `expected_count` del plan, nunca calculado en el cliente), `members_by_state`, `command`. El detalle por campaña sigue en `GET /{id}` (incluye `configuration`); el listado es ligero y no la incluye.

**Flujo de navegación.** Menú "Campaña" → `/modelo-ia/campanas?datasource=malaria` (reporte). **Nueva Campaña** → `/modelo-ia/campana?datasource=malaria` (form vacío). **Editar** → `/modelo-ia/campana?datasource=malaria&campaignId=<id>` (form prellenado + banner). La página de configuración y el reporte comparten la misma sección del menú.

**Campañas FROZEN (decisión de diseño — requiere aprobación del usuario).** FROZEN es inmutable por `campaign_guard` (no se modifica el guard). Comportamiento de "Editar":
- Guardar **sin cambios** → idempotente, mismo `campaign_id`.
- Guardar **con cambios** → backend `409 CAMPAIGN_ID_CONFLICT`; el frontend reintenta con un **nuevo `campaign_id`** y muestra nota ámbar: se creó una **campaña derivada**; la original permanece intacta en el reporte.

Es el único comportamiento posible sin romper la inmutabilidad. Alternativa (si se prefiere): "Editar" en FROZEN sea solo lectura.

**Terminología.** "Total de Experimentos" (nunca "Miembros de campaña"). Sin `execute`/`run`/`start`/`train`/`launch` en rutas (verificado por test).

## 4. Hallazgo preexistente (NO causado por SWV2.3)

El target canónico `make test-backend` **se aborta con 2 errores de colección** en el contenedor, y **19 tests de guardas de contrato fallan solo en contenedor**. Verificado que ambos conjuntos son **idénticos con y sin los cambios de SWV2.3** (comparación HEAD vs HEAD+cambios vía stash): SWV2.3 no rompe nada.

| Archivo | Causa raíz |
|---|---|
| `tests/test_docker_postgres_contract_guard.py` | `ROOT = Path(__file__).resolve().parents[2]` → en contenedor (tests montados en `/app/tests`) resuelve a `/` → `FileNotFoundError: /scripts/check_docker_postgres_contract.py`. Además ese script **no está horneado** en el Dockerfile. |
| `tests/test_smear_reset_tool.py` | Mismo `parents[2]` → `/scripts/storage/reset_smear_analysis.py` (el horneado está en `/app/scripts/…`). |
| 19 tests en 7 archivos de guardas (runtime role, docker tooling, storage, quality queue, cell detection/classification, db purge, gradcam) | Misma clase: resuelven archivos del repo (`docker-compose.yml`, `Dockerfile`, `Makefile`, `.env.example`, `scripts/…`) vía `__file__` → en contenedor apuntan a `/` (`FileNotFoundError: /docker-compose.yml`, `assert '' == '/'`). Pasan en host, fallan en contenedor. |

Ambos archivos de colección preexisten a SWV2.3 (commits `792f123`, `d71bded`). **No se corrigió** (fuera de alcance; cultura de auditoría). Corrección sugerida: resolver la raíz desde un punto estable (`parents[1]` + montar `scripts/`, o `CAPSTONE_ROOT` como ya hace `verify_alembic_adoption.py`) y hornear el script del guard. Ver `swv2_3_operations.md` §5.

## 5. Fuera de alcance

- Ejecución de campañas (TRAIN/VALIDATION/TEST/EVALUATE/XAI): sigue siendo comando manual de consola (`run_train_all_models.py --campaign-id`). SWV2.3 es solo configuración + reporte.
- `models` vacía en v2 (`model_catalog_identity` FAIL): reportado en SWV2.2, sin cambio.
- `ej.html` (raíz, sin rastrear) y el badge DeepWiki en `README.md`: artefactos ajenos a la feature (ver `swv2_3_operations.md` §6).
