# Invariantes, lifecycle y resolución TRAINABLE — SPLIT 2C

## 1. Objetivo y migrations

SPLIT 2C protege PostgreSQL antes de que SPLIT 3 genere assignments. Las revisiones
aditivas `20260812_01_scientific_dataset_invariants_and_trainability.py` y
`20260812_02_harden_frozen_assignment_updates.py` siguen el head canónico y no contienen
backfill. La segunda endurece explícitamente updates que intenten mover un assignment
desde o hacia una versión FROZEN.

## 2. Invariantes de assignment

Un trigger `BEFORE INSERT OR UPDATE` carga identidad y clase desde
`dataset_source_records` y rechaza cualquier discrepancia con el assignment. La
redundancia de `class_index/class_name` se conserva por compatibilidad, pero no puede
reinterpretar el source record.

Patient-disjointness se garantiza por `(dataset_version_id, clinical_identity_id)`: el
trigger toma un advisory transaction lock determinístico para ese par y rechaza un
`split_name` distinto al ya persistido. El lock evita carreras de dos transacciones
concurrentes. Varias células del mismo paciente en el mismo split siguen permitidas. El
UNIQUE existente `(dataset_version_id, source_record_id)` evita asignar dos veces una
observación dentro de una versión.

## 3. Lifecycle y timestamps

Transiciones permitidas:

```text
DRAFT     → GENERATED | ARCHIVED
GENERATED → VALIDATED | ARCHIVED
VALIDATED → FROZEN | ARCHIVED
FROZEN    → ARCHIVED
ARCHIVED  → ninguna
```

Archivar desde estados mutables permite cancelar una versión sin borrarla. El trigger
rechaza retrocesos y rellena el timestamp correspondiente al entrar en GENERATED,
VALIDATED, FROZEN o ARCHIVED. El service `transition_dataset_version` valida la misma
máquina de estados y bloquea la fila; PostgreSQL sigue siendo la defensa definitiva.

## 4. Inmutabilidad FROZEN

Desde FROZEN no pueden cambiar nombre/semver, grouping, stratification, algoritmo,
versión del algoritmo, seed, ratios, clase positiva, class mapping, source count ni
methodology JSON. Sólo se permite el cambio lifecycle FROZEN→ARCHIVED sin mutar esos
campos.

Assignments FROZEN rechazan INSERT, UPDATE y DELETE, incluso si un UPDATE intenta mover
la fila a otra versión. La composición `dataset_version_sources` rechaza INSERT, UPDATE
y DELETE cuando OLD o NEW pertenece a una versión FROZEN.

La población fuente global no se bloquea por existir una versión FROZEN, porque los
source records son reutilizables entre versiones. Su protección efectiva se compone de
source links inmutables, `source_record_count`, assignments inmutables y, al freeze final
de SPLIT 6, checks completos más fingerprint sellado de población/identidad/assignments.

## 5. Single-current y ACTIVE

El índice parcial UNIQUE de 2A sobre `dataset_family WHERE deactivated_at IS NULL`
garantiza máximo una activación vigente y permite historial desactivado. Un trigger
adicional exige que activation y materialization pertenezcan a la misma version.

ACTIVE sólo define default/root operacional. No participa en TRAINABLE y las pruebas
demuestran que READY+PASS puede ser entrenable con o sin activation.

## 6. TRAINABLE derivado

`get_dataset_version_trainability` devuelve booleano, materialización resuelta y reasons:

```text
DATASET_NOT_FROZEN
VALIDATION_NOT_PASS
NO_READY_RECONCILED_MATERIALIZATION
```

TRAINABLE exige simultáneamente FROZEN, logical validation PASS y al menos una
materialización READY con reconciliation PASS. No se persiste un status TRAINABLE.

Logical validation usa el resultado más reciente por nombre (`executed_at,id`) y exige
los doce checks blocking en PASS: `identity_coverage`, `identity_conflicts`, tres
patient overlaps, `duplicate_cross_split_overlap`, `assignment_count`,
`source_record_count`, `split_completeness` y presencia de clase en train/val/test. Un
check requerido ausente o cualquier blocking FAIL impide TRAINABLE.

## 7. Resolución de materialización

El usuario no elige `materialization_id`. Entre candidatos READY+PASS se selecciona
determinísticamente `attempt_number DESC`, luego `completed_at DESC NULLS LAST` y `id
DESC`. Cero candidatos significa no disponible. Esta resolución es estable para el mismo
estado PostgreSQL.

## 8. Lista, default y selección simple

`list_trainable_dataset_versions` devuelve únicamente candidatos entrenables con id,
nombre, semver, status, metodología, grouping, frozen_at y materialization resuelta. Se
ordenan por `frozen_at DESC NULLS LAST, id DESC`; no se asume que strings arbitrarios
sean semver comparables.

`resolve_default_trainable_dataset_version` retorna NONE con cero candidatos, el único
con uno y el primero determinístico con varios. Con múltiples versiones, el usuario sólo
puede cambiar `dataset_version_id`. Source, seed, split, método, materialization, path,
activation y checks son derivados.

## 9. Run, EVALUATE y calibraciones

El contrato futuro registra `runs.dataset_version_id` y un snapshot de la materialización
resuelta; el helper de dominio rechaza cambiar cualquiera después de persistir. No se
modificó TRAIN real.

EVALUATE estándar hereda la versión desde TRAIN. External validation será un flujo
explícito separado. Threshold y probability calibration también heredan la versión y
usan exclusivamente `val`; test sigue fuera de fit y calibraciones. La regla productiva
permanece TRAIN completed + EVALUATE completed.

## 10. Pruebas y alcance diferido

Fixtures en `malaria_experiments` usan transacciones/savepoints con rollback y nunca
alteran v1. Cubren patient-disjoint, coherencia identity/class, uniqueness, lifecycle,
freeze, source composition, single-current, matriz TRAINABLE, checks ausentes,
resolución por attempts, lista y autoselección.

SPLIT 2D deberá completar únicamente el alcance que su contrato defina; no se anticipa
aquí. SPLIT 3 generará por primera vez los 27.558 assignments patient-disjoint. SPLIT 4
poblará checks reales y SPLIT 6 coordinará freeze/fingerprint, snapshot del run e
integración TRAIN/EVALUATE/UI.
