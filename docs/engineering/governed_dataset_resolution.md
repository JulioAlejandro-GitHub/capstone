# Resolución y aislamiento físico del dataset gobernado

Estado documental: `CURRENT_DOC`.
Fecha de verificación: 2026-10-08.
Rama de trabajo: `refactor/unified-dataset-resolution`; sin integración en `main`.

La identidad científica del dataset es global. La verificación física y la carga
operativa se limitan a los splits explícitamente solicitados y autorizados.

## Diagnóstico previo al ajuste

La unificación anterior resolvió la recuperación de snapshots históricos y las
rutas Docker/macOS. La auditoría posterior identificó que `verify_integrity()`
todavía enumeraba `root.rglob("*")` y calculaba hashes de todos los archivos,
incluso para EVALUATE/EXPLAIN VAL.

| Comprobación | Fuente | Alcance |
|---|---|---|
| FROZEN, sello, materialización READY/PASS y validaciones históricas | PostgreSQL | Global, sin imágenes |
| Cuatro fingerprints, cobertura, conteos, identidad clínica y separación de pacientes | PostgreSQL | Global, sin imágenes |
| Referencias de hashes, rutas esperadas y colisiones de nombres | Metadatos en memoria | Global, sin filesystem de imágenes |
| Enumeración de archivos y cálculo SHA-256 | Filesystem | Solo los splits autorizados |
| Selección, decodificación y preprocesamiento | `dataset_samples` / `KerasRuntime` | Solo el split de la operación |

La auditoría quedó documentada antes de modificar el código. Otros accesos
identificados: SHAP solicitaba TRAIN como background para EXPLAIN VAL;
`--inspect` adquiría un coordinador que escribe en PostgreSQL; y el bloqueo final
de TEST se comprobaba al reservar el intento, después de preparar las imágenes.

## Contrato transversal

`resolve_governed_dataset()`, `verify_dataset_for_execution()`,
`resolve_training_run_dataset()` y `verify_integrity()` exigen
`required_splits` explícito. Omitirlo, pasar una cadena, duplicados o nombres
inválidos produce rechazo antes de consultar la base o abrir imágenes.

| Operación | `required_splits` | Autorización |
|---|---|---|
| TRAIN individual/campaña, creación y congelamiento de campaña TRAIN | `("train", "val")` | Contrato TRAIN existente |
| EVALUATE VAL | `("val",)` | Protocolo de desarrollo explícito |
| EXPLAIN VAL | `("val",)` | Protocolo y muestras explícitas |
| EVALUATE/EXPLAIN TEST | `("test",)` | Protocolo final y bloqueo exacto previo en PostgreSQL |
| Consulta administrativa de identidad | `()` | Solo metadatos; sin acreditación física |
| Verificación física integral administrativa | `("train", "val", "test")` | Inclusión deliberada de TEST y autorización explícita del llamador |

No existe un default que incluya TEST. El argumento interno `test_authorized`
no se expone como opción CLI para saltarse los bloqueos. En las entradas
científicas solo se habilita después de comprobar el bloqueo final persistido.

El mismo verificador recalcula los cuatro fingerprints a partir de los metadatos
actuales de PostgreSQL y los compara con el contrato FROZEN. Comprueba identidad,
materialización, separación de pacientes, conteos y referencias de toda la
población sin abrir imágenes de otros splits. Devuelve los conteos globales para
conservar el snapshot original.

La parte física enumera únicamente cada directorio solicitado mediante
`os.scandir`, sin recorrer la raíz completa. Rechaza enlaces simbólicos antes de
seguirlos, incluidos enlaces desde VAL hacia TRAIN/TEST. Compara el conjunto
exacto de archivos del split y calcula sus hashes. Un archivo corrupto, faltante
o extra en el split solicitado provoca rechazo. Una verificación VAL no acredita
el contenido físico actual de TRAIN o TEST, aunque sus fingerprints históricos
formen parte de la identidad global.

## Snapshot, ubicación y consumidores

`training_dataset_metadata()` conserva su recuperación de solo lectura: sesión,
snapshot anidado y formatos históricos completos. No ensambla evidencia ausente;
comprueba las otras representaciones, incluso parciales, y devuelve una copia.
`assert_run_dataset_snapshot_unchanged()` mantiene las comprobaciones de versión,
materialización, fingerprints, conteos y ubicación relativa acreditada.

`local_dataset_root()` sigue siendo la única traducción de ubicación entre
Docker y macOS. `GovernedDatasetSnapshot.metadata()` no cambia: el alcance de una
verificación actual no se incorpora al snapshot científico histórico.

Los seis comandos conservan sus consumidores comunes:

