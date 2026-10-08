# Elegibilidad técnica de Etapa 2 con E6

Estado documental: `HISTORICAL_AUDIT`. Fecha: 2026-10-08.

Este diagnóstico de lectura precede a la [implementación de activación para Clasificación celular](cell_model_activation.md), que resuelve las limitaciones de publicación aquí documentadas.

## Diagnóstico

El panel de Ejecuciones consultaba dos servicios mediante `Promise.all`:

- `GET /api/training-runs/{id}/stage2-release-status` llamaba a
  `Stage2PublicationService.status_for_training()`. Este exigía primero una fila
  de `model_versions`; para el caso real no existe. El resultado era
  `GovernanceNotFoundError: model version inexistente`, convertido por `safe()`
  en HTTP 409. No significaba que el TRAIN estuviera incompleto.
- `GET /api/training-runs/{id}/stage2-availability` llamaba a
  `Stage2ModelAvailabilityService.preview()`. Su evaluación provenía únicamente
  de `run_lineage JOIN runs`: ignoraba E6 y devolvía inelegibilidad incorrecta.
- Al fallar la primera consulta, `Runs.loadStage2()` descartaba el resultado
  combinado. `Stage2PublicationPanel` trataba `status=undefined` como no elegible
  y llenaba todos los campos con «No registrado».

Los campos ausentes tenían causas distintas: estado y fechas ya existían en
`runs` y `assessment_attempts`; el modelo y arquitectura estaban en `models`;
la identidad de versión y checkpoint estaba en E5/E6; el número de versión
operativa no existe porque no hay fila de `model_versions`. EXPLAIN no se ejecutó
y es opcional. No existe publicación ni deployment para este TRAIN.

## Regla y contrato

`src/malaria_dl/governance/eligibility.py:stage2_eligibility()` contiene la regla
compartida por el nuevo lector y por los servicios históricos de publicación y
disponibilidad: TRAIN de tipo training y estado completed, más una evaluación
completada inequívocamente asociada. No consulta recall, F2, épocas, arquitectura,
EXPLAIN ni disponibilidad del checkpoint.

Para E6 se requiere estado verified, fecha de finalización, verificación persistida,
identidad e intento identificados y concordancia entre
`assessment_identities.training_run_id` y `identity.model.training_run_id`.
Los estados active, failed e interrupted no completan la regla. En el linaje
tradicional, una evaluación asociada a más de un TRAIN no satisface el vínculo
inequívoco.

El repositorio `backend_api/app/repositories/stage2_status.py` reutiliza
`LINEAGE_SOURCES_CTES`, incluyendo la selección por identidad y deduplicación E6.
Entre evaluaciones visibles se prioriza una completada; las fechas e IDs dan un
orden determinista. No se fabrican RUN ni se materializan resultados nuevos.

Ambos endpoints anteriores ahora llaman al mismo `Stage2StatusService.status()`
y devuelven `Stage2Status`. El frontend consume una sola respuesta de
stage2-release-status. Un error de consulta se devuelve como HTTP 503, conserva
un mensaje explícito y ofrece reintento; no se devuelve eligible=false como
sustituto del error. Un TRAIN inexistente responde HTTP 404.

Se distinguen cuatro dimensiones:

| Dimensión | Contrato |
|---|---|
| Elegibilidad técnica | `eligible`, `eligibility` |
| Preparación operativa | `deployment_readiness`, `technical_blockers` |
| Publicación | `published`, `publication` |
| Disponibilidad efectiva | `available`, `available_for_inference`: publicación activa, deployment activo y smoke persistido PASS |

Las comprobaciones operativas tradicionales de paquete se conservan con una
conexión forzada a READ ONLY. El lector comprueba acceso, tamaño y SHA-256 del
checkpoint sin reconstruirlo ni ejecutar predicciones. No llama a enable() ni
publish(). Los endpoints mutantes siguen requiriendo la acción explícita y sus
validaciones operativas. La elegibilidad no constituye aprobación clínica.

## Evidencia real

TRAIN `bbbd5b60-afaa-4034-a504-a60ed642aafe`, E6
`dded6222-12ae-407a-82c6-601e265e3f7d`:

