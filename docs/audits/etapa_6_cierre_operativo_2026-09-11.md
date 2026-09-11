# E6 — Cierre técnico y operativo

**Dictamen: APROBADA en el alcance técnico verificado de E6.** Este cierre sustituye los dictámenes pendientes de los informes anteriores, que se conservan como evidencia cronológica. No acredita desempeño clínico ni inicia E7.

## Evidencia final

El usuario aportó, después de instalar la migración mediante el wrapper:

```text
17 passed in 2.31s
```

Corresponde a la suite completa `tests/test_assessment_postgres.py`, con `RUN_STAGE6_POSTGRES_TESTS=1`, dentro del Compose autorizado. Incluye los 16 casos sintéticos y la lectura pública de revisión, seis tablas y ocho triggers E6 habilitados.

Respuesta posterior de `/ready`:

```json
{"status":"ready","components":{"database":"ready","migrations":"ready","storage":"ready"},"version":"0.3.0","environment":"development"}
```

Estos resultados son evidencia de la terminal del usuario; no se presentan como reejecución del asistente. La lectura pública y readiness ahora son posteriores al upgrade, a diferencia del fallo por esquema pendiente registrado anteriormente.

## Revisión y continuidad

- HEAD: `cd5c64d703358797570f5183dd598d93314dc0eb`, rama main; implementación efectiva sin commit, identificada por el manifiesto final E6.
- Verificación local antes del cierre: **61/61 hashes** del manifiesto de migración operativa coincidentes.
- Este turno agrega sólo documentación y manifiesto. No cambia código, pruebas, migraciones ni datos operativos.
- Migración instalada e inmutable: `20260912_02`, sobre `20260912_01`.
- Instalación ya acreditada mediante `make db-migrate`: identidad/adopción válidas, backup custom `capstone_20260911T183223Z.dump`, contenido requerido comprobado con `pg_restore --list`, SHA-256 `adbf49417bd66700ae9d6a10551e36ad47d6382ffd302cdfaa3441b1370ca1bd`, preflight con rollback confirmado y posterior upgrade persistente; current=head.

## Alcance verificado

| Evidencia | Resultado |
|---|---|
| Suite local amplia de implementación E6 y regresiones | 194 passed, 17 skipped, 17 warnings in 19.83s en la revisión documentada antes de corregir concurrencia |
| Suite local afectada por la corrección concurrente | 39 passed, 17 skipped, 7 warnings in 12.31s; no se suman ambos conteos |
| Causa concurrente original reproducida | INSERT, UniqueViolation, SQLSTATE 23505, assessment_identities_structural_hash_key |
| Corrección concurrente en PostgreSQL sintético | Dos conexiones, una identidad, un intento activo y un propietario; 1 passed in 0.55s |
| Suite sintética corregida completa | 16 passed, 1 deselected in 2.29s |
| Migración operativa | Wrapper, backup, preflight/rollback y upgrade a 20260912_02 acreditados |
| Suite PostgreSQL completa posterior al upgrade | **17 passed in 2.31s** |
| Readiness posterior al upgrade | **database, migrations, storage: ready** |

Se conservan la identidad exacta TRAIN/versión/checkpoint, herencia E1, contrato E3, decisión explícita, reserva/reutilización, predicciones y métricas estructuradas, artefactos exclusivos, EXPLAIN con contexto y dominio de score declarados y consumo de campaña desde el intento aceptado. La matriz requisito → cambio → prueba figura en el informe de implementación E6; este cierre completa su evidencia PostgreSQL e instalación pendiente.

## Límites preservados

Las escrituras de prueba se limitan al esquema sintético: rollback/savepoints y limpieza posterior comprobada por el fixture; los casos con conexiones independientes hacen commit sólo de ese esquema. Las tablas padre simplificadas no acreditan todas las constraints operativas por sí solas. La prueba pública comprueba el esquema instalado mediante lectura; no ejecuta inferencia científica.

No se confunde la verificación del rollback con durabilidad ante caída física del host. El backup fue listado/verificado por el wrapper; no se afirma haber ensayado una restauración completa. La recuperación conserva los casos de propietario remoto o indeterminado como rechazo seguro.

Históricos sin evidencia suficiente siguen consultables y no originan nuevas ejecuciones por suposición. Se consume calibración de umbral E5 sobre score bruto; no se importan calibradores históricos de probabilidades ni se inventa linaje. Los endpoints y pantallas históricas conservan su semántica, y la nueva evidencia se consulta mediante `/assessments`.

No hubo TEST operativo, campañas científicas, ajuste de umbral/calibrador con TEST, ranking, publicación o cambios de producción. La gestión del bloqueo final del candidato corresponde a E7; E6 conserva el rechazo seguro y su caso permitido sólo se probó con fixtures. La selección de producción continúa manual.

**E6 APROBADA técnicamente. E7 no iniciada.**
