# Etapa 1 — Dataset explícito e integridad del consumo

Fecha: 2026-09-10. **Puerta E1: NO APROBADA — verificación operativa D1–D2 pendiente.**

## 1. Dictamen separado

| Dimensión | Resultado |
|---|---|
| Implementación local DATA-01–03 y guarda DATA-04 | Completada en el árbol de trabajo, con las limitaciones de alcance detalladas abajo |
| Pruebas aisladas | **80 aprobadas**, 2 advertencias de dependencias; no entrenamientos ni evaluaciones científicas |
| Integración PostgreSQL | **NO VERIFICADA**: una prueba opt-in omitida, no se presenta como aprobada |
| Datos operativos y evidencia upstream D1–D2 | **NO VERIFICADOS**: acceso Docker denegado y sin UUID designado recibido para comprobación operativa |
| Puerta E1 | **NO APROBADA**. No se convierte la ausencia de evidencia crítica en aprobación con observaciones |

No se inicia Etapa 2 ni una campaña científica. El dictamen no significa que PostgreSQL esté caído ni que los datos estén dañados: falta comprobarlos en esta sesión.

## 2. Línea base, instrucciones y preservación

- Commit inicial/final funcional: `93845d4ca4a52ec625d304a63d80aff688dc50bf`, rama `main`.
- Árbol inicial limpio (`git status --short` sin salida). No había modificaciones ajenas que alterar. No se hicieron commits.
- Se leyeron el [informe 0A](etapa_0a_pipeline_modelos_2026-09-10.md) y el [contrato 0B](../engineering/etapa_0b_contrato_aceptacion_2026-09-10.md). La copia ya contiene **v1.1**, 28 requisitos, 31 escenarios y nueve puertas, en el commit inicial. No hubo que inventar ni incorporar una revisión faltante.
- 0A SHA-256: `3d3a0c5e9a8797532ec6b5d470fc943dbb177b4f80c6d0e68dfbf618e050ee7b`.
- 0B SHA-256: `6e6a5b5714bf90f3c3fcfe7f3a1836cea55bde588ef749e3ea8020d7adb4872e`.
- No se encontraron AGENTS.md en la búsqueda del repositorio; se conserva la comprobación previa de ancestros. Se respetó [PostgreSQL de instancia única](../engineering/postgresql_docker_single_instance.md): Compose `db:5432`, sin instancia alternativa, sin cambios de servicios o permisos.
- Wrappers conservados: `src/train.py` → `malaria_dl.training.trainer`; `src/evaluate.py` → `malaria_dl.evaluation.evaluator`; `src/explain.py` → `malaria_dl.explainability.pipeline`. Los cambios se hicieron en implementaciones efectivas.
- No se modificaron split, V1_ID, namespaces, hashes aprobados, migraciones, BD operativa, datasets, checkpoints, publicaciones, frontend o backend. La comparación Git de esos ámbitos no mostró cambios. No se instalaron dependencias ni se levantaron servicios.
- Sólo las pruebas generan bytes sintéticos/cachés en directorios temporales. Los nuevos caminos de evidencia no escriben CSV ni JSON laterales. Los escritores legacy ajenos al alcance siguen presentes.

Las referencias cortas de código siguientes son relativas a `malaria_dl_local_project/src/malaria_dl/`; scripts y tests son relativos a `malaria_dl_local_project/`. Se indican símbolos estables además de líneas, ya que pueden desplazarse en revisiones posteriores.

## 3. Cambios de comportamiento

### Identidad y resolución

Antes, TRAIN aceptaba UUID omitido y `resolve_governed_dataset` seleccionaba la versión entrenable más reciente. Ahora `normalize_dataset_version_id` (`data/governed_dataset.py:63`) rechaza ausente/vacío/malformado; `dataset_uuid_arg` normaliza la CLI. TRAIN exige el argumento (`training/trainer.py`, `parse_args`) y el resolver programático lo exige independientemente de argparse (`governed_dataset.py`, `resolve_governed_dataset`). No hay fallback por ruta, entorno ni fecha.

