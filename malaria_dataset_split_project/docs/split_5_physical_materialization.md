# Materialización física versionada — SPLIT 5

Estado: **SPLIT_5=APPROVED; SPLIT_6_READY=YES**.

## 1. Versión y attempt

Se materializó `Malaria Patient Split v1`, UUID
`d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`, manteniendo lifecycle VALIDATED. El primer
attempt oficial es `e15dc166-1c4b-558e-b77b-727b1783430c`, attempt number 1, creado como
MATERIALIZING/PENDING y finalizado READY/PASS.

Root final relativo persistido:
`malaria_dataset_versions/d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`. El staging fue
`.d8c0cab5-09dd-597f-9de7-7ca01aee2ec2.attempt-1.staging` bajo el mismo filesystem.

## 2. Fuente, layout y estrategia de nombres

El plan derivó exclusivamente de `dataset_split_assignments` +
`dataset_source_records`. Resolvió 27.558/27.558 PNG originales NLM/LHNCBC y cero
ausencias. Los nombres fueron únicos dentro de cada `split/class`; hubo cero colisiones y
se utilizó `PRESERVE_SOURCE_FILENAME`.

El layout final contiene exactamente:

```text
train/{parasitized,uninfected}
val/{parasitized,uninfected}
test/{parasitized,uninfected}
```

La copia usó bytes fuente sin resize, decode, transformación ni re-encoding.

## 3. Counts y reconciliación

| Split | Total | Parasitized | Uninfected | Patients |
|---|---:|---:|---:|---:|
| train | 22.180 | 11.137 | 11.043 | 161 |
| val | 2.693 | 1.325 | 1.368 | 20 |
| test | 2.685 | 1.317 | 1.368 | 20 |

La reconciliación completa verificó cada path esperado contra source_record, split y
clase. Resultado: 27.558 expected/found; cero missing, unexpected, wrong split o wrong
class. Los overlaps patient train-val, train-test y val-test permanecen en cero.

Se calcularon 27.558 SHA-256 sobre bytes materializados: 27.558 match y cero mismatch
contra `dataset_source_records.source_file_sha256`. Los fingerprints lógicos permanecen:

```text
Patient: cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f
Record:  9709ce48b9b41bcacca49ccfb53ec62b48c4822c2fb8e227643bf26aed196ea2
```

## 4. Promoción y estado PostgreSQL

Sólo después del PASS en staging se promovió por rename dentro del mismo filesystem. Se
repitió la reconciliación completa sobre el root final y recién entonces se actualizó el
attempt a READY/PASS, record_count 27.558 y completed_at
`2026-08-14T13:26:59.882377-04:00`.

El manifest JSON guarda contrato, filename strategy, ambos fingerprints, counts, clases,
pacientes, overlaps y evidencia SHA. No se creó activation ni se cambió la Dataset
Version a FROZEN.

## 5. Trainability e idempotencia

TRAINABLE continúa NO. Formal validation y READY/PASS ya se resuelven correctamente, por
lo que la única razón restante es `DATASET_NOT_FROZEN`.

La segunda ejecución reconstruyó el plan, recalculó los 27.558 SHA/path mappings y
devolvió `ALREADY_MATERIALIZED_MATCH_NO_OP`. Conservó el mismo attempt, timestamps y root
mtime; no creó attempt 2 ni escribió filesystem/DB. Un READY/PASS cuyo root o manifest no
coincida produce `MATERIALIZED_STATE_CONFLICT`, sin reparación silenciosa.

## 6. Legacy, tests y alcance pendiente

El legacy `malaria_physical_split` sigue intacto con 27.558 imágenes:
22.046/2.756/2.756. `dataset_split_images` conserva 27.558 filas sin backfill a v1, los
runs históricos siguen sin vínculo v1 y no se modificaron TRAIN, EVALUATE, backend,
frontend ni publishing.

La suite post-materialización terminó con 77 passed, 0 skipped y 0 failed. Tests pequeños
cubren reconciliación correcta, count/path incorrecto y SHA corrupto; los tests de
trainability existentes cubren el resolver READY/PASS y la ausencia de freeze.

SPLIT 6 queda autorizado para fingerprints finales, freeze, lineage e integración
TRAIN/EVALUATE. SPLIT 5 no realizó ninguna de esas operaciones.
