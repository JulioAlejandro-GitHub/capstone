# API de carga de imágenes

- `GET /api/v1/scientific/subjects/lookup?subject_code=…`
- `POST /api/v1/scientific/subjects/auto`
- `GET /api/v1/scientific/subjects/{id}/samples`
- `POST /api/v1/scientific/subjects/{id}/samples/auto`
- `POST /api/v1/scientific/images/upload`
- `GET /api/v1/scientific/images/{id}/content`

Upload usa `files`, modos existing/automatic_new y origen. Campos derivados
(autor, checksum, key, MIME, dimensiones, estado y tiempos) producen 422 si el
cliente los intenta controlar. Content exige JWT/RBAC, no sirve archivados y
envía nosniff, no-store, longitud, disposition y ETag SHA-256.
