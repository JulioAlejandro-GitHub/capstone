# SCC-XAI.2 — Catálogo y generación compartida

Estado documental: `CURRENT_DOC`. Estado técnico: **generación científica implementada y comprobada en navegador; límites operativos al final**.
Fecha: 2026-10-16. Sin tablas ni migraciones. Sustituye la propuesta de cola anterior.

## Auditoría previa a cambios funcionales

| Consumidor / operación | HTTP → endpoint | Aplicación → SQL / motor → persistencia | Acción realizada |
|---|---|---|---|
| TRAIN / visor | `api.getTrainingLineageChildren` → linaje TRAIN | `lineage_children` → assessments existentes | Reutilizada sin cambios |
| Detalle EXPLAIN | `api.getAssessment`, `getAssessmentArtifacts` → `/assessments/{id}` y `/artifacts` | `AssessmentReadService` → `AssessmentReadRepository` | Reutilizada sin cambios |
| Original gobernado | `api.getArtifactBlob` → `/artifacts/file?source=dataset_sample` | `original_sample_image` → `DatasetSampleReadRepository` → catálogo gobernado + binario verificado | Adaptada: muestra acreditada en identidad EVALUATE/EXPLAIN |
| Artefacto científico | `api.getArtifactBlob` → `/artifacts/file?source=assessment` | `scientific_artifact` → `ArtifactReadRepository` → assessment_artifacts + storage | Reutilizada sin cambios |
| Selección EXPLAIN | CLI `src.explain` | `prepare` → `select_explanation_samples` → `select_dataset_sample_ids` | Reutilizada sin cambios |
| Background SHAP | Nueva aplicación HTTP | `select_dataset_sample_ids(dataset, 'val', limit=1)`; equivalente al ORDER BY r.id autorizado, con FK a registros fuente | Reutilizada; equivalencia SQL probada |
| Ejecución | CLI → `assessment.cli` | `prepare`, `run`, `KerasRuntime` → AssessmentRepository → PostgreSQL + artifacts/assessments | Adaptada: reserva separada de ejecución, sin algoritmos nuevos |
| Auditoría celular | `CellReviewWorkspace` → `CellClassificationAuditModal` → `CaseExplainabilityView` | `toSmearCellExplainabilityCase`, prediction seleccionada, crop y modelo históricos | Preservada sin cambios de presentación |

El cliente autenticado está en `frontend/src/services/api.ts` (`request`,
`requestBlob`, bearer, deduplicación GET). No se necesita otro cliente global.
El backend usa `current_principal` y `require_permission`, rutas con Depends,
servicios de aplicación y repositorios con las transacciones existentes.
La política científica de lectura es por rol; no se inventará propiedad por usuario.

Solo TRAIN consume actualmente `XAIComparisonViewer` mediante
`TrainingXAIComparison`. `AssessmentDetail` muestra EXPLAIN con
`AssessmentExplanationDetail`; Comparación Científica muestra `ComparisonRunCard`.
Estos dos contextos necesitan adoptar el mismo contenedor, no tres visores nuevos.

## Auditoría clínica

En este checkout, el botón «Auditar clasificación» ejecuta `setAuditOpen(true)`.
No abre un documento blob ni llama a window.open. Renderiza el modal React
`CellClassificationAuditModal`; su adaptador recibe `predictionDetail` o la
predicción seleccionada y el run de clasificación. Las URLs blob corresponden
al contenido de imágenes autenticadas. No se encontró un generador independiente
HTML/PDF de «Tríada XAI» en este recorrido.

Las identidades clínicas detection/prediction/crop no son source_record_id de
un split. El motor assessment requiere un TRAIN verificable y una muestra del
dataset gobernado. Falta un adaptador científico para ejecutar LIME/SHAP sobre
el crop clínico con su modelo histórico, preprocesamiento, clase, referencia
SHAP acreditada y persistencia clínica. No se fabricará un dataset o assessment
para ese crop. Se conserva Grad-CAM clínico y su presentación especializada.
Ambos contextos comparten cliente HTTP/autenticación y los algoritmos existentes;
los resolutores de dominio permanecen distintos.

## Ejecución implementada

`ExplainService` y `ExplainRepository` reutilizan `prepare`, `explanation_spec`,
`verify`, `AssessmentRepository` y la conexión PostgreSQL del backend. Se extrajeron
`reserve_execution` y `execute_reserved` del `run` existente: la CLI sigue usando
`run`, y ambos caminos ejecutan exactamente el mismo bucle científico y KerasRuntime.
No cambiaron Grad-CAM, LIME ni SHAP.

