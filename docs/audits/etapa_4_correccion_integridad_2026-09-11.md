# E4 — Corrección del precheck e integridad SQL (2026-09-11)

Dictamen: **NO APROBADA**. Corrección local y renderizado offline completados; instalación e integración PostgreSQL **NO VERIFICADAS**. No se aplicó ninguna migración operativa, ni se inició E5 o un entrenamiento.

## Línea base y conservación

Revisión Git: `6b24d50ad24ea641e70e7c8b758cc93c79729d7e`, rama `main`. La revisión efectiva incluye los archivos sin commit enumerados en el manifiesto complementario `etapa_4_manifiesto_correccion_2026-09-11.json`; el HEAD por sí solo no identifica esta entrega.

Se revisaron el contrato 0B v1.1, las políticas `alembic_simple_policy.md` y `database_safety_policy.md`, el informe y guía E4, los dos verificadores de migración, la migración E4, la parametrización/aislamiento PostgreSQL y el escritor `persist_model_configuration` de E2. No se encontraron instrucciones AGENTS aplicables. El árbol ya contenía la implementación E4 sin commit. Se conservaron sus cambios y los informes anteriores.

El manifiesto inicial E4 no existía al comenzar esta corrección: se capturó antes de editar como `etapa_4_manifiesto_2026-09-11.json`, indicando esa circunstancia. No constituye evidencia retrospectiva de una revisión anterior. Sus diez archivos permanecen iguales salvo la suite PostgreSQL, ampliada aquí. Los 26 archivos del manifiesto E3 conservan sus hashes.

La consulta de revisión instalada mediante Compose no pudo llegar a PostgreSQL: `permission denied while trying to connect to the docker API` (ruta local omitida). Esto acredita una restricción de acceso, no una BD caída. No se conoce desde esta sesión si `20260911_01` fue aplicada. Por ello se conserva exactamente su contenido y se añade la corrección hacia adelante `20260911_02`, hija de `20260911_01`. No se reescribió historia ni se modificaron datos para satisfacer los nuevos CHECK.

## Causa comprobada y corrección del precheck

El patrón anterior evaluaba `Path(__file__).resolve().parents[2]` como argumento de `os.getenv`. Python evalúa todos los argumentos antes de invocar la función, incluso cuando `CAPSTONE_ROOT` existe. Ejecutado por stdin desde `/app`, `__file__` es `<stdin>` y `/app/<stdin>` sólo tiene dos padres; el índice 2 produce el `IndexError: 2` comunicado por el usuario. Se reprodujo localmente esa operación de pathlib y la evaluación anticipada.

Ambos scripts, `verify_alembic_adoption.py` y `validate_alembic_transactionally.py`, ahora resuelven explícitamente la raíz: variable presente, absoluta y válida primero; ubicación real del archivo sólo si falta la variable. Se exige directorio, `alembic.ini` y directorio `alembic`. Por stdin sin raíz se emite `CAPSTONE_ROOT_REQUIRED_FOR_STDIN`; raíz vacía/incorrecta produce `CAPSTONE_ROOT_INVALID`. No se intenta otra ubicación. Se mantuvo el resolver autocontenido porque el wrapper transmite únicamente el script por stdin.

Se cubren ambos scripts mediante subprocess: archivo, stdin con raíz válida, stdin sin raíz, raíz inexistente y vacía. `--help` sale antes de importar configuración de aplicación o conectar a la BD. Una prueba adicional verifica que una raíz explícita evita evaluar el fallback. El precheck usa una transacción READ ONLY. Se corrigió también su rechazo de un head anterior válido al incorporar una nueva revisión: admite revisiones conocidas del historial lineal, manteniendo el rechazo de revisiones desconocidas. La ubicación de scripts Alembic se fija de forma absoluta, independiente del cwd. Los otros usos de `parents[2]` en `scripts/db` corresponden a scripts ejecutados como archivo, sin este fallback anticipado.

## Corrección SQL propuesta

`20260911_02_campaign_integrity.py` añade CHECK con predicado `IS TRUE`: SQL NULL nunca acredita un contrato. Exige hash no nulo, formato hexadecimal SHA-256, comparación `IS NOT DISTINCT FROM` contra el cálculo y equivalencia del JSON canónico. Las validaciones originales siguen presentes; la revisión adicional cierra sus huecos de lógica ternaria.

Los validadores SQL verifican presencia, estructura y tipos del contrato, protocolo, presupuesto, semillas, registro, miembros y configuraciones E2/E3. `max_members` y `max_attempts_per_member` son números enteros positivos; se verifica cardinalidad frente al presupuesto. Se rechazan semillas nulas, duplicadas o de otro tipo. Se comprueban objetos obligatorios, arrays y sus elementos, flags booleanos y valores numéricos de configuración. No se confunde un campo opcional con uno ausente: `experiment_id` y `exclusion_reason` pueden ser JSON null; la dimensión batch de entrada y `internal.mode` también; monitores opcionales E2 conservan presencia con valor null permitido. Los parámetros opcionales del optimizador no se convierten arbitrariamente en obligatorios. Los CHECK se añaden NOT VALID y se validan dentro de la migración: datos incompatibles provocarán fallo, no reparación automática.

