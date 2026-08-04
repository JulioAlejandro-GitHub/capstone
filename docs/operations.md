# Operaciones locales

El único runtime soportado es local: PostgreSQL persistente, API Python, SPA
Vite y storage de archivos bajo la raíz configurada. No hay stack Docker ni un
procedimiento de despliegue remoto mantenido por este repositorio.

## Arranque y verificación

1. Cargue `.env` y ejecute `make db-status`.
2. Inicie la API con `./scripts/start_backend_api.sh`.
3. Verifique `/health` y `/ready`.
4. Inicie la SPA con `npm --prefix frontend run dev`.
5. Compruebe login, `/modelo-ia/resumen` y `/frotis/analizar`.

El script de API usa el entorno de `malaria_dl_local_project`, valida las
dependencias API/ML y carga `.env`. Si readiness falla, no continúe con
operaciones que escriban: revise conexión PostgreSQL, head Alembic y storage.

## Backup y migraciones

```bash
make db-status
make db-backup
make db-migrate-check
make db-migrate
```

Los backups se guardan por defecto fuera del repositorio, bajo el directorio
temporal del sistema, y se verifican con `pg_restore --list` y SHA-256. Para una
retención real configure `CAPSTONE_BACKUP_DIR` en una ubicación protegida y
pruebe restauración fuera de la base activa. Vea
[`engineering/capstone_backup_runbook.md`](engineering/capstone_backup_runbook.md).

## Storage

Ejecute reconciliaciones en modo lectura antes de cualquier corrección:

```bash
malaria_dl_local_project/.venv/bin/python scripts/storage/reconcile.py
malaria_dl_local_project/.venv/bin/python scripts/storage/reconcile_cell_crops.py
malaria_dl_local_project/.venv/bin/python scripts/storage/reconcile_cell_explanations.py
malaria_dl_local_project/.venv/bin/python scripts/storage/cleanup_staging.py
```

`cleanup_staging.py` es dry-run por defecto; `--apply` elimina archivos
elegibles y requiere una decisión operacional explícita. No borre originales,
crops, Grad-CAM ni directorios de storage para resolver inconsistencias. Revise
[`engineering/storage_reconciliation.md`](engineering/storage_reconciliation.md).

## Diagnóstico

- **API no inicia:** confirme Python 3.12, dependencias y variables obligatorias.
- **`/ready` falla:** use `make db-status`; compare current con head y revise
  permisos/ruta de storage.
- **401:** la sesión pudo expirar; autentique de nuevo. No reutilice tokens de
  logs o herramientas.
- **403:** el usuario está autenticado pero no tiene rol/ownership suficiente.
- **Modelo productivo no disponible:** confirme que exista exactamente una
  publicación Stage 2 activa y revise sus validaciones técnicas; no active un
  fallback.
- **Archivo ausente:** ejecute reconciliación dry-run y preserve la evidencia de
  base antes de reparar.

La guía extendida está en
[`engineering/troubleshooting.md`](engineering/troubleshooting.md) y los logs en
[`engineering/logging_observability.md`](engineering/logging_observability.md).

## Cambios prohibidos durante una incidencia

No resetee la base, no ejecute downgrades, no edite migraciones aplicadas, no
borre storage y no publique un modelo para ocultar un fallo de resolución. Tome
backup, capture correlation IDs y trabaje con cambios reversibles y auditables.
