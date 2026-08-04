# Base de datos y Alembic

PostgreSQL es la fuente de verdad de estados, linaje y auditoría. El repositorio
conserva dos capas históricas que no son intercambiables:

1. `malaria_dl_local_project/db/init/*.sql` contiene el bootstrap SQL
   001–029 y sus checksums en `schema_migrations`.
2. `alembic/versions/*.py` contiene la adopción y evolución posterior mediante
   una única cadena Alembic.

No elimine, renumere, edite ni consolide migraciones ya aplicadas.
`malaria_dl_local_project/scripts/init_db.py` ejecuta únicamente el ledger SQL:
no crea `alembic_version`, no hace `stamp` y no aplica revisiones Alembic.
`alembic/env.py` usa `target_metadata=None`, por lo que la historia versionada,
no autogenerate, es la autoridad del esquema.

## Cadena Alembic vigente

```text
20260726_00  baseline deliberadamente vacío (stamp-only)
  → 20260726_01  auth/RBAC
  → 20260726_02  auditoría
  → 20260727_01  dominio científico
  → 20260727_02  ingesta
  → 20260727_03  quality gate
  → 20260727_04  cola de análisis
  → 20260727_05  detección celular
  → 20260728_01  clasificación celular
  → 20260728_02  resumen de clasificación
  → 20260728_03  contrato de resumen revisado
  → 20260804_01  identidad de inferencia basada en publicación
```

El head vigente al consolidar esta documentación es `20260804_01`. El baseline
`20260726_00_legacy_029_baseline.py` no crea tablas: representa una base que ya
contiene el bootstrap SQL hasta 029. Estampar una base incompleta produciría un
estado inválido.

## Operación segura

Con `DATABASE_URL` y `JWT_SECRET` cargadas:

```bash
make db-status
make db-migrate-check
make db-backup
make db-migrate
```

`db-migrate` ejecuta preflight de adopción, backup verificable, validación
transaccional del upgrade y finalmente `alembic upgrade head`. El script valida
la identidad real de la base, exige una cadena lineal con head único, acepta
únicamente revisiones ancestro presentes en el repositorio y rechaza esquemas
incompatibles.

La adopción de una base histórica sin `alembic_version` requiere revisión
manual: confirmar todas las entradas y checksums del ledger SQL —incluida la
migración 029—, las tablas esperadas y un backup restaurable antes de cualquier
`alembic stamp 20260726_00`. Este repositorio no autoriza un rebaseline
automático.

Para verificar una instalación desde cero sin alterar `public`, use
`make test-fresh-schema`: crea un schema temporal validado, aplica el ledger SQL
y Alembic, compara fingerprints y elimina el schema aunque falle el gate. No
equivale a autorizar un bootstrap o stamp sobre la base persistente.

## Prohibiciones

- No ejecutar `DROP DATABASE`, `DROP SCHEMA public`, resets ni truncados masivos.
- No usar `alembic downgrade` en la base persistente.
- No editar el baseline para que cree o borre objetos.
- No usar datos reales como fixtures ni una `TEST_DATABASE_URL` paralela.
- No aplicar manualmente una revisión Alembic aislada de su cadena.

Las reglas completas están en
[`engineering/database_safety_policy.md`](engineering/database_safety_policy.md),
[`engineering/alembic_simple_policy.md`](engineering/alembic_simple_policy.md)
y [`engineering/alembic_transition.md`](engineering/alembic_transition.md). El
inventario científico se describe en
[`engineering/scientific_data_dictionary.md`](engineering/scientific_data_dictionary.md).

## Pruebas

Los tests PostgreSQL usan la misma base configurada y aislamiento transaccional:

```bash
make test-backend-integration
make test-fresh-schema
make test-schema-clean
```

Los schemas temporales sólo se permiten con prefijo validado
`capstone_test_...`; los schemas de sistema y `public` se rechazan. Consulte
[testing.md](testing.md).
