**La ruta `/frotis/microscopio/:analysisId` es viable con los contratos existentes para un análisis asociado a un frotis.** Ya existe un endpoint que reconstruye su jerarquía usando únicamente ese UUID.

Las principales brechas son el soporte de varios frotis dentro de un mismo análisis, las anotaciones por frotis o región y la persistencia del contexto espacial. Las cinco vistas de `/frotis/analisis-2` son una maqueta funcional; la integración científica reutilizable está principalmente en el historial y en `components/cell-review`.

Auditoría realizada el 11 de noviembre de 2026, sin modificar archivos, rutas ni PostgreSQL, y sin instalar dependencias.

**Alcance y evidencia**

Se inspeccionaron documentación, código de `frontend`, rutas FastAPI, servicios, repositorios y el esquema efectivo de PostgreSQL mediante `information_schema` y `pg_constraint`. Las consultas de verificación usaron conexiones configuradas en modo de solo lectura.

Docker confirma que la aplicación de `localhost` monta `frontend`, no `frontend2`. La ruta de referencia responde HTTP 200; el endpoint histórico sin sesión responde HTTP 401. La recuperación del ejemplo se verificó invocando directamente el servicio backend contra PostgreSQL real. Esto valida la resolución y los datos, pero no constituye una prueba visual ni una prueba HTTP autenticada de extremo a extremo.

### 1. Mapa de rutas y componentes

Las rutas están declaradas en `frontend/src/App.tsx`; las constantes y utilidades de navegación, en `frontend/src/router.ts`.

| Ruta | Componentes reales | Fuente de datos |
|---|---|---|
| `/frotis/analisis-2` | `AnalisisFrotis2Page` | Redirige a `review-cells`, conserva query |
| `/frotis/analisis-2/full-field-review` | `FullFieldReviewPage` → `FullFieldView` | Demostración |
| `/frotis/analisis-2/specimen-quality` | `SpecimenQualityPage` → `QualityView` | Demostración |
| `/frotis/analisis-2/analysis-area` | `AnalysisAreaPage` → `FullFieldView`, con `isAnalysisArea` | Demostración |
| `/frotis/analisis-2/review-cells` | `ReviewCellsPage` → `DifferentialSidebar`, `CellGallery`, `SlideViewer` | Demostración |
| `/frotis/analisis-2/report` | `ReportPage` → `ReportView` | Demostración |
| `/frotis/historial` | `SmearAnalysisHistory` | API de workflows |
| `/frotis/historial/:analysisRunId` | `SmearAnalysisHistoryDetail` → `SmearAnalysisReadOnlyView` | API por UUID del análisis |
| Ruta definida por `routes.smearWorkflow` | `SmearWorkflow` | Workflow científico conectado |

Los componentes de las cinco vistas se encuentran en:

`frontend/src/features/analisis-frotis-v2/`

La documentación del módulo describe expresamente su condición de demostración y coincide con el código inspeccionado:

- `useFrotisDemo()` utiliza `mockCases` e `initialCellsData`.
- La selección celular utiliza identificadores numéricos locales.
- Reclasificación y marcado modifican estado React.
- `NotesDrawer` mantiene notas locales.
- No hay recuperación de predicciones, modelos ni anotaciones desde backend.
- Recargar reinicia el estado.
- El informe y su firma son simulados.

Por tanto, conservar sus componentes visuales resulta útil, pero sus estados y cálculos no deben convertirse en la fuente científica del microscopio.

### 2. Jerarquía real de PostgreSQL

La jerarquía comprobada es:

```text
research_subjects
  └─ scientific_cases.subject_id
      └─ blood_samples.case_id
          └─ smear_slides.sample_id
              └─ microscopy_images.slide_id

microscopy_analysis_runs
  ├─ subject_id
  ├─ case_id
  ├─ sample_id
  ├─ slide_id
  ├─ ingestion_batch_id
  └─ microscopy_analysis_run_images
      └─ microscopy_image_id

microscopy_analysis_runs
  └─ cell_detection_runs.analysis_run_id
      └─ image_connected_components
          └─ cell_detections
              └─ cell_crops

cell_classification_runs
  └─ cell_classification_inputs
      └─ cell_predictions
```

**Identidades y relaciones relevantes**

