# ADR-019: detección celular basal y revisión científica

- Estado: Aceptado
- Fecha: 2026-07-28
- Alcance: Prompt 7, Etapa 2
- Decisiones relacionadas: ADR-003, ADR-004, ADR-011, ADR-013, ADR-015 y
  ADR-018

## Contexto

Los `microscopy_analysis_runs` ya congelan el conjunto de imágenes y el quality
gate determina si un run queda habilitado para análisis. Falta una etapa
reproducible que localice regiones candidatas, genere crops identificables y
permita revisión humana sin presentar sus resultados como clasificación o
diagnóstico.

El sistema es local: FastAPI, PostgreSQL y React/Vite sobre macOS, con artefactos
en `var/storage`. No existe una transacción distribuida entre PostgreSQL y el
filesystem ni se incorporarán workers, colas automáticas o storage remoto.

## Decisión

1. Se adopta `connected_components_v1` versión `1.0.0` como detector basal,
   determinístico, configurable y exclusivamente académico. El detector localiza
   candidatos; no clasifica células ni estima probabilidad de malaria.
2. La fuente de elegibilidad es
   `microscopy_analysis_runs.ready_for_analysis=true`, junto con la comprobación
   del resultado permitido del quality gate, disponibilidad, checksum y
   dimensiones de todas las imágenes congeladas. La cola de calidad de Prompt 6
   no es fuente de verdad y no se modifica.
3. Cada ejecución conserva detector, versión, versión del algoritmo, snapshot
   del perfil e `input_manifest_sha256`. La equivalencia se impide mientras haya
   un run creado, activo o completado; repetir el POST resuelve ese mismo run
   sin procesarlo otra vez. Un run fallido permite un reintento manual nuevo.
4. Componentes, detecciones y crops son resultados automáticos inmutables. Las
   cajas se guardan como metadata en `original_image_pixels`, origen `top-left`
   y formato `xywh`; nunca se dibujan sobre el original.
5. Los crops PNG se derivan de los píxeles originales, se validan en staging y
   se promueven mediante `os.replace` dentro del mismo filesystem. PostgreSQL
   conserva solamente claves POSIX relativas, checksum, tamaño y dimensiones.
   La compensación y la reconciliación cubren la frontera no transaccional entre
   base de datos y storage.
6. `scientific_reviews` es append-only y separado del resultado automático. La
   última decisión efectiva determina la presentación, pero nunca modifica
   `automated_status`, el bbox o el crop.
7. La ejecución es manual y síncrona, con trabajo CPU fuera del event loop. Un
   fallo deja el run en `failed`, registra un error sanitizado y no dispara
   reintentos automáticos.
8. La revisión se presenta en `/frotis/revision`: lista de ejecuciones y un
   workspace de tres paneles en escritorio, adaptado a pestañas/segmentos en
   móvil. Galería y overlay SVG comparten `selectedDetectionId`; imagen y cajas
   comparten el mismo espacio y transformación de zoom/pan.
9. RBAC separa `scientific.cell_detection.read`, `.execute` y `.review`. El
   actor procede del JWT y los cambios de estado y revisiones producen eventos
   de auditoría sin tokens, PII, píxeles ni rutas físicas.

## Consecuencias

### Positivas

- Los resultados se pueden reproducir a partir de un manifiesto y perfil
  inmutables.
- El límite detector/clasificador evita atribuir semántica clínica a geometría.
- Los originales permanecen inmutables y los artefactos se pueden reconciliar.
- Una nueva revisión no destruye la historia anterior.
- La UI puede manejar cientos de candidatos sin cargar todos los crops.

### Costes y riesgos

- Los movimientos de varios crops son atómicos por archivo, no como lote. Un
  cierre abrupto puede dejar huérfanos temporales; el reconciliador los reporta
  y las rutas determinísticas permiten compensación.
- Un baseline por threshold y componentes conectados puede unir células en
  contacto, perder contraste bajo o aceptar artefactos. La separación es
  configurable y estas limitaciones deben permanecer visibles.
- Cambiar orientación, threshold, morfología, conectividad, orden de componentes
  o fórmulas geométricas exige una nueva versión; no se puede reinterpretar un
  run histórico.
- Mantener alineado el overlay requiere que visor y detector usen el mismo
  raster orientado, dimensiones y transformación.

## Alternativas rechazadas

- RBCNet, U-Net, Faster R-CNN, YOLO o modelos descargados: fuera del alcance y
  sin validación local.
- Pipeline monolítico con clasificación: viola ADR-004 y adelanta Prompt 8.
- Bboxes u overlays rasterizados sobre el original: rompe su inmutabilidad.
- Binarios en PostgreSQL o paths absolutos: rompen el contrato de storage.
- Edición de bbox, revisión masiva o sobrescritura de la decisión previa:
  destruyen trazabilidad.
- Celery, Redis, Docker, S3, MinIO o retry automático: no pertenecen a la
  arquitectura oficial de esta etapa.

## Criterio de revisión futura

Un detector posterior puede sustituir el baseline sólo mediante otra
`detector_key`/versión y conservando los contratos de elegibilidad, coordenadas,
provenance, storage, API y revisión. La validación clínica, si alguna vez se
realiza, requiere una decisión y evidencia independientes; no puede inferirse de
este ADR.
