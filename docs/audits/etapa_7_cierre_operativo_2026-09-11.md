# E7 — Cierre técnico y operativo

**Dictamen: APROBADA en el alcance técnico verificado de E7.** Este cierre sustituye el dictamen pendiente del informe de implementación, que se conserva. **La ejecución científica completa continúa pendiente.** No acredita desempeño clínico ni inicia E8.

## Evidencia recibida

El usuario aportó el resultado del comando Compose pendiente para `tests/test_science_postgres.py`, con `RUN_STAGE7_POSTGRES_TESTS=1`:

```text
E7 synthetic report: exact readback, one event, append-only rejection, outer transaction usable
E7 report rollback: zero events from another connection; no commit durability claimed
...
3 passed in 2.34s
```

Es evidencia de la terminal del usuario; no se presenta como reejecución del asistente. Completa los tres casos PostgreSQL omitidos en la suite local anterior. La denegación previa del socket se conserva como hecho de aquella sesión, sin interpretarla como caída de PostgreSQL.

## Revisión y continuidad

HEAD: `15f2c957a99306fd5f77d8c7cd5ce0d317bd63a1`, rama main. Los archivos E7 siguen sin commit. Antes de este cierre se verificaron **79/79 hashes** del manifiesto E7, sin diferencias; incluyen las 63 entradas E6. Se revisó el contenido de las tres pruebas para contrastar las aserciones con la salida recibida.

Este cierre sólo añade documentación y un manifiesto final. No modifica código, pruebas, protocolo, configuraciones, migraciones ni datos operativos. Se conserva el protocolo `capstone_science_e7_v1`, SHA-256 canónico `7db076d71c2143934f0b3bae47ff253f18d3f65c5c3f8efb2634586acbadbdf2`.

## Alcance verificado

| Evidencia | Resultado |
|---|---|
| Suite local E7 y regresiones E4/E6 | 110 passed, 3 skipped, 7 warnings in 13.05s, ya documentados; no reejecutados en este cierre |
| Integración PostgreSQL E7 | **3 passed in 2.34s**, salida aportada por el usuario |
| Reporte sintético | Inserción/lectura idénticas, idempotencia y un evento |
| Append-only y savepoints | UPDATE rechazado; transacción externa utilizable |
| Escritura fallida | Rechazo sanitizado, cero eventos parciales, recuperación del savepoint, exportación bloqueada sin BD |
| Rollback | Cero eventos desde otra conexión después del rollback |
| Bloqueo final E6 sintético | Identidad exacta reservable, identidad diferente rechazada, cero predicciones |
| Limpieza | Fixture de esquema sintético finalizado sin error de teardown |
| Continuidad de archivos | 79/79 hashes del manifiesto anterior coinciden |

No se suman los conteos de ejecuciones separadas como si fueran una única invocación de pytest. No se requieren nuevas migraciones E7: se reutilizan `audit_events` y las estructuras E6. Este resultado no es una nueva comprobación de `/ready` ni de la revisión pública instalada; esas evidencias permanecen atribuidas al cierre E6.

## Límites de la integración

Las escrituras corresponden exclusivamente al esquema sintético del fixture E4. El caso de round-trip hace visible ese esquema y mantiene las escrituras E7 en una transacción externa con savepoints; la conexión posterior acredita ausencia tras rollback. No demuestra durabilidad de un commit operativo entre sesiones ni resistencia a caída física.

El caso de bloqueo final sustituye la resolución del candidato por evidencia sintética para aislar las constraints y transacciones SQL. No acredita un candidato científico real ni ejecuta inferencia. La selección, el linaje y las métricas se verificaron por separado con los casos locales y las regresiones E6.

## Estado científico separado

Permanecen pendientes la acreditación operativa E1 para la campaña científica, población y exposición histórica a TEST, creación/congelamiento de campaña, entrenamientos y repeticiones autorizados, comparación VAL y eventual congelamiento de candidato/checkpoint/decisión antes de un TEST futuro autorizado. La ablación sintética sigue planificada y no disponible.

El reporte de preparación no contiene resultados científicos ni ganador. No se ejecutaron entrenamientos completos, TEST operativo, promociones o cambios de Producción. La selección de Producción permanece manual. E8 no se inicia.

Referencias: [informe de implementación](etapa_7_protocolo_comparacion_2026-09-11.md), [operación y comandos](../science/operacion_e7.md), [reporte de preparación](../science/preparacion_e7_v1.md).
