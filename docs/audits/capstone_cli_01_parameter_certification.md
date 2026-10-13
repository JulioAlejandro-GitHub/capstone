# CAPSTONE-CLI-01 — Certificación de parámetros científicos

Estado documental: `CURRENT_DOC`. Fecha: 2026-10-13.
Base revisada: `a087104`. Estado final: **CERTIFICADO mediante mocks y fixtures sintéticos**, con los límites de la sección 12.

## 1. Objetivo, alcance y estado previo

Consolidar TRAIN, EVALUATE, EXPLAIN y TEST en cuatro módulos públicos; retirar los
cuatro ejecutores `run_*`, sin alterar protocolos científicos, campañas, checkpoints,
resultados históricos, esquema PostgreSQL, activación productiva ni frontend.

**VERIFICADO por lectura antes de editar:** `execution/operations.py` ya creaba
TRAIN nuevos desde configuraciones de campaña o de un TRAIN de referencia;
`execution/selection.py` compartía selección entre operaciones. La condición de
campaña se comprobaba separadamente cuando se proporcionaban ambos IDs.
`assessment/service.py::run()` ya añadía un UUID nuevo, reservaba identidad y
recorría `value["samples"]`; verificación y persistencia exigían la población declarada.

Los parsers aún exponían dataset/modelo/rutas redundantes, seed=42 y batch=64.
EXPLAIN exigía método y capa; aceptaba cualquier `num_samples > 0`. LIME pasaba ese
valor a `explain_instance`, SHAP a `shap_values(nsamples=...)`. No había selección
parcial o individual. El incidente de LIME con `--num-samples 1` corresponde a una
perturbación interna, no a una imagen. No se reabrió el problema anterior de rechazo
de parámetros ni se intentó reproducir sobre datos operativos la ejecución interrumpida.

## 2. Inventario y matriz pública definitiva

Directorio de invocación: `malaria_dl_local_project`; Python 3.12 del entorno del
proyecto. PostgreSQL y control plane siguen en Docker; execution plane local se conserva.

| Parámetro | TRAIN | EVALUATE | EXPLAIN | TEST |
|---|:---:|:---:|:---:|:---:|
| `--campaign-id` | Sí | Sí | Sí | Sí |
| `--source-training-run-id` | Sí | Sí | Sí | Sí |
| `--inspect` | Sí | Sí | Sí | Sí |
| `--plan` | Sí | — | — | — |
| `--dry-run` | Sí | — | — | — |
| `--threshold` | — | Sí | Sí | Sí |
| `--seed` | — | Sí | Sí | Sí |
| `--batch-size` | — | Sí | Sí | Sí |
| `--method` | — | — | Sí | — |
| `--layer` | — | — | Sí | — |
| `--class-id` | — | — | Sí | — |
| `--num-samples` | — | — | Sí | — |
| `--max-images` | — | — | Sí | — |
| `--sample-id` | — | — | Sí | — |
| `--background-sample-id` | — | — | Sí | — |

`--help`/`-h` son opciones estándar. Se deshabilitaron abreviaciones de argumentos
para que `--model` o prefijos parciales no se acepten accidentalmente.

## 3. Selección de campaña y TRAIN

Al menos uno de los dos IDs es obligatorio. Ambos se normalizan como UUID.

- TRAIN solo campaña: recorre los miembros y configuraciones persistidos mediante
  `CampaignRepository.get`; conserva cada semilla y la selección vigente de EXEC.1.
- TRAIN por referencia: recupera configuración completa y dataset del TRAIN indicado;
  `ExecutionRepository.standalone` genera UUID y directorio nuevos. Registra origen y
  campaña sin actualizar el RUN de referencia ni reabrir miembros históricos.
- EVALUATE/EXPLAIN/TEST por campaña: seleccionan todos los TRAIN asociados, incluidos
  vínculos de `campaign_attempts` → `campaign_members`; no usan «latest» ni `LIMIT 1`.
