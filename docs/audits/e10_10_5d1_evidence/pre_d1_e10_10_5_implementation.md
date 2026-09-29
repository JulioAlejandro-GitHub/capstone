# Ejecución D tras Gate C aprobado

**E10.10.5D — BLOQUEADA. GATE D NO APROBABLE.**

Se obtuvo backup consistente y restore legacy en PostgreSQL 17.9 aislado. El preflight rechazó `LEGACY_SEQUENCE_DRIFT`: dependencia IDENTITY `i` frente a `a` en Ruta A. Diagnóstico adicional: defaults cualificados producen `LEGACY_SCHEMA_DRIFT`. No hubo apply, delta, transición de revisión ni reparación de datos. Catálogo final, integridad/equivalencia adoptada, rollback, repetición y backup/restore adoptado siguen pendientes. No se inició E ni cutover.

[Informe de nueve puntos y comandos](e10_10_5_route_b_results.md), [diff de secuencia](e10_10_5d_evidence/sequence_difference.json), [hashes y límites](e10_10_5_data_equivalence.json). La certificación B y la implementación C previas se conservan; sus resultados no acreditan D. Riesgo adicional: backups privados en /private/tmp requieren conservación; no contienen credenciales en informes públicos.

---

# E10.10.5 — Implementación C tras Gate B aprobado

**E10.10.5C — ADAPTADOR IMPLEMENTADO. PENDIENTE DE REVISIÓN Y APROBACIÓN PARA ENSAYO SOBRE COPIA AISLADA.**

Gate B fue aprobado expresamente por el usuario. Se implementó exclusivamente C, con validación estática y fixtures inventadas. La certificación A/B permanece sin cambios en [Ruta A](e10_10_5_route_a_results.md) y [catálogo B](e10_10_5_catalog_diff.json). La implementación al cierre de B se conserva en [snapshot previo a C](e10_10_5c_evidence/pre_c_e10_10_5_implementation.md).

## Código entregado

- `adoption_v2/`: contrato estructural legacy y checksums congelados, autorización/preflight, referencias y archivo reversible, transformaciones deterministas, plan/reconciliación, delta independiente de baseline, ejecutor condicionado a D y CLI. [Contrato de uso](../../adoption_v2/README.md).
- `tests/adoption_v2/`: fixtures sintéticas y 50 tests de mapeos, conservación, rechazos científicos, identidad, reconciliación y transacción simulada.
- `scripts/db/check_v2_stage_c.py`: ocho comandos offline fijos, comprobación de 54 archivos históricos, mapeo por tabla/columna y evidencia sintética reproducible.
- Seis entregables C: plan Ruta B, CSV legacy, preflight, tests, riesgos e implementación. [Inventario de archivos y hashes](e10_10_5c_evidence/implementation_files.json).

El adaptador cubre 97 tablas fuente y 103 destino, con 105 entradas de mapping. Conserva 83 tablas de datos KEEP/PROTECTED íntegramente y trata la revisión Alembic mediante transición explícita, identifica las 11 REFACTOR y archiva originales de las 2 MERGE. No genera datos científicos ausentes. Las nuevas entidades reciben valores explícitos y UUID estables; no se depende de timestamps/UUID aleatorios para completar evidencia. Las configuraciones, eventos y payloads originales se conservan con sus hashes.

Los bindings aportan referencias a evidencia existente o documentos revisados con hash. No existe mapping aprobado para datos reales en C. La futura transacción sólo puede promover el head después de constraints, reconciliación y catálogo idéntico a Ruta A. No se usa stamp, no se desactivan guardas y no se ejecutan SQL históricos.

## Validación y evidencias

**50 tests C + 20 baseline + 5 Alembic = 75 aprobados. Ocho comandos offline aprobados.** Generación del delta de 617 sentencias, parser, Ruff y compilación correctos. El manifiesto conserva SHA-256 `c1063136941e9429373d91d666fbea5d25afd0dc39f111fdf2b9779aa1f51eb0`; los 54 archivos históricos permanecen intactos.

[Comandos y salidas](e10_10_5c_evidence/commands.json), [resultado estructurado](e10_10_5c_evidence/static_results.json), [entradas E10.10.4/B](e10_10_5c_evidence/inputs.json), [detalle de pruebas y correcciones](e10_10_5_adoption_tests.md), [nueve puntos del informe](e10_10_5_route_b_adoption_plan.md).

La revisión de C corrigió transporte de arrays/JSONB, bloqueo de contexto incompleto, coherencia de UUID, integridad E10, cardinalidad del destino y garantías del archivo. No hubo modificaciones del contrato científico, baseline, SQL históricos ni recursos operativos. Los tests transaccionales son simulaciones; aplicación/rollback/no-op/restore reales de adopción quedan pendientes de D.

## Cierre

No hubo conexiones SQL ni acciones Docker durante C. No se modificaron PostgreSQL operativo, datasets, modelos, usuarios, campañas, eventos, checkpoints o imágenes reales. No se ejecutaron adopción sobre copia real, D/E ni cutover.

**Se solicita Gate C para revisar el adaptador y autorizar el ensayo exclusivo sobre copia aislada en E10.10.5D.** La aprobación no se presupone ni se deriva de los tests.
