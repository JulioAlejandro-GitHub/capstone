# Validación científica formal — SPLIT 4

Estado: **SPLIT_4=APPROVED; SPLIT_5_READY=YES**.

## 1. Versión y precondiciones

Se validó exclusivamente `Malaria Patient Split v1`, UUID
`d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`, después del cierre APPROVED de SPLIT 3.
Alembic current/head permaneció `20260812_02`; el schema existente soportó statistics y
checks, por lo que no hubo migration.

Antes de escribir, PostgreSQL confirmó GENERATED, 27.558 assignments y cero statistics,
checks, materializations y activations. La prevalidación fue completamente read-only.

## 2. Fingerprints y estadísticas

Los gates SHA-256 reprodujeron:

```text
Patient assignment: cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f
Record assignment:  9709ce48b9b41bcacca49ccfb53ec62b48c4822c2fb8e227643bf26aed196ea2
```

Se persistió un único snapshot oficial `formal_scientific_validation_v1` en
`dataset_split_statistics.details_json`:

| Split | Records | Record ratio | Patients | Patient ratio | Parasitized | Uninfected | BOTH/UO |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 22.180 | 0,8048479570 | 161 | 0,8009950249 | 11.137 | 11.043 | 121/40 |
| val | 2.693 | 0,0977211699 | 20 | 0,0995024876 | 1.325 | 1.368 | 15/5 |
| test | 2.685 | 0,0974308731 | 20 | 0,0995024876 | 1.317 | 1.368 | 15/5 |

Totales: 27.558 source records, 201 pacientes, 13.779 parasitized y 13.779 uninfected.
El snapshot incluye ambos fingerprints y cero pacientes PARASITIZED_ONLY.

## 3. Checks formales

La prevalidación calculó 12/12 PASS y cero FAIL. La transacción persistió exactamente una
fila oficial para cada nombre requerido:

| Check | Observado | Esperado | Estado |
|---|---:|---:|---|
| identity_coverage | 27558 | 27558 | PASS |
| identity_conflicts | 0 | 0 | PASS |
| patient_train_val_overlap | 0 | 0 | PASS |
| patient_train_test_overlap | 0 | 0 | PASS |
| patient_val_test_overlap | 0 | 0 | PASS |
| duplicate_cross_split_overlap | 0 | 0 | PASS |
| assignment_count | 27558 | 27558 | PASS |
| source_record_count | 27558 | 27558 | PASS |
| split_completeness | complete | complete | PASS |
| class_presence_train | both | both | PASS |
| class_presence_val | both | both | PASS |
| class_presence_test | both | both | PASS |

`split_completeness` registró cero source records sin asignar o multiassigned, cero
pacientes sin asignar o multi-split y cero nombres de split inválidos. Todos los checks
son blocking para validation y freeze.

## 4. Transacción y lifecycle

La única transacción oficial tomó `FOR UPDATE NOWAIT`, revalidó GENERATED/0/0, insertó el
snapshot y los 12 checks, verificó 12 PASS y utilizó el lifecycle service para
GENERATED→VALIDATED. El commit registró
`validated_at=2026-08-13T15:58:49.791368-04:00`.

Fixtures independientes demostraron que un check FAIL bloquea lifecycle sin writes y que
un fallo después de insertar las 12 filas revierte statistics, checks y status mediante
rollback PostgreSQL real.

## 5. Postcommit, trainability e idempotencia

Una conexión nueva confirmó VALIDATED, un snapshot y 12 checks PASS. TRAINABLE permanece
NO. `VALIDATION_NOT_PASS` desapareció; las razones restantes son
`DATASET_NOT_FROZEN` y `NO_READY_RECONCILED_MATERIALIZATION`.

La segunda ejecución recalculó fingerprints, statistics y checks, comparó el estado
persistido y devolvió `ALREADY_VALIDATED_MATCH_NO_OP`. No duplicó filas ni cambió
`validated_at`. Un estado VALIDATED con statistics/checks distintos produce
`VALIDATED_STATE_CONFLICT` y nunca se repara silenciosamente.

## 6. Tests, legacy y alcance pendiente

La suite completa postcommit terminó con 74 passed, 0 skipped y 0 failed. El filesystem
legacy continúa con 27.558 imágenes (22.046/2.756/2.756), `dataset_split_images` conserva
27.558 filas y no se modificaron TRAIN, EVALUATE, backend, frontend ni publishing.

SPLIT 4 no creó materializations ni activations y no cambió a FROZEN. SPLIT 5 queda
autorizado para materialización física versionada, manifest, hashes y reconciliation;
sólo después podrán evaluarse los requisitos de freeze/activation previstos por el
contrato arquitectónico.