| Concepto | Identidad y relación real |
|---|---|
| Análisis microscópico | `microscopy_analysis_runs.id`, UUID |
| Paciente/sujeto | `research_subjects.id`; dispone de `subject_code` y `external_patient_id` opcional |
| Caso | `scientific_cases.id`; `subject_id` es nullable en el esquema general |
| Muestra | `blood_samples.id`, FK a caso |
| Frotis físico | `smear_slides.id`, FK a muestra |
| Imagen/captura | `microscopy_images.id`, FK a frotis |
| Imagen incluida en análisis | `microscopy_analysis_run_images`, FK al análisis y a la imagen |
| Ejecución de detección | `cell_detection_runs.id` |
| Célula detectada | `cell_detections.id`; `cell_code` es único |
| Predicción | `cell_predictions.id`, ligada a entrada de clasificación, detección y crop |
| Ejecución de clasificación | `cell_classification_runs.id`, ligada a detección y análisis |
| Resumen | `smear_analysis_summaries`, asociado a clasificación |

**Sí existe una entidad explícita de frotis:** `smear_slides`. Incluye `smear_type`, `stain_type`, `preparation_method` y `prepared_at`. No se necesita crear otra entidad de preparación.

Sin embargo, `microscopy_analysis_runs.slide_id` es obligatorio y singular. El modelo y el servicio actual representan un análisis sobre un lote y un frotis. No sustentan todavía la interpretación de un único análisis que agrupa varios frotis.

Las FK compuestas protegen el linaje de clasificación: una predicción referencia una entrada que conserva conjuntamente clasificación, detección y crop. También se comprueba la pertenencia de la detección al RUN y a la imagen.

**Identidad celular:** `cell_detections.id` identifica una detección concreta. No se encontró una entidad que garantice que dos detecciones de ejecuciones diferentes representan la misma célula física. Esa equivalencia no debe inferirse por posición o `cell_index`.

Las coordenadas de las detecciones están restringidas a `original_image_pixels`; sus bounding boxes usan `bbox_x`, `bbox_y`, `bbox_width` y `bbox_height`.

### 3. Servicios y endpoints reutilizables

El cliente existente es `frontend/src/services/api.ts`. Estas operaciones científicas no requieren `datasource`.

| Operación | Endpoint existente | Cliente o servicio |
|---|---|---|
| Resolver análisis y jerarquía | `GET /api/v1/scientific/analysis-history/{analysisId}` | `api.getSmearAnalysisHistoryDetail()` |
| Detalle técnico del análisis | `GET /api/v1/analysis/runs/{analysisId}` | `api.getAnalysisRun()` |
| Recuperar workflow por lote | `GET /api/v1/scientific/workflows/{batchId}` | `api.getSmearWorkflow()` |
| Listar historial | `GET /api/v1/scientific/workflows` | `api.getSmearAnalysisHistory()` |
| Listar frotis de muestra | `GET /api/v1/scientific/samples/{sampleId}/slides` | `ScientificService.list()` |
| Listar imágenes de frotis | `GET /api/v1/scientific/slides/{slideId}/images` | `ScientificService.list()` |
| Jerarquía del caso | `GET /api/v1/scientific/cases/{caseId}/traceability` | `ScientificService.traceability()` |
| Contenido de imagen | `GET /api/v1/scientific/images/{imageId}/content` | `api.getMicroscopyImageBlob()` |
| Imágenes de detección | `GET /api/v1/cell-analysis/detection-runs/{runId}/images` | `api.getCellDetectionImages()` |
| Detecciones por imagen | `GET /api/v1/cell-analysis/detection-runs/{runId}/images/{imageId}/detections` | `api.getCellDetections()` |
| Detalle celular | `GET /api/v1/cell-analysis/detections/{cellId}` | `api.getCellDetection()` |
| Predicciones | `GET /api/v1/cell-classification/classification-runs/{runId}/predictions` | `api.getCellClassificationPredictions()` |
| Detalle de predicción | `GET /api/v1/cell-classification/predictions/{predictionId}` | `api.getCellPrediction()` |
| Resumen científico | `GET /api/v1/cell-classification/classification-runs/{runId}/summary` | `api.getCellClassificationSummary()` |

Evidencia backend principal:

