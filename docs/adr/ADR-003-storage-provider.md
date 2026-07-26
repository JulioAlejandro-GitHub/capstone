# ADR-003: StorageProvider

- Estado: Aceptado
- Contexto/problema: paths filesystem están acoplados a DB/API.
- Decisión: interfaz `StorageProvider`, implementación inicial `LocalStorageProvider`, URI lógica, SHA-256, create-only original y artifacts versionados; PostgreSQL no guarda bytes.
- Alternativas: paths directos, BYTEA, S3 inmediato; rechazadas por portabilidad, escala o alcance.
- Positivas: inmutabilidad y migración futura sin cambiar API.
- Negativas: consistencia DB/filesystem y reconciliador.
- Riesgos/mitigación: orphan/missing/traversal; prepare-finalize, canonicalización y reconciliation.
- Compatibilidad: adapter para artifact service/releases y paths legacy.
- Revisión futura: adopción MinIO/S3.
- Componentes/prompts: storage/ingest/artifacts; P3/P4.
