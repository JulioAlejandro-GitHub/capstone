# Backlog derivado de auditoría

Estimación relativa: XS, S, M, L, XL. No representa horas ni fechas.

|Épica|Tipo|Ítem|Prioridad|Est.|Dependencias|Criterio de aceptación|Evidencia esperada|
|---|---|---|---|:---:|---|---|---|
|E0 Arquitectura|Decisión cerrada|ADR fuente de verdad Productivo Etapa 2/default/rollback|Crítica|M|—|Aprobado: catálogo multi-modelo + default único|ADR-002 + baseline v1.1|
|E0|Decisión cerrada|ADR monolito modular, límites y lenguaje no diagnóstico|Crítica|S|—|Aprobado|ADR-015 + baseline v1.1|
|E0|Decisión cerrada|Cola PostgreSQL, polling y recuperación|Crítica|M|—|Aprobado: SKIP LOCKED, lease, tres intentos|ADR-001/006/008|
|E0|Decisión cerrada|StorageProvider e inmutabilidad|Crítica|M|—|Aprobado: LocalStorageProvider|ADR-003|
|E0|Spike|Licencia/contrato RBCNet y NIH/NLM|Alta|M|—|Uso permitido y formatos confirmados|Nota de evidencia primaria|
|E1 Fundación|Tarea implementada|Baseline Alembic en migración 029|Alta|L|E0|Up en BD efímera sin reescribir historia|Baseline + adoption verifier|
|E1|Tarea implementada|Settings validados y perfiles local/test/demo|Alta|M|E0|Sin defaults a DB personal|Config tests|
|E1|Historia parcial|Autenticación académica y RBAC|Crítica|XL|E0|Cinco roles, JWT y guards; auditoría completa diferida|API auth matrix|
|E1|Tarea implementada|JSON logging + correlation propagation|Alta|M|Settings|Request correlacionable|Log fixture|
|E1|Superada|Docker/Compose API y PostgreSQL|—|—|Decisión Prompt 2.2.1|Fuera de arquitectura operativa|No aplica|
|E1|Tarea implementada|CI test/build/Alembic/ML rápido|Alta|L|Alembic|PR gate sin BD del usuario|Workflow|
|E2 Dominio|Historia|Subjects pseudonimizados, samples, slides|Crítica|L|Alembic/auth|Constraints y audit, sin PII|Migration/API tests|
|E2|Historia|Lab, microscope, camera, capture session|Alta|M|samples|Snapshots de captura|Schema tests|
|E2|Historia|Full smear images y relación 1:N|Crítica|L|subjects/storage ADR|Original identity estable|Migration tests|
|E2|Historia|Policies/pipeline versions y audit events|Crítica|L|E0|Snapshots versionados + append-only|Trigger tests|
|E2|Decisión|Nuevas tablas vs `predictions`|Crítica|S|E0|Se aprueban detections/crops/cell predictions/results|ADR|
|E3 Storage|Historia|FilesystemStorageProvider|Crítica|L|E1,E2|Put immutable/open/stat/checksum/URI|Contract tests|
|E3|Historia|Upload streaming seguro e idempotente|Crítica|L|Provider/auth|MIME/size/bomb/traversal/duplicate cubiertos|Security tests|
|E3|Tarea|Retención y clasificación regenerable/inmutable|Alta|M|Provider|Policy aplicada sin borrar original|Policy test|
|E4 Calidad|Historia|Assessment persistente y policy versionada|Crítica|L|Full image|Resolution/blur/brightness/contrast/exposure/saturation|Golden fixtures|
|E4|Historia|Gate reject/warn/pass antes de detector|Crítica|M|Assessment/jobs|Rejected visible y no detectado|Pipeline test|
|E4|Spike|Contenido útil y densidad celular|Media|M|Dataset|Método y límites científicamente documentados|Evaluation note|
|E5 Jobs|Historia|Priority 1–100 y claim order|Crítica|M|Schema/queue ADR|Orden exacto y concurrent claim seguro|Concurrency tests|
|E5|Historia|Worker, lease, heartbeat, attempts y retry|Crítica|XL|Broker/storage|Crash/restart recuperable|Fault injection|
|E5|Historia|Progress, cancellation, partial failure|Alta|L|Worker|Estado por etapa y cancel cooperativa|API/E2E tests|
|E5|Historia|Idempotencia pipeline completa|Crítica|L|Jobs/storage|Repetición no duplica outputs|E2E test|
|E6 Dataset|Historia|Ingest NIH/NLM sin incluir binarios en Git|Crítica|L|Storage/licencia|Checksums/provenance/licencia|Manifest|
|E6|Historia|Parsers Point Set y Polygon Set|Crítica|L|Fixtures|Conversión validada a coordenadas comunes|Golden tests|
|E6|Historia|Split por patient_id|Crítica|M|Subject mapping|Intersección pacientes vacía|Leakage test|
|E6|Historia|Manifest/export detector versionado|Crítica|M|Parsers/split|Reproducible byte-for-byte|Snapshot test|
|E7 Detector|Historia|Contrato `CellDetector` y fake|Crítica|M|Coordinates|Fake ejecuta pipeline sin pesos|Contract/E2E|
|E7|Historia|Tiling/overlap/global transform/NMS|Crítica|XL|Full image|Cobertura, borde e IoU probados|Property/golden tests|
|E7|Historia|RBCNet adapter|Alta|XL|Spike/contract|No clasifica; registra versión/weights|Adapter tests|
|E7|Historia|Detection runs/detections y métricas|Crítica|L|Schema/dataset|mAP/recall/IoU por split|Evaluation report|
|E8 Crops|Historia|Crop generator con padding/bordes|Crítica|L|Detections/storage|Crops deterministas|Pixel/golden tests|
|E8|Historia|Crops trazables e inmutables|Crítica|M|Provider|Original+bbox+policy+checksum|Lineage test|
|E9 Classifier|Historia|CellClassifier batch adapter|Crítica|L|Crops/default|Reutiliza modelo vigente|Regression tests|
|E9|Historia|Threshold/preprocessing/cache/provenance|Crítica|M|Governance|Snapshot completo por run|Integrity tests|
|E9|Historia|Incertidumbre y ranking|Alta|M|Predictions|Policy versionada y estable|Metric tests|
|E9|Spike|OOD baseline|Baja|M|Classifier|Decisión basada en datos|Spike report|
|E10 Resultados|Historia|Agregación por imagen no diagnóstica|Crítica|L|Detector/classifier|Denominador/método/version visibles|Scientific tests|
|E10|Historia|Manifest E2E|Crítica|M|Todos runs|Reproduce artefactos/decisiones|Manifest validation|
|E11 XAI|Historia|Grad-CAM automático selectivo|Alta|M|Crops/ranking|Policy y presupuesto respetados|Worker tests|
|E11|Historia|LIME/SHAP prioritario/on-demand|Media|L|Jobs/auth|Autorizado, idempotente, cancelable|API/E2E|
|E11|Historia|Contexto original + crop + XAI|Alta|M|Coordinates|Alineación visual probada|Visual regression|
|E12 Review|Historia|Review/anotaciones append-only|Crítica|XL|Auth/results|Auto intacto; humano versionado|Audit tests|
|E12|Historia|Auditoría before/after y firma experta|Crítica|L|RBAC|Actor autenticado y transición válida|Security tests|
|E13 Workbench|Historia|Menú/lista/nueva muestra|Alta|L|APIs/auth|Paginación, loading/error, accesibilidad|Component/E2E|
|E13|Historia|QC/progreso|Alta|M|QC/jobs|Estado observable y reintento permitido|E2E|
|E13|Historia|Viewer pan/zoom/overlays/filtros|Alta|XL|Tiles/detections|Boxes alineadas a todo zoom|Browser tests|
|E13|Historia|Inspector/carrusel/review/XAI|Alta|XL|Review/XAI|Flujo teclado y provenance visible|Accessibility E2E|
|E14 Reportes|Historia|Manifest + HTML/PDF versionado|Alta|L|Review/result|Disclaimer y versiones visibles|Golden report|
|E14 Agentes|Decisión|Tools read-only, aprobación y prohibición diagnóstica|Alta|M|Auth/audit|Agente no muta resultado ni diagnostica|Policy/red-team tests|
|E14 Validación|Tarea|Métricas clasificador/detector/E2E|Crítica|XL|Pipeline|Protocolos por paciente aprobados|Evaluation package|
|E14 Operación|Tarea|Readiness, backup/restore y runbook|Alta|L|Infra|Restore drill y degradación documentada|Runbook log|

## Decisiones diferidas no estructurales

Los ADR de E0 están cerrados. Se difieren valores numéricos QC, lease/backoff exactos, licencia/adapter RBCNet, thresholds de confianza/OOD, retención temporal y motor de PDF hasta sus prompts y evidencia de datos/profiling. La política multimodelo, XAI, review y report ya tiene contrato estructural.
