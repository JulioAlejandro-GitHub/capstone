# Algoritmo `connected_components_v1`

## Identidad y propósito

| Campo | Valor |
|---|---|
| `detector_key` | `connected_components_v1` |
| `detector_version` | `1.0.0` |
| `algorithm_version` | `pillow-connected-components-1.0.0` |
| naturaleza | baseline académico determinístico |
| salida | regiones candidatas, bboxes y crops |

No es RBCNet ni un detector clínicamente validado. No clasifica, no estima
probabilidad, no identifica infección y no diagnostica. Un score emitido por el
algoritmo es geométrico/heurístico y no se interpreta como confianza clínica.

## Perfil reproducible

Cada run guarda el snapshot completo, no sólo el nombre del perfil:

- `detector_key`, `detector_version`, `algorithm_version`;
- `orientation_policy=exif_transpose`;
- `threshold_method=otsu_dark_foreground` y polaridad foreground oscuro;
- `blur_kernel=3`;
- `morphology_kernel=3`;
- `morphology_iterations=1`;
- `minimum_component_area_px=64`;
- `maximum_component_area_px=250000`;
- `minimum_width_px=6`, `minimum_height_px=6`;
- `minimum_circularity=0.05`, `minimum_solidity=0.20`;
- `reject_border_components=true`;
- `crop_padding_px=4`;
- `maximum_components_per_image=500`;
- conectividad `8`;
- `component_separation=none`;
- `coordinate_space=original_image_pixels`;
- `coordinate_origin=top_left`;
- `bbox_format=xywh`.

Los límites geométricos son académicos y configurables. Un cambio de valor,
fórmula, orden, conectividad, orientación o estrategia de separación exige un
snapshot diferente y, cuando altera la semántica del algoritmo, otra versión.

## Entrada segura y orientación

Para cada imagen congelada:

1. resolver la key relativa bajo `STORAGE_ROOT`, rechazando escape y symlinks;
2. exigir archivo regular;
3. comparar bytes y SHA-256 con el manifiesto;
4. decodificar de forma segura y comprobar formato y dimensiones **raw**;
5. aplicar `PIL.ImageOps.exif_transpose` sólo en memoria;
6. conservar ancho/alto del raster orientado para API, bbox, crop y overlay.

`exif_transpose` aplica la rotación/reflexión declarada por EXIF y elimina esa
ambigüedad sin redimensionar ni interpolar. En este contrato
`original_image_pixels` significa el raster original en su orientación visual
canónica: mismos píxeles, sin reescalado. El checksum continúa siendo el del
archivo inmutable raw.

El navegador presenta el JPEG respetando EXIF; por eso el visor usa las
dimensiones orientadas devueltas por la API. Un bbox calculado sobre la matriz
raw con dimensiones orientadas sería inválido.

## Segmentación

La representación orientada y su modo se conservan para crops. Una copia RGB de
análisis:

1. se convierte a luminancia;
2. recibe suavizado gaussiano con kernel 3;
3. calcula threshold global de Otsu;
4. marca foreground cuando `luminance <= threshold`;
5. aplica apertura y cierre morfológicos con kernel 3, una iteración;
6. etiqueta componentes con vecindad de 8 píxeles.

Otsu y las operaciones morfológicas sólo construyen la máscara. Si la
luminancia no tiene rango suficiente, el threshold queda `NULL`, la máscara es
vacía y se emite `NO_ACCEPTED_COMPONENTS`; no se inventa foreground. Estas
operaciones no cambian el archivo original.

La estrategia `component_separation=none` no ejecuta watershed ni distance
transform. Círculos/células en contacto pueden quedar como un componente único.
Es una limitación conocida, explícita y cubierta con una imagen sintética; no se
oculta como una detección clínica correcta. La versión Pillow evita incorporar
SciPy/scikit-image al runtime de FastAPI sólo para esta línea base.

## Métricas y filtros

Para cada etiqueta se calculan sobre la máscara:

- área en píxeles;
- bbox mínimo;
- centroide;
- perímetro;
- circularidad, cuando el perímetro permite calcularla;
- solidity, cuando existe un área de envolvente válida;
- contacto con cualquiera de los cuatro bordes.

Fórmulas versionadas:

