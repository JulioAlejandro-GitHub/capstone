# SCC-ELIGIBILITY.1

## Plan inspeccionado (2026-10-19)

El selector de ModelComparison consume `/models?view=traceability` y los resúmenes
TRAIN de Ejecuciones. Se ampliará opcionalmente el catálogo con elegibilidad;
se conservarán los resúmenes y la selección múltiple. Las rutas de preflight y
report validarán nuevamente la elegibilidad antes de consultar comparaciones.

Se reutilizan AssessmentReadRepository, ScientificReadRepository.comparison_checkpoint
y checkpoint_evidence. La evidencia E5 de train_execution_sessions es necesaria:
el checkpoint_artifact_id de sus assessments es un UUID derivado de version_id,
y no el UUID del registro de artifacts publicado por TRAIN. La resolución debe
seguir assessment/lineage.py, acreditando contenido, propietario y selección;
comparar solamente los UUID rechazaría incorrectamente los dos RUN auditados.

Se agregarán pruebas de contrato, selector y consultas SELECT reales. No se
modificarán datos ni se ejecutarán procesos científicos.

## Contrato implementado

`GET /models?view=traceability&comparison=true` amplía cada `training_runs[]` con
`eligibility`: `run_id`, `eligible`, `train`, `evaluate`, `explain`, `reasons` y
referencias de `identity_id`/`attempt_id` en `evidence`. Sin `comparison=true` no
se realizan las consultas adicionales. Se conserva `SCC_MAX_COMPARISON_RUNS`.

Las etapas son booleanas; `null` significa error técnico de consulta, nunca
pendiente. Los motivos contienen `stage`, `code` y `message`. Las rutas POST
`/models/comparison/preflight` y `/models/comparison/report` vuelven a consultar
la evidencia: HTTP 422 `RUN_NOT_ELIGIBLE` o 503 `ERROR_DE_CONSULTA` impiden
continuar aunque el cliente eluda el selector. Se mantienen permisos existentes.

- TRAIN: tipo training, estado completed y checkpoint seleccionado registrado,
  propietario correcto y selección coherente con época/fase.
- E5: sesión verified, prueba persistida concordante con el artefacto registrado
  (path, SHA-256, bytes, época/fase y RUN); referencia derivada con la misma
  fórmula UUID5 de `assessment/lineage.py`; versión, input_contract y procedencia
  coinciden con el modelo de cada assessment.
- EVALUATE: identidad independiente, intento verified y finished_at presente,
  resultados positivos, cantidad igual a samples declarados y verification.count,
  hash de verificación presente y checkpoint coherente.
- EXPLAIN: iguales comprobaciones, más dos artefactos por resultado y
  artifacts_hash presente, conforme a `assessment_attempt_guard` y al contrato
  de verificación `assessment/service.py`. Esa cantidad se aplica a la población
  declarada por ese EXPLAIN, no a toda la población VAL/TEST.
- Los resultados y artefactos se cuentan por attempt_id. Ningún intento failed,
  parcial, ni identidad sin intento habilita la selección. Se aceptan todas las
  alternativas válidas sin combinar intentos; `training_validation_final` no
  aparece como sustituto en la consulta de assessments.
- No se exige TEST, cobertura universal EXPLAIN ni igualdad de commit. La
  elegibilidad no asocia un EXPLAIN con una evaluación particular: acredita ambos
  contra el mismo TRAIN/checkpoint. Los análisis posteriores conservan sus
  verificaciones de split, propósito, población y protocolo.

Reutilización SQL: `ScientificReadRepository.comparison_checkpoint` (proyección
ampliada con path/bytes, sólo interna), `checkpoint_evidence` y
`AssessmentReadRepository`. Se añadieron `eligibility_training` (runs +
train_execution_sessions) y `eligibility_attempts` (identidades + intentos +
conteos correlacionados de resultados/artefactos). Transacciones READ ONLY,
REPEATABLE READ y savepoint por RUN; errores de conexión invalidan la respuesta
completa y errores de un RUN no contaminan los demás. No hay migraciones ni
comprobaciones de versión de esquema.

A5 reutiliza `checkpoint_binding` para resolver referencias E5 cuando el UUID
lógico no corresponde directamente a artifacts. A6 conserva su advertencia
PROTOCOL_DIFFERENCE_DECISION con texto explícito sobre umbrales distintos.
No se recalculan ni modifican resultados científicos.

## Archivos

