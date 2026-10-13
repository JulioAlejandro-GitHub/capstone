# E6 en el linaje de ejecuciones

Estado documental: `CURRENT_DOC`. Fecha: 2026-10-08.

## Contrato de lectura

`/runs/training-summaries` y `/runs/{training_run_id}/lineage-children`
comparten `LINEAGE_SOURCES_CTES` en
`backend_api/app/repositories/assessment_lineage.py`. Se conserva el linaje
tradicional de EVALUATE y EXPLAIN y se incorporan identidades E6 de tipo
`evaluate` mediante `assessment_identities.training_run_id`.

La proyección es exclusivamente de lectura. No crea RUN, relaciones, evaluaciones,
métricas ni artefactos. No modifica el contrato de ejecución ni la elegibilidad
para Stage 2.

## Estados y duplicación

- Se muestra una evaluación por identidad E6 con al menos un intento.
- Se prioriza un intento `verified`; entre intentos del mismo grupo se elige el
  mayor `ordinal`, con ID como desempate determinista.
- Si no hay verificado, se muestra el último intento `active`, `failed` o
  `interrupted`. La tarjeta comunica el estado y carece de métricas verificadas.
- `evaluation_count` cuenta evaluaciones relacionadas visibles, no exclusivamente
  éxitos científicos. Los fallos y reintentos de una identidad no suman múltiples
  evaluaciones. Las identidades científicas distintas sí cuentan por separado.
- Si `evaluations.source_assessment_attempt_id` vincula un RUN tradicional con
  cualquiera de los intentos de una identidad E6 visible del mismo TRAIN, prevalece
  E6. El RUN sigue disponible por su ruta histórica pero no se cuenta dos veces.
- La deduplicación requiere ese vínculo explícito; no infiere equivalencia por
  modelo, métricas, fechas o nombres. Los EXPLAIN tradicionales se conservan.
- El orden global sigue siendo inicio ascendente, creación e ID; `limit` limita
  el total combinado, y los contadores describen el conjunto completo.

## Representación y navegación

Cada resultado tradicional incluye `source_kind="run"` y su `run_id`.
E6 incluye `source_kind="assessment_e6"`, `attempt_id`, `identity_id`,
`training_run_id`, `state`, `ordinal`, `split`, `purpose`, fechas y `verification`.
No contiene `run_id`. Las métricas proceden de `verification.metrics`.

El frontend reutiliza las tarjetas, badges, matriz y métricas existentes. Los
filtros identifican E6 con `assessment:{attempt_id}` para evitar confundir IDs.
La ruta `/modelo-ia/evaluaciones/e6/{attempt_id}` consulta el endpoint existente
`GET /assessments/{attempt_id}`; tiene un enlace al TRAIN original. La navegación
tradicional de RUN y EXPLAIN permanece independiente.

## Validación

```sh
make test-e6-lineage-backend
make test-e6-lineage-frontend
```

El primer target ejecuta contratos y escenarios PostgreSQL de solo lectura. Los
escenarios sintéticos usan CTEs con `jsonb_populate_recordset`, sin insertar datos,
crear tablas temporales ni ejecutar operaciones científicas. Cubren ausencia de
hijos, fuentes separadas y combinadas, reintentos, estados, identidades distintas,
deduplicación explícita, alcance por TRAIN, EXPLAIN y límite global.

La prueba del caso real compara huellas de `runs`, `run_lineage`, `evaluations`,
`assessment_identities`, `assessment_attempts`, `assessment_results` y
`assessment_artifacts` antes y después de las lecturas HTTP; exige igualdad.

Evidencia HTTP del backend activo, 2026-10-08:

| Consulta | Resultado |
|---|---|
| Resumen de `bbbd5b60-afaa-4034-a504-a60ed642aafe` | HTTP 200; `evaluation_count=1`, `explainability_count=0` |
| Hijos de ese TRAIN | HTTP 200; incluye `dded6222-12ae-407a-82c6-601e265e3f7d`, origen E6, `verified`, `val`, `development` |
| `/assessments/dded6222-12ae-407a-82c6-601e265e3f7d` | HTTP 200; 2.693 resultados, recall `0.910188679245283`, F2 `0.900268736936399` |

La huella de resultados persistida del intento es
`5aebe6e3e04c86e2825eb10329f4fa245ab32ad85ac2bb19dbea4a75bcc925c3`.
La prueba de referencia presupone que esa evidencia continúa disponible.

Las pruebas frontend comprueban renderizado, apertura de tarjetas y detalle,
enlaces de E6 y TRAIN, estados sin métricas, carga HTTP, cancelación y errores.
El target también valida TypeScript y el build de Vite dentro de Docker.
Resultado de cierre: 46 pruebas backend y 63 pruebas frontend focalizadas
aprobadas; compilación TypeScript/Vite aprobada.

La suite frontend amplia detectó una falla previa ajena a E6 en
`executions-dataset-version.test.mjs`: espera el literal `No registrado`, mientras
`RunSummaryRow.tsx` ya contiene `No registrado 2` en HEAD. No se cambió ese texto
ni se debilitó esa prueba. Las suites focalizadas de E6, carga diferida, rutas,
resultados científicos y Stage 2 se ejecutan con el target anterior.

## Archivos de implementación

- Backend: `repositories/assessment_lineage.py`, `schemas/assessment_lineage.py`,
  `schemas/lineage_children.py`, `services/lineage_children.py` y
  `services/training_summaries.py`, bajo `backend_api/app/`.
- Frontend: `src/App.tsx`, `src/router.ts`, `src/services/api.ts`,
  `src/types/api.ts`, `src/pages/Runs.tsx`, `src/pages/AssessmentDetail.tsx`,
  `src/hooks/useAssessment.ts`, `src/components/reports/TrainingRunGroupCard.tsx`
  y `src/components/reports/AssessmentEvaluationCard.tsx`.
- Pruebas: `backend_api/tests/test_e6_lineage_read_only.py`,
  `backend_api/tests/test_lineage_children_api.py`,
  `backend_api/tests/test_training_summaries_api.py`,
  `frontend/tests/e6-lineage.test.mjs` y los dos targets de `Makefile`.
- Documentación: este contrato e índice `docs/README.md`.
