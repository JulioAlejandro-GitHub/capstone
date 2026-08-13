# Ensayo transaccional de persistencia — SPLIT 3B.1

## 1. Candidato y regeneración

El rehearsal trabajó exclusivamente con v1
`d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`, algoritmo
`patient_group_stratified_v1` 1.0.0 y seed 42. Antes de escribir, reconstruyó los 201
Patient Profiles desde PostgreSQL, ejecutó la optimización aprobada y reprodujo el digest
`cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f`.

No se leyó un JSON de assignments. El mapping se expandió consultando los 27.558 source
records PostgreSQL; cada fila heredó el split de `clinical_identity_id`. Los hashes no
participaron en la selección y sólo se usaron en la auditoría de duplicados.

## 2. Servicio único y boundary transaccional

`malaria_split.persistence.split_generation` concentra preparación y persistencia. La
misma función `persist_split_generation` acepta `REHEARSE` o `APPLY`; 3B.1 invoca sólo
REHEARSE. No existe una segunda implementación para el futuro commit.

La preparación read-only se realiza antes de la transacción larga. Luego una única
connection abre BEGIN, adquiere `SELECT ... FOR UPDATE NOWAIT` sobre v1, revalida
DRAFT/0 y ejecuta batches executemany de 1.000 filas. No hay commits internos y ningún
trigger se desactiva.

## 3. Auditoría dentro de PostgreSQL

Con las filas temporalmente persistidas, PostgreSQL reprodujo:

```text
assignments/source records/patients: 27558 / 27558 / 201
records train/val/test: 22180 / 2693 / 2685
patients train/val/test: 161 / 20 / 20
classes train: 11137 parasitized / 11043 uninfected
classes val:    1325 parasitized /  1368 uninfected
classes test:   1317 parasitized /  1368 uninfected
profiles train: 121 BOTH / 40 UNINFECTED_ONLY
profiles val:    15 BOTH /  5 UNINFECTED_ONLY
profiles test:   15 BOTH /  5 UNINFECTED_ONLY
patient overlap: 0
duplicate cross-split overlap: 0
```

El digest Patient→split reconstruido con rows PostgreSQL fue exactamente el aprobado.
El control adicional, SHA-256 de líneas
`source_record_id|clinical_identity_id|split_name` ordenadas por source_record_id, fue
`9709ce48b9b41bcacca49ccfb53ec62b48c4822c2fb8e227643bf26aed196ea2`.

## 4. Metadata y lifecycle

El rehearsal preparó `methodology_json.generation_contract` sin reemplazar provenance
previa: algoritmo/version/seed, unidad y método de randomización, objective/priority,
multi-start, búsqueda local, tie-break, digest/candidate y conteos aprobados. Después de
auditar assignments y digests actualizó esa metadata dentro de la misma transacción y
usó `transition_dataset_version` para DRAFT→GENERATED. El trigger estableció
`generated_at`.

Temporalmente se observaron GENERATED y 27.558 assignments. TRAINABLE continuó false
porque no hay formal validation PASS, materialization READY ni reconciliation PASS.

## 5. Rollback y atomicidad

Se ejecutó ROLLBACK obligatorio. Una connection nueva confirmó DRAFT y cero assignments;
statistics, validation checks, materializations y activations permanecieron en cero. La
metadata y `generated_at` temporales también fueron revertidos por la misma transacción.

El test de fallo insertó un batch real parcial de 1.000 assignments con triggers activos,
levantó una excepción y verificó DRAFT/0 desde otra connection. Un expected digest falso
abortó durante preparación antes de cualquier escritura. El test de concurrencia mantuvo
un row lock y confirmó que un segundo `FOR UPDATE NOWAIT` fue rechazado. Finalmente, se
verificó `tgenabled='O'` y un assignment con Patient-ID incorrecto fue rechazado por el
trigger.

## 6. CLI, filesystem y readiness

CLI ejecutada:

```text
python -m malaria_split.cli persist-patient-split-v1 --rehearse
```

No fue necesaria migration. No se crearon statistics/checks/materializations ni archivos;
el split activo, TRAIN, EVALUATE, backend, frontend y regla productiva permanecen
intactos. SPLIT 3B.2 puede invocar el mismo servicio en APPLY después de repetir
preflight, digest y auditorías; ésa será la primera autorización de COMMIT.
