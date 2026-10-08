# 76.3B/C — Adaptador YOLO y resolver del backend

Estado documental: `CURRENT_DOC` — implementación y pruebas simuladas verificadas el 2026-10-08.
Alcance: adaptación HTTP y registro centralizado. **76.3D y el flujo clínico completo no ejecutados.**
Contrato origen: [Runtime local 76.3A](yolo_runtime.md). El backend no importa
Ultralytics, PyTorch ni módulos del proyecto de segmentación.

## Selección y configuración

La única selección sigue siendo `CELL_DETECTOR_KEY`, leída por `Settings` y utilizada
por `CellAnalysisService`. El resolver contiene un diccionario con
`connected_components_v1` y `yolo26_seg_v1`; mantiene el contrato `Detector` y rechaza
claves desconocidas. Resolver o consultar el perfil no hace solicitudes HTTP.

En el `.env` local consumido por Docker Compose, para la futura validación 76.3D:

```dotenv
CELL_DETECTOR_KEY=yolo26_seg_v1
YOLO_RUNTIME_URL=http://host.docker.internal:8765
YOLO_RUNTIME_TOKEN=<mismo-token-secreto-del-runtime-macOS>
YOLO_RUNTIME_TIMEOUT_SECONDS=120
```

El valor predeterminado de selección sigue siendo `connected_components_v1`;
no necesita un token YOLO. El token se valida al invocar el adaptador, debe tener
al menos 32 caracteres ASCII imprimibles sin espacios y nunca forma parte del
perfil ni del `repr` de Settings. Se añadieron únicamente tres configuraciones
YOLO: URL, token y timeout. No se modificó el `.env` operativo ni se activó YOLO.
Docker Compose ya utiliza `env_file: .env`; no se necesita otra variable de selección
ni modificar su topología. Los cambios de entorno requieren recrear el contenedor
backend para aplicarse (un reload de código no actualiza el entorno del proceso).

Solo se acepta el origen HTTP(S) `host.docker.internal`, con puerto válido y sin
credenciales, ruta, query o fragmento. `localhost` dentro de Docker apunta al propio
contenedor y no se admite. No se siguen redirecciones y `trust_env=False` deshabilita
proxies implícitos. Esta política está limitada a Docker Desktop/macOS; otra
arquitectura de red requiere una revisión explícita del destino confiable.
El timeout positivo y finito se aplica a las fases HTTP de httpx; no es un deadline
global para todo el análisis ni modifica el timeout del flujo clínico.

## Adaptación y semántica

Flujo existente: `cell_analysis.py → resolve_detector() → yolo26_seg_v1 →
POST /v1/detect → DetectionResult → bbox_crop_v1`.

Se aplica EXIF transpose antes del envío, se convierte a RGB y se codifica PNG sin
metadatos para impedir una segunda rotación. El original permanece intacto;
`bbox_crop_v1` sigue recortando sus píxeles originales orientados. Se envía cuerpo
binario con Bearer token y los parámetros query del contrato real de 76.3A.

Se exige HTTP 200 y una respuesta completa, tipada y finita. Se validan identidad,
versiones, dispositivo MPS, checkpoint, dimensiones, opciones efectivas, contadores,
warnings conocidos, cajas, centroides, máscaras y áreas. Las máscaras degeneradas
o cuya área no concuerda con el área reportada se rechazan; se admite una tolerancia
numérica de 1e-4 relativa / 1e-3 absoluta para esa comparación. No se corrigen cajas
fuera de límites ni se sustituyen respuestas inválidas por resultados vacíos.

La identidad queda congelada al checkpoint de 76.3A:

- Ruta relativa: `smear_segmentation_project/runs/yolo26_seg/yolo26n_rbc_1024_v1/weights/best.pt`.
- SHA-256: `1a64bc34d188a48b7ed4fcd3276a41aa61d4ab7c037e360ac4beab3e24c31c26`.
- Detector: `yolo26_seg_v1`, versión `1.0.0`.
- Algoritmo: `yolo26-seg-tiling-global-nms-1.0.0`.

El Runtime debe devolver una ruta absoluta terminada en esa ruta relativa y el mismo
hash. El perfil existente guarda identidad, hash y políticas de conversión sin nuevas
tablas ni llamadas a la BD desde el adaptador. Otro checkpoint se rechaza; su adopción
requiere una implementación versionada, no cambiar silenciosamente el artefacto.

