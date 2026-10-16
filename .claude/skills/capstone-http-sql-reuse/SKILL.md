---
name: capstone-http-sql-reuse
description: Localizar y reutilizar operaciones HTTP SQL y contratos existentes antes de agregar nuevas implementaciones.
---

# capstone-http-sql-reuse

## Procedimiento obligatorio
1. Identificar operación, identidad, parámetros y consumidores existentes.
2. Buscar primero rutas, servicios, repositorios, clientes frontend y consultas SQL ya implementadas.
3. Comprobar contrato real: inputs, outputs, autenticación, transacciones, paginación y semántica de errores.
4. Reutilizar el punto de entrada apropiado; evitar duplicar SQL, fetch, endpoints o modelos de respuesta.
5. Si falta una operación, implementarla en la capa correcta con pruebas; documentar diferencia respecto al contrato existente.
6. PostgreSQL actual es el único esquema; no introducir preflight de versiones ni compatibilidad legacy.

## Referencias
- `references/discovery-checklist.md`
- `references/operation-inventory.md` (plantilla a completar mediante auditoría).
