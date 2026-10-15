# SCC-XAI.1 — Visor unificado de explicabilidad científica

Estado documental: `CURRENT_DOC`. Fecha: 2026-10-15.
Estado técnico: visor y FIX de original implementados; compilación aprobada.
Validación del FIX: ver sección final; cinco fallos preexistentes en la suite ampliada de resolución.
**Aceptación visual autenticada pendiente. SCC-XAI.1 no está cerrado: requiere confirmación del usuario en frontend.**

## Auditoría focalizada

Se revisaron `code.html`, `DESIGN.md` y `screen.png` del ZIP Stitch. Se inspeccionaron
los reportes TRAIN/EXPLAIN, sus hooks, las referencias de imágenes originales,
los modales de dominio y CAPSTONE-UI-TOKENS.1. El árbol Git estaba limpio al inicio.

- `RunDetail` ya consulta TRAIN → EXPLAIN mediante `useTrainingExplanations` y el
  endpoint de linaje corregido por SCC-ART.1 FIX.2; se conserva esa recuperación.
- `TrainingExplanationAttempt` abre `AssessmentExplanationDetail`, que conserva
  detalles, verificación, referencia SHAP y páginas de 100 artefactos.
- `useAssessment` y `useAssessmentArtifacts` proporcionan identidad y referencias
  públicas `view=traceability`; el visor reutiliza ambos sin endpoints adicionales.
- `ScientificArtifact` recuperaba blobs mediante `api.getArtifactBlob` y
  `useAuthenticatedObjectUrl`. Esa lógica se extrajo a `useScientificArtifact`,
  consumido tanto por el componente existente como por el visor nuevo.
- Los originales históricos usan `LegacyArtifactMedia`; los crops clínicos tienen
  su propio contrato. Ninguno acredita automáticamente el original de una muestra
  EXPLAIN E6. No se enlazan por filename, orden ni background SHAP.
- Los modales existentes son específicos de despliegue/revisión clínica; no se
  reutilizan sus acciones de negocio. Se usa `dialog` nativo con la primitiva
  `report-viewer`, conforme a la política CSS.
- TRAIN: `/modelo-ia/ejecuciones/:runId?datasource=malaria`.
  EXPLAIN E6: `/modelo-ia/evaluaciones/e6/:attemptId?datasource=malaria`.
  Solo se integra el visor en la primera ruta, dentro de «Explicabilidad por caso».

## Arquitectura y archivos

Nuevos:

- `frontend/src/components/reports/XAIComparisonViewer.tsx`: propietario de recursos,
  observación de visibilidad, modal y presentación única `XAIComparisonContent`.
- `frontend/src/components/reports/TrainingXAIComparison.tsx`: selección de un intento
  por método, recuperación paginada, validación de linaje y páginas de cinco filas.
- `frontend/src/components/reports/xai/comparison.ts`: contrato y adaptador puro de
  agrupación científica; no realiza IO.
- `frontend/src/hooks/useScientificArtifact.ts`: lógica compartida de SCC-ART.1,
  clasificación de fallos, MIME, descarga y URLs temporales.
- `frontend/tests/scc-xai.test.mjs`: pruebas específicas del visor.
- Este contrato, indexado en `docs/README.md`.

Modificados:

- `frontend/src/pages/RunDetail.tsx`: alterna comparación e historial; conserva los
  intentos y la tabla histórica. No rediseña otras secciones.
- `frontend/src/components/reports/ScientificArtifact.tsx`: consume el hook extraído;
  mantiene carga automática/diferida, PNG y descarga de mapas/JSON/CSV.
- `frontend/src/styles/report-components.css`: composición XAI bajo `.ds-report`.
- `frontend/tests/scc-art.test.mjs` y `frontend/tests/e6-lineage.test.mjs`: ajustan
  mocks a la extracción del hook, conservando sus comprobaciones funcionales.
- `docs/README.md`: indexación documental.

