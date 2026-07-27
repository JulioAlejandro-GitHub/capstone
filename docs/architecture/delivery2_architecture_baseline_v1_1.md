# Architecture Baseline v1.1 — Etapa 2

Estado: **APROBADA PARA IMPLEMENTACIÓN POR PROMPTS**, sujeta a los gates de [architecture_approval_v1_1.md](architecture_approval_v1_1.md).

Extensión 2026-07-27: la baseline incorpora `research_subjects`, `scientific_cases`,
`blood_samples`, `smear_slides` y `microscopy_images` como dominio transaccional.
Storage, calidad e inferencia permanecen componentes futuros separados.

Snapshot: `main` en `3c79bb08a36f210c58d7076cf58111d4de554752`. El delta desde `092a237497615ac3f1e775a61c54c6d6417dd515` contiene sólo los siete documentos de Prompt 0; no cambia código ni migraciones. Archivo local previo `complemento e2.txt`: fuera de alcance y no modificado.

## Visión y naturaleza

**Plataforma científica experimental de apoyo al análisis de imágenes microscópicas de frotis sanguíneo.** Produce regiones candidatas, sospecha algorítmica, probabilidades estimadas, hallazgos asistidos por IA y resultados experimentales sujetos a revisión. No es diagnóstico, dispositivo médico, sistema hospitalario ni reemplazo del especialista.

## Alcance

Incluye diseño de ingesta inmutable, QC terminal, cola PostgreSQL, detección, crops, clasificación por célula y modelo, XAI, agregado cuantitativo, review versionado, reports, API/polling, RBAC, auditoría y lineage. No implementa SQL, migraciones, worker, RBCNet, dataset, crops, frontend, cloud, entrenamiento, ensemble, agentes, LIS/HIS o certificación.

## Principios cerrados

1. Monolito modular: FastAPI + React/TypeScript + PostgreSQL + filesystem administrado.
2. API no ejecuta ML pesado; workers reclaman jobs persistentes PostgreSQL.
3. QC precede al job; rejected conserva original/assessment y no detecta.
4. `StorageProvider` con `LocalStorageProvider`; URI lógica y SHA.
5. Detector y clasificador separados; RBCNet sólo adapter detector.
6. Mapping inmutable `0=uninfected`, `1=parasitized`, score `probability_parasitized`.
7. Publicaciones son catálogo; `stage2/default` es único default.
8. Multimodelo presenta resultados paralelos, sin ensemble automático.
9. Original, checkpoint, auto result y artifacts históricos no se sobrescriben; review es append-only.
10. Nuevos datasets se separan por patient_id.
11. Nuevos imports usan `malaria_dl`; adapters `src.*` permanecen en MVP.
12. Grad-CAM automático por predicción salvo limitación registrada; LIME/SHAP priority/on-demand.
13. Polling HTTP en MVP; modelo de estados independiente del transporte.
14. Migraciones futuras usarán Alembic con baseline sobre el estado 029; los SQL 001–029 y sus checksums no se reescriben.

## Arquitectura objetivo y transición

Estado actual verificado: `backend_api/app/main.py` incluye routers; `TraceableInferenceService.infer()` ejecuta síncrono; `quality_control.py` sólo hace checks básicos; `cell_detection` es documental; `image_analysis_jobs` no es cola; publications y deployments no están acoplados.

Objetivo: componentes de [component diagram](delivery2_component_diagram.md) bajo `malaria_dl` canónico, tablas especializadas y API `/api/v1`. Transición aditiva: conservar TRAIN/EVALUATE/EXPLAIN, inference y schemas 001–029; añadir adapters/read models, no escritura dual; ninguna tabla `predictions` representa todo Etapa 2.

## Flujo oficial

Upload → original create-only → assessment QC → si rejected: respuesta inmediata, fin sin job → si accepted: crear/encolar job → claim/lease → detection → boxes progresivas → crops progresivos → assignments de modelos publicados → prediction individual → Grad-CAM y XAI selectivo → aggregate global y por modelo → report → review humana separada. Véanse [secuencias](delivery2_analysis_sequences.md).

## Contratos funcionales

### CellDetector

