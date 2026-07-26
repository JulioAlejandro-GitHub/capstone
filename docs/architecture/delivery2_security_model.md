# Modelo de seguridad y RBAC — Entrega 2

## Autenticación académica

MVP: identidad local administrada, contraseña con hash resistente, sesión/JWT de corta duración, rotación/revocación y HTTPS en despliegue. El diseño admite OIDC posterior mapeando `subject` externo al mismo usuario interno. Headers `actor`/`X-Requester` dejan de ser identidad y pasan a metadata opcional.

## Roles y permisos

Leyenda: ✓ permitido; A permitido y auditado como acción sensible; — denegado.

|Acción|administrator|researcher|operator|reviewer|read_only|
|---|:---:|:---:|:---:|:---:|:---:|
|Crear subject/sample|A|✓|A|—|—|
|Cargar imagen / ejecutar QC|A|✓|A|—|—|
|Crear job / seleccionar publicados|A|A|A|—|—|
|Cambiar prioridad / cancelar / retry|A|—|A|—|—|
|Publicar/desactivar modelo|A|—|—|—|—|
|Modificar `stage2/default`|A|—|—|—|—|
|Consultar imágenes/resultados permitidos|✓|✓|✓|✓|✓|
|Revisar célula/frotis, excluir, anotar|A|—|—|A|—|
|Exportar reporte|A|A|A|A|✓ según scope|
|Consultar auditoría|A|✓ limitada|—|propia|—|
|Administrar usuarios/policies|A|—|—|—|—|

Principio de mínimo privilegio; un usuario puede tener varios roles, pero permisos se evalúan server-side por recurso/datasource. Corrección general requiere reviewer; administrator puede operar de emergencia con motivo.

## Audit events

Obligatorios para publicación/desactivación, default/rollback, prioridad, cancel/retry, selección de modelos, review/correction/exclusion, resultado general, export, eliminación regenerable, cambios de policy/roles. Campos: event ID/type, actor autenticado, roles, resource, before/after, reason, request/correlation ID, IP/user-agent minimizados, timestamp, outcome y error. Append-only y `ON DELETE RESTRICT`.

## Archivos y API

- Multipart con límites, MIME/firma/decodificación, UUID y streaming.
- Access reference opaca, corta y autorizada; no path físico.
- Parametrización SQL y allowlists.
- CORS por perfil y sólo métodos/orígenes necesarios.
- 401 sin sesión; 403 sin permiso; 404 puede ocultar recursos ajenos.
- Rate limit para login, upload, report y XAI on-demand.
- No registrar tokens, contraseñas, paths, PII ni bytes en logs.

## Pseudonimización

`subjects.id` es UUID interno. Un `pseudonym` no reversible y único puede almacenarse; identificadores clínicos externos legibles quedan fuera del MVP. Paths usan UUID. Metadata es allowlist y nunca acepta campos libres con PII sin revisión.

## Amenazas y controles

Traversal/symlink → provider confinado; image bomb → límites de píxeles/bytes; IDOR → autorización por recurso; job duplication → idempotency; worker spoofing → credencial técnica y lease/fencing; model substitution → publication/default + SHA; review tampering → append-only; diagnostic misuse → vocabulario, disclaimers, roles y export control.