## Contrato TypeScript

`XAIComparison` identifica TRAIN, modelo, checkpoint, muestra, dataset, split y
propósito. Admite predicción y clase real opcionales, una referencia original y un
mapa parcial de métodos (`gradcam`, `lime`, `shap`). No sustituye datos ausentes.

`XAIEvidence` separa ejecución (`not_executed`, `pending`, `running`, `completed`,
`failed`) de disponibilidad (`available`, `no_evidence`, `missing`, `denied`,
`integrity_failed`, `not_comparable`, `error`). Conserva intento, identidad de
assessment, artefacto, mensaje, metadatos y referencias background SHAP.

`XAIArtifact` conserva el PK real, fuente, restricciones de intento/TRAIN, hash y
bytes. En el adaptador E6 siempre se proporcionan `source=assessment`, intento y
TRAIN; la opcionalidad de restricciones en el tipo compartido conserva consumidores
TRAIN existentes. El contenedor que aporte un original debe acreditar su relación
con la muestra; el FIX obtiene esa relación por TRAIN, dataset, intento y source_record_id, sin inventar artifact_id.

`XAIGenerationAction` requiere `authorized` y un callback real `execute`.
En el FIX se muestran botones de generación deshabilitados cuando no existe una acción autorizada. El callback
opcional maneja progreso/error, pero no simula resultados ni altera el estado de
evidencia: el contenedor deberá refrescar datos después de una ejecución real.

## Agrupación científica y SCC-CORE.1

Solo se consideran detalles EXPLAIN del TRAIN solicitado. El contenedor valida
además el ID y método seleccionado antes de listar artefactos. Cada referencia
requiere correspondencia explícita de `attempt_id` y `training_run_id`.
Una discrepancia se muestra como no comparable y no obtiene una URL de imagen.

La clave incluye TRAIN, versión de modelo, checkpoint, `sample_id`, dataset,
split, propósito y contexto científico canónico. Este último retiene campos de
modelo/dataset (incluidos input contract y fingerprints disponibles), decisión,
protocolo y campos adicionales no excluidos. El orden de claves JSON es irrelevante.

Se excluyen parámetros propios del método/background, selección total de muestras,
identidades de campaña/ejecución, seed, batch size, code, kind, schema, evaluación
relacionada y definición de métricas: no identifican el contenido de la célula ni
el modelo explicado. No se comparan ubicaciones físicas de modelo/dataset ni el
registro utilizado para seleccionar un checkpoint ya identificado por PK/hash.
Todos esos datos siguen presentes en los metadatos del intento.

Identidades incompletas permanecen aisladas y llevan una advertencia de no
comparabilidad; el artefacto con relación intento/TRAIN válida sigue inspeccionable
individualmente. No se deduce `sample_id` de SHAP background. Una repetición del
mismo método no sobrescribe otra evidencia: conserva otra fila. Referencias
idénticas de un mismo intento se deduplican.

La comparación abarca las páginas y los intentos seleccionados, no todo el catálogo.
«Sin evidencia» significa que no hay evidencia comparable en ese conjunto; no se
presenta como prueba de que el método nunca se ejecutó. Las páginas sin overlay
conservan un registro sin muestra inferida y el estado del intento. Un fallo al
listar referencias se muestra como error fuera de la fila, nunca como resultado vacío.

## Presentación, estados y sistema visual

Siempre cuatro cuadros: **Original → Grad-CAM → LIME → SHAP**. La cuadrícula usa
cuatro columnas iguales y espacios de imagen cuadrados, con `object-fit: contain`.
Los PNG científicos pueden incluir gráficos/títulos: no se recortan ni transforman.
En pantallas estrechas la región conserva las columnas y permite scroll horizontal,
con instrucciones visibles, nombre accesible, foco y navegación nativa con flechas.

