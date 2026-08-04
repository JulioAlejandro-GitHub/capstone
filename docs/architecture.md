# Arquitectura actual

Este documento es el índice canónico de la arquitectura ejecutable. El sistema
es un monolito modular local: una SPA React consume una API FastAPI; la API
coordina PostgreSQL, almacenamiento de archivos local y el paquete científico
`malaria_dl`. No hay contenedores ni servicios remotos obligatorios en el
runtime soportado.

## Componentes de runtime

| Componente | Implementación | Responsabilidad |
|---|---|---|
| Frontend | `frontend/src`, React 19, TypeScript y Vite | Autenticación, gobierno de modelos y workflow de frotis |
| API | `backend_api/app`, FastAPI | Contratos HTTP, JWT/RBAC, auditoría y orquestación |
| Dominio ML | `malaria_dl_local_project/src/malaria_dl` | Dataset, entrenamiento, evaluación, inferencia y explicabilidad |
| Persistencia | PostgreSQL 17 | Linaje, estado, publicaciones, resultados y auditoría |
| Objetos | `var/storage` y artefactos configurados | Originales, crops y explicaciones con claves relativas |
| Migraciones | SQL histórico + Alembic lineal | Evolución auditable del esquema |

El entrypoint de la API es `backend_api/app/main.py`; el del frontend es
`frontend/src/main.tsx`. La API no sirve la SPA. En un hosting distinto de Vite
se necesita fallback de rutas a `index.html`, excluyendo `/api` y los health
checks.

## Límites funcionales

- **Modelo IA** administra datasets, ejecuciones, evaluaciones, versiones,
  publicaciones y trazabilidad.
- **Análisis de frotis** registra identidad pseudonimizada, ingesta originales,
  quality gate, detección, clasificación, revisión humana, Grad-CAM y agregación.
- El backend es la autoridad para permisos y transiciones. La interfaz sólo
  representa capacidades recibidas; no inventa estados ni habilita fallbacks.
- Los resultados automáticos y los revisados se preservan por separado. Nunca
  se presenta el sistema como dispositivo o diagnóstico clínico.

El recorrido de datos vigente se documenta en
[ai-pipeline.md](ai-pipeline.md). Los modelos de dominio detallados están en
[scientific_data_model.md](architecture/scientific_data_model.md),
[microscopy_analysis_runs.md](architecture/microscopy_analysis_runs.md),
[cell_detection_data_model.md](architecture/cell_detection_data_model.md),
[cell_classification_data_model.md](architecture/cell_classification_data_model.md)
y [smear_analysis_aggregation.md](architecture/smear_analysis_aggregation.md).

## Decisiones y contratos

Los ADR vigentes están en [`docs/adr`](adr/) y los esquemas de intercambio en
[`docs/contracts`](contracts/). En especial:

- ADR-002 conserva el diseño histórico de catálogo/slot; ADR-021 supersede su
  requisito de slot para inferencias nuevas.
- ADR-003 conserva storage local como proveedor actual.
- ADR-004 separa detector y clasificador.
- ADR-009 separa resultados automáticos y humanos.
- ADR-013 define RBAC de Etapa 2.
- ADR-015 impone la comunicación no diagnóstica.
- ADR-017 a ADR-020 cubren ingesta, calidad, detección y clasificación.
- ADR-021 registra la identidad publication-first de la inferencia actual y la
  compatibilidad de snapshots legacy.

## Delivery 2: referencia, no runtime

Los siguientes archivos se conservan por trazabilidad de diseño, pero todos se
clasifican como **`DESIGN_REFERENCE / NOT_RUNTIME`**. Ante una discrepancia,
prevalecen el código, las migraciones, los ADR y esta documentación canónica.

- `architecture/architecture_approval_v1_1.md`
- `architecture/delivery2_analysis_sequences.md`
- `architecture/delivery2_architecture_baseline_v1_1.md`
- `architecture/delivery2_component_diagram.md`
- `architecture/delivery2_container_diagram.md`
- `architecture/delivery2_context_diagram.md`
- `architecture/delivery2_data_model.md`
- `architecture/delivery2_model_governance.md`
- `architecture/delivery2_postgresql_queue_design.md`
- `architecture/delivery2_security_model.md`
- `architecture/delivery2_state_machines.md`
- `architecture/delivery2_storage_design.md`

El borrador `api/delivery2_openapi_v1_draft.yaml` también es material de
revisión y no un contrato runtime publicado.

## Restricciones de evolución

No se reemplaza la historia SQL/Alembic por un baseline nuevo sin aprobación
manual. Tampoco se eliminan artefactos científicos o storage para “limpiar” el
repositorio. Las extensiones deben mantener UUID públicos, auditoría append-only,
operaciones idempotentes y compatibilidad explícita cuando exista una ruta o
import legacy.