- `backend_api/app/routes/scientific.py`
- `backend_api/app/routes/analysis.py`
- `backend_api/app/routes/cell_analysis.py`
- `backend_api/app/routes/cell_classification.py`
- `backend_api/app/services/smear_workflow.py`
- `backend_api/app/services/microscopy_analysis.py`
- `backend_api/app/repositories/cell_classification.py`

`SmearWorkflowService.get_by_analysis_run()` resuelve el lote desde el UUID y llama a `get(..., analysis_run_id=...)`, conservando el análisis solicitado.

Su payload contiene sujeto, caso, muestra, frotis, imágenes, análisis, cola, detección, clasificación y resumen. No contiene todas las detecciones y predicciones: se recuperan mediante sus endpoints paginados.

**Semántica que debe preservarse**

- El servicio selecciona la detección más reciente por `created_at DESC, id DESC`.
- Selecciona la clasificación más reciente de esa detección.
- No selecciona necesariamente la última ejecución exitosa.
- Las imágenes del workflow se ordenan por `image_sequence_number, id` y proceden del lote.
- La pertenencia científica al análisis debe contrastarse con `analysis_run.images` y las imágenes del RUN de detección.
- Las listas de detecciones y predicciones tienen paginación y máximos configurables; no debe asumirse que una página representa toda la población.
- Los endpoints requieren sesión y permisos científicos específicos.

### 4. Contrato de resolución por `analysisId`

**Contrato propuesto de frontend, sin nuevo endpoint inicial:**

```text
Entrada obligatoria:
  analysisId = microscopy_analysis_runs.id

Resolución:
  api.getSmearAnalysisHistoryDetail(analysisId)

Datos derivados:
  subject, case, sample, slide, images,
  analysis_run, detection_run, classification_run,
  classification_summary
```

Secuencia recomendada:

1. Validar el UUID con el patrón existente de `isValidPublicId`.
2. Recuperar el workflow mediante el endpoint histórico.
3. Comprobar que `analysis_run.id` coincide con el solicitado.
4. Construir la preparación actual desde `slide.id`.
5. Restaurar contexto local únicamente si sus identidades siguen perteneciendo al análisis.
6. En ausencia de contexto, seleccionar la primera imagen perteneciente al análisis según secuencia e ID.
7. Si existe detección, cargar sus imágenes y detecciones paginadas.
8. Si existe clasificación, cargar predicciones y resumen conservando sus identificadores de RUN.
9. Presentar estados parciales explícitos cuando todavía no existan resultados.

**Ejemplo verificado contra la base real**

| Entidad | Resultado |
|---|---|
| Análisis | `0eaed5d3-9e9a-4aac-8003-d207be388823` |
| Estado del workflow | `classification_completed` |
| Muestra | `d8a3f7b3-57c0-42d4-a0e4-fe522726583d` |
| Frotis | `7e61f33d-9426-4c27-9432-d5da4460a24d` |
| Imagen | `8f914c58-2a62-40a2-84eb-eb30c3a2f446`, 514 × 514 px |
| Detección RUN | `111ca124-8b41-4870-81af-6fc766615aa5` |
| Clasificación RUN | `4a5d7189-9cfd-4b1c-ac99-76d600469e62` |
| Modelo | `biomedclip_fine_tuning`; `model_version` es null |
| Célula del enlace | `e6f4d3bd-1d57-4465-a824-9211e7b8ce26` |
| Código celular | `CELL-69545AFC1253` |
| Predicción del enlace | `7c2c994a-61f1-432a-ae46-6eb6727ec138` |
| Bounding box | x=24, y=90, ancho=42, alto=38 |

La predicción y la detección proporcionadas pertenecen efectivamente al análisis y a la imagen del ejemplo. La jerarquía se puede recuperar sin enviar esos UUID adicionales.

**Datasource**

`App.tsx` añade globalmente `datasource` a la query cuando falta. Los endpoints científicos anteriores no dependen de él.

La ruta puede funcionar con `analysisId` como único dato obligatorio conservando esa normalización global. El shell podría añadir `?datasource=malaria` automáticamente. Exigir que la URL permanezca literalmente sin query entra en conflicto con conservar intacta la regla actual; no es necesario para resolver el análisis.

**Análisis antiguos o incompletos**

