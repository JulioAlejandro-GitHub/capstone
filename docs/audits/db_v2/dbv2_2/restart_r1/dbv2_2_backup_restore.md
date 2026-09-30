# DBV2.2 — Backup/restore

PASS. pg_dump PostgreSQL 17.9 produce structural_backup.sql y technical_state_backup.sql. El segundo contiene exclusivamente alembic_version y experiment_execution_gate. Ningún dato legacy/dataset/usuario se respalda o transfiere.

Restore en otra base nueva PostgreSQL 17.9 mediante conexión autenticada capstone_v2_migrator. Se repone explícitamente la ACL de base, que pg_dump sin --create no incluye. Se verifica catálogo completo normalizado, ownership/ACL, secuencias, extensiones y head pg_v2_baseline. Resultado: backup_restore.json, cero diferencias; hashes de backups incluidos.

Diagnóstico preservado: backup_restore_initial_owner_mismatch.json. Restaurar como postgres hacía que pgcrypto perteneciera a postgres; se corrigió el rol del procedimiento de restore y se repitió en otra base vacía. No se cambió la baseline ni se ampliaron permisos para resolverlo.
