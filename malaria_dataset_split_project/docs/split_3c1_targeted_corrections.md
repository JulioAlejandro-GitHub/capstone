# Correcciones acotadas post-GENERATED — SPLIT 3C.1

Estado: **SPLIT_3C1=APPROVED; SPLIT_3C_REAUDIT_READY=YES**.

## 1. Motivo y alcance

La primera auditoría 3C rechazó SPLIT 3 por dos motivos operacionales, no científicos:
dos pruebas críticas dependían de que la v1 oficial estuviera DRAFT y el bootstrap
dry-run reconstruía la población pero no reconocía explícitamente la v1 PostgreSQL ya
GENERATED. 3C.1 corrigió exclusivamente esos dos puntos. No cambió algoritmo, optimizer,
objective, assignments, lifecycle real, schema, filesystem ni integración operacional.

## 2. Fixture DRAFT transaccional

`test_split_generation_rehearsal.py` crea para cada ensayo una Dataset Version con UUID
único dentro de una transacción exterior. Copia el contrato científico de v1 y enlaza la
misma fuente PRIMARY sin duplicar ni modificar source records o identidades. Su estado es
DRAFT y sus assignments iniciales son cero. Al terminar se ejecuta rollback y una nueva
conexión confirma cero versiones y cero assignments con el UUID temporal.

La fixture captura además status, generated_at, assignment count, Patient digest, Record
digest y hash canónico de methodology de la v1 oficial. El teardown exige que el snapshot
posterior sea idéntico.

## 3. Atomic failure y digest mismatch

El test de atomicidad prepara las 27.558 filas mediante el servicio científico real,
inserta un batch real de 1.000 filas PostgreSQL dentro de un savepoint, observa esas
1.000 filas, simula el fallo y revierte el savepoint. Luego confirma DRAFT y cero
assignments. No se mockeó la operación PostgreSQL central.

El test de digest mismatch regenera desde la población PostgreSQL para la versión
temporal con un expected digest deliberadamente falso. `DigestMismatch` ocurre durante
preparación, antes del primer INSERT; PostgreSQL confirma DRAFT y cero assignments.

## 4. Triggers y cobertura crítica

El antiguo test omitido de triggers usa ahora la misma fixture temporal. Comprueba que
todos los triggers no internos de assignments están `tgenabled='O'`, intenta insertar un
assignment con identidad incorrecta y PostgreSQL lo rechaza. La suite 2C mantiene además
cobertura activa separada para patient-disjointness, identity/class consistency y unique
source assignment.

## 5. Bootstrap GENERATED read-only

`bootstrap-malaria-v1 --dry-run` sigue reconstruyendo archivos, mapping oficial, hashes e
identidades. Después abre una conexión exclusivamente de lectura y verifica:

- UUID, nombre y semver canónicos;
- grouping, stratification, algoritmo/version, seed, targets y class mapping;
- una fuente PRIMARY con provider/reference/version esperados;
- fingerprints de los mappings oficiales;
- los 201 Patient-ID verificados;
- las 27.558 source keys, paciente, clase, source SHA y decoded-pixel SHA;
- los campos base de methodology como subconjunto de la metadata extendida por SPLIT 3;
- lifecycle DRAFT/0 o GENERATED/27.558 como pares coherentes.

Para la v1 real devolvió `ALREADY_BOOTSTRAPPED_AND_ADVANCED`, status GENERATED,
assignment count 27.558 y `dry_run_database_writes=0`. Snapshots criptográficos antes y
después fueron idénticos. El código no contiene UPDATE, INSERT, DELETE ni transición en
esta ruta.

## 6. Preservación de conflictos científicos

La comparación por subconjunto sólo permite campos adicionales gobernados; no relaja los
campos base. Tests activos rechazan seed base diferente, Patient-ID diferente y source
SHA diferente. La auditoría E2E compara todas las source keys y hashes reales, por lo que
un cambio científico continúa levantando `BootstrapConflict`.

## 7. Matriz de cobertura crítica

| Invariante | Evidencia ejecutable | Estado | ¿Muta v1 oficial? |
|---|---|---|---|
| atomic rollback | `test_failure_after_partial_real_bulk_insert_is_atomic` | PASS | NO |
| digest mismatch pre-write | `test_digest_mismatch_aborts_before_writes` | PASS | NO |
| patient-disjoint trigger | `test_patient_disjoint_and_source_record_unique` | PASS | NO |
| identity consistency | `test_assignment_identity_and_class_consistency` + trigger fixture | PASS | NO |
| class consistency | `test_assignment_identity_and_class_consistency` | PASS | NO |
| assignment uniqueness | `test_patient_disjoint_and_source_record_unique` | PASS | NO |
| concurrency locking | `test_dataset_version_nowait_lock_blocks_concurrent_generator` | PASS | NO |
| same-seed reproducibility | optimizer and patient-group unit tests | PASS | NO |
| idempotent APPLY | snapshot/APPLY/snapshot E2E de 3C | PASS | NO |
| bootstrap GENERATED recognition | unit contract + CLI E2E | PASS | NO |
| bootstrap dry-run no-write | `test_generated_bootstrap_audit_is_read_only` + CLI snapshots | PASS | NO |
| bootstrap conflict preservation | methodology/source/identity conflict unit tests | PASS | NO |
| official v1 immutability | fixture teardown + E2E snapshots | PASS | NO |

## 8. Suite y estado posterior

La suite completa terminó `71 passed, 0 skipped, 0 failed`. Los tres skips dependientes
del estado global fueron eliminados. `git diff --check` pasó.

Después de las pruebas, v1 permanece GENERATED con generated_at
`2026-08-13T09:00:52.387279-04:00`, 27.558 assignments, Patient digest
`cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f` y Record digest
`9709ce48b9b41bcacca49ccfb53ec62b48c4822c2fb8e227643bf26aed196ea2`.
Statistics, validation checks, materializations y activations siguen en cero; TRAINABLE
sigue NO. Legacy conserva 27.558 filas y el filesystem 22.046/2.756/2.756. Cero runs
históricos fueron vinculados a v1.

## 9. Readiness

Los dos motivos exclusivos del rechazo 3C quedaron corregidos:

```text
POST_GENERATED_TEST_COVERAGE_GAP=NO
BOOTSTRAP_GENERATED_DRY_RUN_AUDIT=PASS
SPLIT_3C1=APPROVED
SPLIT_3C_REAUDIT_READY=YES
```

Esto no aprueba retroactivamente SPLIT 3 ni habilita por sí solo SPLIT 4. Corresponde
repetir SPLIT 3C como auditoría independiente.
