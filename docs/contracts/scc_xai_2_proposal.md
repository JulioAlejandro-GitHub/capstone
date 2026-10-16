# SCC-XAI.2 — Auditoría y propuesta de ejecución persistente

Estado documental: `SUPERSEDED`. Fecha: 2026-10-16.
Estado técnico: **propuesta descartada por instrucción del usuario: sin tablas nuevas**.
Véase `scc_xai_2.md` para la implementación con assessments existentes.
Este documento no acredita generación real ni cierre de SCC-XAI.2.

## Consumidores comprobados

| Contexto | Implementación actual | Trabajo necesario |
|---|---|---|
| TRAIN | `RunDetail` → `TrainingXAIComparison` → `XAIComparisonViewer` | Conectar generación y consulta de evidencia por muestra; permitir seleccionar muestras aunque no haya EXPLAIN previo. |
| EVALUATE/EXPLAIN | `AssessmentDetail`; EXPLAIN usa `AssessmentExplanationDetail` y `ScientificArtifact` | Integrar el mismo visor, conservando el intento explícito y su contexto. EVALUATE no consume actualmente el visor. |
| Comparación Científica | `ModelComparison` → `ComparisonRunCard` | Integrar el mismo contenedor para cada TRAIN; actualmente solo muestra fichas de ejecuciones. |

No existen tres consumidores actuales de `XAIComparisonViewer`. Solo TRAIN lo
consume. `CaseExplainabilityView`, usado en Explainability y revisión celular,
es otro contrato de dominio y no demuestra pertenencia a un assessment E6.
Su endpoint síncrono de Grad-CAM no satisface este requerimiento.

`useTrainingExplanations` recupera hijos de linaje paginados. `useAssessment` y
`useAssessmentArtifacts` recuperan detalle y artefactos con `view=traceability`.
`groupXAIComparisons` agrupa páginas seleccionadas; ausencia en una página no
demuestra ausencia global. Su clave conserva TRAIN, modelo, checkpoint, dataset,
muestra, split, propósito y contexto científico. El intento, la identidad y el
artefacto conservan sus UUID independientes. La muestra procede del artefacto,
nunca del background SHAP. `useScientificArtifact` recupera blobs autenticados.
El original exige TRAIN, dataset, muestra e intento EXPLAIN acreditado; habrá que
extender esa acreditación a la selección gobernada previa al primer EXPLAIN.

## Flujo científico existente

`python -m src.explain` delega en `assessment.cli.main("explain")`.
Acepta un método por operación y `--sample-id` exclusivo con `--max-images`.
La CLI fija `val/development`. `assessment.service.prepare` resuelve TRAIN,
checkpoint, integridad, dataset, umbral y selección autorizada.
`explanation_spec` exige referencias explícitas para SHAP; `prepare` comprueba
que pertenezcan al split autorizado **antes** de reducir las muestras objetivo.
El código auditado no selecciona automáticamente referencias. La aclaración del
usuario establece la siguiente política por defecto para la nueva orquestación.

### Parámetros y selección acordados

| Parámetro | Regla |
|---|---|
| `method` | `gradcam` (default), `lime` o `shap` |
| `layer` | Solo Grad-CAM; omitir para usar la última capa convolucional compatible |
| `class_id` | `0` o `1`; default `1` |
| `num_samples` | Solo LIME/SHAP, entero 1000–5000, default 1000; no limita células |
| `sample_id` | Célula objetivo perteneciente al split autorizado |
| `max_images` | Entero positivo o `all` (default); incompatible con `sample_id` cuando ambos se proporcionan explícitamente |
| `background_sample_id` | Referencia SHAP explícita; si falta en la solicitud del visor, resolverla por la política SQL siguiente |

```sql
SELECT r.id AS background_sample_id, r.source_filename, r.class_name, a.split_name
FROM runs t
JOIN dataset_split_assignments a ON a.dataset_version_id = t.dataset_version_id
JOIN dataset_source_records r ON r.id = a.source_record_id
WHERE t.id = CAST(:training_run_id AS uuid)
  AND t.run_type = 'training'
  AND a.split_name = 'val'
ORDER BY r.id
LIMIT 1;
```

Resolver en el repositorio con parámetros ligados; pasar el UUID resultante
explícitamente a `explanation_spec` y conservar la validación de `prepare`.
No sustituir una referencia explícita inválida por el default. Si no hay
referencia acreditable, devolver un error para SHAP y conservar los otros métodos.
El background puede coincidir con la célula objetivo si así resulta del orden
SQL: el contrato no exige UUID diferentes. Sus funciones y metadatos permanecen
independientes; no se añade un filtro de exclusión o de clase no autorizado.