`ExplainLauncher` inicia únicamente `python -m app.services.explain_worker`, con
JSON validado, sin shell. Un pipe privado confirma la reserva antes de autorizar
el cálculo. El handshake tiene un límite de 60 segundos; no mantiene HTTP abierto
hasta terminar las atribuciones. El worker adquiere `GlobalGate` y usa el mismo
runtime y las mismas tablas que la CLI.

La prueba real reveló `uq_global_assessment_active`: solo puede existir **un**
assessment activo. Se preserva ese índice. La acción completa prepara los métodos,
reserva el primero y persiste en su identidad `http_request` con la solicitud
completa, actor y errores de preparación. Devuelve ese `operation_id` y el primer
`attempt_id`; después ejecuta/reserva los siguientes métodos secuencialmente bajo
el mismo gate. Cada método conserva su identidad, resultado y artefactos originales.
Los fallos parciales no borran resultados. Si todos fallan antes de reservar, se
rechaza la solicitud y no se inventa una identidad de seguimiento.

Los estados derivan de assessments y de la solicitud persistida. `pending` es una
proyección de un método solicitado en un lote con otro intento activo, no un nuevo
estado SQL. Los métodos completos requieren `verify` y readback de los artefactos.
Un método incompleto de un lote terminado queda reintentable. La consulta identifica
TRAIN/dataset/muestra y clase; no mezcla decisiones, protocolos, checkpoints,
clases objetivo, perturbaciones ni referencias SHAP incompatibles.

El gate ocupado responde 409. Dos solicitudes concurrentes no reservan dos intentos.
Si ya existe evidencia íntegra compatible se devuelve el intento existente. La
recuperación de un intento interrumpido requiere demostrar ausencia del propietario.
Se corrigió la detección canónica de procesos zombie: ya han terminado, pero sus
hijos vivos siguen bloqueando el gate. No se usa un timeout como prueba de muerte.
La recarga del proceso web no es la fuente de verdad de las operaciones.

Los checkpoints registrados en Mac existen en el montaje Docker con otro prefijo.
`execution/storage_paths.py` resuelve exclusivamente los subárboles gobernados
`outputs/train_runs/<UUID>` y `artifacts/assessments/<UUID>`; conserva los registros,
bytes y hashes, y rechaza traversal y escapes mediante symlinks. KerasRuntime usa
ese resolutor al cargar el mismo checkpoint. Compose añade escritura únicamente
al directorio existente `artifacts/assessments`; el código ML sigue en solo lectura.

## Catálogo HTTP implementado

Cliente único: `frontend/src/services/api.ts`, usando `request`/`requestBlob`,
bearer y cabecera JSON existentes. Contratos: `types/explainGeneration.ts` y
`app/schemas/explain_generation.py`. Aplicación: `app/services/explain_generation.py`.
Rutas: `app/routes/explain_generation.py`, con `response_model` Pydantic explícito.

| Operación del cliente | Endpoint | Contrato |
|---|---|---|
| `getTrainingAssessments` | GET `/assessments?training_run_id=…&view=traceability` | Contextos del TRAIN, paginados |
| `getExplainContext` | GET `/assessments/{id}?view=traceability` | Identidad sin rutas físicas |
| `getDatasetSampleBlob` | GET `/artifacts/file?source=dataset_sample` | TRAIN + dataset + sample + intento que acredita la muestra |
| `prepareExplanation` | POST `/explain-generations/prepare` | Preparación científica en modo inspección, sin ejecutar algoritmos |
| `generateExplanation` | POST `/explain-generations` | Una célula, lista cerrada de métodos; 202 tras reserva persistente |
| `getExplainState` | GET `/explain-generations` | Contexto, muestra, clase y estados/evidencia recuperables |
| `getArtifactBlob` | GET `/artifacts/file?source=assessment` | UUID real, intento, TRAIN e integridad verificada |

Los GET de generación requieren RUNS_READ, DATASETS_READ y ARTIFACTS_READ.
Los POST exigen además SCIENTIFIC_CELL_CLASSIFICATION_EXPLAIN y la dependencia
central `audited_permission`. El worker registra su ciclo en los eventos del gate.
El API admite `class_id` 0/1, `num_samples` 1000–5000 y referencia SHAP explícita.
El visor preserva la clase del contexto (1 para EVALUATE) y usa 1000 perturbaciones.
No recibe comandos, rutas, max_images ni textos de shell.