- Ambos IDs: la misma consulta aplica `r.id=:train` y pertenencia a `:campaign` por
  `runs.campaign_id` o relación de intentos/miembros. Ningún filtro se ignora.
- Orden estable: `ORDER BY r.started_at,r.id`. No se elige arbitrariamente un TRAIN.
- Errores explícitos: `CAMPAIGN_NOT_FOUND`, `CAMPAIGN_HAS_NO_TRAININGS`,
  `SOURCE_TRAINING_RUN_NOT_FOUND`, `SOURCE_TRAINING_RUN_CAMPAIGN_SELECTION_EMPTY`.
  Para TRAIN sin miembros: `CAMPAIGN_CONFIGURATION_UNAVAILABLE`.

El procesamiento de varios TRAIN conserva el comportamiento existente: registra
resultado o error por elemento y devuelve código 2 si alguno falla. No se cambió la
orquestación científica ni se recuperaron builders legacy de matrices modelo×optimizador.

## 4. Defaults, validación y resolución automática

| Opción | Default / comportamiento |
|---|---|
| `--threshold` | `auto`: evidencia persistida del TRAIN, umbral fijo o calibración VAL del checkpoint seleccionado |
| `--threshold clinical` | Calibración VAL válida del linaje; ausencia produce `CLINICAL_THRESHOLD_EVIDENCE_REQUIRED`; no ajusta calibración |
| `--threshold número` | Probabilidad explícita [0,1], finita, incorporada al protocolo y decisión efectiva |
| `--seed` | `auto`: `resolved.execution.seed` persistida; entero explícito prevalece, incluido cero |
| `--batch-size` | Entero positivo explícito; si falta, perfil de operación → perfil `inference` → `resolved.execution.batch_size` persistido |
| `--inspect` | Prepara y muestra selección/configuración, sin `run`, reserva ni global gate escritor |
| TRAIN `--plan`, `--dry-run` | Misma inspección de configuración; no entrena |

**VERIFICADO:** las configuraciones actuales de Custom CNN, VGG16 y DenseNet121 no
contienen un perfil separado de inferencia/explicación. Se eliminó el 64 universal
del parser; el respaldo mínimo es el batch persistido del TRAIN. No se impone 200
ni se interpreta seed como threshold. Configuración automática ausente o inválida
falla explícitamente, sin reconstruir un default desde el entorno actual.

`assessment.lineage.resolve` conserva la verificación del checkpoint seleccionado,
contrato de entrada, SHA-256 y dataset heredado. La configuración se recupera de
`runs.execution_parameters.model_configuration_e2.configuration`. Rutas de dataset
se resuelven con el mecanismo Docker/macOS existente. Las raíces internas de salida
se conservan: `outputs/train_runs` y `artifacts/assessments`, con subdirectorios por
UUID; ya no son argumentos públicos.

EVALUATE y EXPLAIN usan `val`/`development` (VALIDATION). TEST usa únicamente
`test`/`final`, hereda checkpoint y no requiere EVALUATE, EXPLAIN ni locks finales.
La inspección TEST verifica metadatos de muestras sin abrir sus imágenes. Se mantiene
la inspección física VAL existente. La capa automática de Grad-CAM figura como
`null` en la especificación hasta resolver el grafo durante ejecución; su nombre
concreto queda en el resultado de cada explicación.

## 5. Parámetros eliminados

TRAIN: `--dataset-version-id`, `--artifact-root`.

EVALUATE/TEST: `--model-version-id`, `--dataset-version-id`, `--model`,
`--dataset-dir`, `--artifact-root`.

EXPLAIN: los mismos, además de `--evaluation-id`. No se incorporan wrappers,
traducciones de flags antiguos ni aliases de los ejecutores eliminados.

## 6. Grad-CAM, LIME y SHAP

