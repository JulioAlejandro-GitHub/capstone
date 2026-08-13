# Patient split persistido oficialmente — SPLIT 3B.2

## 1. Objetivo y dependencia

SPLIT 3B.2 realizó el primer COMMIT científico definitivo de `Malaria Patient Split v1`
después del rehearsal 3B.1. No rediseñó algoritmo, objective, randomización, búsqueda,
tie-break ni candidato. Reutilizó `malaria_split.persistence.split_generation` y la misma
frontera transaccional; el único cambio fue modo APPLY en vez de REHEARSE.

## 2. Preflight y regeneración

Alembic current/head eran `20260812_02`; no se necesitó migration. V1 estaba DRAFT con
cero assignments/statistics/checks/materializations/activations y TRAINABLE false. La
población seguía en 27.558 records, 201 Patient-ID verificados y cero conflictos.

El candidato se reconstruyó desde PostgreSQL con `patient_group_stratified_v1` 1.0.0,
seed 42. El digest prewrite coincidió con
`cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f`; no se usó JSON,
filesystem o split legacy como autoridad.

## 3. Transacción, lock y bulk insert

Una transacción única adquirió `SELECT ... FOR UPDATE NOWAIT`, revalidó DRAFT/0 y envió
27.558 assignments mediante SQLAlchemy executemany en batches de 1.000 sin commits por
batch. Patient-disjoint, identity/class consistency, uniqueness y lifecycle triggers
permanecieron activos.

## 4. Auditorías pre-commit

PostgreSQL reprodujo exactamente:

```text
records train/val/test: 22180 / 2693 / 2685
patients train/val/test: 161 / 20 / 20
train classes: 11137 parasitized / 11043 uninfected
val classes:    1325 parasitized /  1368 uninfected
test classes:   1317 parasitized /  1368 uninfected
profiles train: 121 BOTH_CLASSES / 40 UNINFECTED_ONLY
profiles val:    15 BOTH_CLASSES /  5 UNINFECTED_ONLY
profiles test:   15 BOTH_CLASSES /  5 UNINFECTED_ONLY
patient overlap: 0
duplicate cross-split overlap: 0
```

Los 201 patients y 27.558 source records quedaron completos y únicos. El digest Patient
persistido coincidió con `cbe7...ea7f`; el digest record-level coincidió con
`9709ce48b9b41bcacca49ccfb53ec62b48c4822c2fb8e227643bf26aed196ea2`.

## 5. Methodology y lifecycle

El service hizo merge controlado bajo `methodology_json.generation_contract`; preservó
class mapping, grouping, hard constraints, identity requirement, priorities, seed y
targets previos. Añadió algoritmo/version, randomization, objective/function/priority,
multi-start, búsqueda MOVE/SWAP, tie-break, candidate/digests y conteos oficiales.

Sólo después de todas las auditorías utilizó el lifecycle service para DRAFT→GENERATED.
El trigger registró `generated_at=2026-08-13T09:00:52.387279-04:00`. Antes del commit
TRAINABLE seguía false. La transacción hizo COMMIT.

## 6. Auditoría post-commit

Una connection nueva confirmó GENERATED, 27.558 assignments, todos los conteos/hard
constraints y ambos digests. Statistics, validation checks, materializations y
activations permanecen en cero. TRAINABLE sigue false: GENERATED no equivale a FROZEN,
validated ni materialized.

## 7. Segundo APPLY e idempotencia

El segundo `persist-patient-split-v1 --apply` regeneró el candidato, tomó el lock y
detectó GENERATED con 27.558 filas y ambos digests aprobados. Retornó
`already_applied=true` y NO-OP. No insertó, actualizó metadata, repitió lifecycle ni
cambió `generated_at`.

Si una futura ejecución encuentra GENERATED con count o digest diferente, el service
lanza `GENERATED_STATE_CONFLICT`; no borra, sobrescribe, retrocede ni repara. Cambiar
pacientes, seed, ratios, metodología o assignments requiere una nueva Dataset Version
DRAFT.

## 8. Legacy y separación lógica/física

`dataset_split_images` conserva 27.558 filas legacy sin backfill y los runs históricos
siguen sin `dataset_version_id`. El filesystem activo continúa siendo el split image-level
legacy 22.046/2.756/2.756. PostgreSQL contiene ahora el nuevo split lógico GENERATED,
pero no existe materialización física v1 ni activation. Esta separación es intencional.

No se modificaron TRAIN, EVALUATE, backend, frontend o publishing; la regla productiva
sigue TRAIN completed + EVALUATE completed.

## 9. Próximas etapas

SPLIT 3C debe auditar predominantemente read-only el estado persistido y ambos digests.
SPLIT 4 persistirá estadísticas y validation checks formales. Materialización/activación
e integración de ejecución permanecen para SPLIT 5/6 según el contrato arquitectónico.
