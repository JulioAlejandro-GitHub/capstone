# ADR-001: Cola de jobs PostgreSQL

- Estado: Aceptado
- Contexto/problema: `image_analysis_jobs` existe, pero `TraceableInferenceService.infer()` es síncrono y no hay worker.
- Decisión: PostgreSQL será cola MVP con `READ COMMITTED`, claim `FOR UPDATE SKIP LOCKED`, orden priority DESC/created ASC, lease, heartbeat, fencing por attempt, máximo tres intentos, backoff, cancelación cooperativa y eventos append-only.
- Alternativas: Redis/Celery/RQ/Dramatiq/RabbitMQ y ejecución HTTP; rechazadas por decisión de alcance y falta de recuperación.
- Positivas: una fuente durable/transaccional, operación simple.
- Negativas: polling DB, reaper y tuning propios.
- Riesgos/mitigación: contención/doble ejecución; índices, transacciones cortas, leases y claves naturales.
- Compatibilidad: jobs legacy permanecen; contrato nuevo es aditivo.
- Revisión futura: throughput sostenido exceda objetivos o PG afecte cargas principales.
- Componentes/prompts: queue, worker, jobs; P2/P3/P6.
