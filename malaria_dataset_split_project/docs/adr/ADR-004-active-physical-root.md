# ADR-004: Root físico activo compatible

## Context

TRAIN/EVALUATE consumen `malaria_physical_split/train|val|test` desde filesystem.

## Decision

Se conserva ese root como materialización ACTIVE, nunca como identidad científica. Habrá
máximo una activación vigente por familia malaria, registrada en PostgreSQL. La promoción
será atómica/controlada desde una materialización FROZEN reconciliada.

## Consequences

TRAIN/EVALUATE mantienen su layout. La activación necesita lock, rollback target y
compensación ante fallos entre filesystem y registro; legacy debe preservarse primero.

