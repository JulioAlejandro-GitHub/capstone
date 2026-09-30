# SWV2.1 — Postflight

Fuente: `swv2_1_check_post_restart.json` (tras `docker compose restart`), mismo procedimiento READ ONLY certificado en SWV2.0.

| Invariante | Resultado |
|---|---|
| PostgreSQL | 17.9 (`server_version_num` 170009), no recovery |
| Database / OID | malaria_experiments / 16386 |
| sysid | 7691366089693499436 |
| Volumen | `capstone_v2_isolated_persistent_data` en `/var/lib/postgresql/data`; `capstone_db` healthy |
| Alembic | `pg_v2_baseline` (1 fila); 1 root / 1 head estático |
| Structural manifest (catálogo vivo) | `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb` = GATE DB-V2 |
| Conteos | 104 tablas, 33 vistas, 79 funciones, 105 triggers, 413 índices, PK 104 / FK 251 / CHECK 518 / UNIQUE 77 |
| Baseline (`pg_v2_baseline` sha256 `e3aaad12…f279`, recursos, manifest) | diff vs freeze `28346b7` = 0; untracked = 0 |
| XAI | 9 tablas contractuales presentes, todas con 0 filas; `xai_explanations` ausente |
| Dataset | FROZEN, 22,180 / 2,693 / 2,685 = 27,558; 16/16 hashes de transferencia = DBV2.4; fingerprints intactos |
| Usuario de aplicación | users/roles/user_roles 1/1/1; password hash sin cambio; única diferencia vs DBV2.4 = `last_login_at` del login previo a SWV2.1 (`swv2_1_auth.md`) |
| Filas fuera del conjunto transferido | sólo técnicas (`alembic_version` 1, `experiment_execution_gate` 1) + 1 `audit_events` de entrada; tablas científicas = 0 filas |
| Escrituras de SWV2.1 | 0 (chequeos `integrated` → `post_auth` → `post_restart` idénticos en datos) |
| DDL / GRANT / REVOKE / Alembic upgrade-downgrade-stamp / migración nueva | ninguno (ACL y catálogo incluidos en el manifest estructural, invariante) |
| Volumen legacy `capstone-malaria_postgres_data` | conservado, no montado |

Resultado: **PASS**.
