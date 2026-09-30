# DBV2.2 — Fallo inyectado / rollback

PASS. Se reutilizó scripts/db/v2_inject_failure.py: hook SQLAlchemy externo a la baseline, error PostgreSQL 1/0 después de 500 DDL reales. La salida captura objetos parciales y cero filas de head antes del fallo. failure_rollback.json contiene stderr y retorno no cero; catálogo posterior idéntico al vacío inicial, sin ledger falso ni funciones/tablas parciales.

Se repitió upgrade normal en esa base vacía; failure_recovery.json acredita igualdad de catálogo completo. No se modificó código de baseline ni se desactivaron guardas para inyectar el fallo.

Adicionalmente e04_edges_dbv22.json demuestra rechazo al COMMIT de miembro default huérfano y ausencia de su run tras rollback. No equivale a tests de concurrencia ni a ResultService E2E, fuera de esta fase.
