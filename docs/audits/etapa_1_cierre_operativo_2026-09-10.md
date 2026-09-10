# Etapa 1 — Comprobación operativa de D1–D2

Fecha: 2026-09-10. **Dictamen E1: NO APROBADA.**

Este complemento conserva el [informe E1 original](etapa_1_dataset_explicito_2026-09-10.md). La designación explícita por el usuario del UUID **d8c0cab5-09dd-597f-9de7-7ca01aee2ec2** resuelve la falta de identidad autorizada registrada anteriormente; no acredita su existencia, integridad ni persistencia. No se seleccionó otra versión.

## Revisión y preservación

- HEAD comprobado: `54c9d9568f04ca7a5f15582b784375b07a8463e2`, rama `main`; árbol inicial limpio (`git status --short` sin salida).
- Se revisaron el contrato [0B v1.1](../engineering/etapa_0b_contrato_aceptacion_2026-09-10.md), especialmente DATA-01–04, TRACE-04, puerta E1 y D1–D2; el informe E1; y la instrucción [PostgreSQL Docker, instancia única](../engineering/postgresql_docker_single_instance.md). No se encontraron AGENTS.md en el repositorio ni sus ancestros.
- SHA-256 del informe E1 conservado: `a6b9af298744d3f4b4b5b9193abcdaf86765d5522a51a58cc46da438bff0b39b`.
- Único cambio de esta comprobación: este informe. No se modificó código funcional, configuración, servicios, permisos, migraciones ni datos. No se realizaron commits.

## Resultados separados

| Comprobación | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|
| D1: acceso Compose | API Docker accesible e inventario de servicios | Acceso al socket denegado, salida 1 | NO VERIFICADA |
| D1: base, esquema y migraciones | Identidad efectiva, estructuras E1 y revisiones instaladas comprobadas mediante lecturas | No se pudo entrar al entorno autorizado; no se ejecutó SQL | NO VERIFICADA |
| D2: UUID designado | Existente, FROZEN, entrenable, checks vigentes PASS sin fallo bloqueante | Resolver operativo no ejecutado | NO VERIFICADA |
| D2: sello y contenido | Materialización exacta READY/PASS, pertenencia, raíz/archivos accesibles, huellas y conteos iguales al sello, sin solapamiento de pacientes | Sin lecturas operativas de BD ni archivos del dataset | NO VERIFICADA |
| Integración de evidencia PostgreSQL | Inserción sintética, lectura idéntica, fallo por duplicado aislado, ausencia tras rollback | Prueba inspeccionada, no ejecutada por falta de acceso | NO VERIFICADA |

Comando efectivamente ejecutado desde la raíz del repositorio:

```sh
docker compose ps --status running --services
```

Error sanitizado (sin credenciales; ruta personal sustituida):

```text
permission denied while trying to connect to the docker API at unix:///<usuario>/.docker/run/docker.sock
```

El error prueba una restricción de acceso de esta sesión, **no que PostgreSQL esté caído**. No se solicitó cambiar permisos, no se levantaron servicios, no se instaló otra BD y no se intentó eludir la restricción. `db:5432`, servicio `db` y contenedor `capstone_db` son referencias contractuales, no identidad operativa comprobada. Nombre efectivo de la base, esquema, versión del servidor y revisión instalada siguen desconocidos.

## Revisión estática de los verificadores y del aislamiento

Rutas siguientes relativas a `malaria_dl_local_project/`:

- `src/malaria_dl/data/governed_dataset.py`: `resolve_governed_dataset` usa `dataset_read_connection`, que abre una transacción explícita `REPEATABLE READ, READ ONLY`. Resuelve exclusivamente el UUID recibido, exige FROZEN, sello v1 e identidad coincidente, materialización exacta del sello y pertenencia, READY/PASS, los doce checks requeridos vigentes y ausencia de cualquier check bloqueante FAIL. Comprueba raíz antes de delegar la integridad.
- `src/malaria_dl/data/dataset_integrity.py`: compara las cuatro huellas con referencias selladas; verifica asignaciones, cobertura, población, identidad clínica, cardinalidades y no solapamiento por paciente. Contrasta conjunto exacto de archivos y SHA-256 de bytes con referencias incluidas en la población sellada. Mantiene las reglas canónicas E1 de ordenación, saltos de línea y nombres en colisiones. No sustituye referencias aprobadas ni regenera split.
- `src/malaria_dl/persistence/dataset_evidence.py`: `verify_dataset_for_execution` persiste auditoría y **no** debe invocarse como comprobación READ ONLY. No se invocó. El escritor inserta en `audit_events` y compara después el objeto completo leído (`after_state`, `success`, `error_code`). La vinculación con runs pertenece a otro método; no se creó un TRAIN para probarla.
- `tests/test_dataset_evidence_postgres.py`: UUID de evento y UUID de recurso sintéticos; payload sintético. Conserva una conexión real y una transacción externa. Sustituye el engine del escritor por un proxy cuyo `begin` abre `begin_nested()` sobre esa misma conexión: sus commits liberan savepoints, no la transacción externa. La lectura del escritor se sustituye por la misma conexión. El duplicado de PK debe fallar dentro de otro savepoint; luego exige un único evento. `finally` revierte la transacción externa. Una conexión posterior, en READ ONLY, exige cero eventos con ese UUID.
- `alembic/versions/20260726_02_audit_events.py`: declara la tabla y el trigger que prohíbe UPDATE/DELETE. El rollback de INSERT no necesita DELETE. El recurso sintético no referencia por FK un dataset operativo. No se ejecutó esta migración.

