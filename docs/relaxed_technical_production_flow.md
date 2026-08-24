# Producción técnica relajada para Etapa 2

> **Estado documental: LEGACY_REQUIRED / COMPATIBILITY.** Conserva evidencia de un
> flujo técnico anterior y de endpoints aún compatibles; **no autoriza publicar sin un
> EVALUATE completado ni define la fuente de verdad actual**. La regla mínima de
> elegibilidad vigente es `TRAIN completed + EVALUATE completed`; la habilitación
> técnica añade contrato, threshold, smoke e inferencia. Consulte
> [stage2_productive_training_card.md](stage2_productive_training_card.md).

> **Lectura del cuerpo:** los enunciados del flujo relajado son un snapshot histórico,
> no el contrato vigente de los endpoints compatibles. Cuando difieren, prevalecen la
> regla anterior y el servicio actual.

## Fuente de verdad

La disponibilidad se deriva exclusivamente de:

```text
training_run_id
→ model_version_id
→ deployed_model_version_id
   environment=production
   alias=champion
   status=active
   metadata.production_scope=stage2_technical
→ inference_run_id
→ image_analysis_job_id
```

No se usa una bandera aislada del training. La marca de Ejecuciones y Modelos
liberados se calcula desde el deployment activo.

## Producción técnica frente a validación clínica

“Modelo productivo técnico para Etapa 2” significa que el archivo fue
congelado, verificado, cargado y ejecutó una inferencia real. No significa
certificación clínica, autorización sanitaria ni aprobación para diagnóstico.
El flujo clínico estricto permanece disponible y separado.

## Readiness del snapshot relajado

En el snapshot no bloqueaban la ausencia de explainability o evaluación formal, la
falta de aprobación clínica, el estado discovered/candidate, la metadata histórica
parcial ni la ausencia de threshold formal; se persistían como advertencias.

En la implementación compatible vigente, EXPLAIN y la aprobación clínica siguen sin
participar en la elegibilidad, pero un EVALUATE `completed` sí es obligatorio y la
habilitación técnica rechaza una model version sin calibración de threshold registrada
y trazable.

En el snapshot sí bloqueaban: archivo no localizable/copiable, SHA inválido, modelo
corrupto o no cargable, preprocessing no ejecutable, firma incompatible, mapping
invertido, inferencia fallida o error transaccional.

La convención obligatoria es:

```text
0 = uninfected
1 = parasitized
positive_class = 1
positive_label = parasitized
score_name = probability_parasitized
```

## Artefacto y contrato

El orquestador reutiliza `ModelContractService`, hashing, artifacts,
`model_versions`, repositorio de deployments y `TraceableInferenceService`.
Localiza el checkpoint gobernado o legacy, verifica sus bytes y crea sin
sobrescritura:

```text
releases/production/<model>/<model_version_id>/
  model.keras
  manifest.json
  preprocessing.json
  class_mapping.json
  signatures.json
  threshold.json
  checksums.sha256
```

En el snapshot las firmas se inspeccionaban cargando Keras con `compile=false`. El
threshold se elegía desde calibración, evaluación, training o deployment; si no
existía, se registraba `0.5` como `stage2_operational_default`, nunca como calibrado
clínicamente. Ese fallback ya no describe el servicio compatible vigente.

## Publicación y rollback

El modelo se valida antes de tocar el champion. Luego se crea/reutiliza una
revisión pending, se persiste smoke PASS, se desactiva el champion anterior y se
activa el nuevo. Un índice parcial garantiza un único `production/champion`.
Las revisiones anteriores quedan inactive/retired y disponibles para rollback.
Los reintentos reutilizan el deployment activo verificado.

## API

- `GET /api/model-versions/{id}/technical-production-preview`
- `POST /api/model-versions/{id}/publish-technical-production`
- `POST /api/training-runs/{id}/publish-technical-production`
- `GET /api/models/available?environment=production`

El frontend nunca envía `artifact_path`. El POST exige actor, motivo,
confirmación y opcionalmente una imagen/preprocessing controlados.

## Interfaz

En Despliegues → Revisar despliegue aparece “Publicar como modelo productivo”.
El modal identifica modelo, training, model version, SHA, contrato, warnings y
el destino `production/champion`. El encabezado distingue el champion técnico
del champion clínico. Ejecuciones muestra “✓ Modelo productivo para Etapa 2” y
Modelos liberados muestra “Productivo Etapa 2”.

El selector usa `deployed_model_version_id`, no `model_name`.

## Caso real verificado

- modelo: `custom_cnn`;
- training: `371a9e75-2e87-4c22-b1d0-8f249007cc33`;
- model version: `8f5277bd-e2bb-4dff-a4d6-821f9f5a60e7`;
- artifact inmutable:
  `releases/production/custom_cnn/8f5277bd-e2bb-4dff-a4d6-821f9f5a60e7/model.keras`;
- SHA-256:
  `d54bbdcddbd4ca3b10ce675eb28f60b24a9718ffba881f83ca24ef19820415d8`;
- preprocessing: `rescale_0_1`;
- entrada: `[null,200,200,3] float32`;
- salida: `[null,1] float32`;
- threshold: `0.262956857681274`, calibración de validation;
- deployment: `dcb78025-3928-469d-bf2b-3e35c67c5654`;
- inference: `fb5b5e47-715b-4b1a-b7ec-17f1fc41d27f`;
- image job: `16445576-aaf4-4541-a476-9c3b49eca429`;
- rollback: deployment anterior
  `3861e6d7-d6a8-4220-82e4-e4d7a1c86fbd`.

## Reemplazo

1. Revisar el deployment del modelo elegido.
2. Abrir “Publicar como modelo productivo”.
3. Revisar evidencia y advertencias.
4. Confirmar responsable y motivo.
5. Esperar copia, inspección, smoke, activación e inferencia.
6. Verificar el encabezado “Modelo productivo para Etapa 2”.
7. Ante regresión, seleccionar la revisión anterior y crear rollback pendiente.
