# Seguridad

El proyecto está diseñado para desarrollo científico local, con controles
fail-closed y datos pseudonimizados. No debe exponerse directamente a Internet
ni tratarse como sistema clínico certificado.

## Autenticación y sesión

- La API usa `AUTH_MODE=local_jwt`, hashing Argon2 y expiración configurable.
- `JWT_SECRET` es obligatorio y no tiene valor por defecto.
- La SPA guarda el token en `localStorage` para restaurar la sesión al recargar;
  cerrar sesión lo elimina. Esto implica que cualquier vulnerabilidad XSS
  podría leerlo: no introduzca HTML no confiable ni registre tokens.
- El backend, no el frontend, valida JWT, roles y ownership en cada operación.
- CORS acepta únicamente orígenes HTTP(S) explícitos; `*` se rechaza.

Los roles, permisos y respuestas 401/403 se detallan en
[`engineering/authentication_rbac.md`](engineering/authentication_rbac.md) y
[`adr/ADR-013-stage2-security-rbac.md`](adr/ADR-013-stage2-security-rbac.md).

## Datos y auditoría

- Casos, pacientes, muestras e imágenes usan identificadores públicos
  pseudonimizados. No incluya nombres, correo, teléfono, documento nacional ni
  otros identificadores directos en metadata libre.
- Mutaciones sensibles generan auditoría en la misma transacción. Los eventos
  se agregan; no se reescriben para corregir historial.
- Las respuestas públicas omiten contraseñas, tokens, `DATABASE_URL`, paths de
  checkpoints y claves físicas de storage.
- Los logs usan correlation ID y deben conservar redacción de secretos y URLs.

Consulte [identidad de ingesta](architecture/image_ingestion_identity.md),
[`engineering/patient_sample_identifiers.md`](engineering/patient_sample_identifiers.md)
y [`engineering/logging_observability.md`](engineering/logging_observability.md).

## Imágenes y storage

La API recibe archivos por streaming, limita bytes/píxeles, valida con Pillow,
calcula SHA-256 en backend y sólo acepta formatos declarados. Storage usa claves
relativas contenidas bajo `STORAGE_ROOT`; se rechazan rutas absolutas, `..`,
bytes nulos y symlinks. Originales, crops y explicaciones no deben servirse como
archivos estáticos públicos.

Detalles: [`engineering/image_security_validation.md`](engineering/image_security_validation.md),
[`engineering/local_storage.md`](engineering/local_storage.md),
[`engineering/cell_crop_storage.md`](engineering/cell_crop_storage.md) y
[`engineering/cell_gradcam.md`](engineering/cell_gradcam.md).

## Configuración segura

`.env` está ignorado por Git; la plantilla raíz `.env.example` es la única para
API/ML y sólo define nombres/defaults no secretos. `frontend/.env.example`
contiene únicamente variables públicas de build Vite. No confirme dumps,
backups ni credenciales. Mantenga
`ALLOW_DATABASE_DROP=false`, `ALLOW_PUBLIC_SCHEMA_DROP=false`,
`INCLUDE_STACKTRACE=false` y no deshabilite auth salvo una autorización local
explícita. El runbook está en
[`engineering/security_runbook.md`](engineering/security_runbook.md).
