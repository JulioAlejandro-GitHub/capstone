# API para preparar una liberación desde Ejecuciones

## Propósito

Esta capa conecta un `training_run_id` con la gobernanza existente. El Run ID es el
punto de entrada, nunca la identidad productiva:

```text
training_run_id → model_version_id → deployed_model_version_id
```

La implementación reutiliza:

- `model_governance.repository.create_model_version`;
- `model_governance.releases.sha256_file`;
- `ModelDeploymentService.validate_activation`;
- `runs`, `artifacts`, `run_lineage`, `run_checkpoint_policy`,
  `run_threshold_calibration`, `run_clinical_metrics`, `model_versions` y
  `deployed_model_versions`.

No crea deployments, no activa aliases y no despliega
`outputs/<model>/best_model.keras`.

## Endpoints

### Consultar estado

```http
GET /api/training-runs/{training_run_id}/promotion-status?datasource=malaria
```

Es read-only: no crea versiones, manifests, artifacts, deployments ni registros de
auditoría. Calcula el estado actual para el botón TRAIN.

### Preparar liberación

```http
POST /api/training-runs/{training_run_id}/prepare-release?datasource=malaria
Content-Type: application/json
X-Requester: usuario
X-Request-ID: correlation-id

{
  "target_environment": "experimental"
}
```

`target_environment` es sólo información preliminar de auditoría. No crea ni activa
un deployment. En ausencia de autenticación integrada, `X-Requester` es opcional y
no debe considerarse una identidad confiable para producción.

## Contrato de respuesta

Ambos endpoints entregan el mismo estado enriquecido:

```json
{
  "training_run_id": "11111111-1111-4111-8111-111111111111",
  "training_status": "completed",
  "model_name": "custom_cnn",
  "model_version_id": "22222222-2222-4222-8222-222222222222",
  "model_version_status": "candidate",
  "lineage_status": "resolved",
  "evaluation_run_id": "33333333-3333-4333-8333-333333333333",
  "explainability_run_ids": [
    "44444444-4444-4444-8444-444444444444"
  ],
  "checkpoint_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "threshold": {
    "value": 0.42,
    "source": "clinical",
    "evaluated_on_test": true
  },
  "can_release": true,
  "can_deploy": false,
  "deployment_id": null,
  "deployment_status": null,
  "environment": null,
  "alias": null,
  "next_action": "review_model_version",
  "button_label": "Ver modelo liberado",
  "button_enabled": true,
  "blocking_reasons": [],
  "target_url": "/modelo-ia/modelos-liberados/22222222-2222-4222-8222-222222222222"
}
```

Nunca se expone `checkpoint_path`, `artifact_uri` ni otra ruta física.

## Estados

| `next_action` | Botón | Significado |
|---|---|---|
| `prepare_release` | Preparar despliegue | Requisitos base completos, aún sin versión |
| `review_model_version` | Ver modelo liberado | Versión candidate/discovered |
| `approve_model_version` | Ver modelo liberado | Versión validated pendiente de aprobación |
| `create_deployment` | Continuar despliegue | Versión apta; el usuario puede solicitar un deployment en otra operación |
| `review_pending_deployment` | Ver despliegue pendiente | Ya existe una revisión pending/failed |
| `view_active_deployment` | Ver despliegue | Ya existe una revisión active |
| `unavailable` | No disponible | Existen bloqueadores |

`can_release` expresa integridad suficiente para obtener o crear la model version.
`can_deploy` exige además estado de versión, evaluación, threshold clínico en test,
ausencia de colapso y aceptación de `ModelDeploymentService`.

## Validaciones

Preparar exige:

- UUID y training run existentes;
- `run_type=training`;
- `status=completed`;
- `model_name`;
- exactamente un checkpoint inmutable registrado;
- ownership del artifact por el training run;
- ruta bajo `runs/<training_run_id>/` o `artifact_uri` gobernado;
- archivo disponible y SHA-256 coincidente;
- exactamente cero o una model version coherente;
- `lineage_status=resolved` para una versión existente;
- preprocessing registrado;
- mapping clínico canónico;
- modelo cargable en el POST.

