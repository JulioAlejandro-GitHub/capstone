# E10.10.3 — Integridad, consultas e índices

**E10.10.3 — AUDITORÍA COMPLETADA, CAMBIOS IDENTIFICADOS.**

## Dictamen ejecutivo

Se acredita **un defecto de lectura/agrupación** en el resumen físico antiguo del dataset y se proponen dos mejoras de integridad: vincular declarativamente publicación–versión–TRAIN y verificar los checksums históricos desde el preflight. Las optimizaciones de lectores de eventos y los posibles índices de listados/publicaciones quedan como **candidatos sin beneficio medido**. No se justifica crear ni eliminar índices ahora.

Se conservan las clasificaciones ACTIVE de E10.10.2. Los controles globales, el ledger dual TRAIN y los contratos científicos no se sustituyen ni se relajan. Las próximas decisiones están ordenadas en [propuesta de migración](e10_10_3_migration_proposal.md); el [JSON](e10_10_3_findings.json) contiene cada hallazgo con evidencia, consultas, resultados SELECT, catálogos y fuentes de reproducción.

## Alcance y evidencia

Se leyeron íntegramente los cuatro documentos obligatorios; el JSON completo se cargó y recorrió programáticamente, y se contrastaron sus catálogos con código/SQL y las matrices completas de ownership. Se usa E10.10.1 como baseline y E10.10.2 como frontera funcional; no se vuelve a auditar obsolescencia ni se ejecuta otra revisión integral de huérfanos.

Commit inspeccionado: `077b96c1737879e772f1d897d82e56f3a3b8e4a2`. Capturas selectivas UTC: `2026-09-29T13:13:10.127105+00:00` y `2026-09-29T13:14:44.019300+00:00`. Base `malaria_experiments`, OID 1600436, PostgreSQL 17.9, `public`, Alembic `20260922_01`. Dos conexiones con `default_transaction_read_only=on` desde apertura, aislamiento REPEATABLE READ, statement_timeout 20 s, lock_timeout 2 s y ROLLBACK al finalizar. Los SELECT de catálogos afectan contadores de lectura, pero no datos de aplicación. No se importaron ni invocaron servicios de escritura.

No se ejecutaron DDL, DML, migraciones, TRAIN, EVALUATE, EXPLAIN científico, TEST clínico, ANALYZE ni cargas sintéticas. No se modificaron usuarios/modelos/dataset, ni se recalcularon fingerprints de imágenes. Sólo se ejecutaron SELECT y una reproducción local de funciones puras de agregación, sin inicializar la aplicación.

**Límite de planes SQL:** se preparó un colector con EXPLAIN sin ANALYZE, pero la revisión automática lo rechazó al interpretar la prohibición de EXPLAIN de las restricciones como prevalente. Ese colector no se ejecutó. Se retiró EXPLAIN y se ejecutó una alternativa exclusivamente SELECT. Por ello no se publican planes, costes estimados ni tiempos inventados; las propuestas de rendimiento se apoyan en forma SQL/catálogo y quedan condicionadas a medición posterior.

Resultados del contraste enfocado:

- 389 definiciones de índices coinciden con el baseline; **ningún duplicado físico exacto** en la firma estructural comparada. Esto no excluye coberturas por prefijo.
- 134 constraints y 12 funciones críticas coinciden con el baseline; no es una prueba nueva de todas las máquinas de estado ni de concurrencia.
- Los 22 checksums vivos coinciden con los archivos históricos. No se editó ni normalizó ninguno.
- Gate: una fila libre. Runs, miembros, intentos, sesiones, records TRAIN, model_versions y publicaciones: cero filas. No hay cardinalidad experimental representativa para recomendar DDL por rendimiento.
- Asignaciones oficiales: 27.558; inventario físico: dos raíces de 27.558, todas sus FK opcionales de versión/materialización NULL. La suma física 55.116 no define el universo oficial.

## Registro de hallazgos

| ID | Clase | Prioridad | Hallazgo | Migración |
| --- | --- | --- | --- | --- |
| E10.10.3-F01 | CONFIRMED_DEFECT | P1 | El resumen físico mezcla raíces y sobrescribe clases | False |
| E10.10.3-F02 | INTEGRITY_IMPROVEMENT | P2 | La publicación no liga declarativamente su TRAIN a su model_version | True |
| E10.10.3-F03 | PERFORMANCE_CANDIDATE | P2 | Los lectores de eventos convierten filas completas a JSON para filtrar y ordenar | False |
| E10.10.3-F04 | PERFORMANCE_CANDIDATE | P3 | Ordenamientos Top-N de frontend sin índice con el contrato completo | conditional |
| E10.10.3-F05 | PERFORMANCE_CANDIDATE | P3 | Consulta histórica de publicaciones no coincide con el índice de candidatas activas | conditional |
| E10.10.3-F06 | PERFORMANCE_CANDIDATE | P3 | Cuatro pares tienen cobertura por prefijo, sin redundancia económica demostrada | conditional |
| E10.10.3-F07 | INTENTIONAL_DESIGN | P2 | Exclusividad, idempotencia y evidencia dual son invariantes complementarias | False |
| E10.10.3-F08 | INTENTIONAL_DESIGN | P2 | Los consumidores científicos seleccionan versión y asignaciones; el inventario tiene otro alcance | False |
| E10.10.3-F09 | INTENTIONAL_DESIGN | P2 | FK sin índice no implica índice faltante en reservas y recuperación | False |
| E10.10.3-F10 | INTEGRITY_IMPROVEMENT | P1 | El preflight de adopción no comprueba los 22 checksums que preserva la política | False |
| E10.10.3-F11 | INTENTIONAL_DESIGN | P1 | Una revisión futura exige desplegar compatibilidad E10 deliberadamente | paired_with_candidate |
| E10.10.3-F12 | INTENTIONAL_DESIGN | P1 | El preflight transaccional no es una vía genérica para índices concurrentes | False |
| E10.10.3-F13 | INSUFFICIENT_EVIDENCE | P3 | No hay evidencia para atribuir latencia o fijar un lote de índices | False |

Prioridades: P1 antes de cualquier evolución/uso del contrato afectado; P2 mejora candidata a revisar; P3 diferir hasta evidencia de escala. Un hallazgo INTENTIONAL_DESIGN P1 es una condición de compatibilidad, no un defecto a eliminar.

## Rutas críticas: consultas, selectividad y coste de escritura

