# E10.10.5C — Pruebas del adaptador

**Resultado: 75 pruebas automatizadas aprobadas; 8 comandos offline aprobados.** Son 50 tests nuevos C y 25 regresiones de A/B. No se ejecutó adopción ni SQL sobre PostgreSQL. Fecha y salida exacta de cada comando: [commands.json](e10_10_5c_evidence/commands.json).

## Cobertura C

| Grupo | Comprobaciones |
| --- | --- |
| Inventario/mapping | 97 tablas fuente, 103 destino, 105 entradas de mapping; PK originales, credenciales sintéticas y 83 tablas de datos KEEP/PROTECTED intactas; revisión Alembic archivada y transición separada; cobertura y orden físico de columnas. |
| Determinismo | Mismo snapshot/bindings produce mismo plan/hash; no modifica entradas; archivo reversible con UUID/Decimal/timestamp y sin colisiones de tags JSON. |
| Checksums/esquema | Cada uno de los 22 hashes incorrectos bloquea; entradas faltantes/duplicadas, head incorrecto, deriva de función y trigger deshabilitado rechazados. |
| Seguridad | Descriptor C no alcanza conexión/inspección; rechazo de rol, URL, query options, puerto y cluster no autorizados; gate ocupado y estados activos rechazados. |
| Configuración | Canonical/hash y configuración congelada; valores faltantes no se completan. |
| Clínica | Mapeo total y único, counts inválidos, discrepancia de ratios, nullable sin inventar AUC y conservación del cero original en archivo. |
| External / A-01 | Procedencia incompleta y reinterpretación como VAL/TEST bloqueadas; externo complementario con referencias completas aceptado. |
| Historia/E10 | Conflictos de alias/epoch y cardinalidad; canonical_event exacto, identidad y secuencia; epoch concordante con registro legacy; evaluación E10 contrastada contra payload; hash de ledger incorrecto rechazado. |
| Calibración | Caso VAL positivo, PK original y pareja explícita; TEST/external/validation rechazados, población o umbral contradictorios bloqueados. |
| Consolidación | Matriz/reporte concordantes consolidados con originales archivados; faltantes y support contradictorio rechazados. |
| XAI | Procedencia completa aceptada sin leer artefactos; input/checkpoint conflictivos rechazados; padre incompleto exige disposición expresa y permanece intacto. |
| Reconciliación | Catálogo distinto y cambio de credencial sintética bloqueados; comparación de filas y proyecciones. |
| Transacción simulada | Fallo durante DDL y fallo de catálogo causan rollback sin promover head; éxito promueve después de constraints; repetición con plan completo no aplica DDL/DML. Drivers, Docker y conexión reemplazados por mocks. |
| DDL/archivo | 617 sentencias parseadas, dos MERGE previstas, guardas sin desactivar, probes de invariantes antes de triggers definitivos; archivo exclusivo 0600. |

Los tests son `tests/adoption_v2/test_adoption.py`, `test_extended.py` y `test_transaction.py`, con fixtures inventadas en `fixtures.py`. Los subcasos recorren múltiples checksums/estados; el número 50 cuenta métodos unittest, no cada iteración.

## Regresión y reproducibilidad

20 pruebas del compilador/manifiesto/guardas de baseline y 5 del sobre Alembic pasan. Se recompiló la baseline en modo `--check`, sin regenerar recursos. Los 54 archivos históricos y el manifiesto certificado permanecen byte a byte iguales. Ruff check/format y compilación en memoria de módulos correctos.

Comando ejecutado en el entorno de trabajo:

```sh
PYTHONPATH=/tmp/e10_10_4_sql_parser:. python3 scripts/db/check_v2_stage_c.py \
  --alembic-python malaria_dl_local_project/.venv/bin/python \
  --ruff /Users/julio/Library/Python/3.9/bin/ruff
```

Para otro entorno, instalar `adoption_v2/requirements.txt`, usar Python 3.11+ y pasar intérprete/Ruff disponibles; no se necesita servidor PostgreSQL. El runner contiene una lista fija de ocho comandos offline, además de comprobaciones puras de hashes, generación del delta y fixtures. No invoca Docker, psql, Alembic upgrade ni el modo apply contra un servidor.

[Resultado estructurado](e10_10_5c_evidence/static_results.json), [delta reproducible](e10_10_5c_evidence/ddl_plan.json), [conteos/hashes sintéticos](e10_10_5c_evidence/synthetic_reconciliation.json). Los hashes sintéticos no son fingerprints de datos reales.

## Correcciones durante C

Se corrigieron defectos detectados al construir fixtures: excepciones por contexto incompleto convertidas en bloqueo explícito; separación de arrays SQL y JSONB en parámetros; UUID cargado como texto estable para bindings; tipmods y orden de columnas comprobados; hash de backup requerido antes de conectar; archivos privados fuera del repositorio. Se añadió comprobación de epoch E10 contra legacy, hash de sesión verificada, unicidad del destino, linaje XAI y valores explícitos en entidades nuevas para evitar timestamps/UUID aleatorios por default.

Se escogió READ COMMITTED con locks exclusivos de todas las tablas fuente para capturar commits concluidos mientras se adquirían los locks, evitando conservar el snapshot previo de la consulta advisory. La prueba de contexto incompleto falló inicialmente con AttributeError; tras la corrección, los 50 tests C pasan. Ninguna corrección modificó diseño científico, SQL históricos, restricciones ni baseline.

## Pendiente de Gate C y D

No ejecutados: catálogo real de una copia legacy actual; instalación del delta en PostgreSQL 17.9; FK/triggers con filas reales; rollback PostgreSQL real de adopción; commit incierto; repetición real; backup/restore de la copia adoptada y verificación de disponibilidad/procedencia de artefactos. Los fixtures no simulan todas las FK de 103 tablas; la aceptación final exige el servidor y catálogo exacto. La certificación B acredita instalación vacía, no adopción. No hay fallos estáticos pendientes; no se atribuyen resultados a estas pruebas aún no ejecutadas.
