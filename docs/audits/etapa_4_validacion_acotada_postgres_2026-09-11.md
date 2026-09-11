# E4 — Evidencia PostgreSQL acotada aportada por el usuario

El usuario ejecutó mediante Docker Compose autorizado:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE4_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_campaigns_postgres.py::test_configuration_json_shape_operator_precedence
```

Resultado comunicado: **1 passed in 0.45s**. Evidencia aportada por el usuario, no ejecución directa de esta sesión; la salida no incluye hashes de los archivos del contenedor.

Según las aserciones del caso actual, el resultado acredita la reproducción aislada del 22P02 con la expresión anterior, la extracción correcta del array con los paréntesis, y la aceptación SQL de las doce configuraciones sintéticas del resolver E2, incluida DenseNet121 con head_units=0. El fixture instala 01 y 02 en esquema sintético y verifica su ausencia desde otra conexión tras el rollback. No acredita instalación pública ni durabilidad de un commit operativo.

Queda pendiente ejecutar toda la suite sintética, incluidos rechazos de NULL/tipos, integridad de TRAIN, atomicidad y concurrencia: el comando anterior sustituyendo el nodeid por `tests/test_campaigns_postgres.py -k 'not public_migration_readonly'`. Esperado: **49 aprobadas y una deseleccionada**. La prueba de instalación pública queda separada y no se autoriza aplicar migraciones mediante esta evidencia.

Dictamen E4: **NO APROBADA**, hasta completar integración e instalación correspondientes. No se modificó código ni se inició E5.
