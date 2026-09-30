# E10.10.5D.4 — riesgos y límites

**E10.10.5D — ADOPCIÓN CERTIFICADA SOBRE COPIA AISLADA. PENDIENTE DE REVISIÓN Y APROBACIÓN.**

- D-01/D-02 y D-04 continúan resueltas; contrato de pgcrypto sin cambios. D-05 corregida y recertificada. D-06: cuatro equivalencias demostradas; cero diferencias semánticas detectadas.
- Gate D requiere revisión y aprobación explícita. E y cutover quedan fuera de alcance y no se iniciarán automáticamente.
- Certificación limitada al backup acreditado. E10, campañas, assessments y evaluaciones externas sin registros históricos en esta copia: su preservación es vacua, no evidencia de historial poblado. Los contratos se verifican con fixtures positivos/negativos; una futura fuente distinta requerirá nuevo preflight.
- Backups y correspondencias privadas están en temporales externos al repositorio, modo 0600/0700; conservarlos junto con volúmenes aislados para recuperación. Checksums publicados, sin contraseñas ni filas sensibles.
- Cuatro CHECK difieren textualmente y los hashes brutos de catálogo son distintos; se mantienen visibles. La regla canónica es específica a PostgreSQL 17.9 y exige mismos objetos/dependencias, sin excepciones generales.
- No se certificó carga productiva concurrente ni cutover. No existen bloqueos técnicos pendientes dentro de D sobre esta copia.

Evidencia anterior conservada en `e10_10_5d4_evidence/previous_reports/`; D-03 no certifica el manifiesto modificado. [Nueve puntos y decisión](e10_10_5_route_b_results.md).