```text
circularity = min(1, 4 * pi * area / perimeter_edges^2)
hull_estimate = max(
  area,
  convex_hull_area_of_boundary_centres + (bbox_width + bbox_height) / 2
)
solidity = min(1, area / hull_estimate)
```

`perimeter_edges` cuenta lados de pixel expuestos. La corrección de medio píxel
en el hull evita subestimar componentes pequeños. Si el perímetro fuese cero,
la implementación usa el valor geométrico acotado definido por esta versión; no
se presenta como medición clínica.

Un componente queda `rejected_by_filter` si incumple un filtro. `rejection_code`
conserva la primera razón según esta prioridad estable y
`metrics_json.rejection_codes` conserva todas:

1. `BORDER_COMPONENT`;
2. `COMPONENT_AREA_BELOW_MINIMUM`;
3. `COMPONENT_AREA_ABOVE_MAXIMUM`;
4. `COMPONENT_WIDTH_BELOW_MINIMUM`;
5. `COMPONENT_HEIGHT_BELOW_MINIMUM`;
6. `COMPONENT_CIRCULARITY_BELOW_MINIMUM`;
7. `COMPONENT_SOLIDITY_BELOW_MINIMUM`;
8. `MAXIMUM_COMPONENTS_EXCEEDED`.

El resto queda `accepted` y genera una detección con
`automated_status=candidate`. El máximo cuenta componentes geométricamente
aceptables en orden raster; los que lo exceden se conservan como rechazados, no
se omiten.

Todos los componentes, incluso rechazados, se persisten para explicar conteos.
El máximo por imagen es un control de recursos versionado; nunca autoriza a
fabricar boxes ni a procesar en orden no determinístico.

## Coordenadas, orden e identidad

Contrato:

```text
coordinate_space = original_image_pixels
origin           = top_left
format           = xywh
x grows          = right
y grows          = down
```

Para un raster orientado `W x H`:

```text
0 <= x < W
0 <= y < H
width  > 0
height > 0
x + width  <= W
y + height <= H
```

La caja se obtiene directamente de los extremos del componente; no se
normaliza, escala ni vuelve a calcular en React. Componentes/detecciones se
descubren en recorrido raster row-major. `component_index` sigue ese orden y
`cell_index` es global dentro del run: primero `sequence_number` de imagen y
luego componente aceptado. `CELL-` más 12 hexadecimales mayúsculos no depende
del orden de un `set` o de una consulta SQL sin `ORDER BY`.

`detector_score`, cuando existe, se calcula:

```text
clamp((circularity + solidity) / 2, 0, 1)
```

Es un score geométrico para ordenar/inspeccionar el baseline, no una
probabilidad ni una confianza diagnóstica.

## Crops

Sólo un componente aceptado genera crop. El rectángulo de crop agrega
`crop_padding_px` y se limita a `[0,W] x [0,H]`. El contenido se extrae del
raster orientado original, no de la máscara, la luminancia ni la copia RGB de
análisis. Se conserva el modo/píxeles para modos PNG compatibles (`1`, `L`,
`LA`, `P`, `RGB`, `RGBA`, `I;16`, `I;16L`, `I;16B`) y se codifica sin resize,
overlay o realce. Un modo que PNG no admite falla de manera sanitizada con
`UNSUPPORTED_CROP_MODE`; no se convierte silenciosamente ni se deja un run
parcial.

Antes de persistir metadata se reabre el PNG y se verifican:

- formato;
- dimensiones esperadas;
- tamaño mayor a cero;
- SHA-256 de los bytes finales.

El bbox sigue describiendo el componente sin padding; `padding_px` describe la
intención configurada y el clipping de bordes se deduce con bbox/dimensiones.

## Determinismo y límites

Con los mismos bytes de entrada, versión, snapshot y runtime soportado deben
coincidir máscara, orden, componentes, boxes y crops. La reproducibilidad se
prueba con imágenes sintéticas, no con imágenes clínicas descargadas.

Limitaciones conocidas:

- Otsu global puede fallar con iluminación no uniforme;
- foreground oscuro puede incluir polvo, tinción o estructuras no celulares;
- apertura/cierre puede eliminar objetos pequeños o unir regiones próximas;
- sin watershed, contactos quedan unidos;
- filtros geométricos no validan biología;
- no existe calibración en micrómetros ni magnificación inferida;
- el baseline no tiene sensibilidad/especificidad clínica demostrada.
