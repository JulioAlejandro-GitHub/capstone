# PRE-S4 — Flujo actual de Análisis de Frotis

Estado documental: `HISTORICAL_AUDIT` — snapshot del código, 2026-10-03.

Commit inspeccionado: `dfc96215968b25794f98fb69e8f7e462a9827e13`. Auditoría estática de solo lectura sobre la aplicación y el esquema versionado. No se consultó ni modificó la BD, no se ejecutó inferencia, entrenamiento, S4, migraciones, commit ni push. Los únicos cambios son este reporte y su índice. No se inspeccionó `malaria_dataset_split_project`. Las referencias siguientes apuntan al código; las recomendaciones se distinguen del comportamiento observado.

## 1. Resultado principal

**Sí: podemos incorporar YOLO26-seg como otro detector y conservar la clasificación, predicción, agregación y presentación actuales.** No basta con sustituir una función que devuelva `bbox`: el contrato actual entrega **componentes y crops PNG**, y la persistencia exige un componente por detección. La generación del crop rectangular ya funciona, pero está embebida en `connected_components_v1.detect_image`; para compartirla conviene extraer ese bloque sin cambiar su comportamiento. No hay necesidad demostrada de nuevas tablas o migraciones para esta integración mínima.

El orquestador secuencial real es **`useSmearAnalysisWorkflow` en el frontend**. `SmearWorkflowService` consulta y reconstruye estados; no dispara el pipeline. Calidad, detección y clasificación se ejecutan por peticiones HTTP separadas que esperan el trabajo del backend. No se encontró polling periódico en el hook, la página ni el workspace de resultados.

## 2. Diagrama de llamadas real

Abreviaturas: `F = frontend/src`, `B = backend_api/app`, `M = malaria_dl_local_project/src/malaria_dl`. Cada flecha identifica el archivo y la función que realiza la transición. Las continuaciones posteriores a una respuesta son responsabilidad del hook.

```text
F/pages/SmearUpload.tsx: botón INICIAR ANÁLISIS
  └─[SmearUpload.tsx: onClick → submit]
     FormData(files, identidad, origen)
  └─[SmearUpload.tsx: submit → onAnalyze;
     F/pages/SmearWorkflow.tsx: onAnalyze={controller.start}]
     F/hooks/useSmearAnalysisWorkflow.ts: start
  └─[hook:start → F/services/api.ts: uploadMicroscopyImages]
     POST /api/v1/scientific/images/upload
  └─[B/routes/scientific.py: upload_images → ImageIngestionService.upload]
     B/services/image_ingestion.py: upload
  └─[upload → LocalStorage.stage / image_validation.validate_image / promote]
     originales + jerarquía científica + ingestion_batch + microscopy_images
  └─[respuesta → hook:start → createAnalysisAndContinue → api.createAnalysisRun]
     POST /api/v1/analysis/runs {ingestion_batch_id}
  └─[B/routes/analysis.py:create_run → MicroscopyAnalysisService.create]
     análisis + imágenes congeladas + manifiesto + perfil de calidad
  └─[respuesta → hook:createQueueAndAssess → api.enqueueQuality]
     POST /api/v1/analysis/queue {analysis_run_id, priority:50}
  └─[B/routes/analysis.py:enqueue → QualityQueueService.enqueue]
     quality_assessment_queue_items
  └─[respuesta → hook:executeQueuedQuality → api.executeQueueItem]
     POST /api/v1/analysis/queue/{id}/execute
  └─[B/routes/analysis.py:execute_queue_item → QualityQueueService.execute]
     claim → MicroscopyAnalysisService.measurements
  └─[B/services/microscopy_analysis.py:measurements → image_quality.assess_image]
     métricas y veredicto por imagen
  └─[B/services/quality_queue.py:execute → persist_measurements → complete]
     quality gate persistido
  └─[hook:executeQueuedQuality → api.getAnalysisRun → evaluateQuality]
     pass / warning aprobado → executeDetection
     warning sin aprobar → decideWarning → quality-decision → executeDetection
     fail → se detiene
  └─[hook:executeDetection → api.createCellDetectionRun]
     POST /api/v1/cell-analysis/detection-runs {analysis_run_id}
  └─[B/routes/cell_analysis.py:create_detection_run → CellAnalysisService.execute_detection]
     _create_or_existing → _eligible → LocalStorage.resolve_verified
  └─[B/services/cell_analysis.py:execute_detection → connected_components_v1.detect_path]
     B/services/detectors/connected_components_v1.py: detect_image
  └─[detect_image → _foreground_mask → _components]
     componentes aceptados / rechazados
  └─[detect_image: BoundingBox.padded → oriented.crop → PNG]
     ImageDetectionResult(components, crops, warnings, dimensiones, threshold)
  └─[CellAnalysisService.execute_detection → CellCropStorage.stage;
     CellAnalysisRepository.insert_component/insert_detection/insert_crop;
     CellCropStorage.promote → repository.complete_run]
     detecciones y crops persistidos
  └─[respuesta → hook:executeDetection → executeClassification]
     api.getProductiveModelAvailability + getEligibleCellClassificationRuns
  └─[hook:executeClassification → api.createCellClassificationRun]
     POST /api/v1/cell-classification/classification-runs {detection_run_id}
  └─[B/routes/cell_classification.py:create_classification_run → execute_classification]
     B/services/cell_classification.py: CellClassificationService
  └─[execute_classification → ProductiveModelResolver.resolve;
     _create_or_existing → repository.detection_run_input;
     _preflight_detections → freeze_classification_inputs]
     modelo y entradas congelados
  └─[execute_classification → ProductiveModelResolver.load → _run_batches]
     _preprocess → M/data/input_contract.py:transform_bytes
  └─[_run_batches → _predict → model.predict(batch, verbose=0)]
     salida binaria → normalize_binary_outputs → classification_decision
  └─[_run_batches → _persist_batch → repository.insert_prediction]
     cell_predictions: probabilidad parasitized + etiqueta P/U
  └─[execute_classification → _finalize → build_automatic_summary;
     CellClassificationRepository.create_summary]
     smear_analysis_summaries
  └─[respuesta → hook:executeClassification → api.getCellClassificationSummary]
     GET /api/v1/cell-classification/classification-runs/{id}/summary
  └─[B/routes/cell_classification.py:classification_run_summary → service.get_summary]
     resumen automático + resumen revisado calculado
  └─[hook:setSnapshot → SmearWorkflow → SmearAnalysisImmersiveView]
     F/components/cell-review/CellReviewWorkspace.tsx
  └─[CellReviewWorkspace: efectos de carga + renderResultBody]
     original, cajas, galería de crops, P/U, probabilidades y resultado del frotis
```