Sin selector, la CLI explica todas las elegibles; un límite numérico selecciona
las primeras N por orden SQL estable de los identificadores reales. Una muestra
inexistente o fuera del split falla antes de ejecutar EXPLAIN. Persistir las
identidades efectivamente seleccionadas y el alcance completo o parcial.
El visor por caso siempre utiliza `sample_id`, también en la acción completa;
no envía `max_images` ni activa implícitamente el procesamiento de otras células.
Persistir también la referencia SHAP resuelta e incluirla en la clave de
reutilización y deduplicación antes de reservar el trabajo.

`run` añade un `execution_id` nuevo en cada invocación, reserva un intento,
ejecuta `KerasRuntime`, registra mapas y overlays, verifica integridad y termina
en `verified` o `failed`. Por ello llamar repetidamente a `run` no constituye
deduplicación de solicitudes de usuario. Se reutilizarán estos servicios y
repositorios; los algoritmos científicos no requieren cambios.

## Necesidad concreta de persistencia adicional

El contrato SQL revisado está en `alembic_v2/baseline/04_functions.sql`:

- `assessment_attempt_guard`: el INSERT debe comenzar en `active`; solo permite
  pasar a `verified`, `failed` o `interrupted`. Propietario, host y PID son
  inmutables. No es una cola pendiente transferible a otro proceso.
- `experiment_reservation_guard`: exige el propietario del bloqueo global e
  impide reservar assessments cuando existe TRAIN activo/completed.
- `assessment_attempts_state_check` no incluye `pending`.
- `local_execution_jobs` exige campaña/agente y está vinculado al contrato
  controlado de TRAIN. `quality_assessment_queue_items` exige un análisis de
  microscopía. Ninguna es una cola genérica de explicabilidad por muestra.

Es posible rechazar una solicitud hasta que el ejecutor esté libre y arrancar
directamente un assessment; esa alternativa no ofrece la solicitud pendiente
durable, con recuperación y seguimiento durante preparación, que aquí se propone.
Una tarea FastAPI en memoria tampoco conserva solicitudes tras reiniciar.
No se harán reservas ficticias ni se reutilizarán tablas de otros dominios.
Esta conclusión procede de revisión de código; no se añadieron chequeos de
versiones/esquemas en tiempo de ejecución.

## Cambio solicitado para aprobación

**Una tabla nueva `xai_generation_requests` y su migración en `alembic_v2/`.**
Una fila por método solicitado; la acción completa crea únicamente solicitudes
de métodos sin evidencia compatible verificada. Las filas anteriores se conservan.

| Campo propuesto | Contrato |
|---|---|
| `id` | UUID, PK, identificador público de seguimiento |
| `training_run_id` | UUID, FK a `runs`, ON DELETE RESTRICT |
| `source_attempt_id` | UUID nullable, FK a `assessment_attempts`, contexto seleccionado |
| `dataset_version_id` | UUID, FK al catálogo gobernado, ON DELETE RESTRICT |
| `sample_id` | UUID, FK al registro fuente gobernado; acreditar además pertenencia al split |
| `checkpoint_artifact_id` | UUID del checkpoint seleccionado; FK al catálogo correspondiente |
| `method` | CHECK `gradcam`, `lime`, `shap` |
| `specification` | JSONB inmutable: split, propósito, clase, configuración científica y referencias SHAP explícitas |
| `request_key` | SHA-256 calculado por servidor sobre el contexto científico canónico y la especificación |
| `status` | CHECK `pending`, `running`, `completed`, `failed` |
| `requested_by` | UUID, FK a `users`, ON DELETE RESTRICT |
| `attempt_id` | UUID nullable, FK a `assessment_attempts`; identifica el intento real o reutilizado |
| `worker_identity` | JSONB privado, proceso/host/arranque para recuperación segura |
| `error_code` | Código sanitizado, sin rutas ni SQL |
| Fechas | TIMESTAMPTZ de solicitud, comienzo y finalización |

Índice único parcial sobre `request_key` para `pending/running`; índice para
consulta por TRAIN/dataset/muestra y fecha. Restricciones de estado y coherencia
temporal; una finalización exige intento verificado y artefactos acreditados.
Los nombres exactos de FK se resolverán contra los repositorios científicos
vigentes al implementar la migración. No se crean tablas de píxeles ni se alteran
las tablas científicas existentes. La aprobación debe cubrir crear y aplicar
esta migración al entorno de desarrollo para poder validar el recorrido real.

## Arquitectura propuesta

1. Ruta autenticada → esquema estricto → servicio → repositorio. Autorizar lectura
   de TRAIN/dataset/artefactos y operación científica por los permisos vigentes;
   rechazar parámetros libres y contextos incompatibles.
2. Resolver selección por identificadores, no nombres ni rutas. La primera
   versión respetará `val/development` de la CLI; otros splits mostrarán operación
   no disponible hasta contar con un protocolo científico autorizado.
3. Buscar evidencia por contexto científico completo y especificación del método,
   incluyendo clase y referencias SHAP; verificar resultados y archivos antes de
   reutilizar. No elegir un checkpoint distinto del seleccionado por el contexto.