| Método | Default `num-samples` | Rango | Otros parámetros |
|---|---|---|---|
| Grad-CAM (default) | No aplica | Se rechaza si se proporciona | Clase 1 por defecto; clase 0/1; capa explícita o automática |
| LIME | 1000 | Entero 1000–5000 | Perturbaciones del modelo explicativo local |
| SHAP | 1000 | Entero 1000–5000 | Muestras internas del estimador; background explícito obligatorio |

**IMPLEMENTADO / PROBADO:** validación CLI antes de bootstrap, gate o reserva y
validación del contrato en `explanation_spec`. 999, 5001, fracciones y `num-samples`
en Grad-CAM se rechazan. No se utiliza para contar imágenes. No se añadieron otras
restricciones científicas al rango acordado. La regresión LIME/SHAP usa 1000 y convierte
`UndefinedMetricWarning` en error de prueba.

Grad-CAM reutiliza sin cambios `compute_gradcam_artifacts` y `find_last_conv_layer`.
Se probaron los grafos Custom CNN, VGG16 y DenseNet121 con pesos aleatorios, sin
predicción ni entrenamiento: existe una salida espacial conectada de rango 4. En
DenseNet121 anidado, el resolver existente utiliza el backbone convolucional conectado
como fallback; no se cambió la matemática para exigir un `Conv2D` interno desconectado.
La capa explícita y clase 0/1 conservan su semántica; clase 0 invierte la salida escalar.

SHAP conserva referencias explícitas, únicas y acreditadas dentro del mismo split y
dataset autorizado. `--background-sample-id` puede repetirse, como en el contrato
previo, para declarar varias referencias; no se selecciona background automáticamente.

## 7. Objetivos, límites y referencia

| Parámetro | Significado |
|---|---|
| `--num-samples` | Trabajo interno LIME/SHAP; no selecciona células |
| `--max-images N\|all` | Máximo de células objetivo; default `all` |
| `--sample-id UUID` | Exactamente una célula objetivo de VAL del linaje |
| `--background-sample-id UUID` | Referencia SHAP; no constituye un objetivo implícito |

`--max-images` exige entero positivo o `all`. El parser rechaza su combinación
explícita con `--sample-id`, incluso `--max-images all`. Un N superior a la población
procesa los disponibles. Una muestra inexistente o de otro split/dataset produce
`EXPLANATION_SAMPLE_SELECTION_EMPTY`.

La población elegible se acredita mediante `dataset_samples`, preservando conteos,
hashes y resolución de colisiones de nombres. Para objetivos parciales/individuales:

```sql
SELECT source_record_id
FROM dataset_split_assignments
WHERE dataset_version_id=CAST(:dataset AS uuid)
  AND split_name=:split
  AND (CAST(:sample AS uuid) IS NULL OR source_record_id=CAST(:sample AS uuid))
ORDER BY source_record_id
LIMIT :limit;
```

`source_record_id` es la columna real que se representa como `sample_id`. El conjunto
completo usa el orden SQL existente por `a.source_record_id`. No hay muestreo aleatorio,
`LIMIT` sin orden ni búsqueda en otros splits. La selección ocurre en `prepare`, antes
de `identity`, no mediante un slice tardío dentro de `run`.

El background se valida contra toda la población elegible antes de limitar los
objetivos: puede ser una célula distinta y quedar fuera del límite solicitado.

## 8. Persistencia e integridad

La identidad JSONB existente permite representar todos los datos sin DDL nuevo:

- `model`: TRAIN, versión, checkpoint, contrato de entrada y hashes.
- `dataset`, `split`, `purpose`, `decision`, `seed`, `batch_size`, `code`:
  procedencia y parámetros efectivos.
- `explanation`: método, clase, capa solicitada, muestras internas y background.
- `explanation.selection`: `eligible_count`, `requested_max_images`,
  `requested_sample_id`, `selected_count`, `sample_ids`.
- `samples`: identidades, pacientes, hashes y rutas de los objetivos seleccionados.
- `assessment_results` y `assessment_artifacts`: resultados y referencias binarias;
  `assessment_attempts`: estado y verificación, cuyo `count` confirma cuántas se procesaron.