La recuperación tiene una rama propia: `hook.recover → api.getSmearWorkflow → GET /api/v1/scientific/workflows/{batch} → routes/scientific.get_smear_workflow → SmearWorkflowService.get → build_workflow_payload/derive_workflow_stage`. Lee análisis, cola, detección, clasificación y summary; por defecto elige los runs más recientes. No ejecuta las etapas.

## 3. Entrada frontend, HTTP y estados

En `SmearUpload.tsx:422`, `smear-analyze-reason` es el **ID de un párrafo**, usado por `aria-describedby` del botón. El handler está en `submit` (línea 159), llamado por `onClick` (429). Seleccionar archivos solo actualiza estado/preview; la subida ocurre al iniciar.

El formulario envía `files` repetido, `subject_mode` y `sample_mode` (`automatic_new`/`existing`), opcionalmente `subject_code` y `sample_id`, y `acquisition_origin`. NIH agrega `source_system=nih_nlm_thin_blood_smears_pf`, `external_patient_id` y eventualmente `external_sample_id`; captura externa envía su `source_system`. El tipo de frotis visible no se envía como selector de detector. `start` agrega `metadata_json={client_request_id: UUID}` para idempotencia de ingesta. No se envía detector ni modelo de clasificación.

La UI valida extensiones/MIME JPEG, PNG, TIFF, 20 MiB por archivo, identidad/origen y permisos. El preview mide la primera imagen y compara con 100 MP; la validación backend es la que cubre cada archivo. `SmearWorkflow` pasa capacidades al hook y `onAnalyze={controller.start}`. La ruta es `/frotis/analizar` (`router.ts`, registrada por `App.tsx`).

| Acción del hook / cliente API | Endpoint y payload | Respuesta utilizada / siguiente transición |
|---|---|---|
| `start / uploadMicroscopyImages` | POST `/api/v1/scientific/images/upload`, multipart descrito arriba | identidad, `ingestion_batch`, `images`; conserva batch y primera image; crea análisis |
| `createAnalysisAndContinue / createAnalysisRun` | POST `/api/v1/analysis/runs`, `{ingestion_batch_id}` | `AnalysisRun`, imágenes/eventos/decisiones; crea cola |
| `createQueueAndAssess / enqueueQuality` | POST `/api/v1/analysis/queue`, `{analysis_run_id,priority:50}` | item `id`; ejecuta cola |
| `executeQueuedQuality / executeQueueItem` | POST `/api/v1/analysis/queue/{id}/execute` | item terminal; GET `/api/v1/analysis/runs/{id}` y `evaluateQuality` |
| `decideWarning` | POST `/api/v1/analysis/runs/{id}/quality-decision`, `{decision,comment}` | análisis actualizado; aprobación continúa; rechazo bloquea |
| `executeDetection / createCellDetectionRun` | POST `/api/v1/cell-analysis/detection-runs`, `{analysis_run_id}` | detalle run, conteos, imágenes, eventos, reviews, `idempotent`; si completado clasifica |
| `executeClassification` preflight | GET `/api/stage2/productive-model-availability?datasource=…` y GET `/api/v1/cell-classification/eligible-detection-runs?detection_run_id=…&limit=1&offset=0` | disponibilidad y elegibilidad; puede quedar `awaiting_productive_model` o fallar |
| `createCellClassificationRun` | POST `/api/v1/cell-classification/classification-runs`, `{detection_run_id}` | run y estado; completado lleva a GET summary |
| `getCellClassificationSummary` | GET `/api/v1/cell-classification/classification-runs/{id}/summary` | outcome, conteos, probabilidades, resumen por imagen y revisado |
| `recover / refresh` | GET workflow por batch; GET runs para resolver IDs cuando corresponde | reconstrucción de estado, sin repetir automáticamente todas las mutaciones |

`writeIdentifiers` guarda `batch,image,analysis,queue,detection,classification,selected_detection,selected_prediction` en query params con reemplazo de URL. Hay recuperación tras recarga, conflictos 409 y algunos errores de petición, además de acciones manuales de continuar/reintentar. Los POST de calidad/detección/clasificación usan `run_in_threadpool` en sus rutas y esperan el resultado: esa cola de calidad **no implica aquí un worker autónomo que continúe el resto del flujo**. El cliente da 120 s a upload/detección y 600 s a clasificación. Un timeout no prueba rollback del backend; existen rutas de recuperación de lo persistido.

No hay `setInterval` ni `setTimeout` de polling en el hook, `SmearWorkflow` o `CellReviewWorkspace`. Las actualizaciones llegan de respuestas, efectos React por cambio de IDs, recuperación y refresh/reviews. Por eso recargar/cerrar la página puede interrumpir la continuación frontend entre etapas aunque el trabajo backend solicitado ya haya quedado persistido.

## 4. Tabla de etapas y persistencia real

Los servicios de ingesta, análisis, cola y consulta de workflow ejecutan SQL directamente. No se inventa un repository para esas etapas; los repositorios de detección y clasificación sí son explícitos.