La evaluación y explicabilidad se resuelven únicamente desde `run_lineage` con el
mismo `model_version_id` y `checkpoint_artifact_id` cuando esos IDs existen. Una
evaluación desplegable debe estar completed y contener evidencia de test/external.
El threshold debe estar ligado a la versión/run correspondiente, conservar
`positive_label=parasitized` y `score_name=probability_parasitized`, y haber sido
usado en la evaluación formal.

La convención clínica es:

```text
0 = uninfected
1 = parasitized
positive_class = 1
positive_label = parasitized
```

## Bloqueadores y errores

`blocking_reasons` contiene objetos estables:

```json
{
  "code": "CHECKPOINT_HASH_MISMATCH",
  "message": "El SHA-256 no coincide con el artifact registrado."
}
```

Códigos implementados:

- `TRAINING_RUN_NOT_FOUND`;
- `INVALID_RUN_TYPE`;
- `TRAINING_NOT_COMPLETED`;
- `MODEL_NAME_REQUIRED`;
- `CHECKPOINT_NOT_FOUND`;
- `UNRESOLVED_LINEAGE`;
- `CHECKPOINT_HASH_MISMATCH`;
- `MODEL_NOT_LOADABLE`;
- `MODEL_VERSION_CONFLICT`;
- `PREPROCESSING_REQUIRED`;
- `CLASS_MAPPING_INVALID`;
- `EVALUATION_REQUIRED`;
- `CLINICAL_THRESHOLD_REQUIRED`;
- `DEPLOYMENT_NOT_ALLOWED`.

Un UUID inválido produce HTTP 422. Un fallo inesperado de la fachada produce HTTP
409 con `PROMOTION_STATUS_FAILED` o `PREPARE_RELEASE_FAILED`, sin exponer paths ni
excepciones internas. Los bloqueos de negocio esperados se devuelven en el contrato
normal para que Ejecuciones pueda representar “No disponible” y su causa.

## Idempotencia y concurrencia

Antes de crear, el servicio:

1. busca model versions del training run;
2. valida cardinalidad y coherencia;
3. toma un advisory lock transaccional por `training_run_id`;
4. vuelve a buscar por training run o `checkpoint_artifact_id`;
5. reutiliza la única versión encontrada;
6. sólo si no existe, llama al repositorio gobernado.

Por ello los reintentos no duplican model versions ni artifacts y no degradan una
versión existente. Esta capa no genera un manifest adicional: el checkpoint
inmutable ya registrado es el artifact de la model version. La copia/manifest de
`create_release` sigue disponible para el proceso operativo existente, pero no se
duplica desde este endpoint.

## Auditoría

Sólo el POST escribe una entrada en `execution_logs`, con:

- requester;
- timestamp de la tabla;
- training run y model version;
- acción y resultado;
- bloqueadores;
- request/correlation ID;
- target environment preliminar.

El GET no registra auditoría para mantener su garantía de ausencia de efectos
secundarios. Un run inexistente no puede registrarse en `execution_logs` porque la
tabla exige FK a `runs`; el resultado se comunica al cliente.

## Seguridad

El repositorio todavía no posee autenticación/autorización. Antes de habilitar esta
operación en un ambiente productivo se debe:

- autenticar en FastAPI;
- obtener requester desde el principal, no desde un header del cliente;
- autorizar una capacidad `model_releaser`;
- limitar datasource y target environment;
- propagar/generar un correlation ID confiable;
- aplicar rate limit y límites de concurrencia;
- proteger también los POST de deployments ya existentes.

El endpoint rechaza campos extra y no acepta checkpoint, model path, alias ni
deployment ID en el body.

## Ejemplo bloqueado

```json
{
  "training_run_id": "11111111-1111-4111-8111-111111111111",
  "training_status": "completed",
  "model_name": "custom_cnn",
  "model_version_id": null,
  "model_version_status": null,
  "lineage_status": "unresolved",
  "evaluation_run_id": null,
  "explainability_run_ids": [],
  "checkpoint_sha256": null,
  "threshold": null,
  "can_release": false,
  "can_deploy": false,
  "deployment_id": null,
  "deployment_status": null,
  "environment": null,
  "alias": null,
  "next_action": "unavailable",
  "button_label": "No disponible",
  "button_enabled": false,
  "blocking_reasons": [
    {
      "code": "CHECKPOINT_NOT_FOUND",
      "message": "No existe un checkpoint inmutable inequívoco."
    }
  ],
  "target_url": null
}
```

