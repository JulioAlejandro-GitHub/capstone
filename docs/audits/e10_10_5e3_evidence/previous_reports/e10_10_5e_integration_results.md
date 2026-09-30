# E10.10.5E — integración incompleta, bloqueada por E-03

**E-02 aprobada; escritor corregido. Gate E permanece bloqueado y no solicitado.**

[Resolución E.2, evidencia y decisión específica E-03](e10_10_5e2_resolution.md). Se detuvo la integración al reproducir en PostgreSQL que el contrato de origen E10 prohíbe los dos roles exigidos por la calibración. No se cambió la baseline.

| # | Recorrido integral | Estado E.2 |
|---|---|---|
| 1 | TRAIN sintético local | Pendiente; no se acredita con el fixture del servicio |
| 2 | TRAIN sintético Docker | Pendiente |
| 3 | Ledger y proyección tipada | Probado runtime real para evaluación sin calibración y procedencia sintética; productor pendiente |
| 4 | Duplicación global event_id | Duplicado y conflicto de payload probados; cruce entre runs pendiente |
| 5 | event_sequence | Gap y conflicto probados en runtime real; recorrido integral pendiente |
| 6 | Fallo SQL ledger/proyección | Rollback real probado después del INSERT de evaluación y antes de métricas; reintento aprobado |
| 7 | Pérdida de ACK | Replay con nueva instancia de servicio probado; transporte real pendiente |
| 8 | Reinicio y recuperación | Pendiente proceso/contenedor; recrear servicio no lo sustituye |
| 9 | Concurrencia/fencing | Owner inválido probado; concurrencia integral pendiente |
| 10 | Historial E10 sintético poblado | Fixture mínimo con época/evaluación; historial integral pendiente |
| 11 | VALIDATION | Cálculo/proyección sintéticos probados; TRAIN integral pendiente |
| 12 | Calibración sólo VALIDATION | Bloqueada E-03: roles calibration_default/selected incompatibles con source_kind=e10 |
| 13 | training_history | Productor y recorrido pendiente |
| 14 | Ensembles | Productor y recorrido pendiente |
| 15 | XAI y productores | Pendiente |
| 16 | Publicación y linaje | Pendiente; completion todavía depende del JSONB legacy |
| 17 | EVALUATE/EXPLAIN | Pendiente |
| 18 | API real PostgreSQL v2 | Pendiente; lector de resúmenes todavía requiere adaptación |
| 19 | React consumiendo API | Pendiente |
| 20 | Regresión legacy | 76 tests de servicio/routing aprobados; regresión integral pendiente |

E-02: INSERT/UPDATE de resultados JSONB rechazados por CHECK real; ResultService v2 no emite ese UPDATE. Duplicado no duplica proyecciones; fallo SQL revierte ledger/evaluación/métricas. No se acredita aún el conjunto completo de lectores, NULL, procedencia producida ni finalización v2.

No se solicita Gate E ni se declara integración completada. Sin acceso operativo, cutover, campañas reales, modificación del dataset congelado ni de contratos D-01 a D-06/E-01. [Informe anterior preservado](e10_10_5e2_evidence/previous_reports/e10_10_5e_integration_results.md).
