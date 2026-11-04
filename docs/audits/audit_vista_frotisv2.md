La integración de FULL FIELD REVIEW es viable con los servicios actuales de Historial. Recomiendo la alternativa A: /frotis/analisis-2/full-field-review/:analysisRunId, conservando las rutas estáticas actuales.

Los cambios principales serían compartir la carga y selección hoy contenidas en Historial, adaptar el visor a imágenes y coordenadas reales, y excluir datasource de la nueva URL. No modifiqué archivos ni implementé la integración.

A. Diagnóstico de navegación

El contrato real de Historial es:
/frotis/historial/:analysisRunId
  ?datasource=malaria
  &image=<microscopy_image_id>
  &selected_detection=<cell_detection_id>
  &selected_prediction=<cell_prediction_id>
El nombre real del parámetro de path es analysisRunId. Se valida como UUID antes de montar el detalle. Los tres parámetros de selección son opcionales.
Elemento	Comportamiento encontrado
Listado de Historial	HistoryRow construye «Ver detalle» con routes.smearHistoryDetail(item.analysis_run_id) y conserva location.search completo.
Navegación desde el análisis operativo	goToHistory construye el detalle histórico y transmite exclusivamente datasource, image, selected_detection y selected_prediction, cuando existen.
Regreso al listado	backToHistory elimina los tres parámetros de selección y conserva los demás.
Menú «Análisis de frotis 2»	Abre la entrada estática, sin identificador de análisis.
Entrada de la maqueta	Redirige a review-cells, conservando la query.
Pestañas nuevas	Construyen rutas estáticas y conservan location.search; no transportan un análisis en el path.
Redirecciones antiguas	/frotis/cargar, /frotis/analisis y /frotis/revision conducen al workflow original. No conducen a la maqueta.
Acción para abrir FULL FIELD REVIEW real	No existe actualmente.


Por tanto, la navegación sigue abriendo /frotis/historial/:analysisRunId porque ese destino está expresamente programado. No encontré una redirección incorrecta que estuviera impidiendo abrir Análisis de frotis 2. Falta una acción específica para ese destino.

Los enlaces actuales de «Ver detalle», regreso a Historial y consulta del workflow deben conservarse. Para la integración posterior recomiendo una acción diferenciada, por ejemplo «Abrir FULL FIELD REVIEW», sin reemplazar automáticamente los enlaces históricos.

Evidencia: [SmearAnalysisHistory.tsx (line 50)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/frontend/src/pages/SmearAnalysisHistory.tsx:50), [goToHistory (line 1101)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/frontend/src/pages/SmearWorkflow.tsx:1101) y [declaraciones de rutas (line 121)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/frontend/src/App.tsx:121).

La comparación de alternativas queda así:
Alternativa	Impacto	Evaluación
A. /full-field-review/:analysisRunId	Añadir una ruta contextual, reconocerla en el header y construir sus enlaces.	Recomendada: integra únicamente la página autorizada y mantiene las rutas actuales.
B. /review-cells/:analysisRunId	Introduce el contexto bajo otra pestaña.	No corresponde al alcance inicial y haría ambiguo qué página está integrada.
C. /:analysisRunId/full-field-review	Permite agrupar todas las páginas bajo un análisis, pero requiere organizar una nueva rama contextual y su navegación.	Es válida para una integración conjunta posterior; supone mayor intervención ahora.


La URL recomendada sería:
/frotis/analisis-2/full-field-review/<analysisRunId>
  ?image=<microscopy_image_id>
  &selected_detection=<cell_detection_id>
  &selected_prediction=<cell_prediction_id>
No necesita analysis_id en query ni datasource.

Hay dos ajustes imprescindibles:
1. AnalisisFrotis2Page determina la pestaña con pathname.endsWith("/" + route.path). Una ruta terminada en UUID caería actualmente en REVIEW CELLS. Debe reconocerse mediante el patrón de ruta.
2. App.tsx añade datasource automáticamente a cualquier URL que no lo tenga. También lo incorporan el menú lateral, las migas de pan y el selector global. La política de omitirlo debe aplicarse solo al nuevo contrato contextual, conservando el comportamiento actual de Historial y del resto del frontend.
Evidencia: [entrada de la maqueta (line 19)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/frontend/src/features/analisis-frotis-v2/AnalisisFrotis2Page.tsx:19) y [normalización global de datasource (line 64)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/frontend/src/App.tsx:64).

