# E8 — Cierre técnico con evidencia PostgreSQL

Fecha: 2026-09-11. Dictamen: **APROBADA en el alcance técnico verificado de E8**. La ejecución y las conclusiones científicas siguen pendientes.

Este complemento conserva el informe `etapa_8_ensembles_2026-09-11.md` y su manifiesto original. Sustituye su pendiente de integración PostgreSQL con la salida aportada por el usuario desde su terminal; no representa una nueva ejecución del asistente.

## Revisión efectiva

HEAD: `9eb5c721d3d7a39247bd3f0fdb51a9092c11df7a`, rama `main`. La implementación E8 permanece sin commit. Se comprobaron los hashes y tamaños de **94/94 archivos** del manifiesto E8 original, sin diferencias. Este cierre añade únicamente documentación y el manifiesto final; conserva todos los cambios existentes.

Contrato: `probability_ensemble_e8_v1`, SHA-256 `8744f0e7326088b4a7ac419c6439007a655810adb7e38ff6f0dbb2193d5cc001`.

## Validación registrada

La validación local anterior permanece: **105 passed, 6 skipped, 7 warnings en 15.29 s**; Ruff aprobado. Los seis casos omitidos eran las tres pruebas PostgreSQL E8 y las tres de regresión E7. El intento previo del asistente fue denegado por acceso al socket Docker antes de iniciar pytest; no se interpretó como caída de PostgreSQL.

Comando reproducible desde la raíz del repositorio, mediante Compose autorizado:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE8_POSTGRES_TESTS=1 -e RUN_STAGE7_POSTGRES_TESTS=1 \
  -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -s -p no:cacheprovider \
  tests/test_ensemble_postgres.py tests/test_science_postgres.py
```

Salida aportada por el usuario:

```text
E8 configuration/evaluation/comparison: exact readback, 3 events, immutable; no synthetic TRAIN inserted
E8 rollback: zero ensemble events from another connection; commit durability not claimed
...E7 synthetic report: exact readback, one event, append-only rejection, outer transaction usable
E7 report rollback: zero events from another connection; no commit durability claimed
...
6 passed in 4.42s
```

| Evidencia | Resultado |
| --- | --- |
| E8: configuración, evaluación y comparación | Lectura exacta; tres eventos; inmutabilidad comprobada |
| E8: escritura fallida y auditoría de fallo | Prueba aprobada, recuperación del savepoint y reintento |
| E8: referencias y separación de tipos de evento | Prueba aprobada; evaluación requiere configuración persistida |
| Regresión PostgreSQL E7 | Tres pruebas aprobadas |
| Rollback E8 y E7 | Cero eventos correspondientes desde otra conexión |

Las pruebas inspeccionadas usan fixtures sintéticos y transacción externa con savepoints. El rechazo append-only deja la transacción utilizable. El caso E8 no inserta un TRAIN sintético para representar el ensemble. El commit de preparación del esquema de prueba se distingue del rollback de los eventos bajo prueba; la limpieza pertenece al fixture aislado.

## Límites del cierre

La evidencia acredita integración sintética con PostgreSQL, igualdad de lectura, restricciones y aislamiento. **No acredita durabilidad de un commit entre sesiones**, tolerancia a fallo del host, ni una nueva lectura de la revisión operativa o de `/ready`. E8 no requiere una nueva migración; la revisión `20260912_02` procede de la evidencia E6 anterior.

Los datos fuente de estas pruebas son fixtures controlados: no prueban superioridad del ensemble, rendimiento clínico ni disponibilidad de candidatos científicos operativos. Continúan pendientes las ejecuciones científicas previstas en `docs/science/preparacion_e8_v1.md`. TEST permanece deshabilitado en el ejecutor E8 actual. No se ejecutaron entrenamientos, búsqueda de pesos, inferencia operativa, promoción, ni E9. No se generaron CSV ni archivos como fallback de PostgreSQL.

El manifiesto final enlaza el manifiesto original y registra estos resultados sin borrar los resultados históricos.