SHAP usa la política autorizada por el usuario: primera muestra VAL del dataset
del TRAIN, ordenada por source_record_id, mediante el selector SQL canónico. La
referencia se entrega explícitamente a `explanation_spec` y se valida en `prepare`.
No se sustituye una referencia explícita inválida por el default. Objetivo y
background pueden coincidir si así resulta de esa política, pero nunca se confunden.

## Catálogo SQL y persistencia

- `data/sample_repository.py::select_dataset_sample_ids`: selección exacta por
  dataset/split/sample/limit, orden estable, sin abrir una conexión propia.
- `select_dataset_sample_records`: materialización gobernada y colisiones.
- `DatasetSampleReadRepository`: acredita la muestra en la identidad del intento;
  `original_sample_image` verifica pertenencia, confinamiento y hash del original.
- `ExplainRepository.source/samples/candidates`: contexto autorizado, delegación al
  selector canónico y búsqueda explícita de assessments por TRAIN/muestra.
- `AssessmentRepository`: única implementación de reserva, resultados, artefactos,
  finalización y recuperación de assessments. Ninguna tabla nueva.
- `ArtifactReadRepository` / `scientific_artifact`: recuperación autenticada de
  binarios, sin duplicar consultas ni fabricar artifact_id.

## Consumidores frontend

`useExplainGeneration` consulta y refresca estados reales, descarta respuestas de
otra selección y actualiza solo los métodos correspondientes. `GeneratedXAIComparison`
conecta el hook con el visor existente y la acción completa. Se mantienen compacta,
modal, descarga y cuatro cuadros. La generación también se conserva en el modal.

`AssessmentSampleXAI` permite elegir la célula de un contexto existente;
`TrainingAssessmentXAI` recupera los contextos del TRAIN. Se integran en RunDetail,
AssessmentDetail (EVALUATE/EXPLAIN) y ComparisonRunCard. TrainingXAIComparison también
usa la misma conexión para sus filas históricas. La carga de imágenes sigue siendo
bajo demanda; los paneles fuera del viewport no descargan imágenes automáticamente.
El selector permite generar el primer EXPLAIN a partir de un EVALUATE existente.

La ruta E6 se asocia a la sección Ejecuciones para evitar el rótulo incorrecto
«Página no encontrada» que apareció durante la inspección en navegador.

## Evidencia científica real (2026-10-16)

TRAIN: `d3d42cf3-0800-468c-b3ed-995860967da1`.
Contexto EVALUATE: `f88ef341-d5fa-403c-8caa-9174efef2280`.
Dataset: `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`. Split VAL, clase objetivo 1.
Referencia SHAP: `000f6007-9330-5085-972a-247631c541c6`; objetivo diferente.

| Recorrido real | Muestra | Grad-CAM / LIME / SHAP: attempt_id |
|---|---|---|
| HTTP autenticado; segunda solicitud reutilizó Grad-CAM | `00124cf9-7657-5f92-aba0-3be871ce33fb` | `2114aeed-a482-48d6-b75f-377bfb627ca2` / `d853bd2c-4694-47be-be16-d618e6d2d3f5` / `bbec1149-7766-4f78-938b-7b734293e496` |
| Botón completo en Chrome, actualización sin recarga | `002f616e-2ca2-559f-9af0-95b981240ded` | `0de35d75-fc99-4bf2-a1d9-3e8a36437e51` / `0e511214-d0ed-4cb0-9563-1513447185e0` / `e10aabaa-aed4-4a9f-8c02-8f098fa4ddb2` |
| Tres botones individuales en Chrome | `00407b51-0603-5260-a0db-1ab700451f9f` | `6ab266f8-de59-4b52-a0b3-cea0a0fdec94` / `ebf5f873-2ea5-4041-a92f-eeba156f6a6a` / `0e7d6652-f952-4df4-a39a-744350ef5b68` |

Los nueve overlays respondieron HTTP 200 autenticado; sus bytes y SHA-256
coincidieron con PostgreSQL. Por ejemplo, el Grad-CAM del botón completo usa
artifact `3b6d2660-9155-4dc9-a2cb-7ade36a88cfd`, 36398 bytes,
SHA-256 `0258ec12cacbddbdb546a823bdb7a10ba9bac7631a4cf01d8464b52b4e822284`.

Concurrencia real sobre `0045ba38-42c5-5408-a54a-a4b124325573`: dos POST simultáneos,
202 y 409 GLOBAL_EXPERIMENT_BUSY; **un solo intento**, `8119575b-7fd1-455b-8603-3c928caa19ea`.

Chrome verificó cuatro imágenes cargadas, sin alertas, en EVALUATE, TRAIN y
Comparación Científica para la misma selección compatible; modal con cuatro
paneles y recuperación tras recarga. Capturas locales:
`/private/tmp/scc-xai2-generated-browser.png` y
`/private/tmp/scc-xai2-comparison-modal.png`.

