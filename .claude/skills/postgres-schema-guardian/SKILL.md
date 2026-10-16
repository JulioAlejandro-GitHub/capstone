---
name: postgres-schema-guardian
description: Proteger esquema PostgreSQL actual integridad relacional y persistencia científica sin preflight de versiones.
---

# postgres-schema-guardian

## Reglas
- El esquema PostgreSQL actual es el único soportado. Ejecutar SQL directamente, sin verificaciones de versión/revisión Alembic ni compatibilidad histórica.
- Si falla SQL estructural, corregir SQL; no incorporar fallback legacy.
- Mantener PK, FK, UNIQUE, CHECK, NOT NULL, triggers y transacciones reales.
- Validar contra esquema efectivo antes de proponer nombres de tablas o columnas; no inventar contratos.
- Conservar historial científico inmutable y relaciones de ejecución.
- Para localizar operaciones reutilizables consultar `capstone-http-sql-reuse`.

## Referencias
- `references/postgres-policy.md`
- `references/legacy-original.md` (histórica).
