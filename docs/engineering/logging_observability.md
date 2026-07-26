# Logging y observabilidad

Cada request recibe o genera un UUID en `X-Correlation-ID`, devuelto en headers y errores. JSON logs incluyen método, path sin query, status, duración, ambiente e ID. La sanitización elimina password, Authorization, cookies, JWT/token y DATABASE_URL. `/health` no toca DB; `/ready` comprueba DB, Alembic y storage.
