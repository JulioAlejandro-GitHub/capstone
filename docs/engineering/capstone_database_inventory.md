# Inventario de la base Capstone

Inventario de solo lectura del 2026-07-26:

- servicio: Homebrew `postgresql@17`, una instancia local activa;
- host/puerto: `127.0.0.1:5432`;
- versión: PostgreSQL 17.9, arm64;
- usuario observado: `julio`;
- base persistente Capstone: `malaria_experiments`;
- schema principal: `public`;
- tamaño aproximado: 548 MB;
- Alembic inicial: `20260726_01`; head del repositorio: `20260726_02`;
- tablas confirmadas: `runs`, `model_versions`, `stage2_model_publications`,
  `schema_migrations`, `alembic_version`, `users`, `roles`;
- `audit_events` no existía al inventariar, coherente con la revisión pendiente.

También se observó una base preexistente `malaria_experiments_test`. Este trabajo no la
creó, no la usa y no la modifica. Su retiro requiere una decisión administrativa separada;
la aplicación y sus scripts no mantienen una segunda conexión.

No fue posible confirmar un backup reciente solo mediante catálogo PostgreSQL. Todo upgrade
debe crear uno mediante `make db-backup`.
