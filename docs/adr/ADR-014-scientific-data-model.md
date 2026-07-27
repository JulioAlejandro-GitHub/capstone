# ADR-014 — Modelo de datos científicos

Estado: aceptado — 2026-07-27

> Nota de catálogo: el repositorio ya contenía `ADR-014-explainability-policy.md`. Se conserva
> inmutable y se usa el nombre solicitado por Prompt 3; el índice ADR debe renumerarse en una
> tarea documental posterior para eliminar la colisión histórica.

## Decisión

Se adopta una cadena normalizada:
`research_subjects → scientific_cases → blood_samples → smear_slides → microscopy_images`.
Un caso puede omitir sujeto. Los UUID son identidad interna y los códigos legibles son
identidad científica única en su contexto.

`research_subjects` reemplaza deliberadamente el concepto de paciente: contiene sólo un
pseudónimo de investigación y atributos científicos generales; se prohíbe PII tanto en
columnas como en claves conocidas de `metadata_json`. Caso, muestra y frotis se separan
porque tienen ciclos de vida y cardinalidades diferentes. Imagen es una captura individual,
no el binario: PostgreSQL conserva provider, key relativa, checksum y propiedades técnicas.

El borrado físico no se expone. El archivado es explícito, no cascada y queda bloqueado si
hay hijos activos. Las FK usan `ON DELETE RESTRICT`; estados, JSON objeto, cronología,
dimensiones, tamaño y SHA-256 están protegidos por constraints.

Cada mutación requiere un permiso específico y comparte una transacción PostgreSQL con su
`audit_event`. La trazabilidad se consulta con un join único, preparado para futuras
entidades de calidad e inferencia sin incorporarlas todavía.

## Consecuencias

- La cadena de custodia es consultable sin N+1.
- Una misma captura no puede repetirse por checksum dentro del mismo frotis.
- El storage externo debe mantener estable el `storage_key`.
- El control de PII por claves es defensa adicional, no reemplaza revisión humana.
- Una futura ingesta deberá verificar el checksum y storage antes de marcar `available`.