| Etapa | Archivo | Función | Entrada | Salida | Persistencia / repository |
|---|---|---|---|---|---|
| Preparación | `F/pages/SmearUpload.tsx` | `selectFiles`, `submit` | Files y formulario | FormData | estado React |
| Ingesta | `B/services/image_ingestion.py` | `upload`, `_upload_response` | multipart validado | batch, identidad, imágenes | SQL directo: `research_subjects`, `scientific_cases`, `blood_samples`, `smear_slides`, `image_ingestion_batches`, `microscopy_images`; `LocalStorage.stage/promote` |
| Análisis | `B/services/microscopy_analysis.py` | `create`, `manifest` | batch | run con perfil y manifiesto | SQL directo: `microscopy_analysis_runs`, `microscopy_analysis_run_images`, `microscopy_analysis_events` |
| Cola | `B/services/quality_queue.py` | `enqueue`, `claim`, `execute`, `complete/fail` | run y prioridad / item ID | cola terminal | SQL directo: `quality_assessment_queue_items` |
| Medición | `B/services/image_quality.py` | `assess_image` | original + perfil | métricas, warning/failure codes | devuelve datos a `MicroscopyAnalysisService.persist_measurements` |
| Gate | `B/services/microscopy_analysis.py` | `persist_measurements`, `review` | resultados o decisión | ready / warning / blocked | SQL directo: `image_quality_assessments`, `quality_gate_decisions`; actualiza run e imágenes congeladas, agrega eventos |
| Detección | `B/services/cell_analysis.py` | `_create_or_existing`, `execute_detection` | análisis listo | detection run | `CellAnalysisRepository.analysis_input/find_equivalent/create_run/start_run` → `cell_detection_runs` |
| Algoritmo + crops | `B/services/detectors/connected_components_v1.py` | `detect_path`, `detect_image`, `_components` | original verificado y profile | `ImageDetectionResult` | cálculo en memoria |
| Persistencia detección | `B/services/cell_analysis.py` y `cell_crop_storage.py` | `execute_detection`, `stage/promote` | componentes y PNG | detecciones/crops disponibles | `CellAnalysisRepository.insert_component/insert_detection/insert_crop/add_event/complete_run` → `image_connected_components`, `cell_detections`, `cell_crops`, `cell_detection_events`; PNG en disco |
| Resolución modelo | `B/services/productive_model.py` | `resolve`, `_fetch_candidates`, `_validate`, `load` | slot Stage 2 | checkpoint, threshold y contrato | lecturas SQL de publicaciones, deployments, versiones, artefactos, calibración y lineage |
| Congelación clasificación | `B/services/cell_classification.py` | `_create_or_existing`, `_preflight_detections`, `freeze_classification_inputs` | detection run y modelo | inputs elegibles/excluidos + snapshot | `CellClassificationRepository.detection_run_input/create_run/insert_inputs` → `cell_classification_runs`, `cell_classification_inputs` |
| Inferencia | mismo servicio + `M/data/input_contract.py` | `_run_batches`, `_preprocess`, `_predict`, `transform_bytes` | PNG y contrato | probabilidades y P/U | `CellClassificationRepository.insert_prediction`, eventos/conteos → `cell_predictions`, `cell_classification_events` |
| Agregación | `B/services/cell_classification.py` | `_finalize`, `build_automatic_summary`, `get_summary` | inputs y predicciones | summary automático/revisado | `CellClassificationRepository.create_summary/get_summary`; `smear_analysis_summaries`; reviews en `cell_classification_reviews` |
| Recuperación | `B/services/smear_workflow.py` | `get`, `build_workflow_payload`, `derive_workflow_stage` | batch / analysis ID | DTO de workflow | SQL directo + servicios/repositorios de lectura |
| Resultado | `F/components/cell-review/CellReviewWorkspace.tsx` | efectos, `renderResultBody` | run, detecciones, predictions, summary | workspace y resultado experimental | GET, selección local; revisiones explícitas por APIs |

Las mutaciones también registran auditoría mediante `record_event`; estos eventos no son motores de transición.

### Ingesta y calidad

`ImageIngestionService.upload` resuelve/crea sujeto y caso, crea/reutiliza muestra, frotis y batch según identidad/origen; valida pertenencia jerárquica. Ordena los archivos por nombre, hace staging, decodifica con `validate_image`, calcula integridad y promueve los originales. Conserva píxeles originales y referencias, no binarios en BD. NIH espera cinco imágenes: un lote incompleto o inconsistente no habilita este análisis. Existe deduplicación por request ID, procedencia y checksum según la rama.

`MicroscopyAnalysisService.create` congela IDs, SHA-256, tamaño, dimensiones y secuencia en `microscopy_analysis_run_images`; guarda manifiesto y perfil elegido por `quality_profiles.select_profile`. `assess_image` verifica almacenamiento/checksum/formato/dimensiones, aplica orientación EXIF y reduce solo la copia de medición a lado máximo 2048. Calcula brillo, contraste, entropía, Laplaciano, Tenengrad, proporciones oscuro/claro, borde y área útil. El detector posteriormente vuelve al original completo: no recibe esta miniatura.

El gate global es `fail` si alguna imagen tiene fail/error, `warning` si no hubo fail pero sí warning, y `pass` en otro caso. Pass habilita detección; warning necesita decisión existente `approve_with_warnings` y comentario; fail bloquea. Aprobar warning cambia `ready_for_analysis`, **no transforma el gate en pass**. `_eligible` de detección comprueba ambos, las imágenes congeladas y el manifiesto.

## 5. Detector actual: selección, algoritmo, geometría y crops

### Selección

`B/services/cell_analysis.py:17` importa directamente `DETECTOR_KEY`, `DETECTOR_VERSION`, `ALGORITHM_VERSION`, `COORDINATE_SPACE`, `detect_path`, `profile_snapshot` y `DetectorInputError` desde `detectors.connected_components_v1`. La identidad es `connected_components_v1 / 1.0.0 / pillow-connected-components-1.0.0`.

