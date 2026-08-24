# Arquitectura del workspace de revisión celular

## Ubicación y jerarquía

El workspace se integra en la ruta canónica `/frotis/analizar`, bajo:

```text
Análisis de frotis
  - Ingesta
  - Control de calidad
  - Detección, clasificación y revisión celular
```

`/frotis/revision` se conserva sólo como redirect de compatibilidad hacia
`/frotis/analizar`; no debe usarse como ruta canónica en enlaces nuevos.

No se agrega al grupo `Modelo IA`. El shell, sidebar, tokens, botones e iconos
siguen siendo los existentes. La maqueta de referencia sólo informa jerarquía,
densidad y sincronización; no se copian su código, navegación global, categorías
hematológicas ni datos simulados.

La página tiene dos niveles:

1. listado de runs, runs elegibles y ejecución manual;
2. estación de revisión de un detection run.

## Layout

En escritorio ancho:

```text
minmax(250px,300px) minmax(330px,420px) minmax(0,1fr)
resumen/filtros      galería             visor + detalle
```

Cada panel conserva heading, loading/error/empty state y scroll vertical
independiente. No debe producir scroll horizontal. El visor es el área
dominante.

En viewport mediano se puede colapsar el resumen y estrechar la galería sin
ocultar el visor. En móvil, pestañas o segmentos `Resumen`, `Células`, `Imagen`
y `Detalle` sustituyen las tres columnas y conservan selección, filtro, imagen
y transformación. La altura se deriva del layout real, no de un
`calc(100vh - header-hardcodeado)`.

## Estado compartido

La fuente única de selección es:

```text
selectedDetectionId
```

Estado complementario:

- detection run e imagen actual;
- filtro de review status;
- página/cursor de galería;
- transform compartido `{scale, translateX, translateY}`;
- visibilidad de boxes, labels y rejilla;
- detalle/revisión en curso.

Seleccionar un crop actualiza `selectedDetectionId`, centra su caja y resalta el
overlay. Seleccionar una caja actualiza el mismo ID, activa su tarjeta y hace
scroll hasta ella. No hay estados paralelos de “crop seleccionado” y “box
seleccionado”.

## Imagen y overlay

El dominio base de coordenadas de la imagen autenticada y el SVG es:

```text
viewBox="0 0 {original_width} {original_height}"
```

En fit, el `viewBox` muestra ese dominio completo. Zoom/pan puede cambiar la
ventana visible del `viewBox`, pero `<image>` y boxes permanecen en las mismas
coordenadas originales. El SVG usa directamente `bbox_x`, `bbox_y`,
`bbox_width` y `bbox_height`; no recalcula detecciones. La misma transformación
se aplica al raster y al overlay para fit, zoom, pan, resize y
apertura/cierre de paneles.

La API entrega ancho/alto del raster original después de
`orientation_policy=exif_transpose`. El browser presenta el original con esa
orientación EXIF y el SVG usa exactamente esas dimensiones; no se mezclan
coordenadas raw con dimensiones visuales ni se reescala el detector.

Estados visuales:

- sin revisar: neutral;
- aceptada: success;
- rechazada: danger;
- requiere atención: warning.

Color se acompaña con texto/patrón/ícono. La caja seleccionada tiene mayor
grosor, label e indicador perceptible, y se puede activar con teclado. Una
leyenda explica los estados.

## Paneles

### Resumen y filtros

Muestra `detection_run_code`, códigos pseudonimizados, imágenes, totales,
revisadas y pendientes. Los filtros `Todas`, `Sin revisar`, `Aceptadas`,
`Rechazadas` y `Requieren atención` incluyen cantidad y porcentaje.

La lista de imágenes muestra secuencia, `safe_name` determinístico
(`Imagen 001`, `Imagen 002`, …), detecciones, revisadas, warnings y selección.
Los DTO de cell-analysis no exponen `original_filename`. No existe “verificar
todos” ni acción masiva.

### Galería

Muestra sólo detecciones de la imagen y filtro actuales, en orden estable por
`cell_index`. Cada tarjeta cuadrada contiene crop real, código corto, estado,
selección y warning técnico. Enter y Space equivalen al click.

Crops se paginan/cargan incrementalmente. `loading="lazy"` e
`IntersectionObserver` (o el patrón equivalente del proyecto) evitan descargar
fuera del viewport. Cada URL generada con `URL.createObjectURL` se libera en
cleanup, cambio de identidad y desmontaje.

### Visor y detalle

La toolbar ofrece selector de imagen, fit, 25/50/100/200 %, acercar, alejar,
reset, toggles accesibles, anterior/siguiente y siguiente sin revisar. Si no
existe magnificación registrada se muestra `Zoom digital`, nunca una
magnificación inventada.

El detalle enlaza crop, código, run, imagen, detector/versiones, resultado
automático, score geométrico, bbox, métricas, borde, checksum abreviado, última
revisión e historial. Usa lenguaje no clínico.

## Rendimiento

El objetivo mínimo es una imagen con 500 detecciones sin bloquear la
interacción:

- backend paginado con máximo configurable;
- overlay limitado a la imagen actual y a las 500 detecciones aceptadas que
  admite el perfil 1.0.0; así ninguna detección paginada queda sin box;
- tarjetas memoizadas;
- crops fuera de viewport sin fetch;
- ninguna consulta HTTP por tarjeta cuando el listado puede incluir metadata;
- transformaciones memoizadas y una sola imagen grande renderizada;
- selección y conteos actualizados sin recargar binarios.

La validación debe medir comportamiento con datos sintéticos; este documento no
afirma resultados de rendimiento sin evidencia.

## Accesibilidad y seguridad

- headings identifican paneles y regiones;
- foco visible y orden lógico;
- botones con nombre accesible y toggles con `aria-pressed`;
- tarjetas y boxes seleccionables con Enter/Space;
- `aria-live` informa revisión guardada o error;
- crops tienen alt seguro, sin PII ni interpretación clínica;
- texto legible y estado nunca comunicado sólo por color;
- content de original y crops siempre se obtiene con JWT; ningún payload expone
  storage keys, filenames de origen o paths físicos.

## Estados explícitos

Cada nivel presenta mensaje y recuperación para: sin runs elegibles, run sin
detecciones, imagen sin componentes, filtro sin resultados, crop u original no
disponible, detection run fallido y error al guardar revisión. No se muestran
paneles vacíos, stack traces ni rutas locales.
