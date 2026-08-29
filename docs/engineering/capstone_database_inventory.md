# Inventario histórico de la base Capstone

> **Estado documental:** `HISTORICAL_AUDIT`
> **Uso operativo:** No.
> **Snapshot:** lectura de solo acceso del 2026-07-26.
> Entorno anterior retirado; la arquitectura vigente está en
> [PostgreSQL Docker](postgresql_docker_single_instance.md).

Hechos preservados del inventario:

- versión observada: PostgreSQL 17.9, arm64;
- usuario observado: `julio`;
- base persistente Capstone: `malaria_experiments`;
- schema principal: `public`;
- tamaño aproximado: 548 MB;
- Alembic inicial: `20260726_01`; head versionado entonces: `20260726_02`;
- tablas confirmadas: `runs`, `model_versions`, `stage2_model_publications`,
  `schema_migrations`, `alembic_version`, `users`, `roles`;
- `audit_events` no existía en ese snapshot.

También se observó otra base histórica, no creada ni usada por este trabajo. Su gestión
requería una decisión administrativa separada. Ese hecho no define la arquitectura actual
ni autoriza una segunda conexión.

No fue posible confirmar un backup reciente solo mediante catálogo. El procedimiento
vigente es `make db-backup`.
