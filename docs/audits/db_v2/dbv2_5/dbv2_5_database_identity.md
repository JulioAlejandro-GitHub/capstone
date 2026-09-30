# DBV2.5 — Identidad de la base de datos

| Atributo | Esperado | Observado | Resultado |
|---|---|---|---|
| PostgreSQL | 17.9 | `17.9 (Debian 17.9-1.pgdg13+1)`, `server_version_num = 170009` | PASS |
| Database | `capstone_v2_isolated_persistent` | `capstone_v2_isolated_persistent` | PASS |
| Database OID | 16386 | 16386 | PASS |
| Server sysid | 7691366089693499436 | 7691366089693499436 | PASS |
| Container | `capstone_db_v2` | `capstone_db_v2` (`1dc48428c6b938da6525754cc4f26d535814f1f8c101928487f7c0d630ce4971`) | PASS |
| Endpoint | 127.0.0.1:56440 | `5432/tcp → 127.0.0.1:56440` (único binding) | PASS |
| Persistent volume | `capstone_v2_isolated_persistent_data` | único mount, `/var/lib/postgresql/data`, RW; labels `lifecycle=persistent`, isolation `1a590188-5f24-4068-ab38-b77bb8c61e65` (= `dbv2_3/persistent_target.json`) | PASS |
| Recovery | false | false | PASS |
| Guard `inspect_isolation` + `validate_server_snapshot` (safety.py certificado) | PASS | PASS | PASS |

Mismo container ID, mismo sysid de clúster y mismo OID que DBV2.3/DBV2.4: no es una BD reconstruida.

Evidencia: `dbv2_5_verification.json` → `identity`; `dbv2_5_final_check.json` → `result.identity`.
