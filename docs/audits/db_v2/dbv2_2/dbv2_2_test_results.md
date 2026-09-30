# DBV2.2 — Resultados

| Categoría | Estado | Evidencia / límite |
|---|---|---|
| STATIC documental DBV2.1 | PASS_STATIC_ONLY | dbv2_2_static_result.json; parser PostgreSQL 18.4; no certifica runtime |
| PostgreSQL 17.9 reproducción mínima | CONFLICT CONFIRMED | contract_trigger_probe.sql y .log; 42703 en ambas tablas |
| Instalación completa y catálogo | NOT RUN — BLOCKED | Contradicción normativa detectada antes de modificar baseline |
| NEGATIVE recall/FK/UNIQUE/XAI/E-04 | NOT RUN — BLOCKED | No baseline instalada |
| REPEATABILITY | NOT RUN — BLOCKED | No primer upgrade |
| FAILURE/ROLLBACK de baseline | NOT RUN — BLOCKED | El rollback del reproducer no equivale a probar instalación |
| BACKUP/RESTORE | NOT RUN — BLOCKED | No baseline instalada |

Revalidación estática: `PYTHONPATH=/tmp/e10_10_4_sql_parser python3 scripts/db/validate_dbv2_1.py`. La ruta temporal corresponde al pglast 8.4 ya disponible en esta estación. No se modificó DBV2.1.
