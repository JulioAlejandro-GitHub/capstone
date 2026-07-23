# Revisión contextual de deployments

## Problema original

`Deployments.tsx` guardaba el deployment seleccionado, pero `DataTable` solo
renderizaba filas simples. El único lugar disponible para el detalle era después
del componente de tabla. Con varios registros, el usuario pulsaba “Revisar y
desplegar” sin percibir un cambio y debía desplazarse hasta el final.

El panel global tampoco mantenía suficientemente visible la identidad
`modelo → versión → deployment`.

## Estructura anterior

```text
Tabla completa
  fila deployment A
  fila deployment B
  fila deployment C
Panel global del deployment seleccionado
```

## Estructura nueva

```text
Modelo activo en producción

Pendientes de activación
  fila deployment A
  fila deployment B [seleccionada]
    panel inline: identidad, readiness, smoke y activación

Activos
Historial
```

`DataTable` acepta de forma opcional:

- `expandedRowKey`;
- `renderExpandedRow`;
- `getRowClassName`;
- `tableClassName`;
- `expandedRowIdPrefix`.

Cada fila y su expansión se renderizan en el mismo `Fragment`. Como
`expandedRowKey` es escalar, puede existir como máximo una expansión. Las demás
páginas siguen usando `DataTable` sin estas propiedades y conservan su
comportamiento anterior.

## Componentes

- `DeploymentReviewPanel`: identidad, requisitos y operaciones contextualizadas.
- `ProductionActivationModal`: confirmación de producción, champion reemplazado,
  Escape y focus trap.
- `ActiveProductionModel`: resumen independiente del champion activo.
- `DataTable`: soporte genérico y retrocompatible para filas expandidas.

## Identidad visible

El panel comienza con:

```text
Está revisando: {model_name} v{version_number}
```

Y mantiene visibles:

- deployment name e ID abreviado;
- model version ID abreviado;
- training run ID abreviado;
- environment y alias;
- threshold;
- smoke;
- estado y fecha de activación.

No se muestran rutas de checkpoints.

## Estados del flujo

### Paso 1 — Revisar requisitos

Representa `pass`, `pending`, `blocked` y `not_applicable` mediante texto,
icono y estilo; la información no depende solo del color.

### Paso 2 — Validar modelo

Solo se habilita si `can_run_smoke=true` y todavía no existe PASS. El botón
incluye el nombre y versión. PASS y FAIL producen mensajes específicos dentro
de la misma expansión.

### Paso 3 — Activar

Solo se habilita si `can_activate=true`. En staging/experimental invoca la
activación controlada. En producción abre el modal y únicamente la confirmación
envía `confirm_production=true`.

Después de cada operación se refrescan deployments y readiness, se conserva el
ID expandido y el resultado permanece junto al modelo.

## Producción

La cabecera de la página busca exactamente:

```text
environment=production AND status=active AND alias=champion
```

Si existe, muestra modelo, versión, deployment, alias, threshold, activación y
estado. Si no existe, diferencia explícitamente esa condición de una lista
vacía: “No existe un modelo activo en producción.”

El modal informa qué champion será reemplazado y que la revisión anterior se
conserva para rollback.

## Orden y responsive

Los registros no se duplican y se separan en:

1. pendientes;
2. activos;
3. historial.

Dentro del orden global se prioriza production pending, production active,
staging/experimental pending, inactive y retired.

En pantallas de hasta 700 px, la tabla de deployments se transforma en tarjetas:
cada celda muestra su etiqueta y el panel se expande inmediatamente debajo de la
tarjeta seleccionada.

## Accesibilidad

- `aria-expanded` y `aria-controls` en fila y botón;
- `aria-live` en el panel;
- foco programático en “Está revisando”;
- `scrollIntoView` para navegación por `selectedDeploymentId`;
- foco visible;
- modal con `role=dialog`, `aria-modal`, Escape y focus trap;
- navegación completa con botones nativos.

## Tests y verificación

- Frontend: 37 tests PASS.
- TypeScript y build Vite: PASS.
- Se verificó estructuralmente que la expansión se inserta inmediatamente
  después de la fila dentro del mismo `Fragment`.
- Se verificó que no existe el antiguo `detail-panel` global.
- Se cubren selección única, refresh, mensajes PASS/FAIL, modal, confirmación
  production, champion, accesibilidad, responsive y ausencia de paths.

La validación no modifica `can_run_smoke`, `can_activate` ni las reglas del
backend; solo hace visible su resultado en el contexto correcto.
