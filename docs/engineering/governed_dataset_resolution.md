# Resolución transversal del dataset gobernado

Estado documental: `CURRENT_DOC`.
Fecha de verificación: 2026-10-08.

## Diagnóstico de los seis puntos de entrada

| Entrada | Recorrido vigente | Hallazgo previo al cambio |
|---|---|---|
| TRAIN campaña | `run_train_all_models.py` → `execution.campaign.preflight` → `execution.worker` → `execution.train.train` | Verificaba la población oficial; traducía la ruta únicamente en una copia de la sesión del worker. |
| TRAIN individual | `src.train` → `training.cli` → `execution.train.standalone` → `train` | Ya verificaba el dataset; el bootstrap del entorno macOS estaba limitado al lanzador de campañas. |
| EVALUATE campaña | `run_evaluate_all_trainings.py` → `assessment.cli` → `service.prepare/run` | Verificaba una raíz local, pero seleccionaba y cargaba archivos desde la ruta histórica de TRAIN. |
| EVALUATE individual | `src.evaluate` → `evaluation.evaluator.main` → `assessment.cli` | Mismo consumidor y mismo defecto que la campaña. |
| EXPLAIN campaña | `run_explain_all_trainings.py` → `assessment.cli` → `service.prepare/run` | Compartía el defecto de EVALUATE, incluidos los backgrounds autorizados de SHAP. |
| EXPLAIN individual | `src.explain` → `explainability.pipeline.main` → `assessment.cli` | Mismo consumidor y mismo defecto que la campaña. |

`training_dataset_metadata()` solo examinaba las representaciones superiores de
`runs.execution_parameters` y `runs.parameters`. Omitía la sesión y el snapshot
anidado. Además, `service.prepare()` seleccionaba archivos antes de comprobar la
autorización del split en `identity()`.

Las funciones históricas de inventario/planificación que permanecen en los
lanzadores no son sus `main()` vigentes. Los loaders genéricos conservan opciones
legacy de TFDS y `malaria_physical_split`; ninguno de los seis recorridos vigentes
utiliza esas opciones para resolver el dataset oficial.

## Contrato compartido

1. TRAIN obtiene la versión explícita o la versión congelada de la campaña.
   EVALUATE/EXPLAIN recuperan el TRAIN y checkpoint explícitos.
2. `verify_dataset_for_execution()` conserva la verificación y la persistencia de
   evidencia existentes. Invoca `resolve_governed_dataset()`, que comprueba sello,
   materialización, validaciones, fingerprints y contenido mediante
   `dataset_integrity.verify_integrity()`.
3. `local_dataset_root()` es la única traducción entre prefijos del host. La
   existencia de una carpeta extranjera ya no hace que prevalezca sobre la copia
   verificada de `<PROJECT_ROOT>/data`. Una ruta no acredita por sí sola identidad.
4. TRAIN resuelve su variable local `dataset_root` en el consumidor común y carga
   exclusivamente TRAIN/VAL. La sesión conserva el snapshot original.
5. `dataset_samples()` utiliza la raíz devuelta por el verificador, y mantiene IDs,
   etiquetas y hashes de las asignaciones oficiales. `KerasRuntime` traduce la
   ubicación sin cambiar la identidad persistida y vuelve a comprobar el hash de
   cada imagen antes de decodificarla. Solo admite las muestras seleccionadas y
   los backgrounds acreditados; conserva el contrato de entrada del checkpoint.

La validación de split/protocolo se extrajo de `identity()` y se reutiliza al
principio de `prepare()`. Sus reglas no cambian. El bloqueo clínico de TEST y los
controles PostgreSQL de autorización final permanecen vigentes.

`--dataset-dir` se interpreta como ubicación de la misma materialización; no
selecciona otra población. EVALUATE/EXPLAIN aceptan `--model` como comprobación de
consistencia con el TRAIN, incluidos los alias del descriptor. Sigue siendo
necesario identificar el TRAIN o la versión del modelo: un nombre de arquitectura
no selecciona implícitamente un checkpoint. Las opciones de campaña pasan por el
mismo `prepare()` que las individuales.

El bootstrap existente configura en macOS el acceso al PostgreSQL de Compose
para los seis comandos. En Docker conserva el entorno existente.

## Recuperación del snapshot histórico

Una consulta de solo lectura une `runs` con `train_execution_sessions`. Se elige
una representación completa, en este orden: sesión, snapshot anidado en
`execution_parameters.model_configuration_e2.dataset`, representación superior de
`execution_parameters`, y las representaciones equivalentes de `parameters`.

Debe contener versión, materialización, raíz, cuatro fingerprints y conteos.
No se ensamblan representaciones incompletas ni se rellenan identidades ausentes.
Todos los campos presentes en las otras representaciones, incluso parciales, deben
coincidir. Los UUID se normalizan y las rutas se comparan por su ubicación relativa
bajo `data`, admitiendo distintos prefijos Docker/macOS. Se devuelve una copia
profunda; ninguna consulta actualiza registros históricos.

## Archivos y funciones modificados

Rutas Python relativas a `malaria_dl_local_project/src/malaria_dl/`:

