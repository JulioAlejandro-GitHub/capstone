# Pruebas y gates

Las pruebas se dividen por riesgo. No se fijan conteos en la documentación
canónica porque cambian con el producto; cada comando debe terminar con código
cero y sin tests fallidos.

## Gates principales

| Gate | Comando | Dependencias |
|---|---|---|
| Validación de repo | `make validate` | shell y toolchains instalados |
| Backend unitario | `make test-backend` | Python, sin PostgreSQL para el subconjunto normal |
| Backend integración | `make test-backend-integration` | PostgreSQL local configurado |
| Frontend | `make test-frontend` | Node 22/npm 10; tests y build |
| ML completo | `make test-ml` | entorno ML Python 3.12 |
| Todo lo no-ML | `make test` | backend unitario + frontend |
| Formato del diff | `make lint` | Git |

El CI ejecuta documentación/configuración, backend unitario, head Alembic
estático, frontend y un subconjunto ML rápido. No inicia PostgreSQL ni Docker;
la integración con base real es un gate local explícito.

## PostgreSQL

```bash
TEST_EXECUTION=true \
TEST_ISOLATION_MODE=transaction \
PYTHONPATH=backend_api \
malaria_dl_local_project/.venv/bin/python -m pytest backend_api/tests -m requires_local_postgres
```

Los tests usan la misma `DATABASE_URL` y rollback externo. Los que requieren
DDL usan un schema temporal de nombre validado; `make test-schema-clean`
comprueba que no queden schemas huérfanos. No se usa `TEST_DATABASE_URL`, no se
resetea la base y nunca se elimina `public`.

`make test-fresh-schema` crea un único schema temporal validado, ejecuta allí el
bootstrap SQL y toda la cadena Alembic, compara su estructura con la proyección
de `public`, prueba seeds y smoke HTTP, y elimina el schema en `finally`. Es un
gate PostgreSQL explícito y no se ejecuta dentro de `make test`.

Vea [`engineering/test_transaction_isolation.md`](engineering/test_transaction_isolation.md),
[`engineering/temporary_schema_testing.md`](engineering/temporary_schema_testing.md)
y [`engineering/test_environment.md`](engineering/test_environment.md).

## Alembic

El gate estático comprueba compilación y una cadena lineal con head único
(`20260804_01` al consolidar esta documentación). Deriva el head del grafo y no
mantiene una constante que quede obsoleta. Antes de migrar una base local
ejecute:

```bash
make db-migrate-check
```

La validación transaccional completa se integra en `make db-migrate`. No use un
upgrade real sólo para satisfacer un test. Consulte [database.md](database.md).

## Qué verificar al cambiar el producto

- Contratos de request/response y redacción de datos internos.
- RBAC, ownership, auditoría y rollback ante errores.
- Idempotencia y concurrencia de transiciones.
- Recarga/deep links del frontend, estados 401/403/404 y accesibilidad.
- Mapping, preprocessing, threshold, checksum y determinismo en ML.
- Storage: containment, inmutabilidad, reconciliación y limpieza de staging.

No convierta una validación manual histórica en evidencia permanente: registre
el comando, el entorno y el resultado actual en la entrega correspondiente.
