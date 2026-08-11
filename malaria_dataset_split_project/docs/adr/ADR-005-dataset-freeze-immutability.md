# ADR-005: Inmutabilidad de dataset FROZEN

## Context

Comparabilidad y reconstrucción exigen que metodología, población y assignments no
cambien después de aprobar una versión.

## Decision

FROZEN es irreversible salvo ARCHIVED lógico. Congela sources, identity mapping,
assignments, método/seed/ratios/mapping de clases, statistics, validation snapshot y
materialization manifest. Todo cambio crea nueva semantic version.

## Consequences

Se requieren fingerprints y guards de escritura. Pueden existir múltiples FROZEN y una
sola ACTIVE. Correcciones no mutan una versión publicada: generan otra.

