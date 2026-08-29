# Política de seguridad de base

Eliminar bases, eliminar el schema `public`, resetear la instancia o truncar globalmente
está prohibido. La identidad real debe coincidir con `DATABASE_URL`, cuyo destino permitido
es exclusivamente `db:5432`.

Los schemas temporales deben cumplir `^capstone_test_[a-z0-9_]{6,48}$`; se rechazan
schemas del sistema, caracteres especiales y nombres externos. Toda prueba de escritura
usa rollback o cleanup garantizado. No se crea otra base para pruebas.

Las operaciones se ejecutan mediante los targets y wrappers Docker versionados.
