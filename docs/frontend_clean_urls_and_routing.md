# Routing y URLs limpias del frontend

## Problema original

La aplicación seleccionaba la página y los objetos con estado React en `App.tsx`. El menú era una lista de botones y `selectedRunId`, `selectedModelVersionId` y `selectedDeploymentId` solo existían en memoria. Una recarga regresaba al resumen, el historial del navegador no representaba el recorrido y no había enlaces directos.

## Solución

Se utiliza React Router 7 con `BrowserRouter`, `Routes`, rutas anidadas, `Outlet`, `NavLink`, `Navigate`, `useNavigate`, `useParams` y `useSearchParams`. La navegación normal agrega historial; `replace` se reserva para la entrada `/`, la normalización del datasource y redirects legacy.

El archivo central es `frontend/src/router.ts`. Los componentes no deben construir rutas dispersas: deben usar `routes`, `withAllowedQuery` y `buildShareableUrl`.

## Mapa de rutas

| Página | URL | ID principal | Query parameters |
|---|---|---|---|
| Resumen | `/modelo-ia/resumen` | — | `datasource` |
| Ejecuciones | `/modelo-ia/ejecuciones` | — | `datasource`, `run`, `modelo` |
| Detalle de ejecución | `/modelo-ia/ejecuciones/:trainingRunId` | UUID de run | `datasource` |
| Evaluaciones | `/modelo-ia/evaluaciones` | — | `datasource` |
| Comparación | `/modelo-ia/comparacion` | — | `datasource` |
| Modelos liberados | `/modelo-ia/modelos-liberados` | — | `datasource` |
| Detalle de model version | `/modelo-ia/modelos-liberados/:modelVersionId` | UUID de model version | `datasource` |
| Despliegues | `/modelo-ia/despliegues` | — | `datasource` |
| Revisión de deployment | `/modelo-ia/despliegues/:deploymentId` | UUID de deployment | `datasource` |
| Trazabilidad | `/modelo-ia/trazabilidad` | — | `datasource` |
| Explicabilidad | `/modelo-ia/explicabilidad` | — | `datasource` |
| Predicciones | `/modelo-ia/predicciones` | — | `datasource` |
| Dataset | `/modelo-ia/dataset` | — | `datasource` |
| Datasets y modelos | `/modelo-ia/datasets-modelos` | — | `datasource` |
| Errores y logs | `/modelo-ia/errores-logs` | — | `datasource` |

No se añadieron rutas de detalle para evaluación, explicabilidad o predicción: el frontend actual no dispone de una carga estable del objeto individual por el ID público correspondiente. Añadir la URL antes del endpoint produciría un deep link que no podría reconstruirse.

## Datasource y filtros

El datasource es contexto transversal y se representa como `?datasource=malaria`, coincidiendo con el contrato del backend. En la carga se valida contra `/datasources`; un valor ausente o no habilitado se normaliza al primer datasource habilitado. El selector, las llamadas API y los enlaces internos usan el mismo slug.

Los filtros estables de Ejecuciones (`run` y `modelo`) se leen y escriben con `useSearchParams`, por lo que Atrás y Adelante restauran la vista. Los parámetros temporales, objetos JSON, credenciales y paths físicos no se escriben en la URL.

## Detalles, breadcrumbs y títulos

Los IDs se leen con `useParams` y se validan como UUID antes de montar páginas que consultan la API. Un ID inválido muestra una vista específica y no dispara la consulta. Run detail usa `/api/runs/:id`; model version usa `/api/model-versions/:id`; deployment se resuelve desde `/api/deployments` y consulta readiness por ID.

El layout genera breadcrumbs desde la ruta, mantiene “Modelo IA” expandido y actualiza `document.title`. Al cambiar de pathname se lleva el foco al primer `h1`. Los detalles de run, model version y deployment ofrecen “Copiar enlace”; el helper usa el origin actual, conserva el datasource y no contiene un dominio de desarrollo fijo.

## Panel de Despliegues

`/modelo-ia/despliegues/:deploymentId` selecciona la fila, expande la revisión, carga readiness y desplaza el panel al viewport. “Cerrar revisión” navega a la lista conservando datasource. El estado local sigue administrando datos transitorios del formulario, pero la identidad seleccionada procede de la URL.

## Redirects legacy

Se normalizan con `replace` y se conserva el query string:

- `/runs` → `/modelo-ia/ejecuciones`
- `/evaluations` → `/modelo-ia/evaluaciones`
- `/model-versions` → `/modelo-ia/modelos-liberados`
- `/deployments` → `/modelo-ia/despliegues`
- `/modelo-ia/ejecuciones/RunId=<uuid>` → ruta canónica del run

La ruta `/` redirige a `/modelo-ia/resumen`.

## 404 y errores

Una ruta desconocida muestra “Página no encontrada” dentro del layout. Un UUID inválido muestra “Identificador inválido”. Los errores de carga permanecen en las páginas existentes; no se redirigen silenciosamente al resumen. Las vistas no muestran stack traces ni paths locales.

## Fallback del servidor

Vite dev y Vite preview sirven `index.html` para deep links de la SPA. `backend_api` es exclusivamente API y no sirve el frontend; por eso no se agregó un fallback que pudiera interceptar `/api`.

En el servidor web de producción que publique `frontend/dist`, la regla requerida es equivalente a `try_files $uri $uri/ /index.html`, con `/api/`, health checks y assets existentes excluidos o enviados al backend. Esta regla pertenece al hosting del frontend; no existe una configuración Nginx/Docker de frontend en este repositorio que sea seguro modificar.

## Seguridad y accesibilidad

- Solo UUID públicos y slugs aparecen en paths.
- No se incluyen `checkpoint_path`, `artifact_path`, tokens, objetos completos ni rutas físicas.
- El menú usa enlaces nativos, permite Ctrl/Cmd/clic central y deriva `aria-current` de la URL.
- La 404, mensajes de copia y estados de carga usan semántica accesible.
- Los permisos continúan dependiendo del backend; no se inventaron roles ni guards.

## Pruebas

`frontend/tests/clean-routing.test.mjs` comprueba router único, rutas anidadas, UUID, datasource, enlaces canónicos, redirects, 404, navegación del deployment y ausencia de paths internos. Las pruebas preexistentes se actualizaron para comprobar rutas en vez de claves de estado.

## Cómo agregar una página

1. Confirmar que la página y su endpoint existen.
2. Añadir el constructor a `router.ts`.
3. Registrar la ruta hija en `App.tsx`.
4. Añadir un `NavLink` en `Layout.tsx` si es una sección principal.
5. Si tiene detalle, validar el ID antes de consultar, reconstruir el objeto desde API y añadir copia de enlace.
6. Definir únicamente query parameters estables y permitidos.
7. Añadir pruebas de acceso directo, recarga, Atrás/Adelante, 404 y seguridad.

## Ejemplo de recorrido

`/modelo-ia/ejecuciones/<run>?datasource=malaria`
→ `/modelo-ia/modelos-liberados/<version>?datasource=malaria`
→ `/modelo-ia/despliegues/<deployment>?datasource=malaria`.

Cada transición utiliza `navigate` o un enlace real y, por tanto, puede recorrerse con Atrás y Adelante.
