# E10.10.5E.2 — resultados parciales

**Escritor E-02 probado; E-03 reproducida. E incompleta; Gate E bloqueado.**

- 76 pruebas unitarias aprobadas: servicio y selección v2/legacy; sin UPDATE legacy en v2.
- PostgreSQL aislado E.1 runtime real: aceptación, duplicado sin nuevas proyecciones, fencing, gap/conflictos, rechazo de procedencia ausente.
- Fallo SQL 22012 entre evaluación y métricas: rollback completo del evento y proyecciones; reintento aceptado.
- INSERT/UPDATE training_results rechazados por 23514 / ck_v2_no_result_json.
- Dos rechazos reales 23514 / v2_evaluations_check_6a2239d39784 para calibración de origen E10: nueva decisión E-03 requerida.
- Catálogo comparado íntegramente con E.1; archivos históricos protegidos verificados contra Git HEAD.

[Resultados SQL](e10_10_5e2_evidence/route_a/e10_projection.json) · [pytest](e10_10_5e2_evidence/unit_tests.txt) · [Preservación](e10_10_5e2_evidence/route_a/preservation.json) · [Alcance e incidencias](e10_10_5e2_resolution.md).

No se acredita TRAIN integral, producción de procedencia, NULL en todos los lectores, API/React, reinicio real, concurrencia ni regresión PostgreSQL legacy. Los resultados baseline/ACL anteriores siguen siendo históricos y no se presentan como pruebas nuevas. [Informe E.1 preservado](e10_10_5e2_evidence/previous_reports/e10_10_5_test_results.md).
