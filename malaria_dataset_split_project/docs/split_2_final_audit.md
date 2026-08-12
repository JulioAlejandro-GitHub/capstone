# Auditoría E2E y cierre definitivo de SPLIT 2

Fecha de auditoría: 2026-08-12. Resultado: **PASS — SPLIT 2 APPROVED; SPLIT 3 READY**.

## 1. Objetivo y alcance

Esta auditoría independiente verifica SPLIT 2A, 2B y 2C contra el contrato arquitectónico.
No implementa funcionalidad, no altera schema ni lifecycle, y no crea records, Patient-ID,
versions, assignments, statistics, checks, materializations, activations o archivos. Las
únicas escrituras de prueba se ejecutaron en transacciones/savepoints revertidos. La
reejecución del bootstrap fue idempotente y conservó todos los conteos.

## 2. Alembic y schema

PostgreSQL real: 17.9, `malaria_experiments.public`. Current y head son ambos
`20260812_02`, con una sola cadena coherente:

```text
20260810_05 → 20260811_01 → 20260812_01 → 20260812_02
```

Las tres migrations SPLIT existen y sus dependencias son correctas. No se ejecutó
downgrade ni stamp. Existen las diez tablas científicas requeridas, con PK/FK/UNIQUE/
CHECK/índices auditados. También existen las FKs nullable de versión/materialización en
`runs`, `dataset_split_images` y `run_io_records`. Los seis triggers 2C y el índice
parcial single-current están instalados. Resultado Alembic/schema: PASS.

## 3. Dataset source y dataset version

La fuente PRIMARY única es `3f4058c7-5671-4c2f-a089-d1482d5661f4`, `NIH/NLM Malaria
Cell Images`, provider NLM/LHNCBC, versión 1.0.0 y referencia oficial LHNCBC. TFDS malaria
1.0.0 está registrado como distribución técnica, no origen clínico.

Existe exactamente una `Malaria Patient Split v1`, id
`d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`, semver 1.0.0, DRAFT, `patient_group`,
`patient_id`, algoritmo `patient_group_stratified_v1` 1.0.0, seed 42, targets
0.80/0.10/0.10, positiva `parasitized`, mapping 0=uninfected/1=parasitized y población
declarada 27.558. Tiene un solo source link, PRIMARY.

## 4. Población científica y Patient-ID

Consultas directas PostgreSQL reproducen 27.558 source records y 201 identidades PATIENT
únicas, todas VERIFIED. Los 27.558 records tienen exactamente una FK de identidad; hay
cero sin identidad, non-PATIENT, unresolved, conflict o múltiples identidades.

La distribución oficial persistida es 13.779 parasitized y 13.779 uninfected. Por
paciente: mínimo 65, máximo 702, 0 sólo parasitized, 50 sólo uninfected y 151 con ambas
clases. Resultado de población/identidad: PASS.

## 5. Identity evidence

Existen 27.558 evidencias y 27.558 records distintos cubiertos, sin ausencias ni
placeholders. Todas declaran `OFFICIAL_METADATA_AND_EXACT_PIXEL_MATCH`, nivel
`LEVEL_1_PLUS_LEVEL_4` y método `decoded_pixel_hash_to_official_metadata`. Cada JSON
preserva filename, decoded pixel SHA y cadena:

```text
source record → decoded RGB SHA-256 → original PNG/filename
→ official NLM/LHNCBC CSV → Patient-ID
```

Resultado evidence: PASS.

## 6. Hashes y provenance

Los 27.558 `source_file_sha256` y los 27.558 `decoded_pixel_sha256` están poblados y
cumplen 64 hexadecimales. Los dominios permanecen separados: el primero corresponde a
bytes del PNG fuente original; el segundo a `RGB.tobytes()` decodificado.

El dry-run volvió a localizar y hashear 27.558 PNG bajo el caché extraído de la
distribución oficial TFDS `cell_images.zip`, no bajo `malaria_physical_split`. Reprodujo
los SHA de mappings oficiales: parasitized
`d0367e513397404e980baee2a641bce9ce329a22e62ea9007962dfca2f8418d3` y uninfected
`a8577b21e7154724f4bbd18326218e2c63a99b22ab372b79a7530d36df6dab78`. El bootstrap
idempotente comparó cada hash preparado contra PostgreSQL sin conflicto. Resultado
provenance: PASS.

## 7. Estado vacío de v1

V1 permanece DRAFT y no entrenable, con reasons `DATASET_NOT_FROZEN`,
`VALIDATION_NOT_PASS` y `NO_READY_RECONCILED_MATERIALIZATION`. Tiene cero assignments,
statistics, validation checks, materializations y activations. SPLIT 3 aún no ocurrió.

