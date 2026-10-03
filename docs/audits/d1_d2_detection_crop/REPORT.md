# D1 + D2 — Separación de CELL DETECTION y CELL CROP

Estado documental: `HISTORICAL_AUDIT` — implementación y validación, 2026-10-03.

Base: [auditoría PRE-S4 existente](../pre_s4_detection_workflow/REPORT.md), sin repetirla. Referencia anterior: `dfc96215968b25794f98fb69e8f7e462a9827e13`. Cambios sin commit ni push.

## Resultado

| Campo | Resultado |
|---|---|
| D1 CELL DETECTION | **APPROVED** — separación y equivalencia verificadas |
| configured detector | `connected_components_v1` |
| resolver | `app/services/detectors/resolver.py::resolve_detector` |
| D1 behavior changed | **NO**, resultado científico y metadata conservados |
| D2 CELL CROP | **APPROVED** — extracción y equivalencia verificadas |
| configured crop | `bbox_crop_v1` |
| crop implementation | `app/services/crops/bbox_crop_v1.py::crop_image` |
| D2 behavior changed | **NO**, PNG, píxeles, geometría y SHA conservados en las referencias verificadas |
| Detection equivalence | **PASS** |
| Crop SHA equivalence | **PASS** |
| Database migration | **NO** |
| Classification changed | **NO** |
| Ready for next phase | **NO** para un gate global verde: persisten fallas previas de pruebas detalladas abajo. D1/D2 están implementados y validados en su alcance. |

Las aprobaciones D1/D2 describen este refactor; no certifican que todas las pruebas del repositorio pasen ni autorizan S4.

## Flujo implementado

```text
SmearUpload → ingesta → Microscopy Analysis → Quality Gate
→ CellAnalysisService
  → CELL DETECTION: resolve_detector → connected_components_v1
  → DetectionResult: componentes/instancias, métricas, warnings; sin crops
  → CELL CROP: resolve_crop_strategy → bbox_crop_v1
  → ImageDetectionResult: componentes + crops PNG
  → almacenamiento y persistencia existentes → cell_crops
→ PIPELINE EXISTENTE: CellClassificationService → ProductiveModelResolver
→ modelo productivo → predicción P/U → Smear Summary → frontend
```

Configuración backend: `CELL_DETECTOR_KEY=connected_components_v1` y `CELL_CROP_STRATEGY_KEY=bbox_crop_v1`, ambos defaults. El constructor del servicio permite resolver claves explícitas. Las claves desconocidas o todavía no implementadas fallan, sin fallback silencioso. No hay selector HTTP/frontend, registro dinámico ni framework nuevo.

El servicio resuelve una vez sus implementaciones. Usa la identidad resuelta en elegibilidad, búsqueda de runs equivalentes, creación y eventos; ejecuta con el `profile_snapshot` persistido. Se mantienen `detector_version=1.0.0`, `algorithm_version=pillow-connected-components-1.0.0`, el perfil completo y la equivalencia SQL existente.

El detector conserva su preparación EXIF/RGB y algoritmo. La etapa crop obtiene el original EXIF orientado, sin resize ni conversión de modo, y reutiliza `BoundingBox.padded → oriented.crop → PNG optimize=False`. Conserva `component_index`, padding y un crop por componente accepted; los rejected permanecen disponibles sin crop. La verificación del original y sus errores se trasladan a la función común `cell_detection.detect_path`; almacenamiento, SHA, promoción, repositorios y transacciones no se modifican.

## Archivos creados y piezas trasladadas

Rutas relativas a `backend_api/`, salvo indicación:

| Etapa | Creado / trasladado |
|---|---|
| D1 | `app/services/detectors/resolver.py`: contrato pequeño y resolución determinista |
| D1/D2 | `app/services/cell_detection.py`: composición de etapas; `detect_path` trasladado desde el detector |
| D2 | `app/services/crops/__init__.py`, `bbox_crop_v1.py`, `resolver.py`: bloque de crop extraído y resolución independiente |
| Contratos | `app/models/cell_detection.py`: `DetectionResult` sin crops; `ImageDetectionResult` combinado para persistencia; error de entrada compartido |
| Integración | `app/config.py`, `app/services/cell_analysis.py`, `app/services/detectors/connected_components_v1.py` |
| Equivalencia | `tests/test_detection_crop_equivalence.py`, `tests/fixtures/detection_crop/connected_components_v1.json` |
| Regresión | `tests/test_cell_detection_services.py`: imports de la composición; `test_cell_detection_postgres.py`: perfil completo y consumo por clasificación |
| Fixtures PostgreSQL | `test_cell_detection_postgres.py`, `test_cell_classification_postgres.py`: guard de tablas requeridas en lugar de exigir una revisión histórica exacta |
| Ejecución/documentación | `Makefile`: dos targets focalizados; este reporte y su entrada en `docs/README.md` |

Los imports internos de `detect_path` y de detección+crops ahora apuntan a `app.services.cell_detection`. `connected_components_v1.detect_image` devuelve únicamente detección: es el cambio intencional de responsabilidad, no un cambio científico. No se modificó código productivo de clasificación, modelo, summary, frontend ni SQL de persistencia.

## Evidencia de equivalencia

Antes de editar el detector se capturaron referencias con su implementación anterior, ejecutada en el mismo contenedor. El fixture incluye perfil completo y resultados para **11 casos**: default, vacío, rechazos, límite de componentes, padding recortado al borde, L, RGBA, paleta P y JPEG con EXIF 2/6/8.