Se usa `.ds-report[data-surface=workbench]`, tokens de `tokens.css`, controles,
estados, acordeones y metadatos de `ds-primitives.css`, y `report-section`,
`report-viewer`, `report-scientific-image` y `report-identifier`. Las nuevas clases
`xai-*` solo componen el visor y están delimitadas por `.ds-report`. No se añaden
colores, frameworks, fuentes, `!important` ni cambios al CSS de frotis.

Estados: disponible, sin evidencia, pendiente, ejecutándose, fallido, archivo no
disponible, acceso denegado, integridad fallida, no comparable y error de recuperación.
Ejecución y disponibilidad se presentan separadamente. Los errores conservan su
contexto; también se informa una imagen que el navegador no puede decodificar.
No se inventan porcentajes, correlaciones, consenso ni conclusiones clínicas.

Stitch aporta el encabezado contextual, la fila comparativa, ampliación y acceso a
trazabilidad. Se descartan su paleta oscura, controles simulados de transformación,
valores ilustrativos y acciones clínicas. La apariencia procede de Capstone.

## Modalidad integrada y ampliada

`XAIComparisonViewer` posee cuatro hooks de recurso. `XAIComparisonContent` recibe
los resultados y se utiliza tanto inline como en modal. Abrir la comparación
ampliada no crea otra solicitud de blobs. La selección identifica el método en el
título y conserva muestra, metadatos y descarga en la comparación completa.

El `dialog.showModal()` nativo proporciona modalidad y navegación de foco; botón
visible de cierre con `method=dialog`, Escape nativo y retorno explícito al
control disparador. No se utilizan modales de frotis ni portales fuera del scope.
UUID y hashes se muestran completos, seleccionables y con ajuste de línea.

## Artefactos, seguridad y rendimiento — SCC-ART.1

El único transporte es `api.getArtifactBlob` → `requestBlob`, con bearer vigente,
`artifact_id`, `source=assessment`, `attempt_id`, `training_run_id` y datasource.
El backend conserva autorización e integridad. No se crean URLs a rutas físicas,
no se confunde el UUID del filename con el PK y no se cambia el cliente HTTP.

`useAuthenticatedObjectUrl` conserva cancelación, invalidación por clave y revocación
al desmontar o resolver tarde. No se modifica ese hook ni la caché clínica. No se
introduce caché global de imágenes científicas entre sesiones; el recurso activo
se reutiliza para presentación, ampliación y descarga durante la vida de la fila.
Comparación e historial se montan alternativamente para no descargar simultáneamente
los mismos artefactos por dos presentaciones.

Se recuperan como máximo 100 referencias por método seleccionado. Cada método
conserva sus controles de página y errores independientes. Solo se montan cinco
filas por página visual, y un `IntersectionObserver` habilita sus bytes al entrar
en pantalla. Un navegador sin esa API carga únicamente esas cinco filas.
Los mapas y otros artefactos siguen disponibles en el historial paginado existente.
No se recorren miles de PNG ni se ejecuta EXPLAIN.

## Pruebas y evidencia operativa

Comando: `make test-exec1-frontend`, target existente que ejecuta tests y build
exclusivamente en el contenedor frontend.

- **316/316 pruebas aprobadas**, cero fallos/omitidas; 32 nuevas SCC-XAI y 284
  regresiones existentes, incluidas SCC-ART, linaje y frotis.
- Cubren cuatro posiciones, SHAP solo, vacío, los tres métodos, IDs completos,
  incompatibilidad por TRAIN/modelo/checkpoint/muestra/contexto, metadatos,
  duplicados, errores, generación autorizada, descarga, bearer/fuente, limpieza
  de URLs, observador, acciones de modal/retorno de foco y límite de cinco filas.
- TypeScript de `tsconfig.json` y `tsconfig.node.json`: aprobado, sin emisión.
- Vite build: aprobado, 140 módulos; advertencia preexistente de chunk >500 kB.
- `git diff --check`: aprobado.
- Node del contenedor: v20.20.2; `package.json` requiere >=22 <23. Se conserva el
  entorno existente; queda pendiente repetir en Node 22 para alinearlo.