Cada detección válida se convierte a `ConnectedComponent`:

- `confidence` se conserva como `detector_score`; bbox y centroide permanecen en
  coordenadas originales orientadas.
- `area_px` continua se convierte con `ceil` al entero exigido por el contrato;
  `area_policy=runtime_area_ceil` documenta la cuantización. No equivale a medir
  píxeles de una máscara rasterizada.
- `perimeter_px`, `circularity` y `solidity` son **None/null**, con política de perfil
  explícita y warning `YOLO_GEOMETRIC_METRICS_UNAVAILABLE`. No se inventan mediciones
  ni se calculan a partir de una caja como si describieran la célula.
- Las tres anotaciones de `ConnectedComponent` ahora admiten None, conforme a la
  nulabilidad que ya existe en PostgreSQL y en la interfaz. La estructura de
  `DetectionResult` no cambió y connected components sigue produciendo sus métricas.
- `threshold_value=None`; el perfil usa `threshold_method=yolo_confidence`.
- `ACCEPTED` significa elegible para crop, no diagnóstico ni aprobación humana.
  No se aplican filtros morfológicos de connected components a YOLO.
- Orden determinista por confidence descendente, tile y geometría. Índices desde 1.
  Se conserva el máximo de 500 aceptadas compatible con la revisión existente;
  excedentes permanecen como `REJECTED_BY_FILTER/MAXIMUM_COMPONENTS_EXCEEDED`, sin crop.
  El perfil puede reducir ese límite; no puede elevarlo sobre 500.

El contrato público existente no transporta máscaras ni procedencia por tile dentro
de cada componente; se usan para validar y ordenar, pero no se agregan campos nuevos.
La trazabilidad persistente del detector/versiones/checkpoint corresponde al perfil
existente. El JSON del Runtime no se persiste como un nuevo artefacto.

## Errores

El adaptador lanza `YoloRuntimeError` con un código seguro:
`YOLO_RUNTIME_TOKEN_INVALID`, `YOLO_RUNTIME_TIMEOUT`, `YOLO_RUNTIME_UNAVAILABLE`,
`YOLO_RUNTIME_HTTP_<status>`, `YOLO_RUNTIME_INVALID_RESPONSE` o
`YOLO_RUNTIME_RESPONSE_MISMATCH`. No incluye respuestas HTTP, imágenes ni secretos
en mensajes; no reintenta ni hace fallback a connected components.

`cell_analysis.py` conserva su manejo actual: excepciones no especializadas se
convierten a `CELL_DETECTION_FAILED`/HTTP 500 y abortan la ejecución. Los códigos
específicos anteriores están disponibles en el límite del adaptador; no se añadió
una nueva taxonomía pública de errores ni otro orquestador.

## Validación y archivos

Ejecutado mediante Makefile en el contenedor backend:

- `make test-backend-yolo-adapter`: **106 aprobadas** (HTTP simulado).
- `make test-backend-detection-crop`: **111 aprobadas** antes y después de integrar;
  conserva las pruebas golden de connected components y los contratos de clasificación/crop.

Se comprobó selección desde `CELL_DETECTOR_KEY`, autenticación, EXIF, contenido PNG,
crops con píxeles originales, confidence, métricas nulas, orden, límite de componentes,
timeouts, errores HTTP, rechazo de redirecciones/destinos no confiables, identidad,
respuestas incompletas, NaN/Infinity y ausencia de fallback. Las pruebas no requieren
Runtime activo, dataset ni conexión a PostgreSQL.

Archivos creados: adaptador `backend_api/app/services/detectors/yolo26_seg_v1.py`,
pruebas `backend_api/tests/test_yolo_detector_adapter.py` y este documento.
Archivos actualizados: `backend_api/app/config.py`, `backend_api/app/models/cell_detection.py`
(solo anotaciones de tres métricas), `backend_api/app/services/detectors/resolver.py`,
`.env.example`, `Makefile`, `docs/README.md`.

No se modificaron PostgreSQL, clasificadores, connected components, bbox crop,
Runtime, dataset ni checkpoint. TEST no se leyó ni modificó. No se realizaron commits.
La inferencia real a través del adaptador y el flujo clínico completo quedan para 76.3D;
los ensayos reales documentados en 76.3A no sustituyen esa validación.
