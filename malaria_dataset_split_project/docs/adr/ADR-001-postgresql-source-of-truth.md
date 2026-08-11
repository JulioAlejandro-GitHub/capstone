# ADR-001: PostgreSQL como source of truth

## Context

El split histórico se representa parcialmente en filesystem, CSV/JSON y tablas sin una
versión científica única.

## Decision

PostgreSQL será canónico para sources, versions, identities, assignments, validations,
statistics, materializations, activations y lineage. Filesystem y exports son derivados.

## Consequences

Toda materialización nace de assignments persistidos; exports pueden regenerarse. La BD
requiere migrations aditivas, constraints, provenance y backups adecuados.

