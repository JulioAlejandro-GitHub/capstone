# ADR-013: Seguridad y RBAC Etapa 2

- Estado: Aceptado
- Contexto/problema: API actual no autentica y actor es texto cliente.
- Decisión: auth académica local inicialmente, extensible a OIDC; roles administrator/researcher/operator/reviewer/read_only; checks server-side y audit de acciones sensibles.
- Alternativas: red confiable o headers; rechazadas por operaciones de publicación/review.
- Positivas: responsabilidad verificable.
- Negativas: gestión de usuarios/sesiones.
- Riesgos/mitigación: credenciales/IDOR; hashes resistentes, tokens cortos, scopes y tests.
- Compatibilidad: actor legacy queda metadata, no autoridad.
- Revisión futura: proveedor OIDC disponible.
- Componentes/prompts: API/UI/audit; P2/P13/P14.
