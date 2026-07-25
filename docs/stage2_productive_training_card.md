# Publicación de candidatos para Etapa 2 desde Ejecuciones

## Regla única

Una versión puede publicarse cuando:

```text
TRAIN.status = completed
AND EVALUATE asociado.status = completed
```

El EVALUATE se resuelve por `run_lineage.relationship_type =
evaluates_checkpoint_from`. Si existe más de uno, se prefiere uno completado y
el más reciente. EXPLAIN, firmas, TensorFlow, métricas, threshold, estabilidad
y disponibilidad de GPU no participan en la elegibilidad.

La publicación es técnica y experimental; no constituye aprobación clínica ni
diagnóstico automatizado.

## Persistencia e inmutabilidad

La migración `029_stage2_model_publications.sql` agrega:

- `stage2_model_publications`: disponibilidad actual reversible;
- `stage2_model_publication_events`: bitácora append-only de publicación, baja
  y reactivación.

La publicación referencia `model_version_id`, `training_run_id`,
`evaluation_run_id` y `checkpoint_artifact_id` existentes. No copia, modifica
ni reemplaza el modelo. La FK compuesta a `model_versions` congela el par
versión/artefacto y `ON DELETE RESTRICT` protege el linaje.

Pueden existir varias versiones activas. La unicidad sólo impide dos
publicaciones activas contradictorias para la misma `model_version`.

## Ciclo e idempotencia

```text
available → production → available
```

Publicar una versión activa o dar de baja una versión ya inactiva devuelve el
estado existente. Un advisory lock por versión y el índice parcial único
protegen solicitudes concurrentes.

La baja no elimina registros ni cambia TRAIN, EVALUATE, model version,
artefactos o trabajos previos. La reactivación conserva el mismo registro y
agrega un nuevo evento, por lo que todos los intervalos pueden reconstruirse.

Eventos:

- `MODEL_STAGE2_PUBLISHED`
- `MODEL_STAGE2_DEACTIVATED`
- `MODEL_STAGE2_REACTIVATED`

## API

| Método | Endpoint | Uso |
|---|---|---|
| GET | `/api/training-runs/{id}/stage2-release-status` | Estado para la tarjeta TRAIN |
| GET | `/api/model-versions/{id}/stage2-status` | Elegibilidad y publicación |
| POST | `/api/model-versions/{id}/stage2-publications` | Publicar o reactivar |
| POST | `/api/stage2-publications/{id}/deactivate` | Dar de baja |
| GET | `/api/stage2/models?datasource=malaria` | Candidatos activos para trabajos nuevos |

Los endpoints anteriores de deployment y la vista de liberación independiente
se conservan para compatibilidad, pero no son la fuente de verdad de este flujo.

## Interfaz

“Ver detalle” es un botón con `aria-expanded` y `aria-controls`. Abre un panel
dentro de la tarjeta TRAIN y conserva visible el linaje TRAIN → EVALUATE /
EXPLAIN. El panel muestra regla, identidades, checkpoint, estado, publicación,
actor y advertencia experimental.

Las confirmaciones de publicación y baja son inline, sin modal. Tras cada
acción sólo se actualiza la tarjeta afectada. Una publicación activa aplica
estilo success tenue, badge textual e icono, sin depender únicamente del color.

## Prueba manual

1. Aplicar migraciones y arrancar backend/frontend.
2. Abrir `/modelo-ia/ejecuciones?datasource=malaria`.
3. En un TRAIN con EVALUATE completed, pulsar “Ver detalle”.
4. Confirmar “Disponibilizar para Etapa 2”.
5. Verificar badge y borde success.
6. Consultar `/api/stage2/models?datasource=malaria`.
7. Confirmar la baja y verificar que desaparece del selector.
8. Publicar nuevamente y consultar los eventos de auditoría.
