# Capstone — Auditoría SQL de evidencia científica para Comparación Científica (SCC)

**Fecha:** 16 de octubre de 2026  
**Base:** PostgreSQL actual de Capstone (única fuente de verdad estructurada)  
**Alcance:** cuatro ejecuciones Custom CNN (RUN A–D), dataset oficial, campaña, checkpoints, métricas VAL y predicciones individuales.  
**Modalidad:** consultas de solo lectura. No ejecutar entrenamientos, evaluaciones ni cambios en la base de datos.

## 1. Propósito y criterios de lectura

Este documento consolida las consultas SQL utilizadas durante la auditoría conversacional, explica su finalidad y registra los resultados comunicados. También incluye consultas de inspección y una consulta de control opcional para reproducir verificaciones. **Los resultados consignados proceden de las salidas SQL compartidas por el usuario; este documento no representa una ejecución independiente sobre PostgreSQL.**

Distinguir:

- **TRAIN/VAL**: entrenamiento y validación durante el desarrollo.
- **VALIDATION final** (`evaluation_role = 'training_validation_final'`, `purpose = 'development'`): evaluación persistida sobre VAL, atribuida al checkpoint.
- **TEST independiente**: evaluación diferente, no encontrada para A–D en las consultas realizadas.
- **Checkpoint lógico**: asociación por RUN, época y `artifact_id`; **integridad física**: existencia y SHA-256 del `.keras` comprobados en disco, que no se infieren de la existencia de la fila.
- **Misma población observada**: igualdad de claves `sample` y etiquetas en las predicciones; no debe confundirse con un registro exhaustivo de imágenes consumidas durante cada entrenamiento.

### Identificadores utilizados

| Alias | Optimizador | RUN ID | Época seleccionada | Checkpoint |
|---|---|---|---:|---|
| A | Adadelta | `565a1dac-9c51-411b-a76c-efeb1d38722c` | 14 | `epoch_14.keras` |
| B | Adam | `a1c310c5-1cb0-4b1e-afc4-b087ed13ab24` | 4 | `epoch_4.keras` |
| C | AdamW | `c96bb5c1-1edb-4ef3-9854-fd715c4025f4` | 2 | `epoch_2.keras` |
| D | SGD | `cc925f74-3535-40e0-9060-23a06cea8024` | 19 | `epoch_19.keras` |

- Campaña: `b54ea684-1b0c-421d-a4b2-9f12667bd619`.
- Versión del dataset: `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`.
- Materialización: `e15dc166-1c4b-558e-b77b-727b1783430c`.
- Evidencia de dataset: `861d263b-f414-497d-bb60-cca3bd059d79`.

---

## 2. A1–A3 — Campaña, snapshot y procedencia del dataset

### SQL 01 — Inventariar claves del snapshot de campaña

**Uso:** identificar los campos disponibles en `experimental_campaigns.dataset_snapshot` antes de interpretar su contenido. También muestra la versión y evidencia de dataset asociadas a la campaña.

```sql
SELECT
    id AS campaign_id,
    dataset_version_id,
    dataset_evidence_id,
    jsonb_typeof(dataset_snapshot) AS snapshot_type,
    CASE
        WHEN jsonb_typeof(dataset_snapshot) = 'object'
        THEN (
            SELECT array_agg(k ORDER BY k)
            FROM jsonb_object_keys(dataset_snapshot) AS k
        )
        ELSE NULL
    END AS snapshot_keys,
    contract_hash
FROM public.experimental_campaigns
WHERE id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619';
```

**Resultado observado:** snapshot tipo `object`, con claves `clinical_identity_fingerprint`, `counts`, `dataset_materialization_id`, `dataset_root`, `dataset_version_id`, `patient_assignment_fingerprint`, `record_assignment_fingerprint`, `selection_unit`, `source_population_fingerprint`. La versión y evidencia de dataset están presentes.

### SQL 02 — Consultar huellas, unidad de selección y conteos

**Uso:** comprobar que la campaña conserva huellas de población y asignación de registros/pacientes, así como los conteos del split oficial. No se muestran rutas locales.

