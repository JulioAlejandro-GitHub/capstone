# Autenticación y RBAC

`POST /api/v1/auth/login` entrega JWT corto y `GET /api/v1/auth/me` devuelve el principal. Passwords usan Argon2 mediante `pwdlib`; JWT usa PyJWT/HS256 configurable. El token vive sólo en memoria del tab: reduce persistencia ante XSS, pero se pierde al recargar.

|Rol|Acceso actual|
|---|---|
|administrator|Todos los permisos|
|researcher|Lectura científica, inferencia y auditoría limitada|
|operator|Lectura e inferencia|
|reviewer|Lectura; permisos de review reservados|
|read_only|Sólo lectura|

Permisos futuros de subjects/samples/images/quality/analysis/reviews/reports quedan reservados documentalmente. Publicar, desactivar y cambiar disponibilidad Stage 2 están protegidos por permisos centrales. `AUTH_MODE=disabled` sólo funciona en local con opt-in visible.