B. Diagnóstico de backend y contratos reutilizables

Los siguientes servicios existen tanto en el cliente frontend como en las rutas del backend:
Necesidad	Cliente existente	Endpoint GET
Listar análisis	getSmearAnalysisHistory	/api/v1/scientific/workflows
Cargar un análisis histórico	getSmearAnalysisHistoryDetail	/api/v1/scientific/analysis-history/{analysisRunId}
Obtener ejecución de detección	getCellDetectionRun	/api/v1/cell-analysis/detection-runs/{detectionRunId}
Obtener imágenes de detección	getCellDetectionImages	/api/v1/cell-analysis/detection-runs/{detectionRunId}/images
Obtener detecciones de una imagen	getCellDetections	/api/v1/cell-analysis/detection-runs/{detectionRunId}/images/{imageId}/detections
Obtener detalle de detección	getCellDetection	/api/v1/cell-analysis/detections/{detectionId}
Obtener original autenticado	getCellOriginalImageBlob	/api/v1/cell-analysis/detection-runs/{detectionRunId}/images/{imageId}/content
Obtener crop autenticado	getCellCropBlob	/api/v1/cell-analysis/crops/{cropId}/content
Obtener ejecución de clasificación	getCellClassificationRun	/api/v1/cell-classification/classification-runs/{classificationRunId}
Obtener predicciones por imagen	getCellClassificationPredictions	/api/v1/cell-classification/classification-runs/{classificationRunId}/predictions
Obtener predicción individual	getCellPrediction	/api/v1/cell-classification/predictions/{predictionId}
Obtener resumen existente	getCellClassificationSummary	/api/v1/cell-classification/classification-runs/{classificationRunId}/summary


No hace falta crear endpoints ni un segundo cliente HTTP.

El detalle histórico devuelve SmearWorkflowResponse: sujeto, caso, muestra, portaobjetos, imágenes, análisis, detección, clasificación y resumen. El backend conserva el análisis solicitado, pero selecciona la ejecución de detección más reciente del análisis y la clasificación más reciente de esa detección. La URL actual no fija esas dos ejecuciones adicionales.

Las relaciones relevantes son:
analysisRunId
  └─ detection_run.id
       ├─ imágenes: microscopy_image_id
       ├─ detecciones: cell_detection_id
       └─ classification_run.id
            └─ predicciones
                 ├─ cell_detection_id
                 ├─ microscopy_image_id
                 └─ crop_id
image representa microscopy_image_id; no debe confundirse con analysis_run_image_id, sample_id o crop_id.

Los contratos reutilizables son:
- SmearWorkflowResponse, en services/api.ts.
- CellDetectionRunDetail, CellDetectionImage, CellDetectionSummary y CellDetectionDetail, en types/cellReview.ts.
- CellClassificationRunDetail, CellPredictionSummary, CellPredictionDetail y SmearAnalysisSummary, en types/cellClassification.ts.
Evidencia: [cliente API (line 797)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/frontend/src/services/api.ts:797), [contratos de detección (line 87)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/frontend/src/types/cellReview.ts:87) y [resolución del análisis histórico (line 511)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/backend_api/app/services/smear_workflow.py:511).

La reutilización de hooks tiene un límite importante:
Código	Reutilización
useSmearAnalysisHistoryDetail	Directa: carga, estado inicial, error y protección frente a respuestas después del desmontaje.
useAuthenticatedObjectUrl	Directa: carga del binario, cancelación, creación y liberación de object URLs.
AuthenticatedImageCacheProvider	Disponible para crops; no es una caché general del análisis.
CellReviewWorkspace	Contiene la carga de imágenes, detecciones, predicciones y la reconciliación de selección. Esa lógica todavía no está separada en hooks.
CellImageViewer	Contiene geometría, zoom, pan, overlays y minimapa. Su presentación es diferente de la maqueta.
useSmearAnalysisWorkflow	No conviene reutilizarlo completo: controla carga, cola y ejecución del pipeline, fuera del alcance de consulta de FFR.


Las imágenes deben seguir pasando por el cliente autenticado; no mediante <img src={content_url}> sin bearer. El cliente restringe las URLs de contenido aceptadas, y el backend comprueba pertenencia de la imagen a la ejecución y disponibilidad/integridad del archivo.

