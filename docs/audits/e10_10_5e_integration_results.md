# E10.10.5E — integración incompleta, detenida por E-05

**E-04 resuelta y baseline recertificada. Gate E bloqueado y no solicitado.**

[Resolución E-04](e10_10_5e4_resolution.md). El consumo de contexto explícito por ResultService está probado; los fixtures no sustituyen su productor real. Al iniciar ese productor se detectó la [incompatibilidad E-05](e10_10_5e5_decision.md) entre el objetivo configurable y el objetivo fijo de PostgreSQL. Integración detenida según el apartado 15.

| # | Recorrido integral | Estado al detener E.4 |
|---|---|---|
| 1 | TRAIN sintético local | Pendiente; no se acredita con el fixture del servicio |
| 2 | TRAIN sintético Docker | Pendiente |
| 3 | Ledger y proyección tipada | Probado runtime real para evaluación sin calibración y procedencia sintética; productor pendiente |
| 4 | Duplicación global event_id | Duplicado y conflicto de payload probados; cruce entre runs pendiente |
| 5 | event_sequence | Gap y conflicto probados en runtime real; recorrido integral pendiente |
| 6 | Fallo SQL ledger/proyección | Evaluación y siete puntos de pareja calibrada probados; rollback/reintento/idempotencia aprobados |
| 7 | Pérdida de ACK | Replay con nueva instancia de servicio probado; transporte real pendiente |
| 8 | Reinicio y recuperación | Pendiente proceso/contenedor; recrear servicio no lo sustituye |
| 9 | Concurrencia/fencing | Owner inválido probado; concurrencia integral pendiente |
| 10 | Historial E10 sintético poblado | Fixture mínimo con época/evaluación; historial integral pendiente |
| 11 | VALIDATION | Cálculo/proyección sintéticos probados; TRAIN integral pendiente |
| 12 | Calibración sólo VALIDATION | E-04 aprobada: pareja, procedencia, NULL, unicidad y atomicidad; productor real pendiente por E-05 |
| 13 | training_history | Productor y recorrido pendiente |
| 14 | Ensembles | Productor y recorrido pendiente |
| 15 | XAI y productores | Pendiente |
| 16 | Publicación y linaje | Pendiente; completion todavía depende del JSONB legacy |
| 17 | EVALUATE/EXPLAIN | Pendiente |
| 18 | API real PostgreSQL v2 | Pendiente; lector de resúmenes todavía requiere adaptación |
| 19 | React consumiendo API | Pendiente |
| 20 | Regresión legacy | 76 tests servicio/routing y 50 legacy aprobados; regresión integral pendiente |

E-01 y E-02 revalidados en la baseline E-04; Route B aprobada sobre copia archivada aislada. Ningún resultado sustituye los recorridos integrales pendientes. Sin acceso operativo, cutover, campañas reales ni alteración del dataset/splits o hashes históricos.

[Informe anterior preservado](e10_10_5e4_evidence/previous_reports/e10_10_5e_integration_results.md).
