# Análisis de gaps de Entrega 2

Clasificación: A reutilizar sin cambios; B extender; C adaptar; D refactorizar; E reemplazar; F crear; G compatibilidad heredada; H diferir. Estados: R reutilizable, P parcial, A adaptador, C conflicto semántico, N no existe, H fuera de MVP. Evidencia transversal: migraciones `db/init/001–029`, paquete `src/malaria_dl`, API `backend_api/app`, UI `frontend/src` y tests homónimos. “Sin test” significa que la búsqueda del inventario no encontró una prueba de la capacidad, no que una ruta nominal garantice funcionamiento.

|ID|Requisito|Estado actual|Evidencia en código|Tests|Gap|Clase|Cambio requerido|Riesgo|Dependencia|Criterio de aceptación futuro|Prompt/release|
|---:|---|---|---|---|---|:---:|---|---|---|---|---|
|1|Paciente pseudonimizado|N|Sin tabla/código|Sin test|Identidad|F|Crear subject/pseudonym|Alto datos|ADR/BD|Sin PII; ID estable y auditado|P3|
|2|Muestras|N|Sin `samples`|Sin test|Dominio|F|Entidad y API|Alto|1|CRUD gobernado y lineage|P3|
|3|Láminas|N|Sin `slides`|Sin test|Dominio|F|Entidad ligada a muestra|Alto|2|1:N y constraints|P3|
|4|Laboratorio|N|Sin tabla|Sin test|Proveniencia|F|Catálogo versionado|Medio|3|Snapshot de captura|P3|
|5|Microscopio|N|Sin tabla|Sin test|Proveniencia|F|Dispositivo|Medio|4|Marca/modelo/ID auditables|P3|
|6|Cámara|N|Sin tabla|Sin test|Proveniencia|F|Dispositivo|Medio|4|Metadata capturada|P3|
|7|Imágenes completas|N|Sólo `dataset_split_images` de células|Browser|Semántica|F|`full_smear_images`|Crítico|2–6,13|Original distinguible e inmutable|P3–4|
|8|Múltiples imágenes/muestra|N|Sin sample|Sin test|Relación|F|FK e índices|Alto|2,7|1:N probado|P3|
|9|Upload|P|`inference/uploads.py` para predicción|Uploads parciales|No frotis/límites|D|Endpoint streaming seguro|Crítico seguridad|7,13,78|MIME, tamaño, checksum, atomicidad|P4|
|10|Checksum|R|`governance/releases.py:sha256_file`; artifacts|Gobierno|No universal|B|Aplicar al ingreso|Alto|13|SHA-256 obligatorio y verificado|P4|
|11|Duplicados|P|Checksums opcionales registry|Registry|Sin política frotis|B|Unique/política por bytes|Medio|7,10|Detección idempotente explícita|P4|
|12|Original inmutable|P|Releases sí; uploads no contrato global|Release tests|Falta original|B|Write-once + eventos|Crítico|7,13|No overwrite/delete lógico auditado|P4|
|13|StorageProvider|N|Paths directos en common/artifacts|Path tests|Acoplamiento FS|F|Interfaz filesystem-first|Crítico|ADR|URI lógica, stat/open/put immutable|P4|
|14|Control de calidad|P|`quality_control.py`|`test_image_quality.py`|Métricas/gate|B|Servicio de assessment|Alto científico|7,15|Resultado persistido y reproducible|P5|
|15|Política QC versionada|N|Thresholds literales|Sin test|Reproducibilidad|F|Policy ID+snapshot|Alto|14|Version/checksum en assessment|P5|
|16|Rechazo antes detector|N|Inferencia ignora QC|Sin test|Gate|F|Estado/gate explícito|Crítico|14,18|Rejected nunca encola detector|P5–6|
|17|Rechazados visibles/anotables|N|Sin UI/review|Sin test|UX|F|Lista y anotación|Medio|16,56|Visible con razón y review|P13–14|
|18|Analysis jobs|P|Tabla `image_analysis_jobs`|Gobierno/E2E opt-in|No pipeline completo|D|Evolucionar + attempts/events|Crítico|3–7|Job por imagen, snapshot pipeline|P6|
|19|Prioridad 1–100|N|Sin columna priority|Sin test|Scheduling|F|Constraint 1–100|Alto|18|Validación API/DB|P6|
|20|Orden prioridad/creación|N|Índice status/created DESC|Sin test|Orden incorrecto|F|Índice/claim query|Alto|19|`priority DESC, created_at ASC`|P6|
|21|Cola persistente|N|Sin broker/claim loop|Sin test|Ejecución|F|Cola PostgreSQL aprobada por ADR-001|Crítico|18|Sobrevive reinicio|P2,6|
|22|Worker|N|Sin proceso worker|Sin test|Ejecución|F|Worker separado|Crítico|21|Consume y heartbeat|P6|
|23|Progreso|N|Sólo estados terminales|Sin test|Observabilidad|F|Etapas/%/events|Alto|18,22|Monótono y consultable|P6|
|24|Reintentos|N|Sin attempt/max retries|Sin test|Resiliencia|F|Attempts/backoff|Alto|22|Retry acotado y auditado|P6|
|25|Cancelación|P|Estado admite cancelled|Sin comportamiento|No señal/endpoint|B|Cancel requested/cooperativa|Medio|22|No inicia nuevas etapas|P6|
|26|Recuperación|N|Sin leases/heartbeat|Sin test|Stale jobs|F|Lease y requeue|Crítico|21,22|Recupera worker muerto|P6|
|27|Idempotencia|P|Key por inference run|Repository tests|Scope débil|B|Clave ingest/pipeline|Alto|18|Mismo request no duplica outputs|P6|
|28|Fallos parciales|N|Job completo/failed|Sin test|Granularidad|F|Etapas/attempts y artifacts válidos|Alto|18|Reanuda desde checkpoint|P6|
|29|Detector desacoplado|N|Sólo frontera documental|Sin test|Contrato|F|`CellDetector`|Crítico|ADR,87|Implementaciones intercambiables|P8|
|30|RBCNet Adapter|N|No RBCNet|Sin test|Integración|C|Adapter aislado|Alto licencia|29,87|Boxes normalizadas + provenance|P8|
|31|Adapter anotaciones|N|Sin parsers|Sin test|Fallback|F|Point/Polygon adapter|Alto datos|87–89|Ground truth al contrato detector|P7–8|
|32|Detector simulado|N|Sin fake|Sin test|Smoke|F|Determinista fixture|Medio|29|Pipeline E2E sin pesos|P8|
|33|Tiling|N|Sin código|Sin test|Escala|F|Tiler versionado|Alto|7,29|Cobertura completa|P8|
|34|Solapamiento|N|Sin código|Sin test|Bordes|F|Policy overlap|Alto|33|Sin gaps y manifest|P8|
|35|Coordenadas globales|N|Sólo columnas bbox|Sin test|Transformación|F|Transform contract|Crítico|33|Round-trip probado|P8|
|36|NMS|N|Sin código|Sin test|Duplicados detección|F|NMS configurable|Alto|35|IoU/threshold versionados|P8|
|37|Bounding boxes|P|Campos en `predictions`|Constraints SQL|Entidad incorrecta|D|Tabla `detections`|Crítico|29|xyxy/space/version explícitos|P3,8|
|38|Detection runs|N|Sin entidad|Sin test|Proveniencia|F|Run especializado ligado a job|Alto|18,29|Modelo/config/Git registrados|P3,8|
|39|Crop Generator|N|Sin código|Sin test|Pipeline|F|Servicio puro|Crítico|37|Crop por detection|P9|
|40|Padding/bordes|N|Sin código|Sin test|Calidad crop|F|Policy versionada|Alto|39|Dimensión y padding probados|P9|
|41|Crops trazables|N|`crop_artifact_id` reservado|SQL parcial|Sin artefacto|F|`cell_crops` + checksum|Crítico|13,39|BBox/original/checksum lineage|P9|
|42|Modelo Productivo E2|C|Publication y deployments divergentes|Gobierno/API/UI|Dos fuentes|D|Unificar catálogo/default|Crítico|ADR|Una definición transaccional|P1,10|
|43|Modelo default|P|deployment `stage2/default`; publicaciones sin default|Deployment tests|Ambigüedad UI|D|Slot único inferible|Crítico|42|Resolución determinista|P1,10|
|44|Checkpoint inmutable|R|model version/artifact FK, SHA, triggers|Amplia|Aplicarlo pipeline|A|Reusar identidad|Bajo|42|Bytes y checksum bloqueados|P10|
|45|Threshold calibrado|R|`run_threshold_calibration`|Amplia|Default 0.5 permitido|B|Policy de selección E2|Alto científico|42|Fuente/calibración visibles|P10|
|46|Preprocessing versionado|P|snapshot en model/deployment/release|Gobierno|No pipeline version entity|B|Snapshot checksum|Medio|42|Exacto por classification run|P10|
|47|Clasificación batch|P|predictor/TTA; traceable single|ML tests|No crops batch|C|Adapter batch al clasificador|Alto|41–46|Batch determinista y persistido|P10|
|48|Incertidumbre|P|low confidence/case selection|Explain tests|No contrato E2|B|Score/margen/entropía|Alto|47|Ranking versionado|P10–11|
|49|OOD|N|Sin detector OOD|Sin test|Método científico|H|Spike; fuera MVP salvo baseline|Medio|47|Policy y validación si se activa|P15|
|50|Agregado por imagen|N|Job tiene counts opcionales|Sin test|Resultado|F|`image_level_results`|Crítico|47|Método/version/denominador|P11|
|51|Estado automático no diagnóstico|P|Warnings técnicos en servicios|UI tests|No entidad resultado|B|Vocabulario/constraint|Crítico científico|50|Nunca etiqueta diagnóstico|P11|
|52|Grad-CAM automático|P|Implementado batch|XAI tests|No worker/crop|C|Adapter y policy|Alto cómputo|41,48|Genera casos configurados|P12|
|53|LIME prioritario|P|Algoritmo existe|XAI tests|No prioridad|C|Task selectiva|Alto cómputo|48,21|Sólo casos policy|P12|
|54|SHAP prioritario|P|Algoritmo existe|XAI tests|No prioridad|C|Task selectiva|Alto cómputo|48,21|Sólo casos policy|P12|
|55|XAI bajo demanda|N|API sólo lectura|Sin test|Command path|F|Endpoint/job autorizado|Alto seguridad|52–54,78|Idempotente/cancelable/auditado|P12|
|56|Revisión por célula|N|Campos review en predictions|SQL constraints|No versionado/API|F|Review + annotation|Crítico|41,78|Auto intacto, humano versionado|P13|
|57|Revisión de frotis|N|Sin entidad|Sin test|Workflow|F|Expert review|Crítico|50,56|Estado/firma/actor|P13|
|58|Anotaciones por célula|N|Sólo reviewed_label plano|Sin test|Historial|F|Annotations append-only|Alto|56|BBox/label/comment versionados|P13|
|59|Anotaciones generales|N|Sin tabla|Sin test|Review|F|Annotation scope image/sample|Medio|57|Historial consultable|P13|
|60|Automático inmutable|P|Releases sí; predictions mutables|Gobierno|Sin protección resultado|B|Append-only/version|Crítico|50|No UPDATE de resultado|P13|
|61|Humano versionado|N|Campos planos sobrescribibles|Sin test|Auditoría|F|Review revisions|Crítico|56|Cada corrección nueva versión|P13|
|62|Auditoría before/after|P|Gobierno audit/events|Governance|No general|B|Audit events transversal|Crítico seguridad|78|Actor autenticado + before/after|P13|
|63|Reportes|P|Componentes UI “reports” de runs|Frontend static|No reporte frotis|F|Manifest+HTML/PDF derivado|Alto|50,57|Versionado/no diagnóstico|P15|
|64|Manifest reproducibilidad|P|Releases/manifests|Release tests|No pipeline image|B|Manifest pipeline agregado|Crítico|18,38,47|Modelos/policies/Git/checksums|P11|
|65|Menú Frotis|N|`navigationConfig.ts`|Navigation tests|Sin sección|F|Grupo y rutas|Medio|66–76|Accesible/roles|P14|
|66|Lista muestras paginada|N|Sin página/API|Sin test|Workbench|F|API+tabla|Medio|2|Paginación/filter estable|P14|
|67|Nueva muestra|N|Sin página/API|Sin test|Ingesta|F|Formulario accesible|Alto datos|1–9|Validación y consentimiento académico|P14|
|68|Pantalla calidad|N|Sin UI/API|Sin test|Visibilidad|F|Assessment UI|Medio|14–17|Métricas/policy/razón|P14|
|69|Progreso|N|Sin UI|Sin test|Operación|F|Polling de job|Medio|23|Etapa, %, retry/error|P14|
|70|Visor científico|N|Sólo imágenes dataset|Browser tests|Sin whole slide|F|Viewer especializado|Alto UX|7,37|Imagen y overlays sincronizados|P14|
|71|Pan/zoom|N|Sin librería/componente|Sin test|Viewer|F|Canvas/tile viewer|Alto|70|Interacción fluida/accesible|P14|
|72|Overlays/boxes|N|Sin componente|Sin test|Viewer|F|Overlay coords globales|Crítico|35,70|Boxes alineadas a todo zoom|P14|
|73|Filtros|P|Filtros en páginas existentes|Frontend tests|No células|B|Filtros sospecha/review/score|Medio|47,56|URL compartible|P14|
|74|Carrusel/panel celular|N|Sin componente|Sin test|Review UX|F|Virtualized list|Medio|41|Orden por prioridad|P14|
|75|Inspector celular|N|Sin componente|Sin test|Review UX|F|Crop/pred/XAI/review|Alto|52–58|Proveniencia visible|P14|
|76|Contexto + explicación|N|Galería sólo artefactos|Sin test|Composición|F|Vista dual|Alto científico|35,52|BBox original junto a mapa|P14|
|77|Modelos/checkpoints visibles|R|Run/model/deployment pages|Frontend tests|Integrar Workbench|B|Mostrar snapshots|Bajo|42|IDs/version/checksum sin path|P14|
|78|Autenticación|N|Sin middleware|Sin test|Control acceso|F|OIDC/local académico|Crítico|ADR|Identidad verificada|P2|
|79|Roles|N|Actor cliente|Sin test|Autorización|F|RBAC|Crítico|78|Expert/publisher separados|P2|
|80|Seguridad archivos|P|Artifact/dataset path confinement|API tests|Upload size/MIME|B|Storage + streaming validation|Crítico|9,13|Traversal/MIME/bomb tests|P4|
|81|Observabilidad|P|health/errors/logs|API tests|Sin worker metrics|B|Metrics/jobs/readiness|Alto operación|22|SLO técnicos consultables|P2,6|
|82|Logging estructurado|N|Print/DB logs heterogéneos|Sin test|Correlación|F|JSON logging|Medio|83|Campos estándar, sin secretos|P2|
|83|Correlation ID|P|Header sólo en algunas acciones|Gobierno parcial|No middleware|B|Middleware/propagación|Alto auditoría|82|Request→job→run→artifact|P2|
|84|Docker|N|Sin Dockerfile/Compose|N/A|Reproducibilidad|F|Imágenes API/worker/UI|Alto|21,22|Build y health reproducibles|P2|
|85|CI|N|Sin workflows|N/A|Gate automático|F|Lint/test/build sin DB real|Alto|2|PR gates y E2E efímero|P2|
|86|Config local/test/demo|P|`.env.example`, dos venvs|Validate|Defaults divergentes|D|Settings tipados/perfiles|Alto|2|Sin secretos y misma semántica|P2|
|87|Dataset NIH/NLM|N|TFDS células únicamente|Dataset tests|Fuente nueva|F|Ingesta controlada|Crítico datos|1,13|Provenance/licencia/checksum|P7|
|88|Parser Point Set|N|Sin parser|Sin test|Anotaciones|F|Parser + fixtures|Crítico|87|Conversión determinista|P7|
|89|Parser Polygon Set|N|Sin parser|Sin test|Anotaciones|F|Parser + fixtures|Crítico|87|Polígono/box validados|P7|
|90|Split patient_id|N|Split seed por imagen|Registry tests|Leakage|E|Nuevo splitter patient-aware|Crítico científico|1,87|Cero paciente entre splits|P7|
|91|Manifest versionado|P|Registry/release manifests|Dataset tests|Sin patient/annotations|B|Manifest NIH completo|Crítico|87–90|Hash, parser, seed, split|P7|
|92|Métricas detector|N|Sin detector|Sin test|Evaluación|F|mAP/recall/IoU protocolo|Crítico|29,87|Por split paciente|P8|
|93|Métricas clasificador|R|Clinical metrics/calibration|Amplia|Aplicar a crops/patient split|B|Evaluation adapter|Alto|41,90|Sens/spec/F2/calibración|P10|
|94|Métricas end-to-end|N|Sin pipeline|Sin test|Ciencia|F|Protocolo imagen/muestra|Crítico|50,92,93|Error propagado y CI|P15|
|95|Restricciones agentes IA|N|Sin agentes/policy|Sin test|Gobierno|H|Policy/read-only tools/approval|Crítico alcance|62,78|No diagnostican ni mutan sin autorización|P15|

## Lectura consolidada

- Reutilización fuerte: gobierno de artefactos/checkpoints, mapping clínico, calibración, métricas, XAI, lineage, API/UI de experimentos.
- Extensión segura: checksums, manifests, dataset registry, correlation ID, observabilidad y XAI adaptado a crops.
- Creación neta: dominio de muestras, storage abstraction, cola/worker, detector, crops, agregación, revisión y workbench.
- Conflictos que deben resolverse antes de implementar: doble identidad “Productivo Etapa 2”, `predictions` sobrecargada y split actual por imagen.
