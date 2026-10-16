# Capstone Skills — reorganización propuesta

**Versión de trabajo:** 2026-10-16. Preparada a partir de las 8 skills recibidas; **no auditada contra el repositorio ni PostgreSQL actuales**.

## Skills activas (8)
- `fastapi-architecture-guardian`
- `execution-plane-guardian` (fusiona `hybrid-architecture-runtime`)
- `fullstack-coding-standards`
- `dataset-governance-guardian` (sustituye `ignorar-dataset-malaria`)
- `postgres-schema-guardian`
- `malaria-image-and-xai-guardian`
- `testing-audit-guardian`
- `capstone-http-sql-reuse` (nueva)

## Convención
`SKILL.md` contiene activación y reglas; `references/` contiene contratos, procedimientos y evidencia. Los `legacy-*` son históricos no normativos. Cada contrato debe identificar fuente de verdad, decisión, verificación, pruebas y fecha.

## Migración
1. Respaldar carpeta original.
2. Comparar skills activas y revisar las reglas nuevas.
3. Auditar referencias marcadas PENDIENTE contra código/DDL/tests; completar tablas de parámetros con defaults reales.
4. Reemplazar la carpeta de skills en el repositorio solo tras aprobación; actualizar referencias a los nombres renombrados.
5. Validar frontmatter, enlaces, activación y pruebas.

**No se modificó el repositorio del usuario.**
