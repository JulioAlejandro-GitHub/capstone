# SWV2.0 — Preflight y backup

Ejecutado antes de cualquier cambio Docker/PostgreSQL, sesión `REPEATABLE READ READ ONLY` como `capstone_v2_migrator` contra `capstone_db_v2` (127.0.0.1:56440). Script: `scripts/db/swv20_integration.py check --label preflight` (reutiliza `structure()` de DBV2.5 y `hashes()`/`science()`/`integrity()` de DBV2.4). Evidencia completa: `swv2_0_check_preflight.json`.

| Verificación | Esperado | Observado | Resultado |
|---|---|---|---|
| PostgreSQL | 17.9 | 17.9 (170009) | PASS |
| Database | capstone_v2_isolated_persistent | capstone_v2_isolated_persistent | PASS |
| OID | 16386 | 16386 | PASS |
| Server sysid | 7691366089693499436 | 7691366089693499436 | PASS |
| alembic_version | pg_v2_baseline | pg_v2_baseline (1 fila); estático: 1 root / 1 head, down_revision None | PASS |
| Structural manifest | 15c95e0c…b3eafb | 15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb | PASS |
| Root revision | e3aaad12…ef279 | idéntico; baseline sin diff vs commit GATE DBV2.4 | PASS |
| Dataset | d8c0cab5-…-7ca01aee2ec2 FROZEN | idem, `frozen_at` igual a DBV2.5 | PASS |
| TOTAL / patients | 27,558 / 201 | 27,558 / 201 | PASS |
| Transfer hashes (16 tablas) | = manifest DBV2.4 | 16/16 idénticos (count, transfer_hash, pk_hash) | PASS |
| Usuarios aplicación | ≥ 1 | users 1 / roles 1 / user_roles 1 (activo 1) | PASS |
| Integridad FK/CHECK/UNIQUE | 0 violaciones | 0 | PASS |

Hallazgos del clúster v2 (no forman parte del manifest estructural): bases `template0/1`, `postgres`, `capstone_v2_isolated_persistent`; `malaria_experiments` **no existe**; roles `postgres` (superuser), `capstone_v2_migrator`, `capstone_v2_runtime`; **rol `julio` ausente**; 0 conexiones cliente. `datacl` de la base no concede CONNECT a PUBLIC.

Puerto 5432: único listener = Docker (`capstone_db` legacy, `0.0.0.0:5432`). Sin PostgreSQL nativo en el host.

## Backup lógico BD-v2

Tomado desde `capstone_db_v2` vía socket del contenedor (sin credenciales en argv), antes de cualquier cambio.

| Archivo (en `backups/swv2_0/`, ignorado por Git, permisos 600) | SHA-256 |
|---|---|
| `bd_v2_capstone_v2_isolated_persistent_20260930T193201Z.dump` (pg_dump `-Fc`, 12.7 MB) | `353759cf8752d825964d64ee77fd72d769044713baf67ac896b9fdb09b59358b` |
| `bd_v2_globals_20260930T193201Z.sql` (roles; contiene verificadores SCRAM → privado) | `bc06e4f4a55c8d39b950ac1ae2efc8fe17ebcb88ba584d6ef7e65b8eac92ffa4` |

Verificación: TOC con 105 TABLE DATA, 251 FK, 105 TRIGGER, 79 FUNCTION, 33 VIEW. **Restore completo** en contenedor desechable `postgres:17.9` sin red (`--network none`): 105 tablas, 33 views, 105 triggers, `pg_v2_baseline`, train/val/test 22,180/2,693/2,685, 201 pacientes, 55,116 `dataset_split_images`, 1 usuario, 9 tablas XAI. Contenedor desechable y su volumen anónimo eliminados después (verificado que no era el volumen certificado).

Es una salvaguarda de datos, no una segunda arquitectura PostgreSQL.
