# E10.10.5E.2 — escritor E-02 corregido; integración detenida por E-03

**Baseline E.1 preservada. Integración incompleta. Gate E bloqueado y no solicitado.**

La revisión reconocida selecciona el destino: legacy conserva runs.parameters.training_results; v2 retorna tras la proyección tipada en la misma transacción que canonical_event. Sin fallback por excepción ni segundo JSONB de resultados.

Se reprodujo una incompatibilidad nueva: la pareja de calibración requiere roles calibration_default y calibration_selected, pero el CHECK de origen E10 sólo admite training_validation_final. Se detuvo la integración conforme al apartado 9; no se modificó la baseline ni se reclasificaron hechos nuevos como legacy.

[Implementación, pruebas y propuesta E-03](e10_10_5e2_resolution.md) · [Matriz pendiente](e10_10_5e_integration_results.md) · [Informe anterior](e10_10_5e2_evidence/previous_reports/e10_10_5_implementation.md).
