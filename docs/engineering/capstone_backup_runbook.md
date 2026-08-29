# Runbook de backup de Capstone

Defina opcionalmente `CAPSTONE_BACKUP_DIR` en una ruta controlada del host y ejecute:

```bash
make db-backup
```

El wrapper ejecuta las herramientas de backup dentro del servicio `db`, transmite el dump
custom hacia el destino controlado, aplica permisos restrictivos, rechaza archivos vacíos,
valida el catálogo e informa SHA-256 sin mostrar credenciales.

La restauración requiere autorización, ventana de mantenimiento y destino explícito. Este
repositorio no crea automáticamente otra base para ensayarla.