`_create_or_existing` usa `profile_snapshot()` sin overrides. `eligible_analysis_runs`, la búsqueda de equivalencia, creación y auditoría usan esas constantes. `execute_detection` llama directamente a ese `detect_path`. El schema `CellDetectionRunCreate` solo declara `analysis_run_id`; no hay selector frontend/API ni resolver de detectores. `profile_snapshot(overrides)` existe como función de bajo nivel, pero prohíbe cambiar identidad y otros campos fijos. **No equivale a selección configurable de tecnologías.**

### Algoritmo

1. `detect_path` recibe `Path`, SHA, dimensiones y tamaño esperados, profile y `integrity_preverified`. El servicio verifica almacenamiento antes; el detector verifica dimensiones y decodifica.
2. `detect_image` conserva dimensiones crudas y aplica `ImageOps.exif_transpose`. Convierte una copia a RGB y luminancia; no remuestrea el raster de detección.
3. Blur Gaussiano (kernel configurado 3, radio 1); Otsu para foreground oscuro (`value <= threshold`). Imagen prácticamente uniforme produce máscara vacía y threshold `None`.
4. Apertura y cierre con MinFilter/MaxFilter, kernel 3, una iteración. `_components` recorre la máscara con BFS; conectividad 8 por defecto (4 disponible en perfil).
5. Área = cantidad de píxeles de máscara. Centroide = media x/y. Perímetro = aristas expuestas según vecindad de cuatro direcciones. Circularidad = `min(1,4π*área/perímetro²)`; solidity usa hull de píxeles de borde con corrección descrita por `_solidity`.
6. Rechaza componentes de borde, área <64 o >250000, ancho/alto <6, circularidad <0.05 o solidity <0.20. Si ya aceptó 500, agrega `MAXIMUM_COMPONENTS_EXCEEDED`. Guarda todos los componentes, incluso rechazados.
7. `component_status=accepted` si no hay códigos; de lo contrario `rejected_by_filter`. `rejection_code` conserva el primero y `rejection_codes` todos. Aceptación algorítmica no es revisión humana: `cell_detections.automated_status` empieza como `candidate`.
8. `detector_score=clamp((circularity+solidity)/2,0,1)`: es una heurística geométrica, **no** probabilidad de parasitized ni confidence de una red.

Bounding box entera `xywh`, origen superior izquierdo, sobre el raster **orientado por EXIF**, aunque `coordinate_space` se llame `original_image_pixels`. `width=max_x-min_x+1`, `height=max_y-min_y+1`; `right=x+width`, `bottom=y+height` son extremos exclusivos para Pillow. La caja de detección no lleva padding.

### Generación/persistencia de crops

Solo accepted genera `CellCrop`: padding por defecto 4 px mediante `BoundingBox.padded`, limitado a dimensiones orientadas; `oriented.crop((x,y,right,bottom))`; PNG sin resize, normalización ni fondo enmascarado. Se recorta el raster original orientado, no la imagen borrosa ni la máscara. Modos que no permiten PNG preservando píxeles producen `UNSUPPORTED_CROP_MODE` cuando existen candidatos aceptados.

`CellCrop.component_index` enlaza en memoria con el componente. `execute_detection` exige un crop por accepted (`MISSING_ACCEPTED_CROP` si falta), asigna UUIDs de componente/detección/crop y un `cell_index` global del run. `CellCropStorage` valida PNG y dimensiones, calcula SHA/tamaño y almacena en `cell-crops/{analysis_run_id}/{detection_run_id}/{microscopy_image_id}/{cell_detection_id}/crop.png`. `cell_crops` guarda referencia, checksum, tamaño, dimensiones, formato y padding; **no guarda los bytes ni una máscara, ni una bbox de crop independiente**.

Los registros de componentes/detecciones/crops y la finalización se insertan en una transacción; promoción de archivos tiene compensación/limpieza en errores. El run se crea/inicia antes y puede quedar failed si falla esta fase. Warnings actuales: `NO_ACCEPTED_COMPONENTS`, `MAXIMUM_COMPONENTS_REACHED`; se guardan en eventos por imagen y el run suma su cantidad. Un rechazo geométrico por sí solo no incrementa ese warning_count. Cero accepted termina detección con warnings, pero clasificación rechaza `NO_DETECTIONS`/`NO_CROPS`: no llega automáticamente a un summary negativo.

### Relación con el proyecto ML

`M/cell_detection/` contiene únicamente `__init__.py` (declara que no hay implementación) y un README de intención futura. No hay llamada a ese paquete desde el detector productivo encontrado. Su README dice que se clasifican imágenes completas y que no existe detección activa: **esa descripción está desactualizada respecto de este workflow**, que sí detecta en backend y clasifica crops.

La dependencia real del clasificador hacia ML es `M/data/input_contract.py` y `data/preprocessing.py`, importados por `_resolved_input_contract/_preprocess`, no `M/cell_detection`. Ambos directorios de detección no son implementaciones intercambiables actuales.

## 6. Contrato Detection → Crops → Prediction

### Resultado exacto de detección en memoria

```text
ImageDetectionResult
  raw_width_px, raw_height_px
  oriented_width_px, oriented_height_px
  threshold_value: int | None
  components: tuple[ConnectedComponent]
    component_index
    bbox: BoundingBox(x,y,width,height)
    centroid_x, centroid_y, area_px
    perimeter_px, circularity, solidity, touches_border
    component_status, rejection_code, rejection_codes
    detector_score
  crops: tuple[CellCrop]
    component_index
    bbox: caja con padding
    padding_px, png_bytes, width_px, height_px
  warnings: tuple[str]
```

Definiciones en `B/models/cell_detection.py`. El consumidor también accede a `profile["threshold_method"]` y `profile["orientation_policy"]`; no basta con devolver una lista de boxes. La máscara binaria y los píxeles del contorno son internos; no aparecen en el resultado ni se persisten como segmentación.

### Qué recibe cada nivel de clasificación