## 8. Patient-disjoint y consistencia de assignments

Fixtures transaccionales permitieron múltiples records PAT-A→train y PAT-B→test. Insert
o update PAT-A→otro split fue rechazado por PostgreSQL. El trigger usa advisory
transaction lock determinístico por `(dataset_version, clinical_identity)` para cerrar
carreras concurrentes. El UNIQUE version+source record también fue confirmado.

Assignments con Patient-ID distinto al source record o con clase/index distintos fueron
rechazados por PostgreSQL. Resultados patient-disjoint, identity y class: PASS.

## 9. Lifecycle e inmutabilidad FROZEN

Se probaron las transiciones forward y archive permitidas, timestamps y rechazo de
retrocesos/ARCHIVED→mutable. Los campos científicos FROZEN son inmutables. INSERT,
UPDATE y DELETE de assignments FROZEN fueron rechazados, incluso intentando moverlos a
otra versión. Lo mismo ocurrió con source composition. Resultados: PASS.

La población global reutilizable no se bloquea. El fingerprint final de
población/identidad/assignments sigue explícitamente pendiente y rastreado para el freeze
coordinado de SPLIT 6, junto con checks y manifest sellados. No se implementa en 2D.

## 10. Single-active

El UNIQUE parcial por `dataset_family WHERE deactivated_at IS NULL` rechazó dos CURRENT,
permitió desactivar A y activar B, y conservó historial. Otro trigger rechazó una
activation cuya version no coincidía con la materialization. Resultado: PASS.

## 11. TRAINABLE, validations y materialization

TRAINABLE continúa derivado exclusivamente de FROZEN + logical validation PASS + READY +
reconciliation PASS. ACTIVE no participa. La matriz DRAFT/FAIL/FAILED/reconciliation FAIL
y los casos READY+PASS con/sin ACTIVE pasaron.

Los doce checks obligatorios están declarados explícitamente. El resolver toma el último
resultado por check; falta de un required check o cualquier blocking FAIL produce
`VALIDATION_NOT_PASS`, no un PASS por ausencia de fallas.

La materialization se resuelve sin input del usuario: READY+PASS, orden
`attempt_number DESC, completed_at DESC NULLS LAST, id DESC`. Los fixtures eligieron
attempt 2 sobre FAILED attempt 1 y luego attempt 3. Resultado: PASS.

## 12. Listado, autoselección y selección simple

El listado devolvió únicamente versiones entrenables en orden determinístico por
`frozen_at DESC NULLS LAST, id DESC`. La resolución default devolvió NONE/única/más
reciente para 0/1/N candidatos. La única dimensión que el usuario cambiará es
`dataset_version_id`; materialization, source, seed, assignments, path, activation,
validation y reconciliation son resueltos por el sistema. Resultado: PASS.

## 13. EVALUATE, calibraciones y producción

El contrato sigue siendo: EVALUATE estándar, threshold calibration y probability
calibration heredan `dataset_version_id` desde TRAIN. Threshold/probability usan val;
test no participa en fit ni calibraciones. No se modificó código real. Publishing sigue
requiriendo únicamente TRAIN completed + EVALUATE completed.

## 14. Legacy physical split y runs históricos

PostgreSQL conserva 27.558 `dataset_split_images`: train 22.046, val 2.756, test 2.756.
El filesystem contiene exactamente los mismos conteos. No existen FKs version/
materialization ni checksums backfilled en ese inventario por SPLIT 2.

Persisten 12 training y 12 evaluation; cero runs tienen `dataset_version_id` poblado.
No hubo lineage retroactivo especulativo. Resultado legacy/runs: PASS.

## 15. Bootstrap, pruebas y límites de scope

El dry-run completo pasó y no escribió. La reejecución idempotente retornó los mismos IDs
y dejó exactamente 2 datasets, 1 version, 201 identities, 27.558 records/evidences y cero
outputs de split. Los 15 tests focalizados 2C y la suite completa de 50 tests pasaron.

El único archivo creado por 2D es este informe. No se modificaron TRAIN, EVALUATE,
backend, frontend, active physical root ni regla productiva. `git diff --check` pasa.

## 16. Conclusión y readiness

Todos los 44 criterios de aprobación fueron verificados. PostgreSQL es una foundation
coherente, la población/identidad es completa, los invariantes impiden leakage e
inmutabilidad rota, y la UX futura conserva selección simple. SPLIT 2 queda APPROVED y
SPLIT 3 está READY para generar determinísticamente assignments patient-disjoint con
seed 42, todavía sin materializar archivos.
