# Aislamiento transaccional de pruebas

Los tests PostgreSQL locales establecen `TEST_EXECUTION=true` y
`TEST_ISOLATION_MODE=transaction`. Una conexión compartida abre la transacción, los
repositorios reciben esa conexión, y el teardown ejecuta rollback incluso ante excepción o
assertion fallida. Los datos usan UUID nuevos y marcas explícitas de test.

Un test que abra conexiones independientes o confirme internamente no pertenece a este gate
hasta ser adaptado a una unidad de trabajo compartida. Se marca `requires_local_postgres`;
CI remoto no simula este gate.