| Ruta | Acceso real / selectividad | Índices y evaluación | Frecuencia estimada, no medida |
| --- | --- | --- | --- |
| Crear/congelar campaña | PK de campaña; configuraciones por campaña/hash; miembros por campaña/posición. Las guardas validan matriz, hashes y snapshots. | PK/UNIQUE existentes soportan identidades y referencias. Una matriz congelada tiene conjunto finito de miembros; no se justifica un índice por cada FK. | Creación/congelación una vez por campaña; escrituras por configuración/miembro, no por epoch. |
| Claim/ejecución | `ExecutionRepository.claim`: campaña + estado; count de attempts por member; ORDER BY (state='pending') DESC,position y LIMIT 1. | Campaña/estado y campaña/posición; attempts(member_id,ordinal), sesión por PK. Booleano puede necesitar sort; no medido. Conservar orden determinista/presupuesto. | Una reserva por intento; el gate impone exclusión, no usar SKIP LOCKED para “acelerarla”. |
| Recuperación | `CampaignRepository.get` obtiene attempts vía member y orden position/ordinal; reconcile consulta cada sesión por run y verifica evidencia/checkpoints. | JOIN por member y PK sesión cubiertos; existe trabajo por intento, pero también verificación de archivos. No atribuir su coste sólo a SQL ni saltar verificación de sesiones verified. | Por reanudación/recuperación; aumenta con historial de intentos. No ejecutado aquí. |
| Persistir RunEvent | Igualdad global event_id, igualdad run_id/sequence y MAX(sequence) por run; autorizar/bloquear antes de aceptar duplicado. | UNIQUE parcial event_id y (run_id,event_sequence); no necesita otro índice run_id. MAX tiene clave pertinente, sin afirmar plan observado. | Varios eventos por epoch/fase más terminales; mantener tres índices del ledger implica WAL en escrituras. No agregar GIN al payload por defecto. |
| Leer evidencia TRAIN | Lectores separan por to_jsonb(record)->event_id; E10 ordena sequence convertido. | PK soporta run + orden legacy; el orden expresivo no coincide directamente con índice tipado E10. F03 prioriza reescritura antes que índice. | Finalización, verificación, recuperación y consulta de estado; payloads pueden contener muestras de validación por epoch. |
| Consultar validación | `TRAINING_SUMMARIES_SQL`: página MATERIALIZED de trainings, JOIN por run y `parameters->training_results`; `_summary_row` valida TrainingResultsV1 y fuerza metrics_split='val'. | No se filtra por JSON científico: no hay evidencia para otro GIN. La consulta legacy de calibración fija todas las columnas de PK del record, por lo que no justifica índice en created_at. | Por carga/refresco de frontend; limitada a 500 trainings. La proyección científica se escribe una vez en la aceptación final, no recalcula métricas en lectura. |
| Listado /runs | Vista `vw_run_dashboard`, agregación de run_metrics, orden run_name/started_at, límite; posteriores LATERAL por run. | Índice run_metrics(run_id); ningún índice nuevo se deduce sólo de LIMIT. F04 distingue esta consulta de TRAIN summaries. | Por navegación; coste depende de número de runs y métricas, ambos sin historial aquí. |
| Modelos disponibles/publicación | `Stage2PublicationService.models`: datasource,scope,is_active + published_at; status busca por versión y todo historial. `_context` sigue versión→TRAIN/checkpoint y evaluación. | Índice candidates coincide con lista activa; history no comparte exactamente filtros/orden (F05). PK y FK compuestas sostienen checkpoints; F02 propone una relación adicional sin duplicar UNIQUE. | Lectura por navegación/selección; publicación/reactivación poco frecuente frente a eventos TRAIN. |
| Dataset oficial | `_resolve(version_id)` y verify_integrity leen asignaciones por versión; UNIQUE(version,source_record) permite ese filtro y orden. Devuelve snapshot/materialización sellada. | Selectividad versión actual ≈100% de las asignaciones: una lectura amplia puede ser correcta, no un defecto por sí sola. No crear índice por cada columna que aparece en JOIN. | Preflight de campaña/intento según ruta; verifica también archivos en operación normal, omitido aquí. |

El corpus exacto de SELECT extraído sin imports está en `query_corpus` del JSON. Incluye consultas con locks de las rutas originales **como texto**, no ejecutadas por esta auditoría. Las estimaciones anteriores se deducen de los llamadores, no de contadores de producción.

## Dataset: defecto reproducido y consumidores correctos

`dataset_summary()` consulta la vista física sin dataset_dir ni dataset_version_id. Recibe 12 filas; `counts_from_rows` asigna cada clase con `=` y suma los totales con `+=`. Al haber dos filas de cada pareja split/clase, el último registro gana para la clase, pero ambos suman al total. El ORDER BY no desambigua raíz y first aporta metadata de sólo una. Resultado de la reproducción:

| Magnitud | Observación |
| --- | ---: |
| Filas agrupadas leídas | 12 |
| Total publicado por agregador | 55.116 |
| Total TRAIN físico | 44.226 |
| Total val físico | 5.449 |
| Total test físico | 5.441 |
| Suma de clases del resultado observado | 27.578 |
| Cambian clases al invertir filas | Sí |

No se etiqueta ese 27.578 como población real: es un artefacto del orden en la función defectuosa. Los valores oficiales por asignaciones siguen siendo 22.180/2.693/2.685. La reproducción usa filas SELECT reales y sólo tres funciones puras extraídas por AST. No es una nueva prueba de split ni una ejecución clínica.

La pantalla actual `DatasetBrowser.tsx:170` consume `/api/datasets` y el detalle por versión; no el resumen físico defectuoso. `backend_api/app/services/governed_datasets.py` usa estadísticas/checks por versión y materialización. La API antigua sigue registrada, así que el defecto de contrato es real aunque no se acredite tráfico actual sobre ella.

`/api/dataset/images` sí devuelve inventario global y es usado por UploadedPredictions/Deployments. Puede ofrecer imágenes de ambas raíces para inferencia técnica; no equivale a resolver el split oficial. `Stage2AvailabilityService._smoke` y `DeploymentService` pueden escoger la primera imagen del inventario si no se da ID: esto no acredita contaminación de TRAIN ni justifica cambiar criterios clínicos. Es conveniente mostrar procedencia explícita, sin cambiar silenciosamente la imagen seleccionada. `data/registry.py` filtra dataset_dir al recuperar inventario; `assessment/lineage.py` usa asignaciones por versión. No se encontró una ruta de campaña que use 55.116 como población científica.

