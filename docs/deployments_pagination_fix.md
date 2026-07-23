# Corrección de carga de Despliegues por contrato de paginación

## Resumen

La página **Modelo IA → Despliegues** volvía error porque cargaba en paralelo:

1. `GET /api/deployments?datasource=malaria`;
2. `GET /api/dataset/images?datasource=malaria&page_size=1`.

El segundo request obtiene una imagen controlada para el smoke test. El backend
solo permite tamaños `12`, `24`, `48` y `96`, por lo que respondió:

```text
HTTP 400
{"detail":"page_size debe ser 12, 24, 48 o 96."}
```

`Promise.all` propagaba ese fallo auxiliar y la página mostraba “Error al cargar
deployments”, aunque `GET /api/deployments` funcionaba correctamente.

## Causa raíz

El valor inválido estaba codificado en
`frontend/src/pages/Deployments.tsx` como `page_size: 1`. No provenía de:

- localStorage o sessionStorage;
- query string de navegación;
- estado global;
- un selector de paginación;
- el valor por defecto del backend.

El endpoint `GET /api/deployments` no es paginado en la arquitectura actual. La
validación pertenece a `GET /api/dataset/images`; no se añadió paginación
artificial al listado de deployments.

## Contrato definitivo

La solicitud auxiliar de Despliegues ahora es:

```http
GET /api/dataset/images?datasource=malaria&page=1&page_size=12
```

El frontend centraliza:

```ts
DATASET_IMAGE_PAGE_SIZES = [12, 24, 48, 96]
DEFAULT_DATASET_IMAGE_PAGE_SIZE = 12
```

El backend centraliza:

```python
DATASET_IMAGE_PAGE_SIZE_CHOICES = (12, 24, 48, 96)
DEFAULT_DATASET_IMAGE_PAGE_SIZE = 12
```

El default del endpoint queda alineado en `12`. El navegador de dataset conserva
su elección explícita inicial de `24`, que también es válida. La página
Despliegues envía explícitamente `12`, porque solo necesita la primera imagen
disponible. OpenAPI documenta los cuatro valores mediante el schema del query
parameter.

Un valor arbitrario como `20` sigue retornando HTTP 400; no se eliminó ni se
relajó la validación.

## Valores persistidos

Despliegues no guarda `page_size` en localStorage, sessionStorage ni estado
global, por lo que no existe un valor histórico que migrar. Se agregó
`normalizeDatasetImagePageSize` al contrato frontend para cualquier consumidor
futuro: conserva `12/24/48/96` y normaliza `20`, `"abc"` o valores vacíos a
`12`. No se requiere que el usuario borre almacenamiento.

## Manejo de errores

La página ahora:

- presenta un mensaje legible;
- registra el detalle técnico con `console.error`;
- ofrece un botón **Reintentar**;
- no hace retry automático ni genera loops;
- distingue un error de paginación de un fallo genérico.

## Archivos modificados

- `frontend/src/pages/Deployments.tsx`
- `frontend/src/config/pagination.ts`
- `frontend/tests/deployments-pagination.test.mjs`
- `backend_api/app/services/dataset_browser.py`
- `backend_api/app/routes/dataset.py`
- `backend_api/tests/test_dataset_browser_api.py`

## Verificación HTTP real

Contra `malaria_experiments`:

| Request | Resultado |
|---|---|
| `GET /api/deployments?datasource=malaria` | 200, 28 deployments |
| `GET /api/dataset/images?...page=1&page_size=12` | 200, metadata `page=1`, `page_size=12`, 12 items |
| `GET /api/dataset/images?datasource=malaria` | 200, default `page=1`, `page_size=12` |
| `page_size=24` | 200 |
| `page_size=48` | 200 |
| `page_size=96` | 200 |
| `page_size=20` | 400 con detalle de tamaños permitidos |
| `page=0&page_size=12` | 422 por `page >= 1` |

El componente renderiza la tabla cuando ambas respuestas son exitosas y
mantiene el estado vacío “No existen deployments registrados” cuando la lista
no tiene elementos.

## Tests

- backend API: 39 passed, 3 opt-in skipped; tamaños `12/24/48/96`,
  default `12`, metadata y rechazo de `20`;
- frontend: request inicial con `page=1/page_size=12`, constantes permitidas,
  normalización, mensaje legible y reintento sin loop; 24 passed;
- TypeScript y build Vite de producción: PASS;
- integración HTTP con PostgreSQL local.

## Resultado

La solicitud inválida `page_size=1` fue reemplazada por `page_size=12`. La
página puede cargar sus deployments y la imagen auxiliar sin recibir el error
400 original.
