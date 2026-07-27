# API científica

Prefijo: `/api/v1/scientific`. Todas las rutas requieren Bearer JWT y permisos científicos.
Listados aceptan `limit` (1–200), `offset`, `status` y `search`, ordenados por
`created_at DESC`.

Familias CRUD sin DELETE:

- `/subjects`, `/subjects/{id}`, `/subjects/{id}/archive`
- `/cases`, `/cases/{id}`, `/cases/{id}/archive`
- `/cases/{id}/samples`, `/samples/{id}`, `/samples/{id}/archive`
- `/samples/{id}/slides`, `/slides/{id}`, `/slides/{id}/archive`
- `/slides/{id}/images`, `/images/{id}`, `/images/{id}/archive`
- `/cases/{id}/traceability`

Ejemplo de registro de imagen:

```json
{
  "image_code": "IMG-001",
  "storage_provider": "local",
  "storage_key": "scientific/case-01/img-001.png",
  "mime_type": "image/png",
  "file_size_bytes": 402133,
  "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "width_px": 2048,
  "height_px": 1536,
  "magnification": 100
}
```

La API responde 201 al crear; 200 al leer, actualizar o archivar; 401/403 por autenticación
o autorización; 404 por identidad/relación inexistente; 409 por duplicado, transición o
dependencia activa; y 422 por payload inválido.

Roles: administrator posee todo; researcher y operator leen/crean/actualizan/registran;
reviewer y read_only sólo leen. El archivado queda reservado al administrator.