## Integridad: límites entre SQL y aplicación

Los guards vigentes y sus cuerpos coinciden con el baseline. PK/FK/UNIQUE/CHECK y triggers se complementan: las FK aseguran existencia, los bindings diferidos validan el agregado campaña-intento-run-sesión, y completion verifica el contrato científico. El CHECK de metadatos E10 admite dos familias y valida envelope; no decodifica el texto canónico completo ni todos los valores científicos. Esa responsabilidad permanece en `_decode`, ResultService y TrainingCompletionValidator. No se propone duplicar todas esas reglas con CHECK sobre JSONB.

La dependencia exacta del ledger es **train_execution_records.run_id → train_execution_sessions.run_id → runs.id**. Sesión active y owner válido son necesarios para escribir. El índice de secuencia es numérico y parcial; no convertir a texto para ordenar ni alterar el índice que el guard valida por nombre/predicado. La idempotencia no autoriza reintentar sobre sesión cerrada: esa restricción es intencional.

En modelos, las FK compuestas de run_lineage y model_versions vinculan checkpoint, artifact y TRAIN; UNIQUE con id como prefijo puede existir para ser objetivo de FK y no se elimina por parecer redundante con PK(id). Publicaciones fijan par versión/artifact pero su TRAIN es una FK independiente: F02 refuerza ese vínculo. No se detectaron publicaciones incoherentes y no se realizó una inserción negativa. La política `_eligibility` exige TRAIN/EVALUATE completed y está cubierta por `test_stage2_publication_eligibility.py`; no se añade requisito de métricas, EXPLAIN científico o elegibilidad clínica en esta auditoría. Vincular una evaluación a un checkpoint exacto exigiría una decisión funcional distinta y no se convierte aquí en defecto confirmado.

## Índices: conservar garantías y evitar sobreindexación

La firma de duplicados comparó tabla, método, unicidad, NULLS NOT DISTINCT, keys/INCLUDE, opclasses, collations, opciones de orden, expresiones, predicado y reloptions. Cero grupos idénticos. No se usó nombre parecido, tamaño ni idx_scan=0 como criterio de borrado. Los cuatro pares de prefijo del baseline se conservan como candidatos F06:

| Estrecho | Más ancho | Escritura / límite de la inferencia |
| --- | --- | --- |
| `idx_artifacts_artifact_type` | `idx_artifacts_type_path` | 8192 / 8192 bytes actuales; no representa volumen futuro. |
| `idx_predictions_case_type` | `idx_predictions_case_type_run` | 8192 / 8192 bytes actuales; no representa volumen futuro. |
| `idx_runs_run_type` | `idx_runs_inference_script` | 8192 / 8192 bytes actuales; no representa volumen futuro. |
| `idx_training_history_run_id` | `idx_training_history_run_phase_epoch` | 8192 / 8192 bytes actuales; no representa volumen futuro. |

`idx_model_versions_checkpoint_artifact` y `uq_model_versions_checkpoint_artifact` comparten columna, pero uno es completo no único y el otro parcial único (no NULL): no son duplicados exactos. El UNIQUE protege identidad, el completo puede cubrir consultas sobre NULL; no se aprueba su retiro sin revisar esas consultas. Lo mismo vale para índices de FK compuestas y parciales de exclusión. No se crea un índice adicional sólo porque el inventario reporte FK sin prefijo conservador.

Frecuencia relativa: filas E10 se escriben por eventos/epochs; `training_history` y `predictions` pertenecen también a rutas históricas y no reciben automáticamente todos esos eventos. Retirar sus índices no garantiza acelerar E10. Un índice parcial de lista TRAIN se mantiene al crear/modificar el run, mientras que un índice en records se mantiene en cada evento: estos costes no son equivalentes. Sin carga no se cuantifica ahorro de WAL, tiempo, bloat ni espacio futuro.

## Hallazgos detallados

### E10.10.3-F01 — CONFIRMED_DEFECT

**El resumen físico mezcla raíces y sobrescribe clases**

**Objetos:** `vw_dataset_browser_summary`, `/api/dataset/summary`, `/api/dataset/split`, `counts_from_rows`.

**Evidencia:**

