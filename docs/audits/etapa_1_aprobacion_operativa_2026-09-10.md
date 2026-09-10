# Etapa 1 — Cierre de la verificación operativa

Fecha: 2026-09-10. **Dictamen actualizado: E1 APROBADA**, sobre la evidencia local y los resultados operativos aportados por el usuario en esta conversación.

## Revisión y procedencia

HEAD Git comprobado: `54c9d9568f04ca7a5f15582b784375b07a8463e2`. La revisión efectiva incluye cambios sin commit en `malaria_dl_local_project/src/malaria_dl/persistence/dataset_evidence.py`, `tests/test_dataset_evidence_postgres.py` y `tests/test_dataset_stage1.py` de ese proyecto. Se conservan los tres complementos previos sin seguimiento y el informe E1 original. Este cierre añade sólo documentación; no se hicieron commits ni nuevas modificaciones funcionales.

La ejecución operativa se realizó desde la terminal del usuario con acceso a Compose. Este agente no la ejecutó: su acceso al socket seguía denegado. El dictamen incorpora explícitamente la evidencia comunicada por el usuario, sin atribuirle una ejecución propia ni inventar valores de huellas o conteos no transcritos.

## Evidencia consolidada

| Dimensión | Evidencia y procedencia | Estado |
|---|---|---|
| D1 | Usuario confirmó PostgreSQL accesible mediante Compose, base `malaria_experiments`, esquema `public`, head Alembic y revisión instalada `20260901_01`, constraints de audit_events/runs validadas y trigger append-only activo | VERIFICADA según evidencia del usuario |
| D2 | UUID explícitamente designado `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`; usuario confirmó ejecución correcta del resolver E1 | VERIFICADA según evidencia del usuario |
| Implementación y regresión inicial | Informe E1: 80 pruebas aisladas aprobadas; resultado histórico conservado | APROBADA en su alcance |
| Regresión de la corrección | 56 pruebas locales aprobadas, una integración omitida localmente, dos advertencias protobuf, según informe de corrección | APROBADA |
| Integración PostgreSQL corregida | Usuario aporta `1 passed in 0.24s` al repetir el comando opt-in de esta prueba | APROBADA |

El éxito del resolver E1 implica sus controles de existencia, FROZEN/trainability, checks requeridos vigentes, ausencia de fallos bloqueantes, materialización exacta del sello y pertenencia READY/PASS, raíz accesible, asignaciones, población, identidad clínica, cuatro fingerprints, contenido de archivos, cardinalidades y ausencia de solapamiento por paciente. No se seleccionó otro UUID ni se reemplazó una referencia sellada.

## Fallo identificado y corrección validada

El resultado previo aportado por el usuario identificó fase INSERT, excepción original `AmbiguousParameter` y SQLSTATE `42P08`. El INSERT reutilizaba `:id` para columnas UUID y TEXT. Se separaron `id` y `correlation_id`, con casts explícitos UUID/TEXT y la misma identidad lógica. La lectura por ID también tiene cast UUID explícito. La prueba ahora pasa tras ese cambio. El error público y la comparación completa permanecen intactos.

Comando repetido desde la raíz del repositorio en la terminal del usuario:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE1_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_dataset_evidence_postgres.py
```

Salida aportada:

```text
.                                                                        [100%]
1 passed in 0.24s
```

## Aislamiento y rollback

Se revisaron nuevamente las aserciones de la prueba. Su aprobación acredita:

1. Inserción de evento con UUID y payload sintéticos.
2. Lectura idéntica de `after_state`, `success` y `error_code`; correlation_id igual al UUID del evento.
3. Duplicado rechazado en savepoint con `UniqueViolation`, SQLSTATE `23505`.
4. Transacción externa utilizable después del rechazo mediante SELECT 1.
5. Un evento antes del rollback externo.
6. Cero eventos desde una conexión posterior con transacción READ ONLY después del rollback.

El flujo conserva la comprobación posterior también ante errores del cuerpo y acumula los fallos de limpieza sin sustituir el diagnóstico original. Los commits internos sólo liberan savepoints. No se utilizan DELETE, desactivación de triggers, modificación de constraints ni TRAIN operativo ficticio. El código revisado no escribe datasets, runs ni eventos existentes. No se añadieron CSV ni fallback de archivos.

Esta prueba demuestra integración aislada con rollback, **no durabilidad de un commit entre sesiones**. No se presenta ese alcance adicional como verificado.

## Dictamen y límites de etapa

La evidencia operativa comunicada cierra D1–D2 y la integración que impedía aprobar E1. Por ello el dictamen vigente es **APROBADA** en el alcance DATA-01–03, guarda DATA-04 y nueva evidencia de persistencia E1, conforme al contrato 0B v1.1. Los dictámenes NO APROBADA anteriores se conservan como historial de los bloqueos existentes en ese momento.

No se afirma migración integral de épocas/predicciones: corresponde a diseño E2/E4, TRAIN E5, evaluación/EXPLAIN E6, comparación E7 y regresión E9. No se acredita durabilidad general, rendimiento ni resultados científicos. No se ejecutaron entrenamientos ni se alteraron split, dataset, imágenes, checkpoints, publicaciones o esquema operativo. La selección de Producción Etapa 2 permanece manual. **No se inicia Etapa 2.**

Referencias conservadas: [E1 original](etapa_1_dataset_explicito_2026-09-10.md), [cierre operativo inicialmente bloqueado](etapa_1_cierre_operativo_2026-09-10.md), [diagnóstico](etapa_1_diagnostico_persistencia_2026-09-10.md), [corrección](etapa_1_correccion_parametro_evidencia_2026-09-10.md).