```sql
SELECT
    id AS campaign_id,
    dataset_snapshot->>'dataset_version_id'
        AS snapshot_dataset_version_id,
    dataset_snapshot->>'dataset_materialization_id'
        AS materialization_id,
    dataset_snapshot->>'selection_unit'
        AS selection_unit,
    dataset_snapshot->>'record_assignment_fingerprint'
        AS record_assignment_fingerprint,
    dataset_snapshot->>'patient_assignment_fingerprint'
        AS patient_assignment_fingerprint,
    dataset_snapshot->>'clinical_identity_fingerprint'
        AS clinical_identity_fingerprint,
    dataset_snapshot->>'source_population_fingerprint'
        AS source_population_fingerprint,
    dataset_snapshot->'counts'
        AS counts
FROM public.experimental_campaigns
WHERE id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619';
```

**Resultado observado:** `selection_unit = dataset_version_id`; las cuatro huellas están pobladas; `counts = {"train": 22180, "val": 2693, "test": 2685}`; la versión y materialización son las identificadas arriba. Las huellas no se comparan entre sí: cada una representa un objeto de identidad diferente.

### SQL 03 — Validar la materialización referenciada

**Uso:** verificar que la materialización del snapshot existe, pertenece a la misma versión del dataset, está lista y reconcilia los 27.558 registros oficiales.

```sql
SELECT
    ec.id AS campaign_id,
    dm.id AS materialization_id,
    dm.dataset_version_id,
    dm.status,
    dm.reconciliation_status,
    dm.record_count,
    dm.completed_at,
    (
        dm.dataset_version_id = ec.dataset_version_id
    ) AS dataset_matches,
    (
        dm.record_count = 27558
    ) AS population_count_matches
FROM public.experimental_campaigns AS ec
LEFT JOIN public.dataset_materializations AS dm
    ON dm.id::text =
        ec.dataset_snapshot->>'dataset_materialization_id'
WHERE ec.id = 'b54ea684-1b0c-421d-a4b2-9f12667bd619';
```

**Resultado observado:** materialización `READY`, reconciliación `PASS`, `record_count = 27558`, `dataset_matches = true`, `population_count_matches = true`, completada el 18-08-2026.

**Conclusión A1–A3:** procedencia del dataset, split gobernado, snapshot de campaña y materialización acreditados dentro de este alcance. Según la auditoría previa, la versión estaba `FROZEN`, con 12 controles de split `PASS` y sin solapamientos por muestra o paciente. **Limitación:** `run_dataset_images` no registraba consumo individual para A–D; el snapshot y las predicciones VAL no prueban por sí solos cada imagen utilizada durante TRAIN.

---

## 3. A6 — Estructura de evaluaciones y métricas

### SQL 04 — Inspeccionar esquema de `evaluations` y `run_clinical_metrics`

**Uso:** descubrir columnas reales y claves de relación antes de consultar evaluaciones. Permite localizar `training_run_id`, `checkpoint_artifact_id`, `split`, `evaluation_role`, `source_assessment_attempt_id`, `evaluation_id`, métricas y matriz de confusión.

```sql
SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('evaluations', 'run_clinical_metrics')
ORDER BY table_name, ordinal_position;
```

**Resultado observado:** `evaluations` conserva identidad de RUN, checkpoint, dataset, split, protocolo, población y origen; `run_clinical_metrics` conserva métricas clínicas, matriz de confusión, conteo y `evaluation_id`.

### SQL 05 — Inventariar evaluaciones atribuibles a los cuatro RUN

**Uso:** detectar evaluaciones existentes aunque no haya registros de `assessment_identities` para A–D. El `LEFT JOIN` preserva RUN sin evaluación.

```sql
SELECT
    r.id AS training_run_id,
    e.id AS evaluation_id,
    e.run_id AS evaluation_run_id,
    e.split,
    e.evaluation_role,
    e.purpose,
    e.checkpoint_artifact_id,
    e.source_assessment_attempt_id,
    COUNT(cm.run_clinical_metric_id) AS metric_records,
    MAX(cm.sample_count) AS sample_count
FROM public.runs AS r
LEFT JOIN public.evaluations AS e
    ON e.training_run_id = r.id
LEFT JOIN public.run_clinical_metrics AS cm
    ON cm.evaluation_id = e.id
WHERE r.id IN (
    '565a1dac-9c51-411b-a76c-efeb1d38722c',
    'a1c310c5-1cb0-4b1e-afc4-b087ed13ab24',
    'c96bb5c1-1edb-4ef3-9854-fd715c4025f4',
    'cc925f74-3535-40e0-9060-23a06cea8024'
)
GROUP BY
    r.id, e.id, e.run_id, e.split,
    e.evaluation_role, e.purpose,
    e.checkpoint_artifact_id,
    e.source_assessment_attempt_id
ORDER BY r.id, e.id;
```

