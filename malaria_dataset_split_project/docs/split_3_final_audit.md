# Auditoría independiente final de SPLIT 3

Estado: **SPLIT_3=REJECTED; SPLIT_4_READY=NO**.

La evidencia científico-datos es íntegramente conforme. El rechazo se debe a dos gates
operacionales explícitos de SPLIT 3C: existe pérdida de cobertura ejecutable después de
que v1 dejó DRAFT, y el bootstrap dry-run no demuestra que reconoce la v1 PostgreSQL en
GENERATED. Esta auditoría no reparó silenciosamente ninguno de ellos y no modificó v1.

## 1. Propósito, dependencias y modo

Se auditó independientemente `Malaria Patient Split v1`, UUID
`d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`, sobre PostgreSQL 17.9. Se leyeron los contratos
de SPLIT 2, 3A.1, 3A.2, 3B.1 y 3B.2. La auditoría fue predominantemente read-only; la
única operación nominalmente APPLY fue la verificación de idempotencia exigida, que tomó
lock, reconoció el estado ya aplicado y revirtió sin cambios.

Alembic current y head son `20260812_02`. No hubo migration ni cambio de schema.

## 2. Población e identidad

PostgreSQL conserva 27.558 source records: 13.779 parasitized y 13.779 uninfected. Los
27.558 tienen identidad verificada; no hay registros sin identidad, unresolved ni
conflict. Existen 201 identidades PATIENT, todas VERIFIED y sin conflictos.

Los perfiles se reconstruyeron desde `dataset_source_records`, `clinical_identities` y la
composición PRIMARY de v1, sin usar assignments como entrada: 151 BOTH_CLASSES, 50
UNINFECTED_ONLY y cero PARASITIZED_ONLY. El tamaño global va de 65 a 702 células por
paciente (media 137,104478; mediana 85).

## 3. Algoritmo, randomización y optimización

Se reutilizó `patient_group_stratified_v1` 1.0.0, seed 42. La unidad randomizada continúa
siendo `clinical_identity_id`; el código ordena canónicamente pacientes y usa un
`random.Random(seed)` local. No randomiza imágenes, células ni source records.

Dos optimizaciones independientes desde la población PostgreSQL produjeron el mismo
digest `cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f`. El ganador
sigue siendo mejor que la baseline: objective ganador
`(0.02081972566949705, 0.009497206703910632, 0.004847957036069328,
0.0009950248756218638)` frente a baseline
`(0.2290550838232092, 0.14758751182592245, 0.08845344364612817,
0.06069651741293525)`.

## 4. Comparación regenerado contra PostgreSQL

La comparación explícita de los 201 pares Patient→Split produjo cero diferencias. La
cadena de fingerprints fue:

```text
APPROVED PATIENT = REGENERATED A = REGENERATED B = DATABASE
cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f

APPROVED RECORD = DATABASE
9709ce48b9b41bcacca49ccfb53ec62b48c4822c2fb8e227643bf26aed196ea2
```

## 5. Assignments, composición y hard constraints

Hay 27.558 assignments y 27.558 source records distintos, con cero unassigned y cero
multiassigned. Se asignaron los 201 pacientes, sin unassigned ni multi-split. La unión de
pacientes es 201 y los overlaps train-val, train-test y val-test son cero.

| Split | Records | Ratio records | Patients | Ratio patients | Parasitized | Uninfected |
|---|---:|---:|---:|---:|---:|---:|
| train | 22.180 | 0,8048479570 | 161 | 0,8009950249 | 11.137 | 11.043 |
| val | 2.693 | 0,0977211699 | 20 | 0,0995024876 | 1.325 | 1.368 |
| test | 2.685 | 0,0974308731 | 20 | 0,0995024876 | 1.317 | 1.368 |

Cada split contiene ambas clases. Perfiles: train 121 BOTH/40 UNINFECTED_ONLY; val
15/5; test 15/5. PostgreSQL tiene cero grupos y cero records en grupos de SHA-256 exactos
duplicados; duplicate cross-split overlap es cero.

## 6. Representatividad y objective recompuesto

| Split | Size min/max/mean/median | BOTH parasitized ratio min/max/mean/median |
|---|---|---|
| train | 65/702/137,763975/84 | 0,014286/0,901709/0,372410/0,288660 |
| val | 66/687/134,650000/87,5 | 0,068493/0,896652/0,392624/0,403509 |
| test | 68/568/134,250000/90,5 | 0,042857/0,882042/0,393903/0,345794 |

El evaluator aprobado reprodujo: patient profile deviation 0,0012437810945273853;
patient size deviation 0,02081972566949705; within-patient parasitized-ratio deviation
0,017349819485102058; class balance 0,009497206703910632; record ratio
0,004847957036069328; patient ratio 0,0009950248756218638. Auditoría objective: PASS.

## 7. Metadata, lifecycle y trainability

`methodology_json.generation_contract` conserva algoritmo/version, seed 42, unidad de
randomización, candidate id `candidate-cbe7a7b8c92d3761`, ambos digests, objective,
búsqueda y conteos. También preserva class mapping, grouping, hard constraints, identity
requirement, priorities y targets previos. Su hash JSON canónico observado fue
`33a0f9a88f1dc83718a4d2237f396f541c83b60e567e158bbd5a04606e3a1239`.

