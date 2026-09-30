# Usuario preflight READ ONLY

PASS estructural para roles, users y user_roles: 15 columnas. Se conserva ID, username/email, password_hash, estado, timestamps, disabled_at y relaciones originales, sin cambiar algoritmo ni credenciales.

Origen: un usuario activo, una relación user_roles, cinco definiciones de rol; una definición de rol está referenciada. Plan mínimo: copiar ese usuario y su relación, y sólo roles referenciados; no se fabrican usuarios/contraseñas ni se promueve ningún rol. El filtro de roles no cambia ninguna asignación del usuario.

No se leyó el valor de password_hash. Sólo catálogo de columna (text y nulabilidad) y conteos agregados de estado/relaciones. El plan futuro enumera password_hash como columna de copia, sin literales ni salida de valor. La validación futura es booleana mediante diferencias de filas; errores muestran sólo el nombre de tabla. No enviar esos valores a logs/evidencia.

No se prueba login HTTP/JWT/API/frontend. Esta fase sólo acredita preservación estructural. audit_events existe y su FK actor_user_id→users es una dependencia saliente de audit_events: copiar usuarios no obliga a copiar sus eventos hijos. transfer_required=false.

Tablas directas: 3. Manejo técnico de columnas: 0. Transformaciones semánticas: 0. Registros transferidos: 0.
