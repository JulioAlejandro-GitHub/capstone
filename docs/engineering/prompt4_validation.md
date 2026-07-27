# Validación de Prompt 4

La validación cubre revisión Alembic, constraints, JWT/RBAC, identidad,
multipart/streaming, metadata backend-only, formatos, duplicados, contenido,
auditoría, compensación, perfil NIH-NLM, frontend, scripts y ausencia de
residuos. Los tests PostgreSQL usan rollback externo y los de archivos una raíz
temporal. No se usa Docker ni otra base.

Los resultados finales de comandos y conteos se registran en el informe de
entrega del agente.
