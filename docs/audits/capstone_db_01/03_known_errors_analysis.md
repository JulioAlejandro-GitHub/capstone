# CAPSTONE-DB-01 — Errores conocidos

Estado documental: `HISTORICAL_AUDIT` — 2026-10-12. Diagnóstico sin ejecutar pipelines ni mutaciones.

## DB-01 — campaign_guard y CAMPAIGN_DATABASE_OPERATION_FAILED

**Incompatibilidad del guard identificada; el código público corresponde a un fallo de operación del repositorio.**

Aclaración posterior del usuario: el mensaje exacto es «Configuración rechazada por el contrato (CAMPAIGN_DATABASE_OPERATION_FAILED)». Sustituye el literal de conexión incluido en la solicitud inicial. No hay evidencia aportada de un fallo de red en este caso.

Existe `public.campaign_guard()`, PL/pgSQL, search_path `public, pg_catalog`. El trigger `campaign_guard` es BEFORE INSERT/DELETE/UPDATE, por fila, en `public.experimental_campaigns`. Está habilitado. Definición completa: `catalog_inventory.json/routines` y respaldo `functions.sql`; declaración del trigger en `triggers_classification.csv`.

Al insertar (y al actualizar un draft), consulta `audit_events` por `dataset_evidence_id` y exige simultáneamente:

1. Evidencia existente con event_type `ml.dataset_verification`.
2. success verdadero y error_code nulo.
3. `after_state.integrity_status` exactamente `verified`.
4. Igualdad JSON del snapshot con `NEW.dataset_snapshot`.
5. Igualdad de dataset_version_id.

La disyunción de incumplimientos produce `CAMPAIGN_DATASET_EVIDENCE_CONFLICT`. No referencia columnas inexistentes en ese recorrido: el catálogo tiene los campos usados. También protege inmutabilidad, transiciones, hash canónico, matriz configuración×seed, conteos y protocolo científico. Estas reglas no son todas obsoletas.

El productor vigente `malaria_dl_local_project/src/malaria_dl/data/governed_dataset.py:64`, `GovernedDatasetSnapshot.verification_metadata`, emite `verified` solo si verified_splits es exactamente `(train,val,test)`. Para train/val emite `verified_requested_splits`, con global_integrity_status `verified_frozen_metadata` y physical_integrity_status `verified`. `campaigns/service.py:139`, `CampaignService.configure`, solicita precisamente train/val; `persistence/dataset_evidence.py:163` persiste el evento exitoso.

Evidencia de solo lectura en `assessments.jsonl`:

- Nueve verificaciones exitosas de `campaigns.configure` tienen `verified_requested_splits` y verificación física `verified`.
- Existen diez evidencias anteriores de ese consumidor con `verified`.
- En cuatro campañas persistidas no faltan evidencias ni difieren snapshot/version. Una tiene hoy un estado de evidencia distinto del literal exigido. **No se deduce cuándo o por qué fue admitida**, ni se declara corrupción: un trigger no revalida retroactivamente todas las filas.
- Logs retenidos de PostgreSQL y backend registran `CAMPAIGN_DATASET_EVIDENCE_CONFLICT`; ambos contienen un evento a `2026-10-11T13:48:13Z`. Las firmas se conservaron sin parámetros, SQL con valores, usuarios clínicos ni payloads. Otros eventos de logs pueden corresponder a pruebas históricas; sus cantidades no equivalen a solicitudes del usuario.

Recorrido de creación: `frontend/src/pages/CampaignConfiguration.tsx` → API → `backend_api/app/routes/campaigns.py:53` (`POST /api/campaigns`) → `services/campaign_configuration.py:154` → `CampaignService.configure` → `CampaignRepository.create_frozen` (`campaigns/repository.py:281`) → INSERT draft + materialización + UPDATE frozen en una transacción. El estado draft inicial se usa internamente y no prueba por sí mismo un bloqueo artificial.

Tratamiento de excepciones: `CampaignRepository.transaction:50` captura excepciones distintas de CampaignError y las transforma en `CampaignError("CAMPAIGN_DATABASE_OPERATION_FAILED")`, suprimiendo su causa pública. El servicio, línea 176, traduce ese CampaignError a HTTP 422; `app/main.py:35` serializa el código en details. `CampaignConfiguration.tsx:50–64` extrae ese código y lo envuelve en el texto mostrado por el usuario. Este recorrido explica el mensaje corregido; no es necesario postular un error de red o CORS para explicarlo.

