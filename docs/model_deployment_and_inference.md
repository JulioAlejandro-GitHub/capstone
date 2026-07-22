# Despliegue controlado e inferencia trazable

## Ciclo de vida

Un deployment se crea como `pending`, puede pasar a `active`, volver a `inactive` y
terminar en `retired`. La activación valida nuevamente la model version, evaluación,
threshold calibrado, snapshots clínicos, firmas, artifact store, SHA-256 y carga
Keras. `approved` y `validated` son los estados de versión aceptados por la política.
Explicabilidad se registra como disponible/no disponible, pero no bloquea.

Un alias (`candidate`, `challenger`, `champion`, `experimental`) identifica un único
deployment activo dentro de `(deployment_name, environment, alias)`. Activar una
nueva revisión desactiva atómicamente la anterior. Rollback consiste en reactivar
una revisión inactiva después de repetir todas las validaciones; nunca se cambia la
identidad ni el archivo de una revisión existente.

```bash
python scripts/deploy_model_version.py \
  --model-version-id <uuid> --deployment-name malaria-classifier \
  --environment experimental --alias champion \
  --threshold-profile-id <uuid> --deployed-by usuario --dry-run

python scripts/deploy_model_version.py \
  --model-version-id <uuid> --deployment-name malaria-classifier \
  --environment experimental --alias champion \
  --threshold-profile-id <uuid> --deployed-by usuario --activate
```

## Inferencia

`POST /api/image-analysis-jobs` acepta una identidad concreta:

```json
{"deployed_model_version_id":"<uuid>","source_image_id":"<uuid>"}
```

o un alias controlado:

```json
{"deployment_name":"malaria-classifier","environment":"experimental","alias":"champion","source_image_id":"<uuid>"}
```

El backend resuelve y congela deployment/model version, verifica hash, crea el
inference run y el image job, ejecuta clasificación y guarda una predicción con
`prediction_scope=image`. No crea celdas, bounding boxes ni detecciones ficticias.
La decisión es `probability_parasitized >= threshold_used`; índice 1 corresponde a
`parasitized` y 0 a `uninfected`.

La caché usa `(model_version_id, sha256)`, tiene límite LRU e invalida entradas al
cambiar el alias activo. Un nombre de modelo nunca es clave suficiente.

## Endpoints

- `GET /api/model-versions`, `/{id}` y `/{id}/lineage`
- `GET /api/deployments`, `/active` y `/{id}`
- `POST /api/deployments` y `/{id}/activate|deactivate|retire`
- `POST /api/image-analysis-jobs`
- `GET /api/image-analysis-jobs/{id}` y `/{id}/predictions`
- `GET /api/inference-runs/{id}`

Ejemplo de reconstrucción: consultar el inference run, tomar sus IDs de deployment y
model version, consultar el job y sus predicciones, y finalmente consultar
`/api/model-versions/{id}/lineage` para alcanzar training/evaluation runs.

## Seguridad y errores

Los cuerpos rechazan campos extra, incluyendo `checkpoint`, `model_path` y pickle.
Los modelos sólo se cargan desde `outputs/` o `releases/` registrados, nunca desde
una ruta cliente. Los endpoints públicos omiten paths internos y los errores sólo
exponen el tipo, no rutas ni detalles del sistema. UUID, probabilidades, mappings y
ownership se validan. Fallos posteriores a crear el run/job marcan ambos como
`failed` dentro de la transacción.

No existe actualmente un endpoint productivo legacy de inferencia por checkpoint.
Si se incorpora compatibilidad por `model_name`, deberá resolver un alias configurado,
emitir deprecación y se retirará en API `v1.0`; jamás aceptará una ruta física.

Errores esperables incluyen versión no evaluada, threshold ajeno, checksum distinto,
deployment inactivo, alias ambiguo, imagen inexistente, firma incompatible o fallo de
carga. Ningún error activa otro modelo automáticamente. No se incluye YOLO ni Etapa 2.
