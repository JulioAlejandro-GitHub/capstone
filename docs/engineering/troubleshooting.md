# Troubleshooting

- `DATABASE_URL es obligatorio`: revise la inyección de Compose en backend y ML.
- `Base rechazada`: confirme que la conexión interna apunta únicamente a `db:5432`.
- `/ready` 503: revise por componente DB, migrations o storage.
- Alembic incompatible: no haga stamp; restaure/complete 001–029 y ejecute el verificador.
- Frontend 401: vuelva a ingresar; el token en `localStorage` se elimina ante
  autenticación fallida y se revalida con `/api/v1/auth/me` al recargar.
- Docker Compose es el único runtime oficial; consulte
  [el contrato PostgreSQL](postgresql_docker_single_instance.md).
