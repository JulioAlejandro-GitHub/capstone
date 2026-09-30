# DBV2.2 — Resultados

| Clase | Resultado | Evidencia |
|---|---|---|
| STATIC | PASS_STATIC_ONLY, 35 tests | static_baseline_tests.log (25), regression_test.log (3), generated_tests.log (2), alembic_envelope_tests.log (5), baseline_static.json, dbv21_static.json |
| POSTGRESQL 17.9 | PASS | empty_catalog.json, catalog_counts.json, catalog_comparison.json, alembic_history.json |
| NEGATIVE / positivas | PASS, 111 comprobaciones | dbv22_server_tests.json (77), e04_contract_tests.json (27), e04_edges_dbv22.json (7) |
| R1 mínima | PASS | r1_probe.sql, r1_probe.log, r1_identity.txt |
| REPEATABILITY | PASS | repeatability.json |
| FAILURE/ROLLBACK | PASS | failure_rollback.json, failure_recovery.json |
| BACKUP/RESTORE | PASS | backup_restore.json |

Los parsers y suites se ejecutaron con intérpretes separados: python3 con PYTHONPATH=/tmp/e10_10_4_sql_parser para pglast 8.4; malaria_dl_local_project/.venv/bin/python para Alembic/psycopg. static_interpreter_diagnostic.log conserva un intento incompatible Python 3.12 frente al binario pglast del otro intérprete; no es prueba PostgreSQL ni PASS.

Se ajustaron sólo fixtures/assertions del harness a DBV2.1 (recall explícito, nombre uq_xai_method_configuration_hash, raw_output válido, ausencia schema_migrations). No se cambió el esquema para hacer pasar pruebas. No hubo segundo conflicto contractual. R1 no sustituye la suite completa.

La prueba inicial de restore autenticada como postgres produjo ownership pgcrypto distinto. backup_restore_initial_owner_mismatch.json conserva ese diagnóstico. La estrategia corregida autentica al migrador; el restore final en otra base nueva coincide sin alterar el contrato ni ampliar permisos.
