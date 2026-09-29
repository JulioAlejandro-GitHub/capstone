# Revisión de base de datos — malaria_experiments

PostgreSQL 17.9 · dump del 28-09-2026 · 111 MB

---

## 1. Alcance y método

El archivo es un dump en formato **custom** (`pg_dump -Fc`, cabecera v1.16). El
`pg_restore` disponible en este entorno es la versión 16 y rechaza ese formato,
así que **no pude leer los datos**: ni conteos de filas, ni tamaños reales por
tabla, ni estadísticas de uso.

Lo que sí extraje íntegro es el esquema, desde el TOC del propio dump:

| | |
|---|---|
| Tablas | 97 |
| Índices | 228 (38 únicos, 222 btree, 6 GIN) |
| Claves foráneas | 208 |
| Restricciones CHECK | 416 |
| Triggers | 77 |
| Funciones | 65 |
| Vistas | 26 |
| Columnas JSONB | 223, repartidas en 72 tablas |
| Extensiones | pgcrypto |

Todo lo que sigue se apoya en ese esquema y en el cruce con el código del
repositorio. Las decisiones que dependen de datos reales —qué índices no se usan
nunca, dónde hay bloat, qué tablas pesan— quedan en la sección 7 como consultas
para ejecutar sobre la base viva.

---

## 2. El hallazgo estructural: dos bases conviviendo en una

Es lo primero que salta y condiciona todo lo demás. La base contiene **dos
esquemas de dominios distintos, gobernados por dos sistemas de migración que no
se conocen entre sí**:

```
alembic_version      -> migraciones del backend clínico (backend_api/alembic)
schema_migrations    -> migraciones del proyecto ML  (malaria_dl_local_project/db/init)
```

Las dos tablas de control coexisten. Nadie tiene una vista completa del esquema,
y una migración de un lado puede romper al otro sin que ningún test lo note.

La evidencia más clara es que hay **dos tablas de predicciones**:

- `predictions` (39 columnas) — del proyecto ML, predicciones de evaluación
- `cell_predictions` (22 columnas) — del backend clínico, predicciones por célula

Y una vista llamada `legacy_cell_predictions`, residuo de cuando se renombró la
tabla del lado ML para liberar el nombre. La cicatriz de una colisión de nombres
ya ocurrida.

**Recomendación.** No fusionar los dominios: separarlos formalmente en dos
esquemas de PostgreSQL (`clinical` y `ml`), con `search_path` explícito por
aplicación. Es un cambio de una migración por lado y elimina de raíz la
posibilidad de colisión. Si eso es demasiado para el plazo de la defensa, el
mínimo aceptable es documentar qué tabla pertenece a qué sistema y prohibir por
convención que un lado escriba en tablas del otro.

---

## 3. ELIMINAR

### 3.1 Seis tablas sin una sola referencia en el código

Busqué cada nombre de tabla en `backend_api/app`, en `alembic/` y en
`malaria_dl_local_project/`. Estas seis no aparecen en ninguno:

```
campaign_controlled_requests
campaign_technical_revisions
experiment_execution_events
experiment_execution_gate
local_execution_jobs
train_execution_revisions
```

Cuatro de ellas tienen triggers y restricciones asociadas, lo que sugiere que
fueron diseñadas con cuidado y luego abandonadas al cambiar el enfoque. Son
esquema muerto que aparece en cada `\dt`, en cada diagrama y en cada revisión.

**Antes de borrar**, comprueba que están vacías:

```sql
SELECT relname, n_live_tup
FROM pg_stat_user_tables
WHERE relname IN ('campaign_controlled_requests','campaign_technical_revisions',
                  'experiment_execution_events','experiment_execution_gate',
                  'local_execution_jobs','train_execution_revisions')
ORDER BY n_live_tup DESC;
```

Si alguna tiene filas, no la borres: significa que algo escribió en ella por una
vía que mi búsqueda no cubre. Si están todas a cero, van en una migración del
sistema que las creó, con su `downgrade` correspondiente.

### 3.2 Cuatro índices redundantes por prefijo

Cada uno de estos está completamente contenido en otro índice más ancho de la
misma tabla. El planificador puede usar el ancho para las consultas del
estrecho, así que el estrecho solo cuesta: espacio y escrituras.

| Sobra | Porque ya existe |
|---|---|
| `idx_artifacts_artifact_type (artifact_type)` | `idx_artifacts_type_path (artifact_type, path)` |
| `idx_predictions_case_type (case_type)` | `idx_predictions_case_type_run (case_type, run_id)` |
| `idx_runs_run_type (run_type)` | `idx_runs_inference_script (run_type, script_name)` |
| `idx_training_history_run_id (run_id)` | `idx_training_history_run_phase_epoch (run_id, phase, epoch)` |

