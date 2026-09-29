# E10.10.3 — Propuesta ordenada de cambios candidatos

**Plan documental. No se ha creado ni ejecutado ninguna migración. No inicia E10.10.4.**

Referencia: [auditoría](e10_10_3_integrity_performance.md) y [hallazgos/evidencia JSON](e10_10_3_findings.json). El head observado sigue siendo `20260922_01`; los 22 checksums históricos coinciden con ledger, baseline y archivos. Se conservan las clasificaciones ACTIVE de E10.10.2 y todos los objetos existentes.

## Decisión propuesta

Primero corregir el defecto de lectura del dataset y mejorar la verificación de checksums, ambos sin DDL. Después considerar una FK aditiva para publicación–versión–TRAIN. Estudiar la lectura tipada de eventos antes de crear un índice. Los índices nuevos o retiros por prefijo se difieren hasta contar con medición suficiente: el estado experimental vacío no justifica su despliegue.

La ausencia de planes SQL es explícita: la revisión automática rechazó EXPLAIN por contradicción entre autorización y restricciones del encargo. Se completó la auditoría con SELECT y análisis estático; ninguna propuesta afirma que un índice mejore un plan observado.

## Secuencia y condiciones de avance

| Orden | Candidato / hallazgos | Cambio propuesto | Condición de avance | Migración |
| --- | --- | --- | --- | --- |
| 0 | Compatibilidad y procedimiento — F11/F12 | Fijar revisiones E10 explícitamente admitidas durante el despliegue y ruta de bootstrap/rehearsal. | Ninguna reserva con aplicación incompatible; conservar comprobación de capacidades, cuerpos y search_path. | Ninguna por sí sola. |
| 1 | Resumen físico — F01 | Agrupar/separar por raíz o exponer selección explícita; no mezclar el inventario con universo oficial. Evitar sobrescritura por clase y metadata de una raíz para el total de ambas. | Contrato API revisado con consumidores; tests de dos raíces y permutación de filas. | No; servicio/API/tests. |
| 2 | Preflight de hashes — F10 | Comparar cada entrada del ledger con su archivo y rechazar diferencias/faltantes. | 22 entradas actuales pasan, 004_seed excluida explícitamente; sin cambiar hashes almacenados. | No; verificador/tests. |
| 3 | Vincular publicación a TRAIN de la versión — F02 | FK compuesta aditiva reutilizando `uq_model_versions_id_training_run`. | Confirmar invariant con responsable; precheck cero discrepancias, fixtures positivas/negativas y head compatible. | Sí, revisión nueva. |
| 4 | Lectores de eventos — F03 | Ruta tipada para capacidades E10 conocidas; conservar fallback anterior, decodificación y hashes. | Equivalencia de resultados/corrupción/orden/compatibilidad y beneficio demostrado en medición autorizada. | No inicialmente. |
| 5 | TRAIN summaries — F04 | Evaluar índice parcial de orden temporal; revisar `/runs` por separado antes de optimizar su vista agregada. | Volumen representativo y evidencia de orden/filtro/coste; no basta una FK o un LIMIT. | Condicional. |
| 6 | Historial de publicaciones — F05 | Evaluar índice por versión/scope/estado/updated_at. | Historial y frecuencia justifican coste; la lista activa ya tiene índice pertinente. | Condicional; prioridad baja. |
| 7 | Pares por prefijo — F06 | Evaluar cada índice estrecho individualmente; conservar por ahora. | Comparación antes/después y contrato completo de consulta, no idx_scan=0. | Condicional; ningún DROP aprobado. |

Los pasos no requieren alterar semilla, particiones, métricas, umbrales, elección de checkpoint, política clínica ni autorización de TEST. No se incorporan nuevos requisitos de elegibilidad científica a publicación.

## Candidato de integridad: FK de publicación

Objeto nuevo propuesto: `fk_stage2_publication_model_training`, nombre sujeto a verificación de colisiones en la futura revisión.

Contrato:

- Tabla hija: `stage2_model_publications`.
- Columnas: `(model_version_id, training_run_id)`.
- Tabla padre: `model_versions`.
- Columnas referenciadas: `(id, training_run_id)`.
- Acción propuesta: `ON DELETE RESTRICT`; conservar semántica inmediata habitual de esta relación.
- Índice padre: **reutilizar** `uq_model_versions_id_training_run`, ya presente. No crear otro UNIQUE.
- Mantener inicialmente las tres FK existentes, el índice parcial de versión activa y los CHECK de estado. No retirar constraints por “redundancia” durante el endurecimiento.

Precheck exclusivamente de lectura para una implementación futura (ya se ejecutó la variante COUNT durante esta auditoría):