- UUID inválido: estado de identificador inválido.
- Análisis inexistente: 404.
- Sin detección: imagen y calidad disponibles, sin células inventadas.
- Sin clasificación: revisión de detecciones disponible, sin predicciones inventadas.
- Ejecución fallida: mostrar estado y evidencia persistidos.
- Imagen archivada, inaccesible o con integridad inválida: error de contenido separado del error del análisis.
- Jerarquía no recuperable por los joins actuales: informar inconsistencia; no reconstruir relaciones mediante nombres.

### 5. Matriz de reutilización de las cinco vistas

| Vista | Reutilización posible | Integración científica necesaria |
|---|---|---|
| Full Field Review | Composición de `FullFieldView`, minimapa y controles visuales | Imagen auténtica, coordenadas y overlays del RUN |
| Specimen Quality | Estructura de `QualityView` | Métricas de `analysis_run.images`, decisiones y eventos reales |
| Analysis Area | Presentación compartida de `FullFieldView` | Contrato de región y persistencia de selección espacial |
| Review Cells | Layout de galería/visor y patrones de interacción | UUID reales, paginación, predicciones, revisión y anotaciones |
| Report | Estructura visual de `ReportView` | Resumen científico real, revisión humana y navegación a resultados |

La maqueta de reporte contiene conceptos de diferencial hematológico que no equivalen al clasificador binario real `parasitized` / `uninfected`. Tampoco deben trasladarse al dominio real sus categorías, recuentos o mediciones simuladas.

**Componentes conectados prioritarios**

En `frontend/src/components/cell-review/`:

- `CellReviewWorkspace`: selección, filtros, galería, navegación relativa, pendientes, revisiones y resultados.
- `CellImageViewer`: imagen autenticada, zoom/pan, bounding boxes, etiquetas, grilla, minimapa y enfoque celular.
- `ScientificAnnotations`: recuperación, creación, edición e historial.
- `CellClassificationAuditModal`: auditoría de clasificación.
- `CellGradCamPreview`: presentación de explicaciones.
- `AuthenticatedCellImage`: carga autenticada y ciclo de vida de object URLs.
- `useControlBarMenu`: gestión de menús.
- `SmearAnalysisImmersiveView`: composición compartida del flujo conectado.

`CellReviewWorkspace` ya contiene funciones como `selectDetection`, `selectRelative`, `nextUnreviewed`, `submitReview` y `submitHumanClassification`. Conviene extraer sus capacidades gradualmente, conservando pruebas y consumidores actuales.

Los menús de filtros, resultados y herramientas ofrecen patrones reutilizables; no constituyen todavía un sistema general de menú contextual espacial por región o frotis.

### 6. Arquitectura frontend propuesta

Añadir una nueva feature y una nueva ruta protegida dentro del `Layout` existente. Los nombres siguientes son propuestas, no archivos existentes:

```text
MicroscopePage
  └─ MicroscopeWorkspaceProvider
      ├─ MicroscopeHeader
      ├─ PreparationNavigator
      ├─ WorkspaceStage
      │   ├─ ImageLoading
      │   ├─ TechnicalValidation
      │   └─ MicroscopeCanvas
      ├─ ActiveViewPanels
      ├─ OpticalInstruments
      └─ AIReviewInstruments
```

El provider mantendría las identidades y selecciones compartidas. Los datos científicos continuarían procediendo del cliente API y de PostgreSQL.

**Tres estados dentro del mismo workspace**

- **Carga:** resolución de análisis y contenido.
- **Validación técnica:** representación de calidad, cola y eventos existentes, con línea horizontal animada.
- **Exploración:** imagen e instrumentos científicos disponibles.

La animación debe reflejar actividad real. Abrir un análisis ya completado no debería repetir artificialmente el procesamiento ni ejecutar operaciones de calidad o inferencia.

La carga inicial de esta ruta debe ser de lectura. `useSmearAnalysisWorkflow` contiene caminos que crean o ejecutan etapas; no conviene reutilizar su orquestación completa como loader del microscopio.

**Header e instrumentos**

Conservar el header global y añadir una sola barra compacta con:

- Full Field Review.
- Review Cells.
- Report.
- Instrumentos ópticos.
- Instrumentos IA y revisión.

`Specimen Quality` y `Analysis Area` pueden convertirse en herramientas o paneles internos.

Los paneles activos deben reservar espacio en el layout. Los instrumentos flotantes se posicionarían dentro del rectángulo restante, con recolocación al cambiar tamaño o paneles; en pantallas pequeñas, pasarían a drawer o barra integrada.

