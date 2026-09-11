# E2 — Cierre de integración PostgreSQL

Fecha: 2026-09-11. **Dictamen actualizado: E2 APROBADA en el alcance de la etapa.**

Este complemento conserva el [informe E2 original](etapa_2_registro_adaptadores_2026-09-11.md). Su bloqueo por integración sin ejecutar queda resuelto mediante el resultado aportado por el usuario desde la terminal autorizada. No se atribuye esa ejecución al agente, cuyo acceso a Docker estaba restringido.

## Revisión efectiva

HEAD comprobado: `b6cace583e93bd96e260164948d400c13a17094f`. Se mantienen los cambios locales de E2 sin commit. Los **25 archivos del manifiesto SHA-256 del informe E2 coinciden**, sin discrepancias. Se revisó nuevamente `tests/test_model_configuration_postgres.py`. Este cierre añade únicamente este documento; conserva código, fixtures e informes anteriores, sin commits.

## Resultado aportado

Comando ejecutado por el usuario desde la raíz del repositorio:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE2_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_model_configuration_postgres.py
```

Salida:

```text
.                                                                        [100%]
1 passed in 0.29s
```

La prueba habilitada pasó, no fue omitida. El resultado completa la evidencia de las 138 pruebas consolidadas y las dos pruebas adicionales de recuperación aprobadas localmente en el informe original. No se repitieron esas suites ni la auditoría operativa E1.

## Evidencia que acredita la prueba

- PostgreSQL de Compose acepta la consulta y actualización JSONB del repositorio E2 sobre una tabla temporal tipada `runs`, con UUID/payloads sintéticos.
- La prueba comprueba que `runs` resuelve al esquema temporal antes de invocar el escritor. No modifica filas de `public.runs`.
- El snapshot devuelto y el leído son iguales; incluye configuración custom_cnn resuelta y runtime/entorno sintéticos.
- Una identidad de dataset incorrecta provoca el error de persistencia esperado. Después, SELECT 1 funciona y permanece una fila sintética en la transacción.
- Los commits internos liberan savepoints; la transacción externa se revierte.
- La comprobación posterior en otra conexión, mediante READ ONLY, confirma ausencia del UUID en `public.runs` y ausencia de la tabla temporal `runs` en esa sesión.
- No se aplican migraciones, se desactivan constraints/triggers ni se borran eventos operativos. No se crean CSV ni fallback de resultados.

## Límites y dictamen

Esta evidencia demuestra **integración aislada con rollback**. No demuestra durabilidad de un commit entre sesiones, permisos de UPDATE ni todos los constraints de `public.runs`, ni round-trip PostgreSQL de una red entrenada completa: la prueba emplea runtime sintético. La construcción/compilación/paso técnico/guardado/recarga de las tres arquitecturas y sus optimizadores se acreditó separadamente en las pruebas locales. No se presenta como un TRAIN científico operativo.

Con la prueba de persistencia requerida ejecutada y aprobada, y el manifiesto local conservado, se actualiza E2 a **APROBADA** para registro conectado, adaptadores, configuración validada, persistencia base, semántica de métricas y regresión E1. La aprobación no amplía el alcance a la ejecución durable integral, la migración de historias/predicciones ni los consumidores de etapas posteriores.

E1 permanece aprobada. Se mantienen los límites E3–E9 del informe original: VGG16 conserva su preprocesamiento histórico en E2; la corrección corresponde a E3. No se inicia E3 ni una campaña científica. Dataset, split, imágenes, checkpoints históricos, esquema operativo y publicaciones se conservan. La selección de Producción Etapa 2 continúa siendo manual.
