# Validación científica: arquitectura y plan de adopción

## Decisión

La sesión de validación es un agregado de trazabilidad, no un pipeline
alternativo. Congela por referencia los artefactos productivos ya persistidos y
agrega el contexto experimental que no existía antes de esta extensión:
protocolo de validación, IoU de matching, selección explícita y digest del
snapshot. No recalcula ni copia detecciones, crops, predicciones, explicaciones
o revisiones.

El backend actual no usa modelos declarativos SQLAlchemy: `app.models` contiene dataclasses/enums de dominio y la persistencia se expresa mediante migraciones Alembic, repositorios y SQL parametrizado. La extensión sigue deliberadamente ese patrón en vez de introducir un segundo estilo ORM.

## Matriz de reutilización

| Funcionalidad | Tabla / servicio / endpoint actual | Reutilizable | Extensión |
|---|---|---:|---|
| Datasource | `app.db`, `DEFAULT_DATASOURCE`, `/datasources` | Sí | La sesión congela la key, no una conexión ni otra base |
| Imagen y muestra | `microscopy_images`, `smear_slides`, `blood_samples`, `scientific_cases`, `research_subjects`; router `scientific` | Sí | Membresía de imagen con FK y checksum congelado |
| Calidad y análisis | `microscopy_analysis_runs`, `microscopy_analysis_run_images`, `image_quality_assessments` | Sí | Se alcanza por lineage; no se duplica |
| Detección | `cell_detection_runs`, `cell_detections`, `image_connected_components`, `cell_crops`; servicio/router `cell_analysis` | Sí | Membresía del run; perfil y versiones van al snapshot |
| Clasificación | `cell_classification_runs`, `cell_classification_inputs`, `cell_predictions`; servicio/router `cell_classification` | Sí | Membresía del run; modelo y threshold productivo van al snapshot |
| Grad-CAM | `cell_explanations`; servicio/router `explainability` | Sí | Ninguna tabla nueva |
| Revisión humana | `scientific_reviews`, `cell_classification_reviews`; workspace `CellReviewWorkspace` | Sí | `scientific_validation_annotations` añade notas versionadas para célula, análisis o muestra sin modificar revisiones automáticas/humanas existentes |
| Resúmenes e historial | `smear_analysis_summaries`, `SmearAnalysisHistory`, hooks de workflow/historial | Sí | La sesión expone IDs para navegación, sin nuevo resumen |
| Autenticación/RBAC | JWT `Principal`, `Permission`, `transactional_permission` | Sí | Cinco permisos `scientific.validation.*`: read, create, update, archive y annotate |
| Auditoría | `audit_events`, `record_event`, transacción compartida | Sí | Eventos create/update/archive del nuevo recurso |
| UI de revisión | `CellReviewWorkspace`, `CellImageViewer`, imágenes autenticadas, galería, filtros, clasificación/Grad-CAM y `ScientificAnnotations` | Sí | La UI consume anotaciones ligadas a sesión o generales; un dashboard de sesiones separado no es requisito del workspace |

## Modelo mínimo nuevo

- `scientific_validation_sessions`: nombre, descripción, datasource, protocolo/version, IoU, estado, actor y timestamps; `initial_snapshot` canónico y `snapshot_sha256` para reproducibilidad.
- `scientific_validation_images`: relación FK a imágenes y orden estable; conserva el SHA-256 observado al crear.
- `scientific_validation_detection_runs`: relación FK a runs de detección existentes.
- `scientific_validation_classification_runs`: relación FK a runs de clasificación existentes.

Las membresías y la identidad del snapshot son inmutables mediante triggers. El
archivado es lógico. Las revisiones `20260810_02`, `20260810_04` y `20260810_05`
añaden `scientific_validation_annotations` y su ledger de eventos; la revisión
intermedia `20260810_03`, sobre comentarios de clasificación humana, es el
`down_revision` efectivo de `20260810_04`. Las anotaciones soportan
targets `cell`, `analysis` y `sample`, dentro de una sesión o como anotación
general. Una actualización incrementa versión y conserva historia; no modifica
detecciones, predicciones ni revisiones científicas previas. Matching, métricas
y errores derivados siguen diferidos hasta disponer de un protocolo validado.

