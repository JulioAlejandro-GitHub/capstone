# Resultados D

**E10.10.5D — BLOQUEADA. GATE D NO APROBABLE.**

Se obtuvo backup consistente y restore legacy en PostgreSQL 17.9 aislado. El preflight rechazó `LEGACY_SEQUENCE_DRIFT`: dependencia IDENTITY `i` frente a `a` en Ruta A. Diagnóstico adicional: defaults cualificados producen `LEGACY_SCHEMA_DRIFT`. No hubo apply, delta, transición de revisión ni reparación de datos. Catálogo final, integridad/equivalencia adoptada, rollback, repetición y backup/restore adoptado siguen pendientes. No se inició E ni cutover.

[Informe de nueve puntos y comandos](e10_10_5_route_b_results.md), [diff de secuencia](e10_10_5d_evidence/sequence_difference.json), [hashes y límites](e10_10_5_data_equivalence.json). La certificación B y la implementación C previas se conservan; sus resultados no acreditan D. Riesgo adicional: backups privados en /private/tmp requieren conservación; no contienen credenciales en informes públicos.

---

# E10.10.5 — Resultados de pruebas A/B

**E10.10.5B — RUTA A CERTIFICADA EN POSTGRESQL 17. PENDIENTE DE REVISIÓN Y APROBACIÓN.**

## Validación estática posterior a B-01

**25/25 tests aprobados** (20 estáticos, incluidos B-01 y A-01; 5 de entorno Alembic). **9/9 comandos offline aprobados**: regeneración --check, catálogo estático, ambas suites, heads/history, lint, formato y compilación en memoria. [Log](e10_10_5a_commands.json), [resultado estructural](e10_10_5a_static_results.json).

Se conservan los 54 SQL históricos, sus checksums acreditados y los cuerpos/constraints protegidos. El parser sigue siendo pglast 8.4 / PostgreSQL 18.4; la certificación del servidor se ejecutó por separado en 17.9. La evidencia A anterior a B-01 se conserva en [b01_original](e10_10_5b_evidence/b01_original/e10_10_5a_commands.json).

## Pruebas reales de PostgreSQL 17.9

**46/46 comprobaciones aprobadas: 40 negativas y 6 controles positivos.** Todas las pruebas de comportamiento ejecutaron DML como capstone_v2_runtime, sobre fixtures sintéticos, con triggers/constraints activos. Cada rechazo exige SQLSTATE y constraint/mensaje concreto: un error ajeno no cuenta como éxito. Los constraints diferidos se fuerzan con SET CONSTRAINTS ALL IMMEDIATE, sin desactivarlos. Los fixtures se revierten al finalizar la suite.

[Detalle JSON de cada caso](e10_10_5b_evidence/run_b01/server_tests.json).

| Prueba | Resultado |
| --- | --- |
| `positive_synthetic_training_configuration` | PASS |
| `A01_external_complementary_cross_dataset_positive_and_view_separation` | PASS |
| `A01_external_rejects_development` | PASS — 23514 |
| `A01_external_rejects_final_test` | PASS — 23514 |
| `A01_external_rejects_training_validation_final` | PASS — 23514 |
| `A01_external_rejects_calibration_default` | PASS — 23514 |
| `A01_external_rejects_calibration_selected` | PASS — 23514 |
| `A01_missing_dataset_origin_id` | PASS — 23514 |
| `A01_missing_dataset_origin_role` | PASS — 23514 |
| `A01_missing_population_manifest_uri` | PASS — 23514 |
| `A01_missing_population_manifest_sha256` | PASS — 23514 |
| `A01_missing_dataset_provenance_uri` | PASS — 23514 |
| `A01_missing_dataset_provenance_sha256` | PASS — 23514 |
| `A01_invalid_provenance_hash` | PASS — 23514 |
| `A01_origin_FK` | PASS — 23503 |
| `A01_no_external_validation_alias` | PASS — 23514 |
| `evaluation_immutable` | PASS — P0001 |
| `training_requires_configuration` | PASS — P0001 |
| `evaluation_requires_metrics_at_transaction_end` | PASS — P0001 |
| `evaluation_checkpoint_training_mismatch` | PASS — P0001 |
| `E10_missing_record_FK` | PASS — 23503 |
| `E10_event_key_identity` | PASS — 23514 |
| `E10_positive_record_projection` | PASS |
| `E10_sequence_gap` | PASS — P0001 |
| `E10_record_append_only` | PASS — P0001 |
| `E10_record_delete_forbidden` | PASS — P0001 |
| `E10_owner_fencing` | PASS — P0001 |
| `calibration_VAL_pair_positive` | PASS |
| `calibration_rejects_test` | PASS — 23514 |
| `calibration_rejects_external` | PASS — 23514 |
| `calibration_rejects_train` | PASS — 23514 |
| `calibration_rejects_validation` | PASS — 23514 |
| `calibration_pair_cannot_be_same` | PASS — P0001 |
| `calibration_pair_excludes_external` | PASS — P0001 |
| `publication_model_training_FK` | PASS — 23503 |
| `publication_checkpoint_FK` | PASS — 23503 |
| `publication_invalid_state` | PASS — 23514 |
| `publication_valid_lineage_positive` | PASS |
| `publication_one_active_per_model_version` | PASS — 23505 |
| `publication_event_append_only` | PASS — P0001 |
| `no_DDL` | PASS — 42501 |
| `no_TEMP` | PASS — 42501 |
| `no_TRUNCATE` | PASS — 42501 |
| `no_alembic_write` | PASS — 42501 |
| `no_ledger_write` | PASS — 42501 |
| `all_valid_fixtures_pass_deferred_constraints` | PASS |

## Ensayos adicionales aprobados

- Catálogo: cero diferencias en todas las categorías exigidas y en metadatos de columnas; ACL/owners y privilegios efectivos incluidos.
- Rollback: fallo real tras 500 DDL, con 103 tablas y 111 funciones ya presentes en la transacción; consulta nueva observa cero objetos public y ausencia de head.
- Idempotencia: upgrade repetido preserva catálogo, 103 tablas de datos, versiones MVCC/ctid, secuencia y filas técnicas.
- Restore: backup PostgreSQL 17.9 de origen aislado, con datos sintéticos confirmados; igualdad de catálogo, filas en 103 tablas y secuencia.
- Descriptor: rechazo de puerto operativo, creación de descriptor nuevo y rechazo de sobrescritura verificados sin servidor.
- Lint/formato/compilación de los scripts de certificación y JSON de evidencia válidos.

## Incidencias conservadas y límites

B-01, error de `%` en la guarda, orden/tipo de fixtures de publicación y restore inicial están documentados en [Ruta A](e10_10_5_route_a_results.md). Los intentos de pruebas previos se conservan como server_tests_attempt_01/02.json; no se contaron como pruebas aprobadas. La primera restauración falló por owner de extensión y representación ACL; el procedimiento corregido pasó sin cambiar permisos del contrato.

**Fallos obligatorios pendientes en B: ninguno.** No se ejecutaron pruebas de adopción legacy ni recorridos funcionales API/React/TRAIN reales, ni C/D/E. No se certifica cobertura de todas las ramas de las funciones ni semántica científica fuera del contrato ensayado.