Cada caso compara dimensiones raw/orientadas, threshold, todos los campos de cada componente (bbox, centroide, área, perímetro, circularidad, solidity, accepted/rejected, códigos, score), orden, warnings y metadata de crops. Compara SHA-256 del PNG y de los píxeles decodificados, modo y formato. Además verifica píxeles contra el recorte directo del original orientado y la correspondencia accepted→crop. **Todos coinciden**. Son referencias sintéticas de regresión; no una evaluación de desempeño sobre nuevos datasets.

Comparación AST adicional contra HEAD: sin cambios en `_components`, `_foreground_mask`, `_otsu_threshold`, `_rejection_codes`, `_solidity`, `_convex_hull`, `_polygon_area`, `_validate_profile`, `profile_snapshot`, identidades ni constantes de perfil.

Las pruebas nuevas verifican resolución/defaults, copias independientes del perfil, configuración efectiva, rechazo de extensiones no implementadas, ejecución detección→crop, uso del padding recibido y detección sin codificador PNG. Los modos no compatibles siguen fallando en crop con `UNSUPPORTED_CROP_MODE`.

La integración PostgreSQL que pasa crea una ejecución real, valida archivos y hashes persistidos, perfil, geometría, eventos e idempotencia. Ahora también lee esos mismos crops mediante `CellClassificationRepository.detection_run_input` y `freeze_classification_inputs`, comprobando rutas, SHA, elegibilidad y manifiesto determinista. Pasan asimismo las pruebas existentes de clasificación por lotes 1/50/500 e idempotencia con modelo de prueba. No se ejecutó inferencia con un modelo productivo real.

## Tests y límites del gate

Todo se ejecutó mediante Makefile y Docker. PostgreSQL utilizó transacciones externas con savepoints y rollback; las fixtures verifican ausencia de residuos.

| Ejecución | Resultado |
|---|---|
| `make test-backend-detection-crop` | **111 passed**, 2 warnings de deprecación |
| `make test-backend-detection-crop-integration` | **9 passed, 4 failed**, 2 warnings |
| `make test-backend` | **562 passed, 14 failed, 54 deselected**, 12 warnings; corrida anterior a agregar el último test focalizado de configuración |
| Código anterior, integración PostgreSQL | **9 passed, los mismos 4 failed**, 2 warnings |
| Código anterior, seis módulos de la suite general que fallaron | **62 passed, los mismos 14 failed** |
| `git diff --check` | **PASS** |

Inicialmente los 13 casos PostgreSQL se detenían en setup: las fixtures exigían `20260810_05`, pero la BD usa `pg_v2_baseline`. Se sustituyó únicamente ese requisito obsoleto por comprobación de las tablas necesarias, manteniendo las verificaciones de seguridad, restricciones y rollback. No se aplicó ni generó una migración.

Las cuatro fallas PostgreSQL son previas, reproducidas con el código de HEAD y las mismas fixtures compatibles con el baseline:

- `test_integrity_failure_finishes_failed_without_partial_results`: esperaba `CHECKSUM_MISMATCH`/409; el flujo existente falla antes en `LocalStorage.resolve_verified` y produce `CELL_CROP_STORAGE_ERROR`/500. Se preservó ese comportamiento y no se relajó la aserción.
- `test_api_rbac_and_safe_block_without_productive_model`: 403 donde esperaba 200.
- `test_reviews_audit_idempotency_and_append_only_integrity`: 403 donde esperaba 201.
- `test_human_classification_is_editable_audited_and_keeps_ai_immutable`: 403 donde esperaba 200.

Las 14 fallas generales son `FileNotFoundError` por rutas de archivos de repositorio no disponibles en la ubicación esperada dentro del contenedor (13) y ausencia del ejecutable `git` (1). Afectan seis módulos: `test_backend_runtime_role_contract`, `test_case_gradcam_service`, `test_docker_postgres_contract_guard`, `test_docker_postgres_tooling`, `test_quality_queue_contract` y `test_scientific_storage_docker_contract`. Se reprodujeron con el código anterior; no se modificó infraestructura para ocultarlas.

La comparación anterior se hizo en `/tmp/capstone_d1_d2_baseline` dentro del contenedor, restaurando desde HEAD los cuatro archivos productivos existentes modificados por D1/D2. Se conservaron las fixtures compatibles con el esquema actual; la comparación PostgreSQL utilizó la versión de las pruebas anterior a las nuevas aserciones D1/D2. Los targets temporales de comparación están en `/tmp/d1_d2_tests.mk` del host. Logs locales: `/tmp/d1_d2_focused.log`, `/tmp/d1_d2_final_postgres.log`, `/tmp/d1_d2_backend_tests.log`, `/tmp/d1_d2_baseline_original_postgres.log`, `/tmp/d1_d2_baseline_regressions.log`.

## Future extension points

Detectors:

- `connected_components_v1`: implementado/default.
- `yolo_seg`: futuro, no implementado.
- `faster_rcnn`: futuro, no implementado.
- `u_net`: futuro, no implementado.

Crop strategies:

- `bbox_crop_v1`: implementado/default.
- `segmented_crop`: futuro, no implementado.
- `masked_crop`: futuro, no implementado.

Una futura implementación se incorpora al resolver correspondiente y debe cumplir el contrato de componentes/coordenadas o crops. En esta fase hay una sola estrategia válida: no se agregó su clave al `profile_snapshot`, para conservarlo exactamente. Antes de habilitar otra estrategia o cambiar parámetros bajo la misma identidad habrá que versionar su efecto y revisar la equivalencia de runs: el índice actual no incluye hash del perfil ni clave de crop. Este refactor no habilita combinaciones científicamente distintas bajo una identidad compartida.

No se ejecutó S4, entrenamiento, migraciones, commit ni push; no se inspeccionó `malaria_dataset_split_project`. Se preservaron la auditoría PRE-S4 y su entrada de índice, presentes antes del trabajo.
