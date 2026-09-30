# SWV2.1 — Autenticación de aplicación

## Por qué una prueba segura equivalente

`POST /api/v1/auth/login` exitoso requiere la contraseña del usuario preservado (no conocida ni solicitada) y **confirma escrituras** (`UPDATE users.last_login_at`, `INSERT audit_events`). SWV2.1 no inventa credenciales ni altera el usuario, por lo que ejecuta el mismo flujo por partes, dentro de `capstone_backend`, con el engine del backend (`capstone_v2_runtime`) — `scripts/db/swv21_backend.py auth`:

1. **Query de login real**: el texto SQL de `app.routes.auth.login` se verifica literalmente contra `inspect.getsource(login)` (falla si la ruta cambia). Se ejecuta con el username en mayúsculas (lookup `lower()`), en una transacción.
2. **Verificación argon2 real** de `verify_password` contra el hash preservado con una contraseña aleatoria → `False` (hash legible con el esquema configurado, `argon2id`). Hash nunca impreso.
3. **Privilegio de escritura del login**: el `UPDATE users SET last_login_at` exacto de la ruta afecta 1 fila → privilegio runtime suficiente. **ROLLBACK**.
4. **Sesión autenticada por HTTP real**: token emitido por `create_access_token` del backend (lo mismo que devuelve login tras verificar la contraseña) → `GET /api/v1/auth/me` → 200, mismo `id`/`username` que la fila, roles `["administrator"]`, 54 permisos, `insecure_local=false`. `current_principal` relee `users` desde PostgreSQL v2.

Resultado (`swv2_1_auth.json`): **PASS**. Token, username, hash y passwords no se registran.

## Integridad del usuario preservado

`swv2_1_check_post_auth.json` y `swv2_1_check_post_restart.json`: users/roles/user_roles = 1/1/1, activo 1, digest del `password_hash` = referencia privada SWV2.0 (**sin cambio**), hashes de transferencia de `roles`/`user_roles` = DBV2.4.

## Delta operacional encontrado a la entrada (no producido por SWV2.1)

El primer chequeo de continuidad detectó `ROW_CONTENT_DRIFT:users`. Diagnóstico READ ONLY:

| Hecho | Valor |
|---|---|
| `users.last_login_at` certificado (DBV2.4, leído del dump SWV2.0 verificado sha256 `353759cf…59358b`, sólo esa columna) | `2026-09-29 21:18:19.690154+00` |
| `users.last_login_at` actual | `2026-09-30 21:17:40.913955+00` |
| `audit_events` | 1 fila `USER_LOGIN_SUCCEEDED`, `POST /api/v1/auth/login`, `2026-09-30 21:17:40.916421+00` |
| Último chequeo SWV2.0 / commit SWV2.0 | 21:12:58Z / 21:15:18Z |
| hash `users` DBV2.4 recalculado restaurando **sólo** `last_login_at` | **igual** al `transfer_hash` certificado |
| digest del `password_hash` | igual a la referencia SWV2.0 |

Conclusión: un login real de la aplicación (backend aún como `julio`) ocurrió después del commit SWV2.0 y antes de SWV2.1. Única diferencia: `last_login_at` + 1 fila de auditoría. No es escritura científica, no altera usuario, roles ni hash. Además acredita un login exitoso real contra PostgreSQL v2. SWV2.1 fija ese estado de entrada (`ENTRY_DELTA` en `swv21_backend.py`); cualquier cambio adicional en `users` o `audit_events` hace fallar los chequeos — los chequeos post-auth y post-restart pasan, por lo que SWV2.1 no escribió.

Opcional para el usuario: un login interactivo en el frontend ya como `capstone_v2_runtime` (actualizará de nuevo `last_login_at` y añadirá un evento de auditoría, comportamiento normal de la aplicación).
