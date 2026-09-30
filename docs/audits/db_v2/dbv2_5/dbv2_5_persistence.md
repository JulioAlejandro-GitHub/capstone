# DBV2.5 — Persistencia final

Procedimiento (`scripts/db/dbv25_freeze.py restart`):

1. verificación completa READ ONLY (identidad, Alembic, manifest, dataset, usuario, hashes, integridad);
2. `docker stop --time 30 capstone_db_v2` (observado `Running=false`);
3. `docker start capstone_db_v2` + `pg_isready`;
4. verificación completa idéntica.

No se ejecutó `docker compose down -v`, no se eliminó ni recreó el volumen ni el contenedor.

| Comprobación | Resultado |
|---|---|
| Mismo container ID | YES |
| Mismo volumen `capstone_v2_isolated_persistent_data` | YES |
| Mismo OID 16386 / sysid 7691366089693499436 | YES |
| Alembic `pg_v2_baseline` | YES |
| Manifest estructural `15c95e0c…3eafb` | YES |
| Dataset, fingerprints, usuario, password_hash_match, ausencias, integridad | idénticos antes/después |
| Contadores `pg_stat_database` tup_inserted/updated/deleted | 154461 / 1731 / 638 antes y después (DBV2.5 no escribió filas) |

**FINAL RESTART PERSISTENCE = PASS**

Evidencia: `dbv2_5_persistence.json`.
