# Modelo de datos de detección y revisión celular

Migración: `20260727_05_cell_detection_and_review.py`, revisión
`20260727_05`, sobre `20260727_04`. Las migraciones históricas no se editan.

## Relaciones

```text
microscopy_analysis_runs
  1 -> N cell_detection_runs
          1 -> N image_connected_components
          1 -> N cell_detections
                  1 -> 1 cell_crops
                  1 -> N scientific_reviews (entity_type=cell_detection)
          1 -> N cell_detection_events
```

Las FK usan `ON DELETE RESTRICT`. Los UUID son identidades internas; los códigos
`DET-…` y `CELL-…` son identificadores seguros para UI y trazabilidad. Ninguna
tabla almacena imágenes o crops como `bytea`, base64 u otro binario.

## `cell_detection_runs`

Conserva la ejecución y su provenance:

- analysis run, código único, detector, versiones y snapshot JSONB;
- SHA-256 del manifiesto de entrada;
- estado y contadores de imágenes/componentes/detecciones/crops/warnings;
- actor solicitante, timestamps y error terminal sanitizado.

Constraints:

- estados: `created`, `processing`, `completed`,
  `completed_with_warnings`, `failed`;
- `profile_snapshot` debe ser objeto JSON;
- SHA-256 debe ocupar 64 caracteres hexadecimales;
- `image_count > 0` y los demás contadores son no negativos;
- `processed_image_count <= image_count`;
- `ck_cell_detection_run_terminal_state` hace coherentes timestamps/error con
  `created`, `processing`, estados completados y `failed`;
- `detection_run_code` es único y cumple `DET-` + 8 hexadecimales mayúsculos.

Índices:

- índice único parcial de equivalencia por analysis run, detector, versiones y
  manifiesto para estados no fallidos:
  `uq_cell_detection_runs_equivalent_active`;
- `ix_cell_detection_runs_status_created` para listados;
- `ix_cell_detection_runs_analysis_created` para lineage;
- `uq_cell_detection_runs_identity (id,analysis_run_id)` soporta FK compuestas.

El run es la única tabla automática que cambia durante su máquina de estados.
`trg_cell_detection_runs_immutable_identity` impide cambiar analysis run,
código, detector/versiones, snapshot, manifiesto, cantidad de imágenes, actor o
fecha de creación incluso durante el procesamiento. El mismo trigger restringe
`created -> processing -> completed|completed_with_warnings|failed`, vuelve
inmutable todo estado terminal y rechaza `DELETE`.

## `image_connected_components`

Registra todos los componentes antes del filtro:

- FK al run, `analysis_run_id`, `analysis_run_image_id` y
  `microscopy_image_id`; `analysis_run_id` permite comprobar identidad mediante
  FK compuestas;
- `component_index`;
- bbox `x,y,width,height`, centroide, área, perímetro, circularidad, solidity y
  contacto con borde;
- `component_status`: `candidate`, `accepted` o `rejected_by_filter`;
- `rejection_code`, `metrics_json` y timestamp.

Constraints:

- `component_index > 0`, coordenadas no negativas y dimensiones/área
  positivas;
- centroides no negativos, perímetro nullable/no negativo, circularidad y
  solidity nullables dentro de `[0,1]`;
- `metrics_json` es objeto;
- un rechazado requiere `rejection_code`; un aceptado no debe simular una razón
  de rechazo;
- `(detection_run_id, analysis_run_image_id, component_index)` es único;
- la referencia compuesta debe impedir mezclar imágenes de otro analysis run.

Índices:

- `uq_image_connected_components_run_image_index` conserva el orden único;
- `uq_image_connected_components_identity` soporta la FK compuesta de
  detecciones;
- `ix_image_connected_components_run_image` sirve listado por imagen;
- `ix_image_connected_components_status` sirve conteos/diagnóstico técnico.

`candidate` queda reservado por el contrato de tabla. La versión 1.0.0
persiste cada resultado de filtrado ya terminal como `accepted` o
`rejected_by_filter`; no deja componentes en un estado transitorio.

## `cell_detections`

Una fila representa un componente automático aceptado:

- FK compuestas al run, componente e imagen congelada, incluyendo
  `analysis_run_id`;
- `cell_index` y `cell_code` único;
- bbox canónico;
- `coordinate_space=original_image_pixels`;
- `detector_score` nullable y `automated_status`.

Constraints:

- una relación uno-a-uno con `connected_component_id`;
- coordenadas no negativas y ancho/alto positivos;
- `(detection_run_id, cell_index)` único;
- `cell_code` cumple `CELL-` + 12 hexadecimales mayúsculos;
- `coordinate_space` queda fijado por `CHECK` y
  `automated_status='candidate'`;
- `detector_score` es nullable y, cuando existe, queda acotado a `[0,1]` sin
  adquirir semántica probabilística;
- la caja debe caber en la imagen; esta regla se comprueba contra las
  dimensiones orientadas calculadas después de verificar las dimensiones raw
  congeladas, porque un `CHECK` no puede consultar otra tabla;
- el score es heurístico y no habilita columnas de clase o diagnóstico.

Índices:

- `uq_cell_detections_component` impone una detección por componente;
- `uq_cell_detections_run_index` impone `cell_index` global y único por run;
- `uq_cell_detections_identity` soporta lookups compuestos;
- `uq_cell_detections_cell_code` hace globalmente único el código;
- `ix_cell_detections_run_image` sirve el listado estable de una imagen.

## `cell_crops`

Metadata de un PNG derivado:

- `cell_detection_id` único;
- `relative_storage_key` POSIX relativa y única;
- SHA-256, bytes, ancho, alto, formato, padding y timestamp.

Constraints:

- bytes/ancho/alto positivos y `padding_px >= 0`;
- `sha256` hexadecimal de 64 caracteres;
- `format` corresponde a `PNG`;
- un `CHECK` restringe la key al layout UUID exacto
  `cell-crops/{analysis_run}/{detection_run}/{image}/{detection}/crop.png`;
- no se aceptan rutas absolutas, `..`, bytes nulos o symlinks; confinement y
  symlinks requieren además validación de filesystem en el servicio.

Índices:

- los `UNIQUE` de detection y key cubren el lookup principal;
- no se indexa metadata de bajo valor selectivo sólo por conveniencia.

## `cell_detection_events`

Bitácora operacional append-only del run. Sigue el patrón de
`microscopy_analysis_events`: run, imagen opcional, tipo, estado/código/mensaje
sanitizado, `metadata_json`, progreso opcional y fecha. Los contadores de
progreso no pueden ser negativos ni superar el total. Los índices
`ix_cell_detection_events_run_created` y
`ix_cell_detection_events_run_image` conservan historias estables.

Esta tabla explica el pipeline; `audit_events` explica quién ejecutó una
mutación HTTP. Ninguna reemplaza a la otra.

## `scientific_reviews`

Historial humano append-only:

- `entity_type='cell_detection'`;
- `entity_id` referencia la detección con `ON DELETE RESTRICT`;
- `decision`: `accepted`, `rejected`, `needs_attention` o `comment_only`;
- comentario nullable sólo para `accepted`;
- actor JWT y timestamp.

Constraints:

- `rejected`, `needs_attention` y `comment_only` requieren comentario no vacío;
- actor referencia `users(id)` con `ON DELETE RESTRICT`;
- trigger o política equivalente rechaza `UPDATE` y `DELETE`;
- `ix_scientific_reviews_entity_created` resuelve historial/última decisión y
  `ix_scientific_reviews_actor_created` permite trazabilidad por actor.

La última fila con una decisión efectiva (`accepted`, `rejected` o
`needs_attention`) determina el estado mostrado. `comment_only` agrega historia
sin reemplazar esa decisión. El estado por defecto es `unreviewed`. Ninguna
revisión modifica `cell_detections.automated_status`.

## Inmutabilidad y ownership

- PostgreSQL contiene metadata y relaciones; `var/storage` contiene binarios.
- Los originales pertenecen a la ingesta y son de sólo lectura para este
  pipeline.
- Componentes, detecciones y crops pertenecen a un run versionado y no se
  actualizan.
- Las revisiones pertenecen al actor humano y siempre se agregan.
- Borrar en cascada queda prohibido para no romper lineage.

La migración instala triggers append-only para
`image_connected_components`, `cell_detections`, `cell_crops`,
`cell_detection_events` y `scientific_reviews`; rechazan `UPDATE` y `DELETE` en
PostgreSQL, no sólo en la API.

Las restricciones y nombres finales deben verificarse contra la migración
Alembic de Prompt 7 antes de aprobar la entrega; la evidencia se registra en
`docs/engineering/prompt7_validation.md`.