La vinculación TRAIN exige `runs.model_id → models.id`, con nombre canónico o alias explícito del registro congelado y versión de adaptador coincidente. Se conserva la comparación íntegra de configuración, dataset, semilla, experimento y entorno relevante. No se infiere identidad por carpeta o fecha. El vínculo bloquea la fila TRAIN y la del catálogo antes de comprobar correspondencia. Cambiar `model_id` de un TRAIN vinculado o renombrar su entrada de catálogo queda protegido; los vínculos previos incompatibles impiden aplicar la corrección.

La identidad congelada del entorno comprende `source_sha256`, `python`, `tensorflow`, `packages` y `determinism_environment`. `git_commit`, `git_dirty`, dispositivos y otros metadatos observados pueden actualizarse sin cambiar esos componentes. Esto coincide con el escritor real E2, que refresca el entorno en cada persistencia. La suite invoca ese escritor con payload sintético y luego actualiza estado, finalización, metadatos y progreso; no ejecuta modelos. Las funciones mantienen search_path fijado al esquema de instalación y pg_catalog.

## Resultados reales

| Comprobación | Resultado |
|---|---|
| Pruebas locales afectadas y regresión pura E1/E2 | **74 aprobadas**, 45 PostgreSQL omitidas, 2 avisos Alembic de path_separator |
| Historial Alembic | **23 revisiones, head único 20260911_02** |
| Renderizado offline de upgrade() de 01 y 02, dialecto PostgreSQL | **44.675 bytes**, SHA-256 `73f10f2fa096c317680270de371d455e18218a005cb24b3cdd2e15fdbaff1624` |
| Revisión instalada y precheck real Compose | **NO VERIFICADOS**: socket Docker denegado |
| Integración PostgreSQL/triggers/rollback/concurrencia | **NO VERIFICADA**; casos preparados, no ejecutados |

El hash anterior identifica el DDL de ambos upgrade() renderizados en memoria mediante Alembic Operations/MigrationContext; el CLI Alembic añade su propio envoltorio y actualización de versión, por lo que su salida no tiene necesariamente ese hash. El renderizado no analiza ni ejecuta los cuerpos PL/pgSQL en PostgreSQL.

La suite contiene **45 casos**: los 11 anteriores, 19 negativos de contrato ausente/null/tipos/presupuesto, 10 negativos de configuración, 4 de identidad relacional/alias y 1 de compatibilidad con el escritor E2. Uno de los 45 comprueba instalación pública mediante READ ONLY; los otros **44** instalan ambas revisiones sólo en un esquema sintético y pueden probarse antes de migrar public.

Se conservaron las pruebas de atomicidad y concurrencia. El fixture mantiene transacción externa y savepoints; tras un rechazo verifica que la transacción sigue utilizable. El finally comprueba desde otra conexión la ausencia del esquema después del rollback. La prueba concurrente hace commits únicamente en el esquema sintético validado y después lo elimina; verifica su ausencia desde otra conexión. Los fallos de limpieza se reportan además del fallo original. Son garantías revisadas en código y aserciones pendientes de ejecución aquí, no evidencia de rollback ya obtenido ni durabilidad de un commit operativo.

No se generaron CSV, resultados científicos ni fallback de archivos. El DDL offline se mantuvo en memoria. No se cambiaron servicios, permisos, datasets, splits, checkpoints, publicaciones ni el esquema operativo.

## Reproducción desde la raíz del repositorio

Precheck sin aplicar migraciones:

```sh
make db-migrate-check
```

Consulta explícita READ ONLY de base/esquema/revisión, sin imprimir credenciales:

```sh
docker compose exec -T backend python -c 'from sqlalchemy import text; from app.db import get_primary_engine; c=get_primary_engine().connect(); t=c.begin(); c.execute(text("SET TRANSACTION READ ONLY")); print(c.execute(text("SELECT current_database(),current_schema(),version_num FROM alembic_version")).all()); t.rollback(); c.close()'
```

Renderizado completo revisado (no instala):

```sh
docker compose exec -T backend python -m alembic upgrade 20260901_01:20260911_02 --sql
```

Si la lectura acredita que 01 ya está instalada, el rango incremental es `20260911_01:20260911_02`.

Integración sintética **antes de aplicar public** (esperado: 44 aprobadas, una deseleccionada):

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE4_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_campaigns_postgres.py -k 'not public_migration_readonly'
```

La selección excluye únicamente la aserción que exige 02 instalada en public; no omite los casos SQL negativos, atomicidad, concurrencia o limpieza. Tras una futura instalación autorizada mediante el procedimiento de preflight/backup del repositorio, la misma suite sin `-k` debe aprobar los 45 casos. **Esta corrección no autoriza ni ejecuta esa instalación.**

Pruebas locales realizadas, desde `malaria_dl_local_project`:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q -p no:cacheprovider \
  --basetemp=/private/tmp/e4-correction-final \
  tests/test_migration_root_e4.py tests/test_campaigns_e4.py \
  tests/test_campaigns_postgres.py tests/test_governed_dataset_contract.py \
  tests/test_model_registry_e2.py::test_lazy_cli \
  tests/test_model_registry_e2.py::test_matrix_and_identical_child_resolution \
  tests/test_model_registry_e2.py::test_invalid_config_before_adapter \
  tests/test_model_registry_e2.py::test_precedence_requested_resolved_and_tracking
```

E4 permanece **NO APROBADA** hasta acreditar instalación e integración correspondientes. La ejecución de campañas y verificación científica pertenece a etapas posteriores; no se afirma migración completa de épocas/predicciones. La selección de Producción Etapa 2 permanece manual.
