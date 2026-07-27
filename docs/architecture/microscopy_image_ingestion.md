# Arquitectura de ingesta microscópica

FastAPI recibe multipart por chunks en `.staging`, calcula SHA-256 incremental,
decodifica el temporal y extrae metadata. Tras validar todo, inserta metadata,
mueve atómicamente cada original y audita antes del commit.

Ante validación fallida se elimina staging y se revierte la transacción. Ante
fallo PostgreSQL, filesystem, auditoría o commit se eliminan finales promovidos.
Persiste una ventana residual movimiento/commit ante caída abrupta; UUID, claves
deterministas, reconciliación dry-run y limpieza de staging la mitigan.
