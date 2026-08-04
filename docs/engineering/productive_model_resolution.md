# Resolución segura del modelo productivo

## Fuente de verdad actual

La inferencia nueva parte de `stage2_model_publications`: debe existir
exactamente una fila con `scope=stage2`, `status=active` e `is_active=true`.
Esa publicación identifica versión, TRAIN, EVALUATE y checkpoint. No requiere
un deployment `stage2/default`; los deployments sólo se consultan al reconstruir
snapshots históricos esquema v1.

La publicación y la ejecución son boundaries distintos. La elegibilidad para
publicar considera únicamente TRAIN y EVALUATE completados. Al iniciar una
inferencia, el resolver valida de forma fail-closed:

1. checkpoint registrado, disponible, regular, sin symlinks y confinado a
   roots locales autorizados;
2. tamaño y SHA-256 coincidentes entre artefacto, versión y bytes cargados;
3. framework Keras/TensorFlow y firmas de entrada/salida completas;
4. preprocessing explícito y soportado;
5. mapping exacto `0=uninfected`, `1=parasitized`, positive label e índice;
6. threshold finito entre 0 y 1, fuente y calibración coherentes;
7. input width/height/channels y versiones de loader/inferencia.

No se usa “latest”, no se elige silenciosamente entre varias publicaciones y
no existe fallback a threshold `0.5`.

## Snapshots

Los runs nuevos congelan snapshot esquema v2 con publicación, model version,
TRAIN/EVALUATE, artefacto/checksum, framework, signatures, preprocessing,
mapping, threshold/calibración y políticas de inferencia/explicabilidad. Los
paths físicos se omiten.

Los snapshots esquema v1 conservan `production_model_id` y
`stage2_default`. Siguen resolviéndose por su identidad congelada incluso si la
publicación ya no está activa. No se actualizan ni convierten a v2.

## Disponibilidad y bloqueos

`GET /api/stage2/productive-model-availability` informa el catálogo sin abrir
el checkpoint. Cero publicaciones activas produce
`PRODUCTIVE_MODEL_NOT_FOUND`; más de una produce
`PRODUCTIVE_MODEL_NOT_UNIQUE`. Con una sola, la respuesta indica que la
validación técnica está pendiente hasta inferencia.

Un contrato inconsistente genera un código técnico específico y el workflow
permanece bloqueado; la clasificación no publica, desactiva ni calibra modelos.
La migración `20260804_01` protege la coexistencia de identidad v1 y v2. La
decisión se registra en
[`../adr/ADR-021-stage2-publication-first-inference.md`](../adr/ADR-021-stage2-publication-first-inference.md).
