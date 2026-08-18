# Freeze, lineage final e integración TRAIN — SPLIT 6

Estado: **SPLIT_6=APPROVED**. No se requirió cambio de esquema; Alembic permanece en
`20260812_02`.

## Freeze y contrato científico

`Malaria Patient Split v1` (`d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`) transitó en una
sola transacción `VALIDATED → FROZEN`. El servicio toma `SELECT FOR UPDATE`, revalida
12/12 checks, los digests aprobados y la materialización READY/PASS, mezcla
`freeze_contract` dentro de `methodology_json` y usa el lifecycle service. La metadata
anterior se preservó. `frozen_at` es `2026-08-18 11:42:50.372607-04:00`.

El contrato `malaria_patient_split_freeze_v1` sella algoritmo 1.0.0, seed 42, 201
Patients, 27.558 records, materialización
`e15dc166-1c4b-558e-b77b-727b1783430c` y los fingerprints:

```text
source population  eef647ce1f3040468a84cbad73ffb1b50b86d685313f1291693b16f4f1f635f0
clinical identity  d4bd79cb2327ca7aa1eeff19e14a9104af157984cccd9418c75b0f62ae3e8a59
patient assignment cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f
record assignment  9709ce48b9b41bcacca49ccfb53ec62b48c4822c2fb8e227643bf26aed196ea2
```

Los dos fingerprints nuevos fueron calculados dos veces con orden canónico e igualdad
exacta. Una segunda ejecución de `python -m malaria_split.cli
freeze-patient-split-v1` devolvió `ALREADY_FROZEN_MATCH_NO_OP`, sin cambiar timestamp,
metadata ni digests. Un estado FROZEN divergente produce `FROZEN_STATE_CONFLICT`.

## Trainability y selección

TRAINABLE ahora es YES, sin reason codes. v1 es la única versión retornada por la lista
entrenable pese a que las activaciones siguen en cero: ACTIVE no participa del guard.
Para nuevos TRAIN la unidad seleccionable es sólo `dataset_version_id`; al omitirse se
elige determinísticamente el candidato entrenable más reciente. El usuario no entrega
source, split, seed, materialization ni path. Un UUID inválido/no entrenable aborta y no
cae al `malaria_physical_split` legacy.

`python -m src.train --dataset-version-id <uuid> ...` ejecuta el pre-train guard,
resuelve automáticamente el attempt READY/PASS y usa su root versionado. El orchestrator
propaga el mismo UUID a todos los modelos de una campaña. El loader conserva
`train/val/test`, clases `uninfected=0` y `parasitized=1`; TRAIN/VAL se abren para fit y
selección/calibración, mientras TEST se abre sólo en la evaluación independiente final.

## Lineage e herencia

El run nuevo persiste `runs.dataset_version_id`. `run_io_records` persiste además
`dataset_materialization_id`, root, counts y los cuatro fingerprints. El snapshot es un
objeto inmutable y el guard rechaza cambios. EVALUATE y calibraciones con TRAIN
gobernado resuelven la versión desde el run padre: no ofrecen override; threshold y
temperature scaling usan exclusivamente VAL. Los 12 TRAIN y 12 EVALUATE históricos
mantienen `dataset_version_id NULL` y su interpretación histórica.

El smoke real autoseleccionó v1, resolvió el materialization oficial, abrió un batch
TRAIN y uno VAL de tamaño 2, verificó `['uninfected','parasitized']` y no abrió TEST.
No se ejecutó campaña completa, no se modificaron backend/frontend, activation,
materialización, legacy filesystem ni regla productiva `TRAIN completed + EVALUATE
completed`.