`_resolve` (`governed_dataset.py:93`) consulta la versión por UUID, exige FROZEN, valida sello `malaria_patient_split_freeze_v1`, su identidad y los cuatro fingerprints. Busca la materialización **por el UUID exacto del sello**, comprueba pertenencia, READY/PASS y raíz accesible dentro del árbol de datos. Exige últimos checks requeridos PASS bloqueantes y rechaza cualquier check adicional vigente bloqueante FAIL, como el contrato upstream. Una materialización más reciente no sustituye la sellada.

`dataset_read_connection` usa transacción explícita `REPEATABLE READ, READ ONLY`; las lecturas del resolver no ejecutan comandos del split. El listado ML de trainables anterior, sin consumidores en la búsqueda de código, se retiró junto con la selección implícita. El sistema split conserva su API/constantes independientes.

### Integridad independiente

`data/dataset_integrity.py`, `verify_integrity`, verifica:

1. Asignaciones paciente→partición, agrupadas/ordenadas como upstream.
2. Asignaciones de registros, ordenadas por source_record_id.
3. Población fuente: ID, identidad clínica, clase, hash de archivo y hash de píxeles registrados.
4. Identidad clínica: ID, identificador fuente y estado.
5. Cobertura/cardinalidades selladas y correspondencia entre registros/pacientes; ausencia de solapamiento de pacientes.
6. Conjunto exacto de archivos y SHA-256 de bytes contra `source_file_sha256`, incluido en la huella sellada de población. La regla de nombre/prefijo en colisiones reproduce la materialización upstream. Rechaza escapes de raíz y archivos inesperados.

No se crea una nueva referencia esperada. Los fingerprints se comparan con el sello independiente existente; la alteración de bytes con mismo nombre/conteo falla. Si faltan sello, fingerprints, referencia de contenido o cardinalidades acreditadas, se rechaza. El hash de píxeles registrado participa en la huella de población; no se decodifican imágenes para crear otro algoritmo de hash de píxeles. La identidad byte a byte se acredita por SHA-256 del archivo completo.

Reglas canónicas leídas: `malaria_dataset_split_project/src/malaria_split/governance/freeze.py`, `_canonical_digest`/`compute_source_population_fingerprint`/`compute_clinical_identity_fingerprint`; `persistence/split_generation.py`, `_sha256_lines`/`audit_persisted_assignments`; `persistence/materialization.py`, construcción y reconciliación. Asignaciones usan join por salto de línea **sin salto final**; población/identidad incluyen salto final por fila. La prueba de paridad carga únicamente las funciones puras por AST y contrasta sus salidas, sin importar inicialización/escritores del split.

### Lotes

`run_train_all_models.py`, `main`, llama una vez a `verify_dataset_for_execution`, obtiene una evidencia persistida y pasa UUID y `--expected-dataset-evidence-id` a todas las combinaciones. Cada hijo verifica de nuevo el contenido y exige igualdad de identidad, materialización, raíz, fingerprints y conteos con la evidencia fijada. No se implementó campaign_id ni persistencia de campañas.

`run_evaluate_all_trainings.py` y `run_explain_all_trainings.py` exigen ámbito UUID, filtran SQL por igualdad y validan también cada fila y cada snapshot padre antes de lanzar. Sus lecturas de inventario usan `BEGIN READ ONLY`. Los comandos hijos reciben UUID/evidencia del lote. Se conservó la selección existente de model_version por fecha en el inventario: **no se presenta como corregida**; corresponde a Etapa 6.

TRAIN dry-run sólo valida sintaxis y genera comandos; imprime **integridad NO VERIFICADA**, sin BD ni subprocesos. EVALUATE/EXPLAIN dry-run consulta inventario read-only filtrado, sin verificar bytes ni ejecutar hijos. Sin acceso no puede generar inventario ni afirmar preflight aprobado.

### Herencia y compatibilidad de rutas

`training_dataset_metadata` (`governed_dataset.py:241`) recupera UUID de runs y snapshot acreditado de execution_parameters/parameters; exige campos y consistencia entre fuentes. No rellena IDs ni elige datasets nuevos para un TRAIN histórico. `assert_run_dataset_snapshot_unchanged` contrasta UUID, materialización y fingerprints, además de raíz/conteos cuando figuran en evidencia previa.

EVALUATE/EXPLAIN usan `verify_dataset_for_execution` antes de predict/generar resultados. Sin override heredan identidad; UUID equivalente normalizado se acepta; uno distinto falla. TRAIN sin snapshot/identidad acreditada no puede originar una nueva ejecución gobernada. Las consultas de resultados históricos no fueron modificadas.