Un intento parcial fallido conserva los resultados escritos y estado de fallo; no
se declara procesada toda la selección hasta verificarla. La verificación exige
exactamente las muestras y dos artefactos por objetivo. Cada invocación añade
`execution_id` nuevo y directorio independiente; las pruebas comparan el primer
intento intacto después de repetir la operación.

**VERIFICADO por lectura:** `assessment_identity_guard`, `assessment_result_guard`
y `assessment_attempt_guard` validan la población de `identity.samples` y la igualdad
de la especificación; no requieren nuevas columnas para selección parcial. Se
mantienen constraints, triggers, transacciones y hashes históricos. No hay guards
nuevos de esquema/Alembic. **NO EJECUTADO:** DDL, migraciones o escrituras operativas.

## 9. Retiro de ejecutores y consumidores

Archivos eliminados (ubicación real: `malaria_dl_local_project/`):

| Eliminado | Única entrada pública sustituta |
|---|---|
| `run_train_all_models.py` | `python -m src.train` |
| `run_evaluate_all_trainings.py` | `python -m src.evaluate` |
| `run_explain_all_trainings.py` | `python -m src.explain` |
| `run_test_all_models.py` | `python -m src.test` |

La lógica activa ya delegaba en `execution.operations` y `assessment.cli`. Los
builders de comandos y consultas legacy dentro de esos archivos solo tenían
consumidores de pruebas; no se trasladaron como compatibilidad. Se eliminaron
`tests/test_run_evaluate_all_trainings.py` y `tests/test_run_explain_all_trainings.py`;
se retiraron/adaptaron casos de builders en suites E1/E2/E3 y de launchers.

`campaigns.plan.execution_command` ahora devuelve `python -m src.train`. Se actualizó
su expectativa en pruebas API y campañas. El reconocimiento de procesos del global
gate usa los cuatro módulos y excluye ayuda/inspección/plan/dry-run.

**VERIFICADO por búsqueda:** backend, frontend, scripts, Docker, Makefile y workflows
no mantienen invocaciones ni importaciones operativas de esos archivos. Frontend no
requirió cambios. Permanecen nombres en informes históricos, pruebas de ausencia y
ejemplos de skills `.agents`/`.claude`; no son consumidores de Python ni scripts de
lanzamiento. Esas skills no se modificaron.

La guía inicial del README ML y este informe son el contrato vigente. Guías antiguas
se marcaron `SUPERSEDED`, EXEC.1 como `HISTORICAL_AUDIT`, y se indexaron en
`docs/README.md`; se preservó su texto de evidencia en lugar de alterar hechos pasados.

## 10. Ejemplos de uso

Ejemplos para una ejecución posterior autorizada; no se ejecutaron contra datos reales.
Los IDs deben ser UUID del mismo linaje. Desde `malaria_dl_local_project`:

```bash
source .venv-local-train/bin/activate

python -m src.train --campaign-id "$CAMPAIGN_ID" --plan
python -m src.train --source-training-run-id "$TRAIN_ID" --dry-run
python -m src.train --campaign-id "$CAMPAIGN_ID" --source-training-run-id "$TRAIN_ID"

python -m src.evaluate --campaign-id "$CAMPAIGN_ID" --inspect
python -m src.evaluate --source-training-run-id "$TRAIN_ID" --threshold auto --seed auto
python -m src.evaluate --source-training-run-id "$TRAIN_ID" --threshold 0.4 --seed 11 --batch-size 16
python -m src.evaluate --source-training-run-id "$TRAIN_ID" --threshold clinical --inspect

python -m src.explain --source-training-run-id "$TRAIN_ID" --max-images all --inspect
python -m src.explain --source-training-run-id "$TRAIN_ID" --sample-id "$SAMPLE_ID"
python -m src.explain --source-training-run-id "$TRAIN_ID" --method gradcam --class-id 0 --layer "$LAYER" --max-images 5
python -m src.explain --source-training-run-id "$TRAIN_ID" --method lime --num-samples 1000 --max-images 1
python -m src.explain --source-training-run-id "$TRAIN_ID" --method lime --num-samples 5000 --sample-id "$SAMPLE_ID"
python -m src.explain --source-training-run-id "$TRAIN_ID" --method shap --num-samples 1000 --sample-id "$SAMPLE_ID" --background-sample-id "$BACKGROUND_ID"
python -m src.explain --source-training-run-id "$TRAIN_ID" --method shap --max-images 5 --background-sample-id "$BACKGROUND_ID" --inspect

python -m src.test --source-training-run-id "$TRAIN_ID" --inspect
python -m src.test --campaign-id "$CAMPAIGN_ID" --source-training-run-id "$TRAIN_ID" --threshold auto --seed auto --inspect
```

