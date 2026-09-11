# E6: EVALUATE y EXPLAIN con identidad exacta

Estado de entrega: implementación local; integración PostgreSQL e instalación **NO VERIFICADAS**. No ejecutar campañas científicas para validar esta etapa. E7 y publicación siguen fuera del alcance.

## Contrato y compatibilidad

`python -m src.evaluate` y `python -m src.explain` delegan en `src.malaria_dl.assessment.cli`. Los dos masivos delegan en ese mismo CLI con `campaign_id` obligatorio. Los argumentos legacy que implicaban TEST, selección de todas las ejecuciones de un dataset, `--track-db` opcional, `--checkpoint`, `--output-dir`, `--method all/both` o sidecars dejan de ser contratos ejecutables. No se traducen por suposición.

Los helpers matemáticos y las consultas históricas siguen disponibles. Los builders de comandos ahora requieren `split`, `purpose`, `protocol` y `seed`; sus consumidores y pruebas se actualizaron. `write_summary` rechaza CSV. Los parsers legacy conservados para importación no gobiernan el nuevo `main`.

La consulta de inventario histórico devuelve todas las versiones y marca la ambigüedad; no elige por fecha. No constituye un ejecutor alternativo por dataset.

La constraint histórica `uq_run_lineage_single_evaluation_training_parent` afecta al **hijo**, no limita el número de EVALUATE distintos por TRAIN. Se conserva. E6 usa un registro separado con FK al TRAIN y la identidad completa. No inserta versiones ni reasigna eventos históricos por aproximación.

Para E5, la versión es el `version_id` ya registrado en el artefacto seleccionado por la verificación del TRAIN. Como E5 no creó una fila en `artifacts` para ese registro, E6 identifica el artefacto mediante UUIDv5(namespace=`version_id`, name=`e5-selected-checkpoint`). Conserva la referencia a `train_execution_records`, su hash y el epoch seleccionado. Ese identificador se persiste dentro de la identidad E6; **no** se presenta como una fila histórica de `model_versions` o `artifacts`.

Un histórico requiere versión inequívoca, artefacto registrado del mismo TRAIN, ruta/hash/tamaño concordantes, snapshot E1 y contrato E3 original completo. Un histórico incompleto sigue consultable pero no inicia una nueva evaluación gobernada. El umbral `clinical` sólo consume la evidencia E5 acreditada de validación; no importa automáticamente calibraciones de archivos históricos.

## Uso explícito

Los ejemplos son plantillas, no instrucciones para realizar una evaluación científica durante E6. Sustituir identificadores únicamente dentro de un protocolo autorizado.

Inspección de campaña sin inferencia ni escritura de auditoría:

```sh
docker compose exec -T -w /app/malaria_dl_local_project backend \
  python -B run_evaluate_all_trainings.py --campaign-id "$CAMPAIGN_ID" --inspect
```

La inspección informa todos los miembros, su estado y la acreditación del TRAIN aceptado. La verificación E1 del dataset se realiza al preparar la ejecución; `eligible` en este inventario no es un dictamen científico ni sustituye ese preflight.

Protocolo mínimo de desarrollo, entregado como argumento JSON (configuración, no archivo de resultados):

```json
{"version":"development_val_v1","purposes":["development"],"splits":["val"],"allowed_numeric_thresholds":[0.5]}
```

Plantilla individual:

```sh
docker compose exec -T -w /app/malaria_dl_local_project backend python -B -m src.evaluate \
  --source-training-run-id "$TRAIN_ID" --model-version-id "$MODEL_VERSION_ID" \
  --purpose development --split val --threshold 0.5 --seed 42 --batch-size 64 \
  --protocol '{"version":"development_val_v1","purposes":["development"],"splits":["val"],"allowed_numeric_thresholds":[0.5]}'
```

El override `--dataset-version-id` sólo comprueba igualdad con la herencia; no cambia el dataset. No se acepta override de carpeta ni normalización por nombre. El contrato completo de entrada puede comprobarse programáticamente con `input_override`; una discrepancia se rechaza.

Para un lote, usar `run_evaluate_all_trainings.py --campaign-id "$CAMPAIGN_ID"` con los mismos argumentos explícitos. `run_explain_all_trainings.py` añade el método. Sólo consume miembros aceptados y verificados; registra asociaciones `assessment_campaign_consumers`, conservando el origen de cada identidad. El código de salida es 2 si hay miembros no verificados o una operación falla.

EXPLAIN individual admite `--evaluation-id` (UUID de **intento E6**, no UUID legacy de runs). Exige una evaluación verificada del mismo modelo, dataset, conjunto de muestras, propósito, protocolo y decisión. Sin ese argumento es EXPLAIN independiente, explícitamente sin evaluación padre.

- Grad-CAM: `--method gradcam --layer NOMBRE_EXACTO --class-id 1`. No acepta `--num-samples`, pues el algoritmo no lo consume.
- LIME: `--method lime --num-samples 200 --class-id 1`; el número corresponde a perturbaciones por imagen.
- SHAP: `--method shap --num-samples 200 --class-id 1 --background-sample-id UUID ...`. Usa GradientExplainer; las referencias deben pertenecer al TRAIN split acreditado y forman parte de la identidad.

Se explica el **score bruto**, también cuando el contexto conserva un umbral clínico. No se declara probabilidad calibrada ni se ajusta un calibrador. E5 proporciona calibración de umbral sobre validación, no un transformador de probabilidades. Los transformadores de score distintos no se aceptan silenciosamente.

