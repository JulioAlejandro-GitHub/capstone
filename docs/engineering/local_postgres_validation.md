# Gate PostgreSQL local

`make db-status`, `make db-migrate-check` y `make test-db` forman el gate local.
`/ready` exige conexión, identidad de base, Alembic current=head y storage accesible mediante
comprobaciones de solo lectura. El resultado se reporta como `LOCAL_POSTGRES_GATE`; CI remoto
reporta por separado `REMOTE_CI_READY`.