## Snapshot inicial

El servidor deriva y canonicaliza: datasource; protocolo; IoU; IDs y checksums de imágenes; manifiesto, detector/perfil/versiones de detection runs; lineage, modelo/version, snapshot de modelo, threshold y fuente de classification runs. El cliente no puede suministrar snapshots ni actor. No contiene binarios, rutas, storage keys ni PII.

## Endpoints

- `POST /api/v1/scientific-validation/sessions`: crea selección y snapshot atómicamente.
- `GET /api/v1/scientific-validation/sessions`: lista paginada y filtrable por estado.
- `GET /api/v1/scientific-validation/sessions/{id}`: detalle, selección y snapshot.
- `PATCH /api/v1/scientific-validation/sessions/{id}`: nombre, descripción y transición válida.
- `DELETE /api/v1/scientific-validation/sessions/{id}`: archivado lógico auditado.

Anotaciones de una sesión:

- `POST/GET /api/v1/scientific-validation/sessions/{id}/annotations`;
- `GET/PATCH /api/v1/scientific-validation/sessions/{id}/annotations/{annotation_id}`;
- `GET /api/v1/scientific-validation/sessions/{id}/annotations/{annotation_id}/history`.

Anotaciones generales, no ligadas a una sesión:

- `POST/GET /api/v1/scientific-annotations`;
- `PATCH /api/v1/scientific-annotations/{annotation_id}`;
- `GET /api/v1/scientific-annotations/{annotation_id}/history`.

Todas requieren los permisos `scientific.validation.read` o
`scientific.validation.annotate` correspondientes. No existe DELETE de
anotaciones.

Estados: `draft → annotation_in_progress → ready_for_analysis → completed`; se admite volver de `ready_for_analysis` a anotación. Cualquier estado no archivado puede archivarse. Una sesión completada no cambia sus metadatos salvo archivado.

## Riesgos y controles

- Runs o imágenes incompatibles: creación valida existencia, estado terminal, lineage clasificación→detección y presencia de imágenes.
- Drift: FKs `RESTRICT`, snapshots preexistentes y digest canónico conservan reproducibilidad.
- Borrado/edición accidental: selección append-only, identidad congelada y archivado lógico.
- Threshold ambiguo: se toma exclusivamente de `cell_classification_runs.model_snapshot`, nunca del estado productivo actual.
- Escala del JSON: contiene manifiestos de identidad, no predicciones por célula; éstas permanecen normalizadas.
- Evolución del protocolo: key/version son obligatorios y el schema del snapshot tiene versión.

## Plan de migración

1. La fundación de sesiones se introdujo en `20260810_01` sobre
   `20260728_03`; anotaciones y sus extensiones están en la cadena lineal
   `20260810_02 → 20260810_03 → 20260810_04 → 20260810_05`.
2. El head versionado actual es `20260812_02`. Operación y despliegue deben
   validar `current=head`; `20260810_01` no es el head operativo actual.
3. Verificar tablas, FK, checks, índices y triggers; estas revisiones no
   requieren backfill de resultados científicos históricos.
4. Los roles reciben permisos mediante el mapa de aplicación, sin mutar roles
   en PostgreSQL. Crear sesiones nuevas sólo desde runs terminales; no importar
   ni recalcular datos históricos.
5. Matching y snapshots de métricas siguen siendo fases posteriores y deberán
   tener contratos y migraciones propios.
6. No ejecutar downgrade sobre la base Capstone. Cualquier reversión destructiva
   requeriría primero preservar/exportar la trazabilidad existente.
