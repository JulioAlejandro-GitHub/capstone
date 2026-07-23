# Disponibilidad técnica de modelos para Etapa 2

## Alcance

Este flujo permite usar un modelo real en la aplicación durante la Etapa 2. No
equivale a aprobación clínica ni a publicación formal en producción. Conserva
la identidad aprobada:

```text
training_run_id
→ model_version_id
→ deployed_model_version_id
→ inference_run_id
→ image_analysis_job_id
```

El `training_run_id` sólo es el punto de entrada. La inferencia siempre usa un
`deployed_model_version_id`.

## Arquitectura reutilizada

- `runs`, `artifacts`, `model_versions`, `run_lineage`,
  `run_threshold_calibration`, `deployed_model_versions`, `inference_runs`,
  `image_analysis_jobs` y `predictions`.
- `ModelContractService` para resolver y congelar preprocessing, firmas,
  mapping y threshold.
- repositorio de gobierno para crear la revisión de deployment.
- `TraceableInferenceService` para la inferencia final controlada.
- hashing SHA-256 y store `releases/` ya existentes.

No se agregan tablas, una segunda identidad de modelo ni otro motor de
inferencia.

## Reglas técnicas

El backend sólo habilita si:

1. el run es TRAIN, está `completed` y no es fixture técnica;
2. existe exactamente una `model_version`;
3. el artefacto existe, su SHA-256 coincide y puede cargarse;
4. preprocessing, input/output signatures y class mapping son resolubles;
5. el mapping conserva `0 = uninfected`, `1 = parasitized` y
   `positive_label = parasitized`;
6. existe un threshold de entrenamiento/calibración o se registra el valor
   operativo `0.5`, marcado explícitamente como no clínico;
7. una imagen real completa el smoke test;
8. la revisión queda `environment=stage2`, `alias=default`, `status=active`;
9. una inferencia trazable final crea `inference_run_id` e
   `image_analysis_job_id`.

Una copia de paquete inmutable se escribe en
`releases/stage2/<model>/<model_version_id>/model.keras`, acompañada de
manifest, preprocessing, mapping, firmas, threshold y checksums. No reemplaza
el par gobernado `(model_version_id, checkpoint_artifact_id)`, que permanece
protegido por las claves de linaje; ambos bytes comparten el SHA verificado. La
ruta física no se expone en la interfaz.

## API

| Método | Endpoint | Uso |
|---|---|---|
| GET | `/api/training-runs/{id}/stage2-availability` | Estado técnico y acción |
| GET | `/api/training-runs/{id}/stage2-package-preview` | Preview del paquete |
| POST | `/api/training-runs/{id}/enable-stage2` | Copia, contrato, smoke, activación e inferencia |
| GET | `/api/stage2/models` | Selector exclusivo de modelos Etapa 2 activos |

El POST exige `actor`, `reason` y `confirm_stage2_enablement=true`. Es
idempotente cuando el mismo training ya tiene una revisión activa.

## Interfaz

La acción aparece únicamente en la tarjeta TRAIN:

- fixture: texto “Ejecución técnica sin modelo desplegable”, sin acción;
- bloqueado: “No disponible” y la primera causa técnica;
- elegible: “Habilitar para Etapa 2”;
- activo: “Ver modelo Etapa 2”.

El modal identifica training, model version, SHA-256, framework, advertencias y
alcance no clínico. Al completar el proceso navega al deployment exacto. Las
acciones EVALUATE y EXPLAIN no cambian.

## Separación de producción

La migración `028_stage2_model_availability.sql` permite una `model_version`
`candidate` sólo en el slot exacto `stage2/default`, con metadata
`stage2.eligible=true` y smoke `PASS`. Cualquier otro ambiente mantiene la
regla formal `approved/deployed`. El selector `/api/models/available` también
mantiene su filtro formal; Etapa 2 usa `/api/stage2/models`.

## Rollback

Al activar una nueva revisión, la anterior del mismo slot pasa a `inactive`;
nunca se sobrescribe. `rollback_available` sólo es verdadero si hay una
revisión histórica inactiva o retirada. El rollback debe crear/reactivar una
nueva revisión auditable mediante el servicio de deployments existente; si no
hay revisión previa, la recuperación segura es desactivar el slot.

Rollback de código:

1. revertir UI y endpoints Etapa 2;
2. desactivar cualquier revisión `stage2/default`;
3. restaurar la función trigger desde la migración 027;
4. conservar artefactos y registros históricos para auditoría.

## Orden de implementación aplicado

1. servicio técnico y paquete inmutable;
2. excepción DB acotada y regla de inferencia;
3. endpoints;
4. acción TRAIN y modal;
5. selector API separado;
6. tests, build y E2E con modelo real.

## Evidencia E2E real

Ejecutada el 2026-07-23 con PostgreSQL y TensorFlow locales:

- training: `8dca1f53-bcb6-443e-8130-f654e6e518ae`;
- model version: `03bf43fa-7e8a-4b3c-84ec-686238325322`;
- deployment: `d6356285-2b00-4dcc-b933-5ff02482da13`;
- SHA-256: `70230aee19f14a4c570fc62dfcf79e1790e6c7674c49ab310d1abdfc056a86ab`;
- smoke: `PASS`;
- inference run: `8a64baf4-0be6-4b4c-bbc6-32dec109657a`;
- image analysis job: `2cbb5360-d1cd-4cda-be0c-d470116ecbb1`;
- `environment=stage2`, `alias=default`, `status=active`;
- champion de producción sin cambios;
- segunda ejecución idempotente: mismo deployment, sin otra inferencia.

`rollback_available=false` es correcto porque ésta es la primera revisión del
slot Etapa 2.
