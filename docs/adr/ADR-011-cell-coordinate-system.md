# ADR-011: Sistema de coordenadas celular

- Estado: Aceptado
- Contexto/problema: no hay contrato bbox y tiles requieren globalización.
- Decisión: `pixel_xywh_top_left_v1`, píxeles de original, x derecha/y abajo, dimensiones positivas y dentro de límites; conservar original/adjusted/crop bbox, tile/offset/padding y algoritmo NMS/IoU versionado.
- Alternativas: xyxy, centro o normalizado como canon; rechazadas por ambigüedad.
- Positivas: viewer/crops reproducibles.
- Negativas: conversiones de adapters.
- Riesgos/mitigación: off-by-one; golden/property tests.
- Compatibilidad: columnas legacy se adaptan con formato declarado.
- Revisión futura: no cambiar; nueva versión explícita si fuese necesario.
- Componentes/prompts: detector/crop/viewer; P8/P9/P14.
