# E10.10.5A — Resultados de validación estática

## E10.10.5B — resultado posterior a aprobación de Gate A

**Gate B BLOQUEADO.** Se preparó una instancia real PostgreSQL 17.9 aislada y pasó el preflight de infraestructura/servidor antes de provisión SQL. La provisión falló en `CREATE ROLE pg_v2_migrator`: PostgreSQL reserva el prefijo `pg_`. No se creó ninguno de los dos roles ni la base prevista. Se detuvo el contenedor exclusivo después de registrar el estado.

No se ejecutaron baseline, comparación de catálogo, pruebas negativas A-01/E10/VAL/publicación, fallo intermedio de migración, segundo upgrade ni backup/restore. Se consideran **pendientes por bloqueo**, no aprobados. La ausencia observada de alembic_version no certifica rollback de migración. Los 24 tests de A que figuran abajo son evidencia histórica estática, no resultados de B.

Evidencia: [Ruta A](e10_10_5_route_a_results.md), [comandos](e10_10_5b_evidence/commands.jsonl), [estado posterior](e10_10_5b_evidence/blocked_state.json), [diff no evaluado](e10_10_5_catalog_diff.json).

---

**IMPLEMENTACIÓN COMPLETADA — PENDIENTE DE REVISIÓN Y APROBACIÓN.**

Resultados reproducibles: [comandos y salida íntegra](e10_10_5a_commands.json), [catálogo estático](e10_10_5a_static_results.json).

## Resultado final

- **24 pruebas aprobadas:** 19 de catálogo, A-01, integridad de recursos y guardas de identidad; 5 del entorno Alembic y rechazo antes de crear engine/Docker.
- **9 comandos del runner aprobados:** regeneración determinista `--check`, validación estructural, ambas suites, heads/history, lint, formato y compilación Python en memoria.
- **0 pruebas fallidas y 0 omitidas en las suites finales seleccionadas.** Las suites se ejecutaron con sus intérpretes correspondientes, sin sustituir pruebas PostgreSQL por mocks.
- **72 cuerpos PL/pgSQL** analizados sintácticamente; además se analiza el SQL de las funciones LANGUAGE sql. No es compilación ni invocación de funciones en servidor.
- Cotejo estático de **65 funciones**, **77 triggers**, **780 restricciones**, **225 índices independientes** y **27 vistas** conservadas frente a E10.10.1; comprobación de **17 tablas protegidas** y **54 archivos históricos intactos**, incluidos los **22 checksums acreditados** y la exclusión de `004_seed.sql`.
- Raíz/head único **pg_v2_baseline**; 102 tablas de aplicación + alembic_version; 33 vistas; 75 funciones; 95 triggers; 249 FK; 229 índices independientes; una secuencia.

Las pruebas de A-01 recorren combinaciones de split/finalidad/rol en los AST y comprueban ausencia de procedencia, hashes mal formados, ámbitos inválidos, separación de vistas, FK al origen y conservación de external_validation. El evaluador estático implementa sólo ese subconjunto de expresiones, con lógica ternaria explícita; no emula PostgreSQL. Las pruebas de identidad usan diccionarios sintéticos y comprueban rechazo de clúster/OID/roles/puertos/volúmenes incorrectos. No se abrió ninguna conexión.

## Incidencias de desarrollo corregidas

- La revisión final detectó que los atributos de FK inline aparecen como nodos separados en el parser. Se corrigió su traslado para conservar DEFERRABLE INITIALLY DEFERRED en las dos FK de calibración, sin adjuntarlos a NOT NULL. Una prueba específica y una validación de constraints inline residuales cubren el caso.

- El primer cotejo estructural detectó diferencias de offsets del parser y de notación `TRIM`/llamada equivalente. El normalizador elimina únicamente ubicaciones y formato de llamada, conservando nodos, nombres, argumentos y semántica; los cuerpos heredados siguen exactos.
- Una primera prueba negativa buscaba `uq_model_versions_id_training_run` como constraint, cuando es un índice UNIQUE independiente. Se corrigió el caso para retirar el índice real; ahora demuestra rechazo de FK sin target único.
- Se cerró un descriptor de lectura CSV observado por ResourceWarning.
- El primer lint señaló 37 incidencias de estilo/importaciones. Se corrigieron en archivos nuevos y el lint final pasa. La sanitización de errores de driver conserva una captura general explícitamente justificada para no exponer credenciales.

## No ejecutado por límite de etapa

Instalación PostgreSQL 17, validación de catálogo real, invocación de funciones/triggers, pruebas de concurrencia, rollback provocado, segunda instalación, backup/restore, adopción legacy y recorrido TRAIN → E10 → VALIDATION → API → React. Corresponden a B–E y no se consideran aprobados ni certificados por estos resultados.

El parser utilizado es pglast 8.4 con gramática PostgreSQL 18.4. Esta limitación permanece abierta para B. No se ejecutaron tests del repositorio que utilizan PostgreSQL operativo ni entrenamientos reales.