```sql
DROP INDEX CONCURRENTLY idx_artifacts_artifact_type;
DROP INDEX CONCURRENTLY idx_predictions_case_type;
DROP INDEX CONCURRENTLY idx_runs_run_type;
DROP INDEX CONCURRENTLY idx_training_history_run_id;
```

### 3.3 Candidatos que necesitan confirmación antes de tocar

- **`legacy_cell_predictions`**: por nombre y por origen es residuo de la
  migración de nombres. Confirma con la consulta de vistas de la sección 7 que
  nada la consulta.
- **Las 26 vistas `vw_*`**: son muchas para una aplicación de este tamaño y
  varias parecen del mismo dominio (`vw_explainability_summary`,
  `vw_explainability_gallery`, `vw_explainability_lineage`,
  `vw_case_level_explainability`). No las borro a ciegas: algunas alimentan
  pantallas de Modelo IA. La sección 7 trae la consulta para saber cuáles no
  usa nadie.
- **Ocho tablas que solo existen del lado ML** y no aparecen en el backend ni en
  alembic: `dataset_splits`, `environment_packages`,
  `model_governance_backfill_audit`, `run_checkpoint_policy`,
  `run_dataset_images`, `stage2_model_publication_events`,
  `synthetic_data_runs`, `schema_migrations`. No son huérfanas —el pipeline de
  entrenamiento las usa— pero conviene saber que la aplicación clínica nunca las
  toca. Si se separan los esquemas, estas van claramente al lado `ml`.

---

## 4. MEJORAR

### 4.1 El problema de rendimiento real: 79 claves foráneas sin índice

Es, con diferencia, el hallazgo más importante de esta revisión.

De las 208 claves foráneas, **79 no tienen ningún índice cuya primera columna
sea la primera columna de la FK**. Y de esas 79, **60 están declaradas
`ON DELETE RESTRICT`**.

Por qué importa: PostgreSQL no indexa automáticamente el lado hijo de una clave
foránea. Cada vez que se borra o actualiza una fila del padre, el motor tiene que
verificar que no queden hijos. Sin índice, esa verificación es un **recorrido
secuencial completo de la tabla hija**, dentro de la transacción y manteniendo
bloqueos.

Hoy no se nota porque las tablas están pequeñas. Con volumen real —y un proyecto
de imágenes médicas crece rápido— se manifiesta como borrados que tardan
segundos y bloquean a todos los demás.

Las tablas más afectadas:

| Tabla | FK sin índice |
|---|---|
| `scientific_validation_annotations` | 5 |
| `predictions` | 4 |
| `image_ingestion_batches` | 4 |
| `microscopy_analysis_runs` | 4 |
| `blood_samples` | 3 |
| `cell_classification_runs` | 3 |
| `microscopy_images` | 3 |
| `research_subjects` | 3 |
| `scientific_cases` | 3 |
| `smear_slides` | 3 |

Un caso concreto para ver la forma del problema. `microscopy_analysis_runs`
tiene seis claves foráneas —`case_id`, `ingestion_batch_id`, `requested_by`,
`sample_id`, `slide_id`, `subject_id`— y solo dos índices, sobre `run_status` y
sobre `subject_id`. Borrar un usuario, una muestra o un portaobjetos recorre la
tabla entera.

**Cómo abordarlo.** No crees los 79 de golpe: cada índice cuesta espacio y
penaliza las escrituras. El orden sensato:

1. Primero los que apuntan a tablas de las que **sí se borra** en la práctica.
   Las que apuntan a `users` probablemente nunca ejerzan el RESTRICT, porque los
   usuarios no se borran.
2. Después los que además sirvan a consultas de lectura que ya existen.
3. El resto, solo si la medición lo justifica.

Consulta para generar los `CREATE INDEX` de forma sistemática, ya filtrada por
FK sin cobertura:

```sql
SELECT 'CREATE INDEX CONCURRENTLY ix_' || c.conrelid::regclass::text || '_' ||
       a.attname || ' ON ' || c.conrelid::regclass || ' (' || a.attname || ');'
FROM pg_constraint c
JOIN LATERAL unnest(c.conkey[1:1]) k(attnum) ON true
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
WHERE c.contype = 'f'
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    WHERE i.indrelid = c.conrelid AND i.indkey[0] = k.attnum
  )
ORDER BY 1;
```

Usa siempre `CONCURRENTLY`: sin eso, cada `CREATE INDEX` bloquea escrituras en
la tabla.

### 4.2 223 columnas JSONB con solo 6 índices GIN

Los seis GIN existentes cubren `runs` (tres), `run_io_records` (dos) y
`datasets` (uno). Las otras 217 columnas JSONB no tienen ninguno.

