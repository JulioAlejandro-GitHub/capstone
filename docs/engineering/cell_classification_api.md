# API de clasificación celular

Base: `/api/v1/cell-classification`. Todas las rutas requieren JWT y permisos
`scientific.cell_classification.*`.

| Método | Ruta | Uso |
|---|---|---|
| GET | `/eligible-detection-runs` | elegibilidad y estado seguro del modelo |
| POST | `/classification-runs` | crear/ejecutar con sólo `detection_run_id` |
| GET | `/classification-runs` | listar con paginación |
| GET | `/classification-runs/{id}` | snapshot, progreso, eventos y conteos |
| GET | `/classification-runs/{id}/predictions` | filtros y orden estable |
| GET | `/classification-runs/{id}/summary` | envelope `automatic_summary` + `reviewed_summary` |
| GET | `/predictions/{id}` | detalle de una célula |
| POST/GET | `/predictions/{id}/explanation` | Grad-CAM manual/consulta |
| GET | `/explanations/{id}/heatmap` | PNG autenticado |
| GET | `/explanations/{id}/overlay` | PNG autenticado |
| POST/GET | `/predictions/{id}/reviews` | revisión append-only/historial |

El body de creación rechaza campos extra. List predictions filtra por imagen,
label, near-threshold, status, review status y `cell_code`, ordenando por
secuencia de imagen, índice e ID.

Los filtros y enums son allowlists del contrato: no se interpolan nombres de
campo, orden, tablas ni storage keys proporcionados por el cliente. Los bodies
de creación, explicación y review usan `extra=forbid`; la explicación sólo
acepta el booleano `retry`, y el retry nunca es automático.

Los endpoints PNG verifican confinement, symlinks, checksum y tamaño, y devuelven
`no-store`, `nosniff`, `Content-Length` y `ETag` sin revelar storage keys.
Las respuestas JSON públicas eliminan claves relativas de storage, paths/URI
físicos, secretos y tokens; para una explicación generada exponen únicamente
URLs autenticadas de contenido.