| Dato | Servicio/congelación | `model.predict` |
|---|---|---|
| Imagen Full Smear | no se usa como input de clasificación | no |
| bbox | sirve a visualización; no determina el tensor de inferencia | no |
| PNG del crop | sí, leído desde storage con integridad y dimensiones verificadas | sus píxeles transformados |
| Máscara | no | no |
| Detection ID y crop ID | sí, trazabilidad, reviews y persistencia | no |
| Metadata del detector | key/version/algorithm congelados y verificados | no |
| Dimensiones, SHA, tamaño del crop | sí, elegibilidad/verificación | tensor redimensionado según modelo |
| Contrato y threshold del modelo | snapshot del run y decisiones | preprocessing define tensor; threshold se aplica después |

`CellClassificationRepository.detection_run_input` une detection run, análisis, detecciones, imágenes congeladas, crops y revisión efectiva. `_eligible_detection_run` exige run terminado, análisis listo, identidad del detector no vacía y consistente, conteos coherentes y al menos una detección/crop. **No tiene whitelist de `connected_components_v1`.**

`_preflight_detections` verifica archivo, tamaño, hash, decodificación y dimensiones. `freeze_classification_inputs` congela todo candidato y sus exclusiones: revisión rejected, crop ausente, metadata inválida o error de preflight. `unreviewed` es elegible si cumple lo demás: no existe aprobación humana previa obligatoria de cada célula. Si no queda ningún crop elegible, `_create_or_existing` rechaza `NO_ELIGIBLE_CROPS`.

`_preprocess → transform_bytes → decode_rgb → transform_rgb`: TensorFlow decodifica a RGB de tres canales y float32; resize bilinear a `[input_height,input_width]`, `antialias=False`; `apply_model_preprocessing` usa `rescale_0_1` o `vgg16_imagenet` según contrato. El contrato contempla también preprocessing interno de DenseNet; no debe duplicarse. No hay tamaño universal de crop requerido: el checkpoint publicado fija el tensor esperado.

`_run_batches` apila arrays (`np.stack`), `_predict` ejecuta realmente `model.predict(batch, verbose=0)`. `normalize_binary_outputs` interpreta sigmoid o dos clases softmax, y logits únicamente cuando el contrato lo declara; verifica shape, finitud y probabilidades. Mapping canónico: 0 uninfected, 1 parasitized. `classification_decision` produce P si `probability_parasitized >= resolved.threshold`, U en otro caso; `near_threshold` si la distancia al threshold es <= review_margin. El score geométrico del detector no participa en esa probabilidad.

### Modelo productivo y resumen

`ProductiveModelResolver.resolve → resolve_current_stage2_productive_model → _fetch_candidates/_validate` busca una única publicación Stage 2 activa y su deployment `stage2/default`, alcance `stage2_experimental`. Lee `stage2_model_publications`, `deployed_model_versions`, `model_versions`, `artifacts`, `runs`, `run_threshold_calibration` y `run_lineage`. Valida artefacto y contrato técnico (framework, firmas, preprocessing, mapping y threshold), revalida dentro de la creación del run y carga el checkpoint verificado con su mecanismo de cache. La selección del clasificador es independiente del futuro detector YOLO. No hay fallback a un modelo arbitrario. La auditoría no verificó si actualmente hay una publicación disponible en la BD.

`_finalize → build_automatic_summary` agrega **células candidatas clasificadas**, no todos los eritrocitos reales:

- Alguna P → `suspicious_cells_detected`.
- Sin P, todas las elegibles clasificadas, sin fallos ni cercanas al threshold según política → `no_suspicious_cells_detected`.
- Otro caso → `inconclusive`.

Persiste conteos, fracción P/clasificadas, máxima/media/mediana de probabilidad, desglose por imagen y política de agregación. Fallos parciales producen run `completed_with_warnings`; si ninguna elegible pudo clasificarse, run failed. Estar cerca del threshold afecta summary, pero por sí solo no hace que `_finalize` marque warnings del run. `get_summary/build_revised_summary` calcula además una vista con revisiones sin reescribir predicciones ni el summary automático.

## 7. Una célula concreta y sus IDs

Ejemplo conceptual, no registros creados durante esta auditoría:

```text
research_subjects S → scientific_cases C → blood_samples B → smear_slides L
  microscopy_images I (slide_id=L, ingestion_batch_id=G, storage_key, SHA)
  microscopy_analysis_runs A (batch G y jerarquía S/C/B/L)
  microscopy_analysis_run_images AI (analysis_run_id=A, microscopy_image_id=I)
  cell_detection_runs D (analysis_run_id=A, identidad del detector)
  image_connected_components K (run D, A, AI, I, component_index=7)
  cell_detections X (connected_component_id=K, D, A, AI, I, cell_index, cell_code)
  cell_crops R (cell_detection_id=X, PNG, SHA, dimensiones)
  cell_classification_runs Q (detection_run_id=D, analysis_run_id=A, modelo congelado)
  cell_classification_inputs J (Q, D, X, I, R, snapshot de detector/crop/review)
  cell_predictions P (classification_input_id=J, classification_run_id=Q,
                      cell_detection_id=X, crop_id=R, probability_parasitized)
  smear_analysis_summaries T (classification_run_id=Q, detection_run_id=D, analysis_run_id=A)
```

`component_index` une resultados antes de persistir; `connected_component_id` enlaza la evidencia geométrica; **`cell_detection_id` es la identidad de célula que atraviesa crop/predicción/revisión/UI**. Una predicción guarda también `crop_id` y `classification_input_id`. El workspace une predictions con detecciones mediante `cell_detection_id` y usa `microscopy_image_id` para cambiar de campo microscópico.

El esquema activo versionado (`alembic_v2/baseline/03_tables.sql`, `05_keys.sql`, `06_constraints.sql`) hace `connected_component_id NOT NULL` y FK compuesta al componente y su run/imagen congelada; impone unicidad de componente por detección y de índice por imagen/run. `validate_cell_classification_input_snapshot` en `04_functions.sql` comprueba IDs, índice, código, identidad del detector y hash/dimensiones contra origen. No basta insertar crops aislados. Esta es evidencia del esquema versionado, no una inspección del catálogo de una instancia viva.