`add_data_source_args(..., governed=True)` en `data/loaders.py` deja `dataset_dir=None` por defecto únicamente para estos entrypoints; se resuelve la raíz del sello. Un `--dataset-dir` explícito es una aserción y debe coincidir exactamente; una ruta legacy contradictoria falla. `tfds` no sustituye una fuente gobernada. Otros consumidores del helper mantienen sus defaults anteriores.

Se identificó además `calibration_cli.py` como consumidor de `resolve_training_run_dataset(training_run_id)`: con TRAIN explícito queda sujeto al endurecimiento de acreditación del padre. No se modificó su motor ni sus escritores; sus rutas standalone sin TRAIN y otros flujos legacy no son el cierre completo de EVALUATE/EXPLAIN ni del protocolo de calibración.

## 4. TRACE-04: persistencia de evidencia nueva

`persistence/dataset_evidence.py` implementa:

- `verify_dataset_for_execution`: resolución/verificación y comparación con padre/evidencia fijada.
- `persist_dataset_evidence`: inserción atómica en `audit_events`, commit y lectura posterior de igualdad; cualquier error produce `DATASET_EVIDENCE_PERSISTENCE_FAILED`, sin exponer mensajes de driver ni usar fallback de archivos.
- `read_dataset_evidence`: recuperación sólo del tipo `ml.dataset_verification`.
- `bind_dataset_evidence_to_run`: vincula por `runs.metadata.dataset_verification_evidence_id` y UUID del dataset; falla si no existe run válido o no se pudo persistir. Se invoca antes de fit/predict cuando hay tracking.

Se reutiliza la tabla append-only definida por `alembic/versions/20260726_02_audit_events.py` y JSONB de runs. No se introdujo migración. Su **disponibilidad operativa no está verificada**; si falta, el código falla cerrado.

La evidencia contiene versión `ml_dataset_integrity_v1`, consumidor, snapshot, cuatro fingerprints, conteos, estado y vínculo con TRAIN/evidencia del lote cuando corresponde. Los rechazos se registran con motivo; si falla verificación de integridad se conservan también referencias selladas esperadas disponibles, sin datos de pacientes. Argumentos sintácticamente inválidos fallan antes de conectar. Si BD no funciona, no se puede registrar el rechazo: la operación se bloquea sin archivo sustituto.

Incluso sin `--track-db`, un flujo nuevo requiere persistir esta auditoría. Sin tracking no se afirma que exista un TRAIN en runs: queda un evento de esa invocación. Con tracking se exige enlace al run. La persistencia de historia por época, predicciones y métricas legacy no se migró; su eliminación de CSV corresponde a etapas posteriores. La nueva evidencia no depende de esos archivos. Imágenes/checkpoints siguen siendo artefactos, no columnas binarias.

Los eventos de preflight son auditorías distintas por invocación/reverificación; no son miembros ni reintentos de una campaña. El requisito de no duplicar métricas/predicciones se cerrará en sus etapas: aquí no se agregan esos escritores.

## 5. Matriz contractual y evidencia