## Pruebas automatizadas y límites

`make test-xai-shared`: **64 backend + 60 motor + 335 frontend aprobadas**;
TypeScript y build aprobados. Incluye contratos de HTTP/autenticación/auditoría,
selección SQL real de solo lectura, integridad, reserva/ejecución, fallos parciales,
recuperación, clasificación de procesos muertos, hooks y consumidores existentes.

`make test-backend`: **761 aprobadas, 20 fallidas, 13 omitidas y 96 deseleccionadas**.
Las 20 pruebas fallidas coinciden exactamente con las de la línea base previa
(738 aprobadas/20 fallidas); no se declara la suite global aprobada. Son contratos
de runtime/Compose/storage, observabilidad DB02A, Grad-CAM anidado, equivalencia
de crops, tooling PostgreSQL y cola de calidad, fuera de la implementación nueva.
La regresión de auditoría detectada durante el desarrollo fue corregida y pasa.

Registros locales: `/private/tmp/scc-xai2-shared-final.log` y
`/private/tmp/scc-xai2-backend-final.log`. `git diff --check` aprobado.
Vite conserva la advertencia de chunk superior a 500 kB.
La reutilización final auditada de la muestra del botón completo devolvió los
mismos tres attempt_id y mantuvo el conteo de intentos **3 → 3**. Se confirmó
el evento `scientific.explain.request` en la auditoría central.
Las pruebas unitarias de fallos parciales y recuperación usan dobles: no se
presentan como ejecuciones científicas reales. La evidencia real es la tabla anterior.

- No hay cola durable independiente ni autoarranque tras reiniciar el ejecutor:
  las solicitudes ocupadas se rechazan y un lote interrumpido se reintenta por
  método o con la acción completa, reutilizando lo ya verificado.
- La generación HTTP se ejecuta en Docker. La CLI Mac continúa siendo válida con
  el mismo motor/BD; no se agregó un despachador HTTP hacia el Mac.
- El visor requiere un contexto EVALUATE/EXPLAIN VAL/development existente. Un
  TRAIN sin ese contexto todavía no dispone de selector de muestras aquí. TEST
  no se habilita eludiendo sus locks/protocolo científico.
- Una muerte de proceso en otro host o un PID reutilizado sin prueba suficiente
  exige recuperación explícita; no se declara muerto por antigüedad.
- Preparación limitada a 60 segundos. Un fallo antes de reservar rechaza la
  solicitud; solo intentos realmente registrados reciben seguimiento persistente.
- La auditoría clínica conserva su flujo y pruebas existentes. No se certifica
  LIME/SHAP para crops clínicos: falta el adaptador descrito arriba. No se alteraron
  su diseño, semántica clínica ni estilos inmersivos.
- Sin tablas, migraciones, cambios de dataset/splits/checkpoints o commits/pushes.

## Archivos de implementación y pruebas

- Backend: `app/main.py`, `app/routes/explain_generation.py`,
  `app/schemas/explain_generation.py`, `app/repositories/explain_generation.py`,
  `app/repositories/dataset_samples.py`, `app/services/explain_generation.py`,
  `app/services/explain_launcher.py`, `app/services/explain_worker.py`.
- Motor ML: `assessment/service.py`, `assessment/repository.py`,
  `assessment/runtime.py`, `execution/artifacts.py`, `execution/storage_paths.py`,
  `execution/global_gate.py` (todos bajo `src/malaria_dl/`).
- Frontend: `services/api.ts`, `types/api.ts`, `types/explainGeneration.ts`,
  `hooks/useExplainGeneration.ts`, `components/reports/AssessmentXAI.tsx`,
  `GeneratedXAIComparison.tsx`, `TrainingXAIComparison.tsx`,
  `XAIComparisonViewer.tsx`, `ComparisonRunCard.tsx`, `reports/xai/comparison.ts`,
  `pages/AssessmentDetail.tsx`, `pages/RunDetail.tsx`,
  `components/navigation/navigationConfig.ts`.
- Pruebas: `backend_api/tests/test_explain_generation.py`,
  `malaria_dl_local_project/tests/test_scientific_storage_paths.py`,
  `frontend/tests/scc-xai.test.mjs`, `scc-art.test.mjs`,
  `scc-selection.test.mjs`, `e6-lineage.test.mjs`.
- Orquestación/documentación: `Makefile`, `docker-compose.override.yml`,
  este documento, `docs/README.md` y banner de la propuesta descartada.