La autenticación usa AuthProvider y ProtectedRoute. Las lecturas están protegidas por permisos como scientific.analysis.read, scientific.cell_detection.read y scientific.cell_classification.read. La guarda frontend por sí sola no sustituye esa autorización del backend.

Aunque se llama SmearAnalysisReadOnlyView, Historial permite determinadas acciones humanas según permisos —revisión, clasificación humana, anotaciones y explicación—. No debe asumirse que montar sus componentes completos equivalga a una consulta sin mutaciones.

Los servicios científicos inspeccionados utilizan internamente get_primary_engine(), cuyo datasource predeterminado es malaria. Sus métodos de lectura anteriores no requieren transmitir datasource desde la URL.

C. Matriz de compatibilidad de FULL FIELD REVIEW

Para abreviar la tabla:
- H: useSmearAnalysisHistoryDetail.
- S: selección y carga actualmente dentro de CellReviewWorkspace; requiere extracción compartida.
- V: geometría y viewport actualmente dentro de CellImageViewer; requiere adaptación compartida.
- B: getCellOriginalImageBlob + useAuthenticatedObjectUrl.
- Local: operación del navegador o estado visual, sin nueva operación de negocio.
Control	Comportamiento actual	Equivalente Historial	Servicio o hook	Parámetros	Adaptación mínima	Backend	Riesgo	Estado
Carpeta: selector de casos	Selecciona mockCases y reinicia células	Listado de análisis	getSmearAnalysisHistory, H	analysisRunId	Usar análisis reales al entrar al contexto FFR	Sí, GET	Confundir caso con ejecución	Adaptación
X del caso activo	Abre el mismo selector	Navegación entre análisis	Constructor de ruta, H	analysisRunId	Conservar la acción de selección	Sí, GET	No representa cerrar ni borrar un análisis	Adaptación
Cinco pestañas del header	Navegan entre páginas estáticas	No existe ese header	Router	ID y selección para FFR	Reconocer ruta contextual; mantener las otras cuatro páginas estáticas	No adicional	Perder contexto o mostrar otra pestaña activa	Adaptación
Compartir/exportar	Abre ExportModal	Sin exportación equivalente de este análisis	Modal local	Caso simulado	Mantener carácter demostrativo; no exportar datos ficticios como reales	No	CSV hematológico no corresponde a malaria	Sin equivalente
Configuración de escaneo	Muestra aviso demostrativo	No hay control del escáner en este flujo	alert local	Ninguno	Mantener respuesta explícita	No	Presentarlo como escáner conectado	Local
Presets 1, 2 y 3	Cambian filtros visuales	Sin presets equivalentes	Estado imageAdjustments	Ninguno	Aplicarlos a la imagen real, sin alterar el original	No adicional	Confundir ajuste visual con procesamiento persistido	Local
Sliders del header y del visor	Abren ajustes	Sin popover equivalente	ImageAdjustmentsPopover	Ninguno	Conservar estado visual compartido	No	Ninguno de integración de datos	Local
Brillo, contraste, saturación y gamma	Modifican CSS/SVG	Operación posible sobre el original	B + filtros existentes	Imagen	Aplicar filtros al original autenticado	Solo carga	No modificar datos o predicciones	Local
RESET de ajustes	Restablece filtros	Operación de navegador	Callback existente	Ninguno	Conservar	No	Bajo	Local
Layout dividido/galería/visor	Cambia layoutMode	Historial tiene otros paneles	Estado local	Ninguno	En FFR actualmente no cambia la composición; no introducir otra página	No	Aparentar un efecto que esta vista no consume	Local
INFO de paciente	Muestra edad y sexo simulados	Contexto de sujeto/muestra	H	analysisRunId	Mostrar solo metadatos disponibles	Sí, GET	El contrato no garantiza edad, sexo ni MRN	Adaptación
Estado Reviewing/Flagged/Approved/Signed-off	Cambia estado local del caso	Estados de ejecución diferentes	H para lectura	analysisRunId	No asociarlo automáticamente a un cambio persistido	Lectura disponible; escritura equivalente no	Semánticas incompatibles	Sin equivalente
HTML autocontenido: abrir modal	Abre recurso demostrativo	Sin equivalente de análisis real	StandaloneHtmlModal	Ninguno	Conservar como maqueta	No API	El HTML no incluye el análisis real	Local
Copiar/descargar/abrir HTML y cerrar	Clipboard, descarga y pestaña	Operaciones del navegador	Recurso HTML local	Ninguno	Sin servicio nuevo	No API	Confundir demo con exportación del caso	Local
CSV del modal	Descarga categorías simuladas	No existe el mismo diferencial en Historial	downloadCsv	Categorías mock	No convertirlo automáticamente en reporte de malaria	No	Categorías y totales incompatibles	Sin equivalente
Imprimir/guardar PDF	Invoca window.print()	Operación de navegador	Navegador	Vista actual	Mantener impresión local	No	No equivale a informe clínico generado	Local
Cerrar modal de exportación	Cambia estado local	Operación local	Callback existente	Ninguno	Conservar	No	Bajo	Local
Mapa de densidad celular	Activa overlay y concentración fija	No encontré equivalente de densidad	showHeatmap	Ninguno real	Mantenerlo explícitamente demostrativo/no disponible para datos reales	No equivalente	No es un heatmap Grad-CAM	Sin equivalente
Imagen/campo principal	Dibuja textura y células sintéticas	Original autenticado por imagen	H, S, B	Análisis, detección, imagen	Sustituir contenido sintético por original y dimensiones reales	Sí, GET	Imagen individual no equivale a un portaobjetos digital completo	Adaptación
Clic en célula, tooltip y selección	Selecciona ID numérico; centra porcentajes	Selección de detección y predicción asociada	S	Imagen, detección, predicción opcional	Conservar UUID y cajas reales	Sí, GET	No usar índices numéricos como identidad	Adaptación
Mostrar/ocultar marcadores	Oculta anillos de células	Mostrar cajas y selección	S, V	Detecciones de imagen	Dibujar overlay sobre cajas reales	Sí para datos; toggle local	Anillo mock no contiene geometría real	Adaptación
Menú regla NONE/LINE/CROSS/CIRCLE	Activa retícula	Sin medición equivalente	Estado local	Calibración ausente	Conservar como demostración; no declarar medidas reales	No equivalente	Falta conversión verificable píxel–µm	Sin equivalente
Tamaño de regla, arrastre y recentrado	Cambia tamaño/posición en campo sintético	Geometría de selección disponible	V	Caja y dimensiones	Posicionamiento reutilizable; medición física no	No adicional	Factores de escala arbitrarios	Adaptación
HPF Grid	Rejilla de 12×8 campos	Rejilla visual de Historial	V	Dimensiones de imagen	Reutilizar rejilla local sin afirmar HPF calibrado	No adicional	Campo visual no es área física validada	Adaptación
Presets 10x/20x/40x/100x	Asignan valores de zoom local	Zoom digital	V	Dimensiones	Adaptar al viewport real; distinguir zoom digital de aumento óptico	No adicional	Etiquetas ópticas no sustentadas	Adaptación
Acercar, alejar y rueda	Escalan campo sintético	Zoom digital	V	Dimensiones y centro	Compartir mecánica, conservar botones	No adicional	Rangos y unidades distintos	Adaptación
Arrastre del campo	Cambia pan	Pan limitado a imagen real	V	Dimensiones y zoom	Compartir transformación en coordenadas reales	No adicional	Desalineación de imagen y cajas	Adaptación
Home/restablecer	Vuelve a coordenadas fijas	Ajustar imagen y centrar	V	Dimensiones	Usar centro real y ajuste a ventana	No adicional	No reutilizar offsets mock	Adaptación
Minimapa y clic para desplazarse	Portaobjetos sintético y offsets fijos	Minimapa de imagen real	B, V	Imagen, dimensiones, viewport	Reutilizar geometría; mantener su presentación	Sí para imagen	Historial no tiene el mismo clic de navegación del mock	Adaptación
Barra de escala µm/mm	Valor calculado solo por zoom mock	Sin escala física equivalente	calculateScaleBar	Calibración ausente	No presentarla como medida real	No equivalente	Medición incorrecta	Sin equivalente
Scan Info: abrir/cerrar	Fecha, superficie, tinción y resolución mock	Metadatos de análisis e imagen	H, S	Análisis e imagen	Mostrar valores presentes; ausentes como no disponibles	Sí, GET	Fecha de análisis no equivale a fecha de escaneo	Adaptación


