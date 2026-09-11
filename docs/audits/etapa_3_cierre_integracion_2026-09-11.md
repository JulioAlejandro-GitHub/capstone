# E3 — Cierre de integración PostgreSQL

Fecha: 2026-09-11. Dictamen actualizado: **APROBADA en el alcance técnico de E3**.

Este complemento conserva el informe de implementación y el manifiesto originales. Sustituye su estado pendiente de integración y su dictamen, no sus resultados históricos. No modifica código, configuraciones, datasets, checkpoints ni publicaciones.

## Evidencia recibida y correspondencia

El usuario ejecutó desde la raíz del proyecto:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE3_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_input_contract_postgres.py
```

Salida aportada:

```text
...                                                                      [100%]
3 passed in 0.30s
```

Procedencia: terminal del usuario en Compose autorizado. No se presenta como ejecución realizada por el agente, cuya sesión había recibido acceso denegado al socket.

Al recibir el resultado se comprobó HEAD `9250a33a6d4472b1b97e02e416ac47345c11c264` y coincidencia de **26/26 SHA-256** del [manifiesto E3](etapa_3_manifiesto_2026-09-11.json), incluidos prueba PostgreSQL, helper E2, implementación, configuración y pruebas locales. Se preservaron todos los cambios sin commit. Se comprobó además que `docker-compose.override.yml` monta `./malaria_dl_local_project` en `/app/malaria_dl_local_project:ro`. El comando apunta a esa ruta en el servicio backend; la correspondencia se sustenta en la revisión local sin cambios y la ejecución aportada, no en una captura independiente de hashes dentro del contenedor.

## Alcance acreditado

Se revisaron nuevamente `test_input_contract_postgres.py` y `configuration_roundtrip_and_rollback` de `test_model_configuration_postgres.py`. Los tres casos corresponden a Custom CNN, VGG16 y DenseNet121. El resultado aprobado implica que pasaron sus aserciones de:

- Persistencia y lectura JSONB del snapshot completo por el camino E2, con igualdad exacta.
- Contrato `malaria_input_v1`, arquitectura correcta y modo efectivo: VGG16 `vgg16_imagenet`; otras arquitecturas `rescale_0_1`.
- Rechazo de escritura con identidad de dataset sintética distinta; transacción aún utilizable y un registro sintético antes del rollback.
- Rollback de la transacción externa y comprobación posterior READ ONLY: UUID sintético ausente de `public.runs` y tabla temporal ausente.

La escritura ocurre en tabla TEMP `runs`, con namespace comprobado, UUID/payload sintéticos y savepoints. El finally intenta rollback y comprobación posterior también si falla el cuerpo, conservando diagnósticos originales si además falla limpieza. Esta ejecución verde acredita el recorrido satisfactorio; no constituye una inyección adicional de fallo del propio rollback.

No se escribieron runs operativos para acreditar esta integración. No se desactivaron constraints/triggers ni se aplicaron migraciones/seeds. No hay fallback de archivos en este camino.

## Dictamen y límites

| Evidencia | Estado |
| --- | --- |
| Implementación y regresión local | APROBADAS: 202 casos en las ejecuciones separadas del informe original |
| PostgreSQL E3 | APROBADA: 3 casos, 0.30s, ejecución aportada por el usuario |
| Compatibilidad histórica | APROBADA para el fixture acreditado explícito; no acredita un checkpoint operativo particular D4 |
| Puerta E3 | **APROBADA en su alcance técnico** |

Las cinco omisiones de la ejecución local permanecen registradas como tales: esta evidencia resuelve los tres casos E3, sin atribuir nuevas ejecuciones a las pruebas E1/E2. Sus aprobaciones previas conservan sus revisiones y alcances originales.

La integración con rollback no acredita durabilidad de un commit entre sesiones, todos los permisos/constraints de `public.runs`, ni persistencia integral de épocas/predicciones. El cierre de linaje, identidad y reutilización de consumidores sigue en E6. No se demuestra beneficio clínico, recuperación de D-6 ni compatibilidad de un histórico operativo no inspeccionado. Estos límites delimitan el alcance aprobado; no sustituyen verificaciones de etapas posteriores.

Se conservan dataset, split, históricos y selección manual de Producción Etapa 2. No se inicia E4 ni una campaña científica.
