# E4 — Corrección de parámetros SQL accidentales

Fecha: 2026-09-11. HEAD: `6b24d50ad24ea641e70e7c8b758cc93c79729d7e`. Dictamen: **NO APROBADA**.

## Evidencia y causa

El usuario comunicó 44 errores de setup, una prueba deseleccionada, en 1,57 s: `StatementError`, SQLSTATE ausente. No se alcanzaron las aserciones SQL. La compilación local del DDL anterior con `sqlalchemy.text` y el dialecto PostgreSQL psycopg identificó parámetros `false` y `1`; `compiled.construct_params({})` produjo `InvalidRequestError: A value is required for bind parameter 'false'`. La revisión 01 y ATTEMPT_GUARD no contienen esos parámetros.

La causa está en los literales JSON `"antialias":false` y `"positive_class":1` de 02. Alembic convierte el string de `op.execute` en TextClause, cuyo reconocimiento de parámetros alcanza esos dos puntos dentro del literal. Es un fallo de preparación anterior al envío al servidor. Se detectó además el mismo defecto en `"progress":2` de la prueba del escritor E2, todavía no alcanzada por la ejecución del usuario.

## Cambios mínimos

Se añadió un espacio después de esos tres separadores JSON. El contenido JSON y las invariantes no cambian. No se alteró 01, no se creó un nuevo esquema operativo ni se aplicó una migración. La modificación de 02 corrige su transporte SQL; el fragmento del usuario acredita un fallo de instalación sintética, no una instalación pública. La revisión pública sigue sin verificarse desde esta sesión.

Se añadieron tres casos locales: compilación y preparación sin parámetros para ambas migraciones, y revisión de los SQL literales de la suite sintética contra sus parámetros declarados. Estos casos habrían detectado el defecto anterior. El renderizado offline por sí solo no lo detectaba y podía sustituir los parámetros accidentales por NULL.

El diagnóstico del fixture ahora incluye la fase (prerrequisitos, migración 01, migración 02, datos sintéticos), tipo original y SQLSTATE, suprimiendo la cadena de excepción del driver. Se conservan rollback, savepoints y comprobación posterior de limpieza; el fallo de limpieza no reemplaza al fallo de setup/cuerpo.

## Validación real

- Mismo conjunto local del informe complementario anterior: **77 aprobadas, 45 PostgreSQL omitidas**, dos avisos existentes de configuración Alembic.
- Ruff y `git diff --check`: aprobados.
- Renderizado en memoria de ambos upgrade(): **44.671 bytes**, SHA-256 `c3e930df0bf5c6ee3b4d8dd5f85c05abf9e07b3f79073ba1921c24a2952e5492`. Sustituye el hash offline del informe anterior; no acredita sintaxis/ejecución PL/pgSQL.
- Intento de la integración Compose: acceso denegado a Docker API. **NO VERIFICADA** en esta sesión. No se interpreta como fallo de PostgreSQL.
- Los 45 casos PostgreSQL se mantienen: 44 sintéticos y uno de instalación pública. El número de casos locales aumentó en tres.

Se preservan informes y manifiestos anteriores; `etapa_4_manifiesto_parametros_sql_2026-09-11.json` identifica los archivos efectivos tras esta corrección. No hubo entrenamiento, E5, CSV ni cambios de datos operativos.

## Repetición

Desde la raíz del repositorio, sin aplicar la migración pública:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE4_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_campaigns_postgres.py -k 'not public_migration_readonly'
```

Esperado: 44 aprobadas, una deseleccionada. Hasta obtener ese resultado y verificar la instalación correspondiente, E4 permanece NO APROBADA. Los comandos de precheck y renderizado revisado siguen siendo `make db-migrate-check` y `docker compose exec -T backend python -m alembic upgrade 20260901_01:20260911_02 --sql`.
