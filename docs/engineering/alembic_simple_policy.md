# Política simple de Alembic

Las migraciones SQL 001–029 son inmutables. `20260726_00` representa la baseline histórica;
todo cambio posterior usa Alembic y una revisión aplicada nunca se edita. No se ejecutan
downgrades sobre Capstone.

Antes de upgrade: validar conexión e identidad, firma histórica y current/head; crear backup
custom completo y comprobarlo con `pg_restore --list`; ejecutar preflight transaccional
cuando sea posible. Después: comprobar current=head, smoke tests y `/ready`. Alembic no
reemplaza backups ni reconstruye el historial.