Eso **no** es automáticamente un problema: un JSONB que solo se lee entero, como
`profile_snapshot` o `model_snapshot`, no necesita índice y no debe tenerlo.
Pero sí lo es cuando se filtra por una clave interna. En el código del backend
hay al menos un caso claro:

```sql
d.metadata->>'production_scope' = :production_scope
```

en la resolución del modelo productivo, sobre `deployed_model_versions`. Si esa
tabla crece, conviene un índice de expresión sobre esa clave concreta —no un GIN
sobre todo el documento:

```sql
CREATE INDEX CONCURRENTLY ix_deployed_model_versions_scope
  ON deployed_model_versions ((metadata->>'production_scope'));
```

La regla general: GIN cuando se consulta el documento con operadores de
contención (`@>`); índice de expresión cuando siempre se filtra por la misma
clave. Ir a GIN por defecto sobre 217 columnas sería peor que no tener ninguno.

### 4.3 `runs`: 56 columnas, 26 de ellas `text` sin límite

Es la tabla más ancha de la base y el punto de encuentro de todo el pipeline de
entrenamiento. 56 columnas, de las cuales 26 son `text` libre y 10 son `jsonb`.

No propongo partirla antes de la defensa: es cirugía mayor y el beneficio real
depende de patrones de acceso que no puedo medir desde el dump. Pero conviene
saber que es la candidata número uno si aparecen problemas de rendimiento, y que
26 columnas de texto sin restricción de dominio son 26 sitios donde puede
entrar un valor que nadie espera.

Contraste útil: las tablas del lado clínico —`microscopy_images` con 25
`varchar`, `image_quality_assessments` con 13— sí usan longitudes acotadas y
`CHECK`. El lado ML es más laxo. Si en algún momento se unifica el criterio,
esta es la dirección correcta.

### 4.4 Las acciones `ON DELETE` no siguen un criterio único

```
RESTRICT               154
NO ACTION (por defecto) 25
CASCADE                 20
SET NULL                 9
```

`RESTRICT` domina, y es la elección correcta para un sistema auditable: nada
desaparece por arrastre. Pero conviven con 25 FK que quedaron en `NO ACTION` por
omisión, no por decisión. `NO ACTION` y `RESTRICT` se comportan casi igual, con
una diferencia sutil —`NO ACTION` permite diferir la comprobación al final de la
transacción— que casi seguro no se eligió a propósito.

Revisa esas 25 y hazlas explícitas. En un proyecto que defiende su trazabilidad,
que la integridad referencial dependa de un valor por defecto es difícil de
sostener ante una pregunta del jurado.

### 4.5 Dependencias sin fijar

No es del esquema, pero afecta directamente a la reproducibilidad de la base:
`backend_api/requirements.txt` fija rangos (`fastapi>=0.115.0,<1.0`,
`SQLAlchemy>=2.0.0,<3.0`, `alembic>=1.14.0,<2.0`). Cualquier versión nueva entra
sola en CI. Hoy eso ya tiene el job `backend-unit` en rojo con 34 errores de
recolección, sin que ningún commit del backend lo haya causado.

Para un trabajo que se defiende por su reproducibilidad, fijar versiones exactas
es parte del argumento, no un detalle de mantenimiento.

---

## 5. MANTENER

Esta sección importa tanto como las anteriores. Hay decisiones en este esquema
que son buenas y que conviene defender explícitamente, no tocar por afán de
simplificar.

### 5.1 Las 416 restricciones CHECK

No son validación redundante: codifican **máquinas de estado** en la propia base.
El patrón se ve con claridad en `cell_detection_runs`:

```sql
CONSTRAINT ck_cell_detection_run_terminal_state CHECK (
  (status='created'    AND started_at IS NULL AND completed_at IS NULL AND failed_at IS NULL ...)
  OR (status='processing' AND started_at IS NOT NULL AND completed_at IS NULL ...)
  OR (status IN ('completed','completed_with_warnings') AND started_at IS NOT NULL AND completed_at IS NOT NULL ...)
  OR (status='failed'  AND started_at IS NOT NULL AND failed_at IS NOT NULL AND error_code IS NOT NULL)
)
```

Eso hace **imposible** que exista en la base una ejecución completada sin fecha
de finalización, o fallida sin código de error. Ningún bug de aplicación puede
producir ese estado. Es exactamente lo que se espera de un sistema de apoyo
diagnóstico, y es un argumento fuerte para la defensa.

### 5.2 Los 77 triggers de inmutabilidad

Funciones como `assessment_attempt_guard()` impiden borrar historial
(`ASSESSMENT_HISTORY_IMMUTABLE`), verifican propiedad mediante
`current_setting('capstone.assessment_owner')` y restringen qué columnas puede
modificar una actualización comparando `to_jsonb(NEW)` contra `to_jsonb(OLD)`
campo por campo.

