# Atomicidad de auditoría

Prompt 2.2.1 comprobó con PostgreSQL real que una FK inválida en `audit_events` aborta y
revierte la mutación dentro de la conexión compartida. La aprobación plena continúa
bloqueada hasta ejercitar cada repositorio crítico con su tabla de dominio y before/after.

Una mutación crítica y su `audit_event` deben compartir conexión y transacción:
before-state, mutación, after-state, evento y commit. Cualquier fallo revierte todo. Login
puede auditarse aparte. Está prohibido declarar éxito desde una conexión independiente.

Los adaptadores heredados que todavía abren su propia unidad de trabajo deben migrarse a una
conexión inyectada antes de considerar cerrado este control.
