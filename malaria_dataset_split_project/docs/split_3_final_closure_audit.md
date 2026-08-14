# Acta final de cierre formal de SPLIT 3

Estado: **SPLIT_3=APPROVED; SPLIT_4_READY=YES**.

## 1. Objetivo y arquitectura

SPLIT 3 convirtió la población científica de malaria ya gobernada por SPLIT 1/2 en una
asignación lógica reproducible y patient-disjoint. PostgreSQL es la autoridad; Patient-ID
es la unidad indivisible. Los assignments preceden a validation, statistics y
materialization. El filesystem legacy no fue entrada del algoritmo ni fue modificado.

La evidencia previa fijó 27.558 células NLM/LHNCBC, 201 Patient-ID con identidad 100 %
verificada, clases globales balanceadas 13.779/13.779 y cero duplicados exactos.

## 2. Trazabilidad completa y gobernanza

```text
SPLIT 3A.1  contrato de perfiles/objective             APPROVED
SPLIT 3A.2  optimización y selección reproducible      APPROVED
SPLIT 3B.1  rehearsal transaccional con rollback       APPROVED
SPLIT 3B.2  persistencia oficial                       APPROVED
SPLIT 3C    auditoría #1                               REJECTED
             ├─ POST_GENERATED_TEST_COVERAGE_GAP
             └─ BOOTSTRAP GENERATED GAP
SPLIT 3C.1  acción correctiva acotada                  APPROVED
SPLIT 3C    reauditoría final independiente            APPROVED
```

La primera auditoría rechazada se preserva en `split_3_final_audit.md`. 3C.1 trasladó
los tests mutables a versiones DRAFT transaccionales propias y añadió reconocimiento
read-only de la v1 GENERATED al bootstrap. Esta reauditoría no asumió esa aprobación:
repitió consultas, regeneración, tests, bootstrap y verificación idempotente.

## 3. SPLIT 3A.1 y perfiles

Los perfiles se reconstruyeron exclusivamente desde la fuente PRIMARY PostgreSQL, sin
usar assignments: 201 pacientes, 151 BOTH_CLASSES, 50 UNINFECTED_ONLY, cero
PARASITIZED_ONLY; tamaños 65–702. Cada perfil agrupa sus records, clases y source SHA por
`clinical_identity_id`.

3A.1 fijó hard gates de completeness, Patient disjointness, split válido, duplicate
exact-file cross-split cero y presencia de ambas clases. Fijó un objective lexicográfico:
representatividad, balance de clase, ratio de records, ratio de pacientes y digest como
tie-break.

## 4. SPLIT 3A.2, algoritmo y randomización

El algoritmo es `patient_group_stratified_v1` 1.0.0, seed 42. La secuencia parte de orden
canónico y usa PRNG local; la unidad randomizada es `clinical_identity_id`, nunca imagen,
célula o source record. La búsqueda acotada multi-start opera con MOVE/SWAP de pacientes
completos.

El ganador `candidate-cbe7a7b8c92d3761` mejoró la baseline en todos los niveles. En esta
reauditoría dos ejecuciones nuevas desde la población PostgreSQL produjeron exactamente:

```text
cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f
```

La comparación explícita de los 201 mappings regenerados contra PostgreSQL produjo cero
diferencias.

## 5. Objective recompuesto

El evaluator aprobado, aplicado a la asignación persistida, reprodujo:

| Componente | Valor |
|---|---:|
| patient profile deviation | 0.0012437810945273853 |
| patient size representativeness | 0.02081972566949705 |
| within-patient parasitized-ratio | 0.017349819485102058 |
| class balance | 0.009497206703910632 |
| record ratio | 0.004847957036069328 |
| patient ratio | 0.0009950248756218638 |

Objective final: `(0.02081972566949705, 0.009497206703910632,
0.004847957036069328, 0.0009950248756218638)`. Auditoría: PASS.

## 6. SPLIT 3B.1 y 3B.2

3B.1 ejercitó preparación, lock `FOR UPDATE NOWAIT`, bulk insert PostgreSQL, auditorías,
lifecycle y rollback único. 3B.2 reutilizó esa misma frontera para el primer commit
oficial. V1 permanece GENERATED desde `2026-08-13T09:00:52.387279-04:00`.

La reauditoría confirmó 27.558 assignments, 27.558 source records distintos y 201
pacientes distintos; cero records/pacientes sin asignar y cero multiassignment.

## 7. Fingerprints

La cadena Patient aprobada, regenerada A, regenerada B y reconstruida desde DB coincide:

```text
cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f
```

