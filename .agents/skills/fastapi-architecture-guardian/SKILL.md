---
name: fastapi-architecture-guardian
description: Aplicar separación de rutas, servicios, repositorios y trazabilidad clínica en FastAPI.
---

# fastapi-architecture-guardian

## Reglas
- Rutas: validación HTTP, dependencias y respuestas; servicios: reglas de negocio; repositorios: acceso persistente. Inspeccionar el patrón real antes de modificarlo.
- Preservar caso → muestra → frotis → imagen y no confundir identidades.
- Usar contratos Pydantic cuando corresponda; no exponer entidades ORM accidentalmente.
- Reutilizar operaciones HTTP/SQL existentes consultando `capstone-http-sql-reuse`.
- No imponer bloqueos de pipeline no verificados ni sustituir la integridad PostgreSQL.

## Referencias
- `references/backend-lineage.md` para linaje y contratos HTTP.
- `references/legacy-original.md` para el texto anterior, sujeto a auditoría.