- [backend_api/app/services/dataset_browser.py:84](../../backend_api/app/services/dataset_browser.py#L84) — `def counts_from_rows(`
- [backend_api/app/services/dataset_browser.py:126](../../backend_api/app/services/dataset_browser.py#L126) — `def dataset_summary(`
- [backend_api/app/routes/dataset.py:28](../../backend_api/app/routes/dataset.py#L28) — `def dataset_split(`
- [frontend/src/pages/DatasetBrowser.tsx:170](../../frontend/src/pages/DatasetBrowser.tsx#L170) — `api.getDatasetVersions`
- `docs/audits/e10_10_3_findings.json` → `observations.dataset_replay` (counts, counts_reversed)

**Impacto:** Respuesta internamente inconsistente: total 55.116 frente a suma de clases 27.578 en el orden observado. Invertir filas cambia clases pero conserva total. first selecciona metadata de una raíz sin seleccionarla en SQL. Puede inducir a interpretar dos inventarios como un único split oficial. No demuestra contaminación de TRAIN ni de la UI gobernada.

**Reproducibilidad:** SELECT devuelve 12 grupos (dos raíces × tres splits × dos clases); ejecución local de las tres funciones puras originales extraídas por AST, sin importar la aplicación. Se incluyen filas y reproducción en observations. No se llamó al endpoint HTTP ni se ejecutó ciencia.

**Propuesta técnica:** Corregir el contrato del endpoint físico: separar explícitamente resultados por dataset_dir y no presentar el agregado como split oficial; conservar conteos por clase sin sobrescritura y orden determinista. Si se pide resumen científico, obtenerlo por dataset_version_id desde asignaciones/estadísticas gobernadas. No sustituir simplemente = por += manteniendo la etiqueta de universo oficial. Mantener /api/dataset/images como inventario explícito hasta acordar su filtro con consumidores.

**Compatibilidad:** Cambio de servicio/contrato API y tests; no DDL, no nueva identidad de dataset ni modificación de filas. La UI actual DatasetBrowser consume /api/datasets, que debe conservarse. UploadedPredictions/Deployments sí consumen /api/dataset/images: no cambiar silenciosamente su población.

**Riesgo:** Medio por compatibilidad de clientes del endpoint antiguo; bajo para datos si sólo se modifica lectura/serialización.

**Migración:** False — Corrección de lectura/agrupación y contrato de respuesta.

**Pruebas requeridas para implementar (no ejecutadas):**

- Dos raíces con clases distintas; invariancia al permutar filas; total = suma de splits = suma de clases.
- Una raíz y cero filas; paginación determinista; fuentes/versiones identificadas.
- Contrato de /api/datasets intacto; split científico 22.180/2.693/2.685 y fingerprints sin cambios.

### E10.10.3-F02 — INTEGRITY_IMPROVEMENT

**La publicación no liga declarativamente su TRAIN a su model_version**

**Objetos:** `stage2_model_publications`, `model_versions`, `uq_model_versions_id_training_run`.

**Evidencia:**

- [malaria_dl_local_project/db/init/029_stage2_model_publications.sql:26](../../malaria_dl_local_project/db/init/029_stage2_model_publications.sql#L26) — `CONSTRAINT fk_stage2_publication_training`
- [malaria_dl_local_project/src/malaria_dl/governance/services/stage2_publication_service.py:23](../../malaria_dl_local_project/src/malaria_dl/governance/services/stage2_publication_service.py#L23) — `def _context(`
- `docs/audits/e10_10_1_baseline.json` → `constraints` (fk_stage2_publication_version_artifact, fk_stage2_publication_training)
- `docs/audits/e10_10_1_baseline.json` → `indexes` (uq_model_versions_id_training_run)

**Impacto:** Las FK garantizan existencia del TRAIN y par versión/checkpoint, pero no igualdad entre publication.training_run_id y model_versions.training_run_id. El servicio obtiene hoy el TRAIN de la versión; no hay publicaciones ni incoherencias observadas. Es una brecha de defensa declarativa, no corrupción acreditada.

**Reproducibilidad:** Comparar definición de las tres FK con _context; SELECT publication_training_mismatch=0 sobre tabla con cero filas. No se intentó insertar una publicación inválida.

**Propuesta técnica:** Considerar una FK compuesta (model_version_id, training_run_id) → model_versions(id, training_run_id), ON DELETE RESTRICT; reutilizar el UNIQUE existente. Conservar las FK actuales en una primera revisión aditiva. Validar previamente toda publicación si aparecen datos. No endurecer automáticamente la política de EVALUATE ni de elegibilidad.

**Compatibilidad:** Compatible con escrituras actuales que copian ambos IDs de _context. Necesita revisión Alembic nueva y compatibilidad del guard E10. El índice referenciado existente soporta la FK; no crear otro UNIQUE idéntico.

**Riesgo:** Medio: locks de validación y rechazo de datos preexistentes si el estado cambia. Sobre publicación normal, una comprobación adicional por escritura; no afecta eventos por epoch.

**Migración:** True — FK nueva, preferentemente aditiva; validación separada si el volumen futuro lo exige.

**Pruebas requeridas para implementar (no ejecutadas):**

- Fixture aislada: par coherente pasa y TRAIN ajeno falla; sin ejecutar entrenamiento.
- Publicar/reactivar/desactivar/reemplazar y rollback; datos históricos limpios.
- Bootstrap completo y upgrades con guard actualizado; preservar checkpoints y hashes.

### E10.10.3-F03 — PERFORMANCE_CANDIDATE

**Los lectores de eventos convierten filas completas a JSON para filtrar y ordenar**

**Objetos:** `train_execution_records`, `read_result_events`, `read_legacy_execution_records`.

**Evidencia:**

- [malaria_dl_local_project/src/malaria_dl/persistence/execution_record_readers.py:17](../../malaria_dl_local_project/src/malaria_dl/persistence/execution_record_readers.py#L17) — `def read_result_events(`
- [malaria_dl_local_project/src/malaria_dl/persistence/execution_record_readers.py:8](../../malaria_dl_local_project/src/malaria_dl/persistence/execution_record_readers.py#L8) — `def read_legacy_execution_records(`
- [malaria_dl_local_project/src/malaria_dl/persistence/result_repository.py:115](../../malaria_dl_local_project/src/malaria_dl/persistence/result_repository.py#L115) — `last = _query`
- `docs/audits/e10_10_1_baseline.json` → `indexes` (train_event_sequence_unique, train_execution_records_pkey)

**Impacto:** El predicado/orden por to_jsonb(record) no coincide sintácticamente con event_sequence ni con su predicado parcial. Además serializa payload al construir la fila JSON, incluso en la lectura legacy que descarta eventos. El impacto aumenta con epochs y payloads de predicción; no está medido y no se afirma un plan Seq Scan.

**Reproducibilidad:** Inspección de SQL y definición de índices. Cero filas TRAIN actuales; no se ejecutó EXPLAIN ni benchmark. Las consultas de igualdad por event_id y por (run_id,event_sequence) ya disponen de índices.

**Propuesta técnica:** Antes de añadir índices, estudiar una ruta tipada para esquema E10 conocido: event_id IS NOT NULL AND event_sequence IS NOT NULL, ORDER BY event_sequence; legacy event_id IS NULL con ORDER BY kind,phase,record_key. Mantener fallback separado para esquema anterior y la validación estricta de _decode. No cambiar _decode, hash ni secuencia. Comprobar que no se ocultan filas corruptas al filtrar metadatos incompletos; la optimización sólo es válida con CHECK validado.

**Compatibilidad:** La conversión actual es deliberada para columnas ausentes en esquema antiguo. La ruta rápida debe quedar condicionada a capacidades verificadas, sin DDL automático ni eliminación del fallback.

**Riesgo:** Medio: romper compatibilidad anterior o dejar de detectar corrupción; riesgo científico indirecto si cambian los bytes/proyección de hash.

**Migración:** False — Primero reescritura compatible; usar índices actuales, no crear otro índice por run_id.

**Pruebas requeridas para implementar (no ejecutadas):**

- Equivalencia de ambas familias, orden, canonical JSON y records_hash con payloads grandes.
- Esquema anterior sin columnas E10, esquema actual, datos corruptos y lectura tras cierre.
- Reintento, gap, carrera, owner perdido y commit fallido; futuros planes y medición sin ciencia en entorno autorizado.

### E10.10.3-F04 — PERFORMANCE_CANDIDATE

**Ordenamientos Top-N de frontend sin índice con el contrato completo**

**Objetos:** `runs`, `vw_run_dashboard`, `TRAINING_SUMMARIES_SQL`.

**Evidencia:**

- [backend_api/app/services/training_summaries.py:13](../../backend_api/app/services/training_summaries.py#L13) — `TRAINING_SUMMARIES_SQL =`
- [backend_api/app/routes/runs.py:290](../../backend_api/app/routes/runs.py#L290) — `def list_runs(`
- `docs/audits/e10_10_1_baseline.json` → `views` (vw_run_dashboard)
- `docs/audits/e10_10_1_baseline.json` → `indexes` (idx_runs_started_at, idx_runs_run_type, idx_run_metrics_run_id)

**Impacto:** TRAIN summaries ya acota la página antes de agregar, pero filtra run_type y ordena started_at DESC NULLS LAST,created_at DESC,id sin índice de ese orden completo. /runs aplica LIMIT sobre una vista agregada y otro orden (run_name DESC,started_at DESC NULLS LAST); un único índice no resuelve automáticamente ambas rutas. Cero runs: no hay latencia demostrada.

**Reproducibilidad:** Contrastar los dos ORDER BY y la vista agrupada con el catálogo actual. Sin plan no se afirma que el agregado procese todas las métricas siempre.

**Propuesta técnica:** Medir primero TRAIN summaries; candidato condicionado: B-tree parcial sobre (started_at DESC NULLS LAST, created_at DESC, id) WHERE run_type=training. Para /runs estudiar paginar IDs de runs antes del agregado, conservando semántica y desempates, antes de proponer otro índice. No materializar vistas ni indexar JSONB de resultados sólo por leerlo.

**Compatibilidad:** No cambia datos científicos; preservar orden, límite 1–500, contratos frontend y precedencia de training_results. Índice nuevo requiere head compatible y vía transaccional acordada.

**Riesgo:** Bajo-medio: coste de almacenamiento/WAL por run creado, no por cada evento; una reescritura de vista tiene riesgo de contrato y empates.

**Migración:** conditional — Sólo para el índice si la medición posterior justifica su coste; la reescritura de lectura puede ser sólo código.

**Pruebas requeridas para implementar (no ejecutadas):**

- Páginas con started_at NULL, fechas iguales y varios tipos de run.
- Equivalencia de métricas/orden y límite; consulta de validación sigue marcada val.
- Comparación de planes y latencias con cardinalidad representativa autorizada; nunca medir creando campañas reales.

### E10.10.3-F05 — PERFORMANCE_CANDIDATE

**Consulta histórica de publicaciones no coincide con el índice de candidatas activas**

**Objetos:** `stage2_model_publications`.

**Evidencia:**

- [malaria_dl_local_project/src/malaria_dl/governance/services/stage2_publication_service.py:73](../../malaria_dl_local_project/src/malaria_dl/governance/services/stage2_publication_service.py#L73) — `def status(`
- [malaria_dl_local_project/src/malaria_dl/governance/services/stage2_publication_service.py:211](../../malaria_dl_local_project/src/malaria_dl/governance/services/stage2_publication_service.py#L211) — `def models(`
- `docs/audits/e10_10_1_baseline.json` → `indexes` (idx_stage2_publication_candidates, uq_stage2_publication_active_version)

**Impacto:** models() filtra datasource/scope/is_active y ordena published_at: existe índice adecuado. status() pide activas e inactivas por model_version_id/scope y orden is_active DESC,updated_at DESC; el UNIQUE parcial no cubre todas las filas y el índice de candidatas comienza por datasource. Volumen y frecuencia bajos hoy (cero filas); prioridad baja.

**Reproducibilidad:** SQL exacto en status/models comparado con predicados/columnas. No se ha medido que sea lento.

**Propuesta técnica:** Si se acredita historial suficiente y lectura frecuente, considerar (model_version_id,scope,is_active DESC,updated_at DESC). No crear ahora; evitar ampliar índices del camino TRAIN. La búsqueda por checkpoint_artifact_id en model_versions ya dispone de índices.

**Compatibilidad:** No cambia elegibilidad ni política de publicación. Conservar UNIQUE parcial y FK compuestas existentes.

**Riesgo:** Bajo: almacenamiento y mantenimiento al publicar/reactivar; el beneficio con pocas publicaciones puede ser nulo.

**Migración:** conditional — Sólo si se selecciona el índice tras medición.

**Pruebas requeridas para implementar (no ejecutadas):**

- Varias publicaciones activas/inactivas por versión y empate temporal.
- Regresión de publish/status/models/reactivate/deactivate en fixtures; comparación de planes con datos representativos.

### E10.10.3-F06 — PERFORMANCE_CANDIDATE

**Cuatro pares tienen cobertura por prefijo, sin redundancia económica demostrada**

**Objetos:** `idx_artifacts_artifact_type`, `idx_artifacts_type_path`, `idx_predictions_case_type`, `idx_predictions_case_type_run`, `idx_runs_run_type`, `idx_runs_inference_script`, `idx_training_history_run_id`, `idx_training_history_run_phase_epoch`.

**Evidencia:**

- `docs/audits/e10_10_1_baseline.json` → `indexes` (idx_artifacts_artifact_type, idx_artifacts_type_path, idx_predictions_case_type, idx_predictions_case_type_run, idx_runs_run_type, idx_runs_inference_script, idx_training_history_run_id, idx_training_history_run_phase_epoch)
- [malaria_dl_local_project/src/malaria_dl/persistence/run_repository.py:895](../../malaria_dl_local_project/src/malaria_dl/persistence/run_repository.py#L895) — `INSERT INTO predictions`
- [backend_api/app/services/training_summaries.py:36](../../backend_api/app/services/training_summaries.py#L36) — `WHERE training.run_type`

**Impacto:** B-tree no únicos con el mismo prefijo inicial; mantener ambos cuesta escritura/espacio, pero el estrecho puede ser más barato de leer. No se encontraron duplicados físicos exactos entre 389 índices según tabla/método/unique/NULLS/keys/opclasses/collations/options/include/expresión/predicado/reloptions. Las tablas vacías y contadores recientes no prueban desuso.

**Reproducibilidad:** Comparación estructural local del catálogo SELECT; se adjuntan los cuatro pares con definiciones, bytes y contadores. Los índices de UNIQUE/FK compuestas no se confunden con redundancia por tener id como prefijo.

**Propuesta técnica:** Conservar los cuatro hasta medir carga real o fixture autorizada. Si un retiro se justifica, hacerlo de a uno en revisión futura, comprobar planes antes/después y guardar definición inversa. No proponer cuatro DROP como paquete automático.

**Compatibilidad:** Estos índices no son los índices únicos de idempotencia E10. Aun así cualquier nueva revisión necesita contrato de head y bootstrap probado.

**Riesgo:** Medio: regresión de consultas selectivas y coste de reconstrucción en rollback operativo; ganancia durante E10 puede ser pequeña porque training_history/predictions no son el ledger TRAIN por epoch.

**Migración:** conditional — Una migración sólo si se aprueba un retiro individual basado en medición posterior.

**Pruebas requeridas para implementar (no ejecutadas):**

- Lecturas por artifact_type, case_type, run_type y run_id más orden/paginación reales.
- Carga de escrituras pertinente por familia; no extrapolar pipeline histórico al ledger E10.
- No perder índices requeridos por constraints ni soporte de FK; prueba bootstrap.

### E10.10.3-F07 — INTENTIONAL_DESIGN

**Exclusividad, idempotencia y evidencia dual son invariantes complementarias**

**Objetos:** `experiment_execution_gate`, `local_execution_jobs`, `train_execution_records`, `train_execution_sessions`, `campaign_attempts`.

**Evidencia:**

- [malaria_dl_local_project/src/malaria_dl/persistence/result_repository.py:98](../../malaria_dl_local_project/src/malaria_dl/persistence/result_repository.py#L98) — `def acceptance_scope(`
- [malaria_dl_local_project/src/malaria_dl/results/service.py:19](../../malaria_dl_local_project/src/malaria_dl/results/service.py#L19) — `def accept_event(`
- [alembic/versions/20260922_01_result_events.py:27](../../alembic/versions/20260922_01_result_events.py#L27) — `CREATE FUNCTION train_event_guard`
- [malaria_dl_local_project/src/malaria_dl/execution/repository.py:266](../../malaria_dl_local_project/src/malaria_dl/execution/repository.py#L266) — `def finish(`
- [malaria_dl_local_project/src/malaria_dl/execution/artifacts.py:20](../../malaria_dl_local_project/src/malaria_dl/execution/artifacts.py#L20) — `def verify_session(`

**Impacto:** El singleton/owner más advisory lock Docker o job Local retenido aseguran exclusión. UNIQUE de evento global y de secuencia por run, CHECK de envelope, guard de secuencia y autorización antes del duplicado preservan retries. El legacy ledger y RunEvent conviven: remover una familia rompería hashes/verificación. Sesión completed conserva exclusión hasta verified; runs completed no significa verificación de sesión.

**Reproducibilidad:** 12 funciones críticas y 134 constraints comparadas con baseline sin diferencias. Gate 1 fila libre; ningún experimento activo. No se ejercitaron guards con DML ni se acredita de nuevo concurrencia.

**Propuesta técnica:** Conservar predicados, nombres esperados por guard, orden de locks y autorización de duplicados. No añadir índices al singleton ni reemplazar journal SQL por filesystem. Mantener pruebas de concurrencia y hash como regresión de cualquier candidato.

**Compatibilidad:** La FK efectiva es records.run_id → train_execution_sessions.run_id → runs.id. El CHECK no decodifica toda la ciencia; ResultService/_decode/completion completan validación. No tratar esa arquitectura en capas como ausencia de integridad.

**Riesgo:** Alto si se alteran; cero cambios propuestos.

**Migración:** False — Diseño a preservar.

**Pruebas requeridas para implementar (no ejecutadas):**

- Como regresión futura: duplicates/reordered/gaps, commit fallido, pérdida de owner y sesión cerrada.
- Docker frente a Local/assessment, owner fencing, calculated frente a released, ambas familias y completion.

### E10.10.3-F08 — INTENTIONAL_DESIGN

**Los consumidores científicos seleccionan versión y asignaciones; el inventario tiene otro alcance**

**Objetos:** `dataset_split_assignments`, `dataset_split_images`, `dataset_versions`, `dataset_materializations`.

**Evidencia:**

- [malaria_dl_local_project/src/malaria_dl/data/governed_dataset.py:93](../../malaria_dl_local_project/src/malaria_dl/data/governed_dataset.py#L93) — `def _resolve(`
- [malaria_dl_local_project/src/malaria_dl/data/dataset_integrity.py:35](../../malaria_dl_local_project/src/malaria_dl/data/dataset_integrity.py#L35) — `def verify_integrity(`
- [malaria_dl_local_project/src/malaria_dl/assessment/lineage.py:161](../../malaria_dl_local_project/src/malaria_dl/assessment/lineage.py#L161) — `FROM dataset_split_assignments`
- [malaria_dl_local_project/src/malaria_dl/data/registry.py:595](../../malaria_dl_local_project/src/malaria_dl/data/registry.py#L595) — `WHERE dataset_dir = :dataset_dir`
- [backend_api/app/services/governed_datasets.py:52](../../backend_api/app/services/governed_datasets.py#L52) — `def _summary(`

**Impacto:** La ruta de campaña valida contrato FROZEN, materialización sellada y asignaciones por versión. TRAIN usa directorios train/val del snapshot; no consulta 55.116 registros como población científica. El registry legado filtra dataset_dir. UI gobernada usa estadísticas/versión. Inventario /images y selección automática de smoke pueden abarcar ambas raíces, sin demostrar contaminación del entrenamiento.

**Reproducibilidad:** SELECT oficial da 27.558 asignaciones y 22.180/2.693/2.685 por split; dos raíces de 27.558 con FK de versión/materialización NULL. Lectura de código, sin ejecutar resolución física ni rehash de imágenes.

**Propuesta técnica:** Mantener esas fronteras. Documentar/identificar procedencia en selectores de imágenes y corregir sólo el resumen defectuoso F01. No backfill automático de las 55.116 FK NULL, ni NOT NULL global, ni regenerate/fingerprint nuevo.

**Compatibilidad:** No modificar split, paths, selección de checkpoint ni permisos de TEST; las NULL actuales no son huérfanos por FK MATCH SIMPLE.

**Riesgo:** Alto si se fusionan poblaciones; ningún cambio científico propuesto.

**Migración:** False — Preservar el contrato oficial; F01 es de lectura.

**Pruebas requeridas para implementar (no ejecutadas):**

- Regresión de versión explícita y rechazo de otra materialización; constantes científicas intactas.
- UI /api/datasets y fuentes de /api/dataset/images diferenciadas; smoke no contado como universo experimental.

### E10.10.3-F09 — INTENTIONAL_DESIGN

**FK sin índice no implica índice faltante en reservas y recuperación**

**Objetos:** `campaign_members`, `campaign_attempts`, `train_execution_sessions`, `run_lineage`, `model_versions`.

**Evidencia:**

- [malaria_dl_local_project/src/malaria_dl/execution/repository.py:85](../../malaria_dl_local_project/src/malaria_dl/execution/repository.py#L85) — `def claim(`
- [malaria_dl_local_project/src/malaria_dl/campaigns/repository.py:71](../../malaria_dl_local_project/src/malaria_dl/campaigns/repository.py#L71) — `def get(`
- [malaria_dl_local_project/src/malaria_dl/execution/campaign.py:95](../../malaria_dl_local_project/src/malaria_dl/execution/campaign.py#L95) — `def reconcile(`
- `docs/audits/e10_10_1_baseline.json` → `indexes` (campaign_members_campaign_id_position_key, campaign_attempts_member_id_ordinal_key, train_execution_sessions_pkey, uq_run_lineage_parent_child_type)

**Impacto:** Claim usa campaña/estado más orden pending-first; índices campaña/posición y campaña/estado, intento por miembro/ordinal, PK sesión/run y UNIQUE de intento ya cubren accesos de igualdad. El orden booleano puede requerir sort, pero matriz/budget acotados y cero filas no justifican otro índice. Reconcile itera intentos y verifica evidencia/checkpoints: no asumir que el coste es sólo SQL.

**Reproducibilidad:** Cruce consulta–catálogo, no benchmark. Las 79 FK de primera columna y 109 del criterio completo siguen siendo listas de inspección, no plan de 79/109 índices.

**Propuesta técnica:** Conservar diseño. Medir con volumen antes de índice por FK, por booleano pending o covering de snapshots. No quitar UNIQUE compuestos (id,run_id)/(id,training_run_id), necesarios como targets de FK de linaje.

**Compatibilidad:** Mantener presupuesto, orden pending-first, locks y constraint triggers diferibles. No usar SKIP LOCKED ni paralelizar TRAIN como optimización.

**Riesgo:** Alto si se altera orquestación; ningún cambio inmediato.

**Migración:** False — Soporte existente suficiente como hipótesis estática; falta evidencia para ampliarlo.

**Pruebas requeridas para implementar (no ejecutadas):**

- Claim determinista, ordinal/budget, binding diferido y recuperación sin relanzamiento.
- Futuros perfiles separando coste SQL de lectura/verificación de artifacts.

### E10.10.3-F10 — INTEGRITY_IMPROVEMENT

**El preflight de adopción no comprueba los 22 checksums que preserva la política**

**Objetos:** `scripts/db/verify_alembic_adoption.py`, `schema_migrations`.

**Evidencia:**

- [scripts/db/verify_alembic_adoption.py:92](../../scripts/db/verify_alembic_adoption.py#L92) — `SELECT checksum FROM schema_migrations`
- [malaria_dl_local_project/scripts/init_db.py:311](../../malaria_dl_local_project/scripts/init_db.py#L311) — `def execute_pending_sql_file(`
- [scripts/reset/reset3/bootstrap_probe.py:26](../../scripts/reset/reset3/bootstrap_probe.py#L26) — `if p.name=='004_seed.sql':continue`

**Impacto:** Los 22 checksums del ledger vivo coinciden con baseline y archivos actuales; no hay alteración histórica. El preflight productivo sólo exige presencia de 029 y no compara su checksum ni los otros. Un cambio accidental de archivo puede pasar el preflight aunque viole la política de inmutabilidad.

**Reproducibilidad:** Comparación SHA-256 local de las 22 entradas vivas: todas iguales. Lectura del flujo de verify_alembic_adoption; no se modificó un archivo para provocar fallo.

**Propuesta técnica:** Extender la verificación de sólo lectura para comparar todas las entradas registradas con archivos y reportar faltantes/mismatch. Diferenciar números ausentes legítimos y exclusión deliberada de 004_seed: no exigir 29 filas ni registrar archivos automáticamente. Definir cobertura esperada para bootstrap sin alterar ledger.

**Compatibilidad:** Sólo código de preflight y pruebas; preservar los 22 hashes, contenidos SQL 001–029 y metadata histórica. No normalizar/recalcular checksums guardados para aceptar discrepancias.

**Riesgo:** Bajo-medio: falsos bloqueos si se confunden exclusiones históricas con errores. No impacto en filas científicas.

**Migración:** False — Mejora del verificador, no del esquema.

**Pruebas requeridas para implementar (no ejecutadas):**

- 22 coincidencias, archivo ausente, checksum distinto, entradas desconocidas y exclusión 004 explícita.
- Preflight sigue siendo SELECT; ninguna reparación/stamp ni reejecución SQL.

### E10.10.3-F11 — INTENTIONAL_DESIGN

**Una revisión futura exige desplegar compatibilidad E10 deliberadamente**

**Objetos:** `execution/schema.py`, `alembic_version`, `train_event_guard`.

**Evidencia:**

- [malaria_dl_local_project/src/malaria_dl/execution/schema.py:7](../../malaria_dl_local_project/src/malaria_dl/execution/schema.py#L7) — `E10_REVISION = '20260922_01'`
- [malaria_dl_local_project/src/malaria_dl/execution/schema.py:90](../../malaria_dl_local_project/src/malaria_dl/execution/schema.py#L90) — `if versions != [E10_REVISION]`
- [alembic/versions/20260922_01_result_events.py:47](../../alembic/versions/20260922_01_result_events.py#L47) — `def upgrade(`

**Impacto:** Todo head nuevo se rechaza por diseño fail-closed aunque sólo añada índice. El guard también fija nombres, predicados, CHECK, hash de cuerpo y search_path: renombrar o recrear objetos críticos puede bloquear reservas. No es defecto del head vigente.

**Reproducibilidad:** Comparación literal de código y revisión viva 20260922_01; no se alteró el stamp ni se inició reserva.

**Propuesta técnica:** Antes de una migración candidata, definir conjunto explícito de revisiones aprobadas durante transición y mantener la verificación de capacidades. Desplegar verificador compatible antes del nuevo head o usar ventana sin reservas. No aceptar cualquier revisión mayor ni hacer stamp para sortear el guard.

**Compatibilidad:** Bootstrap debe crear SQL histórico sin seed + Alembic hasta nuevo head + guard compatible. Mantener función/cuerpo/search_path si no cambia su contrato.

**Riesgo:** Alto operacional si se ignora; cambio de compatibilidad coordinado, no relajar autenticación ni fencing.

**Migración:** paired_with_candidate — Toda revisión futura debe acompañarse de código/pruebas de compatibilidad; este hallazgo no exige DDL por sí solo.

**Pruebas requeridas para implementar (no ejecutadas):**

- Esquema anterior rechazado, actual aceptado, siguiente aprobado aceptado, desconocido rechazado.
- Índice/constraint/trigger/función dañados siguen rechazados; cero reserva en fallo.

### E10.10.3-F12 — INTENTIONAL_DESIGN

**El preflight transaccional no es una vía genérica para índices concurrentes**

**Objetos:** `scripts/db/validate_alembic_transactionally.py`, `scripts/db/migrate.sh`, `bootstrap SQL + Alembic`.

**Evidencia:**

- [scripts/db/validate_alembic_transactionally.py:65](../../scripts/db/validate_alembic_transactionally.py#L65) — `connection.begin_nested()`
- [scripts/db/validate_alembic_transactionally.py:71](../../scripts/db/validate_alembic_transactionally.py#L71) — `command.upgrade(config, "head")`
- [scripts/db/migrate.sh:11](../../scripts/db/migrate.sh#L11) — `validate_alembic_transactionally.py`
- [alembic/versions/20260726_00_legacy_029_baseline.py:9](../../alembic/versions/20260726_00_legacy_029_baseline.py#L9) — `def upgrade(`

**Impacto:** El ensayo de upgrade comparte conexión/transacción y revierte; CREATE INDEX CONCURRENTLY no pertenece a esa transacción. Un autocommit en una nueva revisión no debe colarse en un verificador que promete rollback. El baseline Alembic vacío tampoco construye los objetos históricos desde cero.

**Reproducibilidad:** Inspección del runner y orden de migrate.sh; no se ejecutó Alembic. La incompatibilidad es de la propuesta futura, no una migración fallida observada.

**Propuesta técnica:** Preferir cambios transaccionales pequeños con ventana acordada si se justifica un candidato. Si el volumen exige concurrente, diseñar primero runner/rehearsal aislado específico y verificación de índices inválidos; no añadir autocommit al runner actual. Probar instalación limpia con fundación histórica explícita, sin seed, y nuevo head.

**Compatibilidad:** No editar revisiones aplicadas ni usar el bootstrap extraordinario reset3 como instalador automático operativo. Toda mejora de bootstrap va en código nuevo separado y con target aislado.

**Riesgo:** Alto si se rompe atomicidad del preflight o se reconstruye public por error; no ejecutado.

**Migración:** False — Decisión de procedimiento previa a DDL candidato.

**Pruebas requeridas para implementar (no ejecutadas):**

- Ensayo aislado conserva versión/esquema tras rollback; no efectos persistentes inesperados.
- Nueva instalación y upgrade desde baseline producen constraints/índices/guards equivalentes.
- Si se autoriza vía concurrente, errores/interrupción/índice inválido y recuperación fuera de la base operativa.

### E10.10.3-F13 — INSUFFICIENT_EVIDENCE

**No hay evidencia para atribuir latencia o fijar un lote de índices**

**Objetos:** `planes SQL`, `estadísticas`, `cargas TRAIN`.

**Evidencia:**

- `docs/audits/e10_10_3_findings.json` → `observations.live.results.cardinalities` (runs, train_execution_records, stage2_model_publications)
- `docs/audits/e10_10_1_baseline.json` → `summary` (fk_without_first_column_index, fk_without_ordered_full_prefix)

**Impacto:** Las tablas críticas de experimentos siguen vacías; pg_stat_statements ausente. Contadores y tamaño no representan campañas. EXPLAIN fue rechazado por revisión automática por contradicción en las restricciones y no se ejecutó. No hay costes de plan, timings, uso de buffers ni velocidad comparativa que permitan certificar mejoras.

**Reproducibilidad:** SELECT de cardinalidades/extensiones/estadísticas; rechazo registrado y colector original no ejecutado. Se ejecutó una alternativa que contiene exclusivamente SELECT.

**Propuesta técnica:** Mantener rendimiento como hipótesis explícita; solicitar en una etapa futura autorización inequívoca para planes SQL y medición en fixtures sin ciencia. No crear índices para corregir supuesta latencia no medida. El defecto de F01 y mejora declarativa F02 se sostienen independientemente.

**Compatibilidad:** No bloquea cierre de diagnóstico con cambios identificados; limita aprobación de optimizaciones. No reabrir ownership ni interpretar objetos ACTIVE como obsoletos.

**Riesgo:** Alto riesgo de sobreindexación si se ignora; ninguna carga propuesta en esta etapa.

**Migración:** False — Falta medir antes de elegir DDL de rendimiento.

**Pruebas requeridas para implementar (no ejecutadas):**

- Comparaciones controladas con cardinalidades/frecuencias documentadas y sin TRAIN/EVALUATE/EXPLAIN científico/TEST clínico.

## Fuentes y cierre

- `docs/audits/e10_10_1_baseline.md` — 1461 líneas, SHA-256 `be6e45d356b5e93e8977a36da8017be9f0a34440f3eb0446f3c8abad637db4d8`.
- `docs/audits/e10_10_1_baseline.json` — 75912 líneas, SHA-256 `ace0f14461eb84ef4d66f438aa571e408403e621e1f8bb5cc4f8fb0014792594`.
- `docs/audits/e10_10_2_schema_ownership.md` — 439 líneas, SHA-256 `f6756de0b4a0542ee088b412e47dac12311922669e06eb47f17524bf738630a5`.
- `docs/audits/e10_10_2_obsolete_candidates.md` — 160 líneas, SHA-256 `4de47ac6c1a036b4d52c0bf3b511dfa69b41403c8e1db93ae054d25af7424b6a`.

Se validaron estructura JSON, IDs/campos de hallazgos, coherencia de conteos, referencias de archivo/línea y checksums. No se ejecutaron suites con fixtures PostgreSQL ni se inició E10.10.4. El bloqueo de EXPLAIN limita la evidencia de rendimiento, pero no impide cerrar esta auditoría con un defecto reproducido y propuestas delimitadas.

**E10.10.3 — AUDITORÍA COMPLETADA, CAMBIOS IDENTIFICADOS.**