**Resultado observado:** cuatro evaluaciones, una por RUN, todas `split = val`, `evaluation_role = training_validation_final`, `purpose = development`, una fila de métricas por evaluación y 2.693 muestras cada una. `source_assessment_attempt_id` vacío. Los `checkpoint_artifact_id` coinciden con los checkpoints seleccionados.

### SQL 06 — Recuperar métricas finales VAL

**Uso:** construir SCC-MET.1 directamente desde la evidencia persistida; no requiere abrir `.keras` ni ejecutar inferencias.

```sql
SELECT
    e.training_run_id,
    e.split,
    cm.sample_count,
    cm.accuracy,
    cm.precision_parasitized,
    cm.recall_parasitized,
    cm.specificity,
    cm.f1_parasitized,
    cm.f2_parasitized,
    cm.roc_auc_parasitized,
    cm.pr_auc_parasitized,
    cm.tn,
    cm.fp,
    cm.fn,
    cm.tp,
    cm.threshold_used
FROM public.evaluations AS e
JOIN public.run_clinical_metrics AS cm
    ON cm.evaluation_id = e.id
WHERE e.training_run_id IN (
    '565a1dac-9c51-411b-a76c-efeb1d38722c',
    'a1c310c5-1cb0-4b1e-afc4-b087ed13ab24',
    'c96bb5c1-1edb-4ef3-9854-fd715c4025f4',
    'cc925f74-3535-40e0-9060-23a06cea8024'
)
  AND e.split = 'val'
  AND e.evaluation_role = 'training_validation_final'
ORDER BY e.training_run_id;
```

**Resultado observado:** umbral `0.5` y 2.693 muestras para todos. Valores resumidos:

| RUN | Accuracy | Recall (parasitada) | Especificidad | F2 | ROC-AUC | TN | FP | FN | TP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 0.954697 | 0.929057 | 0.979532 | 0.938405 | 0.990210 | 1340 | 28 | 94 | 1231 |
| B | 0.934645 | 0.898868 | 0.969298 | 0.911526 | 0.984671 | 1326 | 42 | 134 | 1191 |
| C | 0.949127 | 0.939623 | 0.958333 | 0.942896 | 0.986015 | 1311 | 57 | 80 | 1245 |
| D | 0.946899 | 0.916226 | 0.976608 | 0.927284 | 0.989231 | 1336 | 32 | 111 | 1214 |

**Interpretación:** A lidera varias métricas globales, mientras C presenta menos falsos negativos y mayor F2 en VAL. No constituye evidencia de superioridad en TEST ni significación estadística.

---

## 4. Predicciones de EVALUATE/EXPLAIN en `assessment_results`

### SQL 07 — Inspeccionar columnas de `assessment_results`

**Uso:** determinar cómo se relacionan los resultados individuales con intentos de evaluación y muestras.

```sql
SELECT
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'assessment_results'
ORDER BY ordinal_position;
```

**Resultado observado:** `attempt_id uuid`, `sample_id uuid`, `payload jsonb`.

### SQL 08 — Inventario general de resultados individuales

**Uso:** estimar cobertura global y comprobar que existen resultados serializados. **Nota:** `example_payload_key` presenta una sola clave de ejemplo; no enumera todas las claves.

```sql
SELECT
    COUNT(*) AS total_predictions,
    COUNT(DISTINCT attempt_id) AS total_attempts,
    COUNT(DISTINCT sample_id) AS distinct_samples,
    COUNT(*) FILTER (
        WHERE payload IS NULL
    ) AS null_payloads,
    (
        SELECT jsonb_object_keys(ar2.payload)
        FROM public.assessment_results AS ar2
        WHERE jsonb_typeof(ar2.payload) = 'object'
        LIMIT 1
    ) AS example_payload_key
FROM public.assessment_results;
```

**Resultado observado:** 22.889 registros, 26 intentos, 5.378 muestras distintas, cero payloads nulos; clave de ejemplo `label`.

### SQL 09 — Atribuir resultados a RUN e intento

**Uso:** evitar atribuir predicciones de otros entrenamientos a A–D. Distingue `evaluate` de `explain` y muestra el estado de cada intento.