Entrada: job/image/`storage://`/dimensiones/detector version/config de tile, overlap, confidence y NMS. Salida: detection run, detections `pixel_xywh_top_left_v1`, score, label `rbc`, tile y métricas. Errores: `invalid_image`, `unsupported_image`, `detector_unavailable`, `detector_timeout`, `no_detections`, `partial_detection_failure`, `invalid_coordinates`, `persistence_failed`.

Adapters obligatorios futuros: `AnnotationDetectorAdapter`, `SimulatedDetectorAdapter`, `RBCNetDetectorAdapter`, todos con el mismo contrato. Detector no produce clase parasitized/uninfected.

### Crop Generator

Entrada: image, detection/bbox, URI, crop policy, margin/padding/format. Salida: crop UUID, source/effective bbox, URI, dimensiones, SHA y status. Estados `pending|generating|ready|invalid_bbox|empty_crop|failed|excluded`. Regeneración crea artefacto/fila nuevos.

### Clasificación

Puede batchar para rendimiento, pero persiste una fila por crop/model/run. Guarda model/publication/TRAIN/EVALUATE/checkpoint/SHA/preprocessing/threshold/mapping, ambas probabilidades, label/index, confianza y tiempo. No sobrescribe ni combina modelos.

### Explicabilidad

Cada resultado referencia `cell_prediction_id`, crop y model exactos; métodos `gradcam|lime|shap`; modos `automatic|priority|on_demand`; estados `not_requested|pending|processing|completed|failed|unavailable`. Fallo no invalida prediction. UI muestra crop y contexto original, sin causalidad clínica.

### Agregación

Estados automáticos exclusivos: `completed_no_suspicious_cells`, `completed_with_suspicious_cells`, `manual_review_required`, `inconclusive`, `partial_failure`, `processing_failed`.

Denominadores:

- `% parasitized = parasitized completed / all completed non-low-confidence classifications × 100`.
- `% uninfected = uninfected completed / mismo denominador × 100`.
- `% low confidence = low-confidence completed / total classified × 100`.
- Fallidas/excluded nunca entran como clasificadas; counts siempre se muestran.
- En multimodelo se calcula un resultado por assignment. Un resultado global sólo resume completitud y hallazgos por modelo, no fusiona scores.

Las métricas históricas vienen de EVALUATE y se rotulan como tales.

### Revisión

Review celular: prediction, status (`pending|confirmed|corrected|uncertain|excluded|second_review_requested`), reviewed label, comment, authenticated reviewer, reason y history. Revisión general: `parasitized|uninfected|inconclusive|requires_second_review|excluded`, expresada como revisión experta experimental. No alimenta entrenamiento en esta entrega.

## Estado, datos y storage

Las diez máquinas están en [state machines](delivery2_state_machines.md); modelo completo en [data model](delivery2_data_model.md); cola en [queue design](delivery2_postgresql_queue_design.md); storage en [storage design](delivery2_storage_design.md). Los contratos machine-readable están en `docs/contracts/`.

## API y frontend

El borrador [OpenAPI 3.1](../api/delivery2_openapi_v1_draft.yaml) marca todo endpoint nuevo `x-implementation-status: planned` y `x-required-permissions`. Paginación: cursor opaco + `limit` 1–200; filtros allowlisted; `Idempotency-Key` en commands create/retry/report/XAI. Errores usan el envelope común.

Frontend:

- upload recibe assessment o error `QUALITY_REJECTED`;
- job se consulta por polling 1–3 s con backoff;
- cells se actualiza por cursor/`updated_after`;
- boxes pueden aparecer sin crop; crop sin prediction; prediction sin XAI;
- cada modelo se muestra separado con role/status/error;
- automatic y human result aparecen lado a lado;
- rutas físicas nunca se exponen.

## Modelo común de errores

```json
{"error":{"code":"QUALITY_REJECTED","message":"La imagen no cumple la política mínima de calidad.","details":{},"correlation_id":"uuid","retryable":false}}
```