Las primeras corridas nuevas detectaron mocks con rutas anteriores a la extracción,
el target ES5 predeterminado del transpiler de tests (spread de Map) y un tipo
inferido demasiado estrecho para contexto científico. Se corrigieron y la corrida
final completa pasó. No se ocultaron fallos ni se omitieron pruebas.

GET reales de solo lectura a metadatos, sin credenciales generadas:

- SHAP `93966b5d-5548-4b29-96f9-0b67e5c98f9f`: 200, verified, TRAIN
  `d3d42cf3-0800-468c-b3ed-995860967da1`, checkpoint
  `a08a743c-0297-58ac-84f2-da9445baa2e0`, muestra
  `000f6007-9330-5085-972a-247631c541c6`. Primera página: dos referencias,
  incluido PNG `2b4f68d6-2826-489c-980b-69f686223b11`, 19.413 bytes,
  SHA-256 `58833149477dc835aa074e89629acc3dfffbae6408e9fa2c44696e196cd84bb0`.
- Grad-CAM `4703ff9e-2d20-413f-9b9a-cd945c8dd632`: 200, verified, TRAIN
  `338136db-a207-47fc-bbf3-d17ce85c0dc2`; primera página paginada: 100 referencias.
  No se agrupa con el caso SHAP anterior, aunque comparta un sample_id.

Estas lecturas acreditan identidad y referencias, **no un GET autenticado del PNG**.
El usuario informó una comprobación visual previa de SHAP; no se presenta esa
comprobación anterior como validación de este visor nuevo.

## Validación visual pendiente y limitaciones

No hubo herramienta de navegador conectada ni Playwright/Puppeteer/Chromium en el
contenedor. No se capturó ni certificó una sesión legítima del nuevo visor.
Las pruebas SSR y los eventos simulados no certifican contraste, layout, Escape,
focus trap o comportamiento responsive real. El screenshot Stitch sí se inspeccionó,
pero es una referencia de diseño, no evidencia de implementación.

Recorrido de aceptación: abrir con sesión legítima
`/modelo-ia/ejecuciones/d3d42cf3-0800-468c-b3ed-995860967da1?datasource=malaria`,
expandir «Explicabilidad por caso» y comprobar, tras el FIX, original y SHAP junto
a los cuadros Grad-CAM/LIME sin evidencia comparable. Ampliar SHAP, cerrar con Escape, comprobar foco,
descargar y verificar el GET autenticado con `source=assessment`. Revisar trazabilidad
e historial. Revisar anchos 390/700/1000/1340/1440, zoom 200% y frotis sin cambios.
**El usuario debe confirmar la visualización antes del cierre de SCC-XAI.1.**

La API de referencias EXPLAIN no proporciona por sí sola el original, predicción ni
clase real. El FIX descrito abajo incorpora el original desde el dataset gobernado;
predicción y clase real continúan ausentes si el reporte no aporta una fuente explícita. No se navegan automáticamente todas las páginas para buscar
correspondencias: el selector muestra el primer intento disponible por método y
permite elegir otro; no lo declara ganador, óptimo ni equivalente a otro intento.

## Fases siguientes y estado Git

SCC-XAI.2 podrá conectar generación autorizada mediante el callback tipado;
SCC-XAI.3 podrá usar el mismo componente en EXPLAIN/EVALUATE/Comparación Científica.
No se adelantan esas integraciones, endpoints ni lógica de ejecución.

Cambios locales sin commit ni push. La implementación inicial no modificó backend. El FIX extiende la lectura de
originales y extrae SQL compartido sin cambiar PostgreSQL, esquema, checkpoints,
datasets, artefactos, algoritmos ni `smear-analysis-immersive.css`.
La ausencia de cambios en frotis y sus regresiones aprobadas es evidencia técnica;
no sustituye su revisión visual autenticada.