```sql
SELECT p.id, p.model_version_id, p.training_run_id,
       v.training_run_id AS version_training_run_id
FROM stage2_model_publications AS p
JOIN model_versions AS v ON v.id = p.model_version_id
WHERE p.training_run_id IS DISTINCT FROM v.training_run_id;
```

La captura actual tiene cero publicaciones y cero discrepancias. Eso no prueba que un INSERT inválido esté rechazado hoy: precisamente falta la relación declarativa. Si aparecen discrepancias antes de implementar, detener el cambio; este plan no autoriza corregirlas con DML ni borrar publicaciones.

Para una tabla pequeña y ventana controlada, evaluar validación transaccional ordinaria. Si ya existe volumen que haga inconveniente la validación inicial, diseñar adición NOT VALID y validación posterior como pasos explícitos; no dejar indefinidamente una FK no validada ni presentar el paso intermedio como integridad histórica certificada. Se requiere revisión de locks y coordinación con publicaciones concurrentes. No se propone indexar automáticamente la FK hija: la consulta histórica se estudia por separado en F05.

La FK no certifica que un EVALUATE corresponda al checkpoint exacto ni añade umbrales/criterios clínicos. Cambiar esa política sería otra decisión funcional, fuera de esta propuesta.

## Candidatos de índices: definiciones lógicas, no DDL ejecutable

| Candidato lógico | Claves y predicado | Qué podría resolver | Coste / motivo para diferir |
| --- | --- | --- | --- |
| Orden de TRAIN summaries | B-tree `(started_at DESC NULLS LAST, created_at DESC, id)`; parcial `run_type = 'training'` | Filtro y Top-N exactos de la página MATERIALIZED. | Espacio/WAL por run; cero runs actuales. No resuelve por sí mismo el orden distinto de `/runs`. |
| Historial por versión | B-tree `(model_version_id, scope, is_active DESC, updated_at DESC)` | `status()` incluyendo inactivos. | Un índice adicional en publicar/reactivar; con poco historial el coste puede superar el beneficio. |

No se asigna todavía revision_id ni se escribe archivo Alembic. No se añaden INCLUDE de payloads JSONB ni índices GIN de métricas sólo leídas; pueden multiplicar el coste de escritura y no responden a filtros demostrados.

Para `/runs`, considerar primero una selección de IDs con el mismo orden seguida del agregado sólo sobre esa página. La equivalencia debe resolver explícitamente empates y cardinalidad de JOIN. No asumir que PostgreSQL hoy agrega toda la tabla: no hay plan medido. Para TRAIN summaries conservar el CTE MATERIALIZED, la precedencia del resultado científico validado y la etiqueta `val`.

Los candidatos por prefijo son únicamente:

1. `idx_artifacts_artifact_type` frente a `idx_artifacts_type_path`.
2. `idx_predictions_case_type` frente a `idx_predictions_case_type_run`.
3. `idx_runs_run_type` frente a `idx_runs_inference_script`.
4. `idx_training_history_run_id` frente a `idx_training_history_run_phase_epoch`.

No son duplicados exactos y no se aprueba su retirada. Los índices compuestos de identidad `(id, run_id)` o `(id, training_run_id)` pueden ser targets de FK y quedan fuera de esta lista. No tocar `train_event_id_unique`, `train_event_sequence_unique`, PK del ledger ni índices parciales de exclusividad.

## Compatibilidad E10 y despliegue

`execution/schema.py` exige exactamente `20260922_01` y capacidades estructurales. Un head nuevo sin cambio coordinado de aplicación bloqueará nuevas reservas, aunque sólo añada un índice.

Antes de cualquier revisión nueva:

1. Congelar el contrato de capacidades que debe permanecer: columnas, CHECK `train_event_metadata`, índices parciales, trigger `a_train_event_guard`, cuerpo de `train_event_guard` y search_path. No cambiar cuerpos ni nombres incidentalmente.
2. Definir explícitamente qué revisiones pasan el guard durante la transición. Conservar fail-closed para revisiones desconocidas; no comparar IDs lexicográficamente ni aceptar todo head posterior.
3. Desplegar aplicación que reconozca ambas revisiones aprobadas antes del upgrade, o usar una ventana sin nuevas reservas con actualización coordinada. Aceptar el head anterior temporalmente debe ser una decisión probada, no una excepción permanente.
4. Exigir gate libre y ausencia de sesiones/jobs activos mediante consultas de estado antes de mantenimiento que necesite locks. No llamar claim/finish como sondeo y no liberar owners automáticamente.
5. Aplicar únicamente una revisión **nueva** cuando esté autorizada en la fase correspondiente. Nunca editar `20260922_01`, revisiones anteriores ni SQL 001–029; no modificar `schema_migrations` para adecuarlo a una expectativa de conteo.
6. Verificar nuevo head, capacidades E10, constraints validadas e índices válidos/listos; comprobar integridad de hashes históricos y contratos de datos protegidos. Una prueba de reserva con fixtures pertenece al entorno aislado, no a public.