Backend: repositorios `assessments.py`, `scientific_results.py`; servicios
`comparison_eligibility.py`, `catalog.py`, `scientific_preflight.py`; rutas
`catalog.py`, `scientific_preflight.py`; contrato `schemas/scientific_read.py`.
Pruebas: `test_comparison_eligibility.py` y ajuste del aislamiento de la prueba de
permisos en `test_scientific_preflight.py`.

Frontend: `ModelComparison.tsx`, `ComparisonEligibilityStatus.tsx`,
`ScientificReport.tsx`, `useComparisonCatalog.ts`, `services/api.ts`,
`types/scientificRead.ts` y `tests/scc-selection.test.mjs`.
Documentación: este archivo e índice `docs/README.md`. Sin cambios CSS.

## Auditoría PostgreSQL real — 2026-10-19

El catálogo completo tuvo 16 TRAIN, 2 elegibles, 14 no elegibles, 0 errores;
lectura observada de aproximadamente 0,19 segundos en los contenedores existentes.

| RUN | TRAIN | EVALUATE válidos | EXPLAIN válidos | Elegible |
|---|---|---|---|---|
| 338136db-a207-47fc-bbf3-d17ce85c0dc2 | completed, epoch_4.keras | 2 (VAL y TEST) | 5 | Sí |
| bbbd5b60-afaa-4034-a504-a60ed642aafe | completed, epoch_2.keras | 1 (VAL) | 2 | Sí |

La auditoría de las identidades VAL indicadas en el pedido comprobó 2.693 muestras
por RUN, igualdad exacta del mapa sample_id → (label, sha256), cero ausencias y
cero discrepancias. Umbrales efectivos: 0,4 y 0,5. A3 acredita población; A5
acredita linaje; A6 conserva advertencias metodológicas. A4 mantiene evidencia
incompleta de configuración: la elegibilidad no elimina ese diagnóstico ni
implica comparabilidad universal. Las identidades reales se usan sólo en pruebas,
no en reglas de producción.

## Comportamiento verificable del selector

Se conserva el diálogo, búsqueda, resúmenes TRAIN y selección múltiple. Cada RUN
muestra `TRAIN ✓/— · EVALUATE ✓/— · EXPLAIN ✓/—` y su motivo. Un checkbox
incompleto queda disabled pero la fila permanece visible; un RUN ya seleccionado
se puede quitar. Error SQL muestra `Error`, role=alert y reintento de elegibilidad.
Ausencia de respuesta también bloquea la selección. No se añadieron acciones de
ejecución científica. El bloque de representaciones reúne las ausencias de
embeddings/PCA/UMAP/CKA con RUN afectado y aclara que EXPLAIN no las genera
necesariamente. Identidades técnicas no se repiten en los indicadores de etapas.

Verificación mediante renderizado React y aserciones sobre HTML real generado;
no se realizó inspección visual en navegador ni captura de pantalla.

## Pruebas y límites

- `docker exec capstone_backend python -m pytest tests/test_comparison_eligibility.py tests/test_scientific_preflight.py tests/test_scientific_report.py tests/test_scc_core.py -q`: **108 passed**.
- Incluye SELECT real de ambos RUN, poblaciones VAL, advertencia A6, resolución
  A5 y falla SQL real `SELECT 1/0` dentro de savepoint; se comprueba
  transaction_read_only=on. Pruebas sintéticas cubren ausencia de etapas,
  intentos no verificados, resultados parciales, artefactos insuficientes,
  checkpoints contradictorios, alternativas válidas, TEST opcional y rechazo
  en ambas rutas aun eludiendo el selector.
- `docker exec capstone_frontend npm run build`: TypeScript y Vite PASS.
  Advertencia de tamaño de chunk >500 kB; no se modifica empaquetado.
- La elegibilidad acredita evidencia persistida; no relee binarios ni recalcula
  hashes físicos de checkpoints/artefactos. Se conservan las restricciones de
  inmutabilidad existentes en PostgreSQL.
- Las lecturas de catálogo y validación de admisión son snapshots separados;
  cada ruta vuelve a verificar. Los servicios de análisis mantienen sus propias
  transacciones de lectura y sus comprobaciones científicas.
- No se ejecutaron TRAIN/EVALUATE/EXPLAIN, escrituras experimentales, commits ni push.
- `docker exec capstone_frontend npm test`: **395/395 PASS**, sin omitidas.
  La nueva prueba de representaciones requirió aislar sus imports HTTP en el
  cargador de pruebas; después de ese ajuste pasó la suite completa. Las 19
  pruebas de `scc-selection.test.mjs` incluyen renderizado del selector, estados
  elegible/incompleto/error, capacidad, selección y bloque consolidado.
- `git diff --check`: PASS.