|Categoría/códigos representativos|HTTP|Retry|Efecto/auditoría|
|---|---:|---|---|
|validation `VALIDATION_ERROR`|422|No|Sin job; request audit mínimo|
|authentication `AUTHENTICATION_REQUIRED`|401|No|Sin cambio; security event|
|authorization `FORBIDDEN`|403|No|Sin cambio; security event|
|conflict `IDEMPOTENCY_CONFLICT`, `PUBLICATION_IN_USE`|409|No|Estado intacto; audit|
|quality `QUALITY_REJECTED`|422|No para policy|Assessment terminal; no job|
|storage `STORAGE_UNAVAILABLE`, `CHECKSUM_MISMATCH`|503/409|Sí/No|Job queued/failed según etapa; audit|
|queue `LEASE_LOST`, `MAX_ATTEMPTS`|409/500|Sí/No|Requeue o failed; event|
|detector `DETECTOR_TIMEOUT`, `NO_DETECTIONS`|504/200 result|Sí/No|Retry/failed o inconclusive|
|crop `INVALID_BBOX`, `CROP_FAILED`|422/500|No/Sí|Cell failed; job partial|
|classifier `MODEL_UNAVAILABLE`, `CLASSIFICATION_FAILED`|503/500|Sí|Assignment partial; job partial/failed|
|explainability `EXPLANATION_UNAVAILABLE`|422/503|Según causa|Prediction intacta; XAI state|
|aggregation `AGGREGATION_FAILED`|500|Sí|Inputs intactos; job partial|
|review `REVIEW_CONFLICT`|409|No|No overwrite; audit|
|report `REPORT_FAILED`|500|Sí|Analysis unchanged|
|internal `INTERNAL_ERROR`|500|Depende|Mensaje público neutro; audit técnico|

Detalle técnico no sensible queda en logs/audit, no en `message`. Resultados parciales se conservan.

## Seguridad, auditoría y reproducibilidad

RBAC aprobado en [security model](delivery2_security_model.md). Toda acción sensible produce audit event. Cada stage conserva los campos mínimos de reproducibilidad listados en Prompt 1 y la cadena completa de [data model](delivery2_data_model.md). Report es artifact versionado con manifest y disclaimer.

## Compatibilidad heredada

Nuevos módulos importan `malaria_dl.*`, nunca adapters raíz. Adapters se mantienen, no renombran/eliminan ni reciben lógica nueva. Consumidores activos: run scripts, DB/dataset scripts, backend y numerosos tests. Transición: Prompt 2 agrega regla de imports y tests de contrato; prompts posteriores migran imports internos sin romper CLIs. Retiro queda fuera MVP y requiere cero imports internos, inventario externo, un release completo de deprecación y suite legacy verde.

## Criterios de aceptación y Definition of Done arquitectónica

- Quince ADR aceptados y sin decisiones críticas abiertas.
- QC rechazado nunca crea job/detection.
- Queue define claim, ordering, lease, retry≤3, recovery, cancel, idempotency y fencing.
- Default siempre referencia publication activa; desactivación en uso se rechaza.
- Data model representa cada vínculo y separa auto/human.
- Bbox único; detector/crop/classification/XAI/aggregate/review contracts validados.
- OpenAPI/JSON/YAML válidos y nombres coherentes.
- RBAC/audit/reproducibility completos.
- Sólo documentación cambia; sin DB, dataset, modelos o endpoints productivos.

## Decisiones cerradas

Todas las decisiones de principios 1–13, rechazo de publicación en uso, máximo tres attempts, `READ COMMITTED + SKIP LOCKED`, roles definidos, tablas especializadas, denominadores y políticas de fallo parcial quedan cerradas.

## Decisiones diferidas no estructurales

|Decisión|Motivo|Prompt|Condición|
|---|---|---|---|
|Valores numéricos QC|Requieren dataset/validación científica|5/7|Golden set y aprobación científica|
|Lease/heartbeat/backoff exactos|Dependen de profiling|6|Benchmarks y fault injection|
|RBCNet técnica/licencia|Fuera de implementación actual|7/8|Fuente/licencia/pesos verificados|
|Thresholds de confianza/OOD|Requieren calibración|10/15|Validation patient-aware|
|Formato PDF/render engine|No afecta modelo de report|15|Requisitos UX/export|
|OIDC proveedor|Entorno académico no especificado|2|Proveedor/claims disponibles|
|Retención temporal de regenerables|Requiere capacidad operacional|4/15|Storage budget y backup policy|

No se difiere ninguna decisión que cambie límites de módulos, identidad, estados o contratos.
