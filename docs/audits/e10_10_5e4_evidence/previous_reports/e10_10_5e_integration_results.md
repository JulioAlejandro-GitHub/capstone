# E10.10.5E — integración incompleta, bloqueada por E-04

**E-03 aplicada a candidata no certificada. Gate E permanece bloqueado y no solicitado.**

[Resolución E.3, diagnóstico PostgreSQL y propuesta E-04](e10_10_5e3_resolution.md). La candidata amplía los roles E10, pero PostgreSQL acepta ocho casos inválidos adicionales. No hay recertificación E-03 ni avance de los recorridos integrales. Los resultados runtime indicados abajo corresponden a E.2; no se reejecutaron sobre la candidata.

| # | Recorrido integral | Estado al detener E.3 |
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
| 12 | Calibración sólo VALIDATION | Bloqueada E-04: guardas de pareja, unicidad y admisión insuficientes; proyector y atomicidad de pareja pendientes |
| 13 | training_history | Productor y recorrido pendiente |
| 14 | Ensembles | Productor y recorrido pendiente |
| 15 | XAI y productores | Pendiente |
| 16 | Publicación y linaje | Pendiente; completion todavía depende del JSONB legacy |
| 17 | EVALUATE/EXPLAIN | Pendiente |
| 18 | API real PostgreSQL v2 | Pendiente; lector de resúmenes todavía requiere adaptación |
| 19 | React consumiendo API | Pendiente |
| 20 | Regresión legacy | 76 tests de servicio/routing aprobados; regresión integral pendiente |

E-02: INSERT/UPDATE de resultados JSONB rechazados por CHECK real; ResultService v2 no emite ese UPDATE. Duplicado no duplica proyecciones; fallo SQL revierte ledger/evaluación/métricas. No se acredita aún el conjunto completo de lectores, NULL, procedencia producida ni finalización v2.

No se solicita Gate E ni se declara integración completada. Sin acceso operativo, cutover, campañas reales, modificación del dataset congelado ni de contratos D-01 a D-06/E-01. [Informe E.2 preservado](e10_10_5e3_evidence/previous_reports/e10_10_5e_integration_results.md).