TEST real permanece **NO EJECUTADO** en esta fase. `--inspect` no crea resultados.

## 11. Pruebas y evidencia

Comando reproducible desde la raíz del repositorio:

```bash
make test-cli01
```

Se usa el entorno local Python 3.12, `DATABASE_URL` ficticia no operativa, mocks de
catálogo/SQL, fixtures de metadatos, repositorio en memoria y archivos temporales.
Las pruebas numéricas existentes usan modelos diminutos e imágenes sintéticas,
no TRAIN/EVALUATE/EXPLAIN/TEST sobre el dataset científico.

El target ejecuta `test_cli01`, `test_exec1`, `test_assessment_e6`,
`test_dataset_split_isolation`, `test_dataset_stage1`, `test_governed_dataset_contract`,
`test_campaign_cli_plan_swv22` y `test_local_train_launcher`.

Cobertura: matriz exacta y argumentos retirados; cuatro `--help` en subprocess;
IDs ausentes/individuales/combinados, inexistentes e incompatibles; múltiples TRAIN;
umbrales auto/numérico/clinical; seed y batch persistidos/explícitos;
inspección sin ejecución; defaults y límites XAI; SQL ordenado y pertenencia;
objetivos 1/5/all/superiores a población; target y background distintos;
identidad, artefactos, verificación, reintentos y conservación histórica;
TEST sintético independiente; resolución de checkpoint; grafos Grad-CAM de las
tres arquitecturas; UUID y rutas nuevos para TRAIN; ausencia de ejecutores.

Resultado final: **PROBADO — 299 passed, 4 deselected, 7 warnings en 17,85 s**.
Salida íntegra: [capstone_cli_01_tests.txt](capstone_cli_01_tests.txt).

**VERIFICADO:** `git diff --check` sin errores y Ruff F821/F822/F823 sin nombres
indefinidos en módulos modificados y pruebas adaptadas. Los cuatro `--help` y la
falta de selección se verifican en subprocess; `--inspect` se prueba con dependencias
inyectadas para las cuatro operaciones. Las advertencias registradas corresponden a
Keras/SHAP/protobuf; no hay `UndefinedMetricWarning`.

**CERTIFICADO:** los 18 criterios de aceptación del contrato se satisfacen con la
modalidad de mocks/fixtures autorizada. Esto no certifica ejecuciones sobre PostgreSQL
operativo ni calidad científica de nuevas predicciones. Los cuatro casos excluidos
se enumeran a continuación y no se cuentan como aprobados.

Exclusiones expresas del target: una prueba que lee código del subsistema congelado
`malaria_dataset_split_project` y tres pruebas de inspección real de procesos del host
restringida por el sandbox. No son pruebas del contrato CLI. El reconocimiento de
módulos y la exclusión de inspecciones del gate se prueban con argumentos sintéticos.
No se declararon aprobadas esas cuatro pruebas excluidas.

Las primeras corridas detectaron imports de builders retirados, catálogo no aislado
en fixtures antiguos y supuestos demasiado estrictos sobre DenseNet anidado; se
adaptaron las pruebas al contrato y al resolver existente. Se mantuvo la fórmula de
Grad-CAM. No se amplió el acceso a PostgreSQL para resolver los fallos de aislamiento.