## 8. Resultado final y revisión

`SmearWorkflow` entrega summary e IDs a `SmearAnalysisImmersiveView`, que monta `CellReviewWorkspace`. Este carga runs/imágenes, detecciones por imagen, blobs autenticados del original/crop y predicciones por imagen. Presenta overlay de cajas, galería, detalle de célula, P/U, probabilidades y `renderResultBody` con outcome y métricas del summary. El resultado es experimental y tiene revisión experta en la propia UI.

El workspace solicita hasta **500** detecciones para el overlay y **500** predicciones por imagen; el algoritmo actual alinea su máximo de accepted con ese límite. Un nuevo detector con más candidatos necesita conservar ese límite para reutilizar el frontend íntegro, o ampliar su paginación (mejora separada).

Las revisiones de detección usan `scientific_reviews`; las de clasificación `cell_classification_reviews`. Explicabilidad se solicita por acción sobre una predicción (`/predictions/{id}/explanation`); no forma parte de las llamadas automáticas de `start`. No se exige generar Grad-CAM para obtener el summary. Anotaciones científicas y clasificación humana existen como acciones posteriores; no se confunden con la P/U automática.

## 9. Integración mínima de otro detector

### Dónde seleccionar

**Recomendación: selección en `CellAnalysisService` mediante una función pequeña `resolve_detector(key)` y configuración backend con default actual.** No necesita servicio nuevo ni un registro de detectores en BD. Los campos existentes de `cell_detection_runs` ya registran identidad y `profile_snapshot`.

| Lugar | Decisión |
|---|---|
| Frontend | opcional si se quiere elegir por análisis; no hace falta para configurar un default backend |
| Hook/workflow | solo transportar una selección explícita futura; no implementar lógica del detector |
| `SmearWorkflowService` | no corresponde: es lectura/reconstrucción |
| `CellAnalysisService` + resolver mínimo | sitio natural: hoy concentra identidad, creación, elegibilidad y llamada |
| Configuración backend | default `connected_components_v1`; key YOLO cuando exista adapter/runtime |
| BD | reutilizar key/version/algorithm/profile ya presentes; no nuevas tablas |

### NECESARIO

1. Resolver identidad, profile y función del detector conjuntamente; usar lo resuelto en elegibilidad, `find_equivalent`, creación, eventos y ejecución. Resolver una vez y ejecutar con el snapshot congelado, no con un default mutable a mitad del run.
2. Extraer la generación rectangular actual de crops a una función compartida que tome original orientado, componentes accepted y padding. Conservar PNG/píxeles/padding y correspondencia por `component_index`; conservar el algoritmo connected components.
3. Adaptar YOLO a `ImageDetectionResult` y componentes existentes. Evitar exigir Otsu: el profile puede declarar un método propio/no aplicable, `threshold_value=None`; el consumidor debe conservar la semántica real de esa metadata. No falsear el detector como connected components.
4. Mantener el registro `image_connected_components` por cada instancia para satisfacer FK y lecturas actuales. Es un nombre histórico: puede representar una región de instancia derivada de máscara si su procedencia YOLO queda explícita. Calcular área/centroide y métricas desde máscara; los campos SQL perimeter/circularity/solidity permiten NULL, pero el dataclass actual los tipa float: si se eligen NULL, ajustar ese tipado mínimamente. No rellenar mediciones ficticias.
5. Mantener identidad versionada del checkpoint/perfil efectivo. La equivalencia SQL actual y el índice único usan análisis + detector_key + detector_version + algorithm_version + manifiesto de imágenes; **no incluyen hash del profile**. Para el cambio mínimo, usar perfiles/checkpoints inmutables por versión. Cambiar thresholds/pesos bajo la misma identidad podría reutilizar un run anterior; si se requiere configuración arbitraria por petición, ese alcance necesita resolver esta equivalencia explícitamente.
6. Conservar coordenadas originales orientadas, un crop por accepted y máximo 500 accepted por imagen si no se cambia UI.
7. Incorporar runtime, pesos adecuados al dominio y su configuración cuando se implemente YOLO. Esta auditoría no ejecutó ni certificó ese runtime o checkpoint.

Si el requisito posterior es elegir en la pantalla, agregar `detector_key` opcional al schema/API y transportarlo desde UI/hook al servicio; default preserva el cliente actual. Elegir por configuración backend permite reutilizar frontend sin modificaciones.

### MEJORA OPCIONAL

Persistir/mostrar máscaras; comparar múltiples runs de detectores en la misma pantalla; paginar overlays más allá de 500; agregar polling; separar SQL directo de servicios de ingesta/calidad; renombrar entidades históricas; modernizar el README ML. Ninguna de esas mejoras es requisito para la conexión mínima de YOLO a crops y clasificación.

## 10. Compatibilidad conceptual con YOLO26-seg