## SCC-XAI.1 FIX — SQL compartido, original gobernado y visor compacto

Fecha: 2026-10-15. **Implementación técnica disponible; aceptación del frontend
con sesión legítima pendiente de confirmación del usuario.** Esta sección sustituye
la limitación anterior sobre ausencia de mecanismo para recuperar el original.

### Defecto confirmado

El adaptador del visor solo construía referencias de artefactos `overlay` EXPLAIN;
`original` quedaba indefinido. No había solicitud del original ni resolución por
`source_record_id`. El archivo sí existe y la capacidad científica ya lo resuelve
mediante dataset gobernado. No era un PNG ausente ni un fallo de SHAP.
El endpoint histórico `/api/dataset/images/{image_id}/file` usa otra identidad y
no resuelve este caso: `dataset_split_images.image_id` no sustituye la muestra.

### Extracción y reutilización de SQL

Nuevo `malaria_dl_local_project/src/malaria_dl/data/sample_repository.py`:

- `select_dataset_sample_ids(connection, dataset_version_id, split, sample_id=None,
  limit=None)`: consulta parametrizada extraída literalmente de EXPLAIN; conserva
  filtro por versión/split/muestra, `ORDER BY source_record_id` y `LIMIT :limit`,
  incluido `LIMIT NULL`. Devuelve IDs, sin abrir o confirmar transacciones.
- `select_dataset_sample_records(connection, dataset_version_id)`: centraliza el
  join existente de assignments con source records. Lo reutilizan
  `assessment.lineage.dataset_samples`, `data.dataset_integrity.verify_integrity`
  y el nuevo repositorio HTTP. Se conserva el conjunto ordenado, nombres, clases,
  identidades y hashes utilizados para resolver colisiones.

`assessment.service.select_explanation_samples` mantiene validaciones, transacción
readonly, selección `all`, errores, orden y metadatos científicos; solo delega SQL.
No cambia la selección de background SHAP ni la selección científica de EXPLAIN.

### Recuperación HTTP del original

Se extiende el endpoint autenticado existente:

```text
GET /artifacts/file?source=dataset_sample
    &training_run_id=<TRAIN>&dataset_version_id=<dataset>
    &attempt_id=<EXPLAIN>&sample_id=<source_record_id>
    &datasource=malaria
```

No se envían `artifact_id`, `image_id`, filename ni rutas físicas para esta fuente.
Los cuatro UUID son obligatorios para esta modalidad y se validan antes de consultar.
La dependencia existente `ARTIFACTS_READ` exige sesión y permiso.

Nuevo `backend_api/app/repositories/dataset_samples.py`:

1. Comprueba la relación exacta intento EXPLAIN → identidad → TRAIN y que el intento
   registra evidencia para el sample_id solicitado. El split procede de esa identidad,
   no de un parámetro libre del navegador ni de SHAP background.
2. Reutiliza `resolve_training_run_dataset` para obtener la versión **real del TRAIN**
   y acreditar su snapshot contra PostgreSQL y la materialización gobernada.
3. Reutiliza las dos consultas compartidas en una transacción readonly para comprobar
   pertenencia al dataset/split y obtener registros necesarios para colisiones.

Nuevo `backend_api/app/services/dataset_samples.py`:

- Contrasta versión solicitada, versión del intento, versión del TRAIN y snapshot.
- Usa **la función existente `materialized_relative_path()`**, incluida la regla
  `<source_record_id>__filename` para colisiones. `relative_source_key` no interviene.
- Resuelve bajo la raíz gobernada con `LocalStorage.resolve`, que rechaza escapes,
  traversal y symlinks. No crea directorios ni copia imágenes.
- Verifica el SHA-256 registrado mediante `verify_regular_file` y valida firma/MIME
  con el mismo mecanismo utilizado para artefactos científicos.