| Requisito / escenarios | Cambio y evidencia de código | Pruebas ejecutadas relevantes | Límite de aceptación |
|---|---|---|---|
| DATA-01 / S01 | normalize_dataset_version_id, parse_args TRAIN y tres lotes, build_train_command; sin selección implícita | test_resolver_rejects_before_database; test_programmatic_execution_missing_id_is_early; test_train_public_entry_rejects_before_model_or_images; test_batch_cli_requires_uuid; test_batch_resolves_once_propagates_pin_to_twelve; test_dry_run_does_not_accredit_or_connect | Aprobado con fixtures; lote operativo no ejecutado |
| DATA-02 / S02 | _resolve: estado, sello, materialización exacta, checks vigentes y raíz | test_exact_seal_and_upstream_hashing; test_rejected_contracts; test_additional_blocking_failure_is_not_ignored | Trainability/materialización reales NV |
| DATA-03 / S20 | verify_integrity y persist_dataset_evidence; hashes contra sello/bytes fuente | test_each_fingerprint_is_recomputed; test_changed_bytes_same_name_and_count_rejected; test_missing_or_unexpected_file_rejected; test_byte_exact_canonical_rules_match_upstream_sources; test_rejection_evidence_retains_sealed_reference | No se verificaron hashes/población operativa; D2 pendiente |
| DATA-04 guarda / S03 | training_dataset_metadata, verify_dataset_for_execution y entrypoints; lotes filtrados; validate_dataset_location | test_parent_inheritance_normalized_and_pinned; test_historical_unaccredited_blocked_without_backfill; test_consumers_reject_before_inference; test_path_and_source_cannot_replace_governed_dataset; test_inventory_requires_scope_before_connect; test_inventory_filters_and_rejects_wrong_training; test_batch_pin_cannot_substitute_materialization | Cierre de checkpoint/model_version y outputs en E6 |
| TRACE-04 aplicable / S30–S31 | audit_events y vínculo metadata, no CSV ni sidecar | test_evidence_round_trip_without_sidecars; test_failed_persistence_never_returns_verified; test_run_link_failure_is_fatal; nuevas pruebas revisadas sin escritor CSV | Round-trip de repositorio simulado aprobado; integración PostgreSQL omitida, NO VERIFICADA. No equivale al cierre global S30–S31 de épocas/predicciones |

Todos los nombres de pruebas de esta matriz están en `tests/test_dataset_stage1.py`. Las pruebas originales de comandos, snapshots, argumentos, epochs y finalización completan la regresión del conjunto indicado abajo. Los doubles simulan respuestas de conexión; **no son una BD operativa alternativa**.

## 6. Pruebas: comandos y resultados reales

Antes de ejecutar se inspeccionaron las condiciones de aislamiento. Tests nuevos usan datos sintéticos, temporales y conexiones mockeadas. `test_train_integration.py`, pese al nombre, sólo valida argumentos/tipos de ejecución. La prueba de finalización EVALUATE mockea modelo, predicciones, resultados y tracking; no evalúa dataset real ni escribe métricas CSV. No se ejecutó la suite completa ni tests que hagan fit real.

Directorio: `malaria_dl_local_project`.

```sh
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/etapa1-mpl \
XDG_CACHE_HOME=/private/tmp/etapa1-cache .venv/bin/python -B -m pytest \
  -q -p no:cacheprovider --basetemp=/private/tmp/etapa1-tests \
  tests/test_dataset_stage1.py \
  tests/test_dataset_evidence_postgres.py \
  tests/test_governed_dataset_contract.py \
  tests/test_run_evaluate_all_trainings.py \
  tests/test_run_explain_all_trainings.py \
  tests/test_train_checkpoint_policy_args.py \
  tests/test_max_epochs_config.py \
  tests/test_train_integration.py \
  tests/test_evaluation_finalization_integration.py
```

Resultado final: **80 passed, 1 skipped, 2 warnings in 2.79s**, exit0. Las dos advertencias corresponden a tipos protobuf/google._upb con metaclass deprecada; también se imprimió ausencia de GPU soportada. No son fallos de dataset ni acreditan rendimiento/aptitud clínica.

La prueba omitida `tests/test_dataset_evidence_postgres.py` exige `RUN_STAGE1_POSTGRES_TESTS=1` dentro del entorno Compose autorizado. Tiene transacción externa con rollback obligatorio y savepoints internos; escribe sólo evento audit sintético y comprueba que desapareció al revertir. No se habilitó porque no hay acceso. No toca registros de dataset/run reales ni crea otra base. Su diseño de aislamiento fue inspeccionado; **su ejecución y compatibilidad con el esquema instalado no fueron verificadas**.

También pasaron: parseo AST de todos los Python modificados/nuevos, `git diff --check` y `ruff check --select F --no-cache` sobre los módulos nuevos/resolver/tests nuevos. Se usó Ruff ya instalado, sin instalar herramientas. Formato sólo en archivos nuevos y resolver modificado.

`tests/test_max_epochs_main_smoke.py` se ajustó a UUID explícito y al nuevo símbolo de preflight, preservando su doble de modelo, pero **no se ejecutó**: ejercita escritores legacy de archivos que no hacen falta para validar esta etapa. No se afirma que todas las suites del repositorio pasen.

## 7. Comprobación operativa

Se ejecutó únicamente el descubrimiento read-only de servicios:

