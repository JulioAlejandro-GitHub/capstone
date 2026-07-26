# Troubleshooting

- `DATABASE_URL es obligatorio`: exporte la URL efímera/test o la de demo administrada.
- `Base rechazada`: confirme `APP_ENV=test`, `capstone_test`, puerto 55433 y los dos flags.
- `/ready` 503: revise por componente DB, migrations o storage.
- Alembic incompatible: no haga stamp; restaure/complete 001–029 y ejecute el verificador.
- Frontend 401: vuelva a ingresar; el token es deliberadamente sólo memoria.
- Docker no disponible: ejecute unit tests; registre la integración como no ejecutada.
