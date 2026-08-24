# Índice y estado de la documentación

Última revisión: 2026-08-24

Estado documental: `CURRENT_DOC` — índice canónico.

Este directorio contiene tanto documentación operativa vigente como decisiones y
evidencia histórica. Que un archivo exista aquí no significa que sus comandos deban
ejecutarse en el entorno actual.

## Estados documentales

| Estado | Significado | Uso |
|---|---|---|
| `CURRENT_DOC` | Describe el contrato o procedimiento vigente | Puede usarse operativamente |
| `OPTIONAL_CAPABILITY` | Describe una capacidad soportada que no es la ruta productiva canónica | Usar sólo cuando la capacidad sea requerida |
| `LEGACY_REQUIRED` | Conserva compatibilidad o una decisión anterior aún relevante | No usar como fuente de verdad del flujo nuevo |
| `HISTORICAL_AUDIT` | Evidencia fechada de un estado anterior | Sólo auditoría y trazabilidad |
| `HISTORICAL_DESIGN` / `NO_RUNTIME_CONTRACT` | Contrato o diseño previo que no describe el runtime | Comparación arquitectónica; no generar clientes ni validar tráfico |
| `SUPERSEDED` / `OBSOLETE_DOC` | Fue reemplazado por otra fuente | No ejecutar; seguir el reemplazo indicado |

Los banners dentro de cada documento prevalecen sobre su nombre o ubicación.

## Fuentes operativas canónicas

| Tema | Documento |
|---|---|
| Desarrollo local | [Desarrollo local](engineering/local_development.md) |
| PostgreSQL local | [Instancia PostgreSQL única](engineering/postgresql_local_single_instance.md) |
| Seguridad de base de datos | [Política de seguridad DB](engineering/database_safety_policy.md) |
| Alembic | [Política Alembic](engineering/alembic_simple_policy.md) |
| Autenticación y permisos | [Autenticación y RBAC](engineering/authentication_rbac.md) |
| API científica | [API científica](engineering/scientific_api.md) |
| Dataset Versions en la UI | [Dataset gobernado](dataset_ui_governed_versions.md) |
| Auditoría segura de Malaria Patient Split v1 | [Runbook del split](runbook_split_completo_malaria.md) |
| TRAIN/EVALUATE gobernado | [Guía de entrenamiento](guia_entrenamiento_patient_split.md) |
| Entrenamiento productivo Stage 2 | [Tarjeta productiva Stage 2](stage2_productive_training_card.md) |
| Ingesta y almacenamiento | [Ingesta](architecture/microscopy_image_ingestion.md) y [storage local](engineering/local_storage.md) |
| Revisión de células | [Workspace de revisión](architecture/cell_review_workspace.md) |

La regla de elegibilidad para publicar un candidato es únicamente
`TRAIN completed + EVALUATE completed`. La acción vigente **Publicar y desplegar**
también comprueba que el artefacto y su contrato técnico permitan completar de forma
segura el deployment, smoke test e inferencia. Esas comprobaciones son precondiciones
de habilitación técnica; no agregan criterios científicos a la elegibilidad.

## Capacidades opcionales y de compatibilidad

- [Preparación de releases desde Ejecuciones](executions_prepare_release_api.md),
  [inventario y liberación](model_release_process.md) y
  [deployment/inferencia por alias](model_deployment_and_inference.md) describen
  capacidades vigentes. No cambian la elegibilidad mínima Stage 2, aunque la
  habilitación técnica sí debe fallar si el artefacto, contrato, threshold o smoke no
  permiten desplegar e inferir con seguridad.
- Los documentos `four_step_model_production_flow.md`,
  `simplified_model_production_flow.md`, `relaxed_technical_production_flow.md` y
  `stage2_model_availability.md` son contratos `LEGACY_REQUIRED` mantenidos para
  compatibilidad. Sus banners indican cuál es la fuente productiva actual.
- [Diseño histórico del schema de gobernanza](model_governance_schema.md) conserva
  equivalencias y trazabilidad, pero no debe ejecutarse como runbook de migración.

## Contratos de diseño e historia

- `architecture/delivery2_*`, `api/delivery2_openapi_v1_draft.yaml` y
  `contracts/*.json` son artefactos de diseño históricos. El contrato HTTP de runtime
  es el OpenAPI generado por FastAPI.
- Los documentos `prompt*`, auditorías, reportes finales e inventarios fechados son
  snapshots. Pueden mencionar rutas, revisiones Alembic o capacidades que después
  cambiaron.
- Los ADR se preservan como historia de decisiones. Un ADR marcado `LEGACY_REQUIRED`
  o sustituido no debe reescribirse como si siempre hubiera descrito el estado actual.

## Reglas de seguridad documental

- No detener, reconstruir ni reemplazar PostgreSQL siguiendo un snapshot histórico.
- No truncar el schema `public` ni eliminar Dataset Versions, lineage, auditoría,
  materializaciones o `alembic_version` desde una guía obsoleta.
- No borrar materializaciones `FROZEN`, artefactos científicos, runs ni migraciones.
- Antes de ejecutar un comando, comprobar que el documento está marcado
  `CURRENT_DOC` o listado como fuente operativa en este índice, y que coincide con la
  configuración del repositorio.
