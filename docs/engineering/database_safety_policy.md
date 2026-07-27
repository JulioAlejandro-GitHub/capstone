# Política de seguridad de base

`DROP DATABASE`, `DROP SCHEMA public`, reset completo y truncado masivo están prohibidos.
La identidad real debe coincidir con el nombre de `DATABASE_URL`. Los nombres de schemas
temporales deben cumplir `^capstone_test_[a-z0-9_]{6,48}$`; se rechazan schemas del sistema,
caracteres especiales y nombres externos. Nunca se interpolan identificadores no validados.

La base histórica no se reconstruye ni se usan datos reales como fixtures.