Es control de concurrencia y de inmutabilidad hecho en el sitio correcto: la
base, no la aplicación. Una aplicación se puede saltar; un trigger no.

### 5.3 Los índices únicos parciales

El patrón que se repite —y que está bien— es:

```sql
CREATE UNIQUE INDEX uq_cell_detection_runs_equivalent_active
  ON cell_detection_runs (analysis_run_id, detector_key, detector_version,
                          algorithm_version, input_manifest_sha256)
  WHERE status IN ('created','processing','completed','completed_with_warnings');
```

Garantiza idempotencia —no se puede lanzar dos veces la misma detección sobre la
misma entrada— pero deja fuera las ejecuciones fallidas, de modo que un fallo no
bloquea el reintento. Es una solución elegante a un problema real, y explica por
qué el flujo del frontend puede reintentar sin duplicar.

### 5.4 Los snapshots JSONB congelados

`profile_snapshot` en las ejecuciones de detección, `model_snapshot` en las de
clasificación, `preprocessing_profile_snapshot` y `threshold_profile_snapshot`
en los despliegues.

Son la columna vertebral de la auditabilidad: cada ejecución guarda el contrato
exacto con el que se ejecutó, de modo que puede reinterpretarse años después
aunque el código haya cambiado. No los normalices ni los sustituyas por claves
foráneas a tablas de configuración: perderías justo la propiedad que los hace
valiosos.

Es, además, la razón por la que el fallo del contrato de entrada se pudo
diagnosticar con precisión: el snapshot decía exactamente qué faltaba.

### 5.5 `pgcrypto`

Única extensión instalada, y con uso justificado. Mantener.

---

## 6. Resumen de acciones

| Prioridad | Acción | Riesgo | Impacto |
|---|---|---|---|
| 1 | Fijar versiones exactas en `requirements.txt` | Nulo | Desbloquea CI |
| 2 | Indexar las FK `RESTRICT` sobre tablas de las que se borra | Bajo | Alto en rendimiento |
| 3 | Borrar los 4 índices redundantes | Nulo | Menos escrituras |
| 4 | Borrar las 6 tablas huérfanas, tras confirmar que están vacías | Bajo | Claridad |
| 5 | Hacer explícitas las 25 `ON DELETE` por defecto | Bajo | Coherencia |
| 6 | Índice de expresión sobre `metadata->>'production_scope'` | Nulo | Puntual |
| 7 | Auditar y podar las 26 vistas `vw_*` | Medio | Claridad |
| 8 | Separar en esquemas `clinical` y `ml` | Alto | Estructural |

Del 1 al 6 son de bajo riesgo y caben antes de la defensa. El 7 requiere medir
primero. El 8 es una decisión de arquitectura que no haría con la fecha encima.

---

## 7. Lo que falta medir sobre la base viva

Estas cuatro consultas cubren todo lo que el dump no me deja ver. Con sus
salidas puedo cerrar las decisiones que aquí quedaron condicionadas.

**Tamaño y filas por tabla** — para saber dónde están los 111 MB:

```sql
SELECT relname,
       n_live_tup AS filas,
       pg_size_pretty(pg_total_relation_size(relid)) AS total,
       pg_size_pretty(pg_indexes_size(relid))        AS indices
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 30;
```

**Índices que nunca se han usado** — el criterio real para podar:

```sql
SELECT s.relname AS tabla, s.indexrelname AS indice, s.idx_scan AS lecturas,
       pg_size_pretty(pg_relation_size(s.indexrelid)) AS tamano
FROM pg_stat_user_indexes s
JOIN pg_index i ON i.indexrelid = s.indexrelid
WHERE NOT i.indisunique AND NOT i.indisprimary
ORDER BY s.idx_scan, pg_relation_size(s.indexrelid) DESC;
```

Ojo: `idx_scan` cuenta desde el último `pg_stat_reset()`. Si la base se recreó
hace poco, los ceros no significan nada todavía.

**Recorridos secuenciales sobre tablas grandes** — confirma el diagnóstico 4.1:

```sql
SELECT relname, seq_scan, seq_tup_read, idx_scan, n_live_tup
FROM pg_stat_user_tables
WHERE seq_scan > 0 AND n_live_tup > 1000
ORDER BY seq_tup_read DESC
LIMIT 20;
```

**Vistas sin uso** — necesita `pg_stat_statements` activo:

```sql
SELECT viewname
FROM pg_views v
WHERE schemaname = 'public'
  AND NOT EXISTS (
    SELECT 1 FROM pg_stat_statements q
    WHERE q.query ILIKE '%' || v.viewname || '%'
  )
ORDER BY viewname;
```
