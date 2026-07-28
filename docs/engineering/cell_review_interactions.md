# Interacciones de revisión celular

## Modelo de selección

`selectedDetectionId` es la única fuente de selección en la estación. El
estado no duplica una selección para galería y otra para overlay.

### Crop hacia caja

1. Click, Enter o Space en una tarjeta asigna `selectedDetectionId`.
2. Si pertenece a otra imagen, se selecciona esa imagen y se carga su overlay.
3. La caja recibe estado visual y foco identificable.
4. El visor centra la detección sin cambiar el bbox.
5. El detalle muestra exactamente el mismo ID.

### Caja hacia crop

1. Click, Enter o Space en el grupo SVG asigna el mismo ID.
2. La galería conserva el filtro; si el elemento no está cargado, solicita la
   página que lo contiene o explica que queda fuera del filtro.
3. `scrollIntoView` actúa sobre la tarjeta, sin mover el scroll de otros
   paneles.
4. Tarjeta, caja y detalle quedan resaltados de forma coherente.

Cambiar filtro, panel responsive o scroll no borra una selección válida. Si el
filtro excluye la selección, la UI lo comunica y evita mostrar dos selecciones.

## Zoom, pan y fit

Imagen y SVG comparten dimensiones originales, contenedor y transformación:

```text
screen = translate + original_pixel * scale
```

Las cajas nunca se convierten a porcentajes ni se recalculan desde el tamaño
CSS. La toolbar dispone de:

- Ajustar a pantalla;
- 25 %, 50 %, 100 % y 200 %;
- acercar/alejar con límites;
- reset;
- pan por arrastre cuando `scale` supera el fit;
- centrar detección seleccionada.

Resize, cambio de imagen y colapso de panel recalculan el fit del contenedor, no
las coordenadas originales. El pan se limita para no perder por completo el
raster. Labels/boxes/grid son toggles independientes con `aria-pressed`.

## Navegación entre detecciones

Anterior/siguiente usan el orden estable `cell_index` de la imagen actual.
`Siguiente sin revisar` busca desde la selección, continúa por páginas
incrementales y comunica cuando no quedan pendientes. No descarga todos los
crops para calcular la navegación.

El selector de imagen actualiza original, overlay, galería y conteos como una
sola transición. No se renderizan simultáneamente todos los originales de un
run.

## Carga de binarios

- El original se solicita una vez para la imagen activa.
- Crops se solicitan cuando su tarjeta entra o se aproxima al viewport.
- Cada fetch usa JWT; una URL física nunca se interpola desde metadata.
- La UI muestra `safe_name` (`Imagen 001`, …), no `original_filename`.
- Una URL de blob pertenece a un ID de recurso.
- Al cambiar ese ID, abortar, fallar o desmontar, se ejecuta
  `URL.revokeObjectURL`.
- No se revoca una URL todavía usada por otra tarjeta; caché y ownership deben
  ser explícitos.

Tarjetas se memoizan y la respuesta paginada incluye estado y metadata para
evitar N+1. El overlay sólo contiene boxes de la imagen actual. El límite
aceptado del perfil 1.0.0 y el límite mínimo de respuesta están alineados en
500, de modo que todo candidato aceptado de esa imagen conserva sincronización
crop-box. La validación incluye al menos 500 detecciones sintéticas, pero no se
declara éxito sin medir.

## Revisión humana

Acciones para quien posea `scientific.cell_detection.review`:

- Aceptar detección;
- Rechazar detección;
- Requiere atención;
- Agregar comentario.

Reglas:

- rechazo y atención requieren comentario;
- comentario solo requiere texto;
- rechazo pide confirmación explícita;
- guardar inserta una fila; nunca actualiza la anterior;
- tras éxito se anuncia el resultado en `aria-live` y se ofrece
  `Siguiente sin revisar`;
- fallo conserva texto y selección para reintento manual;
- no existe aprobación/rechazo masivo;
- operator ve los resultados pero no controles de review.

La última decisión efectiva controla estilos y conteos; `comment_only` agrega
historia sin cambiarla. El historial permanece ordenado por `created_at,id`.

## Accesibilidad

- paneles son regiones con headings visibles;
- tarjeta y box tienen nombre que incluye código y estado;
- Enter/Space reproducen click;
- foco visible no depende del color;
- la caja seleccionada usa grosor/indicador/label además de color;
- toggles exponen `aria-pressed`;
- mensajes de guardado/error usan `aria-live`/`role=alert`;
- controles iconográficos tienen nombre accesible;
- crops tienen alt como `Crop técnico de CELL-…`, nunca una etiqueta clínica;
- el original usa su `safe_name`, sin filtrar el filename de ingesta;
- pestañas móviles conservan foco y usan roles/atributos apropiados.

## Responsive y estados de error

Escritorio mantiene tres paneles. En ancho mediano se puede colapsar resumen; en
móvil se usan segmentos `Resumen`, `Células`, `Imagen`, `Detalle`. Selección,
imagen, filtro, revisión escrita y transformación se preservan al cambiar de
segmento.

Cada panel distingue carga, error y vacío:

- run sin detecciones;
- imagen sin candidatos;
- filtro sin resultados;
- crop no disponible;
- original no disponible;
- review no guardada;
- run fallido.

No se dejan espacios en blanco ni se muestran stack traces, paths, PII,
probabilidades, diagnósticos, categorías morfológicas, N/C ratio, diámetro o
magnificación no registrada.
