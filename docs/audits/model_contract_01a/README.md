# CAPSTONE-MODEL-CONTRACT-01A

Fecha: 2026-10-27. Estado: **APROBADO para el contrato y la base PostgreSQL actual**.

Rama `main`. Había cambios locales previos de BiomedCLIP, entrenamiento y campañas; se conservaron. No se hizo commit. La lista exhaustiva de archivos de esta intervención está en [modified_files.txt](modified_files.txt).

## Cambios

| Componente / archivo | Resultado |
| --- | --- |
| `malaria_dl_local_project/src/malaria_dl/execution/repository.py` | `project_runtime()` deja de escribir las dos columnas y elimina sus bindings. Conserva JSONB, hardware, transacción y cercado de eventos duplicados. Un objeto vacío no sustituye evidencia existente. |
| `malaria_dl_local_project/src/malaria_dl/persistence/run_repository.py` | `start_run()` elimina columnas y bindings. Copia los parámetros sin mutar al llamador y conserva un snapshot explícito del ejecutor. En ausencia de evidencia captura el proceso actual, con versiones observadas de distribuciones instaladas; TensorFlow es opcional. Mantiene Python, plataforma y GPU. |
| `malaria_dl_local_project/src/malaria_dl/governance/services/prepare_release_service.py` | Lee JSONB y resuelve framework desde versión/modelo/metadatos, con inferencia Keras solo para archivo `.keras`. Keras precede a TensorFlow; PyTorch y OpenCLIP resuelven sus propios paquetes. Sin evidencia devuelve `None`. La creación de versión ya no inventa framework Keras. |
| `malaria_dl_local_project/db/init/001_schema.sql` | Elimina las dos columnas del esquema de inicialización. |
| `malaria_dl_local_project/db/init/027_model_governance_backfill_constraints.sql` | Lee versiones de JSONB según framework efectivo. No se ejecutó este backfill sobre datos históricos. |
| `alembic_v2/baseline/03_tables.sql`, `catalog_manifest.json` | Elimina columnas y actualiza declaración, hash del recurso, offsets y hashes de sus sentencias. |
| Cuatro pruebas solicitadas y `test_runtime_environment_contract.py` | Aserciones JSONB, procedencia del ejecutor, ausencia de TensorFlow, versiones por framework y persistencia real con rollback. Fixtures incorporan GPU y tablas de proyección actuales. Se elimina la exigencia obsoleta de una revisión Alembic exacta; se mantienen comprobaciones estructurales. Las pruebas de TRAIN usan ciencia sintética y permiten CPU únicamente dentro del test. |

El consumidor de `context.framework_version` pasa el dato a `create_model_version`; no hay reinterpretación posterior como versión TensorFlow. Los caminos de campañas siguen registrando el entorno observado por el worker y el evento de inicio, no el entorno de planificación. No se cambió entrenamiento, selección de checkpoints ni reglas científicas de publicación.

## Auditoría y preservación

La base principal es `malaria_experiments` del servicio `capstone_db`. No se modificó el contenedor auxiliar de BiomedCLIP.

- 23 RUNs antes y después; 11 tenían ambas columnas históricas no nulas, sin discrepancias con JSONB.
- Diferencia respecto de la evidencia inicial: la consulta global de versiones JSONB devuelve **23**, no 11. Los otros 12 RUNs también contienen `2.17.1` y `3.15.1`. No se corrigieron ni reorganizaron registros para forzar un conteo de 11.
- [historical_11.jsonl](historical_11.jsonl) identifica los 11 originales; [history_result.txt](history_result.txt) confirma igualdad íntegra de sus objetos runtime, además de ambas versiones.
- La huella de las 23 filas completas, descontando exclusivamente las columnas eliminadas, es idéntica: `ea2086a62d8817b7d65cc2c31f6ba448`.
- Los 22 artefactos y la única model_version conservan conteos y huellas. No se escribieron checkpoints ni artefactos científicos históricos.
- `pg_depend` no encontró objetos dependientes de las columnas. Se revisaron también funciones/procedimientos, vistas, vistas materializadas, triggers, constraints, índices y reglas: cero referencias. Véanse [audit_before.sql](audit_before.sql) y [before.txt](before.txt).
- La búsqueda transversal de código operativo Python, SQL, backend, frontend, scripts y configuración no deja lecturas/escrituras de las columnas. Permanecen nombres internos legítimos en `_tensorflow_environment()` y aserciones negativas en pruebas. Documentación histórica, backups, archivos `.keras` y dependencias externas no fueron reescritos.

