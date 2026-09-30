# SWV2.0 — Identidad PostgreSQL y continuidad BD-v2

Seis verificaciones completas con el mismo script (`swv2_0_check_<label>.json`). En las seis, todo el contenido verificado (Alembic, baseline, structural snapshot, dataset, transfer hashes, fingerprints, usuario, integridad, digest del password hash) es **idéntico** al preflight; sólo cambian nombre de base, contenedor, proyecto Compose y puerto.

| Checkpoint | Endpoint | Contenedor / proyecto | Database | OID | Sysid | Manifest |
|---|---|---|---|---|---|---|
| preflight | 127.0.0.1:56440 | capstone_db_v2 / — | capstone_v2_isolated_persistent | 16386 | 7691366089693499436 | 15c95e0c…b3eafb |
| post_rename | 127.0.0.1:56440 | capstone_db_v2 / — | malaria_experiments | 16386 | 7691366089693499436 | 15c95e0c…b3eafb |
| integrated | 127.0.0.1:5432 | capstone_db / capstone-malaria | malaria_experiments | 16386 | 7691366089693499436 | 15c95e0c…b3eafb |
| after_restart | 127.0.0.1:5432 | capstone_db / capstone-malaria | malaria_experiments | 16386 | 7691366089693499436 | 15c95e0c…b3eafb |
| post_role | 127.0.0.1:5432 | capstone_db / capstone-malaria | malaria_experiments | 16386 | 7691366089693499436 | 15c95e0c…b3eafb |
| final_restart | 127.0.0.1:5432 | capstone_db / capstone-malaria | malaria_experiments | 16386 | 7691366089693499436 | 15c95e0c…b3eafb |

PostgreSQL 17.9 (Debian 17.9-1.pgdg13+1), `recovery = false` en todos.

## Rename de database (cambio de integración, no de schema)

`ALTER DATABASE capstone_v2_isolated_persistent RENAME TO malaria_experiments`, ejecutado como `postgres` conectado a la base de mantenimiento `postgres`, con 0 conexiones a la base objetivo y `malaria_experiments` inexistente en el clúster v2. Antes/después: OID 16386, owner `capstone_v2_migrator`, `datacl`, encoding y collation idénticos (`swv2_0_database_rename.json`). El snapshot estructural no incluye el nombre de la base → manifest sin cambios, verificado.

## Rol de clúster `julio`

`CREATE ROLE julio WITH LOGIN SUPERUSER` (verificador SCRAM, autorizado explícitamente; `swv2_0_role_julio.json`). Es un objeto de clúster fuera del snapshot estructural (que sólo incluye `capstone_v2_*`); manifest recalculado después: idéntico. No es una modificación de `pg_v2_baseline`.

## Catálogo por el endpoint final (127.0.0.1:5432/malaria_experiments)

| Objeto | Valor |
|---|---|
| Tablas de aplicación | 104 (+ `alembic_version`) |
| Views | 33 |
| FK / CHECK / UNIQUE / PK | 251 / 518 / 77 / 104 |
| Índices | 413 de aplicación (414 físicos; +1 = PK de `alembic_version`) |
| Funciones / triggers | 79 / 105 |
| XAI | 9 tablas exactas; `xai_explanations` ausente |

## Alembic

`alembic_version = pg_v2_baseline` (1 fila); estático: revisiones `[pg_v2_baseline]`, `down_revision None`, 1 root / 1 head. No se ejecutó `upgrade`, `downgrade`, `stamp` ni `current` (el guard `alembic_v2/env.py` está ligado al descriptor DBV2.3 y no se modificó).

## Baseline

`alembic_v2/`, `alembic_v2.ini` y el manifest estructural certificado sin diff respecto del commit GATE DBV2.4 y sin archivos no rastreados (verificado en cada checkpoint y con `git diff 28346b7`).

## Escrituras

`pg_stat_database` de `malaria_experiments`: `tup_inserted/updated/deleted = 154461/1731/638` antes y después de iniciar backend/frontend, tras crear `julio`, con el backend conectado como `julio` y tras ambos restarts; iguales a los valores DBV2.5. **Escrituras de filas en SWV2.0 = 0**; únicos cambios de catálogo global: rename de base y creación del rol `julio`.