| Dato | Evidencia |
|---|---|
| TRAIN | completed; finalizó 2026-10-06 18:26:18.880875 UTC |
| EVALUATE | verified; finalizó 2026-10-08 15:37:55.449224 UTC; VAL, development |
| Vínculo | FK y `identity.model.training_run_id` coinciden con el TRAIN |
| Regla mínima | `eligible=true`; ambas condiciones true; sin condiciones faltantes |
| Modelo / arquitectura | custom_cnn / Custom CNN |
| Identidad de versión E5/E6 | 3ffcb0ec-324f-43fb-8521-d55cbe81f229 |
| Registro de versión / número | model_version_registered=false; version_number=null («Sin evidencia») |
| Checkpoint seleccionado | epoch_2.keras; 5.150.164 bytes |
| Identidad de checkpoint E6 | 4294d2b2-690b-5884-a3cb-fc7f0eb3653d |
| SHA-256 | b27d794028914408e186b6703140f8e4c204fe67471801f2dfa9b3a2033b18f3 |
| Acceso operativo | accesible y hash/tamaño verificados desde Docker mediante `_project_path` |
| EXPLAIN | N/A: sin ejecución asociada; no bloquea |
| Preparación / publicación / disponibilidad | ready=false; published=false; available=false |

La identidad E6 del checkpoint no es una afirmación de que exista ese ID en
`artifacts`. También hay evidencia E10 con ID
`0d6a030e-d706-5a68-a390-d5a5ecd8a069`, mismo archivo y checksum. No se cambiaron
ni intercambiaron estas identidades.

Los dos impedimentos operativos del caso son:

1. `MODEL_VERSION_NOT_REGISTERED`: falta registro operativo de la versión.
2. `E6_PUBLICATION_REFERENCE_UNSUPPORTED`: `stage2_model_publications` exige
   `evaluation_run_id NOT NULL` y la FK `fk_stage2_publication_evaluation` hacia
   `runs(id)`. No puede usarse un attempt_id como ese run_id. El lector no cambia
   ese contrato ni ofrece publicación directa de E6 bajo un identificador falso.

La adaptación de escritura para publicación directa de E6 queda fuera de esta
corrección de lectura y requerirá resolver explícitamente ese contrato. No se
aplicó migración, no se registró una versión ni se publicaron modelos.

Consulta reproducible de la evidencia mínima:

```sql
BEGIN TRANSACTION READ ONLY;
SELECT r.id AS training_run_id, r.status AS train_status,
       a.id AS attempt_id, a.state, a.finished_at,
       i.identity #>> '{model,training_run_id}' AS identity_training_run_id,
       i.identity -> 'model' AS model_evidence
FROM public.runs r
JOIN public.assessment_identities i ON i.training_run_id = r.id
JOIN public.assessment_attempts a ON a.identity_id = i.id
WHERE r.id = 'bbbd5b60-afaa-4034-a504-a60ed642aafe'
  AND a.id = 'dded6222-12ae-407a-82c6-601e265e3f7d';
ROLLBACK;
```

## Validación y archivos

`make test-stage2-status-backend`: 49 pruebas aprobadas. Incluye escenarios
sintéticos definidos con CTEs SELECT, el contrato HTTP, el caso real y huellas
antes/después de las tablas científicas, versiones, artefactos, deployments,
publicaciones y eventos. No inserta fixtures en PostgreSQL.

`make test-stage2-status-frontend`: 65 pruebas aprobadas; TypeScript/Vite aprobado.
Incluye fallos de API, reintento, elegibilidad E6, información ausente, métricas
bajas, checkpoint inaccesible y separación de disponibilidad/publicación.

GET reales al backend activo: stage2-release-status y stage2-availability
responden HTTP 200 con la evidencia de la tabla anterior. No se ejecutaron
TRAIN, EVALUATE, EXPLAIN, TEST, smoke tests ni publicación durante la validación.

Archivos principales:

- `backend_api/app/repositories/stage2_status.py`,
  `services/stage2_status.py`, `schemas/stage2_status.py` y `routes/governance.py`.
- `malaria_dl_local_project/src/malaria_dl/governance/eligibility.py` y delegación
  de la regla en `services/stage2_publication_service.py` y
  `services/stage2_availability_service.py`.
- `frontend/src/pages/Runs.tsx`, `pages/Stage2ReleaseDetail.tsx`,
  `components/reports/Stage2PublicationPanel.tsx`,
  `components/reports/TrainingRunGroupCard.tsx` y `types/api.ts`.
- `backend_api/tests/test_stage2_status_read_only.py`,
  `backend_api/tests/test_governance_api.py`, `frontend/tests/stage2-status.test.mjs`,
  `frontend/tests/executions-lazy-loading.test.mjs` y targets de `Makefile`.