Dos precisiones sobre controles y modales:
- En FFR, pulsar una célula solo ejecuta setSelectedCellId; no abre CellDetailModal. Las notas se abren desde REVIEW CELLS. Ambos componentes existen en el padre, pero no son acciones visibles propias de FFR.
- isFullscreen no tiene un control visible asociado. rulerMeasurement comienza en null y no encontré una asignación de medición; su badge de distancia y cierre son inalcanzables actualmente. No hay que contabilizarlos como funcionalidades operativas.
La fuente de esta evaluación es [FullFieldView (line 15)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/frontend/src/features/analisis-frotis-v2/components/FullFieldView.tsx:15), [SlideViewer (line 24)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/frontend/src/features/analisis-frotis-v2/components/SlideViewer.tsx:24) y [Header (line 29)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/frontend/src/features/analisis-frotis-v2/components/Header.tsx:29).

D. Compatibilidad de parámetros y escenarios

La tabla distingue comportamiento deducido del código de una garantía probada en navegador. No ejecuté estos catorce escenarios contra datos reales.
Escenario	Historial actual	Comportamiento que debe reutilizar FFR
1. Solo análisis	Carga contexto, elige primera imagen disponible y normalmente primera detección.	Mismos valores iniciales; manejar análisis sin resultados.
2. Análisis + imagen	Selecciona la imagen si pertenece al conjunto disponible.	Mismo identificador y comprobación de pertenencia.
3. Análisis + imagen + detección	Busca la detección entre los overlays cargados de esa imagen.	Misma selección y fallback.
4. Análisis + imagen + predicción	Consulta la predicción y trata de resolver su imagen/detección.	Reutilizar reconciliación; probar especialmente conflictos con imagen explícita.
5. Cuatro identificadores	Combina selección de imagen, detección y predicción.	Preservar cuando sean coherentes; caracterizar combinaciones contradictorias.
6. Imagen inexistente	Puede caer a primera imagen disponible y normalizar query.	No convertir ese fallback en un error nuevo sin acuerdo.
7. Detección inexistente	Si no aparece en overlays, selecciona una alternativa disponible o ninguna.	Mismo fallback y sincronización URL.
8. Predicción inexistente	Su consulta inicial puede ignorarse; la selección termina derivándose de datos disponibles.	No bloquear el análisis completo por selección opcional inválida.
9. Detección de otra imagen	No se acepta como candidata si no está en overlays de la imagen activa.	Mantener pertenencia; no superponer cajas de otra imagen.
10. Predicción no vinculada a detección	La lista de predicciones puede seleccionar su propia detección; no hay una regla única explícita para todos los conflictos.	Compartir el mecanismo y añadir pruebas de caracterización antes de cambiar prioridades.
11. Acceso directo	El path carga análisis y la query reconstruye selección.	Igual, con validación del UUID y sin datasource en nueva URL.
12. Recarga	Reconstruye desde backend y URL; pierde zoom/pan local.	Igual.
13. Atrás/adelante	Detecta cambios externos de selección; los cambios internos de selección usan replace: true.	Igual: no crear una entrada de historial por cada clic.
14. Cambiar imagen con detección seleccionada	Limpia selección, recarga listas y resuelve una nueva selección/predicción.	Reutilizar callbacks y actualización conjunta de query.