- Devuelve `FileResponse` con nombre UUID, `nosniff`, `private, no-store`, CSP y
  cabeceras de trazabilidad: TRAIN, dataset, muestra, assessment identity, intento
  y SHA-256. No expone rutas físicas.

La inspección usa `required_splits=()` para verificar la metadata gobernada sin
recorrer ni hashear todos los archivos de TRAIN/VAL/TEST. Después verifica físicamente
**solo el original solicitado**. No se llama a `verify_dataset_for_execution` porque
esa función persiste auditoría de ejecución, incompatible con este GET readonly.
Las consultas reutilizan las verificaciones científicas ya existentes; no añaden
preflights de esquema, comprobaciones Alembic ni mecanismos de compatibilidad.

Errores explícitos: 400 UUID inválido; 404 relación/muestra/versiones incompatibles;
410 archivo faltante; 409 integridad, ubicación o evidencia de dataset inválida;
415 MIME inválido; 503 almacenamiento inaccesible. Los fallos nunca producen una
imagen de reemplazo ni publican mensajes del filesystem.

### Integración, trazabilidad y diseño

`XAIDatasetSample` es una referencia separada de `XAIArtifact`: conserva TRAIN,
dataset, sample_id e intento y **no fabrica un artifact_id para el original**.
El adaptador solo la crea a partir de evidencia con relaciones verificables.
`getDatasetSampleBlob` utiliza el mismo `requestBlob` autenticado. El hook compartido
`useScientificArtifact` reutiliza la cancelación y el ciclo de URLs temporales
existente, incluyendo clave por fuente/TRAIN/dataset/muestra/intento/datasource.
Modal y vista integrada comparten el recurso ya cargado.

El contenido único admite `density=compact|expanded`. Inline conserva cuatro
columnas y miniaturas de 112 px de alto, con columna mínima de 144 px; el modal
usa la composición ampliada. Dimensiones añadidas como tokens bajo `.ds-report`.
La acción «Ampliar comparación» está disponible además del clic en una imagen.
Se mantienen cierre por botón/Escape nativo, retorno de foco y scroll horizontal.

Grad-CAM/LIME/SHAP sin evidencia muestran **Generar** deshabilitado y una explicación
visible mientras no exista callback autorizado. El FIX no incorpora endpoints ni
simulación de generación. Los parámetros opcionales permiten la futura SCC-XAI.2.
No hay Tailwind instalado/configurado en este frontend; se conservan CSS y primitivas
Capstone, sin añadir dependencias. Frotis y su CSS protegido permanecen intactos.

### Evidencia operativa y visual obtenida

Lecturas reales en Docker con PostgreSQL actual, sin escrituras:

- `select_dataset_sample_ids(dataset, 'val', limit=1)` devolvió
  `000f6007-9330-5085-972a-247631c541c6`; selección explícita devolvió el mismo ID.
- El servicio real resolvió
  `C168P129ThinF_IMG_20151118_155802_cell_44.png`, MIME `image/png`, **127 × 133**.
- SHA-256 calculado y contrastado:
  `8ac64308af745675e3fe72dc1b7770af29c3ac9e60e065129773ebec264fbc23`.
- Se abrió e inspeccionó visualmente ese archivo original. Esto acredita el contenido
  del archivo; **no es una captura de la aplicación autenticada**.
- GET al endpoint real sin bearer: **401**, conservando la protección existente.
- Se solicitó al usuario comprobar original y SHAP tanto inline como en modal desde
  su sesión habitual. Posteriormente, las capturas 4/5/6 del usuario confirmaron ambas imágenes; ver el ajuste visual al final.

No hubo herramienta de navegador conectada. No se generaron tokens ni se extrajeron
sesiones. El GET autenticado 200 de producción y la aceptación visual del frontend
no se sustituyen por pruebas con principal de test.

### Pruebas del FIX y resultados

`make -k test-scc-xai-fix` ejecuta backend, selección/gobernanza y frontend aunque
un target de regresión falle. **La suite ampliada no está totalmente verde.**

