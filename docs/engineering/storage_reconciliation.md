# Reconciliación de storage

`scripts/storage/reconcile.py` es siempre dry-run: detecta registros sin archivo,
huérfanos, tamaño/checksum inválido, key insegura y conteos de lote discordantes.
`scripts/storage/cleanup_staging.py` también es dry-run por defecto y requiere
`--apply`; sólo elimina archivos regulares más antiguos que
`STAGING_RETENTION_HOURS` y nunca sigue symlinks.