| Entrada | Verificador y consumidor |
|---|---|
| `run_train_all_models.py --campaign-id …` | `execution.campaign.preflight` → worker → `execution.train.train` |
| `python -m src.train …` | `execution.train.standalone` → `train` |
| `run_evaluate_all_trainings.py --campaign-id …` | `assessment.cli` → `prepare` → `dataset_samples` → runtime |
| `python -m src.evaluate …` | Mismo `assessment.prepare` y runtime |
| `run_explain_all_trainings.py --campaign-id …` | Mismo `assessment.prepare` y runtime |
| `python -m src.explain …` | Mismo `assessment.prepare` y runtime |

`--model` y `--dataset-dir` siguen siendo restricciones de consistencia; no
seleccionan otra población ni un checkpoint implícito. Dimensiones de entrada,
orden de clases y preprocesamiento siguen siendo los del TRAIN/checkpoint.

SHAP usa exclusivamente los IDs de background indicados por el usuario que
pertenezcan al split autorizado. Un background histórico de TRAIN no puede usarse
en EXPLAIN VAL: se rechaza con `BACKGROUND_NOT_ACCREDITED`, sin abrir TRAIN ni
sustituir automáticamente sus imágenes. Cambiar los IDs requiere una decisión
científica explícita del usuario; no se reinterpreta una explicación histórica.
El runtime vuelve a exigir que cada muestra/background pertenezca al split.

## Autorización de TEST antes del acceso

`AssessmentRepository.authorize_test_request()` consulta el bloqueo existente
`assessment_final_locks`, su identidad y candidato/decisión. Exige coincidencia
con los identificadores, protocolo, opciones y tipo de operación solicitados.
La identidad completa procede de `evidence.final_identity` o de la fila histórica
correspondiente de `assessment_identities`; sin evidencia suficiente se rechaza.

Después se reconstruye la selección desde metadatos, se compara la identidad
exacta (incluido el código) y solo entonces se permite la verificación física de
TEST. El trigger PostgreSQL existente vuelve a exigir el bloqueo en la reserva.
Las campañas difieren la apertura de checkpoints hasta esta autorización.
El proceso administrativo que crea un bloqueo final consulta muestras TEST como
metadatos: no necesita abrir TEST antes de autorizarlo.

No se cambian tablas, triggers, decisiones clínicas ni bloqueos históricos.
No se ejecutó TEST operativo durante esta tarea.

## Evidencia versionada

La nueva evidencia usa `verifier_version = ml_dataset_integrity_v2` y separa:

- `snapshot`: versión, materialización, cuatro fingerprints y conteos globales.
- `required_splits` y `physically_verified_splits`: alcance de esta comprobación.
- `global_integrity_status = verified_frozen_metadata`: sello contrastado con
  metadatos actuales; no implica lectura actual de todas las imágenes.
- `physical_integrity_status`: `verified` para splits comprobados o `not_checked`
  para una consulta exclusivamente de metadatos.
- `integrity_status`: `verified_requested_splits`, `verified_metadata_only` o
  `verified` únicamente para verificación física integral explícita.
- Consumidor, RUN de TRAIN cuando corresponde, referencia de evidencia esperada
  y resultado/error, mediante el mecanismo existente de auditoría.

Los rechazos no acreditan físicamente ningún split. Las evidencias v1 siguen
sirviendo como referencia de identidad: siempre se verifica de nuevo el alcance
actual. No se reescriben ni se cambia silenciosamente su significado.

`--inspect` conserva el resultado de identidad y añade
`inspection_verification`. No adquiere el coordinador global, no reserva un RUN,
no ejecuta inferencia y no escribe evidencia en PostgreSQL. En campañas,
`--inspect` sin split mantiene el inventario; con split/protocolo realiza la
inspección de ese split para cada miembro elegible.

## Archivos y funciones modificados en este ajuste

Rutas relativas a `malaria_dl_local_project/src/malaria_dl/`:

| Archivo | Funciones y propósito |
|---|---|
| `data/governed_dataset.py` | `normalize_required_splits`, `_resolve`, ambos resolvedores y `verification_metadata`: alcance explícito separado del snapshot. |
| `data/dataset_integrity.py` | `verify_integrity`, versión v2: metadatos globales y recorrido físico selectivo, sin seguir symlinks. |
| `persistence/dataset_evidence.py` | `verify_dataset_for_execution`: propagación y evidencia de alcance; compatibilidad de referencias v1. |
| `execution/campaign.py`, `execution/train.py` | Preflight, dry-run, standalone y finalización TRAIN: TRAIN/VAL explícitos. |
| `campaigns/service.py` | Crear/configurar/congelar campañas: mismo alcance TRAIN/VAL. |
| `assessment/lineage.py` | `dataset_samples`, `campaign_inventory`: selección acotada y consultas de metadatos previas a autorización TEST. |
| `assessment/service.py`, `assessment/repository.py` | `prepare`, `authorize_test_request`: autorización previa y backgrounds del split. |
| `assessment/runtime.py` | `images`: rechazo de muestras de otro split antes de abrirlas. |
| `assessment/cli.py` | Inspección sin escrituras, propagación y salida de evidencia. |
| `science/cli.py`, `science/repository.py` | Comparación y preparación de bloqueo final mediante metadatos. |
| `evaluation/calibration_cli.py` | Propaga el split de calibración ya validado. |
| `local_execution/backend.py`, `training/trainer.py` | Adaptadores existentes: alcance explícito TRAIN/VAL. |

