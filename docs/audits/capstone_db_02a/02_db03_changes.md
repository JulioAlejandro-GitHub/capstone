# CAPSTONE-DB-02A — EXPLAIN E6

Estado documental: `HISTORICAL_AUDIT` — 2026-10-12. Implementación validada en checkout aislado; no desplegada.

## Lectura y contrato

`repositories/assessment_lineage.py` incluye evaluate y explain. Regla: por identidad gana el intento verificado de ordinal mayor; si no existe, el último ordinal, con su estado. Se conserva la deduplicación de EVALUATE proyectado a runs. EXPLAIN E6 usa exclusivamente sus identidades/intentos; las filas históricas basadas en runs conservan su representación, sin decisiones por versión de esquema.

`services/training_summaries.py` y `services/lineage_children.py` comparten la selección y cuentan por kind. EXPLAIN usa source_kind=`assessment_explain_e6`; EVALUATE conserva `assessment_e6`. La lista entrega identity_id, attempt_id, training_run_id, ordinal, estado, método, result_count y artifact_reference. Result_count se toma de verification.count únicamente en estado verified: los estados failed/active/interrupted no exponen evidencia certificada. No se unen assessment_results ni assessment_artifacts en la lista.

`schemas/assessment_lineage.py` y `schemas/lineage_children.py` incorporan AssessmentExplanationChild a la unión discriminada. `frontend/src/types/api.ts` refleja el contrato, sin run_id artificial. La referencia dirige al endpoint existente `/assessments/{attempt_id}/artifacts`; el detalle usa `/assessments/{attempt_id}`. No se crean filas para adaptar el DTO.

## Interfaz

`Runs.tsx`, `TrainingRunGroupCard.tsx` y `AssessmentExplanationCard.tsx` muestran EXPLAIN E6, conservan identidad de filtros y reconciliación de contadores. El endpoint añade offset; las páginas mantienen límite 100 y conteos globales. Anterior/Siguiente permiten alcanzar hijos posteriores al primero centenar.

`useAssessment.ts` acepta evaluate/explain. `AssessmentDetail.tsx` discrimina el detalle. `AssessmentExplanationDetail.tsx`, `useAssessmentArtifacts.ts` y el cliente HTTP conservan método, identidad, intento, checkpoint, evidencia y referencias, cargadas de cien en cien. Los overlays solo solicitan contenido al pulsar «Ver imagen», mediante el servidor de artefactos existente. Error de archivo ausente/inaccesible se presenta dentro del detalle; no elimina la ejecución. Los mapas NPY se muestran como referencia. No se verificó contenido ni hashes de archivos externos.

## Evidencia

- `make -f docs/audits/capstone_db_02a/Makefile test-db03`: **52 PASS** en PostgreSQL aislado con el esquema restaurado. Incluye 14 TRAIN sintéticos, 1 EVALUATE y 2 EXPLAIN, estados, reintentos, endpoint de detalle/artefactos y 106 hijos repartidos en páginas 100+6.
- `make -f docs/audits/capstone_db_02a/Makefile test-db03-ui`: **15 PASS** (incluye mensajes de observabilidad). Verifica enlaces, identidad, evidencia, referencias, error de artefacto y navegación a offset 100.
- Compilación TypeScript/Vite: **PASS**. Advertencia de tamaño de bundle, sin dependencias nuevas.
- Suite completa frontend: **264 PASS / 1 FAIL preexistente**, detallado en el cierre.
- `read_operational.py`: **PASS**, ejecuta list_training_summaries y get_training_lineage_children modificados en proceso separado con PGOPTIONS read-only. 14 TRAIN; uno con 1 EVALUATE y 2 EXPLAIN verificados, otros 13 con cero. Conteos iguales a filas, sin truncamiento. Salida únicamente agregada, sin identidades clínicas, imágenes o predicciones.

## Cambios en pruebas existentes

- `test_e6_lineage_read_only.py`: el caso que esperaba cero EXPLAIN ahora exige la identidad EXPLAIN E6. El escenario con IDs/métricas operativos fijos se reemplaza por fixtures equivalentes en forma, para ejecutar aceptación en la base aislada. La comprobación operativa real está separada en read_operational.py.
- `test_lineage_children_api.py`: expectativas y doble del servicio admiten offset=0.
- `test_lineage_children_postgres.py`: la instantánea antigua de 24 TRAIN y run_id obligatorio se sustituye por un escenario mixto run/E6 con cuatro hijos, páginas, validación de offset e invariancia de tablas científicas aisladas.
- `test_training_summaries_postgres.py`: la instantánea de 35 TRAIN/99 runs y conteos solo por run_lineage se sustituye por TRAIN con y sin E6; conserva validación de campos de publicación y ausencia de escrituras.
- `executions-lazy-loading.test.mjs`: las tres expectativas de código cambian para recarga explícita por paginación, posición dentro del total y unión EXPLAIN run/E6. Se mantiene el bloqueo de GET duplicado al reabrir.
- `e6-lineage.test.mjs`: detalle EVALUATE conserva su prueba, aislando el import del nuevo componente; se agregan renderizados EXPLAIN y navegación.

Los fixtures PostgreSQL emplean CTE jsonb_populate_recordset sobre los tipos reales del esquema aislado. Ejecutan las consultas reales, sin crear evidencia científica ficticia ni relajar triggers. Las pruebas de rollback del Bloque 1 sí realizan escrituras sintéticas exclusivamente en la base aislada.
