# Autenticación y RBAC

El gate real usa exclusivamente `CAPSTONE_E2E_USERNAME` y `CAPSTONE_E2E_PASSWORD` privados.
Si faltan, login autorizado y `/auth/me` quedan BLOCKED; nunca se crean credenciales para
hacer pasar el gate. Usuarios deshabilitados se prueban con fixtures sintéticas revertidas.

`POST /api/v1/auth/login` entrega JWT corto y `GET /api/v1/auth/me` devuelve el
principal. Passwords usan Argon2 mediante `pwdlib`; JWT usa PyJWT/HS256
configurable. El frontend guarda únicamente el bearer en `localStorage`, lo
revalida mediante `/api/v1/auth/me` al recargar y lo elimina al cerrar sesión o
ante un fallo de autenticación. Esta persistencia mantiene la sesión entre
recargas, pero obliga a conservar los controles XSS y a no almacenar otros
datos sensibles junto al token.

|Rol|Acceso actual|
|---|---|
|administrator|Todos los permisos|
|researcher|Lectura y escritura científica; calidad, colas, detección, clasificación, revisión, explicabilidad, validación y auditoría limitada|
|operator|Lectura y ejecución científica, incluida ingesta, calidad, cola, detección y clasificación; sin review|
|reviewer|Lectura científica, revisión de detección/clasificación, Grad-CAM y anotación científica|
|read_only|Sólo lectura|

Los permisos implementados para subjects, cases, samples, slides, images,
quality, queue, cell detection, cell classification y scientific validation se
declaran en `app.security.Permission`; `ROLE_PERMISSIONS` es la fuente de verdad
de su asignación. Publicar, desactivar y cambiar disponibilidad Stage 2 están
protegidos por permisos centrales. `AUTH_MODE=disabled` sólo funciona en local
con opt-in visible.