```sh
docker compose ps --status running --services
```

Resultado: `permission denied while trying to connect to the docker API` en el socket local. No se escaló, cambió permiso ni arrancó servicio. No se ejecutó consulta SQL operativa; no se imprimieron credenciales ni URLs con credenciales.

Se solicitó al usuario el UUID designado para la comprobación operativa y se continuó trabajo local independiente. Al cierre no se había recibido ese UUID. No se eligió una versión por fecha ni se adoptó el UUID que aparece en documentos como si fuera una designación actual.

Pendientes: instancia/esquema, versión explicitamente designada, checks vigentes, materialización sellada, las cuatro huellas y contenido real, asociaciones de TRAIN, persistencia y lectura posterior en el esquema operativo. La documentación y las fixtures no satisfacen D1–D2. Para cerrarlos: lectura explícita READ ONLY usando la instancia autorizada y UUID designado; integración de escritura sólo con aislamiento conforme al contrato del proyecto.

## 8. Estado final y archivos

HEAD permanece `93845d4ca4a52ec625d304a63d80aff688dc50bf`. No hay commits del agente. Archivos versionados modificados:

- README y `docs/training_evaluation_inference_workflow.md` del proyecto ML: uso y precedencia de dataset.
- `run_train_all_models.py`, `run_evaluate_all_trainings.py`, `run_explain_all_trainings.py`: ámbito explícito, preflight/pin y dry-run honesto.
- `data/governed_dataset.py`, `data/loaders.py`: UUID/resolución/herencia/integridad y defaults específicos de entradas gobernadas.
- `training/trainer.py`, `evaluation/evaluator.py`, `explainability/pipeline.py`: guardas y vínculo obligatorio de evidencia.
- Tests existentes: `test_train_checkpoint_policy_args.py`, `test_max_epochs_config.py`, `test_train_integration.py`, `test_max_epochs_main_smoke.py`, `test_evaluation_finalization_integration.py`: fixtures ajustadas al contrato, sin debilitar las nuevas guardas productivas.

Archivos nuevos:

- `data/dataset_integrity.py`, `persistence/dataset_evidence.py`.
- `tests/test_dataset_stage1.py`, `tests/test_dataset_evidence_postgres.py`.
- [Guía de uso](../../malaria_dl_local_project/docs/dataset_explicit_contract.md).
- Este informe nuevo; no se sobrescribió 0A ni 0B.

Las rutas del listado de módulos siguen la convención de §2. El estado final contiene únicamente estos cambios de código/pruebas/documentación. No se usó reset, limpieza, seed ni migración.

## 9. Límites y riesgos remanentes

- La verificación de contenido es de preflight; presupone almacenamiento inmutable durante consumo. No se implementaron locks de filesystem contra modificación externa después del hash. Se revalida por proceso consumidor; la garantía no equivale a snapshot de volumen/WORM.
- Históricos sin materialización/fingerprints completos se bloquean para nueva ejecución gobernada. No se inventa un vínculo retroactivo. Raíces distintas respecto de evidencia previa se rechazan incluso si parecen copias idénticas; la portabilidad de snapshots necesita evidencia explícita, no sustitución silenciosa.
- Recuperación integral del ciclo de ejecución y estados de runs interrumpidos es E5. Un fallo al vincular evidencia impide fit/predict; no se ha reescrito todo el manejador legacy de estados o safe_track.
- Elección reciente/ambigüedad de model_version y reutilización/sobrescritura de salidas EVALUATE/EXPLAIN siguen pendientes de E6 (0A-03/04/16). Esta guarda protege dataset, no certifica todo el linaje de artefactos.
- Registro/adaptadores, VGG16 y parámetros efectivos E2–E3, campañas E4–E5, protocolo/TEST/comparador E7, ensembles E8 y publicación E9 no se implementaron. No se promete mejora clínica ni se cambia selección manual.
- TRACE-04 de esta etapa se limita a evidencia de integridad en BD. CSV/JSON legacy del motor de resultados siguen pendientes; no se afirma que el pipeline completo opere ya sin CSV.

**Conclusión:** implementación local y pruebas aisladas completadas; integración/operación NO VERIFICADAS; **E1 NO APROBADA** hasta comprobar D1–D2 y persistencia real. No se inicia la siguiente etapa.
