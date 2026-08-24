# Troubleshooting

- `DATABASE_URL es obligatorio`: exporte privadamente la URL de `malaria_experiments`.
- `Base rechazada`: confirme `APP_ENV=development` e identidad local sin imprimir secretos.
- `/ready` 503: revise por componente DB, migrations o storage.
- Alembic incompatible: no haga stamp; restaure/complete 001–029 y ejecute el verificador.
- Frontend 401: vuelva a ingresar; el token en `localStorage` se elimina ante
  autenticación fallida y se revalida con `/api/v1/auth/me` al recargar.
- Docker no es requisito del runtime oficial: backend, frontend y PostgreSQL se
  ejecutan localmente. Los entrypoints Docker opcionales se diagnostican por
  separado y no sustituyen el gate local.
