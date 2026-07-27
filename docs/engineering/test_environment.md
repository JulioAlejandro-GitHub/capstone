# Entorno de test

```bash
make db-status
make test-db
make test-frontend
make test-schema-clean
```

No existe ambiente persistente de test ni segunda URL. Las escrituras se revierten; los
schemas temporales son la excepción controlada.
