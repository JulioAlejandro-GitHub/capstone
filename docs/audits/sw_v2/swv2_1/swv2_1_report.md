# SWV2.1 — Adaptación del backend al contrato PostgreSQL v2

**Estado: SWV2.1 — BACKEND POSTGRESQL V2 CERTIFICADO** (pendiente GATE SWV2.1; la aprobación corresponde al usuario).

| Campo | Valor |
|---|---|
| PostgreSQL | 17.9 (Debian 17.9-1.pgdg13+1) |
| Database / OID | malaria_experiments / 16386 |
| Server sysid | 7691366089693499436 |
| Persistent volume | capstone_v2_isolated_persistent_data |
| Alembic | pg_v2_baseline (1 root / 1 head), FROZEN — diff 0 |
| Structural manifest | 15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb |
| Backend PostgreSQL role | capstone_v2_runtime |
| Backend superuser / migrator | NO / NO |
| DBeaver/admin role | julio (sin cambios) |
| v2_runtime_contract | revision pg_v2_baseline, sha256 d77ace1422b46b6c1db970af7d291cbb518ae2258f5709d65d88e9ba107a3181 |
| Contract source | structural manifest congelado DBV2.2-R1 (`15c95e0c…`) vía `scripts/db/build_v2_runtime_contract.py` |
| Contract reproducibility | 2 ejecuciones idénticas + `--check` + test |
| require_e10_schema | PASS (fail-closed intacto) |
| /health · /ready | 200 · 200 (también post-restart) |
| Dataset | d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 FROZEN — 22,180 / 2,693 / 2,685 = 27,558 |
| Application authentication | PASS — prueba segura equivalente (`swv2_1_auth.md`) |
| Password hash modificado | NO |
| Schema / baseline modificados | NO / NO |
| GRANT/REVOKE · migraciones | ninguno |
| Escrituras científicas persistentes | 0 |
| Tests | 0 fallos nuevos; 32 tests nuevos PASS |
| Nuevas infracciones CI | 0 (33 = HEAD) |
| Secret scan | PASS (`swv2_1_secret_scan.json`) |

**P-01 v2 runtime contract: RESOLVED** — `swv2_1_runtime_contract.md`.
**P-02 backend SUPERUSER dependency: RESOLVED** — `swv2_1_runtime_identity.md`.

## Hallazgos

1. **Login previo a SWV2.1** (no bloqueante): `users.last_login_at` + 1 `audit_events` de un login real a las 21:17:40Z, tras el commit SWV2.0. Se probó criptográficamente que es la única diferencia; el hash de la contraseña no cambió. Fijado como estado de entrada (`swv2_1_auth.md`).
2. **Fase posterior** — browser legacy `/api/dataset/summary|split` agrega las 2 raíces físicas de `dataset_split_images` (55,116); no equivale al split gobernado (`swv2_1_dataset.md`).
3. **Fase posterior** — `make db-migrate*`/`scripts/db/migrate.sh` (Alembic legacy vía backend) ya no tienen privilegios DDL con el rol runtime; es la separación runtime ≠ migrator correcta. El tooling v2 para el destino canónico sigue pendiente (SWV2.0).
4. **Fase posterior** — la ruta E10 end-to-end (TRAIN → RunEventEmitter → Reporter → ResultService → PostgreSQL) sólo quedó desbloqueada a nivel de reconocimiento del schema; no se acreditó.
5. Preexistentes sin cambios: 2 fallos backend (política de mutaciones E9.3; bloque TEMPORAL del override), 45 de `adoption_v2`, 33 infracciones CI.

## Evidencia

`swv2_1_preflight.md`, `swv2_1_backend_inventory.md`, `swv2_1_runtime_contract.md`, `swv2_1_runtime_identity.md`, `swv2_1_health_ready.md`, `swv2_1_auth.md`, `swv2_1_dataset.md`, `swv2_1_tests.md`, `swv2_1_postflight.md`, `swv2_1_git.md`, `swv2_1_check_{integrated,post_auth,post_restart}.json`, `swv2_1_runtime_{integrated,post_restart}.json`, `swv2_1_smoke_{integrated,post_restart}.json`, `swv2_1_auth.json`, `swv2_1_secret_scan.json`, `swv2_1_hashes.sha256`.