La revisión del código respalda el diseño de aislamiento: la prueba no escribe datasets ni runs, ni actualiza o borra eventos existentes. **No hay evidencia empírica de inserción, igualdad o rollback en esta sesión.** Además, el round-trip dentro de savepoints no demuestra visibilidad de un commit durable entre sesiones; la prueba comprueba el escritor dentro del aislamiento solicitado.

Las 80 pruebas aprobadas y una integración omitida son resultados históricos del informe E1. No se repitieron ni se presentan como resultados nuevos; no hubo cambios funcionales que requirieran pruebas específicas.

## Consultas y comandos para reproducir lo pendiente

Lo siguiente **no se ejecutó**. Requiere primero acceso permitido al mismo entorno y comprobar sus mounts/dependencias existentes; no autoriza modificar servicios. La ruta del backend sigue el target `test-ml` del Makefile. No imprimir `DATABASE_URL`, variables de credenciales ni configuración Compose expandida.

D1: ejecutar mediante la conexión del proyecto en el backend, con `dataset_read_connection()`; esta función establece la transacción READ ONLY antes de cualquier SELECT. Consultas de inspección:

```sql
SELECT current_database(), current_schema(), current_schemas(false);
SELECT table_schema, table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name IN (
 'audit_events','runs','dataset_versions','dataset_materializations',
 'dataset_split_validation_checks','dataset_split_assignments',
 'dataset_source_records','dataset_version_sources','clinical_identities',
 'alembic_version')
ORDER BY table_schema, table_name, ordinal_position;
SELECT version_num FROM alembic_version ORDER BY version_num;
```

Contrastar tipos/columnas con las consultas del resolver y del escritor revisados. En runs comprobar al menos `id`, `run_type`, `dataset_version_id`, `execution_parameters`, `parameters`, `metadata`; en audit_events todos los campos del INSERT y de lectura. Inspeccionar también constraints y triggers instalados antes de permitir la prueba. Comparar las revisiones instaladas con el historial Alembic versionado mediante lectura, sin `upgrade`, seeds ni scripts de adopción. La declaración de la migración `20260726_02` no prueba su instalación.

D2, sólo resolver de lectura y UUID designado; muestra únicamente snapshot, conteos y huellas, sin identificadores clínicos:

```sh
docker compose exec -T -w /app/malaria_dl_local_project backend python -B - <<'PY'
import json
from src.malaria_dl.data.governed_dataset import resolve_governed_dataset
snapshot = resolve_governed_dataset('d8c0cab5-09dd-597f-9de7-7ca01aee2ec2')
print(json.dumps(snapshot.metadata(), sort_keys=True))
PY
```

Capturar errores sanitizados sin publicar trazas del driver. Las consultas parametrizadas completas de D2 están en `_resolve` y `verify_integrity`, en la revisión indicada: no sustituirlas por una selección de la última versión ni por un wrapper de auditoría con escrituras.

Integración, sólo después de comprobar D1 y que el esquema operativo conserva las condiciones de aislamiento revisadas:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE1_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_dataset_evidence_postgres.py
```

La variable opt-in queda limitada a esa invocación. Resultado exigido: prueba aprobada, igualdad del payload y campos de estado, conteo 1 antes de revertir y 0 desde la conexión posterior. Si esas aserciones no pueden ejecutarse, rollback permanece NO VERIFICADO. No generar resultados CSV ni usar una BD alternativa.

## Cierre y límites

**E1 NO APROBADA** conforme a la puerta del contrato 0B v1.1: acceso, integridad real y persistencia siguen pendientes. La designación del UUID está resuelta; D1–D2 y la integración no están cerradas. La siguiente comprobación necesita acceso permitido al entorno existente, no otra designación del dataset.

La persistencia integral de épocas/predicciones no se acredita aquí: corresponde al diseño E2/E4 y ejecución E5–E6; comparación E7 y regresión E9. La identidad checkpoint y el cierre de herencia de consumo continúan en sus etapas previstas. No se ejecutaron entrenamientos, fit/predict, evaluaciones científicas, calibraciones ni EXPLAIN. Se conservan datasets, split, imágenes, checkpoints, publicaciones e históricos. La selección de Producción Etapa 2 permanece manual. No se inicia Etapa 2.
