# BD-v2 persistente

**BD-V2 PERSISTE PARA DBV2.4**

- PostgreSQL 17.9; imagen postgres:17.9.
- Database: `capstone_v2_isolated_persistent`; OID `16386`.
- Host lógico: `capstone_db_v2`. Endpoint local: `127.0.0.1:56440`.
- Contenedor: `1dc48428c6b938da6525754cc4f26d535814f1f8c101928487f7c0d630ce4971`.
- Cluster system_identifier: `7691366089693499436`.
- Volumen persistente: `capstone_v2_isolated_persistent_data`; driver local, exclusivo; PGDATA /var/lib/postgresql/data.
- Etiquetas: org.capstone.pgv2.lifecycle=persistent; org.capstone.pgv2.isolation=1a590188-5f24-4068-ab38-b77bb8c61e65.
- Estado final: running; restart policy unless-stopped. Sin bind de datos legacy ni almacenamiento tmpfs.

Antes y después del restart: head pg_v2_baseline, manifest `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb`, 104 tablas de aplicación más Alembic. Filas científicas/usuarios/fixtures: cero. Sólo alembic_version y experiment_execution_gate tienen su fila técnica aprobada.

El volumen NO fue eliminado. Se ejecutó docker stop y docker start sobre el mismo ID. No se ejecutó DROP DATABASE, docker rm, volume rm o compose down. No reconstruirlo en DBV2.4.

Autenticación de red SCRAM-SHA-256, puerto publicado únicamente en loopback. Roles migrador/runtime sin privilegios elevados ni memberships. Credenciales propias nuevas protegidas en `var/maintenance/dbv23_persistent/` (directorio 0700; archivos 0600), excluidas por .gitignore; ninguna contraseña se registra en evidencia. El pgpass de ese directorio permite acceso futuro autorizado sin modificar DATABASE_URL de la aplicación.

Descriptor no sensible: persistent_target.json. Inspección filtrada sin Env: persistent_storage_inspection.json. Identidad real: destination_identity.json. Instalación: destination_commands.jsonl. La utilidad dbv23_destination.py no ofrece ninguna operación de eliminación y rechaza reprovisionar un destino existente.
