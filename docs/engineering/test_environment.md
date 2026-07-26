# Entorno de test

```bash
make test-db-up
make test-db-bootstrap
make test-backend
make test-frontend
make test-db-down
```

La guarda exige `APP_ENV=test`, autorización de reset, nombre con `test`, host allowlisted y confirmación efímera. Nunca reemplace estos valores por una base personal.