```sql
SELECT
    ai.training_run_id,
    aa.id AS attempt_id,
    ai.kind AS assessment_kind,
    aa.state AS attempt_state,
    COUNT(ar.sample_id) AS predictions,
    COUNT(DISTINCT ar.sample_id) AS distinct_samples
FROM public.assessment_results AS ar
JOIN public.assessment_attempts AS aa
    ON aa.id = ar.attempt_id
JOIN public.assessment_identities AS ai
    ON ai.id = aa.identity_id
GROUP BY
    ai.training_run_id,
    aa.id,
    ai.kind,
    aa.state
ORDER BY ai.training_run_id, aa.id;
```

**Resultado observado:** los 26 intentos con resultados pertenecen a tres RUN distintos de A–D: `338136db-a207-47fc-bbf3-d17ce85c0dc2`, `bbbd5b60-afaa-4034-a504-a60ed642aafe` y `d3d42cf3-0800-468c-b3ed-995860967da1`. Hay intentos `evaluate` verificados sobre VAL y TEST en algunos de ellos, e intentos `explain` individuales, completos o fallidos. **No reutilizar estos resultados como predicciones de A–D.**

---

## 5. Predicciones individuales históricas en `train_execution_records`

**Nota de esquema:** la columna real usada en las consultas ejecutadas es `kind`, **no** `event_kind`. En una primera versión se intentó seleccionar `ter.kind` sin agruparlo, causando `SQLSTATE 42803`; el SQL corregido siguiente elimina esa columna redundante del `SELECT`.

### SQL 10 — Inventariar eventos `predictions` y claves del JSON

**Uso:** comprobar si TRAIN conservó evidencia de predicción en cada época y conocer las claves del último evento de cada RUN.

```sql
SELECT
    r.id AS training_run_id,
    COUNT(*) AS events,
    (
        SELECT array_agg(k ORDER BY k)
        FROM jsonb_object_keys(
            (
                SELECT t2.payload
                FROM public.train_execution_records AS t2
                WHERE t2.run_id = r.id
                  AND t2.kind = 'predictions'
                ORDER BY t2.created_at DESC
                LIMIT 1
            )
        ) AS k
    ) AS latest_payload_keys
FROM public.runs AS r
JOIN public.train_execution_records AS ter
    ON ter.run_id = r.id
WHERE r.id IN (
    '565a1dac-9c51-411b-a76c-efeb1d38722c',
    'a1c310c5-1cb0-4b1e-afc4-b087ed13ab24',
    'c96bb5c1-1edb-4ef3-9854-fd715c4025f4',
    'cc925f74-3535-40e0-9060-23a06cea8024'
)
  AND ter.kind = 'predictions'
GROUP BY r.id
ORDER BY r.id;
```

**Resultado observado:** A 26, B 16, C 14 y D 31 eventos; claves comunes `{epoch, role, samples}`.

### SQL 11 — Inspeccionar estructura de `samples`

**Uso:** determinar si los eventos contienen estadísticas agregadas o predicciones individualizadas, sin extraer todos los arreglos.

```sql
SELECT DISTINCT ON (run_id)
    run_id,
    payload->>'role' AS role,
    jsonb_typeof(payload->'samples') AS samples_type,
    CASE
        WHEN jsonb_typeof(payload->'samples') = 'array'
        THEN jsonb_array_length(payload->'samples')
    END AS samples_count,
    CASE
        WHEN jsonb_typeof(payload->'samples') = 'array'
         AND jsonb_array_length(payload->'samples') > 0
        THEN payload->'samples'->0
        ELSE payload->'samples'
    END AS sample_example
FROM public.train_execution_records
WHERE kind = 'predictions'
  AND run_id IN (
    '565a1dac-9c51-411b-a76c-efeb1d38722c',
    'a1c310c5-1cb0-4b1e-afc4-b087ed13ab24',
    'c96bb5c1-1edb-4ef3-9854-fd715c4025f4',
    'cc925f74-3535-40e0-9060-23a06cea8024'
  )
ORDER BY run_id, created_at DESC;
```

**Resultado observado:** `role = val`, `samples_type = array`, 2.693 elementos por RUN. Ejemplo:

```json
{"label": 0, "score": 0.0161560270935297, "sample": "val/uninfected/C106P67ThinF_IMG_20150924_102245_cell_123.png"}
```

