# 76.3A — Runtime YOLO local

Estado documental: `CURRENT_DOC` — implementación local validada el 2026-10-08.
Alcance: Runtime exclusivamente; 76.3B–76.3D no implementados en este cambio.

## Inicio en macOS

Desde la raíz del repositorio, con el entorno existente validado:

```sh
export YOLO_RUNTIME_TOKEN="$(openssl rand -hex 32)"
malaria_dl_local_project/.venv-metal/bin/python smear_segmentation_project/runtime_yolo.py --host 127.0.0.1 --port 8765
```

El cliente debe usar el mismo token; no guardarlo en Git. Se exige un mínimo de
32 caracteres. Dependencias declaradas en `smear_segmentation_project/pyproject.toml`,
extras `runtime` y `test`. Entorno comprobado: Python 3.12, PyTorch 2.14.1,
Ultralytics 8.4.174, FastAPI 0.141.1. No se instalaron dependencias durante esta fase.

Un worker carga el checkpoint una vez al iniciar. Fallan explícitamente la ausencia
de MPS, un checkpoint incompatible o `PYTORCH_ENABLE_MPS_FALLBACK=1`.
No existe fallback CPU. Las inferencias se serializan para proteger el predictor.
El servidor limita la concurrencia a cuatro conexiones/tareas; puede responder 503
al superar esa capacidad. No registra accesos, imágenes ni datos clínicos.

El bind loopback fue accesible desde Docker Desktop mediante
`host.docker.internal:8765` en esta máquina. No se requiere `0.0.0.0` y el launcher
rechaza binds wildcard/públicos. Si otra instalación requiere una interfaz privada,
seleccionarla explícitamente y restringir su acceso con el firewall del host.

Configuración propia del Runtime:

| Variable | Predeterminado |
|---|---|
| `YOLO_RUNTIME_TOKEN` | Obligatorio |
| `YOLO_RUNTIME_HOST` | `127.0.0.1` |
| `YOLO_RUNTIME_PORT` | `8765` |
| `YOLO_RUNTIME_CHECKPOINT` | `smear_segmentation_project/runs/yolo26_seg/yolo26n_rbc_1024_v1/weights/best.pt` (resuelto desde el proyecto) |
| `YOLO_RUNTIME_MAX_UPLOAD_BYTES` | `20971520` |
| `YOLO_RUNTIME_MAX_IMAGE_PIXELS` | `25000000` |

## Contrato HTTP v1

`GET /health`, sin token: `status`, `model_loaded`, `device`, `runtime_version`,
`checkpoint_sha256`. Solo se sirve después de cargar el modelo en MPS.

`POST /v1/detect`: cuerpo binario JPEG, PNG o TIFF de una página;
`Authorization: Bearer <token>`. No usa multipart ni recibe rutas de archivos.
Ejemplo (usar exclusivamente una imagen autorizada TRAIN/VAL):

```sh
curl --fail-with-body http://127.0.0.1:8765/v1/detect \
  -H "Authorization: Bearer $YOLO_RUNTIME_TOKEN" \
  -H 'Content-Type: application/octet-stream' \
  --data-binary @/ruta/autorizada/val/imagen.jpg
```

Parámetros query opcionales: `confidence=0.25` (0,1], `nms_iou=0.7` (0,1],
`max_detections_per_tile=1000` [1,2000]. Campos desconocidos son rechazados.
`nms_iou` se pasa al predictor y se aplica a la consolidación global.
Los valores son parámetros operativos iniciales, no umbrales optimizados en esta fase.

Respuesta JSON:

- Identidad: `detector_key=yolo26_seg_v1`, `detector_version=1.0.0`,
  `runtime_version=1.0.0`, `algorithm_version=yolo26-seg-tiling-global-nms-1.0.0`,
  `model_checkpoint` (ruta), `checkpoint_sha256`, `device=mps`.
- Geometría: `image_width`, `image_height` después de EXIF transpose,
  `tile_size=1024`, `tile_overlap=256`, `coordinate_space=original_image_pixels`,
  `orientation_policy=exif_transpose`, `bbox_format=xywh`.
- `options`: parámetros efectivos; `detections`: lista de objetos con `bbox`
  `{x,y,width,height}` entero, `confidence`, `centroid_x`, `centroid_y`, `area_px`,
  `tile_id`, `geometry_source` y `mask_polygon` (pares XY globales o null).
