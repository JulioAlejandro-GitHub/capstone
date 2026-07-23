# Navegación frontend “Modelo IA”

## Inventario anterior

El frontend es React 19 + TypeScript + Vite. No utiliza React Router: la navegación
se conserva como claves de página en `App.tsx`, por lo que no existían URLs públicas,
bookmarks, redirects ni breadcrumbs. Había una barra lateral plana con Dashboard,
Ejecuciones, Evaluación clínica, Comparación, Explicabilidad, Predicciones, Dataset,
Datasets y modelos, y Errores/logs. No se encontraron permisos, feature flags, tema
oscuro, navbar separada ni menú móvil independiente.

## Estructura nueva

```text
Modelo IA
├── Resumen
├── Ejecuciones
├── Evaluaciones
├── Comparación de modelos
├── Modelos liberados
├── Despliegues
├── Trazabilidad
├── Explicabilidad
├── Predicciones
├── Dataset
└── Datasets y modelos

Errores y logs
```

Todas las claves existentes (`dashboard`, `runs`, `clinical-evaluation`, `models`,
`explainability`, `uploaded-predictions`, `dataset-browser`, `datasets`, `errors` y
`run-detail`) se mantienen. Se agregaron únicamente `model-versions`, `deployments` y
`traceability`, respaldadas por endpoints reales. No se agregaron Análisis de imágenes
ni módulos Etapa 2 porque no existe todavía una vista funcional autorizada.

## Componentes y visibilidad

`Layout` contiene un único grupo colapsable, se abre al activar una hija, guarda su
estado en `localStorage`, marca `aria-current` y ofrece `aria-expanded`,
`aria-controls`, flechas izquierda/derecha y breadcrumbs. En móvil el layout pasa a
una columna y el submenú se adapta de dos a una columna.

`ModelVersions` ofrece filtros de modelo, estado y linaje, detalle, relaciones,
evaluación y enlace a deployments. Los estados no aptos se muestran con fines de
auditoría, pero no existe acción para seleccionarlos para análisis. `Deployments` es
de sólo lectura porque la aplicación no tiene permisos de usuario; no se inventaron
roles. `Traceability` reutiliza el linaje agrupado existente mediante un árbol simple.

Endpoints consumidos:

- `GET /api/model-versions`
- `GET /api/model-versions/{id}`
- `GET /api/model-versions/{id}/lineage`
- `GET /api/deployments` y `/active`
- `GET /runs/grouped-lineage`

No existe actualmente un selector de inferencia en el frontend. Cuando se incorpore,
deberá consumir exclusivamente `/api/deployments/active` y enviar
`deployed_model_version_id`; nunca checkpoint, path o `best_model.keras`.

## Promoción desde Ejecuciones

La fila principal TRAIN incorpora una acción secundaria junto a “Ver detalle”. Su
estado se obtiene desde
`GET /api/training-runs/{training_run_id}/promotion-status`; EVALUATE y EXPLAIN
conservan sus acciones y no reciben controles de promoción.

La acción puede preparar una versión mediante
`POST /api/training-runs/{training_run_id}/prepare-release` o navegar usando
`model_version_id`/`deployment_id`. Nunca despliega ni activa. Durante el POST se
bloquea el control, se muestra progreso, existe timeout de 30 segundos y se vuelve a
consultar el estado al fallar.

`App.tsx` conserva los IDs seleccionados en estado porque el proyecto todavía no
usa React Router. `ModelVersions` y `Deployments` enfocan su ficha al recibir el ID.
Las rutas que entrega el backend se usan como contrato de destino; la navegación
interna actual se resuelve por `PageKey`.

Modelos liberados muestra la evidencia disponible y mantiene deshabilitada la
operación administrativa: el sistema no expone permisos de usuario ni endpoints de
validación/aprobación consumibles por esta UI. Despliegues sigue siendo read-only.
No se inventan roles ni acciones.

## Verificación visual y accesibilidad

Ejecutar `npm run dev`, verificar a 1440 px, 900 px y 390 px, navegar con Tab/Enter y
usar flechas izquierda/derecha sobre “Modelo IA”. Confirmar foco, opción activa,
breadcrumb, persistencia tras recarga, loading, vacío y error desconectando el API.
La compilación se valida con `npm run build` y la estructura con `npm test`.

No se añadió tema oscuro porque el producto actual no lo implementa; los cambios
mantienen la paleta clara y el sidebar oscuro ya existente.