## 12. Límites y pendientes independientes

- **NO EJECUTADO:** campañas reales, inferencia sobre datos oficiales, lectura de
  imágenes TEST oficiales, modificaciones de PostgreSQL operativo, migraciones,
  activación productiva, cambios de frontend o publicación/commit.
- **NO EJECUTADO:** nueva integración PostgreSQL; la certificación de esta fase usa
  mocks y fixtures, permitidos por el encargo. La revisión de triggers es estática.
  Pruebas PostgreSQL existentes se adaptaron a los nombres/errores nuevos, sin ejecutarlas.
- **VERIFICADO:** `--max-images` limita explicaciones y artefactos, pero conserva la
  acreditación física de toda la población VAL antes de seleccionar objetivos;
  no promete limitar a N el coste de hashes del verificador de dataset existente.
- **PENDIENTE externo al alcance:** rendimiento y calidad científica de nuevas
  explicaciones reales; esta entrega certifica contrato de software, no eficacia clínica.
- Advertencias de dependencias Keras/SHAP/protobuf se registran en la salida de pruebas;
  no equivalen al `UndefinedMetricWarning` por LIME=1, que ahora es un argumento inválido.

**EXPLAIN-UI-01 — PENDIENTE.** Visualización de artefactos con errores en
`http://localhost/modelo-ia/evaluaciones/e6/4703ff9e-2d20-413f-9b9a-cd945c8dd632?datasource=malaria`.

**EXPLAIN-UI-02 — PENDIENTE.** «Explicabilidad por caso» informa «No hay casos de
explicabilidad registrados para esta ejecución» en
`http://localhost/modelo-ia/ejecuciones/338136db-a207-47fc-bbf3-d17ce85c0dc2?datasource=malaria`.

Ambos requieren auditoría posterior PostgreSQL → API → frontend y acceso a artefactos
Docker/macOS. No se presume ausencia de archivos; no se investigaron ni corrigieron aquí.

## 13. Archivos modificados y eliminados

Inventario de esta entrega, separado de la evidencia histórica conservada:

| Estado | Archivo |
|---|---|
| Modificado | `Makefile` |
| Modificado | `backend_api/app/routes/campaigns.py` |
| Modificado | `backend_api/tests/test_campaigns_api_swv22.py` |
| Modificado | `docs/README.md` |
| Nuevo | `docs/audits/capstone_cli_01_parameter_certification.md` |
| Nuevo | `docs/audits/capstone_cli_01_tests.txt` |
| Modificado | `docs/engineering/campanas_creacion_ejecucion.md` |
| Modificado | `docs/engineering/governed_dataset_resolution.md` |
| Modificado | `docs/engineering/model_training_pipeline.md` |
| Modificado | `docs/exec1_execution_contract.md` |
| Modificado | `docs/guia_entrenamiento_patient_split.md` |
| Modificado | `docs/science/e9_3_operacion_secuencial_2026-09-14.md` |
| Modificado | `docs/science/operacion_e9.md` |
| Modificado | `docs/science/plan_reanudacion_e9_1_2026-09-14.md` |
| Modificado | `malaria_dl_local_project/README.md` |
| Modificado | `malaria_dl_local_project/docs/dataset_explicit_contract.md` |
| Modificado | `malaria_dl_local_project/docs/model_registry_e2.md` |
| Eliminado | `malaria_dl_local_project/run_evaluate_all_trainings.py` |
| Eliminado | `malaria_dl_local_project/run_explain_all_trainings.py` |
| Eliminado | `malaria_dl_local_project/run_test_all_models.py` |
| Eliminado | `malaria_dl_local_project/run_train_all_models.py` |
| Modificado | `malaria_dl_local_project/src/malaria_dl/assessment/cli.py` |
| Modificado | `malaria_dl_local_project/src/malaria_dl/assessment/contracts.py` |
| Modificado | `malaria_dl_local_project/src/malaria_dl/assessment/service.py` |
| Modificado | `malaria_dl_local_project/src/malaria_dl/campaigns/plan.py` |
| Modificado | `malaria_dl_local_project/src/malaria_dl/execution/global_gate.py` |
| Modificado | `malaria_dl_local_project/src/malaria_dl/execution/local_launch.py` |
| Modificado | `malaria_dl_local_project/src/malaria_dl/execution/operations.py` |
| Modificado | `malaria_dl_local_project/src/malaria_dl/execution/selection.py` |
| Modificado | `malaria_dl_local_project/src/malaria_dl/persistence/database.py` |
| Modificado | `malaria_dl_local_project/tests/test_assessment_e6.py` |
| Modificado | `malaria_dl_local_project/tests/test_campaign_cli_plan_swv22.py` |
| Modificado | `malaria_dl_local_project/tests/test_campaign_configuration_postgres_swv22.py` |
| Nuevo | `malaria_dl_local_project/tests/test_cli01.py` |
| Modificado | `malaria_dl_local_project/tests/test_dataset_split_isolation.py` |
| Modificado | `malaria_dl_local_project/tests/test_dataset_stage1.py` |
| Modificado | `malaria_dl_local_project/tests/test_exec1.py` |
| Modificado | `malaria_dl_local_project/tests/test_exec1_postgres.py` |
| Modificado | `malaria_dl_local_project/tests/test_global_execution_postgres.py` |
| Modificado | `malaria_dl_local_project/tests/test_governed_dataset_contract.py` |
| Modificado | `malaria_dl_local_project/tests/test_input_contract_e3.py` |
| Modificado | `malaria_dl_local_project/tests/test_local_train_launcher.py` |
| Modificado | `malaria_dl_local_project/tests/test_model_registry_e2.py` |
| Eliminado | `malaria_dl_local_project/tests/test_run_evaluate_all_trainings.py` |
| Eliminado | `malaria_dl_local_project/tests/test_run_explain_all_trainings.py` |


No se generó commit ni se publicó una rama. El árbol de trabajo contiene la entrega para revisión.

## 14. Corrección posterior: gate retenido tras interrupción

El usuario reportó `PROCESS_TREE_RELEASE_UNPROVEN` al ejecutar EXPLAIN/LIME con
`--max-images 1`. El traceback sitúa el rechazo en `GlobalGate.__enter__`, antes de
preparar EXPLAIN o cargar LIME. La certificación sintética anterior no cubría este
caso; no demostraba disponibilidad operativa de ese gate.

**VERIFICADO por código:** `verify_retained_processes` rechazaba incondicionalmente
`release_confirmed=false`, incluso después de comprobar ausencia local de todas las
identidades y sesiones retenidas. Esa marca refleja el cierre anterior, no demuestra
que los procesos continúen vivos.

**IMPLEMENTADO:** aceptar la ausencia comprobada en el mismo host/arranque cuando
hay identidades retenidas. Se conservan rechazos de procesos vivos, sesiones con
descendientes, evidencia remota sin liberación confirmada y evidencia sin identidades.
Un timestamp actual desconocido no acredita reutilización del PID. El advisory lock,
la búsqueda de otros procesos científicos, las restricciones PostgreSQL y el circuito
de recursos permanecen activos. No se borra ni resetea evidencia para desbloquear.
Los errores controlados del gate se muestran como `STOP <código>` con salida 2, sin traceback.

**PROBADO:** nueve regresiones nuevas con snapshots de procesos simulados;
`make test-cli01`: 299 aprobadas, 4 excluidas, 7 advertencias. Se adaptó además la
expectativa antigua en la suite PostgreSQL del gate; esa integración no se ejecutó.

**PENDIENTE de comprobación operativa:** repetir el comando del usuario. No se
consultó ni modificó PostgreSQL operativo, no se enviaron señales a procesos y no se
inició una explicación real. Esta corrección no acredita que no exista otro bloqueo
operativo posterior.