También se actualizan `Makefile`, las pruebas previas que ahora deben solicitar
su alcance explícitamente, `test_dataset_split_isolation.py` y este documento,
que ya está indexado en `docs/README.md`.

## Pruebas focalizadas

```sh
make test-governed-dataset
make test-governed-dataset DATASET_TEST_PYTHON='docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/app/malaria_dl_local_project -w /app backend python'
```

Resultado final: **183 passed, 1 deselected** en macOS (14,78 s) y
**183 passed, 1 deselected** en Docker (7,00 s). La prueba excluida consulta código
del generador de datasets, fuera del alcance congelado. Las siete advertencias de
cada ejecución proceden de dependencias Protobuf, SHAP y Keras.

La instrumentación intercepta `open` (builtins/io/os), `scandir`, `listdir`,
`stat`, `lstat` y `file_sha256`. Falla si una operación toca una ruta de un split
no autorizado o enumera la raíz completa. Los fixtures contienen los tres splits.
Se ejercitan los comandos individual/campaña y sus inspecciones, corrupción VAL,
conflicto de snapshot, cambio de metadatos TRAIN, enlaces VAL→TRAIN, ausencia de
los directorios no solicitados, backgrounds SHAP, evidencia v1/v2, TRAIN/VAL y
rechazo de TEST sin bloqueo antes de abrir checkpoints o imágenes.

El escenario autorizado de TEST utiliza únicamente bytes sintéticos y un bloqueo
simulado; no realiza evaluación ni inferencia científica. Las pruebas previas de
integridad integral también utilizan exclusivamente datos sintéticos.

## Inspección del dataset y RUN reales

Se comenzó con lecturas de metadatos del RUN
`bbbd5b60-afaa-4034-a504-a60ed642aafe`, completado y con sesión verificada.
Versión `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`, materialización
`e15dc166-1c4b-558e-b77b-727b1783430c`.

La comprobación real ejecutó primero
`resolve_training_run_dataset(run, required_splits=("val",))` y luego
`assessment.cli.main("evaluate", … --inspect --split val …)` con el mismo
instrumento de acceso. Todas las conexiones SQLAlchemy se forzaron a solo lectura,
adicionalmente a las transacciones de lectura del proyecto. El protocolo usado
se identificó como `read_only_val_inspection_v1`; el umbral 0,5 solo forma parte de
la identidad de inspección, sin aplicar predicciones ni persistir decisiones.

| Comprobación real | macOS | Docker |
|---|---|---|
| Identidad global/fingerprints actuales de PostgreSQL contra FROZEN | APROBADO | APROBADO |
| Conjunto y SHA-256 de las 2.693 imágenes VAL | APROBADO | APROBADO |
| Cero accesos físicos a TRAIN/TEST | APROBADO | APROBADO |
| Snapshot antes/después idéntico | APROBADO | APROBADO |
| Inspección completa de EVALUATE del RUN | APROBADO | FALLIDO |

macOS inspeccionó 2.693 muestras, versión de modelo
`3ffcb0ec-324f-43fb-8521-d55cbe81f229`, sin inferencia. SHA-256 canónico de la lista
de muestras: `b55ecbf2e9d7800d97e48bfd3b495b8cb3084384e3a9a12c7fb73d4345206ff9`.

El hash del snapshot histórico permanece, antes/después y en ambos entornos:
`bf096ccff846181d4b3ebd848750c370154a14ad1aa923fe9f2c8f1234138d48`.

En Docker el verificador del dataset completó VAL, pero la inspección del RUN
falló con `CHECKPOINT_NOT_FINALIZED`: el checkpoint está registrado bajo
`/Users/julio/…/malaria_dl_local_project/outputs/campaign_runs/<RUN>/epoch_2.keras`
y esa ubicación no está montada en el contenedor actual. No se alteró el
checkpoint ni su ruta histórica. Este límite es independiente de la resolución
física del dataset, que sí pasó.

## Límites pendientes

- **NO VERIFICADO:** evaluación científica completa, campañas y TEST operativos;
  deliberadamente no ejecutados.
- **NO VERIFICADO:** escritura real de nueva evidencia v2; los tests usan
  persistencia simulada y las inspecciones reales son estrictamente de lectura.
- La inspección completa del RUN en Docker requiere que su checkpoint histórico
  sea accesible y verificable en ese entorno; no se presenta como aprobada.
- Una verificación de VAL no acredita físicamente TRAIN/TEST. Esa ausencia de
  comprobación es parte explícita de la evidencia, no un PASS implícito.
- No hubo cambios de esquema, snapshots históricos, asignaciones de pacientes,
  datasets, checkpoints, arquitecturas, hiperparámetros ni preprocesamiento.
- No se integró la rama en `main`.