Se deben conservar `tokens_frotis_v2.css`, el ámbito `.frotis-v2` y las reglas documentadas en `DESIGN-SYSTEM.md`. Los estilos existentes de `cell-review` necesitarán una adaptación visual controlada al incorporarse al nuevo espacio.

### 7. Contexto de observación, selección y anotaciones

**Estado actual del historial**

`SmearAnalysisReadOnlyView`, en `frontend/src/pages/SmearWorkflow.tsx`, conserva selección mediante `image`, `selected_detection` y `selected_prediction`.

Sus callbacks combinan actualizaciones de query mediante una referencia sincrónica. `CellReviewWorkspace` puede resolver una predicción a su detección e imagen y coordina solicitudes para evitar selecciones obsoletas.

El nuevo módulo debería reutilizar esa lógica de identidad mediante estado compartido, sin obligar a serializarla en la URL.

**Persistencia espacial propuesta**

Guardar por usuario, análisis, frotis e imagen:

```text
analysisId, slideId, imageId
detectionRunId, classificationRunId
selectedDetectionId, selectedPredictionId
centerInOriginalPixels, zoom
activeView, filters, overlays
instrumentVisibility
imageIdentity/hash, contextFormatVersion
```

El centro debe mantenerse en píxeles originales, no en coordenadas CSS. Al restaurar, validar pertenencia, dimensiones y RUNs.

La primera fase puede utilizar almacenamiento local como preferencia de observación. PostgreSQL seguiría siendo la autoridad científica. La recuperación entre dispositivos requeriría una capacidad backend adicional.

Actualmente `CellImageViewer` ejecuta `fit()` al cambiar de imagen y mantiene zoom y centro en estado local. Se necesita una interfaz controlada de viewport para recuperar ese contexto.

**Desde el reporte**

Una acción sobre un resultado puede comunicar `predictionId` al workspace, resolver su detalle y derivar detección e imagen. No necesita transmitir tres identificadores redundantes. Debe validar también su pertenencia al análisis y a la clasificación correspondiente.

El enlace canónico con solo `analysisId` abre el análisis; compartir una célula exacta entre dispositivos exigiría una referencia opcional o un contexto persistido adicional.

**Anotaciones reales**

`scientific_validation_annotations` admite:

| Alcance | Estado real |
|---|---|
| Célula | Disponible mediante `cell_detection_id` |
| Análisis | Disponible mediante `analysis_run_id` |
| Muestra | Disponible mediante `sample_id` |
| Frotis | No disponible |
| Imagen/región | No disponible |

El CHECK de `target_type` permite únicamente `cell`, `analysis` y `sample`. Hay versionado e historial en `scientific_validation_annotation_events`.

El endpoint general es `/api/v1/scientific-annotations`; también existen operaciones por sesión de validación. La lista general exige exactamente el identificador correspondiente al target.

El alcance inicial debe derivarse de la acción: célula seleccionada → célula; acción global → análisis. Una nota de muestra no debe presentarse como nota de frotis, pues una muestra puede tener varias preparaciones.

La consulta real no devolvió anotaciones existentes. Se verificaron estructura y operaciones, pero no la recuperación de una nota poblada del ejemplo.

### 8. Brechas reales

| Brecha | Consecuencia |
|---|---|
| Un análisis referencia un frotis | No se puede prometer multifrotis bajo el mismo UUID con el contrato actual |
| Anotaciones sin target frotis o región | Dos alcances solicitados requieren evolución posterior |
| Viewport sin persistencia espacial | Se pierde posición al cambiar de imagen |
| Vistas v2 con datos simulados | Necesitan adaptadores y sustitución de estados científicos |
| Selección del RUN más reciente | Puede cambiar el contexto al aparecer una nueva ejecución |
| Capturas sin registro espacial explícito | No permiten afirmar continuidad física |
| Contenido servido como archivo completo | Falta validar infraestructura para WSI y lectura parcial |
| Identidad celular por detección | No existe correspondencia física garantizada entre RUNs |
| Reporte v2 demostrativo | Requiere adaptación al dominio y resultados actuales |

Para multifrotis, la adaptación mínima inicial es explorar **preparaciones relacionadas de la misma muestra**, indicando que pertenecen a otros análisis. Eso no equivale a incluirlas en el análisis original.