**Advertencia:** el evento más reciente no necesariamente corresponde a la época del checkpoint seleccionado. Esta consulta es exploratoria, no la selección definitiva para SCC.

### SQL 12 — Verificar eventos de la época seleccionada

**Uso:** comprobar que hay un evento `predictions` VAL para cada checkpoint seleccionado (épocas 14, 4, 2, 19).

```sql
WITH selected_runs(run_id, selected_epoch) AS (
    VALUES
        ('565a1dac-9c51-411b-a76c-efeb1d38722c'::uuid, 14),
        ('a1c310c5-1cb0-4b1e-afc4-b087ed13ab24'::uuid, 4),
        ('c96bb5c1-1edb-4ef3-9854-fd715c4025f4'::uuid, 2),
        ('cc925f74-3535-40e0-9060-23a06cea8024'::uuid, 19)
)
SELECT
    s.run_id,
    s.selected_epoch,
    COUNT(t.run_id) AS matching_events,
    MAX(jsonb_array_length(t.payload->'samples')) AS samples_count,
    MAX(t.payload->>'role') AS role
FROM selected_runs AS s
LEFT JOIN public.train_execution_records AS t
    ON t.run_id = s.run_id
   AND t.kind = 'predictions'
   AND t.payload->>'epoch' = s.selected_epoch::text
   AND jsonb_typeof(t.payload->'samples') = 'array'
GROUP BY s.run_id, s.selected_epoch
ORDER BY s.run_id;
```

**Resultado observado:** 1 evento por RUN, `role = val`, `samples_count = 2693` para las cuatro épocas seleccionadas.

**Consideración de robustez:** `jsonb_array_length` requiere arreglo; la consulta se validó con los datos observados. En código de producción conviene controlar explícitamente tipos JSON antes de aplicar funciones de arreglo.

### SQL 13 — Comparar identidad de muestras y etiquetas entre RUN

**Uso:** demostrar que la comparación por imagen se hace sobre las mismas claves `sample`, detectar ausencias, duplicados y etiquetas contradictorias. La clave de emparejamiento es `sample`, **nunca la posición en el JSON**.

```sql
WITH selected_runs(run_label, run_id, selected_epoch) AS (
    VALUES
        ('A', '565a1dac-9c51-411b-a76c-efeb1d38722c'::uuid, 14),
        ('B', 'a1c310c5-1cb0-4b1e-afc4-b087ed13ab24'::uuid, 4),
        ('C', 'c96bb5c1-1edb-4ef3-9854-fd715c4025f4'::uuid, 2),
        ('D', 'cc925f74-3535-40e0-9060-23a06cea8024'::uuid, 19)
),
predictions AS (
    SELECT
        s.run_label,
        x.item->>'sample' AS sample,
        x.item->>'label' AS label
    FROM selected_runs s
    JOIN public.train_execution_records t
        ON t.run_id = s.run_id
       AND t.kind = 'predictions'
       AND t.payload->>'epoch' = s.selected_epoch::text
       AND t.payload->>'role' = 'val'
    CROSS JOIN LATERAL jsonb_array_elements(
        t.payload->'samples'
    ) AS x(item)
),
per_sample AS (
    SELECT
        sample,
        COUNT(*) AS occurrences,
        COUNT(DISTINCT run_label) AS runs_present,
        COUNT(DISTINCT label) AS distinct_labels
    FROM predictions
    GROUP BY sample
)
SELECT
    COUNT(*) AS distinct_samples,
    COUNT(*) FILTER (
        WHERE runs_present = 4
    ) AS samples_shared_by_all,
    COUNT(*) FILTER (
        WHERE runs_present < 4
    ) AS samples_missing_in_some_runs,
    COUNT(*) FILTER (
        WHERE occurrences > 4
    ) AS samples_with_duplicates,
    COUNT(*) FILTER (
        WHERE distinct_labels > 1
    ) AS samples_with_label_conflicts
FROM per_sample;
```

**Resultado observado:** 2.693 muestras distintas, 2.693 compartidas por A–D, 0 ausentes, 0 duplicadas y 0 con conflicto de etiqueta.

**Límite:** la comprobación usa el identificador de ruta relativa `sample`; no sustituye por sí sola una verificación de identidad binaria de imágenes.

### SQL 14 — Reconstruir matrices de confusión desde las predicciones

