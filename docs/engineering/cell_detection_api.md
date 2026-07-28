# API de detección y revisión celular

## Convenciones

- Base: `/api/v1/cell-analysis`
- Autenticación: bearer JWT en todos los endpoints
- Identidad visible: UUID/códigos seguros, nunca paths de storage
- Errores: mensajes sanitizados, sin stack trace
- Listados: orden estable y límite máximo configurable

El router no modifica endpoints ni estados de la cola de calidad de Prompt 6.
La fuente de elegibilidad es el analysis run y su quality gate.

## Endpoints y permisos

| Método y ruta | Permiso | Propósito |
|---|---|---|
| `GET /eligible-analysis-runs` | `scientific.cell_detection.read` | Runs habilitados que no tienen equivalente activo/completado |
| `POST /detection-runs` | `scientific.cell_detection.execute` | Ejecutar manual y síncronamente el baseline |
| `GET /detection-runs` | `scientific.cell_detection.read` | Listar runs, lineage, contadores y progreso de revisión |
| `GET /detection-runs/{detection_run_id}` | `scientific.cell_detection.read` | Detalle, perfil/versiones, estado y error seguro |
| `GET /detection-runs/{detection_run_id}/images` | `scientific.cell_detection.read` | Imágenes congeladas con conteos y warnings |
| `GET /detection-runs/{detection_run_id}/images/{microscopy_image_id}/detections` | `scientific.cell_detection.read` | Detecciones paginadas de una imagen |
| `GET /detection-runs/{detection_run_id}/images/{microscopy_image_id}/content` | `scientific.cell_detection.read` | Original autenticado, confinado al run |
| `GET /detections/{cell_detection_id}` | `scientific.cell_detection.read` | Detección, componente, crop y última revisión |
| `GET /crops/{crop_id}/content` | `scientific.cell_detection.read` | Contenido PNG autenticado |
| `POST /detections/{cell_detection_id}/reviews` | `scientific.cell_detection.review` | Insertar decisión/comentario append-only |
| `GET /detections/{cell_detection_id}/reviews` | `scientific.cell_detection.read` | Historial cronológico estable |

El visor obtiene el original mediante el endpoint propio de cell-analysis. Este
comprueba que la imagen pertenece al detection run y no recibe `storage_key`
para construir una URL física.

Los DTO de imágenes usan un `safe_name` determinístico por secuencia
(`Imagen 001`, `Imagen 002`, …). No exponen `original_filename`.

## Ejecución manual

Request:

```json
{
  "analysis_run_id": "uuid"
}
```

El servidor resuelve actor y perfil; el cliente no puede inyectar detector,
versiones, snapshot, paths, checksums, estados, contadores o timestamps.

Antes de crear un run se comprueban elegibilidad, manifiesto e idempotencia. El
trabajo CPU se ejecuta fuera del event loop. La respuesta representa el estado
terminal alcanzado por esa llamada. No hay job automático ni retry implícito.
Si ya existe un equivalente no fallido, se devuelve ese mismo recurso con
`idempotent=true`, sin volver a leer imágenes ni generar crops.

Errores de contrato:

- `401`: JWT ausente/inválido;
- `403`: rol sin permiso;
- `404`: run, imagen, detección o crop inexistente/no relacionado;
- `409`: quality gate no habilitado o integridad/manifiesto divergente;
- `422`: UUID/query/body/decisión/comentario inválido;
- error terminal del procesamiento: el run queda `failed` con detalle seguro.

## Listados y filtros

Las detecciones se ordenan por `cell_index` y un desempate estable de ID. El
endpoint admite `limit`/`offset` (100 por defecto,
`CELL_DETECTION_PAGE_MAX=500` por defecto) y filtro de estado:

- `unreviewed`;
- `accepted`;
- `rejected`;
- `needs_attention`;

y devuelve `items`, total filtrado y conteos necesarios para los filtros. El
máximo por respuesta se valida en backend. La metadata suficiente para una
tarjeta se obtiene en el listado; el frontend no realiza una consulta N+1 por
crop.

`comment_only` no es un estado de filtro: conserva la última decisión efectiva,
o `unreviewed` si nunca hubo una.

## Review append-only

Body:

```json
{
  "decision": "accepted | rejected | needs_attention | comment_only",
  "comment": "texto opcional sólo para accepted"
}
```

`rejected`, `needs_attention` y `comment_only` exigen comentario no vacío.
`accepted` puede incluirlo. Pydantic limita el texto a 4000 caracteres. Cada
POST crea una fila nueva con el actor JWT; no existen endpoints
PUT/PATCH/DELETE para revisiones, detecciones, cajas o crops.

La respuesta incluye la revisión creada y el estado humano efectivo para que la
UI actualice conteos e historial sin alterar el resultado automático.

## Contenido de crops

El endpoint:

1. resuelve la key relativa con confinamiento bajo `STORAGE_ROOT`;
2. rechaza ruta absoluta, `..`, byte nulo, escape, symlink y no-archivo;
3. verifica que metadata y archivo regular sean coherentes;
4. envía el PNG sin exponer la key.

Headers mínimos:

```text
Content-Type: image/png
Content-Length: <bytes validados>
ETag: "sha256-<sha256>"
Cache-Control: private, no-store
X-Content-Type-Options: nosniff
```

No se incluyen `Content-Disposition` o nombres con PII. La autorización se
evalúa antes de leer el archivo. El endpoint del original aplica la misma
política: contenido autenticado y sin filename/`Content-Disposition`.

## RBAC

| Rol | read | execute | review |
|---|---:|---:|---:|
| administrator | sí | sí | sí |
| researcher | sí | sí | sí |
| operator | sí | sí | no |
| reviewer | sí | no | sí |
| read_only | sí | no | no |

El frontend puede ocultar/deshabilitar acciones por permiso, pero la decisión
de seguridad siempre corresponde a FastAPI.

## Eventos y auditoría

| Operación | Evento |
|---|---|
| crear run | `scientific.cell_detection.created` |
| comenzar CPU | `scientific.cell_detection.started` |
| terminar | `scientific.cell_detection.completed` |
| fallar | `scientific.cell_detection.failed` |
| agregar review/comentario | `scientific.cell_review.created` |

Los eventos de auditoría usan el actor JWT, request/correlation ID y estado
sanitizado. Se excluyen secretos, datos personales, rutas absolutas, storage
keys innecesarias, filenames de origen, binarios y arrays de píxeles.

## Garantías de lenguaje

Los DTO y mensajes usan `detección candidata`, `resultado automático`,
`revisión humana` y `score geométrico/heurístico`. No exponen campos o textos de
clasificación celular, probabilidad diagnóstica, parasitemia o diagnóstico.