- Backend original/SCC-ART/almacenamiento: **67 aprobadas**. Casos de PNG y cabeceras,
  identificación separada, SHA, muestra/dataset ajenos, archivo ausente/modificado,
  colisiones, traversal, symlinks, MIME, UUID inválido, autenticación y autorización.
- Selección, CLI, E6, aislamiento de splits y gobernanza: **277 aprobadas y 5 fallos
  preexistentes** en `test_dataset_resolution.py`.
- Frontend: **324 aprobadas**, incluidas original + SHAP en cuatro cuadros, fuente
  `dataset_sample`, bearer y UUID separados, errores, densidad compacta, modal,
  descarga, generación deshabilitada y regresiones de reportes/frotis.
- TypeScript (ambos tsconfig), Vite build y `git diff --check`: aprobados.
- Node Docker permanece en 20.20.2 frente a engines >=22 <23; persiste la advertencia
  de chunk JS >500 kB. No se modificó el entorno para este FIX.

Los cinco fallos antiguos se reprodujeron con `dataset_integrity`, `lineage` y
`assessment.service` originales de **HEAD**, cargados solo en memoria dentro de un
proceso Docker de pruebas: **los mismos 5 fallos, 33 aprobadas** en esa suite.
Corresponden a dos expectativas `TEST_FINAL_LOCK_REQUIRED` frente a
`SPLIT_PURPOSE_CONFLICT`, dos mocks de `cli.campaign_inventory` ya inexistente y un
mock `standalone` que no acepta `campaign_id`. No se modificaron contratos ni tests
ajenos para ocultarlos. Los fallos iniciales de extracción (adaptación del resultado
`.mappings().all()` y código del envelope) sí se corrigieron y verificaron.

### Archivos del FIX y pendientes

Nuevos: repositorio SQL compartido, repositorio/servicio HTTP de dataset samples,
`tests/test_sample_repository.py` y `backend_api/tests/test_scc_xai_original.py`.
Modificados: `assessment/service.py`, `assessment/lineage.py`,
`data/dataset_integrity.py`, ruta/DTO de artefactos, cliente HTTP frontend, contrato
XAI, hook compartido, presentación, tokens/CSS, pruebas frontend, Makefile y este
contrato/índice. Los archivos del visor de la entrega anterior siguen siendo cambios
locales del mismo workspace.

Pendientes reales: confirmación visual autenticada del usuario y los cinco tests
antiguos descritos. La resolución verifica metadata del dataset completo para sus
fingerprints y colisiones, pero solo lee el binario solicitado; no se añadió una
caché global de evidencia que pudiera ocultar cambios de integridad.

Sin migraciones, escrituras científicas, cambios de particiones, modelos/checkpoints,
ejecuciones reales EXPLAIN ni regeneración de artefactos. Las pruebas usan fixtures
sintéticos temporales. Sin commits, merges ni pushes.


### Ajuste visual posterior a capturas 4, 5 y 6

El usuario confirmó visualmente original y SHAP mediante capturas de la aplicación,
incluido el modal ampliado (imagen 6). Detectó desbordamiento en inline ancho (imagen
5): el frame era de 112 px, pero el tamaño intrínseco del botón/imagen podía superar
esa fila y aparecer detrás de estados y descargas. Se fija explícitamente la altura
de la fila, botón e imagen compactos; los controles permanecen en la fila inferior.
Las dimensiones del modal se conservan. Muestra, modelo/TRAIN/predicción y ayuda de
scroll se trasladan al contenido del acordeón de trazabilidad, conservando HTML
semántico y la referencia accesible `aria-describedby`.
La confirmación del usuario acredita las imágenes del FIX anterior; el ajuste de
layout posterior aún requiere comprobación visual en navegador.

Validación del ajuste visual: `make test-exec1-frontend`, 324 pruebas aprobadas,
TypeScript y Vite build correctos; `git diff --check` sin errores.
