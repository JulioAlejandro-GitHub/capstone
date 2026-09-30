# SWV2.0 — Integración de PostgreSQL v2 al entorno de desarrollo

**Estado: SWV2.0 — INTEGRACIÓN POSTGRESQL V2 CERTIFICADA** (pendiente GATE SWV2.0; la aprobación corresponde al usuario).

Historial: bloqueo inicial `POSTGRES LOGIN CREDENTIAL REQUIRED` (rol `julio` ausente; creación de superusuario pendiente de autorización) → resuelto con la autorización explícita "AUTORIZACIÓN SWV2.0 — RESOLVER POSTGRES LOGIN julio" (`swv2_0_role_precheck.json`, `swv2_0_role_julio.json`).

| Campo | Valor |
|---|---|
| Docker project | capstone-malaria |
| PostgreSQL service | db |
| Container | capstone_db |
| PostgreSQL | 17.9 (Debian 17.9-1.pgdg13+1) |
| Host endpoint | 127.0.0.1:5432 |
| Database | malaria_experiments |
| Database OID | 16386 |
| Server sysid | 7691366089693499436 |
| Persistent volume | capstone_v2_isolated_persistent_data |
| Alembic revision | pg_v2_baseline (1 root / 1 head) |
| Baseline state | FROZEN / IMMUTABLE — diff 0 |
| Structural manifest | 15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb |
| Application tables | 104 |
| XAI tables | 9 |
| xai_explanations | ausente |
| Dataset version | d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 |
| Dataset state | FROZEN |
| TRAIN / VALIDATION / TEST | 22,180 / 2,693 / 2,685 |
| TOTAL | 27,558 |
| Patients | 201 |
| Patient overlap | 0 / 0 / 0 |
| dataset_split_images | 55,116 |
| Application users / roles / user_roles | 1 / 1 / 1 (password hash sin cambios) |
| PostgreSQL DBeaver role | julio (LOGIN SUPERUSER, cluster-level, SCRAM) |
| DBeaver contract | jdbc:postgresql://127.0.0.1:5432/malaria_experiments |
| DBeaver-equivalent connection test | PASS (post-role y post-restart final) |
| Compose restart | PASS (`down` sin `-v` + `up -d`, dos veces) |
| Cluster identity preserved | YES |
| Dataset preserved | YES (16/16 transfer hashes = DBV2.4; fingerprints intactos) |
| Schema preserved | YES |
| Previous separate capstone_db_v2 required | NO (contenedor eliminado) |
| Certified volume preserved | YES |
| Backend status | STARTS_BUT_CONSUMER_INCOMPATIBILITY + TEMPORARY DEVELOPMENT CREDENTIAL DEPENDENCY (`julio`) |
| Consumer incompatibilities discovered | `require_e10_schema` → `v2_function_contract` (contrato runtime fijado a E.4); backend runtime role → `capstone_v2_runtime` en SWV2.1 |
| Baseline modified | NO |
| Dataset retransferred | NO |
| Cutover infrastructure | YES |
| Functional SW migration | NO |
| Escrituras de filas SWV2.0 | 0 (contadores = DBV2.5) |
| Cambios de catálogo global | rename de base; rol `julio` |
| Backup BD-v2 | dump `353759cf…59358b` + globals, restore verificado (fuera de Git) |
| Secretos en evidencia | 0 |

## Evidencia

`swv2_0_preflight.md`, `swv2_0_docker_before.md`/`.json`, `swv2_0_docker_after.md`/`.json`, `swv2_0_postgres_identity.md`, `swv2_0_database_rename.json`, `swv2_0_role_precheck.json`, `swv2_0_role_julio.json`, `swv2_0_check_{preflight,post_rename,integrated,after_restart,post_role,final_restart}.json`, `swv2_0_dataset_check.md`, `swv2_0_dbeaver_contract.md`, `swv2_0_dbeaver_attempt.json`, `swv2_0_dbeaver_contract_{post_role,final_restart}.json`, `swv2_0_consumer_observations.md`, `swv2_0_git.md`, `swv2_0_secret_scan.json`, `swv2_0_hashes.sha256`.

Pendiente del usuario: **Test Connection** en DBeaver (sin modificar la BD si falla).