- `raw_detection_count`, `invalid_detection_count`, `consolidated_detection_count`,
  `final_detection_count`, `warnings`.

`raw = invalid + consolidated + final`. El área de polígono es continua (float),
no un conteo de píxeles rasterizados. Centroide y área proceden de momentos del
polígono; si falta máscara se usa geometría de bbox y una advertencia explícita.
Los polígonos son el contorno que expone Ultralytics; no representan necesariamente
agujeros o cada región desconectada. No se serializan matrices de máscaras.

Errores: 401 token inválido/ausente; 413 límite de bytes/píxeles; 415 formato no
admitido o multipágina; 422 imagen/parámetros inválidos; 503 fallo de inferencia.
No hay cambio silencioso de dispositivo ni de detector.

## Tiling y consolidación

Se reutilizan `tiles_for_image()`, `axis_starts()`, `tile_id()` y constantes RBC.
Los imports de tipos de anotación en `tiling.py` y `targets.py` quedan bajo
`TYPE_CHECKING`, evitando cargar el subsistema de datasets al importar el Runtime.
`polygon_to_normalized_tile_points()` es una transformación de entrenamiento;
no corresponde a las coordenadas locales en píxeles que devuelve inferencia.

El predictor recibe tiles RGB; las cajas y polígonos se recortan al raster real y
se trasladan por el origen del tile. El último tile cubre el borde según la grilla
existente (su solapamiento puede superar 256). Imágenes pequeñas no se expanden
artificialmente antes del predictor.

NMS global greedy de cajas, por confidence descendente con desempates por tile y
geometría; suprime solo cuando IoU supera el umbral. Conserva score, máscara y tile
de la detección elegida. Cercanía por sí sola no suprime células. Es determinista
para entradas iguales, pero puede suprimir células distintas superpuestas o
conservar duplicados parciales con bajo IoU. No garantiza cobertura completa ni
valida precisión clínica. El límite por tile emite advertencia cuando se alcanza.

Referencia de API: [Ultralytics predict](https://docs.ultralytics.com/modes/predict/)
(`masks.xy`, `retina_masks`, selección de dispositivo).

## Evidencia de validación

`make test-yolo-runtime`: **7 aprobadas**, dos advertencias de deprecación de
Starlette/TestClient. Cubre autenticación, contrato, límites, errores sin fallback,
EXIF, geometría global, clipping, tiling y NMS determinista. Usa imágenes sintéticas
y un predictor simulado; no ejecuta entrenamiento ni necesita PostgreSQL.

Comprobaciones adicionales reales en macOS fuera del sandbox:

- Importación correcta; checkpoint cargado en `mps:0`.
- SHA-256: `1a64bc34d188a48b7ed4fcd3276a41aa61d4ab7c037e360ac4beab3e24c31c26`.
- `/health` y `/v1/detect`: HTTP 200 local y desde el contenedor backend.
- Región VAL RGB de 1024×1792 reconstruida de dos tiles materializados:
  `263f3e97-e124-5d28-afa4-d0f999d38247__x2304_y0768.jpg` y
  `263f3e97-e124-5d28-afa4-d0f999d38247__x2304_y1536.jpg`, pegados con overlap 256.
  No es una lectura del frotis original completo; las coordenadas son relativas a
  esa región reconstruida. Selección por presencia de anotaciones VAL, sin ajustar
  parámetros ni checkpoint.
- **102 raw, 0 inválidas, 7 consolidadas, 95 finales**, sin warnings; todas las cajas
  dentro del raster. Respuestas completas idénticas en repetición local/Docker.
- Primera región ensayada (x0000, y0000/y0768 del mismo registro): 0 raw y 0 finales,
  warning `NO_DETECTIONS`; HTTP 200 local/Docker. No fue un descarte geométrico.
- El proceso temporal se detuvo al terminar y el token no se persistió.

Limitación: falta validar un frotis original completo y evaluar exhaustivamente
la calidad de detección; esta fase valida funcionamiento e interoperabilidad.
TEST no se leyó ni modificó. No se modificaron checkpoint, split, backend,
clasificadores, PostgreSQL, `resolver.py`, `connected_components_v1` ni `bbox_crop_v1`.
