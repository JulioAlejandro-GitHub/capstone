# E10.10.5D.2 — Resultados de pruebas

**Ruta A recertificada; D bloqueada por D-04.**

| Prueba | Resultado |
| --- | --- |
| Generación determinista/validador/historia de 54 archivos y 22 SQL | PASS |
| Baseline + Alembic offline | 26/26 PASS |
| Adaptador offline | 50/50 PASS |
| Ocho comandos estáticos, Ruff/formato | PASS |
| Alembic desde cero PostgreSQL 17.9 nuevo | PASS |
| Catálogo y metadatos directos | Cero diferencias |
| Restricciones/E10 existentes de servidor | 46/46 PASS |
| IDENTITY, UUID y comportamiento D-03 | 45/45 PASS |
| Rollback Ruta A tras 500 CREATE/ALTER | PASS |
| Idempotencia Ruta A | PASS |
| Backup/restore Ruta A, 103 tablas/secuencia | PASS |
| Preflight de datos legacy, 97 hashes, 22 checksums, gate/modelos | PASS |
| D-01 y D-02 sobre copia restaurada | PASS |
| Preflight completo de adopción | BLOCKED: LEGACY_FUNCTION_OWNER_MISMATCH (salida 2) |
| Apply/catálogo/equivalencia adoptada | NO EJECUTADOS |
| Rollback/repetición/backup/restore de adopción | NO EJECUTADOS |

[Ruta A](e10_10_5_route_a_results.md), [Ruta B](e10_10_5_route_b_results.md), [comandos reproducibles](e10_10_5d2_evidence/static_commands.json). Los fallos iniciales de lint durante desarrollo se corrigieron antes del pase final; no hubo fallo de servidor de Ruta A en D.2. Los códigos negativos esperados de los probes no son pruebas fallidas. Los resultados anteriores se conservan en [snapshot previo](e10_10_5d2_evidence/pre_d2_e10_10_5_test_results.md); no certifican la baseline nueva.