Hay dos límites importantes:
- Historial carga hasta 500 detecciones para overlay y 500 predicciones por imagen en esas consultas. Una selección fuera de esa ventana puede no restaurarse. El backend admite paginación; no debe afirmarse que el frontend actual restaura cualquier elemento del conjunto completo.
- La resolución de una predicción y la de detecciones ocurre en flujos asíncronos distintos. No encontré una validación central que garantice una prioridad uniforme ante identificadores contradictorios, ni que todas las predicciones solicitadas pertenezcan a la clasificación activa antes de influir en la selección.
Son riesgos existentes que deben caracterizarse; no propongo corregirlos silenciosamente solo en FFR.

Evidencia: [reconciliación y carga del workspace (line 462)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/frontend/src/components/cell-review/CellReviewWorkspace.tsx:462) y [sincronización histórica de query (line 938)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/frontend/src/pages/SmearWorkflow.tsx:938).

E. Arquitectura y secuencia recomendadas

La presentación debe seguir separada. No recomiendo insertar SmearAnalysisReadOnlyView, SmearAnalysisImmersiveView ni CellReviewWorkspace completos dentro de la maqueta.

La estructura compartida propuesta sería:
Cliente API existente + contratos actuales
                  │
useSmearAnalysisHistoryDetail — contexto del análisis
                  │
