# Resolución segura del modelo productivo

## Fuente de verdad

El resolver parte de exactamente una `stage2_model_publications` con
`scope=stage2`, `status=active` e `is_active=true`. Luego exige su
`deployed_model_versions` para `environment=stage2` y `alias=default`. Las dos
tablas se unen por la identidad compuesta real
`(model_version_id, checkpoint_artifact_id)`; ambas columnas están protegidas
en cada tabla por una FK a
`model_versions(id, checkpoint_artifact_id)`. No existe una FK directa entre
publicación y deployment, ni una columna
`deployed_model_versions.is_active`.

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

## Consulta de verificación

```sql
SELECT
  publication.id AS publication_id,
  publication.is_active,
  deployment.environment,
  deployment.alias,
  deployment.id AS deployed_model_version_id,
  model_version.id AS model_id,
  model_version.model_name,
  publication.training_run_id AS train_id,
  training.status AS train_status,
  publication.evaluation_run_id AS evaluate_id,
  evaluation.status AS evaluate_status,
  publication.checkpoint_artifact_id AS checkpoint_id,
  deployment.threshold_value AS threshold,
  calibration.threshold_source,
  publication.published_at
FROM stage2_model_publications publication
JOIN deployed_model_versions deployment
  ON deployment.model_version_id = publication.model_version_id
 AND deployment.checkpoint_artifact_id = publication.checkpoint_artifact_id
JOIN model_versions model_version
  ON model_version.id = publication.model_version_id
JOIN runs training
  ON training.id = publication.training_run_id
JOIN runs evaluation
  ON evaluation.id = publication.evaluation_run_id
JOIN run_threshold_calibration calibration
  ON calibration.run_threshold_calibration_id =
       deployment.threshold_calibration_id
 AND calibration.model_version_id = deployment.model_version_id
WHERE publication.scope = 'stage2'
  AND publication.status = 'active'
  AND publication.is_active = true
  AND deployment.environment = 'stage2'
  AND deployment.alias = 'default';
```

## Snapshot histórico observado en la corrección de Prompt 8

El precheck encontró cero filas en `deployed_model_versions` y una publicación
Stage 2 activa de catálogo. En consecuencia no existe un slot inferible real:
la publicación y su checkpoint verificado no autorizan inferencia. El resultado
correcto es `PRODUCTIVE_MODEL_NOT_UNIQUE` /
`awaiting_productive_model`, sin crear datos sintéticos ni seleccionar otro
modelo.

Ese resultado pertenece exclusivamente al corte de Prompt 8. No afirma que el
entorno actual conserve cero deployments. La disponibilidad vigente se resuelve
en cada ejecución mediante las validaciones anteriores; nunca se infiere desde
este documento.