| Archivo | Funciones/cambio |
|---|---|
| `data/governed_dataset.py` | `_resolve`, `local_dataset_root`, `training_dataset_metadata`, `validate_dataset_location`: recuperación consistente y ubicación común. |
| `execution/train.py` | `train`: resolución local para ambos lanzadores y rutas relativas de VAL. |
| `execution/worker.py` | `main`: elimina la reescritura particular de la sesión. |
| `training/cli.py` | `main`: reutiliza bootstrap local antes de resolver configuración. |
| `assessment/lineage.py` | `resolve`, `dataset_samples`: snapshot común, evidencia vinculada al TRAIN y archivos de la raíz verificada. |
| `assessment/runtime.py` | `KerasRuntime.__init__/images`: ubicación local y muestras autorizadas. |
| `assessment/contracts.py` | `validate_split_protocol`, `identity`: una sola regla de autorización. |
| `assessment/service.py` | `prepare`: autorización previa, consistencia de `--model`, propagación de linaje y ubicación. |
| `assessment/cli.py` | `parser`, `main`, `_main`: opciones compartidas y bootstrap. |

También cambian `Makefile`, `tests/test_dataset_resolution.py`,
`tests/test_dataset_stage1.py`, `tests/test_assessment_e6.py` y el índice documental.
Los fixtures ajustados usan catálogo sintético y representan la nueva consulta
compartida; no necesitan PostgreSQL. No se modifican loaders, preprocesamiento,
arquitecturas, hiperparámetros, esquema, datasets ni checkpoints.

## Evidencia y límites de validación

La suite focalizada se ejecuta con `make test-governed-dataset`. Cubre snapshots
completos e incompletos, conflictos parciales, materializaciones distintas, raíces
existentes ajenas al host, equivalencia campaña/individual, autorización previa,
TRAIN/VAL sin carga de TEST, evidencia de rechazo, y tensores de entrada de modelos
Keras mínimos con rutas locales y extranjeras. No entrena redes. Usa archivos y
persistencia sintéticos. Se excluye explícitamente una prueba de comparación con
código del generador de datasets, fuera del alcance congelado de esta tarea.

Resultado final: **142 passed, 1 deselected** en macOS (14,34 s) y
**142 passed, 1 deselected** en Docker (8,81 s). Las siete advertencias de cada
ejecución proceden de dependencias Protobuf, SHAP y Keras.

Para reproducir en Docker desde la raíz del repositorio:

```sh
make test-governed-dataset DATASET_TEST_PYTHON='docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/app/malaria_dl_local_project -w /app backend python'
```

La exploración inicial de una suite más amplia produjo 162 aprobadas y 22 fallidas:
incluía dependencias del catálogo PostgreSQL, fixtures antiguos del backend y
pruebas de procesos restringidas por el sandbox. Esa ejecución **FALLÓ**; no se
presenta la suite global como aprobada. Se aislaron los fixtures pertinentes y el
target final contiene las comprobaciones específicas de este contrato.

Comprobaciones reales de solo lectura, realizadas tanto en macOS como en Docker:

- RUN `bbbd5b60-afaa-4034-a504-a60ed642aafe`, estado `completed`.
- Versión `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2` y materialización
  `e15dc166-1c4b-558e-b77b-727b1783430c`, estado `READY`, reconciliación `PASS`.
- Snapshot de sesión y snapshot anidado coincidentes; fingerprints coincidentes
  con los valores persistidos del sello. No se recalcularon todos los fingerprints
  del dataset real durante esta comprobación acotada.
- Conteos persistidos: TRAIN 22.180, VAL 2.693, TEST 2.685. Se enumeraron únicamente
  los archivos físicos de VAL: **2.693** en ambos entornos.
- Se comprobaron dos archivos de VAL, uno por clase, con los mismos IDs y SHA-256
  que PostgreSQL y el otro entorno:
  `0071ea61-5af6-5309-9fe6-085ae804789d` y
  `000f6007-9330-5085-972a-247631c541c6`.
- SHA-256 canónico del snapshot antes/después, idéntico en ambos entornos:
  `bf096ccff846181d4b3ebd848750c370154a14ad1aa923fe9f2c8f1234138d48`.

La ruta histórica permanece en `/app/malaria_dl_local_project/data/…`.
En macOS la ubicación efectiva está bajo el checkout local
`malaria_dl_local_project/data/…`; Docker utiliza su montaje `/app/…`.

**NO VERIFICADO:** ejecución científica completa de los seis comandos con el
dataset real, nueva escritura de evidencia en PostgreSQL y verificación integral
real de todos los archivos. El verificador existente comprueba contenido de todos
los splits, incluido TEST; no se ejecutó contra el dataset operativo para respetar
la exclusión de TEST. Las pruebas integrales de ese verificador usan población
sintética. No hubo campañas, reentrenamientos ni inferencia masiva.

La tabla siguiente califica el contrato auditado y las pruebas focalizadas, no
certifica una ejecución científica completa:

| Punto de entrada | Snapshot oficial | Resolución compartida | Verificación | Estado |
|---|---|---|---|---|
| TRAIN campaña | Versión congelada | Resolver + consumidor TRAIN | Preflight común; prueba sintética | APROBADO |
| TRAIN individual | Versión explícita | Resolver + consumidor TRAIN | Mismo verificador; prueba de equivalencia | APROBADO |
| EVALUATE campaña | TRAIN original | Resolver + `assessment` | Linaje, split y contenido sintético | APROBADO |
| EVALUATE individual | TRAIN original | Mismo `prepare/runtime` | Mismas opciones y contrato de entrada | APROBADO |
| EXPLAIN campaña | TRAIN original | Resolver + `assessment` | Muestras y background acreditados | APROBADO |
| EXPLAIN individual | TRAIN original | Mismo `prepare/runtime` | Mismas opciones y contrato de entrada | APROBADO |
