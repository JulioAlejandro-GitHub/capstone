# ADR-002: Patient-ID como unidad de agrupación

## Context

Patient-ID tiene cobertura verificada 100 %; el split image-level mezcla los 201 pacientes
en las tres particiones.

## Decision

`patient_id` será grouping field. Dentro de una dataset version, una identidad clínica
puede pertenecer a exactamente un split. Overlap requerido: cero.

## Consequences

El balance/ratio se optimiza por grupos y puede no ser exacto. Disjointness prevalece.
Identidades usan UUID interno y evidencia normalizada, sin depender del formato del ID.