Este documento no autoriza ejecutar ninguno de esos pasos operativos.

## Runner transaccional y opción concurrente

El flujo actual `scripts/db/migrate.sh` llama a `validate_alembic_transactionally.py` antes del upgrade. El validador comparte conexión y transacción/savepoint, corre upgrade y revierte. No introducir `CREATE INDEX CONCURRENTLY` ni `autocommit_block()` sin rediseñar y probar esa garantía: concurrente no funciona dentro de la transacción y una salida a autocommit puede invalidar la promesa de ensayo sin persistencia.

Dos opciones a decidir **antes** de escribir una revisión:

- **Transaccional:** índice/constraint ordinario en ventana acordada, ensayo con rollback y revisión de locks. Es la opción a estudiar primero con tablas pequeñas; no implica permiso para bloquear escrituras de campañas activas.
- **Concurrente:** sólo si el volumen y disponibilidad lo exigen, mediante procedimiento específico, ensayo en instalación aislada, detección de índices inválidos y recuperación de interrupciones. No esconder esa vía en el runner actual ni ejecutarla en esta etapa.

Rollback de aplicación y reversión de schema se planifican por separado. La política vigente evita downgrade operativo: preparar corrección forward y conservar definiciones previas. La capacidad de recrear un índice no elimina el riesgo ni el tiempo de hacerlo.

## Bootstrap de instalación nueva

La baseline `20260726_00` tiene `upgrade: pass`; Alembic por sí solo no construye la fundación ML de una base vacía. El bootstrap histórico disponible en `scripts/reset/reset3/bootstrap_probe.py` demuestra el orden **SQL histórico sin 004_seed → Alembic**, pero es una utilidad extraordinaria con target específico, no un instalador general para public.

Una implementación futura deberá probar dos rutas en bases/schema aislados:

1. Upgrade desde una copia estructural compatible con E10.10.1, preservando 22 checksums y registros del ledger.
2. Instalación vacía: fundación SQL original, exclusión explícita del seed que crea datos ajenos, ledger fiel a los archivos realmente instalados y Alembic hasta el nuevo head.

El mismo catálogo final debe contener la FK candidata si fue aprobada, índices seleccionados, guardas E10 intactas y metadatos de revisión compatibles. No importar usuarios/modelos/dataset operativos como fixtures ni usar el bootstrap para regenerar el split. No llamar `init_db.main`, que está retirado; si se formaliza un instalador nuevo, hacerlo en código nuevo revisado, sin reescribir la historia.

## Pruebas y aceptación futura

| Área | Evidencia requerida para implementar | Prohibición en esta etapa |
| --- | --- | --- |
| Dataset API | Dos raíces, permutación, clases, total consistente, metadata correcta, compatibilidad de imágenes y UI gobernada. | No cambiar asignaciones, recalcular fingerprint ni regenerar imágenes. |
| Publicación | FK compuesta acepta par coherente/rechaza TRAIN ajeno; publish/status/reactivate/deactivate conservan comportamiento. | No publicar un modelo real ni ejecutar TRAIN/EVALUATE. |
| E10 | Idempotencia canónica, gaps, carreras, cierre, owner perdido, rollback/ack perdido, hashes legacy y stream E10. | No DML de prueba en public ni carga experimental. |
| Índices | Planes y medición con cardinalidades/frecuencias representativas y equivalencia del resultado. Autorización inequívoca antes de EXPLAIN SQL. | No crear índices ni afirmar rendimiento medido en esta auditoría. |
| Migración | Upgrade/preflight/rollback aislado; bootstrap nuevo; 22 checksums idénticos; head/capacidades aprobados. | No tocar migraciones históricas, stamp ni ledger para evadir guards. |

Las suites existentes se leyeron como evidencia de contratos; no se ejecutaron. La lista detallada de pruebas por hallazgo está en el JSON y en la auditoría. Este plan no certifica resultados futuros de pruebas ni tiempos de despliegue.

## Cierre

Cambios identificados: corrección de resumen físico, refuerzo del preflight histórico y FK aditiva candidata. Optimización de lectura e índices condicionada a evidencia adicional. No hay migraciones ejecutadas ni esquema/datos alterados. Trabajo detenido al cierre de E10.10.3.

**E10.10.3 — AUDITORÍA COMPLETADA, CAMBIOS IDENTIFICADOS.**
