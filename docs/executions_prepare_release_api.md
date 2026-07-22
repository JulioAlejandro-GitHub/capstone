# Especificación Técnica: API de Preparación de Release y Estado de Promoción de Modelos

**Fecha:** 2026-07-22  
**Módulo:** Model Governance MLOps & Promotion Pipeline  
**Proyecto:** Capstone MIA — Universidad Adolfo Ibáñez  

---

## 1. Visión General

Esta API expone los servicios necesarios para iniciar la promoción de un modelo desde una ejecución de entrenamiento (`training_run_id`), conectándolo con el pipeline inmutable de `model_versions` y `deployed_model_versions`.

### Principio Obligatorio de Trazabilidad
El **`training_run_id`** actúa como el punto de entrada para localizar la corrida física y preparar el release, pero **nunca es la identidad del modelo productivo**. La identidad inmutable en producción es **`model_version_id`** (y su instancia **`deployed_model_version_id`**).

---

## 2. Endpoints

### 2.1 GET `/api/training-runs/{training_run_id}/promotion-status`

Consulta **libre de efectos secundarios** (*side-effect free*) utilizada por la pantalla de Ejecuciones para determinar la disponibilidad del botón de promoción y la siguiente acción recomendada.

- **Método:** `GET`
- **Parámetros de Ruta:** `training_run_id` (UUID)
- **Codigos de Respuesta:** `200 OK`, `422 Unprocessable Entity`

#### Ejemplo de Respuesta (Modelo Listo para Preparar Release):
```json
{
  "training_run_id": "ec93bad5-d029-43c1-ab0c-0ab988ecbb49",
  "model_version_id": null,
  "deployment_id": null,
  "deployment_status": null,
  "environment": null,
  "alias": null,
  "next_action": "prepare_release",
  "button_label": "Preparar despliegue",
  "button_enabled": true,
  "blocking_reasons": [],
  "target_url": null,
  "can_release": true,
  "can_deploy": false
}
```

#### Ejemplo de Respuesta (Modelo Bloqueado por Entrenamiento Incompleto):
```json
{
  "training_run_id": "00000000-0000-0000-0000-000000000001",
  "model_version_id": null,
  "deployment_id": null,
  "deployment_status": null,
  "environment": null,
  "alias": null,
  "next_action": "unavailable",
  "button_label": "No disponible",
  "button_enabled": false,
  "blocking_reasons": [
    "TRAINING_NOT_COMPLETED: El entrenamiento no está en estado 'completed' (actual: 'running')."
  ],
  "target_url": null,
  "can_release": false,
  "can_deploy": false
}
```

---

### 2.2 POST `/api/training-runs/{training_run_id}/prepare-release`

Endpoint **idempotente** que recibe una solicitud de promoción, verifica el linaje e inmutabilidad del checkpoint, y obtiene o registra la correspondiente **`model_version`** en la base de datos de gobernanza.

- **Método:** `POST`
- **Parámetros de Ruta:** `training_run_id` (UUID)
- **Cuerpo de la Petición (Opcional):**
  ```json
  {
    "requester": "julio.mora",
    "target_environment": "production"
  }
  ```
- **Códigos de Respuesta:** `200 OK`, `409 Conflict` (rechazo por reglas de gobernanza), `422 Unprocessable Entity`.

#### Ejemplo de Respuesta Exitosa (`200 OK`):
```json
{
  "training_run_id": "ec93bad5-d029-43c1-ab0c-0ab988ecbb49",
  "training_status": "completed",
  "model_name": "vgg16_custom",
  "model_version_id": "67b48742-8b57-4672-827b-6a21d56af073",
  "model_version_status": "candidate",
  "lineage_status": "lineage_resolved",
  "evaluation_run_id": "8dca1f53-bcb6-443e-8130-f654e6e518ae",
  "explainability_run_ids": [
    "f155781b-c9bb-4a35-a3e4-fa495b691bdd"
  ],
  "checkpoint_sha256": "70230aee19f14a4c570fc62dfcf79e1790e6c7674c49ab310d1abdfc056a86ab",
  "threshold": {
    "value": 0.42,
    "source": "clinical",
    "evaluated_on_test": true
  },
  "can_release": true,
  "can_deploy": false,
  "next_action": "review_model_version",
  "blocking_reasons": [],
  "target_url": "/modelo-ia/modelos-liberados/67b48742-8b57-4672-827b-6a21d56af073"
}
```

---

## 3. Estados de `next_action`

| Estado | Significado MLOps | Etiqueta Botón UI | `button_enabled` | `target_url` |
| :--- | :--- | :--- | :---: | :--- |
| `prepare_release` | Run completado con checkpoint válido, sin `model_version` registrada aún. | **Preparar despliegue** | `true` | `null` |
| `review_model_version` | `model_version` registrada (`candidate`/`draft`), requiere revisión/evaluación. | **Ver modelo liberado** | `true` | `/modelo-ia/modelos-liberados/{mv_id}` |
| `approve_model_version` | `model_version` validada, pendiente de aprobación humana. | **Aprobar modelo** | `true` | `/modelo-ia/modelos-liberados/{mv_id}` |
| `create_deployment` | `model_version` aprobada, sin despliegue activo ni pendiente. | **Continuar despliegue** | `true` | `/modelo-ia/modelos-liberados/{mv_id}?action=deploy` |
| `review_pending_deployment` | Despliegue creado en estado `pending` o `inactive`. | **Ver despliegue pendiente** | `true` | `/modelo-ia/despliegues/{dep_id}` |
| `view_active_deployment` | Despliegue en estado `active` en entorno productivo/staging. | **Ver despliegue** | `true` | `/modelo-ia/despliegues/{dep_id}` |
| `unavailable` | Entrenamiento fallido/incompleto, linaje ambiguo o hash no coincidente. | **No disponible** | `false` | `null` |

---

## 4. Códigos y Reglas de Error

- `TRAINING_RUN_NOT_FOUND`: El `training_run_id` no existe en PostgreSQL.
- `INVALID_RUN_TYPE`: El run consultado no es de tipo `training`.
- `TRAINING_NOT_COMPLETED`: El estado del entrenamiento no es `completed`.
- `CHECKPOINT_NOT_FOUND`: No existe archivo ni registro de checkpoint asociado al entrenamiento.
- `UNRESOLVED_LINEAGE`: La ruta del checkpoint es una referencia genérica sin linaje único verificado.
- `CHECKPOINT_HASH_MISMATCH`: El hash SHA-256 del archivo físico en disco no coincide con el registrado.
- `CLASS_MAPPING_INVALID`: La convención clínica no cumple con `0=uninfected`, `1=parasitized` y `positive_label=parasitized`.
- `EVALUATION_REQUIRED`: Se requiere evaluación formal sobre el test set para permitir despliegue.
- `CLINICAL_THRESHOLD_REQUIRED`: El umbral clínico debe estar validado en el conjunto de test.

---

## 5. Garantías de Idempotencia y Auditoría

1. **Idempotencia:** Múltiples invocaciones de `POST /prepare-release` para una misma corrida retornan la misma `model_version_id` previa sin duplicar artefactos en disco ni filas en la base de datos.
2. **Auditoría:** Cada intento de preparación genera un evento en la tabla `execution_logs` registrando usuario, timestamp, `training_run_id`, `model_version_id`, resultado y bloqueadores.