## Identidad, persistencia y recuperación

La identidad incluye TRAIN, versión, artefacto, hash/tamaño/ruta acreditada, contrato E3, snapshot E1, muestras y pacientes pseudónimos, propósito/partición, decisión, protocolo, definición de métricas, código/paquetes, semilla y batch size. EXPLAIN añade método, capa, clase, parámetros, background y evaluación exacta si existe. No incluye owner, tiempo de petición ni UUID del intento actual.

`assessment_identities` conserva JSON y serialización canónica, con hash Python validado en SQL. Un segundo hash estructural SQL normaliza representaciones numéricas equivalentes para impedir identidades duplicadas por otra escritura de JSON. La representación SQL no se confunde con la serialización Python (p. ej., notación exponencial).

La reserva bloquea la identidad y aplica unicidad parcial para estados `active`/`verified`. Una identidad activa devuelve su referencia; no reclama su propietario. Una verificada sólo se reutiliza tras reconstruir conteos, métricas, hash y referencias de artefactos. Las predicciones tienen PK `(attempt_id,sample_id)`; repetir un lote idéntico es idempotente, un duplicado contradictorio falla.

Los conteos esperados están en las muestras de la identidad; escritos en `assessment_results`; verificados y métricas en `assessment_attempts.verification`. Métricas `binary_counts_rates_v1`: TN/FP/FN/TP, matriz, accuracy, precision, recall, specificity y F2; denominadores cero producen null. No se añaden métricas inferidas de CSV.

No se mantiene una transacción durante la inferencia. Los mapas NPY y overlays PNG se escriben en un directorio UUID exclusivo de intento, mediante archivo temporal exclusivo, fsync y enlace final que no sobreescribe destinos. Se registran UUID, hash, tamaño, muestra, rol y estado. La comparación final comprueba contenido y pertenencia al directorio.

Un fallo conserva resultados y archivos parciales. Un reintento usa otro UUID/directorio y recalcula la partición completa: no concatena lotes de intentos distintos. Si falla también el registro del estado de fallo, se conserva la excepción primaria y la nota `ASSESSMENT_FAILURE_STATE_UNCONFIRMED`; no hay fallback.

```sh
docker compose exec -T -w /app/malaria_dl_local_project backend \
  python -B -m src.evaluate --recover-attempt-id "$ATTEMPT_ID"
```

La recuperación sólo marca `interrupted` si el proceso propietario está ausente en el mismo host. Host distinto, PID vivo/reutilizado o permisos insuficientes producen rechazo; no se supone muerte por tiempo transcurrido. Después se repite la petición completa para crear otro intento. No borra archivos huérfanos ni recupera por `latest`. No acredita tolerancia a pérdida física del host, ni certeza ante pérdida de respuesta de commit.

TEST requiere `purpose=final`, protocolo compatible y una fila previa exacta en `assessment_final_locks` que vincule hash de identidad, candidato/checkpoint y decisión. E6 **no** ofrece CLI/API para crear ese bloqueo; su gestión corresponde a E7. La prueba positiva sólo inserta un fixture sintético. Leer hashes de TEST durante E1 no autoriza predict sobre TEST.

## API e históricos

Nuevas lecturas explícitas, todas con transacción READ ONLY:

- `GET /assessments?training_run_id=UUID&campaign_id=UUID&limit=50&offset=0`.
- `GET /assessments/{attempt_id}`: identidad, estado, causa, verificación.
- `GET /assessments/{attempt_id}/results?limit=100&offset=0`.
- `GET /assessments/{attempt_id}/artifacts?limit=100&offset=0`.

Los filtros TRAIN/campaña se combinan; el segundo se basa en asociaciones explícitas, no en compartir dataset. Los resultados se ordenan por UUID y ordinal, sin seleccionar el más reciente.

`/runs`, `/predictions`, `/explainability` y las pantallas históricas mantienen su semántica. E6 no fabrica `runs` legacy ni añade mapas E6 al endpoint de regeneración de Grad-CAM de casos históricos. El frontend actual conserva la consulta histórica; la consulta E6 se entrega por estos endpoints, sin rediseño de interfaz ni publicación.

## Validación operativa pendiente (desde raíz Capstone)

Primero ejecutar sólo el esquema sintético. El fixture compartido con E4 usa rollback externo; las pruebas de concurrencia/lectura posterior hacen commit **del esquema sintético** y comprueban su eliminación desde otra conexión. Las tablas padre simplificadas no acreditan todas las constraints de `public`.

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE6_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_assessment_postgres.py -k 'not public_e6_revision_readonly'
```

Sólo después de que esa integración pase, seguir el procedimiento de migración del proyecto. La generación offline es una revisión del DDL, no una prueba de PostgreSQL:

```sh
make db-migrate-check
docker compose exec -T backend python -m alembic upgrade 20260912_01:20260912_02 --sql
make db-migrate
```

`make db-migrate` debe conservar backup custom validado, preflight transaccional, rollback confirmado y upgrade real. No sustituirlo por un upgrade directo. Si el head o current difieren de los esperados, resolver la divergencia antes de aplicar; no reescribir migraciones instaladas.

Finalmente:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE6_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider tests/test_assessment_postgres.py
curl --fail --silent --show-error http://localhost:8000/ready
```

No atribuir el `/ready` ni las 14 pruebas del cierre E5 a esta revisión nueva. No aprobar E6 hasta disponer de resultados reales y resolver cualquier fallo crítico.
