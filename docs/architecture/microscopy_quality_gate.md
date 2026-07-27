# Quality gate técnico de microscopía

Flujo: `created → integrity_check/quality_assessment → quality_aggregation →
technical_review|completed`. Los estados ejecutables no incluyen segmentación,
detección, crops ni clasificación.

- Cualquier `fail` o `error` de imagen produce gate `fail`, run `blocked`.
- Sin fallos y con advertencias produce gate `warning`, `review_required`.
- Todas en `pass` produce gate `pass`, `ready_for_analysis=true`.

El cálculo ocurre secuencialmente en un threadpool local. Cada imagen se
confirma con assessment, estado y evento; la agregación y actualización final
son transaccionales. Un fallo de integridad se registra y permite continuar con
las demás entradas. No se escribe en filesystem.