El digest de 27.558 líneas `source_record_id|clinical_identity_id|split_name` reconstruido
desde DB coincide con el aprobado:

```text
9709ce48b9b41bcacca49ccfb53ec62b48c4822c2fb8e227643bf26aed196ea2
```

## 8. Composición, leakage, duplicates y clases

| Split | Patients | Patient ratio | Records | Record ratio | Parasitized | Uninfected | Profiles BOTH/UO |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 161 | 0.8009950249 | 22.180 | 0.8048479570 | 11.137 | 11.043 | 121/40 |
| val | 20 | 0.0995024876 | 2.693 | 0.0977211699 | 1.325 | 1.368 | 15/5 |
| test | 20 | 0.0995024876 | 2.685 | 0.0974308731 | 1.317 | 1.368 | 15/5 |

Los overlaps patient train-val, train-test y val-test son cero; la unión contiene los 201
pacientes. Existen cero grupos y cero records duplicados exactos por source SHA, y cero
duplicate cross-split overlap. Cada split contiene ambas clases.

## 9. Metodología, lifecycle y trainability

`methodology_json.generation_contract` conserva algoritmo/version, seed, randomization
unit, candidate id, objective y ambos digests. También preserva la metadata previa:
class mapping, grouping, hard constraints, identity requirement, priorities, positive
class y targets.

Alembic current/head es `20260812_02`; no se requiere schema change. V1 sigue GENERATED,
no VALIDATED. El resolver devuelve TRAINABLE=NO por `DATASET_NOT_FROZEN`,
`VALIDATION_NOT_PASS` y `NO_READY_RECONCILED_MATERIALIZATION`. Statistics, validation
checks, materializations y activations siguen en cero.

## 10. Cobertura post-GENERATED

La suite completa pasó con `71 passed, 0 skipped, 0 failed`. En particular:

- atomic failure usa una Dataset Version DRAFT temporal, inserta 1.000 filas reales y
  demuestra rollback PostgreSQL a DRAFT/0;
- digest mismatch usa fixture DRAFT temporal y demuestra cero writes antes del abort;
- trigger activo rechaza identidad incorrecta sobre fixture temporal;
- pruebas 2C activas cubren patient-disjointness, source uniqueness y coherencia de
  identidad/clase;
- lock NOWAIT y same-seed reproducibility continúan activos.

Snapshots antes y después de la suite —status, generated_at, count, ambos digests y hash
de methodology— fueron idénticos. Critical skipped tests=0 y coverage gap=NO.

## 11. Bootstrap e idempotencia

`bootstrap-malaria-v1 --dry-run` reconstruyó la población y reconoció la v1 por UUID,
semver, fuente, Patient-ID, source keys/hashes y metodología base. Reportó GENERATED,
27.558 assignments, lifecycle accepted, zero writes y
`ALREADY_BOOTSTRAPPED_AND_ADVANCED`. Tests conservan rechazo de conflictos de identidad,
source hash y metodología base. El snapshot no cambió.

Un nuevo `persist-patient-split-v1 --apply` regeneró el candidato, auditó DB y devolvió
`already_applied=true` con rollback/no-op. Status, generated_at, assignments, ambos
digests y methodology permanecieron idénticos.

## 12. Legacy, runs y separación lógica/física

PostgreSQL conserva 27.558 `dataset_split_images`, cero backfilled a v1. El filesystem
legacy continúa 22.046/2.756/2.756. El split lógico PostgreSQL es
22.180/2.693/2.685. Esta diferencia es intencional hasta materialización en SPLIT 5.

Persisten 12 TRAIN y 12 EVALUATE históricos; cero runs están vinculados a v1. No se
modificaron TRAIN, EVALUATE, backend ni frontend. El contrato sigue: train para fitting;
val para checkpoint y calibraciones; test sólo para evaluación final. Publishing sigue
requiriendo TRAIN completed + EVALUATE completed.

## 13. Límites y trabajo aún no realizado

SPLIT 3 no persistió statistics ni validation checks, no cambió a VALIDATED, no creó
materialización, no reconcilió archivos, no congeló ni activó una versión, y no integró
el nuevo split a TRAIN/EVALUATE. Estos límites son deliberados.

## 14. Conclusión y SPLIT 4 readiness

Los 56 gates de cierre pasaron y no surgieron hallazgos nuevos. La falla de la primera
auditoría quedó trazada y su corrección fue verificada independientemente. SPLIT 3 queda
formalmente APPROVED y SPLIT 4 está autorizado para persistir statistics y los doce
validation checks gobernados. Sólo si éstos pasan corresponderá GENERATED→VALIDATED;
todavía sin materialización física.
