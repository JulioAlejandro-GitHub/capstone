# Diccionario científico

Todas las PK son UUID, los timestamps son `TIMESTAMPTZ` UTC y `metadata_json` debe ser un
objeto sin PII. `created_by`, `updated_by` y `archived_by` referencian `users`.

| Tabla | Identidad visible | Relación | Estados | Restricciones principales |
|---|---|---|---|---|
| `research_subjects` | `subject_code` global | — | active, archived | pseudónimo no vacío; coherencia de archivado |
| `scientific_cases` | `case_code` global | `subject_id` opcional | draft, registered, ready, archived | source type y prioridad enumerados |
| `blood_samples` | `sample_code` por caso | `case_id` | registered, received, prepared, archived | recepción ≥ colección |
| `smear_slides` | `slide_code` por muestra | `sample_id` | registered, prepared, ready_for_capture, archived | smear thin/thick/combined/unknown |
| `microscopy_images` | `image_code` por frotis | `slide_id` | registered, available, unavailable, rejected, archived | tamaño/dimensiones positivos; SHA-256 hex; checksum único por frotis |

## Privacidad

No existen columnas para nombre, RUT, documento, dirección, teléfono, email, fecha exacta de
nacimiento, contacto o diagnóstico. La API rechaza esas claves, incluso anidadas, en
`metadata_json`. No deben usarse valores libres para evadir la política.

## Archivos

`storage_provider` y `storage_key` son referencias. `original_filename` es informativo y no
debe contener PII. No hay columnas `BYTEA`, large objects ni multipart en este alcance.

Prompt 4 añade lote, origen de identidad de muestra, procedencia y propiedades
técnicas. Multipart es transporte API; PostgreSQL continúa sin binarios.
# Diccionario Prompt 5

Las tablas `microscopy_analysis_runs`, `microscopy_analysis_run_images`,
`image_quality_assessments`, `microscopy_analysis_events` y
`quality_gate_decisions` se definen íntegramente en la migración
`20260727_03_microscopy_quality_gate.py`, incluidos checks, FKs e índices.