**Uso:** comprobar que `label` y `score` con umbral `0.5` reproducen exactamente las métricas clínicas persistidas. Detecta puntuaciones nulas, fuera de rango o etiquetas inválidas.

```sql
WITH selected_runs(run_label, run_id, selected_epoch) AS (
    VALUES
        ('A', '565a1dac-9c51-411b-a76c-efeb1d38722c'::uuid, 14),
        ('B', 'a1c310c5-1cb0-4b1e-afc4-b087ed13ab24'::uuid, 4),
        ('C', 'c96bb5c1-1edb-4ef3-9854-fd715c4025f4'::uuid, 2),
        ('D', 'cc925f74-3535-40e0-9060-23a06cea8024'::uuid, 19)
),
predictions AS (
    SELECT
        s.run_label,
        (x.item->>'label')::integer AS label,
        (x.item->>'score')::numeric AS score
    FROM selected_runs s
    JOIN public.train_execution_records t
        ON t.run_id = s.run_id
       AND t.kind = 'predictions'
       AND t.payload->>'epoch' = s.selected_epoch::text
       AND t.payload->>'role' = 'val'
    CROSS JOIN LATERAL jsonb_array_elements(
        t.payload->'samples'
    ) AS x(item)
)
SELECT
    run_label,
    COUNT(*) AS samples,
    COUNT(*) FILTER (WHERE label = 0 AND score < 0.5) AS tn,
    COUNT(*) FILTER (WHERE label = 0 AND score >= 0.5) AS fp,
    COUNT(*) FILTER (WHERE label = 1 AND score < 0.5) AS fn,
    COUNT(*) FILTER (WHERE label = 1 AND score >= 0.5) AS tp,
    COUNT(*) FILTER (
        WHERE label NOT IN (0, 1)
           OR score IS NULL
           OR score < 0
           OR score > 1
    ) AS invalid_records
FROM predictions
GROUP BY run_label
ORDER BY run_label;
```

**Resultado observado:** coincidencia exacta 4/4 con las matrices de `run_clinical_metrics`, 2.693 muestras por RUN y 0 registros inválidos:

| RUN | TN | FP | FN | TP | Inválidos |
|---|---:|---:|---:|---:|---:|
| A | 1340 | 28 | 94 | 1231 | 0 |
| B | 1326 | 42 | 134 | 1191 | 0 |
| C | 1311 | 57 | 80 | 1245 | 0 |
| D | 1336 | 32 | 111 | 1214 | 0 |

**Conclusión:** 10.772 predicciones VAL verificadas y reconciliadas con las métricas clínicas oficiales. La interpretación binaria de `score` es consistente con la clase positiva parasitada y umbral 0,5.

---

## 6. Consultas de apoyo: evidencia establecida durante la auditoría previa

En la misma investigación se comunicaron, antes de las consultas transcritas aquí, estas verificaciones sobre PostgreSQL. Se documentan como **resultados conocidos, sin reproducir SQL no disponible literalmente en el tramo conversacional**:

1. `dataset_versions`: versión **Malaria Patient Split v1**, `FROZEN`, split por paciente, semilla 42.
2. `dataset_split_assignments`: TRAIN 22.180, VAL 2.693, TEST 2.685; 201 identidades clínicas disjuntas.
3. `dataset_split_validation_checks`: 12 controles `PASS`; cero solapamientos por identidad clínica o muestra entre particiones.
4. `runs`: A–D pertenecen a la misma campaña y dataset; comparten `dataset_verification_evidence_id`.
5. `train_execution_records`: A 26, B 16, C 14, D 31 eventos `epoch`; cada uno tiene `loss`, `val_loss`, `accuracy`, `val_accuracy`.
6. `train_execution_records` (`kind = 'selection'`) y `artifacts`: época seleccionada 14/4/2/19; correspondencia lógica con los `.keras` y sus registros de checksum.
7. `runs.execution_parameters -> 'e10_v2_evaluation_context_v1' ->> 'checkpoint_artifact_id'`: vínculo directo con `artifacts.id` para los cuatro RUN.
8. `assessment_identities`: sin identidades de EVALUATE/EXPLAIN independientes para A–D en la comprobación efectuada.
9. `run_dataset_images`: sin registros para A–D en la comprobación efectuada.

### Checkpoints lógicos atribuidos

