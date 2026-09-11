# E4 — Precedencia del operador JSON

HEAD conservado: `6b24d50ad24ea641e70e7c8b758cc93c79729d7e`. Dictamen: **NO APROBADA**.

El adjunto del usuario contiene dos ejecuciones. La inicial falla preparando parámetros `false`; la última alcanza el cuerpo de las pruebas y termina con **43 fallos, 1 aprobada y 1 deseleccionada en 2,40 s**. En esa última salida, los casos que insertan configuraciones directamente muestran `InvalidTextRepresentation`, SQLSTATE `22P02`; el repositorio envuelve otros fallos en `CampaignError`. No se atribuyen los nuevos fallos al parámetro `false` ni a un montaje antiguo.

Se identificó por inspección otro defecto en `campaign_configuration_valid`: `(i->'shape' - 0)`. El operador aritmético tiene precedencia sobre la extracción JSON, por lo que puede intentar convertir la cadena `shape` a entero. Se corrigió mínimamente a `((i->'shape') - 0)`, extrayendo primero el array y eliminando luego su dimensión batch. Es coherente con el 22P02 observado; falta corroborar en PostgreSQL que explica y resuelve todos los fallos. No se ha obtenido el diagnóstico original completo de los CampaignError ni se afirma que no existan defectos adicionales.

Se añadió un caso PostgreSQL que reproduce la expresión anterior dentro de un savepoint (espera 22P02), verifica la expresión corregida y llama directamente al validador SQL con las doce configuraciones sintéticas de la matriz. Esto separa la comprobación de configuración de la congelación y de los errores sanitizados del repositorio. Se conservan aislamiento y limpieza del fixture.

Resultados locales: **77 aprobadas, 46 PostgreSQL omitidas**, dos avisos existentes de Alembic. Ruff aprobado. El intento de acceso a Compose sigue denegado por el socket Docker, sin acceso a la BD. La suite ahora tiene **45 casos sintéticos y uno de revisión pública**. No se aplicó migración operativa, ni se modificó 01; sólo se corrigió la expresión de 02 y se amplió la suite. Se preservan los informes y manifiestos anteriores. El nuevo manifiesto `etapa_4_manifiesto_precedencia_json_2026-09-11.json` identifica esta revisión efectiva.

Primero, ejecutar el diagnóstico acotado:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE4_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_campaigns_postgres.py::test_configuration_json_shape_operator_precedence
```

Si pasa, ejecutar todos los casos sintéticos:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE4_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_campaigns_postgres.py -k 'not public_migration_readonly'
```

Esperado: **45 aprobadas, una deseleccionada**. Estos resultados aún no se han obtenido. No iniciar instalación operativa o E5 por esta corrección.

Renderizado offline de ambos upgrade() en memoria: 44673 bytes; SHA-256 `9275fd9f35e32047558b5e997c4a4a6a004a6ccd0803633c641f7392c02f989e`. No constituye ejecución ni validación PL/pgSQL.
