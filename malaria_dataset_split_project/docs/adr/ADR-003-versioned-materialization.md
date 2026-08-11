# ADR-003: Materialización física versionada

## Context

La ruta activa mutable no puede identificar una versión histórica ni conservar intentos.

## Decision

Cada attempt se materializa bajo
`malaria_dl_local_project/data/malaria_dataset_versions/<dataset_version_id>/`, con
storage keys relativos, manifest y SHA-256. Una versión admite varios attempts.

## Consequences

Se separan lifecycle científico y estado físico. Reconciliation PASS precede freeze y
activation; se requiere espacio temporal y limpieza segura de attempts fallidos.