Carga y selección compartidas extraídas del workspace
                  │
         ┌────────┴────────┐
         │                 │
Presentación Historial   Presentación FFR
         │                 │
         └── geometría/viewport compartidos ──┘
Los hooks de selección/carga y viewport del diagrama son extracciones propuestas, no piezas ya existentes.

Para FFR real deben conservarse UUID, bbox_x, bbox_y, bbox_width, bbox_height y coordinate_space: "original_image_pixels". No basta con convertirlos a los CellItem numéricos y porcentuales de la maqueta. Sus categorías leucocitarias tampoco equivalen a las etiquetas parasitized y uninfected.

La secuencia de menor riesgo es:
1. Caracterizar selección actual. Cubrir combinaciones válidas, inválidas y contradictorias, paginación y navegación del navegador.
2. Añadir el contrato de ruta A. Validación de UUID, constructor de enlaces y política acotada sin datasource. Conservar el detalle histórico.
3. Extraer carga y selección de solo lectura. Reutilizarlas desde Historial sin cambiar su comportamiento ni sus acciones humanas.
4. Conectar exclusivamente FFR. Usar el hook histórico para contexto y los servicios existentes para imagen, detecciones y predicciones.
5. Compartir geometría del visor. Extraer únicamente la mecánica necesaria de CellImageViewer, manteniendo la presentación de ambas interfaces.
6. Conservar las otras cuatro páginas y sus mocks. No presentar sus reportes, categorías o estados simulados como resultados del análisis real.
7. Añadir una acción explícita de apertura de FFR, una vez autorizado el origen del enlace.
Los archivos que previsiblemente requerirían cambios son:
Área	Archivos
Contrato y navegación	App.tsx, router.ts, features/analisis-frotis-v2/routes.ts, AnalisisFrotis2Page.tsx
Política URL sin datasource	App.tsx y constructores/callbacks del shell que alcancen la nueva ruta
Presentación FFR	FullFieldReviewPage.tsx, FullFieldView.tsx, SlideViewer.tsx; adaptación acotada de props del Header
Extracción compartida	CellReviewWorkspace.tsx y CellImageViewer.tsx, con hooks de carga/selección y viewport propuestos
Acción de apertura	El componente de origen que se acuerde; previsiblemente el listado de Historial
Verificación	Pruebas existentes de Historial/workspace y pruebas de navegación contextual FFR


services/api.ts, los contratos científicos y useAuthenticatedObjectUrl se reutilizan. No hay necesidad identificada de modificar endpoints, PostgreSQL ni modelos de IA.

Los riesgos prioritarios son la geometría sintética, los identificadores contradictorios, los límites de carga, el datasource reinsertado por el shell y los controles que aparentan mediciones o persistencia sin contrato equivalente. No encontré un contrato de mosaico de portaobjetos completos, pirámides o stitching en este flujo: el contenido existente es una imagen microscópica individual.

Verificación de esta auditoría y decisiones pendientes

Ejecuté 54 pruebas existentes, con 54 aprobadas y 0 fallos, correspondientes a Historial, workspace, rutas, autenticación, capacidades humanas, navegación y maqueta.

No ejecuté nuevas pruebas de integración contra backend, consultas a PostgreSQL, build ni TypeScript en esta fase de inspección. Las pruebas existentes revisadas no sustituyen la validación futura de los catorce escenarios con datos reales.

Solo quedan estas decisiones de producto que el código no resuelve:
- Desde qué acción explícita se abrirá FFR: recomiendo una acción secundaria en Historial, conservando «Ver detalle».
- Cómo deben presentarse en el contexto real los controles sin equivalente: regla/escala física, densidad, estado de caso y exportación diferencial simulada.
- Qué prioridad debe regir ante una URL contradictoria entre imagen, detección y predicción. El comportamiento actual no ofrece una regla uniforme suficientemente explícita.
La auditoría queda completada. La implementación permanece pendiente de autorización.