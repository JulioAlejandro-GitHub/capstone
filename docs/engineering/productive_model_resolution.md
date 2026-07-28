# Resolución segura del modelo productivo

## Fuente de verdad

El resolver exige exactamente un `deployed_model_versions` activo para
`environment=stage2` y `alias=default`, unido por `model_version_id` a una
`stage2_model_publication` activa con scope `stage2`.

Después valida:

1. TRAIN y EVALUATE `completed`;
2. versión no retirada y lineage resuelto;
3. checkpoint registrado/disponible, regular, sin symlinks y confinado;
4. tamaño y SHA-256 coincidentes;
5. framework Keras/TensorFlow e input/output signatures completas;
6. preprocessing explícito;
7. mapping exacto `0=uninfected`, `1=parasitized`;
8. positive label `parasitized`, índice 1 y score semántico;
9. threshold entre 0 y 1, snapshot y fuente publicados.

El snapshot persistido omite paths físicos e incluye deployment/publication,
model version, TRAIN/EVALUATE, artifact/checksum, framework/arquitectura,
signatures, preprocessing, mapping, threshold, fechas y versiones del loader e
inferencia.

## Bloqueos

Slot ausente o duplicado produce `PRODUCTIVE_MODEL_NOT_UNIQUE`; un contrato
inconsistente produce su código tipado específico. No se consulta “latest”, no
se selecciona una publicación de catálogo sola y no se usa `0.5`. El mensaje
para UI es:

> No existe un modelo productivo válido para Etapa 2. Publique un modelo desde
> Modelo IA antes de continuar.

La clasificación sólo lee gobierno de modelos: no publica, desactiva, calibra ni
modifica `stage2/default`.

## Estado observado en Prompt 8

El precheck encontró cero filas en `deployed_model_versions` y una publicación
Stage 2 activa de catálogo. En consecuencia no existe un slot inferible real:
la publicación y su checkpoint verificado no autorizan inferencia. El resultado
correcto es `PRODUCTIVE_MODEL_NOT_UNIQUE` /
`awaiting_productive_model`, sin crear datos sintéticos ni seleccionar otro
modelo.
