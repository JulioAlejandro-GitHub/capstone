# E10.10.5E.2 — riesgos actuales

**E-02 aprobada, escritor corregido. E-03 bloqueante. Gate E bloqueado y no solicitado.**

- E-03: PostgreSQL prohíbe los roles calibration_default/calibration_selected cuando source_kind=e10, aunque la calibración exige esos roles. [Decisión específica y evidencia](e10_10_5e2_resolution.md#decisión-específica-solicitada).
- Procedencia TRAIN/EVALUATE sin productor conectado ni sellado integral. El contexto del probe es exclusivamente sintético.
- Finalización todavía lee training_results; el resumen legacy requiere separación v2. NULL y ausencia de fallback científico pendientes en el recorrido completo API/React.
- Pendientes los recorridos integrales de TRAIN local/Docker, VALIDATION/calibración, recuperación/reinicio/ACK real, concurrencia, publicación/linaje, historial, ensembles y XAI. [Matriz completa](e10_10_5e_integration_results.md).
- Compatibilidad legacy verificada sólo a nivel servicio/routing en E.2; regresión integral pendiente.
- E.1 sigue siendo la baseline certificada. No se autoriza cutover, campaña real, uso clínico ni acceso operativo. Dataset congelado y contratos D-01 a D-06/E-01 preservados.
