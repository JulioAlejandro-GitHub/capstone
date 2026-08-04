# Workflow de Etapa 2

Etapa 2 conecta un experimento reproducible con el análisis técnico de frotis
mediante una publicación explícita. “Publicado” significa disponible para el
runtime experimental; no significa aprobado clínicamente.

## Regla única de elegibilidad

Una versión puede publicarse sólo cuando:

```text
TRAIN.status = completed
AND EVALUATE asociado.status = completed
```

El EVALUATE se asocia por el linaje `evaluates_checkpoint_from`. Si hay más de
uno, se prefiere uno completado y luego el más reciente. EXPLAIN, firmas,
TensorFlow, métricas, threshold, estabilidad y GPU no participan en esta
elegibilidad. Esta regla está implementada por el servicio de publicación y se
describe en [stage2_productive_training_card.md](stage2_productive_training_card.md).

## Publicación y baja

La publicación referencia `model_version_id`, `training_run_id`,
`evaluation_run_id` y `checkpoint_artifact_id`; no copia ni reentrena el modelo.
Publicar una versión activa y dar de baja una inactiva son operaciones
idempotentes. La reactivación conserva el registro y agrega un evento. El
historial es append-only.

Los endpoints de este flujo son:

| Método | Endpoint | Uso |
|---|---|---|
| GET | `/api/training-runs/{id}/stage2-release-status` | Estado en el TRAIN |
| GET | `/api/model-versions/{id}/stage2-status` | Elegibilidad y publicación |
| POST | `/api/model-versions/{id}/stage2-publications` | Publicar o reactivar |
| POST | `/api/stage2-publications/{id}/deactivate` | Dar de baja |
| GET | `/api/stage2/models?datasource=malaria` | Candidatos activos |

## Resolución para inferencia

La inferencia implícita requiere exactamente una publicación Stage 2 activa.
Antes de cargar el artefacto valida disponibilidad e integridad del checkpoint,
checksum, framework/formato, mapping de clases, preprocessing, input shape y
threshold calibrado. Estas validaciones pertenecen al boundary de inferencia y
no deben añadirse a la regla de elegibilidad.

Si no hay una publicación única o cualquier validación falla, el workflow queda
bloqueado con un error explícito y fail-closed. No existe fallback al último
modelo publicado, a un deployment legacy ni a threshold `0.5`.
Consulte
[`engineering/productive_model_resolution.md`](engineering/productive_model_resolution.md)
y [model_release_process.md](model_release_process.md).

## Interfaz

La publicación se administra dentro del detalle de la ejecución TRAIN en
`/modelo-ia/ejecuciones/:trainingRunId`. El consumo ocurre en
`/frotis/analizar`. La interfaz presenta por separado identidad del modelo,
threshold, resultado automático, revisión humana y advertencia experimental.

Los runs nuevos congelan identidad publication-first esquema v2; los snapshots
deployment-backed v1 permanecen legibles. La decisión está en
[`adr/ADR-021-stage2-publication-first-inference.md`](adr/ADR-021-stage2-publication-first-inference.md)
y requiere Alembic `20260804_01`; vea [database.md](database.md).