## Respaldo y DDL

Respaldo previo completo en formato custom: `backups/model_contract_01a/before.dump`, aproximadamente 502 MB. `pg_dump` finalizó correctamente y `pg_restore -l` verificó su catálogo; no se efectuó una restauración completa.

SHA-256: `88f628f779b98ac18ed24a9b919218d23ecc3b4d9dc3254e63fbe1e7adfbb732`.

Se ejecutó [drop_columns.sql](drop_columns.sql): transacción, bloqueo de tabla, repetición de la comprobación de versiones, `DROP COLUMN` sin `CASCADE` y `COMMIT`. [ddl_result.txt](ddl_result.txt) registra el éxito. [after.txt](after.txt) confirma cero columnas y evidencia histórica preservada. No se ejecutó ninguna migración de registros ni se crearon columnas.

## Pruebas y verificación

Comando reproducible desde la raíz:

```sh
malaria_dl_local_project/.venv-local-train/bin/python docs/audits/model_contract_01a/run_tests.py
malaria_dl_local_project/.venv-local-train/bin/python docs/audits/model_contract_01a/verify_history.py
```

El runner obtiene credenciales de `.env` sin imprimirlas, configura acceso local al mismo PostgreSQL y habilita las pruebas opt-in. Las pruebas usan esquemas aislados o transacciones externas con rollback; las verificaciones posteriores confirman que no alteraron los RUNs históricos.

Suites: `test_model_execution_tracking.py`, `test_max_epochs_tracking.py`, `test_prepare_model_release_service.py`, `test_campaigns_postgres.py`, `test_train_run_persistence.py`, `test_runtime_environment_contract.py`.

- Antes del DDL: **107 passed**, 2 warnings, 27.47 s ([evidencia](tests_before_ddl.txt)).
- Después del DDL: **107 passed**, 2 warnings, 27.75 s ([evidencia](tests.txt)).
- Persistencia real de RUN nuevo y lectura de contextos de publicaciones verificadas con SQL PostgreSQL; rollback posterior. No se publicó ni modificó ningún modelo.
- Las dos advertencias son de deprecación de protobuf/Python, sin errores de columnas inexistentes.
- `git diff --check`: correcto.
- Backend recargó los módulos modificados automáticamente; `/health` correcto y `/ready` confirma base y almacenamiento listos.

Las primeras ejecuciones evidenciaron configuración local incorrecta, falta de permisos del rol runtime para crear esquemas de prueba y fixtures desactualizados. Se resolvió usando el acceso administrador existente exclusivamente para las pruebas aisladas y actualizando los fixtures; no se ampliaron privilegios del backend.

## Limitación previa fuera del contrato

El manifiesto de instalación `alembic_v2` ya tenía hashes inconsistentes en `HEAD` para cinco recursos. Se alineó `03_tables.sql`, afectado por esta tarea, incluyendo todas sus sentencias. Persisten discrepancias previas en `05_keys.sql`, `06_constraints.sql`, `07_indexes.sql` y `10_privileges.sql`; evidencia en [preexisting_baseline_checksums.json](preexisting_baseline_checksums.json). Por ello **no se certifica una instalación nueva completa mediante el loader de ese baseline**. No afecta la eliminación aplicada ni la ejecución probada contra la base actual. No se modificaron esos cuatro recursos ni se ocultó el fallo de integridad.

No se ejecutó entrenamiento científico real ni inferencia OpenCLIP: esta intervención verifica su contrato de versiones, no incorpora esa funcionalidad.
