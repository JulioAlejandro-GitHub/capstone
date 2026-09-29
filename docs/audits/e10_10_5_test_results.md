# E10.10.5D.3 — Pruebas

**90 tests offline aprobados. Preflight aprobado. Adopción revertida por catálogo incompatible.**

| Prueba | Resultado |
| --- | --- |
| Adaptador, incluidos 14 tests D-04 | 64/64 PASS |
| Baseline/Alembic estáticos | 26/26 PASS |
| Nueve clases negativas de D-04 | PASS; fixtures en memoria, sin mutar pgcrypto |
| Dependencias alteradas/ausentes, duplicados, propiedades | Rechazados |
| Preflight real completo de copia aislada | PASS |
| Ejecución SQL del adaptador | 838 sentencias correctas, incluidas 316 DDL |
| Reconciliación de datos precommit | 102 tablas y secuencia comprobadas antes del cotejo final |
| Cotejo final completo | FAIL: columna generada D-05 y cuatro CHECK D-06 |
| Commit / promoción de head | NO EJECUTADOS |
| Rollback ante fallo final | PASS; 97 tablas, catálogo, head y secuencia sin cambios |
| Replay diagnóstico auxiliar con rollback obligatorio | PASS; diferencia capturada y reversión exacta |
| Inyección de fallo intermedio en sentencia 50 | PENDIENTE, no ejecutada |
| Repetición / backup-restore adoptado | PENDIENTES; no existe destino adoptado |

[Informe de nueve puntos](e10_10_5_route_b_results.md), [tests D-04](e10_10_5d3_evidence/adoption_tests.out), [rollback real](e10_10_5d3_evidence/after_failure.json). Las 91 comprobaciones de Ruta A de D.2 son evidencia anterior, no pruebas nuevas de D.3. [Resultados previos](e10_10_5d3_evidence/pre_d3_e10_10_5_test_results.md).