Cumplir literalmente “un análisis contiene varios frotis” requiere acordar un nivel de agrupación y evolucionar el contrato. No conviene redefinir silenciosamente `analysisId` como muestra, caso o agrupación.

### 9. Evaluación preliminar del motor de imagen

| Alternativa | Adecuación | Límites |
|---|---|---|
| `SlideViewer` de la maqueta | Referencia de interacción y apariencia | Geometría y métricas simuladas |
| `CellImageViewer` conectado | Mejor punto inicial para capturas actuales | Archivo completo, overlays SVG y estado local |
| Viv + deck.gl | Candidato para imágenes multiescala y bioimagen avanzada | Requiere validar formatos, transporte y adaptación de coordenadas |

Viv ofrece renderizado de OME-TIFF y OME-NGFF y componentes basados en capas de deck.gl. Es una opción razonable para una fase multirresolución, sin que eso garantice compatibilidad directa con cualquier formato WSI. [Proyecto Viv](https://www.hidivelab.org/research/projects/viv/), [repositorio oficial](https://github.com/hms-dbmi/viv).

deck.gl dispone de `TileLayer`, que carga tiles visibles, y `BitmapLayer`, que renderiza imágenes; permite composición en vistas no geográficas. Esa capacidad exige que existan tiles o un mecanismo de carga apropiado. [TileLayer](https://deck.gl/docs/api-reference/geo-layers/tile-layer), [BitmapLayer](https://deck.gl/docs/api-reference/layers/bitmap-layer).

Deben distinguirse tres representaciones:

- **Matriz de capturas:** colección organizada; sus posiciones no prueban continuidad física.
- **Mosaico registrado:** capturas con transformaciones y solapamientos definidos en coordenadas comunes.
- **Pirámide multirresolución:** versiones de distinta resolución de un mismo espacio registrado.

`image_sequence_number` solo aporta orden. No demuestra fila/columna, posición del escenario ni transformación de registro. `metadata_json` tampoco constituye por sí mismo un contrato espacial.

**Recomendación:** reutilizar primero `CellImageViewer` detrás de una interfaz de viewport. Evaluar Viv con un archivo representativo cuando existan requisitos y datos WSI concretos. Verificar lectura parcial, autenticación, CORS, memoria, compatibilidad de compresión y correspondencia de overlays antes de elegirlo.

### 10. Plan incremental

| Fase | Resultado | Dependencias y riesgos | Pruebas necesarias |
|---|---|---|---|
| 1. Resolver por UUID | Nueva ruta con jerarquía real | Mantener semántica del análisis | UUID válido/inválido, 404, 401/403, estados parciales |
| 2. Workspace continuo | Carga, validación y exploración en el mismo shell | Evitar ejecución automática al abrir | Transiciones, eventos, error de imagen, movimiento reducido |
| 3. Captura y células reales | Visor, selección y galería conectados | Paginación y pertenencia entre RUNs | Selección galería/overlay, pendientes, solicitudes tardías |
| 4. Contexto espacial | Restauración por imagen y preparación | Contexto obsoleto o imagen distinta | Cambiar, volver, recargar, borrar contexto y validar fallback |
| 5. Revisión y anotaciones existentes | Operaciones científicas reutilizadas | Permisos, concurrencia y auditoría | Corrección, historial, conflictos de versión y recarga |
| 6. Reporte integrado | Resumen real y enfoque de resultados | Evitar categorías simuladas | Resultado → predicción → célula → imagen |
| 7. Multifrotis y nuevos alcances | Contrato acordado para preparación y región | Requiere decisión de dominio y evolución posterior | Aislamiento por preparación y linaje |
| 8. WSI/tiles | Motor seleccionado con evidencia | Formatos, transporte y rendimiento | Memoria, carga parcial, cancelación, zoom y overlays |

Las pruebas de regresión deben cubrir las rutas actuales, los enlaces completos del historial, su navegación y la normalización global de datasource. También deben comprobar que el nuevo workspace no introduce llamadas de creación, calidad, detección o clasificación al abrir un análisis.

**Decisión recomendada:** avanzar primero con una ruta nueva que use `getSmearAnalysisHistoryDetail(analysisId)` y los componentes científicos conectados. Validar por separado el alcance multifrotis y los targets de anotación pendientes antes de prometerlos como capacidades existentes.