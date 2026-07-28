# Pipeline de detección celular basal

## Propósito y límite científico

Prompt 7 agrega una etapa de localización técnica entre el quality gate y una
futura clasificación. El resultado es una lista de **detecciones candidatas**.
No identifica tipos celulares, no distingue `parasitized/uninfected`, no calcula
parasitemia y no produce diagnóstico ni probabilidad clínica.

Detector vigente:

- `detector_key`: `connected_components_v1`
- `detector_version`: `1.0.0`
- `algorithm_version`: `pillow-connected-components-1.0.0`
- `orientation_policy`: `exif_transpose`
- perfil completo: guardado explícitamente en cada run
- ejecución: manual, local y determinística

## Flujo

```text
microscopy_analysis_run congelado
  -> elegibilidad e integridad
  -> cell_detection_run
  -> imagen original segura
  -> representación de análisis en memoria
  -> threshold/morfología/separación configurada
  -> image_connected_components
  -> filtros geométricos
  -> cell_detections en coordenadas originales
  -> crops PNG validados en staging
  -> promoción a storage + metadata + eventos + auditoría
  -> revisión humana append-only
```

No se consume ni se actualiza `quality_assessment_queue_items`. El endpoint de
ejecución comprueba directamente:

1. existencia del analysis run;
2. `ready_for_analysis=true`;
3. quality gate `pass`, o `warning` con aprobación autorizada;
4. presencia de todas las imágenes congeladas;
5. coincidencia de tamaño, SHA-256 y dimensiones;
6. resolución idempotente de cualquier run equivalente creado, en proceso o
   completado, sin iniciar otro procesamiento.

Checksum y dimensiones se verifican primero sobre el archivo raw congelado. El
detector aplica después `ImageOps.exif_transpose` en memoria, sin resize, y usa
el raster visualmente orientado para bbox, crop y dimensiones entregadas al
visor. Así, browser y overlay interpretan el mismo original.

Una llamada que crea un run espera su resultado, pero el trabajo CPU se deriva a
un threadpool para no ocupar directamente el event loop. Un replay idempotente
puede devolver el estado actual del recurso equivalente. No hay worker,
scheduler, polling de progreso en segundo plano ni retry automático.

## Estados e idempotencia

`cell_detection_runs.status` recorre:

```text
created -> processing -> completed
   |                  \-> completed_with_warnings
   \------------------\-> failed
```

La identidad lógica usa:

```text
(analysis_run_id,
 detector_key,
 detector_version,
 algorithm_version,
 input_manifest_sha256)
```

La unicidad es efectiva para estados creados, activos y completados. Un replay
del POST devuelve ese run con `idempotent=true`; no genera componentes/crops de
nuevo. Una ejecución `failed` no se reutiliza: un reintento explícito crea otro
`DET-{token}` y preserva el fallo anterior.

El snapshot del perfil es JSONB y contiene como mínimo threshold, kernels,
iteraciones, límites geométricos, política de borde, padding, máximo de
componentes, estrategia de separación y contrato de coordenadas. Un cambio que
afecte el resultado exige una versión nueva; nunca se actualiza un snapshot
histórico.

## Unidad de persistencia

- `image_connected_components` conserva tanto candidatos aceptados como
  componentes descartados y su `rejection_code`.
- Sólo un componente automático aceptado se convierte en `cell_detection`.
- Cada detección aceptada debe tener un único `cell_crop`.
- El original no se actualiza, copia ni rasteriza con overlays.
- La revisión se inserta posteriormente en `scientific_reviews`; no forma parte
  de las tablas del detector.

La base y el filesystem no comparten una transacción global. Los crops se
escriben y validan primero en un staging exclusivo, se promueven de manera
atómica por archivo y se compensan si falla la transacción de metadata. Un
cierre de proceso entre pasos puede dejar un huérfano recuperable; el script
`scripts/storage/reconcile_cell_crops.py`, dry-run por defecto, lo debe
detectar.

## Fallos, warnings y observabilidad

Antes de procesar se registra `scientific.cell_detection.created`; al iniciar,
`scientific.cell_detection.started`. El cierre registra
`scientific.cell_detection.completed` o `scientific.cell_detection.failed`.
Cada revisión registra `scientific.cell_review.created`.

Los errores expuestos son códigos y mensajes sanitizados. Eventos y auditoría no
contienen:

- rutas absolutas o claves físicas innecesarias;
- binarios, arrays o valores de píxeles;
- JWT, contraseñas o secretos;
- datos personales.

Un error terminal deja `failed_at`, `error_code` y `error_message`, limpia el
staging alcanzable y conserva los eventos necesarios para explicar el intento.
No modifica originales ni inicia otro run.

## Invariantes

1. Toda caja tiene `x,y >= 0`, ancho/alto positivos y termina dentro de las
   dimensiones del raster original orientado documentado.
2. `coordinate_space=original_image_pixels`, origen superior izquierdo y
   formato `xywh`.
3. `cell_index` y `cell_code` son estables y únicos dentro de su contrato.
4. El checksum del original se verifica antes de usarlo y no cambia después.
5. El checksum del crop se calcula sobre el PNG finalmente persistido.
6. Metadata automática, eventos, auditoría y revisiones no se sobrescriben.
7. Un score, si existe, se denomina heurístico/geométrico; no es confianza
   diagnóstica.

## Siguiente frontera

Prompt 8 podrá consumir los crops identificados y versionados. No debe
reinterpretar el detector basal como clasificador ni agregar etiquetas a las
tablas automáticas de Prompt 7.
