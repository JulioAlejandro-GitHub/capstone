# Aislamiento transaccional de pruebas

Las pruebas PostgreSQL Docker establecen `TEST_EXECUTION=true` y
`TEST_ISOLATION_MODE=transaction`. Una conexión compartida abre la transacción, los
repositorios reciben esa conexión y el teardown ejecuta rollback incluso ante excepción.

Los datos usan UUID nuevos y marcas explícitas. Cuando se requiere DDL, se usa un schema
temporal validado y se garantiza su eliminación. Una prueba que abra transacciones
independientes sin restauración completa queda bloqueada. El marker vigente es
`requires_docker_postgres`.