La incompatibilidad `verified_requested_splits` frente a `verified` es una causa demostrada de rechazo del guard y concuerda con los errores retenidos en logs. **El código público es genérico**: por sí solo no identifica el trigger ni la excepción original. Para atribuir de forma inequívoca esta solicitud concreta al rechazo `CAMPAIGN_DATASET_EVIDENCE_CONFLICT`, falta su correlación temporal o correlation_id con el error interno. No se reprodujo POST por la prohibición de escritura. Se retira el fallo de red como pendiente de DB-01; permanece únicamente la atribución de la excepción interna de esa solicitud.

Recomendación: corregir la condición de evidencia para validar los splits requeridos sin exigir exposición de TEST al crear campaña; conservar identidad, éxito, snapshot y separación científica. Corregir también presentación/observabilidad de errores, preservando sanitización. No deshabilitar campaign_guard.

## DB-02 — unsupported_alembic_revision

**Causa identificada y reproducida mediante lectura con el rol runtime.**

`run_train_all_models.py:173` imprime `STOP {exc}`. `execution/campaign.py:216,379,442` usa preflight E10; `execution/repository.py:83` llega a `execution/schema.py:78`, `require_e10_schema`.

Condición exacta en líneas 91–93: exige una única fila en alembic_version y que pertenezca a `SUPPORTED_REVISIONS = ('20260922_01','pg_v2_baseline')`. La fila operativa es `cell_checkpoint_reuse_v2`; se rechaza antes de comprobar capacidades.

Se ejecutaron únicamente los SELECT de CAPABILITIES, con el catálogo vigente:

| Capacidad E10 | Resultado |
|---|---|
| event_id UUID / event_sequence NUMERIC, forma esperada | true |
| CHECK train_event_metadata validado y expresión esperada | true |
| Índices únicos parciales de evento/secuencia | true |
| a_train_event_guard, estado, firma, search_path y hash del cuerpo | true |

Las comparaciones completas del contrato v2 también coinciden: funciones v2/e04, triggers, constraints de evaluations e índices uq_e04. Se ejecutó `require_v2_capabilities` con `capstone_v2_runtime`, en conexión `default_transaction_read_only=on`: PASS. `require_e10_schema` en esa misma conexión devolvió `E10_SCHEMA_NOT_READY: unsupported_alembic_revision`. Evidencia: `diagnostics.jsonl` y `runtime_probe.json` locales. Las huellas de schema.py y assessment_lineage.py del contenedor coinciden con el workspace.

El bloqueo observado es histórico respecto de las capacidades que valida ese guard; **no demuestra que toda la ejecución TRAIN sea correcta**. No se ejecutaron reserva, claim, TRAIN ni comprobaciones que persistieran evidencia. La campaña solicitada existe y está paused, expected_count=1; no se modificó su estado.

TRAIN utiliza runs, modelos y datasets/materializaciones, campaign_members/attempts, train_execution_sessions/records/revisions, configuración, artefactos, eventos, evaluaciones, calibración y métricas. Estos objetos existen en catálogo. El CHECK, índices únicos, fencing de propietario y relaciones protegen atomicidad e identidad y deben conservarse.

No basta añadir una revisión a la whitelist: `execution/repository.py:256,292`, `persistence/result_repository.py:79,96` y `backend_api/app/services/scientific_results.py:29` seleccionan comportamiento v2 únicamente por igualdad exacta con `pg_v2_baseline`. Admitir el head nuevo sin corregir esas ramas puede omitir run_configurations, contexto de evaluación o proyección normalizada y elegir lectura histórica. La solución futura debe usar directamente el esquema instalado.

También afecta `/ready`, `/runs/{run_id}/scientific-results`, ejecución local/controlada, preflight de campañas y persistencia de eventos de resultados. `schema_contract.py` no importa Alembic: compara catálogo con un JSON histórico. Es una dependencia de la etiqueta/contrato, no una migración en runtime.

## DB-03 — EXPLAIN persistido ausente en Mostrar ejecuciones