V1 permanece GENERATED con `generated_at=2026-08-13T09:00:52.387279-04:00`.
TRAINABLE es NO por `DATASET_NOT_FROZEN`, `VALIDATION_NOT_PASS` y
`NO_READY_RECONCILED_MATERIALIZATION`. Statistics, validation checks, materializations y
current activations siguen en cero.

## 8. Persistencia, rehearsal e idempotencia

3B.1 demostró la transacción única con lock NOWAIT, bulk insert, auditorías y rollback;
3B.2 realizó el commit oficial. En 3C se capturaron status, generated_at, count, ambos
digests y hash de methodology antes/después de `persist-patient-split-v1 --apply`.
El comando devolvió `already_applied=true`, hizo rollback/no-op y los seis valores fueron
idénticos. Auditoría idempotente: PASS.

## 9. Bootstrap después de GENERATED — bloqueador

`bootstrap-malaria-v1 --dry-run` pasó su reconstrucción de filesystem: 27.558 records,
201 pacientes, 100 % identidad y composición exacta. Sin embargo, el camino dry-run no
abre PostgreSQL: no consulta ni reporta que v1 ya existe, status GENERATED, assignments
27.558 o generated_at. Por ello no satisface el gate explícito
`BOOTSTRAP_GENERATED_DRY_RUN_AUDIT`; resultado FAIL. No se ejecutó bootstrap APPLY.

Corrección mínima futura: ampliar exclusivamente el reporte read-only del dry-run para
consultar v1 y declarar compatibilidad con GENERATED sin actualizar metadata, lifecycle
ni assignments; añadir un test post-GENERATED transaccional/read-only.

## 10. Auditoría de los tres skips — bloqueador

1. `test_failure_after_partial_real_bulk_insert_is_atomic`, en
   `tests/integration/test_split_generation_rehearsal.py`: se omite porque el fixture de
   rehearsal exige DRAFT. Invariante: rollback total tras fallo parcial real. No existe
   cobertura activa equivalente de esa frontera de persistencia. Riesgo: medio-alto.
2. `test_digest_mismatch_aborts_before_writes`, mismo archivo: se omite porque v1 ya es
   GENERATED. Invariante: digest incorrecto aborta antes de escribir. No existe cobertura
   activa equivalente. Riesgo: medio.
3. `test_assignment_invariant_triggers_remain_enabled`, mismo archivo: se omite porque su
   mutación usa v1 DRAFT. Invariante: triggers activos y rechazo de identidad incorrecta.
   `test_assignment_identity_and_class_consistency` continúa ejecutándose con fixture
   transaccional y cubre el rechazo de identidad/clase; la inspección explícita de
   `tgenabled` queda omitida. Riesgo residual: bajo.

El lock NOWAIT sí continúa ejecutándose y preserva el estado observado. Same-seed,
patient-disjoint, consistencia identity/class y lifecycle/FROZEN tienen cobertura activa.
No obstante, los skips 1 y 2 dejan cobertura crítica sin equivalente. Por la regla 45:
`POST_GENERATED_TEST_COVERAGE_GAP=YES`.

Corrección mínima futura: usar una dataset version DRAFT temporal y reversible dentro de
la misma DB para atomicidad/digest mismatch, nunca degradar v1; mantener rollback de la
fixture. Este hallazgo no fue corregido dentro de 3C.

## 11. Legacy, runs y separación lógica/física

`dataset_split_images` conserva 27.558 filas y cero están backfilled a v1. El filesystem
legacy tiene 27.558 imágenes: train 22.046, val 2.756, test 2.756. PostgreSQL contiene el
nuevo split lógico GENERATED 22.180/2.693/2.685; la diferencia es intencional hasta
SPLIT 5, no una inconsistencia.

Existen 12 runs training y 12 evaluation históricos; cero runs están vinculados a v1.
También existen 12 explainability y 1 inference, igualmente sin atribución v1. El diff
de SPLIT 3 no incluye TRAIN, EVALUATE, backend ni frontend. La regla productiva continúa
TRAIN completed + EVALUATE completed. Test permanece reservado a evaluación final; val
se usa para checkpoint/threshold/probability calibration.

## 12. Tests, limitaciones y conclusión

La suite terminó con 65 passed y 3 skipped; `git diff --check` pasó. La corrección de una
aserción obsoleta del lock ya forma parte del commit 3B.2, pero los dos huecos descritos
persisten. No se crearon statistics/checks, no se cambió a VALIDATED, no se materializó,
no se activó y no se entrenó.

La conclusión científica sobre el split es favorable: población, reproducibilidad,
digests, composición, disjointness, duplicados, objective, metadata e idempotencia son
PASS. La conclusión formal de SPLIT 3C es, no obstante, REJECTED por las reglas de rechazo
obligatorias `BOOTSTRAP_GENERATED_DRY_RUN_AUDIT=FAIL` y
`POST_GENERATED_TEST_COVERAGE_GAP=YES`. SPLIT 4 no está habilitado hasta resolver ambos
con cambios mínimos, seguros y explícitamente revisados.
