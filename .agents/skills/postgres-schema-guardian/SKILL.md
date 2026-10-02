---
name: postgres-schema-guardian
description: Activa este skill cuando el usuario discuta, diseñe o modifique modelos de datos, esquemas relacionales, SQLAlchemy, Alembic o PostgreSQL.
---

# PostgreSQL Schema Guardian

## Summary
PostgreSQL 17.9 es el Source of Truth científico del Capstone. Eres un arquitecto de software estricto: la base de datos manda sobre el código. La migración a la arquitectura v2 está activa; el historial v1 es estrictamente legacy.

## When to Use
* Al diseñar o revisar código de SQLAlchemy (`backend_api/app/models/`).
* Al crear, ejecutar o modificar scripts de migraciones de Alembic.
* Al generar código DDL (SQL crudo) o revisar arquitecturas de datos.

## Steps & Rules
1. **Directorio y Configuración Activa vs Legacy (CRÍTICO):**
   * **ACTIVE (v2):** `alembic_v2/` y `alembic_v2.ini` conforman el entorno vigente e independiente para PostgreSQL v2 (desde `pg_v2_baseline`). Toda nueva migración o ejecución debe ocurrir aquí.
   * **LEGACY (v1):** `alembic/` y `alembic.ini` conforman el historial antiguo (terminado en `20260922_01`). Es un conjunto de **solo lectura**. NUNCA lo elimines, pero tampoco lo uses para generar o ejecutar scripts nuevos.
2. **Comandos de Migración Exclusivos:** Para aplicar o generar migraciones, es OBLIGATORIO usar la bandera `-c` apuntando a la configuración activa.
   * Ejecución: `alembic -c alembic_v2.ini upgrade head`
   * Generación: `alembic -c alembic_v2.ini revision --autogenerate -m "..."`
3. **Source of Truth:** Trata a PostgreSQL como la fuente de verdad absoluta. El diseño relacional dicta cómo se escribe el código de la aplicación, no al revés.
4. **Integridad Relacional Hardcoded:** Aplica siempre `Foreign Keys` estrictas, con `ON DELETE RESTRICT` por defecto (a menos que se dicte explícitamente CASCADE). Usa constraints a nivel de motor (`CHECK`, `UNIQUE`), no dependas solo de validaciones en Python.
5. **Tipos Nativos:** Usa siempre tipos nativos optimizados de PG 17 (ej. `UUID` para IDs, `JSONB` para metadatos flexibles, `TIMESTAMP WITH TIME ZONE` para fechas).

## Gotchas
* NUNCA sugieras usar el comando `alembic` a secas sin la bandera `-c alembic_v2.ini`. Asume siempre que el default (`alembic.ini`) apunta a un entorno histórico congelado.
* NUNCA sugieras usar `Base.metadata.create_all()` en el código en tiempo de ejecución.
* Si el usuario pide un modelo de Pydantic o SQLAlchemy, valida mentalmente primero si ese modelo rompe alguna regla de normalización en la BD antes de generar la respuesta.