# Política de seguridad de base

Eliminar bases, eliminar el schema `public`, resetear la instancia o truncar globalmente
está prohibido. La identidad real debe coincidir con `DATABASE_URL`, cuyo destino permitido
es exclusivamente `db:5432`.

Los schemas temporales deben cumplir `^capstone_test_[a-z0-9_]{6,48}$`; se rechazan
schemas del sistema, caracteres especiales y nombres externos. Toda prueba de escritura
usa rollback o cleanup garantizado. No se crea otra base para pruebas.

Las operaciones se ejecutan mediante los targets y wrappers Docker versionados.

## Purga de datos por subsistema

`scripts/db/purge.py` (wrapper `scripts/db/purge.sh`, targets `make db-purge-plan` /
`db-purge-execute`) borra filas de un subsistema científico completo — `--dataset`,
`--run` y/o `--cell` — sin tocar el esquema. Reglas fijas:

- `users`, `roles`, `user_roles`, `audit_events`, `alembic_version` y `schema_migrations`
  no se tocan bajo ninguna combinación de flags.
- El modo por defecto es dry-run: sin `--yes` sólo reporta conteos.
- Ejecutar requiere `--yes` **y** `PURGE_DB_ALLOW_EXECUTION=1` **y** un backup PostgreSQL
  custom-format verificado (`CAPSTONE_VERIFIED_BACKUP` / `--backup`).
- Si un flag no solicitado tiene filas que dependen por FK de uno solicitado, el script
  aborta indicando qué flag falta; nunca borra en cascada un subsistema no pedido.
- Una transacción por subsistema; orden global `cell → run → dataset`.

Contrato completo y evidencia: [operations/subsystem_data_purge.md](../operations/subsystem_data_purge.md),
`docs/audits/cell_vs_microscopy_resolution_2026-09-08.md`,
`docs/audits/purge_script_verification_2026-09-08.md`.
