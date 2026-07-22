# Linaje de evaluación y explicabilidad

La entrada preferida es una `model_version` inmutable. `ModelVersionResolver` obtiene
su artefacto y snapshots, comprueba que pertenezca a un training run, que su estado y
linaje permitan uso, y recalcula SHA-256 antes de cargar Keras. La convención clínica
es siempre `0=uninfected`, `1=parasitized`, clase positiva `parasitized`.

## Evaluación

```bash
python -m src.evaluate --model-version-id <uuid> --require-lineage \
  --threshold 0.5 --track-db

python -m src.evaluate --model-version-id <uuid> --require-lineage \
  --threshold clinical --track-db
```

Cada invocación crea un evaluation run separado. Por ello las métricas de threshold
0.5, calibrado clínico o explícito nunca se mezclan. El tracking conserva version,
training run, artifact, path informativo, SHA-256, dataset/split, preprocessing,
mapping, threshold y sus fuentes, métricas, matriz de confusión, predicciones,
ambiente y versión de código.

## Explicabilidad

```bash
python -m src.explain --model-version-id <uuid> \
  --evaluation-run-id <evaluation-uuid> --method gradcam \
  --require-lineage --track-db
```

Cuando se entrega una evaluación, el resolver verifica que su `run_lineage` apunte a
la misma model version. La ejecución registra método, configuración, imágenes de
entrada y artefactos generados mediante el tracking existente, junto con la identidad
gobernada del modelo.

## Compatibilidad legacy

`--checkpoint` y `--model-path` continúan disponibles y emiten `FutureWarning`. No se
aceptan con `--require-lineage`; antes de persistir resultados deben resolverse o
crearse como model version. `--source-training-run-id` se mantiene como ayuda de
migración, pero no sustituye `--model-version-id` en modo estricto.

El entrenamiento debe culminar registrando artefacto y model version antes de estos
comandos. Ninguno de estos flujos crea deployments o cambia thresholds clínicos.