**Causa identificada: proyección SQL y DTO incompletos para assessments EXPLAIN E6.**

El CLI actual `src/explain.py` delega a `explainability/pipeline.py:1217`, que llama `assessment.cli.main('explain')`. No debe confundirse con helpers históricos de ese mismo módulo que crean run_lineage. El camino vigente produce identidad `kind='explain'` y persiste mediante `assessment/repository.py:74,117,198,209`:

`assessment_identities.training_run_id → runs.id`; `assessment_attempts.identity_id → assessment_identities.id`; resultados y artefactos por attempt_id. La identidad conserva checkpoint/modelo/dataset/protocolo; el enlace opcional a evaluación se guarda en `identity.evaluation` como attempt_id e identity_hash. `assessment/service.py:105–122` exige intento verificado y el mismo modelo, dataset, muestras, decisión y protocolo. Los dos EXPLAIN actuales son Grad-CAM y no tienen referencia explícita a intento EVALUATE; comparten TRAIN con el EVALUATE observado. No es obligatorio que exista un run adicional tipo explainability. Campañas se relacionan mediante `assessment_campaign_consumers`; hay cero enlaces para los dos EXPLAIN observados, lo que no explica su exclusión en una pantalla agrupada por TRAIN.

| Evidencia actual | Observado |
|---|---:|
| TRAIN en runs | 14, completed |
| Runs evaluation / explainability | 0 / 0 |
| Assessments EVALUATE verificados | 1 intento; 2.693 resultados |
| Assessments EXPLAIN verificados | 2 identidades/intentos; un mismo TRAIN |
| Resultados EXPLAIN | 5.386 |
| Referencias a artefactos EXPLAIN | 10.772 |
| EXPLAIN sin TRAIN válido | 0 |
| EXPLAIN con TRAIN que también tiene EVALUATE | 2 |
| explainability_results / xai_evidence / xai_artifacts / cell_explanations | 0 / 0 / 0 / 0 |

No se leyeron contenidos de imágenes, predicciones individuales ni identidades clínicas para el informe. La presencia de referencias no verifica la existencia/hash de los archivos externos.

`backend_api/app/repositories/assessment_lineage.py:24` filtra `i.kind='evaluate'`. Su CTE visible_assessments, consumido por training_summaries y lineage_children, incorpora EVALUATE E6 pero no EXPLAIN E6. La alternativa EXPLAIN exige simultáneamente un `runs.run_type='explainability'` y `run_lineage.relationship_type='explains_checkpoint_from'`; ambas tablas carecen de esas filas en esta instantánea. El agregado de explicaciones además lee `explainability_results`, que está vacío.

Rutas: `routes/runs.py:458` para resúmenes y `:462–483` para `/runs/{training_run_id}/lineage-children` y alias `/api/runs/...`. Serializador: `services/lineage_children.py:423` asigna toda fila `source_kind='assessment_e6'` a evaluations. `schemas/lineage_children.py:87` permite EXPLAIN solo como `ExplainabilityLineageChild`, con run_id y linaje de run; no admite la identidad de un intento E6.

Frontend: `types/api.ts:413–414` admite la unión E6 en evaluations, pero explainabilities solo contiene hijos de run. `pages/Runs.tsx:133` consulta los hijos con límite 100 y reconcilia contadores. No contiene un filtro que pueda recuperar los EXPLAIN omitidos por el backend.

Se ejecutó la lectura de los servicios reales `list_training_summaries` y `get_training_lineage_children` sobre los 14 TRAIN, con transacciones de solo lectura: un EVALUATE `assessment_e6`, cero EXPLAIN, sin truncamiento. El problema se demuestra antes del navegador; no depende del bloqueo Alembic DB-02 en este recorrido. Consultas reproducibles en assessment_queries.sql y resultado local report_read_probe.json.

Recomendación: incorporar EXPLAIN E6 a la consulta, contadores, DTO y presentación mediante identity_id/attempt_id/training_run_id reales. Seleccionar intento verificado o último según política explícita, mantener métodos/estados y no inventar runs para satisfacer el DTO viejo. Comprobar detalle/galería además de la lista; mostrar un contador sin navegación válida sería una corrección incompleta.