| RUN | `checkpoint_artifact_id` | Nombre |
|---|---|---|
| A | `0558c938-3d10-5081-9f56-beb1702f49b2` | `epoch_14.keras` |
| B | `ad67b6cd-0abb-55b6-8c5e-d959c50f5f9c` | `epoch_4.keras` |
| C | `8116bf72-dd6a-5b33-90ce-f0cef4e81549` | `epoch_2.keras` |
| D | `cb697916-f3b4-5dd5-885d-bf3ae5901322` | `epoch_19.keras` |

Según la documentación SCC-T aportada: correspondencia de checkpoint 14/14, política satisfecha 12/14 y SHA físico verificado 1/14. **No extender la verificación física de A a B/C/D sin comprobar archivos y hashes.**

---

## 7. Uso de los resultados en los módulos SCC

| Dominio/módulo | Evidencia disponible | Decisión de lectura |
|---|---|---|
| A1 — Dataset | Versión común, snapshot de campaña | Mostrar procedencia acreditada |
| A2 — Split | Split gobernado, controles PASS, materialización READY | Mostrar evidencia oficial y advertir límite de consumo por RUN |
| A3 — Población | Conteos oficiales y 2.693 claves `sample` VAL idénticas | Mostrar población VAL compartida y etiquetas consistentes |
| A4 — Configuración | Parámetros de entrenamiento disponibles parcialmente | Auditoría metodológica adicional pendiente |
| A5 — Checkpoint | Linaje lógico por artifact_id y época | Diferenciar atribución de comprobación física SHA |
| A6 — VAL final | Cuatro evaluaciones `training_validation_final` y métricas | Mostrar VAL sin llamarlo TEST independiente |
| A6 — TEST independiente | No encontrado para A–D en las fuentes consultadas | Indicar ausencia de evidencia; no inferir desde `.keras` |
| SCC-TRAIN.1 | Eventos de época con métricas TRAIN/VAL | Construir curvas desde PostgreSQL |
| SCC-MET.1 | Métricas VAL y confusiones persistidas | Comparación clínica directa, con umbral y población |
| SCC-ERR.1 | Predicciones VAL individuales por época seleccionada | Calcular consenso, desacuerdo y complementariedad por `sample` |
| SCC-EXP / EMB / REP | No acreditados en estas consultas | Auditoría específica antes de presentar resultados |

### Reglas científicas y técnicas para implementar SCC-ERR.1

- Resolver RUN y **época seleccionada desde datos persistidos**, no mantener números de época codificados en la aplicación; los valores fijos de los SQL anteriores corresponden únicamente a esta auditoría reproducible.
- Elegir `role = 'val'` y el evento `predictions` de la época seleccionada; no utilizar el último evento por defecto.
- Emparejar por `sample`, verificar unicidad y consistencia de `label` antes de comparar modelos.
- Utilizar el umbral persistido en la evaluación (en esta auditoría: 0,5); no asumirlo universalmente.
- Verificar integridad de `score`, semántica de clase positiva y correspondencia con matrices de confusión persistidas.
- Calcular categorías `CONSENSUS_TP/TN/FN/FP`, aciertos exclusivos, desacuerdos, errores de alta confianza y oracle únicamente cuando sus definiciones estén explícitas y el conjunto de RUN sea comparable.
- No confundir diferencias entre optimizadores con falta de comparabilidad; preservar configuración y protocolo.
- No ejecutar automáticamente EVALUATE, TEST, EXPLAIN ni inferencia al abrir SCC.
- PostgreSQL es la fuente de verdad estructurada; los archivos `.keras` son artefactos físicos separados.

## 8. Estado de cierre y límites

**Acreditado para A–D:** dataset y materialización oficiales, población VAL de 2.693 imágenes idéntica por identificador y etiqueta, checkpoint lógico seleccionado, evaluación VAL final, métricas clínicas, 10.772 predicciones individuales y reconstrucción exacta de las cuatro matrices de confusión.

**No acreditado por estas consultas:** evaluación TEST independiente para A–D; integridad física actual de todos los `.keras`; consumo exacto de cada imagen durante TRAIN; inferencia nueva sobre checkpoints; consenso/oracle ya calculados; XAI/embeddings/CKA; equivalencia estadística o generalización clínica.

**Cierre recomendado:** usar estos SQL como evidencia de disponibilidad para SCC-PRE, SCC-TRAIN.1, SCC-MET.1 y SCC-ERR.1, manteniendo advertencias científicas y sin modificar la base de datos.
