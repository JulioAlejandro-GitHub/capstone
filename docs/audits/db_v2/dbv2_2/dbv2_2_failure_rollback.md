# DBV2.2 — Fallo y rollback

Instalación Alembic con fallo inyectado: NOT RUN — BLOCKED.

La reproducción mínima se ejecutó dentro de BEGIN/ROLLBACK; confirmó 42703 para ambas tablas. Al terminar quedaron cero esquemas dbv22_contract_probe. Esto prueba únicamente limpieza de la reproducción y no atomicidad de una baseline completa.
