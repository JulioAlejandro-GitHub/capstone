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

Auditoría C2.12: [Integración PostgreSQL y calibración — APROBADO](audits/clinical_calibration_c2_12/README.md)
(`HISTORICAL_AUDIT`, 2026-10-04; cierre operativo C2.12.2: suite E2E real PASSED,
limpieza acreditada, base operativa intacta). Conserva el bloqueo inicial C2.12/C2.12.1
como auditoría histórica; el informe de cierre está en la sección `# Cierre operativo — C2.12`.

| Tema | Documento |
|---|---|
| Desarrollo local | [Desarrollo local](engineering/local_development.md) |
| PostgreSQL Docker-only | [Contrato de instancia PostgreSQL única](engineering/postgresql_docker_single_instance.md) |
| Seguridad de base de datos | [Política de seguridad DB](engineering/database_safety_policy.md) |
| Runtime YOLO local (76.3A) | [Contrato y validación](operations/yolo_runtime.md) |
| Reset de análisis de frotis | [Reset controlado](operations/smear_analysis_reset.md) |
| Purga de datos por subsistema | [Purga por subsistema](operations/subsystem_data_purge.md) |
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

## C2.13 — Validación experimental mini CPU/GPU

- [C2.13 — Preflight C2.13-A](audits/clinical_calibration_c2_13/README.md) — `HISTORICAL_AUDIT`, 2026-10-04.
  Preflight **COMPLETO**, pendiente aprobación explícita del usuario (Option A/B).
  GPU bloqueado (sin Metal); CPU OK. No se han iniciado entrenamientos ni creado campañas.

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

## Auditoría S1.1 de procedencia e identidad

- [S1.1 — TFDS ↔ NLM ↔ Capstone](audits/s1_1/REPORT.md) — `HISTORICAL_AUDIT`, 2026-10-03. Comparación exhaustiva de imágenes y fingerprints; cruces clínicos Polygon/Cell explícitamente no resueltos.

## Preparación reproducible de fuentes S1.D

- [Preparar/verificar Cell y Full Smears](operations/dataset_source_preparation.md) — `CURRENT_DOC`, comandos manuales sin PostgreSQL.
- [S1.D — Implementación y prueba real](audits/s1_d/REPORT.md) — `HISTORICAL_AUDIT`, integridad RAW, idempotencia y límites de `--split`.

- [S1.2 — Canonical NLM Patient Identity](audits/s1_2/REPORT.md) — `HISTORICAL_AUDIT`, 2026-10-03. 193 claves técnicas; Polygon 28/2/3 sobre el split Cell protegido; S2 pendiente.
- [S2 — Thin Blood Smear SAME SPLIT](audits/s2/REPORT.md) — `HISTORICAL_AUDIT`, 2026-10-03. 193 pacientes / 965 imágenes gobernados; versión provisional GENERATED; Polygon 28/2/3, limitaciones científicas y evidencia de integridad. S3 pendiente.
- [S3 — Validation + Dataset Version](audits/s3/REPORT.md) — `HISTORICAL_AUDIT`, 2026-10-03. Misma versión Smear validada/congelada; assignments S2 intactos, manifest reproducible y consumo explícito por S4.

## Auditoría PRE-S4 del flujo de Análisis de Frotis

- [PRE-S4 — Flujo de detección, crops y clasificación](audits/pre_s4_detection_workflow/REPORT.md) — `HISTORICAL_AUDIT`, 2026-10-03. Trazado estático desde SmearUpload hasta el resultado y contrato mínimo para incorporar otro detector.

- [D1 + D2 — Separación de CELL DETECTION y CELL CROP](audits/d1_d2_detection_crop/REPORT.md) — `HISTORICAL_AUDIT`, 2026-10-03. Resolutores mínimos, equivalencia de componentes/PNG/SHA y validación PostgreSQL; gate global pendiente por fallas previas.

## B1 — Entrenamientos históricos y trazabilidad SQL

- [Reporte reproducible B1](../results/benchmarks/cpu_historical/report.md) — `HISTORICAL_AUDIT`, 2026-10-04. Doce configuraciones, 396 épocas y métricas VALIDATION verificadas desde predicciones persistidas; extracción PostgreSQL de solo lectura.
- [Hallazgos científicos y técnicos B1](../results/benchmarks/cpu_historical/HALLAZGOS_B1.md) — `HISTORICAL_AUDIT`, 2026-10-04. Duraciones, EarlyStopping, checkpoints y límites de evidencia CPU/Metal.
- [Consultas y transformaciones B1](../results/benchmarks/cpu_historical/SQL_B1.md) — `HISTORICAL_AUDIT`, 2026-10-04. SQL ejecutado, JOIN, conteos, fórmulas y diagnóstico de fuentes incompletas.

- [Scientific Parameter Registry — C2.11.7](scientific_parameters.md) — `CURRENT_DOC`: diccionario, matriz de dependencias, consumidores y consulta de snapshots efectivos; generado automáticamente.
