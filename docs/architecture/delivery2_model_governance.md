# Gobierno de modelos Etapa 2

> **Estado documental:** `HISTORICAL_AUDIT`
> **Uso operativo:** No; diseño objetivo anterior al resolver productivo vigente.
> **Snapshot:** Entrega 2 / Architecture Baseline v1.1.

## Fuente de verdad

- `stage2_model_publications`: catálogo de modelos autorizados. Puede contener múltiples publicaciones activas.
- Slot `stage2/default`: única selección predeterminada cuando el request no especifica modelos.
- `model_versions` + `checkpoint_artifact_id` + SHA-256: identidad inmutable del clasificador.
- `deployed_model_versions`: historial de revisiones del slot y snapshots ejecutables.

`stage2/default` debe referenciar una `stage2_model_publication` activa y compatible. No puede enlazar sólo un checkpoint. La implementación futura añadirá integridad transaccional; hasta entonces la API objetivo debe verificar ambas identidades antes de inferir.

## Publicación ligera y elegibilidad default

Publicación ligera exige:

- TRAIN `completed`;
- EVALUATE `completed` vinculado;
- `model_version`, checkpoint y runs identificables.

Elegibilidad para `stage2/default` exige además las validaciones ya presentes en `Stage2ModelAvailabilityService`, `ModelContractService`, `TraceableInferenceService` y triggers 027/028:

- lineage resuelto y checkpoint perteneciente al TRAIN;
- artifact disponible, tamaño y SHA-256 coincidentes;
- modelo cargable y signatures compatibles;
- preprocessing y label mapping completos;
- mapping `0=uninfected`, `1=parasitized`;
- score `probability_parasitized`;
- threshold/calibración o fallback técnico explícitamente rotulado;
- métricas y evidencia de evaluación;
- chequeo de colapso cuando esté disponible;
- smoke técnico PASS;
- publicación activa.

Publicar no equivale a seleccionar como default.

## Desactivación y rollback

Conducta aprobada: rechazar con 409 la desactivación de una publicación referenciada por un slot activo. El administrador primero reasigna o desactiva `stage2/default` en una transacción auditada. Esto evita una ventana sin modelo válido y hace explícita la intención.

Rollback crea/activa una nueva revisión del slot que referencia una publicación histórica todavía activa. No modifica publicación, model version, checkpoint, TRAIN ni EVALUATE. Eventos before/after y motivo son obligatorios.

## Multimodelo

El request puede:

1. omitir modelos: resuelve `stage2/default` como `primary`;
2. indicar una o más publicaciones activas;
3. combinar default con modelos adicionales publicados.

Se normalizan y congelan `classifier_assignments` con roles `primary|additional|comparison` y orden. No se crea ensemble ni se combinan scores. Cada crop produce una predicción por assignment; results se muestran en paralelo. La falla de un modelo no oculta los demás.

## Contrato de clasificación

Entrada:

```json
{
  "analysis_job_id": "uuid",
  "crop_ids": ["uuid"],
  "classifier_model_version_id": "uuid",
  "checkpoint_artifact_id": "uuid",
  "preprocessing_version": "string",
  "threshold_policy_version": "string"
}
```

Salida persistida individualmente: crop, classification run, model version, publication, TRAIN, EVALUATE, checkpoint/SHA, preprocessing, mapping, threshold, ambas probabilidades, label/index, confidence, tiempo y estado. Estados de ejecución: `pending|processing|completed|failed|excluded`; confianza: `high|medium|low|manual_review|out_of_distribution`.

## Resultado por modelo

Incluye assignment/role, counts, threshold y score promedio. Recall, precision, specificity, F2, ROC-AUC, PR-AUC, accuracy y balanced accuracy sólo se obtienen del `evaluation_run` y se rotulan **“Métricas históricas de evaluación del modelo utilizado.”** No se atribuyen a una imagen sin ground truth.

## Transición

`GET /api/stage2/models` actual lee publicaciones y la inferencia actual resuelve deployments. Prompt 3/10 debe introducir la relación de publicación en el slot y resolverla mediante un único servicio, conservando endpoints legacy como adapters. No se modifican las reglas actuales en Prompt 1.
