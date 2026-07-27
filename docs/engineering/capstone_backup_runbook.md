# Runbook de backup de Capstone

Defina `DATABASE_URL` local y, opcionalmente, `CAPSTONE_BACKUP_DIR` fuera del repositorio.
Ejecute `make db-backup`. El comando crea un dump custom timestamped, comprueba que no esté
vacío, valida su catálogo con `pg_restore --list` e informa SHA-256 sin imprimir password.

Emergencia: detenga escrituras de aplicación, verifique identidad y backup, y use
`pg_restore` según el procedimiento del administrador. La restauración requiere autorización
explícita y un destino decidido; nunca se ensaya creando automáticamente otra base.