4. Insertar solicitudes faltantes de forma transaccional. Resolver conflictos de
   concurrencia devolviendo el mismo trabajo activo. Reintentos crean otra fila
   y otro intento; conservan resultados anteriores.
5. Un worker separado de FastAPI reclama solicitudes con bloqueo PostgreSQL y
   adquiere `GlobalGate` antes de la reserva científica. Ejecuta `prepare` y `run`
   existentes en el execution plane, sin shell ni argumentos arbitrarios. La
   preparación pesada ocurre fuera de la petición HTTP.
6. Enlazar el intento al trabajo en el punto de reserva, antes del cálculo, para
   resolver caídas entre reserva y finalización. Extraer este punto de extensión
   de orquestación si es necesario; no modificar algoritmos ni duplicar SQL de
   assessment. El worker reporta estados al backend, que persiste la orquestación.
   El flujo científico mantiene sus escrituras existentes en PostgreSQL.
7. Recuperación: nunca deducir muerte del worker solo por timeout. Comprobar su
   identidad y ausencia; reconciliar intentos verificados o fallidos. Un propietario
   cuya muerte no pueda probarse bloquea reintentos y exige recuperación explícita.
8. `completed` requiere readback científico y archivos verificados; cada método
   falla independientemente. Un fallo de SHAP conserva Grad-CAM y LIME.

El ejecutor Docker será un proceso separado del servidor HTTP; la interfaz de
worker debe permitir el agente Mac mediante el transporte autenticado existente,
sin convertir el API TRAIN actual en una API de comandos libres.

## Endpoints propuestos, todavía inexistentes

- `POST /xai/generations`: TRAIN, dataset, checkpoint, muestra, contexto de origen
  y lista cerrada de métodos. Referencias SHAP explícitas o default SQL acordado,
  validado contra el contexto. Respuesta 202 con trabajos por método.
- `GET /xai/generations`: filtro estricto de contexto/muestra para recuperar
  estados y evidencia después de navegar o recargar.
- `GET /xai/generations/{id}`: estado real, causa sanitizada e identidad del
  intento/artefactos cuando estén acreditados.
- Recuperación de imágenes mediante `/artifacts/file` existente, con
  `source=assessment`, `artifact_id`, `attempt_id` y `training_run_id`.

Un único servicio y hook frontend administrarán consulta, cancelación y refresco
por contexto. Los tres consumidores usarán `XAIComparisonViewer`; conservarán
modal, disposición y recursos autenticados. El polling consulta estados del
backend; no inventa progreso. Los paneles se actualizan individualmente. Una
respuesta de un contexto anterior no puede sobrescribir la selección actual.
La operación SHAP permanecerá deshabilitada con motivo explícito si no puede
resolverse una referencia científica acreditada mediante la política acordada.

## Validación pendiente tras aprobación

### Línea base ejecutada el 2026-10-16

- `make test-backend` (Docker): **738 passed, 20 failed, 13 skipped,
  95 deselected**, 17,10 s. Fallos existentes antes de cambios funcionales en
  contratos de runtime/Compose/storage, observabilidad DB02A, Grad-CAM anidado,
  equivalencia de crops, tooling PostgreSQL y cola de calidad. No se investigaron
  ni corrigieron dentro de esta auditoría; no se declara backend aprobado.
- Frontend mediante Make temporal con recetas `docker compose exec -T frontend
  npm test` y `docker compose exec -T frontend npm run build`: **331/331 pruebas**,
  ambos proyectos TypeScript y build aprobados. Vite informa un chunk mayor de
  500 kB. El Makefile del repositorio no se modificó.
- Registros locales: `/private/tmp/scc-xai2-backend.log`,
  `/private/tmp/scc-xai2-frontend.log`, `/private/tmp/scc-xai2-build.log`.
- No se hicieron pruebas de generación real ni inspección visual autenticada.
  Estos resultados son línea base, no evidencia de aceptación de SCC-XAI.2.

### Pruebas de la implementación futura

Casos obligatorios: tres métodos individuales, acción completa, reutilización
verificada, fallo parcial, reintento por método, dos solicitudes concurrentes,
aislamiento TRAIN/dataset/checkpoint/muestra, 401/403/422, reinicio del worker,
readback de intento/artefacto, refresh sin recarga y navegación entre los tres
contextos. Usar PostgreSQL transaccional aislado para pruebas; ejecución real
identificada con TRAIN, muestra, referencias SHAP, intento, artefacto y hash.
La aceptación visual requiere navegador autenticado.
Añadir pruebas de referencia SHAP determinista dentro del dataset del TRAIN,
referencia explícita inválida sin fallback, ausencia de VAL, coincidencia válida
entre objetivo y background, exclusión mutua de selectores y persistencia del
alcance seleccionado. Comprobar que `num_samples` no amplía las células objetivo.

No hay endpoints nuevos ni resultados reales generados en esta auditoría.
No se modificaron algoritmos, datasets, splits, checkpoints o configuraciones,
ni se crearon/aplicaron migraciones. No hubo commit, merge o push.