La documentación oficial describe salida de segmentación por instancia con box, mask, confidence y class ([Ultralytics, segmentación](https://docs.ultralytics.com/tasks/segment)). Esta consulta solo verifica el contrato externo conceptual; **el diagrama de ejecución anterior deriva exclusivamente del código local**. No se asume un adapter YOLO existente en el repositorio.

| YOLO / nuevo adapter | Traducción mínima al consumidor actual |
|---|---|
| bbox | convertir a xywh entero con límites válidos; devolver al raster EXIF original; deshacer cualquier resize/letterbox del runtime |
| mask | usar para área, centroide y métricas de instancia; no se pasa al clasificador ni requiere persistencia binaria en BD |
| confidence | `detector_score` en [0,1]; semántica de confidence, distinta del score geométrico actual y de probabilidad parasitized |
| class | filtrar clases celulares configuradas; no usarla como P/U final; si interesa conservarla, metadata explícita del componente requiere extender el transporte actual |
| instancia | índice único/estable por imagen; estado accepted/rejected y códigos; registro de componente y detección |
| original | misma orientación y dimensiones; crop rectangular con padding, PNG sin fondo enmascarado |
| identidad | key `yolo26_seg`, versiones y profile efectivo con referencia/hash de pesos; reutilizar campos existentes |
| resumen de imagen | dimensiones raw/orientadas, warnings y threshold no aplicable como `None` |

La salida **mínima para entrar sin alterar `execute_detection` sustancialmente** sigue siendo `ImageDetectionResult` completo con crops y componentes. Para compartir generación de crops, el pequeño refactor anterior separa región detectada de recorte pero entrega finalmente ese mismo resultado a persistencia. Boxes/confidence solos no satisfacen el contrato; masks/classes solas tampoco.

Se reutilizan `BoundingBox.padded`, el recorte PNG actual (extraído), `CellCropStorage`, repositorios, tablas de runs/componentes/detecciones/crops, congelación de inputs, resolución del clasificador, preprocessing, `model.predict`, normalización, decisiones, summaries, APIs de lectura y workspace. La máscara YOLO **no necesita enmascarar el crop**; hacerlo cambiaría los píxeles que espera el clasificador y requeriría validar ese nuevo contrato de entrada.

La compatibilidad estructural no demuestra desempeño científico equivalente: el nuevo detector puede cambiar qué regiones llegan al clasificador. Validar que sus crops representan las células esperadas es trabajo de integración/evaluación posterior, no una nueva capa de gobernanza ni motivo para rehacer el pipeline.

## 11. Evidencia y límites de validación

Se siguieron imports y llamadas desde el frontend hasta `model.predict`, SQL de repositorios/servicios y esquema v2. Se contrastaron consumidores de resultados, recuperación, límites de UI, idempotencia y checks de clasificación. No se ejecutaron pruebas de aplicación porque el cambio es documental y la solicitud es auditoría read-only; no se afirma funcionamiento end-to-end observado ni disponibilidad de modelos/archivos/DB. Validación documental completada: 39 enlaces locales resuelven a archivos existentes y `git diff --check` no reportó errores. El estado final solo contiene este reporte nuevo y la entrada agregada en `docs/README.md`.

Fuentes principales (rutas relativas al repositorio):

- [frontend/src/pages/SmearUpload.tsx](../../../frontend/src/pages/SmearUpload.tsx)
- [frontend/src/pages/SmearWorkflow.tsx](../../../frontend/src/pages/SmearWorkflow.tsx)
- [frontend/src/hooks/useSmearAnalysisWorkflow.ts](../../../frontend/src/hooks/useSmearAnalysisWorkflow.ts)
- [frontend/src/services/api.ts](../../../frontend/src/services/api.ts)
- [frontend/src/router.ts](../../../frontend/src/router.ts)
- [frontend/src/App.tsx](../../../frontend/src/App.tsx)
- [frontend/src/components/cell-review/SmearAnalysisImmersiveView.tsx](../../../frontend/src/components/cell-review/SmearAnalysisImmersiveView.tsx)
- [frontend/src/components/cell-review/CellReviewWorkspace.tsx](../../../frontend/src/components/cell-review/CellReviewWorkspace.tsx)
- [backend_api/app/routes/scientific.py](../../../backend_api/app/routes/scientific.py)
- [backend_api/app/routes/analysis.py](../../../backend_api/app/routes/analysis.py)
- [backend_api/app/routes/cell_analysis.py](../../../backend_api/app/routes/cell_analysis.py)
- [backend_api/app/routes/cell_classification.py](../../../backend_api/app/routes/cell_classification.py)
- [backend_api/app/routes/governance.py](../../../backend_api/app/routes/governance.py)
- [backend_api/app/services/image_ingestion.py](../../../backend_api/app/services/image_ingestion.py)
- [backend_api/app/services/image_validation.py](../../../backend_api/app/services/image_validation.py)
- [backend_api/app/services/local_storage.py](../../../backend_api/app/services/local_storage.py)
- [backend_api/app/services/microscopy_analysis.py](../../../backend_api/app/services/microscopy_analysis.py)
- [backend_api/app/services/quality_queue.py](../../../backend_api/app/services/quality_queue.py)
- [backend_api/app/services/image_quality.py](../../../backend_api/app/services/image_quality.py)
- [backend_api/app/services/quality_profiles.py](../../../backend_api/app/services/quality_profiles.py)
- [backend_api/app/services/smear_workflow.py](../../../backend_api/app/services/smear_workflow.py)
- [backend_api/app/services/cell_analysis.py](../../../backend_api/app/services/cell_analysis.py)
- [backend_api/app/services/detectors/connected_components_v1.py](../../../backend_api/app/services/detectors/connected_components_v1.py)
- [backend_api/app/models/cell_detection.py](../../../backend_api/app/models/cell_detection.py)
- [backend_api/app/schemas/cell_analysis.py](../../../backend_api/app/schemas/cell_analysis.py)
- [backend_api/app/services/cell_crop_storage.py](../../../backend_api/app/services/cell_crop_storage.py)
- [backend_api/app/repositories/cell_analysis.py](../../../backend_api/app/repositories/cell_analysis.py)
- [backend_api/app/services/cell_classification.py](../../../backend_api/app/services/cell_classification.py)
- [backend_api/app/repositories/cell_classification.py](../../../backend_api/app/repositories/cell_classification.py)
- [backend_api/app/services/productive_model.py](../../../backend_api/app/services/productive_model.py)
- [malaria_dl_local_project/src/malaria_dl/data/input_contract.py](../../../malaria_dl_local_project/src/malaria_dl/data/input_contract.py)
- [malaria_dl_local_project/src/malaria_dl/data/preprocessing.py](../../../malaria_dl_local_project/src/malaria_dl/data/preprocessing.py)
- [malaria_dl_local_project/src/malaria_dl/cell_detection/__init__.py](../../../malaria_dl_local_project/src/malaria_dl/cell_detection/__init__.py)
- [malaria_dl_local_project/src/malaria_dl/cell_detection/README.md](../../../malaria_dl_local_project/src/malaria_dl/cell_detection/README.md)
- [alembic_v2/baseline/03_tables.sql](../../../alembic_v2/baseline/03_tables.sql)
- [alembic_v2/baseline/04_functions.sql](../../../alembic_v2/baseline/04_functions.sql)
- [alembic_v2/baseline/05_keys.sql](../../../alembic_v2/baseline/05_keys.sql)
- [alembic_v2/baseline/06_constraints.sql](../../../alembic_v2/baseline/06_constraints.sql)
- [alembic_v2/baseline/07_indexes.sql](../../../alembic_v2/baseline/07_indexes.sql)

## PRE-S4 FLOW AUDIT

**Frontend entry:** `frontend/src/pages/SmearUpload.tsx::submit`, clic del botón descrito por `smear-analyze-reason`; `SmearWorkflow` conecta `onAnalyze=controller.start`.

**Initial API:** `POST /api/v1/scientific/images/upload`.

**Workflow orchestrator:** `frontend/src/hooks/useSmearAnalysisWorkflow.ts::start → createAnalysisAndContinue → createQueueAndAssess → executeQueuedQuality → evaluateQuality → executeDetection → executeClassification`. `backend_api/app/services/smear_workflow.py::get` reconstruye estado, no orquesta ejecución.

**Current detector:** `backend_api/app/services/detectors/connected_components_v1.py::detect_path/detect_image`; Pillow, Otsu y componentes conectados.

**Current detector selection:** import directo y constantes en `CellAnalysisService`; profile fijo creado internamente; no selector HTTP/UI.

**Detector input:** path del original, SHA/tamaño/dimensiones congeladas y profile; internamente Pillow sobre imagen EXIF orientada a resolución completa.

**Detector output:** `ImageDetectionResult`: dimensiones crudas/orientadas, threshold, componentes con geometría/score/estado/códigos, crops PNG y warnings.

**Crop generation:** `connected_components_v1.py::detect_image`, `BoundingBox.padded`, `oriented.crop`; persistencia por `cell_crop_storage.py::CellCropStorage.stage/promote`.

**Classification entry:** `backend_api/app/services/cell_classification.py::CellClassificationService.execute_classification(detection_run_id, …)`.

**Prediction input:** batches de arrays RGB float32 provenientes de crops PNG íntegros, redimensionados y preprocesados según contrato publicado; no full smear, bbox ni mask.

**Productive model resolution:** `backend_api/app/services/productive_model.py::ProductiveModelResolver.resolve → resolve_current_stage2_productive_model`, revalidación y `load` del checkpoint del slot Stage 2.

**Smear aggregation:** `backend_api/app/services/cell_classification.py::_finalize → build_automatic_summary`; summary revisado mediante `build_revised_summary`.

**Final frontend result:** `SmearWorkflow → SmearAnalysisImmersiveView → CellReviewWorkspace::renderResultBody`, junto a overlay, galería y detalle P/U.

**Existing DB entities reused:** `research_subjects`, `scientific_cases`, `blood_samples`, `smear_slides`, `image_ingestion_batches`, `microscopy_images`, `microscopy_analysis_runs`, `microscopy_analysis_run_images`, `microscopy_analysis_events`, `quality_assessment_queue_items`, `image_quality_assessments`, `quality_gate_decisions`, `cell_detection_runs`, `image_connected_components`, `cell_detections`, `cell_crops`, `cell_detection_events`, `scientific_reviews`, `cell_classification_runs`, `cell_classification_inputs`, `cell_predictions`, `cell_classification_events`, `smear_analysis_summaries`, `cell_classification_reviews`; resolución productiva mediante publicaciones/deployments/versiones/artefactos/calibración existentes.

**Detector configurable today:** **NO** para seleccionar tecnologías desde el workflow. Hay metadata versionada y overrides de bajo nivel, pero no un mecanismo de selección operativo.

**Minimum change for selectable detectors:** resolver pequeño dentro de la frontera de `CellAnalysisService`, default en configuración backend, identidad/perfil coherentes en creación/equivalencia/ejecución; compartir recorte actual y adaptar YOLO al contrato de componentes+crops. Campo HTTP/UI opcional solo si se necesita selección por solicitud.

**Existing components reusable for YOLO26-seg:** geometría/crop rectangular, almacenamiento y persistencia, trazabilidad, congelación/validación de inputs, clasificador productivo, preprocessing e inferencia, P/U, summary, APIs de lectura y frontend con límite de 500 por imagen.

**Actual blockers:** faltan selector y adapter/runtime YOLO; el recorte está acoplado a `detect_image`; FK/lecturas exigen componente por detección; metadata del consumidor presupone campos de perfil actuales. Son cambios locales resolubles, no bloqueos estructurales que exijan nueva BD. Pesos/runtime y disponibilidad del clasificador no fueron verificados en ejecución. Cero detecciones/crops elegibles o un modelo productivo ausente bloquean clasificación en el flujo existente. Configuración mutable bajo la misma versión colisiona con equivalencia actual.

**Recommended flow:**

```text
SmearUpload → ingesta → análisis → calidad
→ CellAnalysisService → detector configurado [connected_components_v1 | yolo26_seg]
→ componentes de instancia compatibles → recorte rectangular compartido
→ detecciones/crops persistidos → clasificación existente → predicción P/U
→ summary existente → workspace de resultados y revisión
```

**¿Podemos integrar YOLO26-seg como otro detector y conservar desde la generación de crops hacia adelante el flujo actual?** **Sí**, compartiendo la generación de crops hoy embebida en el detector y adaptando las instancias al contrato persistido. Se conservan los crops rectangulares sobre original orientado y todo el clasificador/summary/UI; no basta conectar la salida cruda de YOLO. Las incompatibilidades concretas son la selección hardcodeada, el requisito de componente con geometría e identidad, campos de profile asumidos, coordenadas/escala, correspondencia accepted→crop y el límite de 500 del workspace. No se encontró necesidad de migraciones para resolverlas con el alcance mínimo descrito.
